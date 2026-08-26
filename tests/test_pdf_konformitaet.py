"""Tests für die Konformitätsprüfung mit veraPDF (Issue #34).

Zwei Ebenen, bewusst getrennt:

**Ohne veraPDF** laufen die Entscheidungen, die das Skript allein trifft: XMP
lesen, die Deklaration erkennen, und den richtigen Zustand melden, wenn das
fremde Werkzeug fehlt. Vier Tests, sie laufen in der ganzen Plattform-Matrix.

**Mit veraPDF** läuft der eigentliche Nachweis. Fehlt es, werden diese Tests
übersprungen — der Lauf belegt die Konformität dann eben *nicht*. Damit das
nicht still passiert, prüft `test_verapdf_fehlt_ist_nicht_gruen`, dass das
Skript in diesem Fall Exit 2 liefert und nicht 0: „nicht geprüft" ist ein
eigener Zustand, kein Grün. Und der veraPDF-Job in der CI fährt sie alle.

Wer prüft, dass die Aufteilung stimmt? Die CI selbst hat es getan: Drei Tests
riefen anfangs das Skript als Prozess auf und erwarteten Exit 1 — ohne veraPDF
bricht es aber vorher mit Exit 2 ab. Sie schlugen in der Matrix fehl, weil sie
ihren Gegenstand gar nicht erreichten. Lokal, mit installiertem veraPDF, waren
sie grün. Ein Test, der nur auf der Maschine seines Autors trennt, ist genau
die Sorte Beleg, gegen die dieses Projekt geschrieben ist.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO

SKRIPT = REPO / "scripts" / "pdf_konformitaet.py"
BEISPIEL = REPO / "examples" / "brief-form-b.md"
HAT_VERAPDF = shutil.which("verapdf") is not None

sys.path.insert(0, str(REPO / "scripts"))
import pdf_konformitaet as pk  # noqa: E402


def _rendere(ziel: Path, *extra: str) -> Path:
    lauf = subprocess.run(
        [sys.executable, str(REPO / "skill" / "scripts" / "falzmarke.py"),
         "render", str(BEISPIEL), "-o", str(ziel), *extra],
        capture_output=True, text=True,
    )
    assert lauf.returncode == 0, f"Render fehlgeschlagen: {lauf.stderr[:300]}"
    assert ziel.exists()
    return ziel


def _lauf(*argumente: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SKRIPT), *argumente], capture_output=True, text=True
    )


# ── ohne veraPDF prüfbar: die Entscheidungen, die das Skript selbst trifft ──
#
# Was hier steht, kommt ohne das fremde Werkzeug aus: XMP lesen, Deklaration
# erkennen, den richtigen Zustand melden, wenn veraPDF fehlt.
#
# ACHTUNG, hier lag ein Denkfehler: Drei Tests weiter unten rufen das SKRIPT als
# Prozess auf und erwarten Exit 1. Ohne veraPDF bricht es aber vorher mit Exit 2
# ab (NICHT GEPRÜFT) — sie erreichen ihren Gegenstand gar nicht und schlugen in
# der CI-Matrix fehl, wo kein veraPDF installiert ist. Sie tragen deshalb
# dasselbe `skipif` wie die Prüfungen darunter. Die Deklarations-Logik wird
# stattdessen direkt an der Funktion geprüft, nicht über den Prozess.

def test_deklaration_wird_gelesen_statt_angenommen(tmp_path):
    """Ein normal gerendertes PDF behauptet PDF/A-2b — und das liest das Skript.

    Der Wert steht bewusst nicht als Konstante im Skript: Wird das Projekt
    eines Tages auf A-3b umgestellt, prüft es ohne Änderung mit.
    """
    pdf = _rendere(tmp_path / "normal.pdf")
    assert pk.deklarierte_standards(pdf) == ["2b"]


def test_pdfua_wird_zusaetzlich_erkannt(tmp_path):
    pdf = _rendere(tmp_path / "ua.pdf", "--pdfua")
    assert pk.deklarierte_standards(pdf) == ["2b", "ua1"]


def test_ohne_pdfa_gibt_es_nichts_zu_behaupten(tmp_path):
    """`--no-pdfa` erzeugt eine Datei ohne Deklaration.

    Das ist die Voraussetzung der Gegenprobe: Trüge diese Datei doch eine
    Deklaration, prüfte die Gegenprobe etwas anderes als gedacht.
    """
    pdf = _rendere(tmp_path / "ohne.pdf", "--no-pdfa")
    assert pk.deklarierte_standards(pdf) == []


@pytest.mark.skipif(not HAT_VERAPDF, reason="veraPDF nicht installiert")
def test_datei_ohne_deklaration_ist_ein_befund(tmp_path):
    """Sonst wäre der Lauf genau dann am grünsten, wenn nichts behauptet wird."""
    pdf = _rendere(tmp_path / "ohne.pdf", "--no-pdfa")
    assert _lauf(str(pdf)).returncode == 1


@pytest.mark.skipif(not HAT_VERAPDF, reason="veraPDF nicht installiert")
def test_null_pruefungen_sind_kein_erfolg(tmp_path):
    """Leere Menge gegen leere Menge belegt nichts.

    Wird die einzige Datei übergangen, bleiben null Prüfungen übrig — der Lauf
    muss trotzdem rot sein, sonst liesse sich jeder Nachweis durch Übergehen
    erzeugen.
    """
    pdf = _rendere(tmp_path / "ohne.pdf", "--no-pdfa")
    ergebnis = _lauf(str(pdf), "--ohne-deklaration", "erlaubt")
    assert ergebnis.returncode == 1
    assert "0 Konformitätsprüfungen" in ergebnis.stdout


@pytest.mark.skipif(not HAT_VERAPDF, reason="veraPDF nicht installiert")
def test_fehlende_datei_ist_ein_befund():
    assert _lauf("gibt-es-nicht.pdf").returncode == 1


def test_verapdf_fehlt_ist_nicht_gruen(tmp_path):
    """Der dritte Zustand: NICHT GEPRÜFT.

    Ein Lauf ohne das fremde Werkzeug darf nicht wie ein bestandener aussehen.
    Exit 2 unterscheidet ihn von beidem — bestanden (0) und Befund (1).
    """
    pdf = _rendere(tmp_path / "normal.pdf")
    # Nur PATH leeren, nicht die ganze Umgebung ersetzen: Windows braucht
    # SYSTEMROOT und COMSPEC, sonst startet der Kindprozess gar nicht erst —
    # der Test wäre dann aus dem falschen Grund rot.
    umgebung = {**os.environ, "PATH": ""}
    ergebnis = subprocess.run(
        [sys.executable, str(SKRIPT), str(pdf)],
        capture_output=True, text=True, env=umgebung,
    )
    assert ergebnis.returncode == 2, ergebnis.stdout + ergebnis.stderr
    assert "NICHT GEPRÜFT" in ergebnis.stderr


# ── nur mit veraPDF: der eigentliche Nachweis ───────────────────────────────

@pytest.mark.skipif(not HAT_VERAPDF, reason="veraPDF nicht installiert")
def test_beispiel_besteht_bei_einem_fremden_werkzeug(tmp_path):
    pdf = _rendere(tmp_path / "normal.pdf")
    ergebnis = _lauf(str(pdf))
    assert ergebnis.returncode == 0, ergebnis.stdout
    assert "OK" in ergebnis.stdout


@pytest.mark.skipif(not HAT_VERAPDF, reason="veraPDF nicht installiert")
def test_gegenprobe_faengt_ein_nicht_konformes_pdf():
    """Der Nachweis, dass die Prüfung überhaupt trennt.

    Ohne diesen Test belegt ein grüner Lauf nur, dass veraPDF gestartet ist.
    """
    ok, meldung = pk.gegenprobe(BEISPIEL)
    assert ok, meldung


@pytest.mark.skipif(not HAT_VERAPDF, reason="veraPDF nicht installiert")
def test_verapdf_haelt_das_versprechen_nicht_fuer_jede_datei(tmp_path):
    """Gegenprobe auf der untersten Ebene: veraPDF sagt auch mal Nein.

    Ein Validator, der alles durchwinkt, wäre als Beleg wertlos — und das liesse
    sich von aussen nicht von einem korrekten Lauf unterscheiden.
    """
    ohne = _rendere(tmp_path / "ohne.pdf", "--no-pdfa")
    bestanden, _ = pk.verapdf_urteil(ohne, "2b")
    assert not bestanden

    mit = _rendere(tmp_path / "mit.pdf")
    bestanden, meldung = pk.verapdf_urteil(mit, "2b")
    assert bestanden, meldung


@pytest.mark.skipif(not HAT_VERAPDF, reason="veraPDF nicht installiert")
def test_pruefsumme_belegt_dieselbe_datei(tmp_path):
    """AC3: geprüft wird, was ausgeliefert wird.

    Die Summe im Bericht muss die der Datei auf der Platte sein — sonst bezöge
    sich das Urteil womöglich auf einen Zwischenstand, der danach noch
    Metadaten bekommt.
    """
    pdf = _rendere(tmp_path / "normal.pdf")
    ergebnis = _lauf(str(pdf))
    assert ergebnis.returncode == 0
    assert pk.sha256(pdf)[:16] in ergebnis.stdout
