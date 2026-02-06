from __future__ import annotations

import logging
import re

from app.models.item import Item
from app.services.llm_provider import LlmProviderError, get_llm_provider

logger = logging.getLogger(__name__)
_BULLET_MARKERS = ("•", "-", "*", "—")
_SENTENCE_SPLIT = re.compile(r"[.!?]+")


def clarification_question() -> str:
    return "Что именно хотите понять глубже по этой новости?"


def _format_bullets(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullets: list[str] = []
    for line in lines:
        if line[0] in _BULLET_MARKERS:
            bullets.append(line.lstrip("".join(_BULLET_MARKERS)).strip())
    if not bullets:
        parts = [part.strip() for part in re.split(r"[•\n]", text) if part.strip()]
        if len(parts) > 1:
            bullets = parts
    if not bullets:
        parts = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
        bullets = parts
    bullets = [bullet for bullet in bullets if bullet]
    if len(bullets) < 2:
        bullets.append("Подробности уточняются.")
    bullets = bullets[:6]
    return "\n".join(f"• {bullet}" for bullet in bullets)


def _ensure_report_length(text: str, filler: str) -> str:
    cleaned = text.strip()
    if len(cleaned) > 2500:
        return cleaned[:2500].rstrip()
    filler_text = filler.strip()
    while len(cleaned) < 1500 and filler_text:
        need = 1500 - len(cleaned) - 2
        cleaned = f"{cleaned}\n\n{filler_text[:need]}".strip()
        if len(filler_text) <= need:
            break
    if len(cleaned) < 1500:
        cleaned = cleaned + "\n\n" + ("Дополнительные детали. " * 30)
        cleaned = cleaned[:1500].rstrip()
    return cleaned


async def generate_bulleted_answer(prompt: str) -> str:
    provider = get_llm_provider()
    if not provider:
        return _format_bullets("Ответ будет доступен позже.")
    system = "Ты аналитик. Отвечай на русском, только списком 2-6 буллетов."
    user_prompt = f"Вопрос: {prompt}\nОтветь 2-6 буллетами, без лишнего текста."
    try:
        response = await provider.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]
        )
    except LlmProviderError:
        logger.exception("LLM error while generating QA answer")
        return _format_bullets("Ответ будет доступен позже.")
    return _format_bullets(response)


async def generate_deepdive_report(item: Item, clarification: str) -> str:
    provider = get_llm_provider()
    if not provider:
        fallback = f"Материал: {item.title}\n\n{item.text}"
        return _ensure_report_length(fallback, item.text or item.title)
    prompt = (
        "Составь структурированный отчёт на русском (1500–2500 символов). "
        "Структура: 1) Резюме 2) Ключевые факты 3) Риски и последствия "
        "4) Что наблюдать дальше. Используй связный текст и подзаголовки."
    )
    item_text = item.text or ""
    user_content = (
        f"{prompt}\n\nНовость: {item.title}\n{item_text}\n\n"
        f"Уточнение пользователя: {clarification}"
    )
    try:
        response = await provider.chat(
            [{"role": "system", "content": "Ты опытный аналитик."}, {"role": "user", "content": user_content}]
        )
    except LlmProviderError:
        logger.exception("LLM error while generating deepdive")
        response = f"Материал: {item.title}\n\n{item_text}"
    return _ensure_report_length(response, item_text or item.title)
