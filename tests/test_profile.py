"""Profile: Quellen, eigener Briefkopf, Skill-Zip.

Der rote Faden: Ein Profil muss dort ankommen, wo gearbeitet wird — auch auf
claude.ai, wo kein Verzeichnis den nächsten Chat überlebt.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile

import pytest
import yaml

import normbrief
from conftest import REPO, SKILL

CLI = SKILL / "scripts" / "normbrief.py"
PROFILE = SKILL / "typst" / "profiles"

BRIEF = """---
profil: {profil}
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Probe
anrede: Sehr geehrte Damen und Herren,
---
Text des Briefes.
"""


@pytest.fixture
def eigenes_profil(tmp_path):
    """Ein Profil mit eigenem Briefkopf, außerhalb der Installation."""
    ordner = tmp_path / "profile"
    ordner.mkdir()
    daten = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    daten["briefkopf_typ"] = "meinkopf.typ"
    (ordner / "meins.yaml").write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    shutil.copy(PROFILE / "example-kopf.typ", ordner / "meinkopf.typ")
    return ordner


# ── Quellen ─────────────────────────────────────────────────────────────────

def test_profil_neben_dem_brief(tmp_path):
    shutil.copy(PROFILE / "example.yaml", tmp_path / "hier.yaml")
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="hier"), encoding="utf-8")
    pdf, _ = normbrief.rendere(brief, tmp_path / "b.pdf")
    assert pdf.is_file()


def test_profil_als_pfad(tmp_path):
    ziel = tmp_path / "unterordner"
    ziel.mkdir()
    shutil.copy(PROFILE / "example.yaml", ziel / "firma.yaml")
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="./unterordner/firma.yaml"), encoding="utf-8")
    pdf, _ = normbrief.rendere(brief, tmp_path / "b.pdf")
    assert pdf.is_file()


def test_profil_im_frontmatter_eingebettet(tmp_path):
    """Für claude.ai: ein Brief, der alles Nötige selbst mitbringt."""
    daten = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    daten.pop("briefkopf", None)          # ohne Logo, damit nichts nachzuladen ist
    kopf = yaml.safe_dump({"profil": daten}, allow_unicode=True, sort_keys=False)
    brief = tmp_path / "b.md"
    brief.write_text(
        "---\n" + kopf
        + "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]\n"
        "datum: 2026-08-25\nbetreff: Probe\nanrede: Sehr geehrte Damen und Herren,\n"
        "---\nText des Briefes.\n",
        encoding="utf-8",
    )
    pdf, _ = normbrief.rendere(brief, tmp_path / "b.pdf")
    assert pdf.is_file()


def test_unbekanntes_profil_nennt_die_suchorte(tmp_path):
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="gibtsnicht"), encoding="utf-8")
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        normbrief.rendere(brief, tmp_path / "b.pdf")
    assert "gibtsnicht" in str(fehler.value) and "Gesucht in" in str(fehler.value)


# ── Eigener Briefkopf ───────────────────────────────────────────────────────

def test_eigener_briefkopf_wird_gesetzt(tmp_path, eigenes_profil):
    """Der Hook war seit v0.1.2 in der Doku versprochen und nicht gebaut."""
    import pdfplumber

    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    pdf, _ = normbrief.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=eigenes_profil)

    with pdfplumber.open(str(pdf)) as dokument:
        seite = dokument.pages[0]
        gross = [w for w in seite.extract_words(extra_attrs=["size"])
                 if w["size"] > 18 and w["top"] / 72 * 25.4 < 45]
        linien = [l for l in seite.lines if l["top"] / 72 * 25.4 < 45]
    assert gross, "der eigene Briefkopf setzt den Namen in 22 pt"
    assert linien, "und zieht eine Linie darunter"


def test_eigener_briefkopf_verschiebt_das_anschriftfeld_nicht(tmp_path, eigenes_profil):
    """letter-pro erzwingt die Kopfhöhe — ein eigener Kopf darf die Zonen nicht
    verrücken. Sonst wäre der Hook ein Weg, die Norm zu verlassen."""
    import geometrie

    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    pdf, form = normbrief.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=eigenes_profil)
    bericht = geometrie.pruefe(pdf, form)
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)


def test_briefkopf_typ_ausserhalb_des_profilordners(tmp_path, eigenes_profil):
    daten = yaml.safe_load((eigenes_profil / "meins.yaml").read_text(encoding="utf-8"))
    daten["briefkopf_typ"] = "../woanders.typ"
    (eigenes_profil / "meins.yaml").write_text(
        yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    with pytest.raises(normbrief.Eingabefehler):
        normbrief.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=eigenes_profil)


# ── pack ────────────────────────────────────────────────────────────────────

def test_pack_backt_profil_und_beilagen_ein(tmp_path, eigenes_profil):
    ziel = tmp_path / "meins.skill"
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "pack", "--profil", "meins",
         "--profiles", str(eigenes_profil), "-o", str(ziel)],
        capture_output=True, text=True,
    )
    assert ergebnis.returncode == normbrief.EXIT_OK, ergebnis.stderr
    assert "Absenderdaten" in ergebnis.stdout, "die Warnung muss auffallen"

    with zipfile.ZipFile(ziel) as archiv:
        namen = archiv.namelist()
    assert "normbrief/SKILL.md" in namen, "claude.ai erwartet SKILL.md an der Wurzel"
    assert "normbrief/typst/profiles/meins.yaml" in namen
    assert "normbrief/typst/profiles/meinkopf.typ" in namen, "die Beilage fehlt"


def test_aus_dem_gepackten_skill_laesst_sich_rendern(tmp_path, eigenes_profil):
    """Der eigentliche Beweis: So kommt es auf claude.ai an."""
    ziel = tmp_path / "meins.skill"
    subprocess.run(
        [sys.executable, str(CLI), "pack", "--profil", "meins",
         "--profiles", str(eigenes_profil), "-o", str(ziel)],
        capture_output=True, text=True, check=True,
    )
    entpackt = tmp_path / "entpackt"
    with zipfile.ZipFile(ziel) as archiv:
        archiv.extractall(entpackt)

    brief = entpackt / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    ergebnis = subprocess.run(
        [sys.executable, str(entpackt / "normbrief" / "scripts" / "normbrief.py"),
         "render", str(brief), "-o", str(entpackt / "b.pdf")],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin",
             "XDG_CONFIG_HOME": str(tmp_path / "leer"),
             "HOME": str(tmp_path)},
    )
    assert ergebnis.returncode == normbrief.EXIT_OK, ergebnis.stdout + ergebnis.stderr
    assert (entpackt / "b.pdf").is_file()


def test_pack_meldet_unbekanntes_profil(tmp_path):
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "pack", "--profil", "gibtsnicht", "-o", str(tmp_path / "x.skill")],
        capture_output=True, text=True,
    )
    assert ergebnis.returncode == normbrief.EXIT_EINGABE
    assert "gibtsnicht" in ergebnis.stderr
