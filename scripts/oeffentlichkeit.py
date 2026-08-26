#!/usr/bin/env python3
"""Prüft die öffentlichen Issues auf interne Angaben — nach ADR 0031.

Ein Issue hier beschreibt das Werkzeug, nicht unsere Arbeitsweise. Der Unterschied
ist leicht zu übersehen, weil ein Auftrag beim Übersetzen in ein Issue seinen
Kontext mitbringt. Dieses Skript zählt nach.

    python3 scripts/oeffentlichkeit.py             # holt per gh api, prüft, Exit 1 bei Fund
    python3 scripts/oeffentlichkeit.py --aus x.json  # aus einer Datei statt aus dem Netz

Zwei Eigenheiten, beide notwendig:

**Die Muster nennen keine Namen.** Eine Wortliste mit den zu schützenden
Bezeichnern im öffentlichen Repository veröffentlicht genau das, wovor sie
warnt. Gesucht wird deshalb nach der *Form* — Repository-Endungen, interne
Verzeichnisnamen, lokale Pfade. Wer zusätzliche Eigennamen prüfen will, gibt sie
über die Umgebungsvariable `HYGIENE_ZUSATZ` (kommagetrennt) aus einem Secret
mit; sie erscheinen nie im Protokoll.

**Der Befund wird nicht zitiert.** Das Aktionsprotokoll eines öffentlichen
Repositorys ist öffentlich. Gemeldet werden Issue-Nummer und Musterkennung, nie
die gefundene Zeile — sonst verdoppelt die Meldung den Fund. Aus demselben Grund
kommentiert das Skript nichts am Issue.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

# Form statt Name. Jede Zeile: (Kennung, Muster, wogegen sie schützt).
MUSTER = [
    ("ops-repo", r"\b[a-z][\w]*-ops\b",
     "Name eines Betriebs-Repositorys"),
    ("interner-ordner", r"\b[\w]+-intern\b",
     "internes Verzeichnis"),
    ("auftragsdatei", r"\bauftrag-[\w-]+\.md\b",
     "Auftragsdokument"),
    ("auftragsordner", r"\bdocs/auftraege\b|\bthoughts/shared\b",
     "interne Ablage"),
    ("lokaler-pfad", r"(?:^|[\s(`])(?:/Volumes/|/Users/|~/)[\w.]",
     "Pfad auf einem Arbeitsrechner"),
    ("windows-pfad", r"\b[A-Z]:\\\\?[\w]",
     "Pfad auf einem Arbeitsrechner"),
    ("arbeitspaket", r"###\s*Code-Repo\b|\bArbeitspaket\w*\b",
     "Struktur der internen Arbeitspakete"),
]


class Hygienefehler(RuntimeError):
    """Die Eingabe trägt nicht, was die Prüfung behaupten würde."""


def _zusatzmuster() -> list[tuple[str, str, str]]:
    """Eigennamen aus einem Secret — bewusst ohne Klartext im Repository."""
    roh = os.environ.get("HYGIENE_ZUSATZ", "").strip()
    if not roh:
        return []
    begriffe = [b.strip() for b in roh.split(",") if b.strip()]
    return [(f"zusatz-{i + 1}", re.escape(b), "Begriff aus der Zusatzliste")
            for i, b in enumerate(begriffe)]


def _gh(pfad: str) -> list[dict]:
    lauf = subprocess.run(["gh", "api", "--paginate", pfad],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if lauf.returncode != 0:
        raise Hygienefehler(f"gh api {pfad} scheiterte:\n{lauf.stderr.strip()}")
    return json.loads(lauf.stdout.replace("][", ","))


def hole() -> list[dict]:
    """Offene Issues samt Kommentaren."""
    nwo = os.environ.get("GITHUB_REPOSITORY", "blitzsicht/falzmarke")
    vorgaenge = []
    for vorgang in _gh(f"repos/{nwo}/issues?state=open&per_page=100"):
        if "pull_request" in vorgang:
            continue
        kommentare = _gh(f"repos/{nwo}/issues/{vorgang['number']}/comments?per_page=100")
        vorgaenge.append({
            "number": vorgang["number"],
            "title": vorgang.get("title", ""),
            "body": vorgang.get("body") or "",
            "comments": [k.get("body") or "" for k in kommentare],
        })
    return vorgaenge


def pruefe(vorgaenge: list[dict]) -> list[dict]:
    """Befunde je Issue — Kennung und Anzahl, nie der gefundene Text."""
    if not vorgaenge:
        raise Hygienefehler(
            "Keine offenen Issues gefunden. Eine Prüfung über die leere Menge ist "
            "immer grün und belegt nichts.")

    alle = MUSTER + _zusatzmuster()
    befunde = []
    for vorgang in vorgaenge:
        text = "\n".join([vorgang.get("title", ""), vorgang.get("body") or ""]
                         + list(vorgang.get("comments") or []))
        treffer = []
        for kennung, muster, wogegen in alle:
            anzahl = len(re.findall(muster, text, flags=re.MULTILINE))
            if anzahl:
                treffer.append({"kennung": kennung, "anzahl": anzahl, "wogegen": wogegen})
        if treffer:
            befunde.append({"nummer": vorgang["number"], "treffer": treffer})
    return befunde


def bericht(befunde: list[dict], geprueft: int) -> str:
    """Was im Protokoll landet. Enthält bewusst keine Fundstelle im Klartext."""
    if not befunde:
        return f"OK  {geprueft} offene Issues geprüft, keine internen Angaben gefunden."

    zeilen = [f"{len(befunde)} von {geprueft} offenen Issues nennen Internes (ADR 0031):", ""]
    for befund in befunde:
        teile = ", ".join(f"{t['kennung']}×{t['anzahl']} ({t['wogegen']})"
                          for t in befund["treffer"])
        zeilen.append(f"  #{befund['nummer']}: {teile}")
    zeilen += [
        "",
        "Der Fundtext steht hier absichtlich nicht: dieses Protokoll ist öffentlich.",
        "Nachsehen mit `gh issue view <nr> --comments`.",
    ]
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    zerleger.add_argument("--aus", metavar="DATEI", help="JSON-Liste von Issues statt gh api")
    args = zerleger.parse_args(argv)

    try:
        vorgaenge = (json.loads(open(args.aus, encoding="utf-8").read()) if args.aus else hole())
        befunde = pruefe(vorgaenge)
    except Hygienefehler as fehler:
        print(f"oeffentlichkeit: {fehler}", file=sys.stderr)
        return 2

    print(bericht(befunde, len(vorgaenge)))
    return 1 if befunde else 0


if __name__ == "__main__":
    raise SystemExit(main())
