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

#: Das Quellen-Register. Eine Datei fuer alle Regeldateien — die Ebene `norm`
#: der E-Mail-Regeln beruft sich auf dieselben Sekundaerquellen wie die
#: Briefregeln, und zwei Register waeren zwei Fassungen derselben Sache.
QUELLDATEI = Path(__file__).parent / "quellen.yaml"

#: Regeldateien. `ebene` ist dort Pflicht, wo der Wert True steht (ADR 0035).
REGELDATEIEN = {
    Path(__file__).parent / "din5008.yaml": False,
    Path(__file__).parent / "email.yaml": True,
}

#: Fuer Fehlermeldungen, die keine bestimmte Datei meinen.
DATEI = QUELLDATEI

MEHRFACH = "mehrfach_bestaetigt"
EINZELN = "einzeln_belegt"
OFFEN = "offen"
WERKZEUG = "werkzeug"
#: Der Vorschriftentext selbst liegt vor — ein RFC, ein Paragraf.
#:
#: Warum das eine eigene Stufe ist: Die Skala darueber wurde fuer
#: Sekundaerquellen gebaut. Wir kennen den Normtext nicht, also verlangen wir
#: zwei unabhaengige Referate, bevor eine Regel als Fehler gelten darf. Bei
#: einem RFC gibt es nichts zu bestaetigen — es gibt nur nachzulesen. Eine
#: RFC-Regel als `einzeln_belegt` zu fuehren hiesse, sie auf Warnung
#: herabzustufen, obwohl ihr Beleg staerker ist als jeder Sekundaerbeleg.
#:
#: Genau diese Lage entsteht nach dem Normabgleich auch fuer die DIN-Regeln.
PRIMAER = "primaerquelle"

HERKUENFTE = {MEHRFACH, EINZELN, OFFEN, WERKZEUG, PRIMAER}

# ── ebene: wovon eine Regel redet (ADR 0035) ──────────────────────────────
#
# Zweite Achse neben `herkunft`. Die eine sagt, WOVON die Regel redet, die
# andere, WIE GUT sie belegt ist. Es gilt die schaerfere der beiden Grenzen.
EBENE_NORM = "norm"
EBENE_RECHT = "recht"
EBENE_TECHNIK = "technik"
EBENE_PRAXIS = "praxis"
#: Der eigene Datenvertrag — keine Aussage ueber Norm, Recht oder Technik.
#: ADR 0035 nennt vier Ebenen; diese fuenfte kam beim Eintragen dazu, weil
#: mehrere Regeln zu keiner der vier gehoeren. Nachtrag vom 28.08.2026.
EBENE_WERKZEUG = "werkzeug"

EBENEN = {EBENE_NORM, EBENE_RECHT, EBENE_TECHNIK, EBENE_PRAXIS, EBENE_WERKZEUG}

#: Regeln der Ebenen Recht und Praxis sind nie ein Fehler. Ein Fehler ist die
#: Zusage, dass etwas nachweislich verletzt wurde; Erfahrung mit einem
#: Programm traegt das nicht, und ueber Rechtsfragen urteilt das Werkzeug
#: nicht (ADR 0005).
EBENE_DARF_FEHLER = {EBENE_NORM, EBENE_TECHNIK, EBENE_WERKZEUG}

#: Was in der Meldung neben einer gedeckelten Regel steht.
EBENENHINWEIS = {
    EBENE_RECHT: "Ebene: Recht — eine Erinnerung, keine Rechtsprüfung",
    EBENE_PRAXIS: "Ebene: Praxis — Erfahrung mit Mailprogrammen, kein Nachweis",
}

# Wie weit eine Quelle trägt. Siehe Kopfkommentar von din5008.yaml.
ZAEHLT_VOLL = "voll"        # externer Beleg, zählt auch für „mehrfach"
ZAEHLT_EINZELN = "einzeln"  # Beleg, aber keine unabhängige Bestätigung
ZAEHLT_NIE = "nie"          # zählt gar nicht
ZAEHLSTUFEN = {ZAEHLT_VOLL, ZAEHLT_EINZELN, ZAEHLT_NIE}

# Wie viele Quellen mit `zaehlt: voll` eine Herkunftsstufe mindestens braucht.
MINDESTENS_VOLL = {MEHRFACH: 2, PRIMAER: 1}
# Stufen, für die auch eine nur einzeln tragende Quelle genügt.
MINDESTENS_IRGENDEIN_BELEG = {EINZELN}

# Was eine Herkunft im Linter höchstens bewirken darf.
DARF_FEHLER_SEIN = {MEHRFACH, WERKZEUG, PRIMAER}

