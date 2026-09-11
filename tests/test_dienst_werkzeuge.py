"""Wie viele Werkzeuge der MCP-Dienst hat, steht an mehreren Stellen im Text.

ANLASS

`email_setzen` kam nach den ersten drei Werkzeugen dazu, das Zahlwort „drei“
blieb stehen: im Modul-Docstring von `dienst.py`, in seiner
Abschnittsüberschrift, im Docstring von `baue_server()` und in der README.
Gefunden hat es niemand beim Lesen, sondern erst die Arbeit an #237, weil ein
Verzeichniseintrag die falsche Zahl abgeschrieben hätte — und beim Aufräumen
fiel eine fünfte Stelle erst auf, als die Prüfung unten den ganzen Baum
durchlief statt nur `dienst.py`. Deshalb steht hier keine Zahl.

Deshalb prüft dieser Test nicht die Zahl, sondern die **Namen** — gegen
`dienst.WERKZEUGE`, die einzige Stelle, an der sie wirklich entstehen. Ein
fünftes Werkzeug macht ihn von selbst rot, statt still zu veralten.

Der Import von `dienst` kommt ohne das MCP-SDK aus: Die Werkzeuge sind normale
Funktionen, erst `baue_server()` braucht das SDK.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from falzmarke import dienst

from conftest import REPO

NAMEN = tuple(w.__name__ for w in dienst.WERKZEUGE)


def test_der_dienst_meldet_die_erwarteten_werkzeuge():
    """Die Gegenprobe zu allem darunter: Wäre WERKZEUGE leer, prüfte der Rest
    die leere Menge und bliebe still grün."""
    assert len(NAMEN) >= 4, f"nur {len(NAMEN)} Werkzeuge: {NAMEN}"
    assert "email_setzen" in NAMEN


def test_die_readme_nennt_jedes_werkzeug():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    abschnitt = text.split("### In einem anderen KI-Client", 1)
    assert len(abschnitt) == 2, "Der MCP-Abschnitt der README heißt nicht mehr so"
    mcp_teil = abschnitt[1].split("\n## ", 1)[0]
    fehlend = [n for n in NAMEN if f"`{n}`" not in mcp_teil]
    assert not fehlend, (
        "Die README nennt nicht alle Werkzeuge des Dienstes: "
        + ", ".join(fehlend))


def test_der_handschlag_erwartet_dieselben_werkzeuge():
    """scripts/mcp_handschlag.py führt die Namen ein zweites Mal — er läuft
    gegen einen Container und kann `dienst` nicht importieren. Zwei Kopien
    driften; diese Zeile hält sie zusammen."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    import mcp_handschlag                                          # noqa: E402

    assert set(mcp_handschlag.ERWARTETE_WERKZEUGE) == set(NAMEN), (
        f"Handschlag erwartet {mcp_handschlag.ERWARTETE_WERKZEUGE}, "
        f"der Dienst meldet {NAMEN}")


#: Wo ein Zahlwort vor dem Wort Werkzeuge stehen könnte. Bewusst der ganze
#: Baum und nicht nur `dienst.py`: Beim Aufräumen für #237 waren vier Stellen
#: gefunden und eine übersehen — `tests/test_dienst.py`, also ausgerechnet die
#: Datei, die den Dienst prüft. Eine Suche, die nur die naheliegenden Dateien
#: kennt, findet genau die eine nicht (vgl. tests/test_textkanon.py).
TEXTQUELLEN = sorted(
    p for muster in ("skill/**/*.py", "skill/**/*.md", "docs/**/*.md",
                     "tests/*.py", "scripts/*.py", "README.md")
    for p in REPO.glob(muster)
    if "vendor" not in p.parts and "__pycache__" not in p.parts
    # Diese Datei selbst nicht: Sie erklärt das Verbot und muss die verbotene
    # Wendung dafür aussprechen — im Text oben und in der Gegenprobe unten.
    # Ohne diese Zeile schlägt die Prüfung an ihrer eigenen Begründung an.
    and p.name != Path(__file__).name
)

#: CHANGELOG.md steht nicht in der Liste: Dort ist die alte Zahl ein Zitat des
#: Zustands von damals und wird nicht nachträglich umgeschrieben — dieselbe
#: Ausnahme, die test_textkanon.py für den Verlauf macht.
ZAHLWORT = re.compile(r"\b(?:[Dd]rei|[Vv]ier|[Ff]ünf|[Ss]echs) Werkzeuge")


def test_die_dateiliste_ist_nicht_leer():
    """Sonst prüfte der Test darunter die leere Menge und wäre still grün."""
    assert len(TEXTQUELLEN) >= 20, f"nur {len(TEXTQUELLEN)} Textquellen gefunden"


@pytest.mark.parametrize("datei", TEXTQUELLEN, ids=lambda p: str(p.relative_to(REPO)))
def test_keine_veraltete_anzahl_im_baum(datei):
    zahlwoerter = {3: "drei", 4: "vier", 5: "fünf", 6: "sechs"}
    richtig = zahlwoerter.get(len(NAMEN))
    assert richtig, f"Für {len(NAMEN)} Werkzeuge fehlt hier das Zahlwort."
    falsch = [z.strip() for z in ZAHLWORT.findall(datei.read_text(encoding="utf-8"))
              if z.split()[0].lower() != richtig]
    assert not falsch, (
        f"{datei.relative_to(REPO)} nennt {falsch[0]!r}, es sind {len(NAMEN)}: "
        + ", ".join(NAMEN))


def test_gegenprobe_das_muster_trifft_wirklich():
    """Ohne sie belegte der Test darüber nur, dass ein Regex nichts findet."""
    assert ZAHLWORT.findall("Drei Werkzeuge: brief_rendern, ...")
    assert ZAHLWORT.findall("Die drei Werkzeuge sind gewoehnliche Funktionen")
    # Und der heutige, richtige Wortlaut darf nicht anschlagen.
    assert not [z for z in ZAHLWORT.findall("Vier Werkzeuge: brief_rendern")
                if z.split()[0].lower() != "vier"]
