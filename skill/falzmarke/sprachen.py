"""Beschriftung je Sprache — deutsche Geometrie, fremde Wörter.

Für Briefe an Empfänger, die kein Deutsch lesen. Die Geometrie bleibt dabei
unverändert: Anschriftfeld, Informationsblock, Falzmarken und das 12-pt-Raster
sind Maße der DIN 5008 und hängen nicht an der Sprache. Es ändern sich die
Zeichenketten, die Monatsnamen, die Seitenzählung und `text.lang` — Letzteres
nicht der Optik wegen, sondern für die Silbentrennung.

**Die englischen Wörter sind nicht normbelegt.** DIN 5008 ist eine deutsche Norm
und schreibt keine englische Beschriftung vor; es gibt in ihr kein „Your
reference". Was hier steht, ist die im Geschäftsverkehr übliche Entsprechung —
eine Konvention, keine Fundstelle. Wer einen Brief in englischer Beschriftung
setzt, bekommt deshalb ein Blatt, dessen **Maße** belegt sind und dessen
**Wörter** es nicht sind. Das ist ein Unterschied, den dieses Repository sonst
sorgfältig auseinanderhält (siehe „Quellenlage je Regel"), und er gilt auch hier.

Aus demselben Grund ändert die Sprache nichts an einer Prüfung: `verify` misst
Zonen und Abstände, keine Wörter. Ein englischer Brief fällt weder durch noch
besteht er leichter.

Das Datum folgt der britischen Schreibweise (26 August 2026), nicht der
amerikanischen (August 26, 2026): Ein DIN-5008-Brief ist ein europäischer
Geschäftsbrief, und die Tag-Monat-Jahr-Folge bleibt damit dieselbe wie im
deutschen Original — wer die Zeile überfliegt, verwechselt Tag und Monat nicht.
"""

from __future__ import annotations

VORGABE = "de"

# Reihenfolge und Schlüssel stehen in lint.INFOBLOCK_REIHENFOLGE — hier steht
# nur, wie das Leitwort heisst. tests/test_sprachen.py hält beide Mengen
# zusammen: Eine Sprache, der ein Leitwort fehlt, würde sonst eine leere Zeile
# in den Informationsblock setzen, statt aufzufallen.
LEITWOERTER = {
    "de": {
        "ihr_zeichen": "Ihr Zeichen",
        "ihre_nachricht_vom": "Ihre Nachricht vom",
        "unser_zeichen": "Unser Zeichen",
        "unsere_nachricht_vom": "Unsere Nachricht vom",
        "ansprechpartner": "Name",
        "telefon": "Telefon",
        "fax": "Fax",
        "email": "E-Mail",
        "datum": "Datum",
    },
    "en": {
        "ihr_zeichen": "Your reference",
        "ihre_nachricht_vom": "Your letter of",
        "unser_zeichen": "Our reference",
        "unsere_nachricht_vom": "Our letter of",
        "ansprechpartner": "Contact",
        "telefon": "Phone",
        "fax": "Fax",
        "email": "Email",
        "datum": "Date",
    },
}

MONATE = {
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni",
           "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}

# Wörter, die im Satz selbst stehen. „seite“ ist eine Vorlage mit zwei Stellen:
# laufende Seite und Gesamtzahl.
WOERTER = {
    "de": {"anlage": "Anlage", "anlagen": "Anlagen", "verteiler": "Verteiler",
           "seite": "Seite {n} von {m}"},
    "en": {"anlage": "Enclosure", "anlagen": "Enclosures", "verteiler": "Copies to",
           "seite": "Page {n} of {m}"},
}

# Für Typst: Silbentrennung und Anführungszeichen hängen daran.
# Britisches Englisch, passend zur Datumsschreibweise oben.
GEBIET = {"de": ("de", "DE"), "en": ("en", "GB")}


def erlaubt() -> tuple[str, ...]:
    return tuple(LEITWOERTER)


def pruefe(sprache: str) -> str:
    """Gibt die Sprache zurück oder sagt, welche es gibt.

    Eine unbekannte Sprache still auf Deutsch zurückfallen zu lassen wäre die
    teuerste Art, den Tippfehler zu verstecken: Der Brief ginge deutsch
    beschriftet an einen Empfänger, der kein Deutsch liest.
    """
    if sprache not in LEITWOERTER:
        raise ValueError(
            f"sprache: „{sprache}“ gibt es nicht — vorhanden sind "
            + ", ".join(sorted(LEITWOERTER))
        )
    return sprache


def leitwort(sprache: str, schluessel: str) -> str:
    return LEITWOERTER[pruefe(sprache)][schluessel]


def wort(sprache: str, schluessel: str) -> str:
    return WOERTER[pruefe(sprache)][schluessel]


def monat(sprache: str, nummer: int) -> str:
    return MONATE[pruefe(sprache)][nummer - 1]
