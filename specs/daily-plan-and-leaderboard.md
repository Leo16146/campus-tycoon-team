# Tagesplan und Szenario-Rangliste

**Stand:** Entwurf zur Prüfung, 22.11.2026, 12:15. Nichts davon ist implementiert.
Grundlage ist `main` @ `acd00b2` (P1–P4) und [`campus-week.md`](campus-week.md).
Es gelten dieselben Regeln wie dort: Beträge in ganzen Cent, englische Oberfläche,
Zugriff nur über das Token, eine Transaktion pro Aktion.

**Reihenfolge:**

1. Die heutige App deployen und nach `docs/acceptance-checklist.md` abnehmen.
2. **E1 Tagesplan** umsetzen (Pflicht dieser Runde).
3. **E2 Rangliste** nur, wenn nach E1 noch Zeit für Implementierung, Review und eine
   erneute Browser-Abnahme bleibt.
4. CSV-Export erst danach.

Ein Strategieplaner kommt nicht. Er wäre eine Alternative zur Rangliste, keine
Ergänzung.

Die Kursseite verlangt weder eine Rangliste noch bestimmte Technik. Gemeinsame
Daten sind dort nur eine mögliche Richtung. Keine der Erweiterungen garantiert
eine bestimmte Bewertungsstufe.

---

## E1 · Tagesplan („Plan today“) und „How to play“

### Why

Heute kauft man jedes Produkt einzeln (Produkt wählen, Menge, „Buy“) und speichert
jeden Preis einzeln mit Enter. Ein Tag braucht dadurch bis zu 16 Bedienschritte:
dreimal 3 für den Einkauf, dreimal 2 für die Preise, 1 für den Handel.

Mit dem Tagesplan stehen alle drei Produkte auf einer Seite. Es bleiben bis zu
3 Mengen, bis zu 3 Preise und 2 Knöpfe, also bis zu **8 Schritte**. Mengen und
Preise müssen weiterhin eingegeben werden. Neu ist eine Vorschau vor dem Anwenden.

Die Startseite erklärt bisher weder das Ziel noch die Bewertung.

### What

**Startseite: Kasten „How to play“** (englisch, genau diese drei Punkte):

- *Goal:* end the five trading days with the highest possible overall gain.
- *Each day:* check today's event, buy stock, set selling prices, start the trading day.
- *Score:* final cash + remaining stock at unit cost − €100.00, compared with a simple
  baseline strategy.

**Spielseite: Abschnitt „Plan today“** ersetzt „Buy stock“ und „Selling prices“.

- **Eine Zeile je Produkt** (Coffee, Water, Granola bar). Sie zeigt:
  - Lager
  - Eingabefeld *Buy* (ganze Zahl ≥ 0, Standard 0)
  - Eingabefeld *Selling price (€)*
  - Vorschau: *Cost*, *Demand*, *Expected sales*
- **Bewusst kein `st.form`.** Laut Streamlit-Doku übermittelt ein Formular Werte
  erst beim Absenden. Eine laufende Vorschau ginge damit nicht. Deshalb werden
  normale Eingabefelder verwendet. Jede Änderung löst einen neuen Lauf mit
  aktueller Vorschau aus. Gespeichert wird aber erst über den Knopf.
- **Vorschau je Produkt:**
  - *Cost* = Menge × Stückkosten.
  - *Demand* = Nachfrage des heutigen Ereignisses beim eingegebenen Preis.
  - *Expected sales* = min(*Demand*, Lager + Menge).
  - Ist der Preis ungültig, zeigt die Vorschau *Invalid price*.
- **Summe:** *Total purchase cost* und *Cash after purchases*. Ist die Summe größer
  als die Kasse, erscheint dort ein Hinweis.
- **Knopf „Apply purchases and prices“** ruft `db.apply_plan(path, token, day,
  quantities, prices)` auf, in **einer** Transaktion:
  1. Token und Tag prüfen (`current_game`).
  2. Alle Mengen prüfen (ganze Zahl ≥ 0) und alle Preise (`price_in_cents`).
  3. Prüfen, ob die Kasse für die **Gesamtsumme** reicht.
  4. Erst dann alle Käufe und Preise speichern.
  - Ist eine Eingabe ungültig oder die Summe nicht bezahlbar, wird **nichts**
    gespeichert.
