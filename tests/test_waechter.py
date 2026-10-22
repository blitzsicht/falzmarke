"""Gegenprobe zum Wächter in `conftest.py`: Er muss anschlagen, sonst schützt er nichts.

Jeder Versuch hier zielt so, dass er auch bei kaputtem Wächter **kein Fenster**
öffnete: `open` auf eine Datei, die es nicht gibt, IMAP auf Port 9 (discard,
lokal nie belegt). Fiele der Wächter aus, scheiterte der Aufruf harmlos — und
der Test würde rot, weil kein `WaechterFehler` kam.
"""

from __future__ import annotations

import imaplib
import smtplib
import subprocess
import sys

import pytest

import conftest
from conftest import ABGEFANGEN, WaechterFehler, fenster_programm, pruefe_abgefangen
from falzmarke import oeffnen

NIRGENDS = "/nonexistent-falzmarke-waechter/probe.eml"


def _abgefangen() -> list[str]:
    gesehen = list(ABGEFANGEN)
    ABGEFANGEN.clear()
    return gesehen


def test_open_startet_nicht():
    with pytest.raises(WaechterFehler):
        subprocess.run(["open", NIRGENDS], capture_output=True)
    assert len(_abgefangen()) == 1


def test_der_datei_rueckfall_startet_nicht():
    """Genau der Weg vom 21.10.2026: `oeffne()` mit einer Umgebung, die ein
    Fenster erlaubt. `_lauf` hat `subprocess.run` als Vorgabewert gebunden —
    der Wächter muss trotzdem greifen."""
    with pytest.raises(WaechterFehler):
        oeffnen.oeffne(NIRGENDS, plattform="darwin", umgebung={})
    assert _abgefangen()


def test_thunderbird_und_osascript_starten_nicht():
    with pytest.raises(WaechterFehler):
        oeffnen._lauf(["osascript", "-e", "return 1"], 5)
    assert _abgefangen()
    assert fenster_programm(["/Applications/Thunderbird.app/Contents/MacOS/thunderbird",
                             "-compose", "to=x"])
    assert fenster_programm("thunderbird -compose to=x")
    assert fenster_programm(["C:\\Programme\\Outlook.EXE"])


def test_ein_harmloses_programm_laeuft_und_erbt_den_riegel():
    """Gegenprobe zur Gegenprobe: Der Wächter sperrt nicht alles — und ein
    Kindprozess bekommt `FALZMARKE_OEFFNEN=nie` mit."""
    lauf = subprocess.run([sys.executable, "-c",
                           "import os; print(os.environ.get('FALZMARKE_OEFFNEN'),"
                           " os.environ.get('FALZMARKE_POSTFACH'))"],
                          capture_output=True, text=True, check=True)
    assert lauf.stdout.split() == ["nie", "nie"]
    assert fenster_programm([sys.executable, "-c", "pass"]) is None
    assert fenster_programm(["typst", "compile"]) is None
    assert fenster_programm(["pgrep", "-f", "thunderbird"]) is None


def test_imap_und_smtp_verbinden_nicht():
    with pytest.raises(WaechterFehler):
        imaplib.IMAP4("127.0.0.1", 9, timeout=1)
    with pytest.raises(WaechterFehler):
        smtplib.SMTP("127.0.0.1", 9, timeout=1)
    assert len(_abgefangen()) == 2


def test_ein_geschluckter_versuch_macht_den_test_trotzdem_rot():
    """Fängt der Code den Fehler ab, steht der Versuch noch in der Liste — und
    der Abbau des Wächters schlägt an."""
    try:
        subprocess.run(["xdg-open", NIRGENDS])
    except WaechterFehler:
        pass  # so, wie es ein `except Exception` im Code täte
    assert ABGEFANGEN
    with pytest.raises(AssertionError, match="abgefangen"):
        pruefe_abgefangen()
    assert not ABGEFANGEN


def test_der_waechter_ist_scharf_geschaltet():
    assert subprocess.Popen is conftest._WaechterPopen
    assert imaplib.IMAP4.__init__ is not conftest._ECHTES_POPEN.__init__
