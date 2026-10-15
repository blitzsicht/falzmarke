"""Die mitgebrachte Signatur erbt ihre Farben — wie der Rumpf (15.10.2026).

Seit PR #391 setzt der Rumpf keine Farbe, die auf hellem oder dunklem Grund
unlesbar wäre. Die Signatur aus `email.signatur_html` (erzeugt von `cw-core`)
blieb davon ausgenommen und brachte ihre Farben mit: Name und E-Mail-Link
`#1f2a37`, Firma `#333333`, Labels `#888888`. Ihre Dunkelregeln stehen in ihrem
eigenen `<style>`, und das bekommt der Thunderbird-Entwurf nicht
(`oeffnen.rumpf_fuer_compose`, ADR 0049). Im dunklen Entwurf stand die
Signatur dunkel auf dunkel.

Entschieden wurde, die Vorlage in `cw-core` nicht zu ändern — aus ihr entstehen
auch Kundensignaturen für Outlook. Stattdessen wendet falzmarke beim Einsetzen
dieselbe Regel an wie beim Rumpf: Übernommen werden Aufbau und Inhalt, die
Farben erbt die Mail vom Mailprogramm. Linien, die auf einem Grund nicht
tragen, werden zum geprüften Mittelgrau `emit_html.RAHMEN`.

Gemessen wird mit `tests/farbmessung.py`, derselben Messung wie beim Rumpf, an
zwei Signaturen im Repo: dem Beispiel `examples/email/profiles/signatur/
beispiel.html` und `tests/fixtures/signatur/cw-core-muster.html`, das den
Aufbau der cw-core-Signaturen ohne echte Daten nachstellt (Knöpfe mit Fläche,
`[data-ogsc]`-Regeln, `!important`, einfache Anführungszeichen).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from falzmarke import emit_html as html
from falzmarke import eml, farbe, oeffnen
from falzmarke import markdown as md
from farbmessung import KEINE_FARBE, LINIE_MINDEST, LINIEN, _deklarationen, farben_im_rumpf

REPO = Path(__file__).resolve().parents[1]
MUSTER = REPO / "tests" / "fixtures" / "signatur" / "cw-core-muster.html"
BEISPIEL_SIG = REPO / "examples" / "email" / "profiles" / "signatur" / "beispiel.html"
PROFIL = REPO / "examples" / "email" / "profiles" / "email-signatur.yaml"

SIGNATUREN = [MUSTER, BEISPIEL_SIG]
IDS = dict(ids=lambda p: p.stem)

KOPF = {"typ": "email", "an": "post@example.de", "betreff": "Probe",
        "anrede": "Sehr geehrte Damen und Herren,"}


def _eingesetzt(tmp_path: Path, quelle: Path):
    """`eml.mitgebrachte_signatur` über einen echten Profilpfad — wie im Betrieb."""
    (tmp_path / "sig.html").write_text(quelle.read_text(encoding="utf-8"), encoding="utf-8")
    daten = {"email": {"absender": "muster@example.de", "signatur_html": "sig.html"}}
    return eml.mitgebrachte_signatur(daten, tmp_path / "profil.yaml")


def _rumpf_der_quelle(quelle: Path) -> str:
    roh = quelle.read_text(encoding="utf-8")
    return re.search(r"<body\b[^>]*>(.*)</body>", roh, re.I | re.S).group(1).strip()


def _farbfrei(stil: str) -> dict[str, str]:
    """Die Deklarationen eines `style` ohne alles, was eine Farbe trägt."""
    bleibt = {}
    for name, wert in _deklarationen(stil).items():
        if name in ("color", "background", "background-color"):
            continue
        if name in LINIEN:
            wert = " ".join(t for t in wert.split() if not t.startswith("#"))
        bleibt[name] = wert
    return bleibt


class _Aufbau(HTMLParser):
    """Tags, Attribute ohne Farbe und Text — alles, was gleich bleiben muss."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.folge: list[tuple] = []

    def handle_starttag(self, tag, attrs):
        attribute = {k: v for k, v in attrs if k not in ("style", "bgcolor")}
        stil = dict(attrs).get("style") or ""
        self.folge.append(("<", tag, tuple(sorted(attribute.items())),
                           tuple(sorted(_farbfrei(stil).items()))))

    def handle_endtag(self, tag):
        self.folge.append((">", tag))

    def handle_data(self, daten):
        if daten.strip():
            self.folge.append(("text", daten.strip()))

    def handle_entityref(self, name):
        self.folge.append(("&", name))


def _aufbau(dokument: str) -> list[tuple]:
    zerleger = _Aufbau()
    zerleger.feed(dokument)
    zerleger.close()
    return zerleger.folge


def _farbdeklarationen(stil: str) -> list[str]:
    """`color`- und Grund-Deklarationen in einem Stylesheet, ohne `transparent`."""
    gefunden = []
    for name, wert in re.findall(r"(?<![\w-])(color|background(?:-color)?)\s*:\s*([^;}]+)", stil):
        if wert.replace("!important", "").strip().lower() not in KEINE_FARBE:
            gefunden.append(f"{name}: {wert.strip()}")
    return gefunden


