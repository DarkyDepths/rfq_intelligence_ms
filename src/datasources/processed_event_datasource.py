"""processed_event_datasource.py — Persistence for inbound event processing state."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.processed_event import ProcessedEvent


class ProcessedEventDatasource:
    """Handles DB operations for processed lifecycle events."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_event_id(self, event_id: str) -> Optional[ProcessedEvent]:
        return self.db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()

    def create_processing_event(self, event_id: str, event_type: str, rfq_id: str) -> ProcessedEvent:
        event = ProcessedEvent(
            event_id=event_id,
            event_type=event_type,
            rfq_id=rfq_id,
            status="processing",
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            failed_at=None,
            error_message=None,
        )
        self.db.add(event)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing = self.get_by_event_id(event_id)
            if existing is None:
                raise
            return existing
        return event

    def mark_processing(self, event: ProcessedEvent) -> ProcessedEvent:
        event.status = "processing"
        event.started_at = datetime.now(timezone.utc)
        event.completed_at = None
        event.failed_at = None
        event.error_message = None
        self.db.flush()
        return event

    def mark_completed(self, event: ProcessedEvent) -> ProcessedEvent:
        event.status = "completed"
        event.completed_at = datetime.now(timezone.utc)
        event.failed_at = None
        event.error_message = None
        self.db.flush()
        return event

    def mark_failed(self, event: ProcessedEvent, error_message: str) -> ProcessedEvent:
        event.status = "failed"
        event.failed_at = datetime.now(timezone.utc)
        event.error_message = error_message[:2000]
        self.db.flush()
        return event
