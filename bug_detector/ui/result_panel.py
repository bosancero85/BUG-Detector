"""Ergebnisbereich: Statistik-Filter, Fortschritt und aufklappbare Fund-Karten."""

from __future__ import annotations

from html import escape
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bug_detector.core.models import Finding, Severity, count_by_severity
from bug_detector.ui.theme import COLORS, SEVERITY_COLORS


class _ClickableFrame(QFrame):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


def _transparent(*widgets: QWidget) -> None:
    for widget in widgets:
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class StatButton(_ClickableFrame):
    """Kachel mit Zähler je Schweregrad. Klick schaltet den Filter um."""

    def __init__(self, severity: Severity, parent=None) -> None:
        super().__init__(parent)
        self.severity = severity
        self.setObjectName("stat")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        color = SEVERITY_COLORS[severity]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(0)
        self._count = QLabel("0")
        self._count.setObjectName("statCount")
        self._count.setStyleSheet("color: %s;" % color)
        name = QLabel(severity.label)
        name.setObjectName("statName")
        layout.addWidget(self._count)
        layout.addWidget(name)
        _transparent(self._count, name)
        self._color = color

    def set_count(self, value: int) -> None:
        self._count.setText(str(value))

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.setStyleSheet(
            "#stat { border-color: %s; }" % self._color if active else ""
        )
        _repolish(self)


