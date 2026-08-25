"""Die vendorte Fremddatei muss unverändert bleiben.

letter-pro trägt das Seitenlayout. Eine stille Änderung daran würde alle
Geometrieprüfungen betreffen, ohne dass jemand es beabsichtigt hätte.
Beabsichtigte Änderungen gehören dokumentiert nach vendor/CHANGES.md.
"""

from __future__ import annotations

import hashlib
import re

from conftest import SKILL

VENDOR = SKILL / "typst" / "vendor"
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
