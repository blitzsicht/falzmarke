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
from datetime import datetime, timezone
from email import policy
from pathlib import Path

import pytest

from conftest import PROFILE
from falzmarke import cli as falzmarke
from falzmarke import eml as eml_modul
from falzmarke import oeffnen, postfach
from imap_attrappe import ImapAttrappe, nachricht
from test_oeffnen import THUNDERBIRD_PFAD, Thunderbird

ABSENDER = "muster@example.de"
BETREFF = "AW: Monitoring – Budget"

MAIL = f"""---
typ: email
profil: example
an: Nico Muster <nico@example.org>
betreff: "{BETREFF}"
antwort_auf: "<vorher@example.org>"
anrede: Hallo Nico,
---
danke für deine Antwort, anbei das Angebot.
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


def _vorhanden(betreff=BETREFF, an="nico@example.org"):
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
    server = _server(monkeypatch, [_vorhanden(an="erika@example.com")])
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
