# Campus Week – Team-Erweiterung von Campus Tycoon

**Stand:** 22.11.2026. P0 (technischer Versuch) ist abgeschlossen, siehe unten. P1 (Spieltrennung), P2 (Szenarien), P3 (Baseline) und P4 (Release-Prüfung) sind auf `main`. Der Tagesplan (E1) ist ebenfalls auf `main` (Merge `5471fe0`), siehe [`daily-plan-and-leaderboard.md`](daily-plan-and-leaderboard.md). **Offen:** Deployment der fertigen App und Abnahme nach `docs/acceptance-checklist.md`. Grundlage sind der Solo-Code auf `main` (Commit `c412e92`), [`specs/first-feature.md`](first-feature.md) und die [offizielle Projektseite](https://2477-introduction-programming.gitlab.io/wiki/team-project/), abgerufen am 22.11.2026.

Kennzeichnung in diesem Dokument:

- **[Offiziell]** steht so auf der Kursseite.
- **[Ziel]** ist unser eigener Qualitätsanspruch.
- **[Optional]** wird nur gebaut, wenn Zeit bleibt.
- **[Annahme]** ist noch nicht praktisch geprüft.

Der hier beschriebene Umfang ist unsere Entscheidung. Er ist keine Zusage für eine bestimmte Bewertungsstufe.

## Why

Die Solo-App hat genau ein globales Spiel (`WHERE id = 1` in `db.py`). Unter einer öffentlichen URL [Offiziell: die App läuft unter einer öffentlichen URL] würden alle Besucher denselben Spielstand sehen, und jeder könnte ihn mit „New game“ löschen.

Spielerisch ist jeder Tag gleich. Mit Stückkosten von genau dem halben Referenzpreis bringt der doppelte Referenzpreis immer mehr Rohertrag. Beim Kaffee sind das 5 × €6.00 = €30.00 statt 10 × €2.00 = €20.00. Ein reiner Mengenfaktor pro Tag würde die Einkaufsmenge verändern, aber nicht die bessere Preisstufe.

Campus Week löst beides:

- Jede Person spielt ein eigenes, privates Spiel.
- Jeder Tag hat ein Ereignis, das die Nachfrage **je Preisstufe** festlegt. An manchen Tagen lohnt sich der hohe Preis, an anderen nicht.
- Am Ende zeigt ein Vergleich mit einer festen, einfachen Strategie (der Baseline), ob die Entscheidungen besser waren als „Referenzpreis und auffüllen“.

## What

### Ablauf

1. Ohne Spiel-Link zeigt die App die Startseite. Dort wählt man eines von zwei Szenarien und klickt „Start game“.
2. Die App legt ein neues Spiel an und schreibt den privaten Link in die Adresszeile (`?game=<token>`). Ein Hinweis erklärt: Lesezeichen setzen, um später weiterzuspielen; die Speicherung ist nur vorübergehend.
3. An jedem der fünf Tage sieht man **das Ereignis von heute** mit der Nachfrage je Produkt und Preisstufe, bevor man einkauft und Preise festlegt.
4. Einkauf, Preisänderung und „Start trading day“ funktionieren wie in der Solo-App. „Expected sales“ berücksichtigt das heutige Ereignis.
5. Nach Tag 5 erscheinen die Endergebnisse wie bisher, zusätzlich der **Vergleich mit der Baseline strategy**.
6. „Delete this game“ löscht nach einer Bestätigung nur dieses Spiel.

### Produkte und Preisstufen

Die Produkte und Geldregeln bleiben wie in der Solo-App. Alle Beträge werden intern in ganzen Cent gespeichert.

| Produkt | Stückkosten | Referenzpreis | Start-Verkaufspreis |
|---|---:|---:|---:|
| Coffee (`Kaffee`) | €2.00 | €4.00 | €4.00 |
| Water (`Wasser`) | €0.50 | €1.00 | €1.00 |
| Granola bar (`Müsliriegel`) | €1.00 | €2.00 | €2.00 |

Ein Ereignis legt je Produkt zwei ganze Zahlen fest, `(unten, oben)`:

- Preis ≤ Referenzpreis → Nachfrage = **unten**.
- Referenzpreis < Preis ≤ 2 × Referenzpreis → Nachfrage = **oben**.
- Preis > 2 × Referenzpreis → Nachfrage = **0**, bei jedem Ereignis.
- Verkauf = min(Nachfrage, Lagerbestand). Restware bleibt im Lager.

Es gibt keine Faktoren, keine Rundung und keinen Zufall. Die Solo-Regel entspricht genau der Stufe `(10, 5)`.

Faustregel für die Spielenden: Der Rohertrag pro Stück ist beim doppelten Referenzpreis dreimal so hoch wie beim Referenzpreis. Für einen gegebenen Lagerbestand `B` lohnt sich der doppelte Referenzpreis genau dann, wenn 3 × min(oben, B) > min(unten, B) ist.

- Kann die Nachfrage beider Stufen vollständig bedient werden, wird daraus 3 × oben > unten.
- Mit knappem Bestand kann der hohe Preis trotzdem besser sein. Beispiel Sports day, Water (30, 3), nur 3 Stück im Lager: Bei €1.00 werden 3 Stück verkauft, das bringt €1.50 Gross profit. Bei €2.00 werden ebenfalls 3 Stück verkauft, das bringt €4.50 (Test 21a).

### Szenario 1: „Exam Week“

Kaffee steht im Mittelpunkt. Der hohe Preis lohnt sich fast immer. Die Falle ist der Open Day, an dem niemand den hohen Preis zahlt.

| Tag | Ereignis (Anzeige) | Coffee | Water | Granola bar |
|---|---|---|---|---|
| 1 | Normal day | (10, 5) | (10, 5) | (10, 5) |
| 2 | Revision rush | (20, 10) | (10, 5) | (10, 5) |
| 3 | Exam day | (20, 10) | (10, 5) | (10, 5) |
| 4 | Open Day | (14, 0) | (14, 0) | (14, 0) |
| 5 | Normal day | (10, 5) | (10, 5) | (10, 5) |

### Szenario 2: „Heatwave“

Wasser steht im Mittelpunkt, Kaffee ist schwach. Am Sports day ist die richtige Preisstufe **je Produkt verschieden**: Kaffee lohnt sich teuer, Wasser und Riegel günstig.

| Tag | Ereignis (Anzeige) | Coffee | Water | Granola bar |
|---|---|---|---|---|
| 1 | Warm morning | (10, 5) | (16, 8) | (10, 5) |
| 2 | Heatwave | (6, 3) | (24, 12) | (8, 4) |
| 3 | Heatwave | (6, 3) | (24, 12) | (8, 4) |
| 4 | Sports day | (8, 4) | (30, 3) | (12, 2) |
| 5 | Cool change | (12, 6) | (10, 5) | (10, 5) |

**Unterscheiden sich die Szenarien genug?**

- Sie haben ein anderes Schlüsselprodukt (Kaffee bzw. Wasser).
- Die Falle sieht anders aus: an einem Tag alle Produkte gleich bzw. je Produkt verschieden.
- Bei Heatwave ist der hohe Preis am Sports day nicht null, aber trotzdem schlechter. Dort muss man rechnen statt nur hinzuschauen.
- Die Namen beschreiben die Situation, die Ereignisnamen sind auf Englisch wie die übrige Oberfläche.

### Budget und Lager

- Einkäufe werden sofort aus der Kasse bezahlt (Solo-Regel CT02). Was nicht bezahlbar ist, wird abgelehnt.
- Restbestand wird am Ende zum Einkaufspreis bewertet, bindet während des Spiels aber Geld. Wer am Tag 1 zum Beispiel 45 Coffee für €90.00 kauft, hat nur noch €10.00 und kann keine 21 Water (€10.50) mehr kaufen.
- Mit €100.00 Startkapital und diesen Szenarien wird die Kasse nur bei deutlichem Überkauf knapp.

### Kennzahlen (in der Oberfläche einheitlich benannt)

- **Revenue** = verkaufte Stück × Verkaufspreis.
- **Cost of goods sold** = verkaufte Stück × Stückkosten. Nicht verkaufte Ware zählt hier nicht.
- **Gross profit** = Revenue − Cost of goods sold, je Produkt und Tag. Die Tagessumme ist die Summe der Produkte.
- **Cash** = Kassenstand. Er sinkt beim Einkauf und steigt beim Verkauf.
- **Overall gain / loss** = Endkasse + Restbestand zu Stückkosten − €100.00, wie im bisherigen `final_result`. Über ein vollständiges Spiel ist das gleich der Summe aller Gross profits, weil gekaufte, nicht verkaufte Ware zu Stückkosten zurückgerechnet wird.

### Baseline strategy

Die Baseline ist eine reine Funktion in `logic.py` ohne Datenbank. Sie spielt dasselbe Szenario mit **denselben Regeln** wie ein Mensch:

1. Startkasse €100.00, leeres Lager.
2. Jeden Tag stehen alle Verkaufspreise auf dem Referenzpreis.
3. Pro Produkt in der Reihenfolge Coffee, Water, Granola bar wird auf die heutige untere Nachfrage aufgefüllt: Ziel = `unten` − Lagerbestand, mindestens 0.
4. Reicht die Kasse nicht, kauft die Baseline so viele Stück, wie bezahlbar sind (`cash // Stückkosten`), und geht zum nächsten Produkt.
5. Abrechnung nach denselben Verkaufsregeln.
6. Am Ende wird Overall gain / loss mit derselben Formel berechnet.

Die Baseline nutzt das heutige Ereignis nur für die Menge, nie für den Preis. Die Oberfläche nennt sie „Baseline strategy“ und schreibt dazu: *„A simple reference: reference prices, restocked each day. It is not the best possible strategy.“*

**Abschlussvergleich:** „Your overall gain / loss“, „Baseline overall gain / loss“ und die Differenz, dazu je Tag der eigene Gross profit neben dem der Baseline.

### Datenmodell (SQLite)

```
games    (id INTEGER PRIMARY KEY,
          token_hash TEXT NOT NULL UNIQUE,      -- SHA-256 hex des Tokens
          scenario TEXT NOT NULL,               -- "exam_week" | "heatwave"
          day INTEGER NOT NULL,
          cash INTEGER NOT NULL)
products (game_id INTEGER NOT NULL, position INTEGER NOT NULL,
          name TEXT NOT NULL, cost INTEGER NOT NULL, reference INTEGER NOT NULL,
          price INTEGER NOT NULL, stock INTEGER NOT NULL,
          PRIMARY KEY (game_id, name))
sales    (game_id INTEGER NOT NULL, day INTEGER NOT NULL, name TEXT NOT NULL,
          sold INTEGER NOT NULL, revenue INTEGER NOT NULL,
          expense INTEGER NOT NULL, profit INTEGER NOT NULL,
          PRIMARY KEY (game_id, day, name))
```

- Szenarien und Ereignisse stehen als Konstanten in `logic.py`, nicht in der Datenbank.
- Ein Szenario-Schlüssel wird nie umdefiniert. Eine Änderung bekommt einen neuen Schlüssel.
- `create_game` prüft den Szenario-Schlüssel, **bevor** etwas geschrieben wird. Ein unbekannter Schlüssel führt zu einem `ValueError` (*„Unknown scenario.“*), und es entstehen keine Daten.
- Ein unbekannter Schlüssel bei einem gespeicherten Spiel führt zu der Meldung *„This game uses a scenario that is no longer available.“* und dem Knopf „Start a new game“. Es gibt keinen Absturz und keine Schreiboperation.
- Die Produktnamen bleiben die bisherigen deutschen Schlüssel. Die englischen Anzeigenamen kommen weiter aus `PRODUCT_LABELS`.

### Autorisierung

1. **Spiel anlegen:** `db.create_game(path, scenario)` erzeugt `token = secrets.token_urlsafe(32)` (43 Zeichen). Gespeichert wird nur `sha256(token)`. Das Token geht genau einmal an `app.py` zurück, und die App schreibt es nach `st.query_params["game"]`.
2. **Jede Anfrage:** `app.py` liest `st.query_params.get("game")`. Erlaubt sind nur Tokens, die `[A-Za-z0-9_-]{43}` entsprechen. Ist das Format falsch, findet kein Datenbankzugriff statt.
3. **Datenbankfunktionen** nehmen das **Token** entgegen, nie eine `game_id` von außen. Innerhalb der Transaktion sucht `authorized_game(conn, token)` das Spiel über den Hash. Wird keins gefunden, folgt ein `ValueError`. Erst danach verwendet die Funktion intern die gefundene `game_id`.
4. **Begrenzung auf das eigene Spiel:** Jede Lese- und Schreiboperation (`load`, `buy`, `set_price`, `trade`, `delete_game`) beschränkt sich auf die aus dem Token ermittelte ID: in `games` mit `WHERE id = ?`, in `products` und `sales` mit `WHERE game_id = ?`. Eine `game_id` aus dem Browser verleiht nie Rechte. Sie erscheint weder in URL noch Widgets noch Meldungen.
5. **Doppelte Aktionen:** `expected_day` wird wie bisher innerhalb von `BEGIN IMMEDIATE` geprüft. Ein zweiter Abschluss desselben Tages wird abgelehnt.
6. **Löschen:** `delete_game(path, token)` entfernt `sales`, `products` und `games` des autorisierten Spiels in einer Transaktion. Danach ist der Link ungültig.
7. **Das Token ist vertraulich.** Es steht in keiner Fehlermeldung, keinem Log, keinem Export und keinen Beispieldaten im Repository.

### Ungültige Links, verlorene Spiele, Linkwechsel

- **Kein Parameter `game` in der URL:** Die Startseite erscheint.
- **Parameter vorhanden, aber leer (`?game=`):** Das ist ein ungültiger Link wie in Test 9. Die App unterscheidet „fehlt“ (`"game" not in st.query_params`) von „leer“ und behandelt beides nicht gleich, etwa über ein bloßes `if not token`.
- **Falsches Format, unbekanntes Token, gelöschtes oder verlorenes Spiel:** Alle Fälle bekommen dieselbe Meldung *„This game link is not valid or the game is no longer available. Games are stored temporarily and may be removed.“* und den Knopf „Start a new game“, der zur Startseite führt. Es gibt keine Schreiboperation und keinen Hinweis auf andere Spiele.
- **Linkwechsel in derselben Sitzung:** `app.py` merkt sich den Hash des aktiven Tokens in `st.session_state`. Ändert er sich, werden `product`, `quantity`, `confirm_delete` und `notice` gelöscht. Die Preisfelder werden wie bisher bei jedem Lauf aus der Datenbank gesetzt.
- **Hinweis zur Speicherung** dauerhaft im Spiel sichtbar: *„Bookmark this page to continue later. Games are stored temporarily on the server and may be removed, for example after a restart.“*

### Vorhandene Datenbank im Solo-Schema

- Neuer Standardpfad: `campus_week.sqlite3`. `CAMPUS_TYCOON_DB` überschreibt ihn weiterhin. Die bisherige Datei `kiosk.sqlite3` wird nicht geöffnet.
- Enthält die konfigurierte Datei die Solo-Tabelle `game`, aber nicht `games`, bricht `initialize` mit einer klaren Meldung ab (*„This database uses the solo schema. Set CAMPUS_TYCOON_DB to a new file.“*). Es wird nichts gelöscht, umbenannt oder migriert.
- Eine automatische Übernahme eines Solo-Spiels ist nicht vorgesehen, weil ein Solo-Spiel keinem Szenario zugeordnet ist.

## Out of scope

Bewusst nicht enthalten:

- Rangliste
- eigene Passwortverwaltung, `st.login`
- externe APIs
- dauerhafte Speicherung über Supabase oder Ähnliches
- automatisches Löschen alter Spiele
- Zufallsereignisse, Verderb, laufende Kosten
- Live-Interaktion zwischen Spielen
- Vorschau auf künftige Tage
- Migration von Solo-Spielständen

**[Optional]**, in dieser Reihenfolge, nur nach erfüllter Pflicht:

1. Knopf „Try a finished example“, der ein **neues** privates, fertig gespieltes Exam-Week-Spiel anlegt (Strategie aus Test 23). Das macht die Demo unabhängig von gespeicherten Daten.
2. CSV-Export des eigenen Verlaufs (ohne Token, auch nicht im Dateinamen).
3. Diagramm „Gross profit per day: you vs. baseline“.

**Kürzungsreihenfolge bei Zeitdruck:** Diagramm → CSV → Beispielspiel. Nie gekürzt werden Spieltrennung samt Tests, korrekte Berechnung, verständliche Meldungen, beide Szenarien und die Baseline.

## Limits

Diese Grenzen kommen in README und Repo-Walkthrough:

- **Speicherung:** Laut Streamlit-Doku garantiert Community Cloud keine dauerhafte Speicherung lokaler Dateien. Spiele können jederzeit verschwinden. Ein Lesezeichen garantiert keine Wiederaufnahme. Ein erfolgreicher Neustarttest beweist keine Dauerhaftigkeit.
- **Zugriff:** Wer den Link hat, kann das Spiel spielen und löschen. Der Link identifiziert keine Person. Der Hash schützt die Datenbank, nicht einen weitergegebenen Link. In der Demo nur ein entbehrliches Spiel zeigen.
- **Spiel:** Das Spiel ist deterministisch, alles ist bekannt. Wer die Regel „3 × min(oben, Bestand) > min(unten, Bestand)“ verstanden hat, kann es lösen. Bei ausreichendem Bestand wird daraus „3 × oben > unten“. Das ist als Lernspiel gewollt.
- **Mehrere Nutzerinnen:** Mehrere Personen können gleichzeitig getrennte Spiele spielen. Es gibt keinen gemeinsamen Wettbewerb.
- **Ressourcen:** Die Zahl der Spiele ist nicht begrenzt, es gibt kein automatisches Aufräumen.
- **Gleichzeitige Zugriffe:** SQLite erlaubt jeweils nur einen Schreibvorgang. Ist die Sperre nicht innerhalb von 5 Sekunden frei, wird die Aktion nicht ausgeführt (`DatabaseBusy`). Die App meldet „Nothing was changed“ und bittet darum, es erneut zu versuchen; ein gesperrtes Löschen behält den Spiel-Link. Ein gesperrtes Laden der Seite meldet stattdessen „could not be loaded“ und bietet „Try again“. Es gibt keine automatische Wiederholung. Andere Datenbankfehler werden nicht abgefangen (P4, `tests/test_locks.py`).
- **Wie es sich ändern könnte:** dauerhafte Speicherung durch Austausch von `db.py` (zum Beispiel Postgres); Identität über `st.login`; Rangliste je Szenario auf dieser Grundlage.

## Technischer Versuch P0 (Ergebnis)

Durchgeführt am 22.11.2026 auf Streamlit Community Cloud. Grundlage war der Prototyp `spike_app.py` auf dem Branch `p0-token-spike`. Der Branch wird nicht gemergt, und der Prototyp ist nicht Teil der App.

| # | Annahme | Ergebnis |
|---|---|---|
| 1 | Token in `st.query_params` bleibt nach Neuladen und im Lesezeichen erhalten | **Bestätigt** (Cloud, manuell) |
| 2 | Verschiedene Links haben getrennte Daten | **Bestätigt** (Cloud, manuell: getrennte Zähler) |
| 3 | Leere und ungültige Links werden abgelehnt | **Bestätigt** (Cloud, manuell) |
| 4 | Build aus `uv.lock` mit Python 3.12 | **Bestätigt** (Build-Log und Anzeige der Version) |
| 5 | Verhalten der SQLite-Datei nach „Reboot app“ | **Nicht eindeutig dokumentiert.** Reboot wurde durchgeführt, ob der alte Zähler erhalten blieb, ist offen. Unabhängig davon gilt die Grenze unter „Limits“: keine garantierte Dauerhaftigkeit |

Vorher lokal mit `AppTest` geprüft (Skript außerhalb des Repos, 13 von 13 Prüfungen bestanden):

- Ohne Parameter erscheint die Startseite.
- Leere, falsch formatierte und unbekannte Tokens werden ohne Datenänderung abgelehnt.
- Die Zähler sind getrennt, und ein Link lädt in einer neuen Sitzung wieder seinen Zähler.
- Kein vollständiges Token steht in Datenbank-Datei, Fehlermeldung oder Seitentext.

Außerdem bestätigt der installierte Streamlit-Code 1.67, dass es `AppTest.query_params` gibt.

## Done when

- `uv run pytest` ist auf `main` grün.
- Jeder Test baut seine Ausgangslage selbst auf, Speichertests verwenden eine temporäre SQLite-Datei.
- Die Sollwerte unten sind von Hand gerechnet und werden **nicht** mit der getesteten Funktion erzeugt.
- Für Bestände und Preise gilt die Reihenfolge Coffee, Water, Granola bar.
- „Neu“ bedeutet: frisch angelegt mit €100.00, Lager 0/0/0, Preise €4.00/€1.00/€2.00, Tag 1.
- Die neuen Tests **ergänzen** die bisherigen Solo-Tests und ersetzen sie nicht. Jeder bisherige Test bleibt fachlich erhalten, angepasst auf Spiele mit Token:
  - Spielstart und Wiederaufnahme → Tests 1, 8
  - Kauf mit exakt passendem Geld → 18a
  - Ungültige Mengen → 16
  - Preisgrenzen → 19
  - Bestandsgrenze → 22c
  - Gemischter Verkauf mit Restbestand → 22d, 22f
  - Rollback → 13
  - Abgelehnte ungültige Preise → 17
  - Aktionen nach Spielende → 12
  - Produktsummen bei wechselnden Preisen → 22e
  - Bewertung des Restbestands → 22f
  - Klickablauf und neue Sitzung → 7, 8
  - Bearbeiteter Preis bleibt erhalten → 3, 8
- Die Fünf-Tage-Tests 23–26 verkaufen den gesamten Bestand. Ob Restbestand richtig bewertet wird, prüft deshalb Test 22f.

### Trennung, Autorisierung, Links

| # | Ausgangslage | Aktion | Sollwert |
|---|---|---|---|
| 1 | Leere Datenbank | Spiel „Exam Week“ anlegen | Token mit 43 Zeichen. In `games` steht genau eine Zeile mit `token_hash` = SHA-256 des Tokens; das Token selbst steht in keiner Tabelle. Tag 1, €100.00, Lager 0/0/0, 0 Abschlüsse |
| 2 | Neue Spiele A und B | A kauft 3 Coffee | A: €94.00, Lager 3/0/0. B: €100.00, Lager 0/0/0 |
| 3 | Neue Spiele A und B | A setzt den Coffee-Preis auf €8.00 | A: €8.00. B: €4.00 |
| 4 | A und B haben je einen Abschluss für Tag 1 | A nach Bestätigung löschen | Mit A-Token wird „not valid“ gemeldet. Alle Zeilen von B sind unverändert, keine Zeile mit A-`game_id` bleibt übrig |
| 5 | A vorhanden | „Delete this game“, dann „Cancel“ | Datenbank vollständig unverändert |
| 6 | A, Exam Week, Tag 1 | `trade(token A, 1)` zweimal | Der zweite Aufruf wird abgelehnt („game has changed“). Genau 3 `sales`-Zeilen für Tag 1, Tag 2 |
| 7 | Zwei `AppTest`-Sitzungen mit demselben Token, beide auf Tag 1 | Beide klicken „Start trading day“ | Die zweite zeigt einen Fehler. Genau ein Abschluss, kein doppelter Umsatz |
| 8 | A mit Kauf, Preisänderung und einem Abschluss | Neue `AppTest`-Instanz mit A-Token in `query_params` | Gleiche Kasse, gleiches Lager, gleiche Preise und gleicher Verlauf wie zuvor |
| 9 | Spiel B vorhanden | Token `""`, `"abc"`, 43 Zeichen mit `!` und ein formal gültiges, unbekanntes Token: laden und kaufen | Jedes Mal dieselbe Meldung. Keine Zeile in irgendeiner Tabelle verändert. Die Meldung enthält keine Daten von B |
| 10 | A gelöscht | Alten A-Link öffnen | Meldung und Knopf „Start a new game“, keine Schreiboperation |
| 11 | Sitzung mit A-Link, Menge 7 eingestellt, Bestätigungsdialog offen | In derselben `AppTest`-Sitzung auf den B-Link wechseln | Menge zeigt den Standardwert 1, kein Dialog, keine Meldung von A |
| 12 | A hat Tag 5 abgeschlossen | Kaufen, Preis ändern, abschließen | Alles wird abgelehnt („complete“), Daten unverändert |
| 13 | A, Tag 1, 10 Coffee gekauft | Abschluss, während ein Trigger das Update auf `games` abbricht | Rollback: Kasse, Lager und `sales` wie vorher (bestehender Rollback-Test, auf Spiele angepasst) |
| 14 | Datei im Solo-Schema mit Spielstand (Tag 2, €120.00) | `initialize` | Fehlermeldung „solo schema“. Tabellen und Zeilen unverändert, es entsteht keine Tabelle `games` |
| 14a | Leere Datenbank | `create_game(path, "summer_break")` | `ValueError` „Unknown scenario“. `games`, `products` und `sales` sind leer |
| 14b | Spiel A, dessen `scenario` in der Datenbank auf `"retired_week"` gesetzt wurde | A-Link öffnen | Meldung „scenario that is no longer available“ und Knopf „Start a new game“, kein Absturz. Alle Zeilen von A unverändert |
| 14c | Spiel B vorhanden | App ohne Parameter `game` öffnen | Startseite mit beiden Szenarien, keine Daten von B sichtbar, keine Schreiboperation |
| 14d | Spiel B vorhanden | App mit `?game=` (leerer Wert) öffnen | Dieselbe Meldung wie in Test 9, **nicht** die Startseite. Keine Schreiboperation |

### Eingaben und Budget

| # | Ausgangslage | Aktion | Sollwert |
|---|---|---|---|
| 15 | Neues Spiel | 51 Coffee kaufen (Vorschau €102.00) | Abgelehnt. €100.00, Lager 0/0/0, Tag 1 |
| 16 | Neues Spiel, je Versuch frisch | 0, −1 und 1.5 Coffee kaufen | Alle abgelehnt, nichts verändert |
| 17 | Neues Spiel | Preis „0“, „−0.01“, „4.001“, „abc“, „NaN“, „“ | Alle abgelehnt, Preis bleibt €4.00 |
| 18 | Neues Spiel, Exam Week | 45 Coffee kaufen, dann 21 Water | Coffee gelingt (€10.00 übrig). Water abgelehnt (€10.50 > €10.00), €10.00, Lager 45/0/0 |
| 18a | Neues Spiel (übernommen aus Solo-`test_spend_exact_remaining_cash`) | 10 Coffee, dann 40 Coffee kaufen | Beide Käufe gelingen. Kasse €0.00, Lager 50/0/0 |

### Nachfrage und Ereignisse (Rechenteil, ohne Oberfläche)

| # | Ausgangslage | Aktion | Sollwert |
|---|---|---|---|
| 19 | Referenzpreis Coffee €4.00, Stufen (10, 5) | Nachfrage bei €4.00, €4.01, €8.00, €8.01 | 10, 5, 5, 0 (Solo-Werte unverändert) |
| 20 | Stufen (20, 10) | Nachfrage bei €4.00, €4.01, €8.00, €8.01 | 20, 10, 10, 0 |
| 21 | Water, Referenzpreis €1.00, Sports day (30, 3) | Nachfrage bei €1.00, €1.01, €2.00, €2.01 | 30, 3, 3, 0 |
| 21a | Water, Stückkosten €0.50, Sports day (30, 3), Bestand 3 | Verkauf getrennt bei €1.00 und bei €2.00 berechnen | €1.00: 3 Stück, Revenue €3.00, Gross profit €1.50. €2.00: 3 Stück, Revenue €6.00, Gross profit €4.50. In beiden Fällen Restbestand 0 |

### Abrechnung mit Ereignis

| # | Ausgangslage | Aktion | Sollwert |
|---|---|---|---|
| 22a | Exam Week, Tag 1 ohne Einkauf abgeschlossen (alles 0), Tag 2 (Coffee (20, 10)); 12 Coffee gekauft, Preis €4.00 | Tag 2 abschließen | Coffee: 12 Stück, Revenue €48.00, COGS €24.00, Gross profit €24.00. Kasse €124.00, Lager 0/0/0, Tag 3 |
| 22b | Wie 22a, aber Coffee-Preis €8.01 | Tag 2 abschließen | Coffee 0 Stück, alle Beträge €0.00, Lager 12/0/0, Kasse €76.00 |
| 22c | Exam Week, Tag 1 (10, 5): 12 Coffee zu €4.00 | Tag 1, dann Tag 2 ohne Einkauf abschließen | Tag 1: 10 verkauft, Rest 2. Tag 2 (Nachfrage 20): 2 verkauft. Lager 0, Kasse nach Tag 1 €116.00, nach Tag 2 €124.00 |
| 22d | Heatwave, Tag 4 erreicht (Tage 1–3 ohne Einkauf abgeschlossen), Preise €8.00 / €1.00 / €2.00; 4 Coffee, 30 Water, 12 Bars gekauft | Tag 4 abschließen | Coffee 4 Stück / €32.00 / €8.00 / €24.00. Water 30 / €30.00 / €15.00 / €15.00. Bars 12 / €24.00 / €12.00 / €12.00. Summe 46 Stück, €86.00 / €35.00 / €51.00 |
| 22e | Exam Week (übernommen aus Solo-`test_sales_by_product_uses_actual_daily_prices`). Tag 1: 15 Coffee und 2 Water zu Referenzpreisen kaufen, abschließen. Ab Tag 2 Coffee-Preis €4.01, Tage 2–5 ohne Einkauf abschließen | Endergebnisse öffnen | Tag 1 verkauft 10 Coffee zu €4.00. Tag 2 hat die Stufen (20, 10), die Nachfrage ist also 10, aber nur 5 sind im Lager: 5 Coffee zu €4.01. „Sales by product“: Coffee 15 / €60.05 / €30.05 · Water 2 / €2.00 / €1.00 · Granola bar 0 / €0.00 / €0.00 · Total 17 / €62.05 / €31.05 |
| 22f | Exam Week (übernommen aus Solo-`test_new_game_requires_confirmation_and_persists`). Tage 1–4 ohne Einkauf abschließen, an Tag 5 (Normal day, (10, 5)) 12 Coffee und 4 Water zu Referenzpreisen kaufen, abschließen | Endergebnisse öffnen | Final cash €118.00, Restbestand zu Stückkosten €4.00 (2 Coffee), Overall gain / loss €22.00 = Summe der Gross profits (€20.00 + €2.00) |

### Vollständiger Fünf-Tage-Test (unabhängig nachgerechnet)

Unabhängig gerechnet von Hand und mit einem separaten Rechenskript außerhalb des Repos, das keinen Projektcode verwendet. Die Werte gelten **nur** für das jeweils genannte Szenario und die genau beschriebene Strategie.

**Test 23, Exam Week, gespielt über `db` (Strategie „Premium except Open Day“):**

- Tag 1–3 und 5: Preise €8.00 / €2.00 / €4.00. Tag 4: Preise €4.00 / €1.00 / €2.00.
- Gekauft wird jeden Tag genau die Nachfrage der gewählten Stufe: Tag 1 und 5 je 5/5/5, Tag 2 und 3 10/5/5, Tag 4 14/14/14.
- Es bleibt nie Restbestand.

| Tag | Einkauf | Gross profit | Kasse nach Abschluss |
|---|---:|---:|---:|
| 1 | €17.50 | €52.50 | €152.50 |
| 2 | €27.50 | €82.50 | €235.00 |
| 3 | €27.50 | €82.50 | €317.50 |
| 4 | €49.00 | €49.00 | €366.50 |
| 5 | €17.50 | €52.50 | €419.00 |

Soll: Overall gain / loss **€319.00** = Summe der Gross profits. Danach zeigt die Oberfläche die Endergebnisse und den Baseline-Vergleich: Baseline €229.00, Differenz **+€90.00**.

**Test 24, gleiche Strategie, aber auch an Tag 4 Premium und kein Einkauf an Tag 4:** Tag 4 bringt €0.00, die Kasse nach Tag 4 bleibt bei €317.50, nach Tag 5 €370.00. Overall gain / loss **€270.00**.

**Test 25, Baseline Exam Week (reine Funktion):**

| Tag | Gross profit | Kasse |
|---|---:|---:|
| 1 | €35.00 | €135.00 |
| 2 | €55.00 | €190.00 |
| 3 | €55.00 | €245.00 |
| 4 | €49.00 | €294.00 |
| 5 | €35.00 | €329.00 |

Overall **€229.00**.

**Test 26, Baseline Heatwave:**

| Tag | Gross profit | Kasse |
|---|---:|---:|
| 1 | €38.00 | €138.00 |
| 2 | €32.00 | €170.00 |
| 3 | €32.00 | €202.00 |
| 4 | €43.00 | €245.00 |
| 5 | €39.00 | €284.00 |

Overall **€184.00**.

**Test 27, Determinismus:** Die Baseline zweimal für dasselbe Szenario berechnen ergibt identische Tageswerte und dasselbe Endergebnis.

**Test 28, Budgetregel der Baseline:** Bei einer Startkasse von €5.00 und einer unteren Nachfrage von 10/10/10 kauft sie 2 Coffee (€4.00), 2 Water (€1.00) und 0 Bars.

Zur Information, kein Test: In Heatwave bringt die beste Preisstufe je Produkt und Tag €262.50, Premium an allen Tagen €246.00. Das zeigt, dass die Falle am Sports day €16.50 kostet.

### Bericht und Oberfläche

| # | Ausgangslage | Aktion | Sollwert |
|---|---|---|---|
| 29 | Exam Week, Tag 4 | Seite öffnen | Ereignis „Open Day“ mit Stufen (14, 0) je Produkt sichtbar. Bei Preis €8.00 und Lager 14 zeigt „Expected sales“ für Coffee 0 |
| 30 | Abgeschlossenes Spiel aus Test 23 | Seite öffnen | Overall gain / loss €319.00, Baseline €229.00, Differenz +€90.00. Tageszeilen 52.50/35.00, 82.50/55.00, 82.50/55.00, 49.00/49.00, 52.50/35.00 |
| 31 | Abgeschlossene Spiele A und B | Bericht von A | Enthält nur Zahlen von A |
| 32 | **[Optional]** CSV von A | Herunterladen | Nur Zeilen von A, kein Token in Inhalt und Dateiname |

**Manuelle Abnahme auf der deployten URL [Annahme, noch nicht durchgeführt]:**

- Test 23 im Browser durchspielen.
- Neu laden.
- Link in privatem Fenster ohne Token öffnen.
- Einen ungültigen Link öffnen.
- Ein Spiel löschen.
- Die ungültigen Eingaben aus den Tests 15–17 eingeben.

### Abhängigkeiten

- **Ziel:** keine neue Laufzeitabhängigkeit; `streamlit` bleibt die einzige, `pytest` bleibt Dev-Abhängigkeit.
- **Audit gegen die tatsächlich festgeschriebenen Versionen:**
  1. `uv export --frozen --all-groups --format requirements-txt` in eine Datei **außerhalb** des Repos schreiben.
  2. `pip-audit` mit genau dieser Datei als Prüfziel ausführen (`-r <datei>`).
  3. Ergebnis und Datum in der README festhalten.
- Die genauen Optionen von `pip-audit` (etwa für Hashes oder ohne erneute Auflösung) prüfen wir beim Ausführen. Ein `uvx pip-audit` ohne Prüfziel reicht nicht.
- **Ergebnis (22.11.2026, 02:16; wiederholt um 15:00 mit demselben Ergebnis):**
  - `uv export --frozen --all-groups --no-emit-project --format requirements-txt` in eine temporäre Datei außerhalb des Repos geschrieben.
  - `pip-audit 2.10.1 -r <datei> --require-hashes --disable-pip` prüfte 37 Pakete.
  - Die zwei Pakete mit Plattformbedingung (`colorama`, `watchdog`) wurden einzeln mit `--no-deps` geprüft.
  - **Keine bekannten Schwachstellen in allen 39 Paketen.** Es waren keine Updates nötig.

## Zuordnung zu den Bewertungskriterien

Die Einträge in der Spalte **Offiziell (High)** zitieren die Kursseite. Die übrigen Spalten beschreiben, was wir liefern wollen, und sind keine Zusage für eine Stufe.

| Kriterium | Offiziell (High) | Unser Beitrag [Ziel] | Bekannte Lücke |
|---|---|---|---|
| 1 · It works (20 %) | „runs all workflows without errors, including invalid input“ auf der deployten App | Tests 9–18, 22, 29–31 sowie manuelle Abnahme auf der URL | Spiele können auf dem Host verloren gehen; abgefangen durch die Meldung und Grenze oben |
| 2 · UI/UX (20 %) | „workflows are direct, and results and errors are clearly shown“ | Ereignis vor der Entscheidung, Expected sales, einheitliche Kennzahlen, Vergleichsbericht, eine Meldung für alle ungültigen Links | Das Link-Konzept muss in einem Satz verständlich sein |
| 3 · Scope (20 %) | „Substantial features that go well beyond a solo project, implemented consistently“; Maßstab: 3–4 Personen, drei Wochen | Mehrere private Spiele, zwei Szenarien mit Ereignissen, Baseline und Vergleich | Für diesen Maßstab eher schmal; bewusst gewählt |
| 4 · Verification (10 %) | „accepted and rejected actions and edge cases, and all pass on `main`“ | Tests 1–31 mit handgerechneten Sollwerten | Cloud-Verhalten nur manuell |
| 5 · Security (10 %) | „Access control and input validation are enforced; dependencies are minimal, pinned, and without known vulnerabilities“ | Token-Autorisierung in `db.py`, Formatprüfung, Eingabeprüfung, `uv.lock`, Audit | Link = Zugriff; keine Begrenzung der Spielanzahl |
| 6 · Walkthrough (20 %) | „how the project is built, why, what its limits are, and how it could change“ | Why, Limits und „Wie es sich ändern könnte“ in dieser Spec und der README | – |

**Weitere offizielle Vorgaben (unabhängig vom Umfang):**

- Repo öffentlich, keine Zugangsdaten.
- Code der deployten App auf `main`.
- README mit URL, Namen und Studierendennummern aller Mitglieder sowie den Befehlen für App und Tests.
- Abgabe bis 23.11.2026, 23:59. Commits danach werden nicht bewertet.
- Live-Demo unter der deployten URL, keine Folien oder Videos als Ersatz.
- Teamgröße 3–4 und Code-Beiträge aller Mitglieder. Das wird separat geklärt; diese Spec setzt keine Einzelabgabe als genehmigt voraus.

## Plan

| Block | Inhalt | Fertig, wenn |
|---|---|---|
| S | Diese Spec prüfen (eine Codex-Runde) | Keine kritischen offenen Punkte |
| P0 | Technischer Versuch auf einem eigenen Branch: Token-Prototyp auf Community Cloud, Python 3.12, `uv.lock` | Annahmen 1–3 bestätigt oder Plan angepasst |
| P1 | Schema, Autorisierung, Löschen, Linkwechsel, Solo-Schema-Schutz | Tests 1–18 grün, kein `WHERE id = 1` mehr |
| P2 | Szenarien, Stufen, Ereignisanzeige, Expected sales | Tests 19–22, 29 grün |
| P3 | Baseline und Vergleich | Tests 23–28, 30–31 grün |
| P4 | Merge, Deploy, manuelle Abnahme, Audit, README, `AGENTS.md` | Deploy entspricht `main`; README-Befehle funktionieren in einer frischen Kopie |
| — | Mo, 23.11., ca. 20:00: Merge-Stopp und Abgabe | – |
