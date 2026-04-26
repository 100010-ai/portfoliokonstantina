from __future__ import annotations

import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart, ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ErrorEvent, Message

from config import Config
from database import add_review, save_technical_spec
from keyboards import (
    CALLBACK_ABOUT,
    CALLBACK_BACK,
    CALLBACK_FAQ,
    CALLBACK_KWORK,
    CALLBACK_MAIN_MENU,
    CALLBACK_ORDER_GUIDE,
    CALLBACK_PRICES,
    CALLBACK_PROCESS,
    CALLBACK_REQUEST,
    CALLBACK_REVIEWS,
    CALLBACK_SERVICES,
    CALLBACK_WORKS,
    back_keyboard,
    form_keyboard,
    kwork_keyboard,
    kwork_order_keyboard,
    main_menu_keyboard,
)
from reviews import build_reviews_text, clear_reviews_cache
from review_sync import sync_reviews_once
from texts import (
    ABOUT_TEXT,
    EMPTY_ANSWER_TEXT,
    ERROR_TEXT,
    FAQ_TEXT,
    FORM_CANCELLED_TEXT,
    HELP_TEXT,
    KWORK_TEXT,
    ORDER_GUIDE_TEXT,
    PRICES_TEXT,
    PROCESS_TEXT,
    REQUEST_ADMIN_TEXT,
    REQUEST_START_TEXT,
    REQUEST_SUCCESS_TEXT,
    SERVICES_TEXT,
    START_TEXT,
    UNKNOWN_TEXT,
    WORKS_TEXT,
)
from tz_builder import build_technical_spec


logger = logging.getLogger(__name__)
router = Router()
MAX_TZ_INPUT_LENGTH = 1500


@router.message.outer_middleware()
async def log_messages(handler, event: Message, data: dict):
    logger.info(
        "Incoming message from user_id=%s chat_id=%s text_present=%s",
        event.from_user.id if event.from_user else None,
        event.chat.id,
        bool(event.text),
    )
    return await handler(event, data)


@router.callback_query.outer_middleware()
async def log_callbacks(handler, event: CallbackQuery, data: dict):
    logger.info(
        "Incoming callback from user_id=%s data=%r",
        event.from_user.id,
        event.data,
    )
    return await handler(event, data)


class RequestForm(StatesGroup):
    description = State()


SECTION_TEXTS = {
    CALLBACK_ABOUT: ABOUT_TEXT,
    CALLBACK_SERVICES: SERVICES_TEXT,
    CALLBACK_WORKS: WORKS_TEXT,
    CALLBACK_PRICES: PRICES_TEXT,
    CALLBACK_PROCESS: PROCESS_TEXT,
    CALLBACK_FAQ: FAQ_TEXT,
    CALLBACK_ORDER_GUIDE: ORDER_GUIDE_TEXT,
}

SECTION_CALLBACKS = tuple(SECTION_TEXTS.keys())


async def _show_main_menu(message: Message) -> None:
    await message.answer(START_TEXT, reply_markup=main_menu_keyboard())


