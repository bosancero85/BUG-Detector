"""Analyse-Engine: wendet Regeln an und prüft Syntax-Grundlagen."""

from __future__ import annotations

import re
from typing import Callable, List, Optional, Set, Tuple

from bug_detector.core.languages import is_python
from bug_detector.core.models import Finding, Severity
from bug_detector.core.rules import RULES, Rule

ProgressCallback = Callable[[int, int], None]

_STRING_LITERAL = re.compile(r"([\"'`])(?:\\.|(?!\1).)*\1")
_PY_COMMENT = re.compile(r"#.*")
_C_COMMENT = re.compile(r"//.*")
_TRIPLE_QUOTE = re.compile(r"\"\"\"|'''")

_CLOSERS = {")": "(", "]": "[", "}": "{"}
_OPENERS = "([{"

_PY_BLOCK_HEAD = re.compile(
    r"^\s*(def|if|elif|else|for|while|class|try|except|finally|with)\b"
    r"[^#]*[^:\s#(\[{,\\]\s*(#.*)?$"
)
_PY_BARE_BLOCK = re.compile(r"^\s*(else|try|finally)\s*$")
_BRACKET_GROUP = re.compile(r"\([^()]*\)|\[[^\[\]]*\]|\{[^{}]*\}")

_JS_DECL = re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=")
_PY_IMPORT = re.compile(
    r"^\s*(?:import\s+(\w+)(?:\s+as\s+(\w+))?"
    r"|from\s+(\S+)\s+import\s+(\w+)(?:\s+as\s+(\w+))?)"
)


_BRACKET_FIX = "// Fehlende Klammer ergänzen, z. B.:\nif (cart.length > 0) {\n  return cart;\n}"


def strip_literals(line: str, language: str) -> str:
    """Entfernt String-Inhalte und Zeilenkommentare, damit Klammern darin nicht zählen."""
    line = _STRING_LITERAL.sub('""', line)
    return (_PY_COMMENT if is_python(language) else _C_COMMENT).sub("", line)


def is_comment_line(line: str, language: str) -> bool:
    if is_python(language):
        return line.lstrip().startswith("#")
    stripped = line.lstrip()
    return stripped.startswith(("//", "*", "/*"))


def triple_quoted_lines(lines: List[str]) -> Set[int]:
    """Indizes (0-basiert) von Zeilen, die vollständig in einem Python-Docstring liegen."""
    inside: Set[int] = set()
    delimiter: Optional[str] = None
    for index, line in enumerate(lines):
        started_inside = delimiter is not None
        pos = 0
        while True:
            if delimiter is None:
                match = _TRIPLE_QUOTE.search(line, pos)
                if not match:
                    break
                delimiter = match.group(0)
                pos = match.end()
            else:
                end = line.find(delimiter, pos)
                if end == -1:
                    if started_inside:
                        inside.add(index)
                    break
                delimiter = None
                pos = end + 3
    return inside


def _skip_set(lines: List[str], language: str) -> Set[int]:
    return triple_quoted_lines(lines) if is_python(language) else set()


def find_unbalanced_bracket(
    lines: List[str], language: str, skip: Set[int]
) -> Optional[Tuple[str, int]]:
    """Liefert (Klammer, Zeilennummer) der ersten falsch gesetzten Klammer oder ``None``."""
    stack: List[Tuple[str, int]] = []
    for index, line in enumerate(lines):
        if index in skip or is_comment_line(line, language):
            continue
        for char in strip_literals(line, language):
            if char in _OPENERS:
                stack.append((char, index + 1))
            elif char in _CLOSERS:
                top = stack.pop() if stack else None
                if top is None:
                    return char, index + 1
                if top[0] != _CLOSERS[char]:
                    return top
    return stack[-1] if stack else None


def _bracket_depths(lines: List[str], language: str, skip: Set[int]) -> List[Tuple[int, int]]:
    """Pro Zeile: (Tiefe am Zeilenanfang, Netto-Änderung der Zeile)."""
    depth = 0
    result: List[Tuple[int, int]] = []
    for index, line in enumerate(lines):
        before = depth
        if index not in skip and not is_comment_line(line, language):
            for char in strip_literals(line, language):
                if char in _OPENERS:
                    depth += 1
                elif char in _CLOSERS:
                    depth = max(0, depth - 1)
        result.append((before, depth - before))
    return result


def _has_top_level_colon(stripped: str) -> bool:
    """Prüft auf ':' außerhalb von Klammern (z. B. Einzeiler ``if x: return``)."""
    previous = None
    while previous != stripped:
        previous = stripped
        stripped = _BRACKET_GROUP.sub("", stripped)
    return ":" in stripped


