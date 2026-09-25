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


# ── Dieselbe Pflicht für die Schritte des Typografie-Passes (#332) ──────────
#
# `typografie.SCHRITTE` nennt je Schritt den Namen der Regel, an der er hängt.
# Bis #332 prüfte das niemand: Der Schritt `_vor_angabe` hing an
# `schreibweise.zahlengliederung`, und keine Probe fragte, ob die Regel sagt,
# was der Schritt tut. Die Zuordnung Schritt → Eintrag ist jetzt Pflicht, und
# zwar maschinell — gelesen wird der Syntaxbaum von typografie.py, nicht eine
# Liste, die man nachzuziehen vergisst. Ein neuer Schrittname ohne Eintrag in der
# Regeldatei lässt die Probe scheitern; der Eintrag gehört in dieselbe Änderung.


def _typografie_schrittnamen() -> set[str]:
    """Die Regelnamen in `typografie.SCHRITTE` — aus dem Syntaxbaum.

    Gelesen wird das zweite Element jedes Paars der Liste. Ein Schritt ohne
    Namen (`None`) ist Satztechnik des Werkzeugs und braucht keinen Eintrag.
    """
    import ast
    import pathlib

    quelle = pathlib.Path(typografie.__file__).read_text(encoding="utf-8")
    namen = set()
    for knoten in ast.walk(ast.parse(quelle)):
        if not (isinstance(knoten, ast.Assign) and isinstance(knoten.value, ast.List)
                and any(isinstance(z, ast.Name) and z.id == "SCHRITTE" for z in knoten.targets)):
            continue
        for paar in knoten.value.elts:
            if isinstance(paar, ast.Tuple) and len(paar.elts) == 2:
                zweites = paar.elts[1]
                if isinstance(zweites, ast.Constant) and isinstance(zweites.value, str):
                    namen.add(zweites.value)
    return namen


def _schritte_ohne_eintrag(katalog: list[dict]) -> list[str]:
    zugeordnet = {r["typografie"] for r in katalog if r.get("typografie")}
    return sorted(_typografie_schrittnamen() - zugeordnet)


def _schritte_mit_zwei_regeln(katalog: list[dict]) -> list[str]:
    """`regeln._nach_typografie` baut ein Wörterbuch: Beanspruchen zwei Einträge
    denselben Schritt, gewinnt der letzte, und der andere bleibt stumm stehen."""
    gesehen: dict[str, int] = {}
    for regel in katalog:
        if regel.get("typografie"):
            gesehen[regel["typografie"]] = gesehen.get(regel["typografie"], 0) + 1
    return sorted(schritt for schritt, anzahl in gesehen.items() if anzahl > 1)


def test_der_schrittnamen_leser_findet_ueberhaupt_etwas():
    """Gegenprobe: Eine leere Menge würde die Tests darunter immer bestehen."""
    namen = _typografie_schrittnamen()
    assert {"_abkuerzungen", "_datum", "_einheiten", "_vor_angabe"} <= namen, namen


def test_jeder_benannte_typografie_schritt_ist_zugeordnet():
    fehlend = _schritte_ohne_eintrag(regeln.alle())
    assert not fehlend, (
        f"Diese Schritte des Typografie-Passes stehen in keiner Zeile von din5008.yaml: {fehlend}. "
        "Jeder braucht einen Eintrag mit `typografie:`, Herkunft und einem Titel, der sagt, was er tut.")


def test_kein_eintrag_ohne_schritt_im_code():
    """Die Gegenrichtung: ein Eintrag, dessen Schritt es nicht mehr gibt, sieht
    in der Normreferenz wie eine wirksame Regel aus."""
    bekannt = {r["typografie"] for r in regeln.alle() if r.get("typografie")}
    verwaist = sorted(bekannt - _typografie_schrittnamen())
    assert not verwaist, f"Diese Einträge nennen einen Schritt, den es nicht gibt: {verwaist}"


def test_kein_schritt_haengt_an_zwei_regeln():
    doppelt = _schritte_mit_zwei_regeln(regeln.alle())
    assert not doppelt, (
        f"Diese Schritte beansprucht mehr als ein Eintrag: {doppelt}. Ein Wörterbuch behält "
        "den letzten — welcher, hinge an der Reihenfolge in der Datei.")


def test_die_zuordnung_der_schritte_wuerde_eine_luecke_und_einen_doppelten_bemerken():
    """Gegenprobe: Die Prüfungen darüber sind grün, solange nichts fehlt — hier
    fehlt etwas, und sie müssen es finden."""
    katalog = regeln.alle()
    assert _schritte_ohne_eintrag(katalog) == [] and _schritte_mit_zwei_regeln(katalog) == [], (
        "Vorbedingung: der echte Bestand ist sauber")

    ohne = [r for r in katalog if r.get("typografie") != "_vor_angabe"]
    assert len(ohne) == len(katalog) - 1, "die Sabotage nahm nichts heraus"
    assert _schritte_ohne_eintrag(ohne) == ["_vor_angabe"]

    zwilling = dict(next(r for r in katalog if r.get("typografie") == "_vor_angabe"), id="probe.zwilling")
    assert _schritte_mit_zwei_regeln(katalog + [zwilling]) == ["_vor_angabe"]


# ── Dieselbe Pflicht für die Prüfungen der fertigen Datei (#292) ────────────
#
# `pruefung_eml.py` misst die fertige `.eml`. Bis #292 trug dort keine Prüfung
# einen Regelnamen, und damit wirkte jede als Fehler — `regeln.deckel(None)` gibt
# vorsichtshalber `fehler` zurück. Für die technischen ist das richtig, für eine
# Regel auf der Ebene `praxis` nicht (ADR 0035). Die Zuordnung ist jetzt Pflicht,
# und zwar maschinell: Gelesen wird der Syntaxbaum, nicht eine Liste, die man
# nachzuziehen vergisst.


def _pruefungsregelnamen() -> set[str]:
    """Die Regelnamen, die `pruefung_eml.py` meldet — aus dem Syntaxbaum.

    Gelesen wird das zweite Argument von `_wahr(bericht, "<regel>", …)`.
    """
    import ast
    import pathlib

    from falzmarke import pruefung_eml

    quelle = pathlib.Path(pruefung_eml.__file__).read_text(encoding="utf-8")
    namen = set()
    for knoten in ast.walk(ast.parse(quelle)):
        if (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
                and knoten.func.id == "_wahr" and len(knoten.args) >= 2):
            zweites = knoten.args[1]
            if isinstance(zweites, ast.Constant) and isinstance(zweites.value, str):
                namen.add(zweites.value)
    return namen


def test_jede_pruefung_der_fertigen_datei_ist_zugeordnet():
    bekannt = {r["pruefung"] for r in regeln.alle() if r.get("pruefung")}
    benutzt = _pruefungsregelnamen()
    fehlend = sorted(benutzt - bekannt)
    assert not fehlend, (
        f"Diese Prüfungen stehen in keiner Zeile von email.yaml: {fehlend}. "
        "Jede braucht einen Eintrag mit Herkunft und Ebene — auch eine reine "
        "Werkzeugprüfung. Ohne ihn wirkt sie als Fehler, ohne dass jemand sagt, "
        "wovon sie redet (#292).")


def test_der_pruefungsnamen_leser_findet_ueberhaupt_etwas():
    """Gegenprobe: Eine leere Menge bestünde den Test darüber immer.

    Die Zahl ist eine untere Schranke und absichtlich nicht die genaue: Sie soll
    beim Hinzufügen einer Prüfung nicht rot werden, wohl aber, wenn der Leser
    ins Leere greift — etwa weil `_wahr` umbenannt wurde.
    """
    assert len(_pruefungsregelnamen()) >= 20


def test_kein_eintrag_ohne_pruefung_im_code():
    """Die Gegenrichtung: ein Katalogeintrag, den niemand mehr meldet.

    Er sieht wie Abdeckung aus und ist keine — und beim nächsten Umbau glaubt
    jemand, die Regel werde geprüft.
    """
    bekannt = {r["pruefung"] for r in regeln.alle() if r.get("pruefung")}
    verwaist = sorted(bekannt - _pruefungsregelnamen())
    assert not verwaist, (
        f"Diese Einträge nennen eine Prüfung, die es nicht mehr gibt: {verwaist}")


# ── Q2: Nur mehrfach Belegtes darf Fehler sein ──────────────────────────────

def test_kein_fehler_aus_einer_einzigen_quelle():
    zu_scharf = [
        r["id"] for r in regeln.alle()
        if r.get("wirkung") == "fehler" and r["herkunft"] not in regeln.DARF_FEHLER_SEIN
    ]
    assert not zu_scharf, f"Als Fehler geführt, aber nicht mehrfach belegt: {zu_scharf}"


def test_keine_regel_gibt_sich_schaerfer_als_sie_darf():
    """`wirkung:` in der Regeldatei ist eine Behauptung — hier wird sie geprüft.

    Ohne diese Prüfung könnte `wirkung: fehler` neben `ebene: praxis` stehen.
    Der Linter täte das Richtige (er rechnet über `deckel()`), aber die
    Regeldatei behauptete etwas anderes — und gelesen wird die Regeldatei.

    Gemessen beim Schreiben dieser Prüfung, am 28.08.2026: Vier Regeln stehen
    auf `warnung`, obwohl sie Fehler sein dürften — `werkzeug.tabulator`,
    `werkzeug.umbruch`, `email.datum`, `email.anlage`. Das ist kein Fehler,
    sondern eine Wahl: Sie werden über `bericht.warnung()` gemeldet, nicht über
    `bericht.fehler()`. `deckel()` ist eine **Obergrenze**, keine Vorschrift.
    Milder als erlaubt darf eine Regel sein; schärfer nicht.
    """
    zu_scharf = [
        (r["id"], regeln.deckel(r))
        for r in regeln.alle()
        if r.get("wirkung") == "fehler" and regeln.deckel(r) != regeln.DECKEL_FEHLER
    ]
    assert not zu_scharf, (
        "Als Fehler geführt, obwohl gedeckelt:\n  "
        + "\n  ".join(f"{i}: darf höchstens {d!r} sein" for i, d in zu_scharf))


def test_die_pruefung_wuerde_eine_zu_scharfe_regel_bemerken():
    """Gegenprobe. Eine Praxis-Regel, die sich als Fehler ausgibt, muss auffallen."""
    erfunden = {"id": "probe", "ebene": regeln.EBENE_PRAXIS,
                "herkunft": regeln.MEHRFACH, "wirkung": "fehler"}
    assert regeln.deckel(erfunden) == regeln.DECKEL_WARNUNG, (
        "Die Ebene deckelt nicht — dann greift die Prüfung darüber ins Leere.")


@pytest.mark.parametrize("herkunft, erwartet", [
    (regeln.MEHRFACH, lint.FEHLER),
    (regeln.WERKZEUG, lint.FEHLER),
    (regeln.PRIMAER, lint.FEHLER),
    (regeln.EINZELN, lint.WARNUNG),
])
def test_der_linter_stuft_nach_herkunft_ein(monkeypatch, herkunft, erwartet):
    """Die erste Achse allein — ohne Ebene entscheidet die Belegstärke."""
    monkeypatch.setattr(regeln, "deckel_von_lint",
                        lambda _: regeln.deckel({"herkunft": herkunft}))
    monkeypatch.setattr(regeln, "quellenhinweis", lambda _: "")
    bericht = lint.Bericht()
    bericht.fehler(1, "probe", "Etwas stimmt nicht")
    assert [b.schwere for b in bericht.befunde] == [erwartet]


