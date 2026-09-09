"""Die mitgebrachte Signatur — was eingesetzt wird und was abgelehnt (#275).

Für Blitzsicht, Siluri und die Kunden erzeugt `cw-core` bereits eine gestaltete
Signatur, und die steht in den Mailprogrammen. Zwei Signaturen für denselben
Absender sind eine zu viel; wer eine hat, bringt sie mit.

**Der Kanal gibt dabei nicht nach.** Die Regeln von ADR 0034 gelten für eine
fremde Signatur wie für eigenen Satz. Was durchfällt, wird abgelehnt — mit
Fundstelle, nicht stillschweigend eingesetzt. Diese Datei misst beide
Richtungen: dass eine saubere Signatur ankommt und dass eine unsaubere es nicht
tut.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from falzmarke import eml, markdown as md

REPO = Path(__file__).resolve().parents[1]
BEISPIEL = REPO / "examples" / "email" / "email-signatur.md"
PROFILORDNER = REPO / "examples" / "email" / "profiles"

QUELLE = "wie besprochen die Unterlagen.\n"
KOPF = {"typ": "email", "an": "post@example.de", "betreff": "Probe",
        "anrede": "Sehr geehrte Damen und Herren,"}

SAUBER = """<!DOCTYPE html>
<html lang="de"><head><style>
@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }
</style></head>
<body>
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
<tr><td class="x" style="color: #1a1a1a;">Erika Muster</td></tr>
</table>
</body></html>
"""


@pytest.fixture
def profil() -> dict:
    return yaml.safe_load((PROFILORDNER / "email-signatur.yaml").read_text(encoding="utf-8"))


def _profil_mit(tmp_path: Path, html: str, text: str | None = None) -> tuple[dict, Path]:
    """Ein Profil samt Signaturdatei in einem eigenen Ordner.

    Der Profilpfad ist echt: `mitgebrachte_signatur` löst die Angabe über
    `cli.datei_aus_dem_profilordner` auf, und diese Grenze soll mitgemessen
    werden — nicht umgangen.
    """
    (tmp_path / "sig.html").write_text(html, encoding="utf-8")
    email_teil = {"absender": "muster@example.de", "signatur_html": "sig.html"}
    if text is not None:
        (tmp_path / "sig.txt").write_text(text, encoding="utf-8")
        email_teil["signatur_text"] = "sig.txt"
    return {"email": email_teil}, tmp_path / "profil.yaml"


# ── Was ankommt ─────────────────────────────────────────────────────────────

def test_die_signatur_kommt_an(tmp_path):
    daten, pfad = _profil_mit(tmp_path, SAUBER, "Erika Muster\n")
    sig = eml.mitgebrachte_signatur(daten, pfad)
    assert sig is not None
    assert "Erika Muster" in sig.rumpf
    assert "prefers-color-scheme" in sig.stil
    assert sig.text == "Erika Muster"
    # Der Rumpf ist der Rumpf: Kopf und Stilblock bleiben draußen.
    assert "<!DOCTYPE" not in sig.rumpf and "<style" not in sig.rumpf


def test_ohne_das_feld_bleibt_alles_wie_es_war(tmp_path):
    """Die tragende Gegenprobe. Ohne sie belegte die Datei nur, dass etwas
    passiert, wenn das Feld dasteht — nicht, dass sonst nichts passiert."""
    assert eml.mitgebrachte_signatur({"email": {"absender": "a@example.de"}}, tmp_path) is None
    assert eml.mitgebrachte_signatur({}, tmp_path) is None


def test_ein_fragment_ohne_body_wird_ganz_genommen(tmp_path):
    daten, pfad = _profil_mit(tmp_path, '<p style="color: #1a1a1a;">Nur ein Absatz</p>')
    sig = eml.mitgebrachte_signatur(daten, pfad)
    assert sig.rumpf == '<p style="color: #1a1a1a;">Nur ein Absatz</p>'


def test_ohne_textfassung_bleibt_der_textteil_aus_dem_profil(tmp_path, profil):
    daten, pfad = _profil_mit(tmp_path, SAUBER)          # kein signatur_text
    sig = eml.mitgebrachte_signatur(daten, pfad)
    assert sig.text == ""
    text = eml.textteil(KOPF, profil, md.lies(QUELLE), signatur=sig)
    # Der Absender steht wieder aus den Profilblöcken da, nicht aus der Datei.
    assert (profil.get("email") or {}).get("anzeigename", "Erika Muster") in text


# ── Was abgelehnt wird ──────────────────────────────────────────────────────

ABLEHNUNGEN = [
    ("Skript", '<body><script>alert(1)</script></body>', "Skript"),
    ("Zählpixel",
     '<body><table role="presentation"><tr><td>'
     '<img src="cid:x" alt="x" width="1" height="1"></td></tr></table></body>',
     "Zählpixel"),
    ("Layouttabelle ohne Marke",
     "<body><table><tr><td>Erika Muster</td></tr></table></body>",
     "Tabelle"),
    ("externes Stylesheet",
     '<body><link rel="stylesheet" href="https://x.invalid/a.css"><p>x</p></body>',
     "Stylesheet"),
    ("Ereignis-Attribut", '<body><p onclick="x()">Erika</p></body>', "Ereignis"),
]


@pytest.mark.parametrize("was, html, im_text", ABLEHNUNGEN, ids=[a[0] for a in ABLEHNUNGEN])
def test_eine_unsaubere_signatur_wird_abgelehnt(tmp_path, was, html, im_text):
    """Mit Fundstelle in der Meldung — sonst sucht der Mensch in einer Datei,
    die er nicht selbst geschrieben hat."""
    daten, pfad = _profil_mit(tmp_path, html)
    with pytest.raises(ValueError) as fehler:
        eml.mitgebrachte_signatur(daten, pfad)
    assert im_text.lower() in str(fehler.value).lower(), str(fehler.value)
    assert "sig.html" in str(fehler.value), "die Meldung nennt die Datei nicht"


@pytest.mark.parametrize("stil, erwartet", [
    ("@media (min-width: 1px) { .x { background: url(https://x.invalid/a.png); } }", "Ressource"),
    ("@import url('fremd.css');", "Stylesheet"),
    (".x { behavior: url(#default); }", "Ressource"),
])
def test_ein_stil_der_nach_aussen_zeigt_wird_abgelehnt(tmp_path, stil, erwartet):
    daten, pfad = _profil_mit(tmp_path, f"<html><head><style>{stil}</style></head>"
                                        f"<body><p>x</p></body></html>")
    with pytest.raises(ValueError) as fehler:
        eml.mitgebrachte_signatur(daten, pfad)
    assert erwartet.lower() in str(fehler.value).lower(), str(fehler.value)


def test_eine_leere_datei_ist_ein_fehler(tmp_path):
    daten, pfad = _profil_mit(tmp_path, "<html><head></head><body>   </body></html>")
    with pytest.raises(ValueError, match="Rumpf"):
        eml.mitgebrachte_signatur(daten, pfad)


def test_ohne_profilpfad_gibt_es_keine_stille_annahme(tmp_path):
    """Ein Bibliotheksaufruf ohne Profilpfad darf das Feld nicht einfach
    übergehen — sonst fehlte die Signatur, und niemand wüsste warum."""
    with pytest.raises(ValueError, match="Profilpfad"):
        eml.mitgebrachte_signatur({"email": {"signatur_html": "sig.html"}}, None)


# ── In der fertigen Nachricht ───────────────────────────────────────────────

def test_die_gebaute_signatur_steht_daneben_nicht_mehr_da(profil):
    """Der Zweck des Vorgangs, an der fertigen Nachricht gemessen: EINE
    Signatur, nicht zwei."""
    roh = BEISPIEL.read_text(encoding="utf-8").split("---", 2)[2]
    bloecke = md.lies(roh)
    sig = eml.mitgebrachte_signatur(profil, PROFILORDNER / "email-signatur.yaml")
    html = eml.htmlteil(KOPF, profil, bloecke, signatur=sig)

    assert "Termin vereinbaren" in html, "die mitgebrachte Signatur fehlt"
    assert 'class="fm-t fm-r"' not in html, "die gebaute Signatur steht auch da"
    assert html.count("<style") == 1, "zwei Stilblöcke — einer davon wäre wirkungslos"
    stil = re.search(r"<style[^>]*>(.*?)</style>", html, re.S).group(1)
    assert stil.index("fm-t") < stil.index("sig-name"), "der eigene Teil muss vorn stehen"


# ── Die eigene Breite einer Signatur ist kein Deckel (#279) ─────────────────

def test_eine_signatur_darf_sich_selbst_begrenzen(tmp_path, profil):
    """Der Umschlag umfasst alles und darf deshalb nichts begrenzen (#264).
    Eine Signatur ist ein kurzer Block am Ende — ihre eigene Breite quetscht
    niemanden, und die von `cw-core` erzeugten tragen sie (580 px).

    Bis #279 traf die Prüfung jede Layouttabelle. Eine Mail mit echter Signatur
    endete dadurch mit Code 2, obwohl inhaltlich nichts falsch war.
    """
    from falzmarke import pruefung_eml

    breit = ('<html><body><table role="presentation" '
             'style="max-width:580px;"><tr><td>Erika Muster</td></tr></table></body></html>')
    daten, pfad = _profil_mit(tmp_path, breit)
    sig = eml.mitgebrachte_signatur(daten, pfad)
    html = eml.htmlteil(KOPF, profil, md.lies(QUELLE), signatur=sig)

    bericht = pruefung_eml.Bericht(gegenstand="Prüfungen bestanden")
    pruefung_eml._pruefe_htmlteil(_AlsTeil(html), bericht)
    deckel = [p for p in bericht.pruefungen if p.name == "Umschlag ohne Breitendeckel"]
    assert deckel, "die Prüfung lief gar nicht"
    assert deckel[0].bestanden, deckel[0].ist


def test_gegenprobe_ein_deckel_am_umschlag_faellt_weiter_auf():
    """Ohne sie belegte der Test darüber nur, dass die Prüfung nichts mehr
    findet. Der Fall aus #264 muss rot bleiben."""
    from falzmarke import pruefung_eml

    html = ('<html><body><table role="presentation" style="max-width:600px;">'
            '<tr><td><p>Text</p></td></tr></table></body></html>')
    bericht = pruefung_eml.Bericht(gegenstand="Prüfungen bestanden")
    pruefung_eml._pruefe_htmlteil(_AlsTeil(html), bericht)
    deckel = [p for p in bericht.pruefungen if p.name == "Umschlag ohne Breitendeckel"]
    assert deckel and not deckel[0].bestanden, "der Deckel am Umschlag rutschte durch"


class _AlsTeil:
    """Das Wenigste, was `_pruefe_htmlteil` von einem MIME-Teil braucht.

    Ein echter Teil käme aus einer geschriebenen `.eml`; hier geht es allein um
    die eine Prüfung, und der Umweg über Datei und Umschlag würde sie nicht
    schärfer machen.
    """

    def __init__(self, html: str) -> None:
        self._html = html

    def get_content(self) -> str:
        return self._html

    def get_content_charset(self) -> str:
        return "utf-8"
