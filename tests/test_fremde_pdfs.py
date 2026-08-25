"""`verify` prüft fremde PDFs — was dabei hereinkommt, ist nicht immer eines.

Zwei Funde vom 25.08.2026, beide an v0.3.1 gemessen:

1. Eine Schrift **ohne** `/FontDescriptor` wurde übersprungen und galt damit als
   eingebettet. Der Deskriptor ist aber der einzige Ort, an dem eine FontFile
   stehen kann — fehlt er, ist die Schrift garantiert nicht eingebettet. Genau
   so sehen die 14 PDF-Standardschriften aus. Ein fremdes PDF, das nur
   Helvetica benutzte, kam ohne Beanstandung durch.
2. Eine leere Datei, ein abgebrochener Download oder ein umbenanntes
   Word-Dokument endeten im Python-Traceback statt in einer Meldung.

Die PDFs hier werden von Hand gebaut, nicht von falzmarke erzeugt. Das ist der
Punkt: Ein Linter für fremde Dateien lässt sich nicht mit den eigenen prüfen.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from falzmarke import cli as falzmarke
from falzmarke import geometrie
from conftest import REPO


def _pdf(objekte: list[bytes]) -> bytes:
    """Setzt ein PDF aus fertigen Objektkörpern zusammen, mit gültiger xref."""
    aus = bytearray(b"%PDF-1.7\n")
    versatz = []
    for nummer, koerper in enumerate(objekte, 1):
        versatz.append(len(aus))
        aus += f"{nummer} 0 obj\n".encode() + koerper + b"\nendobj\n"
    start = len(aus)
    aus += f"xref\n0 {len(objekte) + 1}\n".encode() + b"0000000000 65535 f \n"
    for stelle in versatz:
        aus += f"{stelle:010d} 00000 n \n".encode()
    aus += (f"trailer\n<< /Size {len(objekte) + 1} /Root 1 0 R >>\n"
            f"startxref\n{start}\n%%EOF\n").encode()
    return bytes(aus)


def _seite_mit_schrift(schrift_objekt: bytes) -> bytes:
    inhalt = b"BT /F1 24 Tf 72 700 Td (Probe) Tj ET"
    return _pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.276 841.89] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        schrift_objekt,
        b"<< /Length " + str(len(inhalt)).encode() + b" >>\nstream\n" + inhalt + b"\nendstream",
    ])


# ── Fund 1: Schriften ohne Deskriptor ───────────────────────────────────────

def test_standardschrift_ohne_deskriptor_wird_gemeldet(tmp_path):
    """Helvetica ohne `/FontDescriptor` ist nie eingebettet."""
    pdf = tmp_path / "base14.pdf"
    pdf.write_bytes(_seite_mit_schrift(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    assert geometrie._nicht_eingebettete_schriften(pdf) == ["/Helvetica"]


def test_type3_wird_nicht_gemeldet(tmp_path):
    """Gegenprobe zur Ausnahme: Type-3-Glyphen stehen als Zeichenprogramme im
    PDF selbst. Sie brauchen keine FontFile und sind trotzdem mitgeliefert —
    eine Meldung wäre hier falsch."""
    pdf = tmp_path / "type3.pdf"
    pdf.write_bytes(_seite_mit_schrift(
        b"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 1 1] "
        b"/FontMatrix [0.001 0 0 0.001 0 0] /CharProcs << >> "
        b"/Encoding << /Type /Encoding >> /FirstChar 0 /LastChar 0 /Widths [0] >>"))
    assert geometrie._nicht_eingebettete_schriften(pdf) == []


def test_eigenes_pdf_wird_nicht_faelschlich_gemeldet(tmp_path):
    """Die zweite Gegenprobe: Ein Wächter, der alles meldet, ist unbrauchbar.
    falzmarke bettet seine Schriften ein — hier darf nichts kommen."""
    pdf, _ = falzmarke.rendere(
        REPO / "examples" / "brief-form-b.md", tmp_path / "eigen.pdf")
    assert geometrie._nicht_eingebettete_schriften(pdf) == []


# ── Fund 2: unlesbare Dateien ───────────────────────────────────────────────

@pytest.fixture
def kaputte_dateien(tmp_path):
    echt = _seite_mit_schrift(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    dateien = {
        "leer": b"",
        "kein-pdf": "Das ist ein Brief, kein PDF.\n".encode("utf-8"),
        "abgeschnitten": echt[: len(echt) // 2],
        "kaputter-startxref": echt.replace(b"startxref", b"startxrefX"),
        "ohne-seiten": (b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
                        b"trailer\n<< /Size 3 /Root 1 0 R >>\n%%EOF\n"),
    }
    for name, daten in dateien.items():
        (tmp_path / f"{name}.pdf").write_bytes(daten)
    return tmp_path, sorted(dateien)


def test_unlesbare_datei_wirft_pdfunlesbar(kaputte_dateien):
    ordner, namen = kaputte_dateien
    for name in namen:
        with pytest.raises(geometrie.PdfUnlesbar):
            geometrie.pruefe(ordner / f"{name}.pdf", "B")


def test_unlesbare_datei_auch_bei_der_formerkennung(kaputte_dateien):
    """`verify` ohne `--form` erkennt die Form selbst — derselbe Weg, dieselbe
    Datei, und bis v0.3.1 derselbe Traceback."""
    ordner, _ = kaputte_dateien
    with pytest.raises(geometrie.PdfUnlesbar):
        geometrie.erkenne_form(ordner / "leer.pdf")


def test_cli_meldet_statt_abzustuerzen(kaputte_dateien):
    """Am Verhalten gemessen, nicht an der Ausnahme: Der Benutzer sieht eine
    Zeile und Rückgabecode 1, keinen Stapelauszug."""
    ordner, namen = kaputte_dateien
    for name in namen:
        lauf = subprocess.run(
            [sys.executable, str(REPO / "skill" / "scripts" / "falzmarke.py"),
             "verify", str(ordner / f"{name}.pdf"), "--form", "B"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        ausgabe = lauf.stdout + lauf.stderr
        assert "Traceback" not in ausgabe, f"{name}: {ausgabe[-300:]}"
        assert lauf.returncode == falzmarke.EXIT_EINGABE, f"{name}: Code {lauf.returncode}"
        assert "FEHLER" in ausgabe, f"{name}: {ausgabe!r}"


def test_die_pruefung_wuerde_ein_gueltiges_pdf_durchlassen(tmp_path):
    """Gegenprobe: Ohne sie belegen die Tests oben nur, dass irgendetwas wirft."""
    pdf = tmp_path / "gueltig.pdf"
    pdf.write_bytes(_seite_mit_schrift(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    bericht = geometrie.pruefe(pdf, "B")          # wirft nicht
    assert bericht.pruefungen                      # es wurde tatsächlich gemessen
    assert not bericht.ok                          # ein Blatt ohne Falzmarken fällt durch
