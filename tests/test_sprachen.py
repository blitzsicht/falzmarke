"""Englische Beschriftung — und der Nachweis, dass die Maße davon unberührt bleiben.

Die Behauptung dieses Features ist eng: Es ändern sich Zeichenketten, Monatsnamen,
Seitenzählung und `text.lang`. Anschriftfeld, Informationsblock, Falzmarken und das
12-pt-Raster sind Werte der DIN 5008 und haben mit Sprache nichts zu tun.

Genau das prüft `test_die_masse_haengen_nicht_an_der_sprache`: derselbe Brief zweimal,
einmal deutsch und einmal englisch, und beide Messberichte müssen dieselben Zahlen
tragen. Ohne diese Prüfung wäre „die Geometrie bleibt unverändert" eine Behauptung.

Was hier NICHT geprüft wird, weil es nicht prüfbar ist: ob „Your reference" die richtige
Entsprechung für „Ihr Zeichen" ist. DIN 5008 kennt keine englischen Leitwörter — das ist
eine Konvention ohne Fundstelle, und das steht so in sprachen.py und in der Doku.
"""

from __future__ import annotations

import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "skill"))

from falzmarke import cli as falzmarke                           # noqa: E402
from falzmarke import geometrie, sprachen                        # noqa: E402
from falzmarke.lint import FRONTMATTER_FELDER, INFOBLOCK_REIHENFOLGE  # noqa: E402

BRIEF = """---
profil: example
{sprache}datum: 2026-08-26
empfaenger:
  - Example Ltd
  - Ms Jane Smith
  - 12 Sample Street
  - LONDON EC1A 1BB
betreff: Quotation no. 2026-0815
anrede: Dear Ms Smith,
infoblock:
  ihr_zeichen: ABC-12
  ansprechpartner: Erika Muster
gruss: Yours sincerely
anlagen:
  - Quotation 2026-0815
---

thank you for your enquiry.

Kind regards
"""


def _rendere(tmp_path, sprache: str | None):
    quelle = tmp_path / f"brief-{sprache or 'ohne'}.md"
    quelle.write_text(
        BRIEF.format(sprache=f"sprache: {sprache}\n" if sprache else ""), encoding="utf-8")
    pdf, form = falzmarke.rendere(quelle, tmp_path / f"{sprache or 'ohne'}.pdf")
    return pdf, form


def _text(pdf) -> str:
    import pdfplumber

    with pdfplumber.open(str(pdf)) as dokument:
        return "\n".join(seite.extract_text() or "" for seite in dokument.pages)


# ── Das Wörterbuch ist vollständig ──────────────────────────────────────────

@pytest.mark.parametrize("sprache", sprachen.erlaubt())
def test_jede_sprache_kennt_jedes_leitwort(sprache):
    """Ein fehlendes Leitwort ergäbe eine leere Zeile im Informationsblock.

    Die Reihenfolge steht in lint.INFOBLOCK_REIHENFOLGE, die Wörter in
    sprachen.LEITWOERTER — zwei Listen, die auseinanderlaufen können.
    """
    verlangt = {schluessel for schluessel, _ in INFOBLOCK_REIHENFOLGE} | {"datum"}
    vorhanden = set(sprachen.LEITWOERTER[sprache])
    assert verlangt <= vorhanden, f"{sprache}: es fehlen {sorted(verlangt - vorhanden)}"
    assert not (vorhanden - verlangt), (
        f"{sprache}: {sorted(vorhanden - verlangt)} steht im Wörterbuch, wird aber nie "
        "gesetzt — entweder tote Zeile oder vergessene Verdrahtung."
    )


@pytest.mark.parametrize("sprache", sprachen.erlaubt())
def test_jede_sprache_hat_zwoelf_monate_und_alle_woerter(sprache):
    assert len(sprachen.MONATE[sprache]) == 12
    assert set(sprachen.WOERTER[sprache]) == {"anlage", "anlagen", "verteiler", "seite"}
    assert "{n}" in sprachen.WOERTER[sprache]["seite"]
    assert "{m}" in sprachen.WOERTER[sprache]["seite"]


def test_die_deutsche_fassung_bleibt_die_vorgabe():
    """Wer nichts angibt, bekommt weiter einen deutschen Brief."""
    assert sprachen.VORGABE == "de"
    for schluessel, leitwort in INFOBLOCK_REIHENFOLGE:
        assert sprachen.LEITWOERTER["de"][schluessel] == leitwort, (
            f"{schluessel}: lint sagt „{leitwort}“, das Wörterbuch etwas anderes"
        )