class FindingCard(QFrame):
    """Aufklappbare Karte mit Problem, Root-Cause und Lösungsvorschlag."""

    line_requested = pyqtSignal(int)

    def __init__(self, finding: Finding, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._finding = finding
        color = SEVERITY_COLORS[finding.severity]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._header = _ClickableFrame()
        self._header.setObjectName("cardHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        head = QHBoxLayout(self._header)
        head.setContentsMargins(12, 10, 12, 10)
        head.setSpacing(10)

        badge = QLabel(finding.severity.label)
        badge.setStyleSheet(
            "color: %s; border: 1px solid %s; border-radius: 9px; padding: 1px 9px;"
            " font-weight: 700; font-size: 11px;" % (color, color)
        )
        title = QLabel(
            "%s<br><span style='color:%s; font-size:12px;'>Zeile %d</span>"
            % (escape(finding.title), COLORS["dim"], finding.line)
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setWordWrap(True)
        self._chevron = QLabel("▶")
        self._chevron.setStyleSheet("color: %s;" % COLORS["dim"])
        head.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        head.addWidget(title, 1)
        head.addWidget(self._chevron, 0, Qt.AlignmentFlag.AlignTop)
        _transparent(badge, title, self._chevron)
        self._header.clicked.connect(self.toggle)

        self._body = QWidget()
        self._body.setObjectName("cardBody")
        body = QVBoxLayout(self._body)
        body.setContentsMargins(12, 0, 12, 12)
        body.setSpacing(2)
        body.addWidget(self._section("PROBLEM"))
        body.addWidget(self._text(finding.problem))
        body.addWidget(self._section("ROOT-CAUSE"))
        body.addWidget(self._text(finding.root_cause))

        fix_row = QHBoxLayout()
        fix_row.addWidget(self._section("LÖSUNGSVORSCHLAG"))
        fix_row.addStretch(1)
        self._copy = QPushButton("Kopieren")
        self._copy.setObjectName("smallButton")
        self._copy.clicked.connect(self._copy_fix)
        self._reset_timer = QTimer(self._copy)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(lambda: self._copy.setText("Kopieren"))
        fix_row.addWidget(self._copy)
        body.addSpacing(6)
        body.addLayout(fix_row)
        body.addWidget(self._fix_box(finding.fix))
        self._body.setVisible(False)

        outer.addWidget(self._header)
        outer.addWidget(self._body)

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("cardSection")
        return label

    @staticmethod
    def _text(text: str) -> QLabel:
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    @staticmethod
    def _fix_box(text: str) -> QPlainTextEdit:
        box = QPlainTextEdit()
        box.setObjectName("fixBox")
        box.setReadOnly(True)
        box.setPlainText(text)
        box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        box.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        lines = text.count("\n") + 1
        box.setFixedHeight(box.fontMetrics().lineSpacing() * lines + 34)
        return box

    def toggle(self) -> None:
        opened = not self._body.isVisible()
        self._body.setVisible(opened)
        self._chevron.setText("▼" if opened else "▶")
        if opened:
            self.line_requested.emit(self._finding.line)

    def is_open(self) -> bool:
        return self._body.isVisible()

    def _copy_fix(self) -> None:
        QApplication.clipboard().setText(self._finding.fix)
        self._copy.setText("Kopiert ✓")
        self._reset_timer.start(1500)


class ResultPanel(QWidget):
    """Zeigt Platzhalter, Fortschritt, Meldungen oder die Liste der Funde."""

    line_requested = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._findings: List[Finding] = []
        self._filter: Optional[Severity] = None
        self._phase_label: Optional[QLabel] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.hide()
        root.addWidget(self._progress)

        self._stats = QWidget()
        stats_layout = QHBoxLayout(self._stats)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(8)
        self._stat_buttons: Dict[Severity, StatButton] = {}
        for severity in Severity:
            button = StatButton(severity)
            button.clicked.connect(lambda sev=severity: self._toggle_filter(sev))
            self._stat_buttons[severity] = button
            stats_layout.addWidget(button)
        self._status = QFrame()
        self._status.setObjectName("stat")
        status_layout = QVBoxLayout(self._status)
        status_layout.setContentsMargins(10, 8, 10, 8)
        status_layout.setSpacing(0)
        self._status_icon = QLabel("✔")
        self._status_icon.setObjectName("statCount")
        self._status_text = QLabel("Sauber")
        self._status_text.setObjectName("statName")
        status_layout.addWidget(self._status_icon)
        status_layout.addWidget(self._status_text)
        stats_layout.addWidget(self._status)
        self._stats.hide()
        root.addWidget(self._stats)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self._scroll, 1)

        self.show_placeholder()

    # ------------------------------------------------------------------ Zustände
    def show_placeholder(self) -> None:
        self._findings = []
        self._enter_state(busy=False, stats=False)
        self._set_content([self._message_label(
            "Noch kein Ergebnis.\nFüge Code ein und klicke auf „Scan Code“.", "")])

    def show_message(self, text: str, kind: str = "warning") -> None:
        self._findings = []
        self._enter_state(busy=False, stats=False)
        self._set_content([self._message_label(text, kind)])

    def show_busy(self) -> None:
        self._enter_state(busy=True, stats=False)
        self._progress.setValue(0)
        self._phase_label = self._message_label("Code wird geparst …", "")
        self._set_content([self._phase_label])

    def set_progress(self, percent: int, text: str) -> None:
        self._progress.setValue(percent)
        if self._phase_label is not None:
            self._phase_label.setText(text)

    def show_findings(self, findings: List[Finding]) -> None:
        self._findings = list(findings)
        self._filter = None
        self._enter_state(busy=False, stats=True)
        counts = count_by_severity(self._findings)
        for severity, button in self._stat_buttons.items():
            button.set_count(counts[severity])
            button.set_active(False)
        if self._findings:
            self._status_icon.setText("⚠")
            self._status_text.setText("%d Funde" % len(self._findings))
        else:
            self._status_icon.setText("✔")
            self._status_text.setText("Sauber")
        self._rebuild_cards()

    # ------------------------------------------------------------------ intern
    def _enter_state(self, busy: bool, stats: bool) -> None:
        self._progress.setVisible(busy)
        self._stats.setVisible(stats)
        if not busy:
            self._phase_label = None

    def _toggle_filter(self, severity: Severity) -> None:
        self._filter = None if self._filter == severity else severity
        for sev, button in self._stat_buttons.items():
            button.set_active(sev == self._filter)
        self._rebuild_cards()

    def _rebuild_cards(self) -> None:
        if not self._findings:
            self._set_content([self._message_label("✔ Keine Fehler gefunden. Starker Code!", "ok")])
            return
        visible = [f for f in self._findings if self._filter in (None, f.severity)]
        if not visible:
            self._set_content([self._message_label("Keine Funde in dieser Kategorie.", "")])
            return
        cards = []
        for finding in visible:
            card = FindingCard(finding)
            card.line_requested.connect(self.line_requested)
            cards.append(card)
        self._set_content(cards)

    @staticmethod
    def _message_label(text: str, kind: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("emptyBox")
        label.setProperty("kind", kind)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        return label

    def _set_content(self, widgets: List[QWidget]) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(10)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addStretch(1)
        self._scroll.setWidget(container)  # ersetzt und löscht den alten Inhalt
