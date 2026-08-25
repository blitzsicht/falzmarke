# normbrief — DIN-5008-Briefe als PDF, gesteuert durch Claude

Stand: 2026-08-25. Plan für ein öffentliches Repository `normbrief` (MIT). Ausführbar durch Claude Code in einem Durchlauf; Abnahme ausschließlich über Tests, nicht über Sichtprüfung.

## 0. Ergebnis der Recherche

| Kandidat | Typ | Befund | Entscheidung |
|---|---|---|---|
| `Sematre/typst-letter-pro` v3.0.0 | Typst-Package (Typst Universe, MIT) | Form A und B, Maße korrekt (verifiziert per PDF-Vermessung, s. u.), Informationsblock bei 125 mm, Falz-/Lochmarken, Kopf/Fuß, Seitenzählung „Seite x von y“, kompiliert mit Typst 0.15 in 1,3 s | **Layout-Engine übernehmen** (als Einzeldatei vendoren) |
| `MehrCurry/briefversand` | Claude-Code-Skill (Python/reportlab) | 1 Commit (2026-02-16), 1 Stern, **keine Lizenz** (Code damit nicht nachnutzbar), nur Form B, Falzmarken bei 87/192 mm (Form-A-Werte, für Form B falsch: 105/210), Anschriftzone bewusst auf 66 mm verschoben (LetterXpress-Banner statt DIN 62,7 mm), kein Informationsblock (Datum rechtsbündig bei 97,4 mm = alte Bezugszeichenzeile), Standard-Grußformel `Mit freundlichen Gruessen` im Code, keine Tests | **nicht verwenden**; einzige brauchbare Idee: PDF-Geometrie nach dem Rendern vermessen |
| `pascal-huber/typst-letter-template` | Typst | DIN-A/B-Presets, laut Autor „under development, breaking changes“ | nein |
| `ludwig-austermann/typst-din-5008-letter` | Typst | „DIN 5008 inspired“, Fokus Umschläge | nein |
| KOMA-Script `scrlttr2` (`DIN5008A/B.lco`) | LaTeX | Referenzimplementierung, aber TeX-Toolchain im GB-Bereich; in Sandbox/Skill nicht praktikabel | nein |
| `bikeshedder/dinbrief`, `metaminded/dinbrief`, `html-dinbrief`, `pandoc-letter-din5008` | Python/Ruby/HTML/Pandoc | alt, DIN 676-Ära, Form-B-only oder wkhtmltopdf/LaTeX-abhängig | nein |
| Prompt-only-„Skills“ (kibuzzer, skill-sprinters) | Blogartikel | Prompt ohne Renderer; ein LLM kann keinen Text auf 45,0 mm setzen | nein |

Verifizierte Messung (letter-pro, Form B, Typst 0.15, PyMuPDF): Falzmarken 105,0 / 210,0 mm, Lochmarke 148,5 mm, Marken bei x = 5 mm (Heftrand), Rücksendeangabe y = 46,1 mm unterstrichen bei 49,0 mm, Anschrift ab 61,9 mm (Glyph-Box; Zonenlinie 62,7 mm) bis 80 mm, Textrand links 25,0 mm / rechts 20 mm, Seite 210 × 297 mm, Fonts eingebettet (CID-Subset), PDF/A-2b kompiliert.

Konsequenz: Nicht die Layout-Engine bauen, sondern die fehlende Schicht darüber: Datenvertrag (Markdown + Frontmatter), Profile (Briefkopf/Fußzeile je Absender), Renderer-CLI, Geometrie-Tests, Claude-Skill, CI.

## 1. Referenzmaße DIN 5008:2020 (geht 1:1 in `references/din5008.md` und in die Tests)

