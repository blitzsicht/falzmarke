# Offene Quellenprüfungen — die 44 ungeprüften Quelle-Regel-Paare

Stand: 22.09.2026. Erhoben aus `skill/falzmarke/regeln/din5008.yaml`, nicht abgeschrieben.
Der Abschnitt „Nachrechnen" am Ende sagt, wie man das überprüft.

Ein *Paar* ist eine Regel und eine Quelle, die sie nennt. Geprüft heißt: Jemand hat in der
Quelle nachgesehen und das Ergebnis in `belegt_durch:` eingetragen — eine Fundstelle oder
`SCHWEIGT` mit Begründung. Bei 44 Paaren steht dort nichts.

## Warum das dringlicher ist, als es klingt

Ein ungeprüftes Paar wird heute **mitgezählt**: `unabhaengige_belege()` zählt jede Quelle mit
`zaehlt: voll`, solange sie nicht ausdrücklich als schweigend vermerkt ist. Nachlesen kann die
Lage deshalb nur bestätigen oder verschlechtern — aufwerten kann es keine Regel.

Das ist keine Theorie. Bei `onlineprinters` wurden am 27.08.2026 zehn Paare nachgelesen, alle
zehn schwiegen, und drei Regeln fielen von Fehler auf Warnung
([Befund](quellenpruefung-onlineprinters-2026-08-27.md)).

Gemessen am 22.09.2026 hängen **10 Regeln mit Wirkung `fehler`** an mindestens einem
ungeprüften Paar. Sie dürfen heute einen Lauf scheitern lassen, auf Grund, in den niemand
gesehen hat. Schwiegen alle ungeprüften Quellen, verlören **10 Regeln** ihre Stufe.

Das ist der ungünstigste Fall, nicht der erwartete: Dass eine bemaßte Zeichnung von Form B zum
Seitenformat A4 schweigt, ist unwahrscheinlich. Die Zahl sagt, wie viel auf ungeprüftem Grund
steht — nicht, wie viel einstürzen wird.

## Verhältnis zum Normabgleich (#12)

Der Normabgleich ersetzt `herkunft:` durch Fundstellen der Norm; die Quellenliste entfällt dann
ganz ([Prüfliste](normabgleich-pruefliste.md)). Jede Stunde in diesen Paaren wird dadurch
überflüssig — **aber** #12 hängt an einer selbstgesetzten Schwelle von 100 Sternen (Stand:
1 Stern) und ist auf unabsehbare Zeit blockiert. Bis dahin ist diese Liste der einzige Weg,
die Fehler-Regeln auf geprüften Grund zu stellen.

## Reihenfolge

Sortiert nach Wirkung je Aufwand, nicht nach Stückzahl. Maßgeblich ist, ob eine Quelle
überhaupt eine Belegsgruppe tragen kann (`zaehlt: voll`) und wie viele Fehler-Regeln an ihr
hängen. Die Spalte „Folge" in den Einzeltabellen ist regelbezogen: Sie gilt für den Fall, dass
**alle** ungeprüften Quellen dieser Regel schweigen, nicht nur die der jeweiligen Portion.

| # | Quelle | Paare | trägt Gruppe? | Fehler-Regeln | Warum hier |
|---|---|---|---|---|---|
| 1 | `massskizze_b` | 12 | ja | 10 | Ein Dokument, zwölf Werte, zehn davon unter Fehler-Regeln. Der größte Hebel. |
| 2 | `wikipedia` | 5 | ja | 2 | Eigene Gruppe — bei `geometrie.seitenformat` und `geometrie.seitenraender` die zweite. Fällt sie, fallen beide Regeln. |
| 3 | `onlineprinters` | 10 | ja | 8 | Gleiche Gruppe wie `massskizze_b`, bestätigt also nichts Neues. Zehn Paare derselben Quelle schwiegen bereits. |
| 4 | `letter_pro` | 15 | **nein** | 10 | `zaehlt: einzeln` — bewegt keine Stufe. Dafür lokal vendort und damit die billigste Arbeit. |
| 5 | `massskizze_a` | 1 | ja | 0 | Zusammen mit `koma_script` ein Durchgang: beide betreffen nur `geometrie.form_a.masse`. |
| 5 | `koma_script` | 1 | **nein** | 0 | Siehe oben — dieselbe Regel, derselbe Durchgang. |

## 1. `massskizze_b` — 12 Paare

