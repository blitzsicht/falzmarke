"""Wo Profile gesucht werden — und dass eigene ein Update überstehen.

Der Anlass ist ein gemessener Fehler: Bis v0.1.0 lag der einzige Ort für eigene
Profile innerhalb der Installation (`skill/typst/profiles.local/`). Wer den
Skill ersetzte — Zip neu hochladen, `pip install -U` —, verlor seine Absender
und konnte keinen einzigen alten Brief mehr setzen.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from falzmarke import cli as falzmarke
from conftest import REPO, SKILL

CLI = SKILL / "scripts" / "falzmarke.py"


@pytest.fixture
def xdg(tmp_path, monkeypatch):
    """Ein eigenes Konfigurationsverzeichnis, damit nichts im echten landet."""
    ziel = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(ziel))
    return ziel / "falzmarke" / "profiles"


def profil_ablegen(verzeichnis: Path, name: str) -> Path:
    verzeichnis.mkdir(parents=True, exist_ok=True)
    ziel = verzeichnis / f"{name}.yaml"
    inhalt = (SKILL / "falzmarke" / "typst" / "profiles" / "example.yaml").read_text(encoding="utf-8")
    ziel.write_text(inhalt.replace("Beispiel GmbH", f"{name} GmbH"), encoding="utf-8")
    return ziel


def test_benutzerverzeichnis_folgt_xdg(xdg, monkeypatch):
    assert falzmarke.benutzer_profilverzeichnis() == xdg


def test_ohne_xdg_liegt_es_unter_config(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert falzmarke.benutzer_profilverzeichnis() == Path.home() / ".config" / "falzmarke" / "profiles"


def test_profil_im_benutzerverzeichnis_wird_gefunden(xdg):
    profil_ablegen(xdg, "eigenes")
    assert "eigenes" in falzmarke.finde_profile()


def test_profil_im_arbeitsverzeichnis_wird_gefunden(tmp_path, monkeypatch, xdg):
    profil_ablegen(tmp_path / "profiles", "vorgang")
    monkeypatch.chdir(tmp_path)
    assert "vorgang" in falzmarke.finde_profile()


def test_vorrang_arbeitsverzeichnis_vor_benutzerverzeichnis(tmp_path, monkeypatch, xdg):
    """Beide heißen gleich — das zum Vorgang gehörende gewinnt."""
    profil_ablegen(xdg, "doppelt")
    profil_ablegen(tmp_path / "profiles", "doppelt")
    monkeypatch.chdir(tmp_path)
    assert falzmarke.finde_profile()["doppelt"].parent == tmp_path / "profiles"


def test_vorrang_flag_vor_allem(tmp_path, monkeypatch, xdg):
    profil_ablegen(xdg, "doppelt")
    ausdruecklich = tmp_path / "woanders"
    profil_ablegen(ausdruecklich, "doppelt")
    assert falzmarke.finde_profile(ausdruecklich)["doppelt"].parent == ausdruecklich


def test_beispiel_bleibt_auffindbar(xdg):
    assert "example" in falzmarke.finde_profile()


def test_init_profil_legt_am_updatefesten_ort_an(xdg):
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "init-profil", "meinefirma"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == falzmarke.EXIT_OK, ergebnis.stderr
    assert (xdg / "meinefirma.yaml").is_file()
    assert str(SKILL) not in str(xdg), "Der Ort darf nicht in der Installation liegen"


def test_init_profil_ueberschreibt_nicht(xdg):
    profil_ablegen(xdg, "meinefirma")
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "init-profil", "meinefirma"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    assert "gibt es schon" in ergebnis.stderr


def test_erzeugtes_profil_rendert(xdg, tmp_path):
    subprocess.run([sys.executable, str(CLI), "init-profil", "frisch"], capture_output=True)
    brief = tmp_path / "b.md"
    brief.write_text(
        "---\nprofil: frisch\nempfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]\n"
        "datum: 2026-08-25\nbetreff: Probe\nanrede: Sehr geehrte Damen und Herren,\n---\nText.\n",
        encoding="utf-8",
    )
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "render", str(brief), "-o", str(tmp_path / "b.pdf")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == falzmarke.EXIT_OK, ergebnis.stdout + ergebnis.stderr


def test_profil_ueberlebt_das_ersetzen_der_installation(tmp_path, monkeypatch):
    """Die Gegenprobe zum eigentlichen Fehler.

    Der Skill wird kopiert, ein Profil an beiden Orten angelegt, dann die
    Installation ersetzt — so wie ein Zip-Upload oder `pip install -U` es tut.
    Das Profil im Benutzerverzeichnis muss danach noch da sein, das in der
    Installation ist erwartungsgemäß weg.
    """
    installation = tmp_path / "installation"
    shutil.copytree(SKILL, installation)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    benutzer = tmp_path / "config" / "falzmarke" / "profiles"

    profil_ablegen(benutzer, "aussen")
    profil_ablegen(installation / "typst" / "profiles.local", "innen")

    monkeypatch.setattr(falzmarke, "TYPST_DIR", installation / "typst")
    vorher = falzmarke.finde_profile()
    assert {"aussen", "innen"} <= set(vorher)

    # Aktualisierung: Installation wird ersetzt
    shutil.rmtree(installation)
    shutil.copytree(SKILL, installation)

    nachher = falzmarke.finde_profile()
    assert "aussen" in nachher, "Das eigene Profil hat das Update nicht überstanden"
    assert "innen" not in nachher, (
        "Profile in der Installation überleben ein Update nicht — "
        "wäre das hier anders, würde der Test den Fehler nicht mehr messen"
    )
