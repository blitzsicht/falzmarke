"""Anlagen-PDFs anhängen — ohne dabei eine Konformität zu behaupten.

Drei Dinge können hier still schiefgehen, und jedes hat seine Prüfung:

1. Das Ergebnis behauptet weiter PDF/A, obwohl eine Anlage es nicht ist. Ein
   Merge erhält die XMP-Metadaten des Briefes; gemessen mit veraPDF ist das
   Ergebnis dann FAIL, während die Datei weiter „2b" sagt. Wer sie ins Archiv
   legt, merkt es, wenn die Schrift fehlt.
2. Die Kennzeichnung fällt, obwohl sie bleiben dürfte — übervorsichtig, und der
   Nutzer verliert PDF/A ohne Grund.
3. Die Anlage wird nach Briefregeln gemessen und fällt durch Prüfungen, die auf
   sie nie gemünzt waren: keine Kopfzeile mit Betreff, keine Seitenzählung,
   fremde Schriften.

Der Punkt, an dem alles hängt, ist die **Deklaration** der Anlage — was die Datei
über sich selbst sagt. Ob sie stimmt, kann nur ein Prüfwerkzeug wie veraPDF
sagen; das liegt nicht auf jedem Rechner und ist deshalb nicht Voraussetzung
dieser Tests.
"""

from __future__ import annotations

import shutil
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "skill"))

from falzmarke import anlagen                                    # noqa: E402
from falzmarke import cli as falzmarke                           # noqa: E402
from falzmarke import geometrie                                  # noqa: E402

BRIEF = """---
profil: example
datum: 2026-08-26
empfaenger:
  - Muster GmbH
  - Frau Erika Muster
  - Musterstraße 1
  - 12345 Musterstadt
betreff: Angebot mit Anlagen
anrede: Sehr geehrte Frau Muster,
{anlagen}---

anbei die Unterlagen.

Mit freundlichen Grüßen
"""


def _ohne_deklaration(ziel) -> "object":
    """Ein PDF mit nicht eingebetteter Base-14-Schrift — kein PDF/A, sagt auch nichts.

    Von Hand gebaut statt gerendert: Was Typst erzeugt, ist faktisch konform
    (Fonts eingebettet), auch wenn es sich nicht als PDF/A deklariert. Für den
    Fall, um den es hier geht, braucht es eine Datei, die wirklich verstößt.
    """
    objekte = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        None,
    ]
    strom = b"BT /F1 24 Tf 72 750 Td (Rechnung 2026-0815) Tj ET"
    objekte[4] = b"<< /Length %d >>\nstream\n" % len(strom) + strom + b"\nendstream"

    aus, versatz = bytearray(b"%PDF-1.4\n"), []
    for n, koerper in enumerate(objekte, start=1):
        versatz.append(len(aus))
        aus += b"%d 0 obj\n" % n + koerper + b"\nendobj\n"
    start = len(aus)
    aus += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objekte) + 1)
    for v in versatz:
        aus += b"%010d 00000 n \n" % v
    aus += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objekte) + 1, start)
    ziel.write_bytes(bytes(aus))
    return ziel


@pytest.fixture
def brief(tmp_path):
    """Ein frisch gesetzter Brief, PDF/A-2b gekennzeichnet."""
    quelle = tmp_path / "brief.md"
    quelle.write_text(BRIEF.format(anlagen=""), encoding="utf-8")
    pdf, form = falzmarke.rendere(quelle, tmp_path / "brief.pdf")
    return pdf, form


# ── Die Deklaration lesen ───────────────────────────────────────────────────

def test_ein_falzmarke_brief_deklariert_pdfa(brief):
    assert anlagen.deklaration(brief[0]) == "2b"


def test_eine_datei_ohne_xmp_deklariert_nichts(tmp_path):
    assert anlagen.deklaration(_ohne_deklaration(tmp_path / "fremd.pdf")) is None


# ── Anhängen ────────────────────────────────────────────────────────────────

def test_die_seiten_kommen_hinten_dazu(brief, tmp_path):
    pdf, _ = brief
    fremd = _ohne_deklaration(tmp_path / "fremd.pdf")
    bericht = anlagen.haenge_an(pdf, [fremd, fremd])
    assert bericht["seiten_vorher"] == 1
    assert bericht["seiten_nachher"] == 3
    assert [a["datei"] for a in bericht["anlagen"]] == ["fremd.pdf", "fremd.pdf"]


