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
from falzmarke import bruecke, entwurfsbuch
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


# ── --kein-fenster ohne Postfach (#441) ─────────────────────────────────────
#
# Der Abholer in siluri-angebote ruft alle 180 s kopflos auf. Fällt der Proxy
# aus, öffnete jeder Takt ein `-compose`-Fenster, und scheiterte auch das, ging
# die Datei als Lesefenster auf. Die Gegenprobe ohne Schalter ist
# `test_befehl_ohne_proxy_sagt_warum_compose` direkt darüber: derselbe Aufbau,
# genau ein `-compose`.

def _datei_uebergaben(monkeypatch) -> list:
    uebergeben: list = []
    monkeypatch.setattr(oeffnen, "oeffne", lambda pfad, **k: uebergeben.append(pfad))
    return uebergeben


def test_kein_fenster_ohne_proxy_oeffnet_nichts_und_endet_mit_exit_3(befehl, monkeypatch,
                                                                     capsys):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    uebergeben = _datei_uebergaben(monkeypatch)
    code = befehl("--kein-fenster")
    ausgabe = capsys.readouterr()
    assert befehl.tb.compose == [], "-compose trotz --kein-fenster"
    assert uebergeben == [], "die Datei ging trotz --kein-fenster auf"
    assert code == falzmarke.EXIT_UMGEBUNG, f"Exit {code} ohne Entwurf"
    assert "KEIN ENTWURF  kein Postfach-Entwurf: kein IMAP-Proxy unter" in ausgabe.err
    assert "Die geprüfte Nachricht liegt hier:" in ausgabe.err
    assert "OK  Entwurf" not in ausgabe.out


def test_kein_fenster_ohne_entwurfsweg_uebergibt_auch_die_datei_nicht(befehl, monkeypatch,
                                                                      capsys):
    """Kein Weg zum Entwurf, etwa kein Mailprogramm. Ohne Schalter geht die Datei auf."""
    monkeypatch.setattr(oeffnen, "entwurf",
                        lambda felder, **k: oeffnen.Entwurfslage(None, "kein Mailprogramm"))
    uebergeben = _datei_uebergaben(monkeypatch)
    assert befehl() == 0 and len(uebergeben) == 1                          # Gegenprobe
    capsys.readouterr()
    code = befehl("--kein-fenster")
    assert len(uebergeben) == 1, "die Datei ging trotz --kein-fenster auf"
    assert code == falzmarke.EXIT_UMGEBUNG, f"Exit {code} ohne Entwurf"
    assert "KEIN ENTWURF  kein Mailprogramm" in capsys.readouterr().err


def test_kein_fenster_mit_outlook_wird_abgewiesen(befehl, monkeypatch, capsys):
    """Nachreview von #491, Befund 1: Outlook öffnet jeden Entwurf. Die
    Kombination ist ein Eingabefehler, kein „kein Entwurf“."""
    _server(monkeypatch)
    uebergeben = _datei_uebergaben(monkeypatch)
    code = befehl("--programm", "outlook", "--kein-fenster")
    fehler = capsys.readouterr().err
    assert code == falzmarke.EXIT_EINGABE, \
        f"Exit {code}, --programm outlook --kein-fenster nicht abgewiesen"
    assert fehler.startswith("FEHLER  --kein-fenster geht nicht mit --programm outlook")
    assert oeffnen.ohne_fenster_absage("outlook") in fehler, \
        f"Abweisung mit eigener Fassung: {fehler}"
    assert uebergeben == [] and befehl.tb.compose == []


def test_kein_fenster_mit_abgeschaltetem_entwurf_endet_mit_exit_3(befehl, monkeypatch, capsys):
    """Nachreview von #491, Befund 4: `FALZMARKE_ENTWURF=nie` lässt ohne Schalter
    die Datei aufgehen. Mit `--kein-fenster` gibt es die Datei nicht, also Exit 3."""
    _server(monkeypatch)
    monkeypatch.setattr(oeffnen, "entwurf", functools.partial(
        oeffnen.entwurf.func, plattform="darwin",
        umgebung={"DISPLAY": ":0", "FALZMARKE_ENTWURF": "nie"}, laufen=befehl.tb,
        binaer=lambda: THUNDERBIRD_PFAD))
    uebergeben = _datei_uebergaben(monkeypatch)
    assert befehl() == 0 and len(uebergeben) == 1                          # Gegenprobe
    capsys.readouterr()
    code = befehl("--kein-fenster")
    assert len(uebergeben) == 1, "die Datei ging trotz --kein-fenster auf"
    assert code == falzmarke.EXIT_UMGEBUNG, f"Exit {code} ohne Entwurf"
    assert "KEIN ENTWURF  FALZMARKE_ENTWURF=nie ist gesetzt" in capsys.readouterr().err
    assert befehl.tb.compose == []


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


