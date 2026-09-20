"""Leitwort und Schlusspunkt im Betreff hängen nicht an der Längenregel (#296).

Bis dahin meldeten fünf Befunde unter dem Regelnamen `betreff` und damit über
den Katalogeintrag `werkzeug.betreff_laenge`, dessen Titel von der Betrefflänge
redet: Leitwort und Schlusspunkt im Brief, dieselben beiden in der E-Mail und
die Länge im Brief. Eine Herabstufung der Längenregel hätte Leitwort und
Schlusspunkt stillschweigend mitgezogen, in beiden Dokumentarten.

Entschieden ist Option 1: eigene Einträge mit `herkunft: werkzeug`, getrennt
für Brief und E-Mail. Wie die neuen Regelnamen heißen, legt die Entscheidung
nicht fest — diese Tests fragen deshalb den Befund selbst, unter welchem Namen
er meldet, und prüfen dann, was hinter dem Namen im Katalog steht. Ein Name,
den der Test vorgäbe, prüfte die Namenswahl statt der Sache.

Nicht festgelegt ist hier die Schärfe der beiden **E-Mail**-Regeln. Der
Entscheidungstext sagt „Wirkung bleibt, wie sie heute ist" und im selben Satz
„Warnung in der Mail über Ebene praxis"; gemessen ist die Mail-Wirkung heute
ein Fehler. Beides zugleich stimmt nicht; der Umsetzer wählt, und beide Wege
(`ebene: praxis` oder `ebene: werkzeug`) bestehen diese Tests.
"""

from __future__ import annotations

import copy

import pytest

from falzmarke import lint, regeln
from falzmarke import cli as falzmarke
from conftest import SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