- **Nach Erfolg:** Alle Mengenfelder werden auf 0 zurückgesetzt, damit ein
  erneutes Anwenden nicht noch einmal kauft. Die Preisfelder zeigen die
  gespeicherten Preise. Meldung zum Beispiel „Bought 5 Coffee, 5 Water. Prices
  saved.“ oder „Prices saved.“
- **Nichts geändert:** Sind alle Mengen 0 und alle Preise gleich den
  gespeicherten, erscheint „Nothing to apply.“ und es wird nichts geschrieben.
- **Preisfelder** werden nur aus der Datenbank gefüllt, wenn sie noch leer sind:
  beim Öffnen des Spiels, nach erfolgreichem Anwenden, nach einem Tagesabschluss
  und beim Linkwechsel. Heute geschieht das bei **jedem** Lauf (`app.py`, Zeile
  209); das würde eingetippte, noch nicht angewendete Preise überschreiben.
- **„Start trading day“ ist gesperrt** (`disabled`), solange eine Menge > 0 ist
  oder ein Preisfeld vom gespeicherten Preis abweicht. Daneben steht: *„Apply or
  undo your changes before trading.“* So wird nie mit alten Preisen gehandelt,
  weil jemand das Anwenden vergessen hat.
- **Linkwechsel:** `GAME_SESSION_KEYS` umfasst zusätzlich die Mengen- und Preisfelder.
- **Datenbank:** `db.buy` und `db.set_price` bleiben für Tests und als
  Einzelaktionen erhalten. `apply_plan` verwendet dieselben Prüfungen. Gesperrte
  Datenbank → `DatabaseBusy` wie bisher, nichts gespeichert.

**Nicht enthalten:** Rückgängig machen nach dem Anwenden, Speichern von
Teilplänen, automatischer Handel.

### Done when (E1)

Jeder Fall beginnt mit einem neuen Exam-Week-Spiel an Tag 1 (€100.00, Lager 0/0/0,
Preise €4.00 / €1.00 / €2.00), sofern nicht anders angegeben.

| # | Aktion | Sollwert |
|---|---|---|
| U1 | Startseite öffnen | Kasten „How to play“ mit Goal, Each day und Score wie oben |
| U2 | Coffee Buy 10, Preis 8.00 | Vorschau Coffee: Cost €20.00, Demand 5, Expected sales 5. Total €20.00, Cash after €80.00. Datenbank unverändert |
| U3 | Wie U2, dann „Apply …“ | Kasse €80.00, Lager 10/0/0, Coffee-Preis €8.00. Alle Buy-Felder zeigen 0, Preisfeld Coffee zeigt 8.00 |
| U4 | Nach U3 erneut „Apply …“ ohne Änderung | „Nothing to apply.“, Kasse €80.00, Lager 10/0/0 |
| U5 | Coffee 10, Water 5, Coffee-Preis „abc“, „Apply …“ | Fehlermeldung. Kasse €100.00, Lager 0/0/0, Preise €4.00 / €1.00 / €2.00. Vorschau Coffee zeigt „Invalid price“ |
| U6 | Coffee 40 (€80.00) + Water 41 (€20.50), „Apply …“ | Total €100.50, Hinweis bei der Summe. Ablehnung „Not enough cash“, **nichts** gespeichert, obwohl jeder Kauf allein bezahlbar wäre |
| U7 | Coffee 40 + Water 40 = €100.00, „Apply …“ | Angenommen, Kasse €0.00, Lager 40/40/0 |
| U8 | `apply_plan` direkt mit Menge −1 bzw. 1.5 | `ValueError`, nichts gespeichert |
| U9 | Coffee Buy 5 eingeben, nicht anwenden | „Start trading day“ gesperrt, Hinweis sichtbar. Nach „Apply …“ wieder freigegeben |
| U10 | Coffee-Preis 8.00 eintippen, nicht anwenden, dann Water Buy 3 eingeben | Preisfeld Coffee zeigt weiter 8.00, Handel gesperrt |
| U11 | Spiel A mit eingetippten Werten, Wechsel auf Link B | B zeigt Buy 0 und seine eigenen gespeicherten Preise |
| U12 | `apply_plan` mit veraltetem Tag; nach Tag 5 | „game has changed“ bzw. „complete“, nichts gespeichert |
| U13 | `apply_plan` bei gesperrter Datenbank | `DatabaseBusy`, nichts gespeichert. Nach der Freigabe genau einmal erfolgreich |
| U14 | Strategie aus Test 23 vollständig über die neue Oberfläche | Kasse nach den Tagen €152.50 / €235.00 / €317.50 / €366.50 / €419.00. Overall gain / loss €319.00, Differenz +€90.00 |

