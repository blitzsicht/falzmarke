# Änderungen

Das Format folgt lose [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## v0.2.0 — 25.08.2026

### Behoben
- **Stiller Textverlust.** `Az. 12//345` verlor den Rest der Zeile, weil `//` für Typst ein
  Zeilenkommentar ist — ohne Fehler, ohne Warnung. Der Regex-Konverter ist durch einen
  CommonMark-Parser mit Positivliste ersetzt; Text wird jetzt als Typst-Zeichenkette ausgegeben,
  wodurch es im Ergebnis keine Sonderzeichen mehr gibt.
- **Zweizeiliger Betreff wurde abgelehnt.** Die Messung nahm die erste statt der letzten
  Betreffzeile und hielt die zweite für die Anrede. Ein Angebot mit Vorgangsnummer und Gegenstand
  ist der Normalfall.
- **`datum: morgen`** stand wörtlich im Brief, **`datum: 2026-13-45`** endete in einem Traceback.
- **Systemschriften im PDF.** Ein Brief mit Emoji bettete die Apple-Schrift STSong ein — das
  Ergebnis hing am Rechner, auf dem gesetzt wurde.
- **Der `.typ`-Briefkopf** war seit v0.1.2 dokumentiert und nicht gebaut.
- **Der claude.ai-Weg endete nach dem ersten Chat**, weil Profile dort nicht überleben.

### Geändert
- **PyMuPDF (AGPL-3.0) ersetzt** durch pdfplumber (MIT) und pypdf (BSD-3). Alle Abhängigkeiten
  sind jetzt permissiv lizenziert; siehe [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Die
  Messung wurde dabei genauer: Abstände treffen jetzt auf 0,00 mm.
- Der Prüfbericht ist eine Zeile statt dreißig; `--verbose` zeigt alles.
- `check` heißt `verify` und braucht kein `--form` mehr — die Form steht in den Falzmarken.
- normbrief ist ein installierbares Paket: `pipx install normbrief`, `uvx normbrief`.

### Hinzugefügt
- `lint` prüft vor dem Render, ohne Typst.
- `pack --profil NAME` erzeugt ein Skill-Zip mit eingebackenen Absendern für claude.ai.
- `--pdfua` für barrierefreie PDFs (PDF/UA-1), Herkunftsvermerk im PDF, Fremd-PDF-Modus mit
  Millimeterangabe bei verschobenen Marken.

## v0.1.2 — 25.08.2026

### Geändert
- README neu aufgebaut: Wortmarke, Produktversprechen, getrennte Schnellstarts für Claude und
  Terminal, Bildergalerie. Alle Aufrufe zeigen jetzt den Pfad, unter dem der Befehl wirklich liegt.
- `docs/plan.md` ersetzt durch [`docs/normmasse.md`](docs/normmasse.md) — Herkunft der Maße,
  Gegenproben und Messmethodik statt interner Planung.
- Repo-Beschreibung auf den Nutzen statt die Implementierung.

### Hinzugefügt
- Wortmarke und Social Preview unter `docs/assets/brand/`.
- `CONTRIBUTING.md`, `SECURITY.md`, dieses Changelog, Issue- und PR-Vorlagen.
- Test, der die Version in `pyproject.toml` gegen den neuesten Git-Tag hält.

## v0.1.1 — 25.08.2026

### Behoben
- **Eigene Profile überleben jetzt ein Update.** Bis v0.1.0 lag der einzige vorgesehene Ort
  innerhalb der Installation (`skill/typst/profiles.local/`). Wer den Skill ersetzte — Zip neu
  hochladen, Verzeichnis austauschen —, verlor alle Absender und konnte keinen früheren Brief mehr
  setzen. Der Suchpfad kennt jetzt `./profiles/` und `~/.config/normbrief/profiles/`.

### Hinzugefügt
- `normbrief.py init-profil NAME` legt eine ausgefüllte Vorlage am updatefesten Ort an.

## v0.1.0 — 25.08.2026

Erste Fassung.

- Markdown mit YAML-Frontmatter wird zu einem Brief nach DIN 5008:2020, Form A und B, als PDF/A-2b.
- Anschriftfeld mit allen vier Zonen, Informationsblock bei 125 mm, Falz- und Lochmarken,
  12-pt-Raster, Mehrseitigkeit mit Kopfzeile und Seitenzählung.
- Geometrieprüfung des fertigen PDFs nach jedem Lauf; Abweichung ergibt Exit-Code 2.
- Absenderprofile als YAML, optionaler Typst-Hook für eigene Briefköpfe.
- Claude-Skill, eigenständige CLI, PNG-Vorschau.
- Testsuite mit Gegenproben gegen absichtlich verschobene Layouts.
