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
from conftest import EMAIL_BEISPIELE, PROFILE, REPO, profilpfad


def _seite(beispiel=None) -> str:
    """Der HTML-Teil eines Beispiels — samt Logo, wenn sein Profil eines führt.

    Das Logo mitzunehmen ist der Punkt: Ohne es prüften die Tests unten eine
    Fassung, die so nie entsteht.
    """
    beispiel = beispiel or EMAIL_BEISPIELE[0]
    kopf, body, versatz = falzmarke.lies_brief(beispiel)
    pfad = profilpfad(beispiel, kopf["profil"])
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    logo = eml.logo_quelle(profil, pfad)
    return eml.htmlteil(kopf, profil, markdown.lies(body, versatz, ziel="email"), logo=logo)


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
    # „eine Regel mehr" war bis #275 ein Verstoß: Der Block war eine Konstante
    # und sonst nichts. Seitdem darf HINTER dem eigenen Teil ein mitgebrachter
    # stehen — geprüft, nicht verglichen. Was rot bleiben muss, ist ein Zusatz,
    # der nach außen zeigt oder ein zweites Dokument aufmacht.
    ("ein @import dahinter",
     lambda s: s.replace("</style>", "  @import url('x.css');\n</style>")),
    ("Markup im Block", lambda s: s.replace("</style>", "  <b>x</b>\n</style>")),
    ("etwas VOR dem eigenen Teil",
     lambda s: s.replace('<style type="text/css">',
                         '<style type="text/css">p{color:red}')),
    ("ein Leerzeichen mehr", lambda s: s.replace("@media (prefers", "@media  (prefers")),
    ("!important entfernt", lambda s: s.replace(" !important", "")),
    ("Skript daneben", lambda s: s.replace("</head>", "<script>x</script>\n</head>")),
    ("url() im Block", lambda s: s.replace("</style>", "  .x{background:url(a.png)}\n</style>")),
]


@pytest.mark.parametrize("was,sabotiere", SABOTAGEN, ids=[s[0] for s in SABOTAGEN])
def test_die_ausnahme_ist_nicht_dehnbar(was, sabotiere):
    """Der eigene Teil des Blocks bleibt eine Konstante, Zeichen für Zeichen
    verglichen — er steht VORN. Ein mitgebrachter Teil darf dahinter stehen
    (#275), aber nur, wenn er nichts nach außen holt und kein zweites Dokument
    aufmacht."""
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


def test_ein_hintergrund_faellt_immer_auf():
    """`background-color` schaltet KEINE Klasse um — `DUNKELREGELN` kennt nur
    Text-, Dämpfungs- und Rahmenfarbe. Ein gesetzter Hintergrund bliebe im
    dunklen Client unter allen Umständen hell, und darum ist jedes Vorkommen
    ein Befund, mit welcher Klasse auch immer.

    Die Probe hält den Eintrag in `UMSCHALTPFLICHTIG` fest. Bis #243 fiel
    `background-color:` zufällig unter `color:` — die Prüfung suchte den Namen
    als Teilstring irgendwo im Stil. Seit sie an der Deklaration ankert, wäre
    er ohne eigenen Eintrag still weggefallen.
    """
    for klasse in ("", f' class="{html.KLASSE_TEXT}"', f' class="{html.KLASSE_LINIE}"'):
        marke = f'<td{klasse} style="background-color: #ffffff;">'
        befunde = html.nicht_umschaltbar(marke)
        assert any("background-color:" in b for b in befunde), f"{marke} blieb unbemerkt"


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


#: Ein Kopf, der ohne Beispieldatei auskommt — für die Formproben unten.
KOPF_LOGO = {"anrede": "Sehr geehrte Frau Muster,", "unterzeichner": "Erika Muster"}


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


# ── Das Gerüst mit Logo: zwei Spalten, eine Linie dazwischen (#243) ─────────
#
# Bis hierher steckte nur der erste Block in der Tabelle; Kontakt und
# Rechtsangaben liefen darunter unter dem Logo hindurch. Kein Golden führt ein
# Logo — das Beispielprofil hat keines — und deshalb belegte bis zu diesem
# Abschnitt kein einziger Test, wie die Signatur mit Bild überhaupt aussieht.

