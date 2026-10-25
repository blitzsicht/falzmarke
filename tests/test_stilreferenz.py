"""Die Stilreferenz: Nachrichtenlagen und was gestrichen wird.

Zwei Arten von Test stehen hier, und nur die zweite ist ein Nachweis.

Die erste hält fest, dass ein Abschnitt **da** ist. Sie kann nur anschlagen,
wenn jemand ihn löscht — gegen eine Verschlechterung des Inhalts hilft sie
nicht. Sie steht hier trotzdem, aus demselben Grund wie die Textkanon-Tests:
Die Lagen sind eine Zusage, und eine Zusage, die still verschwinden kann, ist
keine.

Die zweite ist die eigentliche Gegenprobe. `stil.md` behauptet jetzt etwas über
ein anderes Modul: dass der Halbgeviertstrich und die Anführungszeichen „…“ in
deutscher Geschäftspost richtig sind, weil `typografie.py` sie absichtlich
erzeugt. Das ist nachprüfbar — und wenn jemand den Typografie-Pass ändert, wird
der Absatz in der Stilreferenz falsch, ohne dass er selbst angefasst wurde.
Genau diesen Fall misst `test_die_absage_an_den_englischen_humanizer_traegt`.
"""

from __future__ import annotations

import pytest

from conftest import SKILL
from falzmarke import typografie

STIL = SKILL / "references" / "stil.md"


@pytest.fixture(scope="module")
def text() -> str:
    return STIL.read_text(encoding="utf-8")


# ── Die Nachrichtenlagen ────────────────────────────────────────────────────

#: Die Lagen, in denen die meisten Mails entstehen. Vorher deckte die Datei nur
#: Brieftypen ab — Angebot, Mahnung, Kündigung, Widerspruch und drei weitere.
LAGEN = [
    "Angebot nachfassen",
    "Reklamation beantworten",
    "Preis oder Nachlass",
    "Lieferant",
    "Intern",
]


@pytest.mark.parametrize("lage", LAGEN)
def test_jede_nachrichtenlage_ist_genannt(text, lage):
    assert f"**{lage}**" in text, f"die Lage „{lage}“ fehlt"


def test_jede_lage_sagt_was_zuerst_kommt(text):
    """Eine Lage ohne Reihenfolge ist eine Überschrift, keine Regel.

    Geprüft wird nicht die Formulierung, sondern dass der Absatz überhaupt eine
    Ordnung nennt: ein Mittelpunkt als Trenner oder das Wort „zuerst“.
    """
    for lage in LAGEN:
        anfang = text.index(f"**{lage}**")
        absatz = text[anfang:text.index("\n\n", anfang)]
        assert "·" in absatz or "zuerst" in absatz, f"„{lage}“ nennt keine Reihenfolge"


# ── Was gestrichen wird ─────────────────────────────────────────────────────

def test_der_abschnitt_existiert(text):
    assert "## Was gestrichen wird" in text


def test_jede_gestrichene_wendung_hat_ihren_gegenfall(text):
    """Die Grenze ist der Punkt, nicht die Liste.

    Dieselbe Disziplin wie bei den Floskeln (`test_floskeln.py`): Neben jedem
    Muster steht der Fall, der ihm ähnlich sieht und bleiben muss. Eine Zeile
    ohne Gegenfall wäre ein Verbot ohne Grenze — und die erste Wendung, die
    jemand irrtümlich streicht, ist dann eine, die etwas trug.
    """
    anfang = text.index("## Was gestrichen wird")
    ende = text.index("**Was hier ausdrücklich nicht steht.**", anfang)
    zeilen = [z for z in text[anfang:ende].splitlines()
              if z.startswith("|") and not z.startswith("|---")
              and "Gestrichen" not in z]
    assert len(zeilen) >= 8, f"nur {len(zeilen)} Muster in der Tabelle"
    for zeile in zeilen:
        spalten = [s.strip() for s in zeile.strip("|").split("|")]
        assert len(spalten) == 2, f"keine zwei Spalten: {zeile}"
        assert spalten[0] and spalten[1], f"Spalte leer: {zeile}"


def test_der_fehler_mit_absicht_ist_ausgeschlossen(text):
    """Zufällige Fehler sind keine Natürlichkeit.

    Das ist die eine Stelle, an der die englischen Vorlagen und diese Datei
    sich nicht nur in der Sprache unterscheiden, sondern im Ziel.
    """
    assert "ein Fehler mit Absicht" in text
    assert "nicht menschlicher, sondern schlechter" in text


# ── Die Gegenprobe: die Absage muss stimmen ─────────────────────────────────

def test_die_absage_an_den_englischen_humanizer_traegt(text):
    """`stil.md` nimmt drei englische Regeln ausdrücklich nicht auf.

    Zwei davon sind nachprüfbar, und zwar nicht in dieser Datei, sondern im
    Typografie-Pass: Er **erzeugt** den Halbgeviertstrich und die deutschen
    Anführungszeichen. Solange er das tut, ist die Absage begründet. Wer die
    Schritte `_striche` oder `_anfuehrungszeichen` entfernt, macht diesen
    Absatz zu einer Behauptung ohne Deckung — und diesen Test rot.
    """
    assert "nicht steht" in text, "der Absatz fehlt"
    assert "typografie.py" in text, "die Begründung nennt ihre Quelle nicht"

    assert "–" in typografie.anwenden("Lieferung -- wie besprochen -- am Montag"), \
        "der Halbgeviertstrich wird nicht mehr gesetzt; stil.md behauptet es aber"
    gesetzt = typografie.anwenden('Er schrieb "ja" dazu.')
    assert "„" in gesetzt and "“" in gesetzt, \
        "die deutschen Anführungszeichen werden nicht mehr gesetzt"


def test_die_datei_hat_echte_umlaute(text):
    """Deutscher Text mit null Umlauten ist verdächtig — hier wäre er falsch."""
    assert sum(text.count(z) for z in "äöüÄÖÜß") > 50
    for ersatz in ("fuer ", "ueber ", "koennen ", "maessig"):
        assert ersatz not in text, f"ASCII-Ersatz „{ersatz.strip()}“ in der Datei"
