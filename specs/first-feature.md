# Erster Handelstag am Campus-Kiosk

**Stand:** Testentwurf zur fachlichen Prüfung. Grundlage ist der [offizielle Projektbrief](../docs/product-brief.html), Version 1.0. Alle Zahlen unten sind Sollwerte.

## Why

Der Spieler soll nach einem Handelstag zwei Fragen beantworten können: Wie viel Geld ist in der Kasse und wie viel hat der Kiosk verdient? Der Kaffeeverkauf macht den Unterschied sichtbar. Die Ware wurde morgens bezahlt. Beim Verkauf fließen die vollen Einnahmen in die Kasse, während der Wareneinsatz den Rohertrag mindert.

## What

Auf einer frischen Datenbank beginnt Tag 1 mit 100,00 €, leerem Lager und 0 von 5 abgeschlossenen Tagen (CT01). Der Spieler wählt Produkt und Menge, sieht den Einkaufspreis für die gesamte Menge und bestätigt den Kauf. Zulässig sind positive ganze Stückzahlen, die aus der Kasse bezahlt werden können (CT02, CT R3).

| Produkt | Stückkosten | Referenzpreis | Anfänglicher Verkaufspreis |
|---|---:|---:|---:|
| Kaffee | 2,00 € | 4,00 € | 4,00 € |
| Wasser | 0,50 € | 1,00 € | 1,00 € |
| Müsliriegel | 1,00 € | 2,00 € | 2,00 € |

Der Spieler sieht die Verkaufspreise und die Nachfrageregel (Teil von CT03, CT R1). Bis einschließlich Referenzpreis beträgt die Nachfrage 10 Stück, darüber bis einschließlich des doppelten Referenzpreises 5 Stück, darüber 0 Stück. Ein Klick auf „Handelstag starten“ rechnet alle drei Produkte ab. Absatz ist das Minimum aus Nachfrage und Bestand. Restware bleibt im Lager (CT04, CT R2). Die Ansicht zeigt pro Produkt und in Summe Absatz, Umsatz, Wareneinsatz und Rohertrag (CT R4). Das Ergebnis von Tag 1 bleibt im Verlauf. Als Nächstes steht Tag 2 an (Teil von CT05, CT R5).

### Geplante Zustandsdaten und Zuständigkeiten

- **Katalog:** Produktkennung, Name, feste Stückkosten und Referenzpreis. **Spielstand:** Kasse, aktueller Tag, Bestand und aktueller Verkaufspreis je Produkt. Geldbeträge intern in ganzen Cent. Der Fortschritt ergibt sich aus den abgeschlossenen Tagen.
- **Tageshistorie:** Ein Abschluss je Spiel und Tag mit Positionen je Produkt für Absatz, Umsatz, Wareneinsatz und Rohertrag. Die angezeigten Summen ergeben sich aus diesen Positionen.
- **`app.py`** lädt den Stand und zeigt Einkaufsvorschau, Kaufentscheidung, Preise, Handelsaktion und Verlauf. Öffnen und Aktualisieren lösen keinen Handel aus.
- **`logic.py`** prüft Menge und Deckung und berechnet Nachfrage, Absatz, Geldbeträge und neue Bestände. Die Rechenregeln sind mit kleinen Zahlen ohne Oberfläche prüfbar.
- **`db.py`** lädt Katalog und Spielstand aus SQLite. Ein bestätigter Kauf speichert Kasse und Lager sofort zusammen. Ein Tagesabschluss speichert Ergebnis, Kasse, Bestände und nächsten Tag gemeinsam in einer Transaktion. Eine abgelehnte Aktion lässt den gespeicherten Stand unverändert.

## Out of scope

Die freie Preisänderung einschließlich sofortiger Speicherung (CT03, vollständiges A2), der Abschluss nach fünf Tagen und das bestätigte Ersetzen eines Laufs (CT01/CT05, A6) folgen später. Für diesen Ablauf wird ein vorhandenes Spiel fortgesetzt. Der volle Fünf-Tage-Lauf bleibt eine Kursanforderung.

**Abgleich mit dem Kursbrief:** Die Zahlen und Regeln im Briefing stimmen für diesen Ablauf mit A1, A3 und A5 überein. Genau drei Produkte erfüllen das Kursminimum von drei. Wasser- und Riegelpreise sowie die anfänglichen Verkaufspreise sind Kioskentscheidungen. 41 weitere Kaffee konkretisieren den vorgeschriebenen Ablehnungsfall über 82 €. SQLite und Cent sind technische Entscheidungen. Die eingeschränkte Preisbedienung und der fehlende Spielabschluss begrenzen diesen ersten Meilenstein.

## Done when

Für die Abnahme prüfen wir Regeln und Speicherung mit `uv run pytest` und den Klickablauf zusätzlich manuell. Jeder automatisierte Test stellt seine Ausgangslage selbst her. Speichertests verwenden eine temporäre SQLite-Datei. Die Zeilen 1–6 bilden beim manuellen Durchspielen einen zusammenhängenden Ablauf. Die weiteren Fälle sind unabhängig. Die Reihenfolge für Bestände und Preise ist Kaffee, Wasser, Müsliriegel.

