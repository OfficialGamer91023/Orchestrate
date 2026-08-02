import re
from datetime import datetime

with open("backend/app/services/router.py", "r") as f:
    content = f.read()

# Add _is_dnd_active
dnd_logic = """
def _is_dnd_active(user_ctx: dict, msg_timestamp_str: str) -> bool:
    dnd = user_ctx.get("do_not_disturb_window")
    if not dnd or not msg_timestamp_str:
        return False
    try:
        from datetime import datetime
        start_str, end_str = dnd.split("-")
        msg_time = datetime.strptime(msg_timestamp_str, "%Y-%m-%d %H:%M").time()
        start = datetime.strptime(start_str.strip(), "%H:%M").time()
        end = datetime.strptime(end_str.strip(), "%H:%M").time()
        if start <= end:
            return start <= msg_time <= end
        else:
            return start <= msg_time or msg_time <= end
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Fast Path Rules Engine
"""
content = content.replace("# ---------------------------------------------------------------------------\n# Fast Path Rules Engine", dnd_logic)

# Replace fast path empty rule
empty_rule_old = """    # ---- Rule 1: Empty message (no text, no media) → mute ----
    has_media = media_type and pd.notna(media_type) and str(media_type).strip()
    if not text.strip() and not has_media:
        return RoutingResult(
            action="mute",
            message_type="unknown",
            reasoning="Empty message with no text or media content.",
            confidence=0.95,
            evidence_message_ids="none",
            route_method="fast_path",
        )"""
empty_rule_new = """    # ---- Rule 1: Empty message (no text, no media) → mute ----
    has_media = media_type and str(media_type).strip() and str(media_type) != "nan"
    if not text.strip() and not has_media and str(media_type) != "voice":
        return RoutingResult(
            action="mute",
            message_type="unknown",
            reasoning="Empty message with no text or media content.",
            confidence=0.92,
            evidence_message_ids="none",
            route_method="fast_path",
        )"""
content = content.replace(empty_rule_old, empty_rule_new)

# Replace @mention rule
mention_old = """    # ---- Rule 3: Direct @mention of the user → notify ----
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
            )"""
mention_new = """    # ---- Rule 3: Direct @mention of the user → notify ----
    is_safe_context = (conversation_type != "business" and forwarded_count == 0)
    user_name = context.get("user", {}).get("first_name", "").lower()
    
    if is_safe_context and text:
        text_lower = text.lower()
        if (user_name and user_name in text_lower) or (f"@{user_id}" in text_lower) or ("you" in text_lower and len(text_lower.split()) < 15):
            return RoutingResult(
                action="notify",
                message_type="personal",
                reasoning="Message directly mentions the user or uses direct pronouns in a short safe context.",
                confidence=0.85,
                evidence_message_ids="none",
                route_method="fast_path",
            )"""
content = content.replace(mention_old, mention_new)

with open("backend/app/services/router.py", "w") as f:
    f.write(content)