@pytest.mark.parametrize(("kein_fenster", "erwartet_gerufen"), [(True, False), (False, True)])
def test_kein_fenster_haelt_die_bruecke_ganz_heraus(monkeypatch, felder, kein_fenster,
                                                    erwartet_gerufen):
    """#415: Vier Briefe in einer Schleife waren vier Fenster und vier Fokussprünge.

    MIT gegen OHNE in einer Probe: Derselbe Aufbau, nur der Schalter wechselt.
    Ein Test allein auf `lage.fenster is None` wäre erfüllt, bevor der Schalter
    existiert — eine nicht antwortende Brücke liefert dasselbe. Gemessen wird
    deshalb `adressen`: Ohne den Schalter wird der Socket angesprochen, mit ihm
    nicht einmal das.
    """
    server = _server(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    lage = _entwurf(felder, Thunderbird(), kein_fenster=kein_fenster)
    neu = server.ordner["Entw&APw-rfe"][-1]
    assert lage.postfach.uid == str(neu.uid), "der Entwurf liegt in beiden Fällen"
    assert bool(tb_bruecke.adressen) is erwartet_gerufen
    assert bool(tb_bruecke.oeffnungen()) is erwartet_gerufen
    assert (lage.fenster is not None) is erwartet_gerufen


def test_der_befehl_mit_kein_fenster_endet_auf_null(befehl, monkeypatch, capsys):
    """Abnahme #415: Der Lauf kommt ohne Fenster aus und liefert trotzdem Exit 0.

    Dazu die Gegenprobe im selben Durchgang: Dass keine Fenstermeldung kommt,
    liegt am Schalter, nicht daran, dass die Attrappe nichts liefert — der Lauf
    ohne ihn meldet sie.
    """
    _server(monkeypatch)
    tb_bruecke = _bruecke(monkeypatch)
    assert befehl("--kein-fenster") == 0
    ausgabe = capsys.readouterr()
    assert f"OK  Entwurf liegt in „Entwürfe“ von {ABSENDER}: {BETREFF}" in ausgabe.out
    assert "Entwurf offen in Thunderbird" not in ausgabe.out
    assert tb_bruecke.adressen == []

    assert befehl() == 0
    assert "Entwurf offen in Thunderbird" in capsys.readouterr().out
    assert tb_bruecke.adressen, "ohne den Schalter wird die Brücke gerufen"


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


def _offen_mit(an=("paula@example.org",), kopie=(), blindkopie=(), **mehr) -> dict:
    """Die Antwort ab Add-on 0.3.8: Das Fenster steht, und so würde es schicken (#464)."""
    return {"ok": True, "zustand": "geoeffnet", "betreff": BETREFF, "live": True,
            "identitaet": ABSENDER, "an": list(an), "kopie": list(kopie),
            "blindkopie": list(blindkopie), **mehr}


def _antworten(oeffnung: dict):
    """Je Befehl eine Antwort: `entwurf_oeffnen` wie angegeben, `fenster` ohne Fenster."""
    def antwort(anfrage: dict) -> dict:
        if anfrage.get("befehl") == "entwurf_oeffnen":
            return oeffnung
        if anfrage.get("befehl") == "fenster":
            return {"ok": True, "fenster": []}
        return {"ok": True, "name": "entwurfsbruecke", "version": "0.3.8",
                "thunderbird": "158.0.1"}
    return antwort


def test_befehl_meldet_die_passenden_empfaenger(befehl, monkeypatch, capsys):
    _server(monkeypatch)
    _bruecke(monkeypatch, _offen_mit())
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert f"OK  Entwurf offen in Thunderbird: {BETREFF}" in ausgabe.out
    assert "OK  Empfänger im Fenster wie in der Nachricht: An 1, Cc 0, Bcc 0" in ausgabe.out
    assert "EMPFÄNGER PRÜFEN" not in ausgabe.err
    assert "NICHT GEPRÜFT  Empfänger" not in ausgabe.err


def test_befehl_warnt_wenn_das_fenster_ohne_empfaenger_aufgeht(befehl, monkeypatch, capsys):
    """ANLASS (03.11.2026): Das Fenster stand ohne An, Cc und Bcc da, und hier
    stand `OK`. Jetzt steht `EMPFÄNGER PRÜFEN` statt der grünen Zeile; der Exit
    bleibt 0, der Entwurf liegt ja (ADR 0038)."""
    _server(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=()))
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert "OK  Entwurf offen" not in ausgabe.out
    assert "EMPFÄNGER PRÜFEN  Entwurf offen in Thunderbird" in ausgabe.err
    assert "An: fehlt paula@example.org" in ausgabe.err


def test_ein_zusaetzlicher_empfaenger_im_fenster_faellt_ebenso_auf(befehl, monkeypatch, capsys):
    _server(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=("paula@example.org", "fremd@example.net")))
    assert befehl() == 0
    assert "An: zusätzlich fremd@example.net" in capsys.readouterr().err


def test_befehl_sagt_wenn_das_add_on_die_empfaenger_nicht_meldet(befehl, monkeypatch, capsys):
    """Die Antwort bis 0.3.7 trägt kein `live`: Das Fenster ist grün, die Empfänger nicht."""
    _server(monkeypatch)
    _bruecke(monkeypatch, {"ok": True, "zustand": "geoeffnet", "betreff": BETREFF})
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert f"OK  Entwurf offen in Thunderbird: {BETREFF}" in ausgabe.out
    assert "OK  Empfänger im Fenster" not in ausgabe.out
    assert ("NICHT GEPRÜFT  Empfänger im Fenster: das Add-on meldet die Empfänger des "
            "Fensters nicht (Fassung vor 0.3.8)") in ausgabe.err


