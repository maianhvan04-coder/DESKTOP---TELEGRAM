from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from desktop_telegram.db.indexes import ensure_indexes
from desktop_telegram.ui.main_window import MainWindow


def main() -> int:
    ensure_indexes()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main()) 