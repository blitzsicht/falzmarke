"""Überholte Entwürfe in den Papierkorb (#425, ADR 0062).

ANLASS (02.11.2026): Fall 1, ein gesendeter Entwurf blieb liegen. Fall 2, die alte
Textfassung lag als `WARTET`, die neue war längst hinaus. Beide räumte der
Betreiber mit einem Einmalskript weg. Dieses Modul nimmt ihm das ab.

Das Risiko liegt in der Gegenrichtung: Ein Entwurf, der noch gebraucht wird,
verschwindet ungefragt. Deshalb steht je Sperre ein Fall, der zeigt, dass sie
ihn hält, und dass er ohne sie durchginge. Die Sperren liegen als Liste in
`entwurfsablage.SPERREN`; die Tests nehmen je eine heraus.

Kein Test öffnet eine Verbindung. Ohne `verschieben_erlaubt=True` wirft die
Attrappe bei `SELECT` und `UID MOVE`.
"""

from __future__ import annotations

import ast
import json
from datetime import timedelta
from pathlib import Path

import pytest
from bruecke_attrappe import BrueckenAttrappe
from conftest import PROFILE
from falzmarke import bruecke, entwurfsablage, entwurfsbuch, oeffnen, postfach
from falzmarke import cli as falzmarke
from imap_attrappe import ImapAttrappe, nachricht
from test_ablage import _befehlswoerter
from test_entwurfsbuch import (
    AN,
    ENTWUERFE,
    GESENDET,
    JETZT,
    PAPIERKORB,
    TEXT,
    VON,
    _eintrag,
    _mit_attrappen,
    _profil,
)

ALT, NEU = "aaaaaaaaaaaa", "bbbbbbbbbbbb"
NEUER_TEXT = ("Hallo Erika,\n\nbitte die Stickdatei für S1 doch in Silber anlegen, alle Formate "
              "neu, und das Farbblatt auch in Silber.\n\nViele Grüße\nPaul\n")
ANGELEGT = JETZT - timedelta(hours=3)
RAUS = JETZT - timedelta(hours=1)


@pytest.fixture(autouse=True)
def _keine_offenen_fenster(monkeypatch):
    monkeypatch.setattr(bruecke, "VERBINDEN", BrueckenAttrappe({"ok": True, "fenster": []}))


def _server(monkeypatch, entwuerfe=(), gesendet_=(), *, erlaubt=True, sonder=None,
            faehigkeiten=("IMAP4REV1", "UIDPLUS", "MOVE")) -> ImapAttrappe:
    attrappe = ImapAttrappe(
        {ENTWUERFE: list(entwuerfe), GESENDET: list(gesendet_), PAPIERKORB: []},
        sonder=sonder or {"INBOX": "", GESENDET: "\\Sent", ENTWUERFE: "\\Drafts",
                          PAPIERKORB: "\\Trash"},
        verschieben_erlaubt=erlaubt, faehigkeiten=faehigkeiten)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    return attrappe


def _mail(*, text=TEXT, betreff="Auftrag S1", zeit=ANGELEGT, fassung=ALT, an=AN, kennung=None):
    kopf = {"X-Falzmarke-Fassung": fassung} if fassung else {}
    return (nachricht(an=an, betreff=betreff, text=text, datum=zeit, von=VON, kopf=kopf,
                      kennung=kennung), zeit)


def _buch(*eintraege: dict, kaputt: bool = False) -> None:
    pfad = entwurfsbuch.BUCH_VORGABE
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as datei:
        for eintrag in eintraege:
            datei.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        if kaputt:
            datei.write("{kein json\n")


def _gesendet_zeile(uid, *, fassung=ALT, message_id="", zeit=RAUS, an=(AN,),
                    betreff="Auftrag S1") -> dict:
    return {"zeit": zeit.isoformat(), "art": "gesendet", "message_id": message_id,
            "an": list(an), "kopie": [], "blindkopie": [],
            "ursprung": {"typ": "draft", "konto": VON, "uid": uid, "fassung": fassung,
                         "betreff": betreff}}


def _lauf(profil=None, *, machen=True) -> entwurfsablage.Bericht:
    return entwurfsablage.raeume_auf(VON, machen=machen, jetzt=JETZT, umgebung={},
                                     profilordner=profil)


def _stand(profil=None) -> entwurfsbuch.Bericht:
    return entwurfsbuch.abgleich(VON, jetzt=JETZT, umgebung={}, profilordner=profil)


def _uids(attrappe, ordner) -> list[str]:
    return [str(n.uid) for n in attrappe.ordner[ordner]]


def _fassung_neu(zeit=ANGELEGT + timedelta(hours=1), fassung=NEU) -> dict:
    """Die gesendete Fassung im Buch: „neuer“ hängt an ihrer Zeit, nicht an der Sendezeit."""
    return _eintrag(999, zeit=zeit, fassung=fassung, text=NEUER_TEXT)


def _fall1(monkeypatch, tmp_path, *, tagebuch_mehr=(), mail_mehr=None, gesendet_mail=None,
           buch_mehr=None):
    """Fall 1 aus #425: gesendet, Tagebuch ohne `message_id`, Entwurf liegt noch."""
    server = _server(monkeypatch, [_mail(**(mail_mehr or {}))],
                     [gesendet_mail or _mail(zeit=RAUS, fassung="", kennung="<a@b>")])
    uid = server.ordner[ENTWUERFE][0].uid
    _buch({**_eintrag(uid, zeit=ANGELEGT, fassung=ALT), **(buch_mehr or {})})
    return server, uid, _profil(tmp_path, [_gesendet_zeile(uid), *tagebuch_mehr])


def _fall2(monkeypatch, tmp_path, *, gesendet_mail=None, tagebuch=None, mail_mehr=None,
           buch=True, buch_mehr=None, kaputt=False):
    """Fall 2 aus #425: Eine neuere Fassung ging hinaus, die alte liegt noch."""
    server = _server(monkeypatch, [_mail(**(mail_mehr or {}))],
                     [gesendet_mail or _mail(text=NEUER_TEXT, zeit=RAUS, fassung="",
                                             kennung="<neu@b>")])
    uid = server.ordner[ENTWUERFE][0].uid
    if buch:
        _buch({**_eintrag(uid, zeit=ANGELEGT, fassung=ALT), **(buch_mehr or {})}, kaputt=kaputt)
    _buch(_fassung_neu())
    profil = _profil(tmp_path, [_gesendet_zeile(999, fassung=NEU, message_id="<neu@b>")]
                     if tagebuch is None else tagebuch)
    return server, uid, profil


# ── Was weg darf ────────────────────────────────────────────────────────────

def test_fall1_gesendet_mit_leerer_message_id_geht_in_den_papierkorb(monkeypatch, tmp_path):
    """Genau die Tagebuchzeile vom 02.11.2026: `message_id` leer, Zuordnung über die UID."""
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    bericht = _lauf(profil)
    assert bericht.verschoben == (str(uid),) and not bericht.grund
    assert bericht.zuege[0].regel == entwurfsablage.SCHON_RAUS
    assert _uids(server, ENTWUERFE) == [] and len(server.ordner[PAPIERKORB]) == 1


def test_fall2_neuere_fassung_gesendet_geht_in_den_papierkorb(monkeypatch, tmp_path):
    server, uid, profil = _fall2(monkeypatch, tmp_path)
    bericht = _lauf(profil)
    assert bericht.verschoben == (str(uid),)
    assert bericht.zuege[0].regel == entwurfsablage.NEUERE_FASSUNG
    assert len(server.ordner[PAPIERKORB]) == 1


def test_fall2_auch_wenn_der_server_die_message_id_ersetzt(monkeypatch, tmp_path):
    """outlook.de: Im Gesendet-Ordner steht eine andere `Message-ID` als im Tagebuch.

    Echt gemessen am Anlass selbst: Die Mail heißt dort `<PA1P…OUTLOOK.COM>`, das
    Tagebuch nennt `<bc7881c0-…@outlook.de>`, und statt `AW:` steht `Re:`.
    """
    _s, uid, profil = _fall2(
        monkeypatch, tmp_path,
        mail_mehr={"betreff": "AW: Küche"},
        buch_mehr={"betreff": "AW: Küche"},
        gesendet_mail=_mail(text=NEUER_TEXT, zeit=RAUS, fassung="", betreff="Re: Küche",
                            kennung="<umgeschrieben@server>"),
        tagebuch=[_gesendet_zeile(999, fassung=NEU, message_id="<anders@tagebuch>",
                                  betreff="AW: Küche", zeit=RAUS + timedelta(seconds=9))])
    assert _lauf(profil).verschoben == (str(uid),)


