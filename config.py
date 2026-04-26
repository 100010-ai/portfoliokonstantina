from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int | None
    kwork_profile_url: str
    kwork_bot_service_url: str
    telegram_proxy_url: str


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_raw = os.getenv("ADMIN_ID", "").strip()
    kwork_profile_url = os.getenv("KWORK_PROFILE_URL", "").strip()
    kwork_bot_service_url = os.getenv("KWORK_BOT_SERVICE_URL", "").strip()
    telegram_proxy_url = os.getenv("TELEGRAM_PROXY_URL", "").strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env before starting the bot.")

    admin_id: int | None = None
    if admin_id_raw:
        try:
            admin_id = int(admin_id_raw)
        except ValueError:
            logger.warning("ADMIN_ID must be an integer. Admin notifications are disabled.")
    else:
        logger.warning("ADMIN_ID is not set. Admin notifications are disabled.")

    if not kwork_profile_url:
        logger.warning("KWORK_PROFILE_URL is not set. Kwork profile button will use kwork.ru.")

    if not kwork_bot_service_url:
        logger.warning("KWORK_BOT_SERVICE_URL is not set. Kwork order button will use kwork.ru.")

    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        kwork_profile_url=kwork_profile_url,
        kwork_bot_service_url=kwork_bot_service_url,
        telegram_proxy_url=telegram_proxy_url,
    )
