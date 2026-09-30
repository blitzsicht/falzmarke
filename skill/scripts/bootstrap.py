#!/usr/bin/env python3
"""Prüft die Laufzeitabhängigkeiten von falzmarke und installiert sie bei Bedarf.

Zwei Wege, in dieser Reihenfolge:

1. **Aus dem Paket, ohne Netz.** Liegt neben diesem Skript ein `vendor/` mit
   Wheels, wird zuerst daraus installiert (`--no-index`). Das Skill-Paket bringt
   das `typst`-Wheel mit — von den sechs Abhängigkeiten die einzige mit nativem
   Binärkern und deshalb die, die in einer Sandbox als Erste fehlt.
2. **Von PyPI**, falls danach noch etwas offen ist und Netzzugriff besteht.

Warum je Requirement einzeln, auf **beiden** Wegen: pip bricht komplett ab,
sobald **ein** genanntes Paket nicht zu bekommen ist — es installiert dann auch
die anderen nicht. Aus `vendor/` hätte ein Paket, das nur `typst` mitbringt,
damit gar nichts ausgerichtet. Und von PyPI gilt dasselbe: In ChatGPT (26.09.2026)
fehlten typst und ein zweites Paket; der Paketspiegel dort hatte das zweite, aber
nicht typst — gebündelt scheiterten beide (#361).

„Vorhanden" heißt: importierbar **und** in der Version, die `DEPS` verlangt. Eine
Sandbox bringt einen Teil der Pakete selbst mit, in unbekannter Version (ChatGPT,
29.09.2026: alle außer typst). Eine zu alte würde sonst still übernommen (#374).

Exit 0: alles vorhanden (oder erfolgreich installiert)
Exit 1: Installation nicht möglich — die Meldung nennt den Grund
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

# Modulname -> pip-Requirement. Alle Abhängigkeiten tragen eine permissive
# Lizenz (MIT/BSD/Apache); siehe THIRD_PARTY_LICENSES.md. Das ist kein Zufall:
# PyMuPDF wäre technisch geeignet, ist aber AGPL-3.0 und hätte jede Firma, die
# falzmarke einbaut, in die AGPL gezwungen.
DEPS = {
    "typst": "typst>=0.15,<0.16",
    "yaml": "pyyaml>=6",
    "pdfplumber": "pdfplumber>=0.11",
    "pypdf": "pypdf>=5",
    "markdown_it": "markdown-it-py>=4,<5",
    "PIL": "pillow>=10",
}

#: Das Skill-Paket mit dem typst-Wheel. Die Fehlermeldung nennt es, damit eine
#: Sandbox ohne PyPI nicht an dieser Stelle endet (#360).
OFFLINE_PAKET = ("https://github.com/blitzsicht/falzmarke/releases/latest/download/"
                 "falzmarke-offline.skill")

#: Wheels, die mit dem Skill-Paket ausgeliefert werden. Im Quellbaum ist das
#: Verzeichnis leer — siehe `vendor/README.md`; gefüllt wird es beim Packen.
VENDOR = Path(__file__).resolve().parent.parent / "vendor"


def _paketname(req: str) -> str:
    return re.split(r"[<>=!~ ]", req, maxsplit=1)[0]


def _grenzen(req: str) -> str:
    return req[len(_paketname(req)):].strip()


def _zahlen(version: str) -> tuple[int, ...] | None:
    treffer = re.match(r"\d+(?:\.\d+)*", version)
    return tuple(int(t) for t in treffer.group().split(".")) if treffer else None


def _erfuellt_ohne_packaging(version: str, grenzen: str) -> bool:
    """Ersatz, falls `packaging` fehlt. Kennt nur Vergleiche mit Zahlenversionen;
    alles andere gilt als nicht erfüllt — dann wird nachinstalliert, statt eine
    Version ungeprüft zu übernehmen."""
    ist = _zahlen(version)
    if ist is None:
        return False
    vergleiche = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
                  ">": lambda a, b: a > b, "<": lambda a, b: a < b,
                  "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
    for grenze in filter(None, (g.strip() for g in grenzen.split(","))):
        treffer = re.fullmatch(r"(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)*)", grenze)
        if not treffer:
            return False
        soll = _zahlen(treffer.group(2))
        breite = max(len(ist), len(soll))
        a = ist + (0,) * (breite - len(ist))
        b = soll + (0,) * (breite - len(soll))
        if not vergleiche[treffer.group(1)](a, b):
            return False
    return True


def _erfuellt(version: str, grenzen: str) -> bool:
    try:
        from packaging.specifiers import InvalidSpecifier, SpecifierSet
        from packaging.version import InvalidVersion
    except ImportError:
        return _erfuellt_ohne_packaging(version, grenzen)
    try:
        return SpecifierSet(grenzen).contains(version, prereleases=True)
    except (InvalidSpecifier, InvalidVersion):
        return False


def grund(modul: str) -> str | None:
    """Warum `modul` nachinstalliert werden muss — oder None, wenn es passt."""
    req = DEPS[modul]
    if importlib.util.find_spec(modul) is None:
        return "nicht installiert"
    grenzen = _grenzen(req)
    try:
        gefunden = importlib.metadata.version(_paketname(req))
    except importlib.metadata.PackageNotFoundError:
        return f"Version nicht feststellbar, verlangt {grenzen}"
    if not _erfuellt(gefunden, grenzen):
        return f"{gefunden} gefunden, verlangt {grenzen}"
    return None


def fehlende() -> dict[str, str]:
    importlib.invalidate_caches()
    return {m: r for m, r in DEPS.items() if grund(m) is not None}


def wheels() -> list[Path]:
    return sorted(VENDOR.glob("*.whl")) if VENDOR.is_dir() else []


def _pip(reqs: list[str], extra: list[str]) -> tuple[bool, str]:
    """Erst der normale Weg, dann der Sandbox-Weg mit --break-system-packages."""
    basis = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
    letzter_fehler = ""
    for schutz in ([], ["--break-system-packages"]):
        ergebnis = subprocess.run(basis + schutz + extra + reqs,
                                  capture_output=True, text=True)
        if ergebnis.returncode == 0:
            return True, ""
        letzter_fehler = ergebnis.stderr.strip()
    return False, letzter_fehler


def aus_dem_paket(offen: dict[str, str]) -> None:
    """Ohne Netz, aus `vendor/`. Fehlschläge sind hier normal und still:
    Was kein Wheel danebenliegen hat, holt der nächste Schritt."""
    for req in offen.values():
        _pip([req], ["--no-index", "--find-links", str(VENDOR)])


def aus_dem_netz(offen: dict[str, str]) -> dict[str, str]:
    """Von PyPI, je Paket einzeln. Gibt je Modul die letzte pip-Zeile zurück,
    für die Pakete, die danach noch fehlen."""
    fehler = {}
    for modul, req in offen.items():
        erfolg, meldung = _pip([req], [])
        if not erfolg:
            fehler[modul] = meldung.splitlines()[-1] if meldung else "ohne Meldung"
    return fehler


def main() -> int:
    offen = fehlende()
    if not offen:
        print("OK  Alle Abhängigkeiten vorhanden.")
        return 0

    vorrat = wheels()
    print(f"Fehlend: {', '.join(offen)} — installiere …")
    for modul in offen:
        print(f"    {_paketname(offen[modul])}: {grund(modul)}")

    if vorrat:
        print(f"    aus dem Paket, ohne Netz ({len(vorrat)} Wheel(s) in vendor/)")
        aus_dem_paket(offen)
        offen = fehlende()

    fehler: dict[str, str] = {}
    if offen:
        if vorrat:
            print(f"    noch offen: {', '.join(offen)} — versuche PyPI")
        fehler = aus_dem_netz(offen)
        offen = fehlende()

    if offen:
        print(
            f"FEHLER  Diese Pakete fehlen weiterhin: {', '.join(offen)}\n"
            f"        Im Paket lagen {len(vorrat)} Wheel(s); für die oben genannten war keines "
            "dabei,\n"
            "        und von PyPI waren sie nicht zu bekommen.\n"
            "        Ohne sie gibt es bewusst keinen Ersatz-Renderer — ein zweiter Renderer "
            "würde\n"
            "        ein anderes Layout erzeugen, und die Nachmessung wäre wertlos.\n"
            "        Ausweg ohne PyPI: das Paket mit mitgeliefertem Typst-Compiler,\n"
            f"        {OFFLINE_PAKET}",
            file=sys.stderr,
        )
        for modul in offen:
            print(f"        {_paketname(offen[modul])}: {grund(modul)}", file=sys.stderr)
            if modul in fehler:
                print(f"        pip zu {modul}: {fehler[modul]}", file=sys.stderr)
        return 1

    print("OK  Abhängigkeiten installiert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