def test_gegenprobe_ohne_zweiten_anker_bliebe_der_outlook_fall_liegen(monkeypatch, tmp_path):
    _s, _uid, profil = _fall2(
        monkeypatch, tmp_path,
        gesendet_mail=_mail(text=NEUER_TEXT, zeit=RAUS, fassung="", kennung="<x@server>"),
        tagebuch=[_gesendet_zeile(999, fassung=NEU, message_id="<y@tagebuch>")])
    monkeypatch.setattr(entwurfsbuch, "tagebuch_fassungen", lambda *_a: frozenset())
    assert _lauf(profil).verschoben == ()


def test_ohne_machen_bewegt_sich_nichts_aber_der_plan_steht(monkeypatch, tmp_path):
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    bericht = _lauf(profil, machen=False)
    assert [z.uid for z in bericht.zuege] == [str(uid)] and bericht.verschoben == ()
    assert _uids(server, ENTWUERFE) == [str(uid)] and not server.befehle("UID MOVE")
    assert "mit --machen verschieben" in "\n".join(entwurfsablage.zeilen(bericht))


# ── Die Sperren, je eine ────────────────────────────────────────────────────

def _offenes_fenster(uid):
    return BrueckenAttrappe({"ok": True, "fenster": [
        {"titel": "Verfassen", "betreff": "Auftrag S1",
         "draft_id": f"imap-message://order%40example.de@127.0.0.1/Entw&APw-rfe#{uid}"}]})


def _aufbau_offen(monkeypatch, tmp_path):
    """`schon_raus` sticht `offen`: Der Zustand allein würde das Fenster nicht sehen."""
    _s, uid, profil = _fall1(monkeypatch, tmp_path)
    monkeypatch.setattr(bruecke, "VERBINDEN", _offenes_fenster(uid))
    return profil


def _aufbau_ohne_fassung(monkeypatch, tmp_path):
    return _fall2(monkeypatch, tmp_path, mail_mehr={"fassung": ""},
                  buch_mehr={"fassung": ""})[2]


def _aufbau_nicht_im_buch(monkeypatch, tmp_path):
    return _fall2(monkeypatch, tmp_path, buch=False)[2]


def _aufbau_gespeichert(monkeypatch, tmp_path):
    server = _server(monkeypatch, [_mail()], [_mail(text=NEUER_TEXT, zeit=RAUS, fassung="",
                                                    kennung="<neu@b>")])
    uid = server.ordner[ENTWUERFE][0].uid
    _buch(_eintrag(uid, zeit=ANGELEGT, fassung=ALT), _fassung_neu())
    return _profil(tmp_path, [
        _gesendet_zeile(999, fassung=NEU, message_id="<neu@b>"),
        {"zeit": ANGELEGT.isoformat(), "art": "gespeichert", "neu_uid": [],
         "ursprung": {"typ": "draft", "konto": VON, "uid": uid, "fassung": ALT}}])


def _aufbau_gekappt(monkeypatch, tmp_path):
    return _fall2(monkeypatch, tmp_path, buch_mehr={"text_gekappt": 40000})[2]


def _aufbau_text_weicht_ab(monkeypatch, tmp_path):
    return _fall2(monkeypatch, tmp_path, buch_mehr={
        "text": "Hallo Erika,\n\nganz etwas anderes als das, was jetzt im Entwurf liegt.\n"})[2]


def _aufbau_buch_unlesbar(monkeypatch, tmp_path):
    return _fall2(monkeypatch, tmp_path, kaputt=True)[2]


def _aufbau_tagebuch_unlesbar(monkeypatch, tmp_path):
    profil = _fall2(monkeypatch, tmp_path)[2]
    datei = next(profil.glob("Profiles/*/" + entwurfsbuch.TAGEBUCH))
    with datei.open("a", encoding="utf-8") as ziel:
        ziel.write("{abgerissene Zeile\n")
    return profil


def _aufbau_fenster_ungeprueft(monkeypatch, tmp_path):
    profil = _fall2(monkeypatch, tmp_path)[2]
    monkeypatch.setattr(bruecke, "VERBINDEN",
                        BrueckenAttrappe({"ok": False, "fehler": "befehl_unbekannt"}))
    return profil


SPERRFAELLE = [("offen", _aufbau_offen), ("ohne_fassung", _aufbau_ohne_fassung),
               ("nicht_im_buch", _aufbau_nicht_im_buch), ("gespeichert", _aufbau_gespeichert),
               ("gekappt", _aufbau_gekappt), ("text_weicht_ab", _aufbau_text_weicht_ab),
               ("beleg_unlesbar", _aufbau_buch_unlesbar),
               ("beleg_unlesbar", _aufbau_tagebuch_unlesbar),
               ("fenster_ungeprueft", _aufbau_fenster_ungeprueft)]


def test_jede_sperre_hat_ihren_fall():
    """Sonst könnte eine neue Sperre ohne Gegenprobe in die Liste rutschen."""
    assert {n for n, _ in entwurfsablage.SPERREN} == {n for n, _ in SPERRFAELLE}


@pytest.mark.parametrize(("sperre", "aufbau"), SPERRFAELLE,
                         ids=[a.__name__ for _, a in SPERRFAELLE])
def test_die_sperre_haelt_den_entwurf_und_nennt_den_grund(sperre, aufbau, monkeypatch, tmp_path):
    profil = aufbau(monkeypatch, tmp_path)
    server = postfach.IMAP_KLASSE
    bericht = _lauf(profil)
    assert bericht.verschoben == () and not bericht.grund
    assert [r.sperre for r in bericht.bleibt] == [sperre]
    assert bericht.bleibt[0].grund in "\n".join(entwurfsablage.zeilen(bericht))
    assert not server.befehle("UID MOVE")


@pytest.mark.parametrize(("sperre", "aufbau"), SPERRFAELLE,
                         ids=[a.__name__ for _, a in SPERRFAELLE])
def test_gegenprobe_ohne_die_sperre_ginge_der_entwurf_durch(sperre, aufbau, monkeypatch, tmp_path):
    """HANDBOOK §2.6: Jede Sperre allein trägt ihren Fall.

    Am Plan (`bewerte`) geprüft, nicht am Lauf: `offen` und `fenster_ungeprueft`
    werden vor dem Zug ein zweites Mal gefragt, und die zweite Prüfung verdeckte
    sonst die erste. Die zweite hat ihre eigenen Tests weiter unten.
    """
    profil = aufbau(monkeypatch, tmp_path)
    stand = _stand(profil)
    # Die gesendete Fassung (UID 999) steht auch im Buch, liegt aber nicht mehr.
    (zustand,) = [z for z in stand.zustaende if z.art in ("wartet", "offen", "schon_raus")]
    assert isinstance(entwurfsablage.bewerte(zustand, stand), entwurfsablage.Bleibt)
    monkeypatch.setattr(entwurfsablage, "SPERREN", tuple(
        (n, s) for n, s in entwurfsablage.SPERREN if n != sperre))
    assert isinstance(entwurfsablage.bewerte(zustand, stand), entwurfsablage.Zug)


# ── Was keine Regel öffnet ──────────────────────────────────────────────────

def _bleibt(profil, sperre) -> None:
    bericht = _lauf(profil)
    assert bericht.verschoben == ()
    assert [r.sperre for r in bericht.bleibt] == [sperre]
    assert not postfach.IMAP_KLASSE.befehle("UID MOVE")


def test_wartet_ohne_gesendeten_nachfolger_bleibt(monkeypatch, tmp_path):
    server = _server(monkeypatch, [_mail()])
    _buch(_eintrag(server.ordner[ENTWUERFE][0].uid, zeit=ANGELEGT, fassung=ALT))
    _bleibt(_profil(tmp_path, []), "wartet")


def test_gleicher_betreff_an_einen_anderen_empfaenger_ist_kein_nachfolger(monkeypatch, tmp_path):
    """Wie am 02.11.: info@ und firmenkunden@ desselben Hauses, gleicher Betreff."""
    anderer = "firmenkunden@example.com"
    _s, _u, profil = _fall2(
        monkeypatch, tmp_path,
        gesendet_mail=_mail(text=NEUER_TEXT, zeit=RAUS, fassung="", an=anderer,
                            kennung="<neu@b>"),
        tagebuch=[_gesendet_zeile(999, fassung=NEU, message_id="<neu@b>", an=(anderer,))])
    _bleibt(profil, "wartet")


