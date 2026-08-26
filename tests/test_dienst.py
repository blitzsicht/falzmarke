"""Der MCP-Dienst — die Werkzeuge selbst und ihr Weg durch das Protokoll.

Zwei Ebenen, mit Absicht getrennt:

Die drei Werkzeuge sind gewoehnliche Funktionen und laufen ohne das SDK. Das ist
kein Zufall, sondern der Grund, warum das SDK optional sein kann — wer falzmarke
nur zum Briefesetzen installiert, laedt keine 28 Pakete mit.

Was das SDK braucht, steht am Ende und wird uebersprungen, wenn es fehlt. Damit
ein uebersprungener Test nicht als Nachweis durchgeht, installiert die CI das
Extra ausdruecklich (.github/workflows/ci.yml).
"""

from __future__ import annotations

import base64
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "skill"))

from falzmarke import dienst                                     # noqa: E402
from falzmarke.cli import Eingabefehler                          # noqa: E402

BRIEF = """---
profil: example
datum: 2026-08-26
empfaenger:
  - Muster GmbH
  - Frau Erika Muster
  - Musterstraße 1
  - 12345 Musterstadt
betreff: Prüflauf des Dienstes
anrede: Sehr geehrte Frau Muster,
---

ein Brief für die Testsuite.

Mit freundlichen Grüßen
"""

FREMDES_PROFIL = {
    "absender": {"name": "Fremd GmbH", "strasse": "Weg 1", "plz": "10115", "ort": "Berlin"},
    "ruecksendeangabe": "Fremd GmbH · Weg 1 · 10115 Berlin",
    "briefkopf": {"logo": "assets/logo.svg", "zeilen": ["Fremd GmbH"]},
    "signatur": "assets/unterschrift.svg",
    "gruss": "Mit freundlichen Grüßen",
    "unterzeichner": "Max Fremd",
}


@pytest.fixture(scope="module")
def gerendert() -> dict:
    return dienst.brief_rendern(BRIEF, als="base64")


def test_der_messbericht_kommt_beim_rendern_mit(gerendert):
    """Ein PDF ohne Bericht waere ein PDF-Generator wie jeder andere."""
    assert gerendert["bestanden"] is True
    assert gerendert["form"] == "B"
    pruefungen = gerendert["bericht"]["pruefungen"]
    assert len(pruefungen) > 20, f"nur {len(pruefungen)} Prüfungen im Bericht"
    assert any(p["name"].startswith("Falzmarke") for p in pruefungen)


def test_base64_ist_ein_pdf(gerendert):
    roh = base64.b64decode(gerendert["pdf_base64"])
    assert roh.startswith(b"%PDF-"), "die Rückgabe ist kein PDF"


def test_der_einfachste_aufruf_liefert_einen_gueltigen_pfad():
    """brief_rendern(brief) ohne alles muss gehen.

    In der ersten Fassung lag das PDG in einem Verzeichnis, das der Aufruf beim
    Verlassen wieder loeschte: Der Pfad kam zurueck, die Datei war weg.
    """
    from pathlib import Path

    ergebnis = dienst.brief_rendern(BRIEF)
    pfad = Path(ergebnis["pfad"])
    assert pfad.is_file(), f"{pfad} gibt es nicht — der Pfad ist wertlos"
    assert pfad.read_bytes().startswith(b"%PDF-")


def test_pruefen_erkennt_die_form_ohne_angabe(gerendert):
    ergebnis = dienst.brief_pruefen(pdf_base64=gerendert["pdf_base64"])
    assert ergebnis["form"] == "B"
    assert ergebnis["bestanden"] is True


def test_ein_inline_profil_braucht_keinen_server(tmp_path):
    """Ein Client ohne Dateisystemzugriff muss seinen Absender mitgeben können."""
    ergebnis = dienst.brief_rendern(BRIEF, profil=FREMDES_PROFIL, als="base64")
    assert ergebnis["bestanden"] is True
    assert "Fremd GmbH" in _text(base64.b64decode(ergebnis["pdf_base64"]), tmp_path)


def test_verworfene_bildfelder_werden_gemeldet():
    """Still verwerfen waere das Schlechteste: Der Brief käme ohne Logo zurück.

    Gegenprobe zugleich: Ein Profil ohne Bildfelder darf nichts melden — sonst
    stünde die Meldung immer da und sagte nichts aus.
    """
    mit_bildern = dienst.brief_rendern(BRIEF, profil=FREMDES_PROFIL, als="base64")
    assert set(mit_bildern["verworfen"]["felder"]) == {"briefkopf.logo", "signatur"}

    ohne = {**FREMDES_PROFIL, "briefkopf": {"zeilen": ["Fremd GmbH"]}}
    ohne.pop("signatur")
    schlicht = dienst.brief_rendern(BRIEF, profil=ohne, als="base64")
    assert "verworfen" not in schlicht


