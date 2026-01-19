"""Add conversation sessions table

Revision ID: 003_conversation_sessions
Revises: 002_seed_data
Create Date: 2025-02-19 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_conversation_sessions"
down_revision: Union[str, None] = "002_seed_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("customer_name", sa.String(100), nullable=True),
        sa.Column("current_intent", sa.String(50), nullable=True),
        sa.Column("previous_intents", sa.JSON(), nullable=True),
        sa.Column("entities", sa.JSON(), nullable=True),
        sa.Column("user_preferences", sa.JSON(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("reservation_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_conversation_sessions_session_id", "conversation_sessions", ["session_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_conversation_sessions_session_id", table_name="conversation_sessions")
    op.drop_table("conversation_sessions")
