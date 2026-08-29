"""Links gibt es in E-Mails, im Brief bleiben sie ein Fehler (#103).

Auf Papier gibt es nichts zum Anklicken — ein Wort, hinter dem sich eine Adresse
verbirgt, ist dort ein Wort und sonst nichts. In einer E-Mail ist der Link der
normale Weg, und ihn abzulehnen hieße, den Schreibenden zur Handarbeit zu
zwingen.

## Wo die Grenze wirklich verläuft

Gemessen am 29.08.2026 mit markdown-it-py 4: Die Bibliothek verwirft
`javascript:`, `data:`, `vbscript:` und `file:` **selbst** — sie macht daraus
gar keinen Link. Das ist richtig, aber es war eine stille Entscheidung: Ohne
eigene Prüfung bekommt der Schreibende keine Meldung, und im Brief steht
danach wörtlich `[Angebot](javascript:…)`, mit Klammern.

Deshalb greifen zwei Prüfungen ineinander:

| Ziel | Wer es abfängt |
|---|---|
| `javascript:`, `data:`, `vbscript:`, `file:` | `GEFAEHRLICHE_LINKZIELE` am Rohtext |
| `ftp:` und andere Schemata | die Positivliste in `_pruefe_link` |
| `/seite`, `#anker`, `seite.html` | dieselbe, mit eigener Meldung |
| `https:`, `http:`, `mailto:`, `tel:` | keiner — sie sind zugelassen |

Die Positivliste ist Absicht. Eine Sperrliste vergisst immer eines.
"""

from __future__ import annotations

import pytest

from falzmarke import baum, emit, emit_html, emit_text, markdown

ZUGELASSEN = ["https://example.de/seite", "http://example.de", "mailto:info@example.de",
              "tel:+4994162098000"]
ABGELEHNT = ["javascript:alert(1)", "data:text/html,<b>x", "vbscript:x",
             "file:///etc/passwd", "ftp://example.de", "/seite", "#anker", "seite.html"]


def _lies(quelle: str, ziel: str = "email", hinweise=None):
    return markdown.lies(quelle + "\n", ziel=ziel, hinweise=hinweise)


# ── Der Brief kennt keinen Link ─────────────────────────────────────────────

def test_im_brief_bleibt_jeder_link_ein_fehler():
    with pytest.raises(markdown.MarkdownFehler, match="auf Papier"):
        _lies("Die [Bedingungen](https://example.de) gelten.", ziel="brief")


def test_und_der_typst_emitter_sagt_warum():
    """Er kann keinen bekommen — aber wenn doch, ist die Meldung die Antwort.

    Ein Notbehelf, der die Adresse still verschluckt, wäre hier das Schlimmere:
    Der Brief ginge raus, und niemand wüsste, dass etwas fehlt.
    """
    knoten = baum.Absatz((baum.Link(ziel="https://example.de",
                                    kinder=(baum.Text("Text"),)),))
    with pytest.raises(TypeError, match="gehört nicht in einen Brief"):
        emit.setze((knoten,))


# ── Die E-Mail kennt ihn, aber nicht jeden ──────────────────────────────────

@pytest.mark.parametrize("ziel", ZUGELASSEN)
def test_zugelassene_ziele_gehen_durch(ziel):
    baumknoten = _lies(f"Ein [Text]({ziel}) darin.")
    link = baumknoten[0].kinder[1]
    assert isinstance(link, baum.Link), baumknoten
    assert link.ziel == ziel


@pytest.mark.parametrize("ziel", ABGELEHNT)
def test_alles_andere_wird_abgelehnt(ziel):
    with pytest.raises(markdown.MarkdownFehler) as fehler:
        _lies(f"Ein [Text]({ziel}) darin.")
    assert fehler.value.regel == "email.linkziel", fehler.value.meldung


def test_die_gefaehrlichen_kommen_gar_nicht_erst_als_link_an():
    """Der Grund, warum es zwei Prüfungen braucht — gemessen, nicht vermutet.

    Fiele diese Eigenschaft von markdown-it weg, müsste `_pruefe_link` sie
    fangen. Fiele umgekehrt die Rohtext-Prüfung weg, stünde die Syntax wörtlich
    im Brief. Dieser Test hält fest, welcher der beiden Wege gerade trägt.
    """
    from markdown_it import MarkdownIt

    md = MarkdownIt("commonmark")
    for ziel in ("javascript:alert(1)", "data:text/html,x", "vbscript:x", "file:///x"):
        inline = [t for t in md.parse(f"[a]({ziel})") if t.type == "inline"][0]
        typen = [k.type for k in inline.children]
        assert "link_open" not in typen, f"{ziel} kommt jetzt als Link an — {typen}"


def test_und_die_ueblichen_sehr_wohl():
    """Gegenprobe. Ohne sie belegt der Test darüber nur, dass markdown-it
    überhaupt nichts verlinkt."""
    from markdown_it import MarkdownIt

    md = MarkdownIt("commonmark")
    inline = [t for t in md.parse("[a](https://example.de)") if t.type == "inline"][0]
    assert "link_open" in [k.type for k in inline.children]


# ── Warnungen, die den Brief nicht anhalten ─────────────────────────────────

