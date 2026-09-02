# 0037 — Ein Changelog-Eintrag je Vorgang, als eigene Datei

**Datum:** 02.09.2026 · **Status:** angenommen · **Umsetzung:** mit dem Merge dieses Eintrags

## Entscheidung

Jeder Vorgang, der das Werkzeug ändert, legt seinen Changelog-Punkt als **eigene Datei** unter
`changelog.d/<vorgang>.<rubrik>.md` ab. Der Pflicht-Check „Changelog-Eintrag" verlangt sie; ohne
sie ist der Pull Request nicht mergebar.

Beim Release bündelt `python3 scripts/changelog.py --buendeln v0.9.2` die Fragmente zu einem
Versionsabschnitt in `CHANGELOG.md` und leert das Verzeichnis. Wer das vergisst, kommt nicht
durch: `release.yml` bricht vor dem Packen ab, solange `changelog.d/` nicht leer ist.

Vier Rubriken: `neu`, `geaendert`, `behoben`, `infrastruktur`. Ausgenommen von der Pflicht sind
Abhängigkeits-Aktualisierungen, Vorgänge, die ausschließlich `docs/`, Markdown im
Wurzelverzeichnis oder `tests/` anfassen, und Einzelfälle mit dem Label `ohne-changelog`.

## Warum

`CHANGELOG.md` hatte keinen Ort für einen Eintrag ohne Version. Wer eintragen wollte, hätte eine
Versionsüberschrift erfinden müssen — für einen Vorgang, dessen Version noch niemand kennt.

Die Folge ist gemessen: Von **46 Vorgängen** zwischen v0.8.2 und v0.9.0 hat **einer**
`CHANGELOG.md` angefasst. Nach dem Nachtragen von 39 Einträgen von Hand (#214) waren es bei den
nächsten vier Vorgängen wieder **null**. Zweimal fiel damit die Nacharbeit für ein halbes
Hundert Vorgänge auf einmal an — und die zweite Nacharbeit war teurer als die erste, weil
niemand mehr wusste, was in einem halben Jahr alten Vorgang eigentlich passiert war.

Das ist kein Disziplinproblem. Ein Weg, den zu gehen Erfindungsgabe verlangt, wird nicht
gegangen.

## Warum kein `## Unveröffentlicht`-Abschnitt

Das wäre der Weg von *Keep a Changelog*, dem dieses Repository sonst lose folgt, und er braucht
keine neue Maschinerie. Dagegen steht die Arbeitsweise hier: Es laufen regelmäßig mehrere Zweige
gleichzeitig, jeder in einem eigenen Arbeitsbaum. Alle trügen ihren Punkt in **dieselben Zeilen**
ein. Ein Merge-Konflikt bei jedem zweiten Vorgang ist ein verlässlicher Weg, eine Regel wieder
loszuwerden.

Fragmentdateien haben diesen Konflikt nicht: Zwei Vorgänge legen zwei Dateien an, und Git hat
nichts zu entscheiden.

## Warum der Check blockiert

Ein Hinweis, der nichts verhindert, ändert nichts. Der Empfänger ist oft ein Worker, der weder
Issue-Kommentare noch die Beitragsseite liest — für ihn ist ein roter, nicht blockierender Check
unsichtbar. Genau das war der Zustand, den die beiden Nacharbeiten belegen: Die Erwartung stand
in `CONTRIBUTING.md`, und sie wurde 45 von 46 Mal nicht erfüllt.

Deshalb steht der Job in `.github/workflows/ci.yml` und nicht in einem eigenen Workflow:
`scripts/pflicht_checks.py` liest nur diese Datei. Ein Job daneben wäre gelaufen, aber nie im
Ruleset gelandet — er hätte gemeldet und nichts verhindert.

## Was das kostet

Einen Handgriff je Vorgang. Das ist der Preis, und er ist bewusst gewählt: Der Punkt entsteht in
dem Moment, in dem jemand am besten weiß, was er geändert hat — nicht Wochen später aus einer
Commit-Liste.

Die vier Ausnahmen halten den Preis dort, wo er etwas kauft. Sie greifen nur, wenn **alle**
geänderten Pfade hineinfallen; wer Code und Doku zugleich ändert, trägt ein. `skill/**` zählt
nie als Doku, auch nicht `skill/references/din5008.md` — dort stehen die Sollwerte der
Normregeln, und ihre Änderung ohne Spur im Verlauf wäre genau die Sorte stille Änderung, gegen
die dieses Repository sonst überall Wächter aufstellt.

## Verwandt

- [0036](0036-pypi-wartezeit-statt-freigabe.md) — eine Versionsnummer auf PyPI ist unwiderruflich
  belegt. Deshalb bricht `--buendeln` ab, wenn die Version im Changelog schon vorkommt.
- [0030](0030-reihenfolge-der-roadmap.md) — dieselbe Bauart: eine erzeugte Seite, deren Quelle
  woanders liegt.