@pytest.mark.parametrize(("oeffnung", "fragt"), [
    ({"ok": True, "zustand": "geoeffnet", "betreff": BETREFF}, False),
    ({"ok": True, "zustand": "fenster_ohne_entwurf"}, False),
    ({"ok": True, "zustand": "ungewiss"}, False),
    (_offen_mit(), True),
], ids=["vor_0.3.8", "fenster_ohne_entwurf", "ungewiss", "gelesen"])
def test_das_aufraeumen_fragt_das_fenster_erst_nach_der_lesung(befehl, monkeypatch, capsys,
                                                                oeffnung, fragt):
    """Der Befehl `fenster` an ein noch ladendes Fenster war die Ursache (#464):
    Sagt das Add-on nicht, dass es fertig geladen hat, bleibt er aus. Auch ein
    ungewisses Fenster kann eben noch laden: `fenster_ohne_entwurf` war mit 0.3.7
    eines, dessen Entwurf in 20 Sekunden nicht kam."""
    _server(monkeypatch)
    monkeypatch.delenv("FALZMARKE_AUFRAEUMEN", raising=False)
    tb_bruecke = _bruecke(monkeypatch, _antworten(oeffnung))
    assert befehl() == 0
    assert ("fenster" in [a["befehl"] for a in tb_bruecke.anfragen]) is fragt
    assert ("nicht aufgeräumt" in capsys.readouterr().err) is not fragt


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


def test_entwurf_oeffnen_vergleicht_das_fenster_mit_dem_entwurf(oeffne_befehl, monkeypatch,
                                                                 capsys):
    """Den Maßstab liest der Befehl aus `Kopf.empfaenger`, nicht aus `Kopf.an`:
    Der wirft An, Cc und Bcc zusammen."""
    _zwei_entwuerfe(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), betreff="Vektor S2: Wappen"))
    assert oeffne_befehl("--betreff", "wappen") == 0
    assert ("OK  Empfänger im Fenster wie in der Nachricht: An 1, Cc 0, Bcc 0"
            in capsys.readouterr().out)


def _entwurf_mit_kopien(monkeypatch):
    roh = nachricht(an="b@example.org", betreff="Vektor S2: Wappen", von=ABSENDER,
                    kopf={"Cc": "Carla <C@example.org>", "Bcc": "archiv@example.de"},
                    datum=datetime(2026, 10, 21, 18, 31, tzinfo=timezone.utc))
    return _server(monkeypatch, [(roh, datetime(2026, 10, 21, 18, 31, tzinfo=timezone.utc))])


def test_der_kopf_traegt_an_cc_und_bcc_getrennt():
    """#481: `koepfe` holt To, Cc und Bcc ohnehin. `Kopf.an` wirft sie zusammen,
    `Kopf.empfaenger` hält sie auseinander, klein und ohne Anzeigenamen."""
    roh = nachricht(an="B@example.org", kopf={"Cc": "Carla <C@example.org>",
                                              "Bcc": "archiv@example.de"})
    kopf = postfach.kopf_aus(roh, "7", None)
    assert kopf.an == ("b@example.org", "c@example.org", "archiv@example.de")
    assert kopf.empfaenger == postfach.Empfaenger(
        an=("b@example.org",), kopie=("c@example.org",), blindkopie=("archiv@example.de",))


def test_entwurf_oeffnen_meldet_sich_einmal_an_und_holt_nur_kopfzeilen(oeffne_befehl,
                                                                         monkeypatch, capsys):
    """#481: Bis dahin eine zweite Anmeldung und `BODY.PEEK[]` für den einen
    Treffer. Das war die ganze Nachricht samt Anhängen, gebraucht wurden drei
    Kopfzeilen, die die erste Sitzung schon hatte."""
    server = _entwurf_mit_kopien(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), kopie=("c@example.org",),
                                     blindkopie=("archiv@example.de",),
                                     betreff="Vektor S2: Wappen"))
    assert oeffne_befehl("--betreff", "wappen") == 0
    assert "OK  Empfänger im Fenster wie in der Nachricht: An 1, Cc 1, Bcc 1" in capsys.readouterr().out
    abrufe = [befehl[2] for befehl in server.befehle("UID FETCH")]
    assert len(server.angemeldet) == 1, f"{len(server.angemeldet)} Anmeldungen am Postfach"
    assert abrufe and all("HEADER.FIELDS" in teile for teile in abrufe), (
        f"ein Abruf ohne Feldliste holt die ganze Nachricht: {abrufe}")


def test_entwurf_oeffnen_sieht_ein_fehlendes_cc(oeffne_befehl, monkeypatch, capsys):
    """Die Trennung trägt: Steht die Kopie im Fenster nicht, fehlt sie im Cc und
    nirgends sonst. Mit `Kopf.an` als Maßstab stünde sie unter An."""
    _entwurf_mit_kopien(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), blindkopie=("archiv@example.de",),
                                     betreff="Vektor S2: Wappen"))
    assert oeffne_befehl("--betreff", "wappen") == 3
    fehler = capsys.readouterr().err
    assert "EMPFÄNGER PRÜFEN" in fehler and "Cc: fehlt c@example.org" in fehler
    assert "An: " not in fehler and "Bcc: " not in fehler, fehler


# ── Der Absender im Fenster (#482) ──────────────────────────────────────────

ALIAS = "alias@example.de"
FREMD = "andere@example.org"          # Identität des zweiten Kontos in `_grundwerte`


