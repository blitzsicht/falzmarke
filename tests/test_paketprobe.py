"""Der Release-Job muss vor dem Tag schon einmal gelaufen sein (#76).

Die erste Veröffentlichung auf PyPI brauchte fünf Anläufe. Alle fünf Ursachen
saßen **vor** dem Upload, vier fielen erst nach dem manuellen Freigabeklick auf
— und jeder Anlauf kostete eine Versionsnummer, die niemand je wieder verwenden
kann. Dass ein Tag sich nicht verschieben lässt, ist richtig und bleibt so; also
muss das, was ohne Tag prüfbar ist, vorher laufen.

Seit dem 27.08.2026 steht es in `scripts/paket_pruefen.sh`, und **beide**
Workflows rufen dasselbe Skript auf. Diese Tests halten das fest: Eine Probe,
die vom echten Job abweichen kann, prüft irgendwann etwas anderes als das, was
beim Release passiert — und dann ist sie schlimmer als keine, weil sie
Sicherheit vortäuscht.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from conftest import REPO

SKRIPT = REPO / "scripts" / "paket_pruefen.sh"
CI = REPO / ".github" / "workflows" / "ci.yml"
RELEASE = REPO / ".github" / "workflows" / "release.yml"
AUFRUF = "bash scripts/paket_pruefen.sh"


def test_das_skript_gibt_es_und_ist_ausfuehrbar():
    """Gefragt wird Git, nicht das Dateisystem.

    Erster Anlauf war `SKRIPT.stat().st_mode & 0o111` — auf Windows immer 0,
    weil dort kein Ausführbar-Bit existiert. Der Test war damit auf einer der
    drei Plattformen zwangsläufig rot und maß die falsche Sache: Entscheidend
    ist der Modus, den Git speichert, denn danach richtet sich der Linux-Runner,
    der das Skript ausführt.
    """
    assert SKRIPT.is_file(), f"{SKRIPT} fehlt"
    eintrag = subprocess.run(
        ["git", "ls-files", "-s", "scripts/paket_pruefen.sh"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert eintrag.startswith("100755"), (
        f"Git führt das Skript nicht als ausführbar: {eintrag.strip() or '— nicht getrackt —'}")


@pytest.mark.parametrize("datei", [CI, RELEASE], ids=lambda p: p.name)
def test_beide_workflows_rufen_dasselbe_skript(datei):
    assert AUFRUF in datei.read_text(encoding="utf-8"), (
        f"{datei.name} ruft {AUFRUF!r} nicht auf. Wer die Schritte dort wieder "
        "ausschreibt, hat zwei Fassungen, die auseinanderlaufen.")


def test_die_pruefung_wuerde_ein_auseinanderlaufen_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass gerade beide dastehen."""
    ohne = RELEASE.read_text(encoding="utf-8").replace(AUFRUF, "python -m build", 1)
    assert AUFRUF not in ohne, "die Sabotage greift nicht"


@pytest.mark.parametrize("schritt, muster", [
    # Ohne `--wheel`: Der Release-Job baut beides, und ein sdist, das erst beim
    # Upload gebaut wird, ist bis dahin ungeprueft.
    ("sdist und Wheel", r"-m build\b(?!.*--wheel)"),
    ("twine check", r"twine check"),
    ("README-Prüfung", r"pytest tests/test_readme_auf_pypi\.py"),
    ("dist-Wächter", r"! -name '\*\.whl'"),
])
def test_das_skript_enthaelt_die_schritte_des_release_jobs(schritt, muster):
    """Was der Release-Job vor dem Upload prüfte, muss im Skript stehen.

    Sonst wandert bei der Umstellung stillschweigend ein Schritt verloren —
    und genau einer davon (`dist/` enthält nur Pakete) hat Lauf 32966455275
    gerettet, nachdem eine Prüfsummen-Datei den Upload zu Fall gebracht hatte.
    """
    text = SKRIPT.read_text(encoding="utf-8")
    assert re.search(muster, text), f"Schritt fehlt im Skript: {schritt}"


def test_der_release_job_schreibt_die_schritte_nicht_mehr_aus():
    """Die Gegenrichtung: Doppelt gepflegt ist auseinandergelaufen."""
    text = RELEASE.read_text(encoding="utf-8")
    ausserhalb_kommentar = "\n".join(
        z for z in text.splitlines() if not z.lstrip().startswith("#"))
    for verboten in ("twine check", "python -m build"):
        assert verboten not in ausserhalb_kommentar, (
            f"release.yml führt {verboten!r} wieder selbst aus statt über das Skript.")


def test_das_skript_fasst_die_umgebung_des_aufrufers_nicht_an():
    """Es soll lokal vor einem Release laufen können, ohne etwas zu verändern.

    Ein `pip install` in die aktive Umgebung wäre genau die Nebenwirkung, wegen
    der niemand das Skript vorher von Hand fährt.
    """
    text = SKRIPT.read_text(encoding="utf-8")
    assert "python3 -m venv" in text, "das Skript legt kein eigenes venv an"
    for zeile in text.splitlines():
        nackt = zeile.strip()
        if nackt.startswith("#") or "pip install" not in nackt:
            continue
        assert '"$VENV/bin/pip"' in nackt, (
            f"pip-Aufruf ohne venv — verändert die Umgebung des Aufrufers: {nackt}")