Maßzeichnung „DIN 5008 Form B“, Wikimedia Commons
`https://commons.wikimedia.org/wiki/File:DIN_5008_Form_B.svg`
Zählstufe `voll`, Gruppe `formb_zeichnung_2013`.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.betreffabstand` | **Fehler** | Betreff zwei Leerzeilen (8,46 mm) unter dem tieferen von Feld und Block | **fällt auf Warnung** |
| `geometrie.form_b.anschriftfeld` | **Fehler** | Anschriftfeld 85 × 45 mm, linke Kante 20 mm, Text ab 25 mm | **fällt auf Warnung** |
| `geometrie.form_b.briefkopf` | **Fehler** | Briefkopfhöhe Form B, 45 mm | **fällt auf Warnung** |
| `geometrie.form_b.falzmarken` | **Fehler** | Falzmarken bei 105 und 210 mm | **fällt auf Warnung** |
| `geometrie.form_b.infoblock` | **Fehler** | Informationsblock x = 125 mm, Breite 75 mm, Oberkante 50 mm | **fällt auf Warnung** |
| `geometrie.form_b.zonen` | **Fehler** | Rücksendeangabe 5 mm, Zusatz-/Vermerkzone 12,7 mm, Anschriftzone 27,3 mm | **fällt auf Warnung** |
| `geometrie.grundzeilenhoehe` | **Fehler** | Grundzeilenhöhe 4,23 mm (12 pt) | **fällt auf Warnung** |
| `geometrie.lochmarke` | **Fehler** | Lochmarke bei 148,5 mm | **fällt auf Warnung** |
| `geometrie.seitenformat` | **Fehler** | A4, 210 × 297 mm | **fällt auf Warnung** |
| `geometrie.seitenraender` | **Fehler** | Rand links 25 mm, rechts 20 mm, Textbreite 165 mm | **fällt auf Warnung** |
| `text.folgeseiten` | Warnung | Folgeseiten tragen die Seitenzahl, Kopfzeile mit Betreffkurzform empfohlen | verliert den letzten Beleg |
| `text.vermerke_max_3` | Warnung | Zusatz- und Vermerkzone fasst bis zu 3 Zeilen | verliert den letzten Beleg |

## 2. `wikipedia` — 5 Paare

DIN 5008 in der deutschsprachigen Wikipedia
`https://de.wikipedia.org/wiki/DIN_5008`
Zählstufe `voll`, Gruppe `wikipedia`.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.seitenformat` | **Fehler** | A4, 210 × 297 mm | **fällt auf Warnung** |
| `geometrie.seitenraender` | **Fehler** | Rand links 25 mm, rechts 20 mm, Textbreite 165 mm | **fällt auf Warnung** |
| `geometrie.schriftgroessen` | Warnung | Fließtext mindestens 10 pt, Anschrift und Informationsblock mindestens 8 pt | verliert den letzten Beleg |
| `schreibweise.abkuerzungen` | Warnung | Abkürzungen mit geschütztem Leerzeichen: z. B., u. a. | verliert den letzten Beleg |
| `schreibweise.datum` | Warnung | Datum als „25. August 2026“ oder „2026-08-25“ | verliert den letzten Beleg |

## 3. `onlineprinters` — 10 Paare

Maßzeichnung Form B im Onlineprinters-Magazin
`https://www.onlineprinters.de/magazin/aufbau-geschaeftsbrief-nach-din-5008/`
Zählstufe `voll`, Gruppe `formb_zeichnung_2013`.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.betreffabstand` | **Fehler** | Betreff zwei Leerzeilen (8,46 mm) unter dem tieferen von Feld und Block | **fällt auf Warnung** |
| `geometrie.form_b.anschriftfeld` | **Fehler** | Anschriftfeld 85 × 45 mm, linke Kante 20 mm, Text ab 25 mm | **fällt auf Warnung** |
| `geometrie.form_b.briefkopf` | **Fehler** | Briefkopfhöhe Form B, 45 mm | **fällt auf Warnung** |
| `geometrie.form_b.falzmarken` | **Fehler** | Falzmarken bei 105 und 210 mm | **fällt auf Warnung** |
| `geometrie.form_b.infoblock` | **Fehler** | Informationsblock x = 125 mm, Breite 75 mm, Oberkante 50 mm | **fällt auf Warnung** |
| `geometrie.form_b.zonen` | **Fehler** | Rücksendeangabe 5 mm, Zusatz-/Vermerkzone 12,7 mm, Anschriftzone 27,3 mm | **fällt auf Warnung** |
| `geometrie.grundzeilenhoehe` | **Fehler** | Grundzeilenhöhe 4,23 mm (12 pt) | **fällt auf Warnung** |
| `geometrie.lochmarke` | **Fehler** | Lochmarke bei 148,5 mm | **fällt auf Warnung** |
| `geometrie.infoblock_mindesthoehe` | Warnung | Informationsblock mindestens 40 mm hoch | verliert den letzten Beleg |
| `geometrie.markenlaenge` | Warnung | Marken 2,5 bis 5 mm lang, im Heftrand bis 20 mm von links | verliert den letzten Beleg |

## 4. `letter_pro` — 15 Paare

typst-letter-pro v3.0.0
`https://github.com/Sematre/typst-letter-pro`
Zählstufe `einzeln`, Gruppe `letter_pro`.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.betreffabstand` | **Fehler** | Betreff zwei Leerzeilen (8,46 mm) unter dem tieferen von Feld und Block | **fällt auf Warnung** |
| `geometrie.form_b.anschriftfeld` | **Fehler** | Anschriftfeld 85 × 45 mm, linke Kante 20 mm, Text ab 25 mm | **fällt auf Warnung** |
| `geometrie.form_b.briefkopf` | **Fehler** | Briefkopfhöhe Form B, 45 mm | **fällt auf Warnung** |
| `geometrie.form_b.falzmarken` | **Fehler** | Falzmarken bei 105 und 210 mm | **fällt auf Warnung** |
| `geometrie.form_b.infoblock` | **Fehler** | Informationsblock x = 125 mm, Breite 75 mm, Oberkante 50 mm | **fällt auf Warnung** |
| `geometrie.form_b.zonen` | **Fehler** | Rücksendeangabe 5 mm, Zusatz-/Vermerkzone 12,7 mm, Anschriftzone 27,3 mm | **fällt auf Warnung** |
| `geometrie.grundzeilenhoehe` | **Fehler** | Grundzeilenhöhe 4,23 mm (12 pt) | **fällt auf Warnung** |
| `geometrie.lochmarke` | **Fehler** | Lochmarke bei 148,5 mm | **fällt auf Warnung** |
| `geometrie.seitenformat` | **Fehler** | A4, 210 × 297 mm | **fällt auf Warnung** |
| `geometrie.seitenraender` | **Fehler** | Rand links 25 mm, rechts 20 mm, Textbreite 165 mm | **fällt auf Warnung** |
| `geometrie.form_a.masse` | Warnung | Form A — Briefkopf 27 mm, Anschriftfeld ab 27 mm, Falzmarken 87 / 192 mm | bleibt |
| `schreibweise.abkuerzungen` | Warnung | Abkürzungen mit geschütztem Leerzeichen: z. B., u. a. | verliert den letzten Beleg |
| `schreibweise.datum` | Warnung | Datum als „25. August 2026“ oder „2026-08-25“ | verliert den letzten Beleg |
| `text.anrede_komma` | Warnung | Anrede endet mit Komma, der Text darunter beginnt klein | bleibt |
| `text.vermerke_max_3` | Warnung | Zusatz- und Vermerkzone fasst bis zu 3 Zeilen | verliert den letzten Beleg |

## 5. `massskizze_a` — 1 Paar

Maßzeichnung Form A im Onlineprinters-Magazin
`https://www.onlineprinters.de/magazin/aufbau-geschaeftsbrief-nach-din-5008/`
Zählstufe `voll`, Gruppe `onlineprinters_magazin`.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.form_a.masse` | Warnung | Form A — Briefkopf 27 mm, Anschriftfeld ab 27 mm, Falzmarken 87 / 192 mm | bleibt |

## 5. `koma_script` — 1 Paar

KOMA-Script, DIN5008A.lco (TeX Live)
`https://ctan.org/pkg/koma-script`
Zählstufe `einzeln`, Gruppe `koma_script`.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.form_a.masse` | Warnung | Form A — Briefkopf 27 mm, Anschriftfeld ab 27 mm, Falzmarken 87 / 192 mm | bleibt |

## Wie eine Prüfung abläuft

1. Quelle öffnen, zur Regel nachsehen.
2. Ergebnis in `din5008.yaml` unter der Regel eintragen:

   ```yaml
   belegt_durch:
     massskizze_b: "Zeichnung, Bemaßung links oben"     # trägt
     wikipedia: "SCHWEIGT — Artikel nennt nur Form B"   # trägt nicht
   ```

3. `python3 -m pytest tests/test_quellenlage.py` — die Schranke `UNGEPRUEFTE_PAARE`
   (`tests/test_quellenlage.py:676`) darf nur sinken. Sinkt sie, will sie von Hand nachgezogen
   werden; der Test sagt das selbst.
4. `python3 scripts/quellenlage.py` erzeugt den Doku-Abschnitt neu.
5. Fällt dabei eine Regel unter ihre Stufe, bricht die Regeldatei ab. Das ist gewollt und der
   eigentliche Zweck der Übung.

Die Zahlen in `docs/recht.md` („Was die Stufen derzeit wert sind") werden von
`tests/test_textkanon.py` nachgezählt und laufen mit — sie sind nach jeder Portion nachzuziehen.

## Nachrechnen

```bash
PYTHONPATH=skill python3 -c "from falzmarke import regeln; \
  p=regeln.ohne_belegpruefung(); print(len(p)); \
  import collections; print(collections.Counter(q for _,q in p).most_common())"
```

Weicht die Zahl von der oben ab, ist dieses Dokument veraltet — es wird nicht automatisch
erzeugt.
