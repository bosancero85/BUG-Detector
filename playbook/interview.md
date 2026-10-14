# Interview / Annahmen

Auftrag: Bug_Detector.html als voll funktionsfähiges, strukturiert und modular aufgebautes Python-Projekt mit benutzerfreundlicher UI für Windows, macOS und Kali Linux.

| Frage | Festlegung |
|---|---|
| Vorlage | Bug_Detector.html (Regel-Scanner, Verlauf, Editor mit Gutter) |
| UI-Framework | PyQt6, nativ auf allen drei Systemen |
| Sprache der Oberfläche | Deutsch (wie Vorlage) |
| Funktionsumfang | 1:1 wie Vorlage: Sprach-Erkennung, Regeln, Syntax-Check, Statistik-Filter, Verlauf, Datei öffnen/Drag & Drop, Beispiel, Fix kopieren |
| Persistenz | JSON-Verlauf im Nutzerdatenordner des Betriebssystems statt localStorage |
| Abweichung | Scan läuft in einem Hintergrund-Thread ohne künstliche Wartezeit |
| Lizenz | MIT |
