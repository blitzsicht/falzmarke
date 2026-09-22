# 0045 — Der Meilenstein „Vor Verbreitung" wird geschlossen

**Datum:** 22.09.2026 · **Status:** angenommen · **Löst ab:** einen Teilsatz aus [ADR 0032](0032-verbreitung-vor-normabgleich.md)

## Entscheidung

Der Meilenstein **„Vor Verbreitung"** wird geschlossen und nicht neu gefüllt. Sein Zuschnitt aus
ADR 0032 ist gegenstandslos geworden.

## Warum

ADR 0032 hat dem Meilenstein unter „Folgen" ausdrücklich einen neuen Zweck gegeben:

> Der Meilenstein „Vor Verbreitung" bekommt einen neuen Zuschnitt. Er hieß so, weil er die
> Bewerbung sperrte. Was ihn jetzt füllt, ist Belegarbeit, die vor einer *starken Behauptung*
> stehen muss — nicht vor der Verbreitung.

Diese Belegarbeit gibt es in dieser Form nicht mehr:

- Das Nachlesen der Quelle-Regel-Paare ruht seit [ADR 0042](0042-quellenpruefung-ruht.md).
- Die beiden Vorgänge, die den Meilenstein zuletzt trugen — der Normabgleich
  ([#12](https://github.com/blitzsicht/falzmarke/issues/12)) und die Handmessung
  ([#16](https://github.com/blitzsicht/falzmarke/issues/16)) — liegen in „Geparkt".
- Gemessen am 22.09.2026 über die API: **0 offen, 8 geschlossen.** Der Meilenstein ist leer,
  seit die beiden umgezogen sind.

Ein leerer Meilenstein, der offen steht, liest sich wie ein Rückstand. Er ist keiner.

## Warum nicht umbenennen

Die naheliegende Alternative war, ihn in „Vor starker Behauptung" umzubenennen und #12 und #16
hineinzuziehen. Das wurde verworfen: Beide lägen dann in zwei Meilensteinen, und „Geparkt" sagt
über ihren Zustand mehr als der neue Name. Zwei Listen für dieselben zwei Vorgänge sind eine
Liste zu viel.

## Was diese Entscheidung nicht ist

- Sie hebt die Zurückhaltung im Wortlaut **nicht** auf. Kein „normgerecht", kein „DIN-konform",
  keine Zertifizierung — `tests/test_textkanon.py` hält das fest, und daran ändert ein
  Meilenstein nichts.
- Sie schließt den Normabgleich **nicht** ab. #12 bleibt vorgesehen, mit der Schwelle aus
  [ADR 0043](0043-sternschwelle-gilt-weiter.md).
- Sie erklärt die Belegarbeit **nicht** für erledigt. Was offen ist, steht in
  [`docs/offene-quellenpruefungen.md`](../offene-quellenpruefungen.md) und in
  [`docs/recht.md`](../recht.md) — dort, wo es jemand liest, und nicht in einem Meilenstein,
  den nur sieht, wer im Vorgangssystem danach sucht.

## Folgen

- Der Meilenstein steht auf `closed`. Die acht geschlossenen Vorgänge bleiben ihm zugeordnet;
  er bleibt als Stück Geschichte lesbar.
- Der oben zitierte Teilsatz aus ADR 0032 ist abgelöst. Der Rest von ADR 0032 gilt unverändert
  — insbesondere die Bedingung, dass die Quellenlage überall ausgewiesen bleibt, wo jemand auf
  das Werkzeug trifft.
