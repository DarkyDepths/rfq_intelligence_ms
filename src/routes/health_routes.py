"""
health_routes.py — Health Check Endpoint

BACAB Layer: Route (API layer — HTTP endpoint definition)

Responsibility:
    Provides a simple health check endpoint for monitoring tools,
    load balancers, and development verification.

Current status: COMPLETE for skeleton.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Health check — returns 200 if the service is alive."""
    return {"status": "healthy", "service": "rfq_intelligence_ms"}
