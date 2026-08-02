"""Core message routing orchestrator.

Implements the hybrid routing pipeline:
1. Fast Path (deterministic rules) — instant, zero-cost
2. Multimodal Extraction (audio transcription, image loading)
3. Deep Path (LLM reasoning via Gemini 2.5 Flash)
"""

import logging
import re
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import json
import threading
from pathlib import Path

from app.core.config import settings
from app.schemas.message import MessageInput, RoutingResult
from app.services.audio_engine import transcribe_audio
from app.services.data_loader import data_loader
from app.services.vision_llm import route_message_with_llm

logger = logging.getLogger(__name__)

# Persistent disk cache for LLM responses
class PersistentCache:
    def __init__(self, path: str = ".llm_cache.json"):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.data = {}
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.warning("Failed to load cache from %s: %s", self.path, e)
                self.data = {}

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        data = self.data[key]
        return RoutingResult(**data)

    def __setitem__(self, key, value: RoutingResult):
        with self.lock:
            self.data[key] = value.model_dump()
            try:
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f)
            except Exception as e:
                logger.error("Failed to write cache to %s: %s", self.path, e)

_route_cache = PersistentCache()

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
    # Prompt injection patterns
    r"(?i)\bignore\s+all\s+previous\b",
    r"(?i)\bmark\s+this\s+(message\s+)?as\s+notify\b",
    r"(?i)\byou\s+are\s+now\s+(a|an)\b",
    r"(?i)\bforget\s+(your|all)\s+(previous\s+)?instructions\b",
    r"(?i)\bsystem\s*:\s*you\s+are\b",
    r"(?i)\bdisregard\s+(all\s+)?(prior|previous)\b",
    r"(?i)\bnew\s+instructions?\s*:",
    r"(?i)\boverride\s+(safety|security|rules)\b",
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
            route_method="fast_path",
        )

    # ---- Rule 2: Scam / phishing patterns → mute ----
    if text and _matches_any(text, SCAM_PATTERNS):
        return RoutingResult(
            action="mute",
            message_type="scam",
            reasoning="Message matches known scam/phishing pattern (OTP request, account threats, or prompt injection).",
            confidence=0.90,
            evidence_message_ids="none",
            route_method="fast_path",
        )

    if text and _matches_any(text, SCAM_URL_PATTERNS):
        return RoutingResult(
            action="mute",
            message_type="scam",
            reasoning="Message contains suspicious URL pattern consistent with phishing.",
            confidence=0.88,
            evidence_message_ids="none",
            route_method="fast_path",
        )

    # ---- Rule 3: Direct @mention of the user → notify ----
    # Only applies to non-business, non-forwarded messages to avoid spam bots triggering notify.
    is_safe_context = (conversation_type != "business" and forwarded_count == 0)
    
    if is_safe_context and text and user_id and f"@{user_id}" in text:
        return RoutingResult(
            action="notify",
            message_type="personal",
            reasoning=f"Message contains a direct @mention of the user ({user_id}).",
            confidence=0.90,
            evidence_message_ids="none",
            route_method="fast_path",
        )

    # Handle custom user handle
    if is_safe_context and text and settings.USER_HANDLE:
        if settings.USER_HANDLE.lower() in text.lower():
            return RoutingResult(
                action="notify",
                message_type="personal",
                reasoning=f"Message contains user's handle ({settings.USER_HANDLE}).",
                confidence=0.90,
                evidence_message_ids="none",
                route_method="fast_path",
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
            route_method="fast_path",
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
                route_method="fast_path",
            )

    # ---- Rule 6: High dismissal rate for Group (Personalization) ----
    grp = context.get("group", {})
    if grp.get("found"):
        reads = grp.get("user_messages_read_30d", 0)
        dismissals = grp.get("user_notifications_dismissed_30d", 0)
        total_interactions = reads + dismissals
        if total_interactions >= 5 and (dismissals / total_interactions) > 0.8:
            return RoutingResult(
                action="digest",
                message_type="event",
                reasoning=f"User has a historically high dismissal rate for this group ({dismissals} dismissals out of {total_interactions} interactions). Auto-routing to digest.",
                confidence=0.92,
                evidence_message_ids="none",
                route_method="fast_path",
            )

    # ---- Rule 7: Business highly dismissed (Personalization) ----
    if biz.get("found"):
        opens = biz.get("user_messages_opened_30d", 0)
        dismissals = biz.get("user_messages_dismissed_30d", 0)
        
        if dismissals >= 5 and opens == 0:
            return RoutingResult(
                action="mute",
                message_type="promotion",
                reasoning=f"User has consistently dismissed ({dismissals}) messages from this business recently without engaging. Hard muting.",
                confidence=0.95,
                evidence_message_ids="none",
                route_method="fast_path",
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

    # Generate cache key based on immutable characteristics
    text_content = str(msg.get("message_text", "") or "")
    sender = str(msg.get("sender_user_id", ""))
    media = str(msg.get("media_type", ""))
    cache_key = hashlib.md5(f"{text_content}:{sender}:{media}".encode()).hexdigest()

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
        _route_cache[cache_key] = fast_result
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

    # Generate cache key based on immutable characteristics
    text_content = str(msg.get("message_text", "") or "")
    sender = str(msg.get("sender_user_id", ""))
    media = str(msg.get("media_type", ""))
    cache_key = hashlib.md5(f"{text_content}:{sender}:{media}".encode()).hexdigest()

    # ---- DEEP PATH (LLM) ----
    if cache_key in _route_cache:
        logger.info("Deep path cache hit for message: %s", msg_id)
        return _route_cache[cache_key]

    llm_result = route_message_with_llm(
        message=msg,
        context=context,
        audio_transcript=audio_transcript,
        image_path=image_path,
    )

    elapsed = int((time.time() - start_time) * 1000)

    if llm_result is not None:
        # ---- ALGORITHMIC EVIDENCE & CONFIDENCE ----
        retrieved_evidence = data_loader.get_evidence_for_message(msg)
        
        # Calculate a deterministic confidence boundary based on history density
        history = context.get("history", [])
        base_confidence = llm_result.confidence
        
        if retrieved_evidence == "none":
            # Cold-start or no similar history: cap confidence at 0.6
            final_confidence = min(base_confidence, 0.6)
        else:
            # Rich history found
            bonus = 0.1 if len(history) > 3 else 0.0
            final_confidence = min(base_confidence + bonus, 1.0)
            
        result = RoutingResult(
            action=llm_result.action,
            message_type=llm_result.message_type,
            reasoning=llm_result.reasoning,
            confidence=round(final_confidence, 2),
            evidence_message_ids=retrieved_evidence,
            route_method="deep_path",
        )
        logger.info(
            "Deep path: %s → %s (%dms)", msg_id, result.action, elapsed
        )
        _route_cache[cache_key] = result
        return result

    # Fallback: should never reach here if LLM has a safe default
    logger.error("Complete routing failure for %s — defaulting to digest", msg_id)
    fallback_result = RoutingResult(
        action="digest",
        message_type="unknown",
        reasoning="Routing pipeline failed. Defaulting to digest to prevent message loss.",
        confidence=0.1,
        evidence_message_ids="none",
        route_method="unknown",
    )
    _route_cache[cache_key] = fallback_result
    return fallback_result


def route_messages(df: pd.DataFrame) -> list[dict]:
    """Route a batch of messages and return results concurrently."""
    data_loader.load()
    results = []

    total = len(df)
    logger.info("Starting batch routing of %d messages", total)
    
    def process_row(idx: int, row: pd.Series) -> dict:
        msg = row.to_dict()
        start_time = time.time()
        
        try:
            result = route_message(msg)
            elapsed = int((time.time() - start_time) * 1000)
            
            logger.info(
                "[%d/%d] %s → %s (%dms) via %s",
                idx + 1, total, msg["message_id"], result.action, elapsed, getattr(result, "route_method", "unknown")
            )
            
            return {
                "message_id": msg["message_id"],
                "action": result.action,
                "message_type": result.message_type,
                "reason": result.reasoning,
                "confidence": result.confidence,
                "evidence_message_ids": result.evidence_message_ids,
                "processing_time_ms": elapsed,
                "route_method": getattr(result, "route_method", "unknown"),
            }
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            logger.exception("Failed to route message %s", msg.get("message_id"))
            return {
                "message_id": msg["message_id"],
                "action": "digest",
                "message_type": "unknown",
                "reason": "Routing error — defaulting to digest.",
                "confidence": 0.1,
                "evidence_message_ids": "none",
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "route_method": "unknown",
            }
            
    # Use max_workers=3 to avoid blowing past OpenAI's token per minute (TPM) limits on gpt-4o-mini
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_row, i, row) for i, row in df.iterrows()]
        for future in as_completed(futures):
            results.append(future.result())
            
    # Sort results by original message ID to maintain deterministic output
    return sorted(results, key=lambda x: x["message_id"])