def find_missing_colons(lines: List[str], skip: Set[int]) -> List[int]:
    """Zeilennummern von Python-Blockköpfen ohne abschließenden Doppelpunkt."""
    depths = _bracket_depths(lines, "python", skip)
    hits: List[int] = []
    for index, line in enumerate(lines):
        if index in skip or is_comment_line(line, "python"):
            continue
        before, net = depths[index]
        if before != 0 or net > 0:
            continue  # Anweisung läuft über mehrere Zeilen weiter
        bare = bool(_PY_BARE_BLOCK.match(line))
        head = bool(_PY_BLOCK_HEAD.match(line)) and not bare
        if not (bare or head):
            continue
        if head and _has_top_level_colon(strip_literals(line, "python")):
            continue
        hits.append(index + 1)
    return hits


def find_unused_names(
    code: str, lines: List[str], language: str, skip: Set[int]
) -> List[Tuple[str, int]]:
    """Findet importierte bzw. deklarierte Namen, die im gesamten Code nur einmal vorkommen."""
    hits: List[Tuple[str, int]] = []
    for index, line in enumerate(lines):
        if index in skip or is_comment_line(line, language):
            continue
        name = _declared_name(line, language)
        if not name:
            continue
        if len(re.findall(r"\b" + re.escape(name) + r"\b", code)) == 1:
            hits.append((name, index + 1))
    return hits


def _declared_name(line: str, language: str) -> Optional[str]:
    if is_python(language):
        match = _PY_IMPORT.match(line)
        if not match:
            return None
        if match.group(1):
            return match.group(2) or match.group(1)
        if match.group(3) == "__future__":
            return None
        return match.group(5) or match.group(4)
    match = _JS_DECL.search(line)
    return match.group(1) if match else None


def _rule_findings(rule: Rule, lines: List[str], language: str, skip: Set[int]) -> List[Finding]:
    found: List[Finding] = []
    for index, line in enumerate(lines):
        if index in skip:
            continue
        if not rule.in_comments and is_comment_line(line, language):
            continue
        if rule.pattern.search(line):
            found.append(
                Finding(
                    severity=rule.severity,
                    title=rule.title,
                    line=index + 1,
                    problem=rule.problem,
                    root_cause=rule.root_cause,
                    fix=rule.fix(line.strip()),
                    rule_id=rule.rule_id,
                )
            )
    return found


def analyze(
    code: str,
    language: str,
    progress: Optional[ProgressCallback] = None,
) -> List[Finding]:
    """Analysiert Quelltext und gibt nach Schweregrad und Zeile sortierte Funde zurück.

    ``progress(erledigt, gesamt)`` wird nach jedem Prüfschritt aufgerufen.
    """
    lines = code.split("\n")
    skip = _skip_set(lines, language)
    rules = [r for r in RULES if r.applies_to(language)]
    total = len(rules) + 3
    done = 0
    findings: List[Finding] = []

    def tick() -> None:
        nonlocal done
        done += 1
        if progress:
            progress(done, total)

    for rule in rules:
        if not (rule.unless and rule.unless.search(code)):
            findings.extend(_rule_findings(rule, lines, language, skip))
        tick()

    bad = find_unbalanced_bracket(lines, language, skip)
    if bad:
        findings.append(
            Finding(
                severity=Severity.CRITICAL,
                title="Syntaxfehler: Klammer „%s“ nicht korrekt geschlossen" % bad[0],
                line=bad[1],
                problem="Der Parser kann die Datei nicht lesen. Das Programm startet nicht.",
                root_cause="Eine öffnende Klammer hat kein passendes Gegenstück.",
                fix=_BRACKET_FIX,
                rule_id="syntax-bracket",
            )
        )
    tick()

    if is_python(language):
        for line_no in find_missing_colons(lines, skip):
            findings.append(
                Finding(
                    severity=Severity.CRITICAL,
                    title="Syntaxfehler: Doppelpunkt fehlt",
                    line=line_no,
                    problem="Python verlangt nach Kopfzeilen von Blöcken einen Doppelpunkt.",
                    root_cause="Die Blockeinleitung ist unvollständig.",
                    fix=lines[line_no - 1].strip() + ":",
                    rule_id="syntax-colon",
                )
            )
    tick()

    for name, line_no in find_unused_names(code, lines, language, skip):
        kind = "Ungenutzter Import" if is_python(language) else "Ungenutzte Variable"
        findings.append(
            Finding(
                severity=Severity.INFO,
                title="%s „%s“" % (kind, name),
                line=line_no,
                problem="„%s“ wird nirgends gelesen. Das ist toter Code und verwirrt Leser."
                % name,
                root_cause="Rest einer Änderung oder ein Tippfehler im späteren Namen.",
                fix="// Zeile %d entfernen (oder die Variable tatsächlich verwenden)" % line_no,
                rule_id="unused-name",
            )
        )
    tick()

    findings.sort(key=lambda f: (f.severity.rank, f.line))
    return findings
