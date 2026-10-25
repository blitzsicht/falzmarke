"""Der Zuruf an die Entwurfsbrücke (ADR 0054).

ANLASS (25.10.2026): „Ich konnte die Entwürfe in Thunderbird nicht öffnen.
Bitte klick sie selbst an.“ Der Postfach-Entwurf aus ADR 0051 lag richtig im
Ordner, aber kein Fenster ging auf, und eine Sitzung kann in Thunderbird nicht
klicken. Das Add-on unter `thunderbird/entwurfsbruecke/` öffnet ihn auf Zuruf;
hier steht, wie falzmarke ruft und was es aus den Antworten macht.

Keine echte Verbindung: die Attrappe aus `bruecke_attrappe.py`.
"""

from __future__ import annotations

import json

import pytest
from bruecke_attrappe import BrueckenAttrappe
from falzmarke import bruecke


def _mit(monkeypatch, attrappe: BrueckenAttrappe) -> BrueckenAttrappe:
    monkeypatch.setattr(bruecke, "VERBINDEN", attrappe)
    return attrappe


def _echter_weg(monkeypatch) -> None:
    """Gibt `_verbinde_unix` frei — dort liegen die Prüfungen am Socketpfad.

    `conftest._keine_echte_bruecke` besetzt `VERBINDEN` für jeden Test; ohne
    diese Freigabe liefe keine der Proben darunter durch den Code, den sie
    prüft. Verbunden wird trotzdem nichts: Der Wächter liegt eine Schicht
    tiefer auf `bruecke._sockel`.
    """
    monkeypatch.setattr(bruecke, "VERBINDEN", None)


# ── Die Anfrage ─────────────────────────────────────────────────────────────

def test_eine_zeile_ascii_an_den_socket(monkeypatch, tmp_path):
    attrappe = _mit(monkeypatch, BrueckenAttrappe())
    socket = tmp_path / bruecke.SOCKET_DATEI
    bruecke.entwurf_oeffnen("müller@example.de", "219248",
                            umgebung={"FALZMARKE_BRUECKE_SOCKET": str(socket)})
    (zeile,) = attrappe.zeilen
    assert zeile.endswith(b"\n") and zeile.count(b"\n") == 1
    zeile.decode("ascii")  # wirft, wenn ein Umlaut roh drinsteht
    assert json.loads(zeile) == {"befehl": "entwurf_oeffnen", "konto": "müller@example.de",
                                 "uid": 219248}
    assert attrappe.adressen == [str(socket)]


def test_der_socketpfad_laesst_sich_setzen(monkeypatch, tmp_path):
    attrappe = _mit(monkeypatch, BrueckenAttrappe())
    bruecke.ping(umgebung={"FALZMARKE_BRUECKE_SOCKET": str(tmp_path / "anders.sock")})
    assert attrappe.adressen == [str(tmp_path / "anders.sock")]


def test_ohne_thunderbird_profil_gibt_es_nichts_zu_rufen(monkeypatch):
    """Der Socket liegt im Profil. Kein Profil, kein Socket — und ein Satz dazu."""
    from falzmarke import oeffnen

    _echter_weg(monkeypatch)
    monkeypatch.setattr(oeffnen, "thunderbird_standardprofil", lambda _ordner: None)
    assert bruecke.socketpfad({}) == ""
    with pytest.raises(bruecke.BrueckenFehler) as fehler:
        bruecke.ping(umgebung={})
    assert bruecke.OHNE_PROFIL in str(fehler.value)


def test_der_socket_liegt_im_thunderbird_profil(monkeypatch, tmp_path):
    from falzmarke import oeffnen

    monkeypatch.setattr(oeffnen, "thunderbird_standardprofil", lambda _ordner: tmp_path)
    assert bruecke.socketpfad({}) == str(tmp_path / "bruecke.sock")


def test_ein_zu_langer_socketpfad_sagt_was_zu_tun_ist(monkeypatch):
    """`sun_path` fasst 104 Byte. Gemessen am 25.10.2026 war der erste Name
    (`falzmarke-entwurfsbruecke.sock`) im Profil dieses Rechners 105 Byte lang —
    eins zu viel; `bruecke.sock` sind 87. Ohne diese Prüfung käme hier ein
    nacktes OSError aus dem Betriebssystem."""
    _echter_weg(monkeypatch)
    lang = "/tmp/" + "x" * 100 + "/bruecke.sock"
    assert len(lang.encode()) > bruecke.MAX_SOCKETPFAD
    with pytest.raises(bruecke.BrueckenFehler) as fehler:
        bruecke.ping(umgebung={"FALZMARKE_BRUECKE_SOCKET": lang})
    assert "FALZMARKE_BRUECKE_SOCKET" in str(fehler.value)
    assert str(bruecke.MAX_SOCKETPFAD) in str(fehler.value)


