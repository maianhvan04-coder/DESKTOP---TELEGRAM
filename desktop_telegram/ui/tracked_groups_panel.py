from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from PySide6.QtCore import (
    QDate,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QAction, QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop_telegram.services.crawl_service import CrawlService
from desktop_telegram.services.message_service import MessageService
from desktop_telegram.services.tracked_group_service import TrackedGroupService


def safe_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def initials(value: str) -> str:
    parts = [x for x in value.strip().split() if x]
    if not parts:
        return "TG"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[1][0]}".upper()


def today_day_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def display_day(day_key: str | None) -> str:
    if not day_key:
        return "--"
    if day_key == today_day_key():
        return "Hôm nay"
    try:
        return datetime.strptime(day_key, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return day_key


def day_key_to_qdate(day_key: str | None) -> QDate:
    if not day_key:
        return QDate.currentDate()
    date = QDate.fromString(day_key, "yyyy-MM-dd")
    return date if date.isValid() else QDate.currentDate()


def unix_to_hhmm(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value)).strftime("%H:%M")
    except Exception:
        return "--"


def build_sender_name(item: dict) -> str:
    direct_name = safe_str(item.get("senderName")).strip()
    if direct_name and direct_name.lower() != "unknown":
        return direct_name

    raw = item.get("raw")
    if isinstance(raw, dict):
        first_name = safe_str(raw.get("first_name")).strip()
        last_name = safe_str(raw.get("last_name")).strip()
        full_name = " ".join(x for x in [first_name, last_name] if x).strip()
        if full_name:
            return full_name

        for key in ("title", "name", "username", "author", "sender_name", "senderName"):
            value = safe_str(raw.get(key)).strip()
            if value and value.lower() != "unknown":
                return value

    return ""


def normalize_message_text(value: Any) -> str:
    text = safe_str(value, "--")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text if text.strip() else "--"


class DatePickerPill(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._date = QDate.currentDate()

        self.setObjectName("DatePickerPill")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        self.setFixedWidth(170)

        self.setStyleSheet(
            """
            QWidget#DatePickerPill {
                background: #FFFFFF;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
            }
            QWidget#DatePickerPill:hover {
                border: 1px solid #BFC6D4;
                background: #FCFCFD;
            }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 0, 16, 0)
        root.setSpacing(0)

        self.text_label = QLabel()
        self.text_label.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Preferred,
        )
        self.text_label.setStyleSheet(
            """
            QLabel {
                color: #101828;
                font-size: 13px;
                font-weight: 800;
                border: none;
                background: transparent;
            }
            """
        )

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setPixmap(self._build_calendar_icon())
        self.icon_label.setStyleSheet("background: transparent; border: none;")

        root.addStretch(1)
        root.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addSpacing(10)
        root.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addStretch(1)

        self.popup = QDialog(
            self,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self.popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.popup.setStyleSheet(
            """
            QDialog {
                background: #FFFFFF;
                border: 1px solid #EAECF0;
                border-radius: 16px;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #F8FAFC;
            }
            QCalendarWidget QToolButton {
                color: #101828;
                font-weight: 700;
                border: none;
                border-radius: 10px;
                padding: 6px 8px;
                background: transparent;
            }
            QCalendarWidget QToolButton:hover {
                background: #F2F4F7;
            }
            QCalendarWidget QMenu {
                background: white;
                border: 1px solid #E5E7EB;
            }
            QCalendarWidget QSpinBox {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 2px 6px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                selection-background-color: #2D9CDB;
                selection-color: white;
                color: #111827;
                outline: 0;
            }
            """
        )

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(10, 10, 10, 10)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setSelectedDate(self._date)
        self.calendar.clicked.connect(self._on_calendar_clicked)

        popup_layout.addWidget(self.calendar)
        self._refresh_text()

    def _build_calendar_icon(self) -> QPixmap:
        size = 20
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        main = QColor("#667085")

        painter.setBrush(main)
        painter.drawRoundedRect(2, 4, 16, 14, 4, 4)

        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(4, 6, 12, 10, 2, 2)

        painter.setBrush(main)
        painter.drawRect(4, 8, 12, 2)

        painter.drawRoundedRect(6, 1, 2, 6, 1, 1)
        painter.drawRoundedRect(12, 1, 2, 6, 1, 1)

        dot = 2
        painter.drawEllipse(6, 11, dot, dot)
        painter.drawEllipse(9, 11, dot, dot)
        painter.drawEllipse(12, 11, dot, dot)
        painter.drawEllipse(6, 14, dot, dot)
        painter.drawEllipse(9, 14, dot, dot)
        painter.drawEllipse(12, 14, dot, dot)

        painter.end()
        return pixmap

    def _refresh_text(self) -> None:
        self.text_label.setText(self._date.toString("dd/MM/yyyy"))

    def _on_calendar_clicked(self, date: QDate) -> None:
        self.setDate(date)
        self.popup.hide()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.show_popup()
        event.accept()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
            Qt.Key.Key_Down,
        ):
            self.show_popup()
            event.accept()
            return
        super().keyPressEvent(event)

    def show_popup(self) -> None:
        self.calendar.setSelectedDate(self._date)
        self.popup.adjustSize()
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.popup.move(pos.x(), pos.y() + 6)
        self.popup.show()

    def date(self) -> QDate:
        return self._date

    def setDate(self, date: QDate) -> None:
        self._date = date
        self.calendar.setSelectedDate(date)
        self._refresh_text()


class AvatarBadge(QLabel):
    def __init__(
        self,
        text: str,
        size: int = 42,
        bg: str = "#FFEFB0",
        fg: str = "#9A6B00",
    ) -> None:
        super().__init__(text)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border-radius: {size // 2}px;
                font-size: 13px;
                font-weight: 800;
            }}
            """
        )


class GroupListItemWidget(QFrame):
    clicked = Signal(dict)

    def __init__(self, group: dict, selected: bool = False) -> None:
        super().__init__()
        self.group = group
        self.selected = selected
        self._build()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit(self.group)
        super().mousePressEvent(event)

    def _build(self) -> None:
        title = (
            safe_str(self.group.get("title"))
            or safe_str(self.group.get("username"))
            or safe_str(self.group.get("chatId"), "Unknown group")
        )
        active = bool(self.group.get("isActive", True))
        meta = f"{safe_str(self.group.get('chatId'))} · {'Đang theo dõi' if active else 'Tạm dừng'}"

        self.setStyleSheet(
            f"""
            QFrame {{
                background: {"#EAF7FF" if self.selected else "transparent"};
                border: none;
                border-radius: 18px;
            }}
            QFrame:hover {{
                background: {"#DDF1FF" if self.selected else "#F8FAFC"};
            }}
            """
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        avatar = AvatarBadge(
            initials(title),
            44,
            "#D9F2FF" if self.selected else "#EAF4FF",
            "#16638A",
        )
        root.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

        info_wrap = QWidget()
        info_wrap.setStyleSheet("background: transparent;")
        info_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        info = QVBoxLayout(info_wrap)
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(4)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: 800;
                color: #101828;
            }
            """
        )

        meta_label = QLabel(meta)
        meta_label.setWordWrap(True)
        meta_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                font-size: 12px;
                color: #667085;
            }
            """
        )

        info.addWidget(title_label)
        info.addWidget(meta_label)

        root.addWidget(info_wrap, 1)


