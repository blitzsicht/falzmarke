"""Der Entwurf liegt im Postfach, nicht in einem Fenster (ADR 0051, Entscheidung 2).

ANLASS (21.10.2026): Der Entwurf aus `thunderbird -compose` trug kein
`In-Reply-To` — die Antwort hing nicht im Verlauf. Und als das Fenster weg
war, schloss eine Sitzung „nicht gesendet“ und öffnete neu; die Mail ging
zweimal hinaus. Im Thunderbird-Weg legt `--oeffnen` die fertige `.eml` deshalb
per `APPEND` in den Entwürfe-Ordner des Absenders, wenn der Proxy erreichbar
ist — mit allen Kopfzeilen. **Dann gibt es kein `-compose`**: zwei Entwürfe
wären genau der Fehler aus #287.

Kein Test hier startet ein Programm oder öffnet eine Verbindung. Thunderbird
ist die Attrappe aus `test_oeffnen.py`, der Proxy die aus `imap_attrappe.py`.
"""

from __future__ import annotations

import email
import functools
import re
from datetime import datetime, timezone
from email import policy
from pathlib import Path

import pytest

from bruecke_attrappe import BrueckenAttrappe
from conftest import PROFILE
from falzmarke import bruecke
from falzmarke import cli as falzmarke
from falzmarke import eml as eml_modul
from falzmarke import oeffnen, postfach
from imap_attrappe import ImapAttrappe, nachricht
from test_oeffnen import THUNDERBIRD_PFAD, Thunderbird

ABSENDER = "muster@example.de"
BETREFF = "AW: Sommerfest – Programm"

MAIL = f"""---
typ: email
profil: example
an: Paula Beispiel <paula@example.org>
betreff: "{BETREFF}"
antwort_auf: "<vorher@example.org>"
anrede: Hallo Paula,
---
danke für die Unterlagen zum Sommerfest, anbei der Lageplan.
"""


@pytest.fixture(autouse=True)
def _keine_dateiuebergabe(monkeypatch):
    """Der Rückfall auf die Datei startet `open` — hier nie wirklich.

    Gemessen beim Schreiben dieser Datei: Ohne diesen Riegel lief ein Test über
    den Rückfall bis zu einem echten `open` auf die Test-`.eml`.
    """
    def _nein(*_a, **_k):
        raise AssertionError("ein Test wollte wirklich eine Datei übergeben")

    monkeypatch.setattr(oeffnen, "_fuehre_aus", _nein)


@pytest.fixture
def eml_pfad(tmp_path) -> Path:
    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / "antwort", profil_verzeichnis=PROFILE)
    return pfad


@pytest.fixture
def felder(eml_pfad) -> dict:
    return eml_modul.entwurfsfelder(eml_pfad)


def _entwurf(felder, tb, **k):
    return oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0"},
                           laufen=tb, binaer=lambda: THUNDERBIRD_PFAD, **k)


def _server(monkeypatch, entwuerfe=(), **k) -> ImapAttrappe:
    attrappe = ImapAttrappe({"Entw&APw-rfe": list(entwuerfe)}, **k)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    return attrappe


def _vorhanden(betreff=BETREFF, an="paula@example.org"):
    zeit = datetime(2026, 10, 21, 18, 31, tzinfo=timezone.utc)
    return nachricht(an=an, betreff=betreff, datum=zeit, von=ABSENDER), zeit


# ── Die Felder ──────────────────────────────────────────────────────────────

def test_die_felder_tragen_die_datei_als_bytes(eml_pfad, felder):
    assert felder["roh"] == eml_pfad.read_bytes()


# ── Der Weg ─────────────────────────────────────────────────────────────────

def test_mit_proxy_liegt_der_entwurf_im_postfach_und_kein_fenster(monkeypatch, eml_pfad, felder):
    server = _server(monkeypatch)
    tb = Thunderbird()
    lage = _entwurf(felder, tb)
    (append,) = server.befehle("APPEND")
    assert append[1] == "Entw&APw-rfe" and append[2] == "(\\Draft \\Seen)"
    assert server.ordner["Entw&APw-rfe"][-1].roh == eml_pfad.read_bytes()
    assert tb.compose == [], "Postfach-Entwurf UND -compose — zwei Entwürfe (#287)"
    assert lage.programm == "Thunderbird"
    assert lage.postfach is not None
    assert lage.postfach.adresse == ABSENDER
    assert lage.postfach.ordner == "Entwürfe"
    assert lage.postfach.betreff == BETREFF
    assert (lage.postfach.vorher, lage.postfach.nachher) == (0, 1)


