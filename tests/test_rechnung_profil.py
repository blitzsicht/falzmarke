"""Der Abschnitt `rechnung:` im Profil (#116).

§ 14 Absatz 4 Nummer 1 und 2 UStG verlangt Name und Anschrift des Ausstellers
sowie Steuernummer oder USt-IdNr. Beides steht im Profil und nicht im einzelnen
Schreiben — der Kommentar zu `RECHNUNG_PFLICHTFELDER` sagte das schon, bevor es
eine Prüfung dafür gab. Dies ist die Prüfung.

Jeder Fall hat hier seine Gegenrichtung: Was melden MUSS, steht neben dem, was
schweigen muss. Eine Sammlung nur schweigender Fälle belegt nichts — sie wäre
auch dann grün, wenn die Prüfung gar nichts täte.

Name, Straße, PLZ und Ort kommen aus `absender:`, das es für den Brief schon
gibt. Doppelt gepflegt liefen die beiden Fassungen auseinander, und die
eingebettete XML läse dann etwas anderes als der Briefkopf.
"""

from __future__ import annotations

import copy

import pytest
import yaml

from falzmarke import lint
from conftest import PROFILE


@pytest.fixture(scope="module")
def basis() -> dict:
    return yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))


def _regeln(profil: dict) -> set[str]:
    bericht = lint.Bericht()
    lint.pruefe_rechnung_profil(profil, bericht)
    return {befund.regel for befund in bericht.befunde}


def _ohne(basis: dict, **ersetzt) -> dict:
    """Kopie des Profils mit geänderten Abschnitten."""
    profil = copy.deepcopy(basis)
    for schluessel, wert in ersetzt.items():
        if wert is None:
            profil.pop(schluessel, None)
        else:
            profil[schluessel] = wert
    return profil


# ── Was schweigen muss ──────────────────────────────────────────────────────

def test_das_mitgelieferte_profil_ist_vollstaendig(basis):
    """Ein ausgeliefertes Profil, das bei jeder Rechnung meldet, wäre Lärm."""
    assert _regeln(basis) == set()


def test_die_steuernummer_genuegt_statt_der_ust_idnr(basis):
    """§ 14 Absatz 4 Nummer 2 verlangt eine von beiden, nicht beide."""
    profil = _ohne(basis, rechnung={"steuernummer": "244/107/01234", "land": "DE"})
    assert _regeln(profil) == set()


def test_beide_angaben_zugleich_sind_zulaessig(basis):
    profil = _ohne(basis, rechnung={
        "steuernummer": "244/107/01234", "ust_idnr": "DE123456789", "land": "DE"})
    assert _regeln(profil) == set()


# ── Was melden MUSS ─────────────────────────────────────────────────────────

def test_ohne_abschnitt_rechnung_meldet_die_pruefung(basis):
    assert "rechnung.aussteller" in _regeln(_ohne(basis, rechnung=None))


def test_ohne_steuerangabe_meldet_die_pruefung(basis):
    profil = _ohne(basis, rechnung={"land": "DE"})
    assert "rechnung.steuernummer" in _regeln(profil)


def test_der_laendercode_wird_nicht_auf_de_geraten(basis):
    """Was fehlt, fehlt sichtbar — geraten wird er nicht, auch nicht für DE."""
    profil = _ohne(basis, rechnung={"ust_idnr": "DE123456789"})
    assert "rechnung.aussteller" in _regeln(profil)


def test_ein_tippfehler_im_feldnamen_bleibt_nicht_stumm(basis):
    """`ust_idnrr` sähe aus wie eine gesetzte Angabe und wäre keine."""
    profil = _ohne(basis, rechnung={"ust_idnrr": "DE123456789", "land": "DE"})
    regeln = _regeln(profil)
    assert "rechnung.aussteller" in regeln      # das unbekannte Feld
    assert "rechnung.steuernummer" in regeln    # und die dadurch fehlende Angabe


@pytest.mark.parametrize("feld", ["name", "strasse", "plz", "ort"])
def test_eine_unvollstaendige_anschrift_meldet_die_pruefung(basis, feld):
    absender = dict(basis["absender"])
    absender.pop(feld)
    assert "rechnung.aussteller" in _regeln(_ohne(basis, absender=absender))


def test_die_meldung_nennt_das_fehlende_feld(basis):
    """Ohne den Namen im Text muss der Leser raten, welches der vier fehlt."""
    absender = dict(basis["absender"])
    absender.pop("plz")
    bericht = lint.Bericht()
    lint.pruefe_rechnung_profil(_ohne(basis, absender=absender), bericht)
    assert any("`plz:`" in b.meldung for b in bericht.befunde), bericht.als_text()


# ── Welches mitgelieferte Profil den Abschnitt trägt, und welches nicht ─────

def test_das_privatprofil_traegt_bewusst_keinen_abschnitt():
    """`example-privat.yaml` ist das Profil einer Privatperson — Kündigung,
    Widerspruch, Bewerbung. Eine Privatperson hat keine USt-IdNr., und ein
    erfundener Wert wäre schlechter als sein Fehlen: Er sähe aus wie eine
    Angabe und wäre keine.

    Der Test steht hier, damit die Lücke als Absicht erkennbar bleibt. Ohne ihn
    trüge sie irgendwann jemand „der Vollständigkeit halber" nach.
    """
    profil = yaml.safe_load(
        (PROFILE / "example-privat.yaml").read_text(encoding="utf-8"))
    assert "rechnung" not in profil

    # Und die Prüfung meldet das auch — wer damit eine Rechnung setzt, erfährt es.
    assert "rechnung.aussteller" in _regeln(profil)


@pytest.mark.parametrize("name", ["example", "example-grafik"])
def test_die_geschaeftsprofile_tragen_den_abschnitt(name):
    """`example-grafik` benutzt die Beispielrechnung; `example` ist die Vorlage."""
    profil = yaml.safe_load((PROFILE / f"{name}.yaml").read_text(encoding="utf-8"))
    assert _regeln(profil) == set(), f"{name}.yaml meldet beim Setzen einer Rechnung"
