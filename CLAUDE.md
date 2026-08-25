# Arbeitsregeln für dieses Repository

## Normtext

**Normtext wird nie geladen, gescannt oder zitiert; einzige Quelle für Normregeln ist
`skill/references/din5008.md`.**

Der Text der DIN 5008:2020-03 ist urheberrechtlich geschützt und kostenpflichtig. Weder sein
Wortlaut noch seine Tabellen oder Abbildungen gehören ins Repository, in einen Commit, in eine
Issue oder in den Kontext einer Sitzung. Das gilt auch für gekaufte Exemplare: Wer den
Normabgleich macht, überträgt **Fundstellen** („Abschnitt 5.2") und **Werte**, keinen Text.

## Quellenlage

Die Herkunft jeder Regel steht an genau einer Stelle:
[`skill/falzmarke/regeln/din5008.yaml`](skill/falzmarke/regeln/din5008.yaml). Der Abschnitt
„Quellenlage je Regel" in `skill/references/din5008.md` wird daraus erzeugt
(`python3 scripts/quellenlage.py`) — nie von Hand ändern.

Nur eine mehrfach belegte Regel darf als Fehler wirken. Wer eine Regel hinzufügt, trägt sie dort
ein; `tests/test_quellenlage.py` besteht sonst nicht.

## Messen statt behaupten

Sollwerte stehen in `skill/falzmarke/geometrie.py` und `skill/references/din5008.md` — beides
zusammen ändern. Jede neue Prüfung braucht ihre Gegenprobe in `tests/test_gegenbeweis.py`: Das
Layout wird an genau einer Stelle sabotiert, und die neue Prüfung muss dort anschlagen. Ein
Prüfmittel, das nie rot werden kann, ist kein Nachweis.

## Sprache

Code, Kommentare, Fehlermeldungen, Dokumentation und Commits auf Deutsch — der Gegenstand ist
eine deutsche Norm. `CONTRIBUTING.md` und `SECURITY.md` sind ebenfalls deutsch, tragen aber je
einen kurzen englischen Absatz: Beiträge und Sicherheitsmeldungen kommen von überall, und wer
kein Deutsch liest, soll wenigstens wissen, worum es geht und wohin er sich wendet.

**Keine Claude-Attribution in Commits** — kein `Co-Authored-By`, kein Session-Trailer, kein
„Generated with". Dass große Teile mit Claude Code entstanden sind, steht in `CONTRIBUTING.md`
unter „KI-gestützte Entwicklung"; das ist die Stelle dafür, nicht jede einzelne Commit-Nachricht.

## Was nicht behauptet wird

Kein „normgerecht", kein „DIN-konform", keine Zertifizierung — solange der Normabgleich aussteht.
`tests/test_textkanon.py` hält den Satz fest, der das erklärt. Einzelheiten in
[`docs/recht.md`](docs/recht.md).
