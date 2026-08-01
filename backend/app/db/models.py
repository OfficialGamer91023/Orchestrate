"""SQLAlchemy ORM models for messages and evaluations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class Message(Base):
    """Stores each processed message and its routing decision."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    message_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    conversation_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # personal, group, business
    group_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    business_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sender_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at_original: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Original timestamp from CSV
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # image, voice, or null
    media_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    forwarded_count: Mapped[int] = mapped_column(Integer, default=0)

    # Extracted content
    audio_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Routing decision
    routing_decision: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # notify, digest, mute
    message_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # personal, urgent, event, payment, etc.
    routing_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_message_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Semicolon-separated

    # Metadata
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    route_method: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # fast_path, deep_path
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="message", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<Message(message_id={self.message_id!r}, "
            f"decision={self.routing_decision!r})>"
        )


class Evaluation(Base):
    """Stores golden labels for evaluation against predictions."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_generate_uuid
    )
    message_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("messages.message_id"),
        unique=True,
        nullable=False,
    )
    expected_action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # notify, digest, mute
    expected_message_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    # Relationship
    message: Mapped["Message"] = relationship(back_populates="evaluation")

    def __repr__(self) -> str:
        return (
            f"<Evaluation(message_id={self.message_id!r}, "
            f"expected={self.expected_action!r})>"
        )
