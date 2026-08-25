# Datenvertrag: das Frontmatter einer Briefdatei

Eine Briefdatei besteht aus YAML-Frontmatter zwischen zwei `---`-Zeilen und dem Brieftext
darunter.

```yaml
---
profil: example                  # Pflicht. Dateiname (ohne .yaml) aus ~/.config/falzmarke/profiles/
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
signatur: keine                         # `keine` = von Hand unterschreiben;
                                        # oder eine Bilddatei neben dem Brief
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

## Der Brieftext

Unter dem Frontmatter steht der Brieftext als Markdown — eine dokumentierte Teilmenge von
CommonMark. Welche Auszeichnungen möglich sind, was der Typografie-Pass von selbst erledigt
und was abbricht, steht in **[falzmarke-Markdown](markdown.md)**.

## Profildatei

Anlegen mit `falzmarke.py init-profil <name>`. Die Datei landet unter
`~/.config/falzmarke/profiles/<name>.yaml` — außerhalb der Installation, damit sie
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