def test_der_aufrufparameter_schlaegt_das_frontmatter():
    """Sonst müsste man den Brieftext umschreiben, um den Absender zu wechseln."""
    ergebnis = dienst.brief_rendern(BRIEF, profil="example-grafik", form="A", als="base64")
    assert ergebnis["form"] == "A"


@pytest.mark.parametrize("ruf, erwartet", [
    (lambda: dienst.brief_rendern(BRIEF, als="xml"), "erlaubt sind"),
    (lambda: dienst.brief_pruefen(), "Genau eines"),
    (lambda: dienst.brief_pruefen(pdf_pfad="a.pdf", pdf_base64="eA=="), "Genau eines"),
    (lambda: dienst.brief_pruefen(pdf_pfad="gibt-es-nicht.pdf"), "nicht gefunden"),
    (lambda: dienst.brief_rendern(BRIEF, profil=42), "weder ein Name noch"),
])
def test_fehlbedienung_wird_benannt(ruf, erwartet):
    with pytest.raises(Eingabefehler) as fehler:
        ruf()
    assert erwartet in str(fehler.value)


def test_profile_auflisten_nennt_keine_inhalte():
    """In einem Profil stehen Anschrift, Bankdaten und Steuernummer."""
    ergebnis = dienst.profile_auflisten()
    assert "example" in ergebnis["profile"]
    assert all(isinstance(name, str) for name in ergebnis["profile"])
    assert "absender" not in str(ergebnis), "die Liste gibt Profilinhalte preis"


def _text(pdf_bytes: bytes, tmp_path) -> str:
    ziel = tmp_path / "brief.pdf"
    ziel.write_bytes(pdf_bytes)
    import pdfplumber

    with pdfplumber.open(str(ziel)) as dokument:
        return "\n".join(seite.extract_text() or "" for seite in dokument.pages)


# ── Was das SDK braucht ─────────────────────────────────────────────────────

def test_ohne_sdk_gibt_es_eine_meldung_mit_befehl(monkeypatch):
    """Ein nackter ImportError sagt dem Benutzer nicht, was zu tun ist."""
    from falzmarke.cli import Umgebungsfehler

    monkeypatch.setitem(sys.modules, "mcp", None)
    monkeypatch.setitem(sys.modules, "mcp.server.mcpserver", None)
    with pytest.raises(Umgebungsfehler) as fehler:
        dienst._mcp_modul()
    assert "falzmarke[mcp]" in str(fehler.value)


def test_der_server_meldet_die_drei_werkzeuge_an():
    pytest.importorskip("mcp", reason="optionales Extra falzmarke[mcp]")
    server = dienst.baue_server()
    assert server is not None
    assert len(dienst.WERKZEUGE) == 3


def test_erwartete_fehler_erreichen_den_client():
    """Ohne Übersetzung bekommt der Client „Error executing tool“ und sonst nichts.

    Gemessen am 26.08.2026 gegen einen echten stdio-Client: Das SDK maskiert
    jede Ausnahme ausser ToolError, damit keine Interna nach draussen gehen.
    „Pflichtfelder fehlen: datum“ ist aber kein Internum, sondern die Auskunft,
    aus der ein Client seinen Aufruf berichtigt.
    """
    pytest.importorskip("mcp", reason="optionales Extra falzmarke[mcp]")
    from mcp.server.mcpserver.exceptions import ToolError

    gewickelt = dienst._durchgereicht(dienst.brief_rendern, ToolError)
    with pytest.raises(ToolError) as fehler:
        gewickelt(BRIEF, als="xml")
    assert "erlaubt sind" in str(fehler.value)


def test_ein_absturz_bleibt_maskiert():
    """Gegenprobe: Nur die erwarteten Fehler werden durchgereicht, nicht alles.

    Wuerde der Wickel jede Ausnahme in ToolError verwandeln, ginge ein
    Programmierfehler als Benutzerhinweis nach draussen.
    """
    pytest.importorskip("mcp", reason="optionales Extra falzmarke[mcp]")
    from mcp.server.mcpserver.exceptions import ToolError

    def stuerzt_ab():
        raise KeyError("interner Schlüssel")

    gewickelt = dienst._durchgereicht(stuerzt_ab, ToolError)
    with pytest.raises(KeyError):
        gewickelt()
