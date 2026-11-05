"""#504: Nacharbeit aus dem Review von #502 — Rat, Wechselgrund, LIST, rohe Leitung.

Jeder Fall nennt das Kriterium, das er misst. Die Gegenprobe steht jeweils daneben:
ein Zwilling, der ohne den fraglichen Umstand anders ausfallen muss.
"""

from __future__ import annotations

import imaplib
import re
import socket
import threading

import pytest

from falzmarke import ablage, postfach
from falzmarke import cli as falzmarke
from test_ablage import _jahr_lage, _mit_fahnen, _neu_nummeriert, _offen, _postfach, _uids

# Der Wächter in `conftest.py` ersetzt `imaplib.IMAP4.__init__` für jeden Test. Dieser Fall will
# echtes `imaplib` gegen einen Socket auf 127.0.0.1 — den Wert hält deshalb die Fassung, die beim
# Einsammeln noch unberührt war. Mit Absicht, nur hier und nur gegen den eigenen Server unten.
_ECHTES_INIT = imaplib.IMAP4.__init__


class _EchtesImap(imaplib.IMAP4):
    __init__ = _ECHTES_INIT


_SONDER = {"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": "\\Archive"}


@pytest.fixture(autouse=True)
def _klasse_zurueck(monkeypatch):
    """`_postfach` setzt `postfach.IMAP_KLASSE` global; hier wird es nach jedem Fall zurückgelegt."""
    monkeypatch.setattr(postfach, "IMAP_KLASSE", postfach.IMAP_KLASSE, raising=False)
    yield


# ── Befund 1: Der Rat zu --trotz-faehnchen führt auf einen Befehl, der durchgeht ──

def _rat_argumente(grund: str) -> list[str]:
    """Die Argumente, die der Rat im letzten Satz des Grundes nennt."""
    rat = grund.rsplit("; ", 1)[-1]
    assert "--trotz-faehnchen" in rat, f"kein Rat im letzten Satz: {grund}"
    treffer = re.search(r"--uidvalidity (\d+)", rat)
    assert treffer, f"der Rat nennt keine UIDVALIDITY, der Befehl liefe auf Exit 1: {rat}"
    return ["--trotz-faehnchen", "--uidvalidity", treffer.group(1)]


def test_der_rat_zu_trotz_faehnchen_nennt_einen_befehl_der_durchgeht(monkeypatch, capsys):
    """AC 1: Wer dem Rat folgt, braucht keinen dritten Lauf."""
    attrappe, _ = _postfach(eingang=[_mit_fahnen(_offen(), "\\Flagged")], sonder=_SONDER)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    grund = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={},
                              uids=["101"]).grund
    rat = _rat_argumente(grund)

    # Der genannte Befehl, so wie ihn der Bediener tippt: --uid, der Rat, --machen.
    code = falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--uid", "101",
                           *rat, "--machen"])
    fehler = capsys.readouterr().err
    assert code == 0, f"der Rat führt auf Exit {code}: {fehler}"
    assert len(attrappe.befehle("UID MOVE")) == 1 and _uids(attrappe) == []


def test_gegenprobe_ohne_den_wert_aus_dem_rat_bleibt_der_befehl_abgewiesen(monkeypatch, capsys):
    """Belegt, dass der Fall oben an der UIDVALIDITY hängt und nicht an etwas anderem."""
    attrappe, _ = _postfach(eingang=[_mit_fahnen(_offen(), "\\Flagged")], sonder=_SONDER)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    code = falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--uid", "101",
                           "--trotz-faehnchen", "--machen"])
    assert code == falzmarke.EXIT_EINGABE
    assert "--uid mit --machen braucht --uidvalidity" in capsys.readouterr().err
    assert not attrappe.befehle("UID MOVE")


# ── Befund 8: Der Wechselgrund passt zum Lauf ───────────────────────────────

def _schluss(grund: str) -> str:
    return grund.partition("erst ")[2] or grund


def test_ohne_machen_sagt_der_wechselgrund_nichts_von_ohne_machen():
    """AC 8: Der Lauf hatte kein --machen, also wird nicht geraten, es wegzulassen."""
    attrappe, _ = _postfach(eingang=[_offen()], sonder=_SONDER)
    _neu_nummeriert(attrappe)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={},
                                uids=["101"], uidvalidity="1")
    assert "UIDVALIDITY des Eingangs ist jetzt 2" in bericht.grund
    assert "--machen" not in bericht.grund, bericht.grund


def test_der_wechselgrund_nennt_dass_uidvalidity_fuer_die_neuanzeige_wegfaellt():
    attrappe, _ = _postfach(eingang=[_offen()], sonder=_SONDER)
    _neu_nummeriert(attrappe)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={},
                                uids=["101"], uidvalidity="1")
    assert "--uidvalidity" in _schluss(bericht.grund), bericht.grund


def test_mit_machen_nennt_der_wechselgrund_machen_und_uidvalidity():
    """Zwilling zum ersten Fall: Mit --machen darf der Satz es nennen."""
    attrappe, _ = _postfach(eingang=[_offen()], sonder=_SONDER)
    _neu_nummeriert(attrappe)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101"], uidvalidity="1")
    schluss = _schluss(bericht.grund)
    assert "--machen" in schluss and "--uidvalidity" in schluss, bericht.grund