def test_der_bezug_wird_im_abgelegten_entwurf_nachgelesen(monkeypatch, felder):
    _server(monkeypatch)
    lage = _entwurf(felder, Thunderbird())
    assert lage.postfach.bezug is True
    assert lage.postfach.fassung is True


def test_ohne_proxy_bleibt_es_bei_compose_mit_grund(monkeypatch, felder):
    attrappe = ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused"))
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    tb = Thunderbird()
    lage = _entwurf(felder, tb)
    assert len(tb.compose) == 1
    assert lage.programm == "Thunderbird" and lage.postfach is None
    assert "127.0.0.1:1993" in lage.postfach_grund


def test_ein_entwurf_an_dieselbe_adresse_mit_demselben_betreff_liegt_schon(monkeypatch, felder):
    server = _server(monkeypatch, [_vorhanden()])
    tb = Thunderbird()
    lage = _entwurf(felder, tb)
    assert server.befehle("APPEND") == [] and tb.compose == []
    assert lage.programm is None and lage.schon_da
    assert BETREFF in lage.schon_da and "21.10.2026" in lage.schon_da
    assert len(server.ordner["Entw&APw-rfe"]) == 1


def test_noch_ein_entwurf_legt_trotzdem_ab(monkeypatch, felder):
    server = _server(monkeypatch, [_vorhanden()])
    lage = _entwurf(felder, Thunderbird(), noch_ein_entwurf=True)
    assert len(server.befehle("APPEND")) == 1
    assert (lage.postfach.vorher, lage.postfach.nachher) == (1, 2)


def test_ein_anderer_betreff_ist_kein_doppel(monkeypatch, felder):
    server = _server(monkeypatch, [_vorhanden(betreff="Termin")])
    _entwurf(felder, Thunderbird())
    assert len(server.befehle("APPEND")) == 1


def test_ein_anderer_empfaenger_ist_kein_doppel(monkeypatch, felder):
    server = _server(monkeypatch, [_vorhanden(an="jonas@example.com")])
    _entwurf(felder, Thunderbird())
    assert len(server.befehle("APPEND")) == 1


def test_nicht_wiedergefunden_ist_ungewiss_und_kein_fenster(monkeypatch, felder):
    _server(monkeypatch, append_wirkt=False)
    tb = Thunderbird()
    lage = _entwurf(felder, tb)
    assert lage.programm is None and lage.ungewiss
    assert tb.compose == [], "ungewiss heißt: nichts nachschieben"


def test_ein_abgerissenes_append_ist_ungewiss(monkeypatch, felder):
    _server(monkeypatch, append_fehler=TimeoutError("timed out"))
    tb = Thunderbird()
    lage = _entwurf(felder, tb)
    assert lage.programm is None and lage.ungewiss
    assert tb.compose == []


def test_outlook_fragt_das_postfach_nicht(monkeypatch, felder):
    server = _server(monkeypatch)

    def osascript(argv, **_k):
        import subprocess
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="nicht da")

    oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0"},
                    laufen=osascript, wahl="outlook")
    assert server.verbindungen == []


def test_abgeschaltet_bleibt_es_bei_compose(monkeypatch, felder):
    server = _server(monkeypatch)
    tb = Thunderbird()
    lage = oeffnen.entwurf(felder, plattform="darwin",
                           umgebung={"DISPLAY": ":0", "FALZMARKE_POSTFACH": "nie"},
                           laufen=tb, binaer=lambda: THUNDERBIRD_PFAD)
    assert server.verbindungen == [] and len(tb.compose) == 1
    assert "FALZMARKE_POSTFACH=nie" in lage.postfach_grund


def test_handgebaute_felder_ohne_bytes_gehen_den_alten_weg(monkeypatch, felder):
    server = _server(monkeypatch)
    tb = Thunderbird()
    _entwurf({k: v for k, v in felder.items() if k != "roh"}, tb)
    assert server.verbindungen == [] and len(tb.compose) == 1


