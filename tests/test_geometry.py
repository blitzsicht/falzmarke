"""Die Maße aus DIN 5008:2020, gemessen am fertigen PDF.

Diese Datei ist die Abnahme. Sie prüft nicht, ob der Code etwas tut, sondern
ob das ausgelieferte PDF die Norm einhält.
"""

from __future__ import annotations

import pytest

from normbrief import geometrie
from conftest import BEISPIELE


@pytest.mark.parametrize("name", [p.stem for p in BEISPIELE])
def test_beispiel_haelt_alle_masse_ein(gerendert, name):
    pdf, form = gerendert[name]
    bericht = geometrie.pruefe(pdf, form)
    gescheitert = [p for p in bericht.pruefungen if not p.bestanden]
    assert not gescheitert, "\n" + "\n".join(
        f"{p.name}: soll {p.soll}, ist {p.ist} (Toleranz {p.toleranz})" for p in gescheitert
    )


def test_form_a_und_form_b_kommen_beide_vor(gerendert):
    formen = {form for _, form in gerendert.values()}
    assert formen == {"A", "B"}, f"Beispiele decken nur {formen} ab"


@pytest.mark.parametrize(
    "name,soll_falz1,soll_falz2,soll_kopf",
    [("brief-form-a", 87.0, 192.0, 27.0), ("brief-form-b", 105.0, 210.0, 45.0)],
)
def test_formspezifische_werte(gerendert, name, soll_falz1, soll_falz2, soll_kopf):
    """Die Formen müssen sich tatsächlich unterscheiden — sonst prüft die
    Testsuite oben nur zweimal dasselbe."""
    pdf, form = gerendert[name]
    import pdfplumber

    with pdfplumber.open(str(pdf)) as dokument:
        ys = [round(m[0], 1) for m in geometrie._marken(dokument.pages[0])]
    assert soll_falz1 in ys and soll_falz2 in ys, f"Falzmarken {ys}, erwartet {soll_falz1}/{soll_falz2}"
    assert geometrie.FORM[form]["kopfhoehe"] == soll_kopf


def test_pdfa_ist_der_standardfall(gerendert):
    for name, (pdf, _) in gerendert.items():
        ist_pdfa, xmp = geometrie.pdfa_geprueft(pdf)
        assert ist_pdfa, f"{name}: kein PDF/A-2b, XMP-Anfang: {xmp[:120]}"


def test_schriften_sind_eingebettet(gerendert):
    """Eine nicht eingebettete Schrift wird beim Empfänger ersetzt — das Layout
    stimmt dann nur auf dem eigenen Rechner."""
    for name, (pdf, _) in gerendert.items():
        offen = geometrie._nicht_eingebettete_schriften(pdf)
        assert not offen, f"{name}: nicht eingebettete Schriften {offen}"


def test_umlaute_ueberstehen_den_weg_ins_pdf(gerendert):
    """Ein Brief mit 'Gruessen' statt 'Grüßen' wäre unbrauchbar."""
    import pdfplumber

    pdf, _ = gerendert["brief-form-b"]
    with pdfplumber.open(str(pdf)) as dokument:
        text = dokument.pages[0].extract_text() or ""
    assert "Grüßen" in text
    assert "Musterstraße" in text
    for falsch in ("Gruessen", "Strasse", "Muenchen", "ue berall"):
        assert falsch not in text
