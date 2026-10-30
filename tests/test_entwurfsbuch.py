"""Was aus einem Postfach-Entwurf wurde — Entwurfsbuch und `falzmarke status` (ADR 0055).

ANLASS (25.10.2026): „Die Entwürfe senden, falls noch nicht geschehen“ — und
die Frage, ob eine Mail schon raus ist, ob sie gelöscht oder vor dem Senden
geändert wurde, ging immer wieder an den Menschen. `status` beantwortet sie aus
dem Postfach, dem Entwurfsbuch und dem Tagebuch der Entwurfsbrücke.

Kein Test hier öffnet eine Verbindung. Das Postfach ist die Attrappe aus
`imap_attrappe.py`; sie wirft bei jedem Befehl, der etwas ändern würde.
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bruecke_attrappe import BrueckenAttrappe
from conftest import PROFILE
from falzmarke import bruecke, entwurfsbuch, oeffnen, postfach
from falzmarke import cli as falzmarke
from falzmarke import eml as eml_modul
from imap_attrappe import ImapAttrappe, nachricht
from test_oeffnen import THUNDERBIRD_PFAD, Thunderbird

JETZT = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
VON = "order@example.de"
AN = "erika@example.com"
TEXT = ("Hallo Erika,\n\nbitte die Stickdatei für S1 in Gold anlegen, alle Formate neu, "
        "und das Farbblatt auch in Gold.\n\nViele Grüße\nPaul\n")
ENTWUERFE, GESENDET, PAPIERKORB = "Entw&APw-rfe", "Gesendete Elemente", "Gel&APY-schte Elemente"

MAIL = """---
typ: email
profil: example
an: Paula Beispiel <paula@example.org>
betreff: "Sommerfest – Programm"
anrede: Hallo Paula,
---
anbei der Lageplan für das Sommerfest.
"""


@pytest.fixture(autouse=True)
def _keine_dateiuebergabe(monkeypatch):
    def _nein(*_a, **_k):
        raise AssertionError("ein Test wollte wirklich eine Datei übergeben")

    monkeypatch.setattr(oeffnen, "_fuehre_aus", _nein)


def _postfach(monkeypatch, entwuerfe=(), gesendet=(), papierkorb=()) -> ImapAttrappe:
    attrappe = ImapAttrappe(
        {ENTWUERFE: list(entwuerfe), GESENDET: list(gesendet), PAPIERKORB: list(papierkorb)},
        sonder={"INBOX": "", GESENDET: "\\Sent", ENTWUERFE: "\\Drafts", PAPIERKORB: "\\Trash"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    return attrappe


def _mail(*, text=TEXT, betreff="Auftrag S1", zeit=JETZT - timedelta(hours=2), fassung=""):
    kopf = {"X-Falzmarke-Fassung": fassung} if fassung else None
    return nachricht(an=AN, betreff=betreff, text=text, datum=zeit, von=VON, kopf=kopf), zeit


def _buch(*eintraege: dict) -> None:
    pfad = entwurfsbuch.BUCH_VORGABE
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as datei:
        for eintrag in eintraege:
            datei.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def _eintrag(uid, *, zeit=JETZT - timedelta(hours=3), text=TEXT, betreff="Auftrag S1",
             fassung="f0f0f0f0f0f0") -> dict:
    return {"zeit": zeit.isoformat(), "konto": VON, "uid": str(uid), "fassung": fassung,
            "betreff": betreff, "an": [AN], "text": text}


def _profil(tmp_path: Path, tagebuch: list[dict]) -> Path:
    """Ein Thunderbird-Ordner mit Standardprofil und Tagebuch der Brücke."""
    profil = tmp_path / "Profiles" / "abc.default-release"
    profil.mkdir(parents=True)
    (tmp_path / "profiles.ini").write_text(
        "[Install1]\nDefault=Profiles/abc.default-release\n", encoding="utf-8")
    (profil / entwurfsbuch.TAGEBUCH).write_text(
        "".join(json.dumps(t) + "\n" for t in tagebuch), encoding="utf-8")
    return tmp_path


def _stand(**k) -> entwurfsbuch.Bericht:
    return entwurfsbuch.abgleich(VON, jetzt=JETZT, umgebung={}, **k)


def _einziger(bericht) -> entwurfsbuch.Zustand:
    assert not bericht.grund, bericht.grund
    (zustand,) = bericht.zustaende
    return zustand


# ── Das Entwurfsbuch ────────────────────────────────────────────────────────

@pytest.fixture
def felder(tmp_path) -> dict:
    quelle = tmp_path / "mail.md"
    quelle.write_text(MAIL, encoding="utf-8")
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / "mail", profil_verzeichnis=PROFILE)
    return eml_modul.entwurfsfelder(pfad)


def _entwurf(felder, umgebung=None):
    return oeffnen.entwurf(felder, plattform="darwin", umgebung=umgebung or {"DISPLAY": ":0"},
                           laufen=Thunderbird(), binaer=lambda: THUNDERBIRD_PFAD)


def test_kein_test_schreibt_ins_echte_entwurfsbuch():
    assert Path.home() / ".local" not in entwurfsbuch.BUCH_VORGABE.parents
    assert not entwurfsbuch.BUCH_VORGABE.exists()


def test_ein_postfach_entwurf_steht_danach_im_buch(monkeypatch, felder):
    server = ImapAttrappe({ENTWUERFE: []})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
    lage = _entwurf(felder)
    assert lage.postfach is not None and lage.buch_grund == ""
    (eintrag,) = entwurfsbuch.lesen({}).eintraege
    assert eintrag.konto == felder["absender"].lower()
    assert eintrag.uid == lage.postfach.uid == str(server.ordner[ENTWUERFE][-1].uid)
    assert eintrag.fassung == felder["fassung"] != ""
    assert eintrag.betreff == "Sommerfest – Programm"
    assert eintrag.an == ("paula@example.org",)
    assert eintrag.blindkopie == tuple(a.lower() for a in felder["blindkopie"])
    assert "Lageplan" in eintrag.text


def test_das_bcc_steht_im_buch_und_fehlt_bei_alten_eintraegen(monkeypatch, felder):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    _entwurf(dict(felder, blindkopie=["Archiv@Example.de"]))
    _buch(_eintrag(150))
    neu, alt = entwurfsbuch.lesen({}).eintraege
    assert neu.blindkopie == ("archiv@example.de",)
    assert alt.blindkopie is None, "ohne Feld ist das Bcc unbekannt, nicht leer"


def test_ohne_postfach_entwurf_kein_eintrag(monkeypatch, felder):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe(
        verbindungsfehler=ConnectionRefusedError(61, "aus")))
    lage = _entwurf(felder)
    assert lage.postfach is None
    assert entwurfsbuch.lesen({}).eintraege == []


def test_abgeschaltet_steht_nichts_im_buch_und_der_grund_kommt_zurueck(monkeypatch, felder):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    lage = _entwurf(felder, {"DISPLAY": ":0", "FALZMARKE_ENTWURFSBUCH": "nie"})
    assert lage.postfach is not None
    assert "FALZMARKE_ENTWURFSBUCH=nie" in lage.buch_grund
    assert entwurfsbuch.lesen({}).eintraege == []


def test_ein_buch_das_sich_nicht_schreiben_laesst_haelt_den_entwurf_nicht_auf(
        monkeypatch, felder, tmp_path):
    (tmp_path / "datei").write_text("", encoding="utf-8")
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    lage = _entwurf(felder, {"DISPLAY": ":0",
                             "FALZMARKE_ENTWURFSBUCH": str(tmp_path / "datei" / "buch.jsonl")})
    assert lage.postfach is not None
    assert lage.buch_grund


def test_der_hinweis_steht_in_der_ausgabe(monkeypatch, tmp_path, capsys):
    (tmp_path / "datei").write_text("", encoding="utf-8")
    monkeypatch.setenv("FALZMARKE_ENTWURFSBUCH", str(tmp_path / "datei" / "buch.jsonl"))
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    monkeypatch.setattr(oeffnen, "entwurf", _mit_attrappen(oeffnen.entwurf))
    quelle = tmp_path / "mail.md"
    quelle.write_text(MAIL, encoding="utf-8")
    falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE), "--oeffnen",
                    "-o", str(tmp_path / "mail")])
    assert "HINWEIS  nicht im Entwurfsbuch" in capsys.readouterr().err


def _mit_attrappen(echt):
    def entwurf(felder, **k):
        k.update(plattform="darwin", umgebung={"DISPLAY": ":0", **_umgebung()},
                 laufen=Thunderbird(), binaer=lambda: THUNDERBIRD_PFAD)
        return echt(felder, **k)
    return entwurf


def _umgebung() -> dict:
    import os

    return {k: v for k, v in os.environ.items() if k.startswith("FALZMARKE_ENTWURFSBUCH")}


# ── Liegt noch ──────────────────────────────────────────────────────────────

def test_liegt_und_nichts_ging_raus_heisst_wartet(monkeypatch):
    _postfach(monkeypatch, entwuerfe=[_mail()])
    zustand = _einziger(_stand())
    assert zustand.art == "wartet"
    assert zustand.gesendet == () and zustand.im_buch is False


def test_liegt_noch_aber_derselbe_text_ging_schon_raus(monkeypatch):
    raus = JETZT - timedelta(hours=1)
    _postfach(monkeypatch, entwuerfe=[_mail()], gesendet=[_mail(zeit=raus)])
    bericht = _stand()
    zustand = _einziger(bericht)
    assert zustand.art == "schon_raus"
    assert zustand.gesendet == (raus,)
    assert "nicht noch einmal senden" in "\n".join(entwurfsbuch.zeilen(bericht))


def test_ein_anderer_empfaenger_ist_nicht_schon_raus(monkeypatch):
    fremd = nachricht(an="jemand@example.net", betreff="Auftrag S1", text=TEXT,
                      datum=JETZT - timedelta(hours=1), von=VON), JETZT - timedelta(hours=1)
    _postfach(monkeypatch, entwuerfe=[_mail()], gesendet=[fremd])
    assert _einziger(_stand()).art == "wartet"


def test_ein_liegender_entwurf_aus_dem_buch_ist_einmal_da(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail(fassung="f0f0f0f0f0f0")])
    _buch(_eintrag(server.ordner[ENTWUERFE][0].uid))
    zustand = _einziger(_stand())
    assert zustand.art == "wartet" and zustand.im_buch is True


def test_ein_offenes_fenster_heisst_offen(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    uid = server.ordner[ENTWUERFE][0].uid
    attrappe = BrueckenAttrappe({"ok": True, "fenster": [
        {"titel": "Verfassen: Auftrag S1", "betreff": "Auftrag S1",
         "draft_id": f"imap-message://order%40example.de@127.0.0.1/Entw&APw-rfe#{uid}"}]})
    monkeypatch.setattr(bruecke, "VERBINDEN", attrappe)
    assert _einziger(_stand()).art == "offen"
    assert [a["befehl"] for a in attrappe.anfragen] == ["fenster"]


def test_eine_bruecke_ohne_fensterliste_ist_kein_offen_und_kein_still(monkeypatch):
    _postfach(monkeypatch, entwuerfe=[_mail()])
    monkeypatch.setattr(bruecke, "VERBINDEN",
                        BrueckenAttrappe({"ok": False, "fehler": "befehl_unbekannt"}))
    bericht = _stand()
    assert _einziger(bericht).art == "wartet"
    assert any(h.startswith("offene Fenster nicht geprüft") for h in bericht.hinweise)


def test_zwei_gleiche_entwuerfe_werden_gemeldet(monkeypatch):
    _postfach(monkeypatch, entwuerfe=[_mail(), _mail(), _mail(betreff="Anderes")])
    bericht = _stand()
    (doppelt,) = [h for h in bericht.hinweise if "nur einen senden" in h]
    assert doppelt.startswith("2 Entwürfe „Auftrag S1“ an erika@example.com")
    assert "UID 101, 102" in doppelt


def test_derselbe_betreff_an_andere_empfaenger_ist_nicht_doppelt(monkeypatch):
    fremd = nachricht(an="jemand@example.net", betreff="Auftrag S1", text=TEXT,
                      datum=JETZT, von=VON), JETZT
    _postfach(monkeypatch, entwuerfe=[_mail(), fremd])
    assert not [h for h in _stand().hinweise if "nur einen senden" in h]


def test_eine_gekappte_suche_wird_gemeldet(monkeypatch):
    monkeypatch.setattr(entwurfsbuch, "GRENZE_GESENDET", 3)
    _postfach(monkeypatch, gesendet=[_mail(zeit=JETZT - timedelta(hours=h)) for h in range(5)])
    bericht = _stand()
    (gekappt,) = [h for h in bericht.hinweise if "nur die neuesten" in h]
    assert gekappt == ("„Gesendete Elemente“: nur die neuesten 3 von 5 Mails angesehen — "
                       "was davor liegt, fehlt im Abgleich")
    assert bericht.angesehen == 3


def test_status_sieht_mehr_gesendete_als_die_grenze_des_ablegens(monkeypatch):
    """Gemessen 25.10.2026: 550 gesendete Mails in vierzehn Tagen, `postfach.GRENZE`
    ist 500. Gelesen wird in Stücken, damit keine Befehlszeile zu lang wird."""
    monkeypatch.setattr(postfach, "GRENZE", 2)
    server = _postfach(monkeypatch,
                       gesendet=[_mail(zeit=JETZT - timedelta(hours=h)) for h in range(5)])
    bericht = _stand()
    assert bericht.angesehen == 5
    assert not [h for h in bericht.hinweise if "nur die neuesten" in h]
    assert len([b for b in server.befehle("UID FETCH") if "HEADER.FIELDS" in str(b)]) == 3


# ── Liegt nicht mehr ────────────────────────────────────────────────────────

def test_aus_dem_buch_gesendet_mit_demselben_text(monkeypatch):
    raus = JETZT - timedelta(hours=1)
    _postfach(monkeypatch, gesendet=[_mail(zeit=raus)])
    _buch(_eintrag(150))
    zustand = _einziger(_stand())
    assert (zustand.art, zustand.text_gleich, zustand.gesendet) == ("gesendet", True, (raus,))
    assert zustand.belegt is False, "ohne Tagebuch ist es eine Quelle, nicht zwei"


def test_zweimal_gesendet_wird_gezaehlt(monkeypatch):
    zeiten = [JETZT - timedelta(hours=2), JETZT - timedelta(hours=1)]
    _postfach(monkeypatch, gesendet=[_mail(zeit=t) for t in zeiten])
    _buch(_eintrag(150))
    bericht = _stand()
    assert _einziger(bericht).gesendet == tuple(zeiten)
    assert ", 2×" in "\n".join(entwurfsbuch.zeilen(bericht))


def test_mit_tagebuch_ist_es_belegt(monkeypatch, tmp_path):
    _postfach(monkeypatch, gesendet=[_mail(zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [
        {"zeit": (JETZT - timedelta(hours=1)).isoformat(), "art": "gesendet",
         "ursprung": {"konto": VON, "uid": 150, "fassung": "f0f0f0f0f0f0"}}])
    bericht = _stand(profilordner=profil)
    zustand = _einziger(bericht)
    assert zustand.belegt is True
    assert bericht.tagebuch == 1
    assert "BELEGT" in "\n".join(entwurfsbuch.zeilen(bericht))


def test_das_tagebuch_eines_anderen_entwurfs_belegt_nichts(monkeypatch, tmp_path):
    _postfach(monkeypatch, gesendet=[_mail(zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [
        {"zeit": (JETZT - timedelta(hours=1)).isoformat(), "art": "gesendet",
         "ursprung": {"konto": VON, "uid": 151, "fassung": "anders"}}])
    assert _einziger(_stand(profilordner=profil)).belegt is False


def _tag(art, uid, *, fassung="f0f0f0f0f0f0", typ="draft", **mehr) -> dict:
    """Eine Tagebuchzeile wie das Add-on sie schreibt. `typ` steht ausdrücklich
    dabei: Ob ein Eintrag von einem Entwurf kommt, entscheidet, ob eine fehlende
    UID ein Fehler ist (#420) oder die Natur der Sache (`new`, `reply`)."""
    return {"zeit": (JETZT - timedelta(hours=1)).isoformat(), "art": art,
            "ursprung": {"typ": typ, "konto": VON, "uid": uid, "fassung": fassung}, **mehr}


def test_zwei_entwuerfe_derselben_quelle_teilen_kein_tagebuch(monkeypatch, tmp_path):
    """Gemessen 25.10.2026: zweimal aus derselben Quelle abgelegt, also dieselbe
    Fassung. Das Tagebuch des einen stand auch beim anderen."""
    server = _postfach(monkeypatch, entwuerfe=[_mail(fassung="f0f0f0f0f0f0"),
                                              _mail(fassung="f0f0f0f0f0f0")])
    erst, zweit = (str(k.uid) for k in server.ordner[ENTWUERFE])
    profil = _profil(tmp_path, [_tag("geoeffnet", int(erst)), _tag("gesperrt", int(zweit))])
    arten = {z.uid: [t["art"] for t in z.tagebuch] for z in _stand(profilordner=profil).zustaende}
    assert arten == {erst: ["geoeffnet"], zweit: ["gesperrt"]}


def test_neu_gespeichert_bleibt_es_derselbe_entwurf(monkeypatch, tmp_path):
    """Speichern legt den Entwurf unter neuer UID ab; gesendet wird dann unter ihr."""
    _postfach(monkeypatch, gesendet=[_mail(zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [_tag("gespeichert", 150, neu_uid=[160]),
                                _tag("gesendet", 160, fassung="")])
    zustand = _einziger(_stand(profilordner=profil))
    assert [t["art"] for t in zustand.tagebuch] == ["gespeichert", "gesendet"]
    assert zustand.belegt is True


def test_ein_liegender_neu_gespeicherter_entwurf_kennt_seine_vorgeschichte(monkeypatch, tmp_path):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    uid = int(server.ordner[ENTWUERFE][0].uid)
    profil = _profil(tmp_path, [_tag("geoeffnet", 90), _tag("gespeichert", 90, neu_uid=[uid]),
                                _tag("geoeffnet", 91)])
    zustand = _einziger(_stand(profilordner=profil))
    assert [t["art"] for t in zustand.tagebuch] == ["geoeffnet", "gespeichert"]


def test_ohne_uid_entscheidet_die_fassung(monkeypatch, tmp_path):
    """Konnte das Add-on die UID nicht lesen, bleibt nur die Fassung."""
    _postfach(monkeypatch, gesendet=[_mail(zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [_tag("gesendet", None)])
    assert _einziger(_stand(profilordner=profil)).belegt is True


def test_geaendert_gesendet_zeigt_den_unterschied(monkeypatch):
    neu = TEXT.replace("in Gold anlegen", "in Silber anlegen")
    _postfach(monkeypatch, gesendet=[_mail(text=neu, zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    bericht = _stand(mit_diff=True)
    zustand = _einziger(bericht)
    assert (zustand.art, zustand.text_gleich) == ("gesendet", False)
    assert any(z.startswith("-") and "Gold" in z for z in zustand.diff)
    assert any(z.startswith("+") and "Silber" in z for z in zustand.diff)
    assert "Text geändert" in "\n".join(entwurfsbuch.zeilen(bericht))


def test_vor_dem_entwurf_gesendetes_ist_nicht_dieser_entwurf(monkeypatch):
    _postfach(monkeypatch, gesendet=[_mail(zeit=JETZT - timedelta(days=2))])
    _buch(_eintrag(150, zeit=JETZT - timedelta(hours=3)))
    assert _einziger(_stand()).art == "verschwunden"


def test_im_papierkorb_heisst_geloescht(monkeypatch):
    _postfach(monkeypatch, papierkorb=[_mail(fassung="f0f0f0f0f0f0")])
    _buch(_eintrag(150))
    bericht = _stand()
    assert _einziger(bericht).art == "geloescht"
    assert "in „Gelöschte Elemente“" in "\n".join(entwurfsbuch.zeilen(bericht))


def test_eine_antwort_im_faden_ist_keine_geaenderte_fassung(monkeypatch):
    """Review 25.10.2026: Der Entwurf lag im Papierkorb, danach ging eine Antwort
    mit anderem Text in denselben Faden. `status` meldete „gesendet, Text geändert“."""
    _postfach(monkeypatch, papierkorb=[_mail(fassung="f0f0f0f0f0f0")],
              gesendet=[_mail(betreff="AW: Auftrag S1", text="Hallo Erika,\n\npasst so.\n",
                              zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    assert _einziger(_stand()).art == "geloescht"


def test_eine_antwort_ohne_papierkorb_ist_keine_geaenderte_fassung(monkeypatch):
    """Der Entwurf ist weg, nicht im Papierkorb; hinaus ging nur eine Antwort darauf."""
    _postfach(monkeypatch, gesendet=[_mail(betreff="AW: Auftrag S1",
                                           text="Hallo Erika,\n\npasst so.\n",
                                           zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    assert _einziger(_stand()).art == "verschwunden"


def test_derselbe_betreff_mit_anderem_text_bleibt_geaendert_gesendet(monkeypatch):
    _postfach(monkeypatch, gesendet=[_mail(text="Hallo Erika,\n\nneue Fassung, bitte in Silber.\n",
                                           zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    zustand = _einziger(_stand())
    assert (zustand.art, zustand.text_gleich) == ("gesendet", False)


def test_ein_aelterer_entwurf_im_papierkorb_verdeckt_kein_geaendertes_senden(monkeypatch):
    """Review 25.10.2026: Ein früherer Entwurf mit demselben Betreff lag im Papierkorb, und
    `status` hätte den geändert gesendeten für gelöscht gehalten."""
    _postfach(monkeypatch, papierkorb=[_mail(zeit=JETZT - timedelta(days=2),
                                             fassung="f0f0f0f0f0f0")],
              gesendet=[_mail(text="Hallo Erika,\n\nneue Fassung, bitte in Silber.\n",
                              zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150, zeit=JETZT - timedelta(hours=3)))
    zustand = _einziger(_stand())
    assert (zustand.art, zustand.text_gleich) == ("gesendet", False)


def test_ein_spaeterer_anderer_entwurf_im_papierkorb_verdeckt_kein_geaendertes_senden(
        monkeypatch):
    """Review 25.10.2026: Der Entwurf ging geändert hinaus, danach warf jemand eine Antwort
    „AW: Auftrag S1“ aus einer anderen Quelle weg. Derselbe Betreff ist nicht derselbe Entwurf."""
    _postfach(monkeypatch, papierkorb=[_mail(betreff="AW: Auftrag S1", fassung="a1a1a1a1a1a1",
                                             zeit=JETZT - timedelta(hours=1))],
              gesendet=[_mail(text="Hallo Erika,\n\nneue Fassung, bitte in Silber.\n",
                              zeit=JETZT - timedelta(hours=2))])
    _buch(_eintrag(150, zeit=JETZT - timedelta(hours=3)))
    zustand = _einziger(_stand())
    assert (zustand.art, zustand.text_gleich) == ("gesendet", False)


def test_ohne_fassung_reicht_derselbe_betreff_fuer_geloescht(monkeypatch):
    """Ein Entwurf, den Thunderbird neu gespeichert hat, trägt womöglich keine Fassung mehr."""
    _postfach(monkeypatch, papierkorb=[_mail(zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150, zeit=JETZT - timedelta(hours=3)))
    assert _einziger(_stand()).art == "geloescht"


def test_nur_ein_aelterer_mit_demselben_betreff_im_papierkorb_heisst_verschwunden(monkeypatch):
    _postfach(monkeypatch, papierkorb=[_mail(zeit=JETZT - timedelta(days=2))])
    _buch(_eintrag(150, zeit=JETZT - timedelta(hours=3)))
    assert _einziger(_stand()).art == "verschwunden"


def test_ein_weggeworfener_antwort_entwurf_ist_geloescht_trotz_gleichem_betreff(monkeypatch):
    """Re-Review 25.10.2026: Thunderbird setzt vor „AW: Auftrag S1“ kein zweites `AW:`.
    Der Entwurf lag im Papierkorb, eine andere Antwort ging mit demselben Betreff hinaus,
    und `status` meldete „gesendet, Text geändert“."""
    angelegt = JETZT - timedelta(hours=3)
    # Wie im Postfach: Das `Date` des Entwurfs steht Sekunden vor seinem Eintrag im Buch.
    _postfach(monkeypatch, papierkorb=[_mail(betreff="AW: Auftrag S1", fassung="f0f0f0f0f0f0",
                                             zeit=angelegt - timedelta(seconds=30))],
              gesendet=[_mail(betreff="AW: Auftrag S1", text="Hallo Erika,\n\npasst so.\n",
                              zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150, betreff="AW: Auftrag S1", zeit=angelegt))
    bericht = _stand()
    zustand = _einziger(bericht)
    assert zustand.art == "geloescht" and len(zustand.anders) == 1
    zeile = "\n".join(entwurfsbuch.zeilen(bericht))
    assert "in „Gelöschte Elemente“ — gleicher Betreff ging" in zeile
    assert "mit anderem Text raus" in zeile


def test_ein_antwort_entwurf_mit_anderem_text_bleibt_geaendert_gesendet(monkeypatch):
    """Der Entwurf ist selbst eine Antwort; gesendet ging er mit demselben `AW:`."""
    _postfach(monkeypatch, gesendet=[_mail(betreff="AW: Auftrag S1",
                                           text="Hallo Erika,\n\nneue Fassung, in Silber.\n",
                                           zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150, betreff="AW: Auftrag S1"))
    zustand = _einziger(_stand())
    assert (zustand.art, zustand.text_gleich) == ("gesendet", False)


def test_eine_kaputte_uid_im_buch_bricht_status_nicht_ab(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    _buch(_eintrag("abc"))
    liegend = str(server.ordner[ENTWUERFE][0].uid)
    assert [z.uid for z in _stand().zustaende] == [liegend]


def test_ein_neuerer_entwurf_mit_demselben_betreff_heisst_ersetzt(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail(text="Hallo, neue Fassung.\n")])
    _buch(_eintrag(50))
    ersetzt = next(z for z in _stand().zustaende if z.uid == "50")
    assert ersetzt.art == "ersetzt"
    assert ersetzt.nachfolger == str(server.ordner[ENTWUERFE][0].uid)


def test_nirgends_heisst_verschwunden_und_nennt_die_ordner(monkeypatch):
    _postfach(monkeypatch)
    _buch(_eintrag(150))
    bericht = _stand()
    assert _einziger(bericht).art == "verschwunden"
    zeile = entwurfsbuch.zeilen(bericht)[1]
    assert zeile.startswith("VERSCHWUNDEN")
    assert "„Entwürfe“" in zeile and "„Gesendete Elemente“" in zeile


def test_aelter_als_das_fenster_zaehlt_nicht(monkeypatch):
    _postfach(monkeypatch)
    _buch(_eintrag(150, zeit=JETZT - timedelta(days=20)))
    assert _stand().zustaende == ()


def test_ein_anderes_konto_zaehlt_nicht(monkeypatch):
    _postfach(monkeypatch)
    _buch(dict(_eintrag(150), konto="servus@example.de"))
    assert _stand().zustaende == ()


# ── Nur lesen, und „nicht geprüft“ ist kein „nichts gefunden“ ──────────────

def test_status_aendert_nichts_im_postfach(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()], gesendet=[_mail()],
                       papierkorb=[_mail()])
    _buch(_eintrag(150))
    _stand()
    assert server.befehle("APPEND") == []
    assert server.befehle("SELECT") == []
    assert len(server.befehle("EXAMINE")) >= 3


def test_ohne_postfach_ist_nichts_geprueft(monkeypatch, capsys):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe(
        verbindungsfehler=ConnectionRefusedError(61, "Connection refused")))
    _buch(_eintrag(150))
    code = falzmarke.main(["status", "--absender", VON])
    ausgabe = capsys.readouterr()
    assert code == falzmarke.EXIT_UMGEBUNG
    assert ausgabe.err.startswith(f"NICHT GEPRÜFT  {VON}")
    assert "VERSCHWUNDEN" not in ausgabe.out + ausgabe.err


def test_json_fuer_sitzungen(monkeypatch, capsys):
    _postfach(monkeypatch, entwuerfe=[_mail()])
    monkeypatch.setattr(entwurfsbuch, "datetime", _Uhr)
    code = falzmarke.main(["status", "--absender", VON, "--json"])
    (bericht,) = json.loads(capsys.readouterr().out)
    assert code == falzmarke.EXIT_OK
    assert bericht["geprueft"] is True
    assert [e["zustand"] for e in bericht["entwuerfe"]] == ["wartet"]


class _Uhr(datetime):
    @classmethod
    def now(cls, tz=None):
        return JETZT if tz else JETZT.replace(tzinfo=None)


def test_tage_unter_eins_ist_ein_eingabefehler(capsys):
    assert falzmarke.main(["status", "--absender", VON, "--tage", "0"]) == falzmarke.EXIT_EINGABE


# ── Fenster, Empfänger und Fassung (ADR 0056) ───────────────────────────────

def _offen(monkeypatch, uid, **fenster) -> None:
    eintrag = {"titel": "Verfassen: Auftrag S1", "betreff": "Auftrag S1", "live": True,
               "draft_id": f"imap-message://order%40example.de@127.0.0.1/Entw&APw-rfe#{uid}",
               "identitaet": VON, "an": [AN], "kopie": [], "blindkopie": ["dms@example.de"],
               "anhaenge": ["Lageplan.pdf"], "text": TEXT, **fenster}
    monkeypatch.setattr(bruecke, "VERBINDEN", BrueckenAttrappe({"ok": True, "fenster": [eintrag]}))


def _fensterzeile(bericht) -> str:
    (zeile,) = [z for z in entwurfsbuch.zeilen(bericht) if "Fenster:" in z]
    return zeile


def test_ein_offenes_fenster_nennt_absender_empfaenger_und_anhaenge(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    _offen(monkeypatch, server.ordner[ENTWUERFE][0].uid)
    bericht = _stand()
    zustand = _einziger(bericht)
    assert (zustand.art, zustand.fenster_text_gleich) == ("offen", True)
    zeile = _fensterzeile(bericht)
    for teil in (f"von {VON}", f"An {AN}", "Bcc dms@example.de", "Anhänge Lageplan.pdf",
                 "Text wie angelegt"):
        assert teil in zeile


def test_gegenprobe_ein_im_fenster_geaenderter_text_faellt_auf(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    _offen(monkeypatch, server.ordner[ENTWUERFE][0].uid,
           text=TEXT.replace("in Gold anlegen", "in Silber anlegen"))
    bericht = _stand()
    assert _einziger(bericht).fenster_text_gleich is False
    zeile = _fensterzeile(bericht)
    assert "Text geändert" in zeile and "Text wie angelegt" not in zeile


def test_die_konto_signatur_im_fenster_aendert_den_text_nicht(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    _offen(monkeypatch, server.ordner[ENTWUERFE][0].uid,
           text=TEXT + "\n-- \nSiluri · Kremser Str. 35\n")
    assert _einziger(_stand()).fenster_text_gleich is True


def test_ein_fenster_von_vor_0_3_meldet_nur_dass_es_offen_ist(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    _offen(monkeypatch, server.ordner[ENTWUERFE][0].uid, live=False, text=None)
    bericht = _stand()
    zustand = _einziger(bericht)
    assert (zustand.art, zustand.fenster_text_gleich) == ("offen", None)
    assert not [z for z in entwurfsbuch.zeilen(bericht) if "Fenster:" in z]


def _versand(*, an=(AN,), blindkopie=("dms@example.de",), message_id="test@example.org",
             **mehr) -> dict:
    return _tag("gesendet", 150, message_id=message_id, identitaet=VON,
                an=list(an), kopie=[], blindkopie=list(blindkopie), anhaenge=[], **mehr)


def _gesendet_mit(monkeypatch, tmp_path, versand, *, blindkopie=("dms@example.de",)):
    _postfach(monkeypatch, gesendet=[_mail(zeit=JETZT - timedelta(hours=1))])
    eintrag = _eintrag(150)
    if blindkopie is not None:
        eintrag["blindkopie"] = list(blindkopie)
    _buch(eintrag)
    return _stand(profilordner=_profil(tmp_path, [versand]))


def test_gesendet_an_die_angelegten_empfaenger(monkeypatch, tmp_path):
    bericht = _gesendet_mit(monkeypatch, tmp_path, _versand())
    zustand = _einziger(bericht)
    assert (zustand.empfaenger_plus, zustand.empfaenger_minus) == ((), ())
    assert "Empfänger wie angelegt" in "\n".join(entwurfsbuch.zeilen(bericht))


def test_gegenprobe_ein_fehlendes_bcc_wird_genannt(monkeypatch, tmp_path):
    bericht = _gesendet_mit(monkeypatch, tmp_path, _versand(blindkopie=()))
    zustand = _einziger(bericht)
    assert (zustand.empfaenger_plus, zustand.empfaenger_minus) == ((), ("dms@example.de",))
    text = "\n".join(entwurfsbuch.zeilen(bericht))
    assert "ABWEICHEND vom Entwurf: −dms@example.de" in text
    assert "Empfänger wie angelegt" not in text


def test_ein_hinzugefuegter_empfaenger_wird_genannt(monkeypatch, tmp_path):
    zustand = _einziger(_gesendet_mit(
        monkeypatch, tmp_path, _versand(an=(AN, "chef@example.de"))))
    assert zustand.empfaenger_plus == ("chef@example.de",)


def test_ein_alter_bucheintrag_ohne_bcc_vergleicht_ohne_bcc(monkeypatch, tmp_path):
    zustand = _einziger(_gesendet_mit(monkeypatch, tmp_path, _versand(), blindkopie=None))
    assert (zustand.empfaenger_plus, zustand.empfaenger_minus) == ((), ())


def test_ein_tagebuch_ohne_empfaenger_gibt_keine_empfaengerzeile(monkeypatch, tmp_path):
    bericht = _gesendet_mit(monkeypatch, tmp_path, _tag("gesendet", 150))
    assert _einziger(bericht).versand is None
    assert not [z for z in entwurfsbuch.zeilen(bericht) if "Ging an" in z]


def test_ohne_kopfzeile_findet_das_tagebuch_die_fassung(monkeypatch, tmp_path):
    """Gemessen 25.10.2026: In der gesendeten Mail fehlt `X-Falzmarke-Fassung`.
    Mit anderem Text erkennt sie dann nur die Message-ID im Tagebuch wieder."""
    neu = "Hallo Erika,\n\nkurze Änderung: Wir nehmen Silber statt Gold.\n\nGruß\nPaul\n"
    _postfach(monkeypatch, gesendet=[_mail(text=neu,
                                           zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [_versand()])
    zustand = _einziger(_stand(profilordner=profil))
    assert zustand.gesendet == (JETZT - timedelta(hours=1),) and zustand.anders == ()


def test_gegenprobe_ohne_tagebuch_bleibt_die_fassung_unbekannt(monkeypatch, tmp_path):
    neu = "Hallo Erika,\n\nkurze Änderung: Wir nehmen Silber statt Gold.\n\nGruß\nPaul\n"
    _postfach(monkeypatch, gesendet=[_mail(text=neu,
                                           zeit=JETZT - timedelta(hours=1))])
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [_versand(message_id="andere@example.org")])
    zustand = _einziger(_stand(profilordner=profil))
    assert zustand.gesendet == () and zustand.anders == (JETZT - timedelta(hours=1),)


def test_json_traegt_fenster_und_empfaenger(monkeypatch, tmp_path):
    bericht = _gesendet_mit(monkeypatch, tmp_path, _versand(blindkopie=()))
    (z,) = entwurfsbuch.als_json(bericht)["entwuerfe"]
    assert z["empfaenger_minus"] == ["dms@example.de"] and z["versand"]["an"] == [AN]
    assert z["fenster"] is None


# ── Das Buch gehört nur dem eigenen Konto (ADR 0058) ────────────────────────
#
# Gemessen am 25.10.2026 auf diesem Rechner: `-rw-r--r--` in `drwxr-xr-x`, mit
# dem Brieftext im Klartext. Wer `--oeffnen` nutzt, legte damit ein für jedes
# Konto des Rechners lesbares Archiv seiner Geschäftspost an. Die Proben hier
# lesen die Rechte **nach** dem Schreiben und fahren mit Umask 022 — sonst
# messen sie die Umask und nicht den Code.

nur_unix = pytest.mark.skipif(os.name != "posix",
                              reason="Rechtebits und Symlinks gibt es nur dort")


@pytest.fixture
def umask_022():
    vorher = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(vorher)


def _rechte(pfad: Path) -> int:
    return pfad.stat().st_mode & 0o777


@nur_unix
def test_das_buch_ist_nur_fuer_das_eigene_konto_lesbar(monkeypatch, felder, umask_022, tmp_path):
    """Der Ordner muss hier erst entstehen.

    `conftest.py` legt das Buch in einen Ordner, den pytest schon angelegt hat
    — und der steht auf 0700. Gegen ihn gemessen wäre die Probe erfüllt,
    bevor `mkdir(mode=…)` überhaupt läuft: Die Sabotage „mkdir ohne Modus"
    ließ am 25.10.2026 alle 63 Tests grün. Deshalb zeigt `BUCH_VORGABE` hier
    auf einen Pfad, den es noch nicht gibt.
    """
    monkeypatch.setattr(entwurfsbuch, "BUCH_VORGABE",
                        tmp_path / "state" / "falzmarke" / "entwuerfe.jsonl")
    assert not entwurfsbuch.BUCH_VORGABE.parent.exists()
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    lage = _entwurf(felder)
    assert lage.buch_grund == ""
    buch = entwurfsbuch.BUCH_VORGABE
    assert _rechte(buch) == 0o600, f"das Buch steht auf {oct(_rechte(buch))}"
    assert _rechte(buch.parent) == 0o700, f"der Ordner steht auf {oct(_rechte(buch.parent))}"


@nur_unix
def test_ein_buch_aus_einer_frueheren_fassung_wird_nachgezogen(monkeypatch, felder, umask_022):
    """Die Rechte zieht erst das Schreiben nach — vorhandene Zeilen bleiben."""
    _buch(_eintrag(900))
    buch = entwurfsbuch.BUCH_VORGABE
    os.chmod(buch, 0o644)
    assert _rechte(buch) == 0o644, "die Vorbedingung des Tests stimmt nicht"
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    assert _entwurf(felder).buch_grund == ""
    assert _rechte(buch) == 0o600
    assert len(entwurfsbuch.lesen({}).eintraege) == 2, \
        "beim Nachziehen ging eine Zeile verloren"


@nur_unix
def test_ein_symlink_an_der_stelle_des_buchs_wird_nicht_beschrieben(monkeypatch, felder,
                                                                   tmp_path):
    """`O_NOFOLLOW`: Sonst hängt die Zeile in der Datei, auf die der Link zeigt."""
    fremd = tmp_path / "fremde-datei"
    fremd.write_text("unberührt\n", encoding="utf-8")
    buch = entwurfsbuch.BUCH_VORGABE
    buch.parent.mkdir(parents=True, exist_ok=True)
    buch.symlink_to(fremd)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    lage = _entwurf(felder)
    assert lage.postfach is not None, "der Entwurf muss trotzdem im Postfach liegen"
    assert lage.buch_grund, "das Schreiben über einen Symlink ging durch"
    assert fremd.read_text(encoding="utf-8") == "unberührt\n"


def test_zu_alte_zeilen_verlassen_das_buch_beim_schreiben(monkeypatch, felder):
    """Aufbewahrung: `status` sieht 14 Tage, das Buch hält das Vierfache."""
    jetzt = datetime.now(timezone.utc)
    alt = jetzt - timedelta(days=entwurfsbuch.AUFBEWAHRUNG_TAGE + 1)
    frisch = jetzt - timedelta(days=1)
    _buch(_eintrag(700, zeit=alt), _eintrag(701, zeit=frisch),
          dict(_eintrag(702, zeit=frisch), zeit="irgendwann"))
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    assert _entwurf(felder).buch_grund == ""
    # Gemessen wird die Datei, nicht `lesen()`: Das übergeht eine Zeile ohne
    # lesbare Zeit (`:250`), sie steht aber weiter im Buch — und genau das ist
    # hier die Zusage.
    zeilen = [json.loads(z) for z in
              entwurfsbuch.BUCH_VORGABE.read_text(encoding="utf-8").splitlines()]
    uids = [z["uid"] for z in zeilen]
    assert "700" not in uids, "eine Zeile älter als die Aufbewahrung blieb stehen"
    assert "701" in uids and "702" in uids, f"eine Zeile wurde zu früh verworfen: {uids}"
    assert len(uids) == 3, f"erwartet: 701, 702 und der neue Eintrag; da sind {uids}"


def test_gegenprobe_ohne_aufbewahrung_bleibt_die_alte_zeile_stehen(monkeypatch, felder):
    """Die Probe nebenan muss anschlagen können."""
    monkeypatch.setattr(entwurfsbuch, "_ausduennen", lambda *a, **k: 0)
    jetzt = datetime.now(timezone.utc)
    _buch(_eintrag(700, zeit=jetzt - timedelta(days=entwurfsbuch.AUFBEWAHRUNG_TAGE + 1)))
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    assert _entwurf(felder).buch_grund == ""
    assert "700" in entwurfsbuch.BUCH_VORGABE.read_text(encoding="utf-8")


def _gespeichert_unter_neuer_uid(monkeypatch, tmp_path, fenstertext):
    """Gemessen 25.10.2026: Thunderbird speichert den offenen Entwurf als HTML unter
    neuer UID. Dessen Klartext taugt nicht als Vorlage, das Buch kennt die alte UID."""
    html = ("<p>Hallo Erika,</p><p>bitte die Stickdatei für S1 in Gold anlegen, alle Formate "
            "neu, und das Farbblatt auch in Gold.</p><p>Viele<br>Grüße</p><p>Paul</p>"
            "<p>Siluri · Kremser Str. 35 · Regensburg</p>")
    neu = nachricht(an=AN, betreff="Auftrag S1", text=None, html=html, von=VON,
                    datum=JETZT - timedelta(hours=1)), JETZT - timedelta(hours=1)
    server = _postfach(monkeypatch, entwuerfe=[neu])
    uid = server.ordner[ENTWUERFE][0].uid
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [_tag("gespeichert", 150, neu_uid=[uid])])
    _offen(monkeypatch, uid, text=fenstertext)
    bericht = _stand(profilordner=profil)
    assert not bericht.grund, bericht.grund
    (zustand,) = [z for z in bericht.zustaende if z.art == "offen"]
    return zustand


def test_neu_gespeichert_vergleicht_das_fenster_mit_dem_buch(monkeypatch, tmp_path):
    zustand = _gespeichert_unter_neuer_uid(monkeypatch, tmp_path, TEXT)
    assert (zustand.art, zustand.fenster_text_gleich) == ("offen", True)


def test_gegenprobe_neu_gespeichert_und_geaendert(monkeypatch, tmp_path):
    zustand = _gespeichert_unter_neuer_uid(
        monkeypatch, tmp_path, TEXT.replace("in Gold anlegen", "in Silber anlegen"))
    assert zustand.fenster_text_gleich is False


# ── Verlorene und unlesbare Zeilen (#411) ───────────────────────────────────
#
# ANLASS: Das Buch konnte Einträge verlieren oder unlesbar machen, und `status`
# meldete dann eine zu kleine Zahl statt eines Hinweises — „die Zeile ist weg“
# war von „es gab sie nie“ nicht zu unterscheiden. Jede Probe hier hat ihre
# Gegenprobe daneben, und jede Sabotage läuft einzeln.

def _unlesbar_hinweis(bericht) -> list[str]:
    return [h for h in bericht.hinweise if "unlesbar" in h]


def _kaputte_zeile(roh: str) -> None:
    """Hängt eine Zeile an, die kein JSON-Objekt ist — wie ein halber Schreibvorgang."""
    pfad = entwurfsbuch.BUCH_VORGABE
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as datei:
        datei.write(roh + "\n")


def test_eine_halbe_zeile_wird_gezaehlt_und_genannt(monkeypatch):
    """Die halb geschriebene Zeile aus #411: gezählt, nicht übergangen."""
    _postfach(monkeypatch)
    _buch(_eintrag(500))
    _kaputte_zeile('{"zeit": "2026-10-25T09:00:00+00:00", "konto": "order@example.de", "ui')
    bericht = _stand()
    assert bericht.unlesbar == 1 and bericht.im_buch == 1
    assert _unlesbar_hinweis(bericht) == [
        "1 Zeile im Entwurfsbuch ist unlesbar — was dort stand, fehlt im Abgleich"]
    assert any("1 Zeile im Entwurfsbuch ist unlesbar" in z
               for z in entwurfsbuch.zeilen(bericht)), "der Hinweis fehlt in der Ausgabe"


def test_gegenprobe_ein_heiles_buch_meldet_nichts(monkeypatch):
    """Die Probe nebenan muss anschlagen können: ohne kaputte Zeile kein Hinweis."""
    _postfach(monkeypatch)
    _buch(_eintrag(500))
    bericht = _stand()
    assert bericht.unlesbar == 0
    assert _unlesbar_hinweis(bericht) == []


def test_eine_zeile_ohne_konto_wird_gezaehlt(monkeypatch):
    _postfach(monkeypatch)
    zeile = _eintrag(501)
    del zeile["konto"]
    _buch(zeile)
    bericht = _stand()
    assert bericht.unlesbar == 1, "eine Zeile ohne Konto ging still verloren"
    assert _unlesbar_hinweis(bericht)


def test_eine_uid_die_keine_zahl_ist_wird_gezaehlt(monkeypatch):
    """Ergänzt `test_eine_kaputte_uid_im_buch_bricht_status_nicht_ab`: Sie bricht
    nicht ab — und sie verschwindet auch nicht mehr lautlos."""
    _postfach(monkeypatch)
    _buch(_eintrag("abc"))
    bericht = _stand()
    assert (bericht.unlesbar, bericht.im_buch) == (1, 0)
    assert _unlesbar_hinweis(bericht)


def test_mehrere_unlesbare_zeilen_stehen_im_plural(monkeypatch):
    _postfach(monkeypatch)
    _kaputte_zeile("kein json")
    _kaputte_zeile("[1, 2, 3]")
    bericht = _stand()
    assert bericht.unlesbar == 2
    assert _unlesbar_hinweis(bericht) == [
        "2 Zeilen im Entwurfsbuch sind unlesbar — was dort stand, fehlt im Abgleich"]


def test_eine_leere_zeile_ist_keine_beschaedigung(monkeypatch):
    """Ein Buch, das mit einem Zeilenumbruch endet, ist heil."""
    _postfach(monkeypatch)
    _buch(_eintrag(502))
    _kaputte_zeile("")
    assert _stand().unlesbar == 0


def test_das_unerreichbare_postfach_nennt_die_unlesbare_zeile_trotzdem(monkeypatch):
    """`NICHT GEPRÜFT` und „eine Zeile ist weg“ sind zwei verschiedene Lücken.

    Gerade wenn das Postfach schweigt, zählt, was das Buch noch weiß.
    """
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe({}, verbindungsfehler=OSError("nicht erreichbar")))
    _kaputte_zeile("kein json")
    bericht = _stand()
    assert bericht.grund, "die Vorbedingung des Tests stimmt nicht: das Postfach antwortet"
    # Gemessen wird die Ausgabe, nicht der Bericht: `zeilen()` stieg bei `grund` früh aus,
    # und der Hinweis stand im Objekt, aber in keiner Zeile (gefunden von Hand, 27.10.2026).
    gemeldet = entwurfsbuch.zeilen(bericht)
    assert gemeldet[0].startswith("NICHT GEPRÜFT"), gemeldet
    assert any("im Entwurfsbuch ist unlesbar" in z for z in gemeldet), gemeldet


def test_eine_unlesbare_tagebuchzeile_wird_genannt(monkeypatch, tmp_path):
    _postfach(monkeypatch)
    profil = _profil(tmp_path, [])
    pfad = profil / "Profiles" / "abc.default-release" / entwurfsbuch.TAGEBUCH
    pfad.write_text('{"art": "geoeffnet", "zeit": "2026-10-25T10:00:00+00:00"}\n{"art": "ge\n',
                    encoding="utf-8")
    bericht = _stand(profilordner=profil)
    assert any("Tagebuch der Entwurfsbrücke" in h and "unlesbar" in h
               for h in bericht.hinweise), bericht.hinweise


def _felder_mit_text(text: str) -> dict:
    """Die Felder, die `_zeile_bauen` liest — mit echtem Mailrumpf."""
    return {"roh": nachricht(an=AN, betreff="Auftrag S1", text=text, datum=JETZT, von=VON),
            "betreff": "Auftrag S1", "an": [AN], "kopie": [], "blindkopie": [],
            "fassung": "f0f0f0f0f0f0"}


def _zeile_fuer(text: str) -> str:
    zeile, grund = entwurfsbuch._zeile_bauen(_felder_mit_text(text), konto=VON,
                                             ordner="Entwürfe", uid="900", jetzt=JETZT)
    assert grund == "", grund
    return zeile


def test_eine_zeile_ueber_der_grenze_wird_am_text_gekappt():
    zeile = _zeile_fuer("Noch eine Zeile mit Inhalt.\n" * 4000)
    assert len(zeile.encode("utf-8")) <= entwurfsbuch.ZEILE_MAX
    wert = json.loads(zeile)
    assert wert["text_gekappt"] > len(wert["text"]) > 0, "gekappt wurde nicht oder alles"
    assert wert["betreff"] == "Auftrag S1" and wert["an"] == [AN], \
        "gekappt werden darf allein der Text"


def test_gegenprobe_eine_gewoehnliche_mail_wird_nicht_gekappt():
    """Die Probe nebenan muss anschlagen können: Unter der Grenze bleibt alles stehen."""
    wert = json.loads(_zeile_fuer(TEXT))
    assert "text_gekappt" not in wert
    assert wert["text"].strip() == TEXT.strip()


def test_die_beispielmails_bleiben_weit_unter_der_zeilengrenze():
    """`ZEILE_MAX` ist gemessen, nicht geraten (27.10.2026).

    Gemessen wird die Buchzeile, die aus dem Rumpf jeder Beispielmail entsteht:
    Der Text bestimmt ihre Länge, Betreff und Adressen sind klein. Wird der
    Abstand knapp, ist die Schranke neu zu begründen — nicht dieser Test zu
    lockern.
    """
    beispiele = sorted((Path(__file__).parents[1] / "examples" / "email").glob("*.md"))
    assert len(beispiele) >= 5, "die Beispielmails fehlen, die Messung liefe ins Leere"
    laengste = max(len(_zeile_fuer(p.read_text(encoding="utf-8")).encode("utf-8"))
                   for p in beispiele)
    assert laengste * 4 <= entwurfsbuch.ZEILE_MAX, (
        f"die längste Beispielmail ergibt {laengste} Bytes, die Schranke ist "
        f"{entwurfsbuch.ZEILE_MAX} — weniger als Faktor vier Luft")


def test_eine_lange_zeile_geht_in_einem_schreibvorgang_ins_buch(monkeypatch):
    """Die Zusage „eine Zeile kommt ganz oder nicht an“ hängt an einem `os.write`.

    Durch `os.fdopen(…, "a")` zerfiel eine Zeile über 8 KiB in mehrere Syscalls,
    die sich mit denen eines zweiten Laufs verschränken konnten (#411).
    """
    zeile = json.dumps({"text": "x" * 20000}, ensure_ascii=False) + "\n"
    aufrufe: list[int] = []
    echt = os.write

    def zaehlend(kennung, daten):
        aufrufe.append(len(daten))
        return echt(kennung, daten)

    buch = entwurfsbuch.BUCH_VORGABE
    buch.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os, "write", zaehlend)
    assert entwurfsbuch._anhaengen(buch, zeile) == ""
    assert aufrufe == [len(zeile.encode("utf-8"))], \
        f"die Zeile ging in {len(aufrufe)} Schreibvorgängen ins Buch: {aufrufe}"
    assert buch.read_text(encoding="utf-8") == zeile


class _Zaehlend(io.RawIOBase):
    """Zählt, in wie vielen Stücken eine Pufferschicht ihre Daten weitergibt."""

    def __init__(self):
        self.vorgaenge: list[int] = []

    def writable(self):
        return True

    def write(self, daten):
        self.vorgaenge.append(len(daten))
        return len(daten)


def _durch_den_wrapper(*zeilen: str) -> list[int]:
    roh = _Zaehlend()
    with io.TextIOWrapper(io.BufferedWriter(roh), encoding="utf-8") as datei:
        for zeile in zeilen:
            datei.write(zeile)
    return roh.vorgaenge


def _als_bytes(zeile: str) -> int:
    """Wie viele Bytes aus `zeile` werden, wenn sie durch den Wrapper geht.

    Der gemessene Wrapper läuft mit `newline=None` — so wie `os.fdopen(…, "a")`,
    der alte Schreibweg des Buchs. Dabei wird `\\n` zu `os.linesep`: unter
    Windows werden aus der 20013-Byte-Zeile 20014.
    """
    return len(zeile.replace("\n", os.linesep).encode("utf-8"))


def _zeilengrenzen_eingehalten(vorgaenge: list[int], laengen: list[int]) -> bool:
    """Endet jeder Schreibvorgang an einer Zeilengrenze?

    Mehrere Zeilen in einem Vorgang sind erlaubt, eine Zeile über zwei Vorgänge
    nicht — das ist die Eigenschaft, auf die es ankommt.
    """
    if sum(vorgaenge) != sum(laengen):
        return False
    grenzen: set[int] = set()
    stand = 0
    for laenge in laengen:
        stand += laenge
        grenzen.add(stand)
    stand = 0
    for vorgang in vorgaenge:
        stand += vorgang
        if stand not in grenzen:
            return False
    return True


def test_der_gepufferte_wrapper_war_nicht_der_verlustweg():
    """Nachgemessen am 28.10.2026, gegen den Wortlaut von #411.

    Der Vorgang sagt, über ~8 KiB zerfalle der Schreibvorgang in mehrere
    Syscalls, die sich verschränken könnten. Für diesen Schreibpfad trifft das
    nicht zu: `TextIOWrapper` über `BufferedWriter` gibt **keine Zeile
    zerstückelt** weiter, jeder Vorgang endet an einer Zeilengrenze. Gemessen
    werden die Klassen, durch die das Buch vor #411 schrieb
    (`os.fdopen(…, "a")`, also `newline=None`).

    Wie viele Zeilen in einen Vorgang gebündelt werden, ist dagegen nicht
    verlässlich — gemessen, nicht vermutet: bei einer kurzen Zeile vor einer
    langen liefern 3.12.9 und 3.13.12 zwei Vorgänge (`[17, 20013]`), 3.14.7
    einen einzigen (`[20030]`). Eine frühere Fassung dieses Tests schrieb die
    Bündelung von 3.14 fest und fiel darum in der CI auf allen drei Plattformen
    (Lauf 40641191943, Python 3.12).

    Genau deshalb hängt die Zusage an `os.write`: ein Syscall, sein Rückgabewert
    sagt, wie viele Bytes ankamen, und nichts davon an Pufferinterna. Der
    belegte Verlustweg ist das Ausdünnen — siehe die Probe mit zwei Läufen.
    """
    lang = json.dumps({"text": "x" * 20000}, ensure_ascii=False) + "\n"
    kurz = "eine kurze Zeile\n"

    assert _zeilengrenzen_eingehalten(_durch_den_wrapper(lang), [_als_bytes(lang)])
    assert _zeilengrenzen_eingehalten(
        _durch_den_wrapper(kurz, lang), [_als_bytes(kurz), _als_bytes(lang)]
    )

    # Gegenprobe: Die zwei Zusagen oben wären wertlos, wenn die Prüfung nie
    # fehlschlagen könnte. Eine Zeile über zwei Vorgänge — genau der Fall, den
    # #411 befürchtete — muss sie melden, ebenso eine unvollständig angekommene.
    ganz = _als_bytes(lang)
    assert not _zeilengrenzen_eingehalten([7000, ganz - 7000], [ganz])
    assert not _zeilengrenzen_eingehalten([ganz - 1], [ganz])


# ── Eine Antwort je Frage: Text gegen --json (#414) ─────────────────────────

def _belegt_stimmt_zusammen(bericht, aus=None) -> list[str]:
    """Zustände, bei denen Textzeile und `--json` über `belegt` auseinanderlaufen.

    Leer heißt einig. Verglichen wird je Eintrag, nicht über die ganze Ausgabe:
    Sonst deckte ein `BELEGT` an der falschen Zeile das Fehlen an der richtigen.
    `aus` nimmt die Textausgabe von außen — die Gegenprobe gibt eine verdrehte
    hinein, ohne dafür `entwurfsbuch.zeilen` auszutauschen.
    """
    aus = entwurfsbuch.zeilen(bericht) if aus is None else aus
    kopfzeilen = [z for z in aus[1:] if not z.startswith((" ", "HINWEIS"))]
    daten = entwurfsbuch.als_json(bericht)["entwuerfe"]
    assert len(kopfzeilen) == len(daten), (len(kopfzeilen), len(daten))
    return [e["zustand"] for zeile, e in zip(kopfzeilen, daten)
            if ("· BELEGT" in zeile) is not e["belegt"]]


def _zustand(art: str) -> entwurfsbuch.Zustand:
    """Ein Zustand dieser Art, bei dem beide Quellen „gesendet“ sagen.

    Sonst wäre `belegt` überall falsch, und der Vergleich unten prüfte nur
    Zeilen, in denen ohnehin kein `BELEGT` stünde.
    """
    return entwurfsbuch.Zustand(
        art, "Auftrag S1", (AN,), JETZT - timedelta(hours=3), "812",
        gesendet=(JETZT - timedelta(hours=1),),
        anders=(JETZT - timedelta(hours=1),) if art == "geloescht" else (),
        im_buch=True, tagebuch=(_tag("gesendet", 812),),
        nachfolger="813" if art == "ersetzt" else "")


def test_belegt_antwortet_in_text_und_json_gleich():
    """Abnahme #414: eine Antwort je Frage, für jede Art.

    Vorher hing „· BELEGT“ allein im Zweig `gesendet`, während `als_json` es
    für jeden Zustand meldete. Der Test läuft über alle Arten aus `KOPF`, damit
    eine neu hinzukommende nicht stillschweigend durchfällt.
    """
    bericht = entwurfsbuch.Bericht(
        VON, tuple(_zustand(art) for art in entwurfsbuch.KOPF),
        entwuerfe="Entwürfe", gesendet="Gesendet", papierkorb="Papierkorb")
    assert set(entwurfsbuch.KOPF) == {z.art for z in bericht.zustaende}
    assert _belegt_stimmt_zusammen(bericht) == []


def test_der_vergleich_schlaegt_an_wenn_beide_auseinanderlaufen():
    """Gegenprobe: Ohne sie könnte `_belegt_stimmt_zusammen` nie etwas melden.

    `geloescht` trägt nur einen Treffer mit anderem Text. Macht man daraus
    einen echten, wird `belegt` wahr — die Textzeile dieses Zustands nennt es
    dann auch, aber die Prüfung muss den umgekehrten Fall ebenso sehen.
    """
    einig = entwurfsbuch.Bericht(VON, (_zustand("gesendet"),), entwuerfe="Entwürfe",
                                 gesendet="Gesendet", papierkorb="Papierkorb")
    assert _belegt_stimmt_zusammen(einig) == []

    # Dieselbe Lage, aber die Textausgabe schweigt über `belegt`.
    stumm = [z.replace(" · BELEGT", "") for z in entwurfsbuch.zeilen(einig)]
    assert stumm != entwurfsbuch.zeilen(einig), "ohne Suffix wäre die Probe wirkungslos"
    assert _belegt_stimmt_zusammen(einig, stumm) == ["gesendet"]


def test_ein_liegender_entwurf_mit_zwei_quellen_nennt_belegt(monkeypatch, tmp_path):
    """Der Fall, der wirklich auseinanderlief — am echten Datenpfad.

    `geloescht` und `ersetzt`, die #414 nennt, können `belegt` gar nicht
    tragen: Sagt das Tagebuch „gesendet“, wird die Art `gesendet`
    (`entwurfsbuch.py`, Zweig über dem Papierkorb). Im liegend-Zweig gibt es
    diese Prüfung nicht — dort ist `schon_raus` mit `belegt` erreichbar, und
    genau dort fehlte das Wort.
    """
    server = _postfach(monkeypatch, entwuerfe=[_mail()],
                       gesendet=[_mail(zeit=JETZT - timedelta(hours=1))])
    profil = _profil(tmp_path, [_tag("gesendet", server.ordner[ENTWUERFE][0].uid)])
    bericht = _stand(profilordner=profil)
    (zustand,) = [z for z in bericht.zustaende if z.art == "schon_raus"]
    assert zustand.belegt is True
    (zeile,) = [z for z in entwurfsbuch.zeilen(bericht) if z.startswith("SCHON RAUS")]
    assert "nicht noch einmal senden · BELEGT" in zeile
    assert _belegt_stimmt_zusammen(bericht) == []


def test_das_tagebuch_erzwingt_gesendet_also_ist_geloescht_nie_belegt(monkeypatch, tmp_path):
    """Messung zur Aussage im Test darüber, statt einer Behauptung.

    Ein Entwurf, der nicht mehr liegt, dessen Fassung im Papierkorb steht und
    zu dem das Tagebuch „gesendet“ meldet: Er heißt `gesendet`, nicht
    `geloescht`. Darum ist `belegt` an einer `GELÖSCHT`-Zeile unerreichbar.

    `belegt` ist hier dennoch falsch, und das gehört zur Messung: In „Gesendet“
    liegt nichts: Das Tagebuch ist die einzige Quelle, und eine Quelle belegt
    nichts. Zwei Quellen zeigt der Test darüber.
    """
    _postfach(monkeypatch, papierkorb=[_mail(fassung="f0f0f0f0f0f0")])
    _buch(_eintrag(150))
    profil = _profil(tmp_path, [_tag("gesendet", 150)])
    bericht = _stand(profilordner=profil)
    zustand = _einziger(bericht)
    assert zustand.art == "gesendet"
    assert not [z for z in entwurfsbuch.zeilen(bericht) if z.startswith("GELÖSCHT")]
    assert zustand.belegt is False, "nur das Tagebuch sagt es — das ist eine Quelle"
    assert _belegt_stimmt_zusammen(bericht) == []


def test_ein_treffer_mit_anderem_text_belegt_nichts(monkeypatch, tmp_path):
    """Die Stelle, an der `belegt` die Art überhaupt braucht — gemessen, nicht geraten.

    Der Entwurf liegt noch, in „Gesendet“ steht nur derselbe Betreff mit anderem
    Text, und das Tagebuch sagt „gesendet“. Das sind zwei Quellen, aber nicht
    über diesen Entwurf: Er liegt ja. Ohne die Abfrage auf `art` in
    `Zustand.belegt` stünde hier `BELEGT`, und zwar in Text und `--json`
    gleichzeitig — der Vergleich oben bliebe stumm. Deshalb dieser Test.
    """
    neu = "Hallo Erika,\n\nkurze Änderung: Wir nehmen Silber statt Gold.\n\nGruß\nPaul\n"
    server = _postfach(monkeypatch, entwuerfe=[_mail()],
                       gesendet=[_mail(text=neu, zeit=JETZT - timedelta(hours=1))])
    profil = _profil(tmp_path, [_tag("gesendet", server.ordner[ENTWUERFE][0].uid)])
    bericht = _stand(profilordner=profil)
    zustand = _einziger(bericht)
    assert (zustand.art, zustand.gesendet) == ("wartet", ()), "sonst prüft der Test etwas anderes"
    assert zustand.anders and [t["art"] for t in zustand.tagebuch] == ["gesendet"]
    assert zustand.belegt is False
    assert "BELEGT" not in "".join(entwurfsbuch.zeilen(bericht))
    assert _belegt_stimmt_zusammen(bericht) == []


def test_die_tagebuchzahl_zaehlt_nur_diesen_absender(monkeypatch, tmp_path):
    """Abnahme #414: Die Zeile steht hinter einem Absender, die Zahl galt für alle.

    Das Tagebuch führt alle Konten des Thunderbird-Profils.
    """
    _postfach(monkeypatch, entwuerfe=[_mail()])
    _buch(_eintrag(150))
    fremd = _tag("gesendet", 900)
    fremd["ursprung"] = {**fremd["ursprung"], "konto": "wer@anders.example"}
    profil = _profil(tmp_path, [_tag("geoeffnet", 150), fremd, _tag("geschlossen", 150)])
    bericht = _stand(profilordner=profil)
    assert bericht.tagebuch == 2, "der fremde Eintrag darf nicht mitzählen"
    assert ", 2 Tagebucheinträge" in entwurfsbuch.zeilen(bericht)[0]


def test_schon_raus_sticht_offen_und_nennt_das_fenster(monkeypatch):
    """Abnahme #414: Dass der Text schon hinausging, ist die Nachricht.

    Vorher trug die Zeile `OFFEN`, obwohl beides zutraf; die Warnung stand nur
    dahinter. Das offene Fenster darf dabei nicht verschwinden.
    """
    server = _postfach(monkeypatch, entwuerfe=[_mail()],
                       gesendet=[_mail(zeit=JETZT - timedelta(hours=1))])
    _offen(monkeypatch, server.ordner[ENTWUERFE][0].uid)
    bericht = _stand()
    zustand = _einziger(bericht)
    assert zustand.art == "schon_raus"
    assert zustand.fenster is not None
    (zeile,) = [z for z in entwurfsbuch.zeilen(bericht) if z.startswith("SCHON RAUS")]
    assert "gerade im Fenster offen" in zeile
    assert "nicht noch einmal senden" in zeile


# ── Zwei Läufe zugleich ─────────────────────────────────────────────────────

KIND = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from falzmarke import entwurfsbuch
# Der zweite Lauf haengt nur an. Wuerde er auch ausduennen, schrieben beide
# Laeufe dieselbe Zwischendatei `entwuerfe.jsonl.neu` und zogen sie einander
# weg -- ein zweiter Schaden, der den Unterschied verdeckt, um den es hier geht.
entwurfsbuch._ausduennen = lambda *a, **k: 0
if os.environ.get("OHNE_SPERRE"):
    entwurfsbuch.fcntl = None
    entwurfsbuch.msvcrt = None
grund = entwurfsbuch._anhaengen(Path(sys.argv[2]), sys.argv[3] + "\\n")
sys.stderr.write(grund)
"""


def _zweiter_lauf(buch: Path, zeile: str, *, ohne_sperre: bool):
    """Startet einen echten zweiten Prozess, der dieselbe Zeile anhängt."""
    import subprocess

    umgebung = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if ohne_sperre:
        umgebung["OHNE_SPERRE"] = "1"
    skill = str(Path(entwurfsbuch.__file__).parents[1])
    return subprocess.Popen([sys.executable, "-c", KIND, skill, str(buch), zeile],
                            env=umgebung, stderr=subprocess.PIPE, text=True)


def _lauf_im_ausduennen(monkeypatch, *, ohne_sperre: bool) -> list[str]:
    """Ein Lauf hängt an, während der andere im Ausdünnen steht. Rückgabe: die UIDs.

    Die Reihenfolge ist erzwungen, nicht zufällig: Der erste Lauf hält in
    `os.replace` an — dem letzten Schritt des Ausdünnens — und startet dort den
    zweiten. Nur die Sperre kann den zweiten so lange warten lassen; ohne sie
    hängt er an das Buch an, das `os.replace` gleich darauf überschreibt (#411).
    """
    alt = JETZT - timedelta(days=entwurfsbuch.AUFBEWAHRUNG_TAGE + 1)
    _buch(_eintrag(700, zeit=alt))  # damit das Ausdünnen wirklich ersetzt
    buch = entwurfsbuch.BUCH_VORGABE
    zweiter = json.dumps(_eintrag(702), ensure_ascii=False)
    kinder = []
    echtes_replace = os.replace

    def anhalten(quelle, ziel):
        if not kinder:
            kinder.append(_zweiter_lauf(buch, zweiter, ohne_sperre=ohne_sperre))
            time.sleep(0.8)  # dem zweiten Lauf Zeit geben, es zu versuchen
        return echtes_replace(quelle, ziel)

    monkeypatch.setattr(os, "replace", anhalten)
    if ohne_sperre:
        monkeypatch.setattr(entwurfsbuch, "fcntl", None)
        monkeypatch.setattr(entwurfsbuch, "msvcrt", None)
    assert entwurfsbuch._anhaengen(buch, json.dumps(_eintrag(701), ensure_ascii=False) + "\n") \
        in ("", ("diese Plattform kennt keine Dateisperre — zwei Läufe zugleich "
                 "können eine Zeile kosten"))
    assert kinder, "das Ausdünnen hat nicht ersetzt — die Vorbedingung stimmt nicht"
    kinder[0].wait(timeout=30)
    monkeypatch.setattr(os, "replace", echtes_replace)
    zeilen, unlesbar = entwurfsbuch._jsonzeilen(buch)
    assert unlesbar == 0, "eine Zeile kam nicht ganz an"
    return [z["uid"] for z in zeilen]


@nur_unix
def test_zwei_laeufe_zugleich_verlieren_keine_zeile(monkeypatch):
    uids = _lauf_im_ausduennen(monkeypatch, ohne_sperre=False)
    assert "700" not in uids, "die alte Zeile blieb stehen — das Ausdünnen lief nicht"
    assert sorted(uids) == ["701", "702"], f"eine Zeile ging verloren: {uids}"


@nur_unix
def test_gegenprobe_ohne_sperre_geht_die_zeile_verloren(monkeypatch):
    """Die Sabotage läuft der Zusage entgegen: Ohne Sperre fehlt die Zeile.

    Derselbe Ablauf, derselbe zweite Lauf — nur die Dateisperre ist abgeschaltet.
    """
    uids = _lauf_im_ausduennen(monkeypatch, ohne_sperre=True)
    assert "702" not in uids, (
        "ohne Sperre blieb die Zeile des zweiten Laufs stehen — dann belegt die Probe "
        f"nebenan nichts: {uids}")
    assert uids == ["701"], f"ohne Sperre ging mehr verloren als die eine Zeile: {uids}"


@nur_unix
def test_eine_gehaltene_sperre_haelt_niemanden_auf(monkeypatch, tmp_path):
    """Nach der Frist wird ohne Sperre geschrieben, und der Grund geht zurück.

    Wie bei der Sperre beim Senden (ADR 0055, Punkt 5): Eine Prüfung, die hängt,
    darf den Menschen nicht aufhalten — dass sie nicht gegriffen hat, steht dann
    im Hinweis.
    """
    import fcntl

    monkeypatch.setattr(entwurfsbuch, "SPERRE_FRIST_S", 0.2)
    buch = tmp_path / "buch.jsonl"
    wache = os.open(tmp_path / "buch.jsonl.sperre", os.O_WRONLY | os.O_CREAT, 0o600)
    fcntl.flock(wache, fcntl.LOCK_EX)
    try:
        grund = entwurfsbuch._anhaengen(buch, '{"uid": "1"}\n')
    finally:
        fcntl.flock(wache, fcntl.LOCK_UN)
        os.close(wache)
    assert "gesperrt" in grund and "ohne Sperre" in grund, grund
    assert buch.read_text(encoding="utf-8") == '{"uid": "1"}\n', "die Zeile fehlt"


# ── Der ungewisse Lauf ──────────────────────────────────────────────────────

def _abgerissen(monkeypatch, felder):
    """Das Ablegen reißt hinter dem APPEND ab — der dritte Zustand (ADR 0051)."""
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe({ENTWUERFE: []}, append_fehler=TimeoutError("timed out")))
    lage = _entwurf(felder)
    assert lage.ungewiss, "die Vorbedingung stimmt nicht: der Lauf war nicht ungewiss"
    return lage


def test_ein_ungewisser_lauf_steht_im_buch(monkeypatch, felder):
    """Ohne diese Zeile wäre der Mailtext verloren, sobald der Entwurf aus
    „Entwürfe“ verschwindet — der Fall, für den ADR 0055 angetreten ist (#411)."""
    lage = _abgerissen(monkeypatch, felder)
    assert lage.buch_grund == "", lage.buch_grund
    stand = entwurfsbuch.lesen({})
    (eintrag,) = stand.ungewiss
    assert eintrag.uid == "", "nach dem Abriss gibt es keine UID, die zu belegen wäre"
    assert "abgebrochen" in eintrag.ungewiss
    assert "Lageplan" in eintrag.text, "der Text des Entwurfs fehlt"
    assert eintrag.betreff == "Sommerfest – Programm" and eintrag.an == ("paula@example.org",)
    assert (stand.eintraege, stand.unlesbar) == ([], 0), \
        "die ungewisse Zeile darf weder als Eintrag noch als unlesbar zählen"


def test_gegenprobe_ein_gelungener_lauf_ist_nicht_ungewiss(monkeypatch, felder):
    """Die Probe nebenan muss anschlagen können."""
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    assert _entwurf(felder).buch_grund == ""
    stand = entwurfsbuch.lesen({})
    assert stand.ungewiss == () and len(stand.eintraege) == 1


def test_status_nennt_den_ungewissen_lauf(monkeypatch, felder, tmp_path):
    _abgerissen(monkeypatch, felder)
    _postfach(monkeypatch)  # das Postfach antwortet wieder
    bericht = entwurfsbuch.abgleich(felder["absender"], umgebung={},
                                    profilordner=_profil(tmp_path, []))
    assert not bericht.grund, bericht.grund
    assert bericht.zustaende == (), "der ungewisse Lauf ist kein Zustand"
    (zeile,) = [z for z in entwurfsbuch.zeilen(bericht) if "ungewiss" in z]
    assert zeile.startswith("HINWEIS"), zeile
    assert "Sommerfest – Programm" in zeile and "paula@example.org" in zeile
    assert "ist offen" in zeile and "steht im Entwurfsbuch" in zeile
    (im_json,) = entwurfsbuch.als_json(bericht)["ungewiss"]
    assert im_json["betreff"] == "Sommerfest – Programm" and im_json["grund"]


def test_gegenprobe_ohne_ungewissen_lauf_nennt_status_keinen(monkeypatch, tmp_path):
    """Die Probe nebenan muss anschlagen können."""
    _postfach(monkeypatch)
    _buch(_eintrag(800))
    bericht = _stand(profilordner=_profil(tmp_path, []))
    assert bericht.ungewiss == ()
    assert not [z for z in entwurfsbuch.zeilen(bericht) if "ungewiss" in z]
    assert entwurfsbuch.als_json(bericht)["ungewiss"] == []


def test_scheitert_das_buch_beim_ungewissen_lauf_sagt_es_die_cli(monkeypatch, capsys,
                                                                 tmp_path):
    """Auch hier gilt ADR 0055, Punkt 1: Der Grund wird gemeldet, nicht verschwiegen.

    Der ganze Weg läuft echt — abgerissenes APPEND und ein Buchpfad, der sich
    nicht schreiben lässt (eine Datei als Elternordner).
    """
    (tmp_path / "datei").write_text("", encoding="utf-8")
    monkeypatch.setenv("FALZMARKE_ENTWURFSBUCH", str(tmp_path / "datei" / "buch.jsonl"))
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe({ENTWUERFE: []}, append_fehler=TimeoutError("timed out")))
    monkeypatch.setattr(oeffnen, "entwurf", _mit_attrappen(oeffnen.entwurf))
    quelle = tmp_path / "mail.md"
    quelle.write_text(MAIL, encoding="utf-8")
    falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE), "--oeffnen",
                    "-o", str(tmp_path / "mail")])
    fehler = capsys.readouterr().err
    assert "Entwurf ungewiss" in fehler
    assert "nicht im Entwurfsbuch" in fehler, fehler


# ── Der gekappte Text im Abgleich ───────────────────────────────────────────

def _gekappt_gegen_gesendet(monkeypatch, *, gekappt: bool):
    anders = TEXT.replace("in Gold", "in Silber")
    _postfach(monkeypatch, gesendet=[_mail(text=anders, zeit=JETZT - timedelta(hours=1))])
    zeile = _eintrag(600, text=TEXT[:40])
    if gekappt:
        zeile["text_gekappt"] = len(TEXT)
    _buch(zeile)
    return _einziger(_stand())


def test_ein_gekappter_text_belegt_kein_geaendert(monkeypatch):
    """Verglichen war nur der Anfang — „Text geändert“ wäre eine Behauptung (#411)."""
    zustand = _gekappt_gegen_gesendet(monkeypatch, gekappt=True)
    assert zustand.art == "gesendet"
    assert zustand.text_gekappt and zustand.text_gleich is None
    assert any("Text im Buch gekappt" in z for z in entwurfsbuch.zeilen(_stand()))


def test_gegenprobe_ohne_kappung_heisst_es_text_geaendert(monkeypatch):
    """Die Probe nebenan muss anschlagen können: Derselbe Fall, nur ungekappt."""
    zustand = _gekappt_gegen_gesendet(monkeypatch, gekappt=False)
    assert (zustand.art, zustand.text_gleich, zustand.text_gekappt) == ("gesendet", False, False)
    assert any("Text geändert" in z for z in entwurfsbuch.zeilen(_stand()))


# ── Tagebuch-Einträge, die an keinem Entwurf hängen (#420) ──────────────────
#
# ANLASS: Am 26.10.2026 trug genau ein Fensterpaar im Tagebuch dieses Rechners
# `uid: null` und `fassung: ""` — bei 117 Öffnungen mit UID. Die Versandzeile
# hing an keinem Eintrag im Entwurfsbuch, und zu sehen war das allein daran,
# dass unter dem Entwurf „Ging an …“ und BELEGT fehlten. Diese Zahl macht den
# Fall sichtbar, auch wenn er wiederkommt.

def _zuordnungshinweis(bericht) -> list[str]:
    return [h for h in bericht.hinweise if "weder UID noch Fassung" in h]


def test_ein_entwurf_ohne_uid_und_ohne_fassung_wird_gemeldet(monkeypatch, tmp_path):
    _postfach(monkeypatch)
    profil = _profil(tmp_path, [_tag("geoeffnet", None, fassung=""),
                                                _tag("gesendet", None, fassung="")])
    bericht = _stand(profilordner=profil)
    assert bericht.ohne_zuordnung == 2
    assert _zuordnungshinweis(bericht) == [
        "2 Tagebuch-Einträge zu einem Entwurf tragen weder UID noch Fassung — sie stehen "
        "unter keinem Entwurf; ab Entwurfsbrücke 0.3.7 nennt `uid_grund` im Tagebuch den Grund"]
    assert any("weder UID noch Fassung" in z for z in entwurfsbuch.zeilen(bericht)), (
        "der Hinweis fehlt in der Ausgabe")
    assert entwurfsbuch.als_json(bericht)["ohne_zuordnung"] == 2


def test_der_einzelne_eintrag_steht_im_singular(monkeypatch, tmp_path):
    _postfach(monkeypatch)
    profil = _profil(tmp_path, [_tag("gesendet", None, fassung="")])
    bericht = _stand(profilordner=profil)
    assert bericht.ohne_zuordnung == 1
    assert _zuordnungshinweis(bericht) == [
        "1 Tagebuch-Eintrag zu einem Entwurf trägt weder UID noch Fassung — er steht "
        "unter keinem Entwurf; ab Entwurfsbrücke 0.3.7 nennt `uid_grund` im Tagebuch den Grund"]


def test_gegenprobe_mit_uid_wird_nichts_gemeldet(monkeypatch, tmp_path):
    """Die Probe nebenan muss anschlagen können: derselbe Eintrag, nur mit UID."""
    _postfach(monkeypatch)
    profil = _profil(tmp_path, [_tag("gesendet", 150, fassung="")])
    bericht = _stand(profilordner=profil)
    assert bericht.ohne_zuordnung == 0 and _zuordnungshinweis(bericht) == []


def test_gegenprobe_mit_fassung_wird_nichts_gemeldet(monkeypatch, tmp_path):
    """Ohne UID, aber mit Fassung ist der Eintrag zuzuordnen — `_gehoert_dazu`
    tut genau das (`test_ohne_uid_entscheidet_die_fassung`)."""
    _postfach(monkeypatch)
    profil = _profil(tmp_path, [_tag("gesendet", None)])
    bericht = _stand(profilordner=profil)
    assert bericht.ohne_zuordnung == 0 and _zuordnungshinweis(bericht) == []


@pytest.mark.parametrize("typ", ["new", "reply"])
def test_gegenprobe_eine_neue_mail_und_eine_antwort_zaehlen_nicht(monkeypatch, tmp_path, typ):
    """Gemessen am Tagebuch dieses Rechners: `new` und `reply` tragen **nie** eine
    UID — es gibt keinen Entwurf, von dem sie käme. Zählte der Hinweis sie mit,
    stünde er unter jedem Postfach und sagte nichts mehr."""
    _postfach(monkeypatch)
    profil = _profil(tmp_path,
                     [_tag("geoeffnet", None, fassung="", typ=typ),
                      _tag("gesendet", None, fassung="", typ=typ)])
    bericht = _stand(profilordner=profil)
    assert bericht.ohne_zuordnung == 0 and _zuordnungshinweis(bericht) == []


def test_das_unerreichbare_postfach_nennt_den_eintrag_trotzdem(monkeypatch, tmp_path):
    """Was das Tagebuch weiß, weiß es unabhängig vom Postfach (#411, #420)."""
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe({}, verbindungsfehler=OSError("nicht erreichbar")))
    profil = _profil(tmp_path, [_tag("gesendet", None, fassung="")])
    bericht = _stand(profilordner=profil)
    assert bericht.grund, "die Vorbedingung stimmt nicht: das Postfach antwortet"
    assert any("weder UID noch Fassung" in z for z in entwurfsbuch.zeilen(bericht))


# ── Das Konto wird nicht aus der URI geraten (#410) ─────────────────────────
#
# Der Autoritätsteil einer `imap-message://`-URI trägt den IMAP-Anmeldenamen,
# nicht die Adresse. `LOGIN_FREMD` ist der Fall, der die alte Teilketten-Prüfung
# `adresse in ziel` nie treffen konnte: ein Login ohne jede Ähnlichkeit zur
# Adresse, wie ihn Telekom-Aliasse, Uni-Kennungen und `m0123456` bei 1&1 haben.
#
# Die Annahme über die URI-Form schrumpft damit auf das Stück, das doppelt
# belegt ist: `#<uid>` am Ende. Dasselbe Muster steht im Add-on, und
# `tests/test_entwurfsbruecke.py` hält beide Seiten gleich — Soll und Ist kommen
# also **nicht** mehr aus derselben Quelle, anders als beim alten Vergleich,
# dessen einzige Festlegung diese Testdatei selbst war.
LOGIN_FREMD = "imap-message://m0123456@imap.example.de/Entw&APw-rfe#{uid}"
LOGIN_EIGEN = "imap-message://order%40example.de@127.0.0.1/Entw&APw-rfe#{uid}"


def _fenster(uid, uri=LOGIN_FREMD, **felder) -> dict:
    return {"titel": "Verfassen: Auftrag S1", "betreff": "Auftrag S1",
            "draft_id": uri.format(uid=uid), **felder}


def _mit_fenstern(monkeypatch, *fenster) -> BrueckenAttrappe:
    attrappe = BrueckenAttrappe({"ok": True, "fenster": list(fenster)})
    monkeypatch.setattr(bruecke, "VERBINDEN", attrappe)
    return attrappe


def test_ein_konto_mit_fremdem_login_erreicht_offen(monkeypatch):
    """Der Fund von #410: `OFFEN` hing an einer Teilkette der IMAP-URI.

    Heißt der Login `m0123456`, während die Adresse `order@example.de` ist, war
    `adresse in ziel` immer falsch — der Entwurf stand in einem Fenster und hieß
    trotzdem `WARTET`. Jetzt entscheidet, was das Add-on meldet.
    """
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    uid = server.ordner[ENTWUERFE][0].uid
    _mit_fenstern(monkeypatch, _fenster(uid, identitaet=VON))
    assert _einziger(_stand()).art == "offen"


def test_ein_fremdes_konto_wird_nicht_offen_weil_die_uri_die_adresse_enthaelt(monkeypatch):
    """Die andere Richtung desselben Funds, und sie ist die gefährlichere.

    Die Teilkette traf auch ein fremdes Konto, dessen URI die eigene Adresse
    als Teilstück trug. Dann hätte ein Entwurf dieses Kontos `OFFEN` geheißen,
    obwohl das Fenster einem anderen Absender gehört.
    """
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    uid = server.ordner[ENTWUERFE][0].uid
    _mit_fenstern(monkeypatch, _fenster(uid, uri=LOGIN_EIGEN, identitaet="fremd@example.net"))
    assert _einziger(_stand()).art == "wartet"


def test_ohne_gemeldete_identitaet_traegt_die_uid_allein(monkeypatch):
    """Ein Add-on vor 0.3.0 — oder ein Fenster, das sich nicht lesen ließ.

    Dann fehlt `identitaet`, und die UID ist der einzige Anker. Sie trägt: Die
    Liste wird je Konto gegen dessen Entwürfe-Ordner abgeglichen. Die Adresse in
    der URI darf hier nicht mehr ausschließen, sonst wäre der Fund nur um eine
    Fassung verschoben.
    """
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    uid = server.ordner[ENTWUERFE][0].uid
    _mit_fenstern(monkeypatch, _fenster(uid, live=False))
    assert _einziger(_stand()).art == "offen"


def test_bei_zwei_fenstern_derselben_uid_entscheidet_die_gemeldete_identitaet(monkeypatch):
    """Mehrdeutigkeit, und zwar die einzige, die übrig bleibt.

    Zwei Fenster melden dieselbe UID; eines nennt seine Identität, das andere
    nicht. Gewählt wird das gemeldete — es ist das einzige, das etwas über das
    Konto aussagt. Geprüft am Betreff, nicht an der Zahl der Fenster: Sonst
    stünde hier, wie viele Einträge die Attrappe liefert, und nicht, welcher
    genommen wurde.
    """
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    uid = server.ordner[ENTWUERFE][0].uid
    _mit_fenstern(monkeypatch,
                  _fenster(uid, uri=LOGIN_EIGEN, betreff="ohne Meldung"),
                  _fenster(uid, identitaet=VON, betreff="mit Meldung"))
    gewaehlt = entwurfsbuch.fenster_des_kontos(
        [_fenster(uid, uri=LOGIN_EIGEN, betreff="ohne Meldung"),
         _fenster(uid, identitaet=VON, betreff="mit Meldung")], VON)
    assert gewaehlt[str(uid)]["betreff"] == "mit Meldung"


def test_ein_fenster_ohne_uid_in_der_uri_zaehlt_nicht(monkeypatch):
    """Ohne `#<uid>` ist nicht zu sagen, welcher Entwurf gemeint ist.

    Gegenprobe zur gelockerten Zuordnung: Dass die Adresse nicht mehr
    ausschließt, heißt nicht, dass jedes Fenster zählt.
    """
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    _mit_fenstern(monkeypatch, {"titel": "Verfassen", "betreff": "neu",
                                "draft_id": "", "identitaet": VON})
    assert _einziger(_stand()).art == "wartet"
    assert server.ordner[ENTWUERFE]


# ── Das Tagebuch kommt aus dem Profil des Sockets (#410) ────────────────────
#
# Vorher las `tagebuch()` stur das Standardprofil, während `bruecke.socketpfad`
# `FALZMARKE_BRUECKE_SOCKET` folgte. Bei gesetztem Schalter antwortete das
# Add-on damit aus Profil B, während hier Profil A gelesen wurde: `BELEGT`
# konnte nicht entstehen, `gesperrt` und `gesendet` blieben unsichtbar, und der
# einzige Hinweis lautete „kein Tagebuch" — was nach einem zu alten Add-on
# klingt, nicht nach dem falschen Profil.

def _zwei_profile(tmp_path, *, in_a=True, in_b=True) -> tuple[Path, Path, Path]:
    """Thunderbird-Ordner, Profil A (Standard) und Profil B (Socket)."""
    ordner = tmp_path / "Thunderbird"
    a, b = ordner / "Profiles" / "aaa.default-release", ordner / "Profiles" / "bbb.zweites"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (ordner / "profiles.ini").write_text(
        "[Install1]\nDefault=Profiles/aaa.default-release\n", encoding="utf-8")
    for profil, da, woher in ((a, in_a, "A"), (b, in_b, "B")):
        if da:
            (profil / entwurfsbuch.TAGEBUCH).write_text(
                json.dumps({"art": "geoeffnet", "zeit": "2026-10-25T11:00:00.000Z",
                            "ursprung": {"konto": VON, "betreff": f"aus {woher}"}}) + "\n",
                encoding="utf-8")
    (b / bruecke.SOCKET_DATEI).write_text("", encoding="utf-8")
    return ordner, a, b


def _betreffe(eintraege) -> list[str]:
    return [(e.get("ursprung") or {}).get("betreff", "") for e in eintraege]


def test_das_tagebuch_kommt_aus_dem_profil_des_sockets(monkeypatch, tmp_path):
    """Der Schalter bestimmt das Profil, und zwar für beide Seiten."""
    ordner, _, b = _zwei_profile(tmp_path)
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER", ordner)
    eintraege, grund = entwurfsbuch.tagebuch(
        umgebung={"FALZMARKE_BRUECKE_SOCKET": str(b / bruecke.SOCKET_DATEI)})
    assert not grund
    assert _betreffe(eintraege) == ["aus B"]


def test_gegenprobe_ohne_schalter_bleibt_es_das_standardprofil(monkeypatch, tmp_path):
    """Dasselbe Verzeichnis, nur ohne Schalter — und ein anderes Ergebnis.

    Die Gegenprobe zur ersten: Ohne sie wäre nicht zu sehen, ob der Schalter
    wirkt oder ob B schon vorher gelesen wurde. Zwei Läufe, zwei verschiedene
    Betreffe.
    """
    ordner, _, _ = _zwei_profile(tmp_path)
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER", ordner)
    eintraege, grund = entwurfsbuch.tagebuch(umgebung={})
    assert not grund
    assert _betreffe(eintraege) == ["aus A"]


def test_fehlt_das_tagebuch_nennt_der_hinweis_das_gelesene_profil(monkeypatch, tmp_path):
    """Liegt im Profil des Sockets keines, muss der Hinweis das Profil nennen.

    Sonst beantwortet er die Frage nicht, die er aufwirft: Es gibt hier zwei
    Profile, und eines trägt ein Tagebuch. „Kein Tagebuch" allein schickt den
    Leser zum Add-on, statt zum Profil.
    """
    ordner, _, b = _zwei_profile(tmp_path, in_b=False)
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER", ordner)
    eintraege, grund = entwurfsbuch.tagebuch(
        umgebung={"FALZMARKE_BRUECKE_SOCKET": str(b / bruecke.SOCKET_DATEI)})
    assert eintraege == []
    assert b.name in grund and "Entwurfsbrücke ab 0.2.0" in grund


def test_ohne_profil_bleibt_der_grund_bei_der_alten_aussage(monkeypatch, tmp_path):
    """Kein Profil heißt weiter „kein Standardprofil", nicht „kein Socket".

    Für den Leser ist das Profil die Sache, die fehlt; der Socket ist nur der
    Weg, auf dem es bestimmt wird.
    """
    leer = tmp_path / "ohne"
    leer.mkdir()
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER", leer)
    eintraege, grund = entwurfsbuch.tagebuch(umgebung={})
    assert eintraege == [] and "kein Thunderbird-Standardprofil" in grund
