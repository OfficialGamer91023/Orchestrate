"""Core message routing orchestrator.

Implements the hybrid routing pipeline:
1. Fast Path (deterministic rules) — instant, zero-cost
2. Multimodal Extraction (audio transcription, image loading)
3. Deep Path (LLM reasoning via Gemini 2.5 Flash)
"""

import logging
import re
import time

import pandas as pd

from app.core.config import settings
from app.schemas.message import MessageInput, RoutingResult
from app.services.audio_engine import transcribe_audio
from app.services.data_loader import data_loader
from app.services.vision_llm import route_message_with_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scam / Phishing Pattern Detection
# ---------------------------------------------------------------------------

SCAM_PATTERNS = [
    r"(?i)\bOTP\b.*\b(verify|confirm|send|share|enter)\b",
    r"(?i)\b(verify|confirm)\b.*\bOTP\b",
    r"(?i)\bpassword\b.*\b(verify|confirm|send|share|enter|reply)\b",
    r"(?i)\b(account|profile)\b.*\b(block|suspend|deactivat|restrict|expir)\b",
    r"(?i)\b(click|tap|visit)\b.*\b(link|url)\b.*\b(verify|confirm|update)\b",
    r"(?i)\bpay\b.*\b(small|reattempt)\b.*\bfee\b",
    r"(?i)\bignore\s+all\s+previous\b",  # Prompt injection
    r"(?i)\bmark\s+this\s+(message\s+)?as\s+notify\b",  # Prompt injection
]

SCAM_URL_PATTERNS = [
    r"(?i)account-login\.\w+",
    r"(?i)(?:amazon|flipkart|bank|paytm|phonepe|gpay)\w*-\w+\.\w+",  # Fake domains
    r"(?i)bit\.ly/\w+",  # Shortened URLs in suspicious context
]

