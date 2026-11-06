"""„Kein Entwurf“ in zwei Klassen: vergeht von selbst oder bleibt (#505).

Ein Aufrufer in einer Schleife (der Abholer in siluri-angebote, alle 180 s)
las bis hierher den Wortlaut des Grundes gegen eine Freiliste. Jetzt trägt jede
Stelle, die ohne Entwurf endet, eine Klasse, und `email --kein-fenster` druckt
sie als eigene Zeile `URSACHE  <Klasse>`. Die Zeile `KEIN ENTWURF  <Grund>`
bleibt wortgleich, damit ein Leser des alten Formats weiterläuft.
"""

from __future__ import annotations

import ast
import errno
import functools
import imaplib
import inspect
import socket
import subprocess
import textwrap

import pytest

from falzmarke import oeffnen, postfach
from imap_attrappe import ImapAttrappe
from test_oeffnen import THUNDERBIRD_PFAD, Thunderbird
from test_postfach_entwurf import befehl, eml_pfad, felder  # noqa: F401 — Fixtures

D, V = oeffnen.DAUERHAFT, oeffnen.VORUEBERGEHEND


# ── Jede Stelle trägt eine Klasse ───────────────────────────────────────────

def _baum(funktion) -> ast.AST:
    return ast.parse(textwrap.dedent(inspect.getsource(funktion)))


def _absagen(funktion) -> list[ast.Call]:
    """Jedes `Entwurfslage(None, …)` ohne `ungewiss=True` in der Funktion."""
    gefunden = []
    for knoten in ast.walk(_baum(funktion)):
        if not isinstance(knoten, ast.Call):
            continue
        if (getattr(knoten.func, "id", "") or getattr(knoten.func, "attr", "")) != "Entwurfslage":
            continue
        erstes = knoten.args[0] if knoten.args else None
        if not (isinstance(erstes, ast.Constant) and erstes.value is None):
            continue
        schluessel = {k.arg: k.value for k in knoten.keywords}
        ungewiss = schluessel.get("ungewiss")
        if isinstance(ungewiss, ast.Constant) and ungewiss.value is True:
            continue
        if "schon_da" in schluessel:          # „liegt schon“ ist kein „kein Entwurf“
            continue
        gefunden.append(knoten)
    return gefunden


def test_jede_absage_in_entwurf_traegt_eine_klasse():
    absagen = _absagen(oeffnen.entwurf)
    assert len(absagen) >= 10, f"nur {len(absagen)} Absagen gefunden — Suche kaputt?"
    ohne = [a.lineno for a in absagen if "dauer" not in {k.arg for k in a.keywords}]
    assert ohne == [], f"Entwurfslage(None, …) ohne dauer= in entwurf, Zeilen {ohne}"


def test_jede_rueckgabe_von_entwurf_postfach_traegt_eine_klasse():
    rueckgaben = [k for k in ast.walk(_baum(oeffnen._entwurf_postfach))
                  if isinstance(k, ast.Return)]
    assert len(rueckgaben) >= 9, f"nur {len(rueckgaben)} return gefunden — Suche kaputt?"
    falsch = [r.lineno for r in rueckgaben
              if not (isinstance(r.value, ast.Tuple) and len(r.value.elts) == 3)]
    assert falsch == [], f"return ohne (Lage, Grund, Dauer) in _entwurf_postfach, Zeilen {falsch}"
    ohne_klasse = [r.lineno for r in rueckgaben
                   if isinstance(r.value.elts[0], ast.Constant) and r.value.elts[0].value is None
                   and isinstance(r.value.elts[2], ast.Constant) and r.value.elts[2].value == ""]
    assert ohne_klasse == [], f"(None, Grund, \"\") in _entwurf_postfach, Zeilen {ohne_klasse}"


def test_die_suche_findet_eine_absage_ohne_klasse():
    """Gegenprobe zur Vollständigkeit: eine Absage ohne `dauer=` fällt auf."""
    def probe():
        return oeffnen.Entwurfslage(None, "x")                    # noqa: F841
    assert len(_absagen(probe)) == 1
    assert "dauer" not in {k.arg for k in _absagen(probe)[0].keywords}


