import unittest

from bug_detector.core.analyzer import (
    analyze,
    find_missing_colons,
    find_unbalanced_bracket,
    triple_quoted_lines,
)
from bug_detector.core.models import Severity, count_by_severity, worst_severity_per_line
from bug_detector.core.sample import SAMPLE_CODE


def ids(findings):
    return {(f.rule_id, f.line) for f in findings}


def rule_ids(findings):
    return {f.rule_id for f in findings}


class SampleTest(unittest.TestCase):
    def setUp(self):
        self.findings = analyze(SAMPLE_CODE, "javascript")

    def test_expected_findings(self):
        expected = {
            ("js-eval", 6),
            ("all-hardcoded-secret", 13),
            ("js-innerhtml", 17),
            ("syntax-bracket", 25),
            ("js-loose-equals", 7),
            ("js-setinterval", 16),
            ("js-listener-leak", 19),
            ("js-empty-catch", 22),
            ("js-var", 2),
            ("js-var", 3),
            ("js-console-log", 8),
            ("unused-name", 3),
            ("unused-name", 13),
        }
        self.assertEqual(ids(self.findings), expected)

    def test_sorted_by_severity_then_line(self):
        keys = [(f.severity.rank, f.line) for f in self.findings]
        self.assertEqual(keys, sorted(keys))

    def test_counts(self):
        counts = count_by_severity(self.findings)
        self.assertEqual(counts[Severity.CRITICAL], 4)
        self.assertEqual(counts[Severity.WARNING], 4)
        self.assertEqual(counts[Severity.INFO], 5)

    def test_bracket_message_names_bracket(self):
        bracket = next(f for f in self.findings if f.rule_id == "syntax-bracket")
        self.assertIn("„(“", bracket.title)

    def test_worst_severity_per_line(self):
        marks = worst_severity_per_line(self.findings)
        self.assertEqual(marks[3], Severity.INFO)
        self.assertEqual(marks[6], Severity.CRITICAL)
        self.assertEqual(marks[13], Severity.CRITICAL)  # Geheimnis schlägt ungenutzte Variable


class GeneralTest(unittest.TestCase):
    def test_clean_code(self):
        code = "const a = 1;\nconsole.error(a);\n"
        self.assertEqual(analyze(code, "javascript"), [])

    def test_empty_code(self):
        self.assertEqual(analyze("", "javascript"), [])

    def test_progress_reaches_total_monotonic(self):
        calls = []
        analyze("var a = 1;\n", "python", lambda d, t: calls.append((d, t)))
        self.assertTrue(calls)
        self.assertEqual(calls[-1][0], calls[-1][1])
        self.assertEqual([c[0] for c in calls], sorted(c[0] for c in calls))

    def test_comment_lines_skipped(self):
        self.assertEqual(analyze("// eval(x)\n/* var a = 1 */\n * eval(y)\n", "javascript"), [])

    def test_typescript_uses_js_rules(self):
        self.assertIn("js-eval", rule_ids(analyze("eval(x);\n", "typescript")))

    def test_python_rules_not_applied_to_js(self):
        self.assertNotIn("py-bare-except", rule_ids(analyze("except:\n", "javascript")))

    def test_generic_rules_apply_to_other_languages(self):
        code = 'password = "hunter2hunter2"\n'
        self.assertIn("all-hardcoded-secret", rule_ids(analyze(code, "go")))

    def test_todo_in_comment_flagged(self):
        code = "// TODO: aufräumen\n# FIXME later\n"
        found = [f for f in analyze(code, "go") if f.rule_id == "all-todo"]
        self.assertEqual(len(found), 2)

    def test_unless_clause(self):
        code = "const id = setInterval(f, 1);\nclearInterval(id);\n"
        self.assertNotIn("js-setinterval", rule_ids(analyze(code, "javascript")))


class FixTest(unittest.TestCase):
    def fix_for(self, code, language, rule_id):
        return next(f.fix for f in analyze(code, language) if f.rule_id == rule_id)

    def test_innerhtml(self):
        fix = self.fix_for("el.innerHTML = x;\n", "javascript", "js-innerhtml")
        self.assertEqual(fix, "el.textContent = x;")

    def test_loose_equals(self):
        fix = self.fix_for("if (a == b) {}\n", "javascript", "js-loose-equals")
        self.assertEqual(fix, "if (a === b) {}")

    def test_var(self):
        fix = self.fix_for("var q = 1;\n", "javascript", "js-var")
        self.assertEqual(fix, "const q = 1;")

    def test_python_none(self):
        fix = self.fix_for("if x == None:\n    pass\n", "python", "py-none-equals")
        self.assertEqual(fix, "if x is None:")
        fix = self.fix_for("if x != None:\n    pass\n", "python", "py-none-equals")
        self.assertEqual(fix, "if x is not None:")

    def test_python_mutable_default(self):
        fix = self.fix_for("def f(a, items=[]):\n    pass\n", "python", "py-mutable-default")
        self.assertIn("items=None", fix)
        self.assertIn("is None", fix)

    def test_java_equals(self):
        fix = self.fix_for('if (name == "x") {}\n', "java", "java-string-equals")
        self.assertEqual(fix, 'if ("x".equals(name)) {}')

    def test_secret_fix_replaces_literal(self):
        fix = self.fix_for('api_key = "abcdef123"\n', "python", "all-hardcoded-secret")
        self.assertNotIn("abcdef123", fix)


