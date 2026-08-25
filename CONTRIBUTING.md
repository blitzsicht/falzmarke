# Mitmachen

Danke für dein Interesse. Dieses Projekt hat eine ungewöhnliche Eigenschaft, die alles andere
bestimmt: **Es misst sein eigenes Ergebnis.** Was hier geändert wird, muss deshalb messbar bleiben.

## Der Grundsatz

Ein Prüfmittel, das nie rot werden kann, ist kein Nachweis.

Wer eine Prüfung hinzufügt, fügt auch die Gegenprobe hinzu: In
[`tests/test_gegenbeweis.py`](tests/test_gegenbeweis.py) wird das Layout an genau einer Stelle
absichtlich verschoben, und die neue Prüfung muss dort anschlagen. Dazu gehört die Kontrollprobe
ohne Sabotage, die grün bleiben muss — ohne sie belegt der Test nur, dass eine Kopie anders misst
als das Original.

Dasselbe gilt für Fehlerbehebungen: **Erst den Fehler reproduzieren, dann beheben.** Wenn er sich
nicht reproduzieren lässt, ist unklar, was der Fix behebt.

## Bevor du einen Pull Request öffnest

```bash
python3 skill/scripts/bootstrap.py
python3 -m pytest -q
for f in examples/*.md; do python3 skill/scripts/falzmarke.py render "$f" -o "/tmp/$(basename "$f" .md).pdf"; done
```

Alle Tests grün, alle sieben Beispiele ohne `FEHL`-Zeile.

## Maße ändern

Die Sollwerte stehen an **einer** Stelle: `FORM` und die Konstanten in
[`skill/scripts/geometrie.py`](skill/scripts/geometrie.py), beschrieben in
[`skill/references/din5008.md`](skill/references/din5008.md). Beides zusammen ändern.

Ein geänderter Wert braucht einen Beleg — die Norm, die Maßzeichnung, eine Messung. Nicht die
verbreitete Word-Vorlage: sie weicht nachweislich um mehrere Millimeter ab, siehe
[`docs/normmasse.md`](docs/normmasse.md).

## Die vendorte Datei

`skill/typst/vendor/letter-pro-v3.0.0.typ` ist Fremdcode (MIT) und **unverändert**. Ein Test
prüft die Prüfsumme. Muss dort wirklich etwas geändert werden, gehört jede Änderung nach
`vendor/CHANGES.md` und die Prüfsumme im Test angepasst — beides im selben Commit.

## Stil

- Code und Kommentare auf Deutsch, passend zum Gegenstand.
- Kommentare erklären **warum**, nicht was. Besonders wertvoll: der Grund, warum etwas *nicht*
  offensichtlich gelöst ist.
- Commit-Nachrichten beschreiben die Wirkung, nicht die Datei.

## Fehler melden

Bei Geometriefehlern **immer die Ausgabe von `check` mitschicken**:

```bash
python3 skill/scripts/falzmarke.py check DEIN.pdf --form B --json
```

Ohne sie lässt sich nicht unterscheiden, ob das Layout falsch sitzt oder die Messung danebenliegt.
