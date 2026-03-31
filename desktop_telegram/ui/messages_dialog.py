from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem

from desktop_telegram.services.message_service import MessageService


class MessagesDialog(QDialog):
    def __init__(self, message_service: MessageService, chat_id: str, day_key: str) -> None:
        super().__init__()
        self.setWindowTitle(f"Messages - {day_key}")
        self.resize(900, 600)

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        layout.addWidget(self.table)

        items = message_service.list_by_day(chat_id, day_key)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Sender", "Text", "Media"])
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(str(item.get("date", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(item.get("senderId", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.get("text", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.get("mediaType", ""))))