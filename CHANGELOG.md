# Änderungen

Das Format folgt lose [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

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
