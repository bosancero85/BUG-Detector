"""Hintergrund-Thread für den Scan, damit die Oberfläche nie einfriert."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from bug_detector.core.analyzer import analyze

PHASES = (
    "Code wird geparst …",
    "Muster werden geprüft …",
    "Speicherzugriffe werden analysiert …",
    "Bericht wird erstellt …",
)


def phase_text(percent: int) -> str:
    """Statustext passend zum Fortschritt (0–100)."""
    return PHASES[min(len(PHASES) - 1, percent * len(PHASES) // 100)]


class ScanWorker(QThread):
    progress = pyqtSignal(int, str)
    result_ready = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, code: str, language: str, parent=None) -> None:
        super().__init__(parent)
        self._code = code
        self._language = language

    def _on_progress(self, done: int, total: int) -> None:
        percent = int(done * 100 / total) if total else 100
        self.progress.emit(percent, phase_text(percent))

    def run(self) -> None:
        try:
            findings = analyze(self._code, self._language, self._on_progress)
        except Exception as exc:  # noqa: BLE001 – jede Störung soll in der UI landen
            self.failed.emit(str(exc))
            return
        self.result_ready.emit(findings)
