"""DB invariant tests for artifacts table constraints."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.artifact import Artifact


def test_unique_current_artifact_per_type_enforced(db_session):
    """At most one current artifact is allowed per (rfq_id, artifact_type)."""
    rfq_id = uuid.uuid4()

    db_session.add(
        Artifact(
            rfq_id=rfq_id,
            artifact_type="intelligence_briefing",
            version=1,
            is_current=True,
            status="complete",
            content={"v": 1},
        )
    )
    db_session.flush()

    db_session.add(
        Artifact(
            rfq_id=rfq_id,
            artifact_type="intelligence_briefing",
            version=2,
            is_current=True,
            status="complete",
            content={"v": 2},
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_non_current_history_rows_still_allowed(db_session):
    """Multiple historical rows are allowed when is_current is false."""
    rfq_id = uuid.uuid4()

    db_session.add_all(
        [
            Artifact(
                rfq_id=rfq_id,
                artifact_type="workbook_profile",
                version=1,
                is_current=False,
                status="complete",
                content={"v": 1},
            ),
            Artifact(
                rfq_id=rfq_id,
                artifact_type="workbook_profile",
                version=2,
                is_current=False,
                status="complete",
                content={"v": 2},
            ),
        ]
    )

    db_session.flush()
