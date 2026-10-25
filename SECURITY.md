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
- **Das Entwurfsbuch** (`~/.local/state/falzmarke/entwuerfe.jsonl`, Pfad über
  `FALZMARKE_ENTWURFSBUCH`, `nie` schaltet es ab) merkt sich zu jedem Entwurf, den
  `--oeffnen` ins Postfach legt, Konto, Empfänger und **den Brieftext im Klartext**. Es wird
  mit 0600 in einem Ordner mit 0700 angelegt, über `os.open` mit `O_NOFOLLOW` geschrieben,
  und Zeilen älter als 56 Tage verlassen es beim Schreiben. Ein Weg, darüber in eine fremde
  Datei zu schreiben oder es für andere Konten lesbar zu machen, wäre ein Fund.
- **Der Horchposten der Entwurfsbrücke.** Das Add-on in Thunderbird
  (`thunderbird/entwurfsbruecke/`) nimmt Zurufe von falzmarke an: eine Zeile JSON über einen
  **Unix-Socket im Thunderbird-Profil** mit Rechten 0600. Es kann einen Entwurf öffnen, offene
  Verfassen-Fenster melden (samt Betreff, Empfängern und Text) und sein Protokoll herausgeben —
  senden, löschen oder verschieben nicht. Bis 0.3.0 lief das über einen Port auf 127.0.0.1;
  dort kam jeder Prozess jedes Kontos des Rechners heran (ADR 0059). Ein Weg, ohne die Rechte
  an diesem Socket eine Antwort zu bekommen, wäre ein Fund.
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
