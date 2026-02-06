from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import get_settings
from app.models.item import Item

settings = get_settings()
_bot: Bot | None = None

_TRUST_STATUS_LABELS = {
    "confirmed": "ПОДТВЕРЖДЕНО",
    "mixed": "СМЕШАННО",
    "unclear": "НЕЯСНО",
    "hype": "ХАЙП",
}
_IMPACT_LABELS = {
    "low": "НИЗКОЕ",
    "medium": "СРЕДНЕЕ",
    "high": "ВЫСОКОЕ",
}


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        if not settings.bot_token:
            raise RuntimeError("BOT_TOKEN не задан")
        _bot = Bot(token=settings.bot_token)
    return _bot


def _safe_label(mapping: dict[str, str], value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    return mapping.get(value, fallback)


def format_smart_card(item: Item) -> str:
    trust_score = item.trust_score if item.trust_score is not None else 0
    trust_status = _safe_label(_TRUST_STATUS_LABELS, item.trust_status, "НЕЯСНО")
    impact = _safe_label(_IMPACT_LABELS, item.impact, "СРЕДНЕЕ")
    lines = [item.title.strip()]
    if item.url:
        lines.append(item.url)
    if item.text:
        snippet = item.text.strip()
        if len(snippet) > 420:
            snippet = snippet[:420].rstrip() + "…"
        lines.append(snippet)
    lines.append(f"Доверие {trust_score} | Статус {trust_status} | Влияние {impact}")
    return "\n\n".join([line for line in lines if line])


def build_deepdive_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 DeepDive", callback_data=f"deepdive:{item_id}")]
        ]
    )