def test_gegenprobe_ein_kurzer_pfad_geht_bis_zum_verbinden(monkeypatch):
    """Die Probe nebenan misst die Länge, nicht das Verbinden: Ein kurzer Pfad
    kommt bis zum Riegel des Wächters."""
    from conftest import ABGEFANGEN, WaechterFehler

    _echter_weg(monkeypatch)
    # Nicht `tmp_path`: Der Pfad von pytest ist hier selbst 135 Byte lang und
    # würde an derselben Prüfung scheitern wie die Probe darüber.
    kurz = "/tmp/falzmarke-probe.sock"
    assert len(kurz.encode()) <= bruecke.MAX_SOCKETPFAD
    with pytest.raises(WaechterFehler):
        bruecke.ping(umgebung={"FALZMARKE_BRUECKE_SOCKET": kurz})
    assert ABGEFANGEN and "Entwurfsbrücke" in ABGEFANGEN[0]
    ABGEFANGEN.clear()


def test_wer_sich_nicht_als_bruecke_ausweist_ist_keine(monkeypatch, tmp_path):
    """Die Rechte am Socket machen eine Fremdantwort unwahrscheinlich, nicht
    unmöglich — `FALZMARKE_BRUECKE_SOCKET` zeigt, wohin man ihn stellt."""
    _mit(monkeypatch, BrueckenAttrappe({"ok": True, "name": "etwas anderes", "version": "9"}))
    with pytest.raises(bruecke.BrueckenFehler) as fehler:
        bruecke.ping(umgebung={"FALZMARKE_BRUECKE_SOCKET": str(tmp_path / "s.sock")})
    assert "nicht die Entwurfsbrücke" in str(fehler.value)


def test_steuerzeichen_aus_der_antwort_gehen_nicht_in_die_ausgabe(monkeypatch, tmp_path):
    """`json.loads` lässt echte ESC-Sequenzen durch, und von dort gehen sie in
    `print`. Der Betreff verliert sie ganz, der Fenstertext behält den Umbruch."""
    umgebung = {"FALZMARKE_BRUECKE_SOCKET": str(tmp_path / "s.sock")}
    _mit(monkeypatch, BrueckenAttrappe({"ok": True, "zustand": "geoeffnet",
                                        "betreff": "Rechnung\x1b[2Küberschrieben\nZeile 2"}))
    lage = bruecke.entwurf_oeffnen("a@example.de", 1, umgebung=umgebung)
    assert lage.betreff == "Rechnung[2KüberschriebenZeile 2"
    assert "\x1b" not in lage.betreff and "\n" not in lage.betreff

    _mit(monkeypatch, BrueckenAttrappe({"ok": True, "fenster": [
        {"betreff": "a\x07b", "text": "Zeile 1\nZeile 2\x1b[31m", "an": ["x\x00@y.de"]}]}))
    (fenster,) = bruecke.offene_entwuerfe(umgebung=umgebung)
    assert fenster["betreff"] == "ab"
    assert fenster["text"] == "Zeile 1\nZeile 2[31m"
    assert "\x1b" not in fenster["text"]
    assert fenster["an"] == ["x@y.de"]


def test_abgeschaltet_ruft_niemanden(monkeypatch):
    attrappe = _mit(monkeypatch, BrueckenAttrappe())
    lage = bruecke.entwurf_oeffnen("a@example.de", 1, umgebung={"FALZMARKE_BRUECKE": "nie"})
    assert lage.zustand == "aus" and "FALZMARKE_BRUECKE=nie" in lage.grund
    assert attrappe.anfragen == []


def test_gegenprobe_ohne_schalter_wird_gerufen(monkeypatch):
    attrappe = _mit(monkeypatch, BrueckenAttrappe())
    bruecke.entwurf_oeffnen("a@example.de", 1, umgebung={"FALZMARKE_BRUECKE": ""})
    assert len(attrappe.anfragen) == 1


def test_eine_kaputte_uid_ruft_niemanden(monkeypatch):
    attrappe = _mit(monkeypatch, BrueckenAttrappe())
    lage = bruecke.entwurf_oeffnen("a@example.de", "x7", umgebung={})
    assert lage.zustand == "fehler" and attrappe.anfragen == []


# ── Die Antworten ───────────────────────────────────────────────────────────

def test_ping_liefert_fassung_und_thunderbird(monkeypatch):
    _mit(monkeypatch, BrueckenAttrappe())
    antwort = bruecke.ping(umgebung={})
    assert antwort["name"] == "entwurfsbruecke" and antwort["thunderbird"] == "158.0.1"


@pytest.mark.parametrize("zustand", ["geoeffnet", "schon_offen"])
def test_offen_mit_dem_betreff_aus_dem_fenster(monkeypatch, zustand):
    _mit(monkeypatch, BrueckenAttrappe({"ok": True, "zustand": zustand, "betreff": "Nachtrag"}))
    lage = bruecke.entwurf_oeffnen("a@example.de", 5, umgebung={})
    assert lage.offen and lage.zustand == zustand and lage.betreff == "Nachtrag"


