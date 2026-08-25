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

## Auf hellem und dunklem Grund

Auf Papier steht das Zeichen unverändert.

Auf dunklem Grund ist es **derzeit unbrauchbar**: Die Blattkontur ist Tinte `#121E2F` und
verschwindet auf jedem dunklen Grund. `logo-dark.svg` existiert zwar, ist aber
**byte-identisch mit `logo.svg`** — es gibt faktisch keine dunkle Variante. Wer das Zeichen
auf dunklem Grund braucht, legt es bis dahin auf eine weiße Fläche mit Schutzraum.

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
- Kein Favicon, kein Bildzeichen ohne Wortmarke.
- Die Wortmarke im SVG besteht aus Pfaden einer geometrischen Grotesk, nicht aus Source Sans 3.
  Solange sie Pfad bleibt, ist das folgenlos; neu gesetzt werden darf sie nur in Montserrat
  oder Source Sans 3.
