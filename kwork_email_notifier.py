from __future__ import annotations

import asyncio
import email
import html
import imaplib
import logging
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message

from aiogram import Bot

from config import Config


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KworkEmailNotification:
    message_id: str
    sender: str
    subject: str
    date: str


def is_configured(config: Config) -> bool:
    return bool(
        config.admin_id
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
                notifications.append(
                    KworkEmailNotification(
                        message_id=message_id.decode(errors="replace"),
                        sender=_decode_mime_header(message.get("From")),
                        subject=_decode_mime_header(message.get("Subject")),
                        date=_decode_mime_header(message.get("Date")),
                    )
                )

    return notifications


def _format_notification(notification: KworkEmailNotification, config: Config) -> str:
    kwork_link = config.kwork_profile_url or "https://kwork.ru"
    return (
        "<b>Новое уведомление от Kwork</b>\n\n"
        f"<b>Тема:</b> {html.escape(notification.subject or 'без темы')}\n"
        f"<b>От:</b> {html.escape(notification.sender or 'не указан')}\n"
        f"<b>Дата:</b> {html.escape(notification.date or 'не указана')}\n\n"
        f'<a href="{html.escape(kwork_link)}">Открыть Kwork</a>\n\n'
        "<i>Проверьте сообщение и отвечайте клиенту внутри Kwork.</i>"
    )


async def start_kwork_email_notifier(bot: Bot, config: Config) -> None:
    if not is_configured(config):
        logger.info("Kwork email notifier is disabled. Fill IMAP settings in .env to enable it.")
        return

    logger.info("Kwork email notifier started")

    while True:
        try:
            notifications = await asyncio.to_thread(_fetch_unseen_notifications, config)
            for notification in notifications:
                await bot.send_message(config.admin_id, _format_notification(notification, config))
                logger.info("Kwork email notification sent for email id=%s", notification.message_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Could not check Kwork email notifications.")

        await asyncio.sleep(config.kwork_email_check_interval)
