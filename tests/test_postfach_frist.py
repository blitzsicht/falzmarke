"""Die Frist einer Postfach-Sitzung ist eine Obergrenze (Review von #570, ADR 0051).

`imaplib` legt das Zeitlimit auf jeden einzelnen Empfang. Bis zu diesem Vorgang
begann die Frist der Sitzung erst nach dem Konstruktor. Begrüßung und
`CAPABILITY` durften deshalb je die volle Frist brauchen. Ein Server, der Byte
für Byte knapp unter dem Zeitlimit tröpfelt, hielt die Sitzung beliebig lange
offen. Gemessen am 06.11.2026 mit `frist=3`: 8,8 s (3.12) und 11,8 s (3.14,
`logout` wartet erneut) bei langsamem Gruß, 35,6 s beim Tröpfeln.

Diese Tests sprechen mit einem **Schein-Server auf einem freien Port von
127.0.0.1** und nie mit dem Proxy unter 1993. Sie setzen `ImapMitFrist`
ausdrücklich ein, weil `conftest.py` sonst jede Verbindung ablehnt. Die
Gegenproben stehen in `tests/test_gegenbeweis.py`, Abschnitt ADR 0051.
"""

from __future__ import annotations

import imaplib
import socket
import threading
import time

import pytest

import conftest
from falzmarke import postfach

#: Der echte Konstruktor, gelesen beim Import, bevor `conftest._waechter` ihn
#: für jeden Test sperrt. Freigegeben wird er nur für die Ports des eigenen
#: Schein-Servers (`schein`), jedes andere Ziel fängt der Wächter weiter ab.
_ECHTER_KONSTRUKTOR = imaplib.IMAP4.__init__

#: Klein, damit die Suite schnell bleibt; groß genug für langsame CI-Rechner.
FRIST = 1.0
#: Was über der Frist an Verwaltung dazukommen darf (Anmelden, Abmelden, Threads).
#: Knapp genug, dass „gruss_dann_stille“ ohne nachgestellte Restzeit (1,6 s)
#: rot wird, großzügig gegen lokale Sockets (gemessen: 1,00 s mit Fix).
SPIEL = 0.4


def _zeile(conn, datei) -> bytes:
    """Eine Befehlszeile samt Literal, falls `imaplib` eines schickt (3.14)."""
    zeile = datei.readline()
    if zeile.rstrip().endswith(b"}"):
        laenge = int(zeile.rstrip()[:-1].rsplit(b"{", 1)[1])
        conn.sendall(b"+ weiter\r\n")
        zeile += datei.read(laenge) + datei.readline()
    return zeile


def _tag(zeile: bytes) -> bytes:
    return zeile.split(b" ", 1)[0]


def _bediene(verhalten: str, conn: socket.socket, schluss: threading.Event) -> None:
    datei = conn.makefile("rb")
    warte = lambda s: schluss.wait(s)  # noqa: E731 — bricht beim Aufräumen sofort ab
    try:
        if verhalten == "troepfelt":
            for byte in b"* OK x\r\n":
                if warte(0.3):
                    return
                conn.sendall(bytes([byte]))
            warte(30)
            return
        if verhalten == "gruss_dann_stille":
            if warte(0.6):
                return
            conn.sendall(b"* OK schein\r\n")
            warte(30)
            return
        if verhalten == "langsam":
            if warte(0.7):
                return
            conn.sendall(b"* OK schein\r\n")
            tag = _tag(_zeile(conn, datei))
            if warte(0.7):
                return
            conn.sendall(b"* CAPABILITY IMAP4rev1\r\n" + tag + b" OK fertig\r\n")
            _zeile(conn, datei)  # LOGIN — bleibt ohne Antwort
            warte(30)
            return
        conn.sendall(b"* OK schein\r\n")
        tag = _tag(_zeile(conn, datei))
        conn.sendall(b"* CAPABILITY IMAP4rev1\r\n" + tag + b" OK fertig\r\n")
        tag = _tag(_zeile(conn, datei))
        conn.sendall(tag + b" OK [CAPABILITY IMAP4rev1] angemeldet\r\n")
        if verhalten == "schweigt_nach_login":
            warte(30)
            return
        # "gesund": antwortet auf LIST, EXAMINE, FETCH (mit Literal) und LOGOUT.
        while not schluss.is_set():
            zeile = _zeile(conn, datei)
            if not zeile:
                return
            tag, befehl = _tag(zeile), zeile.split(b" ")[1].upper()
            if befehl == b"LIST":
                conn.sendall(b'* LIST (\\HasNoChildren) "/" INBOX\r\n' + tag + b" OK fertig\r\n")
            elif befehl == b"EXAMINE":
                conn.sendall(b"* 1 EXISTS\r\n" + tag + b" OK [READ-ONLY] fertig\r\n")
            elif befehl == b"FETCH":
                conn.sendall(b"* 1 FETCH (RFC822 {5}\r\nhallo)\r\n" + tag + b" OK fertig\r\n")
            elif befehl == b"LOGOUT":
                conn.sendall(b"* BYE\r\n" + tag + b" OK fertig\r\n")
                return
            else:
                conn.sendall(tag + b" BAD unbekannt\r\n")
    except OSError:
        pass
    finally:
        conn.close()