# ── Je Ursache die Klasse ───────────────────────────────────────────────────

def _entwurf(felder, umgebung=None, **k):
    return oeffnen.entwurf(felder, plattform="darwin",
                           umgebung={"DISPLAY": ":0", **(umgebung or {})},
                           laufen=Thunderbird(), binaer=lambda: THUNDERBIRD_PFAD,
                           kein_fenster=True, **k)


def _server(monkeypatch, **k) -> ImapAttrappe:
    attrappe = ImapAttrappe({"Entw&APw-rfe": []}, **k)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    return attrappe


@pytest.mark.parametrize("umgebung, teil", [
    ({"FALZMARKE_ENTWURF": "nie"}, "FALZMARKE_ENTWURF=nie"),
    ({"FALZMARKE_OEFFNEN": "nie"}, "FALZMARKE_OEFFNEN=nie"),
    ({"CI": "true"}, "CI ist gesetzt"),
    ({"FALZMARKE_POSTFACH": "nie"}, "FALZMARKE_POSTFACH=nie"),
], ids=["entwurf-nie", "oeffnen-nie", "ci", "postfach-nie"])
def test_abgeschaltet_ist_dauerhaft(monkeypatch, felder, umgebung, teil):
    _server(monkeypatch)
    lage = _entwurf(felder, umgebung)
    assert lage.programm is None and teil in lage.grund
    assert lage.dauer == D, f"{teil}: {lage.dauer!r}"


def test_ohne_osascript_ist_dauerhaft(monkeypatch, felder):
    def _fehlt(*_a, **_k):
        raise FileNotFoundError("osascript")
    monkeypatch.setattr(oeffnen, "entwurfsweg", _fehlt)
    lage = _entwurf(felder)
    assert "osascript" in lage.grund and lage.dauer == D


def test_ohne_mailprogramm_ist_dauerhaft(monkeypatch, felder):
    monkeypatch.setattr(oeffnen, "entwurfsweg", lambda *_a, **_k: None)
    lage = _entwurf(felder)
    assert lage.programm is None and lage.dauer == D


def test_ein_mailprogramm_ohne_antwort_ist_voruebergehend(monkeypatch, felder):
    def _haengt(*_a, **_k):
        raise subprocess.TimeoutExpired("osascript", 20)
    monkeypatch.setattr(oeffnen, "entwurfsweg", _haengt)
    lage = _entwurf(felder)
    assert "antwortete nicht" in lage.grund and lage.dauer == V


def test_der_applescript_weg_mit_kein_fenster_ist_dauerhaft(monkeypatch, felder):
    outlook = oeffnen.Entwurfsprogramm("com.microsoft.Outlook", "Microsoft Outlook", "", "", "",
                                       schluessel="outlook")
    monkeypatch.setattr(oeffnen, "entwurfsweg", lambda *_a, **_k: outlook)
    lage = _entwurf(felder)
    assert "--kein-fenster" in lage.grund and lage.dauer == D


@pytest.mark.parametrize("fehler", [
    ConnectionRefusedError(61, "refused"), TimeoutError("timed out"),
    OSError(errno.EHOSTUNREACH, "No route to host"),
    socket.gaierror(socket.EAI_AGAIN, "temporary failure in name resolution"),
], ids=["abgelehnt", "zeitlimit", "keine-route", "namensaufloesung-gestoert"])
def test_ein_proxy_der_nicht_antwortet_ist_voruebergehend(monkeypatch, felder, fehler):
    _server(monkeypatch, verbindungsfehler=fehler)
    lage = _entwurf(felder)
    assert lage.grund.startswith("kein Postfach-Entwurf: ") and lage.dauer == V, lage


