"""Anwendungsstart: QApplication, Theme und Hauptfenster."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import QApplication

from bug_detector import APP_NAME
from bug_detector.ui.main_window import MainWindow
from bug_detector.ui.theme import STYLESHEET


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv if argv is None else argv)
    app = QApplication(args)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")  # gleiches Aussehen unter Windows, macOS und Linux
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    if len(args) > 1 and Path(args[1]).is_file():
        window.open_path(args[1])
    return app.exec()
