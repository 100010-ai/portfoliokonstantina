from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicalSpec:
    title: str
    plain_text: str
    bot_type: str
    features_summary: str
    deadline: str
    budget: str


def _normalize(text: str) -> str:
    return " ".join(text.strip().split())


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in keywords)


def _pick(text: str, rules: list[tuple[tuple[str, ...], str]], default: str) -> str:
    for keywords, value in rules:
        if _has_any(text, keywords):
            return value
    return default


def _items(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in dict.fromkeys(items))


def _extract_deadline(text: str, fallback: str = "нужно согласовать") -> str:
    patterns = (
        r"(?:за|в течение)\s+\d+\s*(?:дн|дня|дней|час|часа|часов|недел[яиюь])",
        r"\d+\s*-\s*\d+\s*(?:дн|дня|дней|час|часа|часов|недел[яиюь])",
        r"(?:срочно|как можно быстрее|без срочности|не срочно|сегодня|завтра)",
    )
    lower_text = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower_text)
        if match:
            return match.group(0)
    return fallback


def _extract_budget(text: str, fallback: str = "нужно оценить после уточнения деталей") -> str:
    patterns = (
        r"(?:до|от)?\s*\d[\d\s]*(?:-|–)?\s*\d*[\d\s]*\s*(?:₽|руб|р|тыс)",
        r"(?:бюджет|цена|стоимость)\s*[:\-]?\s*[^,.!?]{1,40}",
    )
    lower_text = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower_text)
        if match:
            return _normalize(match.group(0))
    return fallback


def _is_moderation(text: str) -> bool:
    return _has_any(text, ("модерац", "модер", "чат", "групп", "бан", "мут", "спам", "мат", "капс", "флуд"))


def _detect_bot_type(text: str) -> str:
    return _pick(
        text,
        [
            (("модерац", "модер", "чат", "групп", "бан", "мут", "спам", "мат", "капс"), "Telegram-бот для модерации чатов"),
            (("салон", "барбер", "мастер", "маникюр", "красот"), "Telegram-бот для записи клиентов"),
            (("ресторан", "кафе", "доставк", "еда", "меню"), "Telegram-бот для кафе или доставки"),
            (("курс", "школ", "обуч", "урок", "вебинар"), "Telegram-бот для онлайн-школы"),
            (("магаз", "товар", "каталог", "корзин", "продаж"), "Telegram-бот-магазин"),
            (("запис", "брон", "слот", "распис", "услуг"), "Telegram-бот для записи клиентов"),
            (("заяв", "анкета", "форма", "лид", "опрос"), "Telegram-бот для приема заявок"),
            (("ai", "ии", "gpt", "нейро", "ассистент", "консультант"), "AI-ассистент в Telegram"),
            (("рассыл", "уведом", "напомин", "новост"), "Telegram-бот для рассылок и уведомлений"),
            (("админ", "панел", "управлен"), "Telegram-бот с админ-панелью"),
            (("парсер", "парсинг", "сбор данных", "автоматизац"), "Telegram-бот для автоматизации"),
        ],
        "Telegram-бот под задачу бизнеса",
    )


def _detect_goal(text: str) -> str:
    if _is_moderation(text):
        return "помогать администратору следить за порядком в чатах и группах"
    return _pick(
        text,
        [
            (("салон", "барбер", "мастер", "маникюр", "красот", "запис"), "помогать клиентам выбирать услугу и записываться на удобное время"),
            (("магаз", "товар", "каталог", "корзин"), "помогать клиентам выбирать товары и оформлять заказ внутри Telegram"),
            (("заяв", "анкета", "форма", "лид"), "собирать заявки в едином формате и передавать их администратору"),
            (("ai", "ии", "gpt", "нейро", "ассистент"), "отвечать на типовые вопросы пользователей и помогать с первичной консультацией"),
            (("рассыл", "уведом", "напомин"), "доставлять уведомления, новости и напоминания нужным пользователям"),
        ],
        "упростить общение с клиентами и автоматизировать повторяющиеся действия",
    )


def _detect_audience(text: str) -> str:
    if _is_moderation(text):
        return "администраторы и участники Telegram-группы"
    return _pick(
        text,
        [
            (("клиент", "покупател", "заказчик"), "клиенты и потенциальные покупатели"),
            (("сотрудник", "менеджер", "админ"), "сотрудники и администраторы проекта"),
            (("ученик", "студент", "курс", "обуч"), "ученики или участники онлайн-обучения"),
            (("подписчик", "аудитор"), "подписчики и аудитория проекта"),
        ],
        "пользователи Telegram, которым нужно быстро получить услугу или оставить заявку",
    )