class PythonTest(unittest.TestCase):
    def test_rules(self):
        code = (
            "import os\n"
            "def f(x, acc=[]):\n"
            "    try:\n"
            "        v = eval(x)\n"
            "    except:\n"
            "        pass\n"
            "    fh = open('a.txt')\n"
            "    if v == None:\n"
            "        return fh\n"
        )
        found = rule_ids(analyze(code, "python"))
        self.assertTrue(
            {"py-eval-exec", "py-bare-except", "py-mutable-default",
             "py-open-without-with", "py-none-equals", "unused-name"} <= found
        )

    def test_open_with_close_not_flagged(self):
        code = "fh = open('a')\nfh.close()\n"
        self.assertNotIn("py-open-without-with", rule_ids(analyze(code, "python")))

    def test_with_open_not_flagged(self):
        code = "with open('a') as fh:\n    pass\n"
        self.assertNotIn("py-open-without-with", rule_ids(analyze(code, "python")))

    def test_import_alias_used(self):
        code = "import numpy as np\nprint(np.zeros(1))\n"
        self.assertNotIn("unused-name", rule_ids(analyze(code, "python")))

    def test_import_alias_unused(self):
        code = "import numpy as np\nprint(1)\n"
        found = [f for f in analyze(code, "python") if f.rule_id == "unused-name"]
        self.assertEqual(len(found), 1)
        self.assertIn("np", found[0].title)

    def test_future_import_not_flagged(self):
        code = "from __future__ import annotations\nprint(1)\n"
        self.assertNotIn("unused-name", rule_ids(analyze(code, "python")))

    def test_from_import_used(self):
        code = "from os import path\nprint(path)\n"
        self.assertNotIn("unused-name", rule_ids(analyze(code, "python")))


class ColonTest(unittest.TestCase):
    def lines(self, code):
        lines = code.split("\n")
        return find_missing_colons(lines, triple_quoted_lines(lines))

    def test_missing_colon(self):
        self.assertEqual(self.lines("def f()\n    pass\nif x\n    pass"), [1, 3])

    def test_bare_else(self):
        self.assertEqual(self.lines("if x:\n    pass\nelse\n    pass"), [3])

    def test_valid_blocks(self):
        code = (
            "def f(a):\n    if a:\n        pass\n    else:\n        pass\n"
            "class A(B):  # c\n    pass"
        )
        self.assertEqual(self.lines(code), [])

    def test_one_liner_not_flagged(self):
        self.assertEqual(self.lines("if x: return 1\nfor i in y: print(i)"), [])

    def test_multiline_condition_not_flagged(self):
        code = "if (a and\n        b):\n    pass\nx = [i\n     for i in y\n     if i]"
        self.assertEqual(self.lines(code), [])

    def test_docstring_text_ignored(self):
        code = 'def f():\n    """\n    if the value is None\n    for each item\n    """\n    pass'
        self.assertEqual(self.lines(code), [])

    def test_dict_colon_in_brackets_does_not_hide_error(self):
        self.assertEqual(self.lines("if d[1:2] == y\n    pass"), [1])

    def test_integration_via_analyze(self):
        found = analyze("def f()\n    pass\n", "python")
        self.assertIn(("syntax-colon", 1), ids(found))


class DocstringTest(unittest.TestCase):
    def test_masks_inner_lines_only(self):
        lines = ['x = 1', '"""start', 'inside', 'end"""', 'y = 2']
        self.assertEqual(triple_quoted_lines(lines), {2})

    def test_single_line_docstring(self):
        self.assertEqual(triple_quoted_lines(['"""kurz"""', "x = 1"]), set())

    def test_eval_in_docstring_not_flagged(self):
        code = 'def f():\n    """Hinweis\n    Nutze niemals eval(x) hier.\n    """\n    return 1\n'
        self.assertNotIn("py-eval-exec", rule_ids(analyze(code, "python")))


class JavaTest(unittest.TestCase):
    def test_rules(self):
        code = (
            'if (name == "x") {}\n'
            "try { run(); } catch (Exception e) {}\n"
            "FileReader r = new FileReader(path);\n"
            'System.out.println("x");\n'
        )
        found = rule_ids(analyze(code, "java"))
        self.assertTrue(
            {"java-string-equals", "java-empty-catch", "java-stream-leak", "java-println"} <= found
        )

    def test_try_with_resources_not_flagged(self):
        code = "try (FileReader r = new FileReader(path)) {\n}\n"
        self.assertNotIn("java-stream-leak", rule_ids(analyze(code, "java")))


class BracketTest(unittest.TestCase):
    def check(self, code, language="javascript"):
        return find_unbalanced_bracket(code.split("\n"), language, set())

    def test_balanced(self):
        self.assertIsNone(self.check("f(a[1], {b: 2});"))

    def test_unclosed(self):
        self.assertEqual(self.check("a\nf(1,\n"), ("(", 2))

    def test_stray_closer(self):
        self.assertEqual(self.check("x = 1;\n}"), ("}", 2))

    def test_mismatch(self):
        self.assertEqual(self.check("f(]"), ("(", 1))

    def test_brackets_in_strings_and_comments_ignored(self):
        self.assertIsNone(self.check('x = "(";  // )'))
        self.assertIsNone(self.check("x = '[';  # ]", "python"))


if __name__ == "__main__":
    unittest.main()
