"""Einen bestehenden Brief einlesen — als Gerüst mit benannten Lücken (#191).

WORUM ES GEHT

Alle anderen Wege dieses Pakets gehen von Markdown zum PDF. Dieser geht zurück:
Aus einem fertigen Brief entsteht ein falzmarke-Markdown, das man weiterverwenden
kann. Gedacht für Bestände, die jemand vor Jahren in Word gesetzt hat.

DIE ENTSCHEIDUNG, AN DER ALLES HÄNGT: HIER WIRD NICHT GERATEN

Ein falsch erkannter Empfänger fällt erst im gedruckten Brief auf — im Zweifel
beim Empfänger, der ihn nicht bekommen sollte. Das ist die teuerste Fehlerklasse,
die dieses Werkzeug haben kann.

Deshalb wird ein Frontmatter-Feld nur gesetzt, wenn es **belegbar** ist, und sonst
als Lücke mit Begründung ausgewiesen. Was aussieht wie ein Empfänger, aber keiner
sein muss, wird als *Kandidat* danebengestellt — sichtbar unentschieden, damit ein
Mensch oder ein Modell entscheidet.

WARUM POSITIONEN ALLEIN NICHT REICHEN

Die naheliegende Erkennung — "was in der DIN-Anschriftzone steht, ist der
Empfänger" — ist genau dann falsch, wenn sie gebraucht wird. Gemessen am
Testbrief `tests/fixtures/einlesen/altbrief.typ`, einem typischen Word-Brief:

    y = 44,9 mm   Werkstraße 14          <- ABSENDER
    y = 50,2 mm   93055 Regensburg       <- ABSENDER
    ...
    y = 97,6 mm   Steuerberatung ...     <- der echte Empfänger

Die Form-A-Anschriftzone reicht von 44,7 bis 72,0 mm. Der Absender liegt darin,
der Empfänger nicht. Ein zonenbasierter Importer hätte hier mit voller
Überzeugung den Absender als Empfänger ausgegeben.

Positionen sind nur dann aussagekräftig, wenn das Blatt überhaupt nach DIN 5008
gesetzt ist. Ob es das ist, sagen die **Falz- und Lochmarken** im Heftrand —
gemessen:

    Form B (falzmarke)   Marken bei y = 105,0 / 148,5 / 210,0
    Form A (falzmarke)   Marken bei y =  87,0 / 148,5 / 192,0
    Word-Brief           keine

Ohne Marken gilt: kein DIN-Raster, also keine positionsbasierte Aussage. Dann
kommt der Text mit, und die Felder bleiben Lücken mit Kandidaten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from falzmarke.geometrie import (
    ANSCHRIFT_X_RECHTS,
    FORM,
    INFOBLOCK_X,
    KOERPER_PT,
    LOCHMARKE,
    RAND_LINKS,
    RASTER_BIS,
    ZEILE,
    PdfUnlesbar,
    Span,
    _marken,
    _oeffne,
    _spans,
    _zeilen_gruppieren,
)

__all__ = ["Ergebnis", "Luecke", "lies_pdf", "PdfUnlesbar"]

# Toleranz, mit der eine Marke ihrem Sollwert zugeordnet wird. Dieselbe Schranke
# wie in geometrie.pruefe für die exakte Lage — enger wäre gegenüber fremden
# Erzeugern unfair, weiter würde Form A und B verwechseln (sie liegen 18 mm
# auseinander).
MARKE_TOLERANZ = 1.5

# Ein Anschriftblock steht am linken Satzspiegelrand. Dieselbe Schranke wie in
# der Messung (dort ±0,3 mm gegen RAND_LINKS); hier etwas weiter, weil fremde
# Erzeuger runden.
ANSCHRIFT_X_TOLERANZ = 1.5

DATUM_MUSTER = [
    # ISO zuerst: eindeutig, keine Reihenfolgefrage.
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso"),
    (re.compile(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\b"), "dmy"),
    (
        re.compile(
            r"\b(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|"
            r"September|Oktober|November|Dezember)\s+(\d{4})\b"
        ),
        "dmonaty",
    ),
]
MONATE = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
    "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11,
    "Dezember": 12,
}

GRUSSFORMELN = (
    "mit freundlichen grüßen", "mit freundlichem gruß", "freundliche grüße",
    "mit besten grüßen", "beste grüße", "viele grüße", "herzliche grüße",
    "hochachtungsvoll",
)


@dataclass
class Luecke:
    """Ein Feld, das nicht belegbar war.

    `kandidat` ist ausdrücklich KEIN Wert, sondern ein Fund, der so aussieht.
    Er steht im Ergebnis als Kommentar, nie als gesetztes Feld — der Unterschied
    ist der ganze Zweck dieses Moduls.
    """

    feld: str
    grund: str
    kandidat: str | None = None


@dataclass
class Ergebnis:
    felder: dict[str, object] = field(default_factory=dict)
    luecken: list[Luecke] = field(default_factory=list)
    koerper: str = ""
    form: str | None = None
    quelle: str = ""

    def fehlend(self) -> list[str]:
        return [luecke.feld for luecke in self.luecken]

    def als_markdown(self) -> str:
        """Das Gerüst: Frontmatter mit Lücken als Kommentar, dann der Text."""
        zeilen = ["---"]
        if self.form:
            zeilen.append(f"# eingelesen aus: {self.quelle} (Form {self.form})")
        else:
            zeilen.append(f"# eingelesen aus: {self.quelle} (kein DIN-5008-Raster erkannt)")

        for luecke in self.luecken:
            zeilen.append(f"# {luecke.feld}: <nicht erkannt: {luecke.grund}>")
            if luecke.kandidat:
                for teil in luecke.kandidat.split("\n"):
                    zeilen.append(f"#   Kandidat: {teil}")

        for schluessel in ("profil", "form", "empfaenger", "datum", "betreff", "anrede"):
            if schluessel not in self.felder:
                continue
            wert = self.felder[schluessel]
            if isinstance(wert, list):
                zeilen.append(f"{schluessel}:")
                zeilen.extend(f"  - {eintrag}" for eintrag in wert)
            else:
                zeilen.append(f"{schluessel}: {wert}")

        zeilen.append("---")
        zeilen.append("")
        zeilen.append(self.koerper)
        return "\n".join(zeilen).rstrip() + "\n"


def _form_aus_marken(seite) -> str | None:
    """Die Form aus den Marken im Heftrand — oder None.

    None heißt: Das Blatt trägt kein DIN-5008-Raster. Es ist deshalb NICHT
    zulässig, danach mit Zonen zu arbeiten; genau daran scheitert die naive
    Erkennung (siehe Modul-Docstring).
    """
    ys = [marke[0] for marke in _marken(seite)]
    if not ys:
        return None
    for name, masse in FORM.items():
        soll = (masse["falzmarke_1"], LOCHMARKE, masse["falzmarke_2"])
        if all(
            any(abs(y - einzelsoll) <= MARKE_TOLERANZ for y in ys)
            for einzelsoll in soll
        ):
            return name
    return None


def _text(zeile: list[Span]) -> str:
    return " ".join(span.text for span in zeile).strip()


def _datum_normieren(text: str) -> str | None:
    for muster, art in DATUM_MUSTER:
        treffer = muster.search(text)
        if not treffer:
            continue
        if art == "iso":
            return f"{treffer.group(1)}-{treffer.group(2)}-{treffer.group(3)}"
        if art == "dmy":
            tag, monat, jahr = (int(teil) for teil in treffer.groups())
        else:
            tag = int(treffer.group(1))
            monat = MONATE[treffer.group(2)]
            jahr = int(treffer.group(3))
        if not (1 <= monat <= 12 and 1 <= tag <= 31):
            return None
        return f"{jahr:04d}-{monat:02d}-{tag:02d}"
    return None


def _anschrift_aus_zone(zeilen: list[list[Span]], masse: dict) -> list[str] | None:
    """Der Anschriftblock — nur wenn er dort steht, wo die Norm ihn verlangt.

    Zwei Bedingungen, beide nötig: in der Zone UND am linken Satzspiegelrand.
    Die zweite ist der Grund, warum ein zufällig in der Zone liegender Absender
    nicht durchrutscht — er steht selten genau bei 25 mm.
    """
    oben, unten = masse["anschrift_zone"]
    treffer = [
        zeile for zeile in zeilen
        if oben - 1.5 <= zeile[0].y0 <= unten
        and zeile[0].x0 < ANSCHRIFT_X_RECHTS
        and abs(zeile[0].x0 - RAND_LINKS) <= ANSCHRIFT_X_TOLERANZ
        and zeile[0].groesse >= 9.0
    ]
    if not treffer or len(treffer) > 6:
        return None
    # Auf gleicher Hoehe steht rechts der Informationsblock, und die
    # Zeilenbildung fasst beides zu EINER Zeile zusammen: Anschriftzeile 1 kam
    # dadurch als "Muster GmbH Erika Muster" heraus — der Name des
    # Ansprechpartners aus dem Infoblock, angeklebt an den Empfaenger. Der
    # Schnitt bei ANSCHRIFT_X_RECHTS ist dieselbe Grenze, mit der die Zeilen
    # oben ausgewaehlt werden; hier wirkt er innerhalb der Zeile.
    ausgabe = []
    for zeile in treffer:
        links = [span for span in zeile if span.x0 < ANSCHRIFT_X_RECHTS]
        text = " ".join(span.text for span in links).strip()
        if text:
            ausgabe.append(text)
    return ausgabe or None


def _betreff_aus_fettem_block(zeilen: list[list[Span]], masse: dict) -> str | None:
    """Der Betreff ist im DIN-Brief fett und steht unter dem Anschriftfeld.

    Ohne Fettschrift wird nichts zurückgegeben: Ein Betreff ohne Auszeichnung
    ist von der Anrede nur inhaltlich zu unterscheiden, und inhaltlich raten ist
    genau das, was dieses Modul nicht tut.
    """
    _, anschrift_unten = masse["anschrift_zone"]
    fette = [zeile for zeile in zeilen if zeile[0].fett and zeile[0].y0 > anschrift_unten - 5]
    if not fette:
        return None
    block = [fette[0]]
    for zeile in fette[1:]:
        if zeile[0].y0 - block[-1][0].y0 > 1.6 * ZEILE:
            break
        block.append(zeile)
    text = " ".join(_text(zeile) for zeile in block)
    return re.sub(r"^Betreff:\s*", "", text).strip() or None


def _ist_fusszeile(zeile: list[Span]) -> bool:
    """Die Fußzeile gehört zum Absenderprofil, nicht zum Brieftext.

    Zwei unabhängige Merkmale, beide nötig — gemessen am Beispielbrief: Sie
    steht unterhalb des Rasters (y = 273–280 gegen RASTER_BIS = 250) UND ist
    kleiner gesetzt (7,0 pt gegen 11,0 pt Körper). Ein Merkmal allein wäre zu
    grob: Ein langer Brief reicht bis nah an den Fuß, und eine Kleinschrift-
    Anmerkung kann auch mitten im Text stehen.
    """
    return zeile[0].y0 > RASTER_BIS and zeile[0].groesse < KOERPER_PT - 1.0


def _entsilbe(text: str) -> str:
    """Trennstriche des Satzes zurücknehmen: "Neuge- staltung" -> "Neugestaltung".

    Der Umbruch stammt vom Setzer, nicht vom Verfasser — beim Wiedereinlesen
    soll der Satz so dastehen, wie er geschrieben wurde. Zusammengezogen wird
    NUR, wenn nach dem Bindestrich ein Kleinbuchstabe folgt: "Muster- Straße"
    bleibt damit unangetastet, und echte Bindestrich-Komposita
    ("E-Mail-Adresse") sind ohnehin nicht getrennt.
    """
    return re.sub(r"(\w)-\s+([a-zäöüß])", r"\1\2", text)


# Aufzaehlungszeichen, die Typst und Word setzen. Sie werden zu Markdown-
# Listenpunkten zurueckgebaut: Ohne das laeuft eine dreizeilige Liste zu EINEM
# Absatz zusammen ("• Entwurf … • Umsetzung … • Uebergabe …") und ist als Liste
# nicht mehr erkennbar.
AUFZAEHLUNG = re.compile(r"^[•▪◦·–—-]\s+")


def _glaette(text: str) -> str:
    """Leerzeichen vor Satzzeichen entfernen.

    Sie entstehen beim Zusammensetzen der Woerter, nicht im Original: pdfplumber
    liefert Woerter einzeln, und ein Wechsel des Schriftschnitts mitten im Satz
    trennt eines ab ("sieben Werktage ." am Beispielbrief).
    """
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


def _koerper(zeilen: list[list[Span]], ab_y: float) -> str:
    """Fließtext ab einer Höhe, Absätze an Zeilenlücken erkannt.

    Grußformel und Anlagenverzeichnis bleiben im Text stehen. Sie wären
    Frontmatter-Felder, aber ob eine Zeile eine Grußformel IST oder nur so
    anfängt, entscheidet hier niemand — sie werden als Kandidat gemeldet, nicht
    aus dem Text geschnitten. Wer sie ins Frontmatter hebt, sieht dann selbst,
    was er aus dem Körper entfernt.
    """
    absaetze: list[list[str]] = []
    vorige_y: float | None = None
    for zeile in zeilen:
        if zeile[0].y0 <= ab_y or _ist_fusszeile(zeile):
            continue
        text = _text(zeile)
        if not text:
            continue
        if vorige_y is not None and zeile[0].y0 - vorige_y > 1.6 * ZEILE:
            absaetze.append([])
        if not absaetze:
            absaetze.append([])
        # Ein Aufzaehlungspunkt beginnt IMMER einen neuen Absatz, auch ohne
        # Zeilenluecke davor — sonst klebt er an den einleitenden Satz.
        if AUFZAEHLUNG.match(text):
            if absaetze[-1]:
                absaetze.append([])
            absaetze[-1].append("- " + AUFZAEHLUNG.sub("", text))
            vorige_y = zeile[0].y0
            absaetze.append([])
            continue
        absaetze[-1].append(text)
        vorige_y = zeile[0].y0
    roh = "\n\n".join(" ".join(teil) for teil in absaetze if teil).strip()
    # Aufeinanderfolgende Listenpunkte wieder zu EINEM Block: Sie sind oben
    # bewusst einzeln entstanden, gehoeren im Markdown aber zusammen.
    roh = re.sub(r"\n\n(?=- )", "\n", roh)
    return _glaette(_entsilbe(roh))


def _kandidat_anlagen(zeilen: list[list[Span]], ab_y: float) -> str | None:
    """Das Anlagenverzeichnis — als Kandidat, nicht als Feld.

    Es steht am Fuß des Briefes unter einem Leitwort. Das Leitwort ist
    sprachabhängig (`sprachen.py` kennt weitere), und ob die Zeilen darunter
    wirklich Anlagen sind oder schon der nächste Absatz, ist Lesearbeit.
    Deshalb Kandidat: Der Text bleibt vollständig im Körper stehen, und wer die
    Anlagen ins Frontmatter hebt, sieht selbst, was er dort herausnimmt.
    """
    leitworte = ("anlage", "anlagen", "anlage:", "anlagen:", "enclosure", "enclosures")
    for stelle, zeile in enumerate(zeilen):
        if zeile[0].y0 <= ab_y or _ist_fusszeile(zeile):
            continue
        if _text(zeile).strip().lower().rstrip(":") not in [w.rstrip(":") for w in leitworte]:
            continue
        eintraege = []
        for folge in zeilen[stelle + 1:]:
            if _ist_fusszeile(folge):
                break
            text = _text(folge)
            if not text:
                break
            eintraege.append(text)
            if len(eintraege) >= 6:
                break
        return "\n".join(eintraege) if eintraege else None
    return None


def _kandidat_anschrift(zeilen: list[list[Span]]) -> str | None:
    """Ein Block aus 2–6 kurzen, linksbündigen Zeilen mit Postleitzahl.

    Bewusst schwach: Das ist ein Hinweis für den Menschen, kein Wert. Ohne
    Postleitzahl gibt es keinen Kandidaten — dann fehlt jeder Anhaltspunkt.
    """
    beste: list[str] | None = None
    lauf: list[list[Span]] = []
    for zeile in zeilen:
        kurz = len(_text(zeile)) <= 60
        anschluss = not lauf or 0 < zeile[0].y0 - lauf[-1][0].y0 <= 1.6 * ZEILE
        if kurz and anschluss and abs(zeile[0].x0 - (lauf[0][0].x0 if lauf else zeile[0].x0)) <= 1.0:
            lauf.append(zeile)
        else:
            lauf = [zeile] if kurz else []
        texte = [_text(z) for z in lauf]
        if 2 <= len(texte) <= 6 and any(re.search(r"\b\d{5}\b", t) for t in texte):
            if beste is None or len(texte) > len(beste):
                beste = list(texte)
    return "\n".join(beste) if beste else None


def lies_pdf(pdf_pfad: Path) -> Ergebnis:
    """Ein PDF als falzmarke-Gerüst. Setzt nur, was belegbar ist."""
    pdf_pfad = Path(pdf_pfad)
    ergebnis = Ergebnis(quelle=pdf_pfad.name)

    with _oeffne(pdf_pfad) as dokument:
        if not dokument.pages:
            raise PdfUnlesbar(f"{pdf_pfad.name} enthält keine Seite.")
        seite = dokument.pages[0]
        zeilen = _zeilen_gruppieren(_spans(seite))
        form = _form_aus_marken(seite)

    ergebnis.form = form

    # `profil` beschreibt den Absender und lebt als lokale Datei. Es steht in
    # KEINEM PDF und ist deshalb immer eine Lücke — auch bei einem Brief, den
    # falzmarke selbst gesetzt hat. Alles andere wäre eine erfundene Angabe.
    ergebnis.luecken.append(
        Luecke("profil", "Absenderprofil ist eine lokale Datei, im PDF steht es nicht")
    )

    if form is None:
        grund = (
            "keine Falz- und Lochmarken im Heftrand — das Blatt trägt kein "
            "DIN-5008-Raster, Positionen sagen hier nichts"
        )
        ergebnis.luecken.append(Luecke("empfaenger", grund, _kandidat_anschrift(zeilen)))
        datum_kandidat = next(
            (_datum_normieren(_text(z)) for z in zeilen if _datum_normieren(_text(z))), None
        )
        ergebnis.luecken.append(Luecke("datum", grund, datum_kandidat))
        betreff_kandidat = next(
            (re.sub(r"^Betreff:\s*", "", _text(z)) for z in zeilen
             if _text(z).lower().startswith("betreff")), None
        )
        ergebnis.luecken.append(Luecke("betreff", grund, betreff_kandidat))
        ergebnis.koerper = _koerper(zeilen, ab_y=0.0)
        return ergebnis

    masse = FORM[form]
    ergebnis.felder["form"] = form

    anschrift = _anschrift_aus_zone(zeilen, masse)
    if anschrift:
        ergebnis.felder["empfaenger"] = anschrift
    else:
        ergebnis.luecken.append(
            Luecke(
                "empfaenger",
                f"kein Anschriftblock in der Zone {masse['anschrift_zone']} mm "
                f"am linken Satzspiegelrand ({RAND_LINKS} mm)",
                _kandidat_anschrift(zeilen),
            )
        )

    betreff = _betreff_aus_fettem_block(zeilen, masse)
    if betreff:
        ergebnis.felder["betreff"] = betreff
    else:
        ergebnis.luecken.append(
            Luecke("betreff", "kein fett gesetzter Block unter dem Anschriftfeld")
        )

    # Das Datum steht im DIN-Brief rechts, auf Höhe des Informationsblocks oder
    # kurz darunter. Gesucht wird nur dort — ein Datum im Fließtext ("Ihre
    # Nachricht vom 3. März") ist nicht das Briefdatum.
    # Die UNTERSTE, nicht die erste: Im Informationsblock stehen mehrere Daten
    # ("Ihre Nachricht vom", "Unsere Nachricht vom"), und das Briefdatum steht
    # strukturell hinter ihnen — INFOBLOCK_REIHENFOLGE in lint.py fuehrt das
    # Datum nicht, es folgt dem Block. Die erste Datumszeile zu nehmen lieferte
    # am Beispielbrief 2026-08-20 statt 2026-08-25: das Datum der Anfrage,
    # ausgegeben als Briefdatum. Ein plausibler Falschwert ist hier schlimmer
    # als eine Luecke.
    datum = None
    for zeile in zeilen:
        if zeile[0].x0 >= INFOBLOCK_X - 5 and zeile[0].y0 < masse["betreff_standard"]:
            gefunden = _datum_normieren(_text(zeile))
            if gefunden:
                datum = gefunden
    if datum:
        ergebnis.felder["datum"] = datum
    else:
        ergebnis.luecken.append(
            Luecke("datum", f"keine Datumszeile rechts (ab {INFOBLOCK_X} mm) über dem Betreff")
        )

    # Anrede: erste Zeile nach dem Betreffblock. Sie endet an einem Komma —
    # ohne Komma wird nichts gesetzt.
    anrede_y = masse["betreff_standard"]
    anrede = None
    for zeile in zeilen:
        if zeile[0].y0 > anrede_y + 0.5 * ZEILE:
            text = _text(zeile)
            if text.endswith(","):
                anrede = text
                anrede_y = zeile[0].y0
            break
    if anrede:
        ergebnis.felder["anrede"] = anrede
    else:
        ergebnis.luecken.append(
            Luecke("anrede", "erste Zeile nach dem Betreff endet nicht auf ein Komma")
        )

    ergebnis.koerper = _koerper(zeilen, ab_y=anrede_y)

    anlagen = _kandidat_anlagen(zeilen, ab_y=anrede_y)
    if anlagen:
        ergebnis.luecken.append(
            Luecke(
                "anlagen",
                "Leitwort gefunden, aber ob die Zeilen darunter Anlagen sind, "
                "ist Lesearbeit — der Text steht unverändert im Körper",
                anlagen,
            )
        )
    return ergebnis
