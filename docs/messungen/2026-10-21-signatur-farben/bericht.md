# Signaturfarben hell und dunkel — Messung vom 21.10.2026

Gemessen mit [`messung.py`](messung.py): Chromium 156 (Playwright, headless), berechnete Farben
aus dem DOM, gewählte Bildquelle aus `currentSrc`. Die volle Tabelle steht unten und wird vom
Skript erzeugt.

**Belege außerhalb dieses Repositorys.** Bilder, Rohwerte (`messwerte.json`), die Kopie der
gesendeten Mail und der Diff zeigen echte Absenderdaten (Namen, Anschriften, USt-IdNr.). Die
gehören nicht in dieses öffentliche Repository (`.gitignore`, erste Zeile). Sie liegen beim
Betreiber im privaten Repository `falzmarke-profile` unter
`messungen/2026-10-21-signatur-farben/`, noch nicht committet. Die Tabelle hier führt deshalb
Rollen und Farben, keine Textauszüge.

## Kurzfassung

- **Was falzmarke erzeugt, trägt in den Lagen 1, 2 und 4 überall außer am Logo.** Die
  mitgebrachte Signatur kommt ohne eigene Schrift- und Grundfarben an (ADR 0034, Nachtrag vom
  15.10.2026); Schrift und Linien bestehen hell und dunkel. In Lage 3 fällt jede geerbte
  Schrift durch, das ist die bekannte Grenze dieses Entwurfs und kein neuer Fehler.
- **Das Blitzsicht-Logo verschwindet auf dunklem Grund, sobald die Mail nicht umschaltet**
  (Lage 3 und 4): Das Dunkelblau macht 77 % der Fläche aus und steht bei 1,03:1, nur der
  orange Blitz bleibt (19 % der Fläche tragen, nötig sind 50 %). Wo die Mail umschaltet
  (Lage 2), greift das `<picture>` der Signatur und zeigt `logo-dark.png`: 100 % tragen.
- **Die Signaturdateien selbst** (der Weg über Thunderbird, `user.js`) fallen schon im
  Hellen durch: Labels und Pflichtangaben `#888888` mit 3,54:1, der Web-Link und der
  Bewertungs-Knopf in Orange mit 2,89:1. Vorschlag als Diff unten, die Dateien sind nicht
  geändert.
- **Thunderbird verwirft beim Senden die Medienabfrage im `<style>`.** In allen drei
  gesendeten Testmails (21.10.2026, 21:00, 21:27, 21:56) steht nur noch
  `[data-ogsc] .fm-r { … }`; der Block `@media (prefers-color-scheme: dark)` fehlt. Die frisch
  erzeugte `.eml` trägt ihn. Für die Farben folgenlos (die Linie `#7e7e7e` trägt auf beiden
  Gründen), aber `verify --email` auf eine gesendete Mail meldet den Block damit als
  verändert. Ob es am Ablegen des Entwurfs oder am Senden liegt: **?** (der Entwurf ist nach
  dem Senden nicht mehr im Postfach).

## Prüflinge und Lagen

| Kennung | Was | Woher |
|---|---|---|
| `Q <name>` | Signaturdatei, unverändert | Profilordner `signatur/<name>.html`, so wie `user.js` sie Thunderbird gibt |
| `F <profil>` | HTML-Teil der `.eml`, die falzmarke erzeugt | `falzmarke email` mit dem echten Profilordner |
| `G blitzsicht` | HTML-Teil der gesendeten Mail „[falzmarke-test] Signatur-Probe drei“ | Gesendete Elemente, nur lesend per IMAP (`BODY.PEEK`); Kopie bei den Belegen |

| Lage | Farbschema | Grund | Was greift |
|---|---|---|---|
| 1 hell | light | `#ffffff` | nur die hellen Werte |
| 2 dunkel, Mail schaltet um | dark | `#1e1e1e` | Medienabfragen, `<picture>`, Schrift ohne Farbe wird hell (wie Apple Mail, Thunderbird) |
| 3 dunkler Grund, Mail bleibt | light | `#1e1e1e` | nichts; Schrift ohne Farbe bleibt schwarz |
| 4 Teilumkehrung, **nachgestellt** | light | `#1e1e1e` | helle Gründe werden dunkel, dunkle Schrift und Linien kontrasterhaltend hell, Bilder bleiben, kein `<picture>`-Wechsel (Gmail-/Outlook-Art; kein Hersteller legt den Algorithmus offen) |

Schwellen: Schrift 4,5:1 (ab 24 px oder 18,66 px fett 3:1), Linie 3:1, Logo: mindestens 50 %
der sichtbaren Bildpunkte mit 3:1 gegen den Grund (`farbe.ANTEIL_MINDEST`, dieselbe Regel wie
`lint`), bei Animationen das schwächste Einzelbild. Emoji werden ebenso gemessen, aber als
Schmuck getrennt gezählt: Daneben steht immer Text, der dasselbe sagt.

**Gegenprobe:** `#777` auf `#888` fällt in allen vier Lagen durch (1,26:1), `#000` auf `#fff`
besteht, eine Linie `#888` auf `#777` fällt durch, ein dunkles Bild auf `#1e1e1e` fällt durch
und besteht auf Weiß. Schlägt eine davon fehl, bricht das Skript mit Exit 1 ab.

## Befunde (nur was durchfällt)

Gesamt: 1.372 Einzelmessungen in 893 Zeilen, davon **224 Zeilen nicht bestanden** (ohne Emoji
und Gegenprobe). Davon entfallen 53 auf geerbte Schrift in Lage 3 bei `F`/`G` (Absicht, siehe
oben), 152 auf die Signaturdateien (`Q`) und 19 auf Logos in `F`/`G`.

### falzmarke-Ausgabe und gesendete Mail (`F`, `G`)

