"""processed_event.py — Inbound event processing state model."""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from src.database import Base


class ProcessedEvent(Base):
    """Tracks idempotent processing state for inbound lifecycle events."""

    __tablename__ = "processed_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(128), nullable=False, unique=True, index=True)
    event_type = Column(String(64), nullable=False)
    rfq_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    def __repr__(self):
        return (
            f"<ProcessedEvent(id={self.id}, event_id={self.event_id}, "
            f"event_type={self.event_type}, rfq_id={self.rfq_id}, status={self.status})>"
        )
