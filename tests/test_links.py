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


def _lies(quelle: str, ziel: str = "email", hinweise=None, dialekt: str = "1.0"):
    return markdown.lies(quelle + "\n", ziel=ziel, hinweise=hinweise, dialekt=dialekt)


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


# ── Die nackte Adresse wird ein Link (#424) ─────────────────────────────────
#
# Gemessen am 27.10.2026: Aus einer Zeile, die nur eine Adresse trägt, wurde im
# HTML-Teil ein Absatz mit Text, ohne `<a href>`. Im Thunderbird-Entwurf war der
# Link zum Unterschreiben deshalb nicht anklickbar, und genau dieser Link war der
# Zweck der Mail. Verlinkt wird beim Lesen, nicht im Emitter: Danach ist die
# nackte Adresse ein `baum.Link` wie jeder andere und läuft über dieselben Wege.

def _anker(html: str) -> list[str]:
    """Die `href`-Werte aller `<a>` im HTML, in Reihenfolge."""
    import re

    return re.findall(r'<a href="([^"]*)"', html)


def test_nackte_url_als_eigener_absatz_wird_ein_link():
    """Die Reproduktion aus #424, im Kleinen."""
    html = emit_html.setze(_lies("https://sign.example.de/s/NB76qgP6sbHGFQ"))
    assert _anker(html) == ["https://sign.example.de/s/NB76qgP6sbHGFQ"], html
    assert ">https://sign.example.de/s/NB76qgP6sbHGFQ</a>" in html, html


def test_der_punkt_am_satzende_steht_ausserhalb_des_links():
    html = emit_html.setze(_lies("Die Bedingungen stehen unter https://example.de/agb."))
    assert _anker(html) == ["https://example.de/agb"], html
    assert "https://example.de/agb</a>." in html, html


@pytest.mark.parametrize("zeichen", [",", ";", ":", "!", "?", "“", "»", "›", "'", '"'])
def test_auch_andere_satzzeichen_gehoeren_zum_satz(zeichen):
    html = emit_html.setze(_lies(f"Hier: https://example.de/agb{zeichen} danach weiter"))
    assert _anker(html) == ["https://example.de/agb"], html


def test_im_codespan_bleibt_die_adresse_wortlaut():
    """Code ist Wortlaut — dort wird nichts verlinkt (#424, „Erwartet“)."""
    html = emit_html.setze(_lies("Die Adresse `https://example.de/api` steht so im Code.",
                                 dialekt="1.1"))
    assert "<a " not in html, html
    assert "https://example.de/api" in html, html


def test_im_codeblock_ebenso():
    html = emit_html.setze(_lies("```\nhttps://example.de/api\n```", dialekt="1.1"))
    assert "<a " not in html, html


def test_eine_adresse_als_linktext_wird_nicht_verschachtelt():
    """`<a>` in `<a>` ist ungültiges HTML, und Mailprogramme lösen es verschieden auf."""
    knoten = _lies("Mehr unter [https://x.de](https://x.de)")
    link = knoten[0].kinder[1]
    assert isinstance(link, baum.Link), knoten
    assert not any(isinstance(k, baum.Link) for k in link.kinder), link
    html = emit_html.setze(knoten)
    assert html.count("<a ") == 1, html


def test_eine_autolink_adresse_ebenso():
    """`<https://x.de>` ist für CommonMark schon ein Link — kein zweiter darum."""
    html = emit_html.setze(_lies("Mehr unter <https://x.de>."))
    assert html.count("<a ") == 1, html


def test_im_brief_bleibt_die_nackte_adresse_text():
    """Auf Papier gibt es nichts zum Anklicken — und die Adresse ist dort kein
    Fehler, sondern ausgeschrieben, wie #103 es für den Brief verlangt."""
    knoten = _lies("Mehr unter https://example.de/agb.", ziel="brief")
    assert not any(isinstance(k, baum.Link) for k in knoten[0].kinder), knoten
    typst = emit.setze(knoten)
    assert "example.de/agb" in typst, typst


def test_im_klartext_steht_die_nackte_adresse_einmal_in_klammern():
    text = emit_text.falte(_lies("Mehr unter https://example.de/agb."))
    assert text.count("<https://example.de/agb>") == 1, text
    assert text.count("https://example.de/agb") == 1, text
    assert text.strip() == "Mehr unter <https://example.de/agb>.", text


def test_die_klammer_in_der_adresse_bleibt_drin():
    html = emit_html.setze(_lies("Siehe https://de.wikipedia.org/wiki/A_(B) dazu."))
    assert _anker(html) == ["https://de.wikipedia.org/wiki/A_(B)"], html


def test_die_klammer_um_die_adresse_bleibt_draussen():
    html = emit_html.setze(_lies("Die Bedingungen (siehe https://x.de) gelten."))
    assert _anker(html) == ["https://x.de"], html
    assert "https://x.de</a>)" in html, html


