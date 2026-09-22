# Offene Quellenprüfungen — 27 ungeprüfte Quelle-Regel-Paare

<!-- Erzeugt von scripts/offene_paare.py — nicht von Hand ändern.
     Reihenfolge und Erledigt-Abschnitt stehen als REIHENFOLGE bzw. ERLEDIGT dort. -->

Erhoben aus `skill/falzmarke/regeln/din5008.yaml`. Begonnen wurde mit 44 Paaren.

Ein *Paar* ist eine Regel und eine Quelle, die sie nennt. Geprüft heißt: Jemand hat in der
Quelle nachgesehen und das Ergebnis in `belegt_durch:` eingetragen — eine Fundstelle oder
`SCHWEIGT` mit Begründung.

## Warum das dringlicher ist, als es klingt

Ein ungeprüftes Paar wird **mitgezählt**: `unabhaengige_belege()` nimmt jede Quelle mit
`zaehlt: voll`, solange sie nicht ausdrücklich als schweigend vermerkt ist. Nachlesen kann die
Lage deshalb nur bestätigen oder verschlechtern — aufwerten kann es keine Regel.

Das ist keine Theorie. Bei `onlineprinters` wurden am 27.08.2026 zehn Paare nachgelesen, alle
zehn schwiegen, und drei Regeln fielen von Fehler auf Warnung
([Befund](quellenpruefung-onlineprinters-2026-08-27.md)).

Derzeit hängen **10 Regeln mit Wirkung `fehler`** an mindestens einem ungeprüften
Paar; schwiegen alle ungeprüften Quellen, verlören **11 Regeln** ihre Stufe. Das ist der
ungünstigste Fall, nicht der erwartete — dass eine bemaßte Zeichnung zum Seitenformat schweigt,
ist unwahrscheinlich. Die Zahl sagt, wie viel auf ungeprüftem Grund steht.

## Erledigt

**`massskizze_b` — alle zwölf Paare, am 22.09.2026.** Die Zeichnung wurde gerendert und abgelesen; sie führt keine Textelemente, nur Pfade. Elf Paare tragen, eines schweigt: `text.vermerke_max_3` — die Zone ist mit 17,7 mm bemaßt, eine Zeilenzahl nennt sie nicht. Zwei Belege tragen mit benannter Lücke: `geometrie.form_b.zonen` (die Zeichnung zeigt 17,7 mm als **eine** Zone, die Aufteilung 5 + 12,7 nicht) und `text.folgeseiten` (Seitenzahl ausdrücklich, zur empfohlenen Kopfzeile nichts).

**`wikipedia` — alle fünf Paare, am 22.09.2026.** Über die API im Volltext geholt (13 020 Zeichen). Alle fünf tragen, keines schweigt. Drei wörtlich: Seitenformat („A4 (210 mm × 297 mm)“), Abkürzungen („z. B.“ samt geschütztem Leerzeichen) und Datum (beide Formen). Zwei mit Lücke: `geometrie.seitenraender` (nur der linke Rand, 2,5 cm Fluchtlinie) und `geometrie.schriftgroessen` (nur die 8 Punkt, und die nur für die Rücksendeangabe).

## Reihenfolge

Sortiert nach Wirkung je Aufwand, nicht nach Stückzahl. Die Spalte „Folge" ist regelbezogen:
Sie gilt, wenn **alle** ungeprüften Quellen dieser Regel schweigen, nicht nur die der Portion.

| # | Quelle | Paare | trägt Gruppe? | Fehler-Regeln | Warum hier |
|---|---|---|---|---|---|
| 1 | `onlineprinters` | 10 | ja | 8 | Gleiche Gruppe wie die bereits geprüfte `massskizze_b`, bestätigt also keine zweite. Zehn Paare derselben Quelle schwiegen schon — hier ist mit Schweigen zu rechnen, und genau das ist der Grund, es zu wissen. |
| 2 | `letter_pro` | 15 | **nein** | 10 | `zaehlt: einzeln` — hebt keine Regel auf „mehrfach bestätigt“. Hält aber mehrere Warnungen allein am Leben und ist lokal vendort unter `skill/falzmarke/typst/vendor/`, also die billigste Arbeit der Liste. |
| 3 | `koma_script` | 1 | **nein** | 0 | Siehe oben — dieselbe Regel, derselbe Durchgang. |
| 3 | `massskizze_a` | 1 | ja | 0 | Zusammen mit `koma_script` ein Durchgang: beide betreffen nur `geometrie.form_a.masse`, die schwächste Stelle der Quellenlage. |

