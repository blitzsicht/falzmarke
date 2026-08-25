# Fremdkomponenten und ihre Lizenzen

falzmarke steht unter der [MIT-Lizenz](LICENSE). Alles, was mitgeliefert wird oder zur Laufzeit
gebraucht wird, trägt eine permissive Lizenz — MIT, BSD, Apache-2.0 oder OFL. Damit lässt sich
falzmarke auch in geschlossene Systeme einbauen, ohne dass eine Copyleft-Pflicht entsteht.

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
| [typst-letter-pro](https://github.com/Sematre/typst-letter-pro) v3.0.0 | Sematre und Mitwirkende | MIT | Seitenlayout nach DIN 5008; unverändert, Prüfsumme in [`skill/typst/vendor/README.md`](skill/typst/vendor/README.md), Lizenztext daneben |
| [Source Sans 3](https://github.com/adobe-fonts/source-sans) 3.052 | Adobe | SIL OFL 1.1 | wahlweise Profilschrift; Lizenztext in `skill/assets/fonts/` |

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
