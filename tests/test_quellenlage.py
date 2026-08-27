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


# ── Trägt eine Regel die Stufe, die sie behauptet? ──────────────────────────
#
# Anlass, gemessen am 25.08.2026 an v0.5.0: Die Regeldatei dokumentierte im
# Kopfkommentar, wann eine Regel `mehrfach_bestaetigt` heißen darf — und
# **alle 14** so geführten Regeln verfehlten diese Definition. Sie hatten je
# zwei Sekundärquellen plus die vendorte Implementierung; verlangt waren drei
# Quellen beziehungsweise eine plus zwei Implementierungen. Niemandem fiel es
# auf, weil `herkunft:` von Hand gesetzt wurde und nichts nachzählte.
#
# Eine Definition, die nur im Kommentar steht, ist keine Definition.

import yaml

from falzmarke import regeln as regeln_modul


def _regeldatei(tmp_path, aenderung):
    """Die echte Regeldatei, an einer Stelle verändert."""
    quelle = regeln_modul.DATEI.read_text(encoding="utf-8")
    daten = yaml.safe_load(quelle)
    aenderung(daten)
    ziel = tmp_path / "din5008.yaml"
    ziel.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    return ziel


def _laden(pfad):
    """Die Regeldatei unter einem anderen Pfad laden, ohne den Cache zu stören."""
    alt = regeln_modul.DATEI
    try:
        regeln_modul.DATEI = pfad
        regeln_modul.laden.cache_clear()
        return regeln_modul.laden()
    finally:
        regeln_modul.DATEI = alt
        regeln_modul.laden.cache_clear()


def test_die_echte_regeldatei_traegt_ihre_stufen():
    """Positivprobe. Ohne sie sagen die Gegenproben nur, dass irgendetwas blockt."""
    assert len(regeln_modul.alle()) > 0


def test_mehrfach_ohne_zwei_volle_quellen_wird_abgewiesen(tmp_path):
    """Der Fall, der v0.5.0 vierzehnmal unbemerkt blieb."""
    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] == "geometrie.form_a.masse":
                regel["herkunft"] = "mehrfach_bestaetigt"
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, kippen))
    assert "voll zählende" in str(fehler.value), str(fehler.value)


def test_vendorte_implementierung_hebt_nicht_auf_mehrfach(tmp_path):
    """Der Kern: falzmarke setzt mit letter-pro und darf sich damit nicht selbst bestätigen.

    Zwei externe Zeichnungen tragen eine Form-B-Regel. Fällt eine davon weg,
    bleibt eine externe Quelle plus letter-pro — und das darf nicht mehr für
    `mehrfach_bestaetigt` reichen, sonst wäre der Sollwert gegen ein PDF
    geprüft, das dieselbe Quelle erzeugt hat.
    """
    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] == "geometrie.form_b.falzmarken":
                regel["quellen"] = ["massskizze_b", "letter_pro"]
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, kippen))
    assert "nur 1 voll zählende" in str(fehler.value), str(fehler.value)


def test_quelle_ohne_zaehlstufe_wird_abgewiesen(tmp_path):
    """Eine neue Quelle darf nicht stillschweigend als Beleg durchgehen."""
    def kippen(daten):
        daten["quellen"]["massskizze_b"].pop("zaehlt", None)
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, kippen))
    assert "zaehlt=" in str(fehler.value), str(fehler.value)


def test_einzeln_belegt_braucht_wenigstens_einen_beleg(tmp_path):
    """`eigene_messung` allein ist kein Beleg — sie misst nur uns selbst."""
    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] == "geometrie.form_a.masse":
                regel["quellen"] = ["eigene_messung"]
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, kippen))
    assert "trägt sie" in str(fehler.value), str(fehler.value)


def test_letter_pro_traegt_einzeln_aber_nicht_voll():
    """Die Einstufung selbst — sonst könnte sie jemand still zurückdrehen."""
    quellen = regeln_modul.quellen()
    assert quellen["letter_pro"]["zaehlt"] == regeln_modul.ZAEHLT_EINZELN
    assert quellen["eigene_messung"]["zaehlt"] == regeln_modul.ZAEHLT_NIE


# ── Unabhängigkeit: zwei Ansichten derselben Sache sind ein Beleg ────────────
#
# Befund vom 27.08.2026 (docs/quellenunabhaengigkeit-2026-08-27.md): Die
# Form-B-Zeichnung auf Wikimedia Commons (2013, CC0) und die im
# Onlineprinters-Magazin (2021) sind bis in den Fußtext deckungsgleich. Sie
# tragen deshalb dieselbe `gruppe:` — und neun Regeln, die ihre Stufe auf genau
# dieses Paar stützen, stehen damit auf einem einzigen Beleg.
#
# Die Stufen sind **nicht** geändert. Der Test hält den Befund fest, damit er
# sichtbar bleibt und sich nicht unbemerkt verschiebt: Wächst die Liste, ist
# eine Regel dazugekommen, die zu stark belegt ist. Schrumpft sie, hat jemand
# eine echte zweite Quelle nachgetragen — dann gehört die Zeile hier
# angepasst, und das ist eine gute Nachricht.

STUFE_TRAEGT_NICHT = [
    "geometrie.betreffabstand",
    "geometrie.form_b.anschriftfeld",
    "geometrie.form_b.briefkopf",
    "geometrie.form_b.falzmarken",
    "geometrie.form_b.infoblock",
    "geometrie.form_b.zonen",
    "geometrie.grundzeilenhoehe",
    "geometrie.lochmarke",
    "text.vermerke_max_3",
]


def test_jede_quelle_traegt_eine_gruppe():
    """Ohne Gruppe fiele eine Quelle stillschweigend als eigener Beleg durch."""
    ohne = [n for n, d in regeln.quellen().items() if not d.get("gruppe")]
    assert not ohne, f"Quellen ohne `gruppe:`: {ohne}"


def test_der_offene_rest_ist_genau_dieser():
    assert regeln.stufe_traegt_nicht() == STUFE_TRAEGT_NICHT, (
        "Die Beleglage hat sich verschoben. Siehe "
        "docs/quellenunabhaengigkeit-2026-08-27.md und Issue #16.")


def test_die_messung_wuerde_eine_verschiebung_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass eine Liste gleich ist.

    Wären die beiden Zeichnungen als unabhängig geführt — also in verschiedenen
    Gruppen —, müsste die Liste kürzer werden. Genau so war es bis zum
    27.08.2026.
    """
    echt = regeln.quellen()
    getrennt = {n: dict(d) for n, d in echt.items()}
    getrennt["onlineprinters"]["gruppe"] = "so-war-es-vorher"
    assert getrennt["onlineprinters"]["gruppe"] != echt["onlineprinters"]["gruppe"], \
        "die Sabotage greift nicht"

    def belege(regel):
        return {getrennt[n].get("gruppe", n)
                for n in regeln._quellennamen(regel)
                if getrennt.get(n, {}).get("zaehlt") == regeln.ZAEHLT_VOLL}

    vorher = sorted(r["id"] for r in regeln.alle()
                    if r.get("herkunft") == regeln.MEHRFACH and len(belege(r)) < 2)
    assert len(vorher) < len(STUFE_TRAEGT_NICHT), (
        "Mit getrennten Gruppen müssten weniger Regeln auffallen — sonst misst "
        "die Gruppierung nichts.")
