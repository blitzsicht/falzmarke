# Sicherheit

## Melden

Sicherheitsrelevante Funde bitte **nicht** als öffentliches Issue, sondern an
**servus@blitzsicht.com**. Antwort in der Regel innerhalb von drei Werktagen.

## Wo die Angriffsfläche liegt

falzmarke verarbeitet Dateien, die es nicht selbst geschrieben hat, und gibt sie an einen Compiler
weiter. Interessant sind deshalb vor allem:

- **Frontmatter** wird mit `yaml.safe_load` gelesen — nie mit `load`.
- **Brieftext** wird nach Typst-Markup übersetzt; alle Sonderzeichen werden escaped
  ([`markdown_typst.py`](skill/scripts/markdown_typst.py)). Ein Weg, darin Typst-Code
  unterzubringen, wäre ein Fund.
- **Profilpfade und Logos** werden relativ zur Profildatei aufgelöst und in ein temporäres
  Arbeitsverzeichnis kopiert. Ein Weg aus diesem Verzeichnis heraus wäre ein Fund.
- **Typst** kompiliert in einem eigenen Wurzelverzeichnis und liest nichts darüber hinaus.

## Was kein Sicherheitsfund ist

- Ein Brief mit falscher Geometrie — das ist ein Fehler, bitte als Issue melden.
- Zugangsdaten in einem eigenen Profil: Profile gehören nach `~/.config/falzmarke/profiles/`
  und nicht in ein öffentliches Repository. Der mitgelieferte Suchpfad trennt beides bewusst.
