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

#: Was NICHT geprüft wird — und warum. Alles andere wird gefunden.
#:
#: Die Liste stand hier bis zum 29.08.2026 andersherum: als Aufzählung der neun
#: geprüften Dateien. Damit wuchs die Lücke, gegen die es diese Prüfung gibt,
#: auf einer zweiten Ebene weiter — vierzehn Markdown-Dateien standen nicht
#: darin, und wer künftig in einer davon einen Paragrafen nennt, wäre nicht
#: geprüft worden. Eine Ausnahme muss man begründen, eine Aufnahme nicht.
NICHT_GEPRUEFT = {
    # Ein Eintrag wird nicht überschrieben, sondern von einem späteren
    # abgelöst. Ihn nachträglich zu verlinken hieße, Geschichte zu ändern.
    "docs/entscheidungen/": "Entscheidungen halten einen Stand fest",
    "CHANGELOG.md": "ein Changelog wird nicht nachträglich umgeschrieben",
    # Erzeugt aus dem Quellen-Register (scripts/quellenlage.py) und trägt
    # dessen URLs ohnehin.
    "skill/references/din5008.md": "erzeugter Abschnitt aus dem Register",
    # Lizenztexte fremder Pakete — nicht unser Fließtext.
    "THIRD_PARTY_LICENSES.md": "fremde Lizenztexte",
}


def _zu_pruefen() -> list[str]:
    """Jede Markdown-Datei im Repository, außer den begründeten Ausnahmen.

    Bewusst kein `rglob` über alles: `.venv`, `bau/` und Worktrees enthalten
    fremde Dateien, und die Prüfung soll dieses Repository messen.
    """
    kandidaten = sorted(
        list(REPO.glob("*.md")) + list(REPO.glob("docs/*.md"))
        + list(REPO.glob("skill/*.md")) + list(REPO.glob("skill/references/*.md"))
    )
    heraus = []
    for pfad in kandidaten:
        relativ = pfad.relative_to(REPO).as_posix()
        if any(relativ == a or relativ.startswith(a) for a in NICHT_GEPRUEFT):
            continue
        heraus.append(relativ)
    return heraus


GEPRUEFT = _zu_pruefen()

#: Eine Vorschrift oder ein RFC, wie er im Text auftaucht.
#:
#: Das Kürzel ist **nicht aufgezählt**. Bis zum 29.08.2026 stand hier
#: `(?:HGB|GmbHG|AktG|GenG|UWG|UStG)` — sechs Gesetze, und ein siebtes wäre
#: still durchgerutscht. Genau davor warnt #124: „sonst wächst die Lücke beim
#: nächsten Absatz von selbst nach." Ein Muster, das nur kennt, was schon da
#: ist, wächst nicht mit.
#:
#: Ein Kürzel trägt **mindestens zwei Großbuchstaben** — HGB, GmbHG, GewO,
#: BetrVG, StromGVV, MoPeG. Ein gewöhnliches Wort hat einen: `§ 5 Absatz`,
#: `§ 12 dieser`. Der erste Anlauf ließ ein einzelnes Großwort zu und las
#: „Absatz" als Gesetz; die Gegenprobe unten hat es gefunden.
NENNUNG = re.compile(
    r"§+ ?\d+[a-z]?(?: Abs(?:\.|atz) ?\d+[a-z]?)? "
    r"(?=[A-Za-z]{2,10}\b)(?:[a-z]*[A-ZÄÖÜ]){2}[A-Za-z]*\b"
    r"|\bRFC ?\d+\b"
    r"|\b(?:EHUG|MoPeG)\b"
)

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


# ── Die Prüfung wächst mit (#124, ergänzt am 29.08.2026) ────────────────────

def test_die_dateiliste_wird_abgeleitet_und_nicht_gepflegt():
    """Sie stand hier als Aufzählung von neun Dateien — vierzehn fehlten.

    Eine Aufnahme darf niemand vergessen können; eine Ausnahme muss begründet
    sein. Deshalb ist die Liste jetzt herum: Was hier fehlt, wird geprüft.
    """
    assert len(GEPRUEFT) >= 18, f"nur {len(GEPRUEFT)} Dateien — die Ableitung greift nicht"
    for pflicht in ("README.md", "docs/recht.md", "CONTRIBUTING.md", "SECURITY.md",
                    "docs/normmasse.md", "skill/references/markdown.md"):
        assert pflicht in GEPRUEFT, f"{pflicht} wird nicht geprüft"


def test_und_die_ausnahmen_bleiben_draussen():
    """Gegenprobe: Ohne sie könnte die Ableitung alles einsammeln, auch was
    dort nicht hingehört — und die Begründungen wären wirkungslos."""
    for ausnahme in ("CHANGELOG.md", "skill/references/din5008.md",
                     "THIRD_PARTY_LICENSES.md"):
        assert ausnahme not in GEPRUEFT, f"{ausnahme} sollte ausgenommen sein"


@pytest.mark.parametrize("nennung", [
    "§ 13 DDG", "§ 5 TMG", "§ 823 BGB", "§ 15 Abs. 1 UStG", "RFC 9051", "MoPeG",
])
def test_das_muster_kennt_auch_ungenannte_gesetze(nennung):
    """Es zählte sechs Kürzel auf; ein siebtes wäre still durchgerutscht.

    Genau davor warnt #124: „sonst wächst die Lücke beim nächsten Absatz von
    selbst nach." Keines der hier geprüften Kürzel kommt im Repository vor —
    das ist der Punkt.
    """
    assert nennung in _erste_nennungen(f"Dazu sagt {nennung} etwas.")


@pytest.mark.parametrize("kein_gesetz", [
    "§ 5 Absatz", "§ 12 dieser", "§§ 3 und", "RFCs", "§ 7 der",
])
def test_und_haelt_gewoehnlichen_text_heraus(kein_gesetz):
    """Gegenprobe zum Muster selbst.

    Ein Muster, das jede Zahl hinter einem Paragrafenzeichen für ein Gesetz
    hält, meldet Fundstellen, die es nicht gibt — und wird dann abgeschaltet.
    """
    assert not _erste_nennungen(f"Wie in {kein_gesetz} Fassung beschrieben.")


def test_das_mopeg_zeigt_auf_das_aenderungsgesetz():
    """Nicht auf das geänderte.

    Bis zum 29.08.2026 zeigte der Link in `docs/recht.md` auf `hgb/__125.html`.
    Wer nachschlagen wollte, was das MoPeG anordnet, fand dort den heutigen
    § 125 HGB — und kein Wort darüber, dass § 125a aufgehoben wurde.
    """
    quelle = regeln.quellen().get("mopeg")
    assert quelle, "das MoPeG fehlt im Quellen-Register"
    assert "buzer.de" in quelle["url"], quelle["url"]
    text = _text("docs/recht.md")
    assert quelle["url"] in text, "docs/recht.md verweist woandershin"
    assert "gesetze-im-internet.de/hgb/__125.html)" not in text.split("MoPeG]")[1][:80]
