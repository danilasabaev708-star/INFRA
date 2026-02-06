from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeliveryMessage(Base):
    __tablename__ = "delivery_messages"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="ux_delivery_user_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    message_id: Mapped[int] = mapped_column(Integer, index=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
