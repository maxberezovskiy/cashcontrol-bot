from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Токен бота из @BotFather
    BOT_TOKEN: str

    # Базовый URL backend API, напр. http://backend:8000/api/v1 (в docker) или http://localhost:8000/api/v1
    BACKEND_URL: str = "http://backend:8000/api/v1"

    # Общий секрет с backend для сервисных endpoint-ов /telegram/link и /telegram/token
    BOT_API_SECRET: str = "change-me-bot-secret"

    # Имя бота (без @) — нужно только для генерации deep-link в подсказках
    BOT_USERNAME: str | None = None

    # Валюта по умолчанию для быстрых операций
    DEFAULT_CURRENCY: str = "RUB"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
