# Mitmachen

Danke für dein Interesse. Dieses Projekt hat eine ungewöhnliche Eigenschaft, die alles andere
bestimmt: **Es misst sein eigenes Ergebnis.** Was hier geändert wird, muss deshalb messbar
bleiben.

*English: contributions are welcome. This file is in German because the tool, its code comments
and its error messages are — DIN 5008 is a German standard and the letters it produces are German
business correspondence. If German is a barrier, open an issue in English and say so; we will
find a way. The one rule that matters most: a check that can never turn red is not evidence.*

## Der Grundsatz

Ein Prüfmittel, das nie rot werden kann, ist kein Nachweis.

Wer eine Prüfung hinzufügt, fügt auch die Gegenprobe hinzu: In
[`tests/test_gegenbeweis.py`](tests/test_gegenbeweis.py) wird das Layout an genau einer Stelle
absichtlich verschoben, und die neue Prüfung muss dort anschlagen. Dazu gehört die Kontrollprobe
ohne Sabotage, die grün bleiben muss — ohne sie belegt der Test nur, dass eine Kopie anders misst
als das Original.

Dasselbe gilt für Fehlerbehebungen: **Erst den Fehler reproduzieren, dann beheben.** Wenn er sich
nicht reproduzieren lässt, ist unklar, was der Fix behebt.

## Beweispflicht

An einen Pull Request gehört, was du gemessen hast — nicht, was du erwartest:

- die Ausgabe von `pytest`, nicht die Behauptung, sie sei grün;
- bei Layoutänderungen die neu erzeugten Bilder aus `docs/renders/`;
- bei einer neuen Prüfung die Gegenprobe und ihr Ergebnis am sabotierten Stand;
- bei einem behobenen Fehler die Reproduktion von vorher.

Die PR-Vorlage fragt genau danach.

## Bevor du einen Pull Request öffnest

```bash
python3 skill/scripts/bootstrap.py
python3 -m pytest -q
for f in examples/*.md; do
  python3 skill/scripts/falzmarke.py render "$f" -o "/tmp/$(basename "$f" .md).pdf"
done
```

Alle Tests grün, alle acht Beispiele ohne `FEHL`-Zeile.

## Herkunft der Beiträge (DCO)

Beiträge laufen über das
[Developer Certificate of Origin](https://developercertificate.org/): Bestätige mit einer
Signaturzeile, dass du das Eingereichte einbringen darfst.

```bash
git commit -s -m "fix(lint): …"
```

Das setzt `Signed-off-by: Vorname Nachname <mail@example.de>` unter den Commit. Ein
Beitragslizenzvertrag (CLA) wird nicht verlangt.

## KI-gestützte Entwicklung

Große Teile dieses Projekts sind mit Claude Code entstanden — Renderer, Prüfungen und Tests
gleichermaßen. Das wird hier gesagt, weil es den Umgang mit Beiträgen erklärt: Es zählt der
Beweis, nicht die Herkunft einer Zeile. Ein von einem Modell geschriebener Patch ist willkommen,
wenn er reproduziert, misst und seine Gegenprobe mitbringt; ein von Hand geschriebener wird nach
denselben Maßstäben geprüft.

Wer ein Modell benutzt hat, muss das nicht kennzeichnen. Wer ungeprüfte Modellausgaben
einreicht, merkt es spätestens an der Beweispflicht.

## Regeln und Maße ändern

Die Sollwerte und ihre Herkunft stehen an **einer** Stelle:
[`skill/falzmarke/regeln/din5008.yaml`](skill/falzmarke/regeln/din5008.yaml). Daraus wird der
Abschnitt „Quellenlage je Regel" in
[`skill/references/din5008.md`](skill/references/din5008.md) erzeugt
(`python3 scripts/quellenlage.py`) — diesen Abschnitt nie von Hand ändern. Die geometrischen
Konstanten liegen in [`skill/falzmarke/geometrie.py`](skill/falzmarke/geometrie.py) und gehören
zur selben Änderung.

Jede Regel trägt ihre Herkunft. Nur eine mehrfach belegte Regel darf als Fehler wirken; eine aus
einer einzigen Quelle ist eine Warnung. Ein geänderter Wert braucht einen Beleg — die Norm, eine
Maßzeichnung, eine Messung. Nicht die verbreitete Word-Vorlage: sie weicht nachweislich um
mehrere Millimeter ab, siehe [`docs/normmasse.md`](docs/normmasse.md).

**Normtext wird nie geladen, gescannt oder zitiert.** Übertragen werden Fundstellen und Werte,
nie Wortlaut, Tabellen oder Abbildungen — siehe [`CLAUDE.md`](CLAUDE.md) und
[`docs/recht.md`](docs/recht.md).

## Die vendorte Datei

`skill/falzmarke/typst/vendor/letter-pro-v3.0.0.typ` ist Fremdcode (MIT) und bleibt
**unverändert**. Ein Test prüft ihre Prüfsumme. Muss dort wirklich etwas geändert werden, gehört
jede Änderung nach `skill/falzmarke/typst/vendor/CHANGES.md` (anzulegen) und die Prüfsumme im
Test angepasst — beides im selben Commit.

Beachte: In dieser Datei steht das Wort `normbrief`, in einer URL der Deutschen Post. Das ist
kein Überbleibsel des früheren Projektnamens; nicht „korrigieren". Eine Ersetzung würde eine
fremde Quelle verfälschen und die Prüfsumme brechen.

## Musterbriefe beitragen

Beispielbriefe sind willkommen — sie zeigen Fälle, an die niemand gedacht hat. Zwei Bedingungen:
Der Text muss frei von echten Personen-, Firmen- und Bankdaten sein, und er wird vor der Aufnahme
vom Maintainer freigegeben. Ein Musterbrief ist Teil des ausgelieferten Werkzeugs; was darin
steht, steht später in fremden Briefköpfen.

## Stil

- Code, Kommentare, Meldungen und Commits auf Deutsch — passend zum Gegenstand. Englisch bleiben
  `CONTRIBUTING.md` (dieser Absatz oben) und `SECURITY.md` in ihrem englischen Teil.
- Kommentare erklären **warum**, nicht was. Besonders wertvoll: der Grund, warum etwas *nicht*
  offensichtlich gelöst ist.
- Commit-Nachrichten nach [Conventional Commits](https://www.conventionalcommits.org/de/), und
  sie beschreiben die Wirkung, nicht die Datei.

## Fehler melden

Bei Geometriefehlern **immer die Ausgabe von `verify` mitschicken**:

```bash
python3 skill/scripts/falzmarke.py verify DEIN.pdf --form B --json
```

Ohne sie lässt sich nicht unterscheiden, ob das Layout falsch sitzt oder die Messung danebenliegt.
