# Was falzmarke behauptet — und was nicht

Diese Seite sagt, worauf die Regeln des Werkzeugs beruhen und wie belastbar das ist. Sie ist keine
Rechtsberatung.

## Der Satz, auf den es ankommt

> Maße und Schreibregeln folgen öffentlich dokumentierten Quellen (Liste in
> [`skill/references/din5008.md`](../skill/references/din5008.md)); der Abgleich mit dem
> Originaltext der DIN 5008:2020-03 einschließlich Berichtigung 1:2020-07 steht aus. Regeln aus einzelnen Quellen wirken nur als
> Warnung.

Er steht so auch in der [README](../README.md) und wird von einem Test bewacht
(`tests/test_textkanon.py`), damit er bei der nächsten Überarbeitung nicht verschwindet.

## Warum der Normtext nicht im Repository liegt

Der Text der DIN 5008:2020-03 ist urheberrechtlich geschützt und kostenpflichtig. Er wird hier
weder wiedergegeben noch mitgeliefert, weder als Zitat noch als Tabelle noch als Abbildung. Was
das Werkzeug kennt, hat es aus Sekundärquellen — aus Maßzeichnungen, Fachartikeln und zwei
unabhängigen Implementierungen.

Das ist keine Nachlässigkeit, sondern die Bedingung, unter der ein quelloffenes Werkzeug zu
diesem Gegenstand überhaupt möglich ist. Es hat aber eine Folge, die man aussprechen muss: **Wir
wissen nicht mit letzter Sicherheit, ob jede Regel dem Normtext entspricht.**

## Was daraus folgt

| Herkunft einer Regel | Wirkung im Werkzeug |
|---|---|
| mehrfach bestätigt — mindestens zwei Quellen, die zur Bestätigung zählen | darf einen Lauf scheitern lassen (Fehler) |
| einzeln belegt — eine Quelle, die die Regel trägt | Warnung mit Quellenangabe, der Lauf geht weiter |
| offen — Annahme ohne Beleg | wird nicht geprüft |
| Werkzeugprüfung — keine Aussage der Norm | Fehler oder Warnung, je nach Sache |

**Nicht jede genannte Quelle zählt zur Bestätigung.** Zwei zählen bewusst nicht:

- **Die eigene Messung am gerenderten PDF.** Sie belegt, dass das Werkzeug einhält, was es sich
  vornimmt — nicht, dass das Vorgenommene der Norm entspricht.
- **`typst-letter-pro`.** Die Layoutbasis ist unter `skill/falzmarke/typst/vendor/` eingebettet;
  falzmarke *setzt* damit. Ein Sollwert von dort würde gegen ein PDF geprüft, das dieselbe Quelle
  erzeugt hat — die Prüfung könnte nicht rot werden. Als Hinweis darauf, wie jemand anders die
  Norm gelesen hat, bleibt der Eintrag wertvoll; eine Regel auf „mehrfach bestätigt" hebt er nie.

Bis v0.5.0 stand diese Zählung nur in einem Kommentar und wurde von Hand gesetzt. Am 25.08.2026
nachgezählt: **alle vierzehn** als mehrfach bestätigt geführten Regeln verfehlten die damals
dokumentierte Definition. Seitdem prüft `skill/falzmarke/regeln/__init__.py` sie nach — eine
Regel, die ihre Stufe nicht trägt, lässt die Regeldatei abbrechen, und
[Gegenproben](../tests/test_quellenlage.py) halten das fest.

