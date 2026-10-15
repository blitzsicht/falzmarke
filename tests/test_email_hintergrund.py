"""Textfarbe nie ohne eigenen Grund — der Thunderbird-Befund vom 15.10.2026.

`falzmarke email … --oeffnen` legte einen Entwurf in Thunderbird an, und im
dunklen Thema stand der ganze Rumpf fast schwarz auf dunkelgrauem Grund. Lesbar
blieben nur die hellgrauen Adresszeilen der Signatur.

Die Ursache steht in zwei Dateien. `oeffnen.rumpf_fuer_compose` übergibt nur den
Inhalt von `<body>` (ADR 0049) — der `<style>`-Block im Kopf, der im dunklen
Schema auf helle Schrift umschaltet, kommt in Thunderbird nie an. Übrig blieben
die Inline-Farben aus `emit_html.TEXTSTIL` (`color: #1a1a1a`), und die Nachricht
setzte **keinen eigenen Hintergrund**: Sie stand auf dem Grund des Programms,
und der war dunkel.

Dieselbe Lage hat jeder Empfänger, dessen Programm `<style>` entfernt und dunkel
malt. Deshalb gilt die Regel für jeden Weg, nicht nur für Thunderbird: Farbe von
Text und Grund kommen **als Paar**. Ohne Stilunterstützung beide hell
(`#1a1a1a` auf `#ffffff`), mit Stilunterstützung im dunklen Schema beide dunkel
(`#e8e8e8` auf `#1e1e1e`). Nie dunkle Schrift auf dunklem Grund, nie helle auf
Weiß.

Gemessen wird an dem, was das Werkzeug wirklich erzeugt: an der `.eml` aus
`setze_email`, an der Begleitseite und an dem Rumpf, den `rumpf_fuer_compose`
an Thunderbird übergibt. Jede Messung hat ihre Gegenprobe in dieser Datei.
"""

from __future__ import annotations

import email
import re
from email import policy
from html.parser import HTMLParser
from pathlib import Path

import pytest

from falzmarke import cli as falzmarke
from falzmarke import emit_html as html
from falzmarke import farbe, oeffnen
from conftest import EMAIL_BEISPIELE

IDS = dict(ids=lambda p: p.stem)

#: Elemente ohne Ende-Tag. Sie tragen keinen Inhalt und kommen nicht auf den Stapel.
LEERE_ELEMENTE = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                  "link", "meta", "source", "track", "wbr"}

#: Werte, die keine eigene Farbe setzen.
KEINE_FARBE = {"inherit", "currentcolor", "transparent", "none", "initial", "unset"}


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _rgb(wert: str) -> tuple[int, int, int]:
    wert = wert.strip().lstrip("#")
    if len(wert) == 3:
        wert = "".join(z * 2 for z in wert)
    return int(wert[0:2], 16), int(wert[2:4], 16), int(wert[4:6], 16)


def _deklaration(stil: str, eigenschaft: str) -> str | None:
    treffer = re.search(rf"(?:^|;)\s*{re.escape(eigenschaft)}\s*:\s*([^;]*)", stil, re.I)
    return treffer.group(1).strip() if treffer else None


def _hat_grund(attribute: dict[str, str]) -> bool:
    """Setzt das Element selbst einen Hintergrund — per Stil oder per Attribut?"""
    stil = attribute.get("style") or ""
    for eigenschaft in ("background-color", "background"):
        wert = _deklaration(stil, eigenschaft)
        if wert and wert.lower() not in KEINE_FARBE:
            return True
    return bool((attribute.get("bgcolor") or "").strip())


