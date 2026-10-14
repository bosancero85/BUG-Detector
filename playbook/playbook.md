# Playbook – Bug Detector

## Arbeitsweise
1. Verbindliche Checkliste (siehe `fertige_definition.md`) von oben nach unten abarbeiten.
2. Keine Schritte überspringen oder zusammenfassen.
3. Ein Punkt gilt erst als erledigt `[X]`, wenn das Ergebnis vollständig und fehlerfrei ist.
4. Nach größeren Schritten wird der Status gezeigt.
5. Abschluss erst, wenn alle Punkte `[X]` sind.

## Architekturregeln
- `core/` importiert nie PyQt6. Dadurch ist die Logik ohne GUI testbar.
- `ui/` enthält keine Analyse-Logik, nur Darstellung und Ablauf.
- Dateizugriff und Pfade liegen ausschließlich in `utils/`.
- Neue Prüfregeln werden nur in `core/rules.py` ergänzt (ein `Rule`-Eintrag plus ein Test).

## Neue Regel hinzufügen
1. `Rule(...)` in `core/rules.py` an `build_rules()` anhängen.
2. Test in `tests/test_analyzer.py` ergänzen.
3. `python -m unittest discover -s tests` ausführen.

## Plattformhinweise
- Windows und macOS: `pip install -r requirements.txt`.
- Kali Linux: `sudo apt install python3-pyqt6` oder venv mit pip. Bei Qt-xcb-Fehlern `sudo apt install libxcb-cursor0`.
