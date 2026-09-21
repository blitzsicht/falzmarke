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
from difflib import SequenceMatcher

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


# Reihenfolge ist wesentlich: erst die Striche (--- vor --), dann die
# Anführungszeichen, dann die geschützten Leerzeichen — sonst zerlegt eine
# Ersetzung die Vorlage der nächsten.
#
# Der zweite Eintrag ist der Name der Regel in `regeln/din5008.yaml`. Steht
# dort keine (None), ist der Schritt keine Normaussage, sondern Satztechnik
# des Werkzeugs: Geviertstriche und deutsche Anführungszeichen setzt jeder
# Setzkasten so, dafür braucht es die Norm nicht.
SCHRITTE = [
    (_striche, None),
    (_anfuehrungszeichen, None),
    (_abkuerzungen, "_abkuerzungen"),
    (_datum, "_datum"),
    (_einheiten, "_einheiten"),
    (_paragraf, None),
    (_vor_angabe, "_vor_angabe"),
]


def anwenden(text: str) -> str:
    """Der vollständige Pass — aber nur, soweit die Quellenlage ihn trägt.

    Ein Schritt, dessen Regel nur in einer einzigen Quelle steht, ändert den
    Text **nicht**. Eine stille Ersetzung auf dünner Grundlage wäre der
    schlechteste Fall: Der Brief sähe anders aus, als er geschrieben wurde,
    und niemand erführe warum. `vorschlaege()` sammelt stattdessen die Stellen,
    an denen der Schritt etwas geändert hätte; `markdown.lies()` macht daraus
    je Stelle einen Hinweis und `falzmarke lint` eine Warnung. Die Warnung ist
    der Ersatz für die Ersetzung, nicht ihre Begleitung: Trägt die Regel ihre
    Stufe, wird ersetzt und nicht gewarnt.
    """
    from falzmarke import regeln

    for schritt, regelname in SCHRITTE:
        if regelname is None or regeln.darf_automatisch_ersetzen(regelname):
            text = schritt(text)
    return text


def _stellen(text: str, geaendert: str) -> list[str]:
    """Die Stellen von `text`, an denen `geaendert` abweicht — je mit dem Wort
    links und rechts davon, damit man sie im Brief wiederfindet.

    Ein Schritt ist hier ein Schwarzkasten: Sein Ergebnis wird mit der
    Vorlage verglichen, statt seine Muster ein zweites Mal zu führen. Sonst
    stünde jede Regel an zwei Stellen, und eine davon könnte altern.
    Überlappende Stellen werden eine (`u. a. m.` ergibt eine, nicht zwei).
    """
    spannen: list[list[int]] = []
    for art, von, bis, _, _ in SequenceMatcher(None, text, geaendert, autojunk=False).get_opcodes():
        if art == "equal":
            continue
        while von > 0 and not text[von - 1].isspace():
            von -= 1
        while bis < len(text) and not text[bis].isspace():
            bis += 1
        if spannen and von <= spannen[-1][1]:
            spannen[-1][1] = max(spannen[-1][1], bis)
        else:
            spannen.append([von, bis])
    return [text[von:bis] for von, bis in spannen]


def vorschlaege(text: str) -> list[tuple[str, str]]:
    """Wo ein zurückgehaltener Schritt etwas geändert hätte.

    Gibt je Stelle ein Paar (Regelkennung, Stelle) zurück, die Stelle so, wie
    sie im Text steht — leer, wenn nichts anzumerken ist. Der Text selbst
    bleibt unberührt.

    Eine Regel ohne Beleg (`offen`) taucht hier nicht auf: Sie wird weder
    ersetzt noch gemeldet, wie im Linter (`regeln.deckel`).
    """
    from falzmarke import regeln

    offen = []
    for schritt, regelname in SCHRITTE:
        if regelname is None or regeln.darf_automatisch_ersetzen(regelname):
            continue
        regel = regeln.fuer_typografie(regelname)
        if regeln.deckel(regel) == regeln.DECKEL_KEINE:
            continue
        geaendert = schritt(text)
        if geaendert == text:
            continue
        kennung = regel["id"] if regel else regelname
        for stelle in _stellen(text, geaendert):
            offen.append((kennung, stelle))
    return offen
