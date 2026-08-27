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

# Wie weit eine Quelle trägt. Siehe Kopfkommentar von din5008.yaml.
ZAEHLT_VOLL = "voll"        # externer Beleg, zählt auch für „mehrfach"
ZAEHLT_EINZELN = "einzeln"  # Beleg, aber keine unabhängige Bestätigung
ZAEHLT_NIE = "nie"          # zählt gar nicht
ZAEHLSTUFEN = {ZAEHLT_VOLL, ZAEHLT_EINZELN, ZAEHLT_NIE}

# Wie viele Quellen mit `zaehlt: voll` eine Herkunftsstufe mindestens braucht.
MINDESTENS_VOLL = {MEHRFACH: 2}
# Stufen, für die auch eine nur einzeln tragende Quelle genügt.
MINDESTENS_IRGENDEIN_BELEG = {EINZELN}

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
        _pruefe_beleglage(kennung, regel, quellen)
    return {"regeln": regeln, "quellen": quellen}


def _pruefe_beleglage(kennung: str, regel: dict, quellen: dict) -> None:
    """Trägt die Regel die Stufe, die sie behauptet?

    Bis v0.5.0 stand die Zählung nur im Kopfkommentar der Regeldatei und wurde
    von Hand gesetzt. Gemessen am 25.08.2026: **alle 14** als
    `mehrfach_bestaetigt` geführten Regeln verfehlten die damals dokumentierte
    Definition — je zwei Sekundärquellen plus die vendorte Implementierung,
    verlangt waren drei Quellen beziehungsweise eine plus zwei
    Implementierungen. Niemandem fiel es auf, weil nichts nachzählte.

    Eine Definition, die nur im Kommentar steht, ist keine Definition.
    """
    herkunft = regel["herkunft"]
    namen = regel.get("quellen") or []

    stufen = []
    for name in namen:
        stufe = quellen[name].get("zaehlt")
        if stufe not in ZAEHLSTUFEN:
            raise Regelfehler(
                f"{DATEI.name}: Quelle {name!r} hat zaehlt={stufe!r}, "
                f"zulässig sind {sorted(ZAEHLSTUFEN)}. Ohne diese Angabe ist nicht "
                "entscheidbar, ob sie eine Regel trägt.")
        stufen.append(stufe)

    voll = stufen.count(ZAEHLT_VOLL)
    belege = voll + stufen.count(ZAEHLT_EINZELN)

    noetig = MINDESTENS_VOLL.get(herkunft)
    if noetig is not None and voll < noetig:
        schwach = [n for n in namen if quellen[n].get("zaehlt") != ZAEHLT_VOLL]
        raise Regelfehler(
            f"{DATEI.name}: {kennung} ist {herkunft}, hat aber nur {voll} "
            f"voll zählende Quelle(n) — nötig sind {noetig}.\n"
            f"        Genannt: {', '.join(namen) or 'keine'}\n"
            f"        Zählt nicht voll: {', '.join(schwach) or '—'}\n"
            "        Entweder eine unabhängige Quelle ergänzen oder die Regel "
            "auf einzeln_belegt zurückstufen.")

    if herkunft in MINDESTENS_IRGENDEIN_BELEG and belege < 1:
        raise Regelfehler(
            f"{DATEI.name}: {kennung} ist {herkunft}, aber keine der genannten "
            f"Quellen trägt sie ({', '.join(namen) or 'keine'}). "
            "Dann ist sie offen, nicht belegt.")


def alle() -> list[dict]:
    return laden()["regeln"]


def quellen() -> dict:
    return laden()["quellen"]


def _quellennamen(regel: dict) -> list[str]:
    """Die Quellen einer Regel als Namen — egal, wie sie notiert sind."""
    return [q if isinstance(q, str) else q.get("quelle", str(q))
            for q in (regel.get("quellen") or [])]


def unabhaengige_belege(regel: dict) -> set[str]:
    """Die Gruppen, aus denen eine Regel tatsächlich belegt ist.

    Zwei Quellen derselben Gruppe sind **ein** Beleg, keine zwei. Gemessen am
    27.08.2026: `massskizze_b` (Wikimedia Commons, 2013, CC0) und
    `onlineprinters` (Magazin-Zeichnung, 2021) sind bis in den Fußtext
    deckungsgleich — zwei Ansichten derselben Sache, die neun Regeln auf
    `mehrfach_bestaetigt` hoben. Der Befund steht in
    docs/quellenunabhaengigkeit-2026-08-27.md.

    Diese Funktion **misst nur**. Sie stuft nichts herab: Was aus dem Befund
    folgt, ist eine eigene Entscheidung und ein eigener Schritt — eine
    Recherche, die im Vorbeigehen das Verhalten des Werkzeugs ändert, wäre
    keine Recherche.
    """
    q = quellen()
    return {
        q[name].get("gruppe", name)
        for name in _quellennamen(regel)
        if q.get(name, {}).get("zaehlt") == ZAEHLT_VOLL
    }


def stufe_traegt_nicht() -> list[str]:
    """Regeln auf `mehrfach_bestaetigt`, hinter denen nur eine Gruppe steht.

    Der offene Rest von Issue #16. Die Liste ist in tests/test_quellenlage.py
    als erwarteter Stand festgehalten — sie soll sich nicht unbemerkt ändern,
    in keine Richtung.
    """
    return sorted(r["id"] for r in alle()
                  if r.get("herkunft") == MEHRFACH and len(unabhaengige_belege(r)) < 2)


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
