# 0058 — Die Sperre rechnet ohne die eigene Blindkopie und bricht nach zehn Sekunden ab

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:**
[0055](0055-entwurfsbuch-status-und-sperre.md), [0056](0056-entwurfsbruecke-empfaenger-und-fassung.md)

## Anlass

Zwei Befunde aus dem Review vom 25.10.2026, beide an `befund()` in `background.js`.

**Erstens zählte die eigene Blindkopie mit.** Die Sperre bildete die Empfänger der neuen Mail aus
An, Cc **und** Bcc, `gesendet.py` dagegen aus An und Cc (`mit_bcc=False`). Der Unterschied ist
nicht theoretisch: Vier Profile tragen eine Archivadresse in Bcc. Damit teilte jede gesendete Mail
eine Adresse mit jeder neuen, der Vorfilter über die gemeinsamen Empfänger wurde nie leer, und die
Sperre verglich jede Mail mit allem, was in vierzehn Tagen hinausging. Sie fragt dann bei
„Rechnung" an zwei verschiedene Kunden am selben Tag — und ihr Dialog sagt dabei „Ist das die
Korrektur, dann ‚Trotzdem senden'". Wer dreißig Mal umsonst gefragt wird, klickt beim
einunddreißigsten weg. So geht die echte Dublette durch: nicht weil die Sperre fehlt, sondern weil
ihr niemand mehr zuhört.

**Zweitens fehlte die Frist, die ADR 0055 Punkt 5 zusagt.** Dort steht „Eine Prüfung, die hängt,
darf den Menschen nicht aufhalten." Im Code stand dazu nichts: kein `Promise.race`, kein
Abbruch. Abgesichert waren nur Ausnahmen und eine Stückzahl. Dazu riss eine einzige unlesbare
Mail die ganze Prüfung ab, obwohl der echte Treffer zwei Kandidaten später liegen konnte.

## Entscheidung

1. **Eigene Empfänger ohne Bcc, fremde mit.** Die neue Mail wird über An und Cc gebildet, die
   gesendete über An, Cc und Bcc. Die zweite Hälfte bleibt, weil sonst eine Mail aus dem Blick
   fällt, die nur per Blindkopie ging.
2. **Der Eintrag meldet die Blindkopie weiter.** „Nicht verglichen" heißt nicht „nicht
   aufgeschrieben": `versandVon` schreibt sie nach ADR 0056 ins Tagebuch, nur der Vergleich
   übergeht sie.
3. **Zehn Sekunden, dann hinaus.** `befund()` läuft in einem `Promise.race` gegen eine harte
   Frist. Läuft sie ab, steht `pruefung_fehlgeschlagen` mit dem Grund `frist_abgelaufen` im
   Tagebuch und die Mail geht hinaus — die Richtung, die ADR 0055 Punkt 5 vorgibt.
4. **Je Kandidat ein eigenes `try`.** Eine Mail, die sich nicht vollständig lesen lässt, wird
   übersprungen und gezählt; die Prüfung läuft weiter. Die Zahl geht als `pruefung_teilweise` ins
   Tagebuch, und zwar auf **jedem** Weg hinaus, auch beim Treffer: „gesperrt, aber nicht alles
   gesehen" ist eine andere Aussage als „gesperrt".

### Was hingenommen wird

- **Die Sperre sieht eine Mail nicht, die ausschließlich an die eigene Archivadresse ging.** Mit
  leerem An und Cc hält `befund()` gar nicht erst an. Das ist kein Versand an einen
  Geschäftspartner, also kein Fall, den die Sperre meint.
- **Nach zehn Sekunden wird gesendet, nicht gefragt.** Eine Sperre, die bei einer hängenden
  Prüfung ins Fragen kippt, hält den Menschen auf; eine, die sendet, lässt im schlimmsten Fall
  eine Dublette durch. Der Schaden ist in dieser Richtung kleiner, und er steht im Tagebuch.
- **Die Frist gilt für die ganze Prüfung, nicht je Mail.** Zweitausend Kandidaten in zehn
  Sekunden sind nicht zugesagt; was nicht geprüft wurde, wird nicht als geprüft gemeldet.

## Belege

- Beide Änderungen haben eine Sabotage, die einzeln gefahren wurde und genau einen vorher
  benannten Test rot macht: Die zurückgeholte Bcc in der Empfängerbildung macht
  `test_die_eigene_blindkopie_zaehlt_nicht_als_gemeinsamer_empfaenger` rot und sonst keinen
  (1 failed, 35 passed); das entfernte `mitFrist` lässt den Lauf **ohne jedes Urteil** enden.
- Zur Frist gemessen am 25.10.2026: Ohne `mitFrist` endet der Knoten mit 0 und leerem stdout —
  ein offenes Versprechen hält die Ereignisschleife nicht am Leben. Deshalb prüft die Gegenprobe
  das fehlende Urteil und nicht eine Zeitüberschreitung des Prüfprozesses; mit Frist steht an
  derselben Stelle `{}`.
- Die Attrappe für das Hängen antwortet gar nicht (`query` wartet auf ein Versprechen, das nie
  erfüllt wird); vorher war ein Hängen in der Suite nicht darstellbar, weil alle Attrappen
  synchron antworteten.