# Wirkungsstufen, die `deckel()` zurückgibt.
DECKEL_FEHLER = "fehler"
DECKEL_WARNUNG = "warnung"
DECKEL_KEINE = "keine"


class Regelfehler(ValueError):
    """Die Regeldatei ist unbrauchbar — kein Grund, ungeprüft weiterzumachen."""


@functools.lru_cache(maxsize=1)
def laden() -> dict:
    """Ein Quellen-Register, mehrere Regeldateien.

    Bis v0.8.1 war beides eine Datei. Seit ADR 0035 tragen die E-Mail-Regeln
    eine eigene — die Norm-Datei soll nichts ueber RFCs behaupten. Die Quellen
    bleiben gemeinsam: Zwei Definitionen derselben Quelle koennen
    auseinanderlaufen, und dann steht die Herkunft an zwei Stellen statt an
    einer.

    Jede Regel merkt sich unter `_datei`, woher sie stammt. Ohne das nennt eine
    Fehlermeldung die Regel, aber nicht die Datei, in der sie zu suchen ist.
    """
    import yaml

    if not QUELLDATEI.is_file():
        raise Regelfehler(f"Quellen-Register fehlt: {QUELLDATEI}")
    quellen = (yaml.safe_load(QUELLDATEI.read_text(encoding="utf-8")) or {}).get("quellen") or {}
    if not quellen:
        raise Regelfehler(f"{QUELLDATEI.name} enthält keine Quellen.")

    regeln: list[dict] = []
    gesehen: dict[str, str] = {}
    for pfad, ebene_pflicht in REGELDATEIEN.items():
        if not pfad.is_file():
            raise Regelfehler(f"Regeldatei fehlt: {pfad}")
        daten = (yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}).get("regeln") or []
        if not daten:
            raise Regelfehler(f"{pfad.name} enthält keine Regeln.")
        for regel in daten:
            _pruefe_regel(regel, pfad, ebene_pflicht, quellen, gesehen)
            regel["_datei"] = pfad.name
            regeln.append(regel)
    return {"regeln": regeln, "quellen": quellen}


