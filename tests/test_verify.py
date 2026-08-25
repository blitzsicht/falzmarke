"""verify: die Prüfung nach dem Render, auch für fremde PDFs."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

import pytest

from normbrief import geometrie
from normbrief import cli as normbrief
from conftest import REPO, SKILL

CLI = SKILL / "scripts" / "normbrief.py"
PROFILE = SKILL / "normbrief" / "typst" / "profiles"


def rufe(*argumente) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *map(str, argumente)], capture_output=True, text=True
    )


# ── Bericht ─────────────────────────────────────────────────────────────────

def test_bericht_ist_standardmaessig_eine_zeile(gerendert):
    """30 Zeilen je Render verdrängen im Kontext eines Sprachmodells den Brief."""
    pdf, form = gerendert["brief-form-b"]
    ergebnis = rufe("verify", pdf, "--form", form)
    zeilen = ergebnis.stdout.strip().splitlines()
    assert len(zeilen) == 1, ergebnis.stdout
    assert re.match(r"OK  verify: \d+/\d+ Maße eingehalten", zeilen[0])


def test_verbose_zeigt_alle(gerendert):
    pdf, form = gerendert["brief-form-b"]
    ergebnis = rufe("verify", pdf, "--form", form, "--verbose")
    assert len(ergebnis.stdout.strip().splitlines()) > 20


def test_bei_abweichung_nur_die_betroffenen_zeilen(gerendert):
    """Form-B-PDF gegen Form-A-Maße: es sollen die Fehler stehen, nicht alles."""
    pdf, _ = gerendert["brief-form-b"]
    ergebnis = rufe("verify", pdf, "--form", "A")
    assert ergebnis.returncode == normbrief.EXIT_GEOMETRIE
    zeilen = ergebnis.stdout.strip().splitlines()
    assert all(z.startswith("FEHL") or z.startswith("verify:") for z in zeilen), ergebnis.stdout


# ── Form erkennen ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,erwartet", [("brief-form-a", "A"), ("brief-form-b", "B")])
def test_form_wird_aus_den_marken_erkannt(gerendert, name, erwartet):
    pdf, _ = gerendert[name]
    assert geometrie.erkenne_form(pdf) == erwartet


def test_verify_ohne_form_angabe(gerendert):
    pdf, _ = gerendert["brief-form-a"]
    ergebnis = rufe("verify", pdf)
    assert ergebnis.returncode == normbrief.EXIT_OK, ergebnis.stdout + ergebnis.stderr


def test_check_bleibt_als_alias(gerendert):
    pdf, form = gerendert["brief-form-b"]
    assert rufe("check", pdf, "--form", form).returncode == normbrief.EXIT_OK


# ── Fremde PDFs ─────────────────────────────────────────────────────────────

def test_verschobene_marke_wird_mit_millimetern_gemeldet(tmp_path):
    """Der Linter-Fall: Eine Marke bei 102 statt 105 mm ist ein verschobenes
    Layout, keine fehlende Marke. Bis v0.1.2 hieß es dort 'nicht gefunden'."""
    ziel = tmp_path / "typst"
    shutil.copytree(SKILL / "normbrief" / "typst", ziel)
    datei = ziel / "vendor" / "letter-pro-v3.0.0.typ"
    datei.write_text(
        datei.read_text(encoding="utf-8").replace(
            "folding-mark-1-pos: 105mm", "folding-mark-1-pos: 102mm", 1),
        encoding="utf-8",
    )
    original = normbrief.TYPST_DIR
    normbrief.TYPST_DIR = ziel
    try:
        pdf, form = normbrief.rendere(
            REPO / "examples" / "brief-form-b.md", tmp_path / "v.pdf",
            profil_verzeichnis=ziel / "profiles",
        )
    finally:
        normbrief.TYPST_DIR = original

    treffer = [p for p in geometrie.pruefe(pdf, form).pruefungen if p.name == "Falzmarke 1, y"]
    assert treffer and not treffer[0].bestanden
    assert "102.00" in treffer[0].ist and "3.00 mm zu hoch" in treffer[0].ist


def test_pdf_ohne_marken_meldet_die_form_als_unbekannt(tmp_path):
    quelle = tmp_path / "s.typ"
    quelle.write_text('#set page(paper: "a4")\nEin Satz ohne Marken.\n', encoding="utf-8")
    import typst

    typst.compile(str(quelle), output=str(tmp_path / "fremd.pdf"), root=str(tmp_path))
    assert geometrie.erkenne_form(tmp_path / "fremd.pdf") is None
    ergebnis = rufe("verify", tmp_path / "fremd.pdf")
    assert ergebnis.returncode == normbrief.EXIT_EINGABE
    assert "--form" in ergebnis.stderr


# ── Zweizeiliger Betreff ────────────────────────────────────────────────────

def test_zweizeiliger_betreff_wird_akzeptiert(gerendert):
    """Die Norm lässt zwei Zeilen zu; gemessen wird ab der letzten."""
    pdf, form = gerendert["brief-betreff-lang"]
    bericht = geometrie.pruefe(pdf, form)
    zeilen = [p for p in bericht.pruefungen if p.name == "Betreff, Zeilenzahl"]
    assert zeilen and zeilen[0].ist == "2"
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)


# ── Herkunft und Standards ──────────────────────────────────────────────────

def test_herkunft_steht_im_pdf(gerendert):
    from pypdf import PdfReader

    pdf, _ = gerendert["brief-form-b"]
    metadaten = PdfReader(str(pdf)).metadata
    assert metadaten.get("/normbrief_Version") == normbrief.VERSION
    assert metadaten.get("/normbrief_Profil") == "example"
    assert str(metadaten.get("/normbrief_Quelle", "")).startswith("sha256:")


def test_pdfa_ueberlebt_den_herkunftsvermerk(gerendert):
    """pypdf schreibt das Dokument neu — die PDF/A-Kennung darf dabei nicht
    verloren gehen, sonst wäre die Archivfestigkeit still weg."""
    for name, (pdf, _) in gerendert.items():
        ist_pdfa, _ = geometrie.pdfa_geprueft(pdf)
        assert ist_pdfa, f"{name}: PDF/A-Kennzeichnung fehlt"


def test_pdfua_setzt_die_kennung(tmp_path):
    pdf, _ = normbrief.rendere(
        REPO / "examples" / "brief-form-b.md", tmp_path / "ua.pdf",
        profil_verzeichnis=PROFILE, pdfua=True,
    )
    xmp = geometrie.xmp_lesen(pdf)
    assert "pdfuaid:part>1" in xmp.replace(" ", "") or 'pdfuaid:part="1"' in xmp
    ist_pdfa, _ = geometrie.pdfa_geprueft(pdf)
    assert ist_pdfa, "PDF/UA darf PDF/A nicht verdrängen"