GREETING_PATTERNS = [
    r"(?i)^good\s+morning\b",
    r"(?i)\bstay\s+positive\b",
    r"(?i)\bshare\s+(this|it)\s+(with|to)\b.*\b(people|friends|family)\b",
    r"(?i)\bforwarding\s+because\b",
    r"(?i)\bfwd\s+as\s+received\b",
    r"(?i)\bplease?\s+forward\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the given regex patterns."""
    return any(re.search(p, text) for p in patterns)


# ---------------------------------------------------------------------------
# Fast Path Rules Engine
# ---------------------------------------------------------------------------

def _execute_fast_path(
    msg: dict,
    context: dict,
) -> RoutingResult | None:
    """Apply deterministic rules to bypass LLM for obvious cases.

    Returns a RoutingResult if a rule matches, or None to fall through.
    """
    text = str(msg.get("message_text", "") or "")
    user_id = msg.get("user_id", "")
    forwarded_count = int(msg.get("forwarded_count", 0))
    media_type = msg.get("media_type")
    conversation_type = msg.get("conversation_type", "")

    # ---- Rule 1: Empty message (no text, no media) → mute ----
    has_media = media_type and pd.notna(media_type) and str(media_type).strip()
    if not text.strip() and not has_media:
        return RoutingResult(
            action="mute",
            message_type="unknown",
            reasoning="Empty message with no text or media content.",
            confidence=0.95,
            evidence_message_ids="none",
        )

    # ---- Rule 2: Scam / phishing patterns → mute ----
    if text and _matches_any(text, SCAM_PATTERNS):
        return RoutingResult(
            action="mute",
            message_type="scam",
            reasoning="Message matches known scam/phishing pattern (OTP request, account threats, or prompt injection).",
            confidence=0.90,
            evidence_message_ids="none",
        )

    if text and _matches_any(text, SCAM_URL_PATTERNS):
        return RoutingResult(
            action="mute",
            message_type="scam",
            reasoning="Message contains suspicious URL pattern consistent with phishing.",
            confidence=0.88,
            evidence_message_ids="none",
        )

    # ---- Rule 3: Direct @mention of the user → notify ----
    if text and user_id and f"@{user_id}" in text:
        return RoutingResult(
            action="notify",
            message_type="personal",
            reasoning=f"Message contains a direct @mention of the user ({user_id}).",
            confidence=0.90,
            evidence_message_ids="none",
        )

    # Handle custom user handle
    if text and settings.USER_HANDLE:
        if settings.USER_HANDLE.lower() in text.lower():
            return RoutingResult(
                action="notify",
                message_type="personal",
                reasoning=f"Message contains user's handle ({settings.USER_HANDLE}).",
                confidence=0.90,
                evidence_message_ids="none",
            )

    # ---- Rule 4: High forward count with greeting/chain pattern → mute ----
    if forwarded_count >= 5 and text and _matches_any(text, GREETING_PATTERNS):
        # Find historical evidence of similar forwards
        history = context.get("history", [])
        evidence = [
            h["message_id"]
            for h in history
            if h.get("forwarded_count", 0) >= 3
            and (h.get("was_dismissed") or h.get("muted_after"))
        ]
        return RoutingResult(
            action="mute",
            message_type="forward",
            reasoning="Highly forwarded chain message with greeting/forward pattern.",
            confidence=0.85,
            evidence_message_ids=";".join(evidence[:3]) if evidence else "none",
        )

    # ---- Rule 5: Unverified business with domain mismatch → mute ----
    biz = context.get("business", {})
    if biz.get("found") and not biz.get("verified") and biz.get("domain_mismatch"):
        # Check for additional risk signals
        if biz.get("account_age_days", 0) < 90 or biz.get("user_reports_30d", 0) > 10:
            return RoutingResult(
                action="mute",
                message_type="scam",
                reasoning=(
                    f"Unverified business with domain mismatch "
                    f"(official: {biz.get('official_domain')}, "
                    f"used: {biz.get('domain_used_by_sender')}), "
                    f"account age: {biz.get('account_age_days')} days, "
                    f"reports: {biz.get('user_reports_30d')}."
                ),
                confidence=0.88,
                evidence_message_ids="none",
            )

    # No fast-path rule matched → fall through to LLM
    return None


# ---------------------------------------------------------------------------
# Main Routing Function
# ---------------------------------------------------------------------------

def route_message(msg_input: MessageInput | dict) -> RoutingResult:
    """Route a single message through the full pipeline.

    Args:
        msg_input: Message data (Pydantic model or dict)

    Returns:
        RoutingResult with the decision
    """
    start_time = time.time()

    # Normalize to dict
    if isinstance(msg_input, MessageInput):
        msg = msg_input.model_dump()
    else:
        msg = dict(msg_input)

    msg_id = msg.get("message_id", "unknown")
    logger.info("Routing message: %s", msg_id)

    # Load context from datasets
    context = data_loader.get_full_context_for_message(msg)

    # ---- FAST PATH ----
    fast_result = _execute_fast_path(msg, context)
    if fast_result is not None:
        elapsed = int((time.time() - start_time) * 1000)
        logger.info(
            "Fast path: %s → %s (%dms)", msg_id, fast_result.action, elapsed
        )
        return fast_result

    # ---- MULTIMODAL EXTRACTION ----
    audio_transcript = None
    image_path = None

    media_type = msg.get("media_type")
    if media_type and pd.notna(media_type):
        media_path = context.get("media_path")
        if media_path:
            if str(media_type) == "voice":
                audio_transcript = transcribe_audio(media_path)
                if audio_transcript:
                    logger.info(
                        "Audio transcript for %s: %s...",
                        msg_id,
                        audio_transcript[:100],
                    )
            elif str(media_type) == "image":
                image_path = media_path

    # ---- DEEP PATH (LLM) ----
    llm_result = route_message_with_llm(
        message=msg,
        context=context,
        audio_transcript=audio_transcript,
        image_path=image_path,
    )

    elapsed = int((time.time() - start_time) * 1000)

    if llm_result is not None:
        result = RoutingResult(
            action=llm_result.action,
            message_type=llm_result.message_type,
            reasoning=llm_result.reasoning,
            confidence=llm_result.confidence,
            evidence_message_ids=llm_result.evidence_message_ids,
        )
        logger.info(
            "Deep path: %s → %s (%dms)", msg_id, result.action, elapsed
        )
        return result

    # Fallback: should never reach here if LLM has a safe default
    logger.error("Complete routing failure for %s — defaulting to digest", msg_id)
    return RoutingResult(
        action="digest",
        message_type="unknown",
        reasoning="Routing pipeline failed. Defaulting to digest to prevent message loss.",
        confidence=0.1,
        evidence_message_ids="none",
    )


def route_all_messages() -> list[dict]:
    """Route all messages from messages.csv and return results.

    Returns:
        List of dicts with output.csv columns
    """
    data_loader.load()
    results = []

    total = len(data_loader.messages)
    logger.info("Starting batch routing of %d messages", total)

    for idx, row in data_loader.messages.iterrows():
        msg = row.to_dict()
        start_time = time.time()

        try:
            result = route_message(msg)
            elapsed = int((time.time() - start_time) * 1000)

            results.append({
                "message_id": msg["message_id"],
                "action": result.action,
                "message_type": result.message_type,
                "reason": result.reasoning,
                "confidence": result.confidence,
                "evidence_message_ids": result.evidence_message_ids,
                "processing_time_ms": elapsed,
            })

            logger.info(
                "[%d/%d] %s → %s (%dms)",
                idx + 1, total, msg["message_id"], result.action, elapsed,
            )
        except Exception:
            logger.exception("Failed to route message %s", msg.get("message_id"))
            results.append({
                "message_id": msg["message_id"],
                "action": "digest",
                "message_type": "unknown",
                "reason": "Routing error — defaulting to digest.",
                "confidence": 0.1,
                "evidence_message_ids": "none",
                "processing_time_ms": int((time.time() - start_time) * 1000),
            })

    return results
