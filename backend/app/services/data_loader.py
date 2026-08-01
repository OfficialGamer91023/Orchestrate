"""Loads all hackathon CSV files and provides context retrieval functions.

This module loads the 13 dataset CSVs into pandas DataFrames at startup
and exposes helper functions to retrieve contextualized information for
any given message, user, group, or business.
"""

import logging
from pathlib import Path

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


from typing import Any

def _safe_int(val: Any, default: int = 0) -> int:
    if pd.notna(val):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            pass
    return default


def _safe_bool(val: Any, default: bool = False) -> bool:
    if pd.notna(val):
        try:
            return bool(int(float(val)))
        except (ValueError, TypeError):
            return bool(val)
    return default



class DataLoader:
    """Singleton-style loader for the hackathon dataset."""

    def __init__(self, dataset_path: str | None = None):
        self._base = Path(dataset_path or settings.DATASET_PATH).resolve()
        self._loaded = False

        # DataFrames — populated by load()
        self.messages: pd.DataFrame = pd.DataFrame()
        self.sample_messages: pd.DataFrame = pd.DataFrame()
        self.users: pd.DataFrame = pd.DataFrame()
        self.groups: pd.DataFrame = pd.DataFrame()
        self.group_members: pd.DataFrame = pd.DataFrame()
        self.business_accounts: pd.DataFrame = pd.DataFrame()
        self.user_business_history: pd.DataFrame = pd.DataFrame()
        self.message_history: pd.DataFrame = pd.DataFrame()
        self.message_events: pd.DataFrame = pd.DataFrame()
        self.images: pd.DataFrame = pd.DataFrame()
        self.voice_notes: pd.DataFrame = pd.DataFrame()
        self.daily_notification_summary: pd.DataFrame = pd.DataFrame()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load all CSV files from the dataset directory."""
        if self._loaded:
            return

        csv_map = {
            "messages": "messages.csv",
            "sample_messages": "sample_messages.csv",
            "users": "users.csv",
            "groups": "groups.csv",
            "group_members": "group_members.csv",
            "business_accounts": "business_accounts.csv",
            "user_business_history": "user_business_history.csv",
            "message_history": "message_history.csv",
            "message_events": "message_events.csv",
            "images": "images.csv",
            "voice_notes": "voice_notes.csv",
            "daily_notification_summary": "daily_notification_summary.csv",
        }

        for attr, filename in csv_map.items():
            fpath = self._base / filename
            if fpath.exists():
                df = pd.read_csv(fpath)
                setattr(self, attr, df)
                logger.info("Loaded %s: %d rows", filename, len(df))
            else:
                logger.warning("Dataset file not found: %s", fpath)

        self._loaded = True
        logger.info(
            "Dataset loading complete — %d messages to route", len(self.messages)
        )

    # ------------------------------------------------------------------
    # Context Retrieval
    # ------------------------------------------------------------------

    def get_user_context(self, user_id: str) -> dict:
        """Get user preferences, DND window, and engagement stats."""
        row = self.users[self.users["user_id"] == user_id]
        if row.empty:
            return {"user_id": user_id, "found": False}

        r = row.iloc[0]
        return {
            "user_id": user_id,
            "found": True,
            "do_not_disturb_window": r.get("do_not_disturb_window", ""),
            "messages_opened_30d": _safe_int(r.get("messages_opened_30d", 0)),
            "messages_replied_30d": _safe_int(r.get("messages_replied_30d", 0)),
            "notifications_dismissed_30d": _safe_int(
                r.get("notifications_dismissed_30d", 0)
            ),
            "messages_reported_30d": _safe_int(r.get("messages_reported_30d", 0)),
        }

    def get_group_context(self, group_id: str, user_id: str) -> dict:
        """Get group metadata and the user's relationship with the group."""
        result: dict = {"group_id": group_id, "found": False}

        # Group info
        grp = self.groups[self.groups["group_id"] == group_id]
        if not grp.empty:
            g = grp.iloc[0]
            result.update(
                {
                    "found": True,
                    "group_name": g.get("group_name", ""),
                    "group_type": g.get("group_type", ""),
                    "member_count": _safe_int(g.get("member_count", 0)),
                    "admin_count": _safe_int(g.get("admin_count", 0)),
                    "messages_30d": _safe_int(g.get("messages_30d", 0)),
                }
            )

        # User-group membership
        mem = self.group_members[
            (self.group_members["group_id"] == group_id)
            & (self.group_members["user_id"] == user_id)
        ]
        if not mem.empty:
            m = mem.iloc[0]
            result.update(
                {
                    "user_role": m.get("role", "member"),
                    "user_messages_sent_30d": _safe_int(m.get("messages_sent_30d", 0)),
                    "user_messages_read_30d": _safe_int(m.get("messages_read_30d", 0)),
                    "user_replies_sent_30d": _safe_int(m.get("replies_sent_30d", 0)),
                    "user_notifications_dismissed_30d": _safe_int(
                        m.get("notifications_dismissed_30d", 0)
                    ),
                    "group_muted_by_user": _safe_bool(m.get("group_muted_by_user", 0)),
                }
            )

        # Sender info within the group (if sender is also a member)
        return result

    def get_sender_group_role(self, group_id: str, sender_user_id: str) -> dict:
        """Get the sender's role and activity in a group."""
        mem = self.group_members[
            (self.group_members["group_id"] == group_id)
            & (self.group_members["user_id"] == sender_user_id)
        ]
        if mem.empty:
            return {"sender_user_id": sender_user_id, "found": False}

        m = mem.iloc[0]
        return {
            "sender_user_id": sender_user_id,
            "found": True,
            "role": m.get("role", "member"),
            "messages_sent_30d": _safe_int(m.get("messages_sent_30d", 0)),
        }

    def get_business_context(self, business_id: str, user_id: str) -> dict:
        """Get business verification status and user's relationship."""
        result: dict = {"business_id": business_id, "found": False}

        # Business account info
        biz = self.business_accounts[
            self.business_accounts["business_id"] == business_id
        ]
        if not biz.empty:
            b = biz.iloc[0]
            result.update(
                {
                    "found": True,
                    "display_name": b.get("display_name", ""),
                    "brand_name": b.get("brand_name", ""),
                    "category": b.get("category", ""),
                    "verified": _safe_bool(b.get("verified", 0)),
                    "official_domain": b.get("official_domain", ""),
                    "domain_used_by_sender": b.get("domain_used_by_sender", ""),
                    "account_age_days": _safe_int(b.get("account_age_days", 0)),
                    "messages_sent_30d": _safe_int(b.get("messages_sent_30d", 0)),
                    "user_reports_30d": _safe_int(b.get("user_reports_30d", 0)),
                    "domain_used_by_sender_age_days": _safe_int(
                        b.get("domain_used_by_sender_age_days", 0)
                    ),
                    "domain_mismatch": (
                        str(b.get("official_domain", ""))
                        != str(b.get("domain_used_by_sender", ""))
                    ),
                }
            )

        # User-business history
        ubh = self.user_business_history[
            (self.user_business_history["user_id"] == user_id)
            & (self.user_business_history["business_id"] == business_id)
        ]
        if not ubh.empty:
            u = ubh.iloc[0]
            result.update(
                {
                    "user_relationship": u.get("why_user_knows_account", ""),
                    "allows_promotions": _safe_bool(u.get("allows_promotions", 0)),
                    "promotions_opted_out_at": (
                        str(u["promotions_opted_out_at"])
                        if pd.notna(u.get("promotions_opted_out_at"))
                        else None
                    ),
                    "activity_count_180d": _safe_int(u.get("activity_count_180d", 0)),
                    "user_messages_opened_30d": _safe_int(
                        u.get("messages_opened_30d", 0)
                    ),
                    "user_messages_dismissed_30d": _safe_int(
                        u.get("messages_dismissed_30d", 0)
                    ),
                    "user_messages_replied_30d": _safe_int(
                        u.get("messages_replied_30d", 0)
                    ),
                }
            )
        else:
            result["user_relationship"] = "none"

        return result

    def get_message_history_context(
        self,
        user_id: str,
        sender_user_id: str | None = None,
        group_id: str | None = None,
        business_id: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get relevant historical messages and user reactions to them."""
        hist = self.message_history[self.message_history["user_id"] == user_id]

        # Filter by context
        if sender_user_id:
            sender_hist = hist[hist["sender_user_id"] == sender_user_id]
            if not sender_hist.empty:
                hist = sender_hist
        if group_id:
            group_hist = hist[hist["group_id"] == group_id]
            if not group_hist.empty:
                hist = group_hist
        if business_id:
            biz_hist = hist[hist["business_id"] == business_id]
            if not biz_hist.empty:
                hist = biz_hist

        # Sort by date (most recent first) and limit
        if "created_at" in hist.columns:
            hist = hist.sort_values("created_at", ascending=False)
        hist = hist.head(limit)

        results = []
        for _, row in hist.iterrows():
            msg_id = row.get("message_id", "")
            entry: dict = {
                "message_id": msg_id,
                "message_text": row.get("message_text", ""),
                "conversation_type": row.get("conversation_type", ""),
                "created_at": str(row.get("created_at", "")),
                "forwarded_count": _safe_int(row.get("forwarded_count", 0)),
                "media_type": row.get("media_type", ""),
            }

            # Join with events
            events = self.message_events[
                (self.message_events["user_id"] == user_id)
                & (self.message_events["message_id"] == msg_id)
            ]
            if not events.empty:
                e = events.iloc[0]
                entry.update(
                    {
                        "was_opened": _safe_bool(e.get("message_opened", 0)),
                        "was_replied": _safe_bool(e.get("message_replied", 0)),
                        "reaction_time_minutes": _safe_int(
                            e.get("reaction_time_minutes", 0)
                        ),
                        "was_dismissed": _safe_bool(e.get("notification_dismissed", 0)),
                        "muted_after": _safe_bool(e.get("muted_after_message", 0)),
                        "was_reported": _safe_bool(e.get("message_reported", 0)),
                    }
                )

            results.append(entry)

        return results

    def get_notification_load(self, user_id: str, days: int = 7) -> dict:
        """Get the user's recent notification volume."""
        dns = self.daily_notification_summary[
            self.daily_notification_summary["user_id"] == user_id
        ]
        if dns.empty:
            return {"user_id": user_id, "total_sent": 0, "total_dismissed": 0}

        # Take last N days
        if "date" in dns.columns:
            dns = dns.sort_values("date", ascending=False).head(days)

        return {
            "user_id": user_id,
            "total_sent": int(dns["notifications_sent"].sum()),
            "total_dismissed": int(dns["notifications_dismissed"].sum()),
            "avg_daily_sent": round(float(dns["notifications_sent"].mean()), 1),
            "avg_daily_dismissed": round(
                float(dns["notifications_dismissed"].mean()), 1
            ),
            "dismiss_rate": round(
                float(dns["notifications_dismissed"].sum())
                / max(float(dns["notifications_sent"].sum()), 1),
                3,
            ),
        }

    def get_media_path(self, media_type: str, media_id: str) -> str | None:
        """Resolve a media_id to its actual file path."""
        if media_type == "image":
            row = self.images[self.images["image_id"] == media_id]
            col = "file_path"
        elif media_type == "voice":
            row = self.voice_notes[self.voice_notes["voice_note_id"] == media_id]
            col = "file_path"
        else:
            return None

        if row.empty:
            return None

        rel_path = row.iloc[0][col]
        full_path = self._base / rel_path
        return str(full_path) if full_path.exists() else None

    def get_full_context_for_message(self, msg: dict) -> dict:
        """Build the complete context bundle for a single message."""
        user_id = msg.get("user_id", "")
        context: dict = {
            "user": self.get_user_context(user_id),
            "notification_load": self.get_notification_load(user_id),
        }

        group_id = msg.get("group_id")
        if group_id and pd.notna(group_id) and str(group_id).strip():
            context["group"] = self.get_group_context(str(group_id), user_id)
            sender = msg.get("sender_user_id")
            if sender and pd.notna(sender):
                context["sender_role"] = self.get_sender_group_role(
                    str(group_id), str(sender)
                )

        business_id = msg.get("business_id")
        if business_id and pd.notna(business_id) and str(business_id).strip():
            context["business"] = self.get_business_context(
                str(business_id), user_id
            )

        context["history"] = self.get_message_history_context(
            user_id=user_id,
            sender_user_id=(
                str(msg.get("sender_user_id"))
                if pd.notna(msg.get("sender_user_id"))
                else None
            ),
            group_id=(
                str(group_id) if group_id and pd.notna(group_id) else None
            ),
            business_id=(
                str(business_id)
                if business_id and pd.notna(business_id)
                else None
            ),
        )

        # Media path
        media_type = msg.get("media_type")
        media_id = msg.get("media_id")
        if (
            media_type
            and pd.notna(media_type)
            and media_id
            and pd.notna(media_id)
        ):
            context["media_path"] = self.get_media_path(
                str(media_type), str(media_id)
            )
        else:
            context["media_path"] = None

        return context


# Module-level singleton
data_loader = DataLoader()