def _detect_modules(text: str) -> list[str]:
    modules = ["стартовое меню или базовые команды"]

    if _is_moderation(text):
        return modules + [
            "добавление бота в группу и проверка прав администратора",
            "проверка сообщений по правилам: ссылки, спам, мат, капс или флуд",
            "действия при нарушении: предупреждение, удаление сообщения, мут или бан",
            "уведомления администратору о нарушениях",
            "настройка правил модерации для конкретной группы",
            "лог нарушений для последующей проверки",
        ]

    if _has_any(text, ("услуг", "о нас", "обо мне", "портфолио", "цены")):
        modules.append("информационные разделы: услуги, цены, описание проекта")
    if _has_any(text, ("заяв", "анкета", "форма", "лид", "контакт", "телефон")):
        modules.append("пошаговая форма заявки с вопросами для пользователя")
    if _has_any(text, ("запис", "брон", "слот", "дата", "время", "распис")):
        modules.append("запись клиента с выбором услуги, даты и времени")
    if _has_any(text, ("магаз", "товар", "каталог", "корзин")):
        modules.append("каталог товаров, карточки, корзина и оформление заказа")
    if _has_any(text, ("админ", "панел", "управ", "редакт")):
        modules.append("админ-раздел для управления заявками и контентом")
    if _has_any(text, ("база", "sqlite", "postgres", "хран", "сохраня")):
        modules.append("сохранение данных в базе")
    if _has_any(text, ("google", "sheet", "таблиц", "гугл")):
        modules.append("интеграция с Google Sheets")
    if _has_any(text, ("crm", "api", "интеграц", "сервис")):
        modules.append("интеграция с внешним API или CRM")
    if _has_any(text, ("оплат", "платеж", "касс", "yookassa")):
        modules.append("сценарий оплаты или подключение платежного сервиса")
    if _has_any(text, ("ai", "ии", "gpt", "нейро", "ассистент", "консульт")):
        modules.append("AI-ответы по заданной логике или базе знаний")
    if _has_any(text, ("рассыл", "уведом", "напомин")):
        modules.append("рассылки, уведомления и напоминания")

    if len(modules) == 1:
        modules.extend([
            "понятная навигация по разделам",
            "основной пользовательский сценарий",
            "уведомление администратора о важных действиях",
        ])
    return modules


def _detect_data_fields(text: str) -> list[str]:
    if _is_moderation(text):
        return [
            "ID группы или чата",
            "ID пользователя-нарушителя",
            "текст сообщения",
            "тип нарушения",
            "дата и время события",
            "действие бота: предупреждение, удаление, мут, бан или уведомление",
        ]

    fields = []
    if _has_any(text, ("имя", "фио")):
        fields.append("имя пользователя")
    if _has_any(text, ("телефон", "номер")):
        fields.append("номер телефона")
    if _has_any(text, ("username", "ник", "телеграм", "telegram")):
        fields.append("Telegram username")
    if _has_any(text, ("услуг", "товар", "каталог")):
        fields.append("выбранная услуга или товар")
    if _has_any(text, ("дата", "время", "запис", "брон")):
        fields.append("дата и время записи")
    if _has_any(text, ("коммент", "описан", "задач", "пожел")):
        fields.append("комментарий или описание задачи")

    return fields or ["имя", "описание задачи", "выбранная услуга или действие пользователя"]


def _detect_integrations(text: str) -> list[str]:
    if _is_moderation(text):
        integrations = ["Telegram groups API"]
        if _has_any(text, ("ai", "ии", "gpt", "нейро")):
            integrations.append("AI-проверка спорных сообщений")
        return integrations

    integrations = []
    if _has_any(text, ("google", "sheet", "таблиц", "гугл")):
        integrations.append("Google Sheets")
    if _has_any(text, ("crm", "amo", "битрикс", "bitrix")):
        integrations.append("CRM")
    if _has_any(text, ("api", "сервис")):
        integrations.append("внешний API")
    if _has_any(text, ("оплат", "yookassa", "stripe", "платеж")):
        integrations.append("платежный сервис")
    if _has_any(text, ("ai", "ии", "gpt", "openai", "нейро")):
        integrations.append("AI-модель или база знаний")
    return integrations or ["интеграции не указаны, можно добавить при необходимости"]


def _detect_mvp(text: str) -> list[str]:
    if _is_moderation(text):
        return [
            "добавление бота в группу",
            "базовые правила модерации",
            "проверка новых сообщений",
            "команды для администратора",
            "лог нарушений или уведомления админу",
        ]

    mvp = ["меню бота", "основной пользовательский сценарий", "финальное сообщение для пользователя"]
    if _has_any(text, ("заяв", "анкета", "форма", "лид", "запис", "магаз", "заказ")):
        mvp.append("уведомление администратора о новой заявке или заказе")
    if _has_any(text, ("база", "хран", "сохраня", "админ")):
        mvp.append("сохранение данных")
    if _has_any(text, ("админ", "панел")):
        mvp.append("минимальный админ-раздел")
    return mvp


def _detect_risks(text: str) -> list[str]:
    risks = []
    if _is_moderation(text):
        risks.extend([
            "боту нужны права администратора в группе для удаления сообщений, мутов или банов",
            "правила модерации нужно согласовать, чтобы бот не блокировал нормальные сообщения",
        ])
    if _has_any(text, ("оплат", "платеж", "yookassa")):
        risks.append("для оплаты понадобятся данные платежного сервиса и проверка сценария оплаты")
    if _has_any(text, ("ai", "ии", "gpt", "нейро")):
        risks.append("для AI-ответов нужно определить источник знаний и ограничения ответов")
    if _has_any(text, ("crm", "api", "интеграц")):
        risks.append("для интеграций нужны доступы/API-ключи и пример обмена данными")
    if _has_any(text, ("срочно", "сегодня", "завтра")):
        risks.append("срочный срок может потребовать упрощения первой версии")
    return risks or ["перед стартом нужно согласовать точный сценарий и список экранов"]