async def _delete_quietly(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    await callback.answer()

    if callback.message is None:
        return

    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            logger.debug("Could not edit message, sending a new one: %s", error)
            await callback.message.answer(text, reply_markup=reply_markup)


def _clean(value: str) -> str:
    return html.escape(value.strip())


def _escape_limited(value: str, limit: int = 3200) -> str:
    value = value.strip()
    if len(value) > limit:
        value = f"{value[: limit - 40].rstrip()}\n\n...ТЗ получилось длинным, полный текст можно доработать на Kwork."
    return html.escape(value)


def _build_brief_text(data: dict[str, str]) -> str:
    return build_technical_spec(data).plain_text


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    logger.info("Received /start from user_id=%s", message.from_user.id if message.from_user else None)
    await state.clear()
    await _show_main_menu(message)


@router.message(Command("menu"))
async def menu_command(message: Message, state: FSMContext) -> None:
    logger.info("Received /menu from user_id=%s", message.from_user.id if message.from_user else None)
    await state.clear()
    await _show_main_menu(message)


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    logger.info("Received /help from user_id=%s", message.from_user.id if message.from_user else None)
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("status"))
async def status_command(message: Message, config: Config) -> None:
    if config.admin_id is None or not message.from_user or message.from_user.id != config.admin_id:
        await message.answer("Команда доступна только администратору.")
        return

    kwork_email_enabled = bool(
        config.kwork_email_imap_host and config.kwork_email_login and config.kwork_email_password
    )
    status_text = f"""
<b>Статус бота</b>

<b>Kwork профиль:</b> {"заполнен" if config.kwork_profile_url else "не заполнен"}
<b>Kwork услуга:</b> {"заполнена" if config.kwork_bot_service_url else "не заполнена"}
<b>Ссылка отзывов:</b> {"заполнена" if config.kwork_reviews_url else "не заполнена"}
<b>База данных:</b> {"PostgreSQL" if config.database_url else "SQLite"}
<b>Email-уведомления Kwork:</b> {"включены" if kwork_email_enabled else "выключены"}
<b>Синхронизация отзывов:</b> каждые {config.reviews_sync_interval} сек.
<b>IMAP папка:</b> {html.escape(config.kwork_email_folder)}
<b>Интервал проверки:</b> {config.kwork_email_check_interval} сек.
""".strip()
    await message.answer(status_text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data.in_(SECTION_CALLBACKS))
async def show_section(callback: CallbackQuery) -> None:
    logger.info("Show section callback=%s", callback.data)
    await _edit_or_answer(callback, SECTION_TEXTS[callback.data], reply_markup=back_keyboard())


@router.callback_query(F.data == CALLBACK_REVIEWS)
async def show_reviews(callback: CallbackQuery, config: Config) -> None:
    logger.info("Show reviews")
    await _edit_or_answer(callback, build_reviews_text(config), reply_markup=back_keyboard())


@router.callback_query(F.data == CALLBACK_KWORK)
async def show_kwork_section(callback: CallbackQuery, config: Config) -> None:
    logger.info("Show Kwork section")
    await _edit_or_answer(
        callback,
        KWORK_TEXT,
        reply_markup=kwork_keyboard(config.kwork_profile_url, config.kwork_bot_service_url),
    )


@router.callback_query(F.data == CALLBACK_MAIN_MENU)
async def main_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info("Show main menu")
    await state.clear()
    await _edit_or_answer(callback, START_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == CALLBACK_REQUEST)