@pytest.mark.parametrize("text", ["hier", "klicken Sie hier", "Hier", "mehr", "link"])
def test_nichtssagende_linktexte_werden_gemeldet(text):
    hinweise: list = []
    _lies(f"Die Bedingungen stehen [{text}](https://example.de/agb).", hinweise=hinweise)
    assert [h for h in hinweise if h.regel == "email.linktext"], hinweise


def test_ein_sprechender_linktext_nicht():
    """Gegenprobe: Eine Warnung, die jeden Link trifft, kostet Vertrauen in alle
    anderen."""
    hinweise: list = []
    _lies("Die [Geschäftsbedingungen](https://example.de/agb) gelten.", hinweise=hinweise)
    assert not [h for h in hinweise if h.regel == "email.linktext"], hinweise


def test_http_wird_gemeldet_https_nicht():
    for ziel, erwartet in (("http://example.de", True), ("https://example.de", False)):
        hinweise: list = []
        _lies(f"Die [Bedingungen]({ziel}) gelten.", hinweise=hinweise)
        gemeldet = bool([h for h in hinweise if h.regel == "email.linkschema"])
        assert gemeldet is erwartet, f"{ziel}: {hinweise}"


def test_kurz_url_dienste_werden_gemeldet():
    hinweise: list = []
    _lies("Mehr unter [Bedingungen](https://bit.ly/xyz).", hinweise=hinweise)
    assert [h for h in hinweise if h.regel == "email.linkschema"], hinweise


def test_eine_adresse_die_nur_so_aehnlich_heisst_nicht():
    """Gegenprobe: `bit.ly` als Teil eines längeren Namens ist kein Kurzdienst.

    Ohne sie träfe die Liste auch `https://nichts-mit-bit.ly-zu-tun.de`.
    """
    hinweise: list = []
    _lies("Mehr bei [Bitly Consulting](https://bit.ly.example.de/info).", hinweise=hinweise)
    assert not [h for h in hinweise if h.regel == "email.linkschema"], hinweise


# ── Wie er in den beiden Fassungen ankommt ──────────────────────────────────

def test_im_html_steht_ein_a_ohne_nachverfolgung():
    html = emit_html.setze(_lies("Die [Bedingungen](https://example.de/agb) gelten."))
    assert '<a href="https://example.de/agb"' in html, html
    assert "utm_" not in html
    assert "text-decoration: underline" in html, "ohne Unterstreichung trägt allein die Farbe"


def test_der_html_link_schaltet_im_dunklen_schema_mit():
    """Systemblau steht auf dunklem Grund bei 2,3:1. Deshalb erbt er die
    Textfarbe und hängt an derselben Klasse wie der Text."""
    html = emit_html.setze(_lies("Die [Bedingungen](https://example.de) gelten."))
    assert f'class="{emit_html.KLASSE_TEXT}"' in html.split("<a ")[1].split(">")[0]


def test_im_text_steht_die_adresse_ausgeschrieben():
    text = emit_text.falte(_lies("Die [Bedingungen](https://example.de/agb) gelten."))
    assert "<https://example.de/agb>" in text, text
    assert "Bedingungen:" in text


def test_die_adresse_geht_nicht_durch_die_typografie():
    """Aus `-` darf kein Halbgeviertstrich werden — sonst zeigt sie woandershin."""
    ziel = "https://example.de/agb-fassung-2026--08"
    text = emit_text.falte(_lies(f"Die [Bedingungen]({ziel}) gelten."))
    assert ziel in text, text
    html = emit_html.setze(_lies(f"Die [Bedingungen]({ziel}) gelten."))
    assert f'href="{ziel}"' in html, html


def test_mailto_wird_nicht_zweimal_gesagt():
    """`info@example.de: <mailto:info@example.de>` sagt zweimal dasselbe."""
    text = emit_text.falte(_lies("Schreiben Sie an [info@example.de](mailto:info@example.de)."))
    assert text.strip() == "Schreiben Sie an info@example.de.", text


def test_eine_nackte_adresse_steht_nur_einmal():
    text = emit_text.falte(_lies("Mehr unter [https://example.de](https://example.de)"))
    assert text.strip() == "Mehr unter <https://example.de>", text


def test_die_klammern_halten_das_satzzeichen_fern():
    """Der Grund für die Klammern, gemessen.

    Ohne sie steht `…/agb.html, die seit August` — wer die Adresse
    doppelklickt, nimmt das Komma mit, und Mailprogramme, die Adressen selbst
    erkennen, ziehen es in den Verweis.
    """
    text = emit_text.falte(
        _lies("Die [Bedingungen](https://example.de/agb.html), die seit August gelten."))
    assert "<https://example.de/agb.html>," in text, text
    assert "agb.html," not in text.replace("<https://example.de/agb.html>,", ""), text


# ── Und das Regelwerk kennt sie ─────────────────────────────────────────────

@pytest.mark.parametrize("kennung,wirkung", [
    ("email.linkziel", "fehler"),
    ("email.linktext", "warnung"),
    ("email.linkschema", "warnung"),
])
def test_die_regeln_stehen_im_regelwerk(kennung, wirkung):
    from falzmarke import regeln

    treffer = [r for r in regeln.alle() if r["id"] == kennung]
    assert treffer, f"{kennung} fehlt in regeln/email.yaml"
    assert treffer[0]["wirkung"] == wirkung