def test_ein_schnitt_der_empfaenger_reicht_nicht(monkeypatch, tmp_path):
    """Die Sendung ging an AN und jemanden dazu. `treffer` lässt das als Schnitt zu."""
    beide = f"{AN}, zweite@example.com"
    _s, _u, profil = _fall2(
        monkeypatch, tmp_path,
        gesendet_mail=_mail(text=NEUER_TEXT, zeit=RAUS, fassung="", an=beide,
                            kennung="<neu@b>"),
        tagebuch=[_gesendet_zeile(999, fassung=NEU, message_id="<neu@b>",
                                  an=(AN, "zweite@example.com"))])
    _bleibt(profil, "wartet")


def test_eine_antwort_im_faden_ist_keine_neuere_fassung(monkeypatch, tmp_path):
    _s, _u, profil = _fall2(
        monkeypatch, tmp_path,
        gesendet_mail=_mail(text=NEUER_TEXT, zeit=RAUS, fassung="", betreff="AW: Auftrag S1",
                            kennung="<neu@b>"),
        tagebuch=[_gesendet_zeile(999, fassung=NEU, message_id="<neu@b>",
                                  betreff="AW: Auftrag S1")])
    _bleibt(profil, "wartet")


def test_eine_von_hand_gesendete_mail_belegt_keine_neuere_fassung(monkeypatch, tmp_path):
    """Gleicher Betreff, gleiche Empfänger, kein Tagebuch: vielleicht nur eine Rückfrage."""
    _bleibt(_fall2(monkeypatch, tmp_path, tagebuch=[])[2], "wartet")


def test_die_aeltere_fassung_geht_hinaus_die_juengere_bleibt(monkeypatch, tmp_path):
    """F1 lag seit gestern, F2 ist die jüngere. Geht F1 hinaus, ist F2 nicht überholt."""
    _s, uid, profil = _fall2(monkeypatch, tmp_path, tagebuch=[
        _gesendet_zeile(999, fassung="cccccccccccc", message_id="<neu@b>")])
    _buch(_fassung_neu(zeit=ANGELEGT - timedelta(hours=20), fassung="cccccccccccc"))
    bericht = _lauf(profil)
    assert bericht.verschoben == () and bericht.bleibt[0].sperre == "wartet"
    assert _uids(_s, ENTWUERFE) == [str(uid)]


def test_ist_die_gesendete_fassung_nicht_im_buch_ist_neuer_nicht_belegt(monkeypatch, tmp_path):
    _s, uid, profil = _fall2(monkeypatch, tmp_path, tagebuch=[
        _gesendet_zeile(999, fassung="dddddddddddd", message_id="<neu@b>")])
    assert _lauf(profil).verschoben == () and _uids(_s, ENTWUERFE) == [str(uid)]


@pytest.mark.parametrize("zweite", [None, ANGELEGT - timedelta(hours=20)],
                         ids=["unbekannt", "aelter"])
def test_passen_zwei_fassungen_muessen_beide_neuer_sein(monkeypatch, tmp_path, zweite):
    """ADR 0062, Punkt 4: Ein „vielleicht die ältere“ ist kein „eine neuere“."""
    _s, uid, profil = _fall2(monkeypatch, tmp_path, tagebuch=[
        _gesendet_zeile(999, fassung=NEU, message_id="<neu@b>"),
        _gesendet_zeile(998, fassung="cccccccccccc", message_id="<neu@b>")])
    if zweite:
        _buch(_fassung_neu(zeit=zweite, fassung="cccccccccccc"))
    assert _lauf(profil).verschoben == () and _uids(_s, ENTWUERFE) == [str(uid)]


def _zustand_schon_raus(**mehr) -> entwurfsbuch.Zustand:
    sendung = entwurfsbuch.Sendung(RAUS, frozenset({AN}), frozenset(), "auftrag s1", 0, True)
    return entwurfsbuch.Zustand(
        "schon_raus", "Auftrag S1", (AN,), ANGELEGT, "7", fassung=ALT, buch_zeit=ANGELEGT,
        sendungen=(sendung,), tagebuch=({"art": "gesendet", "ursprung": {"fassung": ALT}},),
        **mehr)


def test_regel_a_verlangt_was_status_belegt_nennt():
    """Am Zustand gebaut: Im Abgleich folgt `belegt` aus den übrigen Bedingungen der Regel."""
    assert not entwurfsablage._selbe_fassung_raus(_zustand_schon_raus())
    assert entwurfsablage._selbe_fassung_raus(_zustand_schon_raus(gesendet=(RAUS,)))


def test_eine_sendung_von_vor_dem_entwurf_ueberholt_ihn_nicht(monkeypatch, tmp_path):
    frueher = ANGELEGT - timedelta(minutes=30)
    _s, _u, profil = _fall2(
        monkeypatch, tmp_path,
        gesendet_mail=_mail(text=NEUER_TEXT, zeit=frueher, fassung="", kennung="<neu@b>"),
        tagebuch=[_gesendet_zeile(999, fassung=NEU, message_id="<neu@b>", zeit=frueher)])
    _bleibt(profil, "wartet")


def test_derselbe_text_ohne_tagebuch_ist_nicht_belegt(monkeypatch, tmp_path):
    """Zwillinge derselben Quelle: Dass der Text hinausging, sagt nicht, welcher es war."""
    server = _server(monkeypatch, [_mail()], [_mail(zeit=RAUS, fassung="")])
    _buch(_eintrag(server.ordner[ENTWUERFE][0].uid, zeit=ANGELEGT, fassung=ALT))
    _bleibt(_profil(tmp_path, []), "nicht_belegt")


def test_derselbe_text_nach_dem_versand_neu_angelegt_bleibt(monkeypatch, tmp_path):
    """`--trotz-gesendet`: Wer dieselbe Nachricht neu anlegt, will sie noch einmal senden."""
    spaeter = RAUS + timedelta(minutes=10)
    server = _server(monkeypatch, [_mail(zeit=spaeter)], [_mail(zeit=RAUS, fassung="")])
    _buch(_eintrag(server.ordner[ENTWUERFE][0].uid, zeit=spaeter, fassung=ALT))
    # Ohne UID, wie #420: Der Eintrag hängt über die Fassung am neuen Entwurf.
    profil = _profil(tmp_path, [_gesendet_zeile("")])
    _bleibt(profil, "nicht_belegt")


def test_schon_raus_an_andere_empfaenger_ist_nicht_dieselbe_sendung(monkeypatch, tmp_path):
    """Der Text ging auch an jemand anderen hinaus. `status` nennt das `schon_raus`."""
    beide = f"{AN}, zweite@example.com"
    server = _server(monkeypatch, [_mail()], [_mail(zeit=RAUS, fassung="", an=beide)])
    uid = server.ordner[ENTWUERFE][0].uid
    _buch(_eintrag(uid, zeit=ANGELEGT, fassung=ALT))
    _bleibt(_profil(tmp_path, [_gesendet_zeile(uid)]), "nicht_belegt")


def test_ein_tagebucheintrag_mit_anderer_fassung_belegt_nichts(monkeypatch, tmp_path):
    """Gleiche UID, andere Fassung: Das Tagebuch spricht von etwas anderem.

    Die Empfänger der Zeile weichen ab, damit sie nicht über den zweiten Anker
    die Sendung trifft. Dann wäre es eine neuere Fassung, und der Entwurf ginge
    zu Recht über die andere Regel.
    """
    server = _server(monkeypatch, [_mail()], [_mail(zeit=RAUS, fassung="")])
    uid = server.ordner[ENTWUERFE][0].uid
    _buch(_eintrag(uid, zeit=ANGELEGT, fassung=ALT))
    _bleibt(_profil(tmp_path, [_gesendet_zeile(uid, fassung=NEU, an=("x@example.com",))]),
            "nicht_belegt")


def test_eine_niedrigere_antwortstufe_ist_nicht_derselbe_betreff(monkeypatch, tmp_path):
    """Der Entwurf ist ein `AW:`, gesendet wurde eine neue Mail ohne. `treffer` lässt das zu."""
    _s, _u, profil = _fall2(
        monkeypatch, tmp_path, mail_mehr={"betreff": "AW: Auftrag S1"},
        buch_mehr={"betreff": "AW: Auftrag S1"})
    _bleibt(profil, "wartet")


def test_gleicher_text_unter_anderem_betreff_ist_keine_neuere_fassung(monkeypatch, tmp_path):
    _s, _u, profil = _fall2(
        monkeypatch, tmp_path,
        gesendet_mail=_mail(zeit=RAUS, fassung="", betreff="Etwas ganz anderes",
                            kennung="<neu@b>"),
        tagebuch=[_gesendet_zeile(999, fassung=NEU, message_id="<neu@b>",
                                  betreff="Etwas ganz anderes")])
    _bleibt(profil, "nicht_belegt")


