from __future__ import annotations

from pymongo import ASCENDING

from desktop_telegram.db.mongo import get_db


def ensure_indexes() -> None:
    db = get_db()

    tracked_groups = db.tracked_groups
    messages = db.messages
    crawl_logs = db.crawl_logs

    # Xóa unique index cũ theo chatId nếu còn tồn tại
    index_info = tracked_groups.index_information()
    for index_name, info in index_info.items():
        keys = info.get("key", [])
        is_unique = info.get("unique", False)

        if keys == [("chatId", 1)] and is_unique:
            tracked_groups.drop_index(index_name)

    # Mỗi account chỉ được theo dõi 1 group đúng 1 lần
    tracked_groups.create_index(
        [("ownerAccountId", ASCENDING), ("chatId", ASCENDING)],
        unique=True,
        name="ownerAccountId_1_chatId_1",
    )

    # Hỗ trợ lọc danh sách group theo tài khoản
    tracked_groups.create_index(
        [("ownerAccountId", ASCENDING), ("isActive", ASCENDING)],
        name="ownerAccountId_1_isActive_1",
    )

    tracked_groups.create_index(
        [("ownerAccountId", ASCENDING)],
        name="ownerAccountId_1",
    )

    messages.create_index(
        [("chatId", ASCENDING), ("messageId", ASCENDING)],
        unique=True,
        name="chatId_1_messageId_1",
    )
    messages.create_index(
        [("chatId", ASCENDING), ("dayKey", ASCENDING)],
        name="chatId_1_dayKey_1",
    )
    messages.create_index(
        [("chatId", ASCENDING), ("senderId", ASCENDING)],
        name="chatId_1_senderId_1",
    )

    crawl_logs.create_index(
        [("chatId", ASCENDING), ("dayKey", ASCENDING)],
        unique=True,
        name="chatId_1_dayKey_1",
    )