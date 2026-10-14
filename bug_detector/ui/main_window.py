"""Hauptfenster: verbindet Editor, Ergebnisse, Verlauf und Scan-Worker."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from bug_detector import APP_NAME, __version__
from bug_detector.core.history import HistoryEntry, HistoryStore
from bug_detector.core.languages import EXTENSIONS, LANGUAGES, label_for, resolve_language
from bug_detector.core.models import Finding, count_by_severity, worst_severity_per_line
from bug_detector.core.sample import SAMPLE_CODE, SAMPLE_NAME
from bug_detector.ui.code_editor import CodeEditor
from bug_detector.ui.history_panel import HistoryPanel
from bug_detector.ui.result_panel import ResultPanel
from bug_detector.ui.worker import ScanWorker
from bug_detector.utils.files import FileReadError, read_source_file
from bug_detector.utils.paths import history_file

DEFAULT_NAME = "Eingabe"
SCAN_LABEL = "Scan Code"


class MainWindow(QMainWindow):
    def __init__(self, store: Optional[HistoryStore] = None) -> None:
        super().__init__()
        self._store = store if store is not None else HistoryStore(history_file())
        self._store.load()
        self._findings: List[Finding] = []
        self._stale = False
        self._current_name = DEFAULT_NAME
        self._worker: Optional[ScanWorker] = None

        self.setWindowTitle(APP_NAME)
        self.resize(1400, 860)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._history.set_entries(self._store.entries)
        self.load_text(SAMPLE_CODE, SAMPLE_NAME)

    # ------------------------------------------------------------------ Aufbau
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("header")
        head = QHBoxLayout(header)
        head.setContentsMargins(16, 12, 16, 12)
        head.setSpacing(10)
        title = QLabel('🐞 Bug <span style="color:#10b981">Detector</span>')
        title.setObjectName("title")
        title.setTextFormat(Qt.TextFormat.RichText)
        self._lang = QComboBox()
        self._lang.setToolTip("Sprache der Analyse")
        for key, label in LANGUAGES:
            self._lang.addItem(label, key)
        self._btn_open = QPushButton("Datei öffnen")
        self._btn_demo = QPushButton("Beispiel")
        self._btn_scan = QPushButton(SCAN_LABEL)
        self._btn_scan.setObjectName("scanButton")
        self._btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self._lang)
        head.addWidget(self._btn_open)
        head.addWidget(self._btn_demo)
        head.addWidget(self._btn_scan)
        root.addWidget(header)

        self._history = HistoryPanel()
        self._editor = CodeEditor()
        self._results = ResultPanel()

        editor_box = QWidget()
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.setContentsMargins(16, 16, 8, 16)
        editor_layout.addWidget(self._editor)

        results_box = QWidget()
        results_layout = QVBoxLayout(results_box)
        results_layout.setContentsMargins(8, 16, 16, 16)
        results_layout.addWidget(self._results)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._history)
        splitter.addWidget(editor_box)
        splitter.addWidget(results_box)
        splitter.setSizes([250, 640, 510])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        root.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self._info = QLabel("0 Zeilen")
        self._stale_label = QLabel("")
        self._stale_label.setObjectName("staleLabel")
        self.statusBar().addWidget(self._info)
        self.statusBar().addWidget(self._stale_label)

    def _build_menu(self) -> None:
        bar = self.menuBar()

        file_menu = bar.addMenu("&Datei")
        self._act_open = QAction("Datei öffnen …", self)
        self._act_open.setShortcut(QKeySequence("Ctrl+O"))
        self._act_open.triggered.connect(self.open_file_dialog)
        act_demo = QAction("Beispiel laden", self)
        act_demo.triggered.connect(self.load_sample)
        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(self._act_open)
        file_menu.addAction(act_demo)
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

        scan_menu = bar.addMenu("&Scan")
        self._act_scan = QAction("Scan Code", self)
        self._act_scan.setShortcuts([QKeySequence("F5"), QKeySequence("Ctrl+Return")])
        self._act_scan.triggered.connect(self.start_scan)
        act_clear = QAction("Verlauf leeren", self)
        act_clear.triggered.connect(self.clear_history)
        scan_menu.addAction(self._act_scan)
        scan_menu.addAction(act_clear)

        help_menu = bar.addMenu("&Hilfe")
        act_about = QAction("Über %s" % APP_NAME, self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _connect_signals(self) -> None:
        self._btn_open.clicked.connect(self.open_file_dialog)
        self._btn_demo.clicked.connect(self.load_sample)
        self._btn_scan.clicked.connect(self.start_scan)
        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.file_dropped.connect(self.open_path)
        self._results.line_requested.connect(self._on_line_requested)
        self._history.entry_selected.connect(self._open_history_entry)
        self._history.clear_requested.connect(self.clear_history)

    # ------------------------------------------------------------------ Text laden
    def load_text(self, code: str, name: str = DEFAULT_NAME) -> None:
        """Lädt Text in den Editor und setzt Ergebnisse zurück."""
        self._findings = []
        self._stale = False
        self._current_name = name or DEFAULT_NAME
        self._editor.set_markers({})
        self._editor.setPlainText(code)
        self._stale_label.setText("")
        self._results.show_placeholder()
        self._update_info()

    def load_sample(self) -> None:
        if self._busy():
            return
        self.load_text(SAMPLE_CODE, SAMPLE_NAME)
        self._lang.setCurrentIndex(0)

    def open_file_dialog(self) -> None:
        patterns = " ".join("*.%s" % ext for ext in sorted(EXTENSIONS))
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei öffnen", "", "Quelltext (%s);;Alle Dateien (*)" % patterns
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str) -> None:
        if self._busy():
            return
        try:
            text = read_source_file(path)
        except FileReadError as exc:
            self._results.show_message(str(exc), "error")
            return
        self.load_text(text, Path(path).name)
        self._lang.setCurrentIndex(0)

    # ------------------------------------------------------------------ Scan
    def _busy(self) -> bool:
        return self._worker is not None

    def start_scan(self) -> None:
        if self._busy():
            return
        code = self._editor.toPlainText()
        if not code.strip():
            self._results.show_message(
                "Bitte zuerst Code eingeben oder eine Datei hineinziehen.", "warning"
            )
            return
        language = resolve_language(self._lang.currentData(), code, self._current_name)
        name = self._current_name

        self._btn_scan.setEnabled(False)
        self._btn_scan.setText("0 %")
        self._results.show_busy()

        worker = ScanWorker(code, language, self)
        worker.progress.connect(self._on_progress)
        worker.result_ready.connect(
            lambda findings: self._on_scan_done(findings, code, language, name)
        )
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(self._on_worker_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_progress(self, percent: int, text: str) -> None:
        self._results.set_progress(percent, text)
        self._btn_scan.setText("%d %%" % percent)

    def _on_scan_done(self, findings: List[Finding], code: str, language: str, name: str) -> None:
        self._findings = list(findings)
        self._stale = False
        self._stale_label.setText("")

        counts = {sev.value: n for sev, n in count_by_severity(self._findings).items()}
        display_name = self._store.next_input_name() if name == DEFAULT_NAME else name
        entry = HistoryEntry.create(display_name, label_for(language), counts, code, name)
        saved = self._store.add(entry)
        self._history.set_entries(self._store.entries)
        if not saved:
            self.statusBar().showMessage("Verlauf konnte nicht gespeichert werden.", 5000)

        self._results.show_findings(self._findings)
        self._editor.set_markers(worst_severity_per_line(self._findings))

    def _on_scan_failed(self, message: str) -> None:
        self._results.show_message("Analyse fehlgeschlagen: %s" % message, "error")

    def _on_worker_finished(self) -> None:
        self._worker = None
        self._btn_scan.setEnabled(True)
        self._btn_scan.setText(SCAN_LABEL)

    # ------------------------------------------------------------------ Ereignisse
    def _on_text_changed(self) -> None:
        self._update_info()
        if self._findings and not self._stale:
            self._stale = True
            self._editor.clear_markers()
            self._stale_label.setText("Code geändert – bitte erneut scannen")

    def _update_info(self) -> None:
        lines = self._editor.blockCount()
        chars = max(0, self._editor.document().characterCount() - 1)
        self._info.setText("%d Zeilen · %d Zeichen" % (lines, chars))

    def _on_line_requested(self, line: int) -> None:
        if not self._stale:
            self._editor.jump_to_line(line)

    def _open_history_entry(self, index: int) -> None:
        if self._busy() or not 0 <= index < len(self._store.entries):
            return
        entry = self._store.entries[index]
        self.load_text(entry.code, entry.filename)
        self._lang.setCurrentIndex(0)
        self.start_scan()

    def clear_history(self) -> None:
        self._store.clear()
        self._history.set_entries(self._store.entries)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "Über %s" % APP_NAME,
            "<b>%s</b> %s<br>Regelbasierter Code-Scanner mit Root-Cause und "
            "Lösungsvorschlägen.<br>Lizenz: MIT" % (APP_NAME, __version__),
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        worker = self._worker
        if worker is not None:
            worker.wait(3000)
        super().closeEvent(event)
