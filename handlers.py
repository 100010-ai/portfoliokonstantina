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
from database import add_review, get_recent_technical_specs, get_stats, save_technical_spec
from keyboards import (
    CALLBACK_ABOUT,
    CALLBACK_ADMIN,
    CALLBACK_ADMIN_HELP,
    CALLBACK_ADMIN_LAST_TZ,
    CALLBACK_ADMIN_STATUS,
    CALLBACK_ADMIN_SYNC_REVIEWS,
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
    admin_keyboard,
    back_keyboard,
    form_keyboard,
    kwork_keyboard,
    kwork_order_keyboard,
    main_menu_keyboard,
)
from review_sync import sync_reviews_once
from reviews import build_reviews_text, clear_reviews_cache
from texts import (
    ABOUT_TEXT,
    EMPTY_ANSWER_TEXT,
    ERROR_TEXT,
    FAQ_TEXT,
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
ADMIN_ONLY_TEXT = "🔒 Команда доступна только администратору."


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
    logger.info("Incoming callback from user_id=%s data=%r", event.from_user.id, event.data)
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


def _is_admin_user(message_or_callback, config: Config) -> bool:
    user = getattr(message_or_callback, "from_user", None)
    return bool(config.admin_id is not None and user and user.id == config.admin_id)


def _is_admin_message(message: Message, config: Config) -> bool:
    return bool(config.admin_id is not None and message.from_user and message.from_user.id == config.admin_id)


def _clean(value: str) -> str:
    return html.escape(value.strip())


def _escape_limited(value: str, limit: int = 3200) -> str:
    value = value.strip()
    if len(value) > limit:
        value = f"{value[: limit - 70].rstrip()}\n\n...ТЗ получилось длинным, полный текст сохранен в базе."
    return html.escape(value)


def _build_brief_text(data: dict[str, str]) -> str:
    return build_technical_spec(data).plain_text


def _status_text(config: Config) -> str:
    email_enabled = bool(config.kwork_email_imap_host and config.kwork_email_login and config.kwork_email_password)
    try:
        stats = get_stats(config)
        stats_text = (
            f"📝 <b>ТЗ в базе:</b> {stats.technical_specs}\n"
            f"⭐ <b>Отзывы:</b> {stats.reviews}\n"
            f"📬 <b>Обработано email:</b> {stats.processed_emails}"
        )
    except Exception:
        logger.exception("Could not load database stats.")
        stats_text = "⚠️ <b>Статистика базы:</b> временно недоступна"

    return f"""
<b>⚙️ Админ-панель</b>
<i>Короткая сводка по настройкам и данным бота.</i>

🔗 <b>Kwork профиль:</b> {"заполнен" if config.kwork_profile_url else "не заполнен"}
🛒 <b>Kwork услуга:</b> {"заполнена" if config.kwork_bot_service_url else "не заполнена"}
⭐ <b>Ссылка отзывов:</b> {"заполнена" if config.kwork_reviews_url else "не заполнена"}
🗄 <b>База данных:</b> {"PostgreSQL" if config.database_url else "SQLite"}
🔔 <b>Email-уведомления:</b> {"включены" if email_enabled else "выключены"}

{stats_text}

📁 <b>IMAP папка:</b> {html.escape(config.kwork_email_folder)}
⏱ <b>Проверка почты:</b> каждые {config.kwork_email_check_interval} сек.
🔄 <b>Синхронизация отзывов:</b> каждые {config.reviews_sync_interval} сек.
""".strip()


def _admin_help_text() -> str:
    return """
<b>⚙️ Админ-команды</b>
<i>Короткая шпаргалка для обслуживания бота.</i>

<b>➕ Добавить отзыв вручную:</b>
<code>/add_review 5 | Клиент Kwork | Telegram-бот | Текст отзыва</code>

<b>📝 Последние ТЗ:</b>
<code>/last_tz</code>

<b>📊 Статус сервиса:</b>
<code>/status</code>

<b>🔄 Обновить отзывы с Kwork:</b>
<code>/sync_reviews</code>
""".strip()


def _latest_tz_text(config: Config) -> str:
    specs = get_recent_technical_specs(config, limit=3)
    if not specs:
        return "<b>📝 Последние ТЗ</b>\n\nПока пусто. Когда пользователь соберет ТЗ через бота, оно появится здесь."

    blocks = ["<b>📝 Последние ТЗ</b>", "<i>Показываю 3 последних заявки из базы.</i>"]
    for item in specs:
        preview = item.spec_text.strip()
        if len(preview) > 550:
            preview = f"{preview[:550].rstrip()}..."
        blocks.append(
            f"""
<b>#{item.id}</b> {html.escape(item.username)}
<b>Тип:</b> {html.escape(item.bot_type)}
<b>Срок:</b> {html.escape(item.deadline)}
<b>Бюджет:</b> {html.escape(item.budget)}

<pre>{html.escape(preview)}</pre>
""".strip()
        )
    return "\n\n".join(blocks)


async def _show_main_menu(message: Message, config: Config | None = None) -> None:
    is_admin = bool(config and _is_admin_message(message, config))
    await message.answer(START_TEXT, reply_markup=main_menu_keyboard(is_admin=is_admin))


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


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext, config: Config) -> None:
    logger.info("Received /start from user_id=%s", message.from_user.id if message.from_user else None)
    await state.clear()
    await _show_main_menu(message, config)


