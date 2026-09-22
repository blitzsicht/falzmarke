"""Die Maße aus DIN 5008:2020, gemessen am fertigen PDF.

Diese Datei ist die Abnahme. Sie prüft nicht, ob der Code etwas tut, sondern
ob das ausgelieferte PDF die Norm einhält.
"""

from __future__ import annotations

import pytest

from falzmarke import geometrie
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


@pytest.mark.parametrize("form,soll_kante", [("A", 32.0), ("B", 50.0)])
def test_die_zahl_der_sekundaerquelle_ist_die_zonenkante_nicht_der_briefkopf(form, soll_kante):
    """#345: Der Wikipedia-Artikel nennt 32 mm (Form A) und 50 mm (Form B) unter
    der Blattkante, unsere Regeln sagen 27 und 45 mm. Das ist kein Widerspruch,
    sondern eine andere Kante — und die Bemerkungen an `geometrie.form_a.masse`,
    `geometrie.form_b.briefkopf` und `geometrie.form_b.infoblock` behaupten das.

    Hier steht, woran diese Behauptung hängt: an genau einer Linie, die drei
    Namen trägt. Verschiebt jemand einen der drei Werte allein, wird der Test
    rot und die Bemerkung mit ihm falsch — ohne diese Probe wäre sie Prosa,
    die still altert.

    Die Zahl 32 bzw. 50 steht hier ausgeschrieben, weil sie aus der Quelle kommt
    und nicht aus `geometrie.py`: Ein Test, der beide Seiten aus derselben Datei
    läse, könnte nicht rot werden.
    """
    masse = geometrie.FORM[form]
    kopf = masse["kopfhoehe"]
    zone_oben, zone_unten = masse["ruecksende_zone"]

    assert zone_oben == kopf, (
        f"Form {form}: Die Rücksendezone beginnt bei {zone_oben}, der Briefkopf "
        f"endet bei {kopf} — dann ist die Herleitung in der Regeldatei hinfällig.")
    assert zone_unten == soll_kante, (
        f"Form {form}: Unterkante der Rücksendezone {zone_unten}, die Quelle nennt "
        f"{soll_kante} — die Bemerkung zu #345 stimmt nicht mehr.")
    assert masse["infoblock_oben"] == soll_kante, (
        f"Form {form}: Der Informationsblock beginnt bei {masse['infoblock_oben']}, "
        f"nicht bei {soll_kante} — es ist dann nicht mehr dieselbe Linie.")
    assert zone_unten - kopf == 5.0, (
        f"Form {form}: Die Rücksendezone ist {zone_unten - kopf} mm hoch, nicht 5 — "
        "der 5-mm-Versatz zur Quelle hätte dann eine andere Ursache.")


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