def _profil_mit_alias(monkeypatch, tmp_path):
    """Konto 1 trägt ABSENDER und ALIAS, Konto 2 nur FREMD."""
    from test_thunderbird_signatur import _attrappe, _grundwerte

    werte = _grundwerte(draft_folder="imap://muster%40example.de@outlook.office365.com/"
                                     "Entw&APw-rfe")
    werte["mail.account.account1.identities"] = "id1,id3"
    werte["mail.identity.id3.useremail"] = ALIAS.upper()
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER", _attrappe(tmp_path / "alias", werte))


def test_kontoadressen_nennt_die_identitaeten_eines_kontos(monkeypatch, tmp_path):
    """Über `kontoleser`, wie `_offene_uids` und `absender_pruefen` fragen. Bis #522
    (Punkt 7) prüfte diese Probe `oeffnen.kontoadressen`, das niemand mehr aufrief."""
    _profil_mit_alias(monkeypatch, tmp_path)
    konto = entwurfsbuch.kontoleser({})
    assert konto(ABSENDER) == (frozenset({ABSENDER, ALIAS}), "")
    assert konto(ALIAS) == (frozenset({ABSENDER, ALIAS}), "")
    assert konto(FREMD) == (frozenset({FREMD}), "")
    adressen, grund = konto("niemand@example.net")
    assert adressen is None and "kein Konto mit niemand@example.net" in grund


def test_kontoadressen_ohne_profil_raet_nicht(tmp_path):
    adressen, grund = entwurfsbuch.kontoadressen(ABSENDER, {}, tmp_path / "kein-profil")
    assert adressen is None and "kein Thunderbird-Standardprofil" in grund


def test_kontoadressen_ohne_kontoliste_raet_nicht(monkeypatch, tmp_path):
    """Nachreview #487, Nr. 6: `_identitaeten` zählt ohne Kontoliste alle
    Identitäten, `kontoadressen` bleibt bei `None` (Begründung im Docstring)."""
    from test_thunderbird_signatur import _attrappe

    werte = {"mail.identity.id1.useremail": ABSENDER, "mail.identity.id2.useremail": FREMD}
    ordner = _attrappe(tmp_path / "ohne-liste", werte)
    profil = ordner / "Profiles" / "abcd1234.default-release"
    assert oeffnen._identitaeten(oeffnen.thunderbird_einstellungen(profil)) == ["id1", "id2"]
    adressen, grund = oeffnen.konto_in(oeffnen.thunderbird_einstellungen(profil),
                                       profil.name, ABSENDER)
    assert adressen is None and "nennt keine Konten" in grund


def test_ohne_profil_nennen_beide_den_grund_wortgleich(tmp_path):
    """#506, Befund 7: `profiladressen` und `kontoleser` lösen das Profil über
    `_profil_aus` auf und begründen ein Fehlen gleich. Der Wortlaut steht hier ganz.
    Die zweite Funktion, `oeffnen.kontoadressen`, ist mit #522 (Punkt 7) entfallen."""
    ordner = tmp_path / "kein-profil"
    assert oeffnen.profiladressen(ordner) == (None, f"kein Thunderbird-Profil unter {ordner}")
    fehlt = tmp_path / "weg.default-release"
    assert oeffnen.profiladressen(profil=fehlt) == (None, f"das Thunderbird-Profil {fehlt} fehlt")


def _fenster(identitaet: str, **mehr):
    return bruecke.Oeffnung("geoeffnet", gelesen=True, identitaet=identitaet, **mehr)


@pytest.mark.parametrize("identitaet, geprueft, abweichung, hinweis", [
    (ABSENDER.upper(), True, "", ""),
    (ALIAS, True, "", f"{ALIAS} ist eine Identität im selben Konto wie {ABSENDER}"),
    (FREMD, True, f"Fenster: {FREMD}, Nachricht: {ABSENDER}", ""),
    ("", False, "", "das Add-on meldet keinen Absender des Fensters"),
], ids=["gleich", "alias", "fremdes-konto", "ohne-meldung"])
def test_absender_pruefen(identitaet, geprueft, abweichung, hinweis, monkeypatch, tmp_path):
    _profil_mit_alias(monkeypatch, tmp_path)
    ergebnis = oeffnen.absender_pruefen(_fenster(identitaet), ABSENDER)
    assert (ergebnis.absender_geprueft, ergebnis.absender_abweichung,
            ergebnis.absender_hinweis) == (geprueft, abweichung, hinweis)


def test_absender_pruefen_ohne_profilwissen_meldet_keinen_fehlalarm():
    """Ohne Konto im Profil ist eine andere Adresse weder Alias noch fremd."""
    ergebnis = oeffnen.absender_pruefen(_fenster(FREMD), ABSENDER)
    assert not ergebnis.absender_geprueft and not ergebnis.absender_abweichung
    assert ergebnis.absender_hinweis.startswith(
        f"das Fenster schickt von {FREMD}, die Nachricht von {ABSENDER}; ob beide")


UNBEKANNT = "unbekannt@example.net"   # in keinem Konto von `_profil_mit_alias`


def test_absender_pruefen_fragt_auch_das_konto_des_fensters(monkeypatch, tmp_path):
    """Nachreview #487, Nr. 1: Der `From` ist keine Identität im Profil, das
    Fenster schickt von einer. Thunderbird kann von `soll` gar nicht senden, das
    ist eine Abweichung und nicht „nicht geprüft“."""
    _profil_mit_alias(monkeypatch, tmp_path)
    ergebnis = oeffnen.absender_pruefen(_fenster(FREMD), UNBEKANNT)
    assert ergebnis.absender_abweichung == f"Fenster: {FREMD}, Nachricht: {UNBEKANNT}", \
        "nur NICHT GEPRÜFT, obwohl das Fenster von einer Identität eines Kontos schickt"
    assert ergebnis.absender_geprueft