@router.message(Command("menu"))
async def menu_command(message: Message, state: FSMContext, config: Config) -> None:
    await state.clear()
    await _show_main_menu(message, config)


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext, config: Config) -> None:
    await state.clear()
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard(is_admin=_is_admin_message(message, config)))


@router.message(Command("status"))
async def status_command(message: Message, config: Config) -> None:
    if not _is_admin_message(message, config):
        await message.answer(ADMIN_ONLY_TEXT)
        return
    status_text = await asyncio.to_thread(_status_text, config)
    await message.answer(status_text, reply_markup=admin_keyboard())


@router.message(Command("last_tz"))
async def last_tz_command(message: Message, config: Config) -> None:
    if not _is_admin_message(message, config):
        await message.answer(ADMIN_ONLY_TEXT)
        return
    text = await asyncio.to_thread(_latest_tz_text, config)
    await message.answer(text, reply_markup=admin_keyboard())


@router.callback_query(F.data.in_(SECTION_CALLBACKS))
async def show_section(callback: CallbackQuery) -> None:
    await _edit_or_answer(callback, SECTION_TEXTS[callback.data], reply_markup=back_keyboard())


@router.callback_query(F.data == CALLBACK_REVIEWS)
async def show_reviews(callback: CallbackQuery, config: Config) -> None:
    text = await asyncio.to_thread(build_reviews_text, config)
    await _edit_or_answer(callback, text, reply_markup=back_keyboard())


@router.callback_query(F.data == CALLBACK_KWORK)
async def show_kwork_section(callback: CallbackQuery, config: Config) -> None:
    await _edit_or_answer(
        callback,
        KWORK_TEXT,
        reply_markup=kwork_keyboard(config.kwork_profile_url, config.kwork_bot_service_url),
    )


@router.callback_query(F.data == CALLBACK_MAIN_MENU)
async def main_menu_callback(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.clear()
    await _edit_or_answer(
        callback,
        START_TEXT,
        reply_markup=main_menu_keyboard(is_admin=_is_admin_user(callback, config)),
    )


@router.callback_query(F.data == CALLBACK_ADMIN)
async def admin_panel_callback(callback: CallbackQuery, config: Config) -> None:
    if not _is_admin_user(callback, config):
        await callback.answer("🔒 Недоступно", show_alert=False)
        return
    status_text = await asyncio.to_thread(_status_text, config)
    await _edit_or_answer(callback, status_text, reply_markup=admin_keyboard())


@router.callback_query(F.data == CALLBACK_ADMIN_STATUS)
async def admin_status_callback(callback: CallbackQuery, config: Config) -> None:
    if not _is_admin_user(callback, config):
        await callback.answer("🔒 Недоступно", show_alert=False)
        return
    status_text = await asyncio.to_thread(_status_text, config)
    await _edit_or_answer(callback, status_text, reply_markup=admin_keyboard())


@router.callback_query(F.data == CALLBACK_ADMIN_HELP)
async def admin_help_callback(callback: CallbackQuery, config: Config) -> None:
    if not _is_admin_user(callback, config):
        await callback.answer("🔒 Недоступно", show_alert=False)
        return
    await _edit_or_answer(callback, _admin_help_text(), reply_markup=admin_keyboard())


@router.callback_query(F.data == CALLBACK_ADMIN_LAST_TZ)
async def admin_last_tz_callback(callback: CallbackQuery, config: Config) -> None:
    if not _is_admin_user(callback, config):
        await callback.answer("🔒 Недоступно", show_alert=False)
        return
    text = await asyncio.to_thread(_latest_tz_text, config)
    await _edit_or_answer(callback, text, reply_markup=admin_keyboard())


@router.callback_query(F.data == CALLBACK_ADMIN_SYNC_REVIEWS)
async def admin_sync_reviews_callback(callback: CallbackQuery, config: Config) -> None:
    if not _is_admin_user(callback, config):
        await callback.answer("🔒 Недоступно", show_alert=False)
        return

    await callback.answer("🔄 Обновляю отзывы...")
    try:
        added_count = await asyncio.to_thread(sync_reviews_once, config)
    except Exception:
        logger.exception("Manual reviews sync failed.")
        text = (
            "<b>⚠️ Не удалось синхронизировать отзывы</b>\n\n"
            "Проверьте <code>KWORK_REVIEWS_URL</code>, <code>KWORK_PROFILE_URL</code> и логи Railway."
        )
    else:
        clear_reviews_cache()
        text = f"<b>✅ Синхронизация завершена</b>\n\nНовых отзывов добавлено: <b>{added_count}</b>."

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=admin_keyboard())
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=admin_keyboard())


