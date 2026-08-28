"""Telefonnummern im Informationsblock (Issue #133).

Gefunden beim ersten Einsatz an einem echten Absenderprofil: Nummern mit
fünf- oder sechsstelliger Vorwahl — also die kleinerer Orte — wurden als
abweichend gemeldet, obwohl sie richtig sind.

Eine Warnung, die bei gültigen Eingaben anschlägt, kostet Vertrauen in alle
anderen. Deshalb steht hier zu jedem stillen Fall ein lauter daneben: Ein
Muster, das alles durchlässt, wäre genauso falsch wie eines, das zu viel meldet.
"""

from __future__ import annotations

import pytest

from falzmarke import cli as falzmarke
from falzmarke.lint import TELEFON_MUSTER, telefon_grund
from conftest import SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

KOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""


def linte_telefon(tmp_path, nummer: str):
    pfad = tmp_path / "brief.md"
    pfad.write_text(f'---\n{KOPF}infoblock:\n  telefon: "{nummer}"\n---\nText.\n',
                    encoding="utf-8")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    return [b for b in bericht.befunde if b.regel == "infoblock.telefon"]


# ── Was still bleiben muss ──────────────────────────────────────────────────

STILL = [
    ("089 123456", "zweistellige Ortsnetzkennzahl"),
    ("0941 123456", "dreistellig"),
    ("09401 123456", "vierstellig — vor #133 gemeldet"),
    ("039931 12345", "fünfstellig — vor #133 gemeldet"),
    ("09161 6209800", "wörtlich aus der Quelle der Regel"),
    ("09161 620980-11", "dieselbe Quelle, mit Durchwahl"),
    ("0941 620-9800", "die Musterform"),
    ("0170 1234567", "Mobilfunk"),
    ("+49 941 620-9800", "international"),
    ("+49 9401 123456", "international, vierstellige Kennzahl"),
]


@pytest.mark.parametrize("nummer,warum", STILL, ids=[n for n, _ in STILL])
def test_gueltige_nummer_wird_nicht_gemeldet(tmp_path, nummer, warum):
    assert not linte_telefon(tmp_path, nummer), warum


def test_dieselbe_nummer_national_und_international_gleich_beurteilt(tmp_path):
    """Vor #133 ging `+49 9401 …` durch und `09401 …` nicht — dieselbe Nummer,
    je nach Notation ein anderes Urteil."""
    assert not linte_telefon(tmp_path, "09401 123456")
    assert not linte_telefon(tmp_path, "+49 9401 123456")


# ── Was gemeldet werden muss ────────────────────────────────────────────────

GEMELDET = [
    ("(0941) 620/9800", "Klammern und Schrägstrich"),
    ("0941/620 9800", "Schrägstrich"),
    ("0941620-9800", "kein Leerzeichen nach der Vorwahl"),
    ("+49 (0)941 620", "Null in Klammern"),
    ("Telefon 0941 620", "Text davor"),
    ("0941.620.9800", "Punkte"),
]


@pytest.mark.parametrize("nummer,warum", GEMELDET, ids=[n for n, _ in GEMELDET])
def test_abweichende_schreibweise_wird_weiterhin_gemeldet(tmp_path, nummer, warum):
    """Die Gegenprobe zur Lockerung oben. Ohne sie belegte diese Datei nur, dass
    das Muster mehr durchlässt — nicht, dass es noch etwas prüft."""
    befunde = linte_telefon(tmp_path, nummer)
    assert befunde, f"{warum} bleibt unbemerkt"


# ── Die Meldung nennt den Grund ─────────────────────────────────────────────

GRUENDE = [
    ("(0941) 620/9800", "enthält"),
    ("0941620-9800", "kein Leerzeichen"),
    ("620-9800", "Vorwahl fehlt"),
    ("0941 620 9800 ", "Leerzeichen"),
]


@pytest.mark.parametrize("nummer,erwartet", GRUENDE, ids=[n.strip() for n, _ in GRUENDE])
def test_die_meldung_nennt_den_tatsaechlichen_grund(nummer, erwartet):
    """Die alte Meldung wiederholte die Sollform — im auslösenden Fall waren
    beide genannten Punkte erfüllt. Sie nannte also zwei Dinge, die stimmten,
    und verschwieg das Eigentliche."""
    assert erwartet in telefon_grund(nummer)


def test_die_meldung_verlangt_keinen_bindestrich_mehr(tmp_path):
    """Der eigentliche Schaden aus #133: Wer die alte Meldung befolgte, fügte
    eine Durchwahl ein, die es nicht gibt."""
    befunde = linte_telefon(tmp_path, "0941620-9800")
    text = " ".join(b.meldung for b in befunde)
    assert "Durchwahl mit Bindestrich" not in text


def test_gegenprobe_der_grund_ist_nicht_immer_derselbe():
    """Sonst wäre `telefon_grund` nur ein umformulierter Einheitssatz."""
    gruende = {telefon_grund(n) for n, _ in GEMELDET}
    assert len(gruende) >= 3, gruende
