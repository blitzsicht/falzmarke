# Datenvertrag: das Frontmatter einer Briefdatei

Eine Briefdatei besteht aus YAML-Frontmatter zwischen zwei `---`-Zeilen und dem Brieftext
darunter.

```yaml
---
profil: example                  # Pflicht. Dateiname (ohne .yaml) aus ~/.config/normbrief/profiles/
form: B                          # A oder B. Ohne Angabe gilt der Wert aus dem Profil
norm: din5008                    # reserviert; derzeit nur din5008
empfaenger:                      # Pflicht. 1 bis 6 Zeilen, keine Leerzeilen
  - Muster GmbH                  # Reihenfolge: Firma, Person, Straße, PLZ Ort, [LAND]
  - Frau Erika Muster
  - Musterstraße 1
  - 12345 Musterstadt
vermerke:                        # optional, höchstens 3 Zeilen
  - Einschreiben mit Rückschein
datum: 2026-08-25                # Pflicht, ISO. Die Ausgabe bestimmt das Profil
betreff: Angebot Nr. 2026-0815   # Pflicht, höchstens 2 Zeilen, ohne Schlusspunkt
betreff_kurz: Angebot 2026-0815  # optional, für die Kopfzeile ab Seite 2
infoblock:                       # optional; Leitwörter erscheinen in der Reihenfolge der Norm
  ihr_zeichen: ABC-12
  ihre_nachricht_vom: 2026-08-20
  unser_zeichen: EM
  unsere_nachricht_vom: 2026-08-22
  ansprechpartner: Erika Muster  # erscheint als „Name"
  telefon: 0941 620-9800
  fax: 0941 620-9801
  email: muster@example.de
anrede: Sehr geehrte Frau Muster,       # endet mit Komma. Ohne Angabe: „Sehr geehrte Damen und Herren,"
gruss: Mit freundlichen Grüßen          # ohne Komma. Ohne Angabe: Wert aus dem Profil
unterzeichner: i. A. Erika Muster       # ohne Angabe: Wert aus dem Profil
anlagen:                                # optional
  - Angebot 2026-0815
verteiler:                              # optional
  - Herrn Max Muster
---
```

