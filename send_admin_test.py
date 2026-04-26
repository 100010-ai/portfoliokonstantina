from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import load_config


async def main() -> None:
    config = load_config()
    if config.admin_id is None:
        print("ADMIN_ID is empty or invalid in .env")
        return

    session = AiohttpSession(proxy=config.telegram_proxy_url or None, timeout=10)
    bot = Bot(
        token=config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        me = await bot.get_me(request_timeout=10)
        print(f"Bot from token: @{me.username} id={me.id}")
        await bot.send_message(config.admin_id, "Тест: бот может отправлять сообщения через Bot API.")
        print("Test message sent to ADMIN_ID.")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
