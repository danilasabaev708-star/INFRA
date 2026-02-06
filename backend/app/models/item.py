from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    lang: Mapped[str] = mapped_column(String(8), default="ru")
    is_job: Mapped[bool] = mapped_column(Boolean, default=False)
    impact: Mapped[str | None] = mapped_column(String(16), nullable=True)
    trust_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trust_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentinel_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ItemTopic(Base):
    __tablename__ = "item_topics"

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    assigned_by: Mapped[str] = mapped_column(String(16), default="auto")


class ItemFeedback(Base):
    __tablename__ = "item_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    vote: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    pin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
