- **Ein von Thunderbird gespeicherter Entwurf verliert seine Zuordnung nicht mehr.** Die ganze
  Zuordnung zwischen Entwurfsbuch, Postfach und Tagebuch hing an einer Zahl, und die entstand aus
  genau einem Aufruf: Blieb er leer, hing die Versandzeile an keinem Entwurf — kein „Ging an … ·
  Empfänger wie angelegt", kein `BELEGT`, und die Sendesperre erkannte den Entwurf nicht über
  seine Fassung. Jetzt löst das Add-on die UID über **zwei** Wege auf (`messageKey` und die
  Entwurfsadresse des Verfassen-Fensters), holt sie vor dem Senden noch einmal nach, falls sie
  beim Öffnen leer blieb, und schreibt bei jedem Öffnen **beide** Ergebnisse ins Tagebuch samt
  der Angabe, welcher Weg getragen hat (`uid_quelle`) und warum der andere nicht (`uid_grund`).
  Die Fassung, die Thunderbird beim Speichern wegwirft, kommt über die Kette der Speicherungen
  zurück (`fassung_quelle: "kette"`) — ohne sie in die ausgehende Mail zurückzuschreiben, das
  bleibt verboten. Entwurfsbrücke 0.3.7, ADR 0060 (#420).
- **`falzmarke status` meldet einen Tagebuch-Eintrag, der an keinem Entwurf hängt**, statt ihn
  stillschweigend zu übergehen: „1 Tagebuch-Eintrag zu einem Entwurf trägt weder UID noch
  Fassung". Neue Mails und Antworten haben von Natur aus keine UID und zählen nicht mit. Die
  Zahl steht auch in `--json` (#420).
