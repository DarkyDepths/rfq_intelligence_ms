"""Add partial unique index for current artifact rows.

Revision ID: 002
Revises: 001
Create Date: 2026-03-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_artifact_current_per_type",
        "artifacts",
        ["rfq_id", "artifact_type"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_artifact_current_per_type", table_name="artifacts")
