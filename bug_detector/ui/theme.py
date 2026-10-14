"""Farben und Stylesheet (dunkles Theme wie in der Vorlage)."""

from __future__ import annotations

from typing import Dict, Tuple

from bug_detector.core.models import Severity

COLORS: Dict[str, str] = {
    "bg": "#0e1217",
    "panel": "#161b22",
    "panel2": "#1d242d",
    "line": "#283140",
    "text": "#dce3ec",
    "dim": "#8592a3",
    "ok": "#10b981",
    "cr": "#ff2d55",
    "wa": "#f59e0b",
    "inf": "#38bdf8",
    "code": "#0a0d11",
}

SEVERITY_COLORS: Dict[Severity, str] = {
    Severity.CRITICAL: COLORS["cr"],
    Severity.WARNING: COLORS["wa"],
    Severity.INFO: COLORS["inf"],
}

# RGBA-Tönung der markierten Zeilen im Editor
SEVERITY_TINTS: Dict[Severity, Tuple[int, int, int, int]] = {
    Severity.CRITICAL: (255, 45, 85, 42),
    Severity.WARNING: (245, 158, 11, 36),
    Severity.INFO: (56, 189, 248, 30),
}

_QSS = """
QWidget { background: @bg; color: @text; font-size: 14px; }
QMainWindow, QSplitter, QScrollArea, QScrollArea > QWidget > QWidget { background: @bg; }
QSplitter::handle { background: @line; width: 1px; }
QToolTip { background: @panel2; color: @text; border: 1px solid @line; }

QMenuBar { background: @panel; }
QMenuBar::item:selected { background: @panel2; }
QMenu { background: @panel; border: 1px solid @line; }
QMenu::item:selected { background: @panel2; }
QStatusBar { background: @panel; color: @dim; }
QStatusBar QLabel { background: transparent; }
#staleLabel { color: @wa; }

#header { background: @panel; border-bottom: 1px solid @line; }
#header QLabel { background: transparent; }
#title { font-size: 18px; font-weight: 700; }

QPushButton {
    background: @panel2; border: 1px solid @line; border-radius: 10px; padding: 8px 14px;
}
QPushButton:hover { border-color: @ok; }
QPushButton:pressed { background: @line; }
QPushButton:disabled { color: @dim; }
QPushButton#scanButton {
    background: @ok; border-color: @ok; color: #04130d; font-weight: 700; min-width: 110px;
}
QPushButton#scanButton:disabled { background: #0b7a56; color: #04130d; }
QPushButton#smallButton { padding: 3px 10px; font-size: 12px; border-radius: 8px; }

QComboBox {
    background: @panel2; border: 1px solid @line; border-radius: 10px; padding: 7px 10px;
    min-width: 130px;
}
QComboBox:hover { border-color: @ok; }
QComboBox QAbstractItemView {
    background: @panel; border: 1px solid @line; selection-background-color: @panel2;
}

#historyPanel { background: @panel; border-right: 1px solid @line; }
#historyPanel QLabel { background: transparent; }
#historyTitle { color: @dim; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
QListWidget { background: @panel; border: 0; outline: 0; }
QListWidget::item { padding: 10px; border-radius: 10px; margin: 0 8px 2px 8px; }
QListWidget::item:hover, QListWidget::item:selected { background: @panel2; color: @text; }

QPlainTextEdit#codeEditor {
    background: @panel; border: 1px solid @line; border-radius: 14px; padding: 6px;
    selection-background-color: #1f6f56;
}
QPlainTextEdit#codeEditor[drag="true"] { border: 2px dashed @ok; }
QPlainTextEdit#fixBox {
    background: @code; border: 1px solid @line; border-radius: 10px; padding: 4px;
}

QProgressBar { background: @panel2; border: 0; border-radius: 2px; }
QProgressBar::chunk { background: @ok; border-radius: 2px; }

#stat { background: @panel; border: 1px solid @line; border-radius: 12px; }
#stat:hover { background: @panel2; }
#stat[active="true"] { background: @panel2; }
#stat QLabel { background: transparent; }
#statCount { font-size: 24px; font-weight: 700; }
#statName { color: @dim; font-size: 12px; }

#card { background: @panel; border: 1px solid @line; border-radius: 12px; }
#cardHeader { background: transparent; border-radius: 12px; }
#cardHeader:hover { background: @panel2; }
#cardHeader QLabel, #cardBody QLabel { background: transparent; }
#cardBody { background: transparent; }
#cardSection { color: @dim; font-size: 12px; font-weight: 700; }

#emptyBox {
    border: 1px dashed @line; border-radius: 14px; padding: 32px 16px; color: @dim;
    background: transparent;
}
#emptyBox[kind="ok"] { border-color: @ok; color: @ok; }
#emptyBox[kind="warning"] { color: @wa; }
#emptyBox[kind="error"] { color: @cr; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: @line; border-radius: 5px; min-height: 24px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: @line; border-radius: 5px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""


def build_stylesheet() -> str:
    """Setzt die Farbplatzhalter (``@name``) im Stylesheet ein."""
    sheet = _QSS
    for key in sorted(COLORS, key=len, reverse=True):
        sheet = sheet.replace("@" + key, COLORS[key])
    return sheet


STYLESHEET = build_stylesheet()
