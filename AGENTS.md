# Campus Tycoon — Team project (Campus Week)

Separates Gruppenprojekt für Introduction to Programming an der Nova SBE. Die App
„Campus Week“ simuliert einen Campus-Kiosk mit Kaffee, Wasser und Müsliriegeln über
fünf Handelstage, mit privaten Spielen, zwei Szenarien und einem Baseline-Vergleich.
Maßgeblich für Umfang und Sollwerte ist `specs/campus-week.md`.

Schreibe kurze Funktionen mit verständlichen Namen, die sich in der Klausur erklären
lassen. Alle sichtbaren Texte der App sind auf Englisch. Eurobeträge erscheinen als
`€4.00` und werden intern in ganzen Cent gerechnet.

## Struktur

- `app.py` zeigt die Streamlit-Oberfläche: Startseite, Spiel, Abschlussvergleich, Meldungen.
- `logic.py` enthält die Spielregeln ohne Datenbank: Katalog, `SCENARIOS`, `EVENTS`,
  Nachfrage je Preisstufe, Abrechnung, Baseline.
- `db.py` speichert Spiele mit Pythons eingebautem Modul `sqlite3`.
- `tests/` enthält die pytest-Tests. Speichertests verwenden temporäre SQLite-Dateien.
- `docs/acceptance-checklist.md` ist die manuelle Prüfliste für die deployte App.

## Befehle im Projektordner

- Umgebung mit Python 3.12 einrichten: `uv sync --locked`
- App starten: `uv run streamlit run app.py --server.address 127.0.0.1 --server.port 8503`
- Tests ausführen: `uv run pytest`

## Regeln für Änderungen

- **Zugriff:** Jede Funktion in `db.py`, die ein bestehendes Spiel liest oder ändert,
  erhält das Token, prüft zuerst das Format (`check_token`) und ermittelt die Spiel-ID
  nur über den Token-Hash (`authorized_game`). Eine Spiel-ID aus dem Browser verleiht
  nie Zugriff. Gespeichert wird nur der SHA-256-Hash, nie das Token selbst. Tokens
  erscheinen nicht in Meldungen, Logs oder Beispieldaten.
- **Transaktionen:** Datenbankzugriffe laufen über `db.transaction()`. Nur
  SQLite-Sperrfehler werden zu `DatabaseBusy` (Aktionen: Meldung `db.BUSY`, Link bleibt
  erhalten; Laden der Seite: `BUSY_LOADING` mit „Try again“); andere Datenbankfehler werden nicht
  abgefangen. Abgelehnte oder gesperrte Aktionen ändern nichts und werden nicht
  automatisch wiederholt.
- **Speicherung:** SQLite in `campus_week.sqlite3` (über `CAMPUS_TYCOON_DB` änderbar).
  Auf Streamlit Community Cloud ist die Speicherung vorübergehend. Eine Datenbank im
  Solo-Schema wird nie verändert. Zum Zurücksetzen lokal die Datei löschen; ein
  eigenes Reset-Werkzeug gibt es nicht.
- **Szenarien:** Ein bestehender Schlüssel in `EVENTS`/`SCENARIOS` wird nie
  umdefiniert. Änderungen erhalten einen neuen Schlüssel.
- **Secrets:** Die App braucht keine Secrets. Keine Zugangsdaten, `.env`- oder
  `secrets.toml`-Dateien anlegen oder committen. Datenbankdateien sind über
  `.gitignore` ausgeschlossen.
- **Abhängigkeiten:** Laufzeit nur `streamlit`, Entwicklung nur `pytest`, beide über
  `uv.lock` festgeschrieben. Neue Abhängigkeiten nur mit Begründung. Nach Änderungen
  am Lockfile `pip-audit` gegen einen Export aus `uv.lock` ausführen (siehe README).
- **Tests:** Sollwerte von Hand berechnen und nicht mit der getesteten Funktion
  erzeugen. Jede Änderung braucht Tests für angenommene und abgelehnte Aktionen.
  Vor jedem Commit `uv run pytest` vollständig ausführen.
- **Git:** Arbeit auf Feature-Branches. Kein direkter Commit oder Push auf `main`,
  kein Merge und kein Force-Push ohne ausdrückliche Freigabe. Vor jedem Commit den
  Diff auf Datenbanken und Zugangsdaten prüfen und Dateien einzeln hinzufügen.

## Projektgrenze

Arbeite ausschließlich in diesem Repository. Das benachbarte Repository
`campus-tycoon` enthält das abgeschlossene Einzelprojekt und bleibt unverändert.
Die Ausgangsversion stammt aus dessen Commit
`a10728f4edfacce67ff5523d1749ea92a9a360ee`. `docs/product-brief.html` und
`specs/first-feature.md` dokumentieren die Solo-Grundlage.
