# normbrief

Geschäftsbriefe nach **DIN 5008** aus Markdown — mit nachgemessener Geometrie.

Ein Brief entsteht aus einer Markdown-Datei mit YAML-Frontmatter. Gerendert wird über
[Typst](https://typst.app) mit der vendorten Layout-Vorlage
[`letter-pro` 3.0.0](https://typst.app/universe/package/letter-pro) (MIT). Das Ergebnis ist ein
PDF, auf Wunsch PDF/A-2b für Paperless und GoBD.

Der Unterschied zu einer Briefvorlage: **die Maße werden geprüft, nicht behauptet.**
`normbrief.py check` vermisst das fertige PDF mit PyMuPDF gegen die DIN-Tabelle — Falzmarken,
Lochmarke, Anschriftzone, Informationsblock, Satzspiegel. Weicht etwas ab, ist der Exit-Code
ungleich null.

## Stand

**In Arbeit.** Renderer, Markdown-Konverter und Geometrie-Vermessung stehen; Testsuite,
Referenzdokumentation und CI fehlen noch. Der vollständige Plan liegt in `docs/plan.md`.

## Benutzung

```bash
pip install -r skill/requirements.txt

python skill/scripts/normbrief.py render examples/brief-form-b.md -o brief.pdf
python skill/scripts/normbrief.py check  brief.pdf --form B
python skill/scripts/normbrief.py preview examples/brief-form-b.md -o brief.png
```

Exit-Codes: `0` ok · `1` Eingabefehler · `2` Geometrie-Check gescheitert · `3` Umgebung.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `skill/` | der Claude-Skill — in sich geschlossen, ohne den Rest des Repos lauffähig |
| `skill/scripts/normbrief.py` | CLI: `render`, `check`, `preview`, `profiles`, `init` |
| `skill/typst/vendor/` | `letter-pro-v3.0.0.typ`, vendort statt zur Laufzeit geladen |
| `examples/` | Beispielbriefe als Markdown |
| `tests/` | Geometrie-, Konverter- und CLI-Tests |
| `docs/plan.md` | Spezifikation samt Recherche und Messwerten |

## Profile

Ein Profil hält Absender, Briefkopf und Fußzeile. `skill/typst/profiles/example.yaml` zeigt alle
Felder. **Echte Absenderdaten gehören nicht in dieses Repo** — sie kommen nach
`skill/typst/profiles.local/` (gitignoriert) oder in ein privates Repo. Der Suchpfad lässt sich
über `NORMBRIEF_PROFILES` übersteuern.

## Lizenz

MIT — siehe [LICENSE](LICENSE). Die vendorte Vorlage `letter-pro` steht ebenfalls unter MIT,
ihre Lizenz liegt unter `skill/typst/vendor/LICENSE-letter-pro`.
