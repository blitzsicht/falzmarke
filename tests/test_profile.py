"""Profile: Quellen, eigener Briefkopf, Skill-Zip.

Der rote Faden: Ein Profil muss dort ankommen, wo gearbeitet wird — auch auf
claude.ai, wo kein Verzeichnis den nächsten Chat überlebt.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile

import pytest
import yaml

from falzmarke import cli as falzmarke
from conftest import REPO, SKILL

CLI = SKILL / "scripts" / "falzmarke.py"
PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

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


# ── infoblock_defaults: die Meldung muss die Quelle nennen (#244) ───────────

def _profil_mit_default(tmp_path, wert: str) -> Path:
    ordner = tmp_path / "profile"
    ordner.mkdir(exist_ok=True)
    daten = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    daten.setdefault("infoblock_defaults", {})["ansprechpartner"] = wert
    (ordner / "meins.yaml").write_text(yaml.safe_dump(daten, allow_unicode=True),
                                       encoding="utf-8")
    return ordner


ZU_LANG = "Vorname-Zweitname Nachname"          # 26 Zeichen, Grenze ist 21


def test_ein_zu_langer_wert_im_profil_nennt_das_profil(tmp_path):
    """Der Fall aus #244: Der Wert steht NICHT in der Briefdatei, in der man
    ihn sucht. Drei Fehlversuche kostete das — erst wurde die Fußzeile gekürzt,
    und der gemessene Wert blieb exakt gleich."""
    ordner = _profil_mit_default(tmp_path, ZU_LANG)
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        falzmarke.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=ordner)
    meldung = str(fehler.value)
    assert "infoblock_defaults.ansprechpartner" in meldung, meldung
    assert "im Profil" in meldung, meldung


def test_derselbe_wert_im_brief_nennt_den_brief(tmp_path):
    """Gegenprobe. Ohne sie wäre eine Herkunft, die immer „Profil" sagt, grün —
    und schickte den Leser genau dann in die falsche Datei, wenn der Wert
    ausnahmsweise doch in seinem Brief steht."""
    ordner = _profil_mit_default(tmp_path, "Erika Muster")
    brief = tmp_path / "b.md"
    brief.write_text(
        BRIEF.format(profil="meins").replace(
            "anrede:", f"infoblock:\n  ansprechpartner: {ZU_LANG}\nanrede:"),
        encoding="utf-8")
    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        falzmarke.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=ordner)
    meldung = str(fehler.value)
    assert "infoblock.ansprechpartner" in meldung, meldung
    assert "im Brief" in meldung, meldung


def test_ein_kurzer_wert_im_profil_geht_durch(tmp_path):
    """Sonst wüsste man nur, dass es abbricht — nicht, dass es das Richtige tut."""
    ordner = _profil_mit_default(tmp_path, "Erika Muster")
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    pdf, _ = falzmarke.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=ordner)
    assert pdf.is_file()


# ── Die Grenze selbst: am gerenderten PDF nachgemessen ──────────────────────

#: Ein realistischer Name mit genau `INFOBLOCK_WERT_MAX` Zeichen — und einer mit
#: einem Zeichen mehr. Zusammen nageln sie die Zahl fest: Der kurze MUSS durch
#: den Satzspiegel passen, der lange MUSS ihn sprengen. Eine Grenze, die nur
#: gegen sich selbst geprüft wird, hält gar nichts (in genau diese Falle lief
#: der erste Anlauf zu #244: `len(wert) > INFOBLOCK_WERT_MAX` blieb bei jedem
#: Wert der Konstanten grün).
GERADE_NOCH = "Christoph Fuchsberger"          # 21 Zeichen
EINS_ZU_VIEL = "Wilhelm Wolfmann-Barth"        # 22 Zeichen


def _rechter_rand_haelt(tmp_path, monkeypatch, wert: str) -> bool:
    """Rendert mit `wert` im Infoblock und misst den rechten Rand am PDF.

    Die Zeichengrenze wird dafür beiseitegestellt — sie ist ja gerade das, was
    hier belegt werden soll. Sonst bräche der Renderer vorher ab und der Test
    prüfte die Konstante gegen sich selbst statt gegen den Satzspiegel.
    """
    from falzmarke import geometrie
    monkeypatch.setattr(falzmarke, "INFOBLOCK_WERT_MAX", 999)
    ordner = _profil_mit_default(tmp_path, "Erika Muster")
    brief = tmp_path / "rand.md"
    brief.write_text(
        BRIEF.format(profil="meins").replace(
            "anrede:", f"infoblock:\n  ansprechpartner: {wert}\nanrede:"),
        encoding="utf-8")
    pdf, form = falzmarke.rendere(brief, tmp_path / "rand.pdf",
                                  profil_verzeichnis=ordner)
    bericht = geometrie.pruefe(pdf, form)
    return all(p.bestanden for p in bericht.pruefungen if "rechter Rand" in p.name)


def test_die_grenze_laesst_durch_was_passt(tmp_path, monkeypatch):
    assert len(GERADE_NOCH) == falzmarke.INFOBLOCK_WERT_MAX, (
        "Die Probe muss genau auf der Grenze liegen, sonst misst sie daneben")
    assert _rechter_rand_haelt(tmp_path, monkeypatch, GERADE_NOCH), (
        f"„{GERADE_NOCH}“ ist {len(GERADE_NOCH)} Zeichen lang und sprengt den "
        "Satzspiegel — die Grenze ist zu hoch")


def test_die_grenze_faengt_was_nicht_passt(tmp_path, monkeypatch):
    """Die Gegenrichtung. Ohne sie wäre eine Grenze von 3 ebenfalls grün."""
    assert len(EINS_ZU_VIEL) == falzmarke.INFOBLOCK_WERT_MAX + 1
    assert not _rechter_rand_haelt(tmp_path, monkeypatch, EINS_ZU_VIEL), (
        f"„{EINS_ZU_VIEL}“ hält den Satzspiegel ein — dann darf die Grenze nicht "
        f"bei {falzmarke.INFOBLOCK_WERT_MAX} liegen, sondern höher")


# ── Quellen ─────────────────────────────────────────────────────────────────

def test_profil_neben_dem_brief(tmp_path):
    shutil.copy(PROFILE / "example.yaml", tmp_path / "hier.yaml")
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="hier"), encoding="utf-8")
    pdf, _ = falzmarke.rendere(brief, tmp_path / "b.pdf")
    assert pdf.is_file()


def test_profil_als_pfad(tmp_path):
    ziel = tmp_path / "unterordner"
    ziel.mkdir()
    shutil.copy(PROFILE / "example.yaml", ziel / "firma.yaml")
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="./unterordner/firma.yaml"), encoding="utf-8")
    pdf, _ = falzmarke.rendere(brief, tmp_path / "b.pdf")
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
    pdf, _ = falzmarke.rendere(brief, tmp_path / "b.pdf")
    assert pdf.is_file()


def test_unbekanntes_profil_nennt_die_suchorte(tmp_path):
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="gibtsnicht"), encoding="utf-8")
    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        falzmarke.rendere(brief, tmp_path / "b.pdf")
    assert "gibtsnicht" in str(fehler.value) and "Gesucht in" in str(fehler.value)


# ── Eigener Briefkopf ───────────────────────────────────────────────────────

def test_eigener_briefkopf_wird_gesetzt(tmp_path, eigenes_profil):
    """Der Hook war seit v0.1.2 in der Doku versprochen und nicht gebaut."""
    import pdfplumber

    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    pdf, _ = falzmarke.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=eigenes_profil)

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
    from falzmarke import geometrie

    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    pdf, form = falzmarke.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=eigenes_profil)
    bericht = geometrie.pruefe(pdf, form)
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)


def test_briefkopf_typ_ausserhalb_des_profilordners(tmp_path, eigenes_profil):
    daten = yaml.safe_load((eigenes_profil / "meins.yaml").read_text(encoding="utf-8"))
    daten["briefkopf_typ"] = "../woanders.typ"
    (eigenes_profil / "meins.yaml").write_text(
        yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    with pytest.raises(falzmarke.Eingabefehler):
        falzmarke.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=eigenes_profil)


# ── pack ────────────────────────────────────────────────────────────────────

def test_pack_backt_profil_und_beilagen_ein(tmp_path, eigenes_profil):
    ziel = tmp_path / "meins.skill"
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "pack", "--profil", "meins",
         "--profiles", str(eigenes_profil), "-o", str(ziel)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == falzmarke.EXIT_OK, ergebnis.stderr
    assert "Absenderdaten" in ergebnis.stdout, "die Warnung muss auffallen"

    with zipfile.ZipFile(ziel) as archiv:
        namen = archiv.namelist()
    assert "falzmarke/SKILL.md" in namen, "claude.ai erwartet SKILL.md an der Wurzel"
    # Im Zip liegt der Skill-Ordner, darin das gleichnamige Paket.
    assert "falzmarke/falzmarke/typst/profiles/meins.yaml" in namen
    assert "falzmarke/falzmarke/typst/profiles/meinkopf.typ" in namen, "die Beilage fehlt"


def test_aus_dem_gepackten_skill_laesst_sich_rendern(tmp_path, eigenes_profil):
    """Der eigentliche Beweis: So kommt es auf claude.ai an."""
    ziel = tmp_path / "meins.skill"
    subprocess.run(
        [sys.executable, str(CLI), "pack", "--profil", "meins",
         "--profiles", str(eigenes_profil), "-o", str(ziel)],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    entpackt = tmp_path / "entpackt"
    with zipfile.ZipFile(ziel) as archiv:
        archiv.extractall(entpackt)

    brief = entpackt / "b.md"
    brief.write_text(BRIEF.format(profil="meins"), encoding="utf-8")
    ergebnis = subprocess.run(
        [sys.executable, str(entpackt / "falzmarke" / "scripts" / "falzmarke.py"),
         "render", str(brief), "-o", str(entpackt / "b.pdf")],
        capture_output=True, text=True, encoding="utf-8",
        # Die vorhandene Umgebung übernehmen und nur die Profilorte umbiegen:
        # ein hartkodierter PATH wäre unter Windows falsch.
        env={**os.environ,
             "XDG_CONFIG_HOME": str(tmp_path / "leer"),
             "HOME": str(tmp_path),
             "USERPROFILE": str(tmp_path),
             "FALZMARKE_PROFILES": ""},
    )
    assert ergebnis.returncode == falzmarke.EXIT_OK, ergebnis.stdout + ergebnis.stderr
    assert (entpackt / "b.pdf").is_file()


def test_pack_meldet_unbekanntes_profil(tmp_path):
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "pack", "--profil", "gibtsnicht", "-o", str(tmp_path / "x.skill")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    assert "gibtsnicht" in ergebnis.stderr
