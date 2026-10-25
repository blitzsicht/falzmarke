# 0053 — Der Schreibstil steht im Profil, geteilt in prüfbar und übertragen

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:** [0029](0029-falzmarke-ist-werkzeug-kein-kanal.md), [0034](0034-email-ist-ausgabe.md), [0035](0035-vier-ebenen-fuer-email-regeln.md), [0039](0039-falzmarke-rechnet-nicht.md)

## Worum es geht

`skill/references/stil.md` sagt, wie eine Geschäftsmail aufgebaut ist. Was es nicht sagen kann:
wie **dieser** Absender schreibt. Ein Einzelunternehmer schreibt „ich", eine GmbH „wir"; eine
Werkstatt will „zeitnah" nicht lesen, eine Kanzlei schon. Das in die Stilreferenz zu schreiben
hieße, sie für jeden Absender zu gabeln — und es gibt mehrere: siluri, blitzsicht, privat.

Der Ort dafür ist das Profil, denn dort steht ohnehin, wer der Absender ist. Neu ist der
Abschnitt `email.stil:` mit drei Feldern: `person:`, `floskeln:`, `hinweise:`.

## Entscheidung 1: Der Abschnitt ist geteilt, und die Grenze ist die Zusage

`person:` und `floskeln:` prüft `lint` am Text. `hinweise:` prüft es **nur auf Form** — Liste von
Zeichenketten, höchstens zehn, je höchstens 200 Zeichen. Der Inhalt bleibt ungelesen.

Der Grund ist keine Bequemlichkeit, sondern eine Eigenschaft des Pakets: falzmarke gibt
Profildaten an kein Modell weiter und versteht keinen Satz. Die Abhängigkeiten sind `typst`,
`pyyaml`, `pdfplumber`, `pypdf`, `markdown-it-py`, `pillow` — kein HTTP-Client, kein Modell-SDK
(ADR 0029, ADR 0039). Eine Prüfung, die „Fristen immer als Datum, nie als Dauer" einzuhalten
behauptete, wäre eine Zusage ohne Deckung. Genau das verbietet ADR 0035 Festlegung 1.

Wirksam ist `hinweise:` trotzdem, nur auf dem anderen Weg: `skill/SKILL.md` Schritt 4 lässt den
Abschnitt vor dem Formulieren lesen — wie `references/stil.md` selbst. **falzmarke überträgt die
Stilvorgabe, es erzwingt sie nicht**, und es sagt das an der Stelle, an der jemand es liest.

Wer das später ändern will, braucht dafür keinen Code, sondern eine Antwort auf die Frage, woher
das Urteil kommen soll. Ein LLM-Aufruf in `lint` ist die Antwort nicht (ADR 0029).

## Entscheidung 2: Was geprüft wird, ist Warnung — was die Form betrifft, ist Fehler

Zwei Regeln auf Ebene `praxis`, `herkunft: werkzeug`, `wirkung: warnung`:

| Regel | Was sie sagt |
|---|---|
| `email.stil_person` | Das Profil sagt `person: ich`, im Text steht „wir" (oder umgekehrt) |
| `email.stil_floskel` | Eine Wendung aus `floskeln:` steht im Text |

Warnung, weil es Ermessen ist: Wie jemand schreibt, entscheidet er selbst. Nach ADR 0035
Festlegung 1 **kann** eine Regel auf Ebene `praxis` ohnehin kein Fehler werden; die Eintragung
hält das fest, statt sich darauf zu verlassen.

Die Form des Abschnitts ist dagegen `email.stil` mit `wirkung: fehler`, Ebene und Herkunft
`werkzeug`. Das ist der Datenvertrag, keine Stilaussage. `person: isch` ist ein Tippfehler, und
ein Tippfehler darf nicht stillschweigend die Prüfung abschalten — derselbe Grund wie bei
`email.anrede` und `dialekt`.

## Entscheidung 3: Nur die Subjektform, und nur außerhalb von Auszügen

`person:` sucht `\bich\b` beziehungsweise `\bwir\b`, sonst nichts. „unser Angebot" schreibt auch
ein Einzelunternehmer, „mein Eindruck" auch jemand, der sonst „wir" sagt. Die Possessivformen
mitzuprüfen hätte die Regel bei gültigem Text anschlagen lassen — die Lehre aus der
Telefonprüfung ([#133](https://github.com/blitzsicht/falzmarke/issues/133)).

Beide Prüfungen laufen auf dem Text **ohne wortgetreue Auszüge**: Zäune mit ``` oder ~~~ und
Inline-Auszüge in einfachen Backticks fallen vorher weg. Ein Auszug ist fremder Wortlaut — eine
zitierte Protokollzeile, eine Fehlermeldung, die Antwort eines Kunden. Dass dort „wir" oder
„zeitnah" steht, sagt über den Stil des Absenders nichts.

Die feste Liste `FLOSKELN` bleibt davon unberührt. Was sie heute tut, halten Tests fest; sie
ebenfalls um die Auszüge zu beschneiden ist eine eigene Änderung mit eigener Gegenprobe.

## Entscheidung 4: Das mitgelieferte Beispielprofil trägt kein aktives `stil:`

`skill/falzmarke/typst/profiles/example.yaml` zeigt den Abschnitt als Kommentar. Ein
mitgeliefertes Profil, das bei jedem Lauf warnt, ist Lärm — dieselbe Lehre, die schon
`lint.py` an der Pflichtangaben-Warnung festhält. Wer den Stil festhalten will, trägt ihn in sein
eigenes Profil ein.

## Folgen

- `stil` steht in `PROFIL_EMAIL_FELDER` (`skill/falzmarke/lint.py`). Ohne diesen Eintrag lehnt
  `_melde_unbekannte` das Feld als Tippfehler ab — ein Profil mit `stil:` erzeugte dann einen
  Befund, statt zu wirken. `tests/test_profil_stil.py` hält genau das fest.
- Drei neue Regeln in `skill/falzmarke/regeln/email.yaml`, keine mit Quellenangabe: Das ist
  Werkzeugverhalten, keine Normaussage, und `quellen: []` sagt das, statt eine Fundstelle zu
  erfinden.
- Das Feld ist in `skill/references/frontmatter.md` und `docs/profiles.md` dokumentiert.
  `SKILL.md` sagt, dass `lint` ein dort nicht genanntes Feld ablehnt — undokumentiert wäre es
  unbenutzbar.

## Was ausdrücklich nicht entschieden wird

- **Keine Prüfung von `hinweise:` auf Inhalt**, auch nicht „nur als Warnung". Siehe Entscheidung 1.
- **Kein Umschreiben.** `lint` ändert den Text nicht; die Begründung steht in
  `skill/references/stil.md` und ist älter als dieser Abschnitt.
- **Keine Satzlängen- oder Varianzregel.** Eine Mail nach `stil.md` hat fünf Sätze; eine
  Varianzforderung darauf erzeugt entweder keinen Befund oder einen falschen.
- **Kein zweites Stilprofil neben dem Absenderprofil.** Der Stil hängt am Absender, nicht am
  Schreiben; eine eigene Datei dafür hätte zwei Orte, die auseinanderlaufen können.