def test_absender_pruefen_liest_das_profil_einmal_fuer_beide_adressen(monkeypatch, tmp_path):
    """#515, Befund 6: Der Rückfall auf das Konto des Fensters fragt eine zweite
    Adresse. Bis dahin löste jede Frage das Profil neu auf und las `prefs.js`
    und `user.js` noch einmal."""
    _profil_mit_alias(monkeypatch, tmp_path)
    gelesen = []
    echt = oeffnen.thunderbird_einstellungen
    monkeypatch.setattr(oeffnen, "thunderbird_einstellungen",
                        lambda profil: gelesen.append(profil) or echt(profil))
    ergebnis = oeffnen.absender_pruefen(_fenster(FREMD), UNBEKANNT)
    assert ergebnis.absender_abweichung, "Kontrolle: beide Adressen wurden gefragt"
    assert len(gelesen) == 1, f"das Profil wurde {len(gelesen)}-mal gelesen"


def test_absender_pruefen_kennt_das_profil_keine_der_beiden_bleibt_es_ungeprueft(monkeypatch,
                                                                                tmp_path):
    """Zwilling: Kennt das Profil auch die Adresse des Fensters nicht, wird nicht geraten."""
    _profil_mit_alias(monkeypatch, tmp_path)
    ergebnis = oeffnen.absender_pruefen(_fenster("niemand@example.net"), UNBEKANNT)
    assert not ergebnis.absender_geprueft and not ergebnis.absender_abweichung
    assert f"sagt Thunderbird nicht (kein Konto mit {UNBEKANNT}" in ergebnis.absender_hinweis


def test_entwurf_oeffnen_mit_from_ausserhalb_der_konten_ist_exit_3(oeffne_befehl, monkeypatch,
                                                                   capsys, tmp_path):
    """Derselbe Fall am Befehl: Bis zum Nachreview endete er mit Exit 0."""
    _profil_mit_alias(monkeypatch, tmp_path)
    zeit = datetime(2026, 10, 21, 18, 31, tzinfo=timezone.utc)
    _server(monkeypatch, [(nachricht(an="b@example.org", betreff="Vektor S2: Wappen", datum=zeit,
                                     von=UNBEKANNT), zeit)])
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), betreff="Vektor S2: Wappen",
                                     identitaet=FREMD))
    assert oeffne_befehl("--betreff", "wappen") == 3
    assert f"Fenster: {FREMD}, Nachricht: {UNBEKANNT}" in capsys.readouterr().err


def test_from_ausserhalb_der_konten_nennt_den_richtigen_grund(oeffne_befehl, monkeypatch,
                                                              capsys, tmp_path):
    """#500, Befund 1: Das Fenster schickt von einer Identität eines Kontos, die
    Nachricht stammt von einer Adresse außerhalb. Bis dahin stand „Identität
    außerhalb des Kontos“, also das Gegenteil, und der richtige Grund fiel weg."""
    _profil_mit_alias(monkeypatch, tmp_path)
    zeit = datetime(2026, 10, 21, 18, 31, tzinfo=timezone.utc)
    _server(monkeypatch, [(nachricht(an="b@example.org", betreff="Vektor S2: Wappen", datum=zeit,
                                     von=UNBEKANNT), zeit)])
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), betreff="Vektor S2: Wappen",
                                     identitaet=FREMD))
    assert oeffne_befehl("--betreff", "wappen") == 3
    fehler = capsys.readouterr().err
    assert f"{UNBEKANNT} gehört zu keinem Konto im Profil, {FREMD} schon" in fehler, \
        "ABSENDER PRÜFEN verschweigt, dass die Nachricht von außerhalb der Konten stammt"
    assert "Identität außerhalb des Kontos" not in fehler, fehler


def _alias_nur_am_socket(monkeypatch, tmp_path) -> str:
    """Das Standardprofil kennt den Alias nicht, das Profil am Socket der Brücke
    schon. Gibt den Socketpfad für `FALZMARKE_BRUECKE_SOCKET`."""
    from test_thunderbird_signatur import _attrappe, _grundwerte

    entwuerfe = "imap://muster%40example.de@outlook.office365.com/Entw&APw-rfe"
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER",
                        _attrappe(tmp_path / "a", _grundwerte(draft_folder=entwuerfe)))
    werte = _grundwerte(draft_folder=entwuerfe)
    werte["mail.account.account1.identities"] = "id1,id3"
    werte["mail.identity.id3.useremail"] = ALIAS
    profil_b = _attrappe(tmp_path / "b", werte) / "Profiles" / "abcd1234.default-release"
    return str(profil_b / bruecke.SOCKET_DATEI)