| Element | Form A | Form B |
|---|---|---|
| Briefkopfhöhe | 27 mm | 45 mm |
| Anschriftfeld (85 × 45 mm, linke Kante 20 mm, Text ab 25 mm) Oberkante | 27 mm | 45 mm |
| Rücksendeangabe-Zone (5 mm, 1 Zeile, 7–8 pt, unterstrichen) | 27–32 mm | 45–50 mm |
| Zusatz-/Vermerkzone (12,7 mm, 3 Zeilen, 8 pt) | 32–44,7 mm | 50–62,7 mm |
| Anschriftzone (27,3 mm, 6 Zeilen, keine Leerzeilen) | 44,7–72 mm | 62,7–90 mm |
| Informationsblock (x = 125 mm, Breite ≤ 75 mm, Höhe ≥ 40 mm) Oberkante | 32 mm | 50 mm |
| Betreff (fett, ohne „Betreff:“, ohne Punkt, max. 2 Zeilen; 2 Leerzeilen = 8,46 mm unter Anschriftfeld/Infoblock) | ≈ 80,5 mm | ≈ 98,5 mm |
| Falzmarken | 87 / 192 mm | 105 / 210 mm |
| Lochmarke | 148,5 mm | 148,5 mm |
| Marken: im Heftrand (≤ 20 mm von links), Länge 2,5–5 mm | | |
| Seitenränder: links 25 mm (Norm-Minimum 24,1), rechts 20 mm (Norm-Minimum 8,1), Textbreite 165 mm | | |
| Grundzeilenhöhe 4,23 mm (12 pt); Text ≥ 10 pt; Anschrift/Infoblock ≥ 8 pt | | |

Vertikaler Textaufbau: Betreff → 2 Leerzeilen → Anrede (endet mit Komma, Text beginnt klein) → 1 Leerzeile → Text (Absätze durch 1 Leerzeile) → 1 Leerzeile → Grußformel (ohne Komma) → 3 Leerzeilen → Name (Vorname ausgeschrieben; „i. A.“/„ppa.“ vor dem Namen) → 1 Leerzeile → Anlagen → 1 Leerzeile → Verteiler. Bei Platzmangel Anlagen/Verteiler rechts neben den Grußblock bei 125 mm. Folgeseiten: Seitenzahl Pflicht („Seite 2 von 3“), Kopfzeile mit Datum/Betreffkurzform empfohlen, kein Anschriftfeld.

Schreibregeln (Inhalt): Datum `25. August 2026` oder `2026-08-25`; `25.08.2026` nur Inland. Telefon `+49 941 1234567` (keine Klammern, keine Bindestriche). Beträge `1.234,56 EUR` (Währung nachgestellt). Abkürzungen mit geschütztem Leerzeichen: `z. B.`, `u. a.`. Akademische Grade vor dem Namen (`Dr. Erika Muster`), Bachelor/Master dahinter. Anrede „Sehr geehrte Frau Muster,“; ohne Ansprechpartner „Sehr geehrte Damen und Herren,“. Grußformel ohne Komma. Betreff ohne Schlusspunkt; Frage-/Ausrufezeichen lässt die Norm zu, der Skill-Stil vermeidet sie.

## 2. Architektur (ein Weg, keine Alternativen)

Renderer: **Typst 0.15** über das Python-Package `typst` (bringt den Compiler als Wheel mit, keine Systeminstallation, `pip install typst`). Layout: **letter-pro 3.0.0** als vendorte Einzeldatei `letter-pro-v3.0.0.typ` (17 KB, MIT) → kein Package-Download zur Laufzeit. Eigene Wrapper-Datei `normbrief.typ` nutzt `letter-generic` mit `information-box` (DIN 2020), nicht `letter-simple` (Datum rechtsbündig über dem Betreff = alte Form).

Datenfluss: `brief.md` (YAML-Frontmatter + Markdown-Body) → `normbrief.py render` → Python parst Frontmatter, formatiert Datum, konvertiert Markdown-Teilmenge nach Typst-Markup, lädt Profil, übergibt alles als JSON via `sys_inputs` → Typst kompiliert → PDF (optional PDF/A-2b) + PNG-Vorschau → `normbrief.py check` vermisst das PDF mit PyMuPDF gegen Tabelle 1 → Exit-Code.

Das **Skill-Verzeichnis ist das Produkt**. Es muss ohne den Rest des Repos lauffähig sein, weil claude.ai nur den Skill-Ordner als Zip erhält. Repo = Skill + Tests + CI + Doku.