def _pruefe_regel(regel: dict, pfad, ebene_pflicht: bool,
                  quellen: dict, gesehen: dict) -> None:
    kennung = regel.get("id")
    if not kennung:
        raise Regelfehler(f"{pfad.name}: Regel ohne id: {regel}")
    if kennung in gesehen:
        raise Regelfehler(
            f"{pfad.name}: id doppelt vergeben: {kennung} "
            f"(steht schon in {gesehen[kennung]})")
    gesehen[kennung] = pfad.name

    herkunft = regel.get("herkunft")
    if herkunft not in HERKUENFTE:
        raise Regelfehler(
            f"{pfad.name}: {kennung} hat herkunft={herkunft!r}, "
            f"zulässig sind {sorted(HERKUENFTE)}")

    ebene = regel.get("ebene")
    if ebene_pflicht and ebene not in EBENEN:
        raise Regelfehler(
            f"{pfad.name}: {kennung} hat ebene={ebene!r}, zulässig sind "
            f"{sorted(EBENEN)}. Ohne Ebene sagt die Meldung nicht, wovon die "
            "Regel redet — und das ist der Grund, aus dem es diese Datei gibt "
            "(ADR 0035).")
    if ebene is not None and ebene not in EBENEN:
        raise Regelfehler(
            f"{pfad.name}: {kennung} hat ebene={ebene!r}, zulässig sind {sorted(EBENEN)}")

    # Eine belegte Regel ohne Quelle wäre eine Behauptung.
    if herkunft in (MEHRFACH, EINZELN, PRIMAER) and not regel.get("quellen"):
        raise Regelfehler(f"{pfad.name}: {kennung} ist {herkunft}, nennt aber keine Quelle.")
    for name in regel.get("quellen") or []:
        if name not in quellen:
            raise Regelfehler(f"{pfad.name}: {kennung} nennt unbekannte Quelle {name!r}")
    _pruefe_beleglage(kennung, regel, quellen)


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
                f"{QUELLDATEI.name}: Quelle {name!r} hat zaehlt={stufe!r}, "
                f"zulässig sind {sorted(ZAEHLSTUFEN)}. Ohne diese Angabe ist nicht "
                "entscheidbar, ob sie eine Regel trägt.")
        stufen.append(stufe)

    voll = stufen.count(ZAEHLT_VOLL)
    belege = voll + stufen.count(ZAEHLT_EINZELN)

    noetig = MINDESTENS_VOLL.get(herkunft)
    if noetig is not None and voll < noetig:
        schwach = [n for n in namen if quellen[n].get("zaehlt") != ZAEHLT_VOLL]
        raise Regelfehler(
            f"{regel.get('_datei', 'Regeldatei')}: {kennung} ist {herkunft}, hat aber nur {voll} "
            f"voll zählende Quelle(n) — nötig sind {noetig}.\n"
            f"        Genannt: {', '.join(namen) or 'keine'}\n"
            f"        Zählt nicht voll: {', '.join(schwach) or '—'}\n"
            "        Entweder eine unabhängige Quelle ergänzen oder die Regel "
            "auf einzeln_belegt zurückstufen.")

    if herkunft in MINDESTENS_IRGENDEIN_BELEG and belege < 1:
        raise Regelfehler(
            f"{regel.get('_datei', 'Regeldatei')}: {kennung} ist {herkunft}, aber keine der genannten "
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


#: Vorsatz im Feld `belegt_durch`, mit dem eine geprüfte Quelle als
#: beitragslos gekennzeichnet ist. Ausgeschrieben statt als Bool, damit in der
#: Regeldatei danebensteht, *warum* sie schweigt.
SCHWEIGT = "SCHWEIGT"


def schweigende_quellen() -> list[tuple[str, str]]:
    """Paare (Regel, Quelle), bei denen die Quelle zur Regel nichts sagt.

    Der Befund von Issue #31: Die Validierung prüft, ob eine Regel ihre
    Zählstufe trägt — nicht, ob die genannte Quelle zur Sache überhaupt etwas
    hergibt. Wo das nachgelesen wurde, steht das Ergebnis in `belegt_durch`.

    Auch diese Funktion **misst nur**. Sie entfernt keine Quelle und stuft
    nichts herab.
    """
    ergebnis = []
    for regel in alle():
        for quelle, fundstelle in (regel.get("belegt_durch") or {}).items():
            if str(fundstelle).lstrip().startswith(SCHWEIGT):
                ergebnis.append((regel["id"], quelle))
    return sorted(ergebnis)


def ohne_belegpruefung() -> list[tuple[str, str]]:
    """Paare (Regel, Quelle), bei denen niemand nachgelesen hat.

    Das ist der Rest von #31: `belegt_durch` fehlt. Nicht „kein Beleg" —
    sondern „nicht geprüft", und die beiden dürfen nicht verwechselt werden.
    """
    ergebnis = []
    for regel in alle():
        geprueft = regel.get("belegt_durch") or {}
        for name in _quellennamen(regel):
            if name not in geprueft:
                ergebnis.append((regel["id"], name))
    return sorted(ergebnis)


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


def deckel(regel: dict | None) -> str:
    """Was diese Regel höchstens sein darf — die schärfere zweier Grenzen.

    `herkunft` deckelt nach Belegstärke, `ebene` nach Gegenstand (ADR 0035).
    Eine Regel aus Primärquellen dürfte nach der ersten Achse ein Fehler sein;
    trägt sie die Ebene `recht`, deckelt die zweite sie auf Warnung. Beide
    Achsen können nur herabstufen, nie heraufstufen — deshalb genügt es, die
    schärfere zu nehmen.
    """
    if regel is None:
        return DECKEL_FEHLER          # nicht zugeordnet: wirkt wie bisher
    if regel.get("herkunft") == OFFEN:
        return DECKEL_KEINE
    darf_fehler = regel.get("herkunft") in DARF_FEHLER_SEIN
    ebene = regel.get("ebene")
    if ebene is not None and ebene not in EBENE_DARF_FEHLER:
        darf_fehler = False
    return DECKEL_FEHLER if darf_fehler else DECKEL_WARNUNG


def deckel_von_lint(regelname: str) -> str:
    return deckel(fuer_lint(regelname))


def ebene_von_lint(regelname: str) -> str | None:
    regel = fuer_lint(regelname)
    return regel.get("ebene") if regel else None


def quellenhinweis(regelname: str) -> str:
    """Kurzer Zusatz für die Meldung einer herabgestuften Regel.

    Sagt, WARUM die Regel nur warnt. Bei den E-Mail-Regeln ist das die Ebene —
    ADR 0035 verlangt, dass die Meldung sie nennt; bei den Briefregeln bleibt
    es die Quellenlage. Wo eine Regel keine Ebene trägt, ändert sich nichts an
    dem, was bisher dastand.
    """
    regel = fuer_lint(regelname)
    if not regel:
        return ""
    ebene = regel.get("ebene")
    if ebene in EBENENHINWEIS:
        return EBENENHINWEIS[ebene]
    if regel.get("herkunft") != EINZELN:
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