def test_entwurf_oeffnen_liest_die_aliasse_aus_dem_profil_der_bruecke(oeffne_befehl,
                                                                      monkeypatch, capsys,
                                                                      tmp_path):
    """Nachreview #487, Nr. 2: Das Fenster kommt aus dem Profil am Socket, also
    auch die Identitäten, gegen die es geprüft wird. Zwilling ohne Schalter: Das
    Standardprofil kennt den Alias nicht, und derselbe Aufbau wird rot."""
    socket = _alias_nur_am_socket(monkeypatch, tmp_path)
    _zwei_entwuerfe(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), betreff="Vektor S2: Wappen",
                                     identitaet=ALIAS))
    monkeypatch.setenv("FALZMARKE_BRUECKE_SOCKET", socket)
    assert oeffne_befehl("--betreff", "wappen") == 0, \
        "der Alias aus dem Profil der Brücke gilt als fremd"
    assert "ABSENDER PRÜFEN" not in capsys.readouterr().err
    monkeypatch.delenv("FALZMARKE_BRUECKE_SOCKET")
    assert oeffne_befehl("--betreff", "wappen") == 3, "der Zwilling kann gar nicht rot werden"
    assert "ABSENDER PRÜFEN" in capsys.readouterr().err


def test_email_oeffnen_liest_die_aliasse_aus_dem_profil_der_bruecke(monkeypatch, tmp_path):
    """Derselbe Fall an `_fenster_auf`, dem Weg von `email --oeffnen`: Die
    Umgebung des Laufs bestimmt den Socket und damit das Profil."""
    socket = _alias_nur_am_socket(monkeypatch, tmp_path)
    _bruecke(monkeypatch, _offen_mit(identitaet=ALIAS))
    lage = oeffnen.Entwurfslage(None, "", schon_da="Di 18:31", schon_da_uid="7")
    felder = {"absender": ABSENDER, "an": ["paula@example.org"]}

    def abweichung(umgebung) -> str:
        return oeffnen._fenster_auf(lage, felder, umgebung).fenster.absender_abweichung

    assert abweichung({}) == f"Fenster: {ALIAS}, Nachricht: {ABSENDER}", \
        "der Zwilling kann gar nicht rot werden"
    assert abweichung({"FALZMARKE_BRUECKE_SOCKET": socket}) == "", \
        "email --oeffnen: der Alias aus dem Profil der Brücke gilt als fremd"


def test_ohne_profil_am_socket_nennt_nicht_geprueft_den_grund_der_bruecke(monkeypatch, tmp_path):
    """#500, Befund 2: Liegt der Socket außerhalb eines Profils, und es gibt kein
    Standardprofil, sagt `bruecken_profil` genau das. Bis dahin ging der Satz
    verloren, und die Zeile nannte nur „kein Thunderbird-Profil unter …“."""
    ohne = tmp_path / "kein-profil"
    ohne.mkdir(parents=True)
    _bruecke(monkeypatch, _offen_mit(identitaet=FREMD))
    lage = oeffnen.Entwurfslage(None, "", schon_da="Di 18:31", schon_da_uid="7")
    felder = {"absender": ABSENDER, "an": ["paula@example.org"]}
    fenster = oeffnen._fenster_auf(lage, felder,
                                   {"FALZMARKE_BRUECKE_SOCKET": str(ohne / "falzmarke.sock")}
                                   ).fenster
    assert not fenster.absender_geprueft and not fenster.absender_abweichung
    assert f"der Socket liegt in {ohne}, das ist kein Thunderbird-Profil" \
        in fenster.absender_hinweis, fenster.absender_hinweis


@pytest.mark.parametrize("modul", ["oeffnen", "cli"])
def test_nur_entwurfsbuch_setzt_profil_der_bruecke_und_konto_zusammen(modul):
    """#500, Befund 2: `oeffnen` und `cli` lösen das Profil der Brücke nicht selbst
    auf, sie fragen `entwurfsbuch` (`kontoleser`, `profiladressen`,
    `thunderbird_ordner`). Geprüft sind nur diese beiden Module, nicht das Paket.
    Über `ast`, nicht als Textsuche: Docstrings dürfen den Namen nennen."""
    import ast

    import falzmarke as paket

    baum = ast.parse((Path(paket.__file__).parent / f"{modul}.py").read_text(encoding="utf-8"))
    aufrufe = [k.lineno for k in ast.walk(baum) if isinstance(k, ast.Call)
               and getattr(k.func, "attr", getattr(k.func, "id", "")) == "bruecken_profil"]
    assert aufrufe == [], f"{modul}.py ruft bruecken_profil selbst auf, Z. {aufrufe}"


# ── Die Ordner der Identität aus dem Profil der Brücke (#522, Punkt 6) ──────

def _entwuerfe_nur_am_socket(monkeypatch, tmp_path) -> str:
    """Standardprofil A nennt „Alt“ als Entwürfe-Ordner, Profil B am Socket
    „Entwürfe“. Gibt den Socketpfad für `FALZMARKE_BRUECKE_SOCKET`."""
    from test_thunderbird_signatur import _attrappe, _grundwerte

    konto = "imap://muster%40example.de@outlook.office365.com/"
    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER",
                        _attrappe(tmp_path / "a", _grundwerte(draft_folder=konto + "Alt")))
    profil_b = (_attrappe(tmp_path / "b", _grundwerte(draft_folder=konto + "Entw&APw-rfe"))
                / "Profiles" / "abcd1234.default-release")
    return str(profil_b / bruecke.SOCKET_DATEI)