def test_der_brief_bleibt_seite_eins(brief, tmp_path):
    """Die Reihenfolge ist die Zusage: Brief zuerst, Anlagen dahinter."""
    import pdfplumber

    pdf, _ = brief
    anlagen.haenge_an(pdf, [_ohne_deklaration(tmp_path / "fremd.pdf")])
    with pdfplumber.open(str(pdf)) as dokument:
        erste = dokument.pages[0].extract_text() or ""
        letzte = dokument.pages[-1].extract_text() or ""
    assert "Angebot mit Anlagen" in erste
    assert "Rechnung 2026-0815" in letzte


# ── Die PDF/A-Frage ─────────────────────────────────────────────────────────

def test_eine_anlage_ohne_deklaration_kostet_die_kennzeichnung(brief, tmp_path):
    """Sonst behauptet die Datei PDF/A und ist es nicht — das teuerste Ergebnis."""
    pdf, _ = brief
    bericht = anlagen.haenge_an(pdf, [_ohne_deklaration(tmp_path / "fremd.pdf")])
    assert bericht["pdfa_vorher"] == "2b"
    assert bericht["pdfa_nachher"] is None
    assert bericht["ohne_deklaration"] == ["fremd.pdf"]
    assert anlagen.deklaration(pdf) is None


def test_eine_anlage_mit_deklaration_behaelt_sie(brief, tmp_path):
    """Gegenprobe: Die Regel darf nicht jede Kennzeichnung streichen.

    Ohne diesen Fall wäre „Kennzeichnung entfernt" nicht von „Kennzeichnung
    immer entfernt" zu unterscheiden — und Anlagen und PDF/A schlössen sich
    grundsätzlich aus, ohne dass es jemand entschieden hätte.
    """
    pdf, _ = brief
    zweiter = tmp_path / "anlage-pdfa.pdf"
    shutil.copy(pdf, zweiter)
    bericht = anlagen.haenge_an(pdf, [zweiter])
    assert bericht["ohne_deklaration"] == []
    assert bericht["pdfa_nachher"] == "2b"
    assert anlagen.deklaration(pdf) == "2b"


# ── Die Anlage wird nicht nach Briefregeln gemessen ─────────────────────────

def test_der_brief_bleibt_gruen_trotz_fremder_anlage(brief, tmp_path):
    """Die Forderung aus dem Issue: `check` auf Seite 1 weiterhin grün.

    Die Anlage trägt keine Kopfzeile mit Betreff, keine Seitenzählung und eine
    nicht eingebettete Helvetica. Alle drei sind Prüfungen, die auf sie nie
    gemünzt waren.
    """
    pdf, form = brief
    vorher = geometrie.pruefe(pdf, form)
    assert vorher.ok

    anlagen.haenge_an(pdf, [_ohne_deklaration(tmp_path / "fremd.pdf")])
    nachher = geometrie.pruefe(pdf, form)
    gescheitert = [p["name"] for p in nachher.als_dict()["pruefungen"] if not p["bestanden"]]
    assert nachher.ok, f"Der Brief fällt wegen seiner Anlage durch: {gescheitert}"


def test_ohne_den_vermerk_faellt_die_anlage_durch(brief, tmp_path):
    """Gegenprobe zum Vermerk: Er ist es, der die Grenze zieht.

    Ohne `/falzmarke_Briefseiten` misst `verify` die Anlage mit — und genau das
    passierte, bevor der Vermerk geschrieben wurde.
    """
    from pypdf import PdfReader, PdfWriter

    pdf, form = brief
    anlagen.haenge_an(pdf, [_ohne_deklaration(tmp_path / "fremd.pdf")])

    ohne = tmp_path / "ohne-vermerk.pdf"
    schreiber = PdfWriter(clone_from=PdfReader(str(pdf)))
    schreiber.add_metadata({"/falzmarke_Briefseiten": ""})
    with ohne.open("wb") as datei:
        schreiber.write(datei)

    assert not geometrie.pruefe(ohne, form).ok, (
        "Ohne den Vermerk besteht die Prüfung trotzdem — dann zieht er keine Grenze "
        "und der Test darüber belegt nichts."
    )


# ── Der Weg über das Frontmatter ────────────────────────────────────────────