| Prüfling | Lage | Element | Wert | Bewertung |
|---|---|---|---|---|
| F/G blitzsicht, F blitzsicht-erstkontakt | 3, 4 | Logo `logo-light-animated.png` | 19 % tragen; `#181838` 77 % bei 1,03:1 | **offen**, siehe unten |
| F siluri, siluri-joe, siluri-order | 1–4 | Logo | 47–49 % tragen | Messgrenze: Konturlogo (hellgraue Schrift, schwarzer Rand), sieht auf beiden Gründen gleich aus; die Flächenregel trifft es knapp. **?** kein Handlungsbedarf |
| F gottl-gbr | 1 | Bild (Foto im Kreis) | 18 % tragen | Messgrenze: Foto mit Himmel, kein Logo; Flächenregel nicht sinnvoll |
| alle F, G | 3 | Schrift, Links (`#000`, `#0000ee` auf `#1e1e1e`) | 1,26:1 / 1,77:1 | Grenze des Entwurfs (ADR 0034, 15.10.2026): keine Farbe trägt Schrift auf beiden Gründen |
| alle F, G | 1 | Emoji ⭐ 📅 📇 auf Weiß | 0–46 % | Schmuck; der Stern ist gelb auf weiß |

Lage 2 und 4 für Schrift und Linien in `F`/`G`: **alles bestanden**. Die Links der
mitgebrachten Signatur verlieren ihre Farbe und zeigen das Linkblau des Programms (`#0000ee`
hell 9,40:1, `#9e9eff` dunkel 6,98:1).

### Signaturdateien (`Q`, der Weg über Thunderbird `user.js`)

Blitzsicht (`blitzsicht.html`; `blitzsicht-erstkontakt.html` gleich, ohne Bewertungs-Knopf, mit Datenschutz-Zeile):

| Lage | Element | Farbe auf Grund | Wert |
|---|---|---|---|
| 1 | Labels „E-Mail:“, „Web:“, Pflichtangaben, Hinweis | `#888888` auf `#ffffff` | 3,54:1 |
| 1 | Link „blitzsicht.com“ | `#ef7612` auf `#ffffff` | 2,89:1 |
| 1, 2, 3, 4 | Knopf „Auf Google bewerten“ (nur `blitzsicht.html`) | `#ffffff` auf `#ef7612` | 2,89:1 |
| 1 | Akzentlinie | `#ef7612` auf `#ffffff` | 2,89:1 (Schmucklinie, ? ob 1.4.11 greift) |
| 2 | Link „Kontakt speichern (vCard)“ — ohne Klasse `esig-link`, schaltet nicht um | `#1d1e3b` auf `#1e1e1e` | 1,03:1 |
| 2, 3 | Trennlinie rechts vom Logo — ohne Klasse | `#1d1e3b` auf `#1e1e1e` | 1,03:1 |
| 3 | Name, Mail-Link, Firma, Position | `#1d1e3b` / `#333` / `#666` auf `#1e1e1e` | 1,03–2,90:1 |
| 3, 4 | Logo | wie bei `F` | 19 % |

Siluri (`siluri.html` und die fünf Ableitungen aus `varianten.py`, messgleich): Labels und
Pflichtangaben `#888888` 3,54:1 (Lage 1); Web-Link `#e63946` 4,17:1 hell und 4,00:1 auf
dunklem Grund ohne Umschaltung (Lage 1, 3, 4); Bewertungs-Knopf Weiß auf `#e63946` 4,17:1
(Lage 1, 2, 3); vCard-Link und Trennlinie `#1a1a1a` schalten nicht um, 1,04:1 (Lage 2, 3);
Lage 3 wie bei Blitzsicht.

Gottl GbR (`gottl-gbr.html`): Labels und Pflichtangaben `#888888` 3,54:1 (Lage 1); Trennlinie
`#1f2a37` schaltet nicht um, 1,15:1 (Lage 2, 3).

## Offen, mit Entscheidungsbedarf

1. **Blitzsicht-Logo auf dunklem Grund ohne Umschaltung (Lage 3, 4).** Eine helle Variante
   gibt es (`https://blitzsicht.com/email/logo-dark.png`, weiß, HTTP 200), und sie ist schon
   eingebunden: Die Signatur trägt `<picture><source media="(prefers-color-scheme: dark)" …>`,
   falzmarke reicht es durch, und es übersteht das Senden (Prüfling `G`). Gmail und Outlook
   werten das nach allem Bekannten nicht aus (**?** ungemessen, nachgestellt in Lage 4). Einen
   Weg in falzmarke gibt es nicht ohne Bruch einer Regel: Ein zweites `<img>`, das per
   `[data-ogsc]` umschaltet, verletzt `BILDER_MAX = 1`; ein Hintergrundbild ist verboten
   (ADR 0034). **Default: eine Logodatei, die auf beiden Gründen trägt** (z. B. dunkelblaue
   Flügel mit heller Kontur, wie das Siluri-Logo es mit schwarzem Rand macht), als
   `logo-light-animated.png` ersetzen oder unter neuem Namen in der Signatur eintragen. Liefern
   oder freigeben muss das der Betreiber; hier ist nichts erfunden und nichts hochgeladen.
2. **Farben in den Signaturdateien** (Diff unten). Die Dateien gehen auch per `user.js` an
   Thunderbird und stammen aus der `cw-core`-Vorlage; geändert ist hier nichts. Default:
   übernehmen, und dieselbe Änderung in der Vorlage, sonst überschreibt die nächste Erzeugung sie.

## Vorschlag für `signatur/blitzsicht.html`

`vorschlag-signatur-blitzsicht.diff` bei den Belegen. Gemessen mit demselben
Skript gegen eine Kopie des Profilordners: In Lage 1 und 2 bleibt nur die Akzentlinie (Schmuck)
unter der Schwelle, Lage 3 wie gehabt.

