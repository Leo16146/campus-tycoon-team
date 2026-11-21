# Campus Tycoon — Team project

Separates Gruppenprojekt für Introduction to Programming an der Nova SBE. Die App simuliert
einen Campus-Kiosk mit Kaffee, Wasser und Müsliriegeln. Der Projektbrief steht
in `docs/product-brief.html`. Schreibe kurze Funktionen mit verständlichen Namen,
die sich in der Klausur erklären lassen.

Alle sichtbaren Texte der App sind auf Englisch. Eurobeträge erscheinen als `€4.00`.

## Geplante Struktur

- `app.py` zeigt die Streamlit-Oberfläche.
- `logic.py` enthält die Spielregeln.
- `db.py` speichert und lädt Spielstände mit Pythons eingebautem Modul `sqlite3`.
- `tests/` enthält die pytest-Tests.

## Befehle im Projektordner

- Umgebung mit Python 3.12 einrichten: `uv sync --locked`
- Streamlit-Demo starten: `uv run streamlit hello --server.address 127.0.0.1`
- Sobald `app.py` existiert, App starten: `uv run streamlit run app.py`
- Tests ausführen: `uv run pytest`

## Projektgrenze

Arbeite ausschließlich in diesem Repository. Das benachbarte Repository
`campus-tycoon` enthält das abgeschlossene Einzelprojekt.
Die Ausgangsversion stammt aus dessen Commit
`a10728f4edfacce67ff5523d1749ea92a9a360ee`.
`docs/product-brief.html` und `specs/first-feature.md` dokumentieren die
Solo-Grundlage. Den Umfang der Team-Erweiterung legt die Gruppe separat fest.
