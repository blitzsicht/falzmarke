"""Überschriften, Zitate und Auszüge in der E-Mail (#109).

Bis #109 lehnte `markdown.py` diese drei Formen bei `ziel="email"` ab, auch mit
`dialekt: "1.1"`. Jetzt setzen der HTML- und der Klartextteil sie selbst. Jede
Zusage aus dem Vorgang steht hier als Test, und jeder Test hat eine Probe, die
ihn rot machen muss — sonst belegte er nur, dass etwas dasteht.

Die Vorgaben aus dem Vorgang: Überschriften höchstens zwei Ebenen tief und als
fette Absätze, Zitate mit einer Linie am linken Rand, Code mit Umbruch, weil die
Nachricht sonst waagerecht scrollt.
"""

from __future__ import annotations

from email.message import EmailMessage

import pytest

from falzmarke import emit_html, emit_text, lint, markdown, pruefung_eml
from falzmarke.lint import Bericht as LintBericht
from falzmarke.pruefung_eml import Bericht


def _baum(quelle: str):
    return markdown.lies(quelle, dialekt="1.1", ziel="email")


# ── Überschrift ─────────────────────────────────────────────────────────────


def test_die_ueberschrift_ist_ein_fetter_absatz_kein_h_element():
    html = emit_html.setze(_baum("# Aufbauzeit\n"))
    assert "<h1" not in html and "<h2" not in html
    assert html.startswith("<p ") and "font-weight: 700" in html
    assert 'role="heading"' in html and 'aria-level="1"' in html


def test_ab_ebene_drei_zusaetzlich_kursiv_wie_im_brief():
    """Zwei sichtbare Formen, nicht vier — die Vorgabe „höchstens zwei Ebenen"."""
    zwei = emit_html.setze(_baum("## Zwei\n"))
    drei = emit_html.setze(_baum("### Drei\n"))
    assert "font-style: italic" not in zwei
    assert "font-style: italic" in drei


def test_im_klartext_ist_die_ueberschrift_unterstrichen():
    text = emit_text.setze(_baum("# Aufbauzeit\n\n## Belege\n"))
    assert "Aufbauzeit\n==========" in text
    assert "Belege\n------" in text


# ── Zitat ───────────────────────────────────────────────────────────────────

ZITAT = "> Der Aufbau dauerte fünf Stunden.\n>\n> > Der Saal war belegt.\n>\n> Danach Ruhe.\n"


def test_das_zitat_steht_in_einer_zelle_mit_linker_linie():
    html = emit_html.setze(_baum(ZITAT))
    assert emit_html.ZITAT_ZELLE in html
    assert "border-left: 3px solid" in emit_html.ZITAT_ZELLE
    assert "<blockquote" not in html
    assert emit_html.verstoesse(emit_html.dokument(html)) == []
    assert emit_html.nicht_umschaltbar(html) == []


def test_zitattexte_nimmt_den_text_hinter_dem_inneren_zitat_mit():
    """Die Tiefenzählung: Ohne sie endete das äußere Zitat am Ende des inneren."""
    html = emit_html.setze(_baum(ZITAT))
    aussen, innen = emit_html.zitattexte(html)
    assert "Danach Ruhe." in aussen
    assert "Der Saal war belegt." in innen and "Danach" not in innen


def test_im_klartext_traegt_das_zitat_seine_tiefe():
    text = emit_text.setze(_baum(ZITAT))
    assert "> Der Aufbau dauerte fünf Stunden." in text
    assert ">> Der Saal war belegt." in text


def test_falte_stopft_zitatzeilen_nicht_wohl_aber_fliesstext():
    """Im Zitat ist `>` die Zitattiefe (RFC 3676 §4.5), sonst ein Stopffall."""
    gefaltet = emit_text.falte(_baum(ZITAT))
    assert "\n> Der Aufbau" in "\n" + gefaltet
    assert "\n >" not in "\n" + gefaltet


def test_ein_langes_zitat_wird_hart_gefaltet_mit_zeichen_auf_jeder_zeile():
    lang = "> " + " ".join(["Wort"] * 40) + "\n"
    text = emit_text.falte(_baum(lang))
    zeilen = [z for z in text.split("\n") if z]
    assert len(zeilen) > 1
    assert all(z.startswith("> ") and len(z) <= emit_text.BREITE for z in zeilen), zeilen
    assert not any(z.endswith(" ") for z in zeilen), "Zitatzeilen sind fest, ohne Faltmarke"


