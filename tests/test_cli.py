"""Die Kommandozeile: Exit-Codes, Ausgaben, Verhalten bei Fehlern."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from normbrief import cli as normbrief
from conftest import REPO, SKILL

CLI = SKILL / "scripts" / "normbrief.py"
PROFILE = SKILL / "normbrief" / "typst" / "profiles"
BEISPIEL = REPO / "examples" / "brief-form-b.md"


def rufe(*argumente) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *map(str, argumente)],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_render_gibt_null_zurueck(tmp_path):
    ergebnis = rufe("render", BEISPIEL, "-o", tmp_path / "a.pdf")
    assert ergebnis.returncode == normbrief.EXIT_OK, ergebnis.stderr
    assert (tmp_path / "a.pdf").is_file()
    assert "OK  PDF geschrieben" in ergebnis.stdout


def test_render_meldet_eingabefehler_mit_eins(tmp_path):
    brief = tmp_path / "kaputt.md"
    brief.write_text("---\nprofil: example\n---\nText\n", encoding="utf-8")
    ergebnis = rufe("render", brief, "-o", tmp_path / "a.pdf")
    assert ergebnis.returncode == normbrief.EXIT_EINGABE
    # lint meldet je fehlendes Feld eine eigene Zeile mit Korrektur.
    assert "empfaenger — Pflichtfeld fehlt" in ergebnis.stderr
    assert "Korrektur:" in ergebnis.stderr


def test_markdownfehler_nennt_zeile(tmp_path):
    brief = tmp_path / "kaputt.md"
    brief.write_text(
        "---\nprofil: example\nempfaenger: [Muster GmbH]\ndatum: 2026-08-25\n"
        "betreff: Test\n---\nText\n\n## Verbotene Überschrift\n",
        encoding="utf-8",
    )
    ergebnis = rufe("render", brief, "-o", tmp_path / "a.pdf")
    assert ergebnis.returncode == normbrief.EXIT_EINGABE
    # Zeile 9: sechs Zeilen Frontmatter, dann "Text", eine Leerzeile, die Überschrift.
    assert "kaputt.md:9" in ergebnis.stderr, ergebnis.stderr


def test_check_meldet_zwei_bei_falscher_geometrie(tmp_path, gerendert):
    """Ein Form-B-PDF gegen die Form-A-Maße geprüft muss durchfallen —
    sonst prüft `check` die Form gar nicht."""
    pdf, _ = gerendert["brief-form-b"]
    ergebnis = rufe("check", pdf, "--form", "A")
    assert ergebnis.returncode == normbrief.EXIT_GEOMETRIE
    assert "FEHL" in ergebnis.stdout


def test_check_ist_gruen_fuer_die_richtige_form(gerendert):
    pdf, form = gerendert["brief-form-b"]
    ergebnis = rufe("check", pdf, "--form", form)
    assert ergebnis.returncode == normbrief.EXIT_OK
    assert "FEHL" not in ergebnis.stdout


def test_check_liefert_json(gerendert):
    pdf, form = gerendert["brief-form-b"]
    ergebnis = rufe("check", pdf, "--form", form, "--json")
    import json

    bericht = json.loads(ergebnis.stdout)
    assert bericht["ok"] is True
    assert len(bericht["pruefungen"]) > 20


def test_check_auf_fehlende_datei(tmp_path):
    ergebnis = rufe("check", tmp_path / "gibtsnicht.pdf", "--form", "B")
    assert ergebnis.returncode == normbrief.EXIT_EINGABE


def test_profiles_listet_das_beispiel():
    ergebnis = rufe("profiles")
    assert ergebnis.returncode == normbrief.EXIT_OK
    assert "example" in ergebnis.stdout


def test_init_schreibt_vorlage_und_ueberschreibt_nicht(tmp_path):
    ziel = tmp_path / "neu.md"
    ergebnis = rufe("init", ziel, "--profil", "example", "--betreff", "Ein Betreff",
                    "--empfaenger", "Muster GmbH|Musterstraße 1|12345 Musterstadt")
    assert ergebnis.returncode == normbrief.EXIT_OK
    inhalt = ziel.read_text(encoding="utf-8")
    assert "profil: example" in inhalt and "Musterstraße 1" in inhalt

    nochmal = rufe("init", ziel, "--profil", "example")
    assert nochmal.returncode == normbrief.EXIT_EINGABE
    assert "gibt es schon" in nochmal.stderr


def test_init_ergibt_einen_rendbaren_brief(tmp_path):
    ziel = tmp_path / "neu.md"
    rufe("init", ziel, "--profil", "example", "--betreff", "Ein Betreff")
    ergebnis = rufe("render", ziel, "-o", tmp_path / "neu.pdf")
    assert ergebnis.returncode == normbrief.EXIT_OK, ergebnis.stdout + ergebnis.stderr


def test_preview_erzeugt_png(tmp_path):
    ergebnis = rufe("preview", BEISPIEL, "-o", tmp_path / "v.png")
    assert ergebnis.returncode == normbrief.EXIT_OK
    assert (tmp_path / "v.png").is_file()


def test_mehrseitige_vorschau_schreibt_je_seite_eine_datei(tmp_path):
    """Typst verlangt für mehrseitige PNGs einen Platzhalter im Dateinamen."""
    quelle = REPO / "examples" / "brief-mehrseitig.md"
    ergebnis = rufe("preview", quelle, "-o", tmp_path / "m.png")
    assert ergebnis.returncode == normbrief.EXIT_OK, ergebnis.stderr
    assert sorted(p.name for p in tmp_path.glob("m*.png")) == ["m-1.png", "m-2.png"]


def test_render_ohne_pdfa(tmp_path):
    from normbrief import geometrie

    ergebnis = rufe("render", BEISPIEL, "-o", tmp_path / "a.pdf", "--no-pdfa")
    assert ergebnis.returncode == normbrief.EXIT_OK
    ist_pdfa, _ = geometrie.pdfa_geprueft(tmp_path / "a.pdf")
    assert not ist_pdfa


def test_profil_mit_doppelpunkt_ohne_anfuehrungszeichen(tmp_path):
    """Die häufigste YAML-Falle darf nicht als Dictionary im PDF landen."""
    import shutil
    import yaml

    verzeichnis = tmp_path / "profile"
    verzeichnis.mkdir()
    shutil.copy(PROFILE / "example.yaml", verzeichnis / "kaputt.yaml")
    daten = yaml.safe_load((verzeichnis / "kaputt.yaml").read_text(encoding="utf-8"))
    daten["fusszeile"][3][2] = {"Geschäftsführerin": "Erika Muster"}
    (verzeichnis / "kaputt.yaml").write_text(
        yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8"
    )
    brief = tmp_path / "b.md"
    brief.write_text(
        "---\nprofil: kaputt\nempfaenger: [Muster GmbH]\ndatum: 2026-08-25\n"
        "betreff: Test\n---\nText\n",
        encoding="utf-8",
    )
    ergebnis = rufe("render", brief, "-o", tmp_path / "b.pdf", "--profiles", verzeichnis)
    assert ergebnis.returncode == normbrief.EXIT_EINGABE
    assert "Anführungszeichen" in ergebnis.stderr