## 1. `onlineprinters` — 10 Paare

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
| `geometrie.infoblock_mindesthoehe` | Warnung | Informationsblock mindestens 40 mm hoch | **verliert jeden Beleg** |
| `geometrie.markenlaenge` | Warnung | Marken 2,5 bis 5 mm lang, im Heftrand bis 20 mm von links | **verliert jeden Beleg** |

## 2. `letter_pro` — 15 Paare

typst-letter-pro v3.0.0
`https://github.com/Sematre/typst-letter-pro`
Zählstufe `einzeln`, Gruppe `letter_pro`.

> Diese Quelle zählt `einzeln` und trägt keine Belegsgruppe. Die Spalte „Folge"
> rechnet die **übrigen** ungeprüften Quellen derselben Regel mit — ein Schweigen
> ausgerechnet hier fällt keine dieser Regeln.

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
| `geometrie.seitenformat` | **Fehler** | A4, 210 × 297 mm | bleibt |
| `geometrie.seitenraender` | **Fehler** | Rand links 25 mm, rechts 20 mm, Textbreite 165 mm | bleibt |
| `geometrie.form_a.masse` | Warnung | Form A — Briefkopf 27 mm, Anschriftfeld ab 27 mm, Falzmarken 87 / 192 mm | bleibt |
| `schreibweise.abkuerzungen` | Warnung | Abkürzungen mit geschütztem Leerzeichen: z. B., u. a. | bleibt |
| `schreibweise.datum` | Warnung | Datum als „25. August 2026“ oder „2026-08-25“ | bleibt |
| `text.anrede_komma` | Warnung | Anrede endet mit Komma, der Text darunter beginnt klein | unberührt |
| `text.vermerke_max_3` | Warnung | Zusatz- und Vermerkzone fasst bis zu 3 Zeilen | **verliert jeden Beleg** |

## 3. `koma_script` — 1 Paar

KOMA-Script, DIN5008A.lco (TeX Live)
`https://ctan.org/pkg/koma-script`
Zählstufe `einzeln`, Gruppe `koma_script`.

> Diese Quelle zählt `einzeln` und trägt keine Belegsgruppe. Die Spalte „Folge"
> rechnet die **übrigen** ungeprüften Quellen derselben Regel mit — ein Schweigen
> ausgerechnet hier fällt keine dieser Regeln.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.form_a.masse` | Warnung | Form A — Briefkopf 27 mm, Anschriftfeld ab 27 mm, Falzmarken 87 / 192 mm | bleibt |

## 3. `massskizze_a` — 1 Paar

Maßzeichnung Form A im Onlineprinters-Magazin
`https://www.onlineprinters.de/magazin/aufbau-geschaeftsbrief-nach-din-5008/`
Zählstufe `voll`, Gruppe `onlineprinters_magazin`.

| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
| `geometrie.form_a.masse` | Warnung | Form A — Briefkopf 27 mm, Anschriftfeld ab 27 mm, Falzmarken 87 / 192 mm | bleibt |

## Wie eine Prüfung abläuft

1. Quelle öffnen, zur Regel nachsehen. Eine Maßzeichnung führt ihre Zahlen oft als Pfade, nicht
   als Text — dann rendern (`rsvg-convert -w 2400 …`) und ablesen, nicht im Quelltext suchen.
2. Ergebnis in `din5008.yaml` unter der Regel eintragen:

   ```yaml
   belegt_durch:
     massskizze_b: "Bemaßt mit 45 mm von der oberen Blattkante …"   # trägt
     wikipedia: "SCHWEIGT — Artikel nennt nur Form B"               # trägt nicht
   ```

   Trägt eine Quelle den Kern, aber nicht jedes Detail, gehört die Lücke in denselben Satz.
3. `python3 -m pytest tests/test_quellenlage.py` — die Schranke `UNGEPRUEFTE_PAARE` darf nur
   sinken und will dann von Hand nachgezogen werden; `SCHWEIGENDE_QUELLEN` ebenso.
4. `python3 scripts/quellenlage.py` erzeugt den Doku-Abschnitt in der Normreferenz neu.
5. Die Zahlen in `docs/recht.md` („Was die Stufen derzeit wert sind") nachziehen — sie werden
   von `tests/test_textkanon.py` gegen die Regeldaten gezählt.
6. `python3 scripts/offene_paare.py` — diese Liste neu erzeugen, die abgearbeitete Quelle aus
   `REIHENFOLGE` nehmen und unter `ERLEDIGT` eintragen.
7. Fällt dabei eine Regel unter ihre Stufe, bricht die Regeldatei ab. Das ist gewollt.