async def start_request(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info("Start request form")
    await state.set_state(RequestForm.description)
    await _edit_or_answer(callback, REQUEST_START_TEXT, reply_markup=form_keyboard())
    if callback.message:
        await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(RequestForm.description)
async def request_description(message: Message, state: FSMContext, bot: Bot, config: Config) -> None:
    if not message.text or not message.text.strip():
        await message.answer(EMPTY_ANSWER_TEXT, reply_markup=form_keyboard())
        return

    if len(message.text.strip()) < 15:
        warning = await message.answer(
            "Опишите чуть подробнее: для чего нужен бот и что он должен делать. Можно одним сообщением простыми словами.",
            reply_markup=form_keyboard(),
        )
        await state.update_data(last_bot_message_id=warning.message_id)
        return

    description = message.text.strip()
    if len(description) > MAX_TZ_INPUT_LENGTH:
        description = description[:MAX_TZ_INPUT_LENGTH].rstrip()

    state_data = await state.get_data()
    await _delete_quietly(message)
    if state_data.get("last_bot_message_id"):
        try:
            await bot.delete_message(message.chat.id, state_data["last_bot_message_id"])
        except TelegramBadRequest:
            pass

    data = {"description": description}
    await state.clear()

    username = f"@{message.from_user.username}" if message.from_user and message.from_user.username else "не указан"
    technical_spec = build_technical_spec(data)
    await asyncio.to_thread(
        save_technical_spec,
        config,
        user_id=message.from_user.id if message.from_user else None,
        username=username,
        bot_type=technical_spec.bot_type,
        features=technical_spec.features_summary,
        deadline=technical_spec.deadline,
        budget=technical_spec.budget,
        spec_text=technical_spec.plain_text,
    )
    cleaned_data = {
        "technical_spec": _escape_limited(technical_spec.plain_text),
    }
    admin_text = REQUEST_ADMIN_TEXT.format(
        **cleaned_data,
        username=_clean(username),
    )

    await bot.send_message(
        message.chat.id,
        REQUEST_SUCCESS_TEXT.format(**cleaned_data),
        reply_markup=kwork_order_keyboard(config.kwork_bot_service_url, _build_brief_text(data)),
    )

    if config.admin_id is None:
        logger.warning("Request received, but ADMIN_ID is not configured.")
        return

    try:
        await bot.send_message(config.admin_id, admin_text)
    except TelegramForbiddenError:
        logger.exception("Could not send request to admin. The bot may be blocked by admin.")
    except Exception:
        logger.exception("Could not send request to admin.")


@router.message(Command("add_review"))
async def add_review_command(message: Message, config: Config) -> None:
    if config.admin_id is None or not message.from_user or message.from_user.id != config.admin_id:
        await message.answer("Команда доступна только администратору.")
        return

    raw_text = (message.text or "").removeprefix("/add_review").strip()
    parts = [part.strip() for part in raw_text.split("|")]
    if len(parts) < 4:
        await message.answer(
            "Формат:\n"
            "<code>/add_review 5 | Клиент Kwork | Telegram-бот | Текст отзыва</code>"
        )
        return

    rating_raw, author, project, review_text = parts[0], parts[1], parts[2], " | ".join(parts[3:])
    try:
        rating = int(rating_raw)
    except ValueError:
        rating = 5

    await asyncio.to_thread(
        add_review,
        config,
        author=author,
        rating=rating,
        project=project,
        text=review_text,
        source="Kwork",
    )
    clear_reviews_cache()
    await message.answer("Отзыв добавлен в базу и теперь виден всем в разделе «Отзывы».")


@router.message(Command("sync_reviews"))
async def sync_reviews_command(message: Message, config: Config) -> None:
    if config.admin_id is None or not message.from_user or message.from_user.id != config.admin_id:
        await message.answer("Команда доступна только администратору.")
        return

    await message.answer("Запускаю синхронизацию отзывов с публичной страницы Kwork...")
    try:
        added_count = await asyncio.to_thread(sync_reviews_once, config)
    except Exception:
        logger.exception("Manual reviews sync failed.")
        await message.answer(
            "Не удалось синхронизировать отзывы. Проверьте KWORK_REVIEWS_URL/KWORK_PROFILE_URL и логи Railway."
        )
        return

    clear_reviews_cache()
    await message.answer(f"Синхронизация завершена. Новых отзывов добавлено: {added_count}.")


@router.callback_query(F.data == CALLBACK_BACK)
async def cancel_form_or_back(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info("Back callback")
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        if callback.message:
            try:
                await callback.answer(FORM_CANCELLED_TEXT, show_alert=False)
            except TelegramBadRequest:
                pass

    await _edit_or_answer(callback, START_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("Раздел не найден", show_alert=False)


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(UNKNOWN_TEXT, reply_markup=main_menu_keyboard())


@router.errors(ExceptionTypeFilter(Exception))
async def errors_handler(event: ErrorEvent) -> bool:
    logger.exception("Unhandled update error", exc_info=event.exception)

    update = event.update
    message = getattr(update, "message", None)
    callback_query = getattr(update, "callback_query", None)

    try:
        if message:
            await message.answer(ERROR_TEXT, reply_markup=main_menu_keyboard())
        elif callback_query and callback_query.message:
            await callback_query.message.answer(ERROR_TEXT, reply_markup=main_menu_keyboard())
            await callback_query.answer()
    except Exception:
        logger.exception("Could not send error message to user.")

    return True