def _seite_mit_logo(profil_mit_logo) -> str:
    profil, pfad = profil_mit_logo
    beispiel = EMAIL_BEISPIELE[0]
    kopf, body, versatz = falzmarke.lies_brief(beispiel)
    logo = eml.logo_quelle(profil, pfad)
    return eml.htmlteil(kopf, profil, markdown.lies(body, versatz, ziel="email"), logo=logo)


def _signaturtabelle(seite: str) -> str:
    """Die Tabelle um die Signatur — nicht die Hülle um die ganze Nachricht."""
    treffer = re.search(r'<table[^>]*\bstyle="[^"]*border-top[^"]*">.*?</table>',
                        seite, re.DOTALL)
    assert treffer, seite[-2000:]
    return treffer.group(0)


def test_mit_logo_stehen_alle_drei_bloecke_in_der_tabelle(profil_mit_logo):
    """Der Punkt der Änderung. Vorher trug die Tabelle nur den Namen, und die
    beiden anderen Blöcke standen darunter — das sah aus wie ein Zitatblock
    mit einem Bild davor."""
    tabelle = _signaturtabelle(_seite_mit_logo(profil_mit_logo))
    assert tabelle.count("<p ") == 3, tabelle
    assert "Erika Muster" in tabelle
    assert "Telefon" in tabelle
    assert "USt-IdNr" in tabelle


def test_die_trennlinie_steht_zwischen_den_spalten(profil_mit_logo):
    tabelle = _signaturtabelle(_seite_mit_logo(profil_mit_logo))
    zelle = re.search(r'<td class="([^"]*)" style="([^"]*)"', tabelle)
    assert zelle, tabelle
    assert f"border-left: 1px solid {html.RAHMEN}" in zelle.group(2)
    assert html.KLASSE_LINIE in zelle.group(1), "sonst bleibt die Linie im Dunkeln hell"


def test_die_linie_zur_nachricht_steht_genau_einmal(profil_mit_logo):
    """Mit Logo trägt die Tabelle sie, ohne Logo der erste Absatz. Zweimal wäre
    ein Strich quer durch die rechte Spalte."""
    seite = _seite_mit_logo(profil_mit_logo)
    assert seite.count("border-top: 1px solid") == 1, seite


def test_mit_logo_schaltet_alles_um(profil_mit_logo):
    """Die Probe, die bis #243 fehlte: `test_alles_schaltet_um` läuft über die
    Beispiele, und keines davon führt ein Logo. Gemessen am Stand davor meldete
    diese Prüfung `border: 0` am Bild — unbemerkt, weil niemand hinsah."""
    assert html.nicht_umschaltbar(_seite_mit_logo(profil_mit_logo)) == []


def test_mit_logo_bleibt_die_nachricht_ohne_verstoss(profil_mit_logo):
    assert html.verstoesse(_seite_mit_logo(profil_mit_logo)) == []


def test_ohne_logo_entsteht_keine_signaturtabelle():
    """Die Tabelle greift nur, wenn ein Logo da ist — sonst stünde links eine
    leere Spalte und ein Trenner ohne Gegenüber."""
    seite = _seite()
    signatur = seite[seite.index("border-top: 1px solid"):]
    assert "<table" not in signatur, signatur[:400]


def test_die_pruefung_bemerkt_eine_vergessene_trennlinie(profil_mit_logo):
    """Gegenprobe zur Trennlinie — und zugleich die einzige Probe, die den
    Eintrag `border-left:` in `UMSCHALTPFLICHTIG` festhält.

    Ohne ihn könnte `nicht_umschaltbar()` an der neuen Linie nie rot werden:
    `"border:" in stil` trifft `border-left:` nicht, weil dazwischen ein
    Bindestrich steht und kein Doppelpunkt. Gemessen am 07.09.2026 — die
    Sabotage „Eintrag entfernt" blieb grün, solange die Zelle ihre Klasse trug.
    Erst beides zusammen zeigt, was hier wovon abhängt.
    """
    seite = _seite_mit_logo(profil_mit_logo)
    ohne = seite.replace(f'<td class="{html.KLASSE_TEXT} {html.KLASSE_LINIE}" style="padding',
                         f'<td class="{html.KLASSE_TEXT}" style="padding', 1)
    assert ohne != seite, "die Sabotage griff nicht — der Test misst sich selbst"
    befunde = html.nicht_umschaltbar(ohne)
    assert any("border-left:" in b for b in befunde), befunde


