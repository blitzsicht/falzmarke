#!/usr/bin/env python3
"""Der Typografie-Pass nach DIN 5008.

Läuft ausschließlich auf Textknoten, nie auf Adressen, URLs oder E-Mails — dort
würde ein geschütztes Leerzeichen den Wert unbrauchbar machen.

Die Ersetzungen passieren hier in Python und nicht über Typsts eingebaute
Kurzschreibweisen. Beides führt zum selben Ergebnis, aber diese Fassung ist
deterministisch und lässt sich Zeichen für Zeichen prüfen; Typsts Verhalten
hängt an Spracheinstellungen und Version.
"""

from __future__ import annotations

import re

NBSP = " "          # geschütztes Leerzeichen
SCHMAL = " "        # schmales geschütztes Leerzeichen

# Abkürzungen, die DIN 5008 mit geschütztem Leerzeichen schreibt.
ABKUERZUNGEN = [
    (r"z\. ?B\.", f"z.{NBSP}B."),
    (r"u\. ?a\. ?m\.", f"u.{NBSP}a.{NBSP}m."),
    (r"u\. ?a\.", f"u.{NBSP}a."),
    (r"d\. ?h\.", f"d.{NBSP}h."),
    (r"i\. ?d\. ?R\.", f"i.{NBSP}d.{NBSP}R."),
    (r"o\. ?Ä\.", f"o.{NBSP}Ä."),
    (r"u\. ?U\.", f"u.{NBSP}U."),
    (r"z\. ?T\.", f"z.{NBSP}T."),
    (r"i\. ?A\.", f"i.{NBSP}A."),
    (r"i\. ?V\.", f"i.{NBSP}V."),
    (r"s\. ?o\.", f"s.{NBSP}o."),
    (r"s\. ?u\.", f"s.{NBSP}u."),
    (r"z\. ?Hd\.", f"z.{NBSP}Hd."),
]

# Einheiten und Zeichen, die nicht vom Zahlwert getrennt werden dürfen.
EINHEITEN = [
    "%", "‰", "€", "EUR", "CHF", "km", "kg", "mm", "cm", "m²", "m³", "°C",
    "Std.", "Uhr", "Mio.", "Mrd.", "St.", "Stk.",
]

MONATE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

# Nach diesen Kürzeln folgt eine Angabe, die dazugehört.
VOR_ANGABE = ["Nr.", "Tel.", "Str.", "Abs.", "Art.", "S.", "Rechnung", "Az."]


def _abkuerzungen(text: str) -> str:
    for muster, ersatz in ABKUERZUNGEN:
        text = re.sub(rf"\b{muster}", ersatz, text)
    return text


def _einheiten(text: str) -> str:
    for einheit in EINHEITEN:
        text = re.sub(rf"(\d)\s+{re.escape(einheit)}(?![\w])", rf"\1{NBSP}{einheit}", text)
    return text


def _paragraf(text: str) -> str:
    return re.sub(r"§\s+(\d)", rf"§{NBSP}\1", text)


def _datum(text: str) -> str:
    """25. August → 25.<NBSP>August. Tag und Monat gehören zusammen."""
    monate = "|".join(MONATE)
    return re.sub(rf"(\b\d{{1,2}}\.)\s+({monate})\b", rf"\1{NBSP}\2", text)


def _vor_angabe(text: str) -> str:
    for kuerzel in VOR_ANGABE:
        text = re.sub(rf"\b{re.escape(kuerzel)}\s+(\S)", rf"{kuerzel}{NBSP}\1", text)
    return text


def _striche(text: str) -> str:
    """--- ergibt einen Geviertstrich, -- einen Halbgeviertstrich."""
    text = text.replace("---", "—")
    return re.sub(r"(?<!-)--(?!-)", "–", text)


def _anfuehrungszeichen(text: str) -> str:
    """Gerade Zeichen zu deutschen Anführungszeichen."""
    text = re.sub(r'"([^"]*)"', "„\\1“", text)
    text = re.sub(r"(?<![\w'])'([^']*)'(?![\w])", "‚\\1‘", text)
    return text


def anwenden(text: str) -> str:
    """Der vollständige Pass, in fester Reihenfolge.

    Erst die Striche (--- vor --), dann Anführungszeichen, dann die
    geschützten Leerzeichen — sonst zerlegt eine Ersetzung die Vorlage der
    nächsten.
    """
    text = _striche(text)
    text = _anfuehrungszeichen(text)
    text = _abkuerzungen(text)
    text = _datum(text)
    text = _einheiten(text)
    text = _paragraf(text)
    text = _vor_angabe(text)
    return text