@router.callback_query(F.data == CALLBACK_REQUEST)
async def start_request(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RequestForm.description)
    await _edit_or_answer(callback, REQUEST_START_TEXT, reply_markup=form_keyboard())
    if callback.message:
        await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(RequestForm.description)
async def request_description(message: Message, state: FSMContext, bot: Bot, config: Config) -> None:
    if not message.text or not message.text.strip():
        await message.answer(EMPTY_ANSWER_TEXT, reply_markup=form_keyboard())
        return

    description = message.text.strip()
    if len(description) < 15:
        warning = await message.answer(
            (
                "✍️ Опишите чуть подробнее: для чего нужен бот, что должен делать пользователь "
                "и куда отправлять результат. Можно одним сообщением простыми словами."
            ),
            reply_markup=form_keyboard(),
        )
        await state.update_data(last_bot_message_id=warning.message_id)
        return

    if len(description) > MAX_TZ_INPUT_LENGTH:
        description = description[:MAX_TZ_INPUT_LENGTH].rstrip()

    state_data = await state.get_data()
    await _delete_quietly(message)
    if state_data.get("last_bot_message_id"):
        try:
            await bot.delete_message(message.chat.id, state_data["last_bot_message_id"])
        except TelegramBadRequest:
            pass

    await state.clear()
    data = {"description": description}
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
        "bot_type": _clean(technical_spec.bot_type),
        "deadline": _clean(technical_spec.deadline),
        "budget": _clean(technical_spec.budget),
        "technical_spec": _escape_limited(technical_spec.plain_text),
    }

    await bot.send_message(
        message.chat.id,
        REQUEST_SUCCESS_TEXT.format(**cleaned_data),
        reply_markup=kwork_order_keyboard(config.kwork_bot_service_url, _build_brief_text(data)),
    )

    admin_id = config.admin_id
    if admin_id is None:
        logger.warning("Request received, but ADMIN_ID is not configured.")
        return

    admin_text = REQUEST_ADMIN_TEXT.format(**cleaned_data, username=_clean(username))
    try:
        await bot.send_message(admin_id, admin_text)
    except TelegramForbiddenError:
        logger.exception("Could not send request to admin. The bot may be blocked by admin.")
    except Exception:
        logger.exception("Could not send request to admin.")


@router.message(Command("add_review"))
async def add_review_command(message: Message, config: Config) -> None:
    if not _is_admin_message(message, config):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    raw_text = (message.text or "").removeprefix("/add_review").strip()
    parts = [part.strip() for part in raw_text.split("|")]
    if len(parts) < 4:
        await message.answer(
            "<b>➕ Формат добавления отзыва:</b>\n"
            "<code>/add_review 5 | Клиент Kwork | Telegram-бот | Текст отзыва</code>"
        )
        return

    rating_raw, author, project, review_text = parts[0], parts[1], parts[2], " | ".join(parts[3:])
    try:
        rating = int(rating_raw)
    except ValueError:
        rating = 5

    added = await asyncio.to_thread(
        add_review,
        config,
        author=author,
        rating=rating,
        project=project,
        text=review_text,
        source="Kwork",
    )
    clear_reviews_cache()
    if added:
        await message.answer("✅ Отзыв добавлен в базу и теперь виден всем в разделе «Отзывы».")
    else:
        await message.answer("⚠️ Отзыв не добавлен: он пустой или уже есть в базе.")


@router.message(Command("sync_reviews"))
async def sync_reviews_command(message: Message, config: Config) -> None:
    if not _is_admin_message(message, config):
        await message.answer(ADMIN_ONLY_TEXT)
        return

    await message.answer("🔄 Запускаю синхронизацию отзывов с публичной страницы Kwork...")
    try:
        added_count = await asyncio.to_thread(sync_reviews_once, config)
    except Exception:
        logger.exception("Manual reviews sync failed.")
        await message.answer(
            "<b>⚠️ Не удалось синхронизировать отзывы</b>\n\n"
            "Проверьте <code>KWORK_REVIEWS_URL</code>, <code>KWORK_PROFILE_URL</code> и логи Railway."
        )
        return

    clear_reviews_cache()
    await message.answer(f"<b>✅ Синхронизация завершена</b>\n\nНовых отзывов добавлено: <b>{added_count}</b>.")


@router.callback_query(F.data == CALLBACK_BACK)
async def cancel_form_or_back(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    await _edit_or_answer(
        callback,
        START_TEXT,
        reply_markup=main_menu_keyboard(is_admin=_is_admin_user(callback, config)),
    )


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("Раздел не найден 🙂", show_alert=False)


@router.message()
async def unknown_message(message: Message, config: Config) -> None:
    await message.answer(UNKNOWN_TEXT, reply_markup=main_menu_keyboard(is_admin=_is_admin_message(message, config)))


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
