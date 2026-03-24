"""
app_context.py — BACAB Dependency Injection / Service Registry

BACAB Layer: Cross-cutting (wiring)

Responsibility:
    Wires together all BACAB layers so that each request gets the correct
    dependency graph. Uses FastAPI's Depends() for constructor injection.
    This file is the single place where the object graph is assembled.

    Wiring:
        - artifact_datasource (needs db session)
        - manager_connector (needs manager base URL from config)
        - artifact_translator (stateless)
        - services (need datasource/connectors)
        - intelligence_controller (needs read service)
        - reprocess_controller (needs reprocess services)

    No layer skips a level:
        route → controller → service → datasource

Current status: COMPLETE for skeleton.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.config.settings import settings

# ── Datasources ───────────────────────────────────────
from src.datasources.artifact_datasource import ArtifactDatasource

# ── Connectors ────────────────────────────────────────
from src.connectors.manager_connector import ManagerConnector

# ── Translators ───────────────────────────────────────
from src.translators.artifact_translator import ArtifactTranslator

# ── Controllers ───────────────────────────────────────
from src.controllers.intelligence_controller import IntelligenceController
from src.controllers.reprocess_controller import ReprocessController

# ── Services ──────────────────────────────────────────
from src.services.artifact_read_service import ArtifactReadService
from src.services.intake_service import IntakeService
from src.services.workbook_service import WorkbookService


# ═══════════════════════════════════════════════════════
# DATASOURCE PROVIDERS
# ═══════════════════════════════════════════════════════

def get_artifact_datasource(db: Session = Depends(get_db)) -> ArtifactDatasource:
    return ArtifactDatasource(db)


# ═══════════════════════════════════════════════════════
# CONNECTOR PROVIDERS
# ═══════════════════════════════════════════════════════

def get_manager_connector() -> ManagerConnector:
    return ManagerConnector(base_url=settings.MANAGER_MS_BASE_URL)


# ═══════════════════════════════════════════════════════
# TRANSLATOR PROVIDERS
# ═══════════════════════════════════════════════════════

def get_artifact_translator() -> ArtifactTranslator:
    return ArtifactTranslator()


# ═══════════════════════════════════════════════════════
# SERVICE PROVIDERS
# ═══════════════════════════════════════════════════════

def get_artifact_read_service(
    datasource: ArtifactDatasource = Depends(get_artifact_datasource),
    translator: ArtifactTranslator = Depends(get_artifact_translator),
) -> ArtifactReadService:
    return ArtifactReadService(datasource=datasource, translator=translator)


def get_intake_service(
    datasource: ArtifactDatasource = Depends(get_artifact_datasource),
    connector: ManagerConnector = Depends(get_manager_connector),
) -> IntakeService:
    return IntakeService(datasource=datasource, connector=connector)


def get_workbook_service(
    datasource: ArtifactDatasource = Depends(get_artifact_datasource),
    connector: ManagerConnector = Depends(get_manager_connector),
) -> WorkbookService:
    return WorkbookService(datasource=datasource, connector=connector)


# ═══════════════════════════════════════════════════════
# CONTROLLER PROVIDERS
# ═══════════════════════════════════════════════════════

def get_intelligence_controller(
    artifact_read_service: ArtifactReadService = Depends(get_artifact_read_service),
) -> IntelligenceController:
    return IntelligenceController(artifact_read_service=artifact_read_service)


def get_reprocess_controller(
    intake_service: IntakeService = Depends(get_intake_service),
    workbook_service: WorkbookService = Depends(get_workbook_service),
) -> ReprocessController:
    return ReprocessController(
        intake_service=intake_service,
        workbook_service=workbook_service,
    )