def test_dieselbe_fassung_mit_anderem_text_ist_keine_neuere(monkeypatch, tmp_path):
    """Ein Zwilling, im Fenster geändert und gesendet: Das sagt über diesen Entwurf nichts."""
    _s, _u, profil = _fall2(
        monkeypatch, tmp_path,
        tagebuch=[_gesendet_zeile(999, fassung=ALT, message_id="<neu@b>")])
    bericht = _lauf(profil)
    assert bericht.verschoben == () and not postfach.IMAP_KLASSE.befehle("UID MOVE")


def test_ein_fenster_auf_einer_frueheren_uid_der_kette_haelt_den_entwurf(monkeypatch, tmp_path):
    """Thunderbird speicherte unter neuer UID, das Fenster zeigt noch auf die alte."""
    server, uid, _p = _fall1(monkeypatch, tmp_path / "a")
    alte = uid - 1 if uid > 1 else uid + 50
    monkeypatch.setattr(bruecke, "VERBINDEN", _offenes_fenster(alte))
    profil = _profil(tmp_path, [
        _gesendet_zeile(uid),
        {"zeit": ANGELEGT.isoformat(), "art": "gespeichert", "neu_uid": [uid],
         "ursprung": {"typ": "draft", "konto": VON, "uid": alte, "fassung": ALT}}])
    assert _lauf(profil).bleibt[0].sperre == "offen"
    assert _uids(server, ENTWUERFE) == [str(uid)]


@pytest.mark.parametrize("abweichung", [
    {"datum_plus": 121}, {"betreff": "Anderer Betreff"}, {"an": ("x@example.com",)},
    {"konto": "fremd@example.de"}], ids=["zeit", "betreff", "empfaenger", "konto"])
def test_der_zweite_anker_verlangt_alles_zugleich(abweichung):
    """Je ein Merkmal daneben, und die Sendung gehört keinem Eintrag."""
    kopf = postfach.Kopf("1", RAUS, (AN,), "Auftrag S1", "", "")
    zeile = _gesendet_zeile(5, fassung=NEU)
    assert entwurfsbuch.tagebuch_fassungen(kopf, [zeile], VON) == {NEU}, "die Probe trifft sonst nie"
    if "datum_plus" in abweichung:
        zeile["zeit"] = (RAUS + timedelta(seconds=abweichung["datum_plus"])).isoformat()
    if "betreff" in abweichung:
        zeile["ursprung"]["betreff"] = abweichung["betreff"]
    if "an" in abweichung:
        zeile["an"] = list(abweichung["an"])
    if "konto" in abweichung:
        zeile["ursprung"]["konto"] = abweichung["konto"]
    assert entwurfsbuch.tagebuch_fassungen(kopf, [zeile], VON) == frozenset()


# ── Unmittelbar vor dem Zug ─────────────────────────────────────────────────

def _nach_dem_plan(monkeypatch, tun) -> None:
    """Führt `tun` aus, sobald der Plan steht und bevor die zweite Sitzung beginnt."""
    echt = entwurfsbuch.abgleich

    def abgleich(*a, **k):
        stand = echt(*a, **k)
        tun()
        return stand
    monkeypatch.setattr(entwurfsbuch, "abgleich", abgleich)


def test_steht_unter_der_uid_eine_andere_mail_bleibt_sie(monkeypatch, tmp_path):
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    fremd = _mail(fassung="cccccccccccc", betreff="Ganz andere Mail")[0]

    def tausche():
        server.ordner[ENTWUERFE][0].roh = fremd
    _nach_dem_plan(monkeypatch, tausche)
    bericht = _lauf(profil)
    assert bericht.verschoben == () and _uids(server, ENTWUERFE) == [str(uid)]
    assert bericht.bleibt[0].sperre == "neu_gelesen"
    assert "andere Nachricht" in bericht.bleibt[0].grund


def test_gegenprobe_ohne_kopfvergleich_traefe_der_zug_die_fremde_mail(monkeypatch, tmp_path):
    server, _uid, profil = _fall1(monkeypatch, tmp_path)
    fremd = _mail(fassung="cccccccccccc", betreff="Ganz andere Mail")[0]

    def tausche():
        server.ordner[ENTWUERFE][0].roh = fremd
    _nach_dem_plan(monkeypatch, tausche)
    monkeypatch.setattr(entwurfsablage, "_noch_derselbe", lambda *_a: "")
    assert len(_lauf(profil).verschoben) == 1


def test_ein_fenster_das_nach_dem_plan_auf_der_kette_aufgeht_haelt_den_zug(monkeypatch, tmp_path):
    server, uid, _profil_pfad = _fall1(monkeypatch, tmp_path)
    zug = entwurfsablage.Zug(str(uid), "Auftrag S1", (AN,), ALT, ANGELEGT,
                             entwurfsablage.SCHON_RAUS, frozenset({str(uid), "41"}))
    monkeypatch.setattr(bruecke, "VERBINDEN", _offenes_fenster(41))
    with postfach.verbinde(VON, umgebung={}) as sitzung:
        grund = entwurfsablage._ziehe(sitzung, ENTWUERFE, PAPIERKORB, zug, adresse=VON,
                                      umgebung={}, machen=True)
    assert grund == "gerade in einem Fenster offen" and not server.befehle("UID MOVE")


def test_ein_fenster_das_nach_dem_plan_aufgeht_haelt_den_zug(monkeypatch, tmp_path):
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    _nach_dem_plan(monkeypatch, lambda: monkeypatch.setattr(
        bruecke, "VERBINDEN", _offenes_fenster(uid)))
    bericht = _lauf(profil)
    assert bericht.verschoben == () and _uids(server, ENTWUERFE) == [str(uid)]
    assert "Fenster" in bericht.bleibt[0].grund


def _alias_fenster(uid, identitaet="bestellung@example.de"):
    return BrueckenAttrappe({"ok": True, "fenster": [
        {"titel": "Verfassen", "betreff": "Auftrag S1", "identitaet": identitaet,
         "draft_id": f"imap-message://order%40example.de@127.0.0.1/Entw&APw-rfe#{uid}"}]})


def test_ein_fenster_unter_einer_alias_identitaet_haelt_den_entwurf(monkeypatch, tmp_path):
    """#442 (N3): `identitaet` ist das `From` des Fensters, nicht das Konto.

    Wer unter einem Alias desselben Kontos schreibt, meldet eine fremde
    Adresse. Bis 0.11.0 fiel das Fenster damit aus der Zuordnung, und der
    Entwurf ging aus dem offenen Fenster in den Papierkorb.
    """
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    monkeypatch.setattr(bruecke, "VERBINDEN", _alias_fenster(uid))
    bericht = _lauf(profil)
    assert bericht.verschoben == () and _uids(server, ENTWUERFE) == [str(uid)]
    assert "Fenster" in bericht.bleibt[0].grund


def test_ein_alias_fenster_das_nach_dem_plan_aufgeht_haelt_den_zug(monkeypatch, tmp_path):
    """Dieselbe Sperre an der zweiten Stelle: `_ziehe` fragt unmittelbar vor dem Zug."""
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    _nach_dem_plan(monkeypatch, lambda: monkeypatch.setattr(
        bruecke, "VERBINDEN", _alias_fenster(uid)))
    bericht = _lauf(profil)
    assert bericht.verschoben == () and _uids(server, ENTWUERFE) == [str(uid)]
    assert "Fenster" in bericht.bleibt[0].grund


def test_faellt_die_bruecke_nach_dem_plan_aus_bleibt_der_entwurf(monkeypatch, tmp_path):
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    _nach_dem_plan(monkeypatch, lambda: monkeypatch.setattr(
        bruecke, "VERBINDEN", BrueckenAttrappe({"ok": False, "fehler": "befehl_unbekannt"})))
    assert _lauf(profil).verschoben == ()
    assert _uids(server, ENTWUERFE) == [str(uid)]


def test_ein_move_das_nichts_bewegt_gilt_nicht_als_verschoben(monkeypatch, tmp_path):
    """Ein `UID MOVE` auf eine UID, die es nicht gibt, antwortet `OK`."""
    _s, _uid, profil = _fall1(monkeypatch, tmp_path)
    monkeypatch.setattr(entwurfsablage, "verschiebe", lambda *_a: None)
    bericht = _lauf(profil)
    assert bericht.verschoben == () and "bewegt hat er nichts" in bericht.grund


# ── Was der Lauf zusagt ─────────────────────────────────────────────────────

