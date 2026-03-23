"""
test_routes_smoke.py — Parametrized Smoke Test for All 7 V1 Endpoints

Verifies that all endpoints are registered, reachable, and return the
correct stub status codes:
    - GET single-artifact reads → 404 (no artifact found)
    - GET /artifacts collection → 200 with empty list
    - POST reprocess actions → 202 Accepted
"""

import pytest


# ── Test data: (method, path, expected_status) ────────
ENDPOINT_CASES = [
    # Single-artifact GETs → 404 because no artifacts exist yet
    ("GET", "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/snapshot", 404),
    ("GET", "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/briefing", 404),
    ("GET", "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/workbook-profile", 404),
    ("GET", "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/workbook-review", 404),
    # Collection endpoint → 200 with empty list
    ("GET", "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/artifacts", 200),
    # Reprocess actions → 202 Accepted
    ("POST", "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/reprocess/intake", 202),
    ("POST", "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/reprocess/workbook", 202),
]


@pytest.mark.parametrize("method,path,expected_status", ENDPOINT_CASES)
def test_endpoint_stub_status(client, method, path, expected_status):
    """Each V1 endpoint should return its correct stub status code."""
    if method == "GET":
        response = client.get(path)
    elif method == "POST":
        response = client.post(path)
    else:
        pytest.fail(f"Unexpected method: {method}")

    assert response.status_code == expected_status, (
        f"{method} {path} returned {response.status_code}, expected {expected_status}. "
        f"Body: {response.text}"
    )


def test_artifacts_collection_returns_empty_list(client):
    """GET /artifacts should return 200 with an empty artifacts list."""
    response = client.get(
        "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/artifacts"
    )
    assert response.status_code == 200
    data = response.json()
    assert "artifacts" in data
    assert data["artifacts"] == []


def test_reprocess_intake_returns_accepted_body(client):
    """POST /reprocess/intake should return 202 with status=accepted."""
    response = client.post(
        "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/reprocess/intake"
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "stub" in data["message"].lower() or "not yet implemented" in data["message"].lower()


def test_single_artifact_get_returns_not_found_detail(client):
    """GET single-artifact endpoints should return 404 with a detail message."""
    response = client.get(
        "/intelligence/v1/rfqs/00000000-0000-0000-0000-000000000001/snapshot"
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
