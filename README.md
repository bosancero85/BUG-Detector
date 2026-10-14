# 🐞 Bug Detector

Regelbasierter Code-Scanner mit grafischer Oberfläche. Der Scanner markiert problematische Zeilen
im Editor und erklärt zu jedem Fund das **Problem**, die **Root-Cause** und einen
**Lösungsvorschlag** zum Kopieren.

Läuft auf **Windows**, **macOS** und **Kali Linux** (PyQt6).

## Funktionen

- Editor mit Zeilennummern, Markierung nach Schweregrad (kritisch, Warnung, Info) und Sprung zur Fundstelle
- Datei öffnen (Strg+O) oder per Drag & Drop in den Editor ziehen (bis 1 MB)
- Automatische Spracherkennung (Dateiendung, dann Inhalt) oder manuelle Auswahl
- Statistik-Kacheln, die als Filter dienen
- Aufklappbare Fund-Karten mit Problem, Root-Cause und kopierbarem Lösungsvorschlag
- Verlauf der letzten 12 Scans, Klick lädt den Code und scannt erneut
- Scan läuft im Hintergrund, die Oberfläche bleibt bedienbar
- Hinweis „Code geändert – bitte erneut scannen“, sobald der Text nach einem Scan bearbeitet wird

## Installation

Voraussetzung: Python 3.9 oder neuer.

### Windows und macOS

```bash
cd bug-detector
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS:    source .venv/bin/activate
pip install -r requirements.txt
python3 -m bug_detector
```

### Kali Linux

Variante A, Systempaket (empfohlen):

```bash
sudo apt update
sudo apt install python3-pyqt6 libxcb-cursor0
python3 -m bug_detector
```

Variante B, virtuelle Umgebung:

```bash
sudo apt install python3-venv libxcb-cursor0
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m bug_detector
```

Fehlt `libxcb-cursor0`, bricht Qt unter X11 mit einer Meldung zum Plugin „xcb“ ab.

### Optional: als Befehl installieren

```bash
pip install .
bug-detector
```

## Bedienung

| Aktion | Bedienung |
|---|---|
| Scan starten | Button „Scan Code“, F5 oder Strg+Enter |
| Datei öffnen | Button „Datei öffnen“, Strg+O oder Drag & Drop |
| Beispiel laden | Button „Beispiel“ |
| Nach Schweregrad filtern | Klick auf eine Statistik-Kachel (erneut klicken hebt den Filter auf) |
| Zur Zeile springen | Fund-Karte aufklappen |
| Lösungsvorschlag kopieren | Button „Kopieren“ in der Karte |
| Datei direkt beim Start laden | `python -m bug_detector pfad/zur/datei.py` |

## Geprüfte Muster

| Sprache | Regeln |
|---|---|
| JavaScript, TypeScript | `eval`, `innerHTML`, `setInterval` ohne `clearInterval`, Listener ohne Entfernen, `==`, leerer `catch`, `var`, `console.log` |
| Python | `eval`/`exec`, nacktes `except`, veränderliche Standardwerte, `open` ohne `with`, `== None` |
| Java | String-Vergleich mit `==`, leerer `catch`, Stream ohne try-with-resources, `System.out.println` |
| Alle Sprachen | Fest eincodierte Geheimnisse, TODO/FIXME/HACK |
| Alle Sprachen | Klammerfehler (Syntax-Check) |
| Python | Fehlender Doppelpunkt nach Blockköpfen, ungenutzte Importe |
| JavaScript, TypeScript | Ungenutzte Variablen (`const`/`let`/`var`) |

C#, PHP, Go und C/C++ werden mit den sprachübergreifenden Regeln und dem Klammer-Check geprüft.

## Projektstruktur

```text
bug_detector/
├── core/            Logik ohne GUI
│   ├── models.py        Finding, Severity
│   ├── languages.py     Sprachen und Erkennung
│   ├── rules.py         Prüfregeln (hier neue Regeln ergänzen)
│   ├── analyzer.py      Analyse-Engine
│   ├── history.py       Verlauf (JSON, atomar gespeichert)
│   └── sample.py        Beispielcode
├── ui/              PyQt6-Oberfläche
│   ├── main_window.py   Hauptfenster
│   ├── code_editor.py   Editor mit Zeilennummern und Markierung
│   ├── result_panel.py  Statistik, Filter, Fund-Karten
│   ├── history_panel.py Verlauf-Seitenleiste
│   ├── worker.py        Scan im Hintergrund-Thread
│   ├── theme.py         Farben und Stylesheet
│   └── app.py           Anwendungsstart
└── utils/           Pfade und Dateizugriff
tests/               Unit-Tests
tools/check_code.py  Statische Prüfung ohne Fremdabhängigkeiten
playbook/            Projektsteuerung
```

`core/` importiert kein PyQt6 und ist dadurch ohne GUI testbar.

### Neue Regel hinzufügen

1. In `bug_detector/core/rules.py` einen `Rule(...)`-Eintrag an `build_rules()` anhängen.
2. In `tests/test_analyzer.py` einen Test ergänzen.
3. `python -m unittest discover -s tests` ausführen.

## Tests und Qualitätsprüfung

```bash
python -m unittest discover -s tests      # auch mit pytest möglich
python tools/check_code.py                # Syntax, Namen, Importe, Zeilenlänge
```

Der UI-Smoke-Test (`tests/test_ui_smoke.py`) läuft headless (`QT_QPA_PLATFORM=offscreen`) und wird
übersprungen, wenn PyQt6 fehlt. Die GitHub-Action in `.github/workflows/tests.yml` führt die
Kern-Tests unter Windows, macOS und Linux aus.

## Speicherort des Verlaufs

| System | Pfad |
|---|---|
| Windows | `%APPDATA%\BugDetector\history.json` |
| macOS | `~/Library/Application Support/BugDetector/history.json` |
| Linux / Kali | `~/.local/share/BugDetector/history.json` (bzw. `$XDG_DATA_HOME`) |

## Grenzen

Der Scanner arbeitet zeilenbasiert mit regulären Ausdrücken. Er ist ein schneller Helfer und
**kein Ersatz** für Linter, Compiler oder Code-Review. Fehlalarme und übersehene Fehler sind
möglich, zum Beispiel wenn Muster in Zeichenketten oder einzeiligen Docstrings vorkommen.

Gegenüber der HTML-Vorlage wurden diese Punkte angepasst:

- Der Scan läuft in einem Hintergrund-Thread ohne künstliche Wartezeit.
- Der Verlauf liegt als JSON-Datei im Nutzerordner statt im Browser-Speicher.
- TODO/FIXME werden auch in Kommentarzeilen erkannt.
- Python-Docstrings über mehrere Zeilen werden übersprungen.
- Importe mit Alias (`import numpy as np`) und `from __future__ import …` werden nicht fälschlich als ungenutzt gemeldet.
- Mehrzeilige Python-Bedingungen und Einzeiler (`if x: return`) lösen keinen „Doppelpunkt fehlt“-Fehler aus.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
