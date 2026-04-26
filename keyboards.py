from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


CALLBACK_ABOUT = "section:about"
CALLBACK_SERVICES = "section:services"
CALLBACK_WORKS = "section:works"
CALLBACK_PRICES = "section:prices"
CALLBACK_PROCESS = "section:process"
CALLBACK_FAQ = "section:faq"
CALLBACK_KWORK = "section:kwork"
CALLBACK_ORDER_GUIDE = "section:order_guide"
CALLBACK_REQUEST = "request:start"
CALLBACK_MAIN_MENU = "menu:main"
CALLBACK_BACK = "menu:back"

DEFAULT_KWORK_URL = "https://kwork.ru"


MAIN_MENU_BUTTONS = (
    ("👤 Обо мне", CALLBACK_ABOUT),
    ("🧰 Услуги", CALLBACK_SERVICES),
    ("📂 Кейсы", CALLBACK_WORKS),
    ("💳 Пакеты", CALLBACK_PRICES),
    ("🧭 Этапы", CALLBACK_PROCESS),
    ("💬 FAQ", CALLBACK_FAQ),
    ("📝 Собрать ТЗ", CALLBACK_REQUEST),
    ("🛒 Kwork", CALLBACK_KWORK),
    ("📌 Как оформить заказ", CALLBACK_ORDER_GUIDE),
)


def _safe_url(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else DEFAULT_KWORK_URL


def _button(
    text: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    copy_text: str | None = None,
) -> InlineKeyboardButton:
    payload = {"text": text}
    if callback_data is not None:
        payload["callback_data"] = callback_data
    if url is not None:
        payload["url"] = _safe_url(url)
    if copy_text is not None:
        payload["copy_text"] = {"text": copy_text}

    try:
        return InlineKeyboardButton(**payload)
    except Exception:
        payload.pop("copy_text", None)
        return InlineKeyboardButton(**payload)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            _button(text=MAIN_MENU_BUTTONS[0][0], callback_data=MAIN_MENU_BUTTONS[0][1]),
            _button(text=MAIN_MENU_BUTTONS[1][0], callback_data=MAIN_MENU_BUTTONS[1][1]),
        ],
        [
            _button(text=MAIN_MENU_BUTTONS[2][0], callback_data=MAIN_MENU_BUTTONS[2][1]),
            _button(text=MAIN_MENU_BUTTONS[3][0], callback_data=MAIN_MENU_BUTTONS[3][1]),
        ],
        [
            _button(text=MAIN_MENU_BUTTONS[4][0], callback_data=MAIN_MENU_BUTTONS[4][1]),
            _button(text=MAIN_MENU_BUTTONS[5][0], callback_data=MAIN_MENU_BUTTONS[5][1]),
        ],
        [
            _button(text=MAIN_MENU_BUTTONS[6][0], callback_data=MAIN_MENU_BUTTONS[6][1]),
            _button(text=MAIN_MENU_BUTTONS[7][0], callback_data=MAIN_MENU_BUTTONS[7][1]),
        ],
        [_button(text=MAIN_MENU_BUTTONS[8][0], callback_data=MAIN_MENU_BUTTONS[8][1])],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button(text="← Назад", callback_data=CALLBACK_BACK)],
        ]
    )


def form_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button(text="← Назад", callback_data=CALLBACK_BACK)],
        ]
    )


def kwork_keyboard(profile_url: str, service_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button(text="🛒 Открыть мой Kwork", url=profile_url)],
            [_button(text="🤖 Заказать Telegram-бота", url=service_url)],
            [_button(text="← Назад", callback_data=CALLBACK_BACK)],
        ]
    )


def kwork_order_keyboard(service_url: str, copy_text: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if copy_text:
        rows.append([_button(text="📋 Скопировать ТЗ", copy_text=copy_text)])
    rows.append([_button(text="🛒 Оформить заказ на Kwork", url=service_url)])
    rows.append([_button(text="← Назад", callback_data=CALLBACK_BACK)])

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )
