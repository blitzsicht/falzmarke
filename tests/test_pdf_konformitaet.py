"""Tests für die Konformitätsprüfung mit veraPDF (Issue #34).

Zwei Ebenen, bewusst getrennt:

**Ohne veraPDF** läuft alles, was das Skript selbst entscheidet: Welche
Konformität behauptet eine Datei? Was passiert bei einer Datei ohne
Deklaration? Endet der Lauf im richtigen Zustand, wenn das fremde Werkzeug
fehlt? Diese Tests laufen überall, auch ohne Java.

**Mit veraPDF** läuft der eigentliche Nachweis. Fehlt das Werkzeug, werden
diese Tests übersprungen — aber der Lauf ohne sie belegt die Konformität dann
eben *nicht*. Damit das nicht still passiert, prüft
`test_verapdf_fehlt_ist_nicht_gruen`, dass das Skript in diesem Fall Exit 2
liefert und nicht 0: „nicht geprüft" ist ein eigener Zustand, kein Grün.
"""

from __future__ import annotations

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


# ── ohne veraPDF prüfbar ────────────────────────────────────────────────────

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


def test_datei_ohne_deklaration_ist_ein_befund(tmp_path):
    """Sonst wäre der Lauf genau dann am grünsten, wenn nichts behauptet wird."""
    pdf = _rendere(tmp_path / "ohne.pdf", "--no-pdfa")
    assert _lauf(str(pdf)).returncode == 1


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


def test_fehlende_datei_ist_ein_befund():
    assert _lauf("gibt-es-nicht.pdf").returncode == 1


def test_verapdf_fehlt_ist_nicht_gruen(tmp_path):
    """Der dritte Zustand: NICHT GEPRÜFT.

    Ein Lauf ohne das fremde Werkzeug darf nicht wie ein bestandener aussehen.
    Exit 2 unterscheidet ihn von beidem — bestanden (0) und Befund (1).
    """
    pdf = _rendere(tmp_path / "normal.pdf")
    ergebnis = subprocess.run(
        [sys.executable, str(SKRIPT), str(pdf)],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert ergebnis.returncode == 2
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
