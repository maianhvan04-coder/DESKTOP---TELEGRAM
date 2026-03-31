from __future__ import annotations

from datetime import datetime
from desktop_telegram.db.mongo import get_db


class MessageService:
    def __init__(self) -> None:
        self._db = get_db()

    def list_by_day(self, chat_id: str, day_key: str, keyword: str | None = None, sender_id: str | None = None) -> list[dict]:
        query: dict = {
            "chatId": chat_id,
            "dayKey": day_key,
        }
        if keyword:
            query["text"] = {"$regex": keyword, "$options": "i"}
        if sender_id:
            query["senderId"] = sender_id

        items = list(self._db.messages.find(query).sort("date", 1))
        for item in items:
            item["_id"] = str(item["_id"])
        return items

    def upsert_message(self, data: dict) -> None:
        payload = dict(data)
        payload["createdAt"] = payload.get("createdAt") or datetime.utcnow()

        self._db.messages.update_one(
            {"chatId": payload["chatId"], "messageId": payload["messageId"]},
            {"$set": payload},
            upsert=True,
        )