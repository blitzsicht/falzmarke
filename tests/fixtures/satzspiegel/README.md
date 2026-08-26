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

## Was hier fehlt, und warum

Issue #35 nennt acht Faelle. Gemessen sind nur zwei davon heute ausloesbar:

* **Langes Wort ohne Trennmoeglichkeit** und **lange URL** laufen nicht ueber —
  Typst bricht beide um. Nachgemessen mit einem 96 Zeichen langen Wort und einer
  135 Zeichen langen URL: beide bleiben bei exakt 190,00 mm.
* **Ueberschriften, Listen, Zitate, Codebloecke** kann der Dialekt heute nicht.
  Sie kommen mit Issue #26 — und genau deshalb ist diese Pruefung dessen
  Vorbedingung: Wenn die Elemente eingefuehrt werden, steht das Netz schon.

Wer #26 umsetzt, legt die zugehoerigen Faelle hier ab.