def test_entwurf_oeffnen_liest_den_ordner_aus_dem_profil_der_bruecke(oeffne_befehl, monkeypatch,
                                                                     capsys, tmp_path):
    """#522, Punkt 6: Die Brücke öffnet aus dem Entwürfe-Ordner ihres Profils, also
    muss die UID auch aus diesem Ordner stammen. Zwilling ohne Schalter: Ordner aus A."""
    socket = _entwuerfe_nur_am_socket(monkeypatch, tmp_path / "p6")
    _bruecke(monkeypatch)

    def liste() -> str:
        server = ImapAttrappe({"Entw&APw-rfe": [_vorhanden()], "Alt": []})
        monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
        assert oeffne_befehl() == 0
        return capsys.readouterr().out

    monkeypatch.setenv("FALZMARKE_BRUECKE_SOCKET", socket)
    assert "1 Entwürfe in „Entwürfe“" in liste(), \
        "entwurf-oeffnen liest den Entwürfe-Ordner am Profil der Brücke vorbei"
    monkeypatch.delenv("FALZMARKE_BRUECKE_SOCKET")
    assert "0 Entwürfe in „Alt“" in liste(), "der Zwilling kann gar nicht rot werden"


def test_email_oeffnen_legt_in_den_ordner_aus_dem_profil_der_bruecke(monkeypatch, felder,
                                                                     tmp_path):
    """Derselbe Fall am Weg von `email --oeffnen`: Abgelegt wird, wo die Brücke danach
    öffnet. Die Umgebung des Laufs bestimmt den Socket und damit das Profil."""
    socket = _entwuerfe_nur_am_socket(monkeypatch, tmp_path)

    def abgelegt(umgebung) -> list[str]:
        server = ImapAttrappe({"Entw&APw-rfe": [], "Alt": []})
        monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
        oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0", **umgebung},
                        laufen=Thunderbird(), binaer=lambda: THUNDERBIRD_PFAD)
        return [befehl[1] for befehl in server.befehle("APPEND")]

    assert abgelegt({"FALZMARKE_BRUECKE_SOCKET": socket}) == ["Entw&APw-rfe"], \
        "email --oeffnen legt am Profil der Brücke vorbei ab"
    assert abgelegt({}) == ["Alt"], "der Zwilling kann gar nicht rot werden"


def test_nur_entwurfsbuch_fragt_oeffnen_nach_den_ordnern_der_identitaet():
    """#522, Punkt 6: `oeffnen.thunderbird_ordner` liest das Profil, das man ihm gibt.
    Wer es direkt ruft, nimmt das Standardprofil statt des Profils der Brücke. Die
    Zusammensetzung steht deshalb nur in `entwurfsbuch.thunderbird_ordner`."""
    import ast

    import falzmarke as paket

    funde = []
    for datei in sorted(Path(paket.__file__).parent.glob("*.py")):
        if datei.name == "entwurfsbuch.py":
            continue
        for knoten in ast.walk(ast.parse(datei.read_text(encoding="utf-8"))):
            if not isinstance(knoten, ast.Call):
                continue
            ziel = knoten.func
            direkt = isinstance(ziel, ast.Name) and ziel.id == "thunderbird_ordner"
            ueber_modul = (isinstance(ziel, ast.Attribute) and ziel.attr == "thunderbird_ordner"
                           and getattr(ziel.value, "id", "") != "entwurfsbuch")
            if direkt or ueber_modul:
                funde.append(f"{datei.name}:{knoten.lineno}")
    assert funde == [], f"Ordner der Identität am Profil der Brücke vorbei: {funde}"


@pytest.mark.parametrize("fenster, pruefen, ungeprueft", [
    (bruecke.Oeffnung("geoeffnet", gelesen=True, identitaet=FREMD, lese_grund="Fenster lädt",
                      absender_geprueft=True,
                      absender_abweichung=f"Fenster: {FREMD}, Nachricht: {ABSENDER}"),
     "ABSENDER PRÜFEN", "NICHT GEPRÜFT  Empfänger im Fenster: Fenster lädt"),
    (bruecke.Oeffnung("geoeffnet", gelesen=True, geprueft=True,
                      abweichung="Cc: fehlt c@example.org",
                      absender_hinweis="das Add-on meldet keinen Absender des Fensters"),
     "EMPFÄNGER PRÜFEN",
     "NICHT GEPRÜFT  Absender im Fenster: das Add-on meldet keinen Absender des Fensters"),
], ids=["absender-prueft-empfaenger-offen", "empfaenger-prueft-absender-offen"])
def test_neben_einem_pruefen_steht_was_die_andere_pruefung_nicht_verglich(fenster, pruefen,
                                                                         ungeprueft, capsys):
    """Nachreview #487, Nr. 3: Bis dahin kehrte `_melde_fenster` nach dem
    PRÜFEN-Block zurück, und die Zeile der anderen Prüfung fehlte."""
    falzmarke._melde_fenster(fenster, "Entwürfe", "Vektor S2: Wappen")
    fehler = capsys.readouterr().err
    assert pruefen in fehler
    assert ungeprueft in fehler, f"neben {pruefen} fehlt „{ungeprueft}“"


