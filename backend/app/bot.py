from __future__ import annotations

import asyncio
from typing import Iterable

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types.message_reaction_updated import MessageReactionUpdated
from aiogram.types.reaction_type_emoji import ReactionTypeEmoji
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.delivery import DeliveryMessage
from app.models.item import Item, ItemFeedback
from app.models.user import User
from app.services.ai_assistant import clarification_question, generate_bulleted_answer, generate_deepdive_report
from app.services.ai_usage import RateLimitError, check_and_record_usage

settings = get_settings()
router = Router()
_pending_ask: set[int] = set()
_pending_deepdive: dict[int, int] = {}
_pending_pin_note: dict[int, int] = {}


def _tma_url() -> str | None:
    raw = settings.tma_origins or settings.tma_origin
    if not raw:
        return None
    return raw.split(",")[0].strip() or None


def _open_tma_keyboard() -> InlineKeyboardMarkup | None:
    url = _tma_url()
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть INFRA", url=url)]]
    )


async def _get_or_create_user(session, tg_id: int, username: str | None) -> User:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalars().first()
    if not user:
        user = User(tg_id=tg_id, username=username)
        session.add(user)
        await session.flush()
    return user


async def _update_feedback(
    session,
    user_id: int,
    item_id: int,
    vote: str | None = None,
    pinned: bool | None = None,
    pin_note: str | None = None,
) -> ItemFeedback:
    result = await session.execute(
        select(ItemFeedback).where(
            ItemFeedback.user_id == user_id, ItemFeedback.item_id == item_id
        )
    )
    feedback = result.scalars().first()
    if not feedback:
        feedback = ItemFeedback(user_id=user_id, item_id=item_id, pinned=False)
        session.add(feedback)
    if vote is not None:
        feedback.vote = vote
    if pinned is not None:
        feedback.pinned = pinned
        if not pinned:
            feedback.pin_note = None
    if pin_note is not None:
        feedback.pin_note = pin_note
    await session.flush()
    return feedback


def _extract_emojis(reactions: Iterable) -> set[str]:
    emojis: set[str] = set()
    for reaction in reactions:
        if isinstance(reaction, ReactionTypeEmoji):
            emojis.add(reaction.emoji)
    return emojis


@router.message(CommandStart())
async def start(message: Message) -> None:
    text = "Добро пожаловать в INFRA! Откройте мини-приложение для настройки тем."
    keyboard = _open_tma_keyboard()
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("ask"))
async def ask_command(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        _pending_ask.add(message.from_user.id)
        await message.answer("Напишите вопрос, и я отвечу списком.")
        return
    await _handle_ask(message, parts[1])


@router.callback_query(F.data.startswith("deepdive:"))
async def deepdive_callback(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    try:
        item_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        await query.answer("Неверный запрос.", show_alert=True)
        return
    _pending_deepdive[user_id] = item_id
    await query.message.answer(clarification_question())
    await query.answer()


@router.message()
async def handle_free_text(message: Message) -> None:
    if not message.text or not message.from_user:
        return
    user_id = message.from_user.id
    if user_id in _pending_pin_note:
        item_id = _pending_pin_note.pop(user_id)
        note = message.text.strip()
        if note.lower() in {"/skip", "skip", "-"}:
            note = ""
        async with SessionLocal() as session:
            await _update_feedback(
                session, user_id=user_id, item_id=item_id, pinned=True, pin_note=note or None
            )
            await session.commit()
        await message.answer("Заметка сохранена.")
        return
    if user_id in _pending_deepdive:
        item_id = _pending_deepdive.pop(user_id)
        await _handle_deepdive(message, item_id, message.text)
        return
    if user_id in _pending_ask:
        _pending_ask.discard(user_id)
        await _handle_ask(message, message.text)


@router.message_reaction()
async def handle_reaction(update: MessageReactionUpdated, bot: Bot) -> None:
    if update.new_reaction is None or update.old_reaction is None:
        return
    new_emojis = _extract_emojis(update.new_reaction)
    old_emojis = _extract_emojis(update.old_reaction)
    chat_id = update.chat.id
    message_id = update.message_id
    user_id = update.user.id if update.user else None
    if not user_id:
        return
    async with SessionLocal() as session:
        result = await session.execute(
            select(DeliveryMessage).where(
                DeliveryMessage.chat_id == chat_id, DeliveryMessage.message_id == message_id
            )
        )
        delivery = result.scalars().first()
        if not delivery:
            return
        item_id = delivery.item_id
        vote = None
        if "👍" in new_emojis:
            vote = "like"
        elif "👎" in new_emojis:
            vote = "dislike"
        await _update_feedback(session, user_id, item_id, vote=vote)
        if "📌" in new_emojis and "📌" not in old_emojis:
            await _update_feedback(session, user_id, item_id, pinned=True)
            _pending_pin_note[user_id] = item_id
            await session.commit()
            await bot.send_message(
                chat_id=chat_id,
                text="Хотите добавить заметку? Ответьте сообщением или /skip.",
            )
            return
        if "📌" in old_emojis and "📌" not in new_emojis:
            await _update_feedback(session, user_id, item_id, pinned=False)
        await session.commit()


async def _handle_ask(message: Message, prompt: str) -> None:
    async with SessionLocal() as session:
        user = await _get_or_create_user(session, message.from_user.id, message.from_user.username)
        try:
            await check_and_record_usage(session, user, "qa")
            await session.commit()
        except RateLimitError as exc:
            await session.rollback()
            await message.answer(exc.message)
            return
    answer = await generate_bulleted_answer(prompt)
    await message.answer(answer)


async def _handle_deepdive(message: Message, item_id: int, clarification: str) -> None:
    async with SessionLocal() as session:
        user = await _get_or_create_user(session, message.from_user.id, message.from_user.username)
        item = await session.get(Item, item_id)
        if not item:
            await message.answer("Материал не найден.")
            return
        try:
            await check_and_record_usage(session, user, "deepdive")
            await session.commit()
        except RateLimitError as exc:
            await session.rollback()
            await message.answer(exc.message)
            return
    report = await generate_deepdive_report(item, clarification)
    await message.answer(report)


async def _ensure_delivery_context() -> None:
    async with SessionLocal() as session:
        await session.execute(select(User.id).limit(1))


async def run_bot() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN не задан")
    await _ensure_delivery_context()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
