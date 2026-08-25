"""Was das Werkzeug als Fehler meldet, muss mehrfach belegt sein.

Alle Maße und Schreibregeln in falzmarke stammen aus Sekundärquellen; der
Abgleich mit dem Originaltext der DIN 5008:2020-03 steht aus. Solange das so
ist, gilt: Nur eine mehrfach belegte Regel darf einen Lauf scheitern lassen.
Eine Regel aus einer einzigen Quelle wird zur Warnung und nennt ihre
Quellenlage; eine Regel ohne Beleg wird nicht geprüft.

Die Herkunft steht an genau einer Stelle: `skill/falzmarke/regeln/din5008.yaml`.
Diese Tests halten sie gegen das, was der Linter und der Typografie-Pass
tatsächlich tun.
"""

from __future__ import annotations

import copy

import pytest

from falzmarke import lint, regeln, typografie


# ── Q1: Jede Regel trägt eine Herkunft ──────────────────────────────────────

def test_jede_regel_hat_eine_herkunft():
    ohne = [r.get("id", "<ohne id>") for r in regeln.alle() if r.get("herkunft") not in regeln.HERKUENFTE]
    assert not ohne, f"Regeln ohne gültige Herkunft: {ohne}"


def test_belegte_regeln_nennen_ihre_quellen():
    """`mehrfach_bestaetigt` ohne Quellenliste wäre eine Behauptung."""
    stumm = [
        r["id"] for r in regeln.alle()
        if r["herkunft"] in (regeln.MEHRFACH, regeln.EINZELN) and not r.get("quellen")
    ]
    assert not stumm, f"Belegt, aber ohne Quelle: {stumm}"


def test_mehrfach_bestaetigt_hat_wirklich_mehrere_quellen():
    """Der Name muss halten, was er sagt: drei Quellen, oder eine plus zwei
    Implementierungen."""
    quellen = regeln.quellen()
    schwach = []
    for regel in regeln.alle():
        if regel["herkunft"] != regeln.MEHRFACH:
            continue
        namen = regel["quellen"]
        arten = [quellen[n]["art"] for n in namen]
        sekundaer = arten.count("sekundaerquelle")
        implementierungen = arten.count("implementierung")
        genug = len(namen) >= 3 or (sekundaer >= 1 and implementierungen >= 2)
        if not genug:
            schwach.append((regel["id"], namen))
    assert not schwach, f"Als mehrfach bestätigt geführt, aber zu dünn belegt: {schwach}"


def test_eigene_messung_zaehlt_nie_als_beleg():
    """Sie belegt, dass das Werkzeug einhält, was es sich vornimmt — nicht,
    dass das Vorgenommene stimmt. Als Bestätigung wäre sie ein Zirkelschluss."""
    falsch = [r["id"] for r in regeln.alle()
              if r["herkunft"] == regeln.MEHRFACH and "eigene_messung" in (r.get("quellen") or [])]
    assert not falsch, f"Eigene Messung als Bestätigung geführt: {falsch}"


def test_jede_linter_regel_ist_zugeordnet():
    """Sonst käme eine unbelegte Normregel über den Standardwert `werkzeug`
    herein und dürfte als Fehler wirken, ohne dass es jemand merkt."""
    bekannt = {r["lint"] for r in regeln.alle() if r.get("lint")}
    benutzt = _linter_regelnamen()
    fehlend = sorted(benutzt - bekannt)
    assert not fehlend, (
        f"Diese Linter-Regeln stehen in keiner Zeile von din5008.yaml: {fehlend}. "
        "Jede braucht einen Eintrag mit Herkunft — auch eine reine Werkzeugprüfung.")


def _linter_regelnamen() -> set[str]:
    """Die Regelnamen, die lint.py tatsächlich meldet — aus dem Syntaxbaum."""
    import ast
    import pathlib

    quelle = pathlib.Path(lint.__file__).read_text(encoding="utf-8")
    namen = set()
    for knoten in ast.walk(ast.parse(quelle)):
        if (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Attribute)
                and knoten.func.attr in ("fehler", "warnung") and len(knoten.args) >= 2):
            zweites = knoten.args[1]
            if isinstance(zweites, ast.Constant) and isinstance(zweites.value, str):
                namen.add(zweites.value)
    return namen


def test_der_regelnamen_leser_findet_ueberhaupt_etwas():
    """Gegenprobe: Eine leere Menge würde den Test darüber immer bestehen."""
    assert len(_linter_regelnamen()) >= 8


# ── Q2: Nur mehrfach Belegtes darf Fehler sein ──────────────────────────────

