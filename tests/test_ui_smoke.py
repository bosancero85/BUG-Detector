"""UI-Smoke-Test. Wird übersprungen, wenn PyQt6 nicht installiert ist.

Läuft headless mit QT_QPA_PLATFORM=offscreen.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication

    HAVE_QT = True
except ImportError:  # pragma: no cover
    HAVE_QT = False

if HAVE_QT:
    from bug_detector.core.history import HistoryStore
    from bug_detector.core.sample import SAMPLE_CODE
    from bug_detector.ui.main_window import MainWindow


@unittest.skipUnless(HAVE_QT, "PyQt6 nicht installiert")
class UiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = HistoryStore(Path(self.tmp.name) / "history.json")
        self.window = MainWindow(self.store)
        self.addCleanup(self.window.close)

    def wait_for_scan(self, timeout=10.0):
        deadline = time.time() + timeout
        while self.window._worker is not None and time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.app.processEvents()
        self.assertIsNone(self.window._worker, "Scan wurde nicht rechtzeitig beendet")

    def test_starts_with_sample(self):
        self.assertEqual(self.window._editor.toPlainText(), SAMPLE_CODE)

    def test_scan_marks_lines_and_fills_history(self):
        self.window.start_scan()
        self.wait_for_scan()
        self.assertEqual(len(self.window._findings), 13)
        self.assertEqual(len(self.store.entries), 1)
        self.assertTrue(self.window._editor._markers)
        self.assertTrue(self.window._btn_scan.isEnabled())

    def test_edit_after_scan_marks_stale(self):
        self.window.start_scan()
        self.wait_for_scan()
        self.window._editor.appendPlainText("// neu")
        self.assertTrue(self.window._stale)
        self.assertFalse(self.window._editor._markers)

    def test_empty_scan_shows_hint(self):
        self.window.load_text("   ", "x.js")
        self.window.start_scan()
        self.assertIsNone(self.window._worker)
        self.assertEqual(len(self.store.entries), 0)

    def test_open_history_entry_rescans(self):
        self.window.start_scan()
        self.wait_for_scan()
        self.window._open_history_entry(0)
        self.wait_for_scan()
        self.assertEqual(len(self.store.entries), 2)

    def test_open_missing_file_keeps_editor(self):
        before = self.window._editor.toPlainText()
        self.window.open_path(str(Path(self.tmp.name) / "fehlt.py"))
        self.assertEqual(self.window._editor.toPlainText(), before)


if __name__ == "__main__":
    unittest.main()