@pytest.mark.parametrize("ebene, erwartet", [
    (regeln.EBENE_NORM, lint.FEHLER),
    (regeln.EBENE_TECHNIK, lint.FEHLER),
    (regeln.EBENE_WERKZEUG, lint.FEHLER),
    (regeln.EBENE_RECHT, lint.WARNUNG),
    (regeln.EBENE_PRAXIS, lint.WARNUNG),
])
def test_die_ebene_deckelt_auch_bei_bestem_beleg(monkeypatch, ebene, erwartet):
    """Die Kernzusage von ADR 0035, und der Grund für die zweite Achse.

    Der Beleg ist hier absichtlich der bestmögliche: `mehrfach_bestaetigt`
    dürfte nach der ersten Achse ein Fehler sein. Bleibt eine Regel der Ebene
    Recht oder Praxis trotzdem eine Warnung, dann deckelt die Ebene wirklich —
    und der Eintrag ist umgesetzt und nicht nur beschrieben.
    """
    monkeypatch.setattr(regeln, "deckel_von_lint", lambda _: regeln.deckel(
        {"herkunft": regeln.MEHRFACH, "ebene": ebene}))
    monkeypatch.setattr(regeln, "quellenhinweis", lambda _: "")
    bericht = lint.Bericht()
    bericht.fehler(1, "probe", "Etwas stimmt nicht")
    assert [b.schwere for b in bericht.befunde] == [erwartet]


def test_offene_regel_wird_gar_nicht_gemeldet(monkeypatch):
    monkeypatch.setattr(regeln, "deckel_von_lint", lambda _: regeln.DECKEL_KEINE)
    bericht = lint.Bericht()
    bericht.fehler(1, "probe", "Etwas stimmt nicht")
    assert bericht.befunde == []


def test_die_meldung_nennt_die_quellenlage(monkeypatch):
    """Die Regel ist `datum` und nicht mehr `gruss` (#350).

    `text.gruss_ohne_komma` nennt genau eine Quelle, und die schweigt zur Regel
    — deshalb führt sie `werkzeug`. Der Test übersteuerte die Herkunft auf
    `einzeln_belegt` und baute damit eine Lage nach, die `_pruefe_beleglage`
    beim Laden abweisen würde: belegt, aber von niemandem. Seit die Meldung
    schweigende Quellen überspringt, hat sie dort nichts mehr zu nennen — zu
    Recht. Gemessen wird jetzt an `schreibweise.datum`, die wirklich einzeln
    belegt ist und deren Quelle wirklich spricht.
    """
    assert regeln.herkunft_von_lint("datum") == regeln.EINZELN, (
        "`schreibweise.datum` ist nicht mehr einzeln belegt — der Test misst nichts mehr")
    monkeypatch.setattr(regeln, "herkunft_von_lint", lambda _: regeln.EINZELN)
    bericht = lint.Bericht()
    bericht.fehler(1, "datum", "Das Datum steht in keiner der beiden Formen")
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
    """`schreibweise.einheiten` hat keine Quelle, die zur Sache etwas sagt (#31)
    — die Ersetzung zwischen Zahl und Einheit unterbleibt trotzdem.

    Die Regel führt seither `werkzeug`: eine Setzgewohnheit ohne Beleg. Diese
    Herkunft dürfte nach `DARF_FEHLER_SEIN` ersetzen; hier soll sie es nicht,
    denn sie wirkt weiter als Warnung (AC 2) und verstummt nicht zur Ersetzung.
    """
    assert regeln.fuer_typografie("_einheiten")["herkunft"] == regeln.WERKZEUG
    text = "Die Sendung wiegt 5 kg."
    assert typografie.anwenden(text) == text
    assert any(k == "schreibweise.einheiten" for k, _ in typografie.vorschlaege(text)), (
        "die zurückgehaltene Ersetzung ist nicht mehr sichtbar — die Regel wäre verstummt")


@pytest.mark.parametrize("schritt, text", [
    ("_abkuerzungen", "siehe z. B. dort"),
    ("_datum", "am 3. Oktober"),
])
def test_herabgestufte_ersetzung_aendert_den_text_nicht(monkeypatch, schritt, text):
    """AC 3: Datum und Abkürzungen standen auf `mehrfach_bestaetigt`, gestützt
    auf zwei volle Quellen — deren zweite (`onlineprinters`) schweigt. Mit nur
    einer sprechenden Quelle setzt der Pass nichts mehr, sagt es aber.

    Die zweite Hälfte ist die Gegenprobe: Ohne sie hielte der Test nur fest,
    dass der Pass nie setzt. Unter `mehrfach_bestaetigt` setzt er dieselbe
    Stelle, dann ist der Unterschied die Stufe und nicht der Text.
    """
    regel = regeln.fuer_typografie(schritt)
    assert regel["herkunft"] == regeln.EINZELN, regel["id"]
    assert typografie.NBSP not in typografie.anwenden(text), (
        f"{regel['id']}: der Pass setzt weiter, obwohl die zweite Quelle schweigt")
    assert any(k == regel["id"] for k, _ in typografie.vorschlaege(text)), (
        f"{regel['id']}: nichts zu sehen — die Regel wäre verstummt statt herabgestuft")

    echt = regeln._nach_typografie()
    monkeypatch.setattr(regeln, "_nach_typografie", lambda: {
        **echt, schritt: {**echt[schritt], "herkunft": regeln.MEHRFACH}})
    assert typografie.NBSP in typografie.anwenden(text), (
        "Gegenprobe: unter `mehrfach_bestaetigt` müsste dieselbe Stelle gesetzt werden")


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
    """Der echte Bestand, an einer Stelle verändert.

    Seit ADR 0035 sind es drei Dateien: ein Quellen-Register und zwei
    Regeldateien. Der Helfer führt sie zusammen, lässt die Sabotage darauf los
    und schreibt sie in einen eigenen Baum — das echte Repository wird nie
    angefasst. Die Änderungsfunktion sieht `daten["regeln"]` und
    `daten["quellen"]` wie zuvor.
    """
    quellen = yaml.safe_load(regeln_modul.QUELLDATEI.read_text(encoding="utf-8"))["quellen"]
    regeln_ = []
    for pfad in regeln_modul.REGELDATEIEN:
        regeln_ += yaml.safe_load(pfad.read_text(encoding="utf-8"))["regeln"]
    daten = {"regeln": regeln_, "quellen": quellen}
    aenderung(daten)

    ziel_q = tmp_path / "quellen.yaml"
    ziel_q.write_text(yaml.safe_dump({"quellen": daten["quellen"]}, allow_unicode=True),
                      encoding="utf-8")
    ziel_r = tmp_path / "regeln.yaml"
    ziel_r.write_text(yaml.safe_dump({"regeln": daten["regeln"]}, allow_unicode=True),
                      encoding="utf-8")
    return ziel_q, ziel_r


def _laden(pfade, ebene_pflicht=False):
    """Den sabotierten Bestand laden, ohne den Cache zu stören."""
    ziel_q, ziel_r = pfade
    alt_q, alt_r = regeln_modul.QUELLDATEI, regeln_modul.REGELDATEIEN
    try:
        regeln_modul.QUELLDATEI = ziel_q
        regeln_modul.REGELDATEIEN = {ziel_r: ebene_pflicht}
        regeln_modul.laden.cache_clear()
        return regeln_modul.laden()
    finally:
        regeln_modul.QUELLDATEI = alt_q
        regeln_modul.REGELDATEIEN = alt_r
        regeln_modul.laden.cache_clear()


def test_die_echte_regeldatei_traegt_ihre_stufen():
    """Positivprobe. Ohne sie sagen die Gegenproben nur, dass irgendetwas blockt."""
    assert len(regeln_modul.alle()) > 0


# ── Ein doppelter Schlüssel darf nicht still den ersten fressen (#180) ───────
#
# Befund vom 24.09.2026: `geometrie.form_a.masse` trug zwei `bemerkung:` — einen
# aus #345, einen aus #18. PyYAML nimmt in diesem Fall wortlos den letzten, und
# der zuerst geschriebene Absatz, die Erklärung der 32 mm, war im geladenen
# Regelwerk nicht mehr vorhanden. Die Datei lädt ja; nichts hatte etwas zu
# melden. Seither liest `regeln._yaml_laden()` mit einem eigenen Loader.
#
# Die drei Tests gehören zusammen: der erste zeigt, dass es meldet, der zweite,
# dass es NICHT irgendetwas meldet (sondern denselben Inhalt ohne Duplikat
# durchlässt), der dritte, dass der Schutz auch für `quellen.yaml` gilt.

def _mit_doppeltem_schluessel(tmp_path, zeilen: str) -> Path:
    ziel = tmp_path / "regeln.yaml"
    ziel.write_text(zeilen, encoding="utf-8")
    return ziel


_EINE_REGEL = """regeln:
  - id: probe.regel
    titel: Eine Probe
    herkunft: werkzeug
{zusatz}    wirkung: warnung
"""


def test_doppelter_schluessel_wird_abgewiesen(tmp_path):
    ziel = _mit_doppeltem_schluessel(
        tmp_path, _EINE_REGEL.format(
            zusatz="    bemerkung: erster Absatz\n    bemerkung: zweiter Absatz\n"))
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        regeln_modul._yaml_laden(ziel)
    meldung = str(fehler.value)
    assert "bemerkung" in meldung, meldung
    assert "doppelt" in meldung, meldung


def test_ohne_doppelten_schluessel_laedt_dieselbe_datei(tmp_path):
    """Die Gegenprobe zur Gegenprobe: Der Wächter darf nicht alles abweisen.

    Ohne sie belegte der Test darüber nur, dass irgendetwas blockt — und ein
    Loader, der jede Datei ablehnt, bestünde ihn ebenso.
    """
    ziel = _mit_doppeltem_schluessel(
        tmp_path, _EINE_REGEL.format(zusatz="    bemerkung: zweiter Absatz\n"))
    daten = regeln_modul._yaml_laden(ziel)
    assert daten["regeln"][0]["bemerkung"] == "zweiter Absatz"


def test_der_waechter_gilt_auch_fuer_das_quellen_register(tmp_path):
    """`quellen.yaml` geht durch dieselbe Funktion — sonst wäre die Hälfte des
    Bestands ungeschützt, und zwar die, an der jede Stufe hängt."""
    ziel = tmp_path / "quellen.yaml"
    ziel.write_text(
        "quellen:\n"
        "  probe:\n"
        "    art: sekundaerquelle\n"
        "    zaehlt: voll\n"
        "    zaehlt: nie\n",
        encoding="utf-8")
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        regeln_modul._yaml_laden(ziel)
    assert "zaehlt" in str(fehler.value), str(fehler.value)


def test_die_echten_regeldateien_haben_keinen_doppelten_schluessel():
    """Positivprobe am ausgeführten Pfad, nicht an einer Kopie im tmp-Baum.

    `laden()` ist die Stelle, die das System benutzt; sie geht über
    `_yaml_laden()`. Bricht hier etwas, liegt es an einer echten Datei.
    """
    for pfad in [regeln_modul.QUELLDATEI, *regeln_modul.REGELDATEIEN]:
        assert regeln_modul._yaml_laden(pfad), pfad.name


