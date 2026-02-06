from __future__ import annotations

import asyncio

import httpx

from app.core.config import get_settings

settings = get_settings()


async def send_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})


async def handle_update(update: dict) -> None:
    message = update.get("message") or update.get("channel_post")
    if not message:
        return
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    if text.startswith("/start"):
        await send_message(chat_id, "Добро пожаловать в INFRA! Откройте мини‑приложение для работы.")
    elif text.startswith("/help"):
        await send_message(chat_id, "Доступные команды: /start, /help")


async def run_bot() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN не задан")
    offset = None
    url = f"https://api.telegram.org/bot{settings.bot_token}/getUpdates"
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {"timeout": 25}
            if offset:
                params["offset"] = offset
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                await handle_update(update)
            await asyncio.sleep(1)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
