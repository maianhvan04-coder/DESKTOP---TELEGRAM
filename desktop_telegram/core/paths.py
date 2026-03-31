from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_runtime_root() -> Path:
    """
    Thư mục chạy hiện tại của app:
    - Khi chạy source: thư mục project (chứa main.py, .env)
    - Khi chạy exe: thư mục chứa file DesktopTelegram.exe
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent

    # desktop_telegram/core/paths.py -> ../../
    return Path(__file__).resolve().parents[2]


def get_bundle_root() -> Path:
    """
    Thư mục bundle của PyInstaller, dùng cho file tĩnh nếu sau này có assets.
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def get_env_file() -> Path:
    """
    File .env:
    - Khi chạy source: nằm cạnh main.py
    - Khi chạy exe: nằm cạnh file .exe
    """
    return get_runtime_root() / ".env"


def get_app_data_dir(app_name: str = "TelegramDesktopTool") -> Path:
    """
    Nơi lưu dữ liệu ghi/đọc thật của app trên Windows.
    Ví dụ:
    C:\\Users\\<user>\\AppData\\Roaming\\TelegramDesktopTool
    """
    base = os.getenv("APPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Roaming")

    path = Path(base) / app_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sessions_dir(app_name: str = "TelegramDesktopTool") -> Path:
    path = get_app_data_dir(app_name) / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir(app_name: str = "TelegramDesktopTool") -> Path:
    path = get_app_data_dir(app_name) / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_dir(app_name: str = "TelegramDesktopTool") -> Path:
    path = get_app_data_dir(app_name) / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_assets_dir() -> Path:
    return get_bundle_root() / "assets"