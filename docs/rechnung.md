# Rechnungen mit falzmarke

Ein Schreiben mit `typ: rechnung` im Frontmatter wird keine gewöhnliche Briefseite, sondern eine
Rechnung: `falzmarke render` setzt sie wie einen Brief — Anschriftfeld, Betreff, Anrede, Fußzeile
— und bettet ihr zugleich einen Datensatz bei, den kein Mensch liest. Warum es diesen zweiten
Datenvertrag gibt und was er nicht ist, steht in
[ADR 0039](entscheidungen/0039-falzmarke-rechnet-nicht.md); wie die Felder aussehen, in
[„Die Rechnungsfassung"](../skill/references/frontmatter.md#die-rechnungsfassung). Diese Seite
sagt, was am fertigen Dokument dabei herauskommt — und was nicht.

## Welche Formatfassung und welches Profil entstehen

An Firmen geht die Rechnung als PDF mit eingebetteter ZUGFeRD-XML, an Behörden geht dieselbe
Rechnung als reine XRechnung-XML, ohne PDF.

| | Empfänger | Befehl | Träger |
|---|---|---|---|
| **ZUGFeRD** | Firmen | `falzmarke render` | PDF/A-3b mit eingebetteter XML |
| **XRechnung** | öffentliche Auftraggeber | `falzmarke xml` | reine XML-Datei, kein PDF |

Beide tragen dieselbe Struktur — UN/CEFACT Cross Industry Invoice (CII) — und denselben
Grundumfang: das Profil **EN 16931** (COMFORT), nicht MINIMUM oder BASIC WL. Diese beiden kleineren
Profile enthalten keine Positionen und wären keine Rechnung im umsatzsteuerlichen Sinn; falzmarke erzeugt
sie nicht ([ADR 0039](entscheidungen/0039-falzmarke-rechnet-nicht.md)).

- **ZUGFeRD** ist die Vorgabe, wenn `erechnung:` im Kopf fehlt oder `en16931` trägt: ein PDF, in
  dem die XML unter `factur-x.xml` eingebettet liegt. Vorgabe ist ZUGFeRD 2.x in einer fest
  benannten Fassung (2.5.2, Stand 11.09.2026) — keine „jeweils aktuelle", denn eine Fassung, die
  sich zur Laufzeit ändert, ist kein Datenvertrag.
- **XRechnung** entsteht mit `erechnung: xrechnung` im Kopf. Vorgabe ist **XRechnung 3.0** in
  der Syntax CII, mit der Guideline-ID `urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0`.
  Dazu verlangt XRechnung, was EN 16931 freistellt: Käuferreferenz (Leitweg-ID oder eine andere
  Referenz), Ansprechpartner mit Telefon und E-Mail, ein Konto, die elektronische Adresse
  beider Seiten. `falzmarke lint` meldet, was fehlt, bevor `render` oder `xml` etwas schreibt.
  Eine XRechnung entsteht wahlweise auch als PDF — dann PDF/A-3b mit derselben eingebetteten XML,
  und mit dem Hinweis, dass eine Behörde die XML-Datei erwartet, nicht das PDF.

Welche Fassung ein Empfänger tatsächlich annimmt, entscheidet der Empfänger. falzmarke sagt, was
es erzeugt, nicht, ob es ankommt.

## Wer das Ergebnis abnimmt, und mit welcher Regelfassung

Eine Prüfung, die das eigene Erzeugnis gegen die eigene Vorstellung hält, bestätigt nur, dass
Erzeuger und Prüfer dasselbe meinen. Deshalb läuft in der CI ein fremdes Werkzeug gegen jede
Beispielrechnung, bei jedem Push:

- **Mustang 2.26.0** ([mustangproject.org](https://www.mustangproject.org), Apache-2.0) prüft
  das PDF gegen PDF/A-3 und das eingebettete XML gegen die Schematron-Regeln des jeweiligen
  Profils — für ZUGFeRD die Fassung `ZF_250`, für eine XRechnung `XR_30`. Mustang rechnet dabei
  die Summen nach; falzmarke tut das nicht, siehe unten.
- **KoSIT-Validator 1.6.3** mit der Konfiguration XRechnung 3.0.2 (Stand 31.08.2026) prüft eine
  XRechnung ein zweites Mal, unabhängig von Mustang — mit dem Werkzeug der herausgebenden Stelle
  und ihrer eigenen Schematron-Fassung.

Beide Prüfer laufen an derselben eigenen Beispielrechnung und an derselben absichtlich
unvollständigen Gegenprobe (ohne Käuferreferenz, Regel `BR-DE-15`): Die richtige Datei besteht,
die kaputte fällt an genau dieser Regel durch. Ein Prüfmittel, das nie ablehnt, wäre kein
Nachweis.

**Was das belegt, und was nicht.** Bestanden hat damit ein Beispiel gegen eine benannte
Regelfassung an einem gemessenen Datum — nicht jede erzeugte Rechnung, und nicht, dass ein
Empfänger sie annimmt. Diese Seite behauptet deshalb an keiner Stelle, eine erzeugte Rechnung
erfülle die Vorgaben eines Formats; das wäre eine Zusage, die falzmarke über sich selbst macht,
und die ist keine.

## Was falzmarke rechnet — und was nicht

**falzmarke rechnet nicht.** Es überträgt Positionen, Steuersätze und Beträge unverändert aus der
Quelle in PDF und XML. Es bildet keine Summe, keinen Steuerbetrag und keinen Bruttobetrag — wer
`1240.00` als Betrag einer Position schreibt, bekommt `1240.00` in beiden Dateien, gleich ob die
Menge mal der Einzelpreis dieselbe Zahl ergäbe oder nicht.

Was es tut, sind **Rechenproben über gegebene Werte**: Stehen `summen:` in der Quelle, prüft
`lint`, ob die Positionen den Nettobetrag ergeben, ob Netto plus Steuer den Bruttobetrag ergibt
und ob `steuer_gesamt:` zu den einzelnen Steuerbeträgen passt. Eine Abweichung ist eine Warnung —
sie hält den Lauf nicht an, und falzmarke setzt keinen eigenen Wert ein. Ein Fehler ist dagegen
ein Steuersatz einer Position, zu dem `summen.steuer` keine Zeile hat: Das PDF zeigt nur die
Summenzeilen, der Satz stünde also allein in der XML. Das ist eine Prüfung
über vorhandene Zahlen, kein Bilden eigener; die Grenze dazwischen ist ADR 0039, Entscheidung 1.

Wer verlässlich nachgerechnete Zahlen will, bekommt sie vom fremden Prüfer: Mustang rechnet die
Summen einer Rechnung nach (der Schalter dafür bleibt in der CI eingeschaltet), und genau das ist
die Arbeitsteilung — wer überträgt, lässt nachrechnen.

## Rechnungen von Kleinunternehmern

Sagt das Profil `rechnung.kleinunternehmer: true`, entsteht eine Rechnung ohne Umsatzsteuer nach
[§ 19 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html) ([ADR 0041](entscheidungen/0041-kleinunternehmer.md)). Die XML trägt Kategorie E,
Satz 0 und Steuer 0, dazu den Hinweis aus `rechnung.kleinunternehmer_hinweis:` als BT-120 und
BT-33. Einen VATEX-Code gibt es dafür nicht. Das PDF zeigt den Gesamtbetrag und darunter
denselben Hinweis. Die CI prüft je ein Beispiel als ZUGFeRD und als XRechnung bei Mustang, die
XRechnung auch beim KoSIT-Validator. Die Gegenproben ohne Hinweis und mit Steuersatz müssen an
BR-E-10 und BR-E-05 scheitern.

- **Den Wortlaut des Hinweises gibt falzmarke nicht vor** und bewertet ihn nicht.
- **Ob die Umsatzgrenzen eingehalten sind**, weiß das Werkzeug nicht. Wer die Grenze
  überschreitet, stellt sein Profil um.
- **§ 34a Satz 4 UStDV erlaubt dem Kleinunternehmer immer eine sonstige Rechnung**, also auch das
  PDF allein. falzmarke bettet die XML trotzdem ein, wie bei jeder Rechnung. Eine E-Rechnung
  eines Kleinunternehmers setzt nach Abschn. 14.7a Abs. 3 UStAE die Zustimmung des Empfängers
  voraus. Das prüft falzmarke nicht.
- **Gutschriften und die Kleinunternehmer-Identifikationsnummer** ([§ 19 Abs. 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html)) gehören
  nicht dazu.

## Was falzmarke nicht übernimmt

- **falzmarke vergibt keine Rechnungsnummern.** `rechnungsnummer:` steht in der Quelle und wird
  nur auf Nichtleere geprüft. Eine fortlaufende, lückenlose Nummerierung zu führen ist Sache der
  Buchhaltung des Absenders, nicht dieses Werkzeugs.
- **falzmarke bucht nicht.** Es gibt keine Debitorenliste und keine Schnittstelle zu einer
  Buchhaltung. Ein `zahlungsziel:` steht in PDF und XML, sonst nirgends.
- **falzmarke mahnt nicht.** Ein überschrittenes `zahlungsziel:` löst nichts aus — kein
  Mahnwesen, keine Fristenüberwachung, keine zweite Ausfertigung mit anderem Betreff.
- **falzmarke versendet nichts.** Es gibt für eine Rechnung keinen Versandbefehl, genau wie für
  jeden anderen Brief und jede E-Mail ([ADR 0034](entscheidungen/0034-email-ist-ausgabe.md)). Wer
  die Rechnung per E-Mail schicken will, hängt das PDF an eine Quelle mit `typ: email` an;
  `falzmarke email … --oeffnen` legt daraus einen Entwurf an, gesendet wird er von einem Menschen.

## Was ausdrücklich nicht behauptet wird

Kein „ZUGFeRD-konform“ und kein „XRechnung-konform“. Belegt ist, was oben steht: Die
Beispielrechnungen bestehen bei Mustang, die XRechnung zusätzlich beim KoSIT-Validator, jeweils
mit benannter Regelfassung. Für die Rechnung,
die jemand aus einer eigenen Quelle erzeugt, sagt das nichts. Und kein „normgerecht“ für das
Schreiben selbst: Der Abgleich mit dem Originaltext der DIN 5008:2020-03 steht aus, siehe
[Normmaße und Quellenlage](../skill/references/din5008.md).

Und keine Rechtsberatung: Ob eine Rechnung in einem Einzelfall als elektronische oder als sonstige
Rechnung gelten muss, entscheiden Sitz, Unternehmereigenschaft und Umsatz der Beteiligten — nicht
ein Werkzeug, das diese Tatsachen nicht kennt. Die Rechtslage dazu, mit Fundstellen, steht in
[„Was falzmarke behauptet — und was nicht"](recht.md#e-rechnung-was-das-umsatzsteuerrecht-verlangt).

## Verwandt

- [ADR 0039 — falzmarke rechnet nicht](entscheidungen/0039-falzmarke-rechnet-nicht.md)
- [ADR 0040 — XRechnung 3.0 in CII](entscheidungen/0040-xrechnung-3-0-in-cii.md)
- [Datenvertrag: die Rechnungsfassung](../skill/references/frontmatter.md#die-rechnungsfassung) —
  jedes Feld mit Beispiel
- [Was falzmarke behauptet — und was nicht](recht.md) — auch zum Umsatzsteuerrecht der
  E-Rechnung
- [Die E-Mail-Fassung](email.md) — wenn dieselbe Rechnung als `.eml` statt als PDF hinausgeht
