from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.rate_limits import DeliveryMode, PlanTier
from app.db.base import Base


user_topics = Table(
    "user_topics",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("topic_id", ForeignKey("topics.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_tier: Mapped[str] = mapped_column(
        Enum(PlanTier.FREE, PlanTier.PRO, PlanTier.CORP, name="plan_tier"),
        default=PlanTier.FREE,
    )
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    jobs_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_mode: Mapped[str] = mapped_column(
        Enum(DeliveryMode.DIGEST, DeliveryMode.INSTANT, name="delivery_mode"),
        default=DeliveryMode.DIGEST,
    )
    batch_interval_hours: Mapped[int] = mapped_column(Integer, default=3)
    quiet_hours_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quiet_hours_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    only_important: Mapped[bool] = mapped_column(Boolean, default=False)
    last_ai_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    topics: Mapped[list["Topic"]] = relationship(
        "Topic", secondary=user_topics, back_populates="users"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