def test_mehrfach_ohne_zwei_volle_quellen_wird_abgewiesen(tmp_path):
    """Der Fall, der v0.5.0 vierzehnmal unbemerkt blieb.

    Die Regel, an der gekippt wird, steht **nicht** fest im Test: Sie wird zur
    Laufzeit gesucht. Hier stand bis zum 29.08.2026 `geometrie.form_a.masse`,
    und mit der zweiten Form-A-Quelle aus Issue #18 verlor sie die Eigenschaft,
    auf die dieser Test sich stützt — die Sabotage lief ins Leere, ohne dass
    an der Prüfung etwas falsch war. Ein Testfall an der falschen Stelle.
    """
    quellen = regeln_modul.quellen()

    def volle(regel):
        return sum(1 for n in regel.get("quellen") or []
                   if quellen[n].get("zaehlt") == regeln_modul.ZAEHLT_VOLL)

    # Regeln mit eigenem `deckel:` bleiben außen vor — dieselbe Sorte Falle wie
    # 2026-08-29, nur eine Ebene weiter: Sie scheitern beim Kippen schon an der
    # Deckelprüfung, und die Beleglage käme nie zur Sprache. Am 25.09.2026 rückte
    # `text.anrede_komma` an die erste Stelle, weil die Geometrie-Regeln davor
    # Quellen dazubekommen haben (#355).
    kandidaten = [r["id"] for r in regeln_modul.alle()
                  if (r.get("quellen") or []) and volle(r) < 2 and "deckel" not in r]
    assert kandidaten, (
        "Keine Regel mehr mit weniger als zwei voll zählenden Quellen und ohne "
        "eigenen Deckel — dann kann dieser Test nichts mehr sabotieren und "
        "belegt nichts.")
    ziel = kandidaten[0]

    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] == ziel:
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
    """`eigene_messung` allein ist kein Beleg — sie misst nur uns selbst.

    Die Regel, an der gekippt wird, steht **nicht** fest im Test. Hier stand bis
    zum 24.09.2026 `geometrie.form_a.masse`; mit ihrer Anhebung auf
    `mehrfach_bestaetigt` (#180) hätte dieselbe Sabotage einen anderen Melder
    ausgelöst — „nur 0 voll zählende Quelle(n)" statt „trägt sie" —, und der Test
    wäre aus einem Grund rot geworden, den er gar nicht prüft. Derselbe Unfall
    wie am 29.08.2026 eine Prüfung weiter oben, nur umgekehrt herum.
    """
    kandidaten = [r["id"] for r in regeln_modul.alle()
                  if r.get("herkunft") == regeln_modul.EINZELN and (r.get("quellen") or [])]
    assert kandidaten, (
        "Keine Regel mehr auf `einzeln_belegt` mit Quellen — dann kann dieser "
        "Test nichts sabotieren und belegt nichts.")
    ziel = kandidaten[0]

    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] == ziel:
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
]
# `text.vermerke_max_3` stand bis zum 21.09.2026 in dieser Liste. Ihre zweite
# volle Quelle (`onlineprinters`) schweigt (#31), die Regel ist deshalb nicht
# mehr mehrfach belegt und fällt aus der Messung heraus — nicht, weil sie
# nachgetragen wurde, sondern weil sie die Stufe nicht mehr behauptet.


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


# ── Sagt die Quelle zur Regel überhaupt etwas? ──────────────────────────────
#
# Befund von Issue #31: Die Validierung prüft, ob eine Regel ihre Zählstufe
# trägt — nicht, ob die genannte Quelle zur Sache etwas hergibt. Belegt an
# `text.anrede_komma` (#30): mehrfach bestätigt, Läufe scheiternd, gestützt
# unter anderem auf einen Wikipedia-Artikel, der das Wort „Komma" kein
# einziges Mal enthält.
#
# Am 27.08.2026 wurde die für `onlineprinters` ausstehende Prüfung nachgeholt:
# Artikeltext vollständig gelesen (7.035 Zeichen), Negativbefunde gegen das
# rohe HTML gegengeprüft, damit sie nicht an der Textextraktion hängen.
# Ergebnis in `belegt_durch` je Regel — auch dort, wo die Quelle schweigt.
#
# Bis zum 21.09.2026 änderte nichts davon Stufen; die Entscheidung vom
# 27.08.2026 („Stufen bleiben, bis #12 kommt“) hielt sie unangetastet. Der
# zweite Zuschnitt von #31 nimmt sie zurück: Eine Quelle, deren `belegt_durch`
# mit `SCHWEIGT` beginnt, zählt für die Stufe nicht mehr mit. `belegt_durch`
# sagt weiter, warum sie schweigt; `schweigende_quellen()` liest es von dort.

SCHWEIGENDE_QUELLEN = [
    # Seit 25.09.2026 (#355): Die Onlineprinters-Zeichnung wurde für die drei
    # Geometrie-Regeln nachgelesen, die auf ihr allein standen. Sie bemaßt
    # weder die Höhe des Informationsblocks noch die Marken. Anders als 2026-08
    # kostet das hier keine Stufe: Zwei neue Quellen tragen sie (ADR 0047).
    ("geometrie.infoblock_mindesthoehe", "onlineprinters"),
    ("geometrie.marken_heftrand", "onlineprinters"),
    # `geometrie.markenlaenge` ist der umgekehrte Fall: Hier schweigen ALLE drei,
    # und zwei davon ausdrücklich („keine Vorgaben“). Die Regel ist deshalb
    # keine Normaussage mehr, sondern `werkzeug`.
    ("geometrie.markenlaenge", "natusch"),
    ("geometrie.markenlaenge", "onlineprinters"),
    ("geometrie.markenlaenge", "weka_sekretaria"),
    ("schreibweise.abkuerzungen", "onlineprinters"),
    ("schreibweise.datum", "onlineprinters"),
    ("schreibweise.einheiten", "onlineprinters"),
    ("schreibweise.geldbetrag", "onlineprinters"),
    ("schreibweise.zahlengliederung", "onlineprinters"),
    ("text.anlagen_ohne_doppelpunkt", "onlineprinters"),
    ("text.anrede_komma", "onlineprinters"),
    ("text.anschrift_ohne_leerzeilen", "onlineprinters"),
    ("text.gruss_ohne_komma", "onlineprinters"),
    # Seit 22.09.2026 nicht mehr alle von `onlineprinters`: Die Zeichnung
    # `massskizze_b` bemaßt die Zone (17,7 mm), nennt aber keine Zeilenzahl.
    ("text.vermerke_max_3", "massskizze_b"),
    ("text.vermerke_max_3", "onlineprinters"),
]

#: Wie viele Quelle-Regel-Paare noch niemand nachgelesen hat. Die Zahl soll
#: fallen. Steigt sie, ist eine Quelle eingetragen worden, ohne zu sagen, wo
#: sie die Regel hergibt — genau der Vorgang, den #31 beenden will.
UNGEPRUEFTE_PAARE = 24   # 26 bis zum 25.09.2026 — die beiden offenen `onlineprinters`-Paare
                         # bei `geometrie.infoblock_mindesthoehe` und `geometrie.markenlaenge`
                         # sind nachgelesen; beide schweigen (#355). Die sechs Paare der drei
                         # neuen Quellen zählen nicht mit: Sie kamen mit ihrer Fundstelle.


def test_die_schweigenden_quellen_sind_genau_diese():
    assert regeln.schweigende_quellen() == SCHWEIGENDE_QUELLEN, (
        "Die Belegprüfung hat sich verschoben — siehe Issue #31 und "
        "docs/quellenpruefung-onlineprinters-2026-08-27.md.")


def test_die_zahl_ungeprueffter_paare_steigt_nicht():
    ist = len(regeln.ohne_belegpruefung())
    assert ist <= UNGEPRUEFTE_PAARE, (
        f"{ist} Quelle-Regel-Paare ohne `belegt_durch:` — vorher {UNGEPRUEFTE_PAARE}. "
        "Wer eine Quelle einträgt, sagt dazu, wo sie die Regel hergibt.")
    if ist < UNGEPRUEFTE_PAARE:
        raise AssertionError(
            f"Erfreulich: nur noch {ist} ungeprüfte Paare statt {UNGEPRUEFTE_PAARE}. "
            "Bitte UNGEPRUEFTE_PAARE hier nachziehen, damit die Schranke greift.")


def test_wer_schweigt_traegt_auch_eine_begruendung():
    """Ein „SCHWEIGT" ohne Grund wäre so wenig wert wie die Quelle selbst."""
    for regel in regeln.alle():
        for quelle, text in (regel.get("belegt_durch") or {}).items():
            if str(text).startswith(regeln.SCHWEIGT):
                assert len(str(text)) > len(regeln.SCHWEIGT) + 20, \
                    f"{regel['id']}/{quelle}: SCHWEIGT ohne Begründung"


