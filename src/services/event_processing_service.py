"""event_processing_service.py — Idempotent event orchestration state service."""

from src.datasources.processed_event_datasource import ProcessedEventDatasource


class EventProcessingService:
    """Coordinates idempotency and status transitions for inbound events."""

    def __init__(self, datasource: ProcessedEventDatasource):
        self.datasource = datasource

    def begin_processing(self, event_id: str, event_type: str, rfq_id: str) -> tuple[str, object]:
        """
        Begin or resume processing for an event.

        Returns:
            - ("new", record)
            - ("retry", record)
            - ("duplicate_completed", record)
            - ("in_progress", record)
        """
        existing = self.datasource.get_by_event_id(event_id)
        if existing is None:
            record = self.datasource.create_processing_event(
                event_id=event_id,
                event_type=event_type,
                rfq_id=rfq_id,
            )
            self.datasource.db.commit()
            self.datasource.db.refresh(record)
            return "new", record

        if existing.status == "completed":
            return "duplicate_completed", existing

        if existing.status == "processing":
            return "in_progress", existing

        record = self.datasource.mark_processing(existing)
        self.datasource.db.commit()
        self.datasource.db.refresh(record)
        return "retry", record

    def mark_completed(self, event_id: str):
        record = self.datasource.get_by_event_id(event_id)
        if record is None:
            return None
        self.datasource.mark_completed(record)
        self.datasource.db.commit()
        self.datasource.db.refresh(record)
        return record

    def mark_failed(self, event_id: str, error_message: str):
        record = self.datasource.get_by_event_id(event_id)
        if record is None:
            return None
        self.datasource.mark_failed(record, error_message)
        self.datasource.db.commit()
        self.datasource.db.refresh(record)
        return record

    def rollback_active_transaction(self) -> None:
        self.datasource.db.rollback()