def test_sprache_steht_im_datenvertrag():
    assert "sprache" in FRONTMATTER_FELDER


def test_eine_unbekannte_sprache_faellt_auf():
    """Stiller Rückfall auf Deutsch wäre die teuerste Art, den Tippfehler zu verstecken.

    Der Brief ginge deutsch beschriftet an jemanden, der kein Deutsch liest — und
    niemandem fiele es auf, bis er ankommt.
    """
    with pytest.raises(ValueError) as fehler:
        sprachen.pruefe("fr")
    assert "vorhanden sind" in str(fehler.value)


def test_eine_unbekannte_sprache_im_brief_bricht_den_render_ab(tmp_path):
    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        _rendere(tmp_path, "fr")
    assert "sprache" in str(fehler.value)


# ── Der Brief selbst ────────────────────────────────────────────────────────

def test_der_englische_brief_traegt_englische_leitwoerter(tmp_path):
    text = _text(_rendere(tmp_path, "en")[0])
    for wort in ("Your reference", "Contact", "Date", "Enclosure"):
        assert wort in text, f"„{wort}“ steht nicht im Brief"
    for deutsch in ("Ihr Zeichen", "Anlage\n", "Verteiler"):
        assert deutsch not in text, f"„{deutsch.strip()}“ ist stehen geblieben"


def test_das_datum_folgt_der_britischen_schreibweise(tmp_path):
    """26 August 2026, nicht 26. August und nicht August 26."""
    text = _text(_rendere(tmp_path, "en")[0])
    assert "26 August 2026" in text
    assert "26. August" not in text
    assert "August 26" not in text


# Ein einziges Mass haengt am gesetzten Text statt an einer Zonengrenze: Die
# rechte Kante des Informationsblocks liegt dort, wo sein laengster Eintrag
# endet. „26. August 2026“ traegt den deutschen Ordinalpunkt und ist damit
# breiter als „26 August 2026“ — gemessen 0,78 mm. Der Sollwert ist eine
# Obergrenze (≤ 200,0 mm), beide Sprachen halten sie ein.
#
# Die Ausnahme steht hier namentlich und wird unten selbst geprueft. Eine
# Toleranz ueber alle Masse waere der bequeme Weg gewesen — und haette eine
# echte Verschiebung mit durchgelassen.
TEXTABHAENGIG = {"Infoblock, x-rechts"}


def test_die_masse_haengen_nicht_an_der_sprache(tmp_path):
    """Der Kern: dieselben Zahlen, egal in welcher Sprache beschriftet.

    Verglichen werden Soll- UND Istwerte jeder Pruefung. Waere nur die Zahl der
    bestandenen Pruefungen verglichen, ginge eine verschobene Zone durch, solange
    sie in beiden Sprachen gleich verschoben waere.
    """
    deutsch = geometrie.pruefe(*_rendere(tmp_path, None)).als_dict()
    englisch = geometrie.pruefe(*_rendere(tmp_path, "en")).als_dict()

    assert deutsch["ok"] and englisch["ok"]
    nach_name = {p["name"]: p for p in deutsch["pruefungen"]}
    assert len(nach_name) == len(englisch["pruefungen"])

    assert not [
        (p["name"], nach_name[p["name"]]["soll"], p["soll"])
        for p in englisch["pruefungen"]
        if nach_name[p["name"]]["soll"] != p["soll"]
    ], "die Sollwerte selbst hängen an der Sprache — dann wäre es keine Beschriftung mehr"

    abweichend = [
        (p["name"], nach_name[p["name"]]["ist"], p["ist"])
        for p in englisch["pruefungen"]
        if nach_name[p["name"]]["ist"] != p["ist"]
    ]
    unerwartet = [a for a in abweichend if a[0] not in TEXTABHAENGIG]
    assert not unerwartet, f"Maße unterscheiden sich je Sprache: {unerwartet[:4]}"


def test_die_eine_ausnahme_bleibt_klein_und_bestanden(tmp_path):
    """Gegenprobe zur Ausnahmeliste: Sie darf nicht zum Freibrief werden.

    Ohne diese Pruefung koennte die rechte Kante des Informationsblocks in einer
    Sprache um Zentimeter wandern, und TEXTABHAENGIG haette es gedeckt.
    """
    deutsch = {p["name"]: p for p in
               geometrie.pruefe(*_rendere(tmp_path, None)).als_dict()["pruefungen"]}
    englisch = {p["name"]: p for p in
                geometrie.pruefe(*_rendere(tmp_path, "en")).als_dict()["pruefungen"]}

    for name in TEXTABHAENGIG:
        assert name in deutsch, f"{name} gibt es nicht mehr — Ausnahmeliste veraltet"
        assert deutsch[name]["bestanden"] and englisch[name]["bestanden"]
        unterschied = abs(float(deutsch[name]["ist"]) - float(englisch[name]["ist"]))
        assert unterschied < 2.0, (
            f"{name} weicht um {unterschied:.2f} mm ab — das ist mehr als die Breite "
            "eines Satzzeichens und keine Frage der Beschriftung mehr."
        )