def test_der_entwuerfe_ordner_kommt_aus_thunderbird(monkeypatch, felder, tmp_path):
    from test_thunderbird_signatur import _attrappe, _grundwerte

    ordner = _attrappe(tmp_path, _grundwerte(
        draft_folder="imap://muster%40example.de@outlook.office365.com/Meine Entwürfe"))
    server = ImapAttrappe({"Meine Entw&APw-rfe": []})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
    lage = _entwurf(felder, Thunderbird(), thunderbird_ordner=ordner)
    assert server.befehle("APPEND")[0][1] == "Meine Entw&APw-rfe"
    assert lage.postfach.ordner == "Meine Entwürfe"
    assert not server.befehle("LIST")


def test_ein_ordner_eines_anderen_kontos_zaehlt_nicht(monkeypatch, felder, tmp_path):
    """Liegen die Entwürfe der Identität in einem anderen Konto, ist dort nicht
    angemeldet — dann LIST im eigenen Postfach."""
    from test_thunderbird_signatur import _attrappe, _grundwerte

    ordner = _attrappe(tmp_path, _grundwerte(
        draft_folder="imap://jemand%40example.org@outlook.office365.com/Fremd"))
    server = _server(monkeypatch)
    _entwurf(felder, Thunderbird(), thunderbird_ordner=ordner)
    assert server.befehle("APPEND")[0][1] == "Entw&APw-rfe"


# ── Der Befehl ──────────────────────────────────────────────────────────────

