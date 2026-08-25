# Absenderprofile

Ein Profil ist eine YAML-Datei mit Briefkopf, Fußzeile, Rücksendeangabe und Voreinstellungen.
Es wird einmal angelegt und gilt für alle Briefe, die darauf zeigen.

```bash
python3 skill/scripts/falzmarke.py init-profil meinefirma
```

Das legt eine ausgefüllte Vorlage unter `~/.config/falzmarke/profiles/` an — **außerhalb der
Installation**, damit sie ein Update übersteht.

Alle Felder mit Beispielen stehen im
[Datenvertrag](../skill/references/frontmatter.md#profildatei).

## Wo gesucht wird

In dieser Reihenfolge, das erste Treffer gewinnt:

1. `--profiles VERZEICHNIS`
2. Umgebungsvariable `FALZMARKE_PROFILES`
3. `./profiles/` — zum Vorgang gehörend, neben dem Brief
4. `~/.config/falzmarke/profiles/`
5. die mitgelieferten Beispiele

Die dritte Stelle ist die nützliche für Projekte: Ein Ordner mit Briefen und einem
`profiles/`-Unterordner ist in sich vollständig und lässt sich weitergeben.

## Drei Wege, einen Absender anzugeben

| Weg | Wann |
|---|---|
| `profil: meinefirma` | Normalfall — Name eines Profils aus der Suchreihenfolge |
| `profil: ./profile/firma.yaml` | Pfad, relativ zum Brief |
| Felder direkt im Frontmatter | auf claude.ai, wo kein Verzeichnis den nächsten Chat überlebt |

Für den letzten Fall erzeugt `falzmarke.py pack --profil meinefirma` ein Skill-Zip mit
eingebackenem Absender. **Achtung:** Diese Datei enthält Anschrift, Bankverbindung und
Registerangaben — sie gehört nicht in ein öffentliches Repository.

## Bilder im Profil

`briefkopf.logo:` und `signatur:` zeigen auf Dateien **neben der Profildatei**. Ein Profil mit
Bildern lässt sich deshalb nur samt seinem `assets`-Ordner an einen anderen Ort kopieren.

Die Ordnergrenze ist eine Sicherheitsgrenze, keine Konvention: Ein Brief kann sein Profil im
Frontmatter mitbringen, und dann stammt beides von dem, der den Brief geschickt hat. Ohne
Grenze bettete ein fremder Brief jede Bilddatei ein, die der Empfänger lesen kann. Symlinks
helfen dabei nicht — der Pfad wird aufgelöst.

Die Unterschrift lässt sich je Brief überschreiben: `signatur: keine` lässt drei Leerzeilen
Raum zum Unterschreiben von Hand, eine Dateiangabe setzt ein anderes Bild. Die Datei liegt dann
neben dem **Brief**, nicht neben dem Profil.

## Eigener Briefkopf

Wer den Briefkopf frei gestalten will, setzt `briefkopf_typ: meinkopf.typ` und legt daneben
eine Typst-Datei mit einer Funktion `briefkopf(profil)` — Beispiel:
[`example-kopf.typ`](../skill/falzmarke/typst/profiles/example-kopf.typ).

Das Anschriftfeld bleibt davon unberührt; seine Höhe erzwingt das Layout, damit der Brief im
Fensterumschlag lesbar bleibt. Für alles andere reicht YAML.

## Verwandt

- [Datenvertrag: das Frontmatter](../skill/references/frontmatter.md)
- [Befehle](cli.md)
