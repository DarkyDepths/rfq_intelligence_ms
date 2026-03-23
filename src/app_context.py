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
        - intelligence_controller (needs datasource + translator)
        - reprocess_controller (stateless stub)

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
# CONTROLLER PROVIDERS
# ═══════════════════════════════════════════════════════

def get_intelligence_controller(
    datasource: ArtifactDatasource = Depends(get_artifact_datasource),
    translator: ArtifactTranslator = Depends(get_artifact_translator),
) -> IntelligenceController:
    return IntelligenceController(datasource=datasource, translator=translator)


def get_reprocess_controller() -> ReprocessController:
    return ReprocessController()
