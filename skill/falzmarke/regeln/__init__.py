#!/usr/bin/env python3
"""Die Quellenlage je Regel, gelesen aus `din5008.yaml`.

Warum das eine eigene Ebene ist: Alle Maße und Schreibregeln stammen aus
Sekundärquellen; der Abgleich mit dem Originaltext der DIN 5008:2020-03 steht
aus. Solange das so ist, darf das Werkzeug nur als **Fehler** melden, was
mehrfach belegt ist. Eine Regel aus einer einzigen Quelle wird zur Warnung
herabgestuft und nennt ihre Quellenlage in der Meldung; eine Regel ohne Beleg
wird gar nicht geprüft.

Die Zuordnung zu den Prüfungen steht in derselben YAML (`lint:`, `typografie:`),
damit Regel und Herkunft nicht an zwei Stellen gepflegt werden.
"""

from __future__ import annotations

import functools
from pathlib import Path

DATEI = Path(__file__).parent / "din5008.yaml"

MEHRFACH = "mehrfach_bestaetigt"
EINZELN = "einzeln_belegt"
OFFEN = "offen"
WERKZEUG = "werkzeug"

HERKUENFTE = {MEHRFACH, EINZELN, OFFEN, WERKZEUG}

# Was eine Herkunft im Linter höchstens bewirken darf.
DARF_FEHLER_SEIN = {MEHRFACH, WERKZEUG}


class Regelfehler(ValueError):
    """Die Regeldatei ist unbrauchbar — kein Grund, ungeprüft weiterzumachen."""


@functools.lru_cache(maxsize=1)
def laden() -> dict:
    import yaml

    if not DATEI.is_file():
        raise Regelfehler(f"Regeldatei fehlt: {DATEI}")
    daten = yaml.safe_load(DATEI.read_text(encoding="utf-8")) or {}
    regeln = daten.get("regeln") or []
    quellen = daten.get("quellen") or {}
    if not regeln:
        raise Regelfehler(f"{DATEI.name} enthält keine Regeln.")

    gesehen = set()
    for regel in regeln:
        kennung = regel.get("id")
        if not kennung:
            raise Regelfehler(f"{DATEI.name}: Regel ohne id: {regel}")
        if kennung in gesehen:
            raise Regelfehler(f"{DATEI.name}: id doppelt vergeben: {kennung}")
        gesehen.add(kennung)
        herkunft = regel.get("herkunft")
        if herkunft not in HERKUENFTE:
            raise Regelfehler(
                f"{DATEI.name}: {kennung} hat herkunft={herkunft!r}, "
                f"zulässig sind {sorted(HERKUENFTE)}")
        # Eine belegte Regel ohne Quelle wäre eine Behauptung.
        if herkunft in (MEHRFACH, EINZELN) and not regel.get("quellen"):
            raise Regelfehler(f"{DATEI.name}: {kennung} ist {herkunft}, nennt aber keine Quelle.")
        for name in regel.get("quellen") or []:
            if name not in quellen:
                raise Regelfehler(f"{DATEI.name}: {kennung} nennt unbekannte Quelle {name!r}")
    return {"regeln": regeln, "quellen": quellen}


def alle() -> list[dict]:
    return laden()["regeln"]


def quellen() -> dict:
    return laden()["quellen"]


@functools.lru_cache(maxsize=1)
def _nach_lint() -> dict[str, dict]:
    return {r["lint"]: r for r in alle() if r.get("lint")}


@functools.lru_cache(maxsize=1)
def _nach_typografie() -> dict[str, dict]:
    return {r["typografie"]: r for r in alle() if r.get("typografie")}


def fuer_lint(regelname: str) -> dict | None:
    """Die Regel hinter einem Linter-Befund, oder None wenn nicht zugeordnet."""
    return _nach_lint().get(regelname)


def fuer_typografie(schritt: str) -> dict | None:
    return _nach_typografie().get(schritt)


def herkunft_von_lint(regelname: str) -> str:
    """Nicht zugeordnete Linter-Regeln gelten als Werkzeugprüfung.

    Das ist die vorsichtige Richtung: Eine neue Prüfung wirkt zunächst wie
    bisher. Dass keine unbelegte Normregel auf diesem Weg hereinkommt, prüft
    `tests/test_quellenlage.py` — dort muss jede Linter-Regel zugeordnet sein.
    """
    regel = fuer_lint(regelname)
    return regel["herkunft"] if regel else WERKZEUG


def quellenhinweis(regelname: str) -> str:
    """Kurzer Zusatz für die Meldung einer herabgestuften Regel."""
    regel = fuer_lint(regelname)
    if not regel:
        return ""
    namen = regel.get("quellen") or []
    if not namen:
        return ""
    titel = quellen()[namen[0]]["titel"]
    return f"Quelle: sekundär, einzeln belegt — {titel}"


def darf_automatisch_ersetzen(schritt: str) -> bool:
    """Der Typografie-Pass ändert Text nur bei mehrfach belegten Regeln.

    Alles andere wäre eine stille Änderung auf dünner Grundlage: Der Brief
    sähe anders aus, als er geschrieben wurde, wegen einer Regel aus einer
    einzigen Quelle.
    """
    regel = fuer_typografie(schritt)
    if regel is None:
        return True
    return regel["herkunft"] in DARF_FEHLER_SEIN