def _detect_questions(text: str) -> list[str]:
    if _is_moderation(text):
        return [
            "какие нарушения нужно отслеживать: ссылки, мат, спам, капс, флуд",
            "что делать с нарушителем: предупреждение, удаление сообщения, мут или бан",
            "нужен ли лог нарушений для администратора",
            "нужны ли разные правила для разных групп",
            "достаточно обычных правил или нужна AI-проверка спорных сообщений",
        ]

    questions = []
    if not _has_any(text, ("админ", "уведом", "таблиц", "crm", "почт")):
        questions.append("куда отправлять заявки: в Telegram, таблицу, CRM или другое место")
    if not _has_any(text, ("текст", "кноп", "меню", "раздел")):
        questions.append("какие разделы и кнопки должны быть в первом меню")
    if _has_any(text, ("магаз", "товар", "каталог")) and not _has_any(text, ("достав", "оплат", "самовывоз")):
        questions.append("нужны ли оплата, доставка, самовывоз и статусы заказа")
    if _has_any(text, ("ai", "ии", "gpt", "нейро")) and not _has_any(text, ("база знаний", "файл", "документ", "сайт")):
        questions.append("на основе каких материалов AI должен отвечать")
    if not _has_any(text, ("срок", "день", "недел", "срочно", "бюджет", "руб", "₽")):
        questions.append("какие желаемые сроки и ориентировочный бюджет")
    return questions


def _build_flow(text: str) -> str:
    if _is_moderation(text):
        return "\n".join(
            (
                "1. Администратор добавляет бота в группу и выдает нужные права.",
                "2. Владелец настраивает правила модерации.",
                "3. Бот проверяет новые сообщения в группе.",
                "4. При нарушении бот выполняет действие: предупреждение, удаление сообщения, мут или бан.",
                "5. Администратор получает уведомление или смотрит лог нарушений.",
            )
        )

    return "\n".join(
        (
            "1. Пользователь запускает бота.",
            "2. Бот показывает понятное меню и предлагает нужные действия.",
            "3. Пользователь выбирает раздел или проходит сценарий по шагам.",
            "4. Бот собирает нужные данные, проверяет ответы и показывает итог.",
            "5. Администратор получает уведомление или данные сохраняются в базе/таблице.",
        )
    )


def _build_from_description(description: str, deadline: str = "", budget: str = "") -> TechnicalSpec:
    description = _normalize(description)[:1500]
    deadline = _normalize(deadline) or _extract_deadline(description)
    budget = _normalize(budget) or _extract_budget(description)

    bot_type = _detect_bot_type(description)
    goal = _detect_goal(description)
    audience = _detect_audience(description)
    modules = _detect_modules(description)
    data_fields = _detect_data_fields(description)
    integrations = _detect_integrations(description)
    mvp = _detect_mvp(description)
    risks = _detect_risks(description)
    questions = _detect_questions(description)

    features_summary = "; ".join(modules[:4])
    title = f"ТЗ: {bot_type}"

    plain_text = f"""
Техническое задание для заказа на Kwork

1. Проект
{bot_type}

2. Цель
Разработать Telegram-бота, который будет {goal}.

3. Для кого бот
{audience}.

4. Что написал клиент
{description}

5. Основной функционал
{_items(modules)}

6. Какие данные нужно хранить или передавать
{_items(data_fields)}

7. Логика работы
{_build_flow(description)}

8. Интеграции
{_items(integrations)}

9. Минимальная первая версия
{_items(mvp)}

10. Срок
{deadline}

11. Бюджет
{budget}

12. Важные моменты
{_items(risks)}

13. Что уточнить перед стартом
{_items(questions)}
""".strip()

    plain_text = re.sub(r"\n{3,}", "\n\n", plain_text)
    return TechnicalSpec(
        title=title,
        plain_text=plain_text,
        bot_type=bot_type,
        features_summary=features_summary,
        deadline=deadline,
        budget=budget,
    )


def build_technical_spec_from_description(description: str) -> TechnicalSpec:
    return _build_from_description(description)


def build_technical_spec(data: dict[str, str]) -> TechnicalSpec:
    if data.get("description"):
        return _build_from_description(
            data["description"],
            deadline=data.get("deadline", ""),
            budget=data.get("budget", ""),
        )

    description = ". ".join(
        part
        for part in (
            data.get("bot_type", ""),
            data.get("features", ""),
            f"Срок: {data.get('deadline', '')}" if data.get("deadline") else "",
            f"Бюджет: {data.get('budget', '')}" if data.get("budget") else "",
        )
        if part
    )
    return _build_from_description(description, deadline=data.get("deadline", ""), budget=data.get("budget", ""))
