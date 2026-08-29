"""Die Signatur soll etwas hermachen (Issue #142).

Drei Dinge kommen dazu: das Logo als Teil der Nachricht, ein leiser Rechtsblock
und das dunkle Farbschema. Das letzte braucht einen `<style>`-Block, und der
war bis hierher pauschal verboten — die Ausnahme dafür steht in ADR 0034 und
ist hier gemessen.

Der Fehler, gegen den die meisten dieser Prüfungen gebaut sind, heißt **halb
umgeschaltet**: Beim Bildzeichen der Marke stand die helle Grundregel einmal
nach der Medienabfrage, das Blatt schaltete um und die Kontur nicht. Im Kleinen
sieht man so etwas nicht.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from falzmarke import cli as falzmarke
from falzmarke import eml, markdown
from falzmarke import emit_html as html
from conftest import EMAIL_BEISPIELE, REPO, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"


def _seite(beispiel=None) -> str:
    beispiel = beispiel or EMAIL_BEISPIELE[0]
    kopf, body, versatz = falzmarke.lies_brief(beispiel)
    profil = yaml.safe_load((PROFILE / f"{kopf['profil']}.yaml").read_text(encoding="utf-8"))
    return eml.htmlteil(kopf, profil, markdown.lies(body, versatz, ziel="email"))


# ── Der Dunkelblock, und warum er die einzige Ausnahme ist ──────────────────

def test_die_nachricht_traegt_den_dunkelblock():
    assert html.STILBLOCK in _seite()


def test_beide_umschaltmechanismen_sind_da():
    """`prefers-color-scheme` deckt Apple Mail und Thunderbird ab, `[data-ogsc]`
    setzt Outlook stattdessen. Mit nur einem bleibt genau ein Programm hell."""
    block = html.DUNKELREGELN
    assert "@media (prefers-color-scheme: dark)" in block
    assert "[data-ogsc]" in block


def test_jede_klasse_wird_in_beiden_mechanismen_behandelt():
    """Sonst schaltet Outlook nur die Hälfte um — und das fällt niemandem auf,
    der kein Outlook hat."""
    block = html.DUNKELREGELN
    medien = block[block.index("@media"):block.index("[data-ogsc]")]
    ogsc = block[block.index("[data-ogsc]"):]
    for klasse in (html.KLASSE_TEXT, html.KLASSE_LEISE, html.KLASSE_LINIE):
        assert f".{klasse}" in medien, f"{klasse} fehlt in der Medienabfrage"
        assert f".{klasse}" in ogsc, f"{klasse} fehlt bei [data-ogsc]"


def test_jede_regel_traegt_important():
    """Inline-Stile haben höhere Spezifität als Klassen. Ohne `!important`
    gewinnt der helle Wert, und der Block ist wirkungslos."""
    # Nur Deklarationszeilen, nicht die `@media`-Zeile: Die trägt einen
    # Doppelpunkt und eine Klammer, ist aber keine Regel.
    regeln = [z for z in html.DUNKELREGELN.splitlines()
              if "{" in z and "}" in z and not z.lstrip().startswith("@")]
    assert len(regeln) >= 6, regeln
    assert all("!important" in z for z in regeln), regeln


SABOTAGEN = [
    ("ein zweiter Block", lambda s: s.replace("</head>", "<style>p{color:red}</style>\n</head>")),
    ("eine Farbe geändert", lambda s: s.replace(html.TINTE_DUNKEL, "#ff0000")),
    ("eine Regel mehr", lambda s: s.replace("</style>", "  p { display: none }\n</style>")),
    ("ein Leerzeichen mehr", lambda s: s.replace("@media (prefers", "@media  (prefers")),
    ("!important entfernt", lambda s: s.replace(" !important", "")),
    ("Skript daneben", lambda s: s.replace("</head>", "<script>x</script>\n</head>")),
    ("url() im Block", lambda s: s.replace("</style>", "  .x{background:url(a.png)}\n</style>")),
]


@pytest.mark.parametrize("was,sabotiere", SABOTAGEN, ids=[s[0] for s in SABOTAGEN])
def test_die_ausnahme_ist_nicht_dehnbar(was, sabotiere):
    """Der Block ist eine Konstante des Werkzeugs, Zeichen für Zeichen
    verglichen. Alles daneben bleibt ein Verstoß."""
    assert html.verstoesse(sabotiere(_seite())), f"{was} blieb unbemerkt"


def test_die_echte_nachricht_ist_sauber():
    """Kontrollprobe. Ohne sie prüften die Sabotagen nur, dass irgendetwas
    meldet."""
    assert html.verstoesse(_seite()) == []


def test_crlf_ist_kein_verstoss():
    """Eine `.eml` reist mit CRLF (RFC 5322). Ohne diese Nachsicht meldete die
    Prüfung jede versendete Nachricht als Verstoß gegen sich selbst."""
    assert html.verstoesse(_seite().replace("\n", "\r\n")) == []


def test_crlf_deckt_keine_aenderung_zu():
    """Die Gegenrichtung: Die Nachsicht gilt den Zeilenenden, nicht dem Inhalt."""
    verbogen = _seite().replace("\n", "\r\n").replace(html.TINTE_DUNKEL, "#ff0000")
    assert html.verstoesse(verbogen)


# ── Nichts bleibt hell zurück ───────────────────────────────────────────────

@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, ids=lambda p: p.stem)
def test_alles_schaltet_um(beispiel):
    """Wer eine Farbe inline setzt, muss die Klasse tragen, die sie umschaltet."""
    assert html.nicht_umschaltbar(_seite(beispiel)) == []


def test_die_pruefung_bemerkt_ein_vergessenes_element():
    """Gegenprobe — sonst belegte der Test darüber nur, dass eine Liste leer ist."""
    ohne = _seite().replace(f'<p class="{html.KLASSE_TEXT}" style=', "<p style=", 1)
    assert html.nicht_umschaltbar(ohne)


def test_auch_die_begleitseite_schaltet_um():
    kopf, body, versatz = falzmarke.lies_brief(EMAIL_BEISPIELE[0])
    profil = yaml.safe_load((PROFILE / f"{kopf['profil']}.yaml").read_text(encoding="utf-8"))
    seite = eml.begleit_html(kopf, profil, markdown.lies(body, versatz, ziel="email"))
    assert html.nicht_umschaltbar(seite) == []
    assert html.verstoesse(seite) == []


# ── Das Logo reist mit ──────────────────────────────────────────────────────

@pytest.fixture
def profil_mit_logo(tmp_path):
    """Das Beispielprofil mit einem echten PNG daneben."""
    ziel = tmp_path / "profiles"
    shutil.copytree(PROFILE, ziel)
    bild = ziel / "assets" / "mail-logo.png"
    # Ein gültiges 1×1-PNG, damit kein externes Werkzeug nötig ist.
    bild.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6300010000050001od0a2db40000000049454e44ae426082"
        .replace("od", "6a")))
    pfad = ziel / "example.yaml"
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    profil["email"]["logo"] = "assets/mail-logo.png"
    pfad.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
    return profil, pfad


def _nachricht(profil, profil_pfad):
    beispiel = EMAIL_BEISPIELE[0]
    kopf, body, versatz = falzmarke.lies_brief(beispiel)
    return eml.baue(kopf, profil, body, markdown.lies(body, versatz, ziel="email"),
                    brief_pfad=beispiel, profil_pfad=profil_pfad)


def test_ohne_logo_bleibt_die_nachricht_wie_sie_war():
    profil = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    assert profil["email"]["logo"] is False, "das Beispielprofil führt kein Logo"
    nachricht = _nachricht(profil, PROFILE / "example.yaml")
    assert [t.get_content_type() for t in nachricht.walk()] == [
        "multipart/alternative", "text/plain", "text/html"]


def test_mit_logo_entsteht_ein_related_teil(profil_mit_logo):
    nachricht = _nachricht(*profil_mit_logo)
    typen = [t.get_content_type() for t in nachricht.walk()]
    assert "multipart/related" in typen, typen
    assert "image/png" in typen, typen


def test_das_logo_haengt_am_html_teil_nicht_an_der_nachricht(profil_mit_logo):
    """Als Anhang der Nachricht stünde es in jedem Client in der Anlagenliste —
    neben der Rechnung, die jemand wirklich verschickt hat."""
    roh = _nachricht(*profil_mit_logo).as_string()
    assert "Content-Disposition: attachment" not in roh


def test_kein_verweis_nach_aussen(profil_mit_logo):
    """Eine Adresse, die bei jedem Öffnen abgerufen wird, ist ein Zählpixel —
    ob so gemeint oder nicht. Und ohne Netz erschiene das Logo gar nicht."""
    roh = _nachricht(*profil_mit_logo).as_string()
    assert f"cid:{eml.LOGO_CID}" in roh
    assert not re.search(r'<img[^>]+src="(?!cid:)', roh), "Bild von ausserhalb"
    assert not re.search(r'src=3D"https?://', roh), "Verweis nach aussen"


def test_das_logo_traegt_einen_alternativtext(profil_mit_logo):
    """Am dekodierten HTML-Teil, nicht am Rohtext: Der ist quoted-printable
    kodiert und über Zeilen gebrochen — dort findet keine Suche das `alt`."""
    nachricht = _nachricht(*profil_mit_logo)
    teil = next(t for t in nachricht.walk() if t.get_content_type() == "text/html")
    inhalt = teil.get_content()
    treffer = re.search(r'<img[^>]+alt="([^"]+)"', inhalt)
    assert treffer, inhalt[:300]
    assert treffer.group(1).strip()


def test_svg_wird_abgelehnt(tmp_path):
    """Outlook stellt SVG in Mails nicht dar. Ein Logo, das bei einem der drei
    großen Programme fehlt, ist schlimmer als keines — dann fehlt es überall
    gleich."""
    ziel = tmp_path / "profiles"
    shutil.copytree(PROFILE, ziel)
    profil = yaml.safe_load((ziel / "example.yaml").read_text(encoding="utf-8"))
    profil["email"]["logo"] = "assets/logo.svg"
    with pytest.raises(ValueError, match="Rasterbild"):
        eml.logo_datei(profil, ziel / "example.yaml")


def test_logo_true_nimmt_das_des_briefkopfs(tmp_path):
    """Die Doku versprach das, lange bevor es die Funktion gab."""
    ziel = tmp_path / "profiles"
    shutil.copytree(PROFILE, ziel)
    (ziel / "assets" / "kopf.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    profil = yaml.safe_load((ziel / "example.yaml").read_text(encoding="utf-8"))
    profil["briefkopf"] = {"logo": "assets/kopf.png"}
    profil["email"]["logo"] = True
    assert eml.logo_datei(profil, ziel / "example.yaml").name == "kopf.png"


# ── Der Rechtsblock steht leiser ────────────────────────────────────────────

def test_der_rechtsblock_ist_kleiner_gesetzt():
    """Pflichtangaben und Vertraulichkeitshinweis sind Beiwerk, nicht die
    Botschaft."""
    seite = _seite()
    absaetze = re.findall(r'<p class="([^"]*)" style="([^"]*)"', seite)
    leise = [stil for klassen, stil in absaetze if html.KLASSE_LEISE in klassen]
    assert leise, absaetze
    assert any("font-size: 13px" in stil for stil in leise)