def test_die_pruefung_wuerde_ein_stilles_schweigen_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass eine Liste gleich ist."""
    erfunden = {"id": "probe", "quellen": ["onlineprinters"],
                "belegt_durch": {"onlineprinters": "SCHWEIGT — zur Gegenprobe erfunden."}}
    assert str(erfunden["belegt_durch"]["onlineprinters"]).startswith(regeln.SCHWEIGT)
    ohne = {"id": "probe", "quellen": ["onlineprinters"],
            "belegt_durch": {"onlineprinters": "Absatz X, Beispiel Y"}}
    assert not str(ohne["belegt_durch"]["onlineprinters"]).startswith(regeln.SCHWEIGT)


# ── Eine schweigende Quelle zählt für die Stufe nicht mit (#31, zweiter Zuschnitt)
#
# Bis hierher wurde das Schweigen nur *gemessen*. Jetzt hat es Folgen: Eine
# Regel trägt ihre Stufe nur mit Quellen, die zur Sache etwas sagen.

#: Fünf Regeln, deren einzige Quelle schweigt, dazu `text.anrede_komma`, deren
#: zweite Quelle (`letter_pro`) zählt nicht voll. Keine hat danach eine zählende
#: Quelle — sie führen `werkzeug`: Setzgewohnheit des Werkzeugs, kein Beleg.
#:
#: Bis zum 22.09.2026 stand hier auch `text.anschrift_ohne_leerzeilen`. Sie ist
#: mit #344 herausgefallen — nicht weil sich das Schweigen von `onlineprinters`
#: geändert hätte, sondern weil eine zweite, sprechende Quelle dazukam: siehe
#: BELEGT_STATT_WERKZEUG weiter unten.
NUR_NOCH_WERKZEUG = [
    "schreibweise.einheiten",
    "schreibweise.geldbetrag",
    "schreibweise.zahlengliederung",
    "text.anlagen_ohne_doppelpunkt",
    "text.anrede_komma",
    "text.gruss_ohne_komma",
]

#: Drei Regeln mit je einer sprechenden Quelle neben der schweigenden. Sie
#: fielen von Fehler auf Warnung — gewollt, nicht umgangen.
NUR_NOCH_EINZELN = [
    "schreibweise.abkuerzungen",
    "schreibweise.datum",
    "text.vermerke_max_3",
]

#: Anders als NUR_NOCH_EINZELN: Diese Regel ist nicht von Fehler auf Warnung
#: gefallen, sie ist von `werkzeug` auf `einzeln_belegt` gestiegen. Der Anlass ist
#: nicht #31, sondern #344 — die tragende Quelle war nie geprüft worden, sie war
#: nie eingetragen. Deshalb eine eigene Liste: `test_die_drei_...` verlangt `#31`
#: in jeder `bemerkung`, und das wäre hier die falsche Begründung.
BELEGT_STATT_WERKZEUG = ["text.anschrift_ohne_leerzeilen"]


def _regel(kennung: str) -> dict:
    return next(r for r in regeln.alle() if r["id"] == kennung)


def _traegt_ihre_stufe(regel: dict, quellen: dict, schweigend: set) -> bool:
    """Dieselbe Zählung wie `_pruefe_beleglage`, aber aus den rohen Daten und
    ohne die Schweiger — als unabhängige Probe der echten Regeldatei."""
    namen = [n for n in regeln._quellennamen(regel) if (regel["id"], n) not in schweigend]
    stufen = [quellen[n]["zaehlt"] for n in namen]
    voll = stufen.count(regeln.ZAEHLT_VOLL)
    belege = voll + stufen.count(regeln.ZAEHLT_EINZELN)
    herkunft = regel["herkunft"]
    if herkunft in regeln.MINDESTENS_VOLL:
        return voll >= regeln.MINDESTENS_VOLL[herkunft]
    if herkunft in regeln.MINDESTENS_IRGENDEIN_BELEG:
        return belege >= 1
    return True


def test_keine_stufe_ruht_auf_einer_schweigenden_quelle():
    """AC 1 an der echten Regeldatei: Wer eine Quelle abzieht, die schweigt,
    hat die Stufe noch. Gezählt wird hier aus den Rohdaten, nicht über den
    Lader — sonst prüfte sich der Lader an sich selbst."""
    schweigend = set(regeln.schweigende_quellen())
    assert schweigend, "keine schweigende Quelle — dann misst dieser Test nichts"
    quellen = regeln.quellen()
    zu_hoch = sorted(r["id"] for r in regeln.alle()
                     if not _traegt_ihre_stufe(r, quellen, schweigend))
    assert not zu_hoch, (
        "Diese Regeln tragen ihre Stufe nur mit einer Quelle, die zur Regel "
        f"schweigt: {zu_hoch}")


def test_die_zaehlung_ohne_schweiger_wuerde_eine_zu_hohe_stufe_bemerken():
    """Gegenprobe: Zwei volle Quellen, eine davon stumm, sind keine zwei."""
    quellen = {"a": {"zaehlt": regeln.ZAEHLT_VOLL}, "b": {"zaehlt": regeln.ZAEHLT_VOLL}}
    regel = {"id": "probe", "herkunft": regeln.MEHRFACH, "quellen": ["a", "b"]}
    assert _traegt_ihre_stufe(regel, quellen, set()) is True
    assert _traegt_ihre_stufe(regel, quellen, {("probe", "b")}) is False
    einzeln = {"id": "probe", "herkunft": regeln.EINZELN, "quellen": ["a"]}
    assert _traegt_ihre_stufe(einzeln, quellen, {("probe", "a")}) is False


def test_die_sechs_ohne_zaehlende_quelle_fuehren_werkzeug():
    """AC 2: Sie tragen `herkunft: werkzeug` und wirken weiter als Warnung.

    „Weiter als Warnung“ heißt hier `deckel()`, nicht nur `wirkung:` in der
    Datei: `werkzeug` steht in `DARF_FEHLER_SEIN`, und ohne Zusatz würde aus
    `gruss` und `anrede` mit der Herabstufung ein Fehler. Die Regel wäre nicht
    verstummt, sondern schärfer geworden.
    """
    falsch = {k: _regel(k)["herkunft"] for k in NUR_NOCH_WERKZEUG
              if _regel(k)["herkunft"] != regeln.WERKZEUG}
    assert not falsch, f"Nicht `werkzeug`: {falsch}"

    zu_scharf = {k: regeln.deckel(_regel(k)) for k in NUR_NOCH_WERKZEUG
                 if regeln.deckel(_regel(k)) != regeln.DECKEL_WARNUNG}
    assert not zu_scharf, (
        f"Diese Regeln dürften nach `deckel()` mehr als warnen: {zu_scharf}")

    verstummt = [k for k in NUR_NOCH_WERKZEUG if _regel(k).get("wirkung") != "warnung"]
    assert not verstummt, f"`wirkung:` nicht mehr `warnung`: {verstummt}"


def test_was_eine_quelle_woertlich_traegt_ist_keine_werkzeugpruefung():
    """#344 / ADR 0044: Eine Regel, die eine geführte Quelle in eigener Prosa
    nennt, ist kein Werkzeugurteil — auch wenn eine zweite Quelle dazu schweigt.

    Die Probe misst beides, weil nur beides zusammen die Aussage trägt: Die
    Herkunft ist `einzeln_belegt` UND der Beleg ist ein Fundstellen-Eintrag, kein
    `SCHWEIGT`. Ohne die zweite Hälfte ließe sich die Stufe durch einen leeren
    Eintrag erschleichen.
    """
    for kennung in BELEGT_STATT_WERKZEUG:
        regel = _regel(kennung)
        assert regel["herkunft"] == regeln.EINZELN, f"{kennung}: {regel['herkunft']}"
        assert "deckel" not in regel, (
            f"{kennung}: `deckel:` gilt nur für `werkzeug` — die Regeldatei bricht "
            "sonst beim Laden ab (regeln/__init__.py, `_pruefe_deckel`).")
        assert regeln.deckel(regel) == regeln.DECKEL_WARNUNG, (
            f"{kennung}: eine Quelle allein darf keinen Lauf scheitern lassen")

        belege = regel.get("belegt_durch") or {}
        sprechend = [n for n, text in belege.items() if "SCHWEIGT" not in text]
        assert sprechend, (
            f"{kennung}: kein einziger sprechender Beleg — dann ist die Stufe "
            f"nicht getragen: {sorted(belege)}")
        assert "#344" in (regel.get("bemerkung") or ""), (
            f"{kennung}: Der Aufstieg gehört in den Regeltext (`bemerkung:`), mit "
            "Verweis auf #344 — sonst steht in der Datei kein Grund dafür.")


def test_die_drei_mit_sprechender_quelle_fallen_auf_warnung():
    """AC 3: Fehler → Warnung, ausdrücklich gewollt und im Regeltext gesagt."""
    for kennung in NUR_NOCH_EINZELN:
        regel = _regel(kennung)
        assert regel["herkunft"] == regeln.EINZELN, f"{kennung}: {regel['herkunft']}"
        assert regel["wirkung"] == "warnung", f"{kennung}: wirkung {regel['wirkung']!r}"
        assert regeln.deckel(regel) == regeln.DECKEL_WARNUNG, kennung
        assert "#31" in (regel.get("bemerkung") or ""), (
            f"{kennung}: Die Herabstufung gehört in den Regeltext (`bemerkung:`), "
            "mit Verweis auf #31 — sonst fällt sie als Nebenwirkung niemandem auf.")


#: Regeln, die trotz einer schweigenden Quelle mehr als warnen dürfen — und warum.
#:
#: Bis zum 25.09.2026 galt hier ausnahmslos: Wo eine Quelle schweigt, darf die
#: Regel nur noch warnen. Das war richtig, solange jede betroffene Regel auf
#: genau dieser einen Quelle stand (#31). Mit #355 stimmt es nicht mehr: Eine
#: schweigende Quelle zählt nicht mit — sie widerlegt aber auch nichts, was
#: andere Quellen tragen.
#:
#: Wer hier etwas einträgt, sagt daneben, woraus die Stufe dann kommt.
TROTZ_SCHWEIGENS_HART = {
    # Zwei neue Gruppen tragen die 40 mm: `natusch` und `weka_sekretaria`.
    "geometrie.infoblock_mindesthoehe",
    # Dieselben zwei tragen die Heftrandgrenze wörtlich.
    "geometrie.marken_heftrand",
    # `werkzeug`: Beide sagen ausdrücklich, die Norm gebe zur Gestalt der Marken
    # nichts vor. Die Länge ist damit Setzung des Werkzeugs — und `wirkung: keine`,
    # weil sie am fertigen PDF gar nicht gemessen wird.
    "geometrie.markenlaenge",
}


def test_kein_fehler_aus_einem_schweigen_allein():
    """AC 2 und 3 zusammen, von der anderen Seite: Wo eine Quelle schweigt, darf
    die Regel nur noch warnen — es sei denn, sie steht ausdrücklich in
    `TROTZ_SCHWEIGENS_HART` und trägt ihre Stufe aus anderen Quellen."""
    zu_scharf = sorted(k for k, _ in regeln.schweigende_quellen()
                       if k not in TROTZ_SCHWEIGENS_HART
                       and regeln.deckel(_regel(k)) != regeln.DECKEL_WARNUNG)
    assert not zu_scharf, f"Darf nach `deckel()` mehr als warnen: {zu_scharf}"


def test_die_ausnahmen_stehen_nicht_auf_einer_schweigenden_quelle():
    """Gegenprobe zur Ausnahmeliste: Jede dort genannte Regel muss ihre Stufe
    ohne die schweigende Quelle tragen — sonst wäre die Liste ein Freibrief.

    Für `werkzeug` gilt das nicht: Diese Stufe beruft sich auf gar keine Quelle.
    """
    for kennung in sorted(TROTZ_SCHWEIGENS_HART):
        regel = _regel(kennung)
        if regel["herkunft"] == regeln.WERKZEUG:
            continue
        gruppen = regeln.unabhaengige_belege(regel)
        assert len(gruppen) >= 2, (
            f"{kennung}: nur {len(gruppen)} tragende Gruppe(n) — {sorted(gruppen)}. "
            "Dann darf die Regel trotz des Schweigens nicht mehr als warnen.")


def test_nicht_geprueft_ist_kein_schweigen():
    """AC 4: `schreibweise.kuerzel_vor_angabe` bleibt, wie sie ist.

    Ihre Fundstelle sagt „Nicht gesondert nachgelesen“ — das ist der dritte
    Zustand, weder Beleg noch Schweigen. Er darf nicht als Schweigen gelesen
    werden, sonst verlöre eine Regel ihre Stufe, weil niemand nachgesehen hat.
    """
    regel = _regel("schreibweise.kuerzel_vor_angabe")
    assert ("schreibweise.kuerzel_vor_angabe", "onlineprinters") not in regeln.schweigende_quellen()
    assert regel["herkunft"] == regeln.EINZELN
    assert regel["quellen"] == ["onlineprinters"]
    assert regel["wirkung"] == "warnung"
    assert regel["belegt_durch"]["onlineprinters"].startswith("Nicht gesondert nachgelesen")
    assert regeln.deckel(regel) == regeln.DECKEL_WARNUNG
    assert regeln.darf_automatisch_ersetzen("_vor_angabe") is False


def _belegt_durch(ziel: str, quelle: str, text: str, dazu: bool = False):
    """Sabotage für `_regeldatei`: die Fundstelle einer Quelle einer Regel setzen.

    `dazu=True` nimmt die Quelle zusätzlich in die Quellenliste auf — für den
    Fall, dass die Regel sie noch nicht nennt.
    """
    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] != ziel:
                continue
            if dazu and quelle not in (regel.get("quellen") or []):
                regel["quellen"] = [*(regel.get("quellen") or []), quelle]
            regel["belegt_durch"] = {**(regel.get("belegt_durch") or {}), quelle: text}
    return kippen


SCHWEIGT_ERFUNDEN = "SCHWEIGT — zur Gegenprobe erfunden, die Quelle sagt dazu nichts."
FUNDSTELLE_ERFUNDEN = "Absatz „Zonen“ der Zeichnung, zur Gegenprobe erfunden."


def _mehrfach_mit_genau_zwei_vollen():
    """(Regel, ihre beiden vollen Quellen, eine volle Quelle, die sie nicht nennt).

    Zur Laufzeit gesucht, nicht fest verdrahtet: Ein Test, der eine bestimmte
    Regel sabotiert, läuft ins Leere, sobald sie ihre Eigenschaft verliert —
    dieselbe Lehre wie bei `test_mehrfach_ohne_zwei_volle_quellen_wird_abgewiesen`.

    Verlangt wurde hier bis zum 22.09.2026 zusätzlich ein **leeres**
    `belegt_durch`. Das war zu streng und hätte sich selbst abgeschafft: Je mehr
    Paare nachgelesen werden, desto sicherer findet die Suche kein Objekt mehr —
    am 22.09. war es so weit, nachdem `massskizze_b` abgearbeitet war. Gebraucht
    wird nur, dass keine der beiden vollen Quellen schon schweigt; sonst trägt
    die Regel gar keine zwei Gruppen und die erste Probe könnte nicht laden.
    `_belegt_durch` ist additiv und überschreibt genau einen Eintrag.
    """
    quellen = regeln.quellen()
    for regel in regeln.alle():
        if regel["herkunft"] != regeln.MEHRFACH:
            continue
        namen = regel.get("quellen") or []
        volle = [n for n in namen if quellen[n]["zaehlt"] == regeln.ZAEHLT_VOLL]
        schon_still = any(
            str((regel.get("belegt_durch") or {}).get(n, "")).startswith(
                (regeln.SCHWEIGT, "Nicht gesondert")) for n in volle)
        if len(volle) != 2 or schon_still:
            continue
        fremde = [n for n, d in quellen.items()
                  if d["zaehlt"] == regeln.ZAEHLT_VOLL and n not in namen]
        if fremde:
            return regel["id"], volle, fremde[0]
    raise AssertionError(
        "Keine mehrfach belegte Regel mit genau zwei vollen Quellen und ohne "
        "`belegt_durch` — dann kann dieser Test nichts sabotieren und belegt nichts.")


def test_eine_schweigende_quelle_kostet_die_mehrfach_stufe(tmp_path):
    """AC 1, mit Gegenprobe im selben Durchgang: dieselbe Änderung an derselben
    Quelle — einmal mit Fundstelle, einmal mit `SCHWEIGT`. Nur die zweite darf
    die Stufe kosten, sonst misst der Test die Sabotage und nicht den Schalter.
    """
    ziel, volle, _ = _mehrfach_mit_genau_zwei_vollen()

    _laden(_regeldatei(tmp_path, _belegt_durch(ziel, volle[0], FUNDSTELLE_ERFUNDEN)))

    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, _belegt_durch(ziel, volle[0], SCHWEIGT_ERFUNDEN)))
    assert ziel in str(fehler.value), str(fehler.value)


def test_eine_schweigende_quelle_kostet_auch_die_einzeln_stufe(tmp_path):
    """AC 1 für `einzeln_belegt`: Trägt nur noch eine schweigende Quelle die
    Regel, ist sie „offen, nicht belegt“ — und darf nicht `einzeln_belegt` heißen.
    """
    quellen = regeln.quellen()
    kandidaten = [
        r["id"] for r in regeln.alle()
        if r["herkunft"] == regeln.EINZELN
        and [n for n in r["quellen"] if quellen[n]["zaehlt"] != regeln.ZAEHLT_NIE] == r["quellen"]
        and len(r["quellen"]) == 1
        and not str((r.get("belegt_durch") or {}).get(r["quellen"][0], "")).startswith(
            (regeln.SCHWEIGT, "Nicht gesondert"))
    ]
    assert kandidaten, (
        "Keine einzeln belegte Regel mit genau einer sprechenden Quelle — dann "
        "kann dieser Test nichts sabotieren.")
    ziel = kandidaten[0]
    quelle = _regel(ziel)["quellen"][0]

    _laden(_regeldatei(tmp_path, _belegt_durch(ziel, quelle, FUNDSTELLE_ERFUNDEN)))

    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, _belegt_durch(ziel, quelle, SCHWEIGT_ERFUNDEN)))
    assert ziel in str(fehler.value), str(fehler.value)


def test_gegenprobe_zwei_proben_verlieren_die_stufe_und_behalten_sie(tmp_path):
    """AC 8, beide Hälften in einem Test, damit keine ohne die andere grün wird.

    Probe A: Eine Regel, deren einzige zählende Quelle auf `SCHWEIGT` gesetzt
    wird, verliert ihre Stufe — hier die mehrfach belegte, von zwei vollen
    Quellen auf eine.

    Probe B: Eine mit zwei sprechenden behält sie. Dieselbe Regel bekommt eine
    dritte volle Quelle, die schweigt: Es bleiben zwei, sie lädt.

    Und Probe C hält die Grenze zum dritten Zustand: „Nicht gesondert
    nachgelesen“ ist kein Schweigen und kostet keine Stufe.
    """
    ziel, volle, fremde = _mehrfach_mit_genau_zwei_vollen()

    with pytest.raises(regeln_modul.Regelfehler):
        _laden(_regeldatei(tmp_path, _belegt_durch(ziel, volle[0], SCHWEIGT_ERFUNDEN)))

    geladen = _laden(_regeldatei(
        tmp_path, _belegt_durch(ziel, fremde, SCHWEIGT_ERFUNDEN, dazu=True)))
    regel = next(r for r in geladen["regeln"] if r["id"] == ziel)
    assert regel["herkunft"] == regeln.MEHRFACH
    assert fremde in regel["quellen"], "Die Sabotage hat die Quelle nicht eingetragen"

    _laden(_regeldatei(tmp_path, _belegt_durch(
        ziel, volle[0], "Nicht gesondert nachgelesen. Was die Quelle dazu sagt, ist offen.")))


# ── Die zweite Achse: Ebenen (ADR 0035) ─────────────────────────────────────
#
# Die Prüfungen hier halten fest, was der Eintrag zusagt. Zu jeder gehört ihr
# roter Fall: Eine Regeldatei, die alles annimmt, prüft nichts.

def test_jede_email_regel_traegt_eine_ebene():
    ohne = [r["id"] for r in regeln.alle()
            if r.get("_datei") == "email.yaml" and r.get("ebene") not in regeln.EBENEN]
    assert not ohne, (
        f"E-Mail-Regeln ohne gültige Ebene: {ohne}. Ohne Ebene sagt die Meldung "
        "nicht, wovon die Regel redet — und das ist der Grund für ADR 0035.")


def test_eine_email_regel_ohne_ebene_laesst_die_datei_abbrechen(tmp_path):
    """Gegenprobe. Ohne sie belegt der Test darüber nur, dass gerade alle eine haben."""
    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] == "email.an":
                regel.pop("ebene", None)
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, kippen), ebene_pflicht=True)
    assert "ebene=" in str(fehler.value), str(fehler.value)


def test_eine_erfundene_ebene_wird_abgewiesen(tmp_path):
    """Ein Tippfehler darf nicht als neue Ebene durchgehen."""
    def kippen(daten):
        for regel in daten["regeln"]:
            if regel["id"] == "email.an":
                regel["ebene"] = "techik"
    with pytest.raises(regeln_modul.Regelfehler) as fehler:
        _laden(_regeldatei(tmp_path, kippen))
    assert "techik" in str(fehler.value), str(fehler.value)


def test_dieselbe_id_in_zwei_regeldateien_wird_abgewiesen(tmp_path):
    """Zwei Dateien, ein Namensraum. Die Meldung muss beide Dateien nennen,
    sonst sucht jemand in der falschen."""
    quellen = yaml.safe_load(regeln_modul.QUELLDATEI.read_text(encoding="utf-8"))
    eine = yaml.safe_load(list(regeln_modul.REGELDATEIEN)[0].read_text(encoding="utf-8"))
    doppelt = eine["regeln"][0]

    (tmp_path / "q.yaml").write_text(yaml.safe_dump(quellen, allow_unicode=True),
                                     encoding="utf-8")
    for name in ("a.yaml", "b.yaml"):
        (tmp_path / name).write_text(
            yaml.safe_dump({"regeln": [doppelt]}, allow_unicode=True), encoding="utf-8")

    alt_q, alt_r = regeln_modul.QUELLDATEI, regeln_modul.REGELDATEIEN
    try:
        regeln_modul.QUELLDATEI = tmp_path / "q.yaml"
        regeln_modul.REGELDATEIEN = {tmp_path / "a.yaml": False, tmp_path / "b.yaml": False}
        regeln_modul.laden.cache_clear()
        with pytest.raises(regeln_modul.Regelfehler) as fehler:
            regeln_modul.laden()
    finally:
        regeln_modul.QUELLDATEI, regeln_modul.REGELDATEIEN = alt_q, alt_r
        regeln_modul.laden.cache_clear()
    meldung = str(fehler.value)
    assert "doppelt" in meldung and "a.yaml" in meldung and "b.yaml" in meldung, meldung


@pytest.mark.parametrize("regelname, ebene", [
    ("email.betreff", "Praxis"),
    ("email.pflichtangaben", "Recht"),
])
def test_die_meldung_einer_gedeckelten_regel_nennt_die_ebene(regelname, ebene):
    """Abnahmepunkt 1 aus dem Vorhaben: Die Meldungen nennen die Ebene.

    Geprüft am fertigen Befundtext, nicht am Wörterbuch daneben — sonst wäre
    belegt, dass der Hinweis existiert, nicht dass er ankommt.
    """
    bericht = lint.Bericht()
    bericht.fehler(1, regelname, "Etwas stimmt nicht")
    assert len(bericht.befunde) == 1
    befund = bericht.befunde[0]
    assert befund.schwere == lint.WARNUNG, "gedeckelt heißt Warnung"
    assert f"Ebene: {ebene}" in befund.meldung, befund.meldung


def test_eine_briefregel_traegt_keinen_ebenenhinweis():
    """Die Gegenrichtung: Die Briefregeln haben keine Ebene, und ihre Meldungen
    dürfen sich durch ADR 0035 nicht verändert haben."""
    bericht = lint.Bericht()
    bericht.fehler(1, "gruss", "Die Grußformel steht ohne Komma")
    assert "Ebene:" not in bericht.befunde[0].meldung, bericht.befunde[0].meldung


# ── dinbrief als Quelle (#134) ──────────────────────────────────────────────

def test_dinbrief_steht_im_register():
    quelle = regeln.quellen().get("dinbrief")
    assert quelle, "dinbrief fehlt im Quellen-Register"
    assert quelle["art"] == "implementierung"
    assert quelle["gruppe"] == "dinbrief", "eigene Gruppe — es ist ein anderes Werk als KOMA-Script"
    assert quelle["zaehlt"] == "einzeln"
    assert quelle.get("abgerufen"), "ohne Abrufdatum altert der Eintrag still"


def test_es_belegt_form_a_und_sagt_womit():
    regel = [r for r in regeln.alle() if r["id"] == "geometrie.form_a.masse"][0]
    assert "dinbrief" in regel["quellen"]
    fundstelle = regel.get("belegt_durch", {}).get("dinbrief", "")
    assert "addresshigh" in fundstelle, "die Fundstelle nennt den Befehl nicht"
    assert "87" in fundstelle and "192" in fundstelle, fundstelle


def test_form_a_steigt_nicht_durch_dinbrief():
    """Abnahmepunkt 3 aus #134, wörtlich: „Keine Regel steigt allein deshalb auf
    mehrfach_bestaetigt, weil eine Quelle dazugekommen ist."

    Der Grund steht in `quellen.yaml`: dinbrief beruft sich auf DIN 676, wie
    `koma_script`. Zwei Umsetzungen derselben Grundlage sind keine zwei
    Aussagen über DIN 5008 — und falzmarke misst DIN 5008.

    Bis zum 24.09.2026 stand hier `herkunft == EINZELN`. Die Regel ist mit #180
    gestiegen, aber **nicht** wegen dinbrief: Die Stufe trägt, wer `zaehlt: voll`
    ist, und das sind `massskizze_a` und `federwerk`. Genau das misst dieser
    Test jetzt — die Aussage von #134 gilt unverändert, sie hing nur nie an der
    Stufe der Regel, sondern an der Einstufung der Quelle.
    """
    quellen = regeln.quellen()
    regel = [r for r in regeln.alle() if r["id"] == "geometrie.form_a.masse"][0]
    assert "dinbrief" in regel["quellen"]
    assert quellen["dinbrief"]["zaehlt"] == regeln.ZAEHLT_EINZELN
    assert quellen["koma_script"]["zaehlt"] == regeln.ZAEHLT_EINZELN
    tragend = {n for n in regel["quellen"] if quellen[n]["zaehlt"] == regeln.ZAEHLT_VOLL}
    assert "dinbrief" not in tragend and "koma_script" not in tragend, tragend


def test_die_begruendung_nennt_din_676():
    """Ohne sie wäre `zaehlt: einzeln` eine Behauptung ohne Grund — und der
    nächste, der die Stufe anheben will, wüsste nicht, was zu klären ist."""
    bemerkung = regeln.quellen()["dinbrief"]["bemerkung"]
    assert "DIN 676" in bemerkung
    assert "DIN 5008" in bemerkung, "der Unterschied muss benannt sein"


def test_und_dass_die_anderen_latex_vorlagen_geprueft_wurden():
    """Eine Absage ohne Nennung dessen, was geprüft wurde, lädt zur zweiten
    Suche ein. Die drei anderen bauen auf scrlttr2 — das steht dort."""
    bemerkung = regeln.quellen()["dinbrief"]["bemerkung"]
    assert "scrlttr2" in bemerkung


# ── federwerk als Quelle für Form A (#18) ───────────────────────────────────

def test_federwerk_steht_im_register():
    quelle = regeln.quellen().get("federwerk")
    assert quelle, "federwerk fehlt im Quellen-Register"
    assert quelle["art"] == "sekundaerquelle"
    assert quelle["gruppe"] == "federwerk", "eigene Belegkette, nicht die des Onlineprinters-Artikels"
    assert quelle["zaehlt"] == "voll"
    assert quelle.get("abgerufen"), "ohne Abrufdatum altert der Eintrag still"


def test_es_belegt_form_a_und_nennt_alle_vier_masse():
    """Eine Quelle, die nur einen Teil der Regel hergibt, dürfte nicht voll
    zählen — das ist der Befund von #31. Diese nennt alle vier Maße."""
    regel = [r for r in regeln.alle() if r["id"] == "geometrie.form_a.masse"][0]
    assert "federwerk" in regel["quellen"]
    fundstelle = regel.get("belegt_durch", {}).get("federwerk", "")
    for mass in ("27", "87", "148,5", "192"):
        assert mass in fundstelle, f"{mass} mm fehlt in der Fundstelle: {fundstelle}"


