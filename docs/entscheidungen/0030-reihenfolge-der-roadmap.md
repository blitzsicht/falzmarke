# 0030 — Reihenfolge der Roadmap

**Datum:** 26.08.2026 · **Status:** angenommen

## Entscheidung

Die Roadmap folgt dieser Reihenfolge:

1. **Belegbarkeit** — das Werkzeug soll nur behaupten, was es belegen kann
2. **Lange und professionelle Schreiben** — Überschriften, Listen, Zitate, Code
3. **E-Mail** — Geschäftsmails nach Abschnitt 22 aus derselben Quelle *(ergänzt 27.08.2026)*
4. **Einfacher Zugang** — Dienst, MCP, Browser, Website
5. **Dokumentpakete und Automatisierung** — Anlagen, Hybridbrief, Serienbrief
6. **Beweis** — Signatur (`proof`)

Was dieser Reihenfolge nicht dient, wird **geparkt, nicht gelöscht** — mit einer Begründung, die
sagt, woran es hängt.

## Warum diese Reihenfolge

**Belegbarkeit zuerst**, weil sie das Alleinstellungsmerkmal trägt. Der Satz, um den es geht,
lautet: *Andere Werkzeuge erzeugen ein PDF. falzmarke prüft das Ergebnis.* Fällt der Beleg, fällt
das Versprechen — und mit ihm der Grund, das Werkzeug dem eigenen zu Recht misstrauischen Nutzer
zu empfehlen. Alles Weitere baut darauf auf und wäre ohne es nur Ausstattung.

**Lange Schreiben vor Zugang**, weil ein leicht erreichbares Werkzeug, das den eigentlichen
Anwendungsfall nicht kann, Erwartungen weckt, die es enttäuscht. Wer einen Widerspruch, eine
Kündigung oder einen Schriftsatz setzt, braucht Überschriften und Listen; ohne sie ist der
einfache Zugang ein Zugang zu wenig.

**Zugang vor Dokumentpaketen**, weil Rückmeldung nur von Benutzern kommt. Anlagen, Hybridbrief
und Serienbrief sind Antworten auf Fragen, die bislang niemand gestellt hat.

**Beweis zuletzt**, weil eine Signatur das Dokument bestätigt — und ein Dokument, dessen Maße
noch auf Sekundärquellen stehen, ist die falsche Sache zum Bestätigen. Die Reihenfolge ist hier
nicht Bequemlichkeit, sondern Logik: Erst wissen, was drinsteht, dann besiegeln.

## Eine Spannung, die diese Entscheidung nicht auflöst

Der Meilenstein **Vor Verbreitung** sperrt die Bewerbung, bis der Normabgleich gegen den
Originaltext vorliegt. Der Normabgleich wiederum wartet auf 100 Sterne im Repository (Stand bei
dieser Entscheidung: 0) — und die kommen nur durch Verbreitung.

Das ist ein Kreislauf, und er ist hier **nicht entschieden**. Er gehört in eine eigene
Entscheidung, die den Zuschnitt von „Vor Verbreitung" klärt: Vermutlich ist Verbreitung
vertretbar, solange die Warnstufe ehrlich ausgewiesen bleibt — heute stehen 13 Regeln auf Fehler
und 17 auf Warnung, und das steht auch so im README. Aber das ist eine Abwägung, keine
Ableitung, und sie wird getroffen statt unterstellt.

## Folgen

- Die Meilensteine tragen diese Reihenfolge als Namen, ohne Versionsnummern. Eine Versionsnummer
  vergibt das Release, nicht die Planung.
- Ein Meilenstein **Geparkt** nimmt auf, was wartet — mit Begründung, damit später erkennbar ist,
  worauf.
- Neue Vorschläge werden gegen diese Reihenfolge geprüft, bevor sie ein Issue werden.

## Nachtrag 27.08.2026 — die Phase E-Mail

Die E-Mail-Fassung (#59) ist als dritte Phase aufgenommen, nach den langen Schreiben und vor dem
einfachen Zugang.

**Warum dort und nicht später:** Sie hängt am Dialekt 1.1 (#26) — Überschriften, Zitate und Code
müssen im Markdown-Baum existieren, bevor ein zweiter Emitter sie ausgeben kann. Und sie hängt
*nicht* am Hybridbrief oder am Beweis, also gibt es keinen Grund, sie dahinter zu stellen.

**Warum sie eine eigene Phase ist und nicht in „Dokumentpakete" fällt:** Dort liegen Pakete
*um* ein Dokument herum — Anlagen, Ablage, Serie. Eine E-Mail ist ein anderes Erzeugnis, mit
eigener Struktur, eigenem Prüfweg (`verify --email`) und eigenen Regeln (Abschnitt 22). Sie unter
„Dokumentpakete" zu führen hieße, den Namen der Phase unbrauchbar zu machen.

Die Phase ändert nichts an der Begründung oben: Belegbarkeit bleibt zuerst, und die E-Mail-Regeln
tragen ihre Herkunft wie alle anderen — bis zum Normabgleich (#12) aus Sekundärquellen.

Was die Phase inhaltlich festlegt — E-Mail ist Ausgabe, nicht Kanal —, steht in
[0034](0034-email-ist-ausgabe.md).