def test_am_select_nennt_der_wechselgrund_ebenfalls_uidvalidity():
    """Der Abbruch am Zug (`_SCHLUSS_AM_ZUG`): die alten Teilsätze gelten weiter."""
    attrappe, _ = _postfach(**_jahr_lage())
    echt = attrappe.uid

    def uid(befehl, *args):
        antwort = echt(befehl, *args)
        if befehl == "MOVE":
            attrappe.uidvalidity_select = "2"
        return antwort

    attrappe.uid = uid
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={})
    assert "kein weiterer Zug geht hinaus" in bericht.grund
    assert "--uidvalidity" in _schluss(bericht.grund), bericht.grund


# ── Befund 9: Nach einem Wechsel geht kein LIST zum Jahresordner ────────────

def _listen_mit_wechsel(wechsel: bool) -> int:
    attrappe, _ = _postfach(**_jahr_lage())
    if wechsel:
        _neu_nummeriert(attrappe)
    vorher = len(attrappe.befehle("LIST"))
    ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", umgebung={}, uids=["101"],
                      uidvalidity="1")
    return len(attrappe.befehle("LIST")) - vorher


def test_nach_einem_wechsel_geht_kein_list_zum_jahresordner():
    """AC 9. Die Gegenprobe ist der Zwilling ohne Wechsel: Er muss mehr LISTs schicken,
    sonst zählte die Messung nichts, was am Jahresordner hängt."""
    ohne = _listen_mit_wechsel(False)
    mit = _listen_mit_wechsel(True)
    assert ohne >= 1, f"der Zwilling ohne Wechsel schickt {ohne} LIST: die Messung sähe nichts"
    assert mit == 0, f"nach dem Wechsel gingen noch {mit} LIST zum Jahresordner hinaus"


# ── Befund 6: Eine rohe Zeile `* OK [UIDVALIDITY n]` durch echtes imaplib ───

class _Server:
    """Ein IMAP-Server auf einem Socket, der die Zeilen roh sendet."""

    def __init__(self, zeilen_examine: list[str]):
        self.zeilen_examine = zeilen_examine
        self.sock = socket.create_server(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.faden = threading.Thread(target=self._bediene, daemon=True)
        self.faden.start()

    def _bediene(self) -> None:
        try:
            verbindung, _ = self.sock.accept()
        except OSError:                      # der Test schloss den Socket, ohne dass jemand kam
            return
        with verbindung:
            verbindung.sendall(b"* OK [CAPABILITY IMAP4rev1] bereit\r\n")
            puffer = b""
            while True:
                while b"\r\n" not in puffer:
                    stueck = verbindung.recv(4096)
                    if not stueck:
                        return
                    puffer += stueck
                zeile, _, puffer = puffer.partition(b"\r\n")
                marke, _, rest = zeile.decode().partition(" ")
                befehl = rest.split(" ", 1)[0].upper()
                if befehl == "CAPABILITY":
                    antwort = ["* CAPABILITY IMAP4rev1", f"{marke} OK fertig"]
                elif befehl == "LOGIN":
                    antwort = [f"{marke} OK angemeldet"]
                elif befehl in ("EXAMINE", "SELECT"):
                    antwort = ["* 0 EXISTS", *self.zeilen_examine,
                               f"{marke} OK [READ-ONLY] ausgewählt"]
                elif befehl == "LOGOUT":
                    verbindung.sendall(f"* BYE\r\n{marke} OK tschüss\r\n".encode())
                    return
                else:
                    antwort = [f"{marke} BAD unbekannt"]
                verbindung.sendall(("\r\n".join(antwort) + "\r\n").encode())

    def schliessen(self) -> None:
        self.sock.close()


def _uidvalidity_ueber_die_leitung(zeilen: list[str], monkeypatch):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", _EchtesImap)           # echt, keine Attrappe
    server = _Server(zeilen)
    try:
        umgebung = {"FALZMARKE_GESENDET_IMAP": f"127.0.0.1:{server.port}"}
        with postfach.verbinde("joe@example.org", frist=10, umgebung=umgebung) as sitzung:
            sitzung._waehle("INBOX")
            return sitzung.uidvalidity.get("INBOX", "fehlt")
    finally:
        server.schliessen()


def test_die_rohe_zeile_uidvalidity_wird_aus_echtem_imaplib_gelesen(monkeypatch):
    """AC 6: Die Zeile kommt unzerlegt über den Socket, `postfach` liest den Wert daraus."""
    assert _uidvalidity_ueber_die_leitung(["* OK [UIDVALIDITY 4711] UIDs gelten"],
                                          monkeypatch) == "4711"


def test_gegenprobe_ohne_die_zeile_ist_die_uidvalidity_unbekannt(monkeypatch):
    """Belegt, dass der Wert oben aus der Zeile kommt und nicht aus einer Vorgabe."""
    assert _uidvalidity_ueber_die_leitung(["* OK [UIDNEXT 9] vorhergesagt"], monkeypatch) is None