def test_der_unterschied_zu_din_676_ist_benannt():
    """Der Grund, warum diese Quelle mehr trägt als `koma_script` und
    `dinbrief`: Sie schreibt die Maße der DIN 5008 zu, nicht der DIN 676.
    Ohne diesen Satz wäre `zaehlt: voll` eine Behauptung ohne Begründung."""
    bemerkung = regeln.quellen()["federwerk"]["bemerkung"]
    assert "DIN 676" in bemerkung and "DIN 5008" in bemerkung
    assert "2011" in bemerkung, "die Ausgabe, auf die sie sich beruft, gehört genannt"


def test_form_a_steht_auf_zwei_gruppen_und_wirkt_als_fehler():
    """Die Entscheidung aus #180, seit dem 24.09.2026 (ADR 0046).

    Zwei voll zählende Quellen aus verschiedenen Gruppen — `massskizze_a`
    (Zeichnung, Bezugsnorm 2020) und `federwerk` (Fließtext, schreibt die Maße
    der DIN 5008 zu). Damit trägt die Regel `mehrfach_bestaetigt`.

    Der Test hält beide Hälften fest: dass die Beleglage reicht, und dass die
    Stufe ihr folgt. Fällt die erste, ist eine Quelle verschwunden und die Stufe
    steht in der Luft; fällt die zweite, hat jemand die Entscheidung
    zurückgedreht, ohne den ADR anzufassen.
    """
    quellen = regeln.quellen()
    regel = [r for r in regeln.alle() if r["id"] == "geometrie.form_a.masse"][0]
    volle = [n for n in regel["quellen"] if quellen[n].get("zaehlt") == "voll"]
    assert sorted(volle) == ["federwerk", "massskizze_a"], volle
    assert len({quellen[n]["gruppe"] for n in volle}) == 2, "zwei Quellen, aber eine Gruppe"
    assert regel["herkunft"] == regeln.MEHRFACH
    assert regel["wirkung"] == "fehler"
    assert regeln.deckel(regel) == regeln.DECKEL_FEHLER


