"""Create artifacts table with JSONB content, constraints, and indexes.

Revision ID: 001
Revises: None
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("rfq_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("artifact_type", sa.String(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("content", JSONB(), nullable=True),
        sa.Column("source_event_type", sa.String(), nullable=True),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        # Constraints
        sa.UniqueConstraint("rfq_id", "artifact_type", "version", name="uq_artifact_version"),
    )

    # Composite index for fast current-artifact lookup
    op.create_index(
        "ix_artifact_current_lookup",
        "artifacts",
        ["rfq_id", "artifact_type", "is_current"],
    )


def downgrade() -> None:
    op.drop_index("ix_artifact_current_lookup", table_name="artifacts")
    op.drop_table("artifacts")
