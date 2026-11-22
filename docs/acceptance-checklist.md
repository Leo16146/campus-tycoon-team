# Abnahme auf der deployten App

**Status auf der deployten App: offen.** Die fertige App ist deployed, die Prüfliste
wurde dort aber noch nicht durchgespielt. Die P0-URL zeigt nur den Prototyp und zählt
nicht.

**Lokaler Browserdurchlauf (22.11.2026, automatisiert):** Die Schritte unten wurden
automatisiert in Chromium (Playwright) gegen die App auf `localhost` mit einer leeren
temporären Datenbank geprüft, bei 1280 px und 375 px Breite: **30 von 30 Prüfungen
bestanden.** Das ersetzt weder die Prüfung auf der deployten App noch den kurzen Test
auf einem echten Handy.

**Welcher Stand geprüft wird:** Diese Fassung beschreibt die App mit Tagesplan,
Rangliste, CSV-Export und der neuen Darstellung (warmes Farbschema, Karten). Die
deployte App zeigt immer den aktuellen `main`. Solange diese Änderungen nicht auf
`main` liegen, zeigt sie einen älteren Stand ohne Rangliste, CSV und neue
Darstellung; dann gelten die Schritte 1, 9b, 9c, 11 und 17 dort noch nicht.

**Rangliste auf einer öffentlichen App:** Die lokale Prüfung lief mit leerer
Datenbank. Auf der deployten App können schon Einträge vorhanden sein. Vor Schritt 9c
deshalb notieren, wie viele Einträge die Rangliste „Exam Week“ auf der Startseite hat
(N) und wie viele davon mehr als €319.00 haben (H).

**Voraussetzungen:**

- Die App läuft auf Streamlit Community Cloud aus `main` mit der Datei `app.py` und
  Python 3.12. Das bestätigen das Build-Log und die Einstellungen.
- Ein normales Browserfenster. Für die Schritte 11–12 zusätzlich ein privates
  Fenster, für Schritt 13 ein zweiter Tab.
- Bitte keine vollständigen Spiel-Links in Chats oder Screenshots weitergeben.

Ergebnis je Zeile eintragen: ✅ wie erwartet, ❌ mit kurzer Beschreibung.

