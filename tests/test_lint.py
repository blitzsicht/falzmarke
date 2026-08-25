"""lint: die Prüfung vor dem Render.

Je Regel ein Fall, der sie auslöst, und einer, der sie nicht auslösen darf.
Ohne den zweiten wüsste man nur, dass die Regel feuert — nicht, ob sie trifft.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import pytest

from falzmarke import cli as falzmarke
from conftest import BEISPIELE, REPO, SKILL

CLI = SKILL / "scripts" / "falzmarke.py"
PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

KOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""


def schreibe(tmp_path, kopf: str = KOPF, body: str = "Text des Briefes.\n"):
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{kopf}---\n{body}", encoding="utf-8")
    return pfad


def linte(tmp_path, kopf: str = KOPF, body: str = "Text des Briefes.\n"):
    return falzmarke.linte(schreibe(tmp_path, kopf, body), profil_verzeichnis=PROFILE)


def regeln(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde if b.schwere == "Fehler"}


def warnungen(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde if b.schwere == "Warnung"}


def test_gueltiger_brief_ist_sauber(tmp_path):
    bericht = linte(tmp_path)
    assert bericht.ok, bericht.als_text("brief.md")
    assert bericht.anzahl_warnungen == 0


@pytest.mark.parametrize("name", [p.stem for p in BEISPIELE])
def test_beispiele_sind_sauber(name):
    bericht = falzmarke.linte(REPO / "examples" / f"{name}.md", profil_verzeichnis=PROFILE)
    assert bericht.ok, bericht.als_text(name)


# ── Datum ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("wert", ["morgen", "25.08.2026", "20260825", "nächsten Montag", ""])
def test_datum_muss_iso_sein(tmp_path, wert):
    bericht = linte(tmp_path, KOPF.replace("datum: 2026-08-25", f"datum: {wert or "''"}"))
    assert "datum" in regeln(bericht)


@pytest.mark.parametrize("wert", ["2026-08-25", "2028-02-29", "2026-01-01"])
def test_gueltige_daten_gehen_durch(tmp_path, wert):
    bericht = linte(tmp_path, KOPF.replace("datum: 2026-08-25", f"datum: {wert}"))
    assert "datum" not in regeln(bericht)


def test_unmoegliches_datum_ergibt_keinen_traceback(tmp_path):
    """`2026-13-45` scheiterte bis v0.1.2 in PyYAML mit einem Traceback."""
    brief = schreibe(tmp_path, KOPF.replace("datum: 2026-08-25", "datum: 2026-13-45"))
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "lint", str(brief)], capture_output=True, text=True, encoding="utf-8"
    )
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    assert "Traceback" not in ergebnis.stderr
    assert "2026-08-25" in ergebnis.stderr


# ── Betreff, Anrede, Gruß ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "betreff,regel",
    [
        ('"Betreff: Angebot"', "betreff"),
        ("Angebot Nr. 4711.", "betreff"),
        ("A" * 200, "betreff"),
    ],
)
def test_betreffregeln(tmp_path, betreff, regel):
    bericht = linte(tmp_path, KOPF.replace("betreff: Ein Betreff", f"betreff: {betreff}"))
    assert regel in regeln(bericht)


def test_zweizeiliger_betreff_ist_erlaubt(tmp_path):
    """Ein Angebot mit Vorgangsnummer und Gegenstand ist der Normalfall."""
    lang = "Angebot Nr. 2026-0815 über die Neugestaltung Ihrer Website samt Umzug"
    bericht = linte(tmp_path, KOPF.replace("betreff: Ein Betreff", f"betreff: {lang}"))
    assert bericht.ok, bericht.als_text("brief.md")


def test_anrede_ohne_komma(tmp_path):
    bericht = linte(tmp_path, KOPF.replace("Herren,", "Herren"))
    assert "anrede" in regeln(bericht)


def test_gruss_mit_komma(tmp_path):
    """Warnung statt Fehler: Die Regel steht nur in einer Quelle.

    Die Herabstufung kommt aus `regeln/din5008.yaml` und gilt, bis der
    Abgleich mit dem Originaltext der Norm sie bestätigt.
    """
    bericht = linte(tmp_path, KOPF + "gruss: Mit freundlichen Grüßen,\n")
    assert "gruss" in warnungen(bericht)
    assert "gruss" not in regeln(bericht)


# ── Anschrift und Vermerke ──────────────────────────────────────────────────

def test_sieben_anschriftzeilen(tmp_path):
    zeilen = ", ".join(f"Zeile {i}" for i in range(7))
    bericht = linte(tmp_path, KOPF.replace(
        "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]", f"empfaenger: [{zeilen}]"))
    # Warnung statt Fehler — die Sechs-Zeilen-Grenze steht nur in einer Quelle.
    assert "empfaenger" in warnungen(bericht)


def test_vier_vermerke(tmp_path):
    bericht = linte(tmp_path, KOPF + "vermerke: [Eins, Zwei, Drei, Vier]\n")
    assert "vermerke" in regeln(bericht)


def test_auslandsanschrift_ohne_grossschreibung_warnt(tmp_path):
    bericht = linte(tmp_path, KOPF.replace(
        "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]",
        "empfaenger: [Muster SA, 12 rue de la Paix, 75002 Paris, FRANKREICH]"))
    assert bericht.ok
    assert any(b.regel == "empfaenger" for b in bericht.befunde)


# ── Informationsblock ───────────────────────────────────────────────────────

def test_zu_langer_infoblockwert(tmp_path):
    bericht = linte(tmp_path, KOPF + "infoblock:\n  email: " + "a" * 40 + "@example.de\n")
    assert any(r.startswith("infoblock.") for r in regeln(bericht))


def test_ungueltige_email(tmp_path):
    bericht = linte(tmp_path, KOPF + "infoblock:\n  email: keine-adresse\n")
    assert "infoblock.email" in regeln(bericht)


def test_telefon_ohne_din_schreibweise_warnt(tmp_path):
    bericht = linte(tmp_path, KOPF + 'infoblock:\n  telefon: "(0941) 620/9800"\n')
    assert bericht.ok, "die Schreibweise ist eine Empfehlung, kein Fehler"
    assert bericht.anzahl_warnungen >= 1


# ── Body ────────────────────────────────────────────────────────────────────

def test_markdownfehler_landet_im_bericht(tmp_path):
    bericht = linte(tmp_path, body="Text\n\n## Verbotene Überschrift\n")
    assert "markdown" in regeln(bericht)
    # Frontmatter bis Zeile 7, dann 'Text', Leerzeile, Überschrift in Zeile 10.
    assert any(b.zeile == 10 for b in bericht.befunde)


def test_zwei_leerzeichen_warnen(tmp_path):
    bericht = linte(tmp_path, body="Zeile eins  \nZeile zwei\n")
    assert bericht.ok
    assert any(b.regel == "umbruch" for b in bericht.befunde)


def test_kaputte_url_ist_fehler(tmp_path):
    bericht = linte(tmp_path, body="Siehe https:// dort weiter.\n")
    assert "url" in regeln(bericht)


def test_gueltige_url_geht_durch(tmp_path):
    bericht = linte(tmp_path, body="Siehe https://example.de/pfad dort.\n")
    assert bericht.ok


# ── Verhalten der Befehle ───────────────────────────────────────────────────

def test_render_bricht_vor_dem_setzen_ab(tmp_path):
    """Ein Eingabefehler darf keinen Render kosten — und kein PDF hinterlassen."""
    brief = schreibe(tmp_path, KOPF.replace("datum: 2026-08-25", "datum: morgen"))
    ziel = tmp_path / "aus.pdf"
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "render", str(brief), "-o", str(ziel)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    assert not ziel.exists()
    assert "Maße" not in ergebnis.stderr, "das ist kein Geometriebefund"


def test_json_ausgabe(tmp_path):
    brief = schreibe(tmp_path, KOPF.replace("datum: 2026-08-25", "datum: morgen"))
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "lint", str(brief), "--json"], capture_output=True, text=True, encoding="utf-8"
    )
    bericht = json.loads(ergebnis.stdout)
    assert bericht["ok"] is False and bericht["fehler"] == 1
    assert bericht["befunde"][0]["regel"] == "datum"
    assert bericht["befunde"][0]["korrektur"]


def test_lint_ist_schnell():
    """Ohne Typst — die Grenze ist großzügig, sie soll nur Ausreißer fangen."""
    quelle = REPO / "examples" / "brief-mehrseitig.md"
    start = time.perf_counter()
    falzmarke.linte(quelle, profil_verzeichnis=PROFILE)
    dauer = time.perf_counter() - start
    assert dauer < 0.5, f"lint brauchte {dauer*1000:.0f} ms"


# ── Unbekannte Frontmatter-Felder ───────────────────────────────────────────
#
# Bis v0.4.0 gab es dagegen keine Prüfung: Jeder Schlüssel, den `baue_daten`
# nicht abfragte, wurde still verworfen. Wer `signatur:` in den Brief schrieb —
# naheliegend, es steht im Profil — bekam keinen Fehler, sondern keine Wirkung.
# Das ist genau der stille Ausgang, den das Werkzeug sonst überall vermeidet.

def test_unbekanntes_feld_bricht_ab(tmp_path):
    bericht = linte(tmp_path, KOPF + "quatschfeld: irgendwas\n")
    assert "frontmatter" in regeln(bericht), bericht.als_text("brief.md")


def test_tippfehler_bekommt_den_richtigen_vorschlag(tmp_path):
    """`signature:` ist der wahrscheinlichste Fehlgriff — englisch statt deutsch."""
    bericht = linte(tmp_path, KOPF + "signature: assets/unterschrift.svg\n")
    text = bericht.als_text("brief.md")
    assert "frontmatter" in regeln(bericht), text
    assert "signatur" in text, text


@pytest.mark.parametrize("feld,wert", [
    ("form", "B"),
    ("norm", "din5008"),
    ("vermerke", "[Einschreiben]"),
    ("betreff_kurz", "Kurz"),
    ("gruss", "Mit freundlichen Grüßen"),
    ("unterzeichner", "i. A. Erika Muster"),
    ("signatur", "keine"),
    ("anlagen", "[Angebot]"),
    ("verteiler", "[Herrn Max Muster]"),
])
def test_dokumentierte_felder_bleiben_erlaubt(tmp_path, feld, wert):
    """Gegenprobe: Eine Sperre, die auch Erlaubtes abweist, wäre unbrauchbar."""
    bericht = linte(tmp_path, KOPF + f"{feld}: {wert}\n")
    assert "frontmatter" not in regeln(bericht), bericht.als_text("brief.md")


def test_unbekannter_infoblock_schluessel_bricht_ab(tmp_path):
    bericht = linte(tmp_path, KOPF + "infoblock: {handy: 0170 1234567}\n")
    assert "infoblock" in regeln(bericht), bericht.als_text("brief.md")


def test_die_feldliste_deckt_sich_mit_dem_datenvertrag(tmp_path):
    """Die Liste im Code und die Tabelle in der Doku sind zwei Stellen.

    Ohne diesen Abgleich altert eine von beiden still — und zwar die, die
    niemand ausführt.
    """
    import re

    from falzmarke import lint as lint_modul

    vertrag = (REPO / "skill" / "references" / "frontmatter.md").read_text(encoding="utf-8")
    block = vertrag.split("```yaml", 1)[1].split("```", 1)[0]
    dokumentiert = set(re.findall(r"^([a-z_]+):", block, flags=re.M))

    fehlend = dokumentiert - lint_modul.FRONTMATTER_FELDER
    assert not fehlend, f"In der Doku, aber vom Linter abgewiesen: {sorted(fehlend)}"