def test_form_a_steht_auf_mehr_gruppen_als_jede_form_b_regel():
    """Warum die Anhebung nicht am Vergleich mit Form B scheitert.

    #180 führte als Argument, Form B stehe „auf zwei Zeichnungen" und wirke als
    Fehler. Nachgemessen am 24.09.2026 ist es **eine**: `massskizze_b` und
    `onlineprinters` tragen dieselbe `gruppe:`, weil sie dieselbe Zeichnung sind
    (Befund vom 27.08.2026). Die fünf Form-B-Regeln stehen deshalb in
    `stufe_traegt_nicht()`; Form A steht dort nicht.

    Der Test misst den Kontrast, nicht die Meinung darüber. Verschwindet er —
    etwa weil jemand für Form B eine echte zweite Quelle nachträgt —, gehört die
    Begründung in ADR 0046 nachgezogen, und das ist eine gute Nachricht.
    """
    form_a = [r for r in regeln.alle() if r["id"] == "geometrie.form_a.masse"][0]
    form_b = [r for r in regeln.alle() if r["id"].startswith("geometrie.form_b.")]
    assert form_b, "keine Form-B-Regeln mehr — dann misst dieser Test nichts"
    for regel in form_b:
        assert len(regeln.unabhaengige_belege(regel)) == 1, regel["id"]
        assert regel["id"] in regeln.stufe_traegt_nicht(), regel["id"]
    assert len(regeln.unabhaengige_belege(form_a)) == 2
    assert form_a["id"] not in regeln.stufe_traegt_nicht()


# ── Was quellenlos wurde, beruft sich in seiner Meldung nicht mehr auf die Norm (#328)
#
# #31 hat `text.anrede_komma` und `text.gruss_ohne_komma` die letzte zählende
# Quelle genommen; sie führen `herkunft: werkzeug`. Die Korrekturhinweise in
# `lint.py` sagten weiter „nach DIN endet die Anrede mit einem Komma“ — dieselbe
# Quellenbehauptung, nur eine Ebene tiefer. Gemessen wird am fertigen Befund, den
# `cli.linte` für ein echtes Frontmatter liefert, nicht am Quelltext von
# `lint.py`: Der Hinweis steht dort an vier Stellen (Brief und Mail), und eine
# Suche im Quelltext trifft auch die eigene Prosa.
#
# `text.anschrift_ohne_leerzeilen` war hier bis zum 22.09.2026 der dritte Fall.
# Mit #344 hat sie eine sprechende Quelle bekommen und nennt sie wieder — sie
# steht jetzt in Probe A″ des Gegenprobe-Tests, auf der anderen Seite derselben
# Messung.

import re

from falzmarke import cli as falzmarke_cli

from conftest import SKILL

_PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

#: Was eine Norm-Berufung ausmacht: das Wort selbst, oder das Gütesiegel, das
#: CLAUDE.md ohnehin verbietet. „Normabgleich“ zählt nicht — ehrlich ist gerade
#: der Hinweis, dass er aussteht.
_NORMBERUFUNG = re.compile(r"\b(?:DIN|Norm(?:en)?)\b|normgerecht|normkonform", re.IGNORECASE)

_BRIEFKOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""

_MAILKOPF = """typ: email
profil: example
an: erika.muster@example.de
betreff: Ein Betreff
anrede: Sehr geehrte Frau Muster,
"""

#: Die Gegenrichtung zu `_UMGEWIDMET`: derselbe Aufbau, aber eine Regel MIT
#: sprechender Quelle. Sie stand bis #344 in der Liste darunter (siehe Probe A″).
_BELEGT_EMPFAENGER = (
    "brief-empfaenger",
    _BRIEFKOPF.replace("[Muster GmbH, Musterstraße 1, 12345 Musterstadt]",
                       '[Muster GmbH, "", 12345 Musterstadt]'),
    "empfaenger", "text.anschrift_ohne_leerzeilen", "Leerzeile",
)

#: (Fall, Frontmatter, Regelname des Linters, Regel-ID in der Regeldatei, Stichwort
#: der Meldung). Das Stichwort trennt den gesuchten Befund von anderen unter
#: demselben Regelnamen (`empfaenger` meldet auch Zeilenzahl und Auslandsanschrift).
_UMGEWIDMET = [
    ("brief-anrede",
     _BRIEFKOPF.replace("Herren,", "Herren"),
     "anrede", "text.anrede_komma", "Komma"),
    ("brief-gruss",
     _BRIEFKOPF + "gruss: Mit freundlichen Grüßen,\n",
     "gruss", "text.gruss_ohne_komma", "Komma"),
    ("mail-anrede",
     _MAILKOPF.replace("Muster,", "Muster"),
     "anrede", "text.anrede_komma", "Komma"),
    ("mail-gruss",
     _MAILKOPF + "gruss: Viele Grüße,\n",
     "gruss", "text.gruss_ohne_komma", "Komma"),
]


def _steht_an_der_richtigen_stelle(regelname: str, kennung: str) -> None:
    """Die Regel muss wirklich umgewidmet sein — sonst misst der Fall etwas anderes."""
    regel = regeln.fuer_lint(regelname)
    assert regel["id"] == kennung and regel["herkunft"] == regeln.WERKZEUG, (
        f"{kennung} trägt nicht mehr `werkzeug` — dann steht der Test an der "
        f"falschen Stelle: {regel['id']} / {regel['herkunft']}")


def _befund(tmp_path, kopf: str, regelname: str, stichwort: str):
    """Der eine Befund, den das Frontmatter auslöst — samt Beleg, dass es ihn gibt."""
    pfad = tmp_path / "probe.md"
    pfad.write_text(f"---\n{kopf}---\nText des Briefes.\n", encoding="utf-8")
    bericht = falzmarke_cli.linte(pfad, profil_verzeichnis=_PROFILE)
    treffer = [b for b in bericht.befunde
               if b.regel == regelname and stichwort in b.meldung]
    assert len(treffer) == 1, (
        f"kein einzelner Befund `{regelname}` mit „{stichwort}“ — dann misst dieser "
        f"Test nichts:\n{bericht.als_text('probe.md')}")
    return treffer[0]