# ── Auszug ──────────────────────────────────────────────────────────────────

AUSZUG = '```\n2026-09-12 14:02  Aufbau   "Saal"\n    eingerückt\n```\n'


def test_der_abgesetzte_auszug_kennt_kein_pre():
    """`<pre>` bricht nicht um — eine lange Zeile ließe die Mail waagerecht scrollen."""
    html = emit_html.setze(_baum(AUSZUG))
    assert "<pre" not in html
    assert "<br>" in html
    assert "monospace" in html


def test_der_auszug_bleibt_zeichen_fuer_zeichen():
    html = emit_html.setze(_baum(AUSZUG))
    # Doppelte Leerzeichen bleiben als geschütztes, die Einrückung ganz.
    assert "14:02  Aufbau" in html
    assert "    eingerückt" in html
    # Keine Typografie: Das gerade Anführungszeichen bleibt eines.
    assert "&quot;Saal&quot;" in html and "„" not in html


def test_im_klartext_bleibt_der_auszug_fest_und_eingerueckt():
    lang = "```\n" + "x" * 30 + " " + "y" * 60 + "\n```\n"
    gefaltet = emit_text.falte(_baum(lang))
    zeile = next(z for z in gefaltet.split("\n") if "xxx" in z)
    assert "y" * 60 in zeile, "die Auszugszeile wurde gefaltet"
    assert zeile.startswith("     "), "Einzug plus Stopf-Leerzeichen erwartet"


def test_der_auszug_im_satz_bleibt_im_text():
    bloecke = _baum("Aktenzeichen `AZ 2026-0815/3` bitte angeben.\n")
    assert "<code" in emit_html.setze(bloecke)
    assert "AZ 2026-0815/3" in emit_text.setze(bloecke)


# ── Prüfung: `>` nur als echtes Zitat ───────────────────────────────────────


def _nachricht(textteil: str, html: str) -> EmailMessage:
    nachricht = EmailMessage()
    nachricht.set_content(textteil, subtype="plain", charset="utf-8", cte="quoted-printable",
                          params={"format": "flowed", "delsp": "yes"})
    nachricht.add_alternative(html, subtype="html", charset="utf-8")
    return nachricht


def _stuffing(nachricht: EmailMessage) -> bool:
    bericht = Bericht()
    text_teil = pruefung_eml._teil(nachricht, "text/plain")
    html_teil = pruefung_eml._teil(nachricht, "text/html")
    pruefung_eml._pruefe_textteil(text_teil, bericht, html_teil)
    return next(p for p in bericht.pruefungen if p.name == "Space-Stuffing").bestanden


def test_ein_echtes_zitat_besteht_die_stopfpruefung():
    bloecke = _baum(ZITAT)
    assert _stuffing(_nachricht(emit_text.falte(bloecke), emit_html.setze(bloecke)))


def test_eine_versehentliche_zeile_faellt_trotz_zitat_auf():
    """Die Gegenprobe zur Öffnung: Wörter, die in keinem Zitat stehen, bleiben ein Befund."""
    bloecke = _baum(ZITAT)
    text = emit_text.falte(bloecke) + "\n> Das hat niemand zitiert.\n"
    assert not _stuffing(_nachricht(text, emit_html.setze(bloecke)))


def test_ohne_zitat_im_html_ist_jede_zeile_mit_gt_ein_befund():
    bloecke = _baum(ZITAT)
    assert not _stuffing(_nachricht(emit_text.falte(bloecke), "<p>ohne Zitat</p>"))


# ── Lint: kein Satzspiegel in der E-Mail ────────────────────────────────────


@pytest.mark.parametrize("typ, erwartet", [("brief", 1), ("email", 0)])
def test_die_satzspiegelwarnung_gilt_nur_im_brief(typ, erwartet):
    body = "```\n" + "x" * 90 + "\n```\n"
    bericht = LintBericht()
    lint.pruefe_body(body, 0, bericht, "1.1", typ)
    auszug = [b for b in bericht.befunde if b.regel == "auszug"]
    assert len(auszug) == erwartet, auszug
