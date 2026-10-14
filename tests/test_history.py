import json
import tempfile
import unittest
from pathlib import Path

from bug_detector.core.history import MAX_CODE_CHARS, HistoryEntry, HistoryStore


def make_entry(name="a.js", code="x"):
    return HistoryEntry.create(name, "JavaScript", {"cr": 1, "wa": 2, "in": 3}, code, name)


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "sub" / "history.json"

    def test_roundtrip(self):
        store = HistoryStore(self.path)
        self.assertTrue(store.add(make_entry("one.js", "code")))
        again = HistoryStore(self.path)
        entries = again.load()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "one.js")
        self.assertEqual(entries[0].counts, {"cr": 1, "wa": 2, "in": 3})
        self.assertEqual(entries[0].code, "code")

    def test_newest_first_and_limit(self):
        store = HistoryStore(self.path, max_entries=3)
        for index in range(5):
            store.add(make_entry("f%d" % index))
        self.assertEqual([e.name for e in store.entries], ["f4", "f3", "f2"])
        self.assertEqual(len(HistoryStore(self.path, max_entries=3).load()), 3)

    def test_clear(self):
        store = HistoryStore(self.path)
        store.add(make_entry())
        store.clear()
        self.assertEqual(HistoryStore(self.path).load(), [])

    def test_missing_file(self):
        self.assertEqual(HistoryStore(self.path).load(), [])

    def test_corrupt_json(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{nicht json", encoding="utf-8")
        self.assertEqual(HistoryStore(self.path).load(), [])

    def test_wrong_structure_and_bad_items(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"a": 1}), encoding="utf-8")
        self.assertEqual(HistoryStore(self.path).load(), [])
        good = {
            "name": "ok", "language": "Python", "timestamp": "x",
            "counts": {"cr": 1}, "code": "",
        }
        self.path.write_text(json.dumps([good, 5, {"language": "kein name"}]), encoding="utf-8")
        loaded = HistoryStore(self.path).load()
        self.assertEqual([e.name for e in loaded], ["ok"])
        self.assertEqual(loaded[0].counts, {"cr": 1, "wa": 0, "in": 0})

    def test_code_truncated(self):
        entry = make_entry(code="a" * (MAX_CODE_CHARS + 50))
        self.assertEqual(len(entry.code), MAX_CODE_CHARS)

    def test_unwritable_location_returns_false(self):
        blocker = Path(self.tmp.name) / "datei"
        blocker.write_text("x", encoding="utf-8")
        store = HistoryStore(blocker / "history.json")  # Elternteil ist eine Datei
        self.assertFalse(store.add(make_entry()))
        self.assertEqual(len(store.entries), 1)  # bleibt im Speicher erhalten

    def test_no_temp_files_left(self):
        store = HistoryStore(self.path)
        store.add(make_entry())
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["history.json"])

    def test_display_time(self):
        self.assertRegex(make_entry().display_time, r"^\d\d:\d\d$")
        entry = make_entry()
        entry.timestamp = "kaputt"
        self.assertEqual(entry.display_time, "")

    def test_next_input_name(self):
        store = HistoryStore(self.path)
        self.assertEqual(store.next_input_name(), "Eingabe #1")
        store.add(make_entry())
        self.assertEqual(store.next_input_name(), "Eingabe #2")


if __name__ == "__main__":
    unittest.main()