#: Die Fälle, deren Hinweis die Norm heute beim Namen nennt. Der Hinweis zu `gruss`
#: („die Grußformel steht ohne Komma“) tut es nicht — er behauptet nackt, ohne
#: Absender. Für ihn misst der Ton-Test darunter und Probe B der Gegenprobe; ein
#: Norm-Test wäre dort von Anfang an grün und prüfte nichts.
_NENNT_DIE_NORM = [f for f in _UMGEWIDMET if f[2] != "gruss"]


@pytest.mark.parametrize("fall, kopf, regelname, kennung, stichwort", _NENNT_DIE_NORM,
                         ids=[f[0] for f in _NENNT_DIE_NORM])
def test_die_meldung_einer_quellenlosen_regel_beruft_sich_nicht_auf_die_norm(
        tmp_path, fall, kopf, regelname, kennung, stichwort):
    """AC 1 und AC 4: Brief **und** Mail. Jeder Fall ist für sich rot, solange
    seine Fundstelle in `lint.py` die Norm nennt — eine allein ließe die andere
    Behauptung stehen."""
    _steht_an_der_richtigen_stelle(regelname, kennung)
    befund = _befund(tmp_path, kopf, regelname, stichwort)
    gesagt = f"{befund.meldung} | {befund.korrektur}"
    assert not _NORMBERUFUNG.search(gesagt), (
        f"{fall}: die Regel hat keine zählende Quelle, die Meldung beruft sich "
        f"trotzdem auf die Norm: {gesagt}")


@pytest.mark.parametrize("fall, kopf, regelname, kennung, stichwort", _UMGEWIDMET,
                         ids=[f[0] for f in _UMGEWIDMET])
def test_der_hinweis_einer_quellenlosen_regel_sagt_wessen_urteil_es_ist(
        tmp_path, fall, kopf, regelname, kennung, stichwort):
    """AC 1, die andere Hälfte: Die Norm nur zu streichen ließe einen Befehl ohne
    Absender stehen. Vorbild ist #296: „das hält das Werkzeug für richtig“ — der
    Hinweis sagt, dass es das Werkzeug ist, das hier urteilt."""
    _steht_an_der_richtigen_stelle(regelname, kennung)
    befund = _befund(tmp_path, kopf, regelname, stichwort)
    assert "Werkzeug" in befund.korrektur, (
        f"{fall}: der Hinweis nennt das Werkzeug nicht als Urheber: {befund.korrektur!r}")


#: Die dritte und vierte Fundstelle derselben Behauptung, nicht in der Aufgabe
#: genannt: `cli.baue_daten` bricht beim Setzen hart ab und sagte „die Anrede endet
#: nach DIN mit einem Komma“ (cli.py:333) und „die Grußformel steht ohne Komma“
#: (cli.py:337). Es ist dieselbe Regel, nur der Weg zum Nutzer ist ein anderer —
#: und AC 4 begründet sich genau damit: Eine Fundstelle allein ließe die andere
#: Behauptung stehen. Gemessen wird `baue_daten` selbst, nicht `rendere`: Bis zur
#: Anrede braucht der Abbruch kein Typst, und ein Test über `rendere` wäre in einer
#: Umgebung ohne das Paket aus dem falschen Grund rot.
_BEIM_SETZEN = [
    ("setzen-anrede", _BRIEFKOPF.replace("Herren,", "Herren"), "text.anrede_komma"),
    ("setzen-gruss", _BRIEFKOPF + "gruss: Mit freundlichen Grüßen,\n", "text.gruss_ohne_komma"),
]


@pytest.mark.parametrize("fall, kopf, kennung", _BEIM_SETZEN, ids=[f[0] for f in _BEIM_SETZEN])
def test_auch_der_abbruch_beim_setzen_beruft_sich_nicht_auf_die_norm(tmp_path, fall, kopf, kennung):
    pfad = tmp_path / "probe.md"
    pfad.write_text(f"---\n{kopf}---\nText des Briefes.\n", encoding="utf-8")
    kopf_daten, _, _ = falzmarke_cli.lies_brief(pfad)
    profil, profil_pfad = falzmarke_cli.lade_profil(kopf_daten["profil"], _PROFILE, pfad)
    arbeit = tmp_path / "arbeit"
    falzmarke_cli.baue_arbeitsverzeichnis(arbeit)

    with pytest.raises(falzmarke_cli.Eingabefehler) as fehler:
        falzmarke_cli.baue_daten(kopf_daten, profil, profil_pfad, arbeit, pfad)
    meldung = str(fehler.value)

    assert "Komma" in meldung, (
        f"{fall}: der Abbruch kommt nicht von der Komma-Prüfung — dann misst der Test "
        f"etwas anderes: {meldung!r}")
    assert next(r for r in regeln.alle() if r["id"] == kennung)["herkunft"] == regeln.WERKZEUG
    assert not _NORMBERUFUNG.search(meldung), (
        f"{fall}: die Regel hat keine zählende Quelle, der Abbruch beruft sich "
        f"trotzdem auf die Norm: {meldung!r}")
    assert "Werkzeug" in meldung, f"{fall}: der Abbruch nennt das Werkzeug nicht: {meldung!r}"


def test_gegenprobe_die_regel_mit_quelle_nennt_sie_die_umgewidmete_nicht_mehr(tmp_path):
    """AC 5 und AC 2 in einem Durchgang — zwei Proben, die ein verschiedenes
    Ergebnis liefern müssen, sonst ist offen, ob nur pauschal ersetzt wurde.

    Probe A: `vermerke` (`text.vermerke_max_3`) blieb `einzeln_belegt` und nennt
    seine Quelle weiter in der Meldung; sie wird aus der Regeldatei gelesen, nicht
    fest verdrahtet.
    Probe A′: `infoblock.telefon` (`schreibweise.telefon`) behielt ihre Quelle und
    damit ihren Ton — „Schreibweise der Norm“ bleibt stehen (AC 2). Ohne diese
    Probe genügte es, jedes „Norm“ aus `lint.py` zu tilgen.
    Probe A″: `empfaenger` (`text.anschrift_ohne_leerzeilen`) hat mit #344 den Weg
    zurück gemacht — von `werkzeug` auf `einzeln_belegt`. Sie ist die einzige
    Probe, die rot wird, wenn nur `lint.py` zurückgedreht wird und die Regeldatei
    stehen bleibt; `test_was_eine_quelle_woertlich_traegt_...` deckt den
    umgekehrten Fall. Zwei Sabotagen, zwei verschiedene Melder.
    Probe B: die vier umgewidmeten Fälle nennen keine Quelle und tragen den Ton des
    Werkzeugs.

    Vorab die Probe des Messmittels: Das Muster für „beruft sich auf die Norm“
    muss die beiden alten Hinweise treffen und den neuen Ton in Ruhe lassen. Ein
    erster Entwurf (`Normen?`) traf „die Norm lässt …“ nicht, und der Fall
    `brief-empfaenger` blieb zu Unrecht grün. Beide Wortlaute bleiben als Probe
    stehen, auch der zur Anschrift: Geprüft wird hier das Muster, nicht `lint.py`.
    """
    for alt in ("nach DIN endet die Anrede mit einem Komma",
                "die Norm lässt im Anschriftfeld keine Leerzeilen zu"):
        assert _NORMBERUFUNG.search(alt), f"das Muster erkennt die alte Berufung nicht: {alt!r}"
    for neu in ("das Werkzeug hält ein Komma nach der Anrede für richtig",
                "bis zum Normabgleich eine Setzgewohnheit des Werkzeugs",
                "Leerzeilen im Anschriftfeld hält das Werkzeug für falsch"):
        assert not _NORMBERUFUNG.search(neu), f"das Muster schlägt am neuen Ton an: {neu!r}"

    # Probe A
    vermerke = regeln.fuer_lint("vermerke")
    assert vermerke["herkunft"] == regeln.EINZELN, (
        "`text.vermerke_max_3` ist nicht mehr einzeln belegt — Probe A misst nichts mehr")
    # Der erste SPRECHENDE Titel, nicht `quellen[0]` (#350): dort steht hier die
    # Maßzeichnung, und die schweigt zur Zeilenzahl. Bis zum 23.09.2026 nannte
    # die Meldung sie trotzdem, und dieser Test hielt genau das fest.
    titel = _erster_sprechender_titel(vermerke)
    geschwiegen = regeln.quellen()[vermerke["quellen"][0]]["titel"]
    assert titel != geschwiegen, (
        "`quellen[0]` spricht jetzt selbst — Probe A misst den Unterschied nicht mehr")
    zu_viele = _BRIEFKOPF + "vermerke: [Einschreiben, Persönlich, Eilt, Vertraulich]\n"
    mit_quelle = _befund(tmp_path, zu_viele, "vermerke", "Zeilen")
    assert "einzeln belegt" in mit_quelle.meldung and titel in mit_quelle.meldung, (
        f"die Regel mit Quelle nennt sie nicht mehr: {mit_quelle.meldung!r}")
    assert geschwiegen not in mit_quelle.meldung, (
        f"die Meldung nennt die schweigende Quelle als Beleg: {mit_quelle.meldung!r}")

    # Probe A′
    assert regeln.fuer_lint("infoblock.telefon") is None, (
        "`infoblock.telefon` ist jetzt einer Regel zugeordnet — Probe A′ lesen")
    telefon = next(r for r in regeln.alle() if r["id"] == "schreibweise.telefon")
    assert telefon["herkunft"] == regeln.EINZELN and telefon["quellen"], (
        "`schreibweise.telefon` hat ihre Quelle verloren — Probe A′ misst nichts mehr")
    kopf = _BRIEFKOPF + 'infoblock:\n  telefon: "(0941) 620/9800"\n'
    mit_ton = _befund(tmp_path, kopf, "infoblock.telefon", "Vorwahl")
    assert "Norm" in mit_ton.meldung and "Norm" in mit_ton.korrektur, (
        f"die Regel mit Quelle hat ihren Ton verloren: {mit_ton.meldung!r} | {mit_ton.korrektur!r}")

    # Probe A″
    fall, kopf_leerzeile, regelname, kennung, stichwort = _BELEGT_EMPFAENGER
    anschrift = _regel(kennung)
    assert anschrift["herkunft"] == regeln.EINZELN, (
        f"`{kennung}` ist nicht mehr einzeln belegt — Probe A″ misst nichts mehr")
    wikipedia = regeln.quellen()[anschrift["quellen"][0]]["titel"]
    belegt = _befund(tmp_path, kopf_leerzeile, regelname, stichwort)
    assert "einzeln belegt" in belegt.meldung and wikipedia in belegt.meldung, (
        f"{fall}: die Regel mit Quelle nennt sie nicht: {belegt.meldung!r}")
    assert "Werkzeug" not in belegt.korrektur, (
        f"{fall}: der Hinweis spricht weiter im Werkzeug-Ton, obwohl die Regel "
        f"seit #344 eine Quelle hat: {belegt.korrektur!r}")

    # Probe B
    umgestellt = []
    for fall, kopf, regelname, _, stichwort in _UMGEWIDMET:
        befund = _befund(tmp_path, kopf, regelname, stichwort)
        nennt_quelle = "Quelle:" in befund.meldung or "einzeln belegt" in befund.meldung
        hat_ton = "Werkzeug" in befund.korrektur
        if nennt_quelle or _NORMBERUFUNG.search(befund.korrektur) or not hat_ton:
            umgestellt.append(fall)
    assert not umgestellt, (
        f"Diese Fälle sind nicht umgestellt (Quelle genannt, Norm berufen oder kein "
        f"Werkzeug-Ton): {umgestellt}")


