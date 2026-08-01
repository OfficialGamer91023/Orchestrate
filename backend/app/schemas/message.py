"""Pydantic v2 models for API request/response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionEnum(str, Enum):
    NOTIFY = "notify"
    DIGEST = "digest"
    MUTE = "mute"


class MessageTypeEnum(str, Enum):
    PERSONAL = "personal"
    URGENT = "urgent"
    EVENT = "event"
    PAYMENT = "payment"
    BUSINESS_UPDATE = "business_update"
    PROMOTION = "promotion"
    GREETING = "greeting"
    FORWARD = "forward"
    SPAM = "spam"
    SCAM = "scam"
    UNKNOWN = "unknown"


class ConversationType(str, Enum):
    PERSONAL = "personal"
    GROUP = "group"
    BUSINESS = "business"


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class MessageInput(BaseModel):
    """Input schema matching a row from messages.csv."""
    message_id: str
    user_id: str
    conversation_type: str
    group_id: str | None = None
    business_id: str | None = None
    sender_user_id: str | None = None
    created_at: str | None = None
    message_text: str | None = None
    media_type: str | None = None  # image, voice, or empty
    media_id: str | None = None
    forwarded_count: int = 0
    is_flagged_scam: bool = False  # Can be set by upstream rules


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class RoutingResult(BaseModel):
    """The LLM/rule-engine routing decision."""
    action: str = Field(description="Must be: notify, digest, or mute")
    message_type: str = Field(description="Best-fit message category")
    reasoning: str = Field(description="Step-by-step reasoning for the decision")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0-1")
    evidence_message_ids: str = Field(
        default="none",
        description="Semicolon-separated historical message IDs or 'none'",
    )


class MessageResponse(BaseModel):
    """API response for a single routed message."""
    message_id: str
    action: str
    message_type: str
    reasoning: str
    confidence: float
    evidence_message_ids: str
    processing_time_ms: int
    route_method: str  # fast_path or deep_path
    metrics: dict | None = None


class LogEntry(BaseModel):
    """Single log entry for the logs table view."""
    message_id: str
    user_id: str
    conversation_type: str
    sender_user_id: str | None = None
    group_id: str | None = None
    business_id: str | None = None
    message_text: str | None = None
    media_type: str | None = None
    audio_transcript: str | None = None
    routing_decision: str | None = None
    message_type: str | None = None
    routing_reasoning: str | None = None
    confidence: float | None = None
    evidence_message_ids: str | None = None
    processing_time_ms: int = 0
    route_method: str | None = None
    processed_at: datetime | None = None


class LogsResponse(BaseModel):
    """Paginated response for the logs endpoint."""
    total: int
    page: int
    limit: int
    items: list[LogEntry]


class ClassMetrics(BaseModel):
    """Precision, recall, F1 for a single class."""
    precision: float
    recall: float
    f1: float
    support: int  # Number of true instances


class BatchEvalResponse(BaseModel):
    """Response from the batch evaluation endpoint."""
    total_processed: int
    accuracy: float
    macro_f1: float
    notify_fpr: float  # False Positive Rate for notify specifically
    class_metrics: dict[str, ClassMetrics]


class DashboardStats(BaseModel):
    """High-level dashboard KPI data."""
    total_processed: int
    overall_accuracy: float | None = None
    avg_processing_time_ms: float
    decision_distribution: dict[str, int]  # {notify: X, digest: Y, mute: Z}