BRIEF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: "{betreff}"
anrede: Sehr geehrte Damen und Herren,
"""

MAIL = """typ: email
profil: example
an: erika.muster@example.de
betreff: "{betreff}"
anrede: Sehr geehrte Frau Muster,
"""

VORLAGEN = {"brief": BRIEF, "mail": MAIL}

#: Ein Betreff, der alle drei Regeln zugleich verletzt: Leitwort, Schlusspunkt
#: und Länge (200 Zeichen — über 150 im Brief und über 78 in der Mail).
ALLES_FALSCH = "Betreff: " + "A" * 200 + "."

ROLLEN = ("leitwort", "schlusspunkt")
#: Woran die Rolle in der Meldung zu erkennen ist. Die Meldungen stehen seit
#: v0.1 im Linter; ein umformulierter Text soll hier auffallen, nicht
#: durchrutschen.
STICHWORT = {"leitwort": "Leitwort", "schlusspunkt": "Punkt", "laenge": "Zeichen"}
#: Was im Katalogtitel stehen muss, damit er seinen Gegenstand benennt.
TITELWORT = {"leitwort": "leitwort", "schlusspunkt": "punkt"}

LAENGENREGELN_DER_ART = {"brief": {"betreff"}, "mail": {"betreff", "email.betreff"}}

#: Die beiden Einträge, die von der Länge reden.
LAENGENEINTRAEGE = {"werkzeug.betreff_laenge", "email.betreff_laenge"}


def _linte(tmp_path, art: str, betreff: str = ALLES_FALSCH) -> lint.Bericht:
    pfad = tmp_path / "nachricht.md"
    kopf = VORLAGEN[art].format(betreff=betreff)
    pfad.write_text(f"---\n{kopf}---\nText der Nachricht.\n", encoding="utf-8")
    return falzmarke.linte(pfad, profil_verzeichnis=PROFILE)


def _rollen(bericht: lint.Bericht) -> dict[str, lint.Befund]:
    """Ordnet die drei Betreffmeldungen ihrer Rolle zu — nach dem Wortlaut der
    Meldung, nicht nach dem Regelnamen. Der Name ist ja das, was sich ändert.

    Zugleich die Kontrollprobe: Ohne genau drei Meldungen, je Rolle eine, hätte
    der Aufbau nicht gemessen, was die Tests darunter behaupten.
    """
    rollen: dict[str, lint.Befund] = {}
    for befund in bericht.befunde:
        text = befund.meldung.split(" — ")[0]
        for rolle, wort in STICHWORT.items():
            if wort in text:
                assert rolle not in rollen, (
                    f"zwei Meldungen für {rolle}:\n{bericht.als_text('nachricht.md')}")
                rollen[rolle] = befund
                break
        else:
            raise AssertionError(
                f"unerwartete Meldung neben den drei Betreffregeln:\n"
                f"{bericht.als_text('nachricht.md')}")
    assert set(rollen) == {"leitwort", "schlusspunkt", "laenge"}, (
        f"der Prüfaufbau löst nicht alle drei Regeln aus:\n{bericht.als_text('nachricht.md')}")
    return rollen


def _wirkung(befund: lint.Befund | None) -> str | None:
    """Was der Nutzer sieht: die Schwere, oder nichts, wenn nicht gemeldet wird."""
    return befund.schwere if befund is not None else None


def _sabotiere(monkeypatch, ids: set[str], herkunft: str) -> None:
    """Setzt die Herkunft der genannten Katalogeinträge herab — nur im Speicher.

    Die Zuordnung Regelname → Eintrag wird über `_nach_lint` gelesen; sie ist
    zwischengespeichert und deshalb der Ort, an dem eine Kopie greift. Der
    Anker prüft, dass es die Einträge gibt: Eine Sabotage an nichts wäre grün.
    """
    kaputt = copy.deepcopy(regeln.alle())
    vorhanden = {r["id"] for r in kaputt}
    assert ids <= vorhanden, f"Sabotage an Einträgen, die es nicht gibt: {ids - vorhanden}"
    for regel in kaputt:
        if regel["id"] in ids:
            regel["herkunft"] = herkunft
    monkeypatch.setattr(
        regeln, "_nach_lint", lambda: {r["lint"]: r for r in kaputt if r.get("lint")})


# ── Leitwort und Schlusspunkt melden unter eigenem Namen ────────────────────

@pytest.mark.parametrize("art", ["brief", "mail"])
@pytest.mark.parametrize("rolle", ROLLEN)
def test_leitwort_und_schlusspunkt_haben_einen_eigenen_regelnamen(tmp_path, art, rolle):
    """Nicht mehr der Name — und damit nicht mehr der Eintrag — der Länge."""
    rollen = _rollen(_linte(tmp_path, art))
    eigen, laenge = rollen[rolle].regel, rollen["laenge"].regel
    assert eigen != laenge, f"{rolle} meldet weiter unter dem Namen der Länge: {eigen!r}"
    assert eigen not in LAENGENREGELN_DER_ART[art], (
        f"{rolle} meldet unter {eigen!r}, dem Namen einer Längenregel")
    eintrag, laengeneintrag = regeln.fuer_lint(eigen), regeln.fuer_lint(laenge)
    assert eintrag is not None, f"{eigen!r} steht in keinem Katalogeintrag"
    assert eintrag["id"] != laengeneintrag["id"]
    assert eintrag["id"] not in LAENGENEINTRAEGE


def test_vier_regelnamen_getrennt_fuer_brief_und_mail(tmp_path):
    """Leitwort und Schlusspunkt, je in Brief und Mail: vier verschiedene Namen.

    Ein gemeinsamer Name für Brief und Mail hieße ein gemeinsamer Eintrag — und
    damit eine gemeinsame Wirkung, obwohl die Mail das Leitwort aus einem
    anderen Grund verbietet.
    """
    namen = {(art, rolle): _rollen(_linte(tmp_path, art))[rolle].regel
             for art in VORLAGEN for rolle in ROLLEN}
    assert len(set(namen.values())) == 4, f"nicht vier verschiedene Namen: {namen}"


# ── Jeder neue Name hat einen Katalogeintrag, der seinen Gegenstand nennt ───

@pytest.mark.parametrize("art", ["brief", "mail"])
@pytest.mark.parametrize("rolle", ROLLEN)
def test_der_katalogtitel_benennt_den_gegenstand(tmp_path, art, rolle):
    bericht = _linte(tmp_path, art)
    befund = _rollen(bericht)[rolle]
    eintrag = regeln.fuer_lint(befund.regel)
    assert eintrag is not None, f"{befund.regel!r} steht in keinem Katalogeintrag"
    titel = eintrag["titel"].lower()
    assert TITELWORT[rolle] in titel, (
        f"der Titel von {eintrag['id']} nennt nicht, worum es geht: {eintrag['titel']!r}")
    assert "zeichen" not in titel and "länge" not in titel, (
        f"der Titel redet von der Länge: {eintrag['titel']!r}")


@pytest.mark.parametrize("art", ["brief", "mail"])
@pytest.mark.parametrize("rolle", ROLLEN)
def test_die_neuen_eintraege_sind_werkzeugregeln_ohne_quelle(tmp_path, art, rolle):
    """Option 1: `herkunft: werkzeug`. Eine Quelle zu nennen wäre eine
    Behauptung — geprüft hat sie niemand (#296)."""
    befund = _rollen(_linte(tmp_path, art))[rolle]
    eintrag = regeln.fuer_lint(befund.regel)
    assert eintrag is not None, f"{befund.regel!r} steht in keinem Katalogeintrag"
    # Erst der eigene Eintrag, dann seine Herkunft: Der geerbte Längeneintrag
    # trägt heute schon `werkzeug` — die Herkunft allein bewiese nichts.
    assert eintrag["id"] not in LAENGENEINTRAEGE, (
        f"{rolle} hängt noch am Längeneintrag {eintrag['id']}")
    assert eintrag["herkunft"] == regeln.WERKZEUG, eintrag["id"]
    assert not eintrag.get("quellen"), f"{eintrag['id']} nennt Quellen: {eintrag['quellen']}"
    assert regeln.deckel(eintrag) != regeln.DECKEL_KEINE, (
        f"{eintrag['id']} schaltet die Prüfung ab — das wäre Option 3, nicht Option 1")


@pytest.mark.parametrize("rolle", ROLLEN)
def test_im_brief_wirken_leitwort_und_schlusspunkt_weiter_als_fehler(tmp_path, rolle):
    """Die Wirkung bleibt, wie sie heute ist — im Brief ein Fehler. Steht in
    derselben Datei wie die Namensprobe, damit sie mit den eigenen Einträgen
    gemessen wird und nicht mit dem geerbten."""
    befund = _rollen(_linte(tmp_path, "brief"))[rolle]
    eintrag = regeln.fuer_lint(befund.regel)
    assert eintrag is not None and eintrag["id"] not in LAENGENEINTRAEGE, (
        f"{rolle} hängt noch an einem Längeneintrag")
    assert eintrag["wirkung"] == "fehler", eintrag["id"]
    assert befund.schwere == lint.FEHLER, befund.schwere


# ── `werkzeug.betreff_laenge` bleibt, was es sagt: die Länge ────────────────

@pytest.mark.parametrize("art", ["brief", "mail"])
def test_unter_den_laengennamen_meldet_nur_noch_die_laenge(tmp_path, art):
    """Die Umkehrung: Was unter `betreff` (Brief) beziehungsweise `betreff` und
    `email.betreff` (Mail) läuft, redet nur noch von Zeichen."""
    bericht = _linte(tmp_path, art)
    rollen = _rollen(bericht)
    unter_laengennamen = [b for b in bericht.befunde
                          if b.regel in LAENGENREGELN_DER_ART[art]]
    assert unter_laengennamen == [rollen["laenge"]], (
        "unter dem Namen der Länge meldet noch etwas anderes:\n"
        + bericht.als_text("nachricht.md"))


# ── Gegenprobe: Herabstufen der Länge ändert Leitwort und Schlusspunkt nicht ─
#
# Heute tut sie es — das ist der Beleg, dass die Änderung etwas bewirkt. Jede
# Probe prüft ZUERST, dass die Sabotage die Länge tatsächlich verändert; sonst
# bewiese „Leitwort unverändert" nichts, weil die Sabotage gar nicht gegriffen
# hätte.

@pytest.mark.parametrize("art, herkunft", [
    ("brief", regeln.OFFEN),      # die Länge verschwindet
    ("brief", regeln.EINZELN),    # die Länge wird zur Warnung
    ("mail", regeln.OFFEN),       # die Länge verschwindet (war schon Warnung)
])
def test_herabgestufte_laenge_zieht_leitwort_und_schlusspunkt_nicht_mit(
        tmp_path, monkeypatch, art, herkunft):
    vorher = _rollen(_linte(tmp_path, art))
    _sabotiere(monkeypatch, LAENGENEINTRAEGE, herkunft)
    nachher_bericht = _linte(tmp_path, art)
    nachher = {b.meldung.split(" — ")[0]: b for b in nachher_bericht.befunde}

    def nachher_von(rolle: str) -> lint.Befund | None:
        return next((b for text, b in nachher.items() if STICHWORT[rolle] in text), None)

    assert _wirkung(nachher_von("laenge")) != _wirkung(vorher["laenge"]), (
        "Die Sabotage hat nicht gewirkt — die Länge meldet unverändert")
    for rolle in ROLLEN:
        assert nachher_von(rolle) is not None, (
            f"{rolle} wird nach der Herabstufung der Länge nicht mehr gemeldet")
        assert _wirkung(nachher_von(rolle)) == _wirkung(vorher[rolle]), (
            f"{rolle}: Wirkung {_wirkung(vorher[rolle])!r} → "
            f"{_wirkung(nachher_von(rolle))!r}, obwohl nur die Länge herabgestuft wurde")


@pytest.mark.parametrize("art", ["brief", "mail"])
@pytest.mark.parametrize("herabgestuft, unberuehrt", [
    ("leitwort", ("schlusspunkt", "laenge")),
    ("schlusspunkt", ("leitwort", "laenge")),
])
def test_herabgestufter_eigener_eintrag_beruehrt_die_anderen_nicht(
        tmp_path, monkeypatch, art, herabgestuft, unberuehrt):
    """Die Gegenrichtung: Der eigene Eintrag steuert seine Meldung — und nur sie.

    Ohne diese Probe könnte „eigener Name" auch heißen, dass der Eintrag zwar
    angelegt ist, die Meldung aber weiter woanders hängt.
    """
    vorher = _rollen(_linte(tmp_path, art))
    eintrag = regeln.fuer_lint(vorher[herabgestuft].regel)
    assert eintrag is not None, f"{vorher[herabgestuft].regel!r} steht in keinem Katalogeintrag"
    _sabotiere(monkeypatch, {eintrag["id"]}, regeln.OFFEN)
    nachher_bericht = _linte(tmp_path, art)
    texte = [b.meldung.split(" — ")[0] for b in nachher_bericht.befunde]

    def gemeldet(rolle: str) -> lint.Befund | None:
        return next((b for b in nachher_bericht.befunde
                     if STICHWORT[rolle] in b.meldung.split(" — ")[0]), None)

    assert gemeldet(herabgestuft) is None, (
        f"Die Sabotage hat nicht gewirkt — {herabgestuft} wird weiter gemeldet: {texte}")
    for rolle in unberuehrt:
        assert _wirkung(gemeldet(rolle)) == _wirkung(vorher[rolle]), (
            f"{rolle} hat sich verändert, obwohl nur der Eintrag von {herabgestuft} "
            f"abgeschaltet wurde: {texte}")
