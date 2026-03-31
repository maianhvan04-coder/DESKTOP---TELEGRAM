from __future__ import annotations

from datetime import datetime
from typing import Any

from telethon import errors
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.messages import (
    CheckChatInviteRequest,
    ImportChatInviteRequest,
)
from telethon.tl.types import ChatInviteAlready
from telethon.utils import get_peer_id

from desktop_telegram.db.mongo import get_db
from desktop_telegram.services.auth_service import AuthService


class TrackedGroupService:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth = auth_service
        self._db = get_db()

    def _current_account(self) -> dict:
        status = self._auth.get_status()
        if not isinstance(status, dict) or not status.get("authorized"):
            raise RuntimeError("Chưa đăng nhập Telegram.")

        user = status.get("user") or {}
        account_id = str(user.get("id") or "").strip()
        if not account_id:
            raise RuntimeError("Không lấy được Telegram account id.")

        full_name = " ".join(
            [x for x in [user.get("first_name"), user.get("last_name")] if x]
        ).strip()

        return {
            "accountId": account_id,
            "username": user.get("username"),
            "phone": user.get("phone"),
            "displayName": full_name or user.get("username") or user.get("phone") or account_id,
        }

    def list_groups(self) -> list[dict]:
        account = self._current_account()
        items = list(
            self._db.tracked_groups
            .find({"ownerAccountId": account["accountId"]})
            .sort("updatedAt", -1)
        )
        for item in items:
            item["_id"] = str(item["_id"])
        return items

    def add_public_group(self, value: str) -> dict:
        """
        Hỗ trợ:
        - @username / username
        - chatId dạng số: -100..., hoặc id thường
        """
        client = self._auth._require_client()
        self._auth.connect()

        value = value.strip()
        if not value:
            raise RuntimeError("Vui lòng nhập chatId hoặc username.")

        if self._looks_like_chat_id(value):
            chat = self._auth._loop.run_until_complete(
                self._resolve_chat_by_id(client, value)
            )
            return self._save_group_doc(
                title=getattr(chat, "title", value),
                chat_id=self._to_storage_chat_id(chat),
                username=getattr(chat, "username", None),
                invite_link=None,
                group_type="PUBLIC",
            )

        username = value.replace("@", "").strip()
        if not username:
            raise RuntimeError("Username không hợp lệ.")

        result = self._auth._loop.run_until_complete(
            client(ResolveUsernameRequest(username=username))
        )

        if not result.chats:
            raise RuntimeError("Không tìm thấy group public.")

        chat = result.chats[0]
        return self._save_group_doc(
            title=getattr(chat, "title", username),
            chat_id=self._to_storage_chat_id(chat),
            username=getattr(chat, "username", None) or username,
            invite_link=None,
            group_type="PUBLIC",
        )

    def add_private_group(self, invite_link: str) -> dict:
        client = self._auth._require_client()
        self._auth.connect()

        raw_link = invite_link.strip()
        if not raw_link:
            raise RuntimeError("Invite link là bắt buộc.")

        code = self._extract_invite_code(raw_link)
        if not code:
            raise RuntimeError("Invite link không hợp lệ.")

        try:
            invite_info = self._auth._loop.run_until_complete(
                client(CheckChatInviteRequest(code))
            )

            if isinstance(invite_info, ChatInviteAlready):
                chat = invite_info.chat
            else:
                result = self._auth._loop.run_until_complete(
                    client(ImportChatInviteRequest(code))
                )
                chats = getattr(result, "chats", None) or []
                if not chats:
                    raise RuntimeError("Không join được private group.")
                chat = chats[0]

        except errors.UserAlreadyParticipantError:
            invite_info = self._auth._loop.run_until_complete(
                client(CheckChatInviteRequest(code))
            )
            if not isinstance(invite_info, ChatInviteAlready):
                raise RuntimeError(
                    "Tài khoản đã ở trong group nhưng không lấy được thông tin group."
                )
            chat = invite_info.chat

        except errors.InviteHashExpiredError:
            raise RuntimeError("Invite link đã hết hạn.")

        except errors.InviteHashInvalidError:
            raise RuntimeError("Invite link không hợp lệ.")

        except Exception as exc:
            raise RuntimeError(str(exc))

        return self._save_group_doc(
            title=getattr(chat, "title", "Private group"),
            chat_id=self._to_storage_chat_id(chat),
            username=getattr(chat, "username", None),
            invite_link=raw_link,
            group_type="PRIVATE",
        )

    def toggle_active(self, chat_id: str, is_active: bool) -> None:
        account = self._current_account()
        self._db.tracked_groups.update_one(
            {
                "ownerAccountId": account["accountId"],
                "chatId": str(chat_id),
            },
            {
                "$set": {
                    "isActive": is_active,
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

    def delete_group(self, chat_id: str) -> None:
        account = self._current_account()
        self._db.tracked_groups.delete_one(
            {
                "ownerAccountId": account["accountId"],
                "chatId": str(chat_id),
            }
        )

    def _save_group_doc(
        self,
        *,
        title: str,
        chat_id: str,
        username: str | None,
        invite_link: str | None,
        group_type: str,
    ) -> dict:
        account = self._current_account()
        now = datetime.utcnow()
        chat_id = str(chat_id)

        query = {
            "ownerAccountId": account["accountId"],
            "chatId": chat_id,
        }

        self._db.tracked_groups.update_one(
            query,
            {
                "$set": {
                    "ownerAccountId": account["accountId"],
                    "ownerUsername": account.get("username"),
                    "ownerPhone": account.get("phone"),
                    "ownerDisplayName": account.get("displayName"),
                    "title": title,
                    "chatId": chat_id,
                    "username": username,
                    "inviteLink": invite_link,
                    "type": group_type,
                    "isActive": True,
                    "updatedAt": now,
                },
                "$setOnInsert": {
                    "lastCrawledDay": None,
                    "meta": {},
                    "createdAt": now,
                },
            },
            upsert=True,
        )

        saved = self._db.tracked_groups.find_one(query)
        if saved:
            saved["_id"] = str(saved["_id"])
            return saved

        return {
            "ownerAccountId": account["accountId"],
            "ownerUsername": account.get("username"),
            "ownerPhone": account.get("phone"),
            "ownerDisplayName": account.get("displayName"),
            "title": title,
            "chatId": chat_id,
            "username": username,
            "inviteLink": invite_link,
            "type": group_type,
            "isActive": True,
            "lastCrawledDay": None,
            "meta": {},
            "createdAt": now,
            "updatedAt": now,
        }

    def _looks_like_chat_id(self, value: str) -> bool:
        value = value.strip()
        if not value:
            return False
        if value.startswith("-"):
            return value[1:].isdigit()
        return value.isdigit()

    async def _resolve_chat_by_id(self, client: Any, raw_chat_id: str) -> Any:
        raw_chat_id = raw_chat_id.strip()
        normalized_digits = raw_chat_id.lstrip("-")
        normalized_minus_100 = (
            raw_chat_id if raw_chat_id.startswith("-100") else f"-100{normalized_digits}"
        )

        dialogs = await client.get_dialogs(limit=None)

        for dialog in dialogs:
            entity = dialog.entity

            candidates = {
                str(getattr(entity, "id", "")),
            }

            try:
                candidates.add(str(get_peer_id(entity)))
            except Exception:
                pass

            if raw_chat_id in candidates:
                return entity
            if normalized_digits in candidates:
                return entity
            if normalized_minus_100 in candidates:
                return entity

        raise RuntimeError(
            "Không tìm thấy group theo chatId. Hãy chắc group này đã xuất hiện trong tài khoản Telegram đang đăng nhập."
        )

    def _to_storage_chat_id(self, chat: Any) -> str:
        try:
            return str(get_peer_id(chat))
        except Exception:
            return str(getattr(chat, "id"))

    def _extract_invite_code(self, invite_link: str) -> str:
        value = invite_link.strip()

        prefixes = (
            "https://t.me/+",
            "http://t.me/+",
            "t.me/+",
            "https://telegram.me/+",
            "http://telegram.me/+",
            "telegram.me/+",
            "https://t.me/joinchat/",
            "http://t.me/joinchat/",
            "t.me/joinchat/",
            "https://telegram.me/joinchat/",
            "http://telegram.me/joinchat/",
            "telegram.me/joinchat/",
        )

        for prefix in prefixes:
            if value.startswith(prefix):
                value = value[len(prefix):]
                break

        value = value.strip().strip("/")
        value = value.split("?")[0].strip()
        value = value.replace("+", "").strip()

        return value