@pytest.mark.parametrize("fehler", [
    socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided, or not known"),
    imaplib.IMAP4.error("* NO kein IMAP-Dienst"),
    PermissionError(errno.EACCES, "Permission denied"),
], ids=["unbekannter-host", "begruessung-nein", "keine-berechtigung"])
def test_ein_falsches_ziel_ist_dauerhaft(monkeypatch, felder, fehler):
    """Nachreview von #505: Ein vertippter Hostname ist ein `OSError`, vergeht aber
    nicht. Als vorübergehend holte der Abholer ihn alle 180 s erneut. Eine
    fehlende Berechtigung ebenso (Nachreview von #530)."""
    _server(monkeypatch, verbindungsfehler=fehler)
    lage = _entwurf(felder)
    assert lage.dauer == D, lage


def test_eine_abgelehnte_anmeldung_ist_dauerhaft(monkeypatch, felder):
    _server(monkeypatch, login_fehler="AUTHENTICATE failed")
    lage = _entwurf(felder)
    assert "Anmeldung" in lage.grund and lage.dauer == D, lage


def test_ohne_entwuerfe_ordner_ist_dauerhaft(monkeypatch, felder):
    _server(monkeypatch, sonder={})
    lage = _entwurf(felder)
    assert "kein Entwürfe-Ordner" in lage.grund and lage.dauer == D, lage


def test_ohne_absender_ist_dauerhaft(monkeypatch, felder):
    _server(monkeypatch)
    lage = _entwurf({k: v for k, v in felder.items() if k != "absender"})
    assert lage.programm is None and lage.dauer == D, lage


def test_ein_entwurf_der_steht_hat_keine_klasse(monkeypatch, felder):
    _server(monkeypatch)
    lage = _entwurf(felder)
    assert lage.postfach is not None and lage.dauer == ""


# ── Der Fehler aus dem Postfach ─────────────────────────────────────────────

class _Leitung:
    sock = None

    def __init__(self, fehler):
        self.fehler = fehler

    def noop(self):
        raise self.fehler


