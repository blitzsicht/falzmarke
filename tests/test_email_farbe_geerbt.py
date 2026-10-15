"""Der Rumpf erbt seine Farben — Befund und Entscheidung vom 15.10.2026.

`falzmarke email … --oeffnen` legte einen Entwurf in Thunderbird an, und im
dunklen Thema stand der ganze Rumpf fast schwarz auf dunkelgrauem Grund. Die
Ursache: `oeffnen.rumpf_fuer_compose` übergibt nur den Inhalt von `<body>`
(ADR 0049), der `<style>`-Block mit den Dunkelregeln kommt dort nie an, und
übrig blieb die Inline-Farbe `#1a1a1a`.

Ein erster Umbau gab dem Umschlag einen weißen Grund. Lesbar war das, aber im
dunklen Editor stand ein weißer Kasten; der Betreiber hat ihn am selben Tag
verworfen. Seither gilt: **Der Rumpf setzt keine Farbe, die auf einem der
beiden Gründe unlesbar wäre.** Schrift- und Grundfarbe kommen vom Mailprogramm —
im dunklen Thunderbird hell auf dunkel, beim hellen Empfänger dunkel auf hell.

Gemessen wird gegen die beiden Gründe aus `farbe` (`GRUND_HELL`, `GRUND_DUNKEL`),
gegen die `lint` auch das Logo misst. Schrift braucht 4,5:1 (WCAG 1.4.3), eine
Linie 3:1 (WCAG 1.4.11) — auf **beiden** Gründen. Für Schrift schafft das keine
Farbe überhaupt; der Test `test_keine_farbe_traegt_schrift_auf_beiden_gruenden`
hält das fest. Also erbt die Schrift, und nur Linien tragen eine eigene Farbe.

Die Messung steht hier und nicht im Werkzeug. Sie hängt an keinem neuen Symbol,
damit dieselbe Datei auf dem alten Stand laufen kann und dort rot wird — an
`#1a1a1a` (main) wie am weißen Grund (Zwischenstand a784fd2).

Eine mitgebrachte Signatur (`email.signatur_html`) wird nicht gemessen. Sie
kommt fertig aus `cw-core`, falzmarke setzt sie unverändert ein, und ihre Farben
sind die Sache der Quelle. Die Tests schneiden sie heraus und prüfen getrennt,
dass sie wirklich unverändert drinsteht.
"""

from __future__ import annotations

import email
import re
from email import policy
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from falzmarke import cli as falzmarke
from falzmarke import emit_html as html
from falzmarke import eml, farbe, oeffnen
from conftest import EMAIL_BEISPIELE, profilpfad

IDS = dict(ids=lambda p: p.stem)

GRUENDE = (("hell", farbe.GRUND_HELL), ("dunkel", farbe.GRUND_DUNKEL))

#: Für die Meldung: „auf dunklem Grund“, nicht „dunkelem“.
DATIV = {"hell": "hellem", "dunkel": "dunklem"}

#: WCAG 1.4.3 für Fließtext, WCAG 1.4.11 für grafische Elemente.
SCHRIFT_MINDEST = 4.5
LINIE_MINDEST = 3.0

#: Werte, die keine eigene Farbe setzen.
KEINE_FARBE = {"inherit", "currentcolor", "transparent", "none", "initial", "unset", ""}

#: Rahmen-Eigenschaften, die eine Farbe tragen können.
LINIEN = ("border", "border-top", "border-right", "border-bottom", "border-left",
          "border-color")


def _rgb(wert: str) -> tuple[int, int, int] | None:
    treffer = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", wert.strip())
    if not treffer:
        return None
    ziffern = treffer.group(1)
    if len(ziffern) == 3:
        ziffern = "".join(z * 2 for z in ziffern)
    return int(ziffern[0:2], 16), int(ziffern[2:4], 16), int(ziffern[4:6], 16)


def _schwaechster_grund(rgb: tuple[int, int, int]) -> tuple[str, float]:
    return min(((name, farbe.kontrast(rgb, grund)) for name, grund in GRUENDE),
               key=lambda paar: paar[1])


