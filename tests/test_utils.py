import tempfile
import unittest
from pathlib import Path

from bug_detector.utils.files import FileReadError, read_source_file
from bug_detector.utils.paths import history_file, user_data_dir


class PathsTest(unittest.TestCase):
    def test_windows(self):
        path = user_data_dir("win32", {"APPDATA": "C:/Users/a/AppData/Roaming"}, "C:/Users/a")
        self.assertEqual(path, Path("C:/Users/a/AppData/Roaming") / "BugDetector")

    def test_windows_without_appdata(self):
        path = user_data_dir("win32", {}, "/h")
        self.assertEqual(path, Path("/h") / "AppData" / "Roaming" / "BugDetector")

    def test_macos(self):
        path = user_data_dir("darwin", {}, "/Users/a")
        self.assertEqual(path, Path("/Users/a/Library/Application Support/BugDetector"))

    def test_linux_default_and_kali(self):
        self.assertEqual(
            user_data_dir("linux", {}, "/home/kali"), Path("/home/kali/.local/share/BugDetector")
        )

    def test_linux_xdg(self):
        path = user_data_dir("linux", {"XDG_DATA_HOME": "/x"}, "/home/kali")
        self.assertEqual(path, Path("/x/BugDetector"))

    def test_history_file(self):
        self.assertEqual(
            history_file(platform="linux", environ={}, home="/h").name, "history.json"
        )


class FilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, data: bytes, name="f.txt") -> Path:
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_utf8(self):
        self.assertEqual(read_source_file(self.write("äö€".encode("utf-8"))), "äö€")

    def test_bom_removed(self):
        self.assertEqual(read_source_file(self.write(b"\xef\xbb\xbfabc")), "abc")

    def test_cp1252_fallback(self):
        self.assertEqual(read_source_file(self.write("Grüße".encode("cp1252"))), "Grüße")

    def test_line_endings_normalized(self):
        self.assertEqual(read_source_file(self.write(b"a\r\nb\rc\n")), "a\nb\nc\n")

    def test_too_large(self):
        with self.assertRaises(FileReadError):
            read_source_file(self.write(b"x" * 20), max_bytes=10)

    def test_binary(self):
        with self.assertRaises(FileReadError):
            read_source_file(self.write(b"ab\x00cd"))

    def test_missing(self):
        with self.assertRaises(FileReadError):
            read_source_file(self.dir / "gibt_es_nicht.py")

    def test_directory(self):
        with self.assertRaises(FileReadError):
            read_source_file(self.dir)


if __name__ == "__main__":
    unittest.main()
