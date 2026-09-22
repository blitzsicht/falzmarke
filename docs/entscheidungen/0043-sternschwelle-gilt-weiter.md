# 0043 — Die Sternschwelle für den Normabgleich gilt weiter

**Datum:** 22.09.2026 · **Status:** angenommen · **Löst ab:** einen Teilsatz aus [ADR 0032](0032-verbreitung-vor-normabgleich.md)

## Entscheidung

Der Normabgleich ([#12](https://github.com/blitzsicht/falzmarke/issues/12)) bleibt an die
selbstgesetzte Schwelle von **100 Sternen** gebunden. ADR 0032 wird in genau einem Punkt
abgelöst: in ihrer Folgezeile *„Die 100-Sterne-Bedingung an #12 entfällt."*

Alles andere aus ADR 0032 bleibt in Kraft — vor allem ihre eigentliche Entscheidung, dass
falzmarke verbreitet werden darf, bevor der Abgleich vorliegt.

## Warum diese ADR überhaupt geschrieben wird

Nicht, weil sich etwas ändert, sondern weil etwas **still** geändert worden war. Der Vorgang #12
trägt seit dem 20.09.2026 einen Abschnitt „Stand der Schwelle" mit dem Satz *„Die Schwelle
bleibt"*. Das ist das Gegenteil dessen, was ADR 0032 unter „Folgen" festhält, und es stand in
keiner Entscheidung.

Das [README der Entscheidungen](README.md) verlangt genau das Gegenteil davon: „Eine Entscheidung
wird nicht überschrieben — sie wird von einer späteren abgelöst, und beide bleiben lesbar."
Solange die Ablösung fehlt, widersprechen sich zwei Stellen des Projekts, und wer nur eine liest,
liest etwas Falsches. Aufgefallen beim Schreiben von [ADR 0042](0042-quellenpruefung-ruht.md).

## Warum die Schwelle bleibt

Die Begründung steht in #12 und wird hier nur festgehalten: Der Normtext kostet Geld — das
Praxispaket DIN 5008:2020-03 liegt bei 58 € —, und dieser Einsatz lohnt sich erst, wenn das
Werkzeug tatsächlich benutzt wird. Eine Norm zu kaufen, um ein Werkzeug abzusichern, das niemand
verwendet, ist die falsche Reihenfolge.

ADR 0032 hatte die Schwelle aus einem anderen Grund gestrichen: Sie war damals Teil eines
Kreislaufs — der Meilenstein „Vor Verbreitung" sperrte die Bewerbung bis zum Normabgleich, der
Normabgleich wartete auf Sterne, Sterne entstehen durch Verbreitung. **Dieser Kreislauf ist
aufgelöst**, und zwar durch den anderen Teil von ADR 0032: Die Verbreitung ist frei, sie hängt
nicht mehr am Abgleich. Damit ist die Schwelle keine Sperre mehr, sondern nur noch eine
Kostenentscheidung — und als solche darf sie stehen bleiben.

## Was das offen lässt

Die Henne-Ei-Lage ist damit nicht verschwunden, sie ist nur entschärft. Stand **22.09.2026:
1 Stern**, Repository angelegt am 25.08.2026. Bei diesem Tempo ist 100 keine Schwelle, die man
in Monaten erreicht.

Das hat eine Folge, die benannt gehört, statt sie zu verschweigen: **Der Meilenstein „Vor
Verbreitung" ist auf absehbare Zeit nicht abschließbar.** Offen sind dort #12 und
[#16](https://github.com/blitzsicht/falzmarke/issues/16) (Quellenlage: vendorte Implementierung
zählt als unabhängiger Beleg); #16 wartet auf eine Handmessung, #12 auf den gekauften Normtext.
Ein Meilenstein, der als aktiv geführt wird und es nicht ist, verzerrt jede Planung, die ihn
ansieht.

Das Repository hat für diesen Fall bereits einen Meilenstein **„Geparkt"** (derzeit #10 und #2).
Dorthin gehören beide — als eigener Schritt, nicht als Nebenwirkung dieser Entscheidung.

## Was diese Entscheidung nicht ist

- Sie nimmt **nicht** zurück, dass verbreitet werden darf. Das ist der Kern von ADR 0032 und
  bleibt unberührt.
- Sie sagt **nicht**, dass der Normabgleich unwichtig wäre. Er bleibt der Weg, auf dem die
  Quellenlage abgelöst wird — siehe ADR 0042.
- Sie legt die Schwelle **nicht** neu fest. 100 bleibt, was gesetzt war. Wer sie senken oder an
  etwas anderes hängen will als an Sterne — etwa an den ersten ernsthaften Einsatz —, trifft
  dafür eine eigene Entscheidung; #12 nennt diesen Weg bereits.