| Stelle | alt | neu | hell | dunkel |
|---|---|---|---|---|
| Labels, Pflichtangaben, Hinweis | `#888888` | `#767676` | 4,54:1 | Dunkelregel `#94a3b8` bleibt, 6,50:1 |
| Link „blitzsicht.com“ | `#EF7612` | `#C2560A` | 4,54:1 | Dunkelregel `#93c5fd` bleibt |
| Text im Knopf „Auf Google bewerten“ | `#ffffff` | `#1D1E3B` | 5,59:1 auf `#EF7612` | gleich, der Knopf behält seine Fläche |
| vCard-Link | ohne Klasse | `class="esig-link"` | — | `#93c5fd`, 9,24:1 |
| Trennlinie am Logo | ohne Klasse | `class="esig-divider"` + Dunkelregel `#94a3b8` | — | 6,50:1 |

Für Siluri gilt dasselbe in `siluri.html` (danach `python3 varianten.py`): `#888888` → `#767676`,
`#e63946` → `#d62839` für Link und Knopffläche (4,97:1 auf Weiß, Knopf mit weißer Schrift
4,97:1), vCard-Link und Trennlinie mit Klasse. Für `gottl-gbr.html`: Labels `#767676`,
Trennlinie mit Klasse.

## Bilder

Je Prüfling ein PNG in 390 und 700 px Breite (30 Dateien, bei den Belegen), die vier Lagen
untereinander, Lage 4 im Titel als „nachgestellt“ markiert: `q-*` Signaturdatei, `f-*`
falzmarke-Ausgabe, `g-blitzsicht-*` gesendete Mail. `siluri-bewerbung`, `-buchhaltung`,
`-paypal` sind nur gemessen (messgleich mit `siluri`).

## Grenzen

- Chromium ist keines der Mailprogramme. Lage 2 zeigt, was ein Programm tut, das
  `prefers-color-scheme` und `color-scheme` beachtet; ob Thunderbirds Leseansicht
  `<picture>` umschaltet, ist **nicht gemessen**.
- Lage 4 ist eine Nachbildung. Echte Gmail- und Outlook-Umkehrungen weichen ab.
- Das Linkblau ohne eigene Farbe ist das von Chromium; jedes Programm setzt sein eigenes.

## Messtabelle

<!-- tabelle:anfang -->
_Erzeugt von `messung.py`, nicht von Hand ändern._

Gegenprobe:

- bestätigt: #777 auf #888 fällt in jeder Lage durch
- bestätigt: #000 auf #fff besteht in Lage 1
- bestätigt: Linie #888 auf #777 fällt durch
- bestätigt: dunkles Bild auf #1e1e1e fällt durch
- bestätigt: dunkles Bild auf #ffffff besteht

