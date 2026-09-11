"""Die Signatur-Fixture: Daten statt Abschrift (Issue #221).

`tests/golden/email/signatur-faelle.json` ist das, was ein Port in einer anderen
Sprache gegen DIESES Werkzeug halten kann — Eingabeprofil, Kopf und erwartete
Blöcke je Fall. Die Fälle selbst stehen in `tests/signatur_faelle.py`, das JSON
entsteht in `scripts/golden_email.py`.

Was hier geprüft wird, sind drei verschiedene Dinge, und keines ersetzt ein
anderes:

1. **Die Fixture stimmt mit dem Code überein.** Das ist der Golden-Teil: Eine
   verfälschte Zeile in `signatur_bloecke()` macht mindestens einen Eintrag rot.
2. **Die Fixture ist auf Stand.** Ein von Hand geänderter Eintrag wird beim
   nächsten Lauf überschrieben — und bis dahin fällt er hier auf, nicht erst
   beim Lesen.
3. **Jeder Fall hat Trennschärfe.** Zwei Fälle mit identischen Blöcken sehen wie
   zwei Belege aus und sind einer. Genau das passierte beim Bauen: Mit demselben
   Namen in Kopf und Profil waren `ohne-anzeigename` und `name-aus-dem-profil`
   nicht zu unterscheiden, und ein Port, der nur eine der beiden Rückgriffstufen
   kennt, hätte beide bestanden.
"""

from __future__ import annotations

import json

import pytest
import yaml

from falzmarke import eml
from conftest import PROFILE, REPO
import signatur_faelle as faelle

FIXTURE = REPO / "tests" / "golden" / "email" / "signatur-faelle.json"

#: Die Zweige, die es überhaupt zu belegen gilt — aus `signatur_bloecke()`
#: abgelesen, nicht aus dem Vorgangstext übernommen. Jeder braucht einen Fall;
#: welcher, sagt der Name daneben.
ZWEIGE = {
    "pflichtangaben: fusszeile": "fusszeile",
    "pflichtangaben als Liste": "pflichtangaben-liste",
    "Entdoppelung über zwei Blöcke": "doppelte-zeile-in-zwei-bloecken",
    "pflichtangaben fehlt": "ohne-pflichtangaben",
    "eigenes email.telefon gewinnt": "telefon-eigen",
    "Name aus dem Kopf": "ohne-anzeigename",
    "Name aus dem Profil": "name-aus-dem-profil",
    "karges Profil, weniger Blöcke": "karg",
}


@pytest.fixture(scope="module")
def eintraege() -> list[dict]:
    assert FIXTURE.is_file(), (
        f"{FIXTURE.name} fehlt — `python3 scripts/golden_email.py` erzeugt sie")
    geladen = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert geladen, "die Fixture ist leer — dann prüft hier alles nichts"
    return geladen


@pytest.fixture(scope="module")
def basis() -> dict:
    return yaml.safe_load(
        (PROFILE / f"{faelle.BASISPROFIL}.yaml").read_text(encoding="utf-8"))


# ── 1. Die Fixture stimmt mit dem Code überein ───────────────────────────────

def test_jeder_eintrag_entspricht_dem_werkzeug(eintraege):
    """Der Golden-Teil. Eine verfälschte Zeile in `signatur_bloecke()` macht
    mindestens einen Eintrag rot — und zwar ohne Umweg über eine `.eml`."""
    for eintrag in eintraege:
        gerechnet = eml.signatur_bloecke(eintrag["profil"], eintrag["kopf"])
        assert gerechnet == eintrag["bloecke"], eintrag["name"]


def test_kein_eintrag_ist_leer(eintraege):
    """Ein Eintrag ohne Blöcke würde jede Fassung durchwinken."""
    for eintrag in eintraege:
        assert eintrag["bloecke"], eintrag["name"]
        for block in eintrag["bloecke"]:
            assert block, f"{eintrag['name']}: leerer Block"
            assert all(z.strip() for z in block), eintrag["name"]


# ── 2. Die Fixture ist auf Stand ─────────────────────────────────────────────

def test_die_fixture_ist_auf_stand(eintraege, basis):
    """Dieselbe Rechnung wie im Generator, hier als Prüfung.

    Ohne das bliebe ein von Hand geänderter Eintrag stehen, bis jemand zufällig
    `golden_email.py` laufen lässt — und bis dahin wäre die Fixture das, was ein
    fremder Umsetzer für die Wahrheit nimmt.
    """
    assert [e["name"] for e in eintraege] == list(faelle.FAELLE), \
        "Fälle und Fixture laufen auseinander — `python3 scripts/golden_email.py`"
    for eintrag in eintraege:
        profil, kopf = faelle.wandle(eintrag["name"], basis)
        assert eintrag["profil"] == profil, eintrag["name"]
        assert eintrag["kopf"] == kopf, eintrag["name"]


def test_jeder_eintrag_nennt_seinen_zweck(eintraege):
    """Der Zweck ist das, was ein fremder Umsetzer liest, wenn sein Port an
    einem Fall scheitert. Ohne ihn steht dort nur ein Name."""
    for eintrag in eintraege:
        assert eintrag.get("zweck", "").strip(), eintrag["name"]


