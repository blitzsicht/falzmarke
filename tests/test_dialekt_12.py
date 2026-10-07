"""Dialekt 1.2: das Ausfüllfeld und die Angabentabelle ohne Kopfzeile (ADR 0048).

Die Fassung ist additiv wie 1.1: Was in 1.0 und 1.1 geschrieben ist, setzt
unverändert. Neu sind keine Knotentypen des Parsers, sondern zwei Lesarten —
und genau deshalb steht hier zu jeder die Gegenrichtung: dieselbe Quelle unter
1.1 ergibt, was sie immer ergab.
"""

from __future__ import annotations

import pytest

from falzmarke import baum, emit, emit_html, emit_text
from falzmarke import markdown as md
from falzmarke.markdown import MarkdownFehler, lies

FELDZEILE = "Ort: ________ am _____ bitte.\n"
ANGABEN = "|   |   |\n|---|---|\n| Modell | Gerät 4 |\n| Nummer | ____ |\n"


def _arten(knoten) -> list[str]:
    return [type(k).__name__ for k in knoten]


# ── Die Fassung ─────────────────────────────────────────────────────────────

def test_12_ist_eine_fassung_und_nicht_die_vorgabe():
    assert "1.2" in md.FASSUNGEN
    assert md.STANDARDFASSUNG == "1.0"


@pytest.mark.parametrize("tabelle", ["MAX_UEBERSCHRIFT", "MAX_ZITATTIEFE", "MAX_LISTENTIEFE",
                                     "LISTENTIEFE_WARNUNG", "ZUSAETZLICH"])
def test_jede_tabelle_kennt_jede_fassung(tabelle):
    """Fehlt ein Schlüssel, endet der erste Brief dieser Fassung in einem KeyError."""
    assert set(getattr(md, tabelle)) == set(md.FASSUNGEN)


@pytest.mark.parametrize("quelle,klasse", [
    ("## Ein Abschnitt\n", baum.Ueberschrift),
    ("> Ein Zitat.\n", baum.Zitat),
    ("```\nein Auszug\n```\n", baum.Wortlaut),
])
def test_12_setzt_alles_was_11_setzt(quelle, klasse):
    assert any(isinstance(b, klasse) for b in lies(quelle, dialekt="1.2"))


# ── Ausfüllfeld ─────────────────────────────────────────────────────────────

def test_unterstrichkette_wird_zum_feld():
    absatz, = lies(FELDZEILE, dialekt="1.2")
    assert _arten(absatz.kinder) == ["Text", "Ausfuellfeld", "Text", "Ausfuellfeld", "Text"]
    assert [k.laenge for k in absatz.kinder if isinstance(k, baum.Ausfuellfeld)] == [8, 5]


@pytest.mark.parametrize("fassung", ["1.0", "1.1"])
def test_davor_bleibt_sie_woertlicher_text(fassung):
    """Die Zusage des Dialekts — und die Gegenprobe zum Test darüber."""
    absatz, = lies(FELDZEILE, dialekt=fassung)
    assert _arten(absatz.kinder) == ["Text"]
    assert absatz.kinder[0].inhalt == FELDZEILE.strip()


@pytest.mark.parametrize("quelle", [
    "Datum:________",        # am Doppelpunkt
    "(________)",            # in Klammern
    "________ Unterschrift",  # am Zeilenanfang
    "Bis ________.",         # vor dem Punkt
])
def test_ein_feld_darf_an_satzzeichen_stehen(quelle):
    absatz, = lies(quelle, dialekt="1.2")
    assert _arten(absatz.kinder).count("Ausfuellfeld") == 1


@pytest.mark.parametrize("quelle", [
    "Betrag: ____,__ EUR",   # CommonMark macht das Komma fett
    "ein ___b___ wort",      # fett-kursives b
    "teil_____name",         # ein Bezeichner
    "Nummer __ bitte",       # zwei Unterstriche sind keine Kette — und kein Fettdruck
])
def test_eine_kette_die_kein_feld_wird_faellt_auf(quelle):
    """Sonst stünde im Blatt Fettdruck oder ein Rest aus Strichen, der aussieht wie gewollt."""
    if quelle == "Nummer __ bitte":
        # Unter drei Unterstrichen ist es weder Kette noch Feld — Text, wie er dasteht.
        absatz, = lies(quelle, dialekt="1.2")
        assert _arten(absatz.kinder) == ["Text"]
        return
    with pytest.raises(MarkdownFehler) as fehler:
        lies(quelle, dialekt="1.2")
    assert "muss frei stehen" in str(fehler.value)


def test_geschuetzte_unterstriche_sind_ab_12_ebenfalls_ein_feld():
    """`\\_\\_\\_` ist nach dem Parsen von `___` nicht zu unterscheiden (ADR 0048)."""
    absatz, = lies(r"Datum \_\_\_\_\_ hier", dialekt="1.2")
    assert _arten(absatz.kinder) == ["Text", "Ausfuellfeld", "Text"]
    assert absatz.kinder[1].laenge == 5


def test_unterstriche_im_auszug_bleiben_wortlaut():
    absatz, = lies("Nenne `a___b` und ____ bitte", dialekt="1.2")
    assert _arten(absatz.kinder) == ["Text", "Wortlaut", "Text", "Ausfuellfeld", "Text"]
    assert absatz.kinder[1].inhalt == "a___b"


def test_feld_in_fettdruck_wird_gezaehlt():
    absatz, = lies("**Name: ________**", dialekt="1.2")
    assert _arten(absatz.kinder[0].kinder) == ["Text", "Ausfuellfeld"]


