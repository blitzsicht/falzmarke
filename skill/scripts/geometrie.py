#!/usr/bin/env python3
"""Vermisst ein fertiges PDF gegen die Maße aus DIN 5008:2020.

Die Sollwerte stehen ausschließlich hier und in references/din5008.md.
Sowohl `normbrief.py check` als auch die Testsuite lesen sie von hier —
ein Layoutfehler kann sich damit nicht in zwei Quellen unterschiedlich
niederschlagen.

Alle Maße in Millimetern, Ursprung oben links.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PT_PRO_MM = 72.0 / 25.4


def mm(punkte: float) -> float:
    return punkte / PT_PRO_MM


def pt(millimeter: float) -> float:
    return millimeter * PT_PRO_MM


# Gemessen wird die Glyph-Box, gesetzt wird die Zeilenoberkante. Die Glyph-Box
# beginnt beim Ascender und liegt deshalb hoeher — und zwar je nach Schrift
# unterschiedlich weit: 0,25 em bei Libertinus Serif, 0,34 em bei Source Sans 3.
# Eine feste Toleranz in Millimetern wuerde deshalb entweder Fehlalarme
# erzeugen oder bei kleiner Schrift zu grob werden.
GLYPH_VERSATZ_EM = 0.45


def glyph_versatz(groesse_pt: float) -> float:
    """Wie weit die Glyph-Box hoechstens ueber der Zeilenoberkante liegt (mm)."""
    return mm(GLYPH_VERSATZ_EM * groesse_pt)


# ── Sollwerte ───────────────────────────────────────────────────────────────

FORM = {
    "A": {
        "kopfhoehe": 27.0,
        "falzmarke_1": 87.0,
        "falzmarke_2": 192.0,
        "ruecksende_zone": (27.0, 32.0),
        "vermerk_zone": (32.0, 44.7),
        "anschrift_zone": (44.7, 72.0),
        "infoblock_oben": 32.0,
        "betreff_standard": 80.46,
    },
    "B": {
        "kopfhoehe": 45.0,
        "falzmarke_1": 105.0,
        "falzmarke_2": 210.0,
        "ruecksende_zone": (45.0, 50.0),
        "vermerk_zone": (50.0, 62.7),
        "anschrift_zone": (62.7, 90.0),
        "infoblock_oben": 50.0,
        "betreff_standard": 98.46,
    },
}

SEITE_BREITE = 210.0
SEITE_HOEHE = 297.0
LOCHMARKE = 148.5
RAND_LINKS = 25.0
RAND_RECHTS = 190.0          # 210 - 20
INFOBLOCK_X = 125.0
INFOBLOCK_X_RECHTS = 200.0
ANSCHRIFT_X_RECHTS = 105.0   # 20 mm + 85 mm Fensterbreite
MARKE_X_MAX = 20.0           # Marken liegen im Heftrand
ZEILE = 4.2333
FUSS_MINDESTRAND = 8.0       # mm zwischen unterstem Text und Blattkante
LEERZEILEN_VOR_BETREFF = 2 * ZEILE   # 8,46 mm
INFOBLOCK_MINDESTHOEHE = 40.0


@dataclass
class Pruefung:
    name: str
    soll: str
    ist: str
    toleranz: str
    bestanden: bool


@dataclass
class Bericht:
    pruefungen: list[Pruefung] = field(default_factory=list)

    def add(self, name, soll, ist, toleranz, bestanden) -> None:
        self.pruefungen.append(Pruefung(name, str(soll), str(ist), str(toleranz), bestanden))

    def wert(self, name, ist: float, soll: float, tol: float) -> None:
        self.add(name, f"{soll:.2f}", f"{ist:.2f}", f"±{tol}", abs(ist - soll) <= tol)

    def spanne(self, name, ist: float, unten: float, oben: float, tol: float = 0.0) -> None:
        self.add(
            name, f"{unten:.2f}–{oben:.2f}", f"{ist:.2f}", f"±{tol}",
            unten - tol <= ist <= oben + tol,
        )

    def spanne_asymmetrisch(self, name, ist: float, soll: float, unten: float, oben: float) -> None:
        self.add(
            name, f"{soll:.2f}", f"{ist:.2f}", f"{unten:+g}/{oben:+g}",
            soll + unten <= ist <= soll + oben,
        )

    def wahr(self, name, bedingung: bool, soll: str, ist: str) -> None:
        self.add(name, soll, ist, "—", bool(bedingung))

    @property
    def ok(self) -> bool:
        return all(p.bestanden for p in self.pruefungen)

    def als_text(self) -> str:
        zeilen = []
        for p in self.pruefungen:
            marke = "OK  " if p.bestanden else "FEHL"
            zeilen.append(f"{marke}  {p.name}: soll {p.soll} ist {p.ist} (tol {p.toleranz})")
        return "\n".join(zeilen)

    def als_dict(self) -> dict:
        return {
            "ok": self.ok,
            "pruefungen": [vars(p) for p in self.pruefungen],
        }


# ── Messung ─────────────────────────────────────────────────────────────────

@dataclass
class Span:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    groesse: float
    fett: bool
    font: str


def _spans(seite) -> list[Span]:
    ergebnis = []
    for block in seite.get_text("dict")["blocks"]:
        for zeile in block.get("lines", []):
            for span in zeile["spans"]:
                if not span["text"].strip():
                    continue
                x0, y0, x1, y1 = span["bbox"]
                name = span["font"]
                ergebnis.append(
                    Span(
                        text=span["text"],
                        x0=mm(x0), y0=mm(y0), x1=mm(x1), y1=mm(y1),
                        groesse=span["size"] / PT_PRO_MM * PT_PRO_MM,
                        fett=bool(span["flags"] & 2 ** 4) or "Bold" in name or "Semibold" in name,
                        font=name,
                    )
                )
    return sorted(ergebnis, key=lambda s: (round(s.y0, 1), s.x0))


def _marken(seite) -> list[tuple[float, float, float]]:
    """Waagerechte Striche im Heftrand als (y, x_start, x_ende)."""
    treffer = []
    for zeichnung in seite.get_drawings():
        for element in zeichnung["items"]:
            if element[0] != "l":
                continue
            p1, p2 = element[1], element[2]
            if abs(p1.y - p2.y) > 0.5:          # nicht waagerecht
                continue
            x_start, x_ende = sorted((mm(p1.x), mm(p2.x)))
            if x_ende > MARKE_X_MAX:            # nicht im Heftrand
                continue
            treffer.append((mm(p1.y), x_start, x_ende))
    return sorted(treffer)


def _zeilen_gruppieren(spans: list[Span], toleranz: float = 0.6) -> list[list[Span]]:
    zeilen: list[list[Span]] = []
    for span in spans:
        if zeilen and abs(zeilen[-1][0].y0 - span.y0) <= toleranz:
            zeilen[-1].append(span)
        else:
            zeilen.append([span])
    return zeilen


def pruefe(pdf_pfad: Path, form: str) -> Bericht:
    import pymupdf as fitz

    soll = FORM[form]
    bericht = Bericht()
    dokument = fitz.open(pdf_pfad)
    seite = dokument[0]

    # Seitengröße
    bericht.wert("Seitenbreite", mm(seite.rect.width), SEITE_BREITE, 0.1)
    bericht.wert("Seitenhöhe", mm(seite.rect.height), SEITE_HOEHE, 0.1)

    # Falz- und Lochmarken
    marken = _marken(seite)
    for bezeichnung, sollwert in (
        ("Falzmarke 1", soll["falzmarke_1"]),
        ("Falzmarke 2", soll["falzmarke_2"]),
        ("Lochmarke", LOCHMARKE),
    ):
        passende = [m for m in marken if abs(m[0] - sollwert) <= 2.0]
        if passende:
            y, _, x_ende = passende[0]
            bericht.wert(f"{bezeichnung}, y", y, sollwert, 0.3)
            bericht.wahr(
                f"{bezeichnung}, im Heftrand", x_ende <= MARKE_X_MAX,
                f"x-Ende ≤ {MARKE_X_MAX}", f"{x_ende:.2f}",
            )
        else:
            bericht.wahr(f"{bezeichnung}, y", False, f"{sollwert} mm", "nicht gefunden")

    spans = _spans(seite)

    # Rücksendeangabe: kleinste Schrift in der 5-mm-Zone über dem Anschriftfeld
    zone_oben, zone_unten = soll["ruecksende_zone"]
    ruecksende = [s for s in spans if zone_oben - 1.0 <= s.y0 <= zone_unten and s.x0 < 60]
    if ruecksende:
        r = ruecksende[0]
        bericht.spanne("Rücksendeangabe, y-Oberkante", r.y0, zone_oben, zone_unten, 0.8)
        bericht.wert("Rücksendeangabe, x", r.x0, RAND_LINKS, 0.3)
        bericht.wahr(
            "Rücksendeangabe, Schriftgröße 7–8 pt", 6.5 <= r.groesse <= 8.5,
            "7–8 pt", f"{r.groesse:.1f} pt",
        )
    else:
        bericht.wahr("Rücksendeangabe vorhanden", False, "1 Zeile", "nicht gefunden")

    # Anschrift
    a_oben, a_unten = soll["anschrift_zone"]
    anschrift_spans = [
        s for s in spans
        if a_oben - 1.5 <= s.y0 <= a_unten and s.x0 < ANSCHRIFT_X_RECHTS and s.groesse >= 9.0
    ]
    anschrift_zeilen = _zeilen_gruppieren(anschrift_spans)
    if anschrift_zeilen:
        erste = anschrift_zeilen[0][0]
        letzte = max(s.y1 for s in anschrift_zeilen[-1])
        versatz = glyph_versatz(erste.groesse)
        bericht.add(
            "Anschrift, erste Zeile y", f"≥ {a_oben}", f"{erste.y0:.2f}",
            f"-{versatz:.2f}", erste.y0 >= a_oben - versatz,
        )
        bericht.add(
            "Anschrift, letzte Zeile Unterkante", f"≤ {a_unten}", f"{letzte:.2f}", "0",
            letzte <= a_unten,
        )
        bericht.wert("Anschrift, x-links", erste.x0, RAND_LINKS, 0.3)
        bericht.add(
            "Anschrift, Zeilenzahl", "≤ 6", str(len(anschrift_zeilen)), "—",
            len(anschrift_zeilen) <= 6,
        )
    else:
        bericht.wahr("Anschrift vorhanden", False, "1–6 Zeilen", "nicht gefunden")

    # Informationsblock
    # Erst unterhalb der Kopfhöhe suchen — darüber steht der Briefkopf,
    # der ebenfalls rechtsbündig gesetzt sein darf.
    info_spans = [
        s for s in spans
        if s.x0 >= INFOBLOCK_X - 5 and soll["kopfhoehe"] < s.y0 < 150
    ]
    infoblock_unterkante = soll["kopfhoehe"] + 5.0 + INFOBLOCK_MINDESTHOEHE
    if info_spans:
        links = min(s.x0 for s in info_spans)
        rechts = max(s.x1 for s in info_spans)
        oben = min(s.y0 for s in info_spans)
        gemessene_unterkante = max(s.y1 for s in info_spans)
        bericht.wert("Infoblock, x-links", links, INFOBLOCK_X, 0.5)
        bericht.add(
            "Infoblock, x-rechts", f"≤ {INFOBLOCK_X_RECHTS}", f"{rechts:.2f}", "—",
            rechts <= INFOBLOCK_X_RECHTS,
        )
        bericht.wert("Infoblock, y-Oberkante", oben, soll["infoblock_oben"], 0.8)
        infoblock_unterkante = max(infoblock_unterkante, gemessene_unterkante)

    # Betreff: erster fetter Span unterhalb des Anschriftfelds
    betreff = next((s for s in spans if s.fett and s.y0 > a_unten - 5), None)
    if betreff is not None:
        erwartet = max(soll["kopfhoehe"] + 45.0, infoblock_unterkante) + LEERZEILEN_VOR_BETREFF
        # Gemessen wird die Glyph-Box, gesetzt wird die Zeilenoberkante. Die
        # Glyph-Box beginnt beim Ascender und liegt deshalb systematisch etwas
        # hoeher (0,83 mm bei 10 pt, 0,97 mm bei 11 pt). Nach oben deckt das
        # Fenster diesen Versatz ab, nach unten bleibt es eng: ein zu tief
        # gesetzter Betreff laeuft in den Text und ist der teure Fehler.
        bericht.spanne_asymmetrisch(
            "Betreff, y-Oberkante", betreff.y0, erwartet,
            -glyph_versatz(betreff.groesse), 0.6,
        )
        bericht.wert("Betreff, x-links", betreff.x0, RAND_LINKS, 0.3)
        bericht.wahr(
            "Betreff ohne Leitwort", not betreff.text.strip().lower().startswith("betreff"),
            "kein 'Betreff:'", betreff.text[:30],
        )
        bericht.wahr(
            "Betreff ohne Schlusspunkt", not betreff.text.strip().endswith("."),
            "kein Punkt am Ende", betreff.text[-12:],
        )
    else:
        bericht.wahr("Betreff vorhanden", False, "fett gesetzt", "nicht gefunden")

    # Abstaende statt Absolutpositionen. Der Ascender-Versatz kuerzt sich heraus,
    # weil er beide Messpunkte gleich betrifft — diese Pruefungen sind deshalb
    # schaerfer als die absoluten oben und gelten fuer jede Schrift.
    if betreff is not None and anschrift_zeilen:
        abstand = betreff.y0 - anschrift_zeilen[0][0].y0
        soll_abstand = (
            max(soll["kopfhoehe"] + 45.0, infoblock_unterkante)
            + LEERZEILEN_VOR_BETREFF - a_oben
        )
        bericht.wert("Abstand Anschrift → Betreff", abstand, soll_abstand, 0.3)

    anrede = next((s for s in spans if betreff is not None and s.y0 > betreff.y1), None)
    if betreff is not None and anrede is not None:
        # Konstruktiv exakt: beide Messpunkte tragen denselben Glyph-Versatz,
        # der sich in der Differenz heraushebt. Deshalb enge Toleranz.
        bericht.wert(
            "Abstand Betreff → Anrede (2 Leerzeilen)",
            anrede.y0 - betreff.y0, 3 * ZEILE, 0.2,
        )

    # Textblock
    body_spans = [s for s in spans if betreff is not None and s.y0 > betreff.y1 and s.y1 < 250]
    if body_spans:
        bericht.wert("Textblock, x-links", min(s.x0 for s in body_spans), RAND_LINKS, 0.3)
        bericht.add(
            "Textblock, x-rechts", f"≤ {RAND_RECHTS}",
            f"{max(s.x1 for s in body_spans):.2f}", "±0,3",
            max(s.x1 for s in body_spans) <= RAND_RECHTS + 0.3,
        )

    # Nichts darf aus dem Blatt laufen. Der Fall ist real: eine vierzeilige
    # Fußzeile wächst nach unten und wurde beim 20-mm-Standardrand
    # abgeschnitten, ohne dass Typst gewarnt hätte.
    unterster = max((s.y1 for s in spans), default=0.0)
    bericht.add(
        "Unterster Text, Abstand zur Blattkante", f"≥ {FUSS_MINDESTRAND}",
        f"{SEITE_HOEHE - unterster:.2f}", "—",
        SEITE_HOEHE - unterster >= FUSS_MINDESTRAND,
    )

    # Schriften eingebettet
    nicht_eingebettet = [f for f in seite.get_fonts(full=True) if f[3] == ""]
    bericht.wahr(
        "Schriften eingebettet", not nicht_eingebettet, "alle eingebettet",
        "fehlend: " + ", ".join(f[3] for f in nicht_eingebettet) if nicht_eingebettet else "alle",
    )

    # Folgeseiten
    if dokument.page_count > 1:
        zweite = dokument[1]
        text = zweite.get_text()
        bericht.wahr(
            "Seite 2: Seitenzahl", f"Seite 2 von {dokument.page_count}" in text,
            f"'Seite 2 von {dokument.page_count}'",
            "vorhanden" if f"Seite 2 von {dokument.page_count}" in text else "fehlt",
        )
        spans_2 = _spans(zweite)
        # Auf Folgeseiten entfaellt das Anschriftfeld. Nachweisbar ist das nicht
        # daran, dass die Zone leer waere — dort steht auf Seite 2 normaler
        # Fliesstext —, sondern daran, dass der Text oben beginnt statt erst
        # unterhalb des Feldes, und dass keine Ruecksendeangabe wiederholt wird.
        fliesstext = [s for s in spans_2 if s.y0 > 20.0]
        beginn = min((s.y0 for s in fliesstext), default=999.0)
        bericht.add(
            "Seite 2: Textbeginn", f"≤ {soll['kopfhoehe']}", f"{beginn:.2f}", "—",
            beginn <= soll["kopfhoehe"],
        )
        ruecksende_wiederholt = [
            s for s in spans_2 if s.groesse <= 8.0 and zone_oben <= s.y0 <= zone_unten
        ]
        bericht.wahr(
            "Seite 2: keine Rücksendeangabe", not ruecksende_wiederholt, "keine",
            f"{len(ruecksende_wiederholt)} gefunden",
        )
        kopfzeile = [s for s in spans_2 if s.y0 <= 20.0]
        bericht.wahr(
            "Seite 2: Kopfzeile", bool(kopfzeile), "Betreff und Datum",
            " ".join(s.text for s in kopfzeile)[:40] if kopfzeile else "fehlt",
        )

    dokument.close()
    return bericht


def pdfa_geprueft(pdf_pfad: Path) -> tuple[bool, str]:
    """Liest die XMP-Metadaten und prüft auf PDF/A-2b."""
    import pymupdf as fitz

    dokument = fitz.open(pdf_pfad)
    xmp = dokument.get_xml_metadata() or ""
    dokument.close()
    teil_ok = "pdfaid:part>2" in xmp.replace(" ", "") or 'pdfaid:part="2"' in xmp
    konformitaet_ok = "pdfaid:conformance>B" in xmp.replace(" ", "") or 'pdfaid:conformance="B"' in xmp
    return (teil_ok and konformitaet_ok), xmp[:200]