class _Farbwanderer(HTMLParser):
    """Läuft den Baum ab und merkt sich, ob über der Stelle ein Grund liegt."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        #: Je offenes Element: Name, und ob es selbst oder ein Vorfahr Grund setzt.
        self.stapel: list[tuple[str, bool]] = []
        self.offen: list[str] = []

    def _gedeckt(self) -> bool:
        return bool(self.stapel) and self.stapel[-1][1]

    def handle_starttag(self, tag, attrs):
        attribute = {k: (v or "") for k, v in attrs}
        farbe_ = _deklaration(attribute.get("style") or "", "color")
        gedeckt = self._gedeckt() or _hat_grund(attribute)
        if farbe_ and farbe_.lower() not in KEINE_FARBE and not gedeckt:
            self.offen.append(f"<{tag}> mit color: {farbe_} ohne eigenen Grund")
        if tag not in LEERE_ELEMENTE:
            self.stapel.append((tag, gedeckt))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in LEERE_ELEMENTE and self.stapel:
            self.stapel.pop()

    def handle_endtag(self, tag):
        # Bis zum passenden Anfang zurück — ein nicht geschlossenes Element
        # darunter darf seinen Grund nicht über das Ende hinaus vererben.
        for stelle in range(len(self.stapel) - 1, -1, -1):
            if self.stapel[stelle][0] == tag:
                del self.stapel[stelle:]
                return


def farbe_ohne_grund(dokument: str) -> list[str]:
    """Jedes Element, das eine Textfarbe setzt, ohne dass darüber ein Grund liegt."""
    wanderer = _Farbwanderer()
    wanderer.feed(dokument)
    wanderer.close()
    return wanderer.offen


def _regeln() -> list[tuple[str, str, str, str]]:
    """`DUNKELREGELN` zerlegt: (Mechanismus, Klasse, Eigenschaft, Wert)."""
    block = html.DUNKELREGELN
    medien = block[block.index("@media"):block.index("[data-ogsc]")]
    ogsc = block[block.index("[data-ogsc]"):]
    regeln = []
    for name, teil in (("medien", medien), ("ogsc", ogsc)):
        for klasse, eigenschaft, wert in re.findall(
                r"\.([\w-]+)\s*\{\s*([\w-]+)\s*:\s*([^;!]+?)\s*!important;\s*\}", teil):
            regeln.append((name, klasse, eigenschaft, wert))
    return regeln


def _grundklassen(mechanismus: str) -> set[str]:
    """Die Klassen, deren Hintergrund der Dunkelblock in diesem Mechanismus umschaltet."""
    return {k for m, k, e, _ in _regeln() if m == mechanismus and e == "background-color"}


def _html_der_eml(pfad: Path) -> str:
    nachricht = email.message_from_bytes(pfad.read_bytes(), policy=policy.default)
    for teil in nachricht.walk():
        if teil.get_content_type() == "text/html":
            return teil.get_content()
    raise AssertionError(f"{pfad.name} hat keinen HTML-Teil")


def _text_der_eml(pfad: Path) -> str:
    nachricht = email.message_from_bytes(pfad.read_bytes(), policy=policy.default)
    for teil in nachricht.walk():
        if teil.get_content_type() == "text/plain":
            return teil.get_content()
    raise AssertionError(f"{pfad.name} hat keinen Textteil")


@pytest.fixture(scope="module")
def gesetzt(tmp_path_factory) -> dict[str, tuple[Path, list[Path]]]:
    """Jedes Mail-Beispiel einmal durch die echte Kette — `.eml` und Begleitseite."""
    ziel = tmp_path_factory.mktemp("hintergrund")
    return {b.stem: falzmarke.setze_email(b, ziel / b.stem) for b in EMAIL_BEISPIELE}


def _begleitseite(dateien: list[Path]) -> str:
    seiten = [p for p in dateien if p.suffix == ".html"]
    assert len(seiten) == 1, [p.name for p in dateien]
    return seiten[0].read_text(encoding="utf-8")


def _start_tag(dokument: str, muster: str) -> str:
    treffer = re.search(muster, dokument)
    assert treffer, f"kein Tag auf {muster!r}"
    return treffer.group(0)


# ── Die Messung selbst kann rot werden ──────────────────────────────────────

class TestFarbeOhneGrund:
    """Gegenproben für die Messung — ohne sie belegte eine leere Liste nichts."""

    def test_farbe_ohne_grund_faellt_auf(self):
        assert farbe_ohne_grund('<p style="color: #1a1a1a;">x</p>')

    def test_grund_per_stil_deckt(self):
        assert farbe_ohne_grund(
            '<div style="background-color: #ffffff;"><p style="color: #1a1a1a;">x</p></div>') == []

    def test_grund_per_attribut_deckt(self):
        assert farbe_ohne_grund(
            '<table bgcolor="#ffffff"><tr><td style="color: #1a1a1a;">x</td></tr></table>') == []

    def test_der_grund_endet_mit_seinem_element(self):
        """Ein Geschwister hinter dem Element mit Grund liegt nicht mehr darauf."""
        assert farbe_ohne_grund(
            '<div style="background-color: #fff;"></div><p style="color: #111;">x</p>')

    def test_inherit_ist_keine_farbe(self):
        assert farbe_ohne_grund('<a style="color: inherit;">x</a>') == []

    def test_transparent_ist_kein_grund(self):
        assert farbe_ohne_grund(
            '<div style="background: transparent;"><p style="color: #111;">x</p></div>')


# ── Der Umschlag trägt seinen Grund ─────────────────────────────────────────

class TestDokument:
    """`emit_html.dokument` — Körper, Umschlagtabelle und ihre Zelle."""

    MUSTER = {
        "body": r"<body\b[^>]*>",
        "umschlag": r'<table\b[^>]*role="presentation"[^>]*>',
        "zelle": r'(?<=<tr>)<td\b[^>]*>',
    }

    @pytest.mark.parametrize("stelle", ["body", "umschlag", "zelle"])
    def test_traegt_hellen_grund_als_attribut_und_stil(self, stelle):
        """Beides, weil die Word-Engine des klassischen Outlook nur das Attribut
        liest und Gmail den `<body>` wegwirft — dann trägt die Tabelle."""
        marke = _start_tag(html.dokument("<p>x</p>\n"), self.MUSTER[stelle])
        hell = _hex(farbe.GRUND_HELL)
        assert f'bgcolor="{hell}"' in marke, marke
        stil = re.search(r'style="([^"]*)"', marke).group(1)
        assert _deklaration(stil, "background-color") == hell, marke

    @pytest.mark.parametrize("stelle", ["body", "umschlag", "zelle"])
    def test_der_grund_schaltet_im_dunkelblock_um(self, stelle):
        """Ein Grund, der im Dunkeln weiß bliebe, wäre helle Schrift auf Weiß."""
        marke = _start_tag(html.dokument("<p>x</p>\n"), self.MUSTER[stelle])
        klassen = set(re.search(r'class="([^"]*)"', marke).group(1).split()) \
            if 'class="' in marke else set()
        for mechanismus in ("medien", "ogsc"):
            assert klassen & _grundklassen(mechanismus), (
                f"{marke} trägt keine Klasse, deren Grund {mechanismus} umschaltet")


# ── Der Dunkelblock schaltet Schrift und Grund gemeinsam ────────────────────

class TestDunkelregeln:
    """`emit_html.DUNKELREGELN` — wer Schrift umschaltet, schaltet den Grund mit."""

    @pytest.mark.parametrize("mechanismus", ["medien", "ogsc"])
    def test_wo_schrift_umschaltet_schaltet_der_grund_mit(self, mechanismus):
        schrift = [k for m, k, e, _ in _regeln() if m == mechanismus and e == "color"]
        assert schrift, f"{mechanismus}: der Block schaltet keine Schrift um"
        assert _grundklassen(mechanismus), (
            f"{mechanismus}: {schrift} schalten auf helle Schrift, aber kein Grund wird dunkel")

    @pytest.mark.parametrize("mechanismus", ["medien", "ogsc"])
    def test_der_dunkle_grund_ist_der_gemessene(self, mechanismus):
        """`farbe.GRUND_DUNKEL` ist der Grund, gegen den `lint` das Logo misst.
        Malt die Nachricht ihn selbst, misst `email.logo_kontrast` das, was der
        Leser sieht — und nicht mehr nur eine Schätzung."""
        werte = {w.lower() for m, _, e, w in _regeln()
                 if m == mechanismus and e == "background-color"}
        assert werte == {_hex(farbe.GRUND_DUNKEL)}, werte

    def test_die_paare_tragen_text(self):
        """WCAG 1.4.3 verlangt für Fließtext 4,5:1 — hell wie dunkel.

        Gemessen an den Werten, die tatsächlich gesetzt werden: der helle Grund
        aus dem Umschlag, der dunkle aus dem Block — nicht an `farbe`, sonst
        bliebe ein vertauschter Wert im Block hier unbemerkt."""
        umschlag = _start_tag(html.dokument("<p>x</p>\n"), TestDokument.MUSTER["umschlag"])
        hell = re.search(r'bgcolor="([^"]*)"', umschlag).group(1)
        dunkel = [w for m, _, e, w in _regeln() if m == "medien" and e == "background-color"]
        assert len(dunkel) == 1, dunkel
        paare = [(html.TINTE, hell)]
        paare += [(w, dunkel[0]) for m, _, e, w in _regeln() if m == "medien" and e == "color"]
        for schrift, grund in paare:
            verhaeltnis = farbe.kontrast(_rgb(schrift), _rgb(grund))
            assert verhaeltnis >= 4.5, f"{schrift} auf {grund}: {verhaeltnis:.2f}:1"


# ── Die echte Kette: .eml, Begleitseite, Thunderbird-Rumpf ──────────────────

class TestSetzeEmail:
    """`cli.setze_email` — der HTML-Teil der Nachricht und die Begleitseite."""

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_keine_textfarbe_ohne_grund_in_der_nachricht(self, beispiel, gesetzt):
        eml_pfad, _ = gesetzt[beispiel.stem]
        assert farbe_ohne_grund(_html_der_eml(eml_pfad)) == []

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_keine_textfarbe_ohne_grund_auf_der_begleitseite(self, beispiel, gesetzt):
        _, dateien = gesetzt[beispiel.stem]
        assert farbe_ohne_grund(_begleitseite(dateien)) == []

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_der_textteil_kennt_keine_farbe(self, beispiel, gesetzt):
        """Der Klartext bleibt, was er war — kein Markup, keine Farbe."""
        text = _text_der_eml(gesetzt[beispiel.stem][0])
        for spur in ("bgcolor", "background", "color:", 'class="'):
            assert spur not in text, f"{spur} im Textteil von {beispiel.name}"

    def test_die_mitgebrachte_signatur_liegt_auf_dem_grund(self, gesetzt):
        """`email.signatur_html` setzt eigene Inline-Farben. Sie muss im
        Umschlag stehen, der den Grund trägt — sonst stünde sie wieder auf dem
        Grund des Programms."""
        seite = _html_der_eml(gesetzt["email-signatur"][0])
        assert "Erika Muster" in seite, "das Beispiel trägt die mitgebrachte Signatur nicht"
        umschlag = seite.index('role="presentation"')
        assert umschlag < seite.index("Erika Muster") < seite.rindex("</table>")
        assert farbe_ohne_grund(seite) == []


class TestRumpfFuerCompose:
    """`oeffnen.rumpf_fuer_compose` — was Thunderbird als `body=` bekommt.

    Hier fällt der Dunkelblock weg (ADR 0049). Also muss das helle Paar allein
    tragen: dunkle Schrift auf ihrem eigenen weißen Grund.
    """

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_der_entwurf_bringt_seinen_grund_mit(self, beispiel, gesetzt):
        rumpf = oeffnen.rumpf_fuer_compose(_html_der_eml(gesetzt[beispiel.stem][0]))
        assert "<style" not in rumpf, "der Dunkelblock kommt doch an — dann gilt dieser Test neu"
        assert farbe_ohne_grund(rumpf) == []

    def test_der_grund_im_entwurf_ist_hell(self, gesetzt):
        """Ohne Dunkelblock gilt der helle Wert — Schrift `TINTE` auf Weiß."""
        rumpf = oeffnen.rumpf_fuer_compose(_html_der_eml(gesetzt[EMAIL_BEISPIELE[0].stem][0]))
        aussen = _start_tag(rumpf, r"^<div\b[^>]*>")
        stil = re.search(r'style="([^"]*)"', aussen).group(1)
        assert _deklaration(stil, "background-color") == _hex(farbe.GRUND_HELL), aussen
        assert _deklaration(stil, "color") == html.TINTE, aussen
