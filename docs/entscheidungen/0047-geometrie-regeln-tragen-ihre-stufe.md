# 0047 — Die Geometrie-Regeln tragen die Stufe, mit der sie wirken

**Datum:** 25.09.2026 · **Status:** angenommen · **Betrifft:** [#355](https://github.com/blitzsicht/falzmarke/issues/355)

## Entscheidung

Die drei Geometrie-Regeln, die auf `einzeln_belegt` standen und am fertigen PDF trotzdem als
Fehler wirkten, bekommen die Stufe, die zu ihrer Wirkung passt — nicht dadurch, dass die
Nachmessung die Stufe zu lesen lernt, sondern dadurch, dass die Beleglage nachgeholt wird:

| Regel | vorher | jetzt | woraus |
|---|---|---|---|
| `geometrie.infoblock_mindesthoehe` | einzeln belegt, Warnung | **mehrfach bestätigt**, Fehler | `natusch` und `weka_sekretaria`, beide wörtlich „mindestens 40 mm" |
| `geometrie.schriftgroessen` | einzeln belegt, Warnung | **mehrfach bestätigt**, Fehler | 10 pt aus der Onlineprinters-Zeichnung und `manager_institut`, 8 pt aus `wikipedia` und `manager_institut` |
| `geometrie.markenlaenge` | einzeln belegt, Warnung | **geteilt** (siehe unten) | — |

`geometrie.markenlaenge` bündelte zwei Aussagen. Sie ist geteilt:

- **`geometrie.marken_heftrand`** (neu) — „Marken im Heftrand, bis 20 mm von der linken
  Blattkante". Mehrfach bestätigt, Fehler. Das ist die Hälfte, die am PDF gemessen wird:
  `geometrie.py` prüft je Marke „x-Ende ≤ 20 mm".
- **`geometrie.markenlaenge`** — „Marken 2,5 bis 5 mm lang". `herkunft: werkzeug`,
  `wirkung: keine`. Keine Aussage der Norm und ohnehin ungeprüft: Die Nachmessung erkennt Marken
  an ihrer Lage im Heftrand und misst ihre Länge nirgends.

Drei Quellen kommen neu ins Register: `natusch`, `weka_sekretaria`, `manager_institut`.

## Warum nicht anders

Der Vorgang stellte drei Wege zur Wahl. Gewählt wurde (b).

**(a) Die Nachmessung liest die Stufe** — wie `pruefung_eml._wahr` es tut. Der Apparat dafür
steht. Die Folge wäre aber, dass ein Brief mit zu kurzen Falzmarken oder zu niedrigem
Informationsblock durchläuft: Was heute hart hält, hielte nur noch dem Namen nach. Die Maße sind
Maße.

**(c) Die Tabelle nimmt die Ausnahme auf.** Hätte nichts behauptet und nichts geändert — aber
auch nichts verbessert. Die Regeln wären weiter schwächer belegt, als sie wirken.

**(b) Die Regeln steigen.** Der Einwand dagegen war, dass ADR 0042 die Quellenprüfung ruhen
lässt. Er trägt nicht: Was dort ruht, ist das **Abarbeiten der Liste** offener Paare — „nicht
die Sorgfalt bei neuen Einträgen", und als Anlass zur Wiederaufnahme nennt ADR 0042 ausdrücklich,
„wenn eine neue Quelle hinzukommt". Genau das ist hier geschehen.

## Was dabei gemessen wurde

Nachlesen einer schon genannten Quelle kann eine Regel nur bestätigen oder herabstufen — aufwerten
nie. Aufsteigen kann sie allein über ein **neu eingetragenes** Paar, wie
`text.anschrift_ohne_leerzeilen` mit [#344](https://github.com/blitzsicht/falzmarke/issues/344).
Am 25.09.2026 wurden dafür sechs Quellen im Volltext gelesen:

- **`wikipedia`** — trägt keine der drei weiter: nichts zur Höhe des Informationsblocks, nichts
  zur Gestalt der Marken, zu Schriftgrößen nur die bekannten 8 pt der Rücksendeangabe.
- **`federwerk`** — nennt zur Markenlänge „ca. 5 mm", aber in der Word-Anleitung des Autors und
  nicht als Aussage der DIN. Kein Beleg.
- **`onlineprinters`** — die beiden offenen Paare sind nachgelesen (Bild gerendert und
  abgelesen): Die Zeichnung bemaßt weder die Höhe des Informationsblocks noch die Marken. Beide
  schweigen. Dafür trägt ihr Textteil eine Angabe, die vorher niemand ausgewertet hatte:
  „Schriftgröße 10 - 12 pt".
- **`natusch`**, **`weka_sekretaria`**, **`manager_institut`** — neu, mit Fundstelle eingetragen.

Zwei der neuen Quellen sagen **ausdrücklich**, dass die Norm zur Gestalt der Marken nichts
vorgibt („keine Vorgaben"; „Wie die Marken konkret auszusehen haben, dazu macht die DIN 5008
keine Angaben"). Das ist der Grund für die Teilung — und der Beleg dafür, dass die 2,5 mm keine
Normaussage sind: Sie stammen aus der vendorten Layoutbasis, mit der falzmarke selbst setzt
(`typst/vendor/letter-pro-v3.0.0.typ`, `length: 2.5mm`).

## Was das kostet

- **Die Zahl der schweigenden Quelle-Regel-Paare steigt von 11 auf 16.** Fünf davon sind neu
  nachgelesen und schweigen. Das ist kein Verlust, sondern der Preis dafür, hingesehen zu haben.
- **Eine Annahme aus #31 ist gefallen.** Bis heute galt: Wo eine Quelle schweigt, darf die Regel
  nur noch warnen. Das war richtig, solange jede betroffene Regel auf genau dieser einen Quelle
  stand. `geometrie.infoblock_mindesthoehe` und `geometrie.marken_heftrand` sind die ersten, bei
  denen eine Quelle schweigt und die Stufe trotzdem trägt. Der Test dazu führt sie namentlich
  (`TROTZ_SCHWEIGENS_HART` in `tests/test_quellenlage.py`) und verlangt den Nachweis, dass hinter
  ihnen zwei andere Gruppen stehen.
- **Der offene Rest 1 wächst von 3 auf 6 Regeln:** mehrfach bestätigt aus Quellen verschiedener
  Träger, deren Unabhängigkeit niemand geprüft hat. Bei den drei neuen sind es verschiedene
  Betreiber mit verschiedenen Darstellungsformen — nachgesehen hat es niemand. Das steht so auch
  in `docs/recht.md`.
- **Die Regeln sind nach wie vor sekundär belegt.** Der Normabgleich
  ([#12](https://github.com/blitzsicht/falzmarke/issues/12)) ersetzt jede Herkunftsstufe durch
  eine Fundstelle; bis dahin bleibt es dabei, dass niemand den Normtext gesehen hat.

## Folgen

- Keine Geometrie-Regel steht mehr unter der Wirkung, die sie am PDF hat. Bewacht von
  `test_jede_geometrie_regel_darf_fehler_sein` samt Gegenprobe.
- `test_die_nachmessung_laedt_den_regelkatalog_nicht` hält den zweiten Teil der Begründung fest:
  Wird der Katalog dort doch geladen, ist der Abschnitt „Was daraus folgt" in `docs/recht.md` neu
  zu schreiben.
- Am Verhalten des Werkzeugs ändert sich nichts. Derselbe Brief ergibt denselben Bericht — nur
  die Auskunft darüber, worauf die Maße beruhen, stimmt jetzt.
