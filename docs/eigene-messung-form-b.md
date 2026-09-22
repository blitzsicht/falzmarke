# Eigene Messung: Form B am gedruckten Brief

**Status:** Verfahren festgelegt, Messung steht aus · **Angelegt:** 22.09.2026 · **Zu:** [#16](https://github.com/blitzsicht/falzmarke/issues/16)

## Warum es diese Messung gibt

Acht Regeln zur Geometrie von Form B wirken heute als **Fehler** und stützen sich auf drei
Quellen: `massskizze_b`, `onlineprinters` und `letter_pro`. Die ersten beiden sind **dieselbe
Zeichnung** (Gruppe `formb_zeichnung_2013`), die dritte ist die Implementierung, mit der
falzmarke selbst setzt. Nach der Definition in [recht.md](recht.md) — „drei unabhängige Quellen,
oder eine Quelle plus zwei Implementierungen" — trägt keine der acht ihre Stufe.

Der Ausweg ist nicht, die Strenge zu senken, sondern einen Beleg hinzuzufügen, den es bisher
nicht gibt.

## Was diese Messung belegt — und was nicht

**Sie belegt nicht, dass die Norm einen Wert vorschreibt.** Dafür braucht es den Normtext
(#12), und daran ändert kein Lineal etwas.

**Sie belegt, dass der Brief funktioniert:** dass die Anschrift im Fenster eines handelsüblichen
Umschlags vollständig und allein sichtbar ist, dass die Falzmarken den Bogen so teilen, dass er
nach dem Falten hineinpasst, dass die Lochmarke auf der Mitte liegt. Das ist eine
**Funktionsprüfung am realen Gegenstand** — unabhängig von jeder Zeichnung, weil sie nichts
abschreibt, sondern nachmisst.

Genau deshalb ist sie als Quelle etwas wert: Sie kann der Zeichnung widersprechen.

## Was gebraucht wird

- Ein Drucker, der **ohne Skalierung** druckt (im Dialog „Tatsächliche Größe" / „100 %",
  nicht „An Seite anpassen") — das ist die häufigste Fehlerquelle der ganzen Übung
- Ein Lineal oder Messschieber mit Millimeterteilung, besser ein Stahllineal als ein Geodreieck
- Fensterumschläge **DL** (110 × 220 mm) mit Fenster links, möglichst von zwei Herstellern
- Optional ein Locher mit Anschlag

## Vor der ersten Messung: den Druck prüfen

```bash
python3 skill/scripts/falzmarke.py render examples/brief-form-b.md -o /tmp/messbogen.pdf
```

Auf dem Ausdruck zuerst die **Seitenhöhe** messen: von der oberen zur unteren Blattkante müssen
es 297 mm sein, die Breite 210 mm. Weicht das ab, druckt der Drucker skaliert — dann stimmt
keine der Zahlen darunter, und jede weitere Messung wäre wertlos.

## Die acht Messungen

Alle Maße von der **oberen linken Blattecke**, sofern nicht anders angegeben. Notiere, was du
misst, nicht was dort stehen sollte.

| # | Regel | Was gemessen wird | Sollwert |
|---|---|---|---|
| 1 | `geometrie.form_b.briefkopf` | Oberkante Blatt bis Oberkante Rücksendeangabe | 45,0 mm |
| 2 | `geometrie.form_b.anschriftfeld` | Linke Kante Blatt bis Textbeginn der Anschrift | 25,0 mm |
| | | Breite des Anschriftfelds | 85,0 mm |
| | | Höhe des Anschriftfelds (45 bis 90 mm) | 45,0 mm |
| 3 | `geometrie.form_b.zonen` | Rücksendeangabe: 45,0 bis 50,0 mm | 5,0 mm hoch |
| | | Zusatz-/Vermerkzone: 50,0 bis 62,7 mm | 12,7 mm hoch |
| | | Anschriftzone: 62,7 bis 90,0 mm | 27,3 mm hoch |
| 4 | `geometrie.form_b.infoblock` | Linke Kante Blatt bis linke Kante Informationsblock | 125,0 mm |
| | | Breite des Informationsblocks | 75,0 mm |
| | | Oberkante Blatt bis Oberkante Informationsblock | 50,0 mm |
| 5 | `geometrie.form_b.falzmarken` | Oberkante Blatt bis erste Falzmarke | 105,0 mm |
| | | Oberkante Blatt bis zweite Falzmarke | 210,0 mm |
| 6 | `geometrie.lochmarke` | Oberkante Blatt bis Lochmarke | 148,5 mm |
| 7 | `geometrie.grundzeilenhoehe` | Abstand von zehn Zeilen Fließtext, geteilt durch zehn | 4,23 mm |
| 8 | `geometrie.betreffabstand` | Oberkante Blatt bis Oberkante Betreffzeile | 98,46 mm |

**Zu Nummer 7:** Einzelne Zeilenabstände sind mit dem Lineal nicht sinnvoll zu treffen. Miss
über zehn Zeilen (Sollwert 42,3 mm) und teile — so wird aus einem Ablesefehler von 0,5 mm einer
von 0,05 mm.

## Die Funktionsprüfung — der eigentliche Wert

Sie ist wichtiger als jedes Einzelmaß, weil sie etwas prüft, was keine Zeichnung sagt.

1. **Fenstertest.** Brief zweimal falten (an den Falzmarken, unterste Lasche nach hinten), in
   den DL-Umschlag stecken. Im Fenster muss die vollständige Anschrift stehen — und **nichts
   sonst**. Kein Teil des Betreffs, keine Zeile des Informationsblocks, kein Rand einer anderen
   Zone. Mit Umschlägen von zwei Herstellern wiederholen.
2. **Verrutschtest.** Den gefalteten Brief im Umschlag nach oben und unten schieben, so weit es
   geht. Die Anschrift muss in beiden Endlagen lesbar bleiben — sonst sitzt sie zwar rechnerisch
   richtig, aber ohne Spielraum.
3. **Lochtest.** Ungefaltetes Blatt lochen, Locher am oberen Blattrand angeschlagen. Die Löcher
   müssen symmetrisch zur Lochmarke liegen und dürfen keinen Text treffen.

## Wie das Ergebnis eingetragen wird

**Nicht** in die vorhandene Quelle `eigene_messung`. Die heißt „Messung am gerenderten PDF"
und steht zu Recht auf `zaehlt: nie` — ihre eigene Bemerkung sagt warum: *„Ein Sollwert von hier
würde gegen ein PDF geprüft, das dieselbe Quelle erzeugt hat — die Prüfung könnte nicht rot
werden."* Dieselbe Zirkularität hätte eine Druckmessung nicht, aber verwechseln darf man die
beiden nicht.

Es braucht deshalb eine **neue** Quelle in `skill/falzmarke/regeln/quellen.yaml`, etwa
`messung_druck_2026`, mit eigener `gruppe` und `art: eigene_messung`. Erst sie darf `zaehlt: voll`
tragen, und erst dann tragen die acht Regeln ihre Stufe.

Dafür gehört in die Quelle:

- **Datum** der Messung und **wer** gemessen hat
- **Drucker und Papier** (Modell, Grammatur) — eine Messung ohne Gerät ist nicht wiederholbar
- **Die gemessenen Werte selbst**, nicht nur „stimmt": je Zeile der Tabelle oben der Istwert
- **Die Umschlagmarken** aus der Funktionsprüfung
- **Abweichungen**, falls welche auftreten — besonders die. Eine Messung, die nur Bestätigung
  meldet, ist verdächtig

Bei einer Abweichung über 0,5 mm: nicht den Sollwert anpassen, sondern das Issue kommentieren.
Es könnte der Drucker sein, das Papier, oder tatsächlich das Werkzeug.

## Was danach immer noch offen ist

Die Messung macht die acht Regeln belegbar. Sie sagt weiterhin nichts darüber, ob
DIN 5008:2020-03 diese Werte **vorschreibt** — das bleibt #12. Der Unterschied gehört in jede
Formulierung, die aus dieser Messung entsteht: „gemessen am gedruckten Brief", nicht
„normgerecht".