def test_der_zweite_lauf_bewegt_nichts(monkeypatch, tmp_path):
    server, _uid, profil = _fall1(monkeypatch, tmp_path)
    assert len(_lauf(profil).verschoben) == 1
    zuege = len(server.befehle("UID MOVE"))
    zweiter = _lauf(profil)
    assert zweiter.verschoben == () and zweiter.zuege == () and not zweiter.grund
    assert len(server.befehle("UID MOVE")) == zuege == 1


def test_ohne_move_beim_server_bewegt_sich_nichts(monkeypatch, tmp_path):
    server = _server(monkeypatch, [_mail()], [_mail(zeit=RAUS, fassung="")],
                     faehigkeiten=("IMAP4REV1", "UIDPLUS"))
    uid = server.ordner[ENTWUERFE][0].uid
    _buch(_eintrag(uid, zeit=ANGELEGT, fassung=ALT))
    bericht = _lauf(_profil(tmp_path, [_gesendet_zeile(uid)]))
    assert bericht.verschoben == () and "kein MOVE" in bericht.grund
    assert _uids(server, ENTWUERFE) == [str(uid)]
    assert not server.befehle("UID MOVE") and not server.befehle("SELECT")


def test_ohne_papierkorb_bewegt_sich_nichts(monkeypatch, tmp_path):
    server = _server(monkeypatch, [_mail()], [_mail(zeit=RAUS, fassung="")],
                     sonder={"INBOX": "", GESENDET: "\\Sent", ENTWUERFE: "\\Drafts",
                             PAPIERKORB: ""})
    uid = server.ordner[ENTWUERFE][0].uid
    _buch(_eintrag(uid, zeit=ANGELEGT, fassung=ALT))
    bericht = _lauf(_profil(tmp_path, [_gesendet_zeile(uid)]))
    assert bericht.verschoben == () and "\\Trash" in bericht.grund
    assert not server.befehle("UID MOVE")


def test_postfach_nicht_erreichbar_heisst_nicht_geprueft(monkeypatch, tmp_path, capsys):
    def _weg(*_a, **_k):
        raise OSError("Proxy aus")

    monkeypatch.setattr(postfach, "IMAP_KLASSE", _weg)
    bericht = _lauf()
    assert bericht.grund and bericht.zuege == () and bericht.bleibt == ()
    ausgabe = entwurfsablage.zeilen(bericht)
    assert ausgabe[0].startswith("NICHT GEPRÜFT")
    assert not any(z.startswith("OK") or "überholt" in z for z in ausgabe)
    assert falzmarke.main(["aufraeumen", "--absender", VON, "--entwuerfe"]) \
        == falzmarke.EXIT_UMGEBUNG
    assert "NICHT GEPRÜFT" in capsys.readouterr().err


def test_bricht_der_lauf_ab_steht_das_bewegte_trotzdem_im_bericht(monkeypatch, tmp_path):
    server = _server(monkeypatch, [_mail(), _mail(fassung=NEU, text=NEUER_TEXT)],
                     [_mail(zeit=RAUS, fassung=""), _mail(text=NEUER_TEXT, zeit=RAUS, fassung="")])
    eins, zwei = [n.uid for n in server.ordner[ENTWUERFE]]
    _buch(_eintrag(eins, zeit=ANGELEGT, fassung=ALT),
          _eintrag(zwei, zeit=ANGELEGT, fassung=NEU, text=NEUER_TEXT))
    profil = _profil(tmp_path, [_gesendet_zeile(eins), _gesendet_zeile(zwei, fassung=NEU)])
    echt = entwurfsablage.verschiebe

    def einmal(sitzung, quelle, ziel, uid):
        if server.ordner[PAPIERKORB]:
            raise entwurfsablage.EntwurfsablageFehler("Leitung weg")
        echt(sitzung, quelle, ziel, uid)
    monkeypatch.setattr(entwurfsablage, "verschiebe", einmal)
    bericht = _lauf(profil)
    assert len(bericht.verschoben) == 1 and bericht.grund == "Leitung weg"
    assert "vor dem Abbruch verschoben" in "\n".join(entwurfsablage.zeilen(bericht))


def test_nichts_wird_hart_geloescht(monkeypatch, tmp_path):
    """Die Nachricht liegt danach byte-gleich im Papierkorb, kein STORE, kein EXPUNGE."""
    server, _uid, profil = _fall1(monkeypatch, tmp_path)
    roh = server.ordner[ENTWUERFE][0].roh
    _lauf(profil)
    assert [n.roh for n in server.ordner[PAPIERKORB]] == [roh]
    assert {p[0] for p in server.protokoll} & {"UID STORE", "UID COPY", "EXPUNGE"} == set()
    ziel = server.befehle("UID MOVE")[0][-1]
    assert ziel.strip('"') == PAPIERKORB


def test_json_sagt_dasselbe_wie_der_text(monkeypatch, tmp_path, capsys):
    _s, uid, profil = _fall1(monkeypatch, tmp_path)
    aus = entwurfsablage.als_json(_lauf(profil))
    assert aus["verschoben"] == [str(uid)] and aus["geprueft"] is True
    assert aus["zuege"][0]["regel"] == "schon_raus"


def test_ohne_entwuerfe_bleibt_aufraeumen_beim_eingang(monkeypatch, capsys):
    """Das Verhalten aus #431: Der neue Schalter ändert den alten Befehl nicht."""
    aufgerufen = []
    monkeypatch.setattr(entwurfsablage, "raeume_auf", lambda *a, **k: aufgerufen.append(a))
    monkeypatch.setattr(postfach, "IMAP_KLASSE", ImapAttrappe({"INBOX": []}))
    falzmarke.main(["aufraeumen", "--absender", VON])
    assert aufgerufen == []


def test_status_bleibt_lesend(monkeypatch, tmp_path, capsys):
    """Dieselbe Lage, die das Aufräumen bewegen würde, und ein Server, der MOVE verweigert."""
    server, _uid, _profil_pfad = _fall1(monkeypatch, tmp_path)
    server.verschieben_erlaubt = False
    falzmarke.main(["status", "--absender", VON])
    assert server.befehle("EXAMINE"), "status hat das Postfach gar nicht gelesen"
    assert not server.befehle("UID MOVE") and not server.befehle("SELECT")


# ── email: neuer Text über altem Entwurf ────────────────────────────────────

ALTER_TEXT = "Wir feiern am Samstag, das Programm folgt in den nächsten Tagen hier."
QUELLE = """---
typ: email
profil: example
an: Paula Beispiel <paula@example.org>
betreff: "Sommerfest – Programm"
anrede: Hallo Paula,
---
{text}
"""


@pytest.fixture
def mail_lauf(monkeypatch, tmp_path):
    """Ein `email --oeffnen` gegen die Attrappe, mit erreichbarer Brücke im Lesen."""
    konto = "paul@example.org"
    server = ImapAttrappe({ENTWUERFE: [], GESENDET: [], PAPIERKORB: []},
                          sonder={"INBOX": "", GESENDET: "\\Sent", ENTWUERFE: "\\Drafts",
                                  PAPIERKORB: "\\Trash"}, verschieben_erlaubt=True)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
    monkeypatch.setattr(oeffnen, "entwurf", _mit_attrappen(oeffnen.entwurf))
    monkeypatch.setenv("FALZMARKE_AUFRAEUMEN", "nie")
    monkeypatch.setattr(oeffnen, "_fenster_auf", lambda lage, *_a, **_k: lage)
    tagebuch = tmp_path / "tagebuch"
    tagebuch.mkdir()
    _profil(tagebuch, [])
    echt_ersetzbar = entwurfsablage.ersetzbar

    def ersetzbar(*a, **k):
        k["profilordner"] = tagebuch
        return echt_ersetzbar(*a, **k)
    monkeypatch.setattr(entwurfsablage, "ersetzbar", ersetzbar)
    monkeypatch.setattr(entwurfsbuch, "tagebuch", _tagebuch_aus(tagebuch))

    def lauf(text, *schalter, name="mail"):
        quelle = tmp_path / f"{name}.md"
        quelle.write_text(QUELLE.format(text=text), encoding="utf-8")
        return falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE), "--oeffnen",
                               "-o", str(tmp_path / name), *schalter])
    lauf.server = server
    lauf.konto = konto
    lauf.tagebuch = tagebuch
    return lauf


def kopf_absender(eintrag) -> str:
    import email

    return email.utils.parseaddr(email.message_from_bytes(eintrag.roh)["From"])[1]


def _tagebuch_aus(ordner: Path):
    echt = entwurfsbuch.tagebuch

    def tagebuch(_profilordner=None, umgebung=None):
        return echt(ordner, umgebung)
    return tagebuch


