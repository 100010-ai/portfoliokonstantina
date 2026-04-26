from __future__ import annotations

import asyncio
import email
import html
import imaplib
import logging
import re
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from html.parser import HTMLParser

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import Config
from database import is_email_processed, mark_email_processed


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KworkEmailNotification:
    message_id: str
    event_type: str
    sender: str
    subject: str
    date: str
    preview: str
    matched_keyword: str


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self.parts)


def is_configured(config: Config) -> bool:
    return bool(
        config.admin_id is not None
        and config.kwork_email_imap_host
        and config.kwork_email_login
        and config.kwork_email_password
    )


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""

    parts = []
    for fragment, encoding in decode_header(value):
        if isinstance(fragment, bytes):
            parts.append(fragment.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(fragment)
    return "".join(parts).strip()


def _decode_payload(message: Message) -> str:
    payload = message.get_payload(decode=True)
    if not payload:
        return ""
    charset = message.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _html_to_text(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(value)
    return parser.get_text()


def _extract_body(message: Message) -> str:
    if message.is_multipart():
        html_body = ""
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            if content_type == "text/plain":
                return _decode_payload(part)
            if content_type == "text/html" and not html_body:
                html_body = _decode_payload(part)
        return _html_to_text(html_body)

    body = _decode_payload(message)
    if message.get_content_type() == "text/html":
        return _html_to_text(body)
    return body


def _compact_text(value: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}..."


def _find_keyword(text: str, keywords: tuple[str, ...]) -> str:
    lower_text = text.lower()
    for keyword in keywords:
        if keyword and keyword in lower_text:
            return keyword
    return ""


def _detect_kwork_event(message: Message, subject: str, body: str, config: Config) -> tuple[str, str]:
    sender = _decode_mime_header(message.get("From"))
    header_text = f"{sender}\n{subject}"
    full_text = f"{header_text}\n{body}"

    checks = (
        ("order", header_text, config.kwork_email_order_keywords),
        ("review", header_text, config.kwork_email_review_keywords),
        ("message", header_text, config.kwork_email_client_keywords),
        ("promo", header_text, config.kwork_email_promo_keywords),
        ("order", full_text, config.kwork_email_order_keywords),
        ("review", full_text, config.kwork_email_review_keywords),
        ("message", full_text, config.kwork_email_client_keywords),
        ("promo", full_text, config.kwork_email_promo_keywords),
    )
    for event_type, text, keywords in checks:
        keyword = _find_keyword(text, keywords)
        if keyword:
            return event_type, keyword
    return "unknown", ""


def _fetch_unseen_notifications(config: Config) -> list[KworkEmailNotification]:
    notifications: list[KworkEmailNotification] = []

    with imaplib.IMAP4_SSL(config.kwork_email_imap_host, config.kwork_email_imap_port) as client:
        client.login(config.kwork_email_login, config.kwork_email_password)
        client.select(config.kwork_email_folder)

        from_filter = config.kwork_email_from_filter or "kwork"
        status, data = client.search(None, "UNSEEN", "FROM", f'"{from_filter}"')
        if status != "OK" or not data or not data[0]:
            return notifications

        for message_id in data[0].split():
            fetch_status, fetch_data = client.fetch(message_id, "(RFC822)")
            if fetch_status != "OK" or not fetch_data:
                continue

            for item in fetch_data:
                if not isinstance(item, tuple):
                    continue

                message: Message = email.message_from_bytes(item[1])
                subject = _decode_mime_header(message.get("Subject"))
                body = _extract_body(message)
                event_type, keyword = _detect_kwork_event(message, subject, body, config)
                decoded_id = message_id.decode(errors="replace")
                stable_id = _decode_mime_header(message.get("Message-ID")) or decoded_id

                if event_type in {"promo", "unknown"}:
                    logger.info(
                        "Kwork email skipped. id=%s subject=%r type=%s marker=%r",
                        stable_id,
                        subject,
                        event_type,
                        keyword,
                    )
                    continue

                notifications.append(
                    KworkEmailNotification(
                        message_id=stable_id,
                        event_type=event_type,
                        sender=_decode_mime_header(message.get("From")),
                        subject=subject,
                        date=_decode_mime_header(message.get("Date")),
                        preview=_compact_text(body),
                        matched_keyword=keyword,
                    )
                )

    return notifications


def _format_notification(notification: KworkEmailNotification, config: Config) -> str:
    kwork_link = config.kwork_profile_url or "https://kwork.ru"
    title_by_type = {
        "order": "🛒 Новый заказ на Kwork",
        "review": "⭐ Новый отзыв на Kwork",
        "message": "💬 Сообщение клиента на Kwork",
    }
    action_by_type = {
        "order": "Проверьте страницу заказов на Kwork и начинайте работу только после появления заказа.",
        "review": "Проверьте отзыв на Kwork. После проверки он может попасть в публичный раздел отзывов.",
        "message": "Ответьте клиенту внутри Kwork.",
    }
    return (
        f"<b>{title_by_type.get(notification.event_type, 'Уведомление Kwork')}</b>\n\n"
        f"<b>Тема:</b> {html.escape(notification.subject or 'без темы')}\n"
        f"<b>Отправитель:</b> {html.escape(notification.sender or 'не указан')}\n"
        f"<b>Дата:</b> {html.escape(notification.date or 'не указана')}\n"
        f"<b>Маркер:</b> {html.escape(notification.matched_keyword or 'клиентское письмо')}\n\n"
        f"<b>Фрагмент:</b>\n{html.escape(notification.preview or 'текст письма не найден')}\n\n"
        f'<a href="{html.escape(kwork_link)}">Открыть Kwork</a>\n\n'
        f"<i>{action_by_type.get(notification.event_type, 'Проверьте Kwork.')} "
        "Рекламные рассылки, скидки и дайджесты бот пропускает.</i>"
    )


def _notification_keyboard(config: Config) -> InlineKeyboardMarkup:
    url = config.kwork_profile_url or config.kwork_bot_service_url or "https://kwork.ru"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Открыть Kwork", url=url)],
        ]
    )


async def start_kwork_email_notifier(bot: Bot, config: Config) -> None:
    if not is_configured(config):
        logger.info("Kwork email notifier is disabled. Fill IMAP settings in .env to enable it.")
        return

    admin_id = config.admin_id
    if admin_id is None:
        logger.warning("Kwork email notifier stopped: ADMIN_ID is not configured.")
        return

    logger.info("Kwork email notifier started for admin_id=%s", admin_id)

    while True:
        try:
            notifications = await asyncio.to_thread(_fetch_unseen_notifications, config)
            for notification in notifications:
                if await asyncio.to_thread(is_email_processed, config, notification.message_id):
                    logger.info("Kwork email already processed. id=%s", notification.message_id)
                    continue

                await bot.send_message(
                    admin_id,
                    _format_notification(notification, config),
                    reply_markup=_notification_keyboard(config),
                )
                await asyncio.to_thread(
                    mark_email_processed,
                    config,
                    notification.message_id,
                    notification.event_type,
                    notification.subject,
                )
                logger.info("Kwork email notification sent for email id=%s to admin_id=%s", notification.message_id, admin_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Could not check Kwork email notifications.")

        await asyncio.sleep(config.kwork_email_check_interval)
