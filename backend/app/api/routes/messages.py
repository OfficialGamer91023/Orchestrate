"""Message ingestion and logs API routes."""

import logging
import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import verify_bearer_token
from app.db.database import get_db
from app.db.models import Message
from app.schemas.message import (
    LogEntry,
    LogsResponse,
    MessageInput,
    MessageResponse,
    DashboardStats,
)
from app.services.data_loader import data_loader
from app.services.router import route_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["messages"])


@router.post("/route-message", response_model=MessageResponse)
async def handle_route_message(
    payload: MessageInput,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bearer_token),
) -> MessageResponse:
    """Ingest a new message, process multimodality, route it, and persist."""
    start = time.time()

    # Ensure data is loaded
    data_loader.load()

    # Route the message
    result = route_message(payload)
    elapsed = int((time.time() - start) * 1000)

    # Determine route method
    route_method = "fast_path" if elapsed < 100 else "deep_path"

    # Persist to database
    db_msg = Message(
        message_id=payload.message_id,
        user_id=payload.user_id,
        conversation_type=payload.conversation_type,
        group_id=payload.group_id,
        business_id=payload.business_id,
        sender_user_id=payload.sender_user_id,
        created_at_original=payload.created_at,
        message_text=payload.message_text,
        media_type=payload.media_type,
        media_id=payload.media_id,
        forwarded_count=payload.forwarded_count,
        routing_decision=result.action,
        message_type=result.message_type,
        routing_reasoning=result.reasoning,
        confidence=result.confidence,
        evidence_message_ids=result.evidence_message_ids,
        processing_time_ms=elapsed,
        route_method=route_method,
    )

    # Upsert: update if already exists
    existing = (
        db.query(Message)
        .filter(Message.message_id == payload.message_id)
        .first()
    )
    if existing:
        for key, value in {
            "routing_decision": result.action,
            "message_type": result.message_type,
            "routing_reasoning": result.reasoning,
            "confidence": result.confidence,
            "evidence_message_ids": result.evidence_message_ids,
            "processing_time_ms": elapsed,
            "route_method": route_method,
        }.items():
            setattr(existing, key, value)
    else:
        db.add(db_msg)

    db.commit()

    return MessageResponse(
        message_id=payload.message_id,
        action=result.action,
        message_type=result.message_type,
        reasoning=result.reasoning,
        confidence=result.confidence,
        evidence_message_ids=result.evidence_message_ids,
        processing_time_ms=elapsed,
        route_method=route_method,
    )


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    decision_filter: str | None = Query(None),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bearer_token),
) -> LogsResponse:
    """Paginated fetching of processed messages for the dashboard."""
    query = db.query(Message)

    if decision_filter:
        query = query.filter(Message.routing_decision == decision_filter)

    total = query.count()
    items = (
        query.order_by(Message.processed_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return LogsResponse(
        total=total,
        page=page,
        limit=limit,
        items=[
            LogEntry(
                message_id=m.message_id,
                user_id=m.user_id,
                conversation_type=m.conversation_type,
                sender_user_id=m.sender_user_id,
                group_id=m.group_id,
                business_id=m.business_id,
                message_text=m.message_text,
                media_type=m.media_type,
                audio_transcript=m.audio_transcript,
                routing_decision=m.routing_decision,
                message_type=m.message_type,
                routing_reasoning=m.routing_reasoning,
                confidence=m.confidence,
                evidence_message_ids=m.evidence_message_ids,
                processing_time_ms=m.processing_time_ms,
                route_method=m.route_method,
                processed_at=m.processed_at,
            )
            for m in items
        ],
    )


@router.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bearer_token),
) -> DashboardStats:
    """Get high-level KPI data for the dashboard overview."""
    total = db.query(Message).count()

    if total == 0:
        return DashboardStats(
            total_processed=0,
            avg_processing_time_ms=0.0,
            decision_distribution={"notify": 0, "digest": 0, "mute": 0},
        )

    # Decision distribution
    from sqlalchemy import func

    dist = (
        db.query(Message.routing_decision, func.count(Message.id))
        .group_by(Message.routing_decision)
        .all()
    )
    distribution = {d: c for d, c in dist if d}

    # Average processing time
    avg_time = db.query(func.avg(Message.processing_time_ms)).scalar() or 0.0

    return DashboardStats(
        total_processed=total,
        avg_processing_time_ms=round(float(avg_time), 1),
        decision_distribution=distribution,
    )