# ── #350: Die Meldung nennt keine Quelle, die zur Regel schweigt ────────────
#
# `quellenhinweis()` baute den Zusatz bis zum 23.09.2026 aus `quellen[0]` und
# las `belegt_durch` dabei nie. Bei `text.vermerke_max_3` stand dort die
# Maßzeichnung, die in der Regeldatei ausdrücklich `SCHWEIGT` — die Meldung
# nannte als Beleg, was keiner ist. Die Stufe war davon nie betroffen; falsch
# war nur, was der Nutzer las.
#
# Die Proben unten rechnen die Lage aus den ROHEN Daten nach, nicht über
# `regeln._schweigt`. Ein Sollwert, der sich beim Prüfling bedient, prüft nichts.

def _schweigt_laut_datei(regel: dict, quelle: str) -> bool:
    fundstelle = (regel.get("belegt_durch") or {}).get(quelle)
    return str(fundstelle or "").lstrip().startswith("SCHWEIGT")


def _erster_sprechender_titel(regel: dict) -> str:
    for name in regel["quellen"]:
        if not _schweigt_laut_datei(regel, name):
            return regeln.quellen()[name]["titel"]
    raise AssertionError(f"{regel['id']}: keine einzige sprechende Quelle")


def _mit_verstummter_quelle(lintname: str, *verstummt: str) -> dict:
    """Die echte Regel, an genau den genannten Quellen sabotiert.

    Über `fuer_lint` und nicht über `_regeldatei()`/`_laden()`: Die leeren nur
    `laden.cache_clear()`, nicht den `lru_cache` von `_nach_lint()`, über den
    `quellenhinweis()` geht. Eine Sabotage auf jenem Weg käme bei der Meldung
    nie an — die Probe könnte dann gar nicht rot werden.
    """
    kaputt = copy.deepcopy(regeln.fuer_lint(lintname))
    belege = kaputt.setdefault("belegt_durch", {})
    for quelle in verstummt:
        assert quelle in kaputt["quellen"], (
            f"{kaputt['id']}: {quelle!r} steht gar nicht unter `quellen` — "
            "die Sabotage liefe ins Leere")
        belege[quelle] = "SCHWEIGT — Sabotage dieses Tests, kein Befund."
    return kaputt


def test_die_meldung_ueberspringt_schweigende_quellen():
    """AC 4: zwei Proben, verschiedenes Ergebnis — sonst bleibt offen, ob der
    Fix überhaupt greift.

    Probe A: `schreibweise.datum` — `quellen[0]` spricht, die Meldung nennt sie,
    nichts ändert sich. Probe B: `text.vermerke_max_3` — `quellen[0]` schweigt,
    die Meldung überspringt sie und nennt die erste sprechende.

    Beiden voran der Ankercheck auf die Lage, die sie messen. Ohne ihn misst
    der Test stillschweigend nichts mehr, sobald jemand die Reihenfolge unter
    `quellen:` ändert — und die zu ändern ist seit #350 erlaubt.
    """
    # Probe A — unverändert
    datum = regeln.fuer_lint("datum")
    erste_a = datum["quellen"][0]
    assert not _schweigt_laut_datei(datum, erste_a), (
        f"`schreibweise.datum`: {erste_a!r} schweigt jetzt auch — Probe A misst "
        "nicht mehr den unveränderten Fall")
    assert regeln.quellen()[erste_a]["titel"] in regeln.quellenhinweis("datum")

    # Probe B — ändert sich
    vermerke = regeln.fuer_lint("vermerke")
    erste_b = vermerke["quellen"][0]
    assert _schweigt_laut_datei(vermerke, erste_b), (
        f"`text.vermerke_max_3`: {erste_b!r} schweigt nicht mehr — Probe B hat "
        "keinen Fall mehr, an dem sich etwas ändern könnte")
    hinweis = regeln.quellenhinweis("vermerke")
    assert regeln.quellen()[erste_b]["titel"] not in hinweis, (
        f"die Meldung nennt die schweigende Quelle als Beleg: {hinweis!r}")
    assert _erster_sprechender_titel(vermerke) in hinweis, (
        f"die Meldung nennt die erste sprechende Quelle nicht: {hinweis!r}")


def test_gegenprobe_verstummt_die_tragende_quelle_wandert_die_meldung_weiter(monkeypatch):
    """AC 5, Sabotage an genau einer Stelle, mit vorher benanntem Melder.

    `belegt_durch.wikipedia` von `text.vermerke_max_3` wird auf `SCHWEIGT`
    gesetzt. Dann bleibt unter `quellen:` nur `letter_pro` übrig — die einzige,
    zu der niemand `SCHWEIGT` notiert hat —, und die Meldung muss **sie**
    nennen. Erwartet wird also nicht „irgendetwas ändert sich", sondern ein
    namentlicher Wert.

    `letter_pro` zählt `einzeln` und trägt die Beleglage damit weiter; die
    Regeldatei bräche bei dieser Sabotage nicht schon beim Laden ab, der
    Unterschied entsteht wirklich in `quellenhinweis()`.
    """
    vermerke = regeln.fuer_lint("vermerke")
    vorher = regeln.quellenhinweis("vermerke")
    assert regeln.quellen()["wikipedia"]["titel"] in vorher, (
        f"Ankerwert veraltet: die Meldung trägt Wikipedia gar nicht: {vorher!r}")
    assert regeln.quellen()["letter_pro"]["zaehlt"] != regeln.ZAEHLT_NIE, (
        "`letter_pro` zählt nicht mehr — die Sabotage nähme der Regel ihre Stufe "
        "und mäße etwas anderes als die Meldung")

    kaputt = _mit_verstummter_quelle("vermerke", "wikipedia")
    monkeypatch.setattr(regeln, "fuer_lint",
                        lambda name: kaputt if name == "vermerke" else None)
    nachher = regeln.quellenhinweis("vermerke")
    assert nachher == (f"Quelle: sekundär, einzeln belegt — "
                       f"{regeln.quellen()['letter_pro']['titel']}"), nachher
    assert nachher != vorher, "die Sabotage ändert nichts — die Prüfung kann nicht rot werden"
    assert vermerke["belegt_durch"]["wikipedia"].startswith("Nennt die Zahl"), (
        "die Sabotage hat den echten Bestand angefasst")


def test_schweigen_alle_quellen_nennt_die_meldung_keine(monkeypatch):
    """AC 2: kein Rückfall auf `quellen[0]`.

    Eine Regel, zu der jede genannte Quelle schweigt, dürfte gar nicht
    `einzeln_belegt` heißen — `test_einzeln_belegt_braucht_wenigstens_einen_beleg`
    weist sie beim Laden ab. Die Meldung verlässt sich darauf nicht: Sie nennt
    dann keine, statt die erstbeste zu nehmen.
    """
    kaputt = _mit_verstummter_quelle("vermerke", *regeln.fuer_lint("vermerke")["quellen"])
    monkeypatch.setattr(regeln, "fuer_lint",
                        lambda name: kaputt if name == "vermerke" else None)
    assert regeln.quellenhinweis("vermerke") == "", (
        "die Meldung nennt eine Quelle, obwohl jede von ihnen schweigt")


# ── Die Nachmessung am PDF kennt den Katalog nicht (#355) ──────────────────
#
# `geometrie.py` lädt den Regelkatalog nicht und leitet aus keiner Stufe eine
# Wirkung ab: Jede Abweichung, die es findet, ist ein Fehler. Solange das so
# ist, muss jede dort gemessene Regel eine Stufe tragen, die einen Fehler
# überhaupt zulässt — sonst behauptet docs/recht.md eine Wirkung, die es nicht
# gibt. Bis zum 25.09.2026 war genau das der Fall (#355).


def _geometrie_unter_ihrer_wirkung(alle: list[dict]) -> list[str]:
    """Geometrie-Regeln, die nach `deckel()` keinen Fehler tragen dürften."""
    return sorted(r["id"] for r in alle
                  if r["id"].startswith("geometrie.")
                  and regeln.deckel(r) != regeln.DECKEL_FEHLER)


def test_jede_geometrie_regel_darf_fehler_sein():
    """Der Wächter aus #355. Fällt eine Geometrie-Regel auf `einzeln_belegt`,
    wirkt sie am PDF weiter als Fehler — und die Tabelle in docs/recht.md
    stimmt wieder nicht. Dann ist zu entscheiden, nicht weiterzulaufen.
    """
    geometrie = [r for r in regeln.alle() if r["id"].startswith("geometrie.")]
    assert len(geometrie) >= 10, f"nur {len(geometrie)} Geometrie-Regeln — misst dieser Test noch?"
    zu_schwach = _geometrie_unter_ihrer_wirkung(regeln.alle())
    assert not zu_schwach, (
        f"Diese Regeln dürften nur warnen, wirken am PDF aber als Fehler: {zu_schwach}.\n"
        "Entweder sie steigen (zwei Quellen aus zwei Gruppen), oder sie werden als "
        "Werkzeugprüfung geführt, oder die Nachmessung lernt die Stufe zu lesen — "
        "siehe #355 und ADR 0047.")


def test_die_pruefung_wuerde_eine_zurueckgefallene_geometrie_regel_bemerken():
    """Gegenprobe: eine Regel auf `einzeln_belegt` zurückkippen — die Prüfung
    muss genau sie nennen."""
    ziel = "geometrie.infoblock_mindesthoehe"
    gekippt = [dict(r, herkunft=regeln.EINZELN, wirkung="warnung") if r["id"] == ziel else r
               for r in regeln.alle()]
    assert _geometrie_unter_ihrer_wirkung(gekippt) == [ziel]


def test_die_nachmessung_laedt_den_regelkatalog_nicht():
    """Die Begründung oben hängt daran, und docs/recht.md sagt es so.

    Geprüft am Syntaxbaum, nicht am Text: Ein Kommentar, der den Katalog nur
    erwähnt, ist kein Import — und ein Import in einem Docstring wäre keiner.
    """
    import ast

    from conftest import REPO

    baum = ast.parse((REPO / "skill" / "falzmarke" / "geometrie.py").read_text(encoding="utf-8"))
    geholt = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            geholt.update(a.name for a in knoten.names)
        elif isinstance(knoten, ast.ImportFrom):
            geholt.add(knoten.module or "")
            geholt.update(f"{knoten.module or ''}.{a.name}" for a in knoten.names)
    assert geholt, "keine Importe gefunden — dann liest dieser Test die falsche Datei"
    katalog = sorted(n for n in geholt if "regeln" in n)
    assert not katalog, (
        f"geometrie.py holt jetzt {katalog}. Das ist erlaubt — dann gehört aber der "
        "Abschnitt „Was daraus folgt“ in docs/recht.md neu geschrieben: Er begründet "
        "damit, dass die Nachmessung den Katalog NICHT kennt (#355, ADR 0047).")