def test_anlagen_dateien_im_frontmatter(tmp_path):
    quelle = tmp_path / "brief.md"
    _ohne_deklaration(tmp_path / "rechnung.pdf")
    quelle.write_text(
        BRIEF.format(anlagen="anlagen_dateien:\n  - rechnung.pdf\n"), encoding="utf-8")

    berichte: list = []
    pdf, form = falzmarke.rendere(quelle, tmp_path / "aus.pdf", anlagen_bericht=berichte)

    assert len(berichte) == 1 and berichte[0]["seiten_nachher"] == 2
    assert geometrie.pruefe(pdf, form).ok


def test_pfade_sind_relativ_zur_briefdatei(tmp_path):
    """Ein Brief samt Anlagen ist ein Ordner, den man verschieben können muss."""
    ordner = tmp_path / "vorgang"
    ordner.mkdir()
    _ohne_deklaration(ordner / "rechnung.pdf")
    quelle = ordner / "brief.md"
    quelle.write_text(
        BRIEF.format(anlagen="anlagen_dateien:\n  - rechnung.pdf\n"), encoding="utf-8")

    pdf, _ = falzmarke.rendere(quelle, tmp_path / "aus.pdf")
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf)).pages) == 2


@pytest.mark.parametrize("datei, erwartet", [
    ("gibt-es-nicht.pdf", "gibt es nicht"),
    ("brief.md", "keine PDF-Datei"),
])
def test_fehlende_und_falsche_anlagen_werden_benannt(tmp_path, datei, erwartet):
    quelle = tmp_path / "brief.md"
    quelle.write_text(
        BRIEF.format(anlagen=f"anlagen_dateien:\n  - {datei}\n"), encoding="utf-8")
    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        falzmarke.rendere(quelle, tmp_path / "aus.pdf")
    assert erwartet in str(fehler.value)


def test_der_anlagenvermerk_bleibt_unabhaengig(tmp_path):
    """`anlagen:` nennt sie im Brief, `anlagen_dateien:` legt sie bei.

    Beides ist getrennt: Wer eine Anlage per Post beilegt, nennt sie im Vermerk,
    ohne dass eine Datei existiert.
    """
    import pdfplumber

    quelle = tmp_path / "brief.md"
    quelle.write_text(
        BRIEF.format(anlagen="anlagen:\n  - Rechnung 2026-0815\n"), encoding="utf-8")
    pdf, _ = falzmarke.rendere(quelle, tmp_path / "aus.pdf")
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf)).pages) == 1, "ein Vermerk darf keine Seite anhängen"
    with pdfplumber.open(str(pdf)) as dokument:
        assert "Rechnung 2026-0815" in (dokument.pages[0].extract_text() or "")


def test_englischer_mehrseiter_mit_anlage(tmp_path):
    """Die Kreuzung beider Neuerungen: Sprache (#11) und Anlagen (#1).

    Hier treffen sich zwei Zahlen, die leicht verwechselt werden: die Seiten der
    Datei und die Seiten des Briefes. Die Fusszeile des Briefes zaehlt nur ihn
    selbst („Page 2 of 2"), die Datei hat mit Anlage aber drei Seiten.

    Genau daran ist der Merge von #11 und #55 gescheitert, ohne dass git einen
    Konflikt gemeldet haette: Beide Aenderungen standen textuell nebeneinander,
    aber das Sprachmuster suchte weiter nach „Page 2 of 3“. Kein Konfliktmarker
    zeigt so etwas an — nur ein Test, der beide Wege zugleich geht.
    """
    fueller = "\n\n".join(f"Filler paragraph {n} to force a second page." for n in range(1, 30))
    _ohne_deklaration(tmp_path / "invoice.pdf")
    quelle = tmp_path / "brief.md"
    quelle.write_text(
        BRIEF.format(anlagen="sprache: en\nanlagen_dateien:\n  - invoice.pdf\n") + fueller,
        encoding="utf-8")

    berichte: list = []
    pdf, form = falzmarke.rendere(quelle, tmp_path / "aus.pdf", anlagen_bericht=berichte)

    from pypdf import PdfReader
    assert len(PdfReader(str(pdf)).pages) == 3, "zwei Briefseiten plus eine Anlage"
    assert berichte[0]["seiten_vorher"] == 2

    bericht = geometrie.pruefe(pdf, form)
    gescheitert = [p["name"] for p in bericht.als_dict()["pruefungen"] if not p["bestanden"]]
    assert bericht.ok, f"englischer Mehrseiter mit Anlage fällt durch: {gescheitert}"
