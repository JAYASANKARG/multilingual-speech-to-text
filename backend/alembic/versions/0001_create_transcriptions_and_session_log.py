"""create transcriptions and session_log

Revision ID: 0001
Revises:
Create Date: 2026-11-25
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "languages",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("engine", sa.String(40), nullable=True),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="complete"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "length(btrim(text, E' \\t\\r\\n')) > 0", name="ck_transcriptions_text_not_blank"
        ),
        sa.CheckConstraint("source IN ('spoken', 'manual')", name="ck_transcriptions_source"),
        sa.CheckConstraint(
            "status IN ('complete', 'interrupted')", name="ck_transcriptions_status"
        ),
    )
    op.create_index(
        "ix_transcriptions_created_id",
        "transcriptions",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_transcriptions_languages", "transcriptions", ["languages"], postgresql_using="gin"
    )

    op.create_table(
        "session_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("visitor_id", sa.String(36), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_session_log_visitor_started",
        "session_log",
        ["visitor_id", sa.text("started_at DESC")],
    )
    op.create_index(
        "ix_session_log_ip_started", "session_log", ["ip_hash", sa.text("started_at DESC")]
    )


def downgrade() -> None:
    op.drop_table("session_log")
    op.drop_table("transcriptions")
