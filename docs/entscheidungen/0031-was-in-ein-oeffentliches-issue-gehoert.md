# 0031 — Was in ein öffentliches Issue gehört

**Datum:** 26.08.2026 · **Status:** angenommen

## Entscheidung

Ein Issue in diesem Repository beschreibt **das Werkzeug**: was es können soll, warum das
gebraucht wird, woran man erkennt, dass es erfüllt ist.

Es beschreibt **nicht, wie wir arbeiten**: keine Namen anderer Repositories, keine internen
Dateipfade, keine Auftrags- oder Arbeitspaketstruktur, keine Agenten- oder Rollennamen aus der
eigenen Werkzeugkette, keine Kundennamen.

Die Prüffrage lautet: **Würde eine fremde Beitragende diesen Satz verstehen und brauchen?**
Lautet die Antwort nein, gehört er in den internen Auftrag, nicht ins Issue.

## Warum

Für Dateien galt diese Grenze schon (siehe `docs/entscheidungen/README.md`, Abschnitt „Was hier
steht und was nicht"): Entscheidungen sind öffentlich, Aufträge nicht. Für Issues war sie nie
formuliert — und Issues sind genau die Stelle, an der ein interner Auftrag in ein öffentliches
Arbeitspaket übersetzt wird. Beim Übersetzen rutscht Kontext mit, der im Auftrag richtig war und
im Issue niemandem nützt.

Gemessen am 26.08.2026, kurz nachdem `docs/ROADMAP.md` alle offenen Issues auf **eine**
README-verlinkte Seite gezogen hatte: fünf Stellen nannten das private Ops-Repository samt
internem Verzeichnispfad, eine beschrieb die Arbeitsteilung der eigenen Werkzeugkette. Nichts
davon war ein Zugriffsproblem — ein privates Repository bleibt privat, sein Name öffnet nichts.
Es war ein Informationsproblem: die Arbeitsweise las mit.

Die Roadmap hat den Befund nicht verursacht, sie hat ihn **sichtbar** gemacht. Verstreut über
zwanzig Issues fiel er niemandem auf; gebündelt auf einer Seite sofort.

## Was das nicht heißt

**Belege dürfen weiter intern liegen.** Ein Satz wie „Die Belege liegen beim Maintainer vor;
sie sind nicht frei lizenziert und gehören nicht in dieses Repository" ist genau richtig: Er
sagt ehrlich, dass es einen Beleg gibt und warum er fehlt. Das ist die Belegkultur dieses
Projekts (vgl. `skill/references/din5008.md`). Nur der **Ort** ist wegzulassen — er nützt von
außen niemandem.

**Architekturfragen bleiben öffentlich.** Ob eine Orchestrierungsschicht in dieses Werkzeug
gehört oder daneben, ist eine Frage über das Werkzeug und gehört hierher. Was nicht hierher
gehört, ist die Antwort auf „und so machen wir das heute intern".

## Folgen

- `scripts/oeffentlichkeit.py` prüft die offenen Issues gegen eine Wortliste und läuft wöchentlich
  neben der Roadmap. Eine Regel, die man im richtigen Moment lesen muss, hat hier bereits einmal
  nicht gehalten — dieselbe Grenze existierte für Dateien und riss bei Issues trotzdem.
- Der Wächter meldet Funde **nur im Job-Protokoll**, nie als Kommentar am Issue: ein öffentlicher
  Kommentar, der den Fund zitiert, verdoppelt ihn.
- Ein Issue, das die Grenze nicht einhalten kann, weil sein Gegenstand die Arbeitsweise **ist**,
  wird ins private Ops-Repository verschoben statt entschärft.
