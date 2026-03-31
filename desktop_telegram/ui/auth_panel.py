from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
)

from desktop_telegram.services.auth_service import AuthService


class AuthPanel(QWidget):
    login_success = Signal()

    def __init__(self, auth_service: AuthService) -> None:
        super().__init__()
        self.auth_service = auth_service
        self._login_emitted = False

        self.setObjectName("authPanel")
        self.setMinimumSize(300, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.card.setMaximumWidth(560)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        self.badge = QLabel("TELEGRAM")
        self.badge.setObjectName("badge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title = QLabel("Đăng nhập Telegram")
        self.title.setObjectName("title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.subtitle = QLabel(
            "Nhập số điện thoại, mã xác thực và mật khẩu 2FA nếu tài khoản có bật."
        )
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setWordWrap(True)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info = QLabel("Sẵn sàng để đăng nhập.")
        self.info.setObjectName("infoLabel")
        self.info.setWordWrap(True)

        self.phone_label = QLabel("Số điện thoại")
        self.phone_label.setObjectName("fieldLabel")

        self.phone_input = QLineEdit()
        self.phone_input.setObjectName("lineEdit")
        self.phone_input.setPlaceholderText("Ví dụ: +84901234567")
        self.phone_input.setClearButtonEnabled(True)

        self.send_phone_btn = QPushButton("Gửi số điện thoại")
        self.send_phone_btn.setObjectName("primaryButton")
        self.send_phone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_phone_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.code_label = QLabel("Mã xác thực")
        self.code_label.setObjectName("fieldLabel")

        self.code_input = QLineEdit()
        self.code_input.setObjectName("lineEdit")
        self.code_input.setPlaceholderText("Nhập code Telegram gửi về")
        self.code_input.setClearButtonEnabled(True)

        self.send_code_btn = QPushButton("Xác nhận mã")
        self.send_code_btn.setObjectName("primaryButton")
        self.send_code_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_code_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.password_label = QLabel("Mật khẩu 2FA")
        self.password_label.setObjectName("fieldLabel")

        self.password_input = QLineEdit()
        self.password_input.setObjectName("lineEdit")
        self.password_input.setPlaceholderText("Nhập mật khẩu 2FA")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setClearButtonEnabled(True)

        self.send_password_btn = QPushButton("Gửi mật khẩu")
        self.send_password_btn.setObjectName("primaryButton")
        self.send_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_password_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        footer_row = QHBoxLayout()
        footer_row.setSpacing(10)

        self.status_btn = QPushButton("Kiểm tra trạng thái")
        self.status_btn.setObjectName("secondaryButton")
        self.status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        footer_row.addWidget(self.status_btn)

        card_layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignHCenter)
        card_layout.addWidget(self.title)
        card_layout.addWidget(self.subtitle)
        card_layout.addWidget(self.info)

        card_layout.addSpacing(2)
        card_layout.addWidget(self.phone_label)
        card_layout.addWidget(self.phone_input)
        card_layout.addWidget(self.send_phone_btn)

        card_layout.addSpacing(2)
        card_layout.addWidget(self.code_label)
        card_layout.addWidget(self.code_input)
        card_layout.addWidget(self.send_code_btn)

        card_layout.addSpacing(2)
        card_layout.addWidget(self.password_label)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.send_password_btn)

        card_layout.addSpacing(4)
        card_layout.addLayout(footer_row)

        root_layout.addWidget(self.card)

        self.setStyleSheet(
            """
            QWidget#authPanel {
                background: #f5f7fb;
            }

            QFrame#card {
                background: #ffffff;
                border: 1px solid #e6eaf2;
                border-radius: 22px;
            }

            QLabel#badge {
                background: #eef2ff;
                color: #4f46e5;
                border: 1px solid #dbe4ff;
                border-radius: 999px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                min-height: 18px;
                max-width: 110px;
            }

            QLabel#title {
                color: #111827;
                font-size: 22px;
                font-weight: 700;
                margin-top: 4px;
            }

            QLabel#subtitle {
                color: #6b7280;
                font-size: 13px;
                line-height: 1.45;
                margin-bottom: 2px;
            }

            QLabel#infoLabel {
                background: #f8fafc;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 12px 14px;
                font-size: 13px;
                line-height: 1.45;
            }

            QLabel#fieldLabel {
                color: #111827;
                font-size: 13px;
                font-weight: 600;
            }

            QLineEdit#lineEdit {
                min-height: 42px;
                padding: 0 14px;
                border: 1px solid #d9e1ec;
                border-radius: 14px;
                background: #ffffff;
                color: #111827;
                font-size: 14px;
                selection-background-color: #c7d2fe;
            }

            QLineEdit#lineEdit:focus {
                border: 1px solid #4f46e5;
                background: #ffffff;
            }

            QPushButton#primaryButton {
                min-height: 42px;
                border: none;
                border-radius: 14px;
                background: #4f46e5;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                padding: 0 14px;
            }

            QPushButton#primaryButton:hover {
                background: #4338ca;
            }

            QPushButton#primaryButton:pressed {
                background: #3730a3;
            }

            QPushButton#secondaryButton {
                min-height: 40px;
                border: 1px solid #d9e1ec;
                border-radius: 14px;
                background: #ffffff;
                color: #111827;
                font-size: 14px;
                font-weight: 600;
                padding: 0 14px;
            }

            QPushButton#secondaryButton:hover {
                background: #f8fafc;
            }

            QPushButton#secondaryButton:pressed {
                background: #eef2f7;
            }

            QPushButton:disabled {
                background: #cbd5e1;
                color: #f8fafc;
                border-color: #cbd5e1;
            }
            """
        )

        self.send_phone_btn.clicked.connect(self.on_send_phone)
        self.send_code_btn.clicked.connect(self.on_send_code)
        self.send_password_btn.clicked.connect(self.on_send_password)
        self.status_btn.clicked.connect(self.on_status)

        self.phone_input.returnPressed.connect(self.on_send_phone)
        self.code_input.returnPressed.connect(self.on_send_code)
        self.password_input.returnPressed.connect(self.on_send_password)

        if not self.auth_service.credentials_ready():
            self.set_info(
                "Thiếu TELEGRAM_API_ID / TELEGRAM_API_HASH trong file .env",
                error=True,
            )
            self.send_phone_btn.setEnabled(False)
            self.send_code_btn.setEnabled(False)
            self.send_password_btn.setEnabled(False)
            self.status_btn.setEnabled(False)
        else:
            self.reset_for_login()
            self._check_and_emit_login_success()

    def set_info(self, text: str, error: bool = False, success: bool = False) -> None:
        self.info.setText(text)

        if error:
            self.info.setStyleSheet(
                """
                background: #fef2f2;
                color: #b91c1c;
                border: 1px solid #fecaca;
                border-radius: 14px;
                padding: 12px 14px;
                font-size: 13px;
                """
            )
            return

        if success:
            self.info.setStyleSheet(
                """
                background: #ecfdf5;
                color: #047857;
                border: 1px solid #a7f3d0;
                border-radius: 14px;
                padding: 12px 14px;
                font-size: 13px;
                """
            )
            return

        self.info.setStyleSheet(
            """
            background: #f8fafc;
            color: #334155;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 12px 14px;
            font-size: 13px;
            """
        )

    def reset_for_login(self) -> None:
        self._login_emitted = False
        self.phone_input.clear()
        self.code_input.clear()
        self.password_input.clear()

        if self.auth_service.credentials_ready():
            self.send_phone_btn.setEnabled(True)
            self.send_code_btn.setEnabled(True)
            self.send_password_btn.setEnabled(True)
            self.status_btn.setEnabled(True)
            self.set_info("Nhập số điện thoại để bắt đầu đăng nhập Telegram.")
            self.phone_input.setFocus()

    def _status_step(self, status: object) -> str:
        if isinstance(status, dict):
            return str(status.get("step", "")).upper()
        return str(status).upper()

    def _is_ready_status(self, status: object) -> bool:
        if isinstance(status, dict):
            if bool(status.get("authorized")):
                return True
            return str(status.get("step", "")).upper() == "READY"
        return str(status).upper() == "READY"

    def _emit_login_success_once(self) -> None:
        if not self._login_emitted:
            self._login_emitted = True
            self.login_success.emit()

    def _check_and_emit_login_success(self) -> bool:
        try:
            status = self.auth_service.get_status()
            if self._is_ready_status(status):
                self.set_info("Đăng nhập Telegram thành công.", success=True)
                self._emit_login_success_once()
                return True
        except Exception:
            pass
        return False

    def on_send_phone(self) -> None:
        phone = self.phone_input.text().strip()
        if not phone:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập số điện thoại.")
            self.phone_input.setFocus()
            return

        try:
            self.auth_service.send_phone(phone)
            self._login_emitted = False
            self.set_info(
                "Đã gửi số điện thoại. Kiểm tra Telegram để lấy mã xác thực.",
                success=True,
            )
            QMessageBox.information(self, "OK", "Đã gửi số điện thoại.")
            self.code_input.setFocus()
            self._check_and_emit_login_success()
        except Exception as exc:
            self.set_info(str(exc), error=True)
            QMessageBox.critical(self, "Lỗi", str(exc))

    def on_send_code(self) -> None:
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập mã xác thực.")
            self.code_input.setFocus()
            return

        try:
            step = self.auth_service.send_code(code)
            step_text = self._status_step(step)

            if self._is_ready_status(step):
                self.set_info("Đăng nhập Telegram thành công.", success=True)
                QMessageBox.information(self, "OK", "Đăng nhập thành công.")
                self._emit_login_success_once()
                return

            self.set_info(
                f"Xử lý mã thành công. Trạng thái hiện tại: {step_text}",
                success=True,
            )
            QMessageBox.information(self, "OK", f"Kết quả: {step_text}")

            if step_text == "PASSWORD":
                self.password_input.setFocus()

            self._check_and_emit_login_success()
        except Exception as exc:
            self.set_info(str(exc), error=True)
            QMessageBox.critical(self, "Lỗi", str(exc))

    def on_send_password(self) -> None:
        password = self.password_input.text().strip()
        if not password:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập mật khẩu 2FA.")
            self.password_input.setFocus()
            return

        try:
            step = self.auth_service.send_password(password)
            step_text = self._status_step(step)

            if self._is_ready_status(step):
                self.set_info("Đăng nhập Telegram thành công.", success=True)
                QMessageBox.information(self, "OK", "Đăng nhập thành công.")
                self._emit_login_success_once()
                return

            self.set_info(
                f"Xử lý mật khẩu thành công. Trạng thái hiện tại: {step_text}",
                success=True,
            )
            QMessageBox.information(self, "OK", f"Kết quả: {step_text}")

            self._check_and_emit_login_success()
        except Exception as exc:
            self.set_info(str(exc), error=True)
            QMessageBox.critical(self, "Lỗi", str(exc))

    def on_status(self) -> None:
        try:
            status = self.auth_service.get_status()

            if self._is_ready_status(status):
                self.set_info("Đăng nhập Telegram thành công.", success=True)
                self._emit_login_success_once()
            else:
                self.set_info(f"Trạng thái hiện tại: {status}")

            QMessageBox.information(self, "Status", str(status))
        except Exception as exc:
            self.set_info(str(exc), error=True)
            QMessageBox.critical(self, "Lỗi", str(exc))