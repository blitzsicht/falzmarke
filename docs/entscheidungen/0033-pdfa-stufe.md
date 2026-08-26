# 0033 — PDF/A-2b bleibt die Vorgabe, A-3b wird wählbar

**Datum:** 26.08.2026 · **Status:** angenommen · **Löst:** [#42](https://github.com/blitzsicht/falzmarke/issues/42)

## Entscheidung

falzmarke liefert weiterhin **PDF/A-2b** aus. **PDF/A-3b** wird zusätzlich wählbar — und nur
dort verwendet, wo eine Datei tatsächlich eingebettet wird.

Der Preis ist benannt und wird nicht kleingeredet: Es gibt damit zwei Konformitätspfade, zwei
Prüfpfade, und die Aussage im README wird zu einer Fallunterscheidung statt zu einem Satz. Das
ist der teuerste der drei Wege. Er ist auch der einzige, der keine der beiden Nutzergruppen
gegen die andere ausspielt.

## Warum

Die Frage aus #42 lautete: Bleibt es bei A-2b, oder wird A-3b das Ziel? Beide reinen Antworten
kosten etwas, das falzmarke nicht aufgeben sollte.

**A-2b hat den breiteren Empfang.** Langzeitarchive und Behörden akzeptieren A-2 uneingeschränkt.
A-3 wird von einzelnen Stellen abgelehnt, und zwar aus einem sachlichen Grund: Darin können
beliebige Dateien stecken, die der Empfänger nicht prüfen kann. Für ein Werkzeug, dessen
häufigster Brief an ein Amt geht, ist das kein Randfall.

**A-3b kann etwas, das A-2b nicht kann.** Erst dort darf ein Brief seine Quelldateien mitführen —
die Rechnung als XML, den Vertrag im Original, nachprüfbar an derselben Datei. Diese Fähigkeit
ersatzlos zu streichen, nur damit ein Satz im README kurz bleibt, wäre die falsche Sparsamkeit.

Die Wahl fällt deshalb nicht zwischen den Formaten, sondern zwischen *einer* Zusage und *einer
zutreffenden* Zusage. Wer nichts einbettet — der Normalfall — bekommt A-2b und die volle
Akzeptanz. Wer einbettet, bekommt A-3b und weiß, dass er damit einen engeren Empfängerkreis hat.

## Was daraus folgt

- **Die heutige Auslieferung ändert sich nicht.** A-2b bleibt Vorgabe, Badge und README bleiben
  vorerst richtig. Diese Entscheidung erzeugt für sich genommen keinen Code.
- **Anlagen bleiben Seiten.** [#1](https://github.com/blitzsicht/falzmarke/issues/1) hängt
  Anlagen als Seiten an und lässt die PDF/A-Kennzeichnung fallen, wenn eine Anlage keine trägt.
  Das ist unter A-2b der richtige Weg und bleibt es. Einbetten ist etwas anderes als Anhängen.
- **Der Hybridbrief bettet unter A-3b ein.** Wer Quelldateien mitführen will, bekommt A-3b —
  ausdrücklich verlangt, nicht als stille Umstellung.
- **Zwei Prüfpfade.** `scripts/pdf_konformitaet.py` liest die Stufe ohnehin aus den Metadaten
  des erzeugten PDFs und prüft gegen das, was die Datei behauptet. Diese Entscheidung ändert
  daran nichts — sie ist der Grund, warum die Prüfung von Anfang an so gebaut wurde.
- **Die README-Aussage wird eine Fallunterscheidung**, sobald A-3b implementiert ist. Solange
  nur A-2b ausgeliefert wird, bleibt der Satz einfach; er wird nicht vorsorglich verkompliziert.

## Was diese Entscheidung nicht ist

Keine Umstellung. Wer heute rendert, bekommt A-2b wie zuvor. Die Umsetzung von A-3b gehört in
ein eigenes Issue und entsteht mit dem Hybridbrief, nicht davor.
