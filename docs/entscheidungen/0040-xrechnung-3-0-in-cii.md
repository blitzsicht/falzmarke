# 0040 — XRechnung 3.0 in CII

**Datum:** 13.09.2026 · **Status:** angenommen ·
**Löst:** [#117](https://github.com/blitzsicht/falzmarke/issues/117) ·
**Gehört zu:** [#111](https://github.com/blitzsicht/falzmarke/issues/111) · **Ergänzt:** ADR 0039

## Worum es geht

An öffentliche Auftraggeber in Deutschland geht nicht ZUGFeRD, sondern XRechnung — als reine
XML und mit der Leitweg-ID als Adresse im Verwaltungsnetz. ADR 0039 hat das Profil XRECHNUNG
ausdrücklich an #117 verwiesen. Diese Entscheidung legt fest, was falzmarke dafür erzeugt.

## Entscheidung 1: XRechnung 3.0, Syntax CII

**Vorgabe ist XRechnung 3.0 in der Syntax UN/CEFACT CII**, nicht UBL. Guideline-ID
`urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0`, Prozess-ID
`urn:fdc:peppol.eu:2017:poacc:billing:01:1.0`.

**Begründung.** Der CII-Erzeuger aus #116 existiert; ein zweiter für UBL wäre ein zweiter
Datenweg durch dieselben Zahlen. Und der fremde Prüfer der CI (Mustang 2.26.0) wendet auf CII die
XRechnung-Regeln XR_30 an — gemessen, nicht angenommen: Die eigene Beispiel-XRechnung besteht,
dieselbe Datei ohne Käuferreferenz fällt an genau BR-DE-15 durch.

Die IDs stehen so in `validXRV30.xml` aus dem Mustang-Testmaterial. **Nicht** in
`validXRechnung.pdf`: Die trägt XRechnung 1.2 und läuft gegen XR_12 — sichtbar geworden erst,
als `erechnung_pruefen.py` die Regelfassung je Datei ausgab.

## Entscheidung 2: `erechnung:` im Schreiben, nicht im Profil

`erechnung: en16931 | xrechnung`, ohne Angabe `en16931`. Derselbe Absender beliefert Behörden und
Firmen; die Wahl gehört zum Empfänger. Ebenso `leitweg_id:` bzw. `kaeuferreferenz:` (beide BT-10,
nie zugleich) und `empfaenger_anschrift.adresse` (BT-49).

## Entscheidung 3: reine XML als eigener Befehl, das PDF bleibt möglich

`falzmarke xml` schreibt nur die XML, ohne Typst. `render` setzt auch eine XRechnung als PDF/A-3b
mit eingebetteter XML (`ConformanceLevel` `XRECHNUNG`, wie Mustangs Referenz) — und sagt dabei,
dass eine Behörde die XML erwartet. Ein Schalter an `render` hätte `--png`, `--pdfua` und den
Geometriebericht bedeutungslos gemacht; jedes eigene Erzeugnis hat einen eigenen Befehl (`email`,
`preview`, `einlesen`).

**Offen, und benannt:** Ob FeRD für das Profil XRECHNUNG im PDF den Dateinamen `xrechnung.xml`
statt `factur-x.xml` vorsieht, ist nicht nachgelesen (die Spezifikation liegt hinter einem
Formular). Mustangs Referenz `validXRechnung.pdf` trägt `factur-x.xml`, und die eigene
XRechnung im PDF besteht damit gegen XR_30 (gemessen am 13.09.2026); falzmarke bleibt dabei.

## Entscheidung 4: dieselbe Pflichtliste für `lint` und Emitter

Was XRechnung über EN 16931 hinaus verlangt, steht an einer Stelle
(`emit_xml.xrechnung_maengel`): Käuferreferenz, Kontakt mit Name, Telefon und E-Mail, Konto,
elektronische Adressen beider Seiten. `lint` meldet es, der Emitter bricht damit ab — weil der
MCP-Dienst ohne `lint` setzt. Die Liste folgt den Regeln, die Mustang anwendet; die
Schematron-Dateien der KoSIT sind nicht selbst gelesen, deshalb steht die Regel als
Werkzeugregel. Belegt ist ihre Wirkung am fremden Prüfer in der CI.

Die Leitweg-ID wird nach der Format-Spezifikation 2.0.2 geprüft (Form und Prüfziffer nach
ISO/IEC 7064 MOD 97-10) — eine Regel mit Primärquelle, weil die Spezifikation gelesen ist.

## Was nicht behauptet wird

Kein „XRechnung-konform“. Die CI belegt, dass ein Beispiel gegen eine Regelfassung (Mustang
2.26.0, XR_30) besteht. Sie belegt nicht, dass jede erzeugte Rechnung besteht, und nicht, dass ein
Empfänger sie annimmt. `tests/test_textkanon.py` sperrt den Begriff.

## Nicht Teil dieser Entscheidung

UBL, Versand über Peppol oder die Rechnungseingangsplattformen (ADR 0034 gilt), steuerfreie
Rechnungen nach § 19 UStG, Gutschriften, der KoSIT-Validator als zweiter Prüfer.
