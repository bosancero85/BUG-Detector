"""Seitenleiste mit dem Scan-Verlauf."""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bug_detector.core.history import HistoryEntry

ENTRY_INDEX_ROLE = Qt.ItemDataRole.UserRole


class HistoryPanel(QWidget):
    entry_selected = pyqtSignal(int)
    clear_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(16, 14, 12, 8)
        title = QLabel("VERLAUF")
        title.setObjectName("historyTitle")
        clear = QPushButton("Leeren")
        clear.setObjectName("smallButton")
        clear.clicked.connect(self.clear_requested)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(clear)
        layout.addLayout(head)

        self._list = QListWidget()
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, 1)

    def set_entries(self, entries: List[HistoryEntry]) -> None:
        self._list.clear()
        if not entries:
            item = QListWidgetItem("Noch keine Scans.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)
            return
        for index, entry in enumerate(entries):
            counts = entry.counts
            text = "%s\n%s · %s\n● %d   ● %d   ● %d" % (
                entry.name,
                entry.language,
                entry.display_time,
                counts.get("cr", 0),
                counts.get("wa", 0),
                counts.get("in", 0),
            )
            item = QListWidgetItem(text)
            item.setData(ENTRY_INDEX_ROLE, index)
            self._list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(ENTRY_INDEX_ROLE)
        if index is not None:
            self.entry_selected.emit(int(index))
        self._list.clearSelection()
