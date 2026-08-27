"""Die vendorte Fremddatei muss unverändert bleiben.

letter-pro trägt das Seitenlayout. Eine stille Änderung daran würde alle
Geometrieprüfungen betreffen, ohne dass jemand es beabsichtigt hätte.
Beabsichtigte Änderungen gehören dokumentiert nach vendor/CHANGES.md.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from conftest import REPO, SKILL

VENDOR = SKILL / "falzmarke" / "typst" / "vendor"
DATEI = VENDOR / "letter-pro-v3.0.0.typ"
ERWARTET = "0a66de073f0c1e697d23d4bc66b3364ae04026460cccc7af50fba00c4dac3181"


def test_letter_pro_ist_unveraendert():
    ist = hashlib.sha256(DATEI.read_bytes()).hexdigest()
    assert ist == ERWARTET, (
        f"letter-pro wurde verändert.\nSHA256 ist  {ist}\nSHA256 soll {ERWARTET}\n"
        "Beabsichtigte Änderungen gehören nach skill/typst/vendor/CHANGES.md."
    )


def test_sha_in_der_doku_stimmt_mit_der_datei():
    """Damit die notierte Prüfsumme nicht still veraltet."""
    doku = (VENDOR / "README.md").read_text(encoding="utf-8")
    treffer = re.search(r"SHA256: `([0-9a-f]{64})`", doku)
    assert treffer, "In vendor/README.md steht keine SHA256-Zeile"
    assert treffer.group(1) == ERWARTET


def test_lizenz_liegt_bei():
    lizenz = (VENDOR / "LICENSE-letter-pro").read_text(encoding="utf-8")
    assert "MIT License" in lizenz and "Sematre" in lizenz


# ── Die Doku darf kein Werkzeug beschreiben, das es nicht mehr gibt ──────────
#
# Anlass: `docs/normmasse.md` beschrieb die Messung bis zum 27.08.2026 mit
# `get_drawings()` und `get_text("dict")` — beides PyMuPDF. Gemessen wird seit
# v0.4 mit pdfplumber; PyMuPDF ist AGPL-3.0 und aus der Auslieferung entfernt,
# ein eigener CI-Schritt hält den Rückweg zu. Der greift aber nur in `*.py`,
# `*.txt` und `*.toml` — die Doku fiel durch das Raster und behauptete zwei
# Jahre lang ein Werkzeug, das aus Lizenzgründen verbannt ist.
#
# Über PyMuPDF *als Vergangenheit* zu schreiben, bleibt erlaubt und ist sogar
# nötig: Wer nicht weiß, warum es weg ist, holt es zurück.

#: Aufrufe der verbannten Bibliothek. Wer sie in der Doku findet, liest eine
#: Anleitung für etwas, das dieses Projekt nicht benutzen darf.
#:
#: Die beiden letzten Muster stehen zusammengesetzt da, nicht am Stück: Der
#: CI-Schritt "Keine AGPL-Abhängigkeit" greppt `*.py` nach genau diesen
#: Zeichenfolgen und würde sonst auf diese Datei anschlagen — auf den Wächter
#: statt auf den Rückfall. Gemessen am 27.08.2026, Lauf 33075464489.
VERBANNTE_API = ("get_drawings(", "get_text(", "import " + "fitz", "fitz" + ".open")

DOKU = sorted(
    p for p in list((REPO / "docs").rglob("*.md")) + list((REPO / "skill").rglob("*.md"))
    if "vendor" not in p.parts
)


def test_es_gibt_doku_zu_pruefen():
    """Ohne diese Zeile wäre der Test unten bei leerer Menge still grün."""
    assert len(DOKU) >= 5, [p.name for p in DOKU]


@pytest.mark.parametrize("datei", DOKU, ids=lambda p: p.name)
def test_kein_verbannter_aufruf_in_der_doku(datei):
    text = datei.read_text(encoding="utf-8")
    treffer = [ruf for ruf in VERBANNTE_API if ruf in text]
    assert not treffer, (
        f"{datei.relative_to(REPO)} beschreibt die Messung mit PyMuPDF ({treffer}). "
        "Gemessen wird mit pdfplumber — siehe skill/falzmarke/geometrie.py.")


def test_die_pruefung_wuerde_einen_rueckfall_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass gerade nichts dasteht."""
    echt = (REPO / "docs" / "normmasse.md").read_text(encoding="utf-8")
    rueckfall = echt.replace("`page.lines`", '`get_drawings()`', 1)
    assert rueckfall != echt, "die Sabotage greift nicht — der Anker fehlt"
    assert any(ruf in rueckfall for ruf in VERBANNTE_API)


def test_das_messwerkzeug_steht_in_der_doku_und_in_den_abhaengigkeiten():
    """Die Gegenrichtung: Was die Doku als Messwerkzeug nennt, muss es geben."""
    text = (REPO / "docs" / "normmasse.md").read_text(encoding="utf-8")
    bedarf = (REPO / "skill" / "requirements.txt").read_text(encoding="utf-8")
    for werkzeug in ("pdfplumber", "pypdf"):
        assert werkzeug in text, f"{werkzeug} wird in docs/normmasse.md nicht genannt"
        assert werkzeug in bedarf, f"{werkzeug} steht nicht in skill/requirements.txt"
