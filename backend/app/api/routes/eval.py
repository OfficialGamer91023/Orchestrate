"""Batch evaluation API route."""

import csv
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_bearer_token
from app.db.database import get_db
from app.db.models import Message
from app.schemas.message import BatchEvalResponse
from app.services.data_loader import data_loader
from app.services.metrics import calculate_metrics
from app.services.router import route_messages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["evaluation"])


@router.post("/batch-eval", response_model=BatchEvalResponse)
async def batch_evaluate(
    force_recalculate: bool = Query(False),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bearer_token),
) -> BatchEvalResponse:
    """Process all messages from messages.csv, generate output.csv, and return metrics.

    This endpoint:
    1. Routes all messages through the pipeline
    2. Writes results to output.csv
    3. Compares against sample_messages.csv golden labels
    4. Returns precision/recall/F1 metrics
    """
    start = time.time()
    data_loader.load()

    # Check if we already have results and can skip
    existing_count = db.query(Message).count()
    total_messages = len(data_loader.messages)

    if existing_count >= total_messages and not force_recalculate:
        logger.info(
            "All %d messages already processed — using cached results",
            existing_count,
        )
        # Load results from DB
        results = []
        for msg in db.query(Message).all():
            results.append({
                "message_id": msg.message_id,
                "action": msg.routing_decision or "digest",
                "message_type": msg.message_type or "unknown",
                "reason": msg.routing_reasoning or "",
                "confidence": msg.confidence or 0.5,
                "evidence_message_ids": msg.evidence_message_ids or "none",
            })
    else:
        # Route all messages
        logger.info("Starting batch routing of %d messages", total_messages)
        results = await run_in_threadpool(route_messages, data_loader.messages)

        # Persist results to database
        for r in results:
            existing = (
                db.query(Message)
                .filter(Message.message_id == r["message_id"])
                .first()
            )
            if existing:
                existing.routing_decision = r["action"]
                existing.message_type = r["message_type"]
                existing.routing_reasoning = r["reason"]
                existing.confidence = r["confidence"]
                existing.evidence_message_ids = r["evidence_message_ids"]
                existing.processing_time_ms = r.get("processing_time_ms", 0)
                existing.route_method = "batch"
            else:
                # Find original message data
                orig = data_loader.messages[
                    data_loader.messages["message_id"] == r["message_id"]
                ]
                if not orig.empty:
                    o = orig.iloc[0]
                    db_msg = Message(
                        message_id=r["message_id"],
                        user_id=str(o.get("user_id", "")),
                        conversation_type=str(o.get("conversation_type", "")),
                        group_id=(
                            str(o["group_id"])
                            if o.get("group_id") and str(o.get("group_id")).strip()
                            else None
                        ),
                        business_id=(
                            str(o["business_id"])
                            if o.get("business_id")
                            and str(o.get("business_id")).strip()
                            else None
                        ),
                        sender_user_id=(
                            str(o["sender_user_id"])
                            if o.get("sender_user_id")
                            and str(o.get("sender_user_id")).strip()
                            else None
                        ),
                        created_at_original=str(o.get("created_at", "")),
                        message_text=(
                            str(o["message_text"])
                            if o.get("message_text")
                            and str(o.get("message_text")).strip()
                            else None
                        ),
                        media_type=(
                            str(o["media_type"])
                            if o.get("media_type")
                            and str(o.get("media_type")).strip()
                            else None
                        ),
                        media_id=(
                            str(o["media_id"])
                            if o.get("media_id")
                            and str(o.get("media_id")).strip()
                            else None
                        ),
                        forwarded_count=int(o.get("forwarded_count", 0)),
                        routing_decision=r["action"],
                        message_type=r["message_type"],
                        routing_reasoning=r["reason"],
                        confidence=r["confidence"],
                        evidence_message_ids=r["evidence_message_ids"],
                        processing_time_ms=r.get("processing_time_ms", 0),
                        route_method="batch",
                    )
                    db.add(db_msg)

        db.commit()

    # Write output.csv
    output_path = Path(settings.DATASET_PATH).resolve() / "output.csv"
    _write_output_csv(results, output_path)

    # Also write to project root for submission
    root_output = Path(".").resolve() / "output.csv"
    _write_output_csv(results, root_output)

    logger.info(
        "Batch evaluation complete — %d results written to %s in %.1fs",
        len(results),
        output_path,
        time.time() - start,
    )

    # Calculate metrics against golden labels (sample_messages.csv)
    golden = _load_golden_labels()
    if golden:
        # Extract predictions for golden-label messages from existing results
        # instead of re-routing sample_messages (which wastes LLM calls)
        golden_ids = {g["message_id"] for g in golden}
        sample_results = [r for r in results if r["message_id"] in golden_ids]

        # If some golden messages were not in the 110-message batch, route them
        found_ids = {r["message_id"] for r in sample_results}
        missing_ids = golden_ids - found_ids
        if missing_ids:
            logger.info("Routing %d missing sample messages for evaluation", len(missing_ids))
            missing_df = data_loader.sample_messages[
                data_loader.sample_messages["message_id"].isin(missing_ids)
            ]
            sample_results.extend(route_messages(missing_df))

        metrics = calculate_metrics(sample_results, golden)
        metrics.total_processed = len(results)  # Keep total processed as 110 for the UI

        # P2: Attach cost/latency tracking
        total_latency = sum(r.get("processing_time_ms", 0) for r in results)
        metrics.total_latency_ms = total_latency
        metrics.avg_latency_ms = round(total_latency / len(results), 1) if results else 0.0
        return metrics

    # No golden labels available — return basic stats
    return BatchEvalResponse(
        total_processed=len(results),
        accuracy=0.0,
        macro_f1=0.0,
        notify_fpr=0.0,
        class_metrics={},
    )


def _write_output_csv(results: list[dict], output_path: Path) -> None:
    """Write prediction results to output.csv in the required format."""
    required_keys = {"message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"}
    for r in results:
        missing = required_keys - set(r.keys())
        if missing:
            logger.error("Output validation failed: missing columns %s in result %s", missing, r)
            raise ValueError(f"Output schema violation. Missing keys: {missing}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(required_keys),
        )
        writer.writeheader()
        for r in results:
            writer.writerow({
                "message_id": r["message_id"],
                "action": r["action"],
                "message_type": r.get("message_type", "unknown"),
                "reason": r.get("reason", ""),
                "confidence": r.get("confidence", 0.5),
                "evidence_message_ids": r.get("evidence_message_ids", "none"),
            })


def _load_golden_labels() -> list[dict]:
    """Load golden labels from sample_messages.csv for evaluation."""
    data_loader.load()
    if data_loader.sample_messages.empty:
        return []

    golden = []
    for _, row in data_loader.sample_messages.iterrows():
        if row.get("action"):
            golden.append({
                "message_id": row["message_id"],
                "action": row["action"],
                "message_type": row.get("message_type", ""),
            })
    return golden