@pytest.fixture
def schein(monkeypatch):
    """Startet einen Schein-Server; zurück kommt eine Funktion `verhalten → Umgebung`."""
    schluss = threading.Event()
    lauscher: list[socket.socket] = []
    erlaubt: set[tuple[str, int]] = set()

    def nur_zum_schein(self, host="", port=143, timeout=None):
        if (host, port) not in erlaubt:
            conftest.ABGEFANGEN.append(f"imaplib.IMAP4 an {host}:{port}")
            raise conftest.WaechterFehler(f"Testlauf: nur der Schein-Server, nicht {host}:{port}")
        _ECHTER_KONSTRUKTOR(self, host, port, timeout)

    monkeypatch.setattr(imaplib.IMAP4, "__init__", nur_zum_schein)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", postfach.ImapMitFrist)

    def starte(verhalten: str) -> dict[str, str]:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(4)
        lauscher.append(s)
        erlaubt.add(("127.0.0.1", s.getsockname()[1]))

        def annehmen():
            while not schluss.is_set():
                try:
                    conn, _ = s.accept()
                except OSError:
                    return
                threading.Thread(target=_bediene, args=(verhalten, conn, schluss),
                                 daemon=True).start()

        threading.Thread(target=annehmen, daemon=True).start()
        return {"FALZMARKE_GESENDET_IMAP": f"127.0.0.1:{s.getsockname()[1]}"}

    yield starte
    schluss.set()
    for s in lauscher:
        s.close()


def _dauer(umgebung, *, mit_list: bool) -> tuple[float, str]:
    beginn = time.monotonic()
    try:
        with postfach.verbinde("probe@example.invalid", umgebung=umgebung,
                               frist=FRIST) as sitzung:
            if mit_list:
                sitzung.ordner_liste()
        ergebnis = "OK"
    except postfach.PostfachFehler as fehler:
        ergebnis = str(fehler)
    return time.monotonic() - beginn, ergebnis


@pytest.mark.parametrize("verhalten, mit_list", [
    ("troepfelt", False),
    ("gruss_dann_stille", False),
    ("langsam", False),
    ("schweigt_nach_login", True),
])
def test_ein_haengender_server_haelt_die_sitzung_nicht_ueber_die_frist(schein, verhalten,
                                                                        mit_list):
    dauer, ergebnis = _dauer(schein(verhalten), mit_list=mit_list)
    assert ergebnis != "OK", "der Schein-Server hängt — die Sitzung darf nicht gelingen"
    assert dauer < FRIST + SPIEL, (
        f"{verhalten}: {dauer:.2f} s bei einer Frist von {FRIST:g} s ({ergebnis})")


def test_ein_gesunder_server_arbeitet_durch_die_frist_hindurch(schein):
    """Kontrolle: Der Wrapper um den Socket stört keinen Befehl, auch kein Literal."""
    umgebung = schein("gesund")
    with postfach.verbinde("probe@example.invalid", umgebung=umgebung, frist=FRIST) as sitzung:
        assert [name for name, _ in sitzung.ordner_liste()] == ["INBOX"]
        typ, _ = sitzung._v.select("INBOX", readonly=True)
        assert typ == "OK"
        typ, daten = sitzung._v.fetch("1", "(RFC822)")
        assert typ == "OK" and daten[0][1] == b"hallo"


def test_der_waechter_sperrt_neben_dem_schein_server_weiter(schein):
    """Die Freigabe gilt nur den Ports des eigenen Schein-Servers, nie dem Proxy."""
    schein("gesund")
    with pytest.raises(conftest.WaechterFehler):
        postfach.ImapMitFrist("127.0.0.1", 1993, timeout=FRIST)
    assert conftest.ABGEFANGEN == ["imaplib.IMAP4 an 127.0.0.1:1993"]
    conftest.ABGEFANGEN.clear()


def test_nach_abgelaufener_frist_schliesst_das_abmelden_die_verbindung(schein):
    """`imaplib.logout` sendet erst `LOGOUT` und ruft danach `shutdown` (3.12 wie
    3.14). Ist die Frist um, wirft schon das Senden `TimeoutError`, und `shutdown`
    lief bis zum Nachreview von #574 nie: Die TCP-Verbindung blieb offen, bis die
    Speicherbereinigung sie fand. Gemessen wird am inneren Socket, nicht an der
    Hülle, denn deren `fileno` reicht `__getattr__` nur durch."""
    umgebung = schein("schweigt_nach_login")
    sitzung = postfach.verbinde("probe@example.invalid", umgebung=umgebung, frist=FRIST)
    innen = sitzung._v.sock._sock
    with pytest.raises(postfach.PostfachFehler):
        sitzung.ordner_liste()
    assert innen.fileno() != -1, "die Probe trennt nicht: der Socket ist schon vor dem Abmelden zu"
    sitzung.abmelden()
    assert innen.fileno() == -1, "nach dem Abmelden ist die Verbindung noch offen"
