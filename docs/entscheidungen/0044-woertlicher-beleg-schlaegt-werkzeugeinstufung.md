# 0044 — Was eine geführte Quelle wörtlich sagt, ist keine Werkzeugprüfung

**Datum:** 22.09.2026 · **Status:** angenommen · **Betrifft:** [#344](https://github.com/blitzsicht/falzmarke/issues/344) · **Löst ab:** einen Teilsatz aus [ADR 0042](0042-quellenpruefung-ruht.md)

## Entscheidung

Nennt eine in `quellen.yaml` geführte Quelle eine Regel **in eigener Prosa**, ist die Regel
keine Werkzeugprüfung. Sie trägt `herkunft: einzeln_belegt` (oder höher, wenn genug Quellen
zusammenkommen) — auch dann, wenn ihr Meldetext daraufhin wieder eine Quelle nennen muss.

Der Anlass ist `text.anschrift_ohne_leerzeilen`. Sie stand seit [#31] auf `herkunft: werkzeug`,
weil `onlineprinters` zu ihr schweigt. Der Wikipedia-Artikel trägt beide Hälften der Regel — den
Aufbau des Anschriftfelds („6 Zeilen für die Anschriftzone (AZ)") und das Leerzeilenverbot
(„Leerzeilen innerhalb der Anschrift sind nicht vorgesehen") — in einem Satz. Er war hier nur
nie als Quelle eingetragen.

[#31]: https://github.com/blitzsicht/falzmarke/issues/31

## Warum

**`herkunft: werkzeug` ist eine Behauptung, keine Verlegenheitslösung.** Sie sagt: „keine
Aussage der Norm, sondern eine Prüfung des Werkzeugs". Bei dieser Regel ist das nachweislich
falsch — eine Quelle, die das Repository an fünf anderen Regeln mit `zaehlt: voll` führt, sagt
die Regel wörtlich. Die Einstufung stehen zu lassen hieße, in der Regeldatei etwas zu behaupten,
von dem am selben Ort das Gegenteil belegt ist.

**Für den Nutzer ändert sich nichts.** `einzeln_belegt` steht nicht in `DARF_FEHLER_SEIN`; die
Regel warnt weiter und lässt keinen Lauf scheitern. Was sich ändert, ist die Begründung in der
Meldung: Statt „das Werkzeug hält …" nennt sie wieder die Quelle. Genau das ist der Punkt — die
Stufe soll sagen, worauf die Regel steht.

**Es ist kein Rückbau von [#328].** Dessen Zuschnitt sagt wörtlich: *„Dieser Vorgang stellt nur
um, was durch #31 quellenlos wurde."* Diese Regel war nie quellenlos; die tragende Quelle war nur
nie eingetragen. Korrigiert wird eine Eingangsannahme von #328, nicht dessen Entscheidung.
Nachgemessen am Artikel (22.09.2026): Zu `text.anrede_komma` sagt er ausdrücklich, der
Textinhalt der Anrede sei „hier nicht geregelt"; zu `text.gruss_ohne_komma` nennt er nur
Fluchtlinie und Leerzeilenabstand. **Beide bleiben `werkzeug`** — #328 gilt für zwei von drei
Regeln unverändert weiter.

[#328]: https://github.com/blitzsicht/falzmarke/issues/328

## Was hier abgelöst wird

[ADR 0042](0042-quellenpruefung-ruht.md) sagt unter „Was diese Entscheidung nicht ist"
ausdrücklich: *„Sie stuft **keine Regel** um."* Dieser Teilsatz gilt nicht mehr.

Der Widerspruch ist nur ein scheinbarer, und die Auflösung steht in ADR 0042 selbst: Seine
Begründung ruht darauf, dass **ein ungeprüftes Paar bereits mitgezählt wird** — Nachlesen kann
eine Regel deshalb nur bestätigen oder herabstufen, aufwerten nie. Das gilt für Paare, die
eingetragen **sind**. Eine Quelle, die nie eingetragen war, wurde auch nie mitgezählt; sie ist
der einzige Weg, auf dem eine Regel aufsteigen kann. ADR 0042 hat über das Abarbeiten der Liste
entschieden, nicht über neue Einträge — und hält dazu selbst fest: *„wer eine Quelle neu
einträgt, sagt weiterhin, wo sie die Regel hergibt."*

## Die Grenze: ein Satz, keine Rechnung

Diese Entscheidung gilt für eine Quelle, die die Regel **sagt**. Sie gilt **nicht** für einen
Wert, der sich erst aus zwei anderen Werten derselben Quelle ergibt.

Der Gegenfall lag am selben Tag vor
([#345](https://github.com/blitzsicht/falzmarke/issues/345)): Derselbe Artikel nennt 32 mm
(Form A) und 50 mm (Form B) unter der Blattoberkante. Unsere Werte sind 27 und 45 mm — die
Differenz ist die 5 mm hohe Rücksendezone, und die Zahlen ließen sich also herleiten. Als Beleg
eingetragen werden sie trotzdem nicht: Eine Subtraktion ist keine Nennung, und bei
`geometrie.form_a.masse` hinge daran eine Stufe
([#180](https://github.com/blitzsicht/falzmarke/issues/180)).

## Folgen

- `text.anschrift_ohne_leerzeilen` trägt `herkunft: einzeln_belegt`, `quellen: [wikipedia,
  onlineprinters]` und eine Fundstelle unter `belegt_durch.wikipedia`. `deckel:` entfällt — er
  ist nur für `werkzeug` zulässig.
- **Die Reihenfolge unter `quellen:` ist ab jetzt inhaltlich.** `quellenhinweis()` nennt in der
  Meldung `quellen[0]`. Steht dort eine Quelle, die zur Regel schweigt, nennt die Meldung sie
  trotzdem als Beleg. Deshalb steht `wikipedia` vorn, und `tests/test_quellenlage.py` hält das
  in `test_was_eine_quelle_woertlich_traegt_ist_keine_werkzeugpruefung` fest.

  **Nachtrag 23.09.2026 ([#350](https://github.com/blitzsicht/falzmarke/issues/350)): Dieser
  Punkt gilt nicht mehr.** Er war die Umgehung, nicht die Behebung — und er beschrieb einen
  Zustand, den es schon damals an einer zweiten Stelle gab: Bei `text.vermerke_max_3` stand die
  schweigende Maßzeichnung vorn, und die Meldung nannte sie. `quellenhinweis()` überspringt
  seither die Quellen, zu denen `belegt_durch` `SCHWEIGT` sagt, und nimmt die erste sprechende;
  schweigen alle, nennt die Meldung keine. Die Reihenfolge unter `quellen:` ist damit wieder
  Lesbarkeit, und die Zusicherung im Test ist mit ihrem Grund entfallen. `wikipedia` steht hier
  weiter vorn — das hängt jetzt an nichts mehr.
- Die Meldung sagt wieder „die Norm sieht im Anschriftfeld keine Leerzeilen vor", mit dem
  Zusatz „Quelle: sekundär, einzeln belegt". Gesperrt bleiben „normgerecht", „DIN-konform",
  „normkonform" und „zertifiziert" — daran ändert sich nichts.
- Die Zählung in `docs/recht.md` heißt jetzt „stehen auf `einzeln belegt`" statt „fielen von
  Fehler auf Warnung". Der alte Name stimmte, solange jede solche Regel gefallen war; diese ist
  die erste, die gestiegen ist.
- `UNGEPRUEFTE_PAARE` bleibt **27**. Das neue Paar kam mit Fundstelle und war nie ungeprüft.