Die vollständige Zuordnung steht in der
[Quellenlage je Regel](../skill/references/din5008.md#quellenlage-je-regel), gepflegt in
[`skill/falzmarke/regeln/din5008.yaml`](../skill/falzmarke/regeln/din5008.yaml).

Der Typografie-Pass hält sich an dieselbe Grenze: Er ändert Text nur, wo die Regel mehrfach
belegt ist. Was er sonst geändert hätte, kann er als Vorschlag ausgeben, ohne den Brief
anzufassen. Eine stille Ersetzung auf dünner Grundlage wäre der schlechteste Fall — der Brief
sähe anders aus, als er geschrieben wurde, und niemand erführe warum.

## Was die Stufen derzeit wert sind

Die Tabelle oben sagt, was eine Stufe **bedeutet**. Am 27.08.2026 wurde nachgezählt, was die
Regeln tatsächlich tragen — und das Ergebnis gehört hierher, weil die Stufen unverändert
geblieben sind.

Von 23 Regeln mit Wirkung *Fehler* sind zehn Werkzeugprüfungen ohne Normbezug. Von den
**dreizehn normbezogenen** trägt **keine einzige nachweislich zwei unabhängige Belege**:

| | |
|---|---|
| 9 | stützen sich auf zwei Quellen, die **dieselbe Zeichnung** sind ([Befund](quellenunabhaengigkeit-2026-08-27.md)) |
| 2 | die zweite Quelle **sagt zur Regel nichts** ([Befund](quellenpruefung-onlineprinters-2026-08-27.md)); es bleibt eine |
| 2 | zwei Quellen desselben Trägers, Unabhängigkeit **ungeprüft** |

Dazu sechs Warnungen, deren einzige Quelle zu ihnen schweigt.

**Nach dem eigenen Maßstab müssten die betroffenen Regeln herabgestuft werden** — von Fehler auf
Warnung, teils auf „offen". Das ist bewusst **nicht** geschehen: Der Normabgleich
([unten](#wie-sich-das-ändert)) ersetzt ohnehin jede Herkunftsstufe durch eine Fundstelle und
macht die Frage gegenstandslos. Bis dahin bleiben diese Regeln strenger, als ihr Beleg trägt.

Das ist eine Entscheidung, keine Nachlässigkeit — und sie steht hier, damit niemand die Tabelle
oben für eine Zusage hält, die sie im Einzelfall nicht einlöst. Die Sollwerte selbst sind davon
unberührt: Sie sind an gerenderten PDFs gemessen und stimmen mit den Zeichnungen überein. Zur
Debatte steht nicht, ob sie richtig sind, sondern wie stark sie belegt sind.

## Pflichtangaben in E-Mails

Die DIN 5008 sagt nichts darüber, was in einem Geschäftsbrief stehen **muss** — das steht im
Handelsrecht, und es gilt für E-Mails genauso wie für Papier. Seit dem [EHUG](https://www.buzer.de/gesetz/7443/index.htm) (Gesetz über
elektronische Handelsregister und Genossenschaftsregister sowie das Unternehmensregister, in
Kraft am 1. Januar 2007) sind die Vorschriften über Geschäftsbriefe ausdrücklich auf
Geschäftsbriefe „gleichviel welcher Form" gefasst; eine geschäftliche E-Mail ist damit erfasst.

Wo das steht, hängt an der Rechtsform: [§ 37a HGB](https://www.gesetze-im-internet.de/hgb/__37a.html) (eingetragener
Kaufmann), [§ 125 HGB](https://www.gesetze-im-internet.de/hgb/__125.html) (OHG und KG), [§ 35a GmbHG](https://www.gesetze-im-internet.de/gmbhg/__35a.html),
[§ 80 AktG](https://www.gesetze-im-internet.de/aktg/__80.html), [§ 25a GenG](https://www.gesetze-im-internet.de/geng/__25a.html). Verlangt werden dort — je nach Form — Rechtsform und
Sitz, das Registergericht, die Registernummer und die Namen der Geschäftsführer, Vorstands- oder
Aufsichtsratsmitglieder.

Für Personengesellschaften stand das bis Ende 2023 in § 125a HGB — **ohne Verweis, denn die
Vorschrift gibt es nicht mehr**; die amtliche Sammlung führt nur geltendes Recht. Das
[MoPeG](https://www.buzer.de/51_MoPeG.htm) hat die Vorschrift zum 1. Januar 2024
aufgehoben und den Inhalt nach § 125 HGB überführt.

**falzmarke prüft das nicht.** Welche Angaben eine Rechtsform braucht, entscheidet nicht ein
Werkzeug, das den Text nicht kennt (ADR 0005). Der Linter meldet nur, ob im Profil überhaupt
`email.pflichtangaben:` gesetzt ist — als Erinnerung, als Warnung, ohne den Lauf anzuhalten und
ohne den Inhalt zu bewerten. Was dort steht, verantwortet der Absender.

Das ist keine Rechtsberatung. Wer wissen will, was seine Rechtsform verlangt, fragt jemanden,
der dafür haftet.

## E-Rechnung: was das Umsatzsteuerrecht verlangt

Erhoben am 11.09.2026 aus dem Volltext des UStG und der UStDV (Fassung `ustg_1980` /
`ustdv_1980`, amtliche Quelle gesetze-im-internet.de). Die Fundstellen stehen dabei, weil eine
Frist aus dem Gedächtnis genauso altert wie eine Vorschrift — § 125a HGB stand in dieser Datei
noch, als es ihn nicht mehr gab.

**Keine amtliche Fassung**; verbindlich ist das Bundesgesetzblatt. Und **keine Rechtsberatung**:
Was hier steht, ist der Wortlaut der Norm und seine Fundstelle, nicht seine Anwendung auf einen
Fall.

### Was als elektronische Rechnung gilt

[§ 14 Absatz 1 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html) unterscheidet drei
Dinge, und der Unterschied ist für ein Werkzeug wie dieses der entscheidende:

| Begriff | Was die Norm sagt |
|---|---|
| **Rechnung** | „jedes Dokument, mit dem über eine Lieferung oder sonstige Leistung abgerechnet wird, gleichgültig, wie dieses Dokument im Geschäftsverkehr bezeichnet wird" |
| **elektronische Rechnung** | „in einem **strukturierten elektronischen Format** ausgestellt, übermittelt und empfangen" und „eine elektronische Verarbeitung ermöglicht" |
| **sonstige Rechnung** | „in einem anderen elektronischen Format oder auf Papier übermittelt" |

**Ein PDF ohne strukturierte Daten ist damit keine elektronische Rechnung, sondern eine sonstige.**
Das ist die Antwort auf die Frage, die #113 gestellt hat — und sie entscheidet, was falzmarke
heute erzeugt: sonstige Rechnungen.

Welches Format als strukturiert gilt, sagt § 14 Absatz 1 Satz 6: Es muss „der europäischen Norm
für die elektronische Rechnungsstellung und der Liste der entsprechenden Syntaxen gemäß der
Richtlinie 2014/55/EU" entsprechen — oder zwischen Aussteller und Empfänger vereinbart sein,
sofern sich die erforderlichen Angaben verlustfrei in ein solches Format überführen lassen.

### Ausstellen: Pflicht, und ab wann

Die Pflicht steht in [§ 14 Absatz 2 Satz 2 Nummer 1 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html):
Für eine Leistung an einen anderen Unternehmer für dessen Unternehmen ist die Rechnung „als
elektronische Rechnung nach Absatz 1 Satz 3 und 6 auszustellen, wenn der leistende Unternehmer
und der Leistungsempfänger im Inland … ansässig sind". Frist: innerhalb von sechs Monaten nach
Ausführung der Leistung.

Die Übergangsregelung steht in [§ 27 Absatz 38 UStG](https://www.gesetze-im-internet.de/ustg_1980/__27.html)
und ist gestaffelt:

| Umsatz ausgeführt | Papier oder unstrukturiertes Format noch erlaubt bis | Bedingung |
|---|---|---|
| 01.01.2025 – 31.12.2026 | **31.12.2026** | keine — gilt für alle |
| 01.01.2027 – 31.12.2027 | **31.12.2027** | Gesamtumsatz des Ausstellers im Vorjahr **höchstens 800 000 €** (§ 19 Absatz 2) |
| 01.01.2027 – 31.12.2027 | **31.12.2027** | oder Übermittlung per EDI nach Empfehlung 94/820/EG |

Beides braucht „vorbehaltlich der Zustimmung des Empfängers", wo es um ein elektronisches Format
geht. Ab dem 01.01.2028 nennt die Vorschrift keine Ausnahme mehr.

### Empfangen: es gibt keine eigene Pflicht — und genau das ist der Punkt

Eine Norm „Unternehmen müssen E-Rechnungen empfangen können" existiert nicht. Die Wirkung
entsteht durch einen **Wegfall**: § 14 Absatz 1 Satz 5 verlangt die Zustimmung des Empfängers
für die Übermittlung „soweit keine Verpflichtung nach Absatz 2 Satz 2 Nummer 1 besteht".

Wo die Ausstellungspflicht greift — inländisches B2B —, entfällt das Zustimmungserfordernis
also. Der Empfänger kann eine elektronische Rechnung nicht mehr ablehnen, und das wirkt wie eine
Empfangspflicht, ohne als solche formuliert zu sein. Diese Lesart ergibt sich aus dem Wortlaut;
ob und wie die Verwaltung sie auslegt, steht hier nicht.

### Welche Pflichtangaben unberührt weitergelten

[§ 14 Absatz 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html) zählt zehn Angaben
auf — Name und Anschrift beider Seiten, Steuernummer oder USt-IdNr., Ausstellungsdatum,
fortlaufende Rechnungsnummer, Menge und Art, Leistungszeitpunkt, nach Steuersätzen
aufgeschlüsseltes Entgelt, Steuersatz und Steuerbetrag, gegebenenfalls Hinweis auf die
Aufbewahrungspflicht und bei Gutschriften die Angabe „Gutschrift". Das Format ändert daran
nichts.

### Die Ausnahmen, die ein PDF erlauben

Drei Fälle dürfen **immer** als sonstige Rechnung übermittelt werden, auch im inländischen B2B:

| Fall | Fundstelle | Grenze |
|---|---|---|
| Kleinbetragsrechnung | [§ 33 UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__33.html) | Gesamtbetrag höchstens **250 €**; verkürzter Pflichtangabensatz |
| Fahrausweis | [§ 34 UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__34.html) | Personenbeförderung |
| Rechnung eines Kleinunternehmers | [§ 34a UStDV](https://www.gesetze-im-internet.de/ustdv_1980/__34a.html) | Umsätze nach [§ 19 Absatz 1 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html) steuerfrei |

Jede dieser drei Vorschriften endet mit demselben Satz: „kann abweichend von § 14 Absatz 2
Satz 2 des Gesetzes **immer** als sonstige Rechnung … übermittelt werden."

### Was das für falzmarke bedeutet

Beschreibend, nicht bewertend:

- **Was das Werkzeug heute erzeugt, sind sonstige Rechnungen.** Ein PDF/A ohne eingebettete
  strukturierte Daten erfüllt § 14 Absatz 1 Satz 3 nicht.
- **Für die drei Ausnahmefälle reicht das dauerhaft** — nicht als Übergang, sondern nach dem
  Wortlaut der UStDV.
- **Für inländisches B2B oberhalb der Ausnahmen läuft die Zeit:** bis Ende 2026 allgemein, für
  kleinere Aussteller bis Ende 2027.
- **falzmarke prüft keine dieser Fristen** und wird es nicht tun. Ob ein Umsatz unter die
  Ausstellungspflicht fällt, entscheidet sich an Tatsachen, die das Werkzeug nicht kennt — Sitz
  beider Beteiligten, Unternehmereigenschaft, Vorjahresumsatz, Steuerbefreiung. Dasselbe
  Argument wie bei den Pflichtangaben (ADR 0005).

Was daraus für das Datenmodell folgt, ist nicht hier entschieden, sondern in den Vorgängen #111
und #112.

## Was ausdrücklich nicht behauptet wird

- **Keine Zertifizierung.** falzmarke ist kein Produkt des DIN, steht in keiner Verbindung zum
  DIN und ist von niemandem geprüft worden.
- **Kein „normgerecht", kein „DIN-konform"** ohne den Satz oben. „nach DIN 5008" bleibt als
  beschreibende Nennung dessen, woran sich das Werkzeug orientiert.
- **Keine Rechtssicherheit.** Ob ein Brief formwirksam ist, entscheidet nicht die DIN 5008.

## Wie sich das ändert

Durch den Abgleich mit dem gekauften Normtext — siehe
[`docs/normabgleich-pruefliste.md`](normabgleich-pruefliste.md) und das zugehörige Issue. Danach
tritt an die Stelle jeder Herkunftsangabe eine Fundstelle („DIN 5008:2020-03, Abschnitt …"), die
Quellenliste entfällt, und der Satz oben verschwindet aus README und dieser Seite.

Bis dahin gilt er.
