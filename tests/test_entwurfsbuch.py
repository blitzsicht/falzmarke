"""Was aus einem Postfach-Entwurf wurde — Entwurfsbuch und `falzmarke status` (ADR 0055).

ANLASS (25.10.2026): „Die Entwürfe senden, falls noch nicht geschehen“ — und
die Frage, ob eine Mail schon raus ist, ob sie gelöscht oder vor dem Senden
geändert wurde, ging immer wieder an den Menschen. `status` beantwortet sie aus
dem Postfach, dem Entwurfsbuch und dem Tagebuch der Entwurfsbrücke.

Kein Test hier öffnet eine Verbindung. Das Postfach ist die Attrappe aus
`imap_attrappe.py`; sie wirft bei jedem Befehl, der etwas ändern würde.
"""

from __future__ import annotations

import json
import os
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
    (eintrag,) = entwurfsbuch.lesen({})
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
    neu, alt = entwurfsbuch.lesen({})
    assert neu.blindkopie == ("archiv@example.de",)
    assert alt.blindkopie is None, "ohne Feld ist das Bcc unbekannt, nicht leer"


def test_ohne_postfach_entwurf_kein_eintrag(monkeypatch, felder):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe(
        verbindungsfehler=ConnectionRefusedError(61, "aus")))
    lage = _entwurf(felder)
    assert lage.postfach is None
    assert entwurfsbuch.lesen({}) == []


def test_abgeschaltet_steht_nichts_im_buch_und_der_grund_kommt_zurueck(monkeypatch, felder):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({ENTWUERFE: []}))
    lage = _entwurf(felder, {"DISPLAY": ":0", "FALZMARKE_ENTWURFSBUCH": "nie"})
    assert lage.postfach is not None
    assert "FALZMARKE_ENTWURFSBUCH=nie" in lage.buch_grund
    assert entwurfsbuch.lesen({}) == []


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


def _tag(art, uid, *, fassung="f0f0f0f0f0f0", **mehr) -> dict:
    return {"zeit": (JETZT - timedelta(hours=1)).isoformat(), "art": art,
            "ursprung": {"konto": VON, "uid": uid, "fassung": fassung}, **mehr}


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
               "anhaenge": ["Lageplan.pdf"], "text": TEXT, "ungespeichert": False, **fenster}
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
    assert "ungespeichert" not in zeile


def test_gegenprobe_ein_im_fenster_geaenderter_text_faellt_auf(monkeypatch):
    server = _postfach(monkeypatch, entwuerfe=[_mail()])
    _offen(monkeypatch, server.ordner[ENTWUERFE][0].uid,
           text=TEXT.replace("in Gold anlegen", "in Silber anlegen"), ungespeichert=True)
    bericht = _stand()
    assert _einziger(bericht).fenster_text_gleich is False
    zeile = _fensterzeile(bericht)
    assert "Text geändert" in zeile and "ungespeichert" in zeile


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
    assert len(entwurfsbuch.lesen({})) == 2, "beim Nachziehen ging eine Zeile verloren"


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
