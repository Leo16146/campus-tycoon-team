# Abnahme auf der deployten App

**Status: offen.** Deployment und Cloud-Abnahme der fertigen App sind noch nicht
durchgeführt. Die P0-URL zeigt nur den Prototyp und zählt nicht.

**Voraussetzungen:**

- Die App läuft auf Streamlit Community Cloud aus `main` mit der Datei `app.py` und
  Python 3.12. Das bestätigen das Build-Log und die Einstellungen.
- Die Prüfung findet in einem normalen Browserfenster statt. Für die Schritte 8–9
  braucht es zusätzlich ein privates Fenster.
- Bitte keine vollständigen Spiel-Links in Chats oder Screenshots weitergeben.

Ergebnis je Zeile eintragen: ✅ wie erwartet, ❌ mit kurzer Beschreibung.

| # | Schritt | Sollwert | Ergebnis |
|---|---|---|---|
| 1 | App-URL ohne Parameter öffnen | Startseite „Start a private game“ mit den Szenarien Exam Week und Heatwave | |
| 2 | Exam Week wählen, „Start game“ | `?game=…` in der Adresszeile. Cash €100.00, „1 of 5“, Lager 0/0/0, Preise €4.00/€1.00/€2.00. „Today's event: Normal day“ mit 10 / 5 für jedes Produkt | |
| 3 | Coffee, Menge 51, „Buy“ | Purchase total €102.00. Fehlermeldung „Not enough cash for this purchase.“, Cash bleibt €100.00 | |
| 4 | Coffee-Preis „abc“, dann „0“, dann „4.001“ eingeben | Jedes Mal eine Fehlermeldung, Preis bleibt €4.00 | |
| 5 | Ab hier Tabelle unten (Strategie „Premium except Open Day“) für alle fünf Tage durchspielen | Cash und Ereignis je Tag wie in der Tabelle | |
| 6 | Nach Tag 5 | Final cash €419.00, Overall gain / loss €319.00. Baseline €229.00, Difference +€90.00. Tag 4: €49.00 / €49.00 / €0.00 | |
| 7 | Seite neu laden (F5) | Gleiches Endergebnis, gleiche Tabellen | |
| 8 | Link kopieren, Tab schließen, Link in neuem Tab öffnen | Gleiches Endergebnis | |
| 9 | Privates Fenster: App-URL ohne Parameter / mit `?game=` / mit `?game=abc` | Startseite / Fehlermeldung „not valid“ / Fehlermeldung „not valid“, jeweils ohne Absturz | |
| 10 | Im privaten Fenster Heatwave starten | Anderer Link. „Today's event: Warm morning“: Coffee 10/5, Water 16/8, Granola bar 10/5. Cash €100.00. Spiel aus 2 unverändert | |
| 11 | Heatwave: 10 Water kaufen, Water-Preis 1.50, Tag abschließen | 8 Water verkauft, Revenue €12.00, Gross profit €8.00, Cash €107.00, Lager Water 2 | |
| 12 | „Start another game“ | Startseite. Der Heatwave-Link öffnet das Spiel unverändert (Tag 2, €107.00) | |
| 13 | Im Heatwave-Spiel „Delete this game“, dann „Cancel“ | Spiel bleibt unverändert | |
| 14 | „Delete this game“, dann „Delete game“ | Meldung „Game deleted.“ und Startseite. Der alte Heatwave-Link zeigt „not valid“. Das Exam-Week-Spiel ist unverändert | |
| 15 | Schmaler Bildschirm: Handy oder Browser-Entwicklertools mit etwa 375 px Breite | Startseite, Ereignistabelle, Einkauf und Abschlussvergleich sind lesbar und ohne Überlappungen bedienbar. Seitliches Scrollen in Tabellen ist akzeptabel | |

**Strategie für Schritt 5 (Exam Week):**

- Preise vor dem Einkauf setzen.
- „Premium“ = €8.00 / €2.00 / €4.00, „Reference“ = €4.00 / €1.00 / €2.00.

| Tag | Ereignis | Preise | Kaufen (Coffee / Water / Bars) | Cash nach Abschluss |
|---|---|---|---|---:|
| 1 | Normal day | Premium | 5 / 5 / 5 | €152.50 |
| 2 | Revision rush | Premium | 10 / 5 / 5 | €235.00 |
| 3 | Exam day | Premium | 10 / 5 / 5 | €317.50 |
| 4 | Open Day | Reference | 14 / 14 / 14 | €366.50 |
| 5 | Normal day | Premium | 5 / 5 / 5 | €419.00 |

Die Sollwerte stammen aus `specs/campus-week.md` (Tests 23, 25 und 30) und sind
dort von Hand gerechnet. Schritt 11: Warm morning hat für Water die Stufen (16, 8).
Bei €1.50 ist die Nachfrage 8; 8 × €1.50 = €12.00 Revenue, 8 × €0.50 = €4.00
Wareneinsatz, Cash €100.00 − €5.00 + €12.00 = €107.00.

**Vor der Präsentation:**

- Die URL einige Minuten vorher öffnen, damit die App wach ist.
- Spiele aus der Probe nicht vorführen, sondern ein neues Spiel beginnen.
