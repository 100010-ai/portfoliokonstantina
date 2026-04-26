# Telegram-бот портфолио

Профессиональный Telegram-бот-визитка для Python-разработчика. Бот показывает услуги, примеры работ, цены, FAQ и помогает клиенту подготовить краткое ТЗ для оформления заказа через Kwork.

## Возможности

- Главное меню с inline-кнопками
- Разделы: обо мне, услуги, примеры работ, цены, процесс, FAQ
- Разделы для заказа и инструкции по оформлению через Kwork
- Форма через FSM: тип бота, функции, срок, бюджет
- Локальное авто-составление понятного ТЗ для отправки при заказе на Kwork
- PostgreSQL/SQLite база для ТЗ, отзывов и обработанных email-уведомлений
- Отправка предварительного ТЗ администратору, если указан `ADMIN_ID`
- Уведомления админу о сообщениях, заказах и отзывах Kwork через IMAP
- Публичный раздел отзывов
- Предупреждение, что условия, оплата и переписка по заказу проходят через Kwork
- Команды `/start`, `/menu`, `/help`
- Админ-команда `/status`
- Обработчик неизвестных сообщений
- Логирование и базовая обработка ошибок
- Оптимизация чата: бот редактирует меню и удаляет лишние сообщения формы ТЗ

## Установка

Требуется Python 3.11 или новее.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

## Настройка .env

