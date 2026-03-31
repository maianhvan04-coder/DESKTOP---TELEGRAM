from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem

from desktop_telegram.services.crawl_service import CrawlService


class CrawlLogsPanel(QWidget):
    def __init__(self, crawl_service: CrawlService) -> None:
        super().__init__()
        self.crawl_service = crawl_service

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.reload()

    def reload(self) -> None:
        items = self.crawl_service.list_logs()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Chat ID", "Day", "Fetched", "Status"])
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(str(item.get("chatId", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(item.get("dayKey", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.get("totalFetched", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.get("status", ""))))