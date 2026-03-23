"""
test_health.py — Health Endpoint Smoke Test

Verifies that GET /health returns 200 with the expected response body.
"""


def test_health_returns_200(client):
    """GET /health should return 200 with status=healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "rfq_intelligence_ms"
