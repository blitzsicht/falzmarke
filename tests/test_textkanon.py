"""Sätze, die nicht verschwinden dürfen.

Manche Formulierungen sind kein Stil, sondern eine Zusage. Der Satz zur
Quellenlage sagt, dass der Abgleich mit dem Originaltext der DIN 5008:2020-03
aussteht — er ist der Unterschied zwischen einer beschreibenden Nennung und
einer Behauptung, die das Werkzeug nicht decken kann.

Solche Sätze überleben Überarbeitungen nur, wenn etwas sie festhält. Genau das
ist hier der Fall: Wer sie streicht, sieht einen roten Test und muss sich
entscheiden, statt sie beiläufig zu verlieren.
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO

# Kern des Satzes, ohne die verlinkten Teile — die dürfen sich ändern.
QUELLENLAGE = "der Abgleich mit dem Originaltext der DIN 5008:2020-03 steht aus"
WARNSTUFE = "Regeln aus einzelnen Quellen wirken nur als Warnung"

MUSS_ENTHALTEN = {
    "README.md": [QUELLENLAGE, WARNSTUFE],
    "docs/recht.md": [QUELLENLAGE, WARNSTUFE],
}

# Begriffe, die ohne den Satz oben eine Zusage wären, die niemand geprüft hat.
# Kein `\b` am Ende: gesucht ist auch „normgerechte“, „zertifizierter“.
VERBOTEN = re.compile(r"\b(normgerecht|DIN-konform|normkonform|zertifiziert)\w*", re.I)

# Wo diese Begriffe zulässig sind, weil sie etwas anderes verneinen oder
# beschreiben — die Word-Vorlage ist nachweislich *nicht* normgerecht.
AUSNAHMEN = re.compile(r"(nicht|kein[e]?|keine[rms]?)\s+\S*\s*(normgerecht|DIN-konform|normkonform|zertifiziert)"
                       r"|(normgerecht|DIN-konform|normkonform|zertifiziert)\S*\s*(ist|sind)?\s*(nicht|kein)", re.I)


def _fliesstext(pfad) -> str:
    """Markdown bricht Zeilen frei um — für die Suche ist der Umbruch ein
    Leerzeichen. Ohne diese Normalisierung würde der Test bei jeder
    Neuformatierung rot, ohne dass sich etwas geändert hätte."""
    roh = pfad.read_text(encoding="utf-8")
    return re.sub(r"\s*\n>?\s*", " ", roh)


@pytest.mark.parametrize("datei, saetze", MUSS_ENTHALTEN.items(), ids=list(MUSS_ENTHALTEN))
def test_der_satz_zur_quellenlage_steht_da(datei, saetze):
    text = _fliesstext(REPO / datei)
    fehlend = [s for s in saetze if s not in text]
    assert not fehlend, (
        f"{datei} nennt nicht mehr: {fehlend}\n"
        "Der Satz ist eine Zusage, keine Formulierung. Wenn der Normabgleich "
        "erledigt ist, darf er weg — dann aber auch aus diesem Test.")


@pytest.mark.parametrize("datei", ["README.md", "docs/recht.md", "skill/SKILL.md"])
def test_keine_ungedeckte_konformitaetsbehauptung(datei):
    """„normgerecht“ ohne den Satz zur Quellenlage wäre eine Behauptung, die
    niemand geprüft hat. Verneinungen bleiben erlaubt."""
    text = (REPO / datei).read_text(encoding="utf-8")
    treffer = []
    for zeile in text.splitlines():
        if VERBOTEN.search(zeile) and not AUSNAHMEN.search(zeile):
            treffer.append(zeile.strip()[:100])
    assert not treffer, f"{datei}: ungedeckte Konformitätsbehauptung:\n  " + "\n  ".join(treffer)


def test_die_pruefung_wuerde_eine_behauptung_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass gerade nichts dasteht."""
    assert VERBOTEN.search("falzmarke erzeugt normgerechte Briefe.")
    assert not AUSNAHMEN.search("falzmarke erzeugt normgerechte Briefe.")
    # Und die Verneinung darf nicht anschlagen:
    satz = "Die verbreitete Word-Vorlage ist nicht normgerecht."
    assert AUSNAHMEN.search(satz), "Die Ausnahme greift bei der Verneinung nicht"