- Bestehende Oberflächentests, die „Buy“ und das Speichern per Enter verwenden,
  werden auf den Tagesplan umgestellt. Ihre Sollwerte bleiben gleich.
- Die Tests auf Datenbankebene (`buy`, `set_price`) bleiben unverändert.
- `docs/acceptance-checklist.md` wird an den neuen Ablauf angepasst.

---

## E2 · Freiwillige Szenario-Rangliste (nur nach E1)

### Why

Ein neuer gemeinsamer Ablauf: spielen → Ergebnis veröffentlichen → mit anderen
vergleichen. Fair ist das, weil alle Spielenden eines Szenarios dieselben
Ereignisse bekommen. Manipulationssicher wird die Rangliste dadurch nicht (siehe
„Grenzen“).

### Regeln

1. **Nur abgeschlossene Spiele:** Veröffentlichen ist erst nach Tag 5 möglich
   (gespeicherter Tag = 6). Vorher wird abgelehnt mit *„Finish all five trading
   days before publishing.“*
2. **Ergebnis nur aus der Datenbank:**
   - `publish_result(path, token, nickname)` berechnet das Overall gain / loss in
     der Transaktion aus der gespeicherten Kasse und dem gespeicherten Lager
     (`final_result`) und speichert es.
   - Ein abgeschlossenes Spiel kann sich nicht mehr ändern, das Ergebnis bleibt
     also gültig.
   - Kein Wert aus dem Browser fließt ins Ergebnis ein, nur der Spitzname.
3. **Höchstens ein Eintrag pro Spiel**, gesichert über den Primärschlüssel
   `game_id`. Ein zweites Veröffentlichen wird abgelehnt mit *„This game is
   already on the leaderboard.“*
   - Ohne Konten lässt sich **ein Eintrag pro Person nicht garantieren**.
4. **Spitzname:**
   - Leerzeichen am Anfang und Ende werden entfernt.
   - Danach muss er `[A-Za-z0-9 _-]{3,20}` entsprechen, sonst *„Use 3–20
     letters, digits, spaces, _ or -.“*
   - Gleiche Spitznamen sind erlaubt.
   - Es gibt keinen Wortfilter.
5. **Getrennte Ranglisten je Szenario**, sortiert nach Ergebnis absteigend, bei
   Gleichstand nach Reihenfolge der Veröffentlichung (`entry_id` aufsteigend).
6. **Platz = 1 + Anzahl der Einträge mit höherem Ergebnis.** Gleiche Ergebnisse
   haben also denselben Platz (1, 1, 3).
7. **Öffentlich sichtbar** sind nur Platz, Spitzname und Overall gain / loss.
   Niemals Token, Hash, Spiel-ID oder Link.
8. **Zurückziehen:** Das eigene Spiel bietet *„Remove my result“*. Danach darf
   erneut veröffentlicht werden, als neuer Eintrag mit neuer Reihenfolge.
9. **Löschen des Spiels** entfernt seinen Ranglisteneintrag in derselben
   Transaktion.
10. **Anzeige:**
    - Die Startseite zeigt für jedes Szenario die besten 10 Einträge, oder *„No
      results published yet.“*
    - Der Endbildschirm zeigt die Rangliste des eigenen Szenarios, nach dem
      Veröffentlichen zusätzlich *„Your rank: X of N“*.
    - Beide zeigen den Hinweis *„The leaderboard is stored temporarily and may be
      reset when the server restarts.“*
11. **Zugriff:** Veröffentlichen und Zurückziehen brauchen das Token und laufen
    über `authorized_game`. Das Lesen der Rangliste ist öffentlich und gibt nur
    die Spalten aus Regel 7 zurück.
12. **Schema:**
    - Neue Tabelle `leaderboard (entry_id INTEGER PRIMARY KEY, game_id INTEGER
      NOT NULL UNIQUE, nickname TEXT NOT NULL, score INTEGER NOT NULL)`.
    - `initialize()` legt sie auch in einer bestehenden P4-Datenbank an und
      verändert dabei keine vorhandenen Daten.
    - Die Abkürzung „alle Tabellen vorhanden → nur lesen“ muss `leaderboard`
      einschließen.

