# Telegram-бот портфолио

Бот-портфолио Константина для Telegram-ботов, автоматизации и Python-разработки. Основной сценарий ведет клиента к оформлению заказа через Kwork и помогает подготовить понятное ТЗ.

## Возможности

- главное меню с разделами портфолио
- услуги, примеры работ, цены, процесс, FAQ
- сбор краткого ТЗ одним сообщением
- локальное авто-составление ТЗ без платных AI API
- отправка предварительного ТЗ администратору по `ADMIN_ID`
- админ-панель только для владельца бота
- уведомления о письмах Kwork через IMAP только админу
- синхронизация реальных публичных отзывов Kwork
- PostgreSQL на Railway или SQLite локально

## Переменные окружения

Заполните переменные в `.env` локально или в Railway Variables:

```env
BOT_TOKEN=
ADMIN_ID=

KWORK_PROFILE_URL=
KWORK_BOT_SERVICE_URL=
KWORK_REVIEWS_URL=
REVIEWS_SYNC_INTERVAL=21600

DATABASE_URL=
SQLITE_PATH=bot_data.sqlite3

KWORK_EMAIL_IMAP_HOST=imap.gmail.com
KWORK_EMAIL_IMAP_PORT=993
KWORK_EMAIL_LOGIN=
KWORK_EMAIL_PASSWORD=
KWORK_EMAIL_FOLDER=INBOX
KWORK_EMAIL_FROM_FILTER=kwork
KWORK_EMAIL_CHECK_INTERVAL=60

TELEGRAM_PROXY_URL=
```

`ADMIN_ID` - ваш Telegram ID. Только этот пользователь видит админ-панель и получает приватные уведомления.

`KWORK_BOT_SERVICE_URL` - ссылка на конкретную услугу Kwork, например страницу кворка с созданием Telegram-бота.

`KWORK_REVIEWS_URL` - публичная страница Kwork, откуда бот пробует подтянуть реальные отзывы. Если отзывов нет, раздел честно показывает, что отзывов пока нет.

## Запуск локально

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Railway

1. Залейте проект на GitHub.
2. Создайте сервис в Railway из GitHub-репозитория.
3. Добавьте PostgreSQL и убедитесь, что `DATABASE_URL` доступен сервису.
4. Добавьте переменные окружения.
5. Запустите деплой.

`Procfile` уже настроен:

```text
worker: python main.py
```

## Отзывы

Бот не добавляет фейковые отзывы. Файл `reviews.json` пустой и не используется для автозаполнения.

Отзывы показываются только если они уже есть в базе после синхронизации Kwork или были добавлены администратором вручную как реальные.

Ручная синхронизация для администратора:

```text
/sync_reviews
```

## Админ-команды

```text
/status
/last_tz
/sync_reviews
/add_review 5 | Клиент Kwork | Telegram-бот | Реальный текст отзыва
```

Админ-команды и админ-кнопки проверяют `ADMIN_ID`, поэтому обычный пользователь не сможет открыть приватную панель через callback или команду.