def test_text_gleich_oeffnet_den_alten_und_legt_nichts_an(mail_lauf, capsys):
    mail_lauf(ALTER_TEXT)
    capsys.readouterr()
    vorher = _uids(mail_lauf.server, ENTWUERFE)
    mail_lauf(ALTER_TEXT)
    assert _uids(mail_lauf.server, ENTWUERFE) == vorher
    assert mail_lauf.server.ordner[PAPIERKORB] == []
    assert "ENTWURF LIEGT SCHON" in capsys.readouterr().err


def test_text_geaendert_ersetzt_den_alten_ohne_schalter(mail_lauf, capsys):
    """Die Antwort auf „kann es der Default sein“: Ja, wenn der alte belegt unser ist."""
    mail_lauf(ALTER_TEXT)
    capsys.readouterr()
    alt = _uids(mail_lauf.server, ENTWUERFE)
    assert mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.") == falzmarke.EXIT_OK
    aus = capsys.readouterr()
    neu = _uids(mail_lauf.server, ENTWUERFE)
    assert len(alt) == len(neu) == 1 and alt != neu
    assert len(mail_lauf.server.ordner[PAPIERKORB]) == 1
    assert f"ersetzt: UID {alt[0]} →" in aus.out
    assert "ENTWURF LIEGT SCHON" not in aus.err
    # Erst der neue, dann das Wegräumen.
    arten = [p[0] for p in mail_lauf.server.protokoll]
    assert arten.index("APPEND", arten.index("APPEND") + 1) < arten.index("UID MOVE")


def test_ein_fremder_entwurf_mit_gleichem_betreff_bleibt(mail_lauf, capsys):
    """Ohne Schalter wie bisher „liegt schon“, nichts angelegt, nichts bewegt, Grund genannt."""
    fremd = nachricht(an="paula@example.org", betreff="Sommerfest – Programm",
                      text="Von Hand geschrieben.", datum=ANGELEGT, von=mail_lauf.konto)
    mail_lauf.server._lege_ab(ENTWUERFE, fremd, ANGELEGT)
    vorher = _uids(mail_lauf.server, ENTWUERFE)
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    aus = capsys.readouterr().err
    assert _uids(mail_lauf.server, ENTWUERFE) == vorher
    assert mail_lauf.server.ordner[PAPIERKORB] == []
    assert "ENTWURF LIEGT SCHON" in aus and "trägt keine Fassung" in aus and "--ersetzen" in aus


def test_ersetzen_legt_trotz_fremdem_entwurf_an_und_laesst_ihn_stehen(mail_lauf, capsys):
    fremd = nachricht(an="paula@example.org", betreff="Sommerfest – Programm",
                      text="Von Hand geschrieben.", datum=ANGELEGT, von=mail_lauf.konto)
    mail_lauf.server._lege_ab(ENTWUERFE, fremd, ANGELEGT)
    vorher = _uids(mail_lauf.server, ENTWUERFE)
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.", "--ersetzen")
    aus = capsys.readouterr().err
    assert len(_uids(mail_lauf.server, ENTWUERFE)) == 2
    assert set(vorher) < set(_uids(mail_lauf.server, ENTWUERFE))
    assert mail_lauf.server.ordner[PAPIERKORB] == []
    assert f"bleibt liegen: UID {vorher[0]}" in aus


@pytest.mark.parametrize("sperren", [("ohne_fassung", "nicht_im_buch")], ids=["von_falzmarke"])
def test_gegenprobe_ohne_die_herkunft_floege_der_fremde_entwurf(mail_lauf, sperren, monkeypatch):
    """Das Prüfmittel aus #425: rot, wenn „von falzmarke angelegt“ entfällt."""
    fremd = nachricht(an="paula@example.org", betreff="Sommerfest – Programm",
                      text="Von Hand geschrieben.", datum=ANGELEGT, von=mail_lauf.konto)
    mail_lauf.server._lege_ab(ENTWUERFE, fremd, ANGELEGT)
    monkeypatch.setattr(entwurfsablage, "SPERREN", tuple(
        (n, s) for n, s in entwurfsablage.SPERREN if n not in sperren))
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    assert len(mail_lauf.server.ordner[PAPIERKORB]) == 1


def test_ein_offener_alter_entwurf_wird_nicht_ersetzt(mail_lauf, monkeypatch, capsys):
    mail_lauf(ALTER_TEXT)
    uid = _uids(mail_lauf.server, ENTWUERFE)[0]
    monkeypatch.setattr(bruecke, "VERBINDEN", _offenes_fenster(uid))
    capsys.readouterr()
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.", "--ersetzen")
    assert mail_lauf.server.ordner[PAPIERKORB] == []
    assert "gerade in einem Fenster offen" in capsys.readouterr().err


def test_ein_in_thunderbird_geaenderter_entwurf_wird_nicht_ersetzt(mail_lauf, capsys):
    """Er trägt dieselbe Fassung, aber eine neue UID, die das Buch nicht kennt (#420)."""
    mail_lauf(ALTER_TEXT)
    alt = mail_lauf.server.ordner[ENTWUERFE][0]
    mail_lauf.server.ordner[ENTWUERFE] = []
    mail_lauf.server._lege_ab(ENTWUERFE, alt.roh, ANGELEGT)
    capsys.readouterr()
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    assert mail_lauf.server.ordner[PAPIERKORB] == []
    assert "nicht im Entwurfsbuch" in capsys.readouterr().err


def test_andere_empfaenger_im_schnitt_werden_nicht_ersetzt(mail_lauf, capsys):
    """`_gleicher_entwurf` lässt den Schnitt gelten, das Ersetzen nicht."""
    mail_lauf(ALTER_TEXT)
    capsys.readouterr()
    eintrag = mail_lauf.server.ordner[ENTWUERFE][0]
    kopf = postfach.kopf_aus(eintrag.roh, str(eintrag.uid), None)
    felder = {"absender": kopf_absender(eintrag), "roh": nachricht(
        an="paula@example.org, otto@example.org", betreff="Sommerfest – Programm",
        text="Neu.", datum=RAUS)}
    with postfach.verbinde(felder["absender"], umgebung={}) as sitzung:
        wertung = entwurfsablage.ersetzbar(sitzung, ENTWUERFE, [kopf], felder, umgebung={})
    assert wertung.weg == () and wertung.bleibt[0].sperre == "andere_empfaenger"


def test_ein_abweichender_text_im_alten_entwurf_wird_nicht_ersetzt(mail_lauf, capsys):
    mail_lauf(ALTER_TEXT)
    pfad = entwurfsbuch.BUCH_VORGABE
    zeile = json.loads(pfad.read_text(encoding="utf-8").splitlines()[-1])
    zeile["text"] = "Ein ganz anderer Text, der jetzt nicht mehr dem Entwurf im Ordner entspricht."
    pfad.write_text(json.dumps(zeile) + "\n", encoding="utf-8")
    capsys.readouterr()
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    assert mail_lauf.server.ordner[PAPIERKORB] == []
    assert "Text weicht vom Entwurfsbuch ab" in capsys.readouterr().err


def _plan_ueber_den_liegenden(mail_lauf) -> entwurfsablage.Wertung:
    """`ersetzbar` selbst: `_ziehe` prüft noch einmal und verdeckte sonst den Plan."""
    eintrag = mail_lauf.server.ordner[ENTWUERFE][0]
    kopf = postfach.kopf_aus(eintrag.roh, str(eintrag.uid), None)
    felder = {"absender": kopf_absender(eintrag), "roh": nachricht(
        an="paula@example.org", betreff="Sommerfest – Programm", text="Neu.", datum=RAUS)}
    with postfach.verbinde(felder["absender"], umgebung={}) as sitzung:
        return entwurfsablage.ersetzbar(sitzung, ENTWUERFE, [kopf], felder, umgebung={})


def test_der_plan_laesst_ohne_sperre_den_alten_ziehen(mail_lauf):
    """Der Zwilling zu den vier Fällen darunter: Nichts hält, also geht er."""
    mail_lauf(ALTER_TEXT)
    wertung = _plan_ueber_den_liegenden(mail_lauf)
    assert len(wertung.weg) == 1 and wertung.bleibt == ()


def _gespeichert_im_tagebuch(mail_lauf, _monkeypatch):
    eintrag = mail_lauf.server.ordner[ENTWUERFE][0]
    zeile = {"zeit": ANGELEGT.isoformat(), "art": "gespeichert", "neu_uid": [],
             "ursprung": {"typ": "draft", "konto": kopf_absender(eintrag),
                          "uid": str(eintrag.uid)}}
    pfad = mail_lauf.tagebuch / "Profiles" / "abc.default-release" / entwurfsbuch.TAGEBUCH
    pfad.write_text(json.dumps(zeile) + "\n", encoding="utf-8")


def _andere_fassung_im_buch(_mail_lauf, _monkeypatch):
    """Dieselbe UID, aber das Buch meint eine andere Nachricht."""
    pfad = entwurfsbuch.BUCH_VORGABE
    zeile = json.loads(pfad.read_text(encoding="utf-8").splitlines()[-1])
    pfad.write_text(json.dumps({**zeile, "fassung": "eeeeeeeeeeee"}) + "\n", encoding="utf-8")


def _gekappt_im_buch(_mail_lauf, _monkeypatch):
    pfad = entwurfsbuch.BUCH_VORGABE
    zeile = json.loads(pfad.read_text(encoding="utf-8").splitlines()[-1])
    pfad.write_text(json.dumps({**zeile, "text_gekappt": True}) + "\n", encoding="utf-8")


def _kaputte_buchzeile(_mail_lauf, _monkeypatch):
    _buch(kaputt=True)


def _bruecke_faellt_aus(_mail_lauf, monkeypatch):
    def _nein(*_a, **_k):
        raise OSError("Socket weg")
    monkeypatch.setattr(bruecke, "VERBINDEN", _nein)


@pytest.mark.parametrize(("aufbau", "sperre"), [
    (_gespeichert_im_tagebuch, "gespeichert"), (_gekappt_im_buch, "gekappt"),
    (_kaputte_buchzeile, "beleg_unlesbar"), (_bruecke_faellt_aus, "fenster_ungeprueft"),
    (_andere_fassung_im_buch, "nicht_im_buch")],
    ids=["gespeichert", "gekappt", "beleg_unlesbar", "fenster_ungeprueft", "nicht_im_buch"])
def test_ersetzbar_haelt_jede_sperre_ein(mail_lauf, monkeypatch, aufbau, sperre):
    mail_lauf(ALTER_TEXT)
    aufbau(mail_lauf, monkeypatch)
    wertung = _plan_ueber_den_liegenden(mail_lauf)
    assert wertung.weg == () and [r.sperre for r in wertung.bleibt] == [sperre]


def test_ein_unlesbares_buch_verhindert_das_anlegen_nicht_mit_einem_traceback(
        mail_lauf, monkeypatch, capsys):
    """Vorher „liegt schon“, und dabei bleibt es, statt mit einem Absturz zu enden."""
    mail_lauf(ALTER_TEXT)
    vorher = _uids(mail_lauf.server, ENTWUERFE)

    def _nein(*_a, **_k):
        raise PermissionError("kein Zugriff aufs Buch")
    monkeypatch.setattr(entwurfsbuch, "lesen", _nein)
    capsys.readouterr()
    assert mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.") == falzmarke.EXIT_OK
    aus = capsys.readouterr().err
    assert _uids(mail_lauf.server, ENTWUERFE) == vorher
    assert mail_lauf.server.ordner[PAPIERKORB] == []
    assert "ENTWURF LIEGT SCHON" in aus and "nicht prüfbar: kein Zugriff aufs Buch" in aus


def test_ein_fehler_beim_ersetzen_heisst_nicht_geprueft_nicht_absturz(
        mail_lauf, monkeypatch, capsys):
    mail_lauf(ALTER_TEXT)

    def _nein(*_a, **_k):
        raise RuntimeError("unerwartet")
    monkeypatch.setattr(entwurfsablage, "_ziehe", _nein)
    capsys.readouterr()
    assert mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.") == falzmarke.EXIT_OK
    assert "NICHT GEPRÜFT  alte Entwürfe nicht ersetzt: unerwartet" in capsys.readouterr().err
    assert len(_uids(mail_lauf.server, ENTWUERFE)) == 2


def test_nach_dem_zug_fragt_keiner_mehr_nach_dem_papierkorb(mail_lauf, monkeypatch, capsys):
    """Ein Fehlschlag dort machte aus dem Erfolg „ungewiss“ und verschwieg die bewegten UIDs."""
    mail_lauf(ALTER_TEXT)
    alt = _uids(mail_lauf.server, ENTWUERFE)
    echt = postfach.Postfach.sonderordner

    def sonderordner(selbst, kennzeichen):
        if mail_lauf.server.befehle("UID MOVE"):
            raise postfach.PostfachFehler("LIST scheitert nach dem Zug")
        return echt(selbst, kennzeichen)
    monkeypatch.setattr(postfach.Postfach, "sonderordner", sonderordner)
    capsys.readouterr()
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    aus = capsys.readouterr()
    assert f"ersetzt: UID {alt[0]} →" in aus.out and "abgebrochen" not in aus.err


def test_stimmt_die_nachzaehlung_nicht_bleibt_der_alte(mail_lauf, monkeypatch, capsys):
    """Der Server nahm den neuen an, aber er liegt nicht da: Dann bleibt der einzige, den es gibt."""
    mail_lauf(ALTER_TEXT)
    alt = _uids(mail_lauf.server, ENTWUERFE)
    monkeypatch.setattr(postfach.Postfach, "ablegen", lambda *_a, **_k: None)
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    assert _uids(mail_lauf.server, ENTWUERFE) == alt
    assert mail_lauf.server.ordner[PAPIERKORB] == []


def test_scheitert_das_ablegen_bleibt_der_alte_unberuehrt(mail_lauf, monkeypatch, capsys):
    mail_lauf(ALTER_TEXT)
    alt = _uids(mail_lauf.server, ENTWUERFE)

    def _nein(*_a, **_k):
        raise postfach.PostfachFehler("Leitung weg")
    monkeypatch.setattr(postfach.Postfach, "ablegen", _nein)
    mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    assert _uids(mail_lauf.server, ENTWUERFE) == alt
    assert mail_lauf.server.ordner[PAPIERKORB] == []


def test_scheitert_das_ersetzen_liegen_beide_und_der_lauf_sagt_es(mail_lauf, monkeypatch, capsys):
    mail_lauf(ALTER_TEXT)
    capsys.readouterr()
    mail_lauf.server.capabilities = ("IMAP4REV1",)
    code = mail_lauf("Das Programm steht jetzt fest und liegt als Anlage bei.")
    aus = capsys.readouterr().err
    assert code == falzmarke.EXIT_OK and len(_uids(mail_lauf.server, ENTWUERFE)) == 2
    assert "NICHT GEPRÜFT  alte Entwürfe nicht ersetzt" in aus and "kein MOVE" in aus


def test_ersetzen_und_noch_ein_entwurf_schliessen_sich_aus(tmp_path, capsys):
    with pytest.raises(SystemExit) as ende:
        falzmarke.main(["email", "x.md", "--ersetzen", "--noch-ein-entwurf"])
    assert ende.value.code != 0


def test_ersetzen_steht_in_der_hilfe(capsys):
    with pytest.raises(SystemExit):
        falzmarke.main(["email", "--help"])
    hilfe = capsys.readouterr().out
    assert "--ersetzen" in hilfe
    with pytest.raises(SystemExit):
        falzmarke.main(["aufraeumen", "--help"])
    assert "--entwuerfe" in capsys.readouterr().out


# ── email --oeffnen räumt mit auf ───────────────────────────────────────────

def _automatik(monkeypatch, bericht_oder_fehler):
    def lauf(adresse, **k):
        if isinstance(bericht_oder_fehler, Exception):
            raise bericht_oder_fehler
        return bericht_oder_fehler
    monkeypatch.setattr(entwurfsablage, "raeume_auf", lauf)


def _mitschrift(monkeypatch) -> list[str]:
    """Eine Ausnahme ginge hier nicht: Die Automatik fängt sie und sagt NICHT GEPRÜFT."""
    gerufen: list[str] = []
    monkeypatch.setattr(entwurfsablage, "raeume_auf", lambda adresse, **_k: (
        gerufen.append(adresse), entwurfsablage.Bericht(adresse))[1])
    return gerufen


def test_die_automatik_sagt_in_einer_zeile_welche_uids_weg_sind(monkeypatch, capsys):
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    _automatik(monkeypatch, entwurfsablage.Bericht(
        VON, entwuerfe="Entwürfe", papierkorb="Papierkorb", verschoben=("7", "9")))
    falzmarke._raeume_entwuerfe_mit(VON)
    aus = capsys.readouterr()
    assert aus.out.strip() == f"OK  aus „Entwürfe“ von {VON} weggeräumt: UID 7, 9 → „Papierkorb“"
    assert aus.err == ""


def test_die_automatik_schweigt_wenn_nichts_geschah(monkeypatch, capsys):
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    _automatik(monkeypatch, entwurfsablage.Bericht(VON, entwuerfe="Entwürfe"))
    falzmarke._raeume_entwuerfe_mit(VON)
    aus = capsys.readouterr()
    assert aus.out == "" and aus.err == ""


