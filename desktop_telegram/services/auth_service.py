from __future__ import annotations

import asyncio
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from desktop_telegram.core.config import settings
from desktop_telegram.core.paths import get_sessions_dir


class AuthService:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._client: TelegramClient | None = None
        self._phone: str | None = None
        self._ensure_client()

    def _ensure_client(self) -> None:
        if not settings.has_telegram_credentials:
            self._client = None
            return

        session_file: Path = get_sessions_dir() / "telegram_user"
        self._client = TelegramClient(
            str(session_file),
            settings.telegram_api_id,
            settings.telegram_api_hash,
            loop=self._loop,
        )

    def credentials_ready(self) -> bool:
        return settings.has_telegram_credentials

    def _require_client(self) -> TelegramClient:
        if not settings.has_telegram_credentials:
            raise RuntimeError("Thiếu TELEGRAM_API_ID / TELEGRAM_API_HASH trong .env.")
        if self._client is None:
            self._ensure_client()
        if self._client is None:
            raise RuntimeError("Telegram client is not available.")
        return self._client

    def connect(self) -> None:
        client = self._require_client()
        if not client.is_connected():
            self._loop.run_until_complete(client.connect())

    def send_phone(self, phone: str) -> None:
        phone = phone.strip()
        if not phone:
            raise RuntimeError("Số điện thoại không được để trống.")

        client = self._require_client()
        self.connect()
        self._phone = phone
        self._loop.run_until_complete(client.send_code_request(phone))

    def send_code(self, code: str) -> str:
        code = code.strip()
        if not code:
            raise RuntimeError("Mã xác thực không được để trống.")

        client = self._require_client()
        self.connect()

        if not self._phone:
            raise RuntimeError("Phone number was not submitted yet.")

        try:
            self._loop.run_until_complete(client.sign_in(self._phone, code))
            return "READY"
        except SessionPasswordNeededError:
            return "PASSWORD"

    def send_password(self, password: str) -> str:
        password = password.strip()
        if not password:
            raise RuntimeError("Mật khẩu 2FA không được để trống.")

        client = self._require_client()
        self.connect()
        self._loop.run_until_complete(client.sign_in(password=password))
        return "READY"

    def get_me(self):
        client = self._require_client()
        self.connect()
        return self._loop.run_until_complete(client.get_me())

    def is_authorized(self) -> bool:
        client = self._require_client()
        self.connect()
        return self._loop.run_until_complete(client.is_user_authorized())

    def logout(self) -> None:
        client = self._require_client()
        self.connect()

        try:
            self._loop.run_until_complete(client.log_out())
        finally:
            try:
                if client.is_connected():
                    self._loop.run_until_complete(client.disconnect())
            except Exception:
                pass

            self._client = None
            self._phone = None
            self._ensure_client()

    def get_status(self) -> dict:
        if not settings.has_telegram_credentials:
            return {
                "ok": False,
                "authorized": False,
                "step": "MISSING_CREDENTIALS",
                "message": "Thiếu TELEGRAM_API_ID / TELEGRAM_API_HASH trong .env.",
                "user": None,
            }

        try:
            authorized = self.is_authorized()
            me = self.get_me() if authorized else None
            return {
                "ok": True,
                "authorized": authorized,
                "step": "READY" if authorized else "PHONE",
                "message": "Authorized" if authorized else "Not authorized",
                "user": {
                    "id": getattr(me, "id", None),
                    "first_name": getattr(me, "first_name", None),
                    "last_name": getattr(me, "last_name", None),
                    "username": getattr(me, "username", None),
                    "phone": getattr(me, "phone", None),
                } if me else None,
            }
        except Exception as exc:
            return {
                "ok": False,
                "authorized": False,
                "step": "ERROR",
                "message": str(exc),
                "user": None,
            }