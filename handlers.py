from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart, ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ErrorEvent, Message

from config import Config
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
    CALLBACK_SERVICES,
    CALLBACK_WORKS,
    back_keyboard,
    form_keyboard,
    kwork_keyboard,
    kwork_order_keyboard,
    main_menu_keyboard,
)
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
    REQUEST_BUDGET_TEXT,
    REQUEST_DEADLINE_TEXT,
    REQUEST_FEATURES_TEXT,
    REQUEST_START_TEXT,
    REQUEST_SUCCESS_TEXT,
    SERVICES_TEXT,
    START_TEXT,
    UNKNOWN_TEXT,
    WORKS_TEXT,
)


logger = logging.getLogger(__name__)
router = Router()


@router.message.outer_middleware()
async def log_messages(handler, event: Message, data: dict):
    logger.info(
        "Incoming message from user_id=%s chat_id=%s text=%r",
        event.from_user.id if event.from_user else None,
        event.chat.id,
        event.text,
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
    bot_type = State()
    features = State()
    deadline = State()
    budget = State()


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


def _build_brief_text(data: dict[str, str]) -> str:
    return (
        "Краткое ТЗ для заказа на Kwork\n\n"
        f"Тип бота: {data['bot_type']}\n"
        f"Что должен уметь бот: {data['features']}\n"
        f"Желаемый срок: {data['deadline']}\n"
        f"Примерный бюджет: {data['budget']}"
    )


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


@router.callback_query(F.data.in_(SECTION_CALLBACKS))
async def show_section(callback: CallbackQuery) -> None:
    logger.info("Show section callback=%s", callback.data)
    await _edit_or_answer(callback, SECTION_TEXTS[callback.data], reply_markup=back_keyboard())


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
    await state.set_state(RequestForm.bot_type)
    await _edit_or_answer(callback, REQUEST_START_TEXT, reply_markup=form_keyboard())


@router.message(RequestForm.bot_type)
async def request_bot_type(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer(EMPTY_ANSWER_TEXT, reply_markup=form_keyboard())
        return

    await state.update_data(bot_type=message.text.strip())
    await state.set_state(RequestForm.features)
    await message.answer(REQUEST_FEATURES_TEXT, reply_markup=form_keyboard())


@router.message(RequestForm.features)
async def request_features(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer(EMPTY_ANSWER_TEXT, reply_markup=form_keyboard())
        return

    await state.update_data(features=message.text.strip())
    await state.set_state(RequestForm.deadline)
    await message.answer(REQUEST_DEADLINE_TEXT, reply_markup=form_keyboard())


@router.message(RequestForm.deadline)
async def request_deadline(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer(EMPTY_ANSWER_TEXT, reply_markup=form_keyboard())
        return

    await state.update_data(deadline=message.text.strip())
    await state.set_state(RequestForm.budget)
    await message.answer(REQUEST_BUDGET_TEXT, reply_markup=form_keyboard())


@router.message(RequestForm.budget)
async def request_budget(message: Message, state: FSMContext, bot: Bot, config: Config) -> None:
    if not message.text or not message.text.strip():
        await message.answer(EMPTY_ANSWER_TEXT, reply_markup=form_keyboard())
        return

    await state.update_data(budget=message.text.strip())
    data = await state.get_data()
    await state.clear()

    username = f"@{message.from_user.username}" if message.from_user and message.from_user.username else "не указан"
    cleaned_data = {
        "bot_type": _clean(data["bot_type"]),
        "features": _clean(data["features"]),
        "deadline": _clean(data["deadline"]),
        "budget": _clean(data["budget"]),
    }
    admin_text = REQUEST_ADMIN_TEXT.format(
        **cleaned_data,
        username=_clean(username),
    )

    await message.answer(
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


@router.callback_query(F.data == CALLBACK_BACK)
async def cancel_form_or_back(callback: CallbackQuery, state: FSMContext) -> None:
    logger.info("Back callback")
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        if callback.message:
            await callback.message.answer(FORM_CANCELLED_TEXT)

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