| Prüfung | Ausgangslage | Aktion | Konkreter Sollwert |
|---|---|---|---|
| 1 · Start (CT01) | Neue, leere Datenbank | Spiel öffnen | Tag 1, 0/5 abgeschlossen, 100,00 €, Bestand 0/0/0, Preise 4,00/1,00/2,00 €, 0 Tagesabschlüsse. |
| 2 · Einkauf (A1) | Stand aus 1 | 10 Kaffee auswählen, Vorschau ansehen, kaufen und Spielstand über eine neue Datenbankverbindung laden | Vorschau 20,00 €. Danach 80,00 €, Bestand 10/0/0, weiter Tag 1, 0 Abschlüsse. |
| 3 · Ablehnung (A1) | Stand aus 2 | 41 weitere Kaffee auswählen, Kauf versuchen und gespeicherten Stand neu laden | Vorschau 82,00 €. Ablehnung wegen fehlender Deckung. Weiter 80,00 €, Bestand 10/0/0, Preise unverändert, Tag 1, 0 Abschlüsse. |
| 4 · Tagesabschluss (A3) | Stand aus 3, alle Verkaufspreise auf Referenzniveau | „Handelstag starten“ einmal klicken | Kaffee: 10 Stück, 40,00 € Umsatz, 20,00 € Wareneinsatz, 20,00 € Rohertrag. Wasser und Müsliriegel jeweils 0 Stück und 0,00 € in allen drei Geldspalten. Summe: 10 Stück, 40,00 / 20,00 / 20,00 €. Kasse 120,00 €, Bestand 0/0/0, Tag 2, 1/5 abgeschlossen, genau ein Abschluss für Tag 1. |
| 5 · Aktualisieren (CT R5) | Stand aus 4 | Browserseite neu laden | Tag 2, 120,00 €, Bestand 0/0/0, Preise 4,00/1,00/2,00 €. Genau ein Abschluss für Tag 1 mit denselben Positionen und Summen wie in 4. |
| 6 · Wiederaufnahme (A5) | Stand aus 5 | Streamlit-Prozess beenden, mit derselben SQLite-Datei neu starten, Spiel öffnen | Derselbe Stand wie nach 4, einschließlich Preisen, Verlauf und 1/5 Fortschritt. Tag 2 ist spielbereit. |
| 7 · Ungültige Menge (CT02) | Je Versuch frischer Stand aus 1 | Kauf von 0, −1 bzw. 1,5 Kaffee versuchen | Alle drei Eingaben abgewiesen. Jeweils 100,00 €, Bestand 0/0/0, Tag 1, 0 Abschlüsse. |
| 8 · Bestandsgrenze (A4) | Zwei unabhängige Fälle, Kaffee zu 4,00 €, Nachfrage 10, Lager 3 bzw. 0 Stück | Absatz und Restbestand für Kaffee berechnen | Absatz 3 bzw. 0 Stück, Restbestand in beiden Fällen 0 Stück. |
| 9 · Preisgrenzen (CT R1, Rechenteil von A2) | Referenzpreis für Kaffee 4,00 € | Die Nachfrage in der Spiellogik getrennt für 4,00 €, 4,01 €, 8,00 € und 8,01 € berechnen | Nachfrage in dieser Reihenfolge 10, 5, 5 und 0 Stück. Die Oberfläche zur Preisänderung wird später geprüft. |
| 10 · Gemischter Warenkorb und Restbestand (CT04, CT R2–R4) | Tag 1 nach Einkauf von 12 Kaffee und 4 Wasser für insgesamt 26,00 €. Kasse 74,00 €, Bestand 12/4/0, Preise auf Referenzniveau. | Tag einmal abrechnen und den gespeicherten Stand laden | Kaffee: 10 Stück, 40,00 € Umsatz, 20,00 € Wareneinsatz, 20,00 € Rohertrag. Wasser: 4 Stück, 4,00 € Umsatz, 2,00 € Wareneinsatz, 2,00 € Rohertrag. Riegel: alle Werte null. Gesamt: 14 Stück, 44,00 € Umsatz, 22,00 € Wareneinsatz, 22,00 € Rohertrag. Tag 2 beginnt mit 118,00 €, Bestand 2/0/0 und genau einem Abschluss. |

**Manuelle Abnahme:** Mit einem frischen Testspiel `uv run streamlit run app.py` starten und Zeilen 1–5 durchklicken. Für Zeile 6 den Prozess mit Strg+C beenden und im selben Projektordner mit demselben Befehl erneut starten. Der Dateitest prüft gespeicherte Werte. Erst der Prozessneustart prüft zusätzlich, ob die Oberfläche beim Start diese Datei lädt und keinen zweiten Verkauf auslöst.
