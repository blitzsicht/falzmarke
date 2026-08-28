# Erscheinungsbild

Verbindliche Regeln für Farbe, Schrift und Zeichen. Diese Datei beschreibt den Zustand, der
tatsächlich ausgeliefert wird — Logo, Banner und Vorschaubild richten sich danach, nicht
umgekehrt.

Alle Kontrastwerte sind gemessen (`(L1+0,05)/(L2+0,05)` nach WCAG 2.1), nicht geschätzt.
Nachrechnen: siehe [Kontraste nachmessen](#kontraste-nachmessen).

## Farben

Vier Farben, dazu eine abgedunkelte Textvariante des Grüns.

| Name | Wert | Wofür | auf Papier | auf Tinte |
|---|---|---|---|---|
| **Tinte** | `#121E2F` | Text, Blattkontur des Zeichens, Wortmarke | 16,77 : 1 | — |
| **Papier** | `#FFFFFF` | Grund | — | 16,77 : 1 |
| **Grün** | `#3EB057` | **nur Fläche**: Ecke des Zeichens, Balken, Marker | 2,78 : 1 | 6,03 : 1 |
| **Grün, Text** | `#2F8642` | grüner Text auf hellem Grund | 4,56 : 1 | 3,68 : 1 |
| **Grau** | `#5B6470` | Zweitrangiges: Fußzeilen, Bildunterschriften | 6,00 : 1 | 2,80 : 1 |

### Warum es zwei Grün gibt

`#3EB057` erreicht auf Weiß nur **2,78 : 1** und verfehlt damit WCAG AA (4,5 : 1 für
Fließtext, 3 : 1 für großen Text). Als Fläche ist das gleichgültig — als Text ist es ein
Fehler. Wer grünen Text auf hellem Grund setzt, nimmt `#2F8642`: gleicher Farbton
(133°), gleiche Sättigung, nur abgedunkelt, bis der Wert stimmt.

Auf dunklem Grund ist es umgekehrt: Dort trägt `#3EB057` mit 6,03 : 1 und wird für
Bestätigungszeilen verwendet.

Für ein Werkzeug, das PDF/UA erzeugt und mit „nachgemessen" wirbt, wäre ein Markenton, den
niemand nachgemessen hat, die falsche Pointe.

### Ausdrücklich nicht zur Marke gehören

Kein Verlauf, kein Schatten, kein zweiter Akzent. Farben aus Screenshots fremder Oberflächen
(Terminalgrün, Fehlerrot) sind Inhalt, nicht Marke.

## Schrift

| Rolle | Schrift | Datei |
|---|---|---|
| Kopfzeilen, Bildtitel | **Montserrat ExtraBold** (800) | `docs/marke/fonts/Montserrat-ExtraBold.ttf` |
| Auszeichnung im Bild | **Montserrat SemiBold** (600) | `docs/marke/fonts/Montserrat-SemiBold.ttf` |
| Fließtext, Untertitel | **Source Sans 3** Regular / Semibold | `skill/falzmarke/assets/fonts/` |
| Terminal, Code, Messwerte | Menlo, DejaVu Sans Mono, monospace | — |

Beide Schriften stehen unter der SIL Open Font License. Montserrat liegt bei den
Markendateien, **nicht** bei den Produktschriften: `falzmarke pack` kopiert `skill/`
vollständig ins ausgelieferte `.skill`-Paket, und kein Brief benutzt Montserrat je.

Schreibweise des Namens: `falzmarke`, immer klein, auch am Satzanfang. „Falzmarke" groß nur
als Fachbegriff für die Marke auf dem Blatt.

## Zeichen

Quelle ist [`docs/assets/brand/logo.svg`](../assets/brand/logo.svg), `viewBox="0 0 535.7
429.24"`, daneben die Illustrator-Datei als Master.

Das Zeichen ist ein Blatt in Tinte mit zwei senkrechten Marken am linken Rand, einer
abgeknickten Ecke oben rechts und einer grünen Ecke mit weißem Haken unten rechts. Rechts
daneben die Wortmarke.

- **Schutzraum:** ringsum mindestens die Höhe einer der senkrechten Marken.
- **Mindestgröße:** 24 px für das ganze Zeichen mit Wortmarke. Darunter nur das Blatt ohne
  Schrift.
- **Nie:** verzerren, drehen, umfärben, mit Schlagschatten versehen, das Haken-Grün gegen eine
  andere Farbe tauschen, das Zeichen in einen farbigen Kreis setzen.

### Das Bildzeichen ohne Wortmarke

[`bildzeichen.svg`](../assets/brand/bildzeichen.svg) ist aus `logo.svg` abgeleitet, nicht neu
gezeichnet: Die Gruppe `falzmarke_x5F_font` ist entfernt, sonst nichts geändert. Die `viewBox`
ist der gemessene Inhalt plus 4 % Luft, quadratisch um die Mitte gelegt — gemessen am
gerenderten Bild, nicht aus den Pfaden gerechnet.

Wer es neu ableiten muss: dieselbe Gruppe entfernen, dann die Bounding Box am Rendering
abnehmen. Was **nicht** passieren darf, ist Umfärben, Verzerren oder ein Antasten der grünen
Ecke.

### Zwei Fassungen, und warum

| Größe | Datei | Warum |
|---|---|---|
| ab 32 px | `bildzeichen.svg` | originalgetreu |
| 16–24 px | `bildzeichen-klein.svg` | sonst verschwinden die Marken |

**Der Grund ist gemessen, nicht geschätzt.** Die zwei senkrechten Marken sind 20,4 Einheiten
breit. Umgerechnet auf die Darstellungsgröße:

| | Markenbreite |
|---|---|
| 16 px | **0,70 px** |
| 24 px | 1,06 px |
| 32 px | 1,41 px |

Unter einem Pixel gibt es keinen Strich mehr, nur einen blassen Fleck — und die Marken sind das
Namensgebende an diesem Zeichen. `bildzeichen-klein.svg` legt deshalb eine Kontur von 12
Einheiten in der Blattfarbe auf alle Teile des Blattes: dieselbe Form, mehr Masse. Aus 20,4
werden 32,4 Einheiten, bei 16 px also 1,12 px. Nachgemessen an der fertigen Bitmap: **12
kräftig dunkle Pixel statt 3.**

**Warum 12 und nicht mehr:** Bei 18 läuft die abgeknickte Ecke oben rechts zu — genau das
Detail, das das Zeichen ausmacht. Verglichen wurde bei 16, 24 und 32 px.

**Warum die kleine Fassung nicht überall:** Ab 32 px trägt die Kontur nichts bei und macht die
Ecke nur stumpf. Wer im Zweifel ist, nimmt die originalgetreue Datei.

### Favicon-Satz

Alle Dateien liegen bei den Markendateien und sind aus den beiden SVG abgeleitet:

| Datei | Größen | Quelle |
|---|---|---|
| `favicon.ico` | 16, 32, 48 | 16 aus der kleinen Fassung, 32 und 48 aus der originalgetreuen |
| `apple-touch-icon.png` | 180 | originalgetreu |
| `icon-512.png` | 512 | originalgetreu |
| `bildzeichen.svg` | beliebig | ist selbst das SVG-Favicon |

Das ICO trägt **größenspezifische** Bilder — die 16er-Bitmap ist nicht die herunterskalierte
32er, sonst wäre die kleine Fassung wirkungslos. Wer den Satz neu erzeugt, prüft das nach: Die
16er-Bitmap aus dem ICO muss byteidentisch mit dem Rendering von `bildzeichen-klein.svg` sein
und sich vom Rendering der originalgetreuen Datei unterscheiden. Sind beide gleich, ist etwas
schiefgegangen.

## Auf hellem und dunklem Grund

Auf Papier steht das Zeichen unverändert.

Auf dunklem Grund verschwindet die Blattkontur: Tinte `#121E2F` auf einem dunklen
Tab-Hintergrund ergibt **1,01 : 1**. WCAG 1.4.11 verlangt für grafische Elemente 3,0 : 1 —
übrig bliebe das grüne Dreieck.

**Das Bildzeichen löst das, das volle Zeichen noch nicht.**

`bildzeichen.svg` und `bildzeichen-klein.svg` kehren Tinte zu Papier um, sobald das Farbschema
dunkel ist:

```css
@media (prefers-color-scheme: dark) {
  .st0{fill:#FFFFFF;}      /* Blatt */
  .st-mark{stroke:#FFFFFF;} /* Kontur der kleinen Fassung */
}
```

Beide Farben stehen in der Tabelle oben; es kommt keine dazu. Das grüne Dreieck und der weiße
Haken darin bleiben unverändert — Grün ist Fläche, kein Text, und trägt auf beiden Gründen
(6,00 : 1 auf dunkel, 2,78 : 1 auf hell). Nachgemessen am Rendering: im dunklen Schema bleibt
**kein einziges Tinte-Pixel** übrig, die 170 grünen bleiben. Der Kontrast steigt von 1,01 : 1
auf **16,67 : 1**.

Zwei Grenzen gehören dazu, sonst verspricht die Datei mehr, als sie hält:

- **Nur wo der Browser das SVG nimmt** und die Medienabfrage darin auswertet. Firefox und
  Safari tun das, Chrome nur teilweise.
- **Das ICO kann es grundsätzlich nicht.** Bitmaps tragen keine Medienabfrage; `favicon.ico`
  ist auf hellen Grund gezeichnet.

Beim Schreiben zu beachten: Die helle Grundregel muss **vor** der Medienabfrage stehen. Steht
sie danach, gewinnt sie bei gleicher Spezifität — dann schaltet das Blatt um und die Kontur
nicht.

`logo.svg` mit Wortmarke bleibt davon unberührt: `logo-dark.svg` ist weiterhin
**byte-identisch mit `logo.svg`**, es gibt faktisch keine dunkle Variante des vollen Zeichens.
Wer es auf dunklem Grund braucht, legt es auf eine weiße Fläche mit Schutzraum.

## Wie die Bilder entstehen

Master ist [`quelle/social-preview.html`](quelle/social-preview.html). Daraus:

```bash
bash scripts/marke.sh            # banner.png 2560x1280, social-preview.png 1280x640
bash scripts/marke.sh --verify   # zweimal rendern, Prüfsummen vergleichen
```

Wer die Aussage ändern will, ändert die HTML — nie das PNG.

## Kontraste nachmessen

```bash
python3 - <<'PY'
def lum(h):
    h = h.lstrip("#"); c = [int(h[i:i+2],16)/255 for i in (0,2,4)]
    c = [x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in c]
    return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
def k(a,b):
    l1,l2 = sorted((lum(a),lum(b)), reverse=True); return (l1+0.05)/(l2+0.05)
for name, wert in [("Tinte","#121E2F"),("Gruen","#3EB057"),
                   ("Gruen Text","#2F8642"),("Grau","#5B6470")]:
    print(f"{name:11s} {wert}  auf Papier {k(wert,'#FFFFFF'):5.2f}:1"
          f"  auf Tinte {k(wert,'#121E2F'):5.2f}:1")
PY
```

## Abweichungen vom Auftrag M2

`docs/auftraege/auftrag-marke-falzmarke.md` legt in M2 ein anderes Erscheinungsbild fest:
Tinte `#1A1A1A`, Blattschatten `#E6E6E6`, Akzent `#1F5AA8`, „genau diese vier",
ausschließlich Source Sans 3, und ausdrücklich „kein Häkchen".

Das ausgelieferte Zeichen hält sich daran nicht. Der Nachtrag benennt den Widerspruch (E7)
und verlangt eine Entscheidung, „nicht zwei Wahrheiten". **Die Entscheidung ist zugunsten
des ausgelieferten Zeichens gefallen** — Häkchen, Grün und Montserrat bleiben, und dieses
Dokument ist ab jetzt die Quelle. M2 ist insoweit überholt.

Was davon unberührt bleibt: Der Wunsch aus M2, das Bildzeichen aus derselben Maßtabelle zu
erzeugen wie das Produkt, ist nicht eingelöst. Das Zeichen ist gezeichnet, nicht gerechnet.

## Offen

- `logo-dark.svg` ist eine Kopie von `logo.svg` und trägt auf dunklem Grund nicht.
- Die Wortmarke im SVG besteht aus Pfaden einer geometrischen Grotesk, nicht aus Source Sans 3.
  Solange sie Pfad bleibt, ist das folgenlos; neu gesetzt werden darf sie nur in Montserrat
  oder Source Sans 3.
