from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database import init_database
from handlers import router
from kwork_email_notifier import is_configured as is_kwork_notifier_configured
from kwork_email_notifier import start_kwork_email_notifier
from review_sync import is_configured as is_reviews_sync_configured
from review_sync import start_reviews_sync


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    setup_logging()
    logging.info("Loading config")
    config = load_config()
    logging.info("Config loaded. Proxy is %s", "enabled" if config.telegram_proxy_url else "disabled")
    await asyncio.to_thread(init_database, config)

    session = AiohttpSession(proxy=config.telegram_proxy_url or None, timeout=10)
    bot = Bot(
        token=config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    notifier_task: asyncio.Task | None = None
    reviews_sync_task: asyncio.Task | None = None
    try:
        dispatcher = Dispatcher(storage=MemoryStorage(), config=config)
        dispatcher.include_router(router)

        logging.info("Checking bot token via getMe")
        me = await bot.get_me(request_timeout=10)
        logging.info("Bot started as @%s (id=%s)", me.username, me.id)

        logging.info("Deleting webhook before polling")
        await bot.delete_webhook(drop_pending_updates=False, request_timeout=10)

        if is_kwork_notifier_configured(config):
            notifier_task = asyncio.create_task(start_kwork_email_notifier(bot, config))
        else:
            logging.info("Kwork email notifier is disabled")

        if is_reviews_sync_configured(config):
            reviews_sync_task = asyncio.create_task(start_reviews_sync(config))
        else:
            logging.info("Kwork reviews sync is disabled")

        logging.info("Polling is starting now. Send /start to @%s", me.username)
        await dispatcher.start_polling(bot)
    except TelegramNetworkError:
        logging.exception(
            "Cannot connect to Telegram Bot API. Check internet/VPN/proxy or set TELEGRAM_PROXY_URL in .env."
        )
        raise
    finally:
        if notifier_task:
            notifier_task.cancel()
            try:
                await notifier_task
            except asyncio.CancelledError:
                logging.info("Kwork email notifier stopped")
        if reviews_sync_task:
            reviews_sync_task.cancel()
            try:
                await reviews_sync_task
            except asyncio.CancelledError:
                logging.info("Kwork reviews sync stopped")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
