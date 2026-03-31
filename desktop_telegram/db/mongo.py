from __future__ import annotations

from pymongo import MongoClient
from desktop_telegram.core.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_db():
    uri = settings.mongodb_uri
    db_name = uri.rsplit("/", 1)[-1].split("?")[0]
    return get_client()[db_name]