@pytest.fixture
def befehl(tmp_path, monkeypatch):
    """`email --oeffnen` mit echtem `entwurf`, aber Thunderbird und Proxy als Attrappe."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("FALZMARKE_OEFFNEN", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    tb = Thunderbird()
    echt = oeffnen.entwurf
    monkeypatch.setattr(oeffnen, "entwurf", functools.partial(
        echt, plattform="darwin", umgebung={"DISPLAY": ":0"}, laufen=tb,
        binaer=lambda: THUNDERBIRD_PFAD))
    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")

    def lauf(*extra):
        return falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE), "--oeffnen",
                               *extra])
    lauf.tb = tb
    return lauf


def test_befehl_meldet_den_postfach_entwurf(befehl, monkeypatch, capsys):
    _server(monkeypatch)
    code = befehl()
    ausgabe = capsys.readouterr()
    assert code == 0
    assert f"OK  Entwurf liegt in „Entwürfe“ von {ABSENDER}: {BETREFF}" in ausgabe.out
    assert "In-Reply-To" in ausgabe.out
    assert "trägt den Bezug zur Vorgängernachricht NICHT" not in ausgabe.err
    assert "nachgezählt ist nichts" not in ausgabe.err
    assert "ABSENDER PRÜFEN" not in ausgabe.err
    assert "vermutlich" in ausgabe.err, "die Signatur-Annahme ist nicht gekennzeichnet"
    assert befehl.tb.compose == []


def test_befehl_meldet_einen_liegenden_entwurf(befehl, monkeypatch, capsys):
    server = _server(monkeypatch, [_vorhanden()])
    code = befehl()
    ausgabe = capsys.readouterr()
    assert code == 0
    assert "ENTWURF LIEGT SCHON  " in ausgabe.err
    assert "--noch-ein-entwurf" in ausgabe.err
    assert "OK  geöffnet" not in ausgabe.out, "trotzdem die Datei übergeben"
    assert server.befehle("APPEND") == [] and befehl.tb.compose == []


def test_befehl_reicht_noch_ein_entwurf_durch(befehl, monkeypatch, capsys):
    server = _server(monkeypatch, [_vorhanden()])
    assert befehl("--noch-ein-entwurf") == 0
    assert len(server.befehle("APPEND")) == 1


def test_befehl_ohne_proxy_sagt_warum_compose(befehl, monkeypatch, capsys):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert "OK  Entwurf angelegt: Thunderbird" in ausgabe.out
    assert "kein Postfach-Entwurf" in ausgabe.err
    assert len(befehl.tb.compose) == 1


def test_die_abgelegte_datei_ist_die_gemessene(eml_pfad, felder, monkeypatch):
    """Was im Postfach liegt, ist byte-gleich die Datei, die `verify --email` maß —
    nicht eine zweite Ableitung."""
    server = _server(monkeypatch)
    _entwurf(felder, Thunderbird())
    abgelegt = email.message_from_bytes(server.ordner["Entw&APw-rfe"][-1].roh,
                                        policy=policy.default)
    assert abgelegt["In-Reply-To"] == "<vorher@example.org>"
    assert abgelegt["X-Falzmarke-Fassung"]
    assert server.ordner["Entw&APw-rfe"][-1].roh == eml_pfad.read_bytes()


# ── Das Fenster (ADR 0054) ──────────────────────────────────────────────────
#
# ANLASS (25.10.2026): „Ich konnte die Entwürfe in Thunderbird nicht öffnen.
# Bitte klick sie selbst an.“ Der Postfach-Entwurf lag richtig, aber kein
# Fenster ging auf. Seitdem ruft `--oeffnen` die Entwurfsbrücke — mit genau dem
# Entwurf, der eben abgelegt wurde, und nie mit einem, dessen Lage ungewiss ist.

def _bruecke(monkeypatch, *a, **k) -> BrueckenAttrappe:
    attrappe = BrueckenAttrappe(*a, **k)
    monkeypatch.setattr(bruecke, "VERBINDEN", attrappe)
    return attrappe


def test_der_abgelegte_entwurf_geht_als_fenster_auf(monkeypatch, felder):
    server = _server(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    lage = _entwurf(felder, Thunderbird())
    neu = server.ordner["Entw&APw-rfe"][-1]
    assert lage.postfach.uid == str(neu.uid)
    assert tb_bruecke.oeffnungen() == [(ABSENDER, neu.uid)]
    assert lage.fenster.offen


def test_der_liegende_entwurf_geht_auf_statt_eines_zweiten(monkeypatch, felder):
    server = _server(monkeypatch, [_vorhanden()])
    tb_bruecke = _bruecke(monkeypatch)
    lage = _entwurf(felder, Thunderbird())
    (liegend,) = server.ordner["Entw&APw-rfe"]
    assert server.befehle("APPEND") == []
    assert tb_bruecke.oeffnungen() == [(ABSENDER, liegend.uid)]
    assert lage.schon_da and lage.fenster.offen


@pytest.mark.parametrize("art", [{"append_wirkt": False},
                                 {"append_fehler": TimeoutError("timed out")}])
def test_bei_ungewisser_lage_ruft_niemand_die_bruecke(monkeypatch, felder, art):
    _server(monkeypatch, **art)
    tb_bruecke = _bruecke(monkeypatch)
    lage = _entwurf(felder, Thunderbird())
    assert lage.ungewiss and lage.fenster is None
    assert tb_bruecke.anfragen == []


def test_ohne_postfach_ruft_niemand_die_bruecke(monkeypatch, felder):
    """Der `-compose`-Weg öffnet sein Fenster selbst; ein Zuruf öffnete ein zweites."""
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    tb_bruecke = _bruecke(monkeypatch)
    tb = Thunderbird()
    lage = _entwurf(felder, tb)
    assert len(tb.compose) == 1 and tb_bruecke.anfragen == []
    assert lage.fenster is None


def test_ohne_bruecke_liegt_der_entwurf_trotzdem(monkeypatch, felder):
    server = _server(monkeypatch)
    _bruecke(monkeypatch, fehler=ConnectionRefusedError(61, "refused"))
    tb = Thunderbird()
    lage = _entwurf(felder, tb)
    assert len(server.befehle("APPEND")) == 1 and tb.compose == []
    assert lage.programm == "Thunderbird" and lage.fenster.zustand == "fehler"


def test_befehl_meldet_das_offene_fenster(befehl, monkeypatch, capsys):
    _server(monkeypatch)
    _bruecke(monkeypatch, {"ok": True, "zustand": "geoeffnet", "betreff": BETREFF})
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert f"OK  Entwurf offen in Thunderbird: {BETREFF}" in ausgabe.out
    assert "Es geht kein Fenster auf" not in ausgabe.err


def test_befehl_ohne_bruecke_sagt_warum_kein_fenster(befehl, monkeypatch, capsys):
    _server(monkeypatch)
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert "OK  Entwurf offen" not in ausgabe.out
    assert "Es geht kein Fenster auf" in ausgabe.err
    assert "Entwurfsbrücke: am Socket im Thunderbird-Profil antwortet nichts" in ausgabe.err


def test_befehl_bei_ungewissem_fenster_warnt_vor_dem_zweiten(befehl, monkeypatch, capsys):
    _server(monkeypatch)
    _bruecke(monkeypatch, {"ok": True, "zustand": "ungewiss"})
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert "Fenster ungewiss" in ausgabe.err and "nicht noch einmal öffnen" in ausgabe.err


def test_befehl_oeffnet_den_liegenden_entwurf(befehl, monkeypatch, capsys):
    _server(monkeypatch, [_vorhanden()])
    _bruecke(monkeypatch, {"ok": True, "zustand": "geoeffnet", "betreff": BETREFF})
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert "ENTWURF LIEGT SCHON" in ausgabe.err
    assert f"OK  Entwurf offen in Thunderbird: {BETREFF}" in ausgabe.out


# ── Der Befehl `entwurf-oeffnen` ────────────────────────────────────────────

def _profil_mit_entwuerfen(monkeypatch, tmp_path, draft_folder):
    from test_thunderbird_signatur import _attrappe, _grundwerte

    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER",
                        _attrappe(tmp_path, _grundwerte(draft_folder=draft_folder)))


@pytest.fixture
def oeffne_befehl(monkeypatch, tmp_path):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("FALZMARKE_OEFFNEN", raising=False)
    monkeypatch.delenv("FALZMARKE_BRUECKE", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    _profil_mit_entwuerfen(monkeypatch, tmp_path,
                           "imap://muster%40example.de@outlook.office365.com/Entw&APw-rfe")

    def lauf(*argumente):
        return falzmarke.main(["entwurf-oeffnen", "--absender", ABSENDER, *argumente])
    return lauf


def _zwei_entwuerfe(monkeypatch):
    return _server(monkeypatch, [_vorhanden("Nachtrag S1: Logo"),
                                 _vorhanden("Vektor S2: Wappen", an="b@example.org")])


def test_entwurf_oeffnen_ohne_suche_listet_nur(oeffne_befehl, monkeypatch, capsys):
    _zwei_entwuerfe(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    assert oeffne_befehl() == 0
    ausgabe = capsys.readouterr().out
    assert "2 Entwürfe in „Entwürfe“" in ausgabe and "Vektor S2: Wappen" in ausgabe
    assert tb_bruecke.oeffnungen() == []
    assert [a["befehl"] for a in tb_bruecke.anfragen] == ["ping"]
    assert "OK  Entwurfsbrücke 0.1.1 in Thunderbird 158.0.1" in ausgabe


def test_entwurf_oeffnen_liste_sagt_wenn_keine_bruecke_antwortet(oeffne_befehl, monkeypatch,
                                                                  capsys):
    _zwei_entwuerfe(monkeypatch)
    assert oeffne_befehl() == 0
    ausgabe = capsys.readouterr()
    assert "2 Entwürfe" in ausgabe.out and "OK  Entwurfsbrücke" not in ausgabe.out
    assert "HINWEIS  Entwurfsbrücke: am Socket im Thunderbird-Profil antwortet nichts" in ausgabe.err


def test_entwurf_oeffnen_nach_betreff(oeffne_befehl, monkeypatch, capsys):
    server = _zwei_entwuerfe(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch, {"ok": True, "zustand": "geoeffnet",
                                        "betreff": "Vektor S2: Wappen"})
    assert oeffne_befehl("--betreff", "wappen") == 0
    gesucht = server.ordner["Entw&APw-rfe"][1]
    assert tb_bruecke.oeffnungen() == [(ABSENDER, gesucht.uid)]
    assert "OK  Entwurf offen in Thunderbird: Vektor S2: Wappen" in capsys.readouterr().out


def test_entwurf_oeffnen_bei_mehreren_oeffnet_nichts(oeffne_befehl, monkeypatch, capsys):
    _zwei_entwuerfe(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    assert oeffne_befehl("--betreff", "S") == 1
    assert "MEHRERE ENTWÜRFE  2 passen" in capsys.readouterr().err
    assert tb_bruecke.anfragen == []


def test_entwurf_oeffnen_nach_uid(oeffne_befehl, monkeypatch, capsys):
    server = _zwei_entwuerfe(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    erster = server.ordner["Entw&APw-rfe"][0]
    assert oeffne_befehl("--uid", str(erster.uid)) == 0
    assert tb_bruecke.oeffnungen() == [(ABSENDER, erster.uid)]


def test_entwurf_oeffnen_ohne_treffer(oeffne_befehl, monkeypatch, capsys):
    _zwei_entwuerfe(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    assert oeffne_befehl("--betreff", "gibt es nicht") == 1
    assert "KEIN ENTWURF" in capsys.readouterr().err and tb_bruecke.anfragen == []


def test_entwurf_oeffnen_ohne_bruecke_ist_exit_3(oeffne_befehl, monkeypatch, capsys):
    _zwei_entwuerfe(monkeypatch)
    assert oeffne_befehl("--betreff", "wappen") == 3
    assert "Entwurfsbrücke: am Socket im Thunderbird-Profil antwortet nichts" in capsys.readouterr().err


def test_entwurf_oeffnen_ohne_bildschirm_ruft_niemanden(oeffne_befehl, monkeypatch, capsys):
    _zwei_entwuerfe(monkeypatch)
    monkeypatch.setenv("FALZMARKE_OEFFNEN", "nie")
    tb_bruecke = _bruecke(monkeypatch)
    assert oeffne_befehl("--betreff", "wappen") == 3
    assert tb_bruecke.anfragen == []


def test_entwurf_oeffnen_ohne_thunderbird_profil_oeffnet_nichts(oeffne_befehl, monkeypatch,
                                                                 capsys, tmp_path):
    """Ohne Profil kommt der Ordner vom Server. Ob Thunderbird dieselbe UID
    im selben Ordner führt, weiß dann niemand."""
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER", tmp_path / "kein-profil")
    server = _zwei_entwuerfe(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    assert oeffne_befehl("--uid", str(server.ordner["Entw&APw-rfe"][0].uid)) == 3
    assert "NICHT GEÖFFNET  Thunderbird nennt für" in capsys.readouterr().err
    assert tb_bruecke.anfragen == []


def test_entwurf_oeffnen_mit_entwuerfen_in_fremdem_konto_oeffnet_nichts(oeffne_befehl,
                                                                         monkeypatch, capsys,
                                                                         tmp_path):
    """Die Brücke nähme den Ordner des anderen Kontos, die UID stammt aus diesem."""
    _profil_mit_entwuerfen(monkeypatch, tmp_path / "fremd",
                           "imap://jemand%40example.org@outlook.office365.com/Entw&APw-rfe")
    server = _zwei_entwuerfe(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    assert oeffne_befehl("--uid", str(server.ordner["Entw&APw-rfe"][0].uid)) == 3
    assert "NICHT GEÖFFNET" in capsys.readouterr().err
    assert tb_bruecke.anfragen == []


def test_der_aufrufer_wartet_laenger_als_das_add_on():
    """Sonst meldet `entwurf-oeffnen` „ungewiss“, und das Fenster geht danach doch auf."""
    quelle = (Path(__file__).parent.parent / "thunderbird" / "entwurfsbruecke"
              / "implementation.js").read_text(encoding="utf-8")
    frist = {name: int(wert) / 1000 for name, wert
             in re.findall(r"^const (FRIST_\w+_MS) = (\d+);", quelle, re.M)}
    # Ordner nachladen, dann zweimal warten: aufs Fenster und auf den Entwurf darin.
    # Die Menge ist geschlossen, damit eine neue Frist im Add-on hier auffällt
    # und nicht still an der Rechnung vorbeiläuft.
    assert set(frist) == {"FRIST_ORDNER_MS", "FRIST_FENSTER_MS", "FRIST_LEERLAUF_MS"}
    assert bruecke.FRIST_OEFFNEN_S > frist["FRIST_ORDNER_MS"] + 2 * frist["FRIST_FENSTER_MS"]
    # Die Leerlauffrist zählt in dieser Rechnung nicht mit: Sie läuft nur, bis
    # eine vollständige Zeile da ist, und falzmarke schickt sie sofort
    # (`clearTimeout(leerlauf)` beim ersten Zeilenende, ADR 0059). Was sie
    # abschneidet, ist eine Verbindung, die nichts sagt.
    assert "clearTimeout(leerlauf);" in quelle


def test_entwurf_oeffnen_ohne_proxy_ist_exit_3(oeffne_befehl, monkeypatch, capsys):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    assert oeffne_befehl("--betreff", "x") == 3
    assert "FEHLER  Postfach von" in capsys.readouterr().err
