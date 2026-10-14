import unittest

from bug_detector.core.languages import (
    AUTO,
    JAVA,
    JAVASCRIPT,
    LANGUAGES,
    PHP,
    PYTHON,
    detect_language,
    label_for,
    resolve_language,
)


class LanguageTest(unittest.TestCase):
    def test_by_extension(self):
        self.assertEqual(detect_language("", "a.PY"), PYTHON)
        self.assertEqual(detect_language("", "app.tsx"), "typescript")
        self.assertEqual(detect_language("", "Main.java"), JAVA)
        self.assertEqual(detect_language("", "x.hpp"), "c")

    def test_extension_beats_content(self):
        self.assertEqual(detect_language("def f():\n  pass", "a.js"), JAVASCRIPT)

    def test_by_content(self):
        self.assertEqual(detect_language("def f(x):\n    return x"), PYTHON)
        self.assertEqual(detect_language("print('x')"), PYTHON)
        self.assertEqual(detect_language("public class A {}"), JAVA)
        self.assertEqual(detect_language("<?php echo 1;"), PHP)

    def test_default_is_javascript(self):
        self.assertEqual(detect_language("let a = 1;"), JAVASCRIPT)
        self.assertEqual(detect_language("x", "README"), JAVASCRIPT)
        self.assertEqual(detect_language("x", "archive.unknown"), JAVASCRIPT)

    def test_resolve(self):
        self.assertEqual(resolve_language(AUTO, "def f():\n pass", None), PYTHON)
        self.assertEqual(resolve_language(JAVA, "def f():\n pass", None), JAVA)
        self.assertEqual(resolve_language("", "let a", None), JAVASCRIPT)

    def test_labels(self):
        self.assertEqual(label_for("csharp"), "C#")
        self.assertEqual(label_for("zzz"), "zzz")
        self.assertEqual(LANGUAGES[0][0], AUTO)


if __name__ == "__main__":
    unittest.main()