| # | Schritt | Sollwert | Ergebnis |
|---|---|---|---|
| 1 | App-URL ohne Parameter öffnen | Titel „Campus Week“ im warmen Farbschema, Startseite mit „How to play“ (Goal, Each day, Score) und den Szenarien Exam Week und Heatwave | |
| 2 | Exam Week wählen, „Start game“ | `?game=…` in der Adresszeile. Cash €100.00, „1 of 5“, Lager 0/0/0. „Today's event: Normal day“ mit 10 / 5 für jedes Produkt. Buy-Felder 0, Preisfelder 4.00 / 1.00 / 2.00 | |
| 3 | Buy Coffee 10, Coffee-Preis 8.00 eintippen, **nicht** anwenden | Vorschau Coffee: „Demand: 5 · In stock: 0 · Expected sales: 5 · Cost: €20.00“. Total €20.00, Cash after €80.00. „Start trading day“ ist gesperrt mit Hinweis „Apply or discard …“. Cash oben weiter €100.00 | |
| 4 | „Discard changes“ | Buy 0, Coffee-Preis 4.00, Handel freigegeben | |
| 5 | Buy Coffee 51, „Apply purchases and prices“ | Total €102.00 und Warnung bei der Summe. Fehlermeldung „Not enough cash for this purchase.“, Cash €100.00, das Feld zeigt weiter 51. Danach „Discard changes“ | |
| 6 | Coffee-Preis „abc“, dann „0“, dann „4.001“ (jeweils „Apply …“) | Vorschau „Invalid price“, jedes Mal eine Fehlermeldung, die mit „Coffee:“ beginnt, gespeicherter Preis bleibt €4.00, Handel gesperrt. Danach „Discard changes“ | |
| 7 | Coffee-Preis „4“ eintippen | Keine Sperre des Handels, „Discard changes“ inaktiv | |
| 8 | Ab hier die Tabelle unten für alle fünf Tage spielen: je Tag Mengen und Preise eintippen, „Apply …“, „Start trading day“ | Nach „Apply …“ stehen die Buy-Felder wieder auf 0. Cash je Tag wie in der Tabelle. Nach Tag 1 steht oben „Day 1 result: 15 units sold · revenue €70.00 · gross profit €52.50 · baseline gross profit €35.00“ | |
| 9 | Nach Tag 5 | Final cash €419.00, Overall gain / loss €319.00. Baseline €229.00, Difference +€90.00. Tag 4: €49.00 / €49.00 / €0.00 | |
| 9b | „Download daily results (CSV)“ | Datei `campus-week-exam-week.csv`, enthält z. B. die Zeile `4,Coffee,14,56.00,28.00,28.00`, kein Token | |
| 9c | Spitzname „ab“, „Publish my result“; dann „Ana“ | Erst „Use 3–20 letters, digits, spaces, _ or -.“, dann „Your rank: R of N+1 (as Ana)“ mit R = H + 1 (bei leerer Rangliste „1 of 1“). Ana steht in der angezeigten Rangliste, sofern R ≤ 10 ist (es werden nur die besten zehn gezeigt) | |
| 10 | Seite neu laden (F5); Link kopieren, Tab schließen, in neuem Tab öffnen | Jeweils gleiches Endergebnis und gleiche Tabellen | |
| 11 | Privates Fenster: App-URL ohne Parameter / mit `?game=` / mit `?game=abc` | Startseite mit der Rangliste „Exam Week“, in der Ana steht, sofern R ≤ 10 / „not valid“ / „not valid“, jeweils ohne Absturz | |
| 12 | Im privaten Fenster Heatwave starten. Buy Water 10, Water-Preis 1.50, „Apply …“, „Start trading day“ | „Warm morning“: Coffee 10/5, Water 16/8, Granola bar 10/5. Danach 8 Water verkauft, Revenue €12.00, Gross profit €8.00, Cash €107.00, Lager Water 2. Exam-Week-Spiel unverändert | |
| 13 | Heatwave-Link in einem zweiten Tab öffnen. Dort Buy Coffee 5 eintippen, nicht anwenden. Im ersten Tab „Start trading day“. Dann im zweiten Tab „Apply …“ | Zweiter Tab: Fehlermeldung „game has changed“ **und** „Your plan was discarded because the trading day changed.“ Tag 3, Buy 0, kein Coffee gekauft | |
| 13b | Wieder zwei Tabs mit dem Heatwave-Link. Zweiter Tab: Buy Water 2 eintippen, nicht anwenden. Erster Tab: Water-Preis 1.20 anwenden. Dann im zweiten Tab „Apply …“ | Zweiter Tab: „This game was changed in another window …“ und „Your plan was discarded because the game was changed in another window.“ Water-Preis bleibt €1.20, kein Water gekauft | |
| 14 | „Start another game“ | Startseite. Der Heatwave-Link öffnet das Spiel unverändert | |
| 15 | Im Heatwave-Spiel „Delete this game“, dann „Cancel“; danach „Delete this game“, „Delete game“ | Cancel ändert nichts. Danach „Game deleted.“ und Startseite, der alte Heatwave-Link zeigt „not valid“, das Exam-Week-Spiel ist unverändert | |
| 16 | Schmaler Bildschirm: Handy oder Browser-Entwicklertools mit etwa 375 px Breite | Startseite mit Ranglisten, Ereignistabelle, Tagesplan (Felder, Vorschau, Knöpfe), Abschlussvergleich und Rangliste sind lesbar und ohne Überlappungen bedienbar. Seitliches Scrollen in Tabellen ist akzeptabel | |
| 17 | Nach der Probe: in der Probe veröffentlichte Ergebnisse mit „Remove my result“ entfernen | Rangliste zeigt keine Probeeinträge mehr | |

**Strategie für Schritt 8 (Exam Week):**

- „Premium“ = Preise 8.00 / 2.00 / 4.00, „Reference“ = 4.00 / 1.00 / 2.00.
- Preise und Mengen in denselben Plan eintippen, dann einmal „Apply …“.

| Tag | Ereignis | Preise | Buy (Coffee / Water / Bars) | Cash nach Abschluss |
|---|---|---|---|---:|
| 1 | Normal day | Premium | 5 / 5 / 5 | €152.50 |
| 2 | Revision rush | Premium | 10 / 5 / 5 | €235.00 |
| 3 | Exam day | Premium | 10 / 5 / 5 | €317.50 |
| 4 | Open Day | Reference | 14 / 14 / 14 | €366.50 |
| 5 | Normal day | Premium | 5 / 5 / 5 | €419.00 |

**Herkunft der Sollwerte:**

- Schritte 8–9 stammen aus `specs/campus-week.md` (Tests 23, 25, 30). U14 in
  `tests/test_daily_plan.py` prüft denselben Ablauf über die Oberfläche.
- Schritt 12: Warm morning hat für Water die Stufen (16, 8). Bei €1.50 ist die
  Nachfrage 8. Revenue 8 × €1.50 = €12.00, Wareneinsatz 8 × €0.50 = €4.00, Cash
  €100.00 − €5.00 + €12.00 = €107.00.

**Vor der Präsentation:**

- Die URL einige Minuten vorher öffnen, damit die App wach ist.
- Spiele aus der Probe nicht vorführen, sondern ein neues Spiel beginnen.
