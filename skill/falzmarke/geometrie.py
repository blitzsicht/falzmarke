#!/usr/bin/env python3
"""Vermisst ein fertiges PDF gegen die Maße aus DIN 5008:2020.

Gemessen wird mit pdfplumber (MIT) und pypdf (BSD-3). Die frühere Messung lief
über PyMuPDF — das ist AGPL-3.0 oder kommerziell und hätte jede Firma, die
falzmarke einbaut, in die AGPL gezwungen. Der Wechsel ist außerdem genauer:
pdfplumber liefert die Zeilenoberkante statt der Ascender-Box und trifft die
Sollwerte auf 0,01 mm (Anschrift 62,69 bei Soll 62,70; Betreff 98,45 bei
98,46), wo PyMuPDF um 0,5 mm danebenlag.

Die Sollwerte stehen ausschließlich hier und in references/din5008.md.
Sowohl `falzmarke.py check` als auch die Testsuite lesen sie von hier —
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

#: Die nutzbare Textbreite. Ein Wort, das allein schon breiter ist, kann nirgends
#: passen — es hat keine Trennstelle, sonst haette Typst es umbrochen.
BREITE_SATZSPIEGEL = RAND_RECHTS - RAND_LINKS

#: Ab wie vielen Zeichen ein wortgetreuer Auszug aus dem Satzspiegel laeuft.
#:
#: Gemessen am 28.08.2026 durch Einschachtelung (tests/fixtures/satzspiegel/
#: README.md): Der Codeblock passt bis 68 Zeichen, ab 69 laeuft er ueber. Er
#: verliert zwei Zeichen gegenueber Inline-Code an seinen Einzug. Der Wert gilt
#: fuer die Festbreitenschrift, die `falzmarke.typ` waehlt.
AUSZUG_ZEICHEN = 68
INFOBLOCK_X = 125.0
INFOBLOCK_X_RECHTS = 200.0
ANSCHRIFT_X_RECHTS = 105.0   # 20 mm + 85 mm Fensterbreite
MARKE_X_MAX = 20.0           # Marken liegen im Heftrand
MARKE_ZUORDNUNG = 25.0       # bis hierhin gilt eine Marke als "diese, verschoben"
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
    #: Was in der EINGABE den Befund verursacht — und was daran zu tun waere.
    #:
    #: `soll/ist/toleranz` beschreibt das Symptom: „190,88 statt hoechstens
    #: 190,00". Damit kann niemand etwas anfangen, der den Brief geschrieben hat
    #: und nicht das Werkzeug. Die Ursache benennt das Element und den Weg
    #: heraus (Issue #145).
    #:
    #: Leer, wo sie sich nicht sicher benennen laesst. Eine geratene Ursache ist
    #: schlechter als keine: Sie schickt den Leser an die falsche Stelle.
    ursache: str = ""


@dataclass
class Bericht:
    pruefungen: list[Pruefung] = field(default_factory=list)
    #: Was gezählt wird. Der Brief misst Maße, die E-Mail-Fassung Eigenschaften
    #: der Datei — der Schlusssatz soll benennen, was tatsächlich geprüft wurde.
    gegenstand: str = "Maße eingehalten"

    def add(self, name, soll, ist, toleranz, bestanden, ursache: str = "") -> None:
        self.pruefungen.append(
            Pruefung(name, str(soll), str(ist), str(toleranz), bestanden, ursache))

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

    def als_text(self, ausfuehrlich: bool = False) -> str:
        """Standard: eine Zeile. Bei Abweichung nur die betroffenen Prüfungen.

        Der ausführliche Bericht hat 30 Zeilen und landete bei jedem Render im
        Kontext des Sprachmodells — das verdrängt den Brief, um den es geht.
        """
        gescheitert = [p for p in self.pruefungen if not p.bestanden]
        zeigen = self.pruefungen if ausfuehrlich else gescheitert
        zeilen = []
        for p in zeigen:
            zeilen.append(
                f"{'OK  ' if p.bestanden else 'FEHL'}  {p.name}: "
                f"soll {p.soll} ist {p.ist} (tol {p.toleranz})")
            # Nur bei einem Befund und nur eingerueckt: Bei einem gruenen Lauf
            # gaebe es nichts zu tun, und der ausfuehrliche Bericht wuerde
            # doppelt so lang — er landet bei jedem Render im Kontext.
            if p.ursache and not p.bestanden:
                zeilen.append(f"        {p.ursache}")
        gesamt = len(self.pruefungen)
        if gescheitert:
            zeilen.append(
                f"verify: {gesamt - len(gescheitert)}/{gesamt} {self.gegenstand}")
        else:
            zeilen.append(f"OK  verify: {gesamt}/{gesamt} {self.gegenstand}")
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
    """Wörter mit Position, Größe und Schriftschnitt.

    pdfplumber liefert Wörter statt Textkästen; das ist für die Messung
    gleichwertig und für die Zeilenbildung sogar direkter.
    """
    ergebnis = []
    for wort in seite.extract_words(extra_attrs=["fontname", "size"], use_text_flow=True):
        if not wort["text"].strip():
            continue
        name = wort["fontname"]
        ergebnis.append(
            Span(
                text=wort["text"],
                x0=mm(wort["x0"]), y0=mm(wort["top"]),
                x1=mm(wort["x1"]), y1=mm(wort["bottom"]),
                groesse=round(wort["size"], 1),
                fett="Bold" in name or "Semibold" in name or "Black" in name,
                font=name,
            )
        )
    return sorted(ergebnis, key=lambda s: (round(s.y0, 1), s.x0))


def _kurz(text: str, laenge: int = 22) -> str:
    """Elementtext für den Bericht, gekürzt aber erkennbar."""
    text = " ".join(text.split())
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def _satzspiegel(dokument, bericht: Bericht, briefseiten: int | None = None) -> None:
    """Kein Text ausserhalb des Satzspiegels — auf JEDER Seite.

    Bis hierher endete die Textmessung auf Seite 1: `seite = dokument.pages[0]`.
    Ein mehrseitiger Brief konnte ab Seite 2 beliebig aus dem Satzspiegel laufen
    und die Pruefung trotzdem bestehen (Issue #35). Genau diese Faelle entstehen
    erst im Fliesstext: lange Ueberschriften, breite Tabellen, Codezeilen ohne
    Trennmoeglichkeit, URLs.

    Gemessen wird ueber ALLE Spans, ohne Ausnahmen fuer Briefkopf oder Fusszeile.
    Das ist keine Nachlaessigkeit, sondern gemessen: In allen neun Beispielen
    liegen saemtliche Spans auf saemtlichen Seiten exakt zwischen 25,00 und
    190,00 mm — Briefkopf und Fusszeile eingeschlossen. Eine Ausnahmeliste waere
    ein zweiter Ort, an dem ein Layoutfehler sich verstecken koennte.

    Der Bericht nennt Seite UND Element: „ausserhalb" allein sagt niemandem, wo
    er suchen soll.
    """
    for nummer, seite in enumerate(dokument.pages[:briefseiten], start=1):
        spans = _spans(seite)
        if not spans:
            continue

        links = min(spans, key=lambda s: s.x0)
        bericht.add(
            f"Seite {nummer}, linker Rand", f"≥ {RAND_LINKS}",
            f"{links.x0:.2f} bei „{_kurz(links.text)}“", "±0,3",
            links.x0 >= RAND_LINKS - 0.3,
        )

        rechts = max(spans, key=lambda s: s.x1)
        haelt = rechts.x1 <= RAND_RECHTS + 0.3
        bericht.add(
            f"Seite {nummer}, rechter Rand", f"≤ {RAND_RECHTS}",
            f"{rechts.x1:.2f} bei „{_kurz(rechts.text)}“", "±0,3",
            haelt,
            ursache="" if haelt else _ursache_ueberlauf(rechts, _tabellenbereiche(seite)),
        )

        unten = max(spans, key=lambda s: s.y1)
        bericht.add(
            f"Seite {nummer}, Abstand zur Blattkante", f"≥ {FUSS_MINDESTRAND}",
            f"{SEITE_HOEHE - unten.y1:.2f} bei „{_kurz(unten.text)}“", "—",
            SEITE_HOEHE - unten.y1 >= FUSS_MINDESTRAND,
        )


#: Die Grundzeile des Satzes: 12 pt. Dieselbe Zahl steht in `falzmarke.typ`
#: als `#let zeile`; `tests/test_raster.py` hält beide zusammen.
GRUNDZEILE = 4.2333

#: Schriftgröße des Briefkörpers. Briefkopf (8,5 pt), Informationsblock (10 pt)
#: und Fußzeile (7 pt) folgen eigenen Rastern und werden hier nicht gemessen.
KOERPER_PT = 11.0

#: Ab hier steht kein Fließtext mehr, sondern Seitenzahl und Fußzeile. Beide
#: sitzen im `footer` der Seite, also ausserhalb des Textflusses — im PDF ist
#: ihnen das nicht anzusehen, ihre Lage schon. Gemessen an allen Beispielen:
#: Der Fließtext endet spätestens bei 242,4 mm, die Seitenzahl steht bei 260,2.
RASTER_BIS = 250.0

#: Wie weit ein Zeilenabstand vom Vielfachen der Grundzeile abweichen darf.
#: 0,06 Rasterzeilen sind 0,25 mm. Gemessen liegen die echten Abstände auf
#: ±0,001 genau; die Toleranz fängt Rundung im PDF, nicht Layoutfehler.
RASTER_TOLERANZ = 0.06


def _ursache_ueberlauf(span: Span, tabellen: list[tuple[float, float]]) -> str:
    """Warum dieser Text nach rechts hinausragt — oder "" , wenn unklar.

    `soll/ist` sagt „190,88 statt hoechstens 190,00". Das ist das Symptom. Wer
    den Brief geschrieben hat, sucht danach die Stelle in seiner Datei, und
    „190,88" hilft ihm dabei nicht (Issue #145).

    Gemessen am 29.08.2026 an allen vier Faellen, die `verify` heute ueberhaupt
    zum Anschlagen bringen (`tests/fixtures/satzspiegel/`): Alle vier sind
    Ueberlaeufe nach rechts, und alle vier sind hier unterscheidbar. Die
    haeufigeren Faelle — zu langer Betreff, zu viele Anschriftzeilen — kommen
    gar nicht bis hierher: Der Datenvertrag weist sie vorher ab, mit einer
    Meldung, die die Ursache schon nennt.

    Wo die Zuordnung nicht sicher ist, bleibt die Rueckgabe leer. Eine geratene
    Ursache schickt den Leser an die falsche Stelle und ist schlechter als
    keine.
    """
    if any(oben <= span.y0 <= unten for oben, unten in tabellen):
        return ("Ursache: die Tabelle ist breiter als der Satzspiegel — Spalten "
                "zusammenfassen, kürzer beschriften oder als Aufzählung setzen")

    # Festbreitenschrift heisst hier zwingend wortgetreuer Auszug: Der Satz
    # waehlt sie fuer nichts anderes (falzmarke.typ, `wortlaut`).
    if "Mono" in span.font:
        return ("Ursache: ein wortgetreuer Auszug wird nicht umbrochen — sonst wäre er "
                f"nicht mehr wortgetreu. Er passt bis {AUSZUG_ZEICHEN} Zeichen je Zeile; "
                "längere Zeilen umbrechen oder als Anlage beilegen")

    # Ein Wort, das allein schon breiter ist als der Satzspiegel, hat keine
    # Trennstelle — Typst haette es sonst umbrochen. Ob es in einer Ueberschrift
    # oder im Fliesstext steht, laesst sich am Span nicht sicher sagen, und
    # deshalb steht es hier auch nicht.
    if span.x1 - span.x0 > BREITE_SATZSPIEGEL:
        return (f"Ursache: „{_kurz(span.text)}“ ist ein einzelnes Wort ohne Trennstelle "
                "und damit breiter als der Satzspiegel — ein Trennzeichen einfügen "
                "oder umformulieren")

    return ""


def _tabellenbereiche(seite) -> list[tuple[float, float]]:
    """y-Bereiche, in denen eine Tabelle steht — an ihren Rahmenlinien erkannt.

    Warum Tabellen nicht mitgemessen werden: Die Höhe einer Tabellenzeile hängt
    am Innenabstand der Zellen, nicht am Zeilenraster. Rastertreu wäre sie erst
    bei 0,18 mm Innenabstand — dann kleben die Zellen aneinander. Das ist eine
    Abwägung zwischen Raster und Lesbarkeit, und sie gehört entschieden, nicht
    von einer Prüfung erzwungen (Issue #151).

    Erkannt statt aufgelistet: Eine Ausnahmeliste wäre ein zweiter Ort, an dem
    sich ein Layoutfehler verstecken könnte. Ein Tabellenrahmen dagegen ist
    messbar — drei oder mehr waagerechte Linien gleicher Breite untereinander,
    und zwar im Satzspiegel, nicht im Heftrand wie die Falzmarken.
    """
    waagerecht = [l for l in seite.lines if abs(l["y0"] - l["y1"]) < 0.3
                  and mm(l["x1"] - l["x0"]) > 20.0
                  and mm(l["x0"]) >= RAND_LINKS - 1.0]
    if len(waagerecht) < 3:
        return []
    nach_breite: dict[int, list[float]] = {}
    for linie in waagerecht:
        schluessel = round(mm(linie["x1"] - linie["x0"]), 1)
        nach_breite.setdefault(int(schluessel * 10), []).append(mm(linie["top"]))
    bereiche = []
    for hoehen in nach_breite.values():
        if len(hoehen) >= 3:
            bereiche.append((min(hoehen) - 0.5, max(hoehen) + 0.5))
    return bereiche


def _raster(dokument, bericht: Bericht, briefseiten: int | None = None) -> None:
    """Der Briefkörper steht auf einem 12-pt-Raster — oder es fällt auf.

    Jede „Leerzeile" der Norm ist genau eine Rasterzeile; darauf beruhen die
    Abstände zwischen Betreff, Anrede, Text und Gruß. Bis Issue #140 war das
    eine Zusage von `falzmarke.typ` und sonst nichts: Ein krummer Abstand
    veränderte das PDF messbar, und alle 40 Prüfungen blieben grün.

    Ein Rasterversatz ist die Fehlerart, die man auf einem Ausdruck nicht sieht
    und auf zwei nebeneinandergelegten Blättern sofort — und er summiert sich.

    Gemessen werden die Abstände aufeinanderfolgender Zeilen des Briefkörpers.
    Nicht ihre absolute Lage: Ein einzelner Versatz soll einmal auffallen, nicht
    in jeder Zeile darunter noch einmal.
    """
    for nummer, seite in enumerate(dokument.pages[:briefseiten], start=1):
        tabellen = _tabellenbereiche(seite)
        spans = [s for s in _spans(seite)
                 if abs(s.groesse - KOERPER_PT) < 0.3 and s.y0 < RASTER_BIS]
        if not spans:
            continue
        zeilen = sorted(_zeilen_gruppieren(spans), key=lambda g: min(s.y0 for s in g))
        hoehen = [min(s.y0 for s in z) for z in zeilen]
        # In einer Tabelle richtet sich die Zeilenhöhe nach dem Zellabstand.
        # Auch der Ein- und Austritt zählt nicht: Er misst den Weg von einem
        # Absatz in ein Element mit eigener Höhe.
        in_tabelle = [any(a <= h <= b for a, b in tabellen) for h in hoehen]

        schiefe = []
        for i in range(1, len(hoehen)):
            if in_tabelle[i] or in_tabelle[i - 1]:
                continue
            vielfaches = (hoehen[i] - hoehen[i - 1]) / GRUNDZEILE
            if abs(vielfaches - round(vielfaches)) > RASTER_TOLERANZ:
                schiefe.append((hoehen[i], vielfaches, _kurz(" ".join(s.text for s in zeilen[i]))))
        gemessen = sum(1 for i in range(1, len(hoehen))
                       if not (in_tabelle[i] or in_tabelle[i - 1]))
        if not gemessen:
            continue
        if schiefe:
            hoehe, vielfaches, text = schiefe[0]
            ist = f"{vielfaches:.2f} Zeilen vor „{text}“ (Seite {nummer}, {hoehe:.2f} mm)"
        else:
            # Kurz gehalten: Diese Zeile stand mit 112 Zeichen an der Spitze
            # aller Berichtszeilen (die naechstlange misst 87) und brach im
            # Mitschnitt fuer das README-GIF um — der Terminal dort fasst 111.
            # Dass alle Abstaende passen, sagt bereits das „OK" davor.
            ist = f"{gemessen}× eingehalten"
        bericht.add(
            f"Seite {nummer}, Zeilenraster", "Vielfaches von 4,2333",
            ist, f"±{RASTER_TOLERANZ} Zeilen", not schiefe,
        )


def _marken(seite) -> list[tuple[float, float, float]]:
    """Waagerechte Striche im Heftrand als (y, x_start, x_ende).

    Falz- und Lochmarken zeichnet letter-pro als kurze Linien; pdfplumber führt
    sie in `page.lines`. Manche Erzeuger legen sie stattdessen als sehr flaches
    Rechteck an — deshalb werden `rects` mitgelesen.
    """
    treffer = []
    for element in list(seite.lines) + list(seite.rects):
        hoehe = abs(element["bottom"] - element["top"])
        if hoehe > 0.7:                       # nicht waagerecht
            continue
        x_start, x_ende = mm(element["x0"]), mm(element["x1"])
        if x_ende > MARKE_X_MAX:              # nicht im Heftrand
            continue
        treffer.append((mm(element["top"]), x_start, x_ende))
    return sorted(treffer)


def _zeilen_gruppieren(spans: list[Span], toleranz: float = 0.6) -> list[list[Span]]:
    zeilen: list[list[Span]] = []
    for span in spans:
        if zeilen and abs(zeilen[-1][0].y0 - span.y0) <= toleranz:
            zeilen[-1].append(span)
        else:
            zeilen.append([span])
    return zeilen


class PdfUnlesbar(ValueError):
    """Die Datei lässt sich nicht als PDF lesen.

    `verify` prüft ausdrücklich **fremde** PDFs. Was dabei hereinkommt, ist
    nicht immer eines: eine leere Datei, ein abgebrochener Download, ein
    umbenanntes Word-Dokument. Bis v0.3.1 endete jeder dieser Fälle in einem
    Python-Traceback — für den, der das Werkzeug benutzt, nicht von einem
    Absturz zu unterscheiden.
    """


def _oeffne(pdf_pfad: Path):
    """pdfplumber.open mit verständlicher Fehlermeldung.

    Gefangen wird breit: pdfminer wirft je nach Schaden PdfminerException,
    PSException, struct.error, ValueError oder AssertionError, und die Liste
    wächst mit jeder Version. Eine Aufzählung wäre zwangsläufig unvollständig
    — und ein nicht gefangener Fall sieht für den Benutzer aus wie ein Absturz.
    """
    import pdfplumber

    try:
        return pdfplumber.open(str(pdf_pfad))
    except Exception as fehler:                            # noqa: BLE001
        grund = str(fehler).strip().splitlines()[0] if str(fehler).strip() else type(fehler).__name__
        raise PdfUnlesbar(
            f"{pdf_pfad.name} lässt sich nicht als PDF lesen: {grund}"
        ) from fehler


def _nicht_eingebettete_schriften(pdf_pfad: Path, briefseiten: int | None = None) -> list[str]:
    """Schriften ohne eingebettete Datei — sie werden beim Empfänger ersetzt.

    Ein Font-Deskriptor mit FontFile/FontFile2/FontFile3 trägt die Schrift im
    PDF; fehlt er, hängt das Aussehen vom fremden Rechner ab.

    Fehlt der Deskriptor **ganz**, ist die Schrift erst recht nicht eingebettet:
    Er ist der einzige Ort, an dem eine FontFile stehen kann. Genau so sehen die
    14 PDF-Standardschriften aus (Helvetica, Times, Courier …) — sie dürfen ohne
    Deskriptor auftreten und werden beim Empfänger ersetzt. Bis v0.3.1 wurden
    sie übersprungen und galten damit als eingebettet; ein fremdes PDF, das
    ausschließlich Helvetica benutzte, kam ohne Beanstandung durch.

    Ausnahme sind Type-3-Schriften: Ihre Glyphen stehen als Zeichenprogramme in
    `/CharProcs` im PDF selbst, sie brauchen keine FontFile.
    """
    from pypdf import PdfReader

    offen = []
    leser = PdfReader(str(pdf_pfad))
    # Nur die Seiten, die falzmarke gesetzt hat: Eine angehaengte Anlage ist
    # fremdes Papier. Ihre Schriften sind nicht unsere Zusage — und sie zu
    # beanstanden hiesse, dem Absender einen Fehler vorzuwerfen, den er in
    # einer Datei hat, die er nur weiterreicht.
    for seite in leser.pages[:briefseiten]:
        schriften = (seite.get("/Resources") or {}).get("/Font") or {}
        for schluessel in schriften:
            schrift = schriften[schluessel].get_object()
            nachfahren = schrift.get("/DescendantFonts")
            kandidaten = [d.get_object() for d in nachfahren] if nachfahren else [schrift]
            for kandidat in kandidaten:
                if kandidat.get("/Subtype") == "/Type3":
                    continue
                deskriptor = kandidat.get("/FontDescriptor")
                if deskriptor is None:
                    offen.append(str(kandidat.get("/BaseFont", schluessel)))
                    continue
                deskriptor = deskriptor.get_object()
                if not any(k in deskriptor for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                    offen.append(str(kandidat.get("/BaseFont", schluessel)))
    return sorted(set(offen))


def _briefseiten_aus_metadaten(pdf_pfad: Path) -> int | None:
    """Wie viele Seiten der Brief hat — laut der Datei selbst.

    anlagen.haenge_an schreibt das hinein. Ohne diesen Vermerk koennte `verify`
    auf einer fertigen Datei nicht wissen, wo der Brief endet und die Anlage
    beginnt, und wuerde die Anlage nach Briefregeln messen.
    """
    from pypdf import PdfReader

    try:
        angabe = (PdfReader(str(pdf_pfad)).metadata or {}).get("/falzmarke_Briefseiten")
    except Exception:                                             # noqa: BLE001
        return None
    try:
        zahl = int(str(angabe))
    except (TypeError, ValueError):
        return None
    return zahl if zahl > 0 else None


def pruefe(pdf_pfad: Path, form: str, briefseiten: int | None = None) -> Bericht:
    """Misst den Brief. `briefseiten` begrenzt die Messung auf die ersten n Seiten.

    Nötig, seit `anlagen_dateien` fremde PDFs hinten anhängen kann: Eine Anlage
    trägt keine Kopfzeile mit Betreff, keine Seitenzählung und womöglich keine
    eingebettete Schrift. Sie danach zu beurteilen, hiesse dem Absender einen
    Fehler in einem Dokument vorzuwerfen, das er nur beilegt.

    Ohne Angabe wird die Zahl aus den Metadaten gelesen (`/falzmarke_Briefseiten`,
    von anlagen.haenge_an geschrieben) — so weiss auch ein `verify` auf einer
    fertigen Datei, wo der Brief endet. Steht dort nichts, gilt das ganze
    Dokument als Brief; das ist der Zustand aller Briefe ohne Anlagen.
    """
    soll = FORM[form]
    bericht = Bericht()
    dokument = _oeffne(pdf_pfad)
    if briefseiten is None:
        briefseiten = _briefseiten_aus_metadaten(pdf_pfad)
    if not dokument.pages:
        dokument.close()
        raise PdfUnlesbar(f"{pdf_pfad.name} enthält keine Seite.")
    seite = dokument.pages[0]

    # Seitengröße
    bericht.wert("Seitenbreite", mm(seite.width), SEITE_BREITE, 0.1)
    bericht.wert("Seitenhöhe", mm(seite.height), SEITE_HOEHE, 0.1)

    _satzspiegel(dokument, bericht, briefseiten)
    _raster(dokument, bericht, briefseiten)

    # Falz- und Lochmarken. Gesucht wird die nächstgelegene Marke, nicht die an
    # der Sollposition: Eine Marke bei 84,0 statt 87,0 mm ist ein verschobenes
    # Layout und soll als solches gemeldet werden — bis v0.1.2 hieß es dort
    # "nicht gefunden", was für einen Linter fremder PDFs unbrauchbar ist.
    marken = _marken(seite)
    vergeben: set[float] = set()
    for bezeichnung, sollwert in (
        ("Falzmarke 1", soll["falzmarke_1"]),
        ("Falzmarke 2", soll["falzmarke_2"]),
        ("Lochmarke", LOCHMARKE),
    ):
        frei = [m for m in marken if m[0] not in vergeben]
        naechste = min(frei, key=lambda m: abs(m[0] - sollwert), default=None)
        if naechste is None:
            bericht.wahr(f"{bezeichnung}, y", False, f"{sollwert} mm",
                         "keine Marke im Heftrand gefunden")
            continue
        y, _, x_ende = naechste
        vergeben.add(y)
        abweichung = y - sollwert
        if abs(abweichung) <= 0.3:
            bericht.wert(f"{bezeichnung}, y", y, sollwert, 0.3)
            bericht.wahr(
                f"{bezeichnung}, im Heftrand", x_ende <= MARKE_X_MAX,
                f"x-Ende ≤ {MARKE_X_MAX}", f"{x_ende:.2f}",
            )
        elif abs(abweichung) <= MARKE_ZUORDNUNG:
            # Die Marke ist da, sitzt nur falsch. Für den Linter fremder PDFs
            # ist das die eigentlich nützliche Auskunft.
            richtung = "zu hoch" if abweichung < 0 else "zu tief"
            bericht.add(
                f"{bezeichnung}, y", f"{sollwert:.2f}",
                f"{y:.2f} — {abs(abweichung):.2f} mm {richtung}", "±0.30", False,
            )
        else:
            bericht.wahr(
                f"{bezeichnung}, y", False, f"{sollwert:.2f} mm",
                f"keine Marke in der Nähe (nächste bei {y:.2f} mm)",
            )

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
    # Zum Informationsblock gehört eine Zeile nur, wenn sie rechts BEGINNT.
    # Einzelne Wörter rechts von 125 mm gibt es auch im Fließtext — sie sind
    # Fortsetzung einer Zeile, die links am Satzspiegel anfängt. Erst unterhalb
    # der Kopfhöhe suchen: darüber steht der Briefkopf, der ebenfalls
    # rechtsbündig gesetzt sein darf.
    info_spans = []
    for zeile in _zeilen_gruppieren(
        [s for s in spans if soll["kopfhoehe"] < s.y0 < 150]
    ):
        if min(s.x0 for s in zeile) >= INFOBLOCK_X - 5:
            info_spans.extend(zeile)
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

    # Betreff: der fette Block unterhalb des Anschriftfelds. Er darf zwei
    # Zeilen haben — ein Angebot mit Vorgangsnummer und Gegenstand ist der
    # Normalfall. Gemessen wird deshalb der ganze Block, nicht die erste Zeile:
    # sonst gilt die zweite Betreffzeile als Anrede und der Abstand stimmt nie.
    fette = [s for s in spans if s.fett and s.y0 > a_unten - 5]
    betreff_zeilen = []
    for zeile in _zeilen_gruppieren(fette):
        if betreff_zeilen:
            vorige = betreff_zeilen[-1][0].y0
            if zeile[0].y0 - vorige > 1.6 * ZEILE:   # Lücke: gehört nicht mehr dazu
                break
        betreff_zeilen.append(zeile)

    betreff = betreff_zeilen[0][0] if betreff_zeilen else None
    betreff_letzte = betreff_zeilen[-1][0] if betreff_zeilen else None
    if betreff is not None:
        bericht.add(
            "Betreff, Zeilenzahl", "≤ 2", str(len(betreff_zeilen)), "—",
            len(betreff_zeilen) <= 2,
        )
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

    anrede = next(
        (s for s in spans if betreff_letzte is not None and s.y0 > betreff_letzte.y0 + 0.5 * ZEILE),
        None,
    )
    if betreff_letzte is not None and anrede is not None:
        # Konstruktiv exakt: beide Messpunkte tragen denselben Glyph-Versatz,
        # der sich in der Differenz heraushebt. Deshalb enge Toleranz.
        bericht.wert(
            "Abstand Betreff → Anrede (2 Leerzeilen)",
            anrede.y0 - betreff_letzte.y0, 3 * ZEILE, 0.2,
        )

    # Textblock
    body_spans = [
        s for s in spans
        if betreff_letzte is not None and s.y0 > betreff_letzte.y0 + 0.5 * ZEILE and s.y1 < 250
    ]
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
    nicht_eingebettet = _nicht_eingebettete_schriften(pdf_pfad, briefseiten)
    bericht.wahr(
        "Schriften eingebettet", not nicht_eingebettet, "alle eingebettet",
        "fehlend: " + ", ".join(nicht_eingebettet) if nicht_eingebettet else "alle",
    )

    # Folgeseiten — gezaehlt werden die Seiten des Briefes, nicht die der Datei.
    brief_seitenzahl = briefseiten or len(dokument.pages)
    if brief_seitenzahl > 1:
        zweite = dokument.pages[1]
        text = zweite.extract_text() or ""
        # Die Seitenzahl steht in der Sprache des Briefes. Geprueft wird gegen
        # jede bekannte Fassung, nicht nur die deutsche: `verify` misst auch
        # fremde PDFs, deren Sprache niemand kennt — und ein englischer Brief
        # ist nicht deshalb falsch gesetzt, weil dort „Page 2 of 2“ steht.
        # Zuvor war der deutsche Wortlaut fest verdrahtet, und jeder englische
        # Mehrseiter fiel hier durch.
        from falzmarke import sprachen

        moegliche = [
            sprachen.WOERTER[s]["seite"].replace("{n}", "2").replace(
                "{m}", str(brief_seitenzahl))
            for s in sprachen.erlaubt()
        ]
        gefunden = next((m for m in moegliche if m in text), None)
        bericht.wahr(
            "Seite 2: Seitenzahl", gefunden is not None,
            " oder ".join(f"'{m}'" for m in moegliche),
            f"'{gefunden}'" if gefunden else "fehlt",
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


def xmp_lesen(pdf_pfad: Path) -> str:
    """Die rohen XMP-Metadaten des Dokuments."""
    from pypdf import PdfReader

    leser = PdfReader(str(pdf_pfad))
    roh = leser.xmp_metadata
    if roh is None:
        return ""
    strom = getattr(roh, "stream", None)
    if strom is not None:
        daten = strom.get_data()
        return daten.decode("utf-8", "replace") if isinstance(daten, bytes) else str(daten)
    return str(roh)


def erkenne_form(pdf_pfad: Path) -> str | None:
    """Form A oder B aus den Falzmarken ableiten.

    Form A faltet bei 87 und 192 mm, Form B bei 105 und 210 mm. Die Marken
    stehen im Blatt, also muss man die Form nicht wissen, um zu prüfen.
    """
    import pdfplumber

    with _oeffne(pdf_pfad) as dokument:
        marken = [m[0] for m in _marken(dokument.pages[0])]
    if not marken:
        return None
    treffer = {}
    for form, werte in FORM.items():
        passend = sum(
            1 for sollwert in (werte["falzmarke_1"], werte["falzmarke_2"])
            if any(abs(m - sollwert) <= 1.0 for m in marken)
        )
        treffer[form] = passend
    beste = max(treffer, key=lambda f: treffer[f])
    return beste if treffer[beste] >= 1 else None


def pdfa_geprueft(pdf_pfad: Path) -> tuple[bool, str]:
    """Liest die XMP-Metadaten und prüft auf PDF/A-2b."""
    xmp = xmp_lesen(pdf_pfad)
    teil_ok = "pdfaid:part>2" in xmp.replace(" ", "") or 'pdfaid:part="2"' in xmp
    konformitaet_ok = "pdfaid:conformance>B" in xmp.replace(" ", "") or 'pdfaid:conformance="B"' in xmp
    return (teil_ok and konformitaet_ok), xmp[:200]