@pytest.mark.parametrize("ausgang", [entwurfsablage.Bericht(VON, grund="Proxy aus"),
                                     RuntimeError("Proxy aus")], ids=["bericht", "ausnahme"])
def test_eine_gescheiterte_automatik_heisst_nicht_geprueft(ausgang, monkeypatch, capsys):
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    _automatik(monkeypatch, ausgang)
    falzmarke._raeume_entwuerfe_mit(VON)
    assert "NICHT GEPRÜFT" in capsys.readouterr().err


def test_die_automatik_ist_abschaltbar(monkeypatch):
    monkeypatch.setenv("FALZMARKE_AUFRAEUMEN", "nie")
    gerufen = _mitschrift(monkeypatch)
    falzmarke._raeume_entwuerfe_mit(VON)
    assert gerufen == []


def test_email_oeffnen_ruft_die_automatik_und_der_exit_bleibt(mail_lauf, monkeypatch, capsys):
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    gerufen = []
    monkeypatch.setattr(entwurfsablage, "raeume_auf", lambda adresse, **k: (
        gerufen.append((adresse, k)), entwurfsablage.Bericht(adresse, grund="Proxy aus"))[1])
    assert mail_lauf(ALTER_TEXT) == falzmarke.EXIT_OK
    absender = kopf_absender(mail_lauf.server.ordner[ENTWUERFE][0])
    assert gerufen == [(absender, {"machen": True, "ausser": frozenset()})]
    assert "NICHT GEPRÜFT  Entwürfe von" in capsys.readouterr().err


def test_auch_liegt_schon_raeumt_mit_auf(mail_lauf, monkeypatch, capsys):
    """Und lässt den liegen, den derselbe Lauf gerade öffnet."""
    mail_lauf(ALTER_TEXT)
    uid = _uids(mail_lauf.server, ENTWUERFE)[0]
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    gerufen = []
    monkeypatch.setattr(entwurfsablage, "raeume_auf", lambda adresse, **k: (
        gerufen.append(k), entwurfsablage.Bericht(adresse))[1])
    mail_lauf(ALTER_TEXT)
    assert gerufen == [{"machen": True, "ausser": frozenset({uid})}]


@pytest.mark.parametrize(("schalter", "soll"), [((), False), (("--machen",), True)],
                         ids=["ohne", "mit"])
def test_aufraeumen_entwuerfe_bewegt_nur_mit_machen(schalter, soll, monkeypatch, capsys):
    gerufen = []
    monkeypatch.setattr(entwurfsablage, "raeume_auf", lambda adresse, **k: (
        gerufen.append(k), entwurfsablage.Bericht(adresse))[1])
    assert falzmarke.main(["aufraeumen", "--absender", VON, "--entwuerfe", *schalter]) \
        == falzmarke.EXIT_OK
    assert gerufen[0]["machen"] is soll


def test_die_automatik_laesst_den_eben_geoeffneten_entwurf_liegen(monkeypatch, tmp_path, capsys):
    """Geht er gerade auf, steht er in keiner Fensterliste, auch wenn eine Regel ihn träfe."""
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    bericht = entwurfsablage.raeume_auf(VON, machen=True, jetzt=JETZT, umgebung={},
                                        profilordner=profil, ausser=frozenset({str(uid)}))
    assert bericht.verschoben == () and not server.befehle("UID MOVE")
    assert [(r.uid, r.sperre, r.ueberholt) for r in bericht.bleibt] == [(str(uid), "offen", True)]


def test_ein_abbruch_nennt_was_nicht_bewegt_wurde():
    zug = entwurfsablage.Zug("7", "A", (AN,), ALT, ANGELEGT, entwurfsablage.SCHON_RAUS)
    nicht = zug._replace(uid="8")
    bericht = entwurfsablage.Bericht(VON, grund="Leitung weg", entwuerfe="Entwürfe",
                                     zuege=(zug, nicht), verschoben=("7",))
    zeilen = [z for z in entwurfsablage.zeilen(bericht) if z.startswith("    UID")]
    assert "nicht bewegt" not in zeilen[0] and zeilen[1].endswith(" — nicht bewegt")


def test_ein_unerwarteter_fehler_im_abgleich_heisst_nicht_geprueft(monkeypatch):
    def _nein(*_a, **_k):
        raise PermissionError("Buch gesperrt")
    monkeypatch.setattr(entwurfsbuch, "abgleich", _nein)
    assert "Buch gesperrt" in _lauf().grund


def test_ein_unerwarteter_fehler_nach_dem_ersten_zug_verliert_ihn_nicht(monkeypatch, tmp_path):
    server, uid, profil = _fall1(monkeypatch, tmp_path)
    echt = entwurfsablage._ziehe
    gerufen = []

    def ziehe(*a, **k):
        if gerufen:
            raise RuntimeError("unerwartet")
        gerufen.append(1)
        return echt(*a, **k)
    monkeypatch.setattr(entwurfsablage, "_ziehe", ziehe)
    monkeypatch.setattr(entwurfsbuch, "abgleich", _doppelt(entwurfsbuch.abgleich))
    bericht = _lauf(profil)
    assert bericht.verschoben == (str(uid),) and "unerwartet" in bericht.grund
    assert len(server.ordner[PAPIERKORB]) == 1


def _doppelt(abgleich):
    """Derselbe Entwurf zweimal im Plan: Der zweite Zug ist der, der scheitert."""
    def lauf(*a, **k):
        stand = abgleich(*a, **k)
        return stand._replace(zustaende=(*stand.zustaende, stand.zustaende[0]))
    return lauf


def test_kein_fenster_laesst_die_automatik_aus(mail_lauf, monkeypatch):
    """#415: Ein solcher Lauf spricht die Brücke nicht an, auch nicht zum Lesen."""
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    gerufen = _mitschrift(monkeypatch)
    assert mail_lauf(ALTER_TEXT, "--kein-fenster") == falzmarke.EXIT_OK
    assert gerufen == []


def test_ohne_oeffnen_kein_postfachzugriff(mail_lauf, monkeypatch, tmp_path):
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    _automatik(monkeypatch, AssertionError("lief ohne --oeffnen"))
    quelle = tmp_path / "ohne.md"
    quelle.write_text(QUELLE.format(text=ALTER_TEXT), encoding="utf-8")
    assert falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE),
                           "-o", str(tmp_path / "ohne")]) == falzmarke.EXIT_OK


# ── Die Quelle selbst ───────────────────────────────────────────────────────

PAKET = Path(entwurfsablage.__file__).parent


def test_das_modul_kennt_genau_einen_aendernden_befehl():
    baum = ast.parse(Path(entwurfsablage.__file__).read_text(encoding="utf-8"))
    befehle = _befehlswoerter(baum)
    assert "MOVE" in befehle, "die Prüfung sieht den ändernden Befehl nicht"
    assert not befehle & {"COPY", "STORE", "EXPUNGE", "DELETE", "CREATE", "RENAME",
                          "APPEND"}, befehle
    zugriffe = {k.attr for k in ast.walk(baum) if isinstance(k, ast.Attribute)}
    assert not zugriffe & {"store", "expunge", "copy", "move", "delete", "create", "rename",
                           "send", "sendmail", "send_message", "ablegen"}, zugriffe
    assert {"uid", "select"} <= zugriffe, "die Prüfung sieht die Zugriffe nicht"
    importe = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            importe |= {a.name.split(".")[0] for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom):
            importe.add((knoten.module or "").split(".")[0])
    assert not importe & {"smtplib", "subprocess", "socket", "imaplib"}, importe


def test_gegenprobe_die_quellpruefung_saehe_ein_hartes_loeschen():
    """So stünde das Löschen in `verschiebe`: als weitergereichtes Argument."""
    quelle = Path(entwurfsablage.__file__).read_text(encoding="utf-8")
    sabotiert = quelle.replace('sitzung._v.uid, "MOVE", str(uid), zitiert(ziel))',
                               'sitzung._v.uid, "STORE", str(uid), "+FLAGS", zitiert(ziel))')
    assert sabotiert != quelle, "die Sabotage hat nichts ersetzt"
    assert "STORE" in _befehlswoerter(ast.parse(sabotiert))


def test_nur_die_zwei_ablage_module_bewegen_etwas():
    bewegen = {datei.name for datei in PAKET.glob("*.py")
               if "MOVE" in _befehlswoerter(ast.parse(datei.read_text(encoding="utf-8")))}
    assert bewegen == {"ablage.py", "entwurfsablage.py"}
