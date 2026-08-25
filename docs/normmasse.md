# Woher die Maße stammen und wie sie geprüft werden

Die Maßtabelle selbst steht in [`skill/references/din5008.md`](../skill/references/din5008.md) —
an einer Stelle, weil sie zugleich die Sollwert-Quelle der Tests ist. Diese Seite beantwortet die
Fragen davor und danach: woher die Werte kommen, wie sie gegengeprüft wurden und wie die Messung
im Einzelnen arbeitet.

## Quellen

- **DIN 5008:2020-03** — Normtext urheberrechtlich geschützt, Bezug über
  [DIN Media](https://www.dinmedia.de); hier weder wiedergegeben noch mitgeliefert
- **DIN 5008 Berichtigung 1:2020-07** — Korrektur zur Ausgabe 2020-03, ebenfalls
  kostenpflichtig. Wer nur die Ausgabe 2020-03 heranzieht, prüft gegen eine
  unvollständige Fassung; beide gehören zum Abgleich.
- [DIN 5008 bei Wikipedia](https://de.wikipedia.org/wiki/DIN_5008)
- [Maßzeichnungen von Onlineprinters](https://www.onlineprinters.de/magazin/din-5008-vorlage/)
- Deutsche Post, *Automationsfähige Briefsendungen* — die frühere Adresse ist seit spätestens
  25.08.2026 nicht mehr erreichbar (HTTP 404)

## Gegenprobe

Die Werte wurden nicht aus einer Vorlage übernommen, sondern an einem gerenderten PDF gemessen
(Typst 0.15, PyMuPDF) und anschließend gegen die Maßzeichnungen gehalten. Sie stimmen überein;
der Betreff steht in der Form-B-Zeichnung exakt bei 98,46 mm.

In der Form-A-Zeichnung steht der Betreff bei 103,46 mm statt bei 80,46 mm. Das ist kein
Widerspruch, sondern die Regel selbst: Der dort gezeichnete Informationsblock ist 63 mm hoch, und
der Betreff folgt zwei Leerzeilen unter dem **tiefer reichenden** von Anschriftfeld und
Informationsblock. Genau deshalb rechnet der Renderer die Position, statt sie zu setzen.

**Die verbreitete Word-Vorlage zu diesen Zeichnungen ist nicht normgerecht.** Nachgemessen nach
dem Rendern: Falz- und Lochmarken absolut verankert bei 84,0 / 144,0 / 185,0 mm statt bei
87 / 148,5 / 192 mm, die Rücksendeangabe bei 36,9 mm statt in der Zone 27–32 mm, der
Informationsblock bei x = 130 mm statt 125 mm. Die Marken sind absolut positioniert, der Fehler
ist also unabhängig vom Programm, mit dem die Datei geöffnet wird. Wer damit vergleicht,
vergleicht mit einem Fehler.

## Wie gemessen wird

[`skill/scripts/geometrie.py`](../skill/scripts/geometrie.py) öffnet das erzeugte PDF und
vermisst es: `get_drawings()` liefert die Falz- und Lochmarken als waagerechte Striche im
Heftrand, `get_text("dict")` die Textkästen mit Position, Größe und Schriftschnitt. Verglichen
wird gegen die Tabelle, mit benannten Toleranzen.

Zwei Dinge sind dabei nicht offensichtlich und haben je einen Fehlversuch gekostet:

**Gemessen wird die Glyph-Box, gesetzt wird die Zeilenoberkante.** Die Glyph-Box beginnt beim
Ascender und liegt deshalb systematisch höher — und zwar je nach Schrift unterschiedlich weit:
0,25 em bei Libertinus Serif, 0,34 em bei Source Sans 3. Eine feste Toleranz in Millimetern
erzeugt damit entweder Fehlalarme oder wird bei kleiner Schrift zu grob. Die Grenzen sind deshalb
an die Schriftgröße gebunden, und die tragenden Prüfungen messen **Abstände statt
Absolutpositionen** — darin hebt sich der Versatz heraus.

**Der Zeilenkasten ist fest in em gesetzt**, nicht nach Schriftmetrik: `top-edge: 0.75em`,
`bottom-edge: -0.25em`, Durchschuss 1 pt. Ohne das hängt der Zeilenabstand am Ascender der
jeweiligen Schrift und das 12-pt-Raster der Norm geht nicht auf — gemessen wichen Libertinus
Serif und Source Sans 3 um 1,7 mm voneinander ab, was zwischen Betreff und Anrede aus zwei
Leerzeilen eine halbe zu wenig machte.

## Warum die Prüfung Gegenproben hat

Ein Prüfmittel, das nie rot werden kann, ist kein Nachweis.
[`tests/test_gegenbeweis.py`](../tests/test_gegenbeweis.py) verschiebt deshalb für jede tragende
Prüfung das Layout an genau einer Stelle — Falzmarke, Lochmarke, Anschriftfeld, Betreff,
Informationsblock, unterer Rand — und verlangt, dass die zugehörige Prüfung anschlägt. Dazu
kommt eine Kontrollprobe ohne Sabotage, die grün bleiben muss; ohne sie würde der Test nur
belegen, dass eine Kopie des Layouts anders misst als das Original.
