"""
snapshot_service.py — Intelligence Snapshot Assembly Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Assembles the rfq_intelligence_snapshot — the consumer-facing read model.
    A single assembled projection per RFQ containing latest states of all
    intelligence artifacts, section availability, confidence markers, and
    consumer hints. Simplifies UI and chatbot integration.

    For V1 skeleton: snapshot follows the same shared artifact-table pattern
    as all other artifacts including version and is_current.

Current status: STUB — not yet implemented.

TODO:
    - Artifact reference assembly (latest version + status of each artifact)
    - Availability matrix computation
    - Executive panel, briefing panel, workbook panel, review panel assembly
    - Consumer hints generation (ui_recommended_tabs, chatbot_suggested_questions)
    - Wire to artifact_datasource for persistence
"""

from src.datasources.artifact_datasource import ArtifactDatasource


class SnapshotService:
    """Assembles rfq_intelligence_snapshot read models from underlying artifacts."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    async def refresh_snapshot(self, rfq_id: str) -> None:
        """
        Rebuild the intelligence snapshot for the given RFQ.

        Reads the current state of all underlying artifacts and assembles
        a new snapshot version. Called after every artifact update.

        TODO: Implement snapshot assembly pipeline.
        """
        raise NotImplementedError("Snapshot assembly not yet implemented")
