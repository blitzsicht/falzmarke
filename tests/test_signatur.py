"""Die Signatur in drei Blöcken (Issue #105).

Bis hierher stand alles in einem Block — dreizehn Zeilen, in denen der Name
aussieht wie die Umsatzsteuer-Identifikationsnummer. Drei Blöcke trennen, was
verschieden ist: wer schreibt, wie man ihn erreicht, was das Gesetz verlangt.

Die Signatur ist das, was bei **jeder** Mail mitgeht. Zwei Dinge dürfen ihr
nicht passieren: doppelte Zeilen und Lücken. Beide sind hier geprüft, und zu
jeder Prüfung steht die Gegenrichtung daneben.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from falzmarke import cli as falzmarke
from falzmarke import eml, lint, markdown
from conftest import EMAIL_BEISPIELE, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"
KOPF = {"unterzeichner": "Erika Muster", "anrede": "Sehr geehrte Frau Muster,"}


def _profil(name: str = "example") -> dict:
    return yaml.safe_load((PROFILE / f"{name}.yaml").read_text(encoding="utf-8"))


# ── Die Gliederung ──────────────────────────────────────────────────────────

def test_die_signatur_hat_drei_bloecke():
    bloecke = eml.signatur_bloecke(_profil(), KOPF)
    assert len(bloecke) == 3, [b[:1] for b in bloecke]


def test_person_kontakt_recht_stehen_in_dieser_reihenfolge():
    person, kontakt, recht = eml.signatur_bloecke(_profil(), KOPF)
    assert person[0] == "Erika Muster"
    assert any(z.startswith("Telefon") for z in kontakt), kontakt
    assert any("@" in z for z in kontakt), kontakt
    assert any("HRB" in z for z in recht), recht


def test_der_datenschutzhinweis_steht_beim_recht():
    """Er stand bis #105 zwischen Web und Firma, also im Kontaktteil. Er ist
    eine Rechtsangabe."""
    _, kontakt, recht = eml.signatur_bloecke(_profil(), KOPF)
    assert not any("datenschutz" in z for z in kontakt), kontakt
    assert any("datenschutz" in z for z in recht), recht


def test_kein_block_ist_leer():
    """Eine Leerzeile mitten in einer Signatur sieht aus wie ein Fehler des
    Absenders, nicht wie ein fehlendes Profilfeld."""
    for block in eml.signatur_bloecke(_profil(), KOPF):
        assert block
        assert all(z.strip() for z in block)


def test_ein_karges_profil_ergibt_weniger_bloecke_statt_leerer():
    profil = {"absender": {"name": "Muster GmbH"},
              "email": {"absender": "post@example.de"}}
    bloecke = eml.signatur_bloecke(profil, KOPF)
    assert all(block for block in bloecke)
    assert 1 <= len(bloecke) <= 3


# ── Nichts doppelt, nichts verloren ─────────────────────────────────────────

def test_keine_zeile_kommt_zweimal_vor():
    """Am mitgelieferten Beispielprofil.

    Achtung, diese Prüfung allein belegt wenig: Dort entsteht heute gar keine
    Doppelung, weil `pflichtangaben: fusszeile` die Firma nur aus einer Quelle
    holt. Der Fall, an dem die Entdoppelung wirklich hängt, steht darunter.
    """
    zeilen = eml.signatur_zeilen(_profil(), KOPF)
    vereinheitlicht = [" ".join(z.split()).casefold() for z in zeilen]
    assert len(vereinheitlicht) == len(set(vereinheitlicht)), zeilen


def test_eine_zeile_in_zwei_bloecken_erscheint_nur_einmal():
    """Der Fall, für den es die Entdoppelung gibt — und der Beleg, dass sie
    über ALLE Blöcke laufen muss, nicht je Block.

    Wer seine Website in den Pflichtangaben wiederholt, hat sie im Kontakt- und
    im Rechtsteil. Block-lokal entdoppelt bliebe sie zweimal stehen, und in
    einer Signatur fällt das sofort auf.
    """
    profil = _profil()
    profil["email"]["pflichtangaben"] = ["www.example.de", "Amtsgericht Musterstadt HRB 1"]
    bloecke = eml.signatur_bloecke(profil, KOPF)
    zeilen = [z for b in bloecke for z in b]
    assert zeilen.count("www.example.de") == 1, zeilen

    # Gegenprobe: Ohne Entdoppelung stünde sie zweimal da. Die Zahl der
    # Rohzeilen ist um genau eine höher — sonst prüft der Test etwas anderes.
    _, kontakt, recht = bloecke
    assert "www.example.de" in kontakt
    assert "www.example.de" not in recht, "die spätere Wiederholung fällt weg, nicht die erste"


def test_die_flache_fassung_ist_die_summe_der_bloecke():
    bloecke = eml.signatur_bloecke(_profil(), KOPF)
    assert eml.signatur_zeilen(_profil(), KOPF) == [z for b in bloecke for z in b]


@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, ids=lambda p: p.stem)
def test_die_signatur_kommt_genau_einmal_vor(beispiel):
    """Die Gegenprobe aus #105, und sie gilt für beide Teile."""
    kopf, body, versatz = falzmarke.lies_brief(beispiel)
    profil = _profil(kopf["profil"])
    bloecke = markdown.lies(body, versatz)
    # Nicht am Namen messen: „Erika Muster" steht auch in
    # „Geschäftsführerin: Erika Muster" aus der Fußzeile. Zwei Rollen, kein
    # Duplikat — die Adresse dagegen kommt genau einmal vor.
    adresse = profil["email"]["absender"]

    text = eml.textteil(kopf, profil, bloecke)
    assert text.count(eml.SIGNATUR_TRENNER) == 1, "der Signaturtrenner steht mehrfach"
    assert text.count(adresse) == 1, f"im Textteil {text.count(adresse)}×"

    html = eml.htmlteil(kopf, profil, bloecke)
    assert html.count(adresse) == 1, f"im HTML-Teil {html.count(adresse)}×"


