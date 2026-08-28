# Briefe, die absichtlich falsch sind

Diese Briefe gehoeren **nicht** nach `examples/`. Dort wird jeder Brief in CI
gerendert und muss bestehen; ein absichtlich ueberlaufender Brief waere dort ein
roter Lauf ohne Erkenntnis.

Hier sind sie Pruefgegenstand: `tests/test_satzspiegel.py` verlangt, dass die
Satzspiegel-Pruefung an ihnen **anschlaegt**. Wird einer von ihnen gruen, ist
nicht der Brief in Ordnung — dann misst die Pruefung nicht mehr.

| Datei | Was sie ausloest |
|---|---|
| `tabelle-zu-breit.md` | zwoelfspaltige Tabelle, Ueberlauf nach rechts auf Seite 1 |
| `ueberlauf-auf-seite-zwei.md` | dieselbe Tabelle, aber erst auf Seite 2 — der Fall, den vor Issue #35 niemand gefangen hat |
| `ueberschrift-ohne-trennstelle.md` | Ueberschrift aus einem Zeichen ohne Trennstelle, Ueberlauf nach rechts (Dialekt 1.1) |
| `codezeile-zu-lang.md` | wortgetreuer Auszug mit 120 Zeichen in einer Zeile (Dialekt 1.1) |

## Was hier fehlt, und warum

Issue #35 nennt acht Faelle. Drei davon sind heute ausloesbar; die Liste unten
sagt zu jedem uebrigen, warum nicht.

### Praezisiert am 28.08.2026 (Dialekt 1.1)

Hier stand: „Langes Wort ohne Trennmoeglichkeit und lange URL laufen nicht ueber
— Typst bricht beide um." Das galt fuer den Stand, an dem es gemessen wurde, und
es gilt **im Absatz** weiterhin: ein 120 Zeichen langes Wort mitten in einem Satz
wird hart getrennt und bleibt bei 190,00 mm.

**In einer Ueberschrift gilt es nicht.** Dort steht das Wort am Zeilenanfang, es
gibt keinen vorangehenden Umbruchpunkt, und Typst laesst es durchlaufen —
gemessen 359,35 mm. Der Satz war also nicht falsch, sondern zu allgemein: Er
beschrieb ein Verhalten, das an der Stelle im Text haengt, und die Stelle gab es
noch nicht.

Deshalb liegt `ueberschrift-ohne-trennstelle.md` jetzt hier.

### Wo die Grenze liegt (gemessen 28.08.2026)

Ein **wortgetreuer Auszug** wird nicht umbrochen — sonst waere er nicht mehr
wortgetreu. Er laeuft also zwangslaeufig ueber, sobald die Zeile zu lang ist.
Nachgemessen durch Einschachtelung:

| | passt bis | laeuft ueber ab |
|---|---|---|
| Codeblock | 68 Zeichen | 69 |
| Inline-Code | 70 Zeichen | 71 |

Der Codeblock verliert die zwei Zeichen an seinen Einzug. Beide Werte gelten
fuer die Festbreitenschrift, die `falzmarke.typ` waehlt; steht sie auf einem
System nicht bereit, greift die naechste der Liste und der Wert weicht ab.

Eine gewoehnliche Protokollzeile (77 Zeichen mit Zeitstempel und drei
Feldern) liegt knapp darueber — der Fall ist also nicht konstruiert.

### Noch nicht ausloesbar

* **Blockzitate** laufen nicht ueber: Ihr Inhalt ist gewoehnlicher Text und
  wird umbrochen, der Einzug ist fest.
* **Tiefe Aufzaehlungen** laufen nicht ueber: nachgemessen bis Ebene 6, dem
  Hoechstwert in Fassung 1.1 — Typst bricht den eingerueckten Text um.
* **Seitenwechsel im Zitat**, **zu geringer Abstand zur Fusszeile** und
  **verwaiste Ueberschrift am Seitenende** sind Fragen des Umbruchs, nicht der
  Breite. Sie gehoeren zum vierten Teilvorgang von #26 und brauchen eine eigene
  Pruefung — die Randmessung hier faengt sie nicht.
