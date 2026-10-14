"""Code-Editor mit Zeilennummern, Schweregrad-Markierung und Datei-Drop."""

from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPainter,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from bug_detector.core.models import Severity
from bug_detector.ui.theme import COLORS, SEVERITY_COLORS, SEVERITY_TINTS

FLASH_MS = 1200


class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt-Name)
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Editor, der markierte Zeilen farbig hinterlegt und Dateien per Drag & Drop annimmt."""

    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("codeEditor")
        self._markers: Dict[int, Severity] = {}
        self._flash_line = 0
        self._gutter = _LineNumberArea(self)

        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(11)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setPlaceholderText("Code hier einfügen oder Datei hineinziehen …")
        self.setAcceptDrops(True)

        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter)
        self._update_gutter_width()

    # ------------------------------------------------------------------ Markierungen
    def set_markers(self, markers: Dict[int, Severity]) -> None:
        """Setzt die Zeilenmarkierungen (Zeilennummer ab 1 -> Schweregrad)."""
        self._markers = dict(markers)
        self._flash_line = 0
        self._apply_selections()
        self._gutter.update()

    def clear_markers(self) -> None:
        if self._markers:
            self.set_markers({})

    def jump_to_line(self, line: int) -> None:
        """Springt zur Zeile (ab 1), zentriert sie und lässt sie kurz aufleuchten."""
        block = self.document().findBlockByNumber(line - 1)
        if not block.isValid():
            return
        self.setTextCursor(QTextCursor(block))
        self.centerCursor()
        if line in self._markers:
            self._flash_line = line
            self._apply_selections()
            QTimer.singleShot(FLASH_MS, self._end_flash)

    def _end_flash(self) -> None:
        self._flash_line = 0
        self._apply_selections()

    def _apply_selections(self) -> None:
        selections = []
        for line, severity in sorted(self._markers.items()):
            block = self.document().findBlockByNumber(line - 1)
            if not block.isValid():
                continue
            red, green, blue, alpha = SEVERITY_TINTS[severity]
            if line == self._flash_line:
                alpha = min(255, alpha * 4)
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(red, green, blue, alpha))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = QTextCursor(block)
            selections.append(selection)
        self.setExtraSelections(selections)

    # ------------------------------------------------------------------ Zeilennummern
    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 18 + self.fontMetrics().horizontalAdvance("9") * max(3, digits)

    def _update_gutter_width(self, _count: int = 0) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        area = self.contentsRect()
        self._gutter.setGeometry(
            QRect(area.left(), area.top(), self.line_number_area_width(), area.height())
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), QColor(COLORS["panel"]))

        normal_font = self.font()
        bold_font = QFont(normal_font)
        bold_font.setBold(True)
        line_height = self.fontMetrics().height()
        right_flag = int(Qt.AlignmentFlag.AlignRight.value)

        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                severity = self._markers.get(number + 1)
                if severity is not None:
                    painter.setPen(QColor(SEVERITY_COLORS[severity]))
                    painter.setFont(bold_font)
                else:
                    painter.setPen(QColor(COLORS["dim"]))
                    painter.setFont(normal_font)
                painter.drawText(
                    0, top, self._gutter.width() - 8, line_height, right_flag, str(number + 1)
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1
        painter.end()

    # ------------------------------------------------------------------ Drag & Drop
    def _set_drag(self, active: bool) -> None:
        self.setProperty("drag", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag(True)
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._set_drag(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        self._set_drag(False)
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.file_dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
