# Änderungen

Das Format folgt lose [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## v0.3.1 — 25.08.2026

### Behoben
- **Ein fremdes Profil las Bilder außerhalb seines Ordners.** `briefkopf_typ` prüfte, dass die
  angegebene Datei im Profilordner liegt — `logo` und `signatur` prüften es nicht. Weil ein Brief
  sein Profil im Frontmatter mitbringen darf, konnte ein zugeschickter Brief mit
  `logo: ../geheim/privat.png` jede Bilddatei einbetten, die der Empfänger lesen kann; der Lauf
  meldete dabei `30/30 Maße eingehalten`. Ein Symlink wirkte genauso. Die Prüfung sitzt jetzt an
  einer Stelle und wird von allen drei Feldern benutzt; ein Unterordner bleibt erlaubt.
  Gefunden beim Angriff auf v0.3.0, Protokoll in [`docs/angriff-2026-08-25.md`](docs/angriff-2026-08-25.md).

## v0.3.0 — 25.08.2026

### Geändert
- **normbrief heißt jetzt falzmarke.** Der Name musste vor dem Hybridbrief fallen, dessen
  Schema-URLs ab Veröffentlichung unveränderlich sind. Belegt vor dem Schnitt: TMview meldet
  weltweit keine eingetragene Marke „falzmarke" (Kontrollprobe mit „falz": 1.782 Treffer, die
  Suche misst also), und der Handelsregister-Bestand kennt kein Unternehmen dieses Namens.
- **Harter Schnitt, keine Aliase.** Mit umgezogen sind der CLI-Befehl, `FALZMARKE_PROFILES`,
  `~/.config/falzmarke/profiles/` und die PDF-Metadaten `/falzmarke_*`. Bestehende Profile
  wandern von Hand nach `~/.config/falzmarke/`. Bei null Fremdnutzern wäre eine
  Übergangsschicht toter Code gewesen.
- **`CONTRIBUTING.md` und `SECURITY.md` sind auf Englisch.** Das Werkzeug bleibt deutsch — DIN
  5008 ist eine deutsche Norm —, aber Fehler- und Sicherheitsmeldungen kommen von überall.

### Behoben
- **Bilder brachen `--pdfua`.** Sobald ein Profil ein Logo oder eine Unterschrift benutzte,
  brach der Satz mit `missing alt text` ab: PDF/UA-1 verlangt für jedes Bild eine Beschreibung.
  Logo und Signatur bekommen jetzt einen Alternativtext — der Absendername beziehungsweise
  „Unterschrift <Name>", überschreibbar mit `logo_alt`. Aufgefallen ist es erst, als das
  Beispielprofil die Bilder tatsächlich benutzte.
- **Ein Installationsweg, den es nicht gab.** README und der v0.2.0-Eintrag unten versprachen
  `uvx normbrief` und `pipx install normbrief` — das Paket lag nie auf PyPI, beide Befehle
  schlugen fehl. Der Frischklon-Job der CI konnte das nie melden, weil er ein lokal gebautes
  Wheel testet. Die README nennt jetzt `uvx --from git+…`, nachgemessen, und
  `tests/test_installationswege.py` wacht darüber. Die PyPI-Veröffentlichung bleibt offen
  ([#7](https://github.com/blitzsicht/falzmarke/issues/7)).

### Neu
- **`example-grafik.yaml`** — ein zweites mitgeliefertes Profil mit Logo im Briefkopf und
  Unterschrift über dem Namen. `example.yaml` bleibt bewusst ohne Bilder: Dass eine einzelne
  YAML-Datei ohne Nachbardateien rendert, ist eine Eigenschaft, die Tests bewachen.
- **`scripts/demobilder.sh`** erzeugt die Bilder der README und das Vorschaubild aus den
  Renders. Sie lagen bisher als PNG im Repository, ohne dass irgendwo stand, wie sie entstanden
  sind — und veralteten deshalb still bei jeder Änderung am Beispielbrief.

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