def test_der_textteil_trennt_die_bloecke_durch_leerzeilen():
    kopf, body, versatz = falzmarke.lies_brief(EMAIL_BEISPIELE[0])
    profil = _profil(kopf["profil"])
    text = eml.textteil(kopf, profil, markdown.lies(body, versatz))
    signatur = text[text.index(eml.SIGNATUR_TRENNER):]
    assert signatur.count("\n\n") == 2, "zwei Leerzeilen für drei Blöcke erwartet"


def test_der_htmlteil_setzt_drei_absaetze():
    kopf, body, versatz = falzmarke.lies_brief(EMAIL_BEISPIELE[0])
    profil = _profil(kopf["profil"])
    html = eml.htmlteil(kopf, profil, markdown.lies(body, versatz))
    # Die Trennlinie gehört an den ersten Block, nicht an jeden.
    assert html.count("border-top") == 1, "die Trennlinie steht mehrfach"


# ── Telefon und Mobil aus dem Profil ────────────────────────────────────────

def test_telefon_kommt_aus_dem_informationsblock_wenn_es_fehlt():
    """Kein Feld wurde umbenannt: Wer nur den Informationsblock pflegt, bekommt
    dieselbe Signatur wie vorher."""
    profil = _profil()
    profil["email"].pop("telefon", None)
    _, kontakt, _ = eml.signatur_bloecke(profil, KOPF)
    assert any("0941 620-9800" in z for z in kontakt), kontakt


def test_das_eigene_telefon_im_email_abschnitt_gewinnt():
    profil = _profil()
    profil["email"]["telefon"] = "030 123456"
    _, kontakt, _ = eml.signatur_bloecke(profil, KOPF)
    assert any("030 123456" in z for z in kontakt), kontakt
    assert not any("0941" in z for z in kontakt), kontakt


