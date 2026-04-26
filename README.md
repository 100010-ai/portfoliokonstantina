# Telegram-бот портфолио

Профессиональный Telegram-бот-визитка для Python-разработчика. Бот показывает услуги, примеры работ, цены, FAQ и помогает клиенту подготовить краткое ТЗ для оформления заказа через Kwork.

## Возможности

- Главное меню с inline-кнопками
- Разделы: обо мне, услуги, примеры работ, цены, процесс, FAQ
- Разделы для заказа и инструкции по оформлению через Kwork
- Форма через FSM: тип бота, функции, срок, бюджет
- Генерация краткого ТЗ для отправки при заказе на Kwork
- Отправка предварительного ТЗ администратору, если указан `ADMIN_ID`
- Предупреждение, что условия, оплата и переписка по заказу проходят через Kwork
- Команды `/start`, `/menu`, `/help`
- Обработчик неизвестных сообщений
- Логирование и базовая обработка ошибок

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
KWORK_PROFILE_URL=https://kwork.ru/user/your_login
KWORK_BOT_SERVICE_URL=https://kwork.ru/your_service_url
TELEGRAM_PROXY_URL=
```

Где:

- `BOT_TOKEN` — токен бота из BotFather
- `ADMIN_ID` — ваш Telegram ID, куда будут приходить предварительные ТЗ
- `KWORK_PROFILE_URL` — ссылка на ваш профиль Kwork
- `KWORK_BOT_SERVICE_URL` — ссылка на услугу по разработке Telegram-ботов
- `TELEGRAM_PROXY_URL` — необязательный HTTP/SOCKS-прокси для доступа к Bot API

Узнать свой Telegram ID можно через специальных ботов вроде `@userinfobot`.

Примеры прокси:

```env
TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
TELEGRAM_PROXY_URL=http://127.0.0.1:8080
```

## Запуск

```bash
python main.py
```

После запуска откройте своего бота в Telegram и отправьте команду `/start`.

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
keyboards.py     # inline-клавиатуры и callback-константы
texts.py         # все тексты сообщений
handlers.py      # команды, кнопки, FSM краткого ТЗ и ошибки
requirements.txt # зависимости
.env.example     # пример переменных окружения
README.md        # инструкция запуска
```
