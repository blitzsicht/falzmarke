<div align="center">

<img src="https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/brand/banner.png" alt="falzmarke — Briefe schreiben mit KI, nach Norm, nicht nach Gefühl. DIN-5008-Briefe aus Markdown, als PDF/A gesetzt und auf den Millimeter geprüft." width="100%">

[![CI](https://github.com/blitzsicht/falzmarke/actions/workflows/ci.yml/badge.svg)](https://github.com/blitzsicht/falzmarke/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/blitzsicht/falzmarke)](https://github.com/blitzsicht/falzmarke/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/blitzsicht/falzmarke/blob/main/LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](https://github.com/blitzsicht/falzmarke/blob/main/pyproject.toml)
[![DIN 5008](https://img.shields.io/badge/DIN_5008-2020-245A73)](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/din5008.md)

</div>

---

**Andere Werkzeuge erzeugen ein PDF. falzmarke prüft das Ergebnis.**

Du schreibst den Inhalt als Markdown. falzmarke setzt daraus einen Geschäftsbrief nach
DIN 5008:2020 als PDF/A — und misst anschließend das fertige PDF nach. Sitzt die Falzmarke nicht
auf 105,0 mm, endet der Lauf mit einem Fehler statt mit einem Brief, der nur ungefähr stimmt.

<div align="center">

**[falzmarke.com — Anleitung ohne Terminal](https://falzmarke.com)** ·
**[⬇ Als Claude-Skill laden](https://github.com/blitzsicht/falzmarke/releases/latest/download/falzmarke.skill)** ·
**[In 60 Sekunden ausprobieren](#in-60-sekunden)** ·
**[Beispielbrief ansehen](https://github.com/blitzsicht/falzmarke/raw/main/docs/renders/brief-form-b.png)**

`Linux · macOS · Windows`  ·  `34 Maße je Seite`  ·  `PDF/A-2b`  ·  `MIT`

</div>

---

## In Bewegung

![Ein Terminal zeigt den Musterbrief als Markdown, danach den Lauf von falzmarke render: PDF und Vorschau werden geschrieben, anschließend läuft der Messbericht durch und endet mit der Zeile, die die eingehaltenen Maße zählt.](https://github.com/blitzsicht/falzmarke/raw/main/docs/renders/demo.gif)

Aufgezeichnet aus der echten CLI mit [vhs](https://github.com/charmbracelet/vhs);
das Drehbuch steht in [`docs/marke/video/readme.tape`](https://github.com/blitzsicht/falzmarke/blob/main/docs/marke/video/readme.tape).
Ein Test hält den Mitschnitt gegen einen frischen Lauf, damit hier kein Terminal
steht, das es so nie gab ([`tests/test_tape.py`](https://github.com/blitzsicht/falzmarke/blob/main/tests/test_tape.py)).

---

## Was dabei herauskommt

![Briefkopf, Anschriftfeld, Informationsblock und Betreff](https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/demo/hero.png)

Und was danach geprüft wird — Auszug aus dem Bericht, den jeder Lauf ausgibt:

```
OK    Falzmarke 1, y: soll 105.00 ist 105.00 (tol ±0.3)
OK    Infoblock, x-links: soll 125.00 ist 125.00 (tol ±0.5)
OK    Betreff, y-Oberkante: soll 98.47 ist 97.91 (tol -1.75/+0.6)
OK    Abstand Betreff → Anrede (2 Leerzeilen): soll 12.70 ist 12.70 (tol ±0.2)
```

Das sind vier von 33 Zeilen des Geometrieberichts. Der Film zeigt, wie die übrigen
entstehen: Eine Linie fährt das Blatt ab und hält an jedem gemessenen Höhenmaß. Sie hält
dort, wo die Messung es sagt — bei diesen Prüfungen ist der gemessene Wert zugleich die
Stelle.

![Ein Beispielbrief, daneben ein Textfeld. Eine grüne waagerechte Linie wandert von oben nach unten über das Blatt und hält nacheinander an acht Stellen: Rücksendeangabe bei 46,26 Millimetern, Infoblock bei 50,34, Anschrift erste Zeile bei 62,69 und letzte Zeile bei 77,86, Betreff bei 98,45, Falzmarke 1 bei 105,00, Lochmarke bei 148,50 und Falzmarke 2 bei 210,00. Bei jedem Halt stehen daneben der Name der Prüfung, Sollwert, gemessener Wert, Toleranz und das Wort eingehalten. Am Ende liegen alle acht Linien gleichzeitig auf dem Blatt und daneben steht: 33 von 33 Prüfungen eingehalten.](https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/demo/messfilm.gif)

Acht der 33 Geometrieprüfungen tragen eine Höhe auf dem Blatt; die übrigen messen Breiten,
Abstände und Eigenschaften ohne Ort auf der Seite. Die Zahl 34 weiter oben zählt eine
mehr: Nach einem `render` sieht die CLI zusätzlich die PDF/A-Konformität nach, und die
liegt auf keinem Millimeter. Beide Zahlen stimmen, sie zählen Verschiedenes.

Keine Zahl im Film ist abgetippt — sie kommen alle aus `verify --json`, und
`tests/test_messfilm.py` hält den Film gegen einen frischen Messlauf. Verschiebt jemand
die Falzmarke um 2 mm, muss der betroffene Halt rot werden; tut er es nicht, schlägt der
Test fehl.

Die erste Zeile des Berichts oben spricht von einem Strich, den man auf einem
Vorschaubild kaum sieht — er ist 0,25 pt stark. Vergrößert sieht die Stelle so aus:

![Ausschnitt vom linken Rand eines Briefes, sechs mal vier Millimeter groß: Eine gestrichelte grüne Hilfslinie markiert die Sollposition bei 105,00 Millimetern und geht auf gleicher Höhe in die kurze schwarze Falzmarke über, die knapp die halbe Bildbreite einnimmt. Daneben das ganze Blatt verkleinert, mit einem Rahmen um die vergrößerte Stelle. Darunter steht die gemessene Position 105,00 Millimeter.](https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/demo/falzmarke-detail.png)

Dort wird der Bogen gefaltet, damit die Anschrift im Fensterumschlag steht. Sitzt die
Marke falsch, faltet der Stapel falsch — und das fällt erst nach dem Druck auf.

## Das Problem

Eine Briefvorlage kann nicht prüfen, ob das Ergebnis stimmt. Sie wird kopiert, jemand verschiebt
eine Zeile, und der Fehler fällt erst am fertigen Stapel auf: Die Anschrift steht nicht mehr im
Fensterausschnitt, alles muss neu gedruckt und kuvertiert werden — und wer mit Automationsrabatt
einliefert, verliert ihn für diese Sendung.

Sprachmodelle verschärfen das. Sie formulieren gut, aber sie können keinen Text auf 45,0 mm
setzen. Wer einen Brief von einer KI schreiben lässt, bekommt zuverlässig guten Inhalt in
unzuverlässigem Layout.

Und ein Renderer kann ebenfalls Fehler haben — auch dieser hier.

Deshalb trennt falzmarke drei Dinge: **Inhalt** kommt als Markdown, lesbar und versionierbar.
Das **Layout** setzt ein Renderer, der es immer gleich macht. Und die **Prüfung** misst das
fertige PDF, statt dem Renderer zu glauben.

## Warum nicht einfach Word oder ein Prompt?

Verglichen wird der typische Arbeitsablauf, nicht das Werkzeug an sich — mit einer sorgfältig
gepflegten Vorlage lässt sich vieles davon erreichen.

| | Vorlage in Word / LibreOffice | Brief direkt von einer KI | falzmarke |
|---|---|---|---|
| Quelle diffbar und versionierbar | teilweise | selten | ja — Markdown und YAML |
| Layout reproduzierbar | hängt an Vorlage und Umgebung | nicht zugesichert | ja — derselbe Renderer, dieselbe Ausgabe |
| Fertiges PDF wird nachgemessen | nein | nein | ja — 34 Maße, jede Seite, Abweichung ist ein Fehler |
| Absenderprofile | von Hand gepflegt | uneinheitlich | ja — einmal anlegen, überall nutzen |
| Prüfbericht maschinenlesbar | nein | nein | ja — `--json` und Exit-Codes |
| PDF/A als Voreinstellung | nicht automatisch | nicht zugesichert | ja — ohne zusätzliches Flag |

## Was du davon hast

- **Der Brief sitzt im Fensterumschlag** — Anschriftfeld, Falz- und Lochmarken werden am
  fertigen PDF vermessen, nicht beim Setzen angenommen.
- **Änderungen bleiben nachvollziehbar** — Markdown und YAML sind Textdateien. Ein Diff zeigt,
  was sich geändert hat; das PDF ist Ergebnis, nicht Quelle.
- **Ein Auftritt, viele Briefe** — Profile bündeln Briefkopf, Fußzeile, Logo, Farben und
  Voreinstellungen. Auch die Unterschrift, je Brief überschreibbar.
- **Fehler sind maschinenlesbar** — eigene Exit-Codes für Eingabe-, Geometrie- und
  Umgebungsfehler, dazu `--json`. Damit läuft es in CI und in Automatisierungen.
- **Für Langzeitarchivierung ausgelegt** — PDF/A-2b ohne zusätzliches Flag. Dass die Datei die
  Konformität wirklich einhält, sagt nicht dieses Werkzeug, sondern
  [veraPDF](https://verapdf.org/) — die Referenzimplementierung der PDF Association, in CI bei
  jedem Push. Optional PDF/UA-1 mit `--pdfua`, ebenfalls dort geprüft.
- **Im Gespräch oder im Terminal** — als Claude-Skill oder als CLI, ohne Systeminstallation.

## Woran man sieht, dass es stimmt

Das ist der Teil, an dem sich das Versprechen entscheidet — deshalb steht er vor der Installation.

- **Gemessen wird das fertige PDF**, nicht die Eingabe. `verify` liest das erzeugte Dokument mit
  pdfplumber und vergleicht Zonen, Marken und Abstände gegen die Sollwerte.
- **Jede tragende Prüfung hat eine [Gegenprobe](https://github.com/blitzsicht/falzmarke/blob/main/tests/test_gegenbeweis.py).** Sie läuft gegen ein
  absichtlich verschobenes Layout und muss dort anschlagen — ein Prüfmittel, das nie rot werden
  kann, wäre kein Nachweis. Das gilt auch für das Bild oben: Es entsteht zweimal, einmal aus dem
  ausgelieferten Layout und einmal aus einem, in dem die Marke 2 mm zu tief sitzt.

  ![Ein wechselndes Bild desselben Ausschnitts. Im ersten Zustand liegt die Falzmarke auf der
  gestrichelten Sollinie bei 105,00 Millimetern, darunter steht 105,00 Millimeter und der Hinweis,
  dass so ausgeliefert wird. Im zweiten springt die Marke deutlich nach unten, die Sollinie bleibt
  wo sie war, darunter steht 107,00 Millimeter und der Hinweis, dass verify hier anschlägt.](https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/demo/falzmarke-gegenprobe.gif)

  Unterscheiden sich die beiden Ausschnitte nicht, zeigt der Ausschnitt die Marke gar nicht — dann
  ist das Bild oben wertlos, und `tests/test_detailbild.py` schlägt fehl.
- **CI auf Linux, macOS und Windows**, bei jedem Push.
- **Ein Frischinstallations-Test** führt die Befehle aus dieser README wirklich aus. Hier steht
  kein Befehl, den niemand ausprobiert hat.
- **Alle Beispielbriefe werden in CI gerendert** und vermessen.
- **Die PDF-Konformität bestätigt ein fremdes Werkzeug.** Alles andere auf dieser Liste misst mit
  demselben Code, der das PDF erzeugt hat — das belegt Selbsttreue, nicht Konformität.
  [veraPDF](https://verapdf.org/) hat den Brief nicht geschrieben und teilt keine Zeile mit dem
  Renderer. Geprüft wird, was die Datei selbst deklariert, auf der ausgelieferten Datei, mit
  Prüfsummen-Abgleich — und mit einer Gegenprobe, die ein absichtlich nicht-konformes PDF
  durchfallen lässt ([`scripts/pdf_konformitaet.py`](https://github.com/blitzsicht/falzmarke/blob/main/scripts/pdf_konformitaet.py)).
- **Die Layoutbasis ist vendort und prüfsummengesichert** —
  [`vendor/README.md`](https://github.com/blitzsicht/falzmarke/blob/main/skill/falzmarke/typst/vendor/README.md).

Zwei Aussagen, die gern verwechselt werden, hält das Projekt auseinander:

> **Der Sollwert ist fachlich belegt** und **der Verifier erkennt eine Abweichung davon** sind
> verschiedene Dinge. Das Zweite ist bewiesen. Das Erste hat Grenzen.

**Woher die Sollwerte stammen:** Maße und Schreibregeln folgen öffentlich dokumentierten Quellen
(Liste in [`skill/references/din5008.md`](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/din5008.md)); der Abgleich mit dem
Originaltext der DIN 5008:2020-03 einschließlich Berichtigung 1:2020-07 steht aus. Regeln aus
einzelnen Quellen wirken nur als Warnung. Welche Regel worauf beruht, steht in der
[Quellenlage je Regel](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/din5008.md#quellenlage-je-regel); was daraus rechtlich
folgt, in [`docs/recht.md`](https://github.com/blitzsicht/falzmarke/blob/main/docs/recht.md).

```bash
python3 -m pytest -q
```

## Sicherheit

Genannt wird nur, was im Code steht und geprüft ist. falzmarke ist **nicht** unabhängig
auditiert — Sicherheitsrelevantes bitte nach [SECURITY.md](https://github.com/blitzsicht/falzmarke/blob/main/SECURITY.md), nicht als Issue.

- **Verarbeitung bleibt lokal.** Der Renderpfad importiert keine Netzwerkbibliothek.
- **YAML wird ausschließlich mit `safe_load` gelesen** — an jeder Stelle, auch beim
  eingebetteten Profil.
- **Markdown läuft gegen eine Positivliste** von Knotentypen. Was nicht daraufsteht, ist ein
  Fehler mit Zeilenangabe — nie ein stilles Durchreichen.
- **Brieftext wird nie zu Typst-Code.** Der Emitter übergibt ihn als maskierte Zeichenkette;
  Sonderzeichen können die Struktur nicht verlassen.
- **Profil- und Briefdateien bleiben in ihrem Ordner.** Logo, Unterschrift und eigener Briefkopf
  dürfen nicht darüber hinauszeigen, Symlinks werden aufgelöst
  ([Gegenproben](https://github.com/blitzsicht/falzmarke/blob/main/tests/test_profilgrenze.py)).
- **Typst läuft auf ein eigenes Wurzelverzeichnis begrenzt**, Systemschriften sind abgeschaltet.
- **Alle Abhängigkeiten des Programms sind permissiv lizenziert** —
  [THIRD_PARTY_LICENSES.md](https://github.com/blitzsicht/falzmarke/blob/main/THIRD_PARTY_LICENSES.md).
- **Die CI-Aktionen hängen an vollständigen Commit-SHAs**, nicht an verschiebbaren Tags.

Das Release-Asset lässt sich auf seine Herkunft prüfen:

```bash
gh attestation verify falzmarke.skill --repo blitzsicht/falzmarke
```

Das belegt, aus welchem Lauf und welchem Commit die Datei stammt — **nicht, dass sie fehlerfrei
ist**. Die SHA-256-Summe steht in der Release-Notiz und als `falzmarke.skill.sha256` daneben.

## In 60 Sekunden

Vier Wege, und sie können nicht dasselbe:

| Weg | rendert ohne Netz | Größe | wofür |
|---|---|---|---|
| `falzmarke.skill` hochladen | nein, der erste Lauf lädt nach | ~0,8 MB | claude.ai — der Upload-Dialog nimmt **höchstens 30 MB** |
| `falzmarke-offline.skill` | **ja** — der Typst-Compiler reist mit | ~34 MB | Sandboxen ohne PyPI-Zugriff; **zu groß für den Upload-Dialog** |
| `pipx` / `uvx` | nein, der erste Lauf lädt nach | ~1 MB | Terminal |
| Repository klonen | nein, der erste Lauf lädt nach | ~1 MB | Mitarbeit am Werkzeug |

Die beiden Skill-Pakete unterscheiden sich in genau einer Datei: Das Offline-Paket trägt das
`typst`-Wheel in `vendor/`, das schlanke nicht. Warum es zwei sind und nicht eines, steht in
[`skill/vendor/README.md`](https://github.com/blitzsicht/falzmarke/blob/main/skill/vendor/README.md).

### Mit Claude

1. **[`falzmarke.skill` herunterladen](https://github.com/blitzsicht/falzmarke/releases/latest/download/falzmarke.skill)**
2. In Claude unter Einstellungen › Capabilities hochladen (Tarif mit Code-Ausführung nötig).
   Für Claude Code genügt ein Symlink:
   ```bash
   ln -s "$PWD/skill" ~/.claude/skills/falzmarke
   ```
3. „Schreib einen Brief an die Muster GmbH, Angebot über …"

### Im Terminal

```bash
uvx falzmarke init brief.md --profil example --betreff "Angebot Nr. 2026-0815"
```

oder dauerhaft installiert, danach genügt `falzmarke render brief.md --png`:

```bash
pipx install falzmarke
```

Das Paket liegt auf [PyPI](https://pypi.org/project/falzmarke/). Wer den unveröffentlichten
Stand von `main` will, nimmt weiterhin die Adresse:

```bash
pipx install git+https://github.com/blitzsicht/falzmarke
```

Der Typst-Compiler kommt als Python-Wheel mit: **keine Systeminstallation**, kein LaTeX, kein
wkhtmltopdf, keine Schriftinstallation.

### In einem Repository voller Briefe

Wer seine Briefe versioniert, lässt sie bei jedem Push setzen und nachmessen:

```yaml
- uses: blitzsicht/falzmarke@main
  with:
    briefe: "briefe/*.md"
    profile: "profile"
```

Die PDFs hängen danach als Artefakt am Lauf. Hält ein Brief die Maße nicht ein, wird der Lauf
rot und nennt Datei und Maß — ein Serienbrief-Archiv merkt einen verrutschten Betreff damit
beim Push und nicht beim Empfänger. Die Eingaben stehen in
[`action.yml`](https://github.com/blitzsicht/falzmarke/blob/main/action.yml); die Aktion
installiert falzmarke von PyPI und baut keine zweite Installationsstrecke auf. Wer den Lauf
nachfahrbar halten will, nennt eine feste Fassung: `paket: "falzmarke==0.7.3"`.

### In einem anderen KI-Client

falzmarke spricht MCP — damit setzen auch Clients Briefe, die keinen Claude-Skill kennen.

```bash
pip install 'mcp>=2,<3'          # das SDK ist nicht in der Grundausstattung
falzmarke mcp                    # Server über stdio
```

Drei Werkzeuge: `brief_rendern`, `brief_pruefen`, `profile_auflisten`. Der **Messbericht kommt
bei jedem Rendern mit** — ein Dienst, der ein PDF zurückgibt und offenlässt, ob die Maße
stimmen, wäre ein PDF-Generator wie jeder andere.

Das Absenderprofil darf als Objekt im Aufruf stehen. Ein Client ohne Zugriff auf das
Dateisystem des Servers kann so seinen eigenen Absender mitgeben, statt mit den Profilen zu
leben, die dort zufällig liegen.

Was der Dienst **nicht** tut: versenden, ablegen, zustellen. Er setzt und prüft
([ADR 0029](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0029-falzmarke-ist-werkzeug-kein-kanal.md)).

<details>
<summary>Aus einem Clone, ohne Installation</summary>

```bash
git clone https://github.com/blitzsicht/falzmarke.git
cd falzmarke
python3 skill/scripts/bootstrap.py
python3 skill/scripts/falzmarke.py render examples/brief-form-b.md --png
```

</details>

## Einen Brief schreiben

```markdown
---
profil: example
empfaenger:
  - Muster GmbH
  - Frau Erika Muster
  - Musterstraße 1
  - 12345 Musterstadt
datum: 2026-08-25
betreff: Angebot Nr. 2026-0815 über die Neugestaltung Ihrer Website
anrede: Sehr geehrte Frau Muster,
anlagen:
  - Angebot 2026-0815
---
vielen Dank für Ihre Anfrage vom 20. August 2026. Anbei erhalten Sie unser Angebot.

Die Umsetzung dauert ab Ihrer Freigabe **sieben Werktage**.
```

```bash
python3 skill/scripts/falzmarke.py render brief.md --png
```

Alle Felder stehen im [Datenvertrag](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/frontmatter.md). Ein Feld, das dort nicht
steht, bricht mit Zeilennummer und Vorschlag ab — es wird nie stillschweigend verworfen.

### Was im Brieftext erlaubt ist

Der Text unter dem Frontmatter ist **falzmarke-Markdown**, eine dokumentierte Teilmenge von
[CommonMark](https://commonmark.org/):

| Das geht | Das erledigt falzmarke selbst |
|---|---|
| Absätze, `**fett**`, `*kursiv*` | `z. B.`, `10 %`, `§ 5` bekommen geschützte Leerzeichen |
| Aufzählungen und nummerierte Listen | `--` wird zum Halbgeviertstrich – so |
| Harter Umbruch mit `\` am Zeilenende | `"Wort"` wird zu „Wort“ |
| Pipe-Tabellen mit Ausrichtung | Tag und Monat bleiben zusammen: `25. August` |

Links, Bilder und HTML sind **Fehler** — mit Zeile, Grund und Korrektur, nie
stillschweigend. Auf Papier gibt es keinen Link, und ein Bild im Fließtext verschöbe die
Geometrie, die danach gemessen wird.

**Zwischenüberschriften** (`#` bis `####`), tiefere Aufzählungen, **Blockzitate** und
**wortgetreue Auszüge** gibt es für lange Schreiben: `dialekt: "1.1"` im Frontmatter schaltet
sie frei. Ein Auszug bleibt Zeichen für Zeichen stehen — keine typografischen Ersetzungen,
kein Umbruch, keine Einfärbung, und nichts darin wird ausgeführt. Ohne das Feld gilt Fassung 1.0, und ein
bestehender Brief rendert unverändert.

Die vollständige Liste: [falzmarke-Markdown](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/markdown.md).

## Dieselbe Datei als E-Mail

Ein Schreiben mit `typ: email` im Frontmatter wird keine PDF-Seite, sondern eine `.eml` —
dieselbe Quelle, dasselbe Profil, dieselbe Signatur.

```bash
falzmarke email nachricht.md --html
```

```
OK  geschrieben: nachricht.eml
OK  geschrieben: nachricht.html
OK  verify: 22/22 Prüfungen bestanden
```

Die `.eml` öffnet das Mailprogramm, die `.html` der Browser. Mit `--oeffnen` übergibt falzmarke
die fertige Nachricht gleich dem Programm, das im System für `.eml` eingetragen ist — erst nach
bestandener Prüfung, und ohne selbst ein Programm auszusuchen. Sie erscheint dort als
Lesefenster, nicht als Entwurf; das ist eine Eigenschaft des Formats und in drei Programmen
nachgemessen. Geprüft wird die **fertige Datei**:
MIME-Aufbau, `format=flowed`, Space-Stuffing, die Signaturtrennzeile, und ob im HTML nichts
steht, was dort nicht hingehört — kein Skript, kein externes Stylesheet, kein Zählpixel, keine
Tabelle als Layout. `falzmarke verify --email` misst auch Dateien, die von woanders kommen.

**falzmarke versendet nichts.** Es gibt keinen Versandbefehl und keine Option, die sendet: Wer
eine Datei erzeugt, haftet für ihren Inhalt; wer sie befördert, für Zustellung und Nachweis. Das
sind zwei Versprechen, und falzmarke gibt nur das erste
([ADR 0034](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0034-email-ist-ausgabe.md)). Öffnen ist davon nicht berührt und geht auch keinen
Schritt weiter: eine Datei ans Betriebssystem übergeben — kein Entwurf, keine Steuerung des
Mailprogramms
([ADR 0038](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0038-oeffnen-ist-kein-versand.md)).

Wie die Datei aufgebaut ist, was bewusst fehlt und wo die Grenzen liegen:
[Die E-Mail-Fassung](https://github.com/blitzsicht/falzmarke/blob/main/docs/email.md). Vier
Beispiele liegen unter
[`examples/email/`](https://github.com/blitzsicht/falzmarke/tree/main/examples/email/).

## Beispiele

| Standardbrief | Einschreiben | Mehrseitig |
|---|---|---|
| ![Form B](https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/demo/gallery-standard.png) | ![Vermerkzone](https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/demo/gallery-einschreiben.png) | ![Folgeseiten](https://github.com/blitzsicht/falzmarke/raw/main/docs/assets/demo/gallery-mehrseitig.png) |
| Form B mit Informationsblock | Zusatz- und Vermerkzone | Kopfzeile und Seitenzählung |

Dazu Form A, Auslandsanschrift, Tabelle, ein Brief mit langem Informationsblock und einer
mit englischer Beschriftung (`sprache: en` — deutsche Maße, englische Wörter) —
[alle Beispiele](https://github.com/blitzsicht/falzmarke/tree/main/examples/) und ihre [vollständigen Renderings](https://github.com/blitzsicht/falzmarke/tree/main/docs/renders/).

## Grenzen

- **[falzmarke-Markdown](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/markdown.md) (CommonMark-Teilmenge)**: Absätze,
  fett, kursiv, Aufzählungen, nummerierte Listen, harter Umbruch, Pipe-Tabellen. Alles andere
  bricht mit Zeilenangabe ab, statt still etwas anderes zu setzen.
- **Zonengrößen der Norm**: Anschrift höchstens 6 Zeilen, Vermerke höchstens 3, Werte im
  Informationsblock höchstens 32 Zeichen.
- **Keine Bilder im Fließtext** — ein Logo gehört ins Profil.
- **Nur DIN 5008.** Schweiz (SN 010130) und Österreich (ÖNORM A 1080) sind vorgemerkt
  ([#10](https://github.com/blitzsicht/falzmarke/issues/10)); das Frontmatter-Feld `norm:` ist
  dafür reserviert.
- **Keine Signatur.** Das Unterschriftsbild ist Erscheinungsbild, kein Nachweis. Eine
  kryptografische Signatur ist Gegenstand von
  [#14](https://github.com/blitzsicht/falzmarke/issues/14).

## Weiterlesen

| | |
|---|---|
| [Befehle](https://github.com/blitzsicht/falzmarke/blob/main/docs/cli.md) | alle Unterbefehle, Exit-Codes, was geprüft wird |
| [Absenderprofile](https://github.com/blitzsicht/falzmarke/blob/main/docs/profiles.md) | Profil anlegen, Suchreihenfolge, eigener Briefkopf |
| [Die E-Mail-Fassung](https://github.com/blitzsicht/falzmarke/blob/main/docs/email.md) | Aufbau der `.eml`, ihre Teile und Grenzen |
| [Datenvertrag](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/frontmatter.md) | jedes Frontmatter-Feld mit Beispiel |
| [falzmarke-Markdown](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/markdown.md) | was im Brieftext möglich ist |
| [Normmaße und Quellenlage](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/din5008.md) | Sollwerte und ihre Herkunft |
| [Was falzmarke behauptet — und was nicht](https://github.com/blitzsicht/falzmarke/blob/main/docs/recht.md) | Grenzen der Normaussage |
| [Aufbau des Repositorys](https://github.com/blitzsicht/falzmarke/blob/main/docs/architecture.md) | Schichten, Vendoring, warum das Paket unter `skill/` liegt |
| [Roadmap](https://github.com/blitzsicht/falzmarke/blob/main/docs/ROADMAP.md) | in welcher Reihenfolge gearbeitet wird, und was noch offen ist |
| [Changelog](https://github.com/blitzsicht/falzmarke/blob/main/CHANGELOG.md) · [Releases](https://github.com/blitzsicht/falzmarke/releases) | was sich geändert hat |

## Mitmachen

Fehlerberichte und Vorschläge sind willkommen — siehe [CONTRIBUTING.md](https://github.com/blitzsicht/falzmarke/blob/main/CONTRIBUTING.md).
Bei einem Geometriefehler bitte die Ausgabe von `verify` mitschicken; ohne sie lässt sich nicht
unterscheiden, ob das Layout oder die Messung danebenliegt.

Sicherheitsrelevantes bitte nicht als Issue, sondern nach [SECURITY.md](https://github.com/blitzsicht/falzmarke/blob/main/SECURITY.md).

## Herkunft und Dank

**Markdown** wurde 2004 von [John Gruber](https://daringfireball.net/projects/markdown/) gemeinsam
mit Aaron Swartz entworfen. Die Spezifikation dazu ist [CommonMark](https://commonmark.org/)
(John MacFarlane und Mitwirkende). falzmarke setzt eine dokumentierte Teilmenge davon um
— **[falzmarke-Markdown](https://github.com/blitzsicht/falzmarke/blob/main/skill/references/markdown.md)** — und weicht an drei Stellen bewusst
ab: HTML wird nie durchgereicht, Links werden nie gesetzt, und eine einzelne `2. Text`-Zeile
ohne weitere Listenpunkte wird gemeldet — gesetzt mit erhaltenem Startwert, damit nichts still
umnummeriert wird.

Das **Seitenlayout** stammt von [typst-letter-pro](https://github.com/Sematre/typst-letter-pro)
(MIT) von Sematre und ist unverändert vendort — Prüfsumme in
[`vendor/README.md`](https://github.com/blitzsicht/falzmarke/blob/main/skill/falzmarke/typst/vendor/README.md). falzmarke ergänzt die Schicht
darüber: Datenvertrag, Profile, Markdown-Eingabe, Messung und den Skill.

Gesetzt wird mit [Typst](https://typst.app) (Apache-2.0), geparst mit
[markdown-it-py](https://github.com/executablebooks/markdown-it-py) (MIT), gemessen mit
[pdfplumber](https://github.com/jsvine/pdfplumber) (MIT) und
[pypdf](https://github.com/py-pdf/pypdf) (BSD-3). Schriften: Libertinus und Source Sans 3
(beide OFL 1.1). Die vollständige Aufstellung samt der Begründung, warum PyMuPDF (AGPL-3.0)
ersetzt wurde, steht in [THIRD_PARTY_LICENSES.md](https://github.com/blitzsicht/falzmarke/blob/main/THIRD_PARTY_LICENSES.md).

**Alle Abhängigkeiten des Programms sind permissiv lizenziert** — falzmarke lässt sich damit
auch in geschlossene Systeme einbauen. Nicht permissiv ist allein
[Remotion](https://www.remotion.dev), womit der Erklärfilm gerendert wird: am Programm ist es
nicht beteiligt und wird nicht mitgeliefert.

**DIN 5008** ist eine Norm des DIN Deutsches Institut für Normung e. V. falzmarke ist kein
Produkt des DIN, steht in keiner Verbindung zum DIN und behauptet keine Zertifizierung. Wie die
Maße gemessen wurden, steht in [`docs/normmasse.md`](https://github.com/blitzsicht/falzmarke/blob/main/docs/normmasse.md).

<!-- changelog:anfang -->

## Was sich zuletzt getan hat

Die letzten zwei Versionen im Wortlaut. **Erzeugt aus [`CHANGELOG.md`](https://github.com/blitzsicht/falzmarke/blob/main/CHANGELOG.md) — dort ändern, dann `python3 scripts/changelog.py`.**

### v0.9.3 — 04.09.2026

#### Neu

- **`falzmarke email --oeffnen` übergibt die fertige Nachricht dem Standardprogramm.** Bisher
  endete der Befehl damit, dass ein Pfad im Terminal stand; wer die `.eml` ansehen oder
  weiterleiten wollte, suchte sie im Dateimanager. Das Flag erspart diesen Weg — und sonst
  nichts: Es übergibt eine Datei an das Betriebssystem, sucht keine Anwendung aus und steuert
  kein Mailprogramm. Übergeben wird erst nach bestandener Prüfung, ohne Flag öffnet nichts, und
  ein Fehlschlag beim Öffnen lässt den Exit-Code bei 0 — die Nachricht ist ja geschrieben und
  gemessen. Dass sie im Mailprogramm als Lesefenster erscheint und nicht als Entwurf, bleibt
  wahr und steht in der Doku; der nächste Handgriff heißt weiterhin „Weiterleiten"
  ([ADR 0038](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0038-oeffnen-ist-kein-versand.md)). (#239)

- **`bcc:` im Frontmatter einer E-Mail.** Ein verbreitetes Muster in der Geschäftskorrespondenz
  ist eine Archivadresse im Blindverteiler, über die jede ausgehende Mail im
  Dokumentenmanagement landet. Bisher kannte der Datenvertrag nur `an:` und `cc:`, und die
  Adresse musste im Mailprogramm bei jeder einzelnen Nachricht von Hand nachgetragen werden —
  wird sie einmal vergessen, ist die Mail trotzdem raus und sieht in jeder Hinsicht erledigt
  aus, nur existiert kein Beleg.

  Die Adresse steht jetzt als `Bcc:` in der `.eml` und wird wie `an:` und `cc:` auf ihre Form
  geprüft. **In der `.html`-Vorschau erscheint sie nicht:** Die ist zum Ansehen und
  Herauskopieren da, und eine sichtbare Zeile „Blindkopie" ginge beim Kopieren mit — das Feld
  täte dann das Gegenteil dessen, wofür es da ist. `verify --email` misst eigens, dass keine
  ihrer Adressen im Text- oder HTML-Teil vorkommt.

  Ob ein Mailprogramm die Kopfzeile beim Weiterleiten übernimmt, entscheidet das Programm;
  falzmarke versendet nicht (ADR 0034) und kann es deshalb nicht zusagen. Der Befehl nennt die
  Adresse beim Erzeugen darum eigens — wer die Zeile liest, sieht im Programm nach, statt den
  Blindverteiler für erledigt zu halten.

  In einem Brief gibt es `bcc:` nicht. Anders als `cc:`, das dort `verteiler:` heißt, bekommt es
  keinen Ersatzvorschlag: Wer eine Kopie erhält, ohne im Verteiler zu stehen, ist auf Papier
  nicht vorgesehen. (#242)

#### Geändert

- **Der Skill löst jetzt auch bei E-Mails aus.** Seine Beschreibung nannte ausschließlich
  Papier — Brief, Kündigung, Mahnung, „etwas zum Ausdrucken oder Verschicken" — und kein
  einziges E-Mail-Wort. Da ein Assistent den Skill allein über Name und Beschreibung
  vorauswählt, war die seit v0.8.0 fertige E-Mail-Fassung im Auslösepfad unsichtbar: Wer
  „schreib eine E-Mail an …" sagte, bekam eine frei getippte Nachricht statt einer geprüften
  `.eml`. Die Beschreibung nennt jetzt beide Ausgaben, führt die Auslöser für Mails mit und
  verbietet die selbstgebaute Nachricht so ausdrücklich, wie sie den frei gesetzten Brief
  schon verbot. (#238)

- **Der Name in der Signatur trägt jetzt Gewicht.** Er stand in derselben Größe da wie die
  Umsatzsteuer-Nummer drei Zeilen tiefer, und das Auge fand keinen Anker — beim Vergleich mit
  einem fremden Signaturgenerator fiel das als Erstes auf. Die erste Zeile des ersten Blocks
  ist jetzt 18px und halbfett. Bewusst ohne Akzentfarbe: Die Signatur gehört dem Absender,
  nicht dem Werkzeug, und eine profilabhängige Farbe kann nicht in den Dunkelregeln stehen —
  der Block ist eine Konstante, die zeichenweise verglichen wird. Größe und Gewicht tragen auf
  hellem wie auf dunklem Grund, ohne eine einzige Farbe zu setzen. (#243)

#### Behoben

- **Jede Nachricht trägt jetzt ein `Date`.** Bisher fehlte die Kopfzeile — außer bei gesetztem
  `SOURCE_DATE_EPOCH` —, weil das Datum beim Versand entstehen sollte. Diese Begründung setzte
  voraus, dass das Mailprogramm die `.eml` als Entwurf übernimmt und den Zeitpunkt selbst
  einsetzt; nach der eigenen Messung in `docs/mailprogramme-2026-08-27.md` tut das keines der
  drei geprüften Programme. Der gangbare Weg ist „Weiterleiten", und dabei baut das Programm
  den zitierten Kopf aus den Feldern der Quelle: Das fehlende Feld erschien dort als
  `Datum: (null), (null)` und ging mit raus. RFC 5322, Abschnitt 3.6, führt `orig-date`
  ohnehin als Pflichtfeld. `SOURCE_DATE_EPOCH` behält den Vorrang und bleibt der Weg zum
  Golden-Vergleich; ohne die Variable steht der Zeitpunkt der Erzeugung in der Datei. Der
  eigentliche Befund war dabei der zweite: **`verify --email` meldete solche Dateien grün.**
  Die Prüfung misst jetzt beides — dass `Date` vorhanden und dass es nach RFC 5322 lesbar ist.
  (#236)

- **Profilangaben wirken nicht mehr still falsch.** Zwei Fälle aus einem echten Briefbau, beide
  daran erkennbar, dass das Werkzeug grün meldete und trotzdem etwas anderes tat als gemeint.

  `briefkopf.logo_hoehe_mm` ohne `briefkopf.logo` wirkt nie — die Höhe gehört zu einem Logo,
  das es nicht gibt. `lint` sagt das jetzt als Warnung; ein Fehler wäre es nicht, denn die Höhe
  kann für ein später ergänztes Logo schon dastehen. Der erste Treffer war das mitgelieferte
  `example.yaml` selbst, wo die Höhe aktiv neben einem auskommentierten `logo:` stand; beide
  sind jetzt auskommentiert.

  Der zweite Fall betrifft die Wertespalte des Informationsblocks. Ein zu langer Wert brach den
  Lauf mit einer Meldung ab, die nur das letzte Wort des überstehenden Textes nannte — nicht
  das Feld, aus dem es stammt. Kommt der Wert aus `infoblock_defaults:` des Profils, steht er
  nicht einmal in der Briefdatei, in der man ihn dann sucht. Die Meldung nennt jetzt Feld und
  Herkunft (`infoblock_defaults.ansprechpartner im Profil`), und rutscht ein Wert doch bis zum
  Prüfer am fertigen PDF durch, ordnet der den Überlauf der Wertespalte zu.

  Beim Nachmessen stellte sich heraus, dass die Grenze selbst zu hoch war: **21 Zeichen statt
  32.** Die alte Zahl kam aus „43 mm Spaltenbreite, 1,24 mm je Zeichen", und beides war zu groß
  — die Spalte beginnt bei 157 mm und der Satzspiegel endet bei 190, nutzbar sind also 33 mm,
  und ein Name braucht rund 1,55 mm je Zeichen statt 1,24. Schon „Dr. Anna Meyer-Schmidt" (22
  Zeichen) riss den Rand, ohne beanstandet zu werden. Beide Kopien der Konstanten sind dabei zu
  einer zusammengeführt; sie standen unabhängig in `cli.py` und `lint.py`, ohne dass ein Test
  sie zusammenhielt. (#244)

- **Die Warnung zu `datum:` in einer E-Mail erklärte das Gegenteil dessen, was geschieht.** Sie
  sagte „der Mailclient setzt es beim Versand" — seit der `Date`-Kopfzeile (#236) setzt
  falzmarke den Zeitpunkt selbst. Der Hinweis, dass das Feld in einer Mail nichts bewirkt,
  bleibt richtig; nur seine Begründung stimmte nicht mehr. Betroffen waren neben dem Nutzertext
  vier weitere Stellen mit derselben Aussage, darunter `references/frontmatter.md`, aus dem auch
  das Sprachmodell liest.

  Dabei kam ein Test heraus, der nie rot werden konnte: Er verglich die Kopfzeile mit der
  Zeichenkette `2026-08-29`, die ein RFC-5322-Datum (`Sat, 29 Aug 2026 …`) gar nicht enthalten
  kann. Er liest das Datum jetzt und hält es gegen den Tag des Briefes. (#249)

### v0.9.2 — 02.09.2026

#### Infrastruktur

- **Ein Vorgang ohne Changelog-Eintrag lässt sich nicht mehr mergen.** Von 46 Vorgängen
  zwischen v0.8.2 und v0.9.0 hatte **einer** `CHANGELOG.md` angefasst; nach dem Nachtragen von
  39 Einträgen von Hand waren es bei den nächsten vier wieder null. Der Grund war strukturell:
  Es gab keinen Ort für einen Eintrag ohne Version. Den gibt es jetzt — je Vorgang eine Datei
  in `changelog.d/`, die beim Release zu einem Versionsabschnitt gebündelt wird
  (`scripts/changelog.py --buendeln`). Der Pflicht-Check „Changelog-Eintrag" verlangt sie;
  ausgenommen sind Abhängigkeits-Aktualisierungen, reine Doku, reine Tests und Vorgänge mit
  dem Label `ohne-changelog`. (#229)

- **Der Sammelpunkt für Abhängigkeits-Aktualisierungen entsteht von selbst.** Sie sind vom
  Changelog-Eintrag ausgenommen, und ADR 0037 versprach, sie erschienen beim Release „als
  Sammelpunkt" — den aber niemand schrieb: Er stand in keiner Anleitung, kein Werkzeug verlangte
  ihn. Damit war die Bauart wiederhergestellt, gegen die #229 gebaut wurde. Jetzt liest
  `scripts/changelog.py --buendeln` den git-Verlauf seit dem letzten Versions-Tag und erzeugt den
  Punkt selbst. Ist der Verlauf nicht lesbar, bricht es ab, statt stillschweigend nichts zu
  melden. (#233)

- **Abhängigkeiten aktualisiert.** action-gh-release von 2.6.2 auf 3.0.3 (#222)

Davor liegen 21 weitere Versionen — der vollständige Verlauf steht in [`CHANGELOG.md`](https://github.com/blitzsicht/falzmarke/blob/main/CHANGELOG.md).

<!-- changelog:ende -->

## Lizenz

[MIT](https://github.com/blitzsicht/falzmarke/blob/main/LICENSE)
