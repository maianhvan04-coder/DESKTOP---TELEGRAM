from __future__ import annotations

from datetime import datetime
from typing import Any

from desktop_telegram.core.day import to_day_key
from desktop_telegram.db.mongo import get_db
from desktop_telegram.services.auth_service import AuthService
from desktop_telegram.services.message_service import MessageService


class CrawlService:
    def __init__(self, auth_service: AuthService, message_service: MessageService) -> None:
        self._auth = auth_service
        self._messages = message_service
        self._db = get_db()

    def crawl_chat_for_day(self, chat_id: str, target_day: str | None = None) -> dict:
        client = self._auth._require_client()
        self._auth.connect()

        started_at = datetime.utcnow()
        count = 0

        entity = self._auth._loop.run_until_complete(client.get_entity(int(chat_id)))

        async def _collect() -> list[dict]:
            collected: list[dict] = []

            async for msg in client.iter_messages(entity, limit=300):
                if not msg.date:
                    continue

                day_key = to_day_key(msg.date)
                if target_day and day_key != target_day:
                    continue

                sender_info = await self._extract_sender_info(msg)

                collected.append(
                    {
                        "chatId": str(chat_id),
                        "messageId": str(msg.id),
                        "date": int(msg.date.timestamp()),
                        "dayKey": day_key,
                        "senderId": sender_info["senderId"],
                        "senderType": sender_info["senderType"],
                        "senderName": sender_info["senderName"],
                        "text": msg.message or "",
                        "hasMedia": msg.media is not None,
                        "mediaType": type(msg.media).__name__ if msg.media else None,
                        "raw": sender_info["raw"],
                    }
                )

            return collected

        messages = self._auth._loop.run_until_complete(_collect())

        for item in messages:
            self._messages.upsert_message(item)
            count += 1

        finished_at = datetime.utcnow()
        day_key = target_day or (messages[0]["dayKey"] if messages else None)

        if day_key:
            self._db.crawl_logs.update_one(
                {"chatId": str(chat_id), "dayKey": day_key},
                {
                    "$set": {
                        "chatId": str(chat_id),
                        "dayKey": day_key,
                        "totalFetched": count,
                        "startedAt": started_at,
                        "finishedAt": finished_at,
                        "status": "SUCCESS",
                    }
                },
                upsert=True,
            )

            self._db.tracked_groups.update_one(
                {"chatId": str(chat_id)},
                {"$set": {"lastCrawledDay": day_key, "updatedAt": finished_at}},
            )

        return {
            "ok": True,
            "chatId": str(chat_id),
            "dayKey": day_key,
            "totalFetched": count,
        }

    async def _extract_sender_info(self, msg: Any) -> dict:
        sender = getattr(msg, "sender", None)
        if sender is None:
            try:
                sender = await msg.get_sender()
            except Exception:
                sender = None

        sender_id = getattr(msg, "sender_id", None)
        if sender_id is None and sender is not None:
            sender_id = getattr(sender, "id", None)

        sender_name: str | None = None
        sender_type: str | None = None
        raw: dict[str, Any] = {}

        if sender is not None:
            first_name = getattr(sender, "first_name", None)
            last_name = getattr(sender, "last_name", None)
            username = getattr(sender, "username", None)
            title = getattr(sender, "title", None)

            if first_name or last_name or username:
                sender_type = "USER"
                sender_name = " ".join(
                    x for x in [first_name, last_name] if x
                ).strip() or username

                raw = {
                    "id": str(getattr(sender, "id", "") or ""),
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "title": None,
                    "type": type(sender).__name__,
                }

            elif title:
                sender_type = "CHAT"
                sender_name = title

                raw = {
                    "id": str(getattr(sender, "id", "") or ""),
                    "first_name": None,
                    "last_name": None,
                    "username": getattr(sender, "username", None),
                    "title": title,
                    "type": type(sender).__name__,
                }

            else:
                sender_type = type(sender).__name__.upper()
                raw = {
                    "id": str(getattr(sender, "id", "") or ""),
                    "first_name": None,
                    "last_name": None,
                    "username": getattr(sender, "username", None),
                    "title": getattr(sender, "title", None),
                    "type": type(sender).__name__,
                }

        if not sender_type and sender_id:
            sender_type = "USER"

        return {
            "senderId": str(sender_id) if sender_id is not None else None,
            "senderType": sender_type,
            "senderName": sender_name,
            "raw": raw,
        }

    def list_logs(self) -> list[dict]:
        items = list(self._db.crawl_logs.find().sort("finishedAt", -1))
        for item in items:
            item["_id"] = str(item["_id"])
        return items