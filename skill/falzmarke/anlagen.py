"""Anlagen-PDFs hinten an den Brief hängen — ohne dabei zu lügen.

Der Anlagenvermerk im Brief nennt die Anlagen; dieses Modul legt sie bei. Beides
ist unabhängig: Wer `anlagen:` schreibt, bekommt den Vermerk, wer
`anlagen_dateien:` schreibt, bekommt die Seiten, und wer beides will, schreibt
beides.

DIE PDF/A-FRAGE

Ein Merge erhält die XMP-Metadaten des Briefes — die Datei behauptet danach
weiter PDF/A-2b, gleichgültig, was in der Anlage steckt. Gemessen am 26.08.2026
mit veraPDF:

    Brief allein                                    PASS 2b
    Brief + Anlage aus Typst (Fonts eingebettet)    PASS 2b
    Brief + Anlage mit nicht eingebetteter Schrift  FAIL 2b  — XMP sagt weiter 2b

Der letzte Fall ist der teure: eine Datei, die PDF/A-2b behauptet und es nicht
ist. Wer sie ins Archiv legt, merkt es erst, wenn die Schrift fehlt.

falzmarke hat die Anlage nicht gesetzt und kann ihre Konformität nicht prüfen —
das kann nur ein Prüfwerkzeug wie veraPDF, und das liegt nicht auf jedem
Rechner. Was hier ohne fremdes Werkzeug feststellbar ist, ist die **Deklaration**
der Anlage. Genau daran richtet sich dieses Modul aus, wie
scripts/pdf_konformitaet.py auch:

    alle Anlagen deklarieren PDF/A       Kennzeichnung bleibt, Hinweis auf veraPDF
    eine Anlage tut es nicht             Kennzeichnung wird entfernt, mit Namen

Die Deklaration ist kein Beleg für Konformität — sie ist die Aussage, die im
Umlauf ist. Eine Anlage, die nichts behauptet, ist mit Sicherheit kein PDF/A;
eine, die es behauptet, ist es wahrscheinlich. Auf dieser Grundlage die
Kennzeichnung zu **entfernen** ist sicher; sie stehen zu lassen bleibt eine
Aussage über die Anlage, nicht über die Prüfung. Deshalb der Hinweis.

Still durchgehen lassen wäre in beiden Richtungen das Schlechteste.
"""

from __future__ import annotations

import re
from pathlib import Path

# pdfaid:part steht im XMP entweder als Attribut oder als Element.
PDFA_TEIL = re.compile(rb"pdfaid:part\s*[>=]\s*[\"']?\s*(\d)")
PDFA_STUFE = re.compile(rb"pdfaid:conformance\s*[>=]\s*[\"']?\s*([A-Za-z])")


class AnlagenFehler(ValueError):
    """Eine Anlage fehlt, ist keine PDF oder lässt sich nicht lesen."""


def deklaration(pdf: Path) -> str | None:
    """Was die Datei über sich selbst sagt — „2b“, „3b“ oder nichts.

    Gelesen wird das XMP, nicht der Inhalt: Diese Funktion beantwortet die
    Frage „behauptet die Datei, PDF/A zu sein?“, nicht „ist sie es?“.
    """
    from pypdf import PdfReader

    try:
        xmp = PdfReader(str(pdf)).xmp_metadata
    except Exception as fehler:                                   # noqa: BLE001
        raise AnlagenFehler(f"{pdf.name} lässt sich nicht lesen: {fehler}") from None
    if xmp is None:
        return None
    roh = bytes(xmp.stream.get_data())
    teil = PDFA_TEIL.search(roh)
    if not teil:
        return None
    stufe = PDFA_STUFE.search(roh)
    return teil.group(1).decode() + (stufe.group(1).decode().lower() if stufe else "")