@pytest.mark.parametrize("zustand", ["ungewiss", "fenster_ohne_entwurf", "neu_erfunden"])
def test_kein_gesehenes_fenster_ist_ungewiss_nicht_fehler(monkeypatch, zustand):
    _mit(monkeypatch, BrueckenAttrappe({"ok": True, "zustand": zustand}))
    lage = bruecke.entwurf_oeffnen("a@example.de", 5, umgebung={})
    assert lage.zustand == "ungewiss" and not lage.offen and lage.grund


def test_ein_fehler_des_add_ons_wird_ein_satz(monkeypatch):
    _mit(monkeypatch, BrueckenAttrappe({"ok": False, "fehler": "konto_fehlt"}))
    lage = bruecke.entwurf_oeffnen("a@example.de", 5, umgebung={})
    assert lage.zustand == "fehler" and lage.grund == bruecke.FEHLERTEXTE["konto_fehlt"]


def test_eine_unbekannte_fehlerkennung_wird_genannt(monkeypatch):
    _mit(monkeypatch, BrueckenAttrappe({"ok": False, "fehler": "gibts_nicht"}))
    lage = bruecke.entwurf_oeffnen("a@example.de", 5, umgebung={})
    assert "gibts_nicht" in lage.grund


def test_niemand_da_ist_fehler_und_sagt_warum(monkeypatch):
    _mit(monkeypatch, BrueckenAttrappe(fehler=ConnectionRefusedError(61, "refused")))
    lage = bruecke.entwurf_oeffnen("a@example.de", 5, umgebung={})
    assert lage.zustand == "fehler"
    assert "Thunderbird ist zu oder das Add-on Entwurfsbrücke fehlt" in lage.grund


def test_eine_fehlende_antwort_nach_der_anfrage_ist_ungewiss(monkeypatch):
    """Abgeschickt, aber keine Antwort: Vielleicht steht das Fenster schon."""
    _mit(monkeypatch, BrueckenAttrappe(fehler_beim_lesen=TimeoutError("timed out")))
    lage = bruecke.entwurf_oeffnen("a@example.de", 5, umgebung={})
    assert lage.zustand == "ungewiss" and "Sekunden" in lage.grund


@pytest.mark.parametrize("roh, teil", [
    (b"", "ohne vollständige Antwort"),            # Verbindung gleich wieder zu
    (b'{"ok": true', "ohne vollständige Antwort"),  # abgerissen
    (b"HTTP/1.1 200 OK\n", "kein JSON"),            # ein anderer Dienst auf dem Port
    (b"[1, 2]\n", "kein JSON-Objekt"),
])
def test_unbrauchbare_antworten_sind_ungewiss(monkeypatch, roh, teil):
    _mit(monkeypatch, BrueckenAttrappe(roh=roh))
    lage = bruecke.entwurf_oeffnen("a@example.de", 5, umgebung={})
    assert lage.zustand == "ungewiss" and teil in lage.grund


def test_eine_ueberlange_antwort_bricht_ab(monkeypatch):
    _mit(monkeypatch, BrueckenAttrappe(roh=b"x" * (bruecke.MAX_ANTWORT + 10)))
    with pytest.raises(bruecke.BrueckenFehler, match="länger als"):
        bruecke.ping(umgebung={})


def test_ping_wirft_wenn_niemand_da_ist(monkeypatch):
    _mit(monkeypatch, BrueckenAttrappe(fehler=ConnectionRefusedError(61, "refused")))
    with pytest.raises(bruecke.BrueckenFehler) as fehler:
        bruecke.ping(umgebung={})
    assert not fehler.value.ungewiss


def test_ein_fenster_mit_langem_text_kommt_ganz_an(monkeypatch):
    """Seit 0.3.0 trägt `fenster` den Text, bis 20.000 Zeichen — mit Umlauten als
    ASCII-Escape sechsmal so lang (ADR 0056). Das muss unter `MAX_ANTWORT` bleiben."""
    text = "ä" * 20000
    attrappe = _mit(monkeypatch, BrueckenAttrappe({"ok": True, "fenster": [
        {"titel": "t", "betreff": "b", "draft_id": "", "live": True, "an": ["a@example.de"],
         "blindkopie": ["dms@example.de"], "anhaenge": ["x.pdf"], "text": text}]}))
    (fenster,) = bruecke.offene_entwuerfe(umgebung={})
    assert fenster["text"] == text and fenster["blindkopie"] == ["dms@example.de"]
    assert 100_000 < len(json.dumps({"fenster": [fenster]})) < bruecke.MAX_ANTWORT
    assert attrappe.anfragen