def test_das_logo_beispielprofil_ist_die_kopie_mit_genau_einer_aenderung():
    """`examples/email/profiles/email-logo.yaml` ist das Beispielprofil plus
    `email.logo`. Ohne diese Prüfung driftete die Kopie still auseinander, und
    das Logo-Golden zeigte irgendwann etwas anderes als die fünf daneben.
    """
    ausgeliefert = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    kopie = yaml.safe_load(
        (REPO / "examples" / "email" / "profiles" / "email-logo.yaml").read_text(encoding="utf-8"))

    assert ausgeliefert["email"]["logo"] is False, "das Beispielprofil führt kein Logo"
    assert kopie["email"]["logo"] == "assets/mail-logo.png"

    # Der Rest muss Zeichen für Zeichen dasselbe sein. Verglichen wird nach dem
    # Angleichen genau dieses einen Feldes — was danach noch abweicht, ist Drift.
    kopie["email"]["logo"] = False
    assert kopie == ausgeliefert, "die Kopie weicht über `email.logo` hinaus ab"


# ── Drei Wege für dasselbe Logo (#243, Punkt 2) ─────────────────────────────
#
# `email.logo` nimmt seit #243 auch eine Adresse und eine Data-URI. Der Grund
# ist der Signatur-Baukasten auf falzmarke.com: Eine Webseite hat keinen
# MIME-Container und kann deshalb keinen CID-Anhang erzeugen — dort fehlte das
# Logo bis dahin ganz. Die Dateiform bleibt die Vorgabe; was die beiden anderen
# beim Empfänger kosten, sagt `eml.logo_hinweis()` beim Setzen.

import base64                                                     # noqa: E402

