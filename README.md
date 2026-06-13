# CashControl Telegram Bot

Telegram-бот для CashControl. Отдельный сервис на **aiogram 3** + **httpx**, работает через
backend HTTP API (`/api/v1`) — так же, как и веб-фронтенд. Использует long polling
(публичный HTTPS-endpoint не требуется).

## Возможности

- 💰 `/balance` — баланс по всем счетам с итогом по валютам
- 🏦 `/accounts` — список счетов
- ➕ `/add` — пошаговое добавление дохода/расхода (тип → сумма → счёт → категория → описание)
- 🧾 `/last` — последние 10 операций
- 🔗 `/link <код>` — привязка Telegram к аккаунту CashControl
- 🚫 `/unlink` — отвязка
- ❓ `/help` — справка

Также доступно нижнее меню-клавиатура (Добавить / Баланс / Операции / Счета).

## Как работает авторизация

Бот **не хранит пароли**. Привязка — по одноразовому коду:

1. В веб-приложении: **Настройки → Подключить Telegram** → генерируется код (живёт 10 минут).
2. В боте: `/link КОД` (или переход по deep-link `https://t.me/<bot>?start=КОД`).
3. Backend сохраняет `telegram_id` у пользователя.

Дальше бот получает JWT-токены пользователя через сервисный endpoint `POST /api/v1/telegram/token`
(защищён общим секретом `BOT_API_SECRET`) и вызывает обычные user-эндпоинты от его имени.

## Переменные окружения

См. `.env.example`:

| Переменная       | Описание                                                        |
|------------------|-----------------------------------------------------------------|
| `BOT_TOKEN`      | Токен от [@BotFather](https://t.me/BotFather)                   |
| `BACKEND_URL`    | Базовый URL API (`http://backend:8000/api/v1` в docker)         |
| `BOT_API_SECRET` | Общий секрет с backend (должен совпадать с backend `.env`)      |
| `BOT_USERNAME`   | Имя бота без `@` (опционально, для deep-link)                   |

## Локальный запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить BOT_TOKEN и BOT_API_SECRET
python -m app.main
```

Либо через общий `docker compose up --build bot` из репозитория `cashcontrol-backend`
(бот описан как сервис `bot`, образ собирается из `../cashcontrol-bot`).

## Деплой

CI/CD аналогичен backend/frontend: push в `main` → сборка образа → GHCR
(`ghcr.io/<owner>/cashcontrol-bot:latest` и `:sha`) → деплой на VM по SSH с обновлением
`BOT_TAG` в `/opt/cashcontrol/.env`. Релиз гейтится окружением `production`.
Откат — запуск workflow с нужным SHA в поле `tag`.