def loese_auf(angaben, brief_pfad: Path) -> list[Path]:
    """Dateinamen aus dem Frontmatter zu Pfaden, relativ zur Briefdatei.

    Relativ zum Brief und nicht zum Arbeitsverzeichnis: Ein Brief samt seiner
    Anlagen ist ein Ordner, den man verschieben können muss, ohne dass die
    Verweise brechen.
    """
    pfade = []
    for angabe in angaben:
        pfad = Path(str(angabe))
        if not pfad.is_absolute():
            pfad = (brief_pfad.parent / pfad).resolve()
        if not pfad.is_file():
            raise AnlagenFehler(
                f"anlagen_dateien: {angabe} gibt es nicht.\n"
                f"        Gesucht unter: {pfad}\n"
                "        Pfade sind relativ zur Briefdatei."
            )
        if pfad.suffix.lower() != ".pdf":
            raise AnlagenFehler(
                f"anlagen_dateien: {angabe} ist keine PDF-Datei.\n"
                "        Angehängt werden nur PDFs — andere Formate vorher umwandeln."
            )
        pfade.append(pfad)
    return pfade


def haenge_an(pdf: Path, anlagen: list[Path]) -> dict:
    """Hängt die Anlagen hinten an und richtet die PDF/A-Kennzeichnung danach aus.

    Gibt einen Bericht zurück: wie viele Seiten dazukamen, welche Anlage was
    deklariert, und ob die Kennzeichnung geblieben oder gefallen ist. Der
    Aufrufer zeigt ihn an — was hier still geschähe, fiele niemandem auf.
    """
    from pypdf import PdfReader, PdfWriter

    eigene = deklaration(pdf)
    leser = PdfReader(str(pdf))
    seiten_vorher = len(leser.pages)

    # clone_from statt add_page für den Brief: Es erhält Struktur und XMP.
    # Ein nackter Merge verliert beides — gemessen, siehe Modul-Docstring.
    schreiber = PdfWriter(clone_from=leser)

    ohne_deklaration = []
    je_anlage = []
    for anlage in anlagen:
        sagt = deklaration(anlage)
        je_anlage.append({"datei": anlage.name, "deklariert": sagt})
        if sagt is None:
            ohne_deklaration.append(anlage.name)
        for seite in PdfReader(str(anlage)).pages:
            schreiber.add_page(seite)

    kennzeichnung_bleibt = eigene is not None and not ohne_deklaration
    if eigene is not None and not kennzeichnung_bleibt:
        _entferne_pdfa_kennzeichnung(schreiber)

    # Damit ein spaeteres `verify` weiss, wo der Brief endet: Ohne diesen
    # Vermerk wuerde die Anlage nach Briefregeln gemessen und faellt dann durch
    # Pruefungen, die auf sie nie gemuenzt waren.
    schreiber.add_metadata({"/falzmarke_Briefseiten": str(seiten_vorher)})

    ziel = pdf.with_suffix(".anlagen.pdf")
    with ziel.open("wb") as datei:
        schreiber.write(datei)
    ziel.replace(pdf)

    return {
        "seiten_vorher": seiten_vorher,
        "seiten_nachher": len(PdfReader(str(pdf)).pages),
        "anlagen": je_anlage,
        "pdfa_vorher": eigene,
        "pdfa_nachher": deklaration(pdf),
        "ohne_deklaration": ohne_deklaration,
    }


def _entferne_pdfa_kennzeichnung(schreiber) -> None:
    """Streicht pdfaid aus dem XMP — der Rest der Metadaten bleibt stehen.

    Nicht das ganze XMP wegwerfen: Titel, Autor und der Herkunftsvermerk sind
    weiter richtig. Falsch wird allein die Aussage „dies ist PDF/A“.
    """
    from pypdf.generic import ByteStringObject

    wurzel = schreiber._root_object
    if "/Metadata" not in wurzel:
        return
    strom = wurzel["/Metadata"].get_object()
    roh = bytes(strom.get_data()).decode("utf-8", "replace")

    # Sowohl die Attribut- als auch die Elementschreibweise.
    ohne = re.sub(r'\s*pdfaid:(part|conformance)\s*=\s*"[^"]*"', "", roh)
    ohne = re.sub(r"\s*<pdfaid:(part|conformance)>.*?</pdfaid:\1>", "", ohne, flags=re.S)
    # set_data pflegt /Length selbst mit.
    strom.set_data(ByteStringObject(ohne.encode("utf-8")))
