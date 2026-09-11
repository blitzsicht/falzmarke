# 0039 — falzmarke rechnet nicht

**Datum:** 11.09.2026 · **Status:** angenommen ·
**Löst:** [#112](https://github.com/blitzsicht/falzmarke/issues/112) ·
**Gehört zu:** [#111](https://github.com/blitzsicht/falzmarke/issues/111)

## Worum es geht

Eine Rechnung aus Markdown zu setzen ist nicht dasselbe wie einen Brief zu setzen. Ein Brief ist
Fließtext; eine Rechnung hat Positionen, Steuersätze und Beträge, die zueinander passen müssen.
Ein Datenvertrag dafür ist kein weiterer Emitter, sondern ein **zweiter Datenvertrag** neben dem
Frontmatter — und er verschiebt, was falzmarke ist.

Die Erhebung aus [#113](https://github.com/blitzsicht/falzmarke/issues/113) liegt seit dem
11.09.2026 in [`docs/recht.md`](../recht.md) und macht drei der vier Fragen dieses Vorgangs
entscheidbar. Der entscheidende Satz daraus: **Ein PDF ohne strukturierte Daten ist keine
elektronische Rechnung im Sinne des § 14 Absatz 1 UStG, sondern eine sonstige Rechnung.** Das ist,
was falzmarke heute erzeugt.

## Entscheidung 1: Das Werkzeug rechnet nicht

falzmarke **überträgt**, was ihm gegeben wurde, und sagt das ausdrücklich. Es summiert keine
Positionen, bildet keine Steuerbeträge und prüft nicht, ob Netto plus Steuer den Bruttobetrag
ergibt.

**Begründung.** Wer rechnet, haftet für das Ergebnis. Wer überträgt, haftet dafür nicht — muss
dann aber sagen, dass er nicht rechnet, und zwar dort, wo jemand es liest: in der Dokumentation
und im Datenvertrag, nicht nur in einem ADR.

Das ist dieselbe Linie wie bei „keine Zertifizierung" (ADR 0032), „kein Versand" (ADR 0034) und
„falzmarke prüft die Pflichtangaben nicht" (ADR 0005): Das Werkzeug behauptet nur, was es belegen
kann.

**Was daraus folgt, und es ist unbequem:** Eine Rechnung mit widersprüchlichen Summen geht
durch. falzmarke darf das **melden** — eine Prüfung „Netto plus Steuer ergibt Brutto" ist eine
Rechenprobe über gegebene Werte und kein Bilden eigener — aber sie hält den Lauf nicht an, und
sie ersetzt keine Buchhaltung. Welche Stufe diese Meldung trägt, entscheidet der Regelkatalog
nach ADR 0035; eine Prüfung auf der Ebene `werkzeug` darf Fehler sein.

## Entscheidung 2: ZUGFeRD in einer festen Fassung, nicht „dem aktuellen Stand"

**Vorgabe ist ZUGFeRD 2.x, Fassung ausdrücklich benannt.** Gemessen am 11.09.2026 ist
[2.5.2 die aktuelle Fassung](https://www.ferd-net.de/standards/zugferd) (veröffentlicht
04.08.2026).

**Begründung.** Jede Fassung schreibt einen Dateinamen für die eingebettete XML, ein
XMP-Erweiterungsschema und eine Beziehungsangabe im PDF vor. Wer „die jeweils aktuelle" erzeugt,
erzeugt Dokumente, deren Empfängerkreis niemand kennt — und eine Fassung, die sich zur Laufzeit
ändert, ist kein Datenvertrag.

**Wie sie fortgeschrieben wird:** als eigener Vorgang mit Gegenprobe gegen einen fremden
Validator, nie nebenbei. Die Fassungsnummer gehört in den Messbericht jedes erzeugten Dokuments,
damit im Nachhinein belegbar ist, gegen welche Spezifikation gesetzt wurde.

## Entscheidung 3: Profil EN 16931, nicht MINIMUM und nicht EXTENDED

Die Profilstruktur, belegt über die [FeRD-FAQ](https://www.ferd-net.de/standards/zugferd-faq)
(gemessen 11.09.2026):

| Profil | Was es enthält | Taugt als Rechnung |
|---|---|---|
| MINIMUM | Stamm- und Summendaten, **keine Positionen** | nein — Buchungshilfe |
| BASIC WL | ebenfalls **keine Rechnungspositionen** | nein — Buchungshilfe |
| BASIC | Teilmenge der EN 16931-1, einfache steuerkonforme Rechnungen | ja |
| **EN 16931 (COMFORT)** | setzt EN 16931-1 vollständig um | **ja — Vorgabe** |
| EXTENDED | Erweiterung über die Norm hinaus, komplexere Geschäftsprozesse | ja |
| XRECHNUNG | Referenzprofil für öffentliche Auftraggeber | ja, siehe #117 |

**Vorgabe ist EN 16931 (COMFORT).** Begründung: Das ist genau der Umfang, den § 14 Absatz 1
Satz 6 UStG verlangt — Entsprechung zur „europäischen Norm für die elektronische
Rechnungsstellung … gemäß der Richtlinie
[2014/55/EU](https://eur-lex.europa.eu/eli/dir/2014/55/oj)". Nicht weniger, und nicht mehr.

**MINIMUM und BASIC WL erzeugt falzmarke nicht.** Sie enthalten keine Rechnungspositionen und
sind keine Rechnung im umsatzsteuerlichen Sinn. Ein Werkzeug, das „Rechnung" in den Dateinamen
schreibt und eine Buchungshilfe erzeugt, behauptet zu viel — und der Unterschied fällt dem
Absender erst auf, wenn ihn jemand darauf anspricht.

**EXTENDED ist nicht die Vorgabe.** Es beschreibt Geschäftsprozesse, die falzmarke nicht kennt.
Ob es als Wahlmöglichkeit dazukommt, entscheidet der Bedarf und nicht die Vollständigkeit der
Liste.

**XRECHNUNG** ist der Weg an öffentliche Auftraggeber und hat mit der Leitweg-ID eine eigene
Pflichtangabe. Das ist ein eigener Vorgang ([#117](https://github.com/blitzsicht/falzmarke/issues/117))
und hier nur eingehängt.

## Was das Werkzeug nicht wird

Keine Rechnungsnummernvergabe, keine Buchführung, kein Mahnwesen, kein Versand. Der Versand ist
in ADR 0034 entschieden, und die Begründung trägt hier genauso: Wer versendet, braucht
Zugangsdaten, einen Ausgang und eine Fehlerbehandlung für Dinge, die niemand gelesen hat.

Keine Fristenprüfung. Ob ein Umsatz unter die Ausstellungspflicht fällt, entscheidet sich an
Tatsachen, die das Werkzeug nicht kennt — Sitz beider Beteiligten, Unternehmereigenschaft,
Vorjahresumsatz, Steuerbefreiung. `docs/recht.md` nennt die Fristen; das Werkzeug prüft sie nicht.

## Was ohne fremde Prüfung nicht behauptet wird

Solange kein unabhängiges Prüfwerkzeug das Ergebnis durchlässt, sagt falzmarke **nicht**
„ZUGFeRD-konform". Dieselbe Zurückhaltung wie beim Wort „normgerecht", aus demselben Grund: Eine
Zusage, die das Werkzeug über sich selbst macht, ist keine.

Die fremde Prüfung ist [#118](https://github.com/blitzsicht/falzmarke/issues/118) und gehört in
die CI, nicht in einen Einzellauf. Bis sie läuft, trägt jedes erzeugte Dokument denselben
Vorbehalt wie jeder Brief heute.

## Was diese Entscheidung nicht ist

Sie sagt **nicht**, dass der Datenvertrag so aussieht, wie ihn
[#115](https://github.com/blitzsicht/falzmarke/issues/115) vorschlägt — nur, dass es einen gibt
und dass er keine Rechenvorschrift enthält.

Sie sagt **nicht**, was aus EN 16931 im Einzelnen gilt. Der Normtext ist kostenpflichtig, und es
gilt dieselbe Regel wie für die DIN 5008: Weder Wortlaut noch Tabellen gehören ins Repository.
Übertragen werden Fundstellen und Feldnamen.

Und sie ist keine steuerliche Beratung. Welche Rechnungen ein Unternehmen ausstellen muss,
entscheidet nicht ein Werkzeug, das den Umsatz nicht kennt.