Fonts: Standard = Typst-eigene Libertinus Serif (keine Abhängigkeit). Profile dürfen eine vendorte OFL-Sans (`Source Sans 3`) aus `skill/assets/fonts/` wählen; Übergabe über `font_paths`.

Markdown-Teilmenge (alles andere → Fehler mit Zeilenangabe, kein stilles Durchreichen): Absätze, `**fett**`, `*kursiv*`, `- ` Listen, `1. ` Listen, harter Umbruch (`\` am Zeilenende), Pipe-Tabellen ohne Alignment-Spalten. Typst-Sonderzeichen werden escaped: `# * _ @ < > $ \ ~ ` ` ``.

## 3. Repository-Layout

```
normbrief/
├── README.md                     # Zweck, Install (Claude Code + claude.ai), Beispielrender-PNGs, DIN-Tabelle
├── LICENSE                       # MIT
├── pyproject.toml                # nur für Tests/CI; Laufzeit-Deps stehen in skill/requirements.txt
├── skill/                        # <- der Claude-Skill, in sich geschlossen
│   ├── SKILL.md
│   ├── requirements.txt          # typst>=0.15,<0.16 ; pyyaml>=6 ; pymupdf>=1.24
│   ├── scripts/
│   │   ├── normbrief.py          # CLI: render | check | preview | profiles | init  (argparse, stdlib + obige Deps)
│   │   └── bootstrap.py          # prüft/installiert Deps (pip --break-system-packages in Sandbox, sonst venv), Exit 0/1
│   ├── typst/
│   │   ├── vendor/letter-pro-v3.0.0.typ
│   │   ├── normbrief.typ         # Wrapper, liest sys.inputs.data (JSON-String)
│   │   └── profiles/
│   │       └── example.typ       # Beispielfirma mit allen Feldern; echte Profile sind NICHT im Public Repo
│   ├── assets/fonts/SourceSans3-*.otf (OFL)
│   └── references/
│       ├── din5008.md            # Tabelle 1 + Textaufbau + Schreibregeln
│       ├── stil.md               # Formulierungsregeln für Claude (Tonalität, Anrede, Aufbau typischer Brieftypen)
│       └── frontmatter.md        # Datenvertrag, Pflichtfelder, Beispiele
├── examples/                     # brief-form-b.md, brief-form-a.md, brief-mehrseitig.md, brief-tabelle.md, brief-einschreiben.md
├── docs/renders/                 # von CI erzeugte PNGs der examples (im README eingebunden)
├── tests/
│   ├── conftest.py               # rendert examples einmal pro Session in tmp_path
│   ├── test_geometry.py          # Tabelle 1 für Form A und B, jedes Beispiel
│   ├── test_markdown.py          # Konverter-Teilmenge + Escaping + Fehlerfälle
│   ├── test_frontmatter.py       # Pflichtfelder, Datum, Anschrift ≤ 6 Zeilen, Vermerke ≤ 3
│   ├── test_multipage.py         # Seite 2: Seitenzahl vorhanden, kein Anschriftfeld, Kopfzeile
│   ├── test_pdf.py               # A4, Fonts eingebettet, Metadaten, PDF/A-2b-Flag
│   └── test_cli.py               # Exit-Codes, check schlägt bei manipulierter Geometrie an
├── .github/workflows/ci.yml      # pytest auf ubuntu + macos; Renders als Artefakt; docs/renders committen (nur main)
├── .github/workflows/release.yml # bei Tag: zip skill/ -> normbrief.skill als Release-Asset
└── .gitignore                    # profiles.local/, *.pdf in briefe/, .venv
```

Echte Absenderdaten (Siluri, GbR, Blitzsicht: Anschrift, Bank, USt-IdNr, Handelsregister) kommen in ein gitignoriertes `skill/typst/profiles.local/` bzw. in ein privates Repo; `normbrief.py` sucht Profile in `profiles.local/` vor `profiles/`. Pfad zusätzlich über `NORMBRIEF_PROFILES` übersteuerbar.

## 4. Datenvertrag (`references/frontmatter.md`)

```yaml
---
profil: siluri                 # Pflicht; Dateiname in profiles.local/ oder profiles/
form: B                        # optional, A|B; Default aus Profil (Siluri: B)
empfaenger:                    # Pflicht, 1–6 Zeilen, keine Leerzeilen; Reihenfolge: Firma, Person, Straße, PLZ Ort, [LAND]
  - Muster GmbH
  - Frau Erika Muster
  - Musterstraße 1
  - 12345 Musterstadt
vermerke: [Einschreiben]       # optional, ≤ 3 Zeilen (Zusatz-/Vermerkzone)
datum: 2026-08-25              # Pflicht, ISO; Ausgabe laut Profil (Default Langform "25. August 2026")
betreff: Angebot Nr. 2026-0815 # Pflicht, ≤ 2 Zeilen
infoblock:                     # optional; Leitwörter in DIN-Reihenfolge, Profil liefert Defaults (Name, Telefon, E-Mail)
  ihr_zeichen: ABC-12
  ihre_nachricht_vom: 2026-08-20
  unser_zeichen: JG
  ansprechpartner: Johannes Gottl
  telefon: "+49 941 1234567"
  email: info@example.de
anrede: Sehr geehrte Frau Muster,   # optional; Default "Sehr geehrte Damen und Herren,"
gruss: Mit freundlichen Grüßen      # optional; Default aus Profil
unterzeichner: Johannes-Maximilian Gottl  # optional; Default aus Profil; Zusatz "i. A." erlaubt
anlagen: [Angebot 2026-0815, AGB]   # optional
verteiler: [Frau Muster, Herr Beispiel]  # optional
pdfa: true                     # optional; PDF/A-2b für Paperless/GoBD
---
Markdown-Body (Teilmenge laut Abschnitt 2). Erster Absatz beginnt klein (folgt auf die Anrede).
```

Profil (`profiles/example.typ`) liefert als Dictionary: `absender` (Name, Straße, PLZ Ort), `ruecksendeangabe` (einzeilig), `briefkopf` (Typst-Content: Logo als SVG/PNG-Pfad relativ zum Profil, Name, Claim), `fusszeile` (Spalten: Anschrift/Kontakt, Bank, Register/USt-IdNr), `form` Default, `font`, `farbe`, `datumsformat` (`lang|iso`), `gruss`, `unterzeichner`, `infoblock_defaults`.

## 5. `normbrief.typ` — Wrapper-Spezifikation

- `#let data = json(bytes(sys.inputs.data))`; Profil per `#import "profiles/" + data.profil + ".typ"` ist in Typst nicht dynamisch möglich → Python inliniert das Profil: es erzeugt pro Aufruf eine temporäre `main.typ` (`#import "normbrief.typ": brief` + `#import "<profilpfad>": profil` + `#show: brief.with(profil: profil, data: ...)` + Body). Body wird als Typst-Markup eingefügt, nicht als String.
- `brief` ruft `letter-generic` mit `format: "DIN-5008-" + form`, `header: profil.briefkopf` (Höhe 27/45 mm wird von letter-pro erzwungen), `footer: profil.fusszeile`, `folding-marks: true`, `address-box: address-tribox(sender-box(...), annotations, recipient)` (2020-Zonen 5/12,7/27,3 mm), `information-box: infoblock(...)` mit Leitwörtern in Norm-Reihenfolge und Datum als letzte Zeile, `page-numbering: auto`.
- Betreff: `#v(2 * 4.23mm)` nach dem Anschrift-/Infoblock-Bereich (letter-pro setzt den Body unter dem 45-mm-Block; die 2 Leerzeilen setzt der Wrapper explizit), `strong`, `text(size: 11pt)`. Danach `#v(2 * 4.23mm)`, Anrede, `#v(4.23mm)`, Body mit `par(spacing: 4.23mm)`, `#v(4.23mm)`, Gruß, `#v(3 * 4.23mm)`, Unterzeichner, `#v(4.23mm)`, Anlagen (`strong[Anlagen]` + Zeilen), `#v(4.23mm)`, Verteiler.
- Grundschrift 11 pt, Zeilenabstand so, dass 12-pt-Raster (4,23 mm) gehalten wird (`par(leading: ...)` justiert). Seite 2+: `header` via `page(header: ...)` nur ab Seite 2 mit „Betreff · Datum“, letter-pro liefert Seitenzahl.
- `set text(lang: "de", region: "DE", hyphenate: true)`; Silbentrennung an, Blocksatz aus (linksbündig ist DIN-Empfehlung).
- `set document(title: betreff, author: profil.absender.name, date: datum)`.

## 6. CLI `normbrief.py`

```
normbrief.py render  BRIEF.md [-o OUT.pdf] [--png] [--pdfa] [--profiles DIR]   # Exit 0 = PDF geschrieben; ruft check automatisch
normbrief.py check   OUT.pdf --form B [--json]                                   # vermisst PDF, Exit 0/2, Report mit Soll/Ist/Toleranz
normbrief.py preview OUT.pdf [-o OUT.png] [--ppi 100]                            # PNG Seite 1 (Typst-Compile mit format=png)
normbrief.py profiles                                                            # listet gefundene Profile + Pfad
normbrief.py init    ZIEL.md --profil siluri --empfaenger "..." --betreff "..."  # schreibt Frontmatter-Skelett
```

Exit-Codes: 0 ok, 1 Eingabefehler (Frontmatter/Markdown, mit Zeilenangabe), 2 Geometrie-Check fehlgeschlagen, 3 Umgebung (typst fehlt; Hinweis auf `bootstrap.py`). Alle Ausgaben auf stdout in einer Zeile pro Prüfung: `OK  Falzmarke 1: soll 105.0 ist 105.0 (tol 0.3)`.

Datumsausgabe in Python (deutsche Monatsnamen, Tabelle im Skript); Typst bekommt den fertigen String. `--pdfa` → `pdf_standards=["a-2b"]`; vor Übergabe prüfen, dass keine transparenten PNGs im Profil-Logo stecken (PDF/A-2b erlaubt Transparenz; PDF/A-1b nicht — daher fest 2b).

## 7. Geometrie-Tests (Soll-Werte, Toleranzen)

Vermessung mit PyMuPDF: `page.get_drawings()` für Marken, `page.get_text("dict")` für Text-Boxen (Glyph-Box-Oberkante liegt bis 0,8 mm über der Zonenlinie; Toleranz entsprechend).

| Prüfung | Soll (A / B) | Toleranz |
|---|---|---|
| Seitengröße | 210 × 297 mm | 0,1 |
| Falzmarke 1 / 2, y | 87 / 192 bzw. 105 / 210 | 0,3 |
| Lochmarke, y | 148,5 | 0,3 |
| Marken, x-Ende | ≤ 20 mm | — |
| Rücksendeangabe, y-Oberkante | in [27, 32] bzw. [45, 50] | 0,8 |
| Rücksendeangabe, x | 25,0 | 0,3 |
| Anschrift erste Zeile, y | ≥ 44,7 bzw. ≥ 62,7 | 0,8 |
| Anschrift letzte Zeile, y-Unterkante | ≤ 72 bzw. ≤ 90 | 0 |
| Anschrift, x-Bereich | [25, 105] | 0,3 |
| Anschrift Zeilenzahl | ≤ 6, keine Leerzeile | — |
| Infoblock, x-links | 125,0 | 0,5 |
| Infoblock, y-Oberkante | 32 bzw. 50 | 0,8 |
| Infoblock, x-rechts | ≤ 200 | — |
| Betreff: fett, y ≥ Anschriftfeld-Ende + 8,46 mm, Text beginnt nicht mit „Betreff“ | 80,5 bzw. 98,5 | 1,0 (nach oben nur bei fehlendem Infoblock) |
| Textblock, x-links / x-rechts | 25,0 / ≤ 190 | 0,3 |
| Gruß → Name: 3 Leerzeilen | 12,7 mm | 1,0 |
| Anrede endet mit Komma, Gruß ohne Komma | — | — |
| Seite ≥ 2: Text „Seite 2 von N“ vorhanden, kein Text in [45, 90] × [20, 110] mm außer Kopfzeile | — | — |
| Fonts: alle eingebettet (`get_fonts()` → kein nicht-eingebetteter Eintrag) | — | — |
| Extrahierter Text enthält `Grüßen` und keines von `Gruessen|Strasse|Muenchen`-Mustern aus dem Beispiel | — | — |
| `--pdfa`: XMP-Metadaten `pdfaid:part=2`, `conformance=B` | — | — |

Negativtests: Anschrift mit 7 Zeilen → Exit 1; Markdown mit `## Überschrift` → Exit 1 mit Zeilennummer; manipuliertes PDF (Falzmarke verschoben) → `check` Exit 2.

## 8. Skill-Spezifikation (`skill/SKILL.md`)

Frontmatter:

```yaml
---
name: normbrief
description: >
  Erzeugt Geschäftsbriefe nach DIN 5008:2020 (Form A/B) als PDF mit Falz-/Lochmarken, Anschriftfeld
  für Fensterumschläge, Informationsblock, Briefkopf/Fußzeile aus Absender-Profilen, optional PDF/A-2b.
  Immer verwenden, wenn ein Brief, Anschreiben, Schreiben, Kündigung, Mahnung, Angebot als Brief,
  Mieterschreiben, Behördenschreiben, Widerspruch, Bestätigung oder "etwas zum Ausdrucken/Verschicken"
  gewünscht ist — auch wenn DIN 5008 nicht genannt wird. Nie Briefe als .docx oder frei formatiertes
  PDF bauen, wenn dieser Skill verfügbar ist.
---
```

Body (≤ 200 Zeilen):

1. **Regel 0**: Layout wird nie von Hand gesetzt. Immer `render` → `check` → Vorschau. Kein PDF ohne grünen `check`.
2. **Ablauf**: (a) Profil wählen (`profiles`; bei mehreren Absendern nachfragen, sonst Default aus Kontext), (b) Pflichtfelder aus dem Gespräch ziehen, fehlende **einmal gesammelt** erfragen, (c) Brieftext nach `references/stil.md` formulieren und als `briefe/JJJJ-MM-TT_<empfaenger-slug>_<betreff-slug>.md` schreiben (Quelle der Wahrheit ist die .md, nicht das PDF), (d) `render --png`, (e) PNG zeigen + PDF bereitstellen, (f) Änderungswünsche in der .md ändern und neu rendern.
3. **Umgebung**: erst `python3 scripts/bootstrap.py`; in claude.ai läuft das nur mit Netzwerkzugriff (pip); ohne Netzwerk Abbruch mit klarer Meldung (kein Fallback-Renderer — bewusst, sonst Layout-Drift).
4. **Grenzen**: Markdown-Teilmenge; keine eingebetteten Bilder im Body (nur Logo im Profil); Anschrift ≤ 6 Zeilen; Betreff ≤ 2 Zeilen.
5. Verweise: `references/din5008.md` nur lesen, wenn der Nutzer nach Normdetails fragt oder `check` fehlschlägt; `references/stil.md` immer vor dem Formulieren; `references/frontmatter.md` bei Unsicherheit über Felder.

`references/stil.md`: Anrede-Regeln, Betreff-Formulierung (Nominalstil, konkret, ≤ 60 Zeichen), Aufbau nach Brieftyp (Angebot, Mahnung 1–3, Kündigung, Widerspruch, Mieterschreiben, Bestätigung, Behörde): Einstieg ohne Floskel, ein Anliegen pro Absatz, Frist/Handlung im letzten Absatz, kein „Wir würden uns freuen“, Sie/Ihnen groß, Zahlen/Datum/Telefon nach DIN, keine Emojis, keine Ausrufezeichen.

Installation: Claude Code `ln -s <repo>/skill ~/.claude/skills/normbrief` (Projektskill: `.claude/skills/normbrief`); claude.ai: Release-Asset `normbrief.skill` (Zip mit `normbrief/SKILL.md` an der Wurzel) unter Settings › Features hochladen (Pro/Max/Team mit Code-Ausführung).

## 9. CI

`ci.yml`: Matrix ubuntu-latest + macos-latest, Python 3.12, `pip install -r skill/requirements.txt pytest`, `pytest -q`, danach `normbrief.py render examples/*.md --png` → Upload als Artefakt; auf `main` zusätzlich Commit der PNGs nach `docs/renders/` (Bot-Commit, `[skip ci]`). `release.yml`: bei Tag `v*` → `cd skill && zip -r ../normbrief.skill .` (Ordnername im Zip `normbrief/`) → GitHub Release mit Asset.

## 10. Phasen, Abnahmekriterien, Aufwand

Aufwand: menschliche Entwicklungszeit / Claude-Code-Laufzeit (Kompression ~10×, inkl. Iterationsschleifen und Fehlversuche).

| Phase | Inhalt | Abnahme (Beweis) | Mensch | Claude Code |
|---|---|---|---|---|
| 0 Skelett | Repo, LICENSE, Struktur, letter-pro vendoren (SHA notieren), Fonts, `bootstrap.py`, CI-Grundgerüst | `pytest` läuft leer durch; CI grün | 3 h | 15–20 min |
| 1 Renderer | `normbrief.typ`, `example.typ`, Frontmatter-Parser, Markdown-Konverter, Datumsformat, `render`/`preview`, Form A/B, Infoblock, Mehrseitigkeit, PDF/A | 5 examples rendern; PNGs sichtbar korrekt; Form-A- und Form-B-Beispiel | 8–10 h | 45–60 min |
| 2 Prüfung | `check` + alle Tests aus Abschnitt 7 inkl. Negativtests | `pytest` grün auf ubuntu + macos; `check` rot bei manipuliertem PDF | 5–6 h | 30–40 min |
| 3 Skill | `SKILL.md`, drei `references/*.md`, `init`, 5 Testprompts (Angebot Form B, Mahnung, Mieterschreiben GbR, Widerspruch Form A, mehrseitig mit Tabelle) in Claude Code durchspielen, Beschreibung nachschärfen | Alle 5 Prompts liefern PDF mit grünem `check` ohne manuelles Eingreifen; Zip-Upload in claude.ai funktioniert | 3–4 h | 20–30 min + 30 min Review |
| 4 Doku/Release | README mit Renders, Install-Anleitung, `release.yml`, Tag `v0.1.0` | Release-Asset `normbrief.skill` vorhanden; Fresh-Clone-Test auf zweitem Rechner | 2 h | 10–15 min |
| **Summe** | | | **21–25 h (≈ 3 Arbeitstage)** | **≈ 2–2,5 h Laufzeit + ≈ 1 h eigener Review** |

Kill-Kriterium Phase 1: Wenn letter-pro sich nicht ohne Fork so ansteuern lässt, dass Betreff- und Infoblock-Position innerhalb der Toleranzen liegen, wird `letter-pro-v3.0.0.typ` als Fork in `vendor/` angepasst (MIT erlaubt das; Änderungen in `vendor/CHANGES.md` dokumentieren). Kein Wechsel auf reportlab.

## 11. Backlog nach v0.1.0 (nicht Teil dieses Plans)

Paperless-NGX-Ablage (`POST /api/documents/post_document/`, Tag `Ausgang`, Korrespondent aus `empfaenger[0]`); Postversand über API (LetterXpress oder Deutsche Post; eigene Implementierung, kein Code aus `briefversand`); Odoo-Anhang an `res.partner`; Umschlag-Druck (C6/5, DL) aus denselben Daten; Serienbrief (CSV → n PDFs); Signaturbild im Profil (transparentes PNG über der Unterschriftszeile).

## 12. Kickoff-Prompt für Claude Code

```
Lies normbrief-plan.md vollständig. Baue Phase 0 bis 4 in dieser Reihenfolge, jede Phase mit Commit.
Abnahme pro Phase nur über die dort genannten Beweise; nichts als „fertig“ melden ohne pytest-Ausgabe
und gerenderte PNGs. Keine Alternativen anbieten, keine Rückfragen, die der Plan beantwortet.
Vendore letter-pro-v3.0.0.typ von https://github.com/Sematre/typst-letter-pro/releases/download/v3.0.0/letter-pro-v3.0.0.typ
und notiere SHA256 in skill/typst/vendor/README.md. Echte Absenderdaten kommen ausschließlich nach
skill/typst/profiles.local/ (gitignored); im Repo nur profiles/example.typ.
Am Ende: pytest -q, alle examples gerendert, normbrief.skill gepackt, README mit Renders.
```
