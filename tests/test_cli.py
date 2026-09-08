"""Die Kommandozeile: Exit-Codes, Ausgaben, Verhalten bei Fehlern."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from falzmarke import cli as falzmarke
from conftest import REPO, SKILL

CLI = SKILL / "scripts" / "falzmarke.py"
PROFILE = SKILL / "falzmarke" / "typst" / "profiles"
BEISPIEL = REPO / "examples" / "brief-form-b.md"


def rufe(*argumente) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *map(str, argumente)],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_render_gibt_null_zurueck(tmp_path):
    ergebnis = rufe("render", BEISPIEL, "-o", tmp_path / "a.pdf")
    assert ergebnis.returncode == falzmarke.EXIT_OK, ergebnis.stderr
    assert (tmp_path / "a.pdf").is_file()
    assert "OK  PDF geschrieben" in ergebnis.stdout


def test_render_meldet_eingabefehler_mit_eins(tmp_path):
    brief = tmp_path / "kaputt.md"
    brief.write_text("---\nprofil: example\n---\nText\n", encoding="utf-8")
    ergebnis = rufe("render", brief, "-o", tmp_path / "a.pdf")
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
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
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    # Zeile 9: sechs Zeilen Frontmatter, dann "Text", eine Leerzeile, die Überschrift.
    assert "kaputt.md:9" in ergebnis.stderr, ergebnis.stderr


def test_check_meldet_zwei_bei_falscher_geometrie(tmp_path, gerendert):
    """Ein Form-B-PDF gegen die Form-A-Maße geprüft muss durchfallen —
    sonst prüft `check` die Form gar nicht."""
    pdf, _ = gerendert["brief-form-b"]
    ergebnis = rufe("check", pdf, "--form", "A")
    assert ergebnis.returncode == falzmarke.EXIT_GEOMETRIE
    assert "FEHL" in ergebnis.stdout


def test_check_ist_gruen_fuer_die_richtige_form(gerendert):
    pdf, form = gerendert["brief-form-b"]
    ergebnis = rufe("check", pdf, "--form", form)
    assert ergebnis.returncode == falzmarke.EXIT_OK
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
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE


def test_profiles_listet_das_beispiel():
    ergebnis = rufe("profiles")
    assert ergebnis.returncode == falzmarke.EXIT_OK
    assert "example" in ergebnis.stdout


def test_init_schreibt_vorlage_und_ueberschreibt_nicht(tmp_path):
    ziel = tmp_path / "neu.md"
    ergebnis = rufe("init", ziel, "--profil", "example", "--betreff", "Ein Betreff",
                    "--empfaenger", "Muster GmbH|Musterstraße 1|12345 Musterstadt")
    assert ergebnis.returncode == falzmarke.EXIT_OK
    inhalt = ziel.read_text(encoding="utf-8")
    assert "profil: example" in inhalt and "Musterstraße 1" in inhalt

    nochmal = rufe("init", ziel, "--profil", "example")
    assert nochmal.returncode == falzmarke.EXIT_EINGABE
    assert "gibt es schon" in nochmal.stderr


def test_init_ergibt_einen_rendbaren_brief(tmp_path):
    ziel = tmp_path / "neu.md"
    rufe("init", ziel, "--profil", "example", "--betreff", "Ein Betreff")
    ergebnis = rufe("render", ziel, "-o", tmp_path / "neu.pdf")
    assert ergebnis.returncode == falzmarke.EXIT_OK, ergebnis.stdout + ergebnis.stderr


def test_preview_erzeugt_png(tmp_path):
    ergebnis = rufe("preview", BEISPIEL, "-o", tmp_path / "v.png")
    assert ergebnis.returncode == falzmarke.EXIT_OK
    assert (tmp_path / "v.png").is_file()


def test_mehrseitige_vorschau_schreibt_je_seite_eine_datei(tmp_path):
    """Typst verlangt für mehrseitige PNGs einen Platzhalter im Dateinamen."""
    quelle = REPO / "examples" / "brief-mehrseitig.md"
    ergebnis = rufe("preview", quelle, "-o", tmp_path / "m.png")
    assert ergebnis.returncode == falzmarke.EXIT_OK, ergebnis.stderr
    assert sorted(p.name for p in tmp_path.glob("m*.png")) == ["m-1.png", "m-2.png"]


def test_render_ohne_pdfa(tmp_path):
    from falzmarke import geometrie

    ergebnis = rufe("render", BEISPIEL, "-o", tmp_path / "a.pdf", "--no-pdfa")
    assert ergebnis.returncode == falzmarke.EXIT_OK
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
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    assert "Anführungszeichen" in ergebnis.stderr


def test_jeder_befehl_steht_im_skill():
    """Was `--help` kennt, muss SKILL.md nennen.

    Die Sollmenge kommt aus dem Parser, nicht aus einer zweiten Aufzaehlung im
    Test — die altert genauso still wie die im Dokument. Genau das ist passiert:
    `serie`, `einlesen`, `preview`, `mcp` und `init` standen bis v0.9.5 nur in
    `docs/cli.md`, und `docs/` liegt nicht im Skill-Paket
    (`scripts/skill_packen.sh` kopiert `skill/`). Wer den Skill hochlaedt, sah
    fuenf Befehle nirgends (#261).

    Gesucht wird der Befehl hinter `falzmarke ` bzw. `falzmarke.py ` oder in
    Backticks, und nie mit `-` oder einem Wortzeichen dahinter: Sonst deckte
    `init-profil` den Befehl `init` mit ab.
    """
    hilfe = rufe("--help")
    assert hilfe.returncode == 0, hilfe.stderr

    treffer = re.search(r"\{([^}]*)\}", hilfe.stdout)
    assert treffer, "aus der Hilfe liess sich keine Befehlsliste lesen"
    befehle = [b for b in "".join(treffer.group(1).split()).split(",") if b]
    # Ohne diese Schranke waere eine leere Menge gruen: Aendert argparse seine
    # Ausgabe, faellt der Test auf und meldet nicht stillschweigend Erfolg.
    assert len(befehle) >= 10, f"nur {len(befehle)} Befehle gelesen: {befehle}"

    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    fehlend = [b for b in befehle
               if not re.search(rf"(?:falzmarke(?:\.py)? |`){re.escape(b)}(?![\w-])", text)]
    assert not fehlend, "in SKILL.md nicht genannt: " + ", ".join(fehlend)


def test_die_beschreibung_nennt_serie_und_einlesen():
    """Zwei der fuenf Befehle haben einen eigenen Anlass.

    „Serienbrief an zweihundert Empfaenger" und „lies diesen alten Brief ein"
    sind Aufgaben, bei denen niemand von sich aus an einen DIN-Skill denkt. Sie
    erreichen ihn nur ueber die Beschreibung: Der Rumpf wird erst NACH dem Laden
    gelesen. Fuer `preview`, `init` und `mcp` gilt das nicht — sie haben keinen
    eigenen Anlass und stehen deshalb nur im Rumpf (#261).
    """
    kopf = (SKILL / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
    assert "Serienbrief" in kopf, "die Beschreibung nennt den Serienbrief nicht"
    assert "einlesen" in kopf, "die Beschreibung nennt das Zuruecklesen nicht"
