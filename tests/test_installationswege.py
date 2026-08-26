"""Die README darf keinen Installationsbefehl nennen, den es nicht gibt.

Anlass, gemessen am 25.08.2026: README und CHANGELOG versprachen
`uvx normbrief` und `pipx install normbrief`. Beides schlug fehl — das Paket
lag nie auf PyPI. Aufgefallen ist es niemandem, weil der Frischklon-Job der CI
ein lokal gebautes Wheel testet (`/tmp/frisch/bin/...`) und deshalb auch dann
grün bleibt, wenn es auf PyPI nichts gibt. Ein Prüfmittel, das die eigene
Behauptung nicht messen kann.

Dieser Test braucht kein Netz: Er hält die README gegen eine Konstante, die
sagt, ob veröffentlicht wurde. Wer auf PyPI veröffentlicht, setzt sie auf True
und darf ab dann die kurzen Befehle schreiben.
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO

# Seit v0.7.3 liegt das Paket auf PyPI (26.08.2026, Lauf 32972861001).
# Gemessen: pypi.org/pypi/falzmarke/json -> HTTP 200, Version 0.7.3.
AUF_PYPI = True

PAKET = "falzmarke"
README = REPO / "README.md"

# `uvx falzmarke …` oder `pipx install falzmarke` ohne Herkunftsangabe.
# Mit `--from git+…` bzw. `pipx install git+…` ist der Befehl in Ordnung.
# Kein `\s` als linke Grenze: In der README steht so ein Befehl fast immer in
# Backticks (`pipx install falzmarke`), und ein Backtick ist kein Leerzeichen.
# Genau dieser Fall wäre am 25.08.2026 durchgerutscht.
NACKT = re.compile(
    rf"(?<![\w./-])(?:uvx\s+{PAKET}\b|pipx\s+install\s+{PAKET}\b|pip\s+install\s+{PAKET}\b)"
)


def _nackte_befehle(text: str) -> list[str]:
    return [z.strip() for z in text.splitlines() if NACKT.search(z)]


def test_readme_verspricht_keinen_pypi_befehl_ohne_pypi():
    gefunden = _nackte_befehle(README.read_text(encoding="utf-8"))
    if AUF_PYPI:
        pytest.skip("Paket ist veröffentlicht — die kurzen Befehle sind zulässig")
    assert not gefunden, (
        "Die README nennt einen Installationsbefehl, der ein PyPI-Paket "
        f"voraussetzt, das es nicht gibt:\n  " + "\n  ".join(gefunden) +
        "\n\nEntweder `--from git+…` bzw. `pipx install git+…` schreiben, oder "
        "nach der Veröffentlichung AUF_PYPI = True setzen."
    )


def test_nach_der_veroeffentlichung_steht_der_kurze_befehl_auch_da():
    """Die Gegenrichtung. Ohne sie wird der Test oben mit AUF_PYPI = True nur
    uebersprungen — und ein Skip prueft nichts.

    Die Konstante behauptet, das Paket liege auf PyPI. Wenn das stimmt, muss die
    README den kurzen Befehl auch nennen; sonst ist die Umstellung
    folgenlos geblieben und niemand merkt es. Genau so ist der Fall
    `AUF_PYPI` ueberhaupt erst entstanden: eine Nacharbeit, die nichts erzwingt.
    """
    if not AUF_PYPI:
        pytest.skip("noch nicht veroeffentlicht — dafuer ist der Test oben zustaendig")
    assert _nackte_befehle(README.read_text(encoding="utf-8")), (
        "AUF_PYPI ist True, aber die README nennt keinen kurzen Installationsbefehl.\n"
        "Entweder `pipx install falzmarke` bzw. `uvx falzmarke` eintragen — oder "
        "die Konstante steht falsch."
    )


def test_die_pruefung_wuerde_einen_falschen_befehl_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass gerade nichts dasteht."""
    assert _nackte_befehle("Dauerhaft: `pipx install falzmarke`, danach loslegen.")
    assert _nackte_befehle("    uvx falzmarke render brief.md")
    # Und die erlaubten Formen dürfen nicht anschlagen:
    assert not _nackte_befehle("uvx --from git+https://example.invalid/x falzmarke render b.md")
    assert not _nackte_befehle("pipx install git+https://example.invalid/x")