@pytest.mark.parametrize("fehler, erwartet", [
    (ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"), True),
    (ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused"), True),
    (TimeoutError("timed out"), True),
    (imaplib.IMAP4.abort("socket error: EOF"), True),
    (imaplib.IMAP4.error("SELECT failed"), False),
    (UnicodeEncodeError("ascii", "ü", 0, 1, "nein"), False),
], ids=["reset", "abgelehnt", "timeout", "abort", "nein-vom-server", "kodierung"])
def test_ein_abgerissener_befehl_vergeht_eine_absage_bleibt(fehler, erwartet):
    sitzung = postfach.Postfach(_Leitung(fehler), "a@example.org", 30)
    with pytest.raises(postfach.PostfachFehler) as gefangen:
        sitzung._befehl("NOOP", sitzung._v.noop)
    assert gefangen.value.voruebergehend is erwartet, (
        f"{type(fehler).__name__} nach einem Befehl: voruebergehend={gefangen.value.voruebergehend}")


def test_ein_server_der_nein_sagt_bleibt():
    class _Nein(_Leitung):
        def noop(self):
            return "NO", [b"Mailbox does not exist"]
    sitzung = postfach.Postfach(_Nein(None), "a@example.org", 30)
    with pytest.raises(postfach.PostfachFehler) as gefangen:
        sitzung._befehl("NOOP", sitzung._v.noop)
    assert gefangen.value.voruebergehend is False


def test_abgelaufene_zeit_vergeht():
    sitzung = postfach.Postfach(_Leitung(None), "a@example.org", 0)
    with pytest.raises(postfach.PostfachFehler) as gefangen:
        sitzung._rest()
    assert gefangen.value.voruebergehend is True


def test_ohne_angabe_bleibt_ein_postfachfehler():
    assert postfach.PostfachFehler("x").voruebergehend is False


@pytest.mark.parametrize("fehler", [
    ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"),
    ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused"),
    ConnectionAbortedError(errno.ECONNABORTED, "Software caused connection abort"),
    BrokenPipeError(errno.EPIPE, "Broken pipe"),
    TimeoutError("timed out"),
    OSError(errno.ETIMEDOUT, "Operation timed out"),
    OSError(errno.EHOSTUNREACH, "No route to host"),
    OSError(errno.ENETUNREACH, "Network is unreachable"),
    OSError(errno.ENETDOWN, "Network is down"),
    imaplib.IMAP4.abort("socket error: EOF"),
    socket.gaierror(socket.EAI_AGAIN, "temporary failure in name resolution"),
], ids=["reset", "abgelehnt", "abgebrochen", "rohr", "zeitlimit", "etimedout", "keine-route",
        "netz-unerreichbar", "netz-aus", "abort", "namensaufloesung-gestoert"])
def test_ein_bekannter_netzfehler_vergeht(fehler):
    assert postfach._vergeht(fehler) is True, f"{type(fehler).__name__} gilt als bleibend"


@pytest.mark.parametrize("fehler", [
    PermissionError(errno.EACCES, "Permission denied"),
    OSError(errno.EADDRNOTAVAIL, "Can't assign requested address"),
    FileNotFoundError(errno.ENOENT, "No such file or directory"),
    OSError(errno.EINVAL, "Invalid argument"),
    OSError("ohne Nummer"),
    socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided, or not known"),
    imaplib.IMAP4.error("SELECT failed"),
    UnicodeEncodeError("ascii", "ü", 0, 1, "nein"),
], ids=["keine-berechtigung", "adresse-nicht-verfuegbar", "datei-fehlt", "ungueltig",
        "oserror-ohne-nummer", "unbekannter-host", "nein-vom-server", "kodierung"])
def test_ein_anderer_oserror_bleibt(fehler):
    """Nachreview von #530: `_vergeht` nahm jeden `OSError` außer `gaierror` als
    vorübergehend. Zugesagt ist das Gegenteil: Was sich nicht sicher zuordnen
    lässt, gilt als dauerhaft. Eine fehlende Berechtigung vergeht nicht von selbst."""
    assert postfach._vergeht(fehler) is False, f"{fehler!r} gilt als vorübergehend"


# ── Der Befehl ──────────────────────────────────────────────────────────────

def _ursache(err: str) -> str | None:
    zeilen = [z for z in err.splitlines() if z.startswith("URSACHE  ")]
    assert len(zeilen) <= 1, zeilen
    return zeilen[0].removeprefix("URSACHE  ").split()[0] if zeilen else None


def test_befehl_ohne_proxy_meldet_vorübergehend(befehl, monkeypatch, capsys):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    assert befehl("--kein-fenster") == 3
    err = capsys.readouterr().err
    assert "KEIN ENTWURF  kein Postfach-Entwurf: kein IMAP-Proxy unter" in err, \
        "die alte Zeile muss wortgleich bleiben, der Abholer liest sie"
    assert _ursache(err) == V, err


def test_befehl_mit_abgeschaltetem_entwurf_meldet_dauerhaft(befehl, monkeypatch, capsys):
    monkeypatch.setattr(oeffnen, "entwurf", functools.partial(
        oeffnen.entwurf.func, plattform="darwin",
        umgebung={"DISPLAY": ":0", "FALZMARKE_ENTWURF": "nie"}, laufen=befehl.tb,
        binaer=lambda: THUNDERBIRD_PFAD))
    assert befehl("--kein-fenster") == 3
    err = capsys.readouterr().err
    assert "KEIN ENTWURF  FALZMARKE_ENTWURF=nie ist gesetzt" in err
    assert _ursache(err) == D, err


def test_befehl_ohne_klasse_meldet_dauerhaft(befehl, monkeypatch, capsys):
    """Eine Lage ohne Klasse (etwa aus einer Attrappe) wird nicht zur Schleife."""
    monkeypatch.setattr(oeffnen, "entwurf",
                        lambda felder, **k: oeffnen.Entwurfslage(None, "kein Mailprogramm"))
    assert befehl("--kein-fenster") == 3
    assert _ursache(capsys.readouterr().err) == D


def test_befehl_ohne_kein_fenster_druckt_keine_ursache(befehl, monkeypatch, capsys):
    """Ohne Schalter geht die Datei auf, es gibt kein „kein Entwurf“ zu klassifizieren."""
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    assert befehl() == 0
    assert _ursache(capsys.readouterr().err) is None
