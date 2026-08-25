#!/usr/bin/env python3
"""Prüfung vor dem Render — ohne Typst, in Millisekunden.

Warum eine eigene Stufe: Ein Fehler in der Eingabe ist etwas anderes als ein
Fehler im Ergebnis. Bis v0.1.2 meldete der Betreff mit Schlusspunkt „das PDF
hält die Maße aus DIN 5008 nicht ein" — falsche Fehlerklasse, falscher
Exit-Code, und ein Render, der umsonst lief.

Befunde haben zwei Schweregrade. **Fehler** halten den Render an; **Warnungen**
nennen etwas, das gesetzt wird, aber vermutlich nicht gemeint war (zwei
Leerzeichen als Zeilenumbruch etwa — unsichtbar in jeder Vorschau).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from falzmarke import regeln

FEHLER = "Fehler"
WARNUNG = "Warnung"

# Größen der Zonen, gegen die geprüft wird. Quelle: references/din5008.md
ANSCHRIFT_MAX_ZEILEN = 6
VERMERKE_MAX_ZEILEN = 3
INFOBLOCK_WERT_MAX = 32
BETREFF_MAX_ZEICHEN = 150      # zwei Zeilen bei 165 mm Satzbreite, 11 pt

# Leitwörter des Informationsblocks in der Reihenfolge der Norm.
# Steht hier und nicht in cli.py, weil cli lint importiert und nicht umgekehrt:
# So gibt es EINE Liste statt einer Kopie, die still veraltet.
INFOBLOCK_REIHENFOLGE = [
    ("ihr_zeichen", "Ihr Zeichen"),
    ("ihre_nachricht_vom", "Ihre Nachricht vom"),
    ("unser_zeichen", "Unser Zeichen"),
    ("unsere_nachricht_vom", "Unsere Nachricht vom"),
    ("ansprechpartner", "Name"),
    ("telefon", "Telefon"),
    ("fax", "Fax"),
    ("email", "E-Mail"),
]

PFLICHTFELDER = ("profil", "empfaenger", "datum", "betreff")

# Der vollständige Datenvertrag: was im Frontmatter einer Briefdatei stehen darf.
# Dokumentiert in references/frontmatter.md; ein Test hält beide zusammen.
FRONTMATTER_FELDER = frozenset({
    "profil", "form", "norm", "empfaenger", "vermerke", "datum",
    "betreff", "betreff_kurz", "infoblock", "anrede", "gruss",
    "unterzeichner", "signatur", "anlagen", "verteiler",
})

INFOBLOCK_FELDER = frozenset(schluessel for schluessel, _ in INFOBLOCK_REIHENFOLGE)

URL_MUSTER = re.compile(r"\bhttps?://\S*", re.I)
EMAIL_MUSTER = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
TELEFON_MUSTER = re.compile(r"^\+?[\d]{2,4}(\s\d+)*(-\d+)?$")
ISO_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Befund:
    zeile: int
    regel: str
    schwere: str
    meldung: str
    korrektur: str = ""

    def als_zeile(self, datei: str) -> str:
        marke = "FEHLER " if self.schwere == FEHLER else "WARNUNG"
        ort = f"{datei}:{self.zeile}" if self.zeile else datei
        text = f"{marke} {ort} {self.regel} — {self.meldung}"
        return f"{text}\n         Korrektur: {self.korrektur}" if self.korrektur else text

    def als_dict(self) -> dict:
        return {
            "zeile": self.zeile, "regel": self.regel, "schwere": self.schwere,
            "meldung": self.meldung, "korrektur": self.korrektur,
        }


@dataclass
class Bericht:
    befunde: list[Befund] = field(default_factory=list)

    def fehler(self, zeile: int, regel: str, meldung: str, korrektur: str = "") -> None:
        """Meldet einen Fehler — soweit die Quellenlage das trägt.

        Alle Maße und Schreibregeln stammen aus Sekundärquellen; der Abgleich
        mit dem Originaltext der DIN 5008:2020-03 steht aus. Solange das so
        ist, darf nur als Fehler gelten, was mehrfach belegt ist. Eine Regel
        aus einer einzigen Quelle wird hier zur Warnung und nennt das in der
        Meldung; eine Regel ohne Beleg wird gar nicht gemeldet.

        Die Herabstufung sitzt bewusst an dieser einen Stelle: Jeder Fehler im
        Linter läuft hier durch, und eine neue Prüfung erbt die Regel, ohne
        dass jemand daran denken muss.
        """
        herkunft = regeln.herkunft_von_lint(regel)
        if herkunft == regeln.OFFEN:
            return
        if herkunft == regeln.EINZELN:
            hinweis = regeln.quellenhinweis(regel)
            self.befunde.append(Befund(
                zeile, regel, WARNUNG,
                f"{meldung} — {hinweis}" if hinweis else meldung, korrektur))
            return
        self.befunde.append(Befund(zeile, regel, FEHLER, meldung, korrektur))

    def warnung(self, zeile: int, regel: str, meldung: str, korrektur: str = "") -> None:
        self.befunde.append(Befund(zeile, regel, WARNUNG, meldung, korrektur))

    @property
    def anzahl_fehler(self) -> int:
        return sum(1 for b in self.befunde if b.schwere == FEHLER)

    @property
    def anzahl_warnungen(self) -> int:
        return sum(1 for b in self.befunde if b.schwere == WARNUNG)

    @property
    def ok(self) -> bool:
        return self.anzahl_fehler == 0

    def als_text(self, datei: str) -> str:
        zeilen = [b.als_zeile(datei) for b in self.befunde]
        zeilen.append(f"lint: {self.anzahl_fehler} Fehler, {self.anzahl_warnungen} Warnungen")
        return "\n".join(zeilen)

    def als_dict(self) -> dict:
        return {
            "ok": self.ok,
            "fehler": self.anzahl_fehler,
            "warnungen": self.anzahl_warnungen,
            "befunde": [b.als_dict() for b in self.befunde],
        }


# ── Frontmatter ─────────────────────────────────────────────────────────────

def _feldzeile(kopf_roh: str, feld: str) -> int:
    """Die Zeile, in der ein Feld im Frontmatter steht — für die Meldung."""
    for nummer, zeile in enumerate(kopf_roh.splitlines(), start=1):
        if zeile.strip().startswith(f"{feld}:"):
            return nummer + 1
    return 1


def pruefe_datum(wert, zeile: int, bericht: Bericht) -> None:
    """Nur ein existierendes ISO-Datum.

    Bis v0.1.2 rutschte `datum: morgen` unbemerkt durch und stand wörtlich im
    Brief; `2026-13-45` endete in einem Traceback aus PyYAML.
    """
    if isinstance(wert, dt.date):
        return
    text = str(wert).strip()
    # `fromisoformat` nimmt seit Python 3.11 auch das Basisformat `20260825`.
    # Der Datenvertrag nennt JJJJ-MM-TT — was dort steht, gilt.
    try:
        if not ISO_DATUM.match(text):
            raise ValueError(text)
        dt.date.fromisoformat(text)
    except ValueError:
        bericht.fehler(
            zeile, "datum",
            f"„{text}“ ist kein Datum",
            "als ISO-Datum schreiben, z. B. 2026-08-25 — die Ausgabeform bestimmt das Profil",
        )


def _melde_unbekannte(
    schluessel, erlaubt: frozenset, regel: str, kopf_roh: str, bericht: Bericht
) -> None:
    """Ein Feld, das niemand liest, ist ein Fehler — kein Grund zum Schweigen.

    Bis v0.4.0 verwarf der Renderer jeden Schlüssel, den er nicht abfragte.
    `signatur:` im Brief blieb damit wirkungslos, ohne ein Wort. Das
    widerspricht der Zusage, mit der das Werkzeug antritt: abbrechen statt
    still etwas anderes zu setzen.
    """
    import difflib

    for feld in schluessel:
        if feld in erlaubt:
            continue
        nah = difflib.get_close_matches(str(feld).lower(), sorted(erlaubt), n=1, cutoff=0.6)
        rat = (f"meintest du `{nah[0]}`?" if nah
               else "erlaubt sind: " + ", ".join(sorted(erlaubt)))
        bericht.fehler(
            _feldzeile(kopf_roh, str(feld)), regel,
            f"`{feld}` ist kein Feld des Datenvertrags", rat,
        )


def pruefe_frontmatter(kopf: dict, kopf_roh: str, bericht: Bericht) -> None:
    _melde_unbekannte(kopf.keys(), FRONTMATTER_FELDER, "frontmatter", kopf_roh, bericht)
    if isinstance(kopf.get("infoblock"), dict):
        _melde_unbekannte(
            kopf["infoblock"].keys(), INFOBLOCK_FELDER, "infoblock", kopf_roh, bericht)

    for feld in PFLICHTFELDER:
        if not kopf.get(feld):
            bericht.fehler(1, feld, "Pflichtfeld fehlt", f"`{feld}:` im Frontmatter ergänzen")

    if kopf.get("datum") is not None:
        pruefe_datum(kopf["datum"], _feldzeile(kopf_roh, "datum"), bericht)

    empfaenger = kopf.get("empfaenger")
    if empfaenger:
        zeilen = [empfaenger] if isinstance(empfaenger, str) else list(empfaenger)
        ort = _feldzeile(kopf_roh, "empfaenger")
        if len(zeilen) > ANSCHRIFT_MAX_ZEILEN:
            bericht.fehler(
                ort, "empfaenger", f"{len(zeilen)} Zeilen",
                f"die Anschriftzone fasst {ANSCHRIFT_MAX_ZEILEN} Zeilen — Angaben zusammenfassen",
            )
        if any(not str(z).strip() for z in zeilen):
            bericht.fehler(ort, "empfaenger", "Leerzeile im Anschriftfeld",
                           "die Norm lässt im Anschriftfeld keine Leerzeilen zu")
        if len(zeilen) >= 2:
            letzte = str(zeilen[-1]).strip()
            vorletzte = str(zeilen[-2]).strip()
            if letzte.isupper() and len(letzte) > 3 and not vorletzte.isupper():
                bericht.warnung(
                    ort, "empfaenger",
                    f"„{letzte}“ sieht nach einer Auslandsanschrift aus",
                    "bei Auslandspost gehören Bestimmungsort und Land in Großbuchstaben",
                )

    vermerke = kopf.get("vermerke") or []
    if isinstance(vermerke, str):
        vermerke = [vermerke]
    if len(vermerke) > VERMERKE_MAX_ZEILEN:
        bericht.fehler(
            _feldzeile(kopf_roh, "vermerke"), "vermerke", f"{len(vermerke)} Zeilen",
            f"die Zusatz- und Vermerkzone fasst {VERMERKE_MAX_ZEILEN} Zeilen",
        )

    betreff = str(kopf.get("betreff") or "").strip()
    if betreff:
        ort = _feldzeile(kopf_roh, "betreff")
        if betreff.lower().startswith("betreff"):
            bericht.fehler(ort, "betreff", "beginnt mit dem Leitwort „Betreff“",
                           "das Leitwort entfällt — der Betreff steht für sich")
        if betreff.endswith("."):
            bericht.fehler(ort, "betreff", "endet mit einem Punkt",
                           "der Betreff steht ohne Schlusspunkt")
        if len(betreff) > BETREFF_MAX_ZEICHEN:
            bericht.fehler(
                ort, "betreff", f"{len(betreff)} Zeichen",
                f"höchstens zwei Zeilen, das sind rund {BETREFF_MAX_ZEICHEN} Zeichen",
            )

    anrede = str(kopf.get("anrede") or "").strip()
    if anrede and not anrede.endswith(","):
        bericht.fehler(_feldzeile(kopf_roh, "anrede"), "anrede", "endet nicht mit Komma",
                       "nach DIN endet die Anrede mit einem Komma")

    gruss = str(kopf.get("gruss") or "").strip()
    if gruss.endswith(","):
        bericht.fehler(_feldzeile(kopf_roh, "gruss"), "gruss", "endet mit Komma",
                       "die Grußformel steht ohne Komma")

    infoblock = kopf.get("infoblock") or {}
    if isinstance(infoblock, dict):
        ort = _feldzeile(kopf_roh, "infoblock")
        for schluessel, wert in infoblock.items():
            if wert is None:
                continue
            text = str(wert)
            if len(text) > INFOBLOCK_WERT_MAX:
                bericht.fehler(
                    ort, f"infoblock.{schluessel}", f"{len(text)} Zeichen",
                    f"höchstens {INFOBLOCK_WERT_MAX} — sonst passt die Zeile nicht in die 75 mm",
                )
            if schluessel == "email" and not EMAIL_MUSTER.match(text):
                bericht.fehler(ort, "infoblock.email", f"„{text}“ ist keine E-Mail-Adresse",
                               "Form: name@example.de")
            if schluessel in ("telefon", "fax") and not TELEFON_MUSTER.match(text):
                bericht.warnung(
                    ort, f"infoblock.{schluessel}", f"„{text}“ folgt nicht der Schreibweise nach DIN",
                    "Vorwahl mit Leerzeichen, Durchwahl mit Bindestrich: 0941 620-9800",
                )


# ── Body ────────────────────────────────────────────────────────────────────

def pruefe_body(body: str, versatz: int, bericht: Bericht) -> None:
    for nummer, zeile in enumerate(body.splitlines(), start=1 + versatz):
        if zeile.endswith("  ") and zeile.strip():
            bericht.warnung(
                nummer, "umbruch", "zwei Leerzeichen am Zeilenende erzeugen einen Umbruch",
                "besser einen Backslash setzen — zwei Leerzeichen sieht man in keiner Vorschau",
            )
        if "\t" in zeile:
            bericht.warnung(nummer, "tabulator", "Tabulator im Text wird zu einem Leerzeichen",
                            "Tabulatoren entfernen")
        for treffer in URL_MUSTER.finditer(zeile):
            roh = treffer.group().rstrip(".,;:)")
            zerlegt = urlparse(roh)
            if not zerlegt.netloc or " " in roh:
                bericht.fehler(nummer, "url", f"„{roh}“ ist keine wohlgeformte Adresse",
                               "Schema und Hostname prüfen")


# Keine eigene Glyphenprüfung.
#
# Der Auftrag sah vor, jedes Zeichen gegen die cmap der Profilschrift zu halten.
# Gemessen am 25.08.2026 ist das überflüssig und wäre die schlechtere Lösung:
#
#   1. Mit `ignore_system_fonts` und PDF/A bricht Typst selbst ab und nennt das
#      Zeichen: `the text "🙂" could not be displayed with font "Libertinus Serif"`.
#   2. Ohne PDF/A entsteht Tofu — und weil das Zeichen dann im PDF-Text fehlt,
#      schlägt die Vollständigkeitsprüfung in `verify` an.
#
# Eine selbst gepflegte Zeichenliste könnte dagegen von der Wirklichkeit
# abweichen: Sie veraltet mit jeder Schriftversion und meldet dann Zeichen als
# fehlend, die es gibt — oder umgekehrt. Der Renderer weiß es genau.
#
# Der Preis ist Zeit: Der Befund kommt nach dem Render statt in Millisekunden.