def test_mobil_erscheint_nur_wenn_es_gesetzt_ist():
    ohne = eml.signatur_bloecke(_profil(), KOPF)[1]
    assert not any("Mobil" in z for z in ohne)
    profil = _profil()
    profil["email"]["mobil"] = "0170 1234567"
    mit = eml.signatur_bloecke(profil, KOPF)[1]
    assert any(z == "Mobil 0170 1234567" for z in mit), mit


# ── Anrede und Lautstärke: nur Warnungen ────────────────────────────────────

def _ton(anrede, text, briefanrede="Hallo Erika,"):
    profil = _profil()
    if anrede is not None:
        profil["email"]["anrede"] = anrede
    bericht = lint.Bericht()
    lint.pruefe_email_ton(profil, {"anrede": briefanrede}, text, bericht)
    return bericht.befunde


@pytest.mark.parametrize("anrede,text", [
    ("du", "Hallo Erika, ich schicke dir das Angebot."),
    ("sie", "Sehr geehrte Frau Muster, anbei Ihr Angebot."),
    (None, "Wir senden Ihnen anbei das Angebot."),
])
def test_stimmiger_ton_wird_nicht_gemeldet(anrede, text):
    assert not [b for b in _ton(anrede, text) if b.regel == "email.anrede_ton"]


@pytest.mark.parametrize("anrede,text,wort", [
    ("du", "Wir senden Ihnen anbei das Angebot.", "Ihnen"),
    ("sie", "Hallo Erika, ich schicke dir das Angebot.", "dir"),
])
def test_abweichender_ton_wird_gemeldet(anrede, text, wort):
    befunde = [b for b in _ton(anrede, text) if b.regel == "email.anrede_ton"]
    assert befunde
    assert wort in befunde[0].meldung
    assert befunde[0].schwere == "Warnung", "der Ton ist nie ein Fehler"


def test_ihr_am_satzanfang_loest_nichts_aus():
    """Dort ist es nicht von der dritten Person Plural zu unterscheiden. Eine
    Warnung, die bei gültigem Text anschlägt, kostet Vertrauen in alle anderen
    — das war die Lehre aus #133."""
    assert not [b for b in _ton("du", "Alles klar. Ihre Kollegen melden sich.")
                if b.regel == "email.anrede_ton"]


def test_versalien_werden_gemeldet():
    befunde = [b for b in _ton("sie", "Das ist WIRKLICH dringend.")
               if b.regel == "email.versalien"]
    assert befunde
    assert "WIRKLICH" in befunde[0].meldung
    assert befunde[0].schwere == "Warnung"


@pytest.mark.parametrize("text", [
    "Die GmbH nutzt PDF und AGB.",
    "IBAN DE62 7625 1020, BIC BYLADEM1RBG, HRB 12345.",
    "Wir liefern EUR 200 nach DE.",
])
def test_bekannte_kuerzel_sind_kein_geschrei(text):
    """Die Gegenrichtung. Ohne sie wüsste man nur, dass die Regel feuert."""
    assert not [b for b in _ton("sie", text) if b.regel == "email.versalien"]


def test_der_unbekannte_anredewert_ist_ein_fehler():
    """Ein Tippfehler dürfte nicht als „kein Feld gesetzt" durchgehen — dann
    bliebe die Tonprüfung wirkungslos, ohne dass es jemand merkt."""
    profil = _profil()
    profil["email"]["anrede"] = "hoeflich"
    bericht = lint.Bericht()
    lint.pruefe_email_profil(profil, bericht)
    befunde = [b for b in bericht.befunde if b.regel == "email.anrede"]
    assert befunde and befunde[0].schwere == "Fehler"


def test_bekannte_anredewerte_gehen_durch():
    for wert in lint.ANREDEN:
        profil = _profil()
        profil["email"]["anrede"] = wert
        bericht = lint.Bericht()
        lint.pruefe_email_profil(profil, bericht)
        assert not [b for b in bericht.befunde if b.regel == "email.anrede"], wert
