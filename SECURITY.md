# Sicherheit

## Melden

Sicherheitsrelevante Funde bitte **nicht** als öffentliches Issue, sondern an
**servus@blitzsicht.com**. Antwort in der Regel innerhalb von drei Werktagen.

*English: please report security findings privately to servus@blitzsicht.com rather than in a
public issue. Reports in English are fine. The attack surface is described below in German; the
short version: front matter is parsed with `yaml.safe_load`, letter text is emitted as a Typst
string literal rather than as markup, and profile assets must stay inside the profile's own
directory. A way around any of those is a finding.*

## Wo die Angriffsfläche liegt

falzmarke verarbeitet Dateien, die es nicht selbst geschrieben hat, und gibt sie an einen
Compiler weiter. Interessant sind deshalb vor allem:

- **Frontmatter** wird mit `yaml.safe_load` gelesen — nie mit `load`.
- **Brieftext** wird nach Typst-Markup übersetzt. Der Text wird dabei als Typst-**Zeichenkette**
  ausgegeben, nicht Sonderzeichen für Sonderzeichen escaped
  ([`skill/falzmarke/markdown.py`](skill/falzmarke/markdown.py)), und der Markdown-Parser läuft
  gegen eine Positivliste von Knotentypen. Ein Weg, durch eines von beidem Typst-Code
  einzuschleusen, wäre ein Fund.
- **Profilpfade, Logos und Unterschriftsbilder** werden relativ zur Profildatei aufgelöst und
  müssen **im Profilordner bleiben** (Unterordner sind erlaubt). `resolve()` läuft zuerst, ein
  nach außen zeigender Symlink wird also ebenfalls abgewiesen. Das zählt, weil ein Brief sein
  Profil im eigenen Frontmatter mitbringen darf — dann stammt das Profil von dem, der den Brief
  geschickt hat. Bis v0.3.1 gab es diese Prüfung für `briefkopf_typ`, aber nicht für `logo` und
  `signatur`; siehe [`docs/angriff-2026-08-25.md`](docs/angriff-2026-08-25.md). Ein Weg aus
  diesem Verzeichnis heraus ist ein Fund.
- **Typst** kompiliert in einem eigenen Wurzelverzeichnis und liest nichts darüber hinaus.
  Systemschriften sind abgeschaltet (`ignore_system_fonts`), ein Dokument kann also keine
  Schriften vom Rechner nachladen.

## Was kein Sicherheitsfund ist

- Ein Brief mit falscher Geometrie — das ist ein Fehler, bitte als Issue melden.
- Zugangsdaten in einem eigenen Profil: Profile gehören nach `~/.config/falzmarke/profiles/` und
  nicht in ein öffentliches Repository. Der mitgelieferte Suchpfad trennt beides bewusst.
- Das Wort `normbrief` in `skill/falzmarke/typst/vendor/letter-pro-v3.0.0.typ`. Es steht dort in
  einer URL der Deutschen Post, in einer Fremddatei, die byteweise unverändert bleibt und per
  Prüfsumme bewacht wird.

## Unterstützte Fassungen

Fixes gibt es nur für die jeweils neueste Veröffentlichung. Einen Wartungszweig für ältere
Fassungen gibt es nicht.
