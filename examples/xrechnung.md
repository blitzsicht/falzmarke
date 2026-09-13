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
  adresse: einkauf@example.de
datum: 2026-09-11
betreff: Rechnung 2026-0043 für die Veranstaltung am 3. Oktober
rechnungsnummer: "2026-0043"
# An eine Behörde: XRechnung statt ZUGFeRD, mit Leitweg-ID (#117)
erechnung: xrechnung
leitweg_id: "04011000-1234512345-06"
leistungsdatum: 2026-10-03
zahlungsziel: 2026-10-31
positionen:
  - bezeichnung: Technik und Aufbau
    menge: 1
    einzelpreis: 1240.00
    steuersatz: 19
    betrag: 1240.00
  - bezeichnung: Bestuhlung
    menge: 120
    einheit: Stück
    einzelpreis: 3.00
    steuersatz: 19
    betrag: 360.00
summen:
  netto: 1600.00
  steuer:
    - satz: 19
      basis: 1600.00
      betrag: 304.00
  brutto: 1904.00
anrede: Sehr geehrte Damen und Herren,
---
anbei unsere Rechnung für die Veranstaltung am 3. Oktober.

An öffentliche Auftraggeber geht die Rechnung als XRechnung: der Befehl falzmarke xml erzeugt sie als
reine XML-Datei, ohne PDF. Dieses Schreiben ist die Fassung für Menschen.