### Grenzen (E2)

- Eine Person kann mit mehreren Spielen mehrfach teilnehmen.
- Die Rangliste ist so vorübergehend gespeichert wie die Spiele.
- Spitznamen werden nicht moderiert.
- Die Zahl der Einträge ist nicht begrenzt; angezeigt werden die besten 10.

### Done when (E2)

Spiele, die mit der Strategie aus Test 23 gespielt wurden, enden bei €319.00.
Spiele ohne Einkauf enden bei €0.00.

| # | Ausgangslage | Aktion | Sollwert |
|---|---|---|---|
| L1 | Exam Week, Tag 3 | Veröffentlichen als „Ana“ | Abgelehnt („Finish all five trading days“), keine Zeile in `leaderboard` |
| L2 | A fertig (€319.00) | Veröffentlichen als „Ana“ | Eine Zeile mit score 31900 und nickname „Ana“ |
| L3 | Nach L2 | A erneut veröffentlichen | Abgelehnt („already on the leaderboard“), weiterhin eine Zeile |
| L4 | A fertig | Spitznamen „“, „ab“, 21 Zeichen, „Leo!“, „<b>Leo</b>“ | Alle abgelehnt, nichts gespeichert |
| L5 | A fertig | Spitznamen „  Leo  “ und „Team 4_a-b“ (in getrennten Spielen) | Gespeichert als „Leo“ bzw. „Team 4_a-b“ |
| L6 | Exam Week: A €319.00 „Ana“ (zuerst), B €0.00 „Ben“, C €319.00 „Cleo“ (zuletzt). Heatwave: D €0.00 „Dan“ | Ranglisten lesen | Exam Week: 1 Ana €319.00 · 1 Cleo €319.00 · 3 Ben €0.00. Heatwave: 1 Dan €0.00 |
| L7 | Wie L6 | A „Remove my result“ | Exam Week: 1 Cleo · 2 Ben. Erneut als „Ana“ veröffentlichen: 1 Cleo · 1 Ana · 3 Ben |
| L8 | Wie L6 | Spiel A löschen | A steht nicht mehr in der Rangliste, die übrigen Einträge sind unverändert |
| L9 | Wie L6 | Startseite und Endbildschirm von C | Spalten nur Rank, Nickname, Overall gain / loss. Kein Token im Seitentext. Endbildschirm zeigt „Your rank: 1 of 3“ und den Speicherhinweis |
| L10 | A fertig | Veröffentlichen und Zurückziehen mit unbekanntem bzw. ungültigem Token | „not valid“, keine Änderung |
| L11 | 12 Exam-Week-Einträge mit verschiedenen Ergebnissen | Startseite | Genau 10 Zeilen, absteigend sortiert |
| L12 | Datenbank im P4-Schema mit einem Spiel | `initialize()` | Tabelle `leaderboard` ist angelegt, Spiel und Verkäufe sind unverändert |
| L13 | A fertig, Datenbank gesperrt | Veröffentlichen | `DatabaseBusy`, nichts gespeichert. Nach der Freigabe genau einmal erfolgreich |
| L14 | Leere Rangliste | Startseite | „No results published yet.“ für beide Szenarien |

---

## Zeitplan (Schätzung, keine Zusage)

Stand: Sonntag, 12:15. Abgabe: Montag, 23:59.

| Block | Inhalt | Ergebnis |
|---|---|---|
| jetzt | Deployment der heutigen App aus `main`, Abnahme mit der Prüfliste | URL und Abnahme dokumentiert |
| So, Nachmittag | E1 umsetzen, Tests U1–U14, Codex-Review | Merge nach Freigabe, erneute Browser-Abnahme |
| So, Abend / Mo, Vormittag | Nur wenn E1 abgenommen ist: E2, Tests L1–L14, Review, Browser-Abnahme | Merge nach Freigabe |
| Mo, Nachmittag | README und Prüfliste aktualisieren, Vorbereitung auf die Begehung | – |
| Mo, ca. 20:00 | Merge-Stopp. Letzter Durchlauf auf der URL, Abgabe | – |

Wird E2 nicht rechtzeitig abgenommen, bleibt es unter „How it could change“ in der
README. Eine halb fertige Rangliste wird nicht gemergt.
