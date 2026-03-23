"""
reprocess_controller.py — Reprocessing Controller

BACAB Layer: Controller (application orchestration — HTTP)

Responsibility:
    Handles manual reprocessing triggers via HTTP POST.
    In the future, these will call the appropriate service to re-run
    parsing pipelines. For now, returns 202 Accepted stubs.

    Flow: route → controller → service(s) → datasource

Current status: STUB — returns 202 Accepted without processing.

TODO:
    - Wire to intake_service for intake reprocessing
    - Wire to workbook_service for workbook reprocessing
    - Add idempotency checks
    - Add reprocessing status tracking
"""


class ReprocessController:
    """Handles manual reprocessing triggers (HTTP)."""

    def reprocess_intake(self, rfq_id: str) -> dict:
        """
        Trigger a manual re-run of intake parsing for the given RFQ.

        Returns 202 Accepted — processing happens asynchronously.
        """
        # TODO: Call intake_service.reprocess(rfq_id)
        return {
            "status": "accepted",
            "message": "Reprocess request received (stub only — not yet implemented)",
        }

    def reprocess_workbook(self, rfq_id: str) -> dict:
        """
        Trigger a manual re-run of workbook parsing for the given RFQ.

        Returns 202 Accepted — processing happens asynchronously.
        """
        # TODO: Call workbook_service.reprocess(rfq_id)
        return {
            "status": "accepted",
            "message": "Reprocess request received (stub only — not yet implemented)",
        }
