"""
constants.py — Shared Vocabulary

BACAB Layer: Utils (cross-cutting)

Responsibility:
    Defines the canonical vocabulary shared across the intelligence service:
    artifact types, statuses, and event types. These constants are the
    single source of truth for valid enum-like values throughout the codebase.

Current status: COMPLETE for skeleton.
"""

# ── Artifact Types ────────────────────────────────────
# 6 core intelligence artifacts + 2 parser support artifacts used in
# workbook.uploaded flow (cost_breakdown_profile, parser_report).
ARTIFACT_TYPES = [
    "rfq_intake_profile",
    "intelligence_briefing",
    "workbook_profile",
    "cost_breakdown_profile",
    "parser_report",
    "workbook_review_report",
    "rfq_intelligence_snapshot",
    "rfq_analytical_record",
]

# ── Artifact Statuses ─────────────────────────────────
# Lifecycle state for each artifact instance.
ARTIFACT_STATUSES = ["pending", "partial", "complete", "failed"]

# ── Event Types ───────────────────────────────────────
# The 3 V1 event triggers from rfq_manager_ms.
EVENT_TYPES = ["rfq.created", "workbook.uploaded", "outcome.recorded"]