Создайте файл `.env` в корне проекта по примеру `.env.example`:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_ID=123456789
DATABASE_URL=
SQLITE_PATH=bot_data.sqlite3
KWORK_PROFILE_URL=https://kwork.ru/user/your_login
KWORK_BOT_SERVICE_URL=https://kwork.ru/your_service_url
KWORK_REVIEWS_URL=
REVIEWS_SYNC_INTERVAL=21600
TELEGRAM_PROXY_URL=
REVIEWS_JSON=
KWORK_EMAIL_IMAP_HOST=
KWORK_EMAIL_IMAP_PORT=993
KWORK_EMAIL_LOGIN=
KWORK_EMAIL_PASSWORD=
KWORK_EMAIL_FOLDER=INBOX
KWORK_EMAIL_FROM_FILTER=kwork
KWORK_EMAIL_CLIENT_KEYWORDS=новое сообщение,сообщение от,вам написал,покупатель,клиент,личное сообщение,new message,buyer,customer
KWORK_EMAIL_ORDER_KEYWORDS=новый заказ,заказ создан,заказ оплачен,начинайте работу,поступил заказ,оформил заказ,new order,order created,order paid
KWORK_EMAIL_REVIEW_KEYWORDS=новый отзыв,оставил отзыв,отзыв по заказу,оценил заказ,review,feedback
KWORK_EMAIL_PROMO_KEYWORDS=скидка,скидки,акция,распродажа,промокод,бонус,дайджест,подборка,новости kwork,реклама,рекомендации,вебинар,обучение,sale,discount,promo,newsletter,digest
KWORK_EMAIL_CHECK_INTERVAL=60
```

Где:

- `BOT_TOKEN` — токен бота из BotFather
- `ADMIN_ID` — ваш Telegram ID, куда будут приходить предварительные ТЗ
- `DATABASE_URL` — PostgreSQL URL на Railway; если пусто, используется SQLite
- `SQLITE_PATH` — путь к локальной SQLite базе для разработки
- `KWORK_PROFILE_URL` — ссылка на ваш профиль Kwork
- `KWORK_BOT_SERVICE_URL` — ссылка на услугу по разработке Telegram-ботов
- `KWORK_REVIEWS_URL` — публичная страница Kwork, с которой бот пробует синхронизировать отзывы
- `REVIEWS_SYNC_INTERVAL` — интервал фоновой синхронизации отзывов в секундах
- `TELEGRAM_PROXY_URL` — необязательный HTTP/SOCKS-прокси для доступа к Bot API
- `REVIEWS_JSON` — необязательный JSON со стартовыми отзывами для Railway
- `KWORK_EMAIL_IMAP_HOST` — IMAP-сервер почты, куда приходят уведомления Kwork
- `KWORK_EMAIL_LOGIN` — email-логин
- `KWORK_EMAIL_PASSWORD` — пароль приложения от почты
- `KWORK_EMAIL_FROM_FILTER` — фильтр отправителя, по умолчанию `kwork`
- `KWORK_EMAIL_CLIENT_KEYWORDS` — слова, по которым письмо считается клиентским
- `KWORK_EMAIL_ORDER_KEYWORDS` — слова, по которым письмо считается заказом
- `KWORK_EMAIL_REVIEW_KEYWORDS` — слова, по которым письмо считается отзывом
- `KWORK_EMAIL_PROMO_KEYWORDS` — слова, по которым письмо считается рекламой и пропускается

## База Данных

Бот хранит важные данные в базе:

- собранные ТЗ клиентов;
- обработанные email-уведомления Kwork, чтобы после рестарта не было дублей;
- публичные отзывы для раздела `Отзывы`.

На Railway лучше подключить PostgreSQL:

1. В Railway добавьте PostgreSQL plugin/service.
2. Railway сам создаст переменную `DATABASE_URL`.
3. Убедитесь, что `DATABASE_URL` доступна сервису с ботом.
4. Перезапустите сервис.

Если `DATABASE_URL` пустая, бот использует SQLite-файл `bot_data.sqlite3`. Для локальной разработки это нормально, но на Railway SQLite может потеряться при пересоздании окружения.

Админ может добавить отзыв командой:

```text
/add_review 5 | Клиент Kwork | Telegram-бот | Текст отзыва
```

После этого отзыв сохраняется в базе и показывается всем пользователям в разделе `Отзывы`.

Отзывы также можно синхронизировать с публичной страницы Kwork:

```env
KWORK_REVIEWS_URL=https://kwork.ru/user/your_login
REVIEWS_SYNC_INTERVAL=21600
```

Бот периодически открывает публичную страницу, ищет отзывы в структурированных данных страницы и сохраняет новые отзывы в базу. Ручной запуск:

```text
/sync_reviews
```

Важно: это не официальный API Kwork. Если Kwork не отдаёт отзывы в HTML/JSON-LD публичной страницы или загружает их только через закрытый JavaScript/API, синхронизация не найдёт отзывы. Логин и пароль от Kwork бот не использует.

Узнать свой Telegram ID можно через специальных ботов вроде `@userinfobot`.

Примеры прокси:

```env
TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
TELEGRAM_PROXY_URL=http://127.0.0.1:8080
```

## Уведомления Kwork

У Kwork нет удобного публичного webhook для сообщений, поэтому бот умеет проверять email-уведомления Kwork через IMAP и пересылать админу только письма, похожие на сообщения клиентов, новые заказы, отзывы или важные клиентские события.

1. Включите email-уведомления в аккаунте Kwork.
2. Включите IMAP в настройках почты.
3. Создайте пароль приложения для почты, если используется Gmail, Yandex или Mail.ru.
4. Заполните IMAP-настройки в `.env`.

Примеры:

```env
# Gmail
KWORK_EMAIL_IMAP_HOST=imap.gmail.com
KWORK_EMAIL_IMAP_PORT=993
KWORK_EMAIL_LOGIN=your_email@gmail.com
KWORK_EMAIL_PASSWORD=app_password
```

```env
# Yandex
KWORK_EMAIL_IMAP_HOST=imap.yandex.ru
KWORK_EMAIL_IMAP_PORT=993
KWORK_EMAIL_LOGIN=your_email@yandex.ru
KWORK_EMAIL_PASSWORD=app_password
```

```env
# Mail.ru
KWORK_EMAIL_IMAP_HOST=imap.mail.ru
KWORK_EMAIL_IMAP_PORT=993
KWORK_EMAIL_LOGIN=your_email@mail.ru
KWORK_EMAIL_PASSWORD=app_password
```

Бот проверяет непрочитанные письма от отправителя по фильтру `KWORK_EMAIL_FROM_FILTER`, анализирует тему и текст письма, пропускает скидки, акции, промокоды, дайджесты и другие рассылки. Админу приходит короткое уведомление: тип события, тема, отправитель, дата, фрагмент письма и ссылка на Kwork.

Если Kwork присылает письма с другой формулировкой темы, добавьте нужные слова в `KWORK_EMAIL_CLIENT_KEYWORDS`. Если какая-то реклама всё же проходит, добавьте ее маркеры в `KWORK_EMAIL_PROMO_KEYWORDS`.

## Авто-составление ТЗ

Форма `Собрать ТЗ` не просто показывает ответы клиента. Модуль `tz_builder.py` локально анализирует тип бота и функции, после чего собирает более понятное ТЗ:

- цель проекта
- основной функционал
- базовая логика работы
- уведомления
- пожелания клиента
- срок и бюджет
- вопросы, которые нужно уточнить перед стартом

Внешние AI-сервисы не используются: логика работает локально по правилам и ключевым словам, поэтому не требует токенов и не отправляет данные третьим сервисам.

Для экономии ресурсов и аккуратного чата бот принимает одно описание задачи, ограничивает слишком длинный ввод, удаляет пользовательское сообщение формы после обработки и сохраняет готовое ТЗ в базу.

## Запуск

```bash
python main.py
```

После запуска откройте своего бота в Telegram и отправьте команду `/start`.

## Railway

Проект готов к запуску на Railway:

- `Procfile` запускает worker-команду `python main.py`
- `railway.json` задаёт start command и restart policy
- `.gitignore` исключает `.env`, виртуальное окружение и кэш Python

Для деплоя на Railway:

1. Загрузите проект на GitHub.
2. Создайте сервис в Railway из GitHub-репозитория.
3. Перенесите значения из `.env` в Railway Variables.
4. Убедитесь, что `BOT_TOKEN` и `ADMIN_ID` заполнены.
5. Оставьте `TELEGRAM_PROXY_URL` пустым, если Railway напрямую подключается к Telegram Bot API.

После запуска в логах Railway должны быть строки:

```text
Bot started as @...
Polling is starting now
```

Команда `/status` доступна только администратору и показывает, заполнены ли Kwork-ссылки и включены ли email-уведомления.

## Диагностика

Если бот запустился, но не отвечает:

1. Остановите `main.py`.
2. Запустите диагностику:

```bash
python diagnose.py
```

3. Отправьте `/start` боту, пока диагностика ждёт обновления.

Скрипт покажет username бота из токена, webhook и последние входящие сообщения.

## Структура проекта

```text
main.py          # запуск бота
diagnose.py      # диагностика токена, webhook и входящих сообщений
config.py        # загрузка переменных окружения
database.py      # PostgreSQL/SQLite хранение данных
keyboards.py     # inline-клавиатуры и callback-константы
texts.py         # все тексты сообщений
handlers.py      # команды, кнопки, FSM краткого ТЗ и ошибки
kwork_email_notifier.py # IMAP-уведомления о письмах Kwork
reviews.py       # вывод публичных отзывов из базы
reviews.json     # стартовые отзывы для первичного заполнения базы
tz_builder.py    # локальное авто-составление ТЗ
requirements.txt # зависимости
.env.example     # пример переменных окружения
README.md        # инструкция запуска
Procfile         # worker-команда для Railway
railway.json     # настройки деплоя Railway
```
