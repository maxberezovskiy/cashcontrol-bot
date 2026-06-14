"""Асинхронный клиент к CashControl backend.

Бот не хранит пароли пользователей. Привязка выполняется одноразовым кодом,
после чего бот получает JWT-токены пользователя через сервисный endpoint
/telegram/token (авторизация общим секретом BOT_API_SECRET) и кэширует их
в памяти по telegram_id.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import settings


class ApiError(Exception):
    """Ошибка обращения к backend с человекочитаемым сообщением."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotLinkedError(ApiError):
    """Telegram-аккаунт не привязан к пользователю CashControl."""


@dataclass
class _Token:
    access_token: str
    # unix-время, после которого считаем токен протухшим (с запасом)
    expires_at: float


def _extract_detail(response: httpx.Response, fallback: str) -> str:
    try:
        data = response.json()
    except Exception:
        return fallback
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:
        first = detail[0]
        if isinstance(first, dict) and "msg" in first:
            return str(first["msg"])
    return fallback


class CashControlClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.BACKEND_URL, timeout=15.0)
        # telegram_id -> _Token
        self._tokens: dict[int, _Token] = {}

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _send(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Единая точка вызова backend: транспортные ошибки → понятный ApiError."""
        try:
            return await self._client.request(method, path, **kwargs)
        except httpx.RequestError as e:
            raise ApiError("Сервис временно недоступен, попробуйте позже") from e

    # --- Сервисные вызовы (X-Bot-Secret) ---

    async def link(self, *, code: str, telegram_id: int) -> dict:
        resp = await self._send(
            "POST",
            "/telegram/link",
            json={"code": code, "telegram_id": telegram_id},
            headers={"X-Bot-Secret": settings.BOT_API_SECRET},
        )
        if resp.status_code == 400:
            raise ApiError(_extract_detail(resp, "Неверный или просроченный код"), 400)
        if resp.status_code >= 400:
            raise ApiError(_extract_detail(resp, "Не удалось привязать аккаунт"), resp.status_code)
        # После привязки нужен свежий токен
        self._tokens.pop(telegram_id, None)
        return resp.json()

    async def _fetch_token(self, telegram_id: int) -> str:
        resp = await self._send(
            "POST",
            "/telegram/token",
            json={"telegram_id": telegram_id},
            headers={"X-Bot-Secret": settings.BOT_API_SECRET},
        )
        if resp.status_code == 404:
            raise NotLinkedError("Аккаунт не привязан", 404)
        if resp.status_code >= 400:
            raise ApiError(_extract_detail(resp, "Ошибка авторизации"), resp.status_code)
        access = resp.json()["access_token"]
        # Короткий кэш (60с): после веб-/unlink бот перестаёт действовать в пределах минуты,
        # т.к. перезапрос /telegram/token вернёт 404. Backend-токен тоже короткоживущий.
        self._tokens[telegram_id] = _Token(access_token=access, expires_at=time.time() + 60)
        return access

    async def _token(self, telegram_id: int, *, force: bool = False) -> str:
        cached = self._tokens.get(telegram_id)
        if not force and cached and cached.expires_at > time.time():
            return cached.access_token
        return await self._fetch_token(telegram_id)

    async def is_linked(self, telegram_id: int) -> bool:
        try:
            await self._token(telegram_id)
            return True
        except NotLinkedError:
            return False

    async def authorize(self, telegram_id: int) -> None:
        """Гарантирует наличие токена в кэше (раняя проверка + одно сетевое обращение).

        Полезно перед параллельными запросами, чтобы они не минтили токен наперегонки.
        Бросает NotLinkedError, если аккаунт не привязан.
        """
        await self._token(telegram_id)

    async def unlink(self, telegram_id: int) -> None:
        # Требует валидной привязки — иначе токен не получить
        resp = await self._request(telegram_id, "POST", "/telegram/unlink")
        if resp.status_code >= 400:
            raise ApiError(_extract_detail(resp, "Не удалось отвязать аккаунт"), resp.status_code)
        self._tokens.pop(telegram_id, None)

    # --- Вызовы от имени пользователя (Bearer JWT) ---

    async def _request(self, telegram_id: int, method: str, path: str, **kwargs) -> httpx.Response:
        token = await self._token(telegram_id)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self._send(method, path, headers=headers, **kwargs)
        if resp.status_code == 401:
            # токен мог протухнуть — обновляем один раз
            token = await self._token(telegram_id, force=True)
            headers = {"Authorization": f"Bearer {token}"}
            resp = await self._send(method, path, headers=headers, **kwargs)
        return resp

    async def get_accounts(self, telegram_id: int) -> list[dict]:
        resp = await self._request(telegram_id, "GET", "/accounts/")
        if resp.status_code >= 400:
            raise ApiError(_extract_detail(resp, "Не удалось получить счета"), resp.status_code)
        return resp.json()

    async def get_categories(self, telegram_id: int) -> list[dict]:
        resp = await self._request(telegram_id, "GET", "/categories/")
        if resp.status_code >= 400:
            raise ApiError(_extract_detail(resp, "Не удалось получить категории"), resp.status_code)
        return resp.json()

    async def get_transactions(
        self, telegram_id: int, *, limit: int = 10, account_id: int | None = None
    ) -> list[dict]:
        params: dict = {"limit": limit}
        if account_id is not None:
            params["account_id"] = account_id
        resp = await self._request(telegram_id, "GET", "/transactions/", params=params)
        if resp.status_code >= 400:
            raise ApiError(_extract_detail(resp, "Не удалось получить операции"), resp.status_code)
        return resp.json()

    async def create_transaction(self, telegram_id: int, payload: dict) -> dict:
        resp = await self._request(telegram_id, "POST", "/transactions/", json=payload)
        if resp.status_code >= 400:
            raise ApiError(_extract_detail(resp, "Не удалось создать операцию"), resp.status_code)
        return resp.json()


client = CashControlClient()
