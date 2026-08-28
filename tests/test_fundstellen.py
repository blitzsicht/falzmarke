"""Wer ein Gesetz oder einen RFC nennt, verlinkt ihn — und zwar dorthin, wo er steht.

Befund vom 28.08.2026 (#124): Das Werkzeug berief sich an vierundzwanzig Stellen
auf Gesetze und RFCs. Verlinkt war **eine** — und auch die nur, weil eine
Korrektur sie nötig gemacht hatte. Für die Maßregeln gibt es eine Quellenlage,
in der jede Regel ihre Herkunft nennt; für die Rechtsgrundlagen stand der nackte
Name im Text.

Zwei Dinge werden hier gehalten:

1. **Die erste Nennung je Datei ist verlinkt.** Weitere nicht — sonst wird der
   Text zur Linkwüste, und gelesen wird er trotzdem von vorn.
2. **Der Link zeigt dorthin, wo das Register hinzeigt.** Sonst entstehen zwei
   URLs für dasselbe Gesetz, und eine davon veraltet unbemerkt.

Was **nicht** geprüft wird: die Entscheidungen unter `docs/entscheidungen/`. Ein
Eintrag wird nicht überschrieben, sondern von einem späteren abgelöst; er nennt
seine Quellen über das Register, nicht über eigene Links. Ebenso wenig geprüft
wird die erzeugte Normreferenz — sie entsteht aus dem Register und trägt dessen
URLs ohnehin.
"""

from __future__ import annotations

import re
import sys

import pytest

from conftest import REPO, SKILL

sys.path.insert(0, str(SKILL))
from falzmarke import regeln                                     # noqa: E402

#: Fließtext, den ein Mensch liest — dort gilt die Regel.
GEPRUEFT = [
    "README.md",
    "docs/recht.md",
    "docs/email.md",
    "docs/architecture.md",
    "docs/cli.md",
    "docs/profiles.md",
    "skill/SKILL.md",
    "skill/references/frontmatter.md",
    "skill/references/stil.md",
]

#: Eine Vorschrift oder ein RFC, wie er im Text auftaucht.
NENNUNG = re.compile(r"§ ?\d+[a-z]? (?:HGB|GmbHG|AktG|GenG|UWG|UStG)|\bRFC \d+|\bEHUG\b")

#: Aufgehoben — die amtliche Sammlung führt nur geltendes Recht. Ein Verweis
#: ginge ins Leere, und genau das ist die Aussage der Stelle.
OHNE_FUNDSTELLE = {"§ 125a HGB"}


#: Der Changelog-Auszug in der README wird aus CHANGELOG.md erzeugt
#: (scripts/changelog.py). Er ist eine Sicht, kein eigener Text — und ein
#: Changelog-Eintrag wird nicht nachtraeglich umgeschrieben, so wenig wie eine
#: Entscheidung. Dieselbe Begruendung wie beim Ausklammern der Normreferenz.
ERZEUGT = [("<!-- changelog:anfang -->", "<!-- changelog:ende -->")]


def _text(pfad: str) -> str:
    text = (REPO / pfad).read_text(encoding="utf-8")
    for anfang, ende in ERZEUGT:
        while anfang in text and ende in text:
            text = text[:text.index(anfang)] + text[text.index(ende) + len(ende):]
    return text


def _erste_nennungen(text: str) -> dict[str, int]:
    """Nennung -> Position der ersten Erwähnung."""
    zuerst: dict[str, int] = {}
    for treffer in NENNUNG.finditer(text):
        zuerst.setdefault(treffer.group(0), treffer.start())
    return zuerst


def _ist_verlinkt(text: str, stelle: int) -> bool:
    """Steht die Nennung in einem Markdown-Link mit URL?"""
    for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", text):
        if m.start() <= stelle < m.end():
            return True
    return False


def test_die_dateiliste_traegt_ueberhaupt_nennungen():
    """Sonst prüfte alles darunter die leere Menge und wäre still grün."""
    gesamt = sum(len(_erste_nennungen(_text(p))) for p in GEPRUEFT)
    assert gesamt >= 8, f"nur {gesamt} Nennungen gefunden — die Dateiliste stimmt nicht mehr"


@pytest.mark.parametrize("pfad", GEPRUEFT)
def test_die_erste_nennung_ist_verlinkt(pfad):
    text = _text(pfad)
    ohne = [
        n for n, stelle in _erste_nennungen(text).items()
        if n not in OHNE_FUNDSTELLE and not _ist_verlinkt(text, stelle)
    ]
    assert not ohne, (
        f"{pfad}: erste Nennung ohne Fundstelle: {', '.join(sorted(ohne))}\n"
        "Wer sich auf eine Vorschrift beruft, sagt auch, wo sie steht. Die URL "
        "steht im Quellen-Register (skill/falzmarke/regeln/quellen.yaml)."
    )


def test_die_pruefung_wuerde_eine_nackte_nennung_bemerken():
    """Gegenprobe. Ohne sie belegt der Test oben nur, dass gerade alle verlinkt sind."""
    text = "Das steht in § 37a HGB und gilt.\n"
    zuerst = _erste_nennungen(text)
    assert "§ 37a HGB" in zuerst
    assert not _ist_verlinkt(text, zuerst["§ 37a HGB"]), "die Erkennung greift nicht"


def test_die_pruefung_erkennt_einen_link_als_solchen():
    """Die Gegenrichtung — sonst könnte sie jede Nennung für nackt halten."""
    text = "Das steht in [§ 37a HGB](https://www.gesetze-im-internet.de/hgb/__37a.html).\n"
    zuerst = _erste_nennungen(text)
    assert _ist_verlinkt(text, zuerst["§ 37a HGB"])


def test_kein_zweiter_pfad_zu_derselben_vorschrift():
    """Ein Gesetz, eine URL. Zwei laufen auseinander, und eine veraltet unbemerkt.

    Verglichen wird gegen das Quellen-Register: Jede Gesetzes- oder RFC-URL im
    Fließtext muss dort vorkommen. Andere Links (GitHub, PyPI, Wikimedia) sind
    davon nicht berührt.
    """
    bekannt = {q["url"].rstrip("/") for q in regeln.quellen().values() if q.get("url")}
    amtlich = re.compile(r"https://(?:www\.)?(?:gesetze-im-internet\.de|rfc-editor\.org|buzer\.de)/[^)\s]+")
    fremd = []
    for pfad in GEPRUEFT:
        for url in amtlich.findall(_text(pfad)):
            if url.rstrip("/.") not in bekannt:
                fremd.append(f"{pfad}: {url}")
    assert not fremd, (
        "Diese Fundstellen stehen nicht im Quellen-Register:\n  " + "\n  ".join(fremd) +
        "\nEntweder dort eintragen oder die vorhandene URL verwenden."
    )


def test_das_register_kennt_ueberhaupt_amtliche_quellen():
    """Vorbedingung zum Test darüber: Eine leere Menge weist nichts ab."""
    amtlich = [n for n, q in regeln.quellen().items()
               if q.get("art") == "primaerquelle" and q.get("url")]
    assert len(amtlich) >= 10, f"nur {len(amtlich)} Primärquellen mit URL im Register"
