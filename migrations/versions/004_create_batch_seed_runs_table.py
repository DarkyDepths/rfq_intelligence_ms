"""Create batch_seed_runs table for operational run-level seeding summaries.

Revision ID: 004
Revises: 003
Create Date: 2026-03-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "batch_seed_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("freeze_version", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("persist_artifacts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("input_scope_root", sa.String(length=512), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parsed_ok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parsed_with_warnings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_invalid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_ok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rollback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_status", sa.String(length=32), nullable=False),
        sa.Column("failure_samples", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("warning_samples", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_batch_seed_runs_run_id", "batch_seed_runs", ["run_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_batch_seed_runs_run_id", table_name="batch_seed_runs")
    op.drop_table("batch_seed_runs")