def test_die_seitenzahl_wird_in_beiden_sprachen_gefunden(tmp_path):
    """Zuvor war der deutsche Wortlaut fest verdrahtet — jeder englische
    Mehrseiter fiel an dieser Prüfung durch, ohne dass an ihm etwas falsch war."""
    fueller = "\n\n".join(
        f"Filler paragraph {n} to push the letter onto a second page." for n in range(1, 30))
    for sprache in (None, "en"):
        quelle = tmp_path / f"lang-{sprache or 'de'}.md"
        quelle.write_text(
            BRIEF.format(sprache=f"sprache: {sprache}\n" if sprache else "") + fueller,
            encoding="utf-8")
        pdf, form = falzmarke.rendere(quelle, tmp_path / f"lang-{sprache or 'de'}.pdf")
        bericht = geometrie.pruefe(pdf, form).als_dict()
        seitenzahl = [p for p in bericht["pruefungen"] if p["name"] == "Seite 2: Seitenzahl"]
        assert seitenzahl, "die Prüfung gibt es nicht mehr"
        assert seitenzahl[0]["bestanden"], (
            f"Sprache {sprache or 'de'}: {seitenzahl[0]['ist']}")


def test_das_beispiel_ist_gerendert_und_gemessen(tmp_path):
    """Das Beispiel im Repo muss laufen — die CI rendert alle examples/*.md."""
    beispiel = REPO / "examples" / "brief-englisch.md"
    assert beispiel.is_file()
    pdf, form = falzmarke.rendere(beispiel, tmp_path / "beispiel.pdf")
    assert geometrie.pruefe(pdf, form).ok


# ── Silbentrennung ──────────────────────────────────────────────────────────

# Englischer Fliesstext mit langen, trennbaren Woertern. Dreimal wiederholt,
# damit genug Zeilenenden zum Trennen entstehen.
TRENNPROBE = (
    "Our recommendation concerning the extraordinary development of the international "
    "documentation is that the responsibility for the implementation of these "
    "considerable modifications should be transferred immediately. " * 3
)


def _trennstellen(pdf) -> list[str]:
    """Zeilenenden, an denen getrennt wurde."""
    return [z.strip() for z in _text(pdf).splitlines() if z.rstrip().endswith("-")]


def test_die_silbentrennung_folgt_der_sprache(tmp_path):
    """`text.lang` ist nicht Zierde — es entscheidet, wo Wörter brechen.

    Ohne diese Prüfung war die Umschaltung von `lang` **unbelegt**: Eine
    Gegenprobe, die `lang` fest auf „de“ zurückstellte, ließ die gesamte
    Testsuite grün. Behauptet wurde die Wirkung in sprachen.py und in
    references/frontmatter.md — geprüft hat sie nichts.

    Gemessen am 26.08.2026 an demselben englischen Text: mit `lang: de` bricht
    Typst „do-cumentation“, mit `lang: en` „doc-umentation“ — deutsche gegen
    englische Trennregeln, dasselbe Wort.
    """
    stellen = {}
    for kennung, sprache in (("de", None), ("en", "en")):
        quelle = tmp_path / f"trennung-{kennung}.md"
        quelle.write_text(
            BRIEF.format(sprache=f"sprache: {sprache}\n" if sprache else "").replace(
                "thank you for your enquiry.", TRENNPROBE),
            encoding="utf-8",
        )
        pdf, _ = falzmarke.rendere(quelle, tmp_path / f"trennung-{kennung}.pdf")
        stellen[kennung] = _trennstellen(pdf)

    assert stellen["de"] or stellen["en"], (
        "In keiner der beiden Fassungen wurde getrennt — dann misst diese Prüfung nichts. "
        "Entweder ist die Satzbreite gewachsen oder die Probe zu kurz geworden."
    )
    assert stellen["de"] != stellen["en"], (
        "Derselbe englische Text bricht mit deutscher und englischer Trennregel an "
        "denselben Stellen. Dann wird `text.lang` nicht durchgereicht.\n"
        f"  de: {stellen['de'][:3]}\n  en: {stellen['en'][:3]}"
    )
