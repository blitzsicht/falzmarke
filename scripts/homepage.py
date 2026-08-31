#!/usr/bin/env python3
"""Homepage für ein Repo bestimmen — Standarddomain fest im Skript, nicht in einer Variable.

WARUM ES DAS GIBT

Bis zum 30.08.2026 hing die gesetzte `homepageUrl` allein von der Umgebungsvariable
`FALZMARKE_HOMEPAGE` ab: leer heißt „überschreib die Homepage mit der Release-Seite“.
Wer `scripts/repo-einstellungen.sh` ohne die Variable fuhr — und niemand außerhalb des
Skripts selbst nennt sie überhaupt —, verlor damit unbemerkt den Verweis auf
falzmarke.com, obwohl die Domain die ganze Zeit HTTP 200 antwortete (Issue #199).

Diese Datei trägt die Entscheidungslogik. Der eigentliche Default steht als
`STANDARD_DOMAIN` hier im Repository; das Skript reicht `FALZMARKE_HOMEPAGE` nur noch
als Override für Forks durch. Und: Ein Rückfall auf die Release-Seite bleibt nicht mehr
still, wenn vorher eine andere, echte Domain gesetzt war — genau der Fall, der am
30.08.2026 unbemerkt zuschlug.

    python3 scripts/homepage.py --repo blitzsicht/falzmarke --domain https://falzmarke.com
    python3 scripts/homepage.py --repo blitzsicht/falzmarke --domain https://falzmarke.com --bisher https://falzmarke.com

Verwendet von scripts/repo-einstellungen.sh.
"""

from __future__ import annotations

import argparse
import urllib.error
import urllib.request
from typing import Callable

#: Der Default gehört ins Repository, nicht in eine undokumentierte Variable
#: (Issue #199, "Was zu tun ist" Punkt 1).
STANDARD_DOMAIN = "https://falzmarke.com"

ANTWORT_CODES = (200, 301, 302)


def release_seite(repo: str) -> str:
    return f"https://github.com/{repo}/releases/latest"


def domain_antwortet(url: str, timeout: float = 10.0) -> bool:
    """True bei HTTP 200/301/302, sonst False — auch bei DNS-Fehler oder Timeout."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as antwort:
            return antwort.status in ANTWORT_CODES
    except urllib.error.HTTPError as fehler:
        return fehler.code in ANTWORT_CODES
    except Exception:
        return False


def bestimme(
    repo: str,
    gewuenschte_domain: str,
    bisherige_homepage: str,
    *,
    pruefen: Callable[[str], bool] = domain_antwortet,
) -> tuple[str, str]:
    """(homepage, meldung).

    `pruefen` ist austauschbar, damit die Entscheidungslogik ohne Netzzugriff testbar
    ist — inklusive der Gegenprobe: eine unerreichbare Domain muss den Rückfall
    auslösen, nicht nur behauptet werden.

    Fällt die Domain aus UND vorher stand dort eine andere, echte Homepage (nicht
    schon die Release-Seite) — dann wäre der Rückfall genau der stille Verlust aus
    Issue #199. Die Meldung bekommt dafür ein "WARNUNG:"-Präfix statt eines bloßen
    Hinweises.
    """
    fallback = release_seite(repo)
    if pruefen(gewuenschte_domain):
        return gewuenschte_domain, f"{gewuenschte_domain} antwortet — wird als Homepage gesetzt."

    ueberschreibt_andere_domain = bool(bisherige_homepage) and bisherige_homepage != fallback
    meldung = f"{gewuenschte_domain} antwortet nicht — Homepage zeigt auf die Release-Seite zurück."
    if ueberschreibt_andere_domain:
        meldung = (
            f"WARNUNG: {meldung} Bisher war {bisherige_homepage} gesetzt — "
            "das wird jetzt ersetzt."
        )
    return fallback, meldung


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="OWNER/REPO")
    parser.add_argument("--domain", required=True, help="Gewünschte Homepage-Domain")
    parser.add_argument("--bisher", default="", help="Aktuell gesetzte Homepage, falls bekannt")
    args = parser.parse_args()

    homepage, meldung = bestimme(args.repo, args.domain, args.bisher)
    print(homepage)
    print(meldung)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
