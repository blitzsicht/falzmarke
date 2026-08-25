"""Was im Markdown steht, muss im PDF ankommen — vollständig.

Diese Prüfung ersetzt kein Einzelfall-Repertoire, sie fängt die Klasse: stille
Textverluste durch Typst-Kommentarzeichen, Überlauf aus dem Satzspiegel und
fehlende Glyphen schlagen hier gemeinsam an, auch die Fälle, an die niemand
gedacht hat.

Anlass ist ein gemessener Verlust: `Aktenzeichen 12//345 und danach mehr Text`
endete im PDF nach `12`, weil `//` für Typst ein Zeilenkommentar ist — ohne
Fehler, ohne Warnung.
"""

from __future__ import annotations

import re

import pytest

import normbrief
from conftest import BEISPIELE, REPO

PROFILE = REPO / "skill" / "typst" / "profiles"


def nur_text(markdown: str) -> str:
    """Markdown-Markup entfernen, damit der reine Inhalt übrig bleibt."""
    text = markdown
    text = re.sub(r"^\s*\|.*$", "", text, flags=re.M)      # Tabellen: eigene Prüfung
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)   # Aufzählungszeichen
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.M)
    text = text.replace("**", "").replace("*", "")
    text = re.sub(r"\\(.)", r"\1", text)                   # Markdown-Escapes
    text = text.replace("\\", "")                          # harter Umbruch
    return text


def verdichtet(text: str) -> str:
    """Alles entfernen, was zwischen Quelle und PDF legitim abweichen darf.

    Bindestriche fallen dabei komplett weg — sonst wäre nicht unterscheidbar,
    ob ein Strich am Zeilenende von der Silbentrennung stammt oder zum Wort
    gehört (`Fünf-Minuten-Takt` wird zu `Fünf-Minuten-\nTakt` umbrochen).
    Die Prüfung sucht fehlenden Text, nicht fehlende Zeichensetzung.
    """
    text = text.replace("­", "")                      # weiches Trennzeichen
    text = text.replace(" ", " ").replace(" ", " ")
    text = text.replace("-", "").replace("‑", "")
    return re.sub(r"\s+", "", text)


def pdf_text(pfad) -> str:
    import pdfplumber

    with pdfplumber.open(str(pfad)) as dokument:
        return "\n".join(seite.extract_text() or "" for seite in dokument.pages)


@pytest.mark.parametrize("name", [p.stem for p in BEISPIELE])
def test_beispieltext_kommt_vollstaendig_an(gerendert, name):
    pdf, _ = gerendert[name]
    quelle = (REPO / "examples" / f"{name}.md").read_text(encoding="utf-8")
    body = quelle.split("\n---", 2)[1].lstrip("\n-")

    # Zeilenweise, nicht absatzweise: Zwischen einem Absatz und der folgenden
    # Aufzählung steht im PDF das Aufzählungszeichen, in der Quelle nichts —
    # als ein Block verglichen, würde das als Verlust erscheinen.
    im_pdf = verdichtet(pdf_text(pdf))
    fehlend = [
        zeile.strip()[:70]
        for zeile in nur_text(body).splitlines()
        if len(verdichtet(zeile)) >= 12 and verdichtet(zeile) not in im_pdf
    ]
    assert not fehlend, "Im PDF fehlt Text aus der Quelle:\n" + "\n".join(fehlend)


@pytest.mark.parametrize(
    "zeile,beschreibung",
    [
        ("unser Aktenzeichen 12//345 und danach mehr Text.", "doppelter Schrägstrich"),
        ("Der Zeitraum 01/2026 bis 12/2026 ist gemeint.", "einfache Schrägstriche"),
        ("Ein /* auffälliges */ Zeichenpaar mitten im Satz.", "Blockkommentar-Zeichen"),
        ("Die Menge beträgt 3 \\* 4 Stück insgesamt.", "geschütztes Sternchen"),
        ("Ein \\_Unterstrich\\_ soll sichtbar bleiben.", "geschützter Unterstrich"),
        ("Preis 12,50 EUR — inklusive #Nummer und @Zeichen.", "Sonderzeichen"),
    ],
)
def test_heikle_zeichen_ueberleben(tmp_path, zeile, beschreibung):
    brief = tmp_path / "b.md"
    brief.write_text(
        "---\nprofil: example\nempfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]\n"
        f"datum: 2026-08-25\nbetreff: Probe\nanrede: Sehr geehrte Damen und Herren,\n---\n{zeile}\n",
        encoding="utf-8",
    )
    pdf, _ = normbrief.rendere(brief, tmp_path / "b.pdf", profil_verzeichnis=PROFILE)
    erwartet = verdichtet(nur_text(zeile))
    assert erwartet in verdichtet(pdf_text(pdf)), (
        f"{beschreibung}: Text ging verloren.\nErwartet: {zeile}\n"
        f"Im PDF:   {pdf_text(pdf)[:400]}"
    )