def test_die_nackte_adresse_geht_nicht_durch_die_typografie():
    """Aus `--` darf kein Halbgeviertstrich werden — weder im `href` noch im
    sichtbaren Text, sonst kopiert der Empfänger eine Adresse, die es nicht gibt.
    Gegenprobe im selben Absatz: `--` außerhalb der Adresse wird ersetzt."""
    ziel = "https://example.de/agb-fassung-2026--08/seite"
    html = emit_html.setze(_lies(f"Mehr unter {ziel} und 1--2 sonst nichts"))
    assert _anker(html) == [ziel], html
    assert f">{ziel}</a>" in html, html
    assert "1–2" in html, "Gegenprobe: die Typografie läuft hier gar nicht"


def test_unterstriche_in_der_adresse_werden_kein_ausfuellfeld():
    """Ab Dialekt 1.2 wird `___` im Text ein Feld. In einer Adresse ist es ein
    Teil der Adresse — und die Zählung in `_pruefe_felder` meldet keinen
    Fehlalarm, weil sie die Adresse ebenso ausblendet."""
    ziel = "https://example.de/a___b"
    knoten = _lies(f"Mehr unter {ziel} dazu.", dialekt="1.2")
    assert not any(isinstance(k, baum.Ausfuellfeld) for k in knoten[0].kinder), knoten
    assert _anker(emit_html.setze(knoten)) == [ziel]


def test_das_feld_neben_der_adresse_bleibt_ein_feld():
    """Gegenprobe zum Test darüber: Ausgeblendet wird die Adresse, nicht der Absatz."""
    knoten = _lies("Unterschrift ____ und https://example.de/a___b", dialekt="1.2")
    felder = [k for k in knoten[0].kinder if isinstance(k, baum.Ausfuellfeld)]
    assert len(felder) == 1, knoten


def test_aus_der_adresse_kommt_kein_typografie_hinweis():
    """`z.B.` im Pfad ist Teil der Adresse, keine Abkürzung im Satz.

    Gemessen am 03.11.2026: `typografie.vorschlaege` meldet an
    `https://x.de/z.B./seite` die Abkürzungsregel. Ein Hinweis, die Adresse mit
    geschützten Leerzeichen zu schreiben, führte zu einer anderen Adresse.
    """
    hinweise: list = []
    _lies("Mehr unter https://x.de/z.B./seite dazu", hinweise=hinweise)
    assert not [h for h in hinweise if h.regel == "schreibweise.abkuerzungen"], hinweise


def test_im_satz_kommt_der_hinweis_weiter():
    """Gegenprobe: Ausgenommen ist die Adresse, nicht der Satz um sie herum."""
    hinweise: list = []
    _lies("Mehr unter https://x.de/seite, z.B. dazu", hinweise=hinweise)
    assert [h for h in hinweise if h.regel == "schreibweise.abkuerzungen"], hinweise


def test_http_wird_auch_an_der_nackten_adresse_gemeldet():
    for ziel, erwartet in (("http://example.de", True), ("https://example.de", False)):
        hinweise: list = []
        _lies(f"Mehr unter {ziel} dazu.", hinweise=hinweise)
        gemeldet = bool([h for h in hinweise if h.regel == "email.linkschema"])
        assert gemeldet is erwartet, f"{ziel}: {hinweise}"


def test_ein_kurzdienst_auch():
    hinweise: list = []
    _lies("Mehr unter https://bit.ly/xyz dazu.", hinweise=hinweise)
    assert [h for h in hinweise if h.regel == "email.linkschema"], hinweise


@pytest.mark.parametrize("text", ["www.example.de", "https://", "xhttps://example.de",
                                  "ftp://example.de"])
def test_was_keine_vollstaendige_http_adresse_ist_bleibt_text(text):
    """`www.` ohne Schema wird nicht geraten, und ein Schema ohne Rest ist keins."""
    html = emit_html.setze(_lies(f"Siehe {text} dazu."))
    assert "<a " not in html, html


def test_die_fertige_nachricht_besteht_ihre_eigene_pruefung(tmp_path):
    """Der Prüfpfad, den `falzmarke email` selbst fährt — mit Quellteil.

    Im HTML steht die Adresse jetzt zweimal (`href` und Linktext), im
    Klartext einmal in spitzen Klammern. `pruefung_eml._woerter` vergleicht
    Mengen; das muss gleich bleiben, und die Quelle muss vollständig sein.
    """
    from conftest import SKILL

    from falzmarke import cli, pruefung_eml

    quelle = tmp_path / "probe.md"
    quelle.write_text(
        "---\ntyp: email\nprofil: example\nan: post@example.de\nbetreff: Probe 424\n---\n"
        "bitte unterschreiben Sie hier:\n\nhttps://sign.example.de/s/NB76qgP6sbHGFQ\n\n"
        "Die Bedingungen (siehe https://example.de/agb) gelten.\n",
        encoding="utf-8")
    ziel, _ = cli.setze_email(
        quelle, tmp_path / "probe",
        profil_verzeichnis=SKILL / "falzmarke" / "typst" / "profiles",
        mit_quelle=True)
    roh = ziel.read_text(encoding="utf-8")
    assert "sign.example.de" in roh
    bericht = pruefung_eml.pruefe(ziel)
    gescheitert = [p.name for p in bericht.pruefungen if not p.bestanden]
    assert not gescheitert, bericht.als_text(ausfuehrlich=True)
    assert any(p.name.startswith("Quelle vollständig") for p in bericht.pruefungen), \
        "der Quellteil wurde gar nicht geprüft"


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
