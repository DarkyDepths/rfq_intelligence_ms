"""
briefing_service.py — Intelligence Briefing Generation Service

BACAB Layer: Service (domain logic, called by controllers and event handlers)

Responsibility:
    Generates the intelligence_briefing artifact — the flagship proactive dossier.
    Consumes the rfq_intake_profile and produces a structured briefing with
    active sections (document understanding, compliance/risk) and unavailable
    sections (similarity, cost envelope) clearly marked.

Current status: STUB — not yet implemented.

TODO:
    - Executive summary generation
    - Document understanding section (from intake profile)
    - Compliance/risk flag extraction
    - Section availability matrix (cold-start awareness)
    - Dual format output (summary_text + structured fields)
    - Wire to artifact_datasource for persistence
"""

from src.datasources.artifact_datasource import ArtifactDatasource


class BriefingService:
    """Generates intelligence_briefing artifacts from intake profiles."""

    def __init__(self, datasource: ArtifactDatasource):
        self.datasource = datasource

    async def generate_briefing(self, rfq_id: str) -> None:
        """
        Generate an intelligence briefing for the given RFQ.

        Reads the current rfq_intake_profile, builds briefing sections,
        and persists the intelligence_briefing artifact.

        TODO: Implement briefing generation pipeline.
        """
        raise NotImplementedError("Briefing generation not yet implemented")