Das Datum wird als ISO-Datum angegeben und vom Renderer ausgeschrieben („25. August 2026").
Steht dort bereits ein ausformulierter Text, bleibt er unverändert.

## Grenzen, die abbrechen statt still zu verrutschen

| Feld | Grenze | Grund |
|---|---|---|
| `empfaenger` | 1 bis 6 Zeilen, keine Leerzeile | Anschriftzone ist 27,3 mm hoch |
| `vermerke` | höchstens 3 Zeilen | Zusatz- und Vermerkzone ist 12,7 mm hoch |
| `betreff` | höchstens 2 Zeilen | Norm |
| `infoblock`-Werte | höchstens 32 Zeichen | Wertespalte ist 43 mm breit |
| `anrede` | endet mit Komma | Norm |
| `gruss` | ohne Komma | Norm |

## normbrief-Markdown (CommonMark-Teilmenge)

Geparst wird nach [CommonMark](https://commonmark.org/) 0.31.2. Gesetzt wird davon die Teilmenge,
die in einen Brief gehört; alles andere bricht mit Zeile, Grund und Korrektur ab — nie still.

| Syntax | Verhalten |
|---|---|
| Absätze, durch Leerzeile getrennt | gesetzt |
| `**fett**`, `__fett__` | fett |
| `*kursiv*`, `_kursiv_` | kursiv |
| `***beides***` | fett und kursiv |
| `\` am Zeilenende | Zeilenumbruch |
| zwei Leerzeichen am Zeilenende | Zeilenumbruch, dazu eine Warnung — in keiner Vorschau sichtbar |
| einfacher Zeilenwechsel | Leerzeichen (ein Absatz) |
| `-` / `*` / `+` Aufzählung, bis zwei Ebenen | Liste |
| `1.` / `1)`, beliebiger Startwert | nummerierte Liste, die mit diesem Wert beginnt |
| Tabelle mit Trennzeile, Ausrichtung `:--`, `:-:`, `--:` | Tabelle; Spalten ohne Angabe linksbündig |
| `\* \_ \\ \# \. \- \[ \]` | das Zeichen selbst |
| `*` oder `_` mit Leerzeichen ringsum (`3 * 4`) | Text |
| `&nbsp;` `&amp;` `&copy;` | dekodiert |
| Überschriften `#`, auch `===`/`---` darunter | **Fehler** — der Betreff steht im Frontmatter |
| Blockzitat `>` | **Fehler** |
| Code: `` `x` ``, eingerückt, ``` | **Fehler** — Text ohne Backticks schreiben |
| Links `[t](u)`, `[t][id]`, `<url>` | **Fehler** — auf Papier gibt es keinen Link; Adresse ausschreiben |
| Bilder `![]()` | **Fehler** — Logo und Signatur gehören ins Profil |
| HTML | **Fehler** — wird nie durchgereicht |
| Trennlinie `---` allein | **Fehler** |
| `~~durchgestrichen~~`, `[^1]`, `- [ ]` | **Fehler** mit Nennung der Syntax |
| Tabelle ohne Trennzeile | **Fehler** — sonst stünde die Zeile als Text im Brief |

Drei Stellen weichen bewusst von CommonMark ab:

1. **Eine einzelne Zeile, die wie ein Listenpunkt aussieht, ist keiner.** `2. Mahnung zur
   Rechnung 4711` würde als nummerierte Liste gesetzt und die Zahl verschwände. normbrief lehnt
   das ab und schlägt `2\. Mahnung` vor. Dasselbe gilt für einen einzelnen Strich: `- 5 °C`
   würde ein Aufzählungspunkt.
2. **HTML wird nie durchgereicht.**
3. **Links werden nie gesetzt.**

Typografie nach DIN passiert selbsttätig: geschützte Leerzeichen in `z. B.`, `u. a.`, `d. h.`,
zwischen Zahl und Einheit (`10 %`, `5 km`, `1.234,56 EUR`), nach `§`, zwischen Tag und Monat
(`25. August`); `--` wird zum Halbgeviertstrich, `"..."` zu `„..."`.

## Profildatei

Anlegen mit `normbrief.py init-profil <name>`. Die Datei landet unter
`~/.config/normbrief/profiles/<name>.yaml` — außerhalb der Installation, damit sie
Aktualisierungen übersteht.

```yaml
absender:                    # Pflicht
  name: Beispiel GmbH
  strasse: Musterweg 12
  plz: "93055"
  ort: Regensburg
ruecksendeangabe: Beispiel GmbH · Musterweg 12 · 93055 Regensburg   # Pflicht, einzeilig
form: B                      # Voreinstellung
font: Libertinus Serif       # oder "Source Sans 3" aus assets/fonts/
farbe: "#1a3a5c"
briefkopf:
  logo: assets/logo.png      # relativ zur Profildatei; ohne Logo erscheint der Name
  logo_hoehe_mm: 14
  zeilen: [Beispiel GmbH, "Musterweg 12 · 93055 Regensburg"]
fusszeile:                   # je Liste eine Spalte
  - [Beispiel GmbH, Musterweg 12, 93055 Regensburg]
  - ["Telefon 0941 620-9800", info@example.de]
datumsformat: lang           # lang oder iso
gruss: Mit freundlichen Grüßen
unterzeichner: Erika Muster
firma_ueber_unterschrift: false
signatur: assets/unterschrift.png   # optional, transparentes PNG
rand_unten_mm: 42            # optional; ohne Angabe aus der Fußzeilenhöhe berechnet
infoblock_defaults:
  ansprechpartner: Erika Muster
  telefon: 0941 620-9800
  email: muster@example.de
```

**Doppelpunkte in Textzeilen brauchen Anführungszeichen**, sonst liest YAML sie als Feld:

```yaml
- "Geschäftsführerin: Erika Muster"
```

Ohne Anführungszeichen bricht der Renderer mit einer entsprechenden Meldung ab.
