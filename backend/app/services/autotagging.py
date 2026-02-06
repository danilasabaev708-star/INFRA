from __future__ import annotations

import json
import logging
import re
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item, ItemTopic
from app.models.topic import Topic
from app.services.llm_provider import LlmProviderError, get_llm_provider

logger = logging.getLogger(__name__)
_MAX_TOPICS = 3
_MAX_LLM_TEXT_LENGTH = 1200
_LLM_TOPIC_KEYS = ("topics", "topic_ids")
_MAX_LLM_TOPICS = 50


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _score_topic(text: str, keywords: Iterable[str] | None) -> float:
    if not keywords:
        return 0.0
    score = 0.0
    for keyword in keywords:
        cleaned = keyword.strip().lower()
        if not cleaned:
            continue
        pattern = re.escape(cleaned)
        matches = re.findall(pattern, text)
        score += len(matches)
    return score


def _is_clear_leader(scored: list[tuple[Topic, float]]) -> bool:
    if not scored:
        return False
    if len(scored) == 1:
        return True
    top_score = scored[0][1]
    second_score = scored[1][1]
    return top_score >= second_score + 1


async def _pick_topics_with_llm(
    topics: list[Topic], title: str, text: str
) -> list[int]:
    provider = get_llm_provider()
    if not provider:
        return []
    summary = f"{title}\n\n{text[:_MAX_LLM_TEXT_LENGTH]}"
    limited_topics = topics[:_MAX_LLM_TOPICS]
    topic_catalog = [
        {"id": topic.id, "name": topic.name, "description": topic.description or ""}
        for topic in limited_topics
    ]
    prompt_ru = (
        "Выбери 1-3 темы, которые лучше всего подходят к материалу. "
        "Ответь JSON-массивом идентификаторов тем, например: [1,2]."
    )
    try:
        response = await provider.chat(
            [
                {"role": "system", "content": "Ты помощник, который выбирает темы."},
                {
                    "role": "user",
                    "content": f"{prompt_ru}\n\nТемы: {json.dumps(topic_catalog)}\n\nТекст: {summary}",
                },
            ]
        )
    except LlmProviderError:
        logger.exception("LLM error while picking topics")
        return []
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        for key in _LLM_TOPIC_KEYS:
            if key in parsed:
                parsed = parsed.get(key) or []
                break
        else:
            parsed = []
    if not isinstance(parsed, list):
        return []
    name_to_id = {topic.name.lower(): topic.id for topic in limited_topics}
    valid_ids = {topic.id for topic in limited_topics}
    selected: list[int] = []
    for value in parsed:
        topic_id: int | None = None
        if isinstance(value, int):
            topic_id = value if value in valid_ids else None
        elif isinstance(value, str):
            topic_id = name_to_id.get(value.lower())
        if topic_id and topic_id not in selected:
            selected.append(topic_id)
        if len(selected) >= _MAX_TOPICS:
            break
    return selected


async def assign_topics(session: AsyncSession, item: Item) -> list[ItemTopic]:
    if item.id is None:
        await session.flush()

    result = await session.execute(
        select(Topic).order_by(Topic.order.is_(None), Topic.order, Topic.id)
    )
    topics = result.scalars().all()
    if not topics:
        return []

    existing = (
        await session.execute(select(ItemTopic).where(ItemTopic.item_id == item.id))
    ).scalars().all()
    locked_ids = {row.topic_id for row in existing if row.locked}

    scored: list[tuple[Topic, float]] = []
    text = _normalize_text(f"{item.title} {item.text}")
    for topic in topics:
        score = _score_topic(text, topic.keywords)
        if score > 0:
            scored.append((topic, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)

    selected_topic_ids: list[int] = []
    if scored and _is_clear_leader(scored):
        selected_topic_ids = [topic.id for topic, _ in scored[:_MAX_TOPICS]]
    else:
        selected_topic_ids = await _pick_topics_with_llm(
            topics, item.title, item.text or ""
        )

    if not selected_topic_ids and scored:
        selected_topic_ids = [topic.id for topic, _ in scored[:_MAX_TOPICS]]

    if not selected_topic_ids:
        return []

    selected_scores = {topic.id: score for topic, score in scored}

    # Overwrite only unlocked auto-assignments while preserving locked topics.
    await session.execute(
        delete(ItemTopic).where(
            ItemTopic.item_id == item.id,
            ItemTopic.locked.is_(False),
        )
    )

    created: list[ItemTopic] = []
    for topic_id in selected_topic_ids:
        if topic_id in locked_ids:
            continue
        created_item_topic = ItemTopic(
            item_id=item.id,
            topic_id=topic_id,
            locked=False,
            score=selected_scores.get(topic_id),
            assigned_by="auto",
        )
        session.add(created_item_topic)
        created.append(created_item_topic)

    await session.flush()
    return created