class MessageBubble(QFrame):
    def __init__(self, item: dict) -> None:
        super().__init__()
        self.item = item

        self.sender_name = build_sender_name(self.item)
        self.sender_id = safe_str(self.item.get("senderId")).strip()
        self.text_value = normalize_message_text(self.item.get("text"))
        self.time_text = unix_to_hhmm(self.item.get("date"))

        self._build()

    def _build(self) -> None:
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        avatar_text = initials(self.sender_name or self.sender_id or "TG")
        avatar = AvatarBadge(avatar_text, 48, "#CFEFFD", "#1570A6")
        root.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

        self.right_wrap = QWidget()
        self.right_wrap.setStyleSheet("background: transparent;")
        self.right_wrap.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        right = QVBoxLayout(self.right_wrap)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)

        sender_row = QHBoxLayout()
        sender_row.setContentsMargins(0, 0, 0, 0)
        sender_row.setSpacing(8)

        display_name = self.sender_name or self.sender_id or "Unknown"
        show_sender_id = bool(self.sender_id) and self.sender_id != display_name

        sender_name_label = QLabel(display_name)
        sender_name_label.setTextFormat(Qt.TextFormat.PlainText)
        sender_name_label.setStyleSheet(
            """
            QLabel {
                color: #0F172A;
                font-size: 14px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
            """
        )
        sender_row.addWidget(sender_name_label, 0)

        if show_sender_id:
            sender_id_label = QLabel(self.sender_id)
            sender_id_label.setTextFormat(Qt.TextFormat.PlainText)
            sender_id_label.setStyleSheet(
                """
                QLabel {
                    color: #8CA0B8;
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }
                """
            )
            sender_row.addWidget(sender_id_label, 0)

        sender_row.addStretch(1)

        self.bubble = QFrame()
        self.bubble.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.bubble.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border-radius: 20px;
                border: 1px solid rgba(15, 23, 42, 0.06);
            }
            """
        )

        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(18, 14, 18, 10)
        bubble_layout.setSpacing(10)

        self.text_label = QLabel(self.text_value)
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.text_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        self.text_label.setStyleSheet(
            """
            QLabel {
                color: #0F172A;
                font-size: 15px;
                background: transparent;
                border: none;
            }
            """
        )

        self.footer = QLabel(self.time_text)
        self.footer.setTextFormat(Qt.TextFormat.PlainText)
        self.footer.setStyleSheet(
            """
            QLabel {
                color: #98A2B3;
                font-size: 11px;
                background: transparent;
                border: none;
            }
            """
        )

        bubble_layout.addWidget(self.text_label)
        bubble_layout.addWidget(self.footer, 0, Qt.AlignmentFlag.AlignRight)

        right.addLayout(sender_row)
        right.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignLeft)

        root.addWidget(self.right_wrap, 1)

        self._update_bubble_width()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._update_bubble_width()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_bubble_width()

    def _estimate_text_width(self, max_width: int) -> int:
        lines = self.text_value.splitlines() or [self.text_value]
        fm = self.text_label.fontMetrics()

        widest = 0
        for line in lines:
            current = line if line.strip() else " "
            widest = max(widest, fm.horizontalAdvance(current))

        width = widest + 14
        width = max(80, width)
        width = min(width, max_width)
        return width

    def _update_bubble_width(self) -> None:
        available = self.right_wrap.width()
        if available <= 0:
            return

        max_text_width = max(220, min(1100, available - 60))
        text_width = self._estimate_text_width(max_text_width)

        footer_width = self.footer.fontMetrics().horizontalAdvance(self.time_text) + 6
        inner_width = max(text_width, footer_width)

        self.text_label.setFixedWidth(text_width)
        self.bubble.setFixedWidth(inner_width + 36)


class SummaryPill(QFrame):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.setStyleSheet(
            """
            QFrame {
                background: #F7F8FB;
                border: 1px solid #EEF2F6;
                border-radius: 14px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(
            """
            QLabel {
                color: #475467;
                font-size: 13px;
                background: transparent;
            }
            """
        )
        layout.addWidget(label)


class AddGroupDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode = "CHAT_ID"
        self.setWindowTitle("Thêm group")
        self.resize(560, 300)
        self._build()

    def _build(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background: #FFFFFF;
            }
            QLabel#chip {
                background: #EEF4FF;
                color: #444CE7;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton {
                border-radius: 14px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 700;
                border: none;
            }
            QPlainTextEdit {
                border: 1px solid #E4E7EC;
                border-radius: 16px;
                background: #F8FAFC;
                padding: 10px 12px;
                font-size: 13px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        chip = QLabel("Thêm mới")
        chip.setObjectName("chip")
        chip.setFixedWidth(76)

        title = QLabel("Thêm group theo dõi")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #101828;")

        desc = QLabel("Chọn cách thêm bằng chatId/@username hoặc private invite link.")
        desc.setStyleSheet("font-size: 13px; color: #667085;")

        switch_row = QHBoxLayout()
        switch_row.setSpacing(10)

        self.chat_btn = QPushButton("Chat ID / Username")
        self.link_btn = QPushButton("Invite link")
        self.chat_btn.clicked.connect(lambda: self._set_mode("CHAT_ID"))
        self.link_btn.clicked.connect(lambda: self._set_mode("INVITE_LINK"))

        switch_row.addWidget(self.chat_btn)
        switch_row.addWidget(self.link_btn)

        self.input_label = QLabel("Chat ID / Username")
        self.input_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #344054;")

        self.input = QPlainTextEdit()
        self.input.setFixedHeight(100)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        ok_btn = QPushButton("Thêm group")
        ok_btn.setStyleSheet("background: #0EA5E9; color: white;")
        ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("Hủy")
        cancel_btn.setStyleSheet("background: white; color: #344054; border: 1px solid #D0D5DD;")
        cancel_btn.clicked.connect(self.reject)

        action_row.addWidget(ok_btn)
        action_row.addWidget(cancel_btn)
        action_row.addStretch(1)

        root.addWidget(chip)
        root.addWidget(title)
        root.addWidget(desc)
        root.addLayout(switch_row)
        root.addWidget(self.input_label)
        root.addWidget(self.input)
        root.addLayout(action_row)

        self._set_mode("CHAT_ID")

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        active = "background: #0EA5E9; color: white;"
        normal = "background: #F8FAFC; color: #475467; border: 1px solid #E4E7EC;"

        self.chat_btn.setStyleSheet(active if mode == "CHAT_ID" else normal)
        self.link_btn.setStyleSheet(active if mode == "INVITE_LINK" else normal)

        if mode == "CHAT_ID":
            self.input_label.setText("Chat ID / Username")
            self.input.setPlaceholderText("Ví dụ: -1001234567890 hoặc @ten_nhom")
        else:
            self.input_label.setText("Private invite link")
            self.input.setPlaceholderText("Ví dụ: https://t.me/+xxxxx")

    def get_value(self) -> tuple[str, str]:
        return self.mode, self.input.toPlainText().strip()


class TrackedGroupsPanel(QWidget):
    logged_out = Signal()

    def __init__(
        self,
        tracked_group_service: TrackedGroupService,
        message_service: MessageService,
        crawl_service: CrawlService,
    ) -> None:
        super().__init__()

        self.tracked_group_service = tracked_group_service
        self.message_service = message_service
        self.crawl_service = crawl_service

        self.groups: list[dict] = []
        self.current_group: dict | None = None
        self.current_messages: list[dict] = []

        self.ai_expanded = True
        self.ai_width = 370
        self._ai_target_open = True
        self.ai_animation: QParallelAnimationGroup | None = None

        self._build_ui()
        self._setup_ai_animation()
        self.reload_groups()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #EEF1F4;
                color: #101828;
                font-family: "Segoe UI";
            }
            QFrame#RootShell {
                background: transparent;
                border: none;
            }
            QFrame#LeftSidebar {
                background: #F3F4F6;
                border: 1px solid #E5E7EB;
                border-radius: 28px;
            }
            QFrame#RightShell {
                background: #FFFFFF;
                border: 1px solid #E7ECF1;
                border-radius: 24px;
            }
            QFrame#HeaderCard {
                background: #FFFFFF;
                border-bottom: 1px solid #EEF2F6;
                border-top-left-radius: 24px;
                border-top-right-radius: 24px;
            }
            QFrame#FilterCard {
                background: #FFFFFF;
                border-bottom: 1px solid #EEF2F6;
            }
            QFrame#ChatArea {
                background: #E5EBF2;
                border-bottom-left-radius: 24px;
            }
            QWidget#MessagesContainer {
                background: transparent;
            }
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #E4E7EC;
                border-radius: 22px;
                padding: 11px 14px;
                font-size: 13px;
                color: #101828;
            }
            QLineEdit:focus {
                border: 1px solid #84CAFF;
            }
            QPushButton {
                border: none;
                border-radius: 22px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 700;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                border: none;
                margin: 0 0 8px 0;
            }
            QMenu {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 12px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background: #F2F4F7;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 12px;
                margin: 8px 4px 8px 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #B7C3D1;
                min-height: 46px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #95A4B8;
            }
            QScrollBar::handle:vertical:pressed {
                background: #6B7B8F;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 0px 8px 4px 8px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #B7C3D1;
                min-width: 46px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #95A4B8;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #6B7B8F;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        root = QFrame()
        root.setObjectName("RootShell")
        outer.addWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        self._build_left_sidebar(root_layout)

        right_shell = QFrame()
        right_shell.setObjectName("RightShell")
        root_layout.addWidget(right_shell, 1)

        right_layout = QVBoxLayout(right_shell)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._build_header(right_layout)
        self._build_filters(right_layout)
        self._build_body(right_layout)

    def _build_left_sidebar(self, parent: QHBoxLayout) -> None:
        sidebar = QFrame()
        sidebar.setObjectName("LeftSidebar")
        sidebar.setFixedWidth(330)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)

        self.group_search = QLineEdit()
        self.group_search.setPlaceholderText("Search")
        self.group_search.setFixedHeight(50)
        self.group_search.setStyleSheet(
            """
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
                padding: 0 18px;
                font-size: 13px;
                color: #101828;
            }
            QLineEdit:focus {
                border: 1px solid #BFC6D4;
                background: #FFFFFF;
            }
            """
        )
        self.group_search.textChanged.connect(self._render_group_list_filtered)

        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("↻")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setFixedSize(50, 50)
        self.refresh_btn.setStyleSheet(
            """
            QToolButton {
                background: #FFFFFF;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
                color: #667085;
                font-size: 18px;
                font-weight: 700;
            }
            QToolButton:hover {
                background: #F9FAFB;
                border: 1px solid #BFC6D4;
            }
            QToolButton:pressed {
                background: #F2F4F7;
            }
            """
        )
        self.refresh_btn.clicked.connect(self.reload_groups)

        self.sidebar_menu_btn = QPushButton("⋮")
        self.sidebar_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_menu_btn.setFixedSize(50, 50)
        self.sidebar_menu_btn.setStyleSheet(
            """
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
                color: #667085;
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                background: #F9FAFB;
                border: 1px solid #BFC6D4;
            }
            QPushButton:pressed {
                background: #F2F4F7;
            }
            """
        )
        self.sidebar_menu_btn.clicked.connect(self.show_sidebar_menu)

        top.addWidget(self.group_search, 1)
        top.addWidget(self.refresh_btn, 0)
        top.addWidget(self.sidebar_menu_btn, 0)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #EAECF0; border: none;")

        self.group_list = QListWidget()
        self.group_list.setFrameShape(QFrame.Shape.NoFrame)
        self.group_list.setSpacing(0)

        bottom_divider = QFrame()
        bottom_divider.setFixedHeight(1)
        bottom_divider.setStyleSheet("background: #EAECF0; border: none;")

        layout.addLayout(top)
        layout.addWidget(divider)
        layout.addWidget(self.group_list, 1)
        layout.addWidget(bottom_divider)

        parent.addWidget(sidebar, 0)

    def _build_header(self, parent: QVBoxLayout) -> None:
        header = QFrame()
        header.setObjectName("HeaderCard")
        header.setStyleSheet(
            """
            QFrame#HeaderCard {
                background: #FFFFFF;
                border-bottom: 1px solid #EEF2F6;
                border-top-left-radius: 24px;
                border-top-right-radius: 24px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
            """
        )

        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        self.header_avatar = AvatarBadge("NN", 42, "#FFF1B3", "#9A6B00")

        info_wrap = QFrame()
        info_wrap.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: none;
            }
            """
        )

        info_col = QVBoxLayout(info_wrap)
        info_col.setContentsMargins(0, 0, 0, 0)
        info_col.setSpacing(2)

        self.group_title = QLabel("Chưa có group")
        self.group_title.setAutoFillBackground(False)
        self.group_title.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-size: 17px;
                font-weight: 800;
                color: #101828;
            }
            """
        )

        self.group_meta = QLabel("--")
        self.group_meta.setAutoFillBackground(False)
        self.group_meta.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-size: 12px;
                color: #667085;
            }
            """
        )

        info_col.addWidget(self.group_title)
        info_col.addWidget(self.group_meta)

        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(12)
        left.addWidget(self.header_avatar, 0, Qt.AlignmentFlag.AlignTop)
        left.addWidget(info_wrap, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(10)

        self.crawl_btn = QPushButton("Crawl hôm nay")
        self.crawl_btn.setFixedHeight(50)
        self.crawl_btn.setStyleSheet(
            """
            QPushButton {
                background: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
                padding: 0 22px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #F9FAFB;
                border: 1px solid #BFC6D4;
            }
            QPushButton:pressed {
                background: #F2F4F7;
            }
            """
        )
        self.crawl_btn.clicked.connect(self.crawl_current_group)

        self.ai_btn = QPushButton("✨ AI ‹")
        self.ai_btn.setFixedHeight(50)
        self.ai_btn.setStyleSheet(
            """
            QPushButton {
                background: #F5EEFF;
                color: #7F56D9;
                border: none;
                border-radius: 25px;
                padding: 0 22px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #EFE7FF;
            }
            QPushButton:pressed {
                background: #E7DBFF;
            }
            """
        )
        self.ai_btn.clicked.connect(self.toggle_ai_panel)

        self.menu_btn = QPushButton("⋮")
        self.menu_btn.setFixedSize(50, 50)
        self.menu_btn.setStyleSheet(
            """
            QPushButton {
                background: #FFFFFF;
                color: #344054;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
                padding: 0;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #F9FAFB;
                border: 1px solid #BFC6D4;
            }
            QPushButton:pressed {
                background: #F2F4F7;
            }
            """
        )
        self.menu_btn.clicked.connect(self.show_header_menu)

        actions.addWidget(self.crawl_btn)
        actions.addWidget(self.ai_btn)
        actions.addWidget(self.menu_btn)

        layout.addLayout(left, 1)
        layout.addLayout(actions, 0)

        parent.addWidget(header)

    def _build_filters(self, parent: QVBoxLayout) -> None:
        filters = QFrame()
        filters.setObjectName("FilterCard")

        layout = QHBoxLayout(filters)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        self.date_edit = DatePickerPill()

        self.message_keyword = QLineEdit()
        self.message_keyword.setPlaceholderText("Lọc theo nội dung tin nhắn...")
        self.message_keyword.setFixedHeight(50)
        self.message_keyword.setStyleSheet(
            """
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
                padding: 0 18px;
                font-size: 13px;
                color: #101828;
            }
            QLineEdit:focus {
                border: 1px solid #BFC6D4;
                background: #FFFFFF;
            }
            """
        )

        self.message_sender = QLineEdit()
        self.message_sender.setPlaceholderText("Sender ID")
        self.message_sender.setFixedWidth(260)
        self.message_sender.setFixedHeight(50)
        self.message_sender.setStyleSheet(
            """
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D0D5DD;
                border-radius: 25px;
                padding: 0 18px;
                font-size: 13px;
                color: #101828;
            }
            QLineEdit:focus {
                border: 1px solid #BFC6D4;
                background: #FFFFFF;
            }
            """
        )

        self.load_btn = QPushButton("Lấy danh sách")
        self.load_btn.setFixedHeight(50)
        self.load_btn.setMinimumWidth(210)
        self.load_btn.setStyleSheet(
            """
            QPushButton {
                background: #2D9CDB;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 0 26px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #248DCA;
            }
            QPushButton:pressed {
                background: #1F7DB4;
            }
            """
        )
        self.load_btn.clicked.connect(self.load_messages)

        layout.addWidget(self.date_edit, 0)
        layout.addWidget(self.message_keyword, 1)
        layout.addWidget(self.message_sender, 0)
        layout.addWidget(self.load_btn, 0)

        parent.addWidget(filters)

    def _build_body(self, parent: QVBoxLayout) -> None:
        body = QFrame()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.chat_area = QFrame()
        self.chat_area.setObjectName("ChatArea")

        chat_layout = QVBoxLayout(self.chat_area)
        chat_layout.setContentsMargins(16, 12, 8, 12)
        chat_layout.setSpacing(0)

        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.messages_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.messages_scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
            """
        )

        self.messages_container = QWidget()
        self.messages_container.setObjectName("MessagesContainer")
        self.messages_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 18, 10)
        self.messages_layout.setSpacing(16)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.addItem(
            QSpacerItem(
                20,
                20,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )

        self.messages_scroll.setWidget(self.messages_container)
        chat_layout.addWidget(self.messages_scroll)

        self.ai_panel = QFrame()
        self.ai_panel.setMinimumWidth(self.ai_width)
        self.ai_panel.setMaximumWidth(self.ai_width)
        self.ai_panel.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border-left: 1px solid #EEF2F6;
                border-bottom-right-radius: 24px;
            }
            """
        )

        ai_layout = QVBoxLayout(self.ai_panel)
        ai_layout.setContentsMargins(16, 16, 16, 16)
        ai_layout.setSpacing(12)

        ai_top = QHBoxLayout()
        ai_top.setSpacing(8)

        chip = QLabel("✨ AI Summary")
        chip.setStyleSheet(
            """
            QLabel {
                background: #F3ECFF;
                color: #7F56D9;
                border-radius: 12px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            """
        )

        self.ai_close_btn = QPushButton("×")
        self.ai_close_btn.setFixedSize(34, 34)
        self.ai_close_btn.setStyleSheet(
            """
            QPushButton {
                background: #FFFFFF;
                color: #98A2B3;
                border: 1px solid #EAECF0;
                border-radius: 17px;
                padding: 0;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #F9FAFB;
            }
            """
        )
        self.ai_close_btn.clicked.connect(self.toggle_ai_panel)

        ai_top.addWidget(chip, 0, Qt.AlignmentFlag.AlignLeft)
        ai_top.addStretch(1)
        ai_top.addWidget(self.ai_close_btn, 0, Qt.AlignmentFlag.AlignRight)

        title = QLabel("Tóm tắt theo ngày")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #101828;")

        desc = QLabel("Bản tóm tắt gọn từ tin nhắn của ngày đang chọn.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #667085;")

        self.summary_btn = QPushButton("✨ Tóm tắt lại")
        self.summary_btn.setStyleSheet(
            """
            QPushButton {
                background: #7C3AED;
                color: white;
                border-radius: 16px;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background: #6D28D9;
            }
            """
        )
        self.summary_btn.clicked.connect(self.build_summary)

        self.summary_text = QLabel("Chưa có dữ liệu tóm tắt.")
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet(
            """
            QLabel {
                background: #F6F3FF;
                color: #475467;
                border-radius: 14px;
                padding: 12px;
                font-size: 13px;
            }
            """
        )

        highlight_title = QLabel("Điểm nổi bật")
        highlight_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #101828;")

        highlight_box = QFrame()
        highlight_box.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border: 1px solid #EAECF0;
                border-radius: 18px;
            }
            """
        )
        highlight_box_layout = QVBoxLayout(highlight_box)
        highlight_box_layout.setContentsMargins(10, 10, 10, 10)
        highlight_box_layout.setSpacing(0)

        self.highlights_scroll = QScrollArea()
        self.highlights_scroll.setWidgetResizable(True)
        self.highlights_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.highlights_container = QWidget()
        self.highlights_layout = QVBoxLayout(self.highlights_container)
        self.highlights_layout.setContentsMargins(0, 0, 0, 0)
        self.highlights_layout.setSpacing(10)
        self.highlights_layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        self.highlights_scroll.setWidget(self.highlights_container)
        highlight_box_layout.addWidget(self.highlights_scroll)

        ai_layout.addLayout(ai_top)
        ai_layout.addWidget(title)
        ai_layout.addWidget(desc)
        ai_layout.addWidget(self.summary_btn, 0, Qt.AlignmentFlag.AlignLeft)
        ai_layout.addWidget(self.summary_text)
        ai_layout.addWidget(highlight_title)
        ai_layout.addWidget(highlight_box, 1)

        body_layout.addWidget(self.chat_area, 1)
        body_layout.addWidget(self.ai_panel, 0)

        parent.addWidget(body, 1)

    def _setup_ai_animation(self) -> None:
        self.ai_animation = QParallelAnimationGroup(self)

        self.ai_min_anim = QPropertyAnimation(self.ai_panel, b"minimumWidth", self)
        self.ai_max_anim = QPropertyAnimation(self.ai_panel, b"maximumWidth", self)

        for anim in (self.ai_min_anim, self.ai_max_anim):
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.ai_animation.addAnimation(anim)

        self.ai_animation.finished.connect(self._on_ai_animation_finished)
        self._refresh_ai_button()

    def _refresh_ai_button(self) -> None:
        self.ai_btn.setText("✨ AI ‹" if self.ai_expanded else "✨ AI ›")

    def toggle_ai_panel(self) -> None:
        if self.ai_animation is None:
            return

        self._ai_target_open = not self.ai_expanded

        if self._ai_target_open:
            self.ai_panel.show()

        current_width = max(0, self.ai_panel.width())
        target_width = self.ai_width if self._ai_target_open else 0

        self.ai_min_anim.stop()
        self.ai_max_anim.stop()

        self.ai_min_anim.setStartValue(current_width)
        self.ai_min_anim.setEndValue(target_width)

        self.ai_max_anim.setStartValue(current_width)
        self.ai_max_anim.setEndValue(target_width)

        self.ai_animation.start()

    def _on_ai_animation_finished(self) -> None:
        self.ai_expanded = self._ai_target_open
        target_width = self.ai_width if self.ai_expanded else 0

        self.ai_panel.setMinimumWidth(target_width)
        self.ai_panel.setMaximumWidth(target_width)

        if self.ai_expanded:
            self.ai_panel.show()
        else:
            self.ai_panel.hide()

        self._refresh_ai_button()

    def current_day_key(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    def clear_layout_keep_last_spacer(self, layout: QVBoxLayout) -> None:
        while layout.count() > 1:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def build_empty_state_card(self, title_text: str, desc_text: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background: rgba(255, 255, 255, 0.88);
                border-radius: 24px;
            }
            """
        )
        card.setMinimumHeight(180)
        card.setMaximumHeight(220)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(card)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(title_text)
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        title.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #0F172A;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
            """
        )

        desc = QLabel(desc_text)
        desc.setTextFormat(Qt.TextFormat.PlainText)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setMaximumWidth(620)
        desc.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        desc.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                line-height: 1.45em;
                color: #667085;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
            """
        )

        root.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        root.addWidget(desc, 0, Qt.AlignmentFlag.AlignCenter)

        return card

    def _build_sidebar_menu(self) -> QMenu:
        menu = QMenu(self)

        account_action = QAction("Thông tin Telegram", self)
        account_action.triggered.connect(self.show_account_info)

        add_action = QAction("Thêm group", self)
        add_action.triggered.connect(self.show_add_dialog)

        logout_action = QAction("Đăng xuất Telegram", self)
        logout_action.triggered.connect(self.logout_telegram)

        menu.addAction(account_action)
        menu.addAction(add_action)
        menu.addSeparator()
        menu.addAction(logout_action)
        return menu

    def show_sidebar_menu(self) -> None:
        menu = self._build_sidebar_menu()
        pos = self.sidebar_menu_btn.mapToGlobal(self.sidebar_menu_btn.rect().bottomLeft())
        menu.exec(pos)

    def reload_groups(self) -> None:
        try:
            self.groups = self.tracked_group_service.list_groups()
        except Exception as exc:
            self.groups = []
            QMessageBox.critical(self, "Lỗi", str(exc))

        if self.current_group:
            current_chat_id = safe_str(self.current_group.get("chatId"))
            self.current_group = next(
                (g for g in self.groups if safe_str(g.get("chatId")) == current_chat_id),
                None,
            )

        if not self.current_group and self.groups:
            self.current_group = self.groups[0]

        self._render_group_list_filtered()

        if self.current_group:
            self.apply_selected_group(self.current_group)
        else:
            self.render_empty()

    def _render_group_list_filtered(self, *_args) -> None:
        if not hasattr(self, "group_list"):
            return

        q = self.group_search.text().strip().lower() if hasattr(self, "group_search") else ""

        if not q:
            items = self.groups
        else:
            items = []
            for g in self.groups:
                hay = " ".join(
                    [
                        safe_str(g.get("title")),
                        safe_str(g.get("username")),
                        safe_str(g.get("inviteLink")),
                        safe_str(g.get("chatId")),
                        safe_str(g.get("type")),
                    ]
                ).lower()
                if q in hay:
                    items.append(g)

        self.group_list.clear()

        current_chat_id = safe_str(self.current_group.get("chatId")) if self.current_group else ""

        for group in items:
            item = QListWidgetItem()
            widget = GroupListItemWidget(
                group,
                safe_str(group.get("chatId")) == current_chat_id,
            )
            widget.clicked.connect(self.apply_selected_group)
            item.setSizeHint(widget.sizeHint())
            self.group_list.addItem(item)
            self.group_list.setItemWidget(item, widget)

    def apply_selected_group(self, group: dict) -> None:
        self.current_group = group

        title = (
            safe_str(group.get("title"))
            or safe_str(group.get("username"))
            or safe_str(group.get("chatId"), "Unknown group")
        )
        meta = (
            f"{safe_str(group.get('chatId'))}  •  "
            f"{'Đang theo dõi' if bool(group.get('isActive', True)) else 'Tạm dừng'}  •  "
            f"Crawl gần nhất: {display_day(group.get('lastCrawledDay'))}"
        )

        self.group_title.setTextFormat(Qt.TextFormat.PlainText)
        self.group_meta.setTextFormat(Qt.TextFormat.PlainText)
        self.group_title.setText(title)
        self.group_meta.setText(meta)
        self.header_avatar.setText(initials(title))
        self.date_edit.setDate(day_key_to_qdate(group.get("lastCrawledDay")))

        self._render_group_list_filtered()
        self.load_messages()

    def render_empty(self) -> None:
        self.group_title.setTextFormat(Qt.TextFormat.PlainText)
        self.group_meta.setTextFormat(Qt.TextFormat.PlainText)
        self.group_title.setText("Chưa có group")
        self.group_meta.setText("Hãy thêm group hoặc chọn group đang theo dõi.")
        self.header_avatar.setText("TG")
        self.current_messages = []

        self.clear_layout_keep_last_spacer(self.messages_layout)

        empty_card = self.build_empty_state_card(
            "Chưa có dữ liệu",
            "Bạn thêm group rồi bấm lấy danh sách để xem tin nhắn.",
        )

        self.messages_layout.insertWidget(0, empty_card, 0, Qt.AlignmentFlag.AlignTop)
        self.summary_text.setText("Chưa có dữ liệu tóm tắt.")
        self.set_highlights([])

    def load_messages(self) -> None:
        if not self.current_group:
            self.render_empty()
            return

        chat_id = safe_str(self.current_group.get("chatId"))
        day_key = self.current_day_key()
        keyword = self.message_keyword.text().strip() or None
        sender_id = self.message_sender.text().strip() or None

        try:
            self.current_messages = self.message_service.list_by_day(
                chat_id,
                day_key,
                keyword=keyword,
                sender_id=sender_id,
            )
        except Exception as exc:
            self.current_messages = []
            QMessageBox.critical(self, "Lỗi", str(exc))

        self.render_messages()
        self.build_summary()

    def render_messages(self) -> None:
        self.clear_layout_keep_last_spacer(self.messages_layout)

        if not self.current_messages:
            empty = self.build_empty_state_card(
                "Chưa có tin nhắn",
                "Ngày này chưa có dữ liệu crawl hoặc bộ lọc đang không khớp.",
            )
            self.messages_layout.insertWidget(0, empty, 0, Qt.AlignmentFlag.AlignTop)
            return

        for idx, item in enumerate(self.current_messages):
            self.messages_layout.insertWidget(idx, MessageBubble(item))

    def build_summary(self) -> None:
        if not self.current_messages:
            self.summary_text.setText("Không có dữ liệu trong ngày đang chọn.")
            self.set_highlights([])
            return

        participants = Counter()
        texts: list[str] = []

        for msg in self.current_messages:
            sender = build_sender_name(msg) or safe_str(msg.get("senderId"), "Unknown")
            participants[sender] += 1

            text = safe_str(msg.get("text")).strip()
            if text:
                texts.append(text)

        people_text = ", ".join(
            [f"{name} ({count})" for name, count in participants.most_common(3)]
        )

        pieces = [f"Ngày {display_day(self.current_day_key())} có {len(self.current_messages)} tin nhắn."]
        if people_text:
            pieces.append(f"Người tham gia nổi bật: {people_text}.")
        if texts:
            pieces.append(f"Nội dung chủ yếu: {' | '.join(texts[:3])}")

        self.summary_text.setText(" ".join(pieces))

        highlights: list[str] = []
        for msg in self.current_messages[:10]:
            text = safe_str(msg.get("text")).strip()
            if not text:
                continue
            sender = build_sender_name(msg) or safe_str(msg.get("senderId"), "Unknown")
            clipped = text if len(text) <= 90 else text[:87] + "..."
            highlights.append(f"{unix_to_hhmm(msg.get('date'))} · {sender}: {clipped}")

        self.set_highlights(highlights)

    def set_highlights(self, items: list[str]) -> None:
        self.clear_layout_keep_last_spacer(self.highlights_layout)

        if not items:
            label = QLabel("Chưa có điểm nổi bật.")
            label.setStyleSheet("font-size: 13px; color: #667085;")
            self.highlights_layout.insertWidget(0, label)
            return

        for idx, text in enumerate(items):
            self.highlights_layout.insertWidget(idx, SummaryPill(text))

    def crawl_current_group(self) -> None:
        if not self.current_group:
            return

        try:
            result = self.crawl_service.crawl_chat_for_day(
                safe_str(self.current_group.get("chatId")),
                self.current_day_key(),
            )
            QMessageBox.information(
                self,
                "Crawl xong",
                f"Đã lấy {result.get('totalFetched', 0)} tin nhắn.",
            )
            self.reload_groups()
            self.load_messages()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def toggle_current_group(self) -> None:
        if not self.current_group:
            return

        try:
            chat_id = safe_str(self.current_group.get("chatId"))
            next_value = not bool(self.current_group.get("isActive", True))
            self.tracked_group_service.toggle_active(chat_id, next_value)
            self.reload_groups()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def delete_current_group(self) -> None:
        if not self.current_group:
            return

        title = safe_str(self.current_group.get("title"), "group")
        reply = QMessageBox.question(
            self,
            "Xóa group",
            f"Xóa '{title}' khỏi danh sách theo dõi?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.tracked_group_service.delete_group(
                safe_str(self.current_group.get("chatId"))
            )
            self.current_group = None
            self.reload_groups()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def show_add_dialog(self) -> None:
        dlg = AddGroupDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        mode, value = dlg.get_value()
        if not value:
            return

        try:
            if mode == "CHAT_ID":
                if value.startswith("@"):
                    value = value[1:]
                self.tracked_group_service.add_public_group(value)
            else:
                self.tracked_group_service.add_private_group(value)

            self.reload_groups()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def show_account_info(self) -> None:
        auth = getattr(self.tracked_group_service, "_auth", None)
        if auth is None:
            QMessageBox.information(self, "Telegram", "Không có auth service.")
            return

        try:
            status = auth.get_status()
            user = status.get("user") if isinstance(status, dict) else None
            if status.get("authorized") and user:
                full_name = " ".join(
                    [x for x in [user.get("first_name"), user.get("last_name")] if x]
                ).strip()
                username = user.get("username")
                phone = user.get("phone")
                QMessageBox.information(
                    self,
                    "Telegram account hiện tại",
                    f"Tên: {full_name or '--'}\nUsername: @{username if username else '--'}\nPhone: {phone or '--'}",
                )
            else:
                QMessageBox.information(self, "Telegram", "Chưa đăng nhập Telegram.")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def logout_telegram(self) -> None:
        auth = getattr(self.tracked_group_service, "_auth", None)
        if auth is None:
            QMessageBox.information(self, "Telegram", "Không có auth service.")
            return

        reply = QMessageBox.question(
            self,
            "Đăng xuất Telegram",
            "Bạn có chắc muốn đăng xuất tài khoản Telegram hiện tại không?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            auth.logout()

            self.current_group = None
            self.current_messages = []
            self.groups = []

            if hasattr(self, "message_keyword"):
                self.message_keyword.clear()
            if hasattr(self, "message_sender"):
                self.message_sender.clear()
            if hasattr(self, "group_search"):
                self.group_search.clear()
            if hasattr(self, "group_list"):
                self.group_list.clear()

            self.render_empty()

            QMessageBox.information(
                self,
                "Telegram",
                "Đã đăng xuất Telegram thành công.",
            )

            self.logged_out.emit()

        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def show_header_menu(self) -> None:
        menu = QMenu(self)

        account_action = QAction("Thông tin Telegram", self)
        account_action.triggered.connect(self.show_account_info)

        add_action = QAction("Thêm group", self)
        add_action.triggered.connect(self.show_add_dialog)

        menu.addAction(account_action)
        menu.addAction(add_action)

        if self.groups:
            switch_menu = menu.addMenu("Chọn group")
            for group in self.groups:
                title = (
                    safe_str(group.get("title"))
                    or safe_str(group.get("username"))
                    or safe_str(group.get("chatId"))
                )
                action = QAction(title, self)
                action.triggered.connect(
                    lambda checked=False, grp=group: self.apply_selected_group(grp)
                )
                switch_menu.addAction(action)

        if self.current_group:
            menu.addSeparator()

            crawl_action = QAction("Crawl hôm nay", self)
            crawl_action.triggered.connect(self.crawl_current_group)

            toggle_action = QAction("Bật / tắt theo dõi", self)
            toggle_action.triggered.connect(self.toggle_current_group)

            delete_action = QAction("Xóa group", self)
            delete_action.triggered.connect(self.delete_current_group)

            menu.addAction(crawl_action)
            menu.addAction(toggle_action)
            menu.addAction(delete_action)

        menu.addSeparator()

        logout_action = QAction("Đăng xuất Telegram", self)
        logout_action.triggered.connect(self.logout_telegram)
        menu.addAction(logout_action)

        pos = self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())
        menu.exec(pos)