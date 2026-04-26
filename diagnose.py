from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import load_config


async def main() -> None:
    config = load_config()
    session = AiohttpSession(proxy=config.telegram_proxy_url or None, timeout=10)
    bot = Bot(
        token=config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        me = await bot.get_me(request_timeout=10)
        await bot.delete_webhook(drop_pending_updates=False, request_timeout=10)
        webhook = await bot.get_webhook_info()

        print(f"Bot from token: @{me.username} id={me.id}")
        print(f"Webhook url: {webhook.url or '<empty>'}")
        print(f"Pending updates: {webhook.pending_update_count}")

        print("Waiting for updates for 30 seconds. Send any message to the bot now...")
        updates = await bot.get_updates(timeout=30, allowed_updates=["message", "callback_query"])

        if not updates:
            print("No updates received.")
            return

        for update in updates[-5:]:
            print(f"Update id: {update.update_id}")
            if update.message:
                user = update.message.from_user
                print(f"Message from @{user.username if user else None}: {update.message.text!r}")
                await bot.send_message(update.message.chat.id, "Диагностика: я вижу это сообщение.")
            if update.callback_query:
                print(f"Callback data: {update.callback_query.data!r}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
