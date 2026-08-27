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
(Typst 0.15, pdfplumber) und anschließend gegen die Maßzeichnungen gehalten. Sie stimmen überein;
in der Form-B-Zeichnung liegt der Betreff bei 98,46 mm.

**98,46 mm ist keine feste Betreffposition, sondern ein abgeleiteter Standardfall.** Die Regel
lautet: Der Betreff folgt zwei Leerzeilen unter dem **tiefer reichenden** von Anschriftfeld und
Informationsblock. Bei den Standardhöhen der Form B ergibt das 98,46 mm — bei einem längeren
Informationsblock etwas anderes. Deshalb rechnet der Renderer die Position, statt sie zu setzen,
und deshalb prüft `verify` sie relativ statt absolut. Wer 98,46 mm als Sollwert übernimmt, hat
die Regel durch einen ihrer Werte ersetzt.

Dieselbe Rechnung erklärt die Form-A-Zeichnung, in der der Betreff bei 103,46 mm steht statt bei
80,46 mm: Der dort gezeichnete Informationsblock ist 63 mm hoch und reicht damit tiefer als das
Anschriftfeld.

**Diese Herleitung ist eine Rekonstruktion, keine Fundstelle.** Sie erklärt die Zeichnungen
widerspruchsfrei, aber sie stützt sich auf die Zeichnungen selbst und nicht auf den Normtext. Was
dort steht, ist bis zum [Normabgleich](recht.md#wie-sich-das-ändert) nicht bekannt; sollte die
Norm die Positionen anders herleiten, ändert sich die Begründung — nicht unbedingt die Zahl.

**Die verbreitete Word-Vorlage zu diesen Zeichnungen wich am 25.08.2026 von ihnen ab.**
Nachgemessen nach dem Rendern:

| | Vorlage | Zeichnung |
|---|---|---|
| Falz- und Lochmarken | 84,0 / 144,0 / 185,0 mm | 87 / 148,5 / 192 mm |
| Rücksendeangabe | 36,9 mm | Zone 27–32 mm |
| Informationsblock, x | 130 mm | 125 mm |

Die Marken sind dort absolut positioniert; die Abweichung hängt also nicht am Programm, mit dem
die Datei geöffnet wird. **Wer diese Vorlage als Vergleichsmaßstab nimmt, misst gegen andere
Werte als die, die hier eingehalten werden.**

Nicht behauptet wird, die Vorlage sei „nicht normgerecht". Gemessen wurde gegen die
Maßzeichnungen, nicht gegen den Normtext — und solange der Abgleich mit dem Original aussteht,
sagt falzmarke dieses Wort über niemanden, auch nicht über Fremde. Dass die Messung hier nicht
Schritt für Schritt nachvollziehbar ist, gehört dazugesagt: Sie stammt aus einem einzelnen
Durchgang am genannten Tag; die Vorlage kann sich seitdem geändert haben.

## Wie gemessen wird

[`skill/falzmarke/geometrie.py`](../skill/falzmarke/geometrie.py) öffnet das erzeugte PDF mit
**pdfplumber** (MIT) und vermisst es: `page.lines` und `page.rects` liefern die Falz- und
Lochmarken als kurze Striche im Heftrand — manche Erzeuger legen sie als sehr flache Rechtecke
an, deshalb beide —, `page.extract_words(extra_attrs=["fontname", "size"])` die Wörter mit
Position, Größe und Schriftschnitt. Die Metadaten und die PDF/A-Kennzeichnung liest **pypdf**
(BSD-3). Verglichen wird gegen die Tabelle, mit benannten Toleranzen.

Bis v0.4 lief die Messung über **PyMuPDF**. Das ist AGPL-3.0 oder kommerziell und hätte jede
Firma, die falzmarke einbaut, in die AGPL gezwungen; seitdem hält ein eigener CI-Schritt jeden
Rückweg zu. Der Wechsel war außerdem genauer: pdfplumber liefert die Zeilenoberkante statt der
Ascender-Box und trifft die Sollwerte auf 0,01 mm — Anschrift 62,69 bei Soll 62,70, Betreff 98,45
bei 98,46 —, wo PyMuPDF um 0,5 mm danebenlag.

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
