---
typ: rechnung
profil: example
empfaenger:
  - Muster GmbH
  - Musterstraße 1
  - 12345 Musterstadt
empfaenger_anschrift:
  name: Muster GmbH
  strasse: Musterstraße 1
  plz: "12345"
  ort: Musterstadt
  land: DE
datum: 2026-09-11
betreff: Rechnung 2026-0044 für Beratung und Fachliteratur
rechnungsnummer: "2026-0044"
leistungsdatum: 2026-10-03
zahlungsziel: 2026-10-31
positionen:
  - bezeichnung: Beratung und Aufbau
    menge: 1
    einzelpreis: 200.00
    steuersatz: 19
    betrag: 200.00
  - bezeichnung: Fachbücher Veranstaltungstechnik
    menge: 5
    einheit: Stück
    einzelpreis: 20.00
    steuersatz: 7
    betrag: 100.00
summen:
  netto: 300.00
  steuer:
    - satz: 19
      basis: 200.00
      betrag: 38.00
    - satz: 7
      basis: 100.00
      betrag: 7.00
  steuer_gesamt: 45.00
  brutto: 345.00
anrede: Sehr geehrte Damen und Herren,
---
anbei unsere Rechnung für die Beratung und die mitgelieferten Fachbücher.

Die Beratungsleistung trägt den Regelsatz von 19 %, die Bücher nach § 12 Absatz 2 Nummer 1
UStG den ermäßigten Satz von 7 % — zwei Steuersätze auf einer Rechnung, jeder mit eigener
Zeile in der Summentabelle.

Dieselben Angaben liegen dem PDF als XML nach EN 16931 bei. Ihre Buchhaltung kann sie
einlesen, ohne etwas abzutippen.
