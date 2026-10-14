"""Prüfregeln. Neue Regeln werden ausschließlich hier in ``build_rules`` ergänzt."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, FrozenSet, List, Optional, Pattern

from bug_detector.core.languages import JAVA, JAVASCRIPT, PYTHON, TYPESCRIPT
from bug_detector.core.models import Severity

FixBuilder = Callable[[str], str]


@dataclass(frozen=True)
class Rule:
    """Eine zeilenbasierte Prüfregel.

    languages:   Sprachen, für die die Regel gilt. ``None`` bedeutet alle Sprachen.
    pattern:     Muster, das pro Zeile geprüft wird.
    unless:      Wenn dieses Muster irgendwo im Code vorkommt, wird die Regel übersprungen
                 (z. B. ``clearInterval`` bei der Regel zu ``setInterval``).
    in_comments: Regel gilt auch in Kommentarzeilen (z. B. TODO).
    fix:         Erzeugt den Lösungsvorschlag aus der getrimmten Zeile.
    """

    rule_id: str
    severity: Severity
    title: str
    pattern: Pattern[str]
    problem: str
    root_cause: str
    fix: FixBuilder
    languages: Optional[FrozenSet[str]] = None
    unless: Optional[Pattern[str]] = None
    in_comments: bool = False

    def applies_to(self, language: str) -> bool:
        return self.languages is None or language in self.languages


_JS = frozenset({JAVASCRIPT, TYPESCRIPT})
_PY = frozenset({PYTHON})
_JV = frozenset({JAVA})


def _const(text: str) -> FixBuilder:
    """Fix-Baustein, der unabhängig von der Zeile immer denselben Text liefert."""
    return lambda _line: text


def _sub_first(pattern: str, repl: str) -> FixBuilder:
    return lambda line: re.sub(pattern, repl, line, count=1)


def _python_none_compare(line: str) -> str:
    line = re.sub(r"==\s*None", "is None", line, count=1)
    return re.sub(r"!=\s*None", "is not None", line, count=1)


def _python_mutable_default(line: str) -> str:
    fixed = re.sub(r"=\s*(\[\]|\{\})", "=None", line, count=1)
    return fixed + "\n    # im Rumpf: items = [] if items is None else items"


def _secret_fix(line: str) -> str:
    return re.sub(
        r"([\"'])[^\"']{6,}\1",
        lambda _m: 'process.env.SECRET /* oder os.environ["SECRET"] */',
        line,
        count=1,
    )


def _java_equals(line: str) -> str:
    return re.sub(r'(\w+)\s*==\s*("[^"]*")', r"\2.equals(\1)", line, count=1)


def build_rules() -> List[Rule]:
    """Erzeugt die vollständige Regelliste (Reihenfolge = Prüfreihenfolge)."""
    return [
        # ------------------------------------------------------------ JavaScript / TypeScript
        Rule(
            "js-eval", Severity.CRITICAL, "Unsicheres eval()",
            re.compile(r"\beval\s*\("),
            "eval() führt Text als Programmcode aus. Kommt der Text von außen, kann ein "
            "Angreifer eigenen Code einschleusen.",
            "Daten werden mit Code verwechselt: Es gibt keine Trennung zwischen Eingabe "
            "und Programmlogik.",
            _const("const data = JSON.parse(input); // statt eval(input)"),
            languages=_JS,
        ),
        Rule(
            "js-innerhtml", Severity.CRITICAL, "XSS-Risiko durch innerHTML",
            re.compile(r"\.innerHTML\s*="),
            "Der zugewiesene Text wird als HTML interpretiert. Enthält er Skript-Tags oder "
            "Event-Attribute, läuft fremder Code im Browser.",
            "Ungeprüfte Daten gelangen in einen HTML-Kontext.",
            _sub_first(r"\.innerHTML\s*=", ".textContent ="),
            languages=_JS,
        ),
        Rule(
            "js-setinterval", Severity.WARNING,
            "Möglicher Memory Leak: setInterval ohne clearInterval",
            re.compile(r"\bsetInterval\s*\("),
            "Der Timer läuft weiter, auch wenn das Element oder die Seite nicht mehr "
            "gebraucht wird. Jede Runde hält Referenzen im Speicher.",
            "Die Timer-ID wird nicht gemerkt und der Timer nie gestoppt.",
            _const("const id = setInterval(tick, 1000);\n// beim Aufräumen:\nclearInterval(id);"),
            languages=_JS,
            unless=re.compile(r"clearInterval"),
        ),
        Rule(
            "js-listener-leak", Severity.WARNING,
            "Möglicher Memory Leak: Event-Listener nie entfernt",
            re.compile(r"\.addEventListener\s*\("),
            "Der Listener hält seine Funktion und alles, was sie referenziert, im Speicher, "
            "solange das Ziel existiert.",
            "Registrierung ohne Gegenstück zum Entfernen.",
            _const(
                "const onResize = () => render();\n"
                'window.addEventListener("resize", onResize);\n'
                "// beim Aufräumen:\n"
                'window.removeEventListener("resize", onResize);'
            ),
            languages=_JS,
            unless=re.compile(r"removeEventListener|AbortController"),
        ),
        Rule(
            "js-loose-equals", Severity.WARNING, "Lockerer Vergleich mit ==",
            re.compile(r"[^=!<>]==[^=]"),
            '== wandelt Typen still um: 0 == "" und null == undefined sind true. '
            "Das erzeugt schwer auffindbare Logikfehler.",
            "Implizite Typumwandlung statt eines strikten Vergleichs.",
            lambda line: re.sub(r"([^=!<>])==([^=])", r"\1===\2", line),
            languages=_JS,
        ),
        Rule(
            "js-empty-catch", Severity.WARNING, "Leerer catch-Block",
            re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}"),
            "Fehler werden verschluckt. Das Programm läuft scheinbar normal weiter, der "
            "Fehler bleibt unsichtbar.",
            "Die Fehlerbehandlung fehlt komplett.",
            _const(
                "catch (e) {\n"
                '  console.error("Laden fehlgeschlagen:", e);\n'
                "  // Nutzer informieren oder sauber abbrechen\n"
                "}"
            ),
            languages=_JS,
        ),
        Rule(
            "js-var", Severity.INFO, "var statt let/const",
            re.compile(r"\bvar\s+\w"),
            "var gilt für die ganze Funktion und wird hochgezogen (Hoisting). Das führt zu "
            "überraschenden Werten.",
            "Veraltete Deklaration ohne Block-Gültigkeitsbereich.",
            _sub_first(r"\bvar\b", "const"),
            languages=_JS,
        ),
        Rule(
            "js-console-log", Severity.INFO, "console.log im Code",
            re.compile(r"\bconsole\.log\s*\("),
            "Debug-Ausgaben gehören nicht in produktiven Code. Sie verlangsamen und können "
            "interne Daten preisgeben.",
            "Testcode wurde nicht entfernt.",
            _const("// Zeile entfernen oder ein Logging-Modul mit Log-Level verwenden"),
            languages=_JS,
        ),
        # ------------------------------------------------------------------------- Python
        Rule(
            "py-eval-exec", Severity.CRITICAL, "Unsicheres eval()/exec()",
            re.compile(r"\b(eval|exec)\s*\("),
            "Der übergebene Text wird als Python-Code ausgeführt. Bei fremden Eingaben ist "
            "das eine Codeausführung aus der Ferne.",
            "Eingabe und Programmlogik sind nicht getrennt.",
            _const("import ast\nvalue = ast.literal_eval(text)  # nur Literale, kein Code"),
            languages=_PY,
        ),
        Rule(
            "py-bare-except", Severity.WARNING, "Nacktes except",
            re.compile(r"^\s*except\s*:"),
            "Fängt alles, auch KeyboardInterrupt und SystemExit. Echte Fehler gehen unter.",
            "Die erwartete Ausnahme wird nicht benannt.",
            _const("except (ValueError, KeyError) as exc:\n    logging.exception(exc)"),
            languages=_PY,
        ),
        Rule(
            "py-mutable-default", Severity.WARNING, "Veränderlicher Standardwert",
            re.compile(r"def\s+\w+\([^)]*=\s*(\[\]|\{\})"),
            "Der Standardwert wird einmal beim Definieren angelegt und zwischen allen "
            "Aufrufen geteilt.",
            "Listen und Dictionaries sind veränderlich.",
            _python_mutable_default,
            languages=_PY,
        ),
        Rule(
            "py-open-without-with", Severity.WARNING,
            "Datei ohne with geöffnet (Resource Leak)",
            re.compile(r"^(?!\s*with\b).*\bopen\s*\("),
            "Wird die Datei nicht geschlossen, bleibt der Handle offen, besonders bei Fehlern.",
            "Das Schließen hängt vom Programmfluss ab statt von einem Kontext.",
            _const('with open(path, encoding="utf-8") as fh:\n    data = fh.read()'),
            languages=_PY,
            unless=re.compile(r"\.close\(\)"),
        ),
        Rule(
            "py-none-equals", Severity.INFO, "Vergleich mit None über ==",
            re.compile(r"[=!]=\s*None\b"),
            "None ist ein Singleton. Der Vergleich per is ist korrekt und schneller.",
            "Gleichheit statt Identität.",
            _python_none_compare,
            languages=_PY,
        ),
        # --------------------------------------------------------------------------- Java
        Rule(
            "java-string-equals", Severity.WARNING, "String-Vergleich mit ==",
            re.compile(r'"[^"]*"\s*[=!]=|[=!]=\s*"'),
            "== vergleicht Referenzen, nicht den Inhalt. Das Ergebnis hängt vom String-Pool ab.",
            "Verwechslung von Objekt-Identität und Gleichheit.",
            _java_equals,
            languages=_JV,
        ),
        Rule(
            "java-empty-catch", Severity.WARNING, "Leerer catch-Block",
            re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"),
            "Die Exception wird verschluckt.",
            "Es gibt keine Fehlerbehandlung.",
            _const(
                "catch (IOException e) {\n"
                '    logger.error("Lesen fehlgeschlagen", e);\n'
                "}"
            ),
            languages=_JV,
        ),
        Rule(
            "java-stream-leak", Severity.WARNING, "Stream nicht geschlossen (Resource Leak)",
            re.compile(
                r"^(?!.*\btry\s*\().*new\s+(FileInputStream|FileReader|Scanner|BufferedReader)\s*\("
            ),
            "Der Datei-Handle bleibt offen, bis der Garbage Collector zufällig aufräumt.",
            "Kein try-with-resources.",
            _const("try (var in = new FileInputStream(path)) {\n    // lesen\n}"),
            languages=_JV,
            unless=re.compile(r"\.close\(\)"),
        ),
        Rule(
            "java-println", Severity.INFO, "System.out.println im Code",
            re.compile(r"System\.out\.println|printStackTrace\s*\("),
            "Konsolenausgaben sind kein Logging.",
            "Debugcode blieb stehen.",
            _const(
                "private static final Logger log = LoggerFactory.getLogger(Main.class);\n"
                'log.info("...");'
            ),
            languages=_JV,
        ),
        # ------------------------------------------------------------- Alle Sprachen
        Rule(
            "all-hardcoded-secret", Severity.CRITICAL, "Fest eincodiertes Geheimnis",
            re.compile(
                r"(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*[\"'][^\"']{6,}[\"']",
                re.IGNORECASE,
            ),
            "Zugangsdaten im Quelltext landen in Versionsverwaltung, Builds und Logs.",
            "Konfiguration und Code sind nicht getrennt.",
            _secret_fix,
        ),
        Rule(
            "all-todo", Severity.INFO, "Offener TODO/FIXME-Kommentar",
            re.compile(r"\b(TODO|FIXME|HACK)\b"),
            "Ein bekannter offener Punkt steht noch im Code.",
            "Aufgabe nicht erledigt oder nicht im Ticketsystem erfasst.",
            _const("// Ticket anlegen und hier die Nummer eintragen"),
            in_comments=True,
        ),
    ]


RULES: List[Rule] = build_rules()
