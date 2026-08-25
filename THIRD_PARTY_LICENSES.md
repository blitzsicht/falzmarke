# Fremdkomponenten und ihre Lizenzen

falzmarke steht unter der [MIT-Lizenz](LICENSE). Alles, was **am Programm** mitgeliefert wird
oder zur Laufzeit gebraucht wird, trägt eine permissive Lizenz — MIT, BSD, Apache-2.0 oder OFL.
Damit lässt sich falzmarke auch in geschlossene Systeme einbauen, ohne dass eine Copyleft-Pflicht
entsteht.

Für die Erzeugung der Videos gilt das **nicht** — dort steht ein Werkzeug, das nur
quelloffen einsehbar ist. Es ist am Programm nicht beteiligt und wird nicht mitgeliefert;
Abschnitt [Nur für die Videoerzeugung](#nur-für-die-videoerzeugung) sagt, was das bedeutet.

**Das ist eine bewusste Entscheidung, keine Selbstverständlichkeit.** Bis v0.1.2 wurde die
Geometrie mit [PyMuPDF](https://pymupdf.readthedocs.io) gemessen. PyMuPDF ist *„Dual Licensed —
GNU AFFERO GPL 3.0 or Artifex Commercial License"*: Wer falzmarke eingebaut und die Software über
ein Netzwerk angeboten hätte, wäre unter der AGPL zur Offenlegung des eigenen Quelltexts
verpflichtet gewesen. Für ein Werkzeug, dessen Zielgruppe Firmen sind, ist das ein
Ausschlusskriterium. Seit v0.2.0 messen pdfplumber und pypdf; das ist nebenbei genauer, weil
pdfplumber die Zeilenoberkante statt der Ascender-Box liefert.

## Mitgeliefert (vendort)

| Komponente | Urheber | Lizenz | Verwendung |
|---|---|---|---|
| [typst-letter-pro](https://github.com/Sematre/typst-letter-pro) v3.0.0 | Sematre und Mitwirkende | MIT | Seitenlayout nach DIN 5008; unverändert, Prüfsumme in [`skill/falzmarke/typst/vendor/README.md`](skill/falzmarke/typst/vendor/README.md), Lizenztext daneben |
| [Source Sans 3](https://github.com/adobe-fonts/source-sans) 3.052 | Adobe | SIL OFL 1.1 | wahlweise Profilschrift; Lizenztext in `skill/falzmarke/assets/fonts/` |
| [Montserrat](https://github.com/JulietaUla/Montserrat) 9.000 | Julieta Ulanovsky und Mitwirkende | SIL OFL 1.1 | Schrift der Marke (Kopfzeilen in Banner und Film), **nicht** der Briefe; liegt in `docs/marke/fonts/` und geht deshalb nicht ins `.skill`-Paket |

## Zur Laufzeit

| Komponente | Urheber | Lizenz | Verwendung |
|---|---|---|---|
| [Typst](https://typst.app) 0.15 | Typst GmbH | Apache-2.0 | Satz |
| [typst-py](https://github.com/messense/typst-py) | Messense Lv | Apache-2.0 | Compiler als Python-Wheel |
| [Libertinus](https://github.com/alerque/libertinus) | Philipp H. Poll, Caleb Maclennan | SIL OFL 1.1 | Standardschrift, in Typst enthalten |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | ExecutableBookProject | MIT | CommonMark-Parser |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | Jeremy Singer-Vine | MIT | Geometriemessung am fertigen PDF |
| [pypdf](https://github.com/py-pdf/pypdf) | Mathieu Fenniak, Martin Thoma und Mitwirkende | BSD-3-Clause | Metadaten, XMP, Schriftbettung |
| [PyYAML](https://pyyaml.org) | Kirill Simonov und Mitwirkende | MIT | Frontmatter und Profile |

## Nur für die Videoerzeugung

Diese Komponenten erzeugen den Erklärfilm unter
[`docs/marke/video/erklaerfilm/`](docs/marke/video/erklaerfilm/). Sie sind **nicht Teil des
Programms**, werden nicht mitgeliefert und laufen weder beim Setzen noch beim Prüfen eines
Briefes. Wer falzmarke benutzt oder einbaut, kommt mit ihnen nie in Berührung.

| Komponente | Urheber | Lizenz | Verwendung |
|---|---|---|---|
| [Remotion](https://www.remotion.dev) 4 | Remotion GmbH | [Remotion License](https://www.remotion.dev/docs/license) — **nicht** OSI-offen | Zeitleiste und Rendering des Erklärfilms |
| [React](https://react.dev) 18 | Meta und Mitwirkende | MIT | von Remotion vorausgesetzt |
| [TypeScript](https://www.typescriptlang.org) 5 | Microsoft | Apache-2.0 | Typprüfung der Szenen |
| [vhs](https://github.com/charmbracelet/vhs) | Charm | MIT | zeichnet das README-GIF aus der echten CLI auf |

**Zur Remotion-Lizenz.** Remotion ist quelloffen einsehbar, aber keine Open-Source-Software im
Sinne der OSI. Für Einzelpersonen, Non-Profits und Unternehmen bis drei Beschäftigte ist die
Nutzung kostenlos; ab vier Beschäftigten verlangt der Hersteller eine Company License, und
automatisiertes Rendern gilt als eigener Lizenzfall. Maßgeblich ist immer der Hersteller, nicht
diese Tabelle.

Für dieses Repository heißt das:

- Die **fertigen Videodateien** unter `docs/renders/` sind Ergebnis, nicht Software. Sie stehen
  wie das übrige Repository unter der MIT-Lizenz und dürfen ohne Rücksicht auf Remotion
  verwendet werden.
- Wer den Film **selbst neu rendert**, benutzt Remotion und braucht dafür je nach Betriebsgröße
  eine eigene Lizenz. Deshalb wird der Film lokal erzeugt und das Ergebnis eingecheckt, statt
  ihn in der CI bei jedem Lauf neu zu bauen.
- Sollte die Lizenz je im Weg stehen, ist [Motion Canvas](https://motioncanvas.io) (MIT) der
  vorgesehene Ersatz. Die Szenen hängen an `src/brand.ts` und `src/texte.json`, nicht an
  Remotion-Eigenheiten.

## Normen

DIN 5008 ist eine Norm des DIN Deutsches Institut für Normung e. V. Die Maße in diesem Projekt
folgen öffentlich dokumentierten Quellen (siehe [`docs/normmasse.md`](docs/normmasse.md)).
**falzmarke ist kein Produkt des DIN, steht in keiner Verbindung zum DIN und behauptet keine
Zertifizierung.** Der Normtext selbst ist urheberrechtlich geschützt und wird hier weder
wiedergegeben noch mitgeliefert.

## Markdown

Markdown wurde 2004 von [John Gruber](https://daringfireball.net/projects/markdown/) gemeinsam mit
Aaron Swartz entworfen. Die Spezifikation, an der sich falzmarke orientiert, ist
[CommonMark](https://commonmark.org/) (John MacFarlane und Mitwirkende).