# ── 3. Trennschärfe ──────────────────────────────────────────────────────────

def test_kein_fall_gleicht_einem_anderen(eintraege):
    """Zwei Fälle mit identischen Blöcken sind ein Fall mit zwei Namen.

    Das ist die Prüfung, die beim Bauen dieser Fixture zugeschlagen hat: Sie
    fand `ohne-anzeigename` und `name-aus-dem-profil` ununterscheidbar, weil
    beide denselben Ersatznamen trugen.
    """
    gesehen: dict[str, str] = {}
    for eintrag in eintraege:
        schluessel = json.dumps(eintrag["bloecke"], ensure_ascii=False)
        zwilling = gesehen.get(schluessel)
        assert zwilling is None, (
            f"„{eintrag['name']}“ und „{zwilling}“ ergeben dieselben Blöcke — "
            "dann belegt der eine nichts, was der andere nicht schon belegt")
        gesehen[schluessel] = eintrag["name"]


def test_alle_zweige_haben_einen_fall(eintraege):
    """Die Vorbedingung, sichtbar gemacht: Welcher Zweig von welchem Fall.

    Eine Fixture mit acht Einträgen sagt nichts darüber, ob sie die acht
    *verschiedenen* Wege durch `signatur_bloecke()` treffen.
    """
    namen = {e["name"] for e in eintraege}
    fehlend = {zweig: fall for zweig, fall in ZWEIGE.items() if fall not in namen}
    assert not fehlend, fehlend


@pytest.mark.parametrize("name, erwartet", [
    # Je Fall das eine Merkmal, an dem man sieht, dass sein Zweig gegriffen hat.
    # Ein Fall, der versehentlich denselben Weg nimmt wie der Basisfall, fällt
    # hier auf — `test_kein_fall_gleicht_einem_anderen` sieht nur, DASS er
    # abweicht, nicht WORIN.
    ("fusszeile", "93055 Regensburg"),
    ("pflichtangaben-liste", "Musterweg 12 · 93055 Regensburg"),
    ("telefon-eigen", "Telefon 030 123456"),
    ("ohne-anzeigename", faelle.NAME_AUS_KOPF),
    ("name-aus-dem-profil", faelle.NAME_AUS_PROFIL),
])
def test_der_zweig_ist_am_ergebnis_zu_sehen(eintraege, name, erwartet):
    eintrag = next(e for e in eintraege if e["name"] == name)
    zeilen = [z for block in eintrag["bloecke"] for z in block]
    assert erwartet in zeilen, zeilen


def test_die_entdoppelung_greift_im_dafuer_gebauten_fall(eintraege):
    """`www.example.de` steht im Kontakt UND in den Pflichtangaben.

    Der Fall ist nur dann einer, wenn die Zeile vorher wirklich zweimal
    entstünde — sonst prüft er die Entdoppelung nicht, sondern deren Abwesenheit.
    """
    eintrag = next(e for e in eintraege
                   if e["name"] == "doppelte-zeile-in-zwei-bloecken")
    assert "www.example.de" in eintrag["profil"]["email"]["pflichtangaben"], \
        "die Vorbedingung fehlt — dann kann hier nichts entdoppelt werden"
    assert eintrag["profil"]["email"]["web"] == "www.example.de"

    zeilen = [z for block in eintrag["bloecke"] for z in block]
    assert zeilen.count("www.example.de") == 1, zeilen


# ── Die Nebenwirkung: das Profil liegt als Daten bereit ──────────────────────

def test_das_basisprofil_steht_vollstaendig_in_der_fixture(eintraege, basis):
    """#221, letzter Absatz: Das Website-Repo führte eine **Abschrift** von
    `typst/profiles/example.yaml`, weil es keinen YAML-Parser hat.

    Damit die entfallen kann, muss das Profil hier vollständig stehen — nicht
    nur die Felder, die die Signatur braucht.
    """
    eintrag = next(e for e in eintraege if e["name"] == "fusszeile")
    assert eintrag["profil"] == basis, \
        "der Basisfall weicht vom ausgelieferten Profil ab"
    for feld in ("absender", "briefkopf", "fusszeile", "email", "infoblock_defaults"):
        assert feld in eintrag["profil"], feld


def test_die_fixture_ist_utf8_mit_echten_umlauten():
    """`ensure_ascii=False` im Generator — sonst stünde `\\u00fc` in der Datei
    und jeder Leser müsste sie erst dekodieren."""
    roh = FIXTURE.read_text(encoding="utf-8")
    assert "Geschäftsführerin" in roh, "die Umlaute sind escaped"
    assert "\\u00" not in roh
    assert roh.endswith("\n"), "ohne Zeilenende am Dateiende meckert jedes Werkzeug"


def test_die_fixture_liegt_bei_den_goldens():
    """Nicht weil es schöner ist, sondern weil sie dasselbe Versprechen trägt:
    erzeugt, nicht gepflegt."""
    assert FIXTURE.parent == REPO / "tests" / "golden" / "email"
    assert FIXTURE.suffix == ".json"