| Prüfling | Lage | Element | Vorn | Grund | Wert | Schwelle | Ergebnis | Auszug |
|---|---|---|---|---|---|---|---|---|
| Gegenprobe | 1 | Text | #777777 | #888888 | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** | Gegenprobe #777 auf #888 |
| Gegenprobe | 1 | Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden | Kontrolle #000 auf #fff |
| Gegenprobe | 1 | Linie top (div 2px) | #888888 | #777777 | 1,26:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Gegenprobe | 1 | Logo | DxmxAbWJDzpbAAAAAElFTkSuQmCC | #ffffff | 100% tragen | ≥ 50% | bestanden | #202020 100% 16.29:1 |
| Gegenprobe | 2 | Text | #777777 | #888888 | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** | Gegenprobe #777 auf #888 |
| Gegenprobe | 2 | Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden | Kontrolle #000 auf #fff |
| Gegenprobe | 2 | Linie top (div 2px) | #888888 | #777777 | 1,26:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Gegenprobe | 2 | Logo | DxmxAbWJDzpbAAAAAElFTkSuQmCC | #1e1e1e | 0% tragen | ≥ 50% | **nicht bestanden** | #202020 100% 1.02:1 |
| Gegenprobe | 3 | Text | #777777 | #888888 | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** | Gegenprobe #777 auf #888 |
| Gegenprobe | 3 | Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden | Kontrolle #000 auf #fff |
| Gegenprobe | 3 | Linie top (div 2px) | #888888 | #777777 | 1,26:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Gegenprobe | 3 | Logo | DxmxAbWJDzpbAAAAAElFTkSuQmCC | #1e1e1e | 0% tragen | ≥ 50% | **nicht bestanden** | #202020 100% 1.02:1 |
| Gegenprobe | 4 | Text | #858585 | #777777 | 1,21:1 | ≥ 4,5:1 | **nicht bestanden** | Gegenprobe #777 auf #888 |
| Gegenprobe | 4 | Text | #ffffff | #000000 | 21,00:1 | ≥ 4,5:1 | bestanden | Kontrolle #000 auf #fff |
| Gegenprobe | 4 | Linie top (div 2px) | #888888 | #777777 | 1,26:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Gegenprobe | 4 | Logo | DxmxAbWJDzpbAAAAAElFTkSuQmCC | #1e1e1e | 0% tragen | ≥ 50% | **nicht bestanden** | #202020 100% 1.02:1 |
| F blitzsicht | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 1 | Name | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 1 | Position | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 1 | Label | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 1 | Link | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 1 | Firma | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 1 | Pflichtangabe/Hinweis | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 1 | Emoji | (Glyphe) | #ffffff | 32% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📅 |
| F blitzsicht | 1 | Emoji | (Glyphe) | #ffffff | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| F blitzsicht | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| F blitzsicht | 1 | Linie right (td 3px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 1 | Linie top (td 2px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 1 | Logo | logo-light-animated.png | #ffffff | 68% tragen | ≥ 50% | bestanden | #181838 77% 17.12:1, #e87010 11% 3.11:1 |
| F blitzsicht | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 2 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 2 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 2 | Link | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 2 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 2 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 2 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| F blitzsicht | 2 | Emoji | (Glyphe) | #1e1e1e | 79% tragen | ≥ 50% | bestanden | ⭐ |
| F blitzsicht | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| F blitzsicht | 2 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 2 | Linie top (td 2px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 2 | Logo | logo-dark.png | #1e1e1e | 100% tragen | ≥ 50% | bestanden | #f8f8f8 100% 15.70:1 |
| F blitzsicht | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht | 3 | Name | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht | 3 | Position | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht | 3 | Label | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht | 3 | Link | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht | 3 | Firma | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht | 3 | Pflichtangabe/Hinweis | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht | 3 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| F blitzsicht | 3 | Emoji | (Glyphe) | #1e1e1e | 79% tragen | ≥ 50% | bestanden | ⭐ |
| F blitzsicht | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| F blitzsicht | 3 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 3 | Linie top (td 2px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 3 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| F blitzsicht | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 4 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 4 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 4 | Link | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 4 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 4 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht | 4 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| F blitzsicht | 4 | Emoji | (Glyphe) | #1e1e1e | 79% tragen | ≥ 50% | bestanden | ⭐ |
| F blitzsicht | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| F blitzsicht | 4 | Linie right (td 3px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 4 | Linie top (td 2px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht | 4 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| F blitzsicht-erstkontakt | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Name | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Position | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Label | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Link | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Firma | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Pflichtangabe/Hinweis | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Pflichtangabe/Hinweis | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Emoji | (Glyphe) | #ffffff | 32% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📅 |
| F blitzsicht-erstkontakt | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| F blitzsicht-erstkontakt | 1 | Linie right (td 3px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Linie top (td 2px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 1 | Logo | logo-light-animated.png | #ffffff | 68% tragen | ≥ 50% | bestanden | #181838 77% 17.12:1, #e87010 11% 3.11:1 |
| F blitzsicht-erstkontakt | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Link | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Pflichtangabe/Hinweis | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| F blitzsicht-erstkontakt | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| F blitzsicht-erstkontakt | 2 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Linie top (td 2px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 2 | Logo | logo-dark.png | #1e1e1e | 100% tragen | ≥ 50% | bestanden | #f8f8f8 100% 15.70:1 |
| F blitzsicht-erstkontakt | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Name | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Position | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Label | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Link | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Firma | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Pflichtangabe/Hinweis | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Pflichtangabe/Hinweis | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F blitzsicht-erstkontakt | 3 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| F blitzsicht-erstkontakt | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| F blitzsicht-erstkontakt | 3 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 3 | Linie top (td 2px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 3 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| F blitzsicht-erstkontakt | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Link | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Pflichtangabe/Hinweis | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| F blitzsicht-erstkontakt | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| F blitzsicht-erstkontakt | 4 | Linie right (td 3px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Linie top (td 2px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F blitzsicht-erstkontakt | 4 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| F gottl-gbr | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 1 | Name | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 1 | Label | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 1 | Link | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 1 | Firma | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 1 | Pflichtangabe/Hinweis | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 1 | Linie right (td 3px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 1 | Linie top (td 2px) | #8a6d3b | #ffffff | 4,85:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 1 | Logo | gottl-gbr.png | #ffffff | 18% tragen | ≥ 50% | **nicht bestanden** | #b0d0f8 4% 1.59:1, #c0d8f8 3% 1.46:1 |
| F gottl-gbr | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 2 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 2 | Link | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 2 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 2 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 2 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 2 | Linie top (td 2px) | #8a6d3b | #1e1e1e | 3,44:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 2 | Logo | gottl-gbr.png | #1e1e1e | 89% tragen | ≥ 50% | bestanden | #b0d0f8 4% 10.50:1, #c0d8f8 3% 11.45:1 |
| F gottl-gbr | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F gottl-gbr | 3 | Name | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F gottl-gbr | 3 | Label | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F gottl-gbr | 3 | Link | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F gottl-gbr | 3 | Firma | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F gottl-gbr | 3 | Pflichtangabe/Hinweis | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F gottl-gbr | 3 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 3 | Linie top (td 2px) | #8a6d3b | #1e1e1e | 3,44:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 3 | Logo | gottl-gbr.png | #1e1e1e | 89% tragen | ≥ 50% | bestanden | #b0d0f8 4% 10.50:1, #c0d8f8 3% 11.45:1 |
| F gottl-gbr | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 4 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 4 | Link | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 4 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 4 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F gottl-gbr | 4 | Linie right (td 3px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 4 | Linie top (td 2px) | #b38d4c | #1e1e1e | 5,42:1 | ≥ 3,0:1 | bestanden |  |
| F gottl-gbr | 4 | Logo | gottl-gbr.png | #1e1e1e | 89% tragen | ≥ 50% | bestanden | #b0d0f8 4% 10.50:1, #c0d8f8 3% 11.45:1 |
| F johannes-kueche | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-kueche | 1 | Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-kueche | 1 | Linie top (p 1px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F johannes-kueche | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-kueche | 2 | Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-kueche | 2 | Linie top (p 1px) | #696969 | #1e1e1e | 3,04:1 | ≥ 3,0:1 | bestanden |  |
| F johannes-kueche | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F johannes-kueche | 3 | Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F johannes-kueche | 3 | Linie top (p 1px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F johannes-kueche | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-kueche | 4 | Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-kueche | 4 | Linie top (p 1px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F johannes-privat | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-privat | 1 | Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-privat | 1 | Linie top (p 1px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F johannes-privat | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-privat | 2 | Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-privat | 2 | Linie top (p 1px) | #696969 | #1e1e1e | 3,04:1 | ≥ 3,0:1 | bestanden |  |
| F johannes-privat | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F johannes-privat | 3 | Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F johannes-privat | 3 | Linie top (p 1px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F johannes-privat | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-privat | 4 | Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F johannes-privat | 4 | Linie top (p 1px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 1 | Name | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 1 | Position | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 1 | Label | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 1 | Link | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 1 | Firma | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 1 | Pflichtangabe/Hinweis | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 1 | Emoji | (Glyphe) | #ffffff | 35% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📅 |
| F siluri | 1 | Emoji | (Glyphe) | #ffffff | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| F siluri | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| F siluri | 1 | Linie right (td 3px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| F siluri | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 2 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 2 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 2 | Link | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 2 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 2 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 2 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri | 2 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri | 2 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri | 2 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| F siluri | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri | 3 | Name | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri | 3 | Position | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri | 3 | Label | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri | 3 | Link | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri | 3 | Firma | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri | 3 | Pflichtangabe/Hinweis | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri | 3 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri | 3 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri | 3 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri | 3 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| F siluri | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 4 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 4 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 4 | Link | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 4 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 4 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri | 4 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri | 4 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri | 4 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri | 4 | Linie right (td 3px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| F siluri-joe | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 1 | Name | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 1 | Position | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 1 | Label | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 1 | Link | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 1 | Firma | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 1 | Pflichtangabe/Hinweis | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 1 | Emoji | (Glyphe) | #ffffff | 35% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📅 |
| F siluri-joe | 1 | Emoji | (Glyphe) | #ffffff | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| F siluri-joe | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| F siluri-joe | 1 | Linie right (td 3px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| F siluri-joe | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 2 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 2 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 2 | Link | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 2 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 2 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 2 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri-joe | 2 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri-joe | 2 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri-joe | 2 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| F siluri-joe | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-joe | 3 | Name | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-joe | 3 | Position | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-joe | 3 | Label | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-joe | 3 | Link | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-joe | 3 | Firma | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-joe | 3 | Pflichtangabe/Hinweis | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-joe | 3 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri-joe | 3 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri-joe | 3 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri-joe | 3 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| F siluri-joe | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 4 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 4 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 4 | Link | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 4 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 4 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-joe | 4 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri-joe | 4 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri-joe | 4 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri-joe | 4 | Linie right (td 3px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-joe | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| F siluri-order | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 1 | Name | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 1 | Position | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 1 | Label | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 1 | Link | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 1 | Firma | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 1 | Pflichtangabe/Hinweis | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 1 | Emoji | (Glyphe) | #ffffff | 35% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📅 |
| F siluri-order | 1 | Emoji | (Glyphe) | #ffffff | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| F siluri-order | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| F siluri-order | 1 | Linie right (td 3px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| F siluri-order | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 2 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 2 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 2 | Link | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 2 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 2 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 2 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri-order | 2 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri-order | 2 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri-order | 2 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| F siluri-order | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-order | 3 | Name | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-order | 3 | Position | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-order | 3 | Label | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-order | 3 | Link | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-order | 3 | Firma | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-order | 3 | Pflichtangabe/Hinweis | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| F siluri-order | 3 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri-order | 3 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri-order | 3 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri-order | 3 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| F siluri-order | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 4 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 4 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 4 | Link | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 4 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 4 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| F siluri-order | 4 | Emoji | (Glyphe) | #1e1e1e | 87% tragen | ≥ 50% | bestanden | 📅 |
| F siluri-order | 4 | Emoji | (Glyphe) | #1e1e1e | 80% tragen | ≥ 50% | bestanden | ⭐ |
| F siluri-order | 4 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| F siluri-order | 4 | Linie right (td 3px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| F siluri-order | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| G blitzsicht | 1 | Rumpf-Text | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 1 | Name | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 1 | Position | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 1 | Label | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 1 | Link | #0000ee | #ffffff | 9,40:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 1 | Firma | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 1 | Pflichtangabe/Hinweis | #000000 | #ffffff | 21,00:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 1 | Emoji | (Glyphe) | #ffffff | 32% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📅 |
| G blitzsicht | 1 | Emoji | (Glyphe) | #ffffff | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| G blitzsicht | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| G blitzsicht | 1 | Linie right (td 3px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 1 | Linie top (td 2px) | #7e7e7e | #ffffff | 4,06:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 1 | Logo | logo-light-animated.png | #ffffff | 68% tragen | ≥ 50% | bestanden | #181838 77% 17.12:1, #e87010 11% 3.11:1 |
| G blitzsicht | 2 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 2 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 2 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 2 | Link | #9e9eff | #1e1e1e | 6,98:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 2 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 2 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 2 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| G blitzsicht | 2 | Emoji | (Glyphe) | #1e1e1e | 79% tragen | ≥ 50% | bestanden | ⭐ |
| G blitzsicht | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| G blitzsicht | 2 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 2 | Linie top (td 2px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 2 | Logo | logo-dark.png | #1e1e1e | 100% tragen | ≥ 50% | bestanden | #f8f8f8 100% 15.70:1 |
| G blitzsicht | 3 | Rumpf-Text | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| G blitzsicht | 3 | Name | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| G blitzsicht | 3 | Position | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| G blitzsicht | 3 | Label | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| G blitzsicht | 3 | Link | #0000ee | #1e1e1e | 1,77:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| G blitzsicht | 3 | Firma | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| G blitzsicht | 3 | Pflichtangabe/Hinweis | #000000 | #1e1e1e | 1,26:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| G blitzsicht | 3 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| G blitzsicht | 3 | Emoji | (Glyphe) | #1e1e1e | 79% tragen | ≥ 50% | bestanden | ⭐ |
| G blitzsicht | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| G blitzsicht | 3 | Linie right (td 3px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 3 | Linie top (td 2px) | #7e7e7e | #1e1e1e | 4,11:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 3 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| G blitzsicht | 4 | Rumpf-Text | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 4 | Position | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 4 | Label | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 4 | Link | #bdbdff | #1e1e1e | 9,44:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 4 | Firma | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 4 | Pflichtangabe/Hinweis | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| G blitzsicht | 4 | Emoji | (Glyphe) | #1e1e1e | 95% tragen | ≥ 50% | bestanden | 📅 |
| G blitzsicht | 4 | Emoji | (Glyphe) | #1e1e1e | 79% tragen | ≥ 50% | bestanden | ⭐ |
| G blitzsicht | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| G blitzsicht | 4 | Linie right (td 3px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 4 | Linie top (td 2px) | #808080 | #1e1e1e | 4,22:1 | ≥ 3,0:1 | bestanden |  |
| G blitzsicht | 4 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| Q blitzsicht | 1 | Name | #1d1e3b | #ffffff | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 1 | Link | #1d1e3b | #ffffff | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 1 | Link | #ef7612 | #ffffff | 2,89:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 1 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 1 | Link | #ffffff | #ef7612 | 2,89:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 1 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht | 1 | Emoji | (Glyphe) | #ef7612 | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| Q blitzsicht | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q blitzsicht | 1 | Linie right (td 3px) | #1d1e3b | #ffffff | 16,14:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht | 1 | Linie top (td 2px) | #ef7612 | #ffffff | 2,89:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q blitzsicht | 1 | Logo | logo-light-animated.png | #ffffff | 68% tragen | ≥ 50% | bestanden | #181838 77% 17.12:1, #e87010 11% 3.11:1 |
| Q blitzsicht | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 2 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 2 | Link | #ffffff | #ef7612 | 2,89:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 2 | Link | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 2 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht | 2 | Emoji | (Glyphe) | #ef7612 | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| Q blitzsicht | 2 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| Q blitzsicht | 2 | Linie right (td 3px) | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q blitzsicht | 2 | Linie top (td 2px) | #ef7612 | #1e1e1e | 5,77:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht | 2 | Logo | logo-dark.png | #1e1e1e | 100% tragen | ≥ 50% | bestanden | #f8f8f8 100% 15.70:1 |
| Q blitzsicht | 3 | Name | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 3 | Link | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 3 | Link | #ef7612 | #1e1e1e | 5,77:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 3 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 3 | Link | #ffffff | #ef7612 | 2,89:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 3 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht | 3 | Emoji | (Glyphe) | #ef7612 | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| Q blitzsicht | 3 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| Q blitzsicht | 3 | Linie right (td 3px) | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q blitzsicht | 3 | Linie top (td 2px) | #ef7612 | #1e1e1e | 5,77:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht | 3 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| Q blitzsicht | 4 | Name | #fbfcfd | #1e1e1e | 16,23:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Link | #fbfcfd | #1e1e1e | 16,23:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Link | #ef7612 | #1e1e1e | 5,77:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht | 4 | Link | #ffffff | #ed7410 | 2,96:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht | 4 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht | 4 | Emoji | (Glyphe) | #ed7410 | 0% tragen | ≥ 50% | nicht bestanden (Schmuck) | ⭐ |
| Q blitzsicht | 4 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| Q blitzsicht | 4 | Linie right (td 3px) | #fbfcfd | #1e1e1e | 16,23:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht | 4 | Linie top (td 2px) | #ef7612 | #1e1e1e | 5,77:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht | 4 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| Q blitzsicht-erstkontakt | 1 | Name | #1d1e3b | #ffffff | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 1 | Link | #1d1e3b | #ffffff | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 1 | Link | #ef7612 | #ffffff | 2,89:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 1 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 1 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht-erstkontakt | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q blitzsicht-erstkontakt | 1 | Linie right (td 3px) | #1d1e3b | #ffffff | 16,14:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 1 | Linie top (td 2px) | #ef7612 | #ffffff | 2,89:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 1 | Logo | logo-light-animated.png | #ffffff | 68% tragen | ≥ 50% | bestanden | #181838 77% 17.12:1, #e87010 11% 3.11:1 |
| Q blitzsicht-erstkontakt | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Link | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 2 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht-erstkontakt | 2 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| Q blitzsicht-erstkontakt | 2 | Linie right (td 3px) | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 2 | Linie top (td 2px) | #ef7612 | #1e1e1e | 5,77:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 2 | Logo | logo-dark.png | #1e1e1e | 100% tragen | ≥ 50% | bestanden | #f8f8f8 100% 15.70:1 |
| Q blitzsicht-erstkontakt | 3 | Name | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 3 | Link | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 3 | Link | #ef7612 | #1e1e1e | 5,77:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 3 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 3 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht-erstkontakt | 3 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| Q blitzsicht-erstkontakt | 3 | Linie right (td 3px) | #1d1e3b | #1e1e1e | 1,03:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q blitzsicht-erstkontakt | 3 | Linie top (td 2px) | #ef7612 | #1e1e1e | 5,77:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 3 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| Q blitzsicht-erstkontakt | 4 | Name | #fbfcfd | #1e1e1e | 16,23:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Link | #fbfcfd | #1e1e1e | 16,23:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Link | #ef7612 | #1e1e1e | 5,77:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Link | #ffffff | #1d1e3b | 16,14:1 | ≥ 4,5:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Emoji | (Glyphe) | #1d1e3b | 85% tragen | ≥ 50% | bestanden | 📅 |
| Q blitzsicht-erstkontakt | 4 | Emoji | (Glyphe) | #1e1e1e | 69% tragen | ≥ 50% | bestanden | 📇 |
| Q blitzsicht-erstkontakt | 4 | Linie right (td 3px) | #fbfcfd | #1e1e1e | 16,23:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Linie top (td 2px) | #ef7612 | #1e1e1e | 5,77:1 | ≥ 3,0:1 | bestanden |  |
| Q blitzsicht-erstkontakt | 4 | Logo | logo-light-animated.png | #1e1e1e | 19% tragen | ≥ 50% | **nicht bestanden** | #181838 77% 1.03:1, #e87010 11% 5.36:1 |
| Q gottl-gbr | 1 | Name | #1f2a37 | #ffffff | 14,54:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q gottl-gbr | 1 | Link | #1f2a37 | #ffffff | 14,54:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q gottl-gbr | 1 | Linie right (td 3px) | #1f2a37 | #ffffff | 14,54:1 | ≥ 3,0:1 | bestanden |  |
| Q gottl-gbr | 1 | Linie top (td 2px) | #8a6d3b | #ffffff | 4,85:1 | ≥ 3,0:1 | bestanden |  |
| Q gottl-gbr | 1 | Logo | gottl-gbr.png | #ffffff | 18% tragen | ≥ 50% | **nicht bestanden** | #b0d0f8 4% 1.59:1, #c0d8f8 3% 1.46:1 |
| Q gottl-gbr | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 2 | Linie right (td 3px) | #1f2a37 | #1e1e1e | 1,15:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q gottl-gbr | 2 | Linie top (td 2px) | #8a6d3b | #1e1e1e | 3,44:1 | ≥ 3,0:1 | bestanden |  |
| Q gottl-gbr | 2 | Logo | gottl-gbr.png | #1e1e1e | 89% tragen | ≥ 50% | bestanden | #b0d0f8 4% 10.50:1, #c0d8f8 3% 11.45:1 |
| Q gottl-gbr | 3 | Name | #1f2a37 | #1e1e1e | 1,15:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q gottl-gbr | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 3 | Link | #1f2a37 | #1e1e1e | 1,15:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q gottl-gbr | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q gottl-gbr | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 3 | Linie right (td 3px) | #1f2a37 | #1e1e1e | 1,15:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q gottl-gbr | 3 | Linie top (td 2px) | #8a6d3b | #1e1e1e | 3,44:1 | ≥ 3,0:1 | bestanden |  |
| Q gottl-gbr | 3 | Logo | gottl-gbr.png | #1e1e1e | 89% tragen | ≥ 50% | bestanden | #b0d0f8 4% 10.50:1, #c0d8f8 3% 11.45:1 |
| Q gottl-gbr | 4 | Name | #ecf0f4 | #1e1e1e | 14,56:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 4 | Link | #ecf0f4 | #1e1e1e | 14,56:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q gottl-gbr | 4 | Linie right (td 3px) | #ecf0f4 | #1e1e1e | 14,56:1 | ≥ 3,0:1 | bestanden |  |
| Q gottl-gbr | 4 | Linie top (td 2px) | #b38d4c | #1e1e1e | 5,42:1 | ≥ 3,0:1 | bestanden |  |
| Q gottl-gbr | 4 | Logo | gottl-gbr.png | #1e1e1e | 89% tragen | ≥ 50% | bestanden | #b0d0f8 4% 10.50:1, #c0d8f8 3% 11.45:1 |
| Q siluri | 1 | Name | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 1 | Link | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 1 | Link | #e63946 | #ffffff | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 1 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 1 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 1 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri | 1 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q siluri | 1 | Linie right (td 3px) | #1a1a1a | #ffffff | 17,40:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| Q siluri | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 2 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 2 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 2 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 2 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri | 2 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri | 2 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| Q siluri | 3 | Name | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 3 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 3 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 3 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 3 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 3 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri | 3 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri | 3 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Link | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Link | #ffffff | #c61926 | 5,89:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri | 4 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri | 4 | Emoji | (Glyphe) | #c61926 | 59% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri | 4 | Linie right (td 3px) | #ffffff | #1e1e1e | 16,67:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-bewerbung | 1 | Name | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 1 | Link | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 1 | Link | #e63946 | #ffffff | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 1 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 1 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 1 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-bewerbung | 1 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-bewerbung | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q siluri-bewerbung | 1 | Linie right (td 3px) | #1a1a1a | #ffffff | 17,40:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-bewerbung | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-bewerbung | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| Q siluri-bewerbung | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 2 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 2 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-bewerbung | 2 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-bewerbung | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-bewerbung | 2 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-bewerbung | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| Q siluri-bewerbung | 3 | Name | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 3 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 3 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 3 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 3 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 3 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-bewerbung | 3 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-bewerbung | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-bewerbung | 3 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-bewerbung | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-bewerbung | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Link | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-bewerbung | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Link | #ffffff | #c61926 | 5,89:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-bewerbung | 4 | Emoji | (Glyphe) | #c61926 | 59% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-bewerbung | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-bewerbung | 4 | Linie right (td 3px) | #ffffff | #1e1e1e | 16,67:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-bewerbung | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-buchhaltung | 1 | Name | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 1 | Link | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 1 | Link | #e63946 | #ffffff | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 1 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 1 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 1 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-buchhaltung | 1 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-buchhaltung | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q siluri-buchhaltung | 1 | Linie right (td 3px) | #1a1a1a | #ffffff | 17,40:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-buchhaltung | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-buchhaltung | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| Q siluri-buchhaltung | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 2 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 2 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-buchhaltung | 2 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-buchhaltung | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-buchhaltung | 2 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-buchhaltung | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| Q siluri-buchhaltung | 3 | Name | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 3 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 3 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 3 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 3 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 3 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-buchhaltung | 3 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-buchhaltung | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-buchhaltung | 3 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-buchhaltung | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-buchhaltung | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Link | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-buchhaltung | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Link | #ffffff | #c61926 | 5,89:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-buchhaltung | 4 | Emoji | (Glyphe) | #c61926 | 59% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-buchhaltung | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-buchhaltung | 4 | Linie right (td 3px) | #ffffff | #1e1e1e | 16,67:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-buchhaltung | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-joe | 1 | Name | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 1 | Link | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 1 | Link | #e63946 | #ffffff | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 1 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 1 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 1 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-joe | 1 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-joe | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q siluri-joe | 1 | Linie right (td 3px) | #1a1a1a | #ffffff | 17,40:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-joe | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-joe | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| Q siluri-joe | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 2 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 2 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 2 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 2 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-joe | 2 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-joe | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-joe | 2 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-joe | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-joe | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| Q siluri-joe | 3 | Name | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 3 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 3 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 3 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 3 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 3 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-joe | 3 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-joe | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-joe | 3 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-joe | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-joe | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-joe | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Link | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-joe | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Link | #ffffff | #c61926 | 5,89:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-joe | 4 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-joe | 4 | Emoji | (Glyphe) | #c61926 | 59% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-joe | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-joe | 4 | Linie right (td 3px) | #ffffff | #1e1e1e | 16,67:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-joe | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-joe | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-order | 1 | Name | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 1 | Link | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 1 | Link | #e63946 | #ffffff | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 1 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 1 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 1 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-order | 1 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-order | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q siluri-order | 1 | Linie right (td 3px) | #1a1a1a | #ffffff | 17,40:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-order | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-order | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| Q siluri-order | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 2 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 2 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 2 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 2 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-order | 2 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-order | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-order | 2 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-order | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-order | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| Q siluri-order | 3 | Name | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 3 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 3 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 3 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 3 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 3 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-order | 3 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-order | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-order | 3 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-order | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-order | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-order | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Link | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-order | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Link | #ffffff | #c61926 | 5,89:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-order | 4 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-order | 4 | Emoji | (Glyphe) | #c61926 | 59% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-order | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-order | 4 | Linie right (td 3px) | #ffffff | #1e1e1e | 16,67:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-order | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-order | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-paypal | 1 | Name | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 1 | Position | #666666 | #ffffff | 5,74:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 1 | Label | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 1 | Link | #1a1a1a | #ffffff | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 1 | Link | #e63946 | #ffffff | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 1 | Firma | #333333 | #ffffff | 12,63:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 1 | Pflichtangabe/Hinweis | #888888 | #ffffff | 3,54:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 1 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 1 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 1 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-paypal | 1 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-paypal | 1 | Emoji | (Glyphe) | #ffffff | 46% tragen | ≥ 50% | nicht bestanden (Schmuck) | 📇 |
| Q siluri-paypal | 1 | Linie right (td 3px) | #1a1a1a | #ffffff | 17,40:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-paypal | 1 | Linie top (td 2px) | #e63946 | #ffffff | 4,17:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-paypal | 1 | Logo | logo-light-animated.png | #ffffff | 49% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 20.03:1, #e8e8f0 42% 1.22:1 |
| Q siluri-paypal | 2 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 2 | Position | #cbd5e1 | #1e1e1e | 11,23:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 2 | Label | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 2 | Link | #93c5fd | #1e1e1e | 9,24:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 2 | Firma | #f1f5f9 | #1e1e1e | 15,22:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 2 | Pflichtangabe/Hinweis | #94a3b8 | #1e1e1e | 6,50:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 2 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 2 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 2 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 2 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-paypal | 2 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-paypal | 2 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-paypal | 2 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-paypal | 2 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-paypal | 2 | Logo | logo-dark.png | #1e1e1e | 47% tragen | ≥ 50% | **nicht bestanden** | #080808 51% 1.20:1, #e8e8f0 44% 13.68:1 |
| Q siluri-paypal | 3 | Name | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 3 | Position | #666666 | #1e1e1e | 2,90:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 3 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 3 | Link | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 3 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 3 | Firma | #333333 | #1e1e1e | 1,32:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 3 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 3 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 3 | Link | #ffffff | #e63946 | 4,17:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 3 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-paypal | 3 | Emoji | (Glyphe) | #e63946 | 53% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-paypal | 3 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-paypal | 3 | Linie right (td 3px) | #1a1a1a | #1e1e1e | 1,04:1 | ≥ 3,0:1 | **nicht bestanden** |  |
| Q siluri-paypal | 3 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-paypal | 3 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
| Q siluri-paypal | 4 | Name | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Position | #989898 | #1e1e1e | 5,78:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Label | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Link | #ffffff | #1e1e1e | 16,67:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Link | #e63946 | #1e1e1e | 4,00:1 | ≥ 4,5:1 | **nicht bestanden** |  |
| Q siluri-paypal | 4 | Firma | #e1e1e1 | #1e1e1e | 12,75:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Pflichtangabe/Hinweis | #888888 | #1e1e1e | 4,70:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Link | #ffffff | #1a1a1a | 17,40:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Link | #ffffff | #c61926 | 5,89:1 | ≥ 4,5:1 | bestanden |  |
| Q siluri-paypal | 4 | Emoji | (Glyphe) | #1a1a1a | 97% tragen | ≥ 50% | bestanden | 📅 |
| Q siluri-paypal | 4 | Emoji | (Glyphe) | #c61926 | 59% tragen | ≥ 50% | bestanden | ⭐ |
| Q siluri-paypal | 4 | Emoji | (Glyphe) | #1e1e1e | 67% tragen | ≥ 50% | bestanden | 📇 |
| Q siluri-paypal | 4 | Linie right (td 3px) | #ffffff | #1e1e1e | 16,67:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-paypal | 4 | Linie top (td 2px) | #e63946 | #1e1e1e | 4,00:1 | ≥ 3,0:1 | bestanden |  |
| Q siluri-paypal | 4 | Logo | logo-light-animated.png | #1e1e1e | 48% tragen | ≥ 50% | **nicht bestanden** | #080808 48% 1.20:1, #e8e8f0 42% 13.68:1 |
<!-- tabelle:ende -->
