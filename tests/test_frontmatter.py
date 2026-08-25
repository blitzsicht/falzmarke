"""Datenvertrag: Pflichtfelder, Grenzen der Zonen, Datumsformate."""

from __future__ import annotations

import datetime as dt

import pytest

from normbrief import cli as normbrief
from conftest import REPO

PROFILE = REPO / "skill" / "typst" / "profiles"


def schreibe(tmp_path, kopf: str, body: str = "Text des Briefes.\n"):
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{kopf}---\n{body}", encoding="utf-8")
    return pfad


def rendere(tmp_path, kopf: str, body: str = "Text des Briefes.\n"):
    return normbrief.rendere(
        schreibe(tmp_path, kopf, body), tmp_path / "aus.pdf", profil_verzeichnis=PROFILE
    )


GUELTIG = """profil: example
empfaenger:
  - Muster GmbH
  - Musterstraße 1
  - 12345 Musterstadt
datum: 2026-08-25
betreff: Ein Betreff
"""


def test_gueltiger_brief_rendert(tmp_path):
    pdf, form = rendere(tmp_path, GUELTIG)
    assert pdf.is_file() and form == "B"


@pytest.mark.parametrize("feld", ["profil", "empfaenger", "datum", "betreff"])
def test_pflichtfeld_fehlt(tmp_path, feld):
    kopf = "\n".join(z for z in GUELTIG.splitlines() if not z.startswith(feld)) + "\n"
    if feld == "empfaenger":
        kopf = "\n".join(z for z in kopf.splitlines() if not z.startswith("  - ")) + "\n"
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, kopf)
    assert feld in str(fehler.value)


def test_anschrift_mit_sieben_zeilen(tmp_path):
    """Die Anschriftzone fasst sechs Zeilen. Eine siebte würde aus dem Fenster
    des Umschlags laufen."""
    kopf = GUELTIG.replace(
        "  - 12345 Musterstadt\n",
        "  - 12345 Musterstadt\n" + "".join(f"  - Zeile {i}\n" for i in range(4)),
    )
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, kopf)
    assert "7 Zeilen" in str(fehler.value)


def test_vier_vermerke_sind_zu_viel(tmp_path):
    kopf = GUELTIG + "vermerke: [Einschreiben, Eilt, Persönlich, Vertraulich]\n"
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, kopf)
    assert "Vermerkzone" in str(fehler.value)


def test_anrede_ohne_komma(tmp_path):
    kopf = GUELTIG + "anrede: Sehr geehrte Damen und Herren\n"
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, kopf)
    assert "Komma" in str(fehler.value)


def test_gruss_mit_komma(tmp_path):
    kopf = GUELTIG + "gruss: Mit freundlichen Grüßen,\n"
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, kopf)
    assert "ohne Komma" in str(fehler.value)


def test_unbekannte_form(tmp_path):
    with pytest.raises(normbrief.Eingabefehler):
        rendere(tmp_path, GUELTIG + "form: C\n")


def test_andere_norm_wird_abgelehnt(tmp_path):
    """Das Feld ist reserviert, damit CH und AT später additiv dazukommen."""
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, GUELTIG + "norm: sn010130\n")
    assert "din5008" in str(fehler.value)


@pytest.mark.parametrize(
    "eingabe,format_name,erwartet",
    [
        (dt.date(2026, 8, 25), "lang", "25. August 2026"),
        (dt.date(2026, 8, 25), "iso", "2026-08-25"),
        ("2026-01-01", "lang", "1. Januar 2026"),
        ("2026-12-31", "lang", "31. Dezember 2026"),
    ],
)
def test_datumsformate(eingabe, format_name, erwartet):
    assert normbrief.formatiere_datum(eingabe, format_name) == erwartet


def test_leerer_body(tmp_path):
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, GUELTIG, body="\n")
    assert "keinen Text" in str(fehler.value)


def test_unbekanntes_profil(tmp_path):
    with pytest.raises(normbrief.Eingabefehler) as fehler:
        rendere(tmp_path, GUELTIG.replace("profil: example", "profil: gibtsnicht"))
    assert "gibtsnicht" in str(fehler.value) and "example" in str(fehler.value)