def _deklarationen(stil: str) -> dict[str, str]:
    paare = {}
    for teil in stil.split(";"):
        if ":" in teil:
            name, wert = teil.split(":", 1)
            paare[name.strip().lower()] = wert.strip()
    return paare


class _Farbmesser(HTMLParser):
    """Sammelt jede Farbe, die ein Element inline setzt, und misst sie."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.befunde: list[str] = []

    def _melde(self, tag: str, was: str):
        self.befunde.append(f"<{tag}> {was}")

    def handle_starttag(self, tag, attrs):
        attribute = {k.lower(): (v or "") for k, v in attrs}
        if attribute.get("bgcolor", "").strip():
            self._melde(tag, f'setzt bgcolor="{attribute["bgcolor"]}" — ein Grund im Rumpf')
        stil = _deklarationen(attribute.get("style", ""))
        for name in ("background-color", "background"):
            if stil.get(name, "").lower() not in KEINE_FARBE:
                self._melde(tag, f"setzt {name}: {stil[name]} — ein Grund im Rumpf")
        if stil.get("color", "").lower() not in KEINE_FARBE:
            self._messe(tag, "color", stil["color"], SCHRIFT_MINDEST)
        for name in LINIEN:
            for token in stil.get(name, "").split():
                if token.startswith("#") or token.lower().startswith(("rgb", "hsl")):
                    self._messe(tag, name, token, LINIE_MINDEST)

    handle_startendtag = handle_starttag

    def _messe(self, tag: str, eigenschaft: str, wert: str, mindest: float):
        rgb = _rgb(wert)
        if rgb is None:
            self._melde(tag, f"{eigenschaft}: {wert} — nicht messbar")
            return
        grund, verhaeltnis = _schwaechster_grund(rgb)
        if verhaeltnis < mindest:
            self._melde(tag, f"{eigenschaft}: {wert} — {verhaeltnis:.2f}:1 auf {DATIV[grund]} Grund, "
                             f"verlangt {mindest}:1")


def farben_im_rumpf(dokument: str) -> list[str]:
    """Jeder Grund im Rumpf und jede Farbe, die auf einem der beiden Gründe nicht trägt."""
    messer = _Farbmesser()
    messer.feed(dokument)
    messer.close()
    return messer.befunde


# ── Die echte Kette ─────────────────────────────────────────────────────────

def _mitgebrachte_signatur(beispiel: Path):
    kopf, _, _ = falzmarke.lies_brief(beispiel)
    pfad = profilpfad(beispiel, kopf["profil"])
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    return eml.mitgebrachte_signatur(profil, pfad)


def _eigener_teil(dokument: str, beispiel: Path) -> str:
    """Das Dokument ohne mitgebrachte Signatur — die misst diese Datei nicht."""
    signatur = _mitgebrachte_signatur(beispiel)
    if signatur is None:
        return dokument
    assert signatur.rumpf in dokument, "die mitgebrachte Signatur steht nicht wörtlich drin"
    return dokument.replace(signatur.rumpf, "")


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
    """Jedes Mail-Beispiel einmal durch `setze_email` — `.eml` und Begleitseite."""
    ziel = tmp_path_factory.mktemp("farbe-geerbt")
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

class TestFarbenImRumpf:
    """Gegenproben für die Messung — ohne sie belegte eine leere Liste nichts."""

    @pytest.mark.parametrize("probe", [
        '<p style="color: #1a1a1a;">x</p>',               # dunkel auf Dunkel: 1,04:1
        '<p style="color: #e8e8e8;">x</p>',               # hell auf Weiß
        '<p style="color: #7e7e7e;">x</p>',               # das beste Grau, 4,06:1
        '<p style="color: red;">x</p>',                   # nicht messbar
        '<td bgcolor="#ffffff">x</td>',
        '<td style="background-color: #ffffff;">x</td>',
        '<td style="background: #1e1e1e;">x</td>',
        '<td style="border: 1px solid #c8c8c8;">x</td>',  # 1,67:1 auf Weiß
        '<td style="border-left: 3px solid #4a4a4a;">x</td>',  # 1,88:1 auf Dunkel
    ])
    def test_schlaegt_an(self, probe):
        assert farben_im_rumpf(probe), probe

    @pytest.mark.parametrize("probe", [
        '<p style="font-size: 13px;">x</p>',
        '<a style="color: inherit;">x</a>',
        '<div style="background: transparent;">x</div>',
        '<td style="border: 1px solid #7e7e7e;">x</td>',
        '<img style="border: 0;" alt="x" width="2" height="2">',
    ])
    def test_schweigt(self, probe):
        assert farben_im_rumpf(probe) == [], probe

    def test_keine_farbe_traegt_schrift_auf_beiden_gruenden(self):
        """Der Grund, warum die Schrift erbt: Kein Wert erreicht 4,5:1 auf Weiß
        UND auf `#1e1e1e`. Das Beste ist ein mittleres Grau bei rund 4,1:1 —
        über alle Grauwerte gezählt, und die Leuchtdichte ist das Einzige, was
        in die Formel eingeht."""
        bestes = max(min(farbe.kontrast((v, v, v), g) for _, g in GRUENDE) for v in range(256))
        assert bestes < SCHRIFT_MINDEST, bestes
        assert bestes >= LINIE_MINDEST, "für Linien muss ein Grau reichen"


# ── Der Umschlag setzt nichts ───────────────────────────────────────────────

class TestDokument:
    """`emit_html.dokument` — Körper, Umschlagtabelle und ihre Zelle."""

    MUSTER = {
        "body": r"<body\b[^>]*>",
        "umschlag": r'<table\b[^>]*role="presentation"[^>]*>',
        "zelle": r"(?<=<tr>)<td\b[^>]*>",
    }

    @pytest.mark.parametrize("stelle", ["body", "umschlag", "zelle"])
    def test_setzt_weder_grund_noch_schriftfarbe(self, stelle):
        marke = _start_tag(html.dokument("<p>x</p>\n"), self.MUSTER[stelle])
        assert farben_im_rumpf(marke) == [], marke
        stil = _deklarationen((re.search(r'style="([^"]*)"', marke) or [None, ""])[1])
        assert "color" not in stil, marke


# ── Der Dunkelblock schaltet nur noch, was eine Farbe hat ───────────────────

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


class TestDunkelregeln:
    """`emit_html.DUNKELREGELN` — keine Schrift- und keine Grundregel mehr."""

    def test_der_block_ist_nicht_leer(self):
        assert _regeln(), "der Block hat keine Regel — die Zerlegung misst nichts"

    def test_keine_regel_setzt_schrift_oder_grund(self):
        """Eine Schriftregel hieße: Es gibt eine Klasse, die inline eine Farbe
        setzt. Die gibt es nicht mehr — Schrift erbt."""
        falsch = [r for r in _regeln() if r[2] in ("color", "background-color", "background")]
        assert falsch == [], falsch

    def test_linien_tragen_auch_im_dunkeln(self):
        """Der Block darf eine Linie im Dunkeln ruhiger stellen, aber nicht
        unter 3:1 — sonst verschwindet sie."""
        for _, klasse, eigenschaft, wert in _regeln():
            if eigenschaft.startswith("border"):
                verhaeltnis = farbe.kontrast(_rgb(wert), farbe.GRUND_DUNKEL)
                assert verhaeltnis >= LINIE_MINDEST, f".{klasse} {wert}: {verhaeltnis:.2f}:1"

    def test_jede_regel_hat_ein_ziel(self, gesetzt):
        """Eine Regel für eine Klasse, die inline nichts dergleichen setzt, ist
        totes Gewicht in jeder Nachricht — und eine Einladung, die Farbe wieder
        dazuzuschreiben. `color: inherit` am Link zählt nicht als Ziel — es setzt
        keine Farbe, die eine Regel umschalten müsste."""
        alles = "".join(_html_der_eml(e) for e, _ in gesetzt.values())
        for _, klasse, eigenschaft, _ in _regeln():
            familie = "border" if eigenschaft.startswith("border") else eigenschaft
            ziel = re.search(
                rf'class="[^"]*\b{re.escape(klasse)}\b[^"]*"[^>]*style="[^"]*\b{familie}[\w-]*\s*:'
                rf'(?!\s*(?:inherit|currentcolor|transparent))',
                alles)
            assert ziel, f".{klasse} {{ {eigenschaft} }} trifft kein Element, das {familie} setzt"


# ── Die echte Kette: .eml, Begleitseite, Thunderbird-Rumpf ──────────────────

class TestSetzeEmail:
    """`cli.setze_email` — der HTML-Teil der Nachricht und die Begleitseite."""

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_die_nachricht_setzt_nichts_unlesbares(self, beispiel, gesetzt):
        seite = _html_der_eml(gesetzt[beispiel.stem][0])
        assert farben_im_rumpf(_eigener_teil(seite, beispiel)) == []

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_die_begleitseite_setzt_nichts_unlesbares(self, beispiel, gesetzt):
        seite = _begleitseite(gesetzt[beispiel.stem][1])
        assert farben_im_rumpf(_eigener_teil(seite, beispiel)) == []

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_der_textteil_kennt_keine_farbe(self, beispiel, gesetzt):
        text = _text_der_eml(gesetzt[beispiel.stem][0])
        for spur in ("bgcolor", "background", "color:", 'class="'):
            assert spur not in text, f"{spur} im Textteil von {beispiel.name}"

    def test_es_gibt_eine_mitgebrachte_signatur_zum_herausschneiden(self):
        """Sonst prüfte `_eigener_teil` nie den Fall, für den es da ist."""
        assert any(_mitgebrachte_signatur(b) for b in EMAIL_BEISPIELE)

    def test_die_mitgebrachte_signatur_bleibt_unangetastet(self, gesetzt):
        """Ihre Farben ändert falzmarke nicht — sie steht wörtlich in der Nachricht."""
        beispiel = next(b for b in EMAIL_BEISPIELE if _mitgebrachte_signatur(b))
        signatur = _mitgebrachte_signatur(beispiel)
        assert signatur.rumpf in _html_der_eml(gesetzt[beispiel.stem][0])
        assert farben_im_rumpf(signatur.rumpf), "das Beispiel trägt keine eigenen Farben mehr"


class TestRumpfFuerCompose:
    """`oeffnen.rumpf_fuer_compose` — was Thunderbird als `body=` bekommt.

    Hier fällt der Dunkelblock weg (ADR 0049). Ohne eigene Farbe zeigt
    Thunderbird den Rumpf in seinen eigenen: hell auf dunkel im dunklen Thema.
    """

    @pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
    def test_der_entwurf_setzt_nichts_unlesbares(self, beispiel, gesetzt):
        seite = _eigener_teil(_html_der_eml(gesetzt[beispiel.stem][0]), beispiel)
        rumpf = oeffnen.rumpf_fuer_compose(seite)
        assert "<style" not in rumpf, "der Dunkelblock kommt doch an — dann gilt dieser Test neu"
        assert farben_im_rumpf(rumpf) == []

    def test_die_huelle_des_entwurfs_ist_farblos(self, gesetzt):
        """Das `<div>`, auf das `rumpf_fuer_compose` den Stil des `<body>`
        legt, ist die Stelle, an der am 15.10.2026 `#1a1a1a` stand."""
        seite = _html_der_eml(gesetzt[EMAIL_BEISPIELE[0].stem][0])
        aussen = _start_tag(oeffnen.rumpf_fuer_compose(seite), r"^<div\b[^>]*>")
        stil = _deklarationen(re.search(r'style="([^"]*)"', aussen).group(1))
        assert not {"color", "background-color", "background"} & set(stil), aussen
