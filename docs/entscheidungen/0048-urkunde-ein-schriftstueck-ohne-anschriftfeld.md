# 0048 — Die Urkunde: ein Schriftstück ohne Anschriftfeld ist ein eigener Typ

**Datum:** 07.10.2026 · **Status:** angenommen · **Betrifft:** [#381](https://github.com/blitzsicht/falzmarke/issues/381) · **Ergänzt:** [0029](0029-falzmarke-ist-werkzeug-kein-kanal.md), [0030](0030-reihenfolge-der-roadmap.md)

## Worum es geht

Eine Vereinbarung zwischen zwei Parteien, eine einseitige Erklärung, ein Nachweis: Schriftstücke,
die an niemanden adressiert sind, einen Titel statt eines Betreffs tragen und von Hand
unterschrieben werden. falzmarke konnte sie nicht setzen. Ein Brief verlangt einen Empfänger, und
das Anschriftfeld lässt sich nicht weglassen. Wer so ein Papier brauchte, wich auf ein anderes
Werkzeug aus — ohne Raster, ohne Messung, ohne dass jemand den Seitenumbruch geprüft hätte.

## Entscheidung 1: ein eigener Typ, kein Brief mit Schalter

`typ: urkunde` tritt neben `brief`, `email` und `rechnung`. Die Urkunde hat einen eigenen
Datenvertrag, eine eigene Seitenfunktion und eine eigene Prüfliste.

Der naheliegende andere Weg wäre ein Brief gewesen, dessen Anschriftfeld sich abschalten lässt.
Er scheitert an [ADR 0047](0047-geometrie-regeln-tragen-ihre-stufe.md): Die Maße des Briefes
sind Maße. Ein Brief ohne Anschrift, ohne Rücksendeangabe oder ohne Falzmarken ist rot, ohne
Wenn. Ein Schalter machte aus jeder dieser Prüfungen eine bedingte — und aus der Zusage „hält
alle Briefmaße" die Zusage „hält die Briefmaße, die gerade gelten".

Dazu kommt der Satz selbst: Die Seitenfunktion des Briefes reserviert das Anschriftfeld immer.
Ein Blatt ohne braucht eine eigene.

**Das stärkste Gegenargument** ist der Aufwand. Die Rechnung blieb ein Brief, weil sie
geometrisch einer ist; ein vierter Typ mit eigener Prüfliste ist Pflegefläche. Gemessen kommt
der Fall selten vor — eine Handvoll Schriftstücke im Jahr gegen Dutzende Briefe im Monat. Er
wird trotzdem gebaut, weil die Alternative kein unterlassenes Feature ist, sondern ein Umweg um
das Werkzeug: Der Skill verbietet frei gesetzte PDF, und für diese Papiere gab es nichts anderes.
Klein gehalten wird die Fläche dadurch, dass die Urkunde mit dem Brief teilt, was sich teilen
lässt: Schrift, Zeilenraster, Überschriften, Briefkopf, Fußzeile, Ränder und die Funktionen, die
sie messen.

## Entscheidung 2: Der Name beschreibt die Form, nicht die Wirkung

Der Typ heißt `urkunde`. Zur Wahl standen auch `vertrag` und `vereinbarung`; beide sind für eine
einseitige Erklärung falsch. `schriftstueck` und `dokument` wären für alles richtig und sagten
deshalb nichts — „Schreiben" ist in diesem Repository der Oberbegriff über alle Typen.

`urkunde` meint hier genau das: ein unterschriebenes Schriftstück, das für sich steht. **Über
Beweiskraft, Schriftform oder Wirksamkeit sagt der Name nichts**, und das Werkzeug auch nicht.
Die Unterschriftslinie ist Erscheinungsbild und kein Nachweis; ob ein Papier eine Form wahrt,
entscheidet nicht falzmarke ([`docs/recht.md`](../recht.md), „Keine Rechtssicherheit"). Wer
`typ: vertrag` oder `typ: vereinbarung` schreibt, erfährt vom Linter, wie der Typ heißt.

## Entscheidung 3: Jede Regel ist eine Setzung des Werkzeugs

Die DIN 5008 beschreibt den Geschäftsbrief. Zu einem Blatt ohne Anschriftfeld, zu
Unterschriftslinien, zu einer Zeile für Ort und Datum und zu einer Obergrenze für die Seitenzahl
sagt keine der geführten Quellen etwas. Alle Regeln der Urkunde tragen deshalb
`herkunft: werkzeug` und `ebene: werkzeug` ([`regeln/urkunde.yaml`](../../skill/falzmarke/regeln/urkunde.yaml)).

Zwei Sätze der geführten Quellen klingen verwandt: der Unterschriftsraum von drei Leerzeilen und
die Seitenzählung auf Folgeseiten. Beide stehen dort für den Brief. Die Urkunde übernimmt die
Werte, damit zwei Blätter desselben Absenders gleich aussehen — nicht, weil eine Quelle sie für
dieses Blatt verlangte. [ADR 0044](0044-woertlicher-beleg-schlaegt-werkzeugeinstufung.md) ist
davon nicht berührt: Dort geht es um Regeln, die eine Quelle wörtlich trägt.

Daraus folgt für jede Ausgabe: Schlägt die Messung einer Urkunde fehl, heißt es nicht „hält die
Maße aus DIN 5008 nicht ein". Die Norm hat dazu nichts gesagt. Und die Zahl der Maße, mit der
das Werkzeug für den Brief wirbt, gilt für die Urkunde nicht.

Dass eine Werkzeugregel ein Fehler sein darf, ist seit dem Nachtrag zu
[ADR 0035](0035-vier-ebenen-fuer-email-regeln.md) entschieden. Die Regeln der Messung heißen
`geometrie.urkunde_*`, damit der Wächter aus ADR 0047 sie sieht.

## Entscheidung 4: kein eigener Befehl

[ADR 0040](0040-xrechnung-3-0-in-cii.md) hält fest, dass jedes eigene Erzeugnis einen eigenen
Befehl hat. Die Urkunde ist kein eigenes Erzeugnis in diesem Sinn: Sie ist ein PDF wie der
Brief, mit Vorschau, PDF/A und PDF/UA, und der Messbericht hat dieselbe Gestalt. `render` und
`verify` tragen sie.

`verify` bekommt nur die fertige Datei. Dass sie eine Urkunde ist, steht deshalb als Vermerk im
PDF, dazu die Kopfhöhe, die Zahl der Unterschriften und — wenn gesetzt — die erlaubte
Seitenzahl. **Der Vermerk ist eine Behauptung der Datei, kein Befund.** Zwei Vorkehrungen
verhindern, dass er das letzte Wort hat: Die Urkundenliste prüft, dass keine Falz- und
Lochmarken im Heftrand stehen, sodass ein Brief, der sich als Urkunde ausgibt, auffällt. Und
`verify --form` erzwingt die Briefliste.

Briefe bekommen keinen neuen Vermerk. Jeder zusätzliche Schlüssel hätte die Bytes aller
bestehenden Briefe geändert.

## Entscheidung 5: Dialekt 1.2

Zwei Elemente kommen in den Text, additiv wie Dialekt 1.1 und für alle Typen:

- **Ausfüllfeld.** Eine frei stehende Kette aus mindestens drei Unterstrichen wird zu einer
  leeren Linie, 2 mm je Unterstrich. In 1.0 und 1.1 bleibt sie wörtlicher Text.
- **Angabentabelle.** Eine Tabelle mit leerer Kopfzeile und zwei Spalten wird ohne Kopf und ohne
  Rahmen gesetzt. In 1.0 und 1.1 bleibt die leere Kopfzeile, was sie war, und der Linter weist
  darauf hin.

**Eine geschützte Kette ist ab 1.2 ebenfalls ein Feld.** `\_\_\_` und `___` sind nach dem Parsen
nicht zu unterscheiden. Die Dokumentation des Dialekts nennt `\_` „das Zeichen selbst, ohne
Bedeutung"; für eine Kette ab drei Zeichen gilt das in 1.2 nicht mehr. Wer Unterstriche als
Zeichen braucht, setzt sie in einen wortgetreuen Auszug.

CommonMark liest Unterstriche als Auszeichnung, sobald sie an einem Buchstaben oder Satzzeichen
lehnen: Aus `____,__` wird ein fettes Komma. Der Leser zählt deshalb nach — Ketten im Rohtext
gegen Felder im Baum — und bricht bei einer Differenz ab, statt Fettdruck zu setzen, der wie
gewollt aussieht.

Nichts wird automatisch nummeriert; das bleibt die Zusage aus 1.1. Die Nummer eines Abschnitts
schreibt der Verfasser.

## Entscheidung 6: Die Kopfhöhe folgt dem Briefkopf

Beim Brief folgt die Kopfhöhe der Form und die Form dem Fenster des Umschlags. Die Urkunde hat
kein Fenster. Ihr Kopf ist 27 mm hoch, wenn der Briefkopf des Profils hineinpasst, sonst 45 mm.
Das sind dieselben zwei Höhen; gewählt wird nach dem, was im Kopf steht.

Der Grund ist die Seite: 45 mm über einem flachen Logo sind 18 mm, die dem Text fehlen, und ein
Schriftstück, das unterschrieben wird, soll möglichst auf einem Blatt stehen. Das Raster, die
Schriftgröße und die Ränder bleiben, wie sie beim Brief sind — an ihnen wird für die Seite nicht
gespart.

## Einordnung in die Roadmap

[ADR 0030](0030-reihenfolge-der-roadmap.md) verlangt, einen neuen Vorschlag gegen die
Reihenfolge zu prüfen, bevor er ein Issue wird. Die Urkunde gehört zur Phase **Lange und
professionelle Schreiben**: Sie braucht deren Überschriften und Tabellen und erweitert deren
Dialekt. Geparkt wird sie nicht, weil sie keine Frage beantwortet, die niemand gestellt hat —
der Anlass waren Schriftstücke, die gesetzt werden mussten.

[ADR 0029](0029-falzmarke-ist-werkzeug-kein-kanal.md) nennt falzmarke „ein Werkzeug, das Briefe
setzt und prüft". Der Satz wird hiermit weiter: Es setzt und prüft Schriftstücke eines
Absenders — Briefe, deren Fassung als E-Mail, Rechnungen und Urkunden. Was er ausschließt,
bleibt ausgeschlossen: Das Werkzeug versendet nichts.

## Was diese Entscheidung nicht ist

- **Kein Vertragswerkzeug.** falzmarke kennt keine Klauseln und keine Muster. Die festen Wörter
  des Werkzeugs sind „zwischen", „und" und „Ort, Datum"; der Zusatz einer Partei wird wörtlich
  gesetzt, wie er geschrieben ist.
- **Keine Aussage über Form oder Wirksamkeit.** Siehe Entscheidung 2.
- **Keine digitale Signatur.** Das bleibt [#14](https://github.com/blitzsicht/falzmarke/issues/14)
  (Digitale Signatur des PDF, PAdES) und ist geparkt.
- **Keine E-Mail-Fassung, kein Serienlauf.** `email`, `serie` und `xml` brechen bei einer
  Urkunde mit einer Meldung ab. `einlesen` kennt den Typ nicht: Es liest eine Urkunde wie jedes
  Blatt ohne Briefraster und lässt offen, was es nicht zuordnen kann.
- **Keine Formularfelder im PDF.** Ein Ausfüllfeld ist eine Linie für einen Stift, kein Feld,
  das ein Programm ausfüllt.
- **Höchstens zwei Parteien und zwei Unterschriften**, nebeneinander. Für eine dritte gibt es
  keinen Satz.
- **Kein Signaturbild.** Eine Urkunde wird von Hand unterschrieben.
- **Keine Zeilenköpfe in der Angabentabelle.** Die Satzmaschine kennt in der eingesetzten Fassung
  keine Kopfzelle je Zeile; im PDF stehen die Bezeichnungen als gewöhnliche Zellen.

## Nachtrag 07.10.2026: der Kopf nach dem DIN-Vertrag

Am ersten gesetzten Schriftstück zeigte sich: Ein Titel in 11 pt fett ist von den
Abschnittsüberschriften nicht zu unterscheiden, die genauso stehen. Der Kopf folgt seither dem
Vertrag zwischen Bund und DIN von 1975, wie er als Abdruck auf din.de steht: Titel in 16 pt ohne
Fett, Parteien in 12 pt, darunter eine Linie über die Satzbreite. Das Dokument ist ein Vorbild
für die Gestaltung, nicht die Quelle einer Regel. Die Maße bleiben Setzungen (Entscheidung 3).

Dazu zwei Schalter: `blocksatz` (Gestaltung, kein Schutz gegen Einfügungen) und `paraphen`
(Felder für Initialen auf jeder Seite außer der letzten). Nicht übernommen wurden aus
verbreiteten Layoutempfehlungen für Verträge eine Pflicht zu serifenloser Schrift und 1,15- oder
1,5-zeiliger Satz: Das eine regelt das Profil, das andere bräche das Raster.

**Zum Wort.** „Urkunde“ meint im Alltag auch die Ehren- oder Teilnahmeurkunde, auf Karton und
oft in A3. Die ist hier nicht gemeint und wird nicht gebaut.