#: Ein gültiges PNG als Data-URI — dasselbe Bild wie im Logo-Beispiel.
def _datenuri() -> str:
    roh = (REPO / "examples" / "email" / "profiles" / "assets" / "mail-logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(roh).decode("ascii")


ADRESSE = "https://example.invalid/logo.png"


@pytest.fixture
def profil_mit(tmp_path):
    """Das Beispielprofil mit einem beliebigen `email.logo`-Wert."""
    def bauen(wert):
        ziel = tmp_path / "profiles"
        if not ziel.exists():
            shutil.copytree(PROFILE, ziel)
        pfad = ziel / "example.yaml"
        profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
        profil["email"]["logo"] = wert
        pfad.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
        return profil, pfad
    return bauen


@pytest.mark.parametrize("wert,art", [
    ("assets/mail-logo.png", "datei"),
    (ADRESSE, "url"),
    ("data:image/png;base64,x", "daten"),
])
def test_die_form_wird_am_wert_erkannt(wert, art, profil_mit, tmp_path):
    profil, pfad = profil_mit(wert)
    if art == "datei":
        (pfad.parent / "assets" / "mail-logo.png").write_bytes(
            (REPO / "examples" / "email" / "profiles" / "assets" / "mail-logo.png").read_bytes())
    assert eml._logo_art(str(profil["email"]["logo"])) == art


def test_die_adresse_steht_im_src(profil_mit):
    profil, pfad = profil_mit(ADRESSE)
    seite = eml.htmlteil(KOPF_LOGO, profil, [], logo=eml.logo_quelle(profil, pfad))
    assert f'src="{ADRESSE}"' in seite, seite[seite.find("<img"):][:200]
    assert "cid:" not in seite


def test_die_datenuri_steht_im_src(profil_mit):
    profil, pfad = profil_mit(_datenuri())
    seite = eml.htmlteil(KOPF_LOGO, profil, [], logo=eml.logo_quelle(profil, pfad))
    assert 'src="data:image/png;base64,' in seite


def test_nur_die_datei_wird_angehaengt(profil_mit):
    """Eine Adresse und eine Data-URI brauchen keinen `related`-Teil — und
    dürfen keinen bekommen: Ein Anhang, auf den nichts zeigt, erscheint in der
    Anlagenliste des Empfängers."""
    for wert, erwartet in ((ADRESSE, False), (_datenuri(), False)):
        profil, pfad = profil_mit(wert)
        nachricht = _nachricht(profil, pfad)
        typen = [t.get_content_type() for t in nachricht.walk()]
        assert ("multipart/related" in typen) is erwartet, (wert[:40], typen)


def test_beide_neuen_formen_bleiben_ohne_verstoss(profil_mit):
    """Die Lockerung ist der Punkt: Bis #243 meldete `verstoesse()` beide."""
    for wert in (ADRESSE, _datenuri()):
        profil, pfad = profil_mit(wert)
        seite = eml.htmlteil(KOPF_LOGO, profil, [], logo=eml.logo_quelle(profil, pfad))
        assert html.verstoesse(seite) == [], wert[:40]


def test_die_datenuri_traegt_ihre_masse(profil_mit):
    """Aus den Bytes gerechnet, nicht geraten. Ohne Maße meldet `verstoesse()`
    „Bild ohne Breiten- oder Höhenangabe" — und kein Client reserviert Platz."""
    profil, pfad = profil_mit(_datenuri())
    seite = eml.htmlteil(KOPF_LOGO, profil, [], logo=eml.logo_quelle(profil, pfad))
    assert re.search(r'<img[^>]+width="\d+" height="40"', seite), seite[seite.find("<img"):][:200]


def test_die_adresse_traegt_wenigstens_die_hoehe(profil_mit):
    """Die Breite steht nur im Bild, und das abzurufen ist nicht Sache dieses
    Werkzeugs (ADR 0034). Was fehlt, sagt der Hinweis."""
    profil, pfad = profil_mit(ADRESSE)
    seite = eml.htmlteil(KOPF_LOGO, profil, [], logo=eml.logo_quelle(profil, pfad))
    marke = seite[seite.find("<img"):][:250]
    assert 'height="40"' in marke, marke
    assert "width=" not in marke, marke


@pytest.mark.parametrize("wert,erwartet", [
    ("assets/mail-logo.png", None),
    (ADRESSE, "blockieren externe Bilder"),
    ("data:image/png;base64,x", "vergrößert aber jede Nachricht"),
])
def test_die_wahl_wird_benannt(wert, erwartet):
    """Das Issue verlangt es ausdrücklich: Die Website soll den Hinweis
    übernehmen können, statt ihn selbst zu erfinden. Zur Dateiform gibt es
    nichts zu sagen — ein Satz bei jedem Lauf wäre Lärm."""
    hinweis = eml.logo_hinweis(eml.Logo(eml._logo_art(wert), wert, None))
    assert (erwartet in hinweis) if erwartet else (hinweis is None), hinweis


@pytest.mark.parametrize("wert,wort", [
    ("data:image/svg+xml;base64,x", "Rasterbild"),
    ("data:text/plain;base64,x", "Rasterbild"),
    ("data:image/png,nichtbase64", "base64"),
    ("https://example.invalid/logo.svg", "Rasterbild"),
])
def test_untaugliche_formen_fallen_auf(wert, wort, profil_mit):
    """SVG ist in Outlook tot, egal über welchen Weg es kommt — die Prüfung
    gilt für alle drei Formen, nicht nur für die Datei."""
    profil, pfad = profil_mit(wert)
    with pytest.raises(ValueError, match=wort):
        eml.logo_quelle(profil, pfad)


def test_eine_adresse_ohne_endung_geht_durch(profil_mit):
    """Was hinter `…/logo?id=7` liegt, weiß nur der Server. Danach zu fragen
    hieße, die Adresse abzurufen — die Prüfung greift, wo sie greifen kann, und
    behauptet nicht mehr."""
    profil, pfad = profil_mit("https://example.invalid/logo?id=7")
    assert eml.logo_quelle(profil, pfad).art == "url"
