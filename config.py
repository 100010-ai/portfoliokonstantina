from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, default).strip()
    return tuple(item.strip().lower() for item in raw_value.split(",") if item.strip())


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int | None
    kwork_profile_url: str
    kwork_bot_service_url: str
    kwork_reviews_url: str
    reviews_sync_interval: int
    telegram_proxy_url: str
    database_url: str
    sqlite_path: str
    reviews_json: str
    kwork_email_imap_host: str
    kwork_email_imap_port: int
    kwork_email_login: str
    kwork_email_password: str
    kwork_email_folder: str
    kwork_email_from_filter: str
    kwork_email_client_keywords: tuple[str, ...]
    kwork_email_order_keywords: tuple[str, ...]
    kwork_email_review_keywords: tuple[str, ...]
    kwork_email_promo_keywords: tuple[str, ...]
    kwork_email_check_interval: int


def _parse_int(value: str, default: int, name: str) -> int:
    try:
        return int(value)
    except ValueError:
        logger.warning("%s must be an integer. Default %s will be used.", name, default)
        return default


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_raw = os.getenv("ADMIN_ID", "").strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env or Railway Variables.")

    admin_id: int | None = None
    if admin_id_raw:
        try:
            admin_id = int(admin_id_raw)
        except ValueError:
            logger.warning("ADMIN_ID must be an integer. Admin notifications are disabled.")
    else:
        logger.warning("ADMIN_ID is not set. Admin notifications are disabled.")

    kwork_email_imap_port = _parse_int(os.getenv("KWORK_EMAIL_IMAP_PORT", "993").strip(), 993, "KWORK_EMAIL_IMAP_PORT")
    kwork_email_check_interval = _parse_int(
        os.getenv("KWORK_EMAIL_CHECK_INTERVAL", "60").strip(),
        60,
        "KWORK_EMAIL_CHECK_INTERVAL",
    )
    if kwork_email_check_interval < 30:
        logger.warning("KWORK_EMAIL_CHECK_INTERVAL is too low. Minimum 30 seconds will be used.")
        kwork_email_check_interval = 30

    reviews_sync_interval = _parse_int(os.getenv("REVIEWS_SYNC_INTERVAL", "21600").strip(), 21600, "REVIEWS_SYNC_INTERVAL")
    if reviews_sync_interval < 600:
        logger.warning("REVIEWS_SYNC_INTERVAL is too low. Minimum 600 seconds will be used.")
        reviews_sync_interval = 600

    kwork_profile_url = os.getenv("KWORK_PROFILE_URL", "").strip()
    kwork_bot_service_url = os.getenv("KWORK_BOT_SERVICE_URL", "").strip()
    if not kwork_profile_url:
        logger.warning("KWORK_PROFILE_URL is not set. Kwork profile button will use kwork.ru.")
    if not kwork_bot_service_url:
        logger.warning("KWORK_BOT_SERVICE_URL is not set. Kwork order button will use kwork.ru.")

    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        kwork_profile_url=kwork_profile_url,
        kwork_bot_service_url=kwork_bot_service_url,
        kwork_reviews_url=os.getenv("KWORK_REVIEWS_URL", "").strip(),
        reviews_sync_interval=reviews_sync_interval,
        telegram_proxy_url=os.getenv("TELEGRAM_PROXY_URL", "").strip(),
        database_url=os.getenv("DATABASE_URL", "").strip(),
        sqlite_path=os.getenv("SQLITE_PATH", "bot_data.sqlite3").strip(),
        reviews_json=os.getenv("REVIEWS_JSON", "").strip(),
        kwork_email_imap_host=os.getenv("KWORK_EMAIL_IMAP_HOST", "").strip(),
        kwork_email_imap_port=kwork_email_imap_port,
        kwork_email_login=os.getenv("KWORK_EMAIL_LOGIN", "").strip(),
        kwork_email_password=os.getenv("KWORK_EMAIL_PASSWORD", "").strip(),
        kwork_email_folder=os.getenv("KWORK_EMAIL_FOLDER", "INBOX").strip(),
        kwork_email_from_filter=os.getenv("KWORK_EMAIL_FROM_FILTER", "kwork").strip(),
        kwork_email_client_keywords=_csv_env(
            "KWORK_EMAIL_CLIENT_KEYWORDS",
            "новое сообщение,сообщение от,вам написал,покупатель,клиент,личное сообщение,"
            "new message,buyer,customer",
        ),
        kwork_email_order_keywords=_csv_env(
            "KWORK_EMAIL_ORDER_KEYWORDS",
            "новый заказ,заказ создан,заказ оплачен,начинайте работу,поступил заказ,оформил заказ,"
            "new order,order created,order paid",
        ),
        kwork_email_review_keywords=_csv_env(
            "KWORK_EMAIL_REVIEW_KEYWORDS",
            "новый отзыв,оставил отзыв,отзыв по заказу,оценил заказ,review,feedback",
        ),
        kwork_email_promo_keywords=_csv_env(
            "KWORK_EMAIL_PROMO_KEYWORDS",
            "скидка,скидки,акция,распродажа,промокод,бонус,дайджест,подборка,новости kwork,"
            "реклама,рекомендации,вебинар,обучение,статья,блог,sale,discount,promo,newsletter,digest",
        ),
        kwork_email_check_interval=kwork_email_check_interval,
    )
