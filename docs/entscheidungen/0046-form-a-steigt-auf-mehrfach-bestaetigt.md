# 0046 — Form A steigt auf `mehrfach_bestaetigt`

**Datum:** 24.09.2026 · **Status:** angenommen · **Betrifft:** [#180](https://github.com/blitzsicht/falzmarke/issues/180)

## Entscheidung

`geometrie.form_a.masse` trägt `herkunft: mehrfach_bestaetigt` und `wirkung: fehler`.

Getragen wird die Stufe von `massskizze_a` (Form-A-Zeichnung im Onlineprinters-Magazin,
Bezugsnorm DIN 5008:2020) und `federwerk` (Fließtext, der die vier Maße ausdrücklich der
DIN 5008 zuschreibt) — zwei voll zählende Quellen aus zwei Gruppen. `koma_script`, `dinbrief`
und `letter_pro` zählen weiter nur `einzeln` und bewegen nichts.

## Warum

**Die Folge, um derentwillen #180 zögerte, gibt es nicht.** Das Issue hielt fest, die Anhebung
mache „aus der Warnung einen Fehler", und ein Form-A-Brief mit abweichenden Maßen bräche dann ab.
Nachgemessen am 24.09.2026: Keine der vierzehn Geometrie-Regeln trägt `lint:`, `typografie:` oder
`pruefung:`, und `skill/falzmarke/geometrie.py` importiert den Regelkatalog nicht. Die Maße am
fertigen PDF werden mit der Vorgabe `STUFE_FEHLER` gemessen und entscheiden über `Bericht.ok` und
den Exit-Code — seit jeher, unabhängig von der Stufe in der Regeldatei. Gegenprobe im selben
Durchgang: Mit der **alten** Stufe (`einzeln_belegt` / `warnung`) und einem um 3 mm verschobenen
Sollwert der Form-A-Falzmarke meldet der Lauf `FEHL  Falzmarke 1, y`, schreibt „FEHLGESCHLAGEN —
das PDF hält die Maße aus DIN 5008 nicht ein" und endet mit Exit 2. Daneben stand im selben Lauf
eine echte Warnung (`schreibweise.datum`) — der Bericht kann also beides, er tut es hier nur nicht.

Für die Geometrie sagt die Stufe also etwas über die Beleglage und nichts über die Wirkung. Was
diese Entscheidung ändert, ist die Auskunft des Werkzeugs über sich selbst — und die war falsch.

**Der Vergleich mit Form B trägt umgekehrt.** #180 führte an, Form B stehe „auf zwei Zeichnungen"
und wirke als Fehler, Form A stehe nun ebenso auf zwei Quellen. Es ist eine Zeichnung: `massskizze_b`
und `onlineprinters` tragen dieselbe `gruppe:`, weil sie bis in den Fußtext deckungsgleich sind
([Befund vom 27.08.2026](../quellenunabhaengigkeit-2026-08-27.md)). Alle fünf `geometrie.form_b.*`
stehen deshalb in `regeln.stufe_traegt_nicht()`, dem offenen Rest von [#16]. Form A ist die
einzige der sechs Formregeln, die die Definition **erfüllt** — und war die einzige, die dafür
herabgestuft blieb. (Zwei Regeln außerhalb der Formen, `geometrie.seitenformat` und
`geometrie.seitenraender`, tragen ebenfalls zwei Gruppen; sie standen nie zur Debatte.)

[#16]: https://github.com/blitzsicht/falzmarke/issues/16

**Der Beleg steht jetzt an der Regel.** `belegt_durch.massskizze_a` hat gefehlt; die Stufe hätte
sich auf ein Paar gestützt, das `ohne_belegpruefung()` als ungeprüft führt. Der Beleg ist dabei
nicht neu erhoben, sondern aus dem Quellen-Register an die Regel umgetragen worden — er steht dort
seit dem 26.08.2026 ausformuliert, bis zur Probe 87 + 105 + 105 = 297 mm.

## Was hier nicht entschieden wird

**Die Grenze aus [ADR 0044](0044-woertlicher-beleg-schlaegt-werkzeugeinstufung.md) bleibt.** Die
32 mm, die der Wikipedia-Artikel für das Form-A-Anschriftfeld nennt, sind weiterhin **kein** Beleg
für diese Regel: Unsere 27 mm folgen daraus nur über eine Subtraktion, und eine Subtraktion ist
keine Nennung. ADR 0044 nennt ausdrücklich diese Regel als den Fall, an dem daran eine Stufe hinge.
Sie hängt nicht daran — die Stufe steht auf `massskizze_a` und `federwerk`.

**[ADR 0042](0042-quellenpruefung-ruht.md) ist nicht berührt.** Die Quellenprüfung ruht weiter;
es ist kein ungeprüftes Paar nachgelesen worden. Dass die Zahl von 27 auf 26 fällt, ist die Folge
des Umtragens, nicht die einer Wiederaufnahme.

**Die Unabhängigkeit von `massskizze_a` und `federwerk` ist nicht gemessen.** Das war Einwand 2
in #180, und er bleibt stehen. Die beiden liegen bei verschiedenen Betreibern, haben verschiedene
Darstellungsformen (Zeichnung gegen Fließtext) und berufen sich auf verschiedene Ausgaben (2020
gegen 2011) — das spricht für Unabhängigkeit, misst sie aber nicht. `docs/recht.md` führt die Regel
deshalb unter „Unabhängigkeit ungeprüft", zusammen mit `geometrie.seitenformat` und
`geometrie.seitenraender`. Das ist die schwächere Aussage, und sie steht dort, wo sie zu lesen ist.

Einwand 1 aus #180 — `federwerk` beruft sich auf die Ausgabe 2011 — wiegt nicht mehr als bei Form B:
Dort ist die tragende Zeichnung von 2013. `massskizze_a` nennt als Bezugsnorm 2020. Was die Ausgabe
2020-03 wirklich sagt, klärt ohnehin erst der Normabgleich ([#12]), und der ersetzt dann jede
Herkunftsstufe durch eine Fundstelle.

[#12]: https://github.com/blitzsicht/falzmarke/issues/12

## Folgen

- `geometrie.form_a.masse`: `herkunft: mehrfach_bestaetigt`, `wirkung: fehler`,
  `belegt_durch.massskizze_a` mit Fundstelle.
- Regeln auf „mehrfach bestätigt": 10 → **11**; davon mit ungeprüfter Unabhängigkeit 2 → **3**.
  Die 8, die auf derselben Zeichnung stehen, bleiben 8.
- Ungeprüfte Quelle-Regel-Paare: 27 → **26**. Die Aufteilung in `docs/recht.md` (16 bei Quellen
  ohne Belegsgruppe, 10 bei `onlineprinters`) geht damit wieder auf; mit den 27 tat sie es nicht.
- `regeln._yaml_laden()` weist einen doppelt vergebenen YAML-Schlüssel ab. Anlass war diese Regel:
  Sie trug zwei `bemerkung:`, und PyYAML nahm still den letzten — der Absatz über die 32 mm aus
  [#345](https://github.com/blitzsicht/falzmarke/issues/345) war einen Tag lang im geladenen
  Regelwerk nicht vorhanden, ohne dass etwas meldete.
- `docs/recht.md` sagt jetzt, dass die Herkunftstabelle für die Briefmaße nicht gilt: Die
  Nachmessung am PDF kennt den Katalog nicht. Ob das so bleiben soll, ist offen.
