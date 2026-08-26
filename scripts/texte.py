#!/usr/bin/env python3
"""Erzeugt aus dem Textkanon die lesbare Fassung und die Szenendatei des Films.

Der Kanon wird an genau einer Stelle gepflegt: `docs/marke/texte.yaml`. Die
Markdown-Fassung und die JSON-Datei, die der Erklaerfilm einliest, sind
Ausgaben davon — keine zweiten Quellen. Sonst laufen sie auseinander, und
niemand merkt es, bis im fertigen Video ein Satz steht, den so niemand mehr
sagen wollte.

    python3 scripts/texte.py            # schreibt beide Ausgaben neu
    python3 scripts/texte.py --pruefen  # meldet nur, ob sie aktuell sind

Dasselbe Muster wie scripts/quellenlage.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
QUELLE = REPO / "docs" / "marke" / "texte.yaml"
MARKDOWN = REPO / "docs" / "marke" / "texte.md"
SZENEN = REPO / "docs" / "marke" / "video" / "erklaerfilm" / "src" / "texte.json"

KOPF = """<!-- Erzeugt aus texte.yaml — nicht von Hand aendern.
     Neu bauen: python3 scripts/texte.py -->

# Textkanon

Einzige Quelle fuer Claim, Untertitel und die Szenentexte des Erklaerfilms ist
[`texte.yaml`](texte.yaml). Diese Datei ist daraus erzeugt.

README, `pyproject.toml`, der Banner und der Film werden gegen den Kanon geprueft
(`tests/test_marke.py`). Wer einen Satz aendern will, aendert die YAML und laesst
`python3 scripts/texte.py` laufen.
"""


def kanon() -> dict:
    return yaml.safe_load(QUELLE.read_text(encoding="utf-8"))


def markdown(k: dict) -> str:
    z = [KOPF, "\n## Claim\n"]
    z.append(f"**{k['claim']['de']}**\n")
    z.append(f"Sekundaer, nie allein: *{k['claim']['sekundaer']}*\n")
    z.append("\n## Untertitel\n")
    z.append(f"- Deutsch: {k['untertitel']['de']}")
    z.append(f"- Englisch: {k['untertitel']['en']}\n")
    z.append("\n## Kurzformen\n")
    z.append(f"- Fusszeile: {k['fusszeile']}")
    z.append(f"- Adresse: {k['adresse']}")
    z.append(f"- GitHub-Beschreibung ({len(k['github_beschreibung'])} Zeichen): "
             f"`{k['github_beschreibung']}`\n")
    z.append("\n## Installationsbefehle\n")
    z.append("Nur diese duerfen in Bild und Text gezeigt werden. Seit v0.7.3 gibt es")
    z.append("`pipx install falzmarke` zwar wirklich ([PyPI](https://pypi.org/project/falzmarke/)) —")
    z.append("der Kanon bleibt trotzdem beim `git+`-Weg: Er trifft auch den unveroeffentlichten")
    z.append("Stand von `main`, und er steckt im gerenderten Film. Umstellen hiesse Film und")
    z.append("Szenen neu rendern.\n")
    z.append(f"- Ohne Clone: `{k['installation']['ohne_clone']}`")
    z.append(f"- Dauerhaft: `{k['installation']['dauerhaft']}`\n")
    z.append("\n## Nutzen im Bild\n")
    z.append(f"- ohne: {k['nutzen']['ohne']}")
    z.append(f"- mit: {k['nutzen']['mit']}\n")
    f = k["film"]
    z.append(f"\n## Erklaerfilm — {f['dauer']} Sekunden\n")
    z.append("| Zeit | Szene | Text im Bild | Bild |")
    z.append("|---|---|---|---|")
    for s in f["szenen"]:
        z.append(f"| {s['von']}–{s['bis']} s | {s['name']} | {s['text']} | {s['bild']} |")
    z.append("")
    return "\n".join(z)


def claim_stufen(claim: str) -> tuple[str, str]:
    """Der Claim, in zwei Stufen getrennt.

    Der Abbinder zeigt erst „Briefe schreiben mit KI", dann die Pointe. Getrennt
    wird am Geviertstrich, damit der Kanon eine einzige Quelle bleibt — zwei
    gepflegte Fassungen desselben Satzes waeren zwei Fassungen, die auseinander-
    laufen. tests/test_marke.py prueft, dass beide Teile wieder den Claim ergeben.
    """
    if "—" not in claim:
        raise SystemExit(
            f"Der Claim hat keinen Geviertstrich, an dem sich zwei Stufen trennen "
            f"liessen: {claim!r}"
        )
    erste, zweite = claim.split("—", 1)
    return erste.strip(), zweite.strip()


def szenen(k: dict) -> str:
    f = k["film"]
    stufe1, stufe2 = claim_stufen(k["claim"]["de"])
    daten = {
        "hinweis": "Erzeugt aus docs/marke/texte.yaml — nicht von Hand aendern.",
        "claim": k["claim"]["de"],
        "claimStufe1": stufe1,
        "claimStufe2": stufe2,
        "claimSekundaer": k["claim"]["sekundaer"],
        "untertitel": k["untertitel"]["de"],
        "adresse": k["adresse"],
        "installation": k["installation"]["ohne_clone"],
        "nutzen": k["nutzen"],
        "dauer": f["dauer"],
        "szenen": [
            {"name": s["name"], "von": s["von"], "bis": s["bis"], "text": s["text"]}
            for s in f["szenen"]
        ],
    }
    return json.dumps(daten, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    pruefen = "--pruefen" in sys.argv
    k = kanon()
    aufgaben = [(MARKDOWN, markdown(k)), (SZENEN, szenen(k))]

    veraltet = []
    for ziel, inhalt in aufgaben:
        alt = ziel.read_text(encoding="utf-8") if ziel.exists() else None
        if alt == inhalt:
            continue
        if pruefen:
            veraltet.append(ziel.relative_to(REPO))
        else:
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
            print(f"OK  geschrieben: {ziel.relative_to(REPO)}")

    if pruefen:
        if veraltet:
            for p in veraltet:
                print(f"VERALTET  {p}", file=sys.stderr)
            print("\nNeu bauen: python3 scripts/texte.py", file=sys.stderr)
            return 1
        print("OK  Ausgaben sind am Stand von texte.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