@pytest.mark.parametrize("fenster, pruefen, bestanden", [
    (bruecke.Oeffnung("geoeffnet", gelesen=True, geprueft=True, identitaet=ALIAS,
                      abweichung="Cc: fehlt c@example.org", absender_geprueft=True,
                      absender_hinweis=f"{ALIAS} ist eine Identität im selben Konto wie {ABSENDER}"),
     "EMPFÄNGER PRÜFEN",
     f"OK  Absender im Fenster: {ALIAS} ({ALIAS} ist eine Identität im selben Konto wie "
     f"{ABSENDER})"),
    (bruecke.Oeffnung("geoeffnet", gelesen=True, geprueft=True, identitaet=FREMD,
                      an=("b@example.org",), absender_geprueft=True,
                      absender_abweichung=f"Fenster: {FREMD}, Nachricht: {ABSENDER}"),
     "ABSENDER PRÜFEN", "OK  Empfänger im Fenster wie in der Nachricht: An 1, Cc 0, Bcc 0"),
], ids=["empfaenger-prueft-absender-alias", "absender-prueft-empfaenger-gleich"])
def test_neben_einem_pruefen_steht_was_die_andere_pruefung_bestand(fenster, pruefen, bestanden,
                                                                   capsys):
    """#500, Befund 3: Bestand die andere Prüfung, fehlte ihre Zeile ganz, und
    „bestanden“ war von „vergessen“ nicht zu unterscheiden."""
    falzmarke._melde_fenster(fenster, "Entwürfe", "Vektor S2: Wappen")
    ausgabe = capsys.readouterr()
    assert pruefen in ausgabe.err
    assert bestanden in ausgabe.out, f"neben {pruefen} fehlt „{bestanden}“"
    assert "OK  Entwurf offen" not in ausgabe.out


def test_absender_pruefen_ohne_lesung_laesst_das_fenster_wie_es_ist(monkeypatch, tmp_path):
    """Add-on bis 0.3.7: Es gibt nichts zu vergleichen, wie bei den Empfängern."""
    _profil_mit_alias(monkeypatch, tmp_path)
    ungelesen = bruecke.Oeffnung("geoeffnet", identitaet=FREMD)
    assert oeffnen.absender_pruefen(ungelesen, ABSENDER) == ungelesen


def test_entwurf_oeffnen_unter_fremder_identitaet_ist_exit_3(oeffne_befehl, monkeypatch,
                                                             capsys, tmp_path):
    _profil_mit_alias(monkeypatch, tmp_path)
    _zwei_entwuerfe(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), betreff="Vektor S2: Wappen",
                                     identitaet=FREMD))
    assert oeffne_befehl("--betreff", "wappen") == 3
    ausgabe = capsys.readouterr()
    assert "OK  Entwurf offen" not in ausgabe.out
    assert "ABSENDER PRÜFEN  Entwurf offen in Thunderbird: Vektor S2: Wappen" in ausgabe.err
    assert f"Fenster: {FREMD}, Nachricht: {ABSENDER}" in ausgabe.err
    assert "EMPFÄNGER PRÜFEN" not in ausgabe.err


def test_entwurf_oeffnen_unter_einem_alias_ist_gruen(oeffne_befehl, monkeypatch, capsys,
                                                     tmp_path):
    _profil_mit_alias(monkeypatch, tmp_path)
    _zwei_entwuerfe(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=("b@example.org",), betreff="Vektor S2: Wappen",
                                     identitaet=ALIAS))
    assert oeffne_befehl("--betreff", "wappen") == 0
    ausgabe = capsys.readouterr()
    assert (f"OK  Absender im Fenster: {ALIAS} ({ALIAS} ist eine Identität im selben Konto "
            f"wie {ABSENDER})") in ausgabe.out
    assert "ABSENDER PRÜFEN" not in ausgabe.err


def test_email_oeffnen_unter_fremder_identitaet_warnt_mit_exit_0(befehl, monkeypatch, capsys,
                                                                 tmp_path):
    """`email --oeffnen` endet mit 0, der Entwurf liegt ja (ADR 0038), wie bei
    `EMPFÄNGER PRÜFEN`."""
    _profil_mit_alias(monkeypatch, tmp_path)
    _server(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(identitaet=FREMD))
    assert befehl() == 0
    ausgabe = capsys.readouterr()
    assert "ABSENDER PRÜFEN" in ausgabe.err and f"Fenster: {FREMD}" in ausgabe.err
    assert "OK  Entwurf offen" not in ausgabe.out


def test_entwurf_oeffnen_mit_leerem_fenster_ist_exit_3(oeffne_befehl, monkeypatch, capsys):
    """Ein Fenster mit anderen Empfängern ist nicht das bestellte — Exit 3 wie ohne Fenster."""
    _zwei_entwuerfe(monkeypatch)
    _bruecke(monkeypatch, _offen_mit(an=(), betreff="Vektor S2: Wappen"))
    assert oeffne_befehl("--betreff", "wappen") == 3
    ausgabe = capsys.readouterr()
    assert "EMPFÄNGER PRÜFEN" in ausgabe.err and "An: fehlt b@example.org" in ausgabe.err
    assert "OK  Entwurf offen" not in ausgabe.out


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
    # Ordner nachladen, dann zweimal warten: aufs Fenster und auf den Entwurf darin,
    # und seit 0.3.8 noch einmal, bis das Fenster fertig geladen ist (#464).
    # Die Menge ist geschlossen, damit eine neue Frist im Add-on hier auffällt
    # und nicht still an der Rechnung vorbeiläuft.
    assert set(frist) == {"FRIST_ORDNER_MS", "FRIST_FENSTER_MS", "FRIST_LEERLAUF_MS",
                          "FRIST_LADEN_MS"}
    assert bruecke.FRIST_OEFFNEN_S > (frist["FRIST_ORDNER_MS"] + 2 * frist["FRIST_FENSTER_MS"]
                                      + frist["FRIST_LADEN_MS"])
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
