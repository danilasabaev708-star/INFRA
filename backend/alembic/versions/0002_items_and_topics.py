from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_items_and_topics"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("keywords", sa.JSON(), nullable=True))
    op.add_column("topics", sa.Column("order", sa.Integer(), nullable=True))
    op.add_column("sources", sa.Column("state", sa.JSON(), nullable=True))

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=False),
        sa.Column("is_job", sa.Boolean(), nullable=False),
        sa.Column("impact", sa.String(length=16), nullable=True),
        sa.Column("trust_score", sa.Integer(), nullable=True),
        sa.Column("trust_status", sa.String(length=16), nullable=True),
        sa.Column("sentinel_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("content_hash"),
    )
    op.create_index("ix_items_content_hash", "items", ["content_hash"], unique=True)
    op.create_index("ix_items_source_id", "items", ["source_id"], unique=False)

    op.create_table(
        "item_topics",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), primary_key=True),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("assigned_by", sa.String(length=16), nullable=False),
    )

    op.create_table(
        "item_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("vote", sa.String(length=16), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("pin_note", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_item_feedback_item_id", "item_feedback", ["item_id"], unique=False)
    op.create_index("ix_item_feedback_user_id", "item_feedback", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_item_feedback_user_id", table_name="item_feedback")
    op.drop_index("ix_item_feedback_item_id", table_name="item_feedback")
    op.drop_table("item_feedback")
    op.drop_table("item_topics")
    op.drop_index("ix_items_source_id", table_name="items")
    op.drop_index("ix_items_content_hash", table_name="items")
    op.drop_table("items")
    op.drop_column("sources", "state")
    op.drop_column("topics", "order")
    op.drop_column("topics", "keywords")
