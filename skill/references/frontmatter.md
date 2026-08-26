# Datenvertrag: das Frontmatter einer Briefdatei

Eine Briefdatei besteht aus YAML-Frontmatter zwischen zwei `---`-Zeilen und dem Brieftext
darunter.

```yaml
---
profil: example                  # Pflicht. Dateiname (ohne .yaml) aus ~/.config/falzmarke/profiles/
form: B                          # A oder B. Ohne Angabe gilt der Wert aus dem Profil
norm: din5008                    # reserviert; derzeit nur din5008
sprache: de                      # de oder en. Beschriftung und Datum, nicht die Maße
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
anlagen:                                # optional, der Vermerk im Brief
  - Angebot 2026-0815
anlagen_dateien:                        # optional, PDFs hinten anhängen
  - angebot-2026-0815.pdf               # relativ zur Briefdatei
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
sprache: de                  # Voreinstellung; der Brief darf sie überschreiben
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

## Sprache

`sprache: en` setzt die Beschriftung eines Briefes auf Englisch: die Leitwörter des
Informationsblocks, die Monatsnamen, „Anlagen", „Verteiler" und die Seitenzählung. Dazu
`text.lang`, wovon die Silbentrennung abhängt — ohne das bräche englischer Text nach
deutschen Regeln um.

**Die Maße ändern sich nicht.** Anschriftfeld, Informationsblock, Falzmarken und das
12-pt-Raster sind Werte der DIN 5008 und hängen nicht an der Sprache. `verify` misst
Zonen und Abstände, keine Wörter; ein englischer Brief besteht dieselben Prüfungen.

**Die englischen Wörter sind nicht normbelegt.** DIN 5008 ist eine deutsche Norm und
kennt kein „Your reference". Was `falzmarke` dort einsetzt, ist die im Geschäftsverkehr
übliche Entsprechung — eine Konvention, keine Fundstelle. Wer so einen Brief setzt,
bekommt ein Blatt, dessen Maße belegt sind und dessen Beschriftung es nicht ist.

| Feld | Deutsch | Englisch |
|---|---|---|
| `ihr_zeichen` | Ihr Zeichen | Your reference |
| `ihre_nachricht_vom` | Ihre Nachricht vom | Your letter of |
| `unser_zeichen` | Unser Zeichen | Our reference |
| `unsere_nachricht_vom` | Unsere Nachricht vom | Our letter of |
| `ansprechpartner` | Name | Contact |
| `telefon` | Telefon | Phone |
| `fax` | Fax | Fax |
| `email` | E-Mail | Email |
| — | Datum | Date |
| — | Anlage / Anlagen | Enclosure / Enclosures |
| — | Verteiler | Copies to |
| — | Seite x von y | Page x of y |

Das Datum folgt der britischen Schreibweise (`26 August 2026`), nicht der amerikanischen:
Ein DIN-5008-Brief ist ein europäischer Geschäftsbrief, und die Folge Tag–Monat–Jahr
bleibt damit dieselbe wie im deutschen Original. Wer die Zeile überfliegt, verwechselt
Tag und Monat nicht.

Ein vollständiges Beispiel: [`examples/brief-englisch.md`](../../examples/brief-englisch.md).

## Anlagen beilegen

`anlagen:` und `anlagen_dateien:` sind zweierlei und unabhängig voneinander:

- **`anlagen:`** schreibt den Anlagenvermerk unter den Brief. Er nennt, was beiliegt —
  auch dann, wenn die Anlage per Post beigelegt wird und es keine Datei gibt.
- **`anlagen_dateien:`** hängt PDF-Dateien hinten an das erzeugte PDF. Pfade sind
  relativ zur Briefdatei, damit ein Vorgang samt seinen Anlagen ein Ordner bleibt,
  den man verschieben kann.

Wer beides will, schreibt beides.

### Was das mit PDF/A macht

Ein Merge erhält die XMP-Metadaten des Briefes. Ohne Gegenmaßnahme behauptet die Datei
danach weiter PDF/A-2b, gleichgültig was in der Anlage steckt — gemessen mit veraPDF:

| Anlage | Ergebnis laut veraPDF | XMP sagt |
|---|---|---|
| aus Typst, Schriften eingebettet | PASS 2b | 2b |
| nicht eingebettete Schrift | **FAIL 2b** | 2b |

Der zweite Fall ist der teure: eine Datei, die PDF/A behauptet und es nicht ist. Sie
fällt erst auf, wenn im Archiv die Schrift fehlt.

falzmarke hat die Anlage nicht gesetzt und kann ihre Konformität nicht prüfen — das kann
nur ein Prüfwerkzeug wie veraPDF. Ohne fremdes Werkzeug feststellbar ist allein, was die
Anlage **über sich selbst sagt**. Daran richtet sich die Kennzeichnung aus:

| Lage | Kennzeichnung | Meldung |
|---|---|---|
| alle Anlagen deklarieren PDF/A | bleibt | Hinweis, dass das ihre Aussage ist, keine Prüfung |
| eine Anlage deklariert nichts | wird entfernt | nennt die Datei und den Grund |

Die Deklaration ist kein Beleg für Konformität. Eine Anlage, die nichts behauptet, ist
mit Sicherheit kein PDF/A; eine, die es behauptet, ist es wahrscheinlich. Auf dieser
Grundlage die Kennzeichnung zu *entfernen* ist sicher — sie stehen zu lassen bleibt eine
Aussage über die Anlage. Belegt ist die Konformität des Ergebnisses erst durch veraPDF
([`scripts/pdf_konformitaet.py`](../../scripts/pdf_konformitaet.py)).

### Die Anlage wird nicht nach Briefregeln gemessen

Eine Anlage trägt keine Kopfzeile mit Betreff, keine Seitenzählung und womöglich keine
eingebettete Schrift. `verify` misst deshalb nur die Seiten des Briefes; wo er endet,
vermerkt falzmarke beim Anhängen als `/falzmarke_Briefseiten` im PDF. Auch ein späteres
`verify` auf der fertigen Datei liest das und beurteilt die Anlage nicht.
