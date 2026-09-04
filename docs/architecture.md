# Aufbau des Repositorys

```
skill/                      der Claude-Skill, in sich lauffähig
├── SKILL.md                Anleitung für den Agenten
├── scripts/                Einstiegspunkte ohne Installation
├── falzmarke/              das Python-Paket
│   ├── cli.py              Befehle, Profilauflösung, Renderlauf
│   ├── lint.py             Prüfung vor dem Setzen, Datenvertrag
│   ├── markdown.py         CommonMark-Teilmenge, Positivliste
│   ├── emit.py             Typst-Ausgabe als maskierte Zeichenketten
│   ├── geometrie.py        Messung am fertigen PDF
│   ├── typografie.py       Schreibregeln der Norm
│   ├── regeln/             Quellenlage je Regel (din5008.yaml)
│   ├── typst/
│   │   ├── falzmarke.typ   Layout-Wrapper
│   │   ├── vendor/         letter-pro v3.0.0 (MIT), unverändert
│   │   └── profiles/       Beispielprofile
│   └── assets/fonts/       Source Sans 3 (OFL)
└── references/             DIN-Maße, Stilregeln, Datenvertrag, Markdown-Teilmenge
examples/                   Beispielbriefe, die die Testsuite rendert
tests/                      Geometrie, Gegenproben, Datenvertrag, CLI, Profilsuche
docs/                       Herkunft der Maße, Recht, Befehle, Profile
scripts/quellenlage.py      erzeugt den Quellenlage-Abschnitt der Normreferenz
```

## Warum das Paket unter `skill/` liegt

Derselbe Ordner wird als Claude-Skill ausgeliefert und als Python-Paket installiert. Zwei
Kopien wären zwei Fassungen, die auseinanderlaufen — deshalb `package-dir = {"" = "skill"}`
in `pyproject.toml`.

Folge: Das Paket muss **ohne Installation lauffähig** bleiben. `skill/scripts/falzmarke.py`
ruft es direkt auf, ohne dass etwas eingerichtet sein müsste.

## Die Schichten

| Schicht | Aufgabe | Darf nicht |
|---|---|---|
| `lint` | Eingabe prüfen | rendern |
| `markdown` → `emit` | Brieftext in Typst-Aufrufe übersetzen | Sonderzeichen durchreichen |
| `typst/falzmarke.typ` | Layout setzen | Werte erfinden |
| `geometrie` | fertiges PDF messen | das PDF verändern |
| `oeffnen` | eine fertige Datei ans Betriebssystem übergeben | etwas erzeugen, prüfen oder ein Programm steuern |

`oeffnen` ist die einzige Schicht mit einer Wirkung außerhalb des Prozesses und deshalb das
einzige Modul, das `subprocess` einbindet — nachgemessen in `tests/test_befehl_email.py`. Es
wird spät und nur aus der Befehlsschicht importiert: `dienst` lädt `cli` auf Modulebene, ein
Import weiter oben läge damit in jedem MCP-Prozess ([ADR 0038](entscheidungen/0038-oeffnen-ist-kein-versand.md)).

Die Sollwerte stehen an **einer** Stelle (`falzmarke/regeln/din5008.yaml`) und gelten für
Prüfung und Testsuite gemeinsam. Die Normreferenz
[`skill/references/din5008.md`](../skill/references/din5008.md) wird daraus erzeugt — dort
niemals von Hand ändern, sondern `python3 scripts/quellenlage.py` ausführen.

## Vendorte Layoutbasis

`skill/falzmarke/typst/vendor/letter-pro-v3.0.0.typ` ist eine unveränderte Kopie von
[typst-letter-pro](https://github.com/Sematre/typst-letter-pro) (MIT), prüfsummengesichert in
[`vendor/README.md`](../skill/falzmarke/typst/vendor/README.md).

Weil falzmarke damit *setzt*, zählt die Datei in der Quellenlage **nicht** als unabhängige
Bestätigung eines Sollwerts — ein Wert von dort würde gegen ein PDF geprüft, das dieselbe
Quelle erzeugt hat. Siehe [`docs/recht.md`](recht.md).

## Verwandt

- [Befehle](cli.md) · [Absenderprofile](profiles.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Arbeitsweise, Tests, Pull Requests