# ── Am Einsetzen gemessen: eml.mitgebrachte_signatur ────────────────────────

class TestMitgebrachteSignatur:
    """`eml.mitgebrachte_signatur` — was aus der Datei in die Nachricht geht."""

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_die_quelle_traegt_unlesbare_farben(self, quelle):
        """Kontrollprobe: Ohne sie belegte der Test darunter nur, dass zwei
        farblose Dateien farblos bleiben."""
        assert farben_im_rumpf(_rumpf_der_quelle(quelle))

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_der_rumpf_setzt_nichts_unlesbares(self, tmp_path, quelle):
        assert farben_im_rumpf(_eingesetzt(tmp_path, quelle).rumpf) == []

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_der_stil_schaltet_keine_schrift_und_keinen_grund(self, tmp_path, quelle):
        stil = _eingesetzt(tmp_path, quelle).stil
        assert _farbdeklarationen(stil) == [], stil

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_eine_dunkle_linienregel_traegt_auf_dunkel(self, tmp_path, quelle):
        """Eine Regel, die die Linie im Dunkeln auf `#4a4a4a` setzt, machte das
        Mittelgrau wieder unlesbar (1,88:1). Sie muss weg oder tragen."""
        stil = _eingesetzt(tmp_path, quelle).stil
        for wert in re.findall(r"border[\w-]*\s*:\s*[^;}]*?(#[0-9a-fA-F]{3,6})", stil):
            rgb = tuple(int(wert.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            assert farbe.kontrast(rgb, farbe.GRUND_DUNKEL) >= LINIE_MINDEST, wert

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_aufbau_und_inhalt_bleiben(self, tmp_path, quelle):
        """Tags, Attribute, Text, Entitäten, Abstände, Größen, Logo — alles außer
        den Farben steht danach da wie vorher."""
        eingesetzt = _eingesetzt(tmp_path, quelle).rumpf
        assert _aufbau(eingesetzt) == _aufbau(_rumpf_der_quelle(quelle))

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_links_bleiben_byte_gleich(self, tmp_path, quelle):
        """Das Ziel eines Links ist Inhalt. Ein rohes `&` in der Adresse bleibt,
        wie es war — kein Neuschreiben des Tags."""
        eingesetzt = _eingesetzt(tmp_path, quelle).rumpf
        ziele = re.findall(r'href="[^"]*"', _rumpf_der_quelle(quelle))
        assert ziele
        for ziel in ziele:
            assert ziel in eingesetzt, ziel

    def test_eine_linie_wird_zum_mittelgrau(self, tmp_path):
        rumpf = _eingesetzt(tmp_path, MUSTER).rumpf
        assert f"border-right:3px solid {html.RAHMEN}" in rumpf, rumpf[:600]
        # Die Akzentlinie trägt auf beiden Gründen (4,85:1 und 3,44:1) und bleibt.
        assert "border-top:2px solid #8a6d3b" in rumpf

    def test_ein_knopf_verliert_seine_flaeche_nicht_seinen_link(self, tmp_path):
        """Weiße Schrift auf eigener Fläche: Die Fläche ist ein Grund im Rumpf,
        die weiße Schrift läge auf Weiß bei 1:1. Beides geht; der Link, seine
        Größe, sein Gewicht und die Rundung bleiben."""
        rumpf = _eingesetzt(tmp_path, MUSTER).rumpf
        assert "bgcolor" not in rumpf and "#ffffff" not in rumpf
        assert 'href="https://example.de/termin?a=1&b=2"' in rumpf
        assert "font-size:11px;font-weight:600;text-decoration:none;" in rumpf
        assert rumpf.count("border-radius:3px") == 2

    def test_transparent_bleibt(self, tmp_path):
        rumpf = _eingesetzt(tmp_path, MUSTER).rumpf
        assert "padding-left:20px;background:transparent;" in rumpf

    def test_der_textteil_bleibt_wie_er_ist(self, tmp_path):
        (tmp_path / "sig.txt").write_text("Erika Muster\nBeispiel GmbH\n", encoding="utf-8")
        (tmp_path / "sig.html").write_text(MUSTER.read_text(encoding="utf-8"), encoding="utf-8")
        daten = {"email": {"absender": "muster@example.de", "signatur_html": "sig.html",
                           "signatur_text": "sig.txt"}}
        assert eml.mitgebrachte_signatur(daten, tmp_path / "profil.yaml").text == \
            "Erika Muster\nBeispiel GmbH"


# ── In der fertigen Nachricht und im Thunderbird-Entwurf ────────────────────

class TestHtmlteil:
    """`eml.htmlteil` mit mitgebrachter Signatur — und was davon Thunderbird bekommt."""

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_die_nachricht_setzt_nichts_unlesbares(self, tmp_path, quelle):
        profil = yaml.safe_load(PROFIL.read_text(encoding="utf-8"))
        seite = eml.htmlteil(KOPF, profil, md.lies("wie besprochen.\n"),
                             signatur=_eingesetzt(tmp_path, quelle))
        assert farben_im_rumpf(seite) == []
        assert html.verstoesse(seite) == []

    @pytest.mark.parametrize("quelle", SIGNATUREN, **IDS)
    def test_der_entwurf_setzt_nichts_unlesbares(self, tmp_path, quelle):
        profil = yaml.safe_load(PROFIL.read_text(encoding="utf-8"))
        seite = eml.htmlteil(KOPF, profil, md.lies("wie besprochen.\n"),
                             signatur=_eingesetzt(tmp_path, quelle))
        rumpf = oeffnen.rumpf_fuer_compose(seite)
        assert "<style" not in rumpf
        assert farben_im_rumpf(rumpf) == []


# ── Die beiden Funktionen, an Grenzfällen ───────────────────────────────────

class TestFremdrumpfOhneFarben:
    """`emit_html.fremdrumpf_ohne_farben` — nur die Farben, sonst kein Byte."""

    @pytest.mark.parametrize("vorher, nachher", [
        ('<p style="margin:0;color:#1f2a37;">x</p>', '<p style="margin:0;">x</p>'),
        ('<a style="color:#1f2a37 !important;text-decoration:none">x</a>',
         '<a style="text-decoration:none">x</a>'),
        ("<span style='color:#888888'>x</span>", "<span>x</span>"),
        ('<span class="a" style="color: red;">x</span>', '<span class="a">x</span>'),
        ('<td bgcolor="#1a1a1a" style="background:#1a1a1a;padding:7px 0;">x</td>',
         '<td style="padding:7px 0;">x</td>'),
        ('<td style="border:1px solid black;">x</td>',
         f'<td style="border:1px solid {html.RAHMEN};">x</td>'),
        ('<font color="#333333">x</font>', "<font>x</font>"),
        ('<a href="x" style="color: #1a3a5c; text-decoration: underline;">x</a>',
         '<a href="x" style="text-decoration: underline;">x</a>'),
    ])
    def test_entfernt_genau_die_farbe(self, vorher, nachher):
        assert html.fremdrumpf_ohne_farben(vorher)[0] == nachher

    @pytest.mark.parametrize("bleibt", [
        '<a href="?a=1&b=2" style="color:inherit;">x</a>',
        '<td style="background:transparent;">x</td>',
        '<td style="border:0;">x</td>',
        f'<td style="border-top:2px solid #8a6d3b;">x</td>',
        '<p>style="color:#000" steht hier als Text</p>',
        '<!-- <p style="color:#000"> --><p>x &middot; y&nbsp;z</p>',
        '<table role="presentation"\n       style="border-collapse: collapse;"><tr><td>x</td></tr></table>',
    ])
    def test_laesst_alles_andere_stehen(self, bleibt):
        assert html.fremdrumpf_ohne_farben(bleibt) == (bleibt, [])

    def test_meldet_was_es_entfernt(self):
        _, entfernt = html.fremdrumpf_ohne_farben(
            '<p style="color:#1f2a37;">x</p><td bgcolor="#e63946">y</td>')
        assert any("#1f2a37" in e for e in entfernt) and any("bgcolor" in e for e in entfernt)


class TestFremdstilOhneFarben:
    """`emit_html.fremdstil_ohne_farben` — der Stil der Signatur, um die Farben bereinigt."""

    def test_die_cw_core_regeln_fallen_ganz_weg(self):
        stil = re.search(r"<style>(.*)</style>", MUSTER.read_text(encoding="utf-8"), re.S).group(1)
        bereinigt, entfernt = html.fremdstil_ohne_farben(stil)
        assert bereinigt == ""
        assert len(entfernt) == 12

    def test_andere_regeln_bleiben(self):
        stil = ("@media (max-width: 600px) { .x { display: block; color: #111; } }\n"
                ".y { font-weight: 600; }")
        bereinigt, _ = html.fremdstil_ohne_farben(stil)
        assert "display: block" in bereinigt and "font-weight: 600" in bereinigt
        assert "#111" not in bereinigt and "@media (max-width: 600px)" in bereinigt

    def test_eine_dunkle_linienregel_bleibt_nur_wenn_sie_traegt(self):
        stil = ("@media (prefers-color-scheme: dark) {\n"
                "  .a { border-color: #4a4a4a !important; }\n"
                "  .b { border-color: #8a8a8a !important; }\n}")
        bereinigt, _ = html.fremdstil_ohne_farben(stil)
        assert "#4a4a4a" not in bereinigt and "#8a8a8a" in bereinigt
        # Weg, nicht ersetzt: Im Dunkeln gilt dann die Linie, die inline steht.
        assert ".a {" not in bereinigt and html.RAHMEN not in bereinigt
