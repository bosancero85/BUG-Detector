"""Unterstützte Sprachen und automatische Spracherkennung."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

AUTO = "auto"
JAVASCRIPT = "javascript"
TYPESCRIPT = "typescript"
PYTHON = "python"
JAVA = "java"
CSHARP = "csharp"
PHP = "php"
GO = "go"
C = "c"

LANGUAGES: List[Tuple[str, str]] = [
    (AUTO, "Automatisch"),
    (JAVASCRIPT, "JavaScript"),
    (TYPESCRIPT, "TypeScript"),
    (PYTHON, "Python"),
    (JAVA, "Java"),
    (CSHARP, "C#"),
    (PHP, "PHP"),
    (GO, "Go"),
    (C, "C / C++"),
]

EXTENSIONS = {
    "js": JAVASCRIPT,
    "mjs": JAVASCRIPT,
    "jsx": JAVASCRIPT,
    "ts": TYPESCRIPT,
    "tsx": TYPESCRIPT,
    "py": PYTHON,
    "pyw": PYTHON,
    "java": JAVA,
    "cs": CSHARP,
    "php": PHP,
    "go": GO,
    "c": C,
    "h": C,
    "cpp": C,
    "hpp": C,
}

_PY_HINT = re.compile(
    r"^\s*def\s+\w+\(.*\)\s*:|^\s*(from\s+\w+\s+)?import\s+\w+\s*$|\bprint\(",
    re.MULTILINE,
)
_JAVA_HINT = re.compile(r"\bpublic\s+(static\s+)?(class|void)|System\.out")
_PHP_HINT = re.compile(r"<\?php")


def label_for(language: str) -> str:
    """Anzeigename einer Sprache. Unbekannte Schlüssel werden unverändert zurückgegeben."""
    for key, label in LANGUAGES:
        if key == language:
            return label
    return language


def is_js(language: str) -> bool:
    return language in (JAVASCRIPT, TYPESCRIPT)


def is_python(language: str) -> bool:
    return language == PYTHON


def is_java(language: str) -> bool:
    return language == JAVA


def detect_language(code: str, filename: Optional[str] = None) -> str:
    """Erkennt die Sprache zuerst an der Dateiendung, danach am Inhalt."""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in EXTENSIONS:
            return EXTENSIONS[ext]
    if _PY_HINT.search(code):
        return PYTHON
    if _JAVA_HINT.search(code):
        return JAVA
    if _PHP_HINT.search(code):
        return PHP
    return JAVASCRIPT


def resolve_language(selected: str, code: str, filename: Optional[str] = None) -> str:
    """Gibt die gewählte Sprache zurück oder erkennt sie bei ``auto``."""
    if selected == AUTO or not selected:
        return detect_language(code, filename)
    return selected