def test_ueberlanges_feld_bricht_ab():
    with pytest.raises(MarkdownFehler, match="passen nicht in eine Zeile"):
        lies("Text " + "_" * (md.FELD_MAX + 1), dialekt="1.2")
    lies("Text " + "_" * md.FELD_MAX, dialekt="1.2")           # die Grenze selbst geht


def test_die_fehlermeldung_nennt_die_zeile_der_quelle():
    with pytest.raises(MarkdownFehler) as fehler:
        lies("Erster Absatz.\n\nBetrag: ____,__ EUR\n", zeilenversatz=10, dialekt="1.2")
    assert fehler.value.zeile == 13


@pytest.mark.parametrize("fassung", ["1.0", "1.1", "1.2"])
def test_zeile_nur_aus_unterstrichen_bleibt_abbruch_und_sagt_warum(fassung):
    with pytest.raises(MarkdownFehler) as fehler:
        lies("Text.\n\n____________\n", dialekt=fassung)
    assert "unterschriften:" in str(fehler.value)


def test_trennlinie_aus_strichen_behaelt_ihre_meldung():
    """Die neue Meldung gilt den Unterstrichen, nicht jeder Trennlinie."""
    with pytest.raises(MarkdownFehler) as fehler:
        lies("Text.\n\n---\n", dialekt="1.2")
    assert "unterschriften" not in str(fehler.value)
    assert "Trennlinien werden nicht gesetzt" in str(fehler.value)


# ── Angabentabelle ──────────────────────────────────────────────────────────

def test_leere_kopfzeile_wird_zur_angabentabelle():
    angaben, = lies(ANGABEN, dialekt="1.2")
    assert isinstance(angaben, baum.Angaben)
    assert len(angaben.zeilen) == 2 and all(len(z) == 2 for z in angaben.zeilen)
    assert _arten(angaben.zeilen[1][1]) == ["Ausfuellfeld"]


@pytest.mark.parametrize("kopf", ["|   |   |", "| | |", "||  |"])
def test_jede_schreibweise_der_leeren_kopfzeile_gilt(kopf):
    quelle = ANGABEN.replace("|   |   |", kopf, 1)
    assert isinstance(lies(quelle, dialekt="1.2")[0], baum.Angaben)


@pytest.mark.parametrize("fassung", ["1.0", "1.1"])
def test_davor_bleibt_es_eine_tabelle_mit_leerer_kopfzeile_und_wird_gemeldet(fassung):
    """Unverändert gesetzt — aber nicht mehr stumm: Der Hinweis nennt die Fassung."""
    hinweise: list = []
    tabelle, = lies(ANGABEN.replace("____", "4711"), dialekt=fassung, hinweise=hinweise)
    assert isinstance(tabelle, baum.Tabelle)
    assert len(tabelle.zeilen) == 3 and tabelle.zeilen[0] == ((), ())
    assert len(hinweise) == 1 and "1.2" in hinweise[0].korrektur


def test_tabelle_mit_kopfzeile_bleibt_in_12_eine_tabelle():
    tabelle, = lies("| Was | Wert |\n|---|---|\n| a | b |\n", dialekt="1.2")
    assert isinstance(tabelle, baum.Tabelle)


def test_teilweise_leere_kopfzeile_ist_keine_angabentabelle():
    tabelle, = lies("|   | Wert |\n|---|---|\n| a | b |\n", dialekt="1.2")
    assert isinstance(tabelle, baum.Tabelle)


@pytest.mark.parametrize("spalten", [1, 3, 4])
def test_angabentabelle_hat_genau_zwei_spalten(spalten):
    quelle = ("|" + "   |" * spalten + "\n|" + "---|" * spalten + "\n|" + " a |" * spalten + "\n")
    with pytest.raises(MarkdownFehler, match="genau zwei Spalten"):
        lies(quelle, dialekt="1.2")


# ── Alle drei Emitter setzen beide Knoten ───────────────────────────────────

def test_typst_ruft_die_bausteine_des_satzes():
    gesetzt = emit.setze(lies(FELDZEILE + "\n" + ANGABEN, dialekt="1.2"))
    assert "#feld(8)" in gesetzt and "#feld(5)" in gesetzt
    assert gesetzt.count("#angaben(") == 1
    assert "table.header" not in gesetzt                       # keine Kopfzeile, auch keine leere
    assert "#table(" not in gesetzt


def test_typst_unter_11_setzt_die_alte_tabelle():
    gesetzt = emit.setze(lies(ANGABEN.replace("____", "4711"), dialekt="1.1"))
    assert "table.header" in gesetzt and "#angaben(" not in gesetzt


def test_text_zeigt_die_unterstriche_und_keine_strichzeile():
    gesetzt = emit_text.setze(lies(FELDZEILE + "\n" + ANGABEN, dialekt="1.2"))
    assert "Ort: ________ am _____ bitte." in gesetzt
    assert "Modell  Gerät 4\nNummer  ____" in gesetzt
    assert "-|-" not in gesetzt and " | " not in gesetzt


def test_html_setzt_zeilenkoepfe_und_keinen_tabellenkopf():
    gesetzt = emit_html.setze(lies(ANGABEN, dialekt="1.2"))
    assert gesetzt.count('<th scope="row"') == 2
    assert "<thead" not in gesetzt and ">____</td>" in gesetzt
    assert emit_html.verstoesse(emit_html.dokument(gesetzt)) == []


def test_html_feld_im_text_sind_die_unterstriche():
    gesetzt = emit_html.setze(lies(FELDZEILE, dialekt="1.2"))
    assert "Ort: ________ am _____ bitte." in gesetzt


def test_die_angabentabelle_wird_im_klartext_nicht_gefaltet():
    """Eine umbrochene Zeile wäre eine andere Zuordnung von Bezeichnung und Wert."""
    assert baum.Angaben in emit_text.FESTE_BLOECKE
