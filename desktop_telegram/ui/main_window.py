from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QLabel,
)

from desktop_telegram.core.config import settings
from desktop_telegram.services.auth_service import AuthService
from desktop_telegram.services.tracked_group_service import TrackedGroupService
from desktop_telegram.services.message_service import MessageService
from desktop_telegram.services.crawl_service import CrawlService
from desktop_telegram.ui.auth_panel import AuthPanel
from desktop_telegram.ui.tracked_groups_panel import TrackedGroupsPanel
from desktop_telegram.ui.crawl_logs_panel import CrawlLogsPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(settings.app_name)
        self.resize(1200, 800)

        self.auth_service = AuthService()
        self.message_service = MessageService()
        self.tracked_group_service = TrackedGroupService(self.auth_service)
        self.crawl_service = CrawlService(self.auth_service, self.message_service)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not self.auth_service.credentials_ready():
            warning = QLabel("Thiếu TELEGRAM_API_ID / TELEGRAM_API_HASH trong .env")
            warning.setContentsMargins(12, 12, 12, 12)
            layout.addWidget(warning)

        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        layout.addWidget(self.tabs)

        self.auth_panel = AuthPanel(self.auth_service)
        self.tracked_groups_panel = TrackedGroupsPanel(
            self.tracked_group_service,
            self.message_service,
            self.crawl_service,
        )
        self.crawl_logs_panel = CrawlLogsPanel(self.crawl_service)

        self.tabs.addTab(self.auth_panel, "Auth")
        self.tabs.addTab(self.tracked_groups_panel, "Tracked groups")
        self.tabs.addTab(self.crawl_logs_panel, "Crawl logs")

        self.auth_panel.login_success.connect(self.go_to_tracked_groups)
        self.tracked_groups_panel.logged_out.connect(self.go_to_login)

        try:
            status = self.auth_service.get_status()
            if self._is_ready_status(status):
                self.go_to_tracked_groups()
            else:
                self.go_to_login()
        except Exception:
            self.go_to_login()

    def _is_ready_status(self, status: object) -> bool:
        if isinstance(status, dict):
            if bool(status.get("authorized")):
                return True
            return str(status.get("step", "")).upper() == "READY"
        return str(status).upper() == "READY"

    def go_to_tracked_groups(self) -> None:
        try:
            self.tracked_groups_panel.reload_groups()
        except Exception:
            pass
        self.tabs.setCurrentWidget(self.tracked_groups_panel)

    def go_to_login(self) -> None:
        try:
            self.auth_panel.reset_for_login()
        except Exception:
            pass
        self.tabs.setCurrentWidget(self.auth_panel)