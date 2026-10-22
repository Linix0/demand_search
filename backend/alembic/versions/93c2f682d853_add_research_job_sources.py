"""add shared research job source membership

Revision ID: 93c2f682d853
Revises: ae1ad88ecfe8
Create Date: 2026-10-22 17:22:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "93c2f682d853"
down_revision: str | None = "ae1ad88ecfe8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_job_sources",
        sa.Column("research_job_id", sa.Uuid(), nullable=False),
        sa.Column("source_item_id", sa.Uuid(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_job_id"],
            ["research_jobs.id"],
            name=op.f("fk_research_job_sources_research_job_id_research_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_item_id"],
            ["source_items.id"],
            name=op.f("fk_research_job_sources_source_item_id_source_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_job_sources")),
        sa.UniqueConstraint(
            "research_job_id",
            "source_item_id",
            name="uq_research_job_sources_job_source",
        ),
    )
    with op.batch_alter_table("research_job_sources", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_research_job_sources_research_job_id"),
            ["research_job_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_research_job_sources_source_item_id"),
            ["source_item_id"],
            unique=False,
        )

    # Existing sources already retain their original job, so backfill those memberships
    # before new jobs begin sharing the source pool.
    op.execute(
        sa.text(
            """
            INSERT INTO research_job_sources (
                id, research_job_id, source_item_id, first_seen_at, created_at, updated_at
            )
            SELECT id, research_job_id, id, COALESCE(collected_at, created_at),
                   created_at, updated_at
            FROM source_items
            WHERE research_job_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("research_job_sources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_research_job_sources_source_item_id"))
        batch_op.drop_index(batch_op.f("ix_research_job_sources_research_job_id"))

    op.drop_table("research_job_sources")
