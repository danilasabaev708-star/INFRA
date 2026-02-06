from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_delivery_messages"
down_revision = "0002_items_and_topics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "item_id", name="ux_delivery_user_item"),
    )
    op.create_index("ix_delivery_messages_user_id", "delivery_messages", ["user_id"], unique=False)
    op.create_index("ix_delivery_messages_item_id", "delivery_messages", ["item_id"], unique=False)
    op.create_index("ix_delivery_messages_chat_id", "delivery_messages", ["chat_id"], unique=False)
    op.create_index("ix_delivery_messages_message_id", "delivery_messages", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_delivery_messages_message_id", table_name="delivery_messages")
    op.drop_index("ix_delivery_messages_chat_id", table_name="delivery_messages")
    op.drop_index("ix_delivery_messages_item_id", table_name="delivery_messages")
    op.drop_index("ix_delivery_messages_user_id", table_name="delivery_messages")
    op.drop_table("delivery_messages")
