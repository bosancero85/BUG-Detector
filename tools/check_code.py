"""Einfache statische Qualitätsprüfung ohne Fremdabhängigkeiten.

Prüft pro Datei: Syntax, nicht definierte Namen, ungenutzte Importe, Zeilenlänge,
Tabs und Leerzeichen am Zeilenende.

Aufruf:  python tools/check_code.py [Ordner ...]
"""

from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path
from typing import Dict, List, Set

MAX_LINE = 100


def _bound_names(tree: ast.AST) -> Set[str]:
    names: Set[str] = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            if not isinstance(node, ast.ClassDef):
                args = node.args
                for arg in args.posonlyargs + args.args + args.kwonlyargs:
                    names.add(arg.arg)
                for extra in (args.vararg, args.kwarg):
                    if extra:
                        names.add(extra.arg)
        elif isinstance(node, ast.Lambda):
            for arg in node.args.args + node.args.kwonlyargs:
                names.add(arg.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
    return names


def _imported(tree: ast.Module) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                result[(alias.asname or alias.name).split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            for alias in node.names:
                result[alias.asname or alias.name] = node.lineno
    return result


def check_file(path: Path) -> List[str]:
    problems: List[str] = []
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, str(path))
    except SyntaxError as exc:
        return ["%s:%s: Syntaxfehler: %s" % (path, exc.lineno, exc.msg)]

    bound = _bound_names(tree)
    used: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
            if node.id not in bound:
                problems.append("%s:%d: Name nicht definiert: %s" % (path, node.lineno, node.id))
    # Namen in String-Annotationen und __all__ zählen als benutzt
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            used.add(node.value.strip("'\" "))
    exported = path.name == "__init__.py"
    if not exported:
        for name, line in _imported(tree).items():
            if name not in used:
                problems.append("%s:%d: Import ungenutzt: %s" % (path, line, name))

    for number, text in enumerate(source.split("\n"), 1):
        if len(text) > MAX_LINE:
            problems.append("%s:%d: Zeile länger als %d Zeichen" % (path, number, MAX_LINE))
        if "\t" in text:
            problems.append("%s:%d: Tabulator" % (path, number))
        if text != text.rstrip():
            problems.append("%s:%d: Leerzeichen am Zeilenende" % (path, number))
    if source and not source.endswith("\n"):
        problems.append("%s: Datei endet ohne Zeilenumbruch" % path)
    return problems


def main(argv: List[str]) -> int:
    roots = [Path(a) for a in argv] or [Path("bug_detector"), Path("tests"), Path("tools")]
    files = sorted(p for root in roots for p in root.rglob("*.py"))
    problems: List[str] = []
    for file in files:
        problems.extend(check_file(file))
    for line in problems:
        print(line)
    print("%d Dateien geprüft, %d Probleme" % (len(files), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
