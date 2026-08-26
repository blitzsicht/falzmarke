# 0029 — falzmarke ist Werkzeug, kein Kanal

**Datum:** 26.08.2026 · **Status:** angenommen

## Entscheidung

falzmarke ist ein Werkzeug, das Briefe **setzt und prüft** — als CLI, als Skill und künftig als
MCP-Dienst. Es befördert nichts.

Nicht Teil von falzmarke sind deshalb:

- **Versand** über Post, E-Mail oder qualifizierte Zustelldienste
- **Zustellnachweise** und deren Verwahrung
- **Versandzustände** in einem Ausgangsbuch

Diese Aufgaben gehören später in ein eigenes Repository, das falzmarke als Bibliothek verwendet
(Arbeitsname `falzmarke-versand`, nicht angelegt). Vorerst gehören sie nirgendwohin.

**Die Signatur (`proof`) bleibt.** Sie betrifft das erzeugte Dokument, nicht seinen Weg — und
damit genau das, was falzmarke herstellt.

**Die E-Mail-Fassung (`--als email`) bleibt ebenfalls.** Sie erzeugt eine Ausgabe und versendet
nichts. Der Unterschied ist nicht formal: Wer eine Datei erzeugt, haftet für ihren Inhalt; wer
sie befördert, für Zustellung und Nachweis. Das sind zwei Versprechen, und falzmarke gibt nur
das erste.

## Warum

Ein Werkzeug, das misst, und ein Dienst, der zustellt, haben unvereinbare Zusicherungen.
Die Messung ist reproduzierbar: dieselbe Eingabe ergibt dasselbe PDF und denselben Prüfbericht,
nachvollziehbar auf jedem Rechner. Zustellung ist es nicht — sie hängt an einem Dritten, an
Zeitpunkten, an Empfängern, an Geld.

Beides in einem Repository hieße, dass die schwächere Zusicherung die stärkere mitzieht: Sobald
falzmarke Zustellung verspricht, ist „auf den Millimeter geprüft" nicht mehr die Aussage des
Werkzeugs, sondern die Aussage einer Kette, deren Glieder es nicht kontrolliert.

## Folgen

- **#8** (Postversand über LetterXpress) wird geschlossen, mit Verweis auf diese Entscheidung.
- **#19** (Beweiskette) verkleinert sich auf `proof`; `delivery` entfällt und wird als Absatz
  „außerhalb" festgehalten, damit die Überlegung nicht verlorengeht.
- **#9** (Ablage in Paperless-NGX) bleibt möglich — Ablage ist keine Beförderung —, aber als
  optionaler Adapter, nicht als Kernaufgabe.
- Der Meilenstein **Geparkt** nimmt auf, was durch diese Entscheidung wartet, statt es zu löschen.

## Was diese Entscheidung nicht sagt

Sie sagt nicht, dass Versand unwichtig wäre. Sie sagt, dass er ein eigenes Versprechen ist und
deshalb ein eigenes Repository braucht — mit eigener Prüfung, eigener Haftungsfrage und eigenem
Namen.
