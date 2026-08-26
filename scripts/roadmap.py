#!/usr/bin/env python3
"""Schreibt `docs/ROADMAP.md` aus den Meilensteinen und offenen Issues.

Die Planung wird an genau einer Stelle gepflegt: im Issue. Diese Seite ist eine
Sicht darauf, keine zweite Wahrheit — sonst laufen beide auseinander, und
niemand merkt es. Die Reihenfolge der Phasen steht in ADR 0030.

    python3 scripts/roadmap.py              # holt per gh api, schreibt die Datei
    python3 scripts/roadmap.py --nach -     # nach stdout, ohne zu schreiben
    python3 scripts/roadmap.py --aus x.json # aus einer Datei statt aus dem Netz

Aufgerufen wird das wöchentlich von `.github/workflows/roadmap.yml`. Von Hand
gepflegte Änderungen an `docs/ROADMAP.md` gehen beim nächsten Lauf verloren.

Bewusst **ohne Standdatum im Text**: ein Datum würde jede Woche einen Commit
erzeugen, auch wenn sich an der Planung nichts geändert hat. Wann die Seite
zuletzt stimmte, steht am letzten Commit der Datei.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ZIEL = REPO / "docs" / "ROADMAP.md"
ADR = "entscheidungen/0030-reihenfolge-der-roadmap.md"

# Die Reihenfolge der Phasen ist eine Entscheidung, keine Eigenschaft der Daten:
# alle Meilensteine haben `due_on: null`, die API hat also keine Ordnung
# anzubieten. Quelle ist ADR 0030 — wer sie ändern will, ändert dort zuerst.
PHASEN = (
    "Vor Verbreitung",
    "Lange Schreiben",
    "Einfacher Zugang",
    "Dokumentpakete",
    "Beweis",
    "Geparkt",
)

# Labels, die keinen Bereich benennen. Alles andere gilt als Bereich — so fällt
# ein neues Bereichs-Label nicht still aus der Tabelle, nur weil es hier fehlt.
PRIORITAETEN = ("P0", "P1", "P2", "P3")
ZUSTAENDE = ("blockiert", "geparkt", "maintainer")

FREMDE_PHASE = "nicht in ADR 0030 vorgesehen"
OHNE_PHASE = "Ohne Phase"


class Roadmapfehler(RuntimeError):
    """Die Eingabe trägt nicht, was die Seite behaupten würde."""


# ── Beschaffung ─────────────────────────────────────────────────────────────

def _gh(pfad: str) -> list[dict]:
    lauf = subprocess.run(
        ["gh", "api", "--paginate", pfad],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if lauf.returncode != 0:
        raise Roadmapfehler(f"gh api {pfad} scheiterte:\n{lauf.stderr.strip()}")
    # --paginate hängt bei mehreren Seiten mehrere JSON-Listen aneinander.
    text = lauf.stdout.replace("][", ",")
    return json.loads(text)


def hole() -> dict:
    """Meilensteine und offene Issues aus GitHub."""
    nwo = os.environ.get("GITHUB_REPOSITORY", "blitzsicht/falzmarke")
    return {
        "milestones": _gh(f"repos/{nwo}/milestones?state=open&per_page=100"),
        "issues": _gh(f"repos/{nwo}/issues?state=open&per_page=100"),
    }


# ── Aufbereitung ────────────────────────────────────────────────────────────

def _labelnamen(vorgang: dict) -> list[str]:
    return [m["name"] if isinstance(m, dict) else str(m) for m in vorgang.get("labels") or []]


def _typ(vorgang: dict) -> str:
    """Der Issue-Typ, sobald die Organisation welche führt.

    Heute traegt kein Issue einen Typ — die Organisation kennt nur Task, Bug und
    Feature, die verlangten Typen (Epic, Aufgabe, Fehler, Forschung,
    Entscheidung) brauchen einen Org-Admin. Die Spalte erscheint von selbst,
    sobald es sie gibt; am Skript ist dafür nichts zu ändern.
    """
    art = vorgang.get("type") or vorgang.get("issueType") or {}
    if isinstance(art, dict):
        return art.get("name") or ""
    return str(art or "")


def _prioritaet(labels: list[str]) -> str:
    for stufe in PRIORITAETEN:
        if stufe in labels:
            return stufe
    return ""


def _ist_pull_request(vorgang: dict) -> bool:
    # `repos/:nwo/issues` liefert auch Pull Requests. Ohne diesen Filter stünden
    # offene PRs als Planungspunkte in der Roadmap.
    return "pull_request" in vorgang


def _sortierschluessel(zeile: dict) -> tuple:
    stufe = zeile["prioritaet"]
    rang = PRIORITAETEN.index(stufe) if stufe in PRIORITAETEN else len(PRIORITAETEN)
    return (rang, zeile["nummer"])


def ordne(daten: dict) -> tuple[list[dict], dict]:
    """(Phasen in ADR-0030-Reihenfolge, Zählwerte).

    Meilensteine, die ADR 0030 nicht kennt, werden hinten angehängt und
    markiert — nicht verschluckt. Issues ohne Meilenstein bekommen eine eigene
    Phase, aus demselben Grund.
    """
    meilensteine = daten.get("milestones") or []
    if not meilensteine:
        raise Roadmapfehler(
            "Keine offenen Meilensteine gefunden. Eine Roadmap ohne Phasen wäre "
            "eine leere Seite, die aussieht wie ein gepflegter Stand.")

    nach_titel = {m["title"]: m for m in meilensteine}
    bekannt = [t for t in PHASEN if t in nach_titel]
    fremd = sorted(t for t in nach_titel if t not in PHASEN)

    eintraege: dict[str, list[dict]] = {t: [] for t in bekannt + fremd}
    eintraege[OHNE_PHASE] = []

    offen = 0
    for vorgang in daten.get("issues") or []:
        if _ist_pull_request(vorgang):
            continue
        offen += 1
        labels = _labelnamen(vorgang)
        meilenstein = (vorgang.get("milestone") or {}).get("title") or OHNE_PHASE
        eintraege.setdefault(meilenstein, [])
        eintraege[meilenstein].append({
            "nummer": vorgang["number"],
            "titel": vorgang["title"],
            "url": vorgang.get("html_url", ""),
            "typ": _typ(vorgang),
            "prioritaet": _prioritaet(labels),
            "bereiche": [l for l in labels if l not in PRIORITAETEN and l not in ZUSTAENDE],
            "zustaende": [l for l in labels if l in ZUSTAENDE],
        })

    phasen = []
    for titel in bekannt + fremd + [OHNE_PHASE]:
        zeilen = sorted(eintraege.get(titel, []), key=_sortierschluessel)
        if titel == OHNE_PHASE and not zeilen:
            continue
        stein = nach_titel.get(titel, {})
        phasen.append({
            "titel": titel,
            "fremd": titel in fremd,
            "ohne_meilenstein": titel == OHNE_PHASE,
            "beschreibung": (stein.get("description") or "").strip(),
            "erledigt": stein.get("closed_issues", 0),
            "zeilen": zeilen,
        })

    return phasen, {"offen": offen, "phasen": len(bekannt) + len(fremd)}


# ── Darstellung ─────────────────────────────────────────────────────────────

def _tabelle(zeilen: list[dict], mit_typ: bool) -> list[str]:
    kopf = ["Nr.", "Was"] + (["Typ"] if mit_typ else []) + ["Priorität", "Bereich", "Zustand"]
    aus = ["| " + " | ".join(kopf) + " |",
           "|" + "|".join(["---"] * len(kopf)) + "|"]
    for z in zeilen:
        nr = f"[#{z['nummer']}]({z['url']})" if z["url"] else f"#{z['nummer']}"
        felder = [nr, z["titel"].replace("|", "\\|")]
        if mit_typ:
            felder.append(z["typ"] or "—")
        felder += [
            z["prioritaet"] or "—",
            ", ".join(z["bereiche"]) or "—",
            ", ".join(z["zustaende"]) or "—",
        ]
        aus.append("| " + " | ".join(felder) + " |")
    return aus


def rendere(daten: dict) -> str:
    """Die ganze Seite aus den Rohdaten. Rein — kein Netz, keine Uhr."""
    phasen, zaehlung = ordne(daten)
    mit_typ = any(z["typ"] for p in phasen for z in p["zeilen"])

    aus = [
        "<!-- Erzeugt von scripts/roadmap.py, wöchentlich über",
        "     .github/workflows/roadmap.yml. Änderungen von Hand gehen beim",
        "     nächsten Lauf verloren. -->",
        "",
        "# Roadmap",
        "",
        f"Die Reihenfolge der Phasen folgt [ADR 0030]({ADR}). Diese Seite wird aus den",
        "Meilensteinen und offenen Issues erzeugt und nicht von Hand gepflegt: die Wahrheit",
        "steht im Issue, hier steht nur eine Sicht darauf.",
        "",
        f"**{zaehlung['offen']} offene Vorgänge** in {zaehlung['phasen']} Phasen.",
        "",
    ]

    for nummer, phase in enumerate(phasen, start=1):
        if phase["ohne_meilenstein"]:
            aus += [
                f"## {OHNE_PHASE}",
                "",
                "Diese Vorgänge sind keiner Phase zugeordnet. Nach ADR 0030 gehört jeder",
                "Vorgang in eine Phase — auch „Geparkt“ ist eine.",
                "",
            ]
        else:
            marke = f" — *{FREMDE_PHASE}*" if phase["fremd"] else ""
            aus += [f"## {nummer}. {phase['titel']}{marke}", ""]
            if phase["beschreibung"]:
                aus += [phase["beschreibung"], ""]
            aus += [f"**{len(phase['zeilen'])} offen · {phase['erledigt']} erledigt**", ""]

        if phase["zeilen"]:
            aus += _tabelle(phase["zeilen"], mit_typ) + [""]
        else:
            aus += ["Nichts offen.", ""]

    return "\n".join(aus).rstrip() + "\n"


# ── Aufruf ──────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    zerleger.add_argument("--aus", metavar="DATEI",
                          help="JSON mit milestones und issues statt gh api")
    zerleger.add_argument("--nach", metavar="ZIEL", default=str(ZIEL),
                          help="Zieldatei, oder - für stdout")
    args = zerleger.parse_args(argv)

    try:
        daten = json.loads(Path(args.aus).read_text(encoding="utf-8")) if args.aus else hole()
        text = rendere(daten)
    except Roadmapfehler as fehler:
        print(f"roadmap: {fehler}", file=sys.stderr)
        return 1

    if args.nach == "-":
        sys.stdout.write(text)
    else:
        Path(args.nach).write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.nach}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