def test_kein_fehler_aus_einer_einzigen_quelle():
    zu_scharf = [
        r["id"] for r in regeln.alle()
        if r.get("wirkung") == "fehler" and r["herkunft"] not in regeln.DARF_FEHLER_SEIN
    ]
    assert not zu_scharf, f"Als Fehler geführt, aber nicht mehrfach belegt: {zu_scharf}"


@pytest.mark.parametrize("herkunft, erwartet", [
    (regeln.MEHRFACH, lint.FEHLER),
    (regeln.WERKZEUG, lint.FEHLER),
    (regeln.EINZELN, lint.WARNUNG),
])
def test_der_linter_stuft_nach_herkunft_ein(monkeypatch, herkunft, erwartet):
    monkeypatch.setattr(regeln, "herkunft_von_lint", lambda _: herkunft)
    monkeypatch.setattr(regeln, "quellenhinweis", lambda _: "")
    bericht = lint.Bericht()
    bericht.fehler(1, "probe", "Etwas stimmt nicht")
    assert [b.schwere for b in bericht.befunde] == [erwartet]


def test_offene_regel_wird_gar_nicht_gemeldet(monkeypatch):
    monkeypatch.setattr(regeln, "herkunft_von_lint", lambda _: regeln.OFFEN)
    bericht = lint.Bericht()
    bericht.fehler(1, "probe", "Etwas stimmt nicht")
    assert bericht.befunde == []


def test_die_meldung_nennt_die_quellenlage(monkeypatch):
    monkeypatch.setattr(regeln, "herkunft_von_lint", lambda _: regeln.EINZELN)
    bericht = lint.Bericht()
    bericht.fehler(1, "gruss", "Die Grußformel steht ohne Komma")
    assert "einzeln belegt" in bericht.befunde[0].meldung


def test_gegenprobe_eine_herabgestufte_fehlerregel_faellt_auf():
    """Ohne diesen Test belegte der obere nur, dass gerade alles passt.

    Hier wird eine als Fehler geführte Regel künstlich auf `einzeln_belegt`
    gesetzt — die Prüfung muss anschlagen.
    """
    kaputt = copy.deepcopy(regeln.alle())
    treffer = next(r for r in kaputt if r.get("wirkung") == "fehler")
    treffer["herkunft"] = regeln.EINZELN

    zu_scharf = [
        r["id"] for r in kaputt
        if r.get("wirkung") == "fehler" and r["herkunft"] not in regeln.DARF_FEHLER_SEIN
    ]
    assert zu_scharf == [treffer["id"]], "Die Prüfung schlägt beim sabotierten Stand nicht an"


# ── Q2: Der Typografie-Pass ändert nur auf tragfähiger Grundlage ────────────

def test_einzeln_belegte_ersetzung_aendert_den_text_nicht():
    """`schreibweise.einheiten` steht nur in einer Quelle — die Ersetzung
    zwischen Zahl und Einheit unterbleibt deshalb."""
    assert regeln.fuer_typografie("_einheiten")["herkunft"] == regeln.EINZELN
    text = "Die Sendung wiegt 5 kg."
    assert typografie.anwenden(text) == text


def test_mehrfach_belegte_ersetzung_greift_weiterhin():
    """Gegenprobe: Ein Pass, der gar nichts mehr täte, wäre kein Fortschritt.
    `schreibweise.abkuerzungen` ist mehrfach belegt und wirkt."""
    assert regeln.fuer_typografie("_abkuerzungen")["herkunft"] == regeln.MEHRFACH
    assert typografie.NBSP in typografie.anwenden("siehe z. B. dort")


def test_zurueckgehaltene_ersetzung_wird_als_vorschlag_sichtbar():
    """Zurückhalten allein wäre stilles Verschlucken. Was der Pass nicht tut,
    muss er wenigstens sagen können."""
    vorschlaege = typografie.vorschlaege("Die Sendung wiegt 5 kg.")
    assert any(kennung == "schreibweise.einheiten" for kennung, _ in vorschlaege)


def test_ohne_offene_faelle_gibt_es_keine_vorschlaege():
    assert typografie.vorschlaege("Ein Satz ohne Anlass.") == []


# ── Q1: Die Normreferenz bleibt am Stand der Regeldatei ─────────────────────

def test_die_normreferenz_ist_auf_dem_stand_der_regeldatei():
    """Der Abschnitt „Quellenlage je Regel“ in references/din5008.md wird aus
    der YAML erzeugt. Läuft er auseinander, ist die Doku still falsch —
    und genau das fällt sonst niemandem auf.
    """
    import subprocess
    import sys as _sys

    from conftest import REPO

    lauf = subprocess.run(
        [_sys.executable, str(REPO / "scripts" / "quellenlage.py"), "--pruefen"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
