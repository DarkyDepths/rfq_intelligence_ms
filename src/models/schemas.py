"""
schemas.py — Pydantic Response / Request Schemas

BACAB Layer: Model (data shapes for API boundary)

Responsibility:
    Defines the Pydantic models used for API request validation and
    response serialization. These are transport-layer shapes, not
    domain models or artifact content schemas.

Current status: STUB — minimal schemas for skeleton endpoints.

TODO:
    - Add detailed artifact content schemas per type when business logic lands
    - Add pagination schemas for artifact listing
    - Add event payload schemas for inbound events
"""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response shape for GET /health."""
    status: str
    service: str


class ArtifactSummary(BaseModel):
    """Compact artifact summary for the artifact index endpoint."""
    id: UUID
    rfq_id: UUID
    artifact_type: str
    version: int
    status: str
    is_current: bool
    schema_version: str
    created_at: str
    updated_at: Optional[str] = None


class ArtifactResponse(BaseModel):
    """Full artifact response for single-artifact GET endpoints."""
    id: UUID
    rfq_id: UUID
    artifact_type: str
    version: int
    status: str
    is_current: bool
    content: Optional[Any] = None
    source_event_type: Optional[str] = None
    source_event_id: Optional[str] = None
    schema_version: str
    created_at: str
    updated_at: Optional[str] = None


class ArtifactListResponse(BaseModel):
    """Response shape for GET /rfqs/{rfq_id}/artifacts."""
    artifacts: list[ArtifactSummary] = []


class ReprocessResponse(BaseModel):
    """Response shape for POST /reprocess/* endpoints."""
    status: str
    message: str
