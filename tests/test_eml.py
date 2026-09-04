"""Die E-Mail-Fassung als Datei: `.eml` und die Begleitdateien (#63).

Zwei Zusagen tragen alles andere und werden deshalb gegen ihre Gegenprobe
geprüft: **Sie versendet nichts** — keine Message-ID, kein Weg nach außen — und
**zwei Läufe mit `SOURCE_DATE_EPOCH` ergeben dieselben Bytes**, sonst ist ein
Golden-Vergleich unmöglich und jede Änderung sieht aus wie eine Änderung.

`Date` steht seit #236 in jeder Datei und ist damit das einzig Veränderliche;
die Byte-Zusage gilt deshalb nur noch mit gesetzter Umgebungsvariablen.
"""

from __future__ import annotations

import email
import os
from email import policy
from email.utils import formatdate, parsedate_to_datetime
from pathlib import Path

import pytest
import yaml

from falzmarke import eml, emit_html, markdown as md
from conftest import SKILL

PROFIL_DATEI = SKILL / "falzmarke" / "typst" / "profiles" / "example.yaml"
QUELLE = "wie besprochen erhalten Sie das Angebot.\n\n- Punkt eins\n- Punkt zwei\n"
KOPF = {
    "an": ["erika.muster@example.de", "Müller GmbH <post@example.de>"],
    "cc": "zweiter@example.de",
    "betreff": "Angebot Nr. 2026-0815 — Überprüfung",
    "anrede": "Sehr geehrte Frau Muster,",
    "unterzeichner": "Erika Muster",
}


@pytest.fixture
def profil() -> dict:
    return yaml.safe_load(PROFIL_DATEI.read_text(encoding="utf-8"))


@pytest.fixture
def bloecke():
    return md.lies(QUELLE)


def _baue(profil, bloecke, kopf=None, **kw):
    return eml.baue(kopf or KOPF, profil, QUELLE, bloecke, **kw)


def _geparst(nachricht):
    return email.message_from_bytes(nachricht.as_bytes(), policy=policy.default)


def _teile(nachricht) -> list[str]:
    return [t.get_content_type() for t in _geparst(nachricht).walk()
            if t.get_content_maintype() != "multipart"]


# ── Sie versendet nichts ────────────────────────────────────────────────────

def test_keine_message_id(profil, bloecke):
    """Eine `.eml` mit eigener Message-ID ist keine Vorlage mehr, sondern eine
    Mail, die es nie gab."""
    assert _baue(profil, bloecke)["Message-ID"] is None


def test_date_auch_ohne_source_date_epoch(profil, bloecke, monkeypatch):
    """RFC 5322 führt `orig-date` als Pflichtfeld. Fehlte es, zeigte das
    Mailprogramm beim Weiterleiten „(null), (null)" im Text an (#236)."""
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    gesetzt = _baue(profil, bloecke)["Date"]
    assert gesetzt is not None
    assert parsedate_to_datetime(str(gesetzt)) is not None


def test_source_date_epoch_hat_vorrang(profil, bloecke, monkeypatch):
    """Gegenprobe zum Test darüber: Ohne sie wüsste man nur, dass irgendein
    Datum dasteht — nicht, dass die Umgebung es bestimmen kann. Genau darauf
    stehen die Goldens."""
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1788134400")
    assert _baue(profil, bloecke)["Date"] == formatdate(1788134400.0, localtime=False)


# ── Zwei Läufe, dieselben Bytes ─────────────────────────────────────────────

def test_zwei_laeufe_sind_byteidentisch(profil, bloecke, monkeypatch):
    """Nur mit `SOURCE_DATE_EPOCH`. Seit #236 trägt jede Nachricht ein `Date`;
    ohne die Variable ist es der Erzeugungszeitpunkt, und zwei Läufe über eine
    Sekundengrenze ergäben verschiedene Bytes. Diesen Fall hier zu prüfen wäre
    ein Test, der meistens grün ist und gelegentlich rot — die teuerste Sorte.
    Die Zusage lautet deshalb genau so weit, wie sie trägt."""
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1788134400")
    assert _baue(profil, bloecke).as_bytes() == _baue(profil, bloecke).as_bytes()


def test_eine_andere_quelle_ergibt_andere_bytes(profil):
    """Gegenprobe: Wären die Trennstrings konstant statt aus der Quelle
    abgeleitet, wäre der Test darüber trivial grün."""
    a = eml.baue(KOPF, profil, QUELLE, md.lies(QUELLE)).as_bytes()
    b = eml.baue(KOPF, profil, QUELLE + "Ein Satz mehr.\n",
                 md.lies(QUELLE + "\nEin Satz mehr.\n")).as_bytes()
    assert a != b


def test_geschachtelte_teile_haben_verschiedene_trennstrings(profil, bloecke, tmp_path):
    """Trügen zwei Ebenen denselben, endete die äußere dort, wo die innere
    beginnt — und kein Parser fände den Anhang."""
    anlage = tmp_path / "angebot.pdf"
    anlage.write_bytes(b"%PDF-1.4 x")
    nachricht = _baue(profil, bloecke, kopf={**KOPF, "anlagen_dateien": ["angebot.pdf"]},
                      brief_pfad=tmp_path / "m.md")
    grenzen = [t.get_boundary() for t in nachricht.walk()
               if t.get_content_maintype() == "multipart"]
    assert len(grenzen) == len(set(grenzen)) == 2, grenzen


# ── Aufbau ──────────────────────────────────────────────────────────────────

def test_ohne_anhang_nur_alternative(profil, bloecke):
    assert _geparst(_baue(profil, bloecke)).get_content_type() == "multipart/alternative"
    assert _teile(_baue(profil, bloecke)) == ["text/plain", "text/html"]


def test_mit_anhang_kommt_mixed_darueber(profil, bloecke, tmp_path):
    (tmp_path / "angebot.pdf").write_bytes(b"%PDF-1.4 kein echtes PDF")
    nachricht = _baue(profil, bloecke, kopf={**KOPF, "anlagen_dateien": ["angebot.pdf"]},
                      brief_pfad=tmp_path / "m.md")
    geparst = _geparst(nachricht)
    assert geparst.get_content_type() == "multipart/mixed"
    anhang = [t for t in geparst.walk() if t.get_filename()][0]
    assert anhang.get_filename() == "angebot.pdf"
    assert anhang.get_content() == b"%PDF-1.4 kein echtes PDF"


def test_fehlende_anlage_bricht_ab(profil, bloecke, tmp_path):
    with pytest.raises(FileNotFoundError):
        _baue(profil, bloecke, kopf={**KOPF, "anlagen_dateien": ["fehlt.pdf"]},
              brief_pfad=tmp_path / "m.md")


def test_textteil_ist_flowed(profil, bloecke):
    teil = [t for t in _geparst(_baue(profil, bloecke)).walk()
            if t.get_content_type() == "text/plain"][0]
    assert teil.get_param("format") == "flowed"
    assert teil.get_param("delsp") == "yes"


@pytest.mark.parametrize("art", ["text/plain", "text/html"])
def test_text_nie_base64(profil, bloecke, art):
    """Eine Mail, deren Textteil als base64 ankommt, ist in jedem
    Rohansicht-Fenster unlesbar — und die Rohansicht ist das, was von einer
    `.eml` als Vorlage übrig bleibt."""
    teil = [t for t in _geparst(_baue(profil, bloecke)).walk()
            if t.get_content_type() == art][0]
    assert teil["Content-Transfer-Encoding"] == "quoted-printable"


def test_kopfzeilen_ueberstehen_den_parser(profil, bloecke):
    geparst = _geparst(_baue(profil, bloecke, kopf={**KOPF, "antwort_auf": "<k@example.de>"}))
    assert geparst["From"] == "Erika Muster <muster@example.de>"
    assert "post@example.de" in geparst["To"] and "erika.muster@example.de" in geparst["To"]
    assert geparst["Cc"] == "zweiter@example.de"
    assert geparst["Subject"] == KOPF["betreff"]
    assert geparst["In-Reply-To"] == "<k@example.de>"
    assert geparst["References"] == "<k@example.de>"


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_content_language_steht_im_umschlag(profil, bloecke, sprache):
    """`set_content` und `add_alternative` räumen jede `Content-*`-Kopfzeile
    aus dem Umschlag. Vorher gesetzt war sie am Ende spurlos weg — weder oben
    noch in einem der Teile."""
    nachricht = _baue(profil, bloecke, kopf={**KOPF, "sprache": sprache})
    assert _geparst(nachricht)["Content-Language"] == sprache


# ── Die Quelle reist nur auf Verlangen mit (ADR 0034, Punkt 3) ──────────────

def test_ohne_quellteil_als_vorgabe(profil, bloecke):
    assert "text/markdown" not in _teile(_baue(profil, bloecke))


def test_mit_quelle_haengt_die_quelle_an(profil, bloecke):
    nachricht = _baue(profil, bloecke, mit_quelle=True)
    assert _teile(nachricht) == ["text/plain", "text/markdown", "text/html"]
    teil = [t for t in _geparst(nachricht).walk()
            if t.get_content_type() == "text/markdown"][0]
    assert teil.get_param("variant") == "CommonMark"
    assert teil.get_content().strip() == QUELLE.strip()


# ── Signatur ────────────────────────────────────────────────────────────────

def test_signatur_beginnt_mit_der_trennzeile(profil, bloecke):
    text = eml.textteil(KOPF, profil, bloecke)
    assert f"\n{eml.SIGNATUR_TRENNER}\n" in text
    assert eml.SIGNATUR_TRENNER.endswith(" "), "der Trenner ist `-- ` mit Leerzeichen"


def test_die_trennzeile_uebersteht_quoted_printable(profil, bloecke):
    """Das Leerzeichen am Ende ist Teil der Trennzeile. Ohne Kodierung würde es
    unterwegs abgeschnitten und die Signatur wäre keine mehr."""
    roh = _baue(profil, bloecke).as_string()
    assert "--=20" in roh, roh[:400]


def test_signatur_ohne_doppelungen(profil):
    """Die Fußzeile eines Briefes trägt die Anschrift ein zweites Mal — auf
    Papier in einer anderen Spalte, in einer Signatur untereinander."""
    zeilen = eml.signatur_zeilen(profil, KOPF)
    schluessel = [" ".join(z.split()).casefold() for z in zeilen]
    assert len(schluessel) == len(set(schluessel)), zeilen


def test_ohne_pflichtangaben_kommt_die_anschrift_aus_dem_absender(profil):
    ohne = {**profil, "email": {k: v for k, v in profil["email"].items()
                                if k != "pflichtangaben"}}
    zeilen = eml.signatur_zeilen(ohne, KOPF)
    assert any("Musterweg 12" in z and "93055" in z for z in zeilen), zeilen


def test_die_reihenfolge_steht_fest(profil):
    zeilen = eml.signatur_zeilen(profil, KOPF)
    assert zeilen[0] == "Erika Muster"
    assert zeilen.index("Geschäftsführerin") < zeilen.index("muster@example.de")
    assert zeilen[-1].startswith("Diese E-Mail")


def test_ohne_absender_gibt_es_kein_from(profil, bloecke):
    ohne = {**profil, "email": {}}
    with pytest.raises(ValueError, match="email.absender"):
        eml.baue(KOPF, ohne, QUELLE, bloecke)


# ── Begleitdateien ──────────────────────────────────────────────────────────

def test_begleit_html_traegt_den_vorschaukopf(profil, bloecke):
    seite = eml.begleit_html(KOPF, profil, bloecke)
    assert "Betreff:" in seite and "An:" in seite


def test_der_vorschaukopf_steht_nicht_in_der_mail(profil, bloecke):
    """Dort stünden An und Betreff ein zweites Mal — unter denen, die der
    Mailclient ohnehin anzeigt."""
    assert "Betreff:" not in eml.htmlteil(KOPF, profil, bloecke)


def test_schreibe_legt_drei_dateien_an(profil, bloecke, tmp_path):
    nachricht = _baue(profil, bloecke)
    dateien = eml.schreibe(nachricht, tmp_path / "nachricht",
                           html=eml.begleit_html(KOPF, profil, bloecke),
                           text=eml.textteil(KOPF, profil, bloecke))
    assert sorted(p.suffix for p in dateien) == [".eml", ".html", ".txt"]
    assert all(p.stat().st_size > 0 for p in dateien)


def test_schreibe_hinterlaesst_keine_reste(profil, bloecke, tmp_path):
    nachricht = _baue(profil, bloecke)
    eml.schreibe(nachricht, tmp_path / "nachricht", html="<p>x</p>", text="x")
    assert [p.name for p in tmp_path.iterdir() if p.suffix == ".teil"] == []


def test_schreibe_ersetzt_eine_bestehende_fassung(profil, bloecke, tmp_path):
    ziel = tmp_path / "nachricht"
    ziel.with_suffix(".txt").write_text("alt", encoding="utf-8")
    eml.schreibe(_baue(profil, bloecke), ziel, html="<p>x</p>", text="neu")
    assert ziel.with_suffix(".txt").read_text(encoding="utf-8") == "neu"


# ── Die erweiterte Grenze (#104) ────────────────────────────────────────────

@pytest.mark.parametrize("html,erwartet", [
    ('<img src="data:image/png;base64,iVBOR" alt="x" width="10" height="10">',
     "data:-URL"),
    ('<img src="cid:x" alt="x">', "Breiten- oder Höhenangabe"),
    ('<form action="https://x.invalid"></form>', "Formular"),
    ('<td onclick="x()">a</td>', "Ereignis-Attribut"),
    ('<table><tr><td>a</td></tr></table>', "role=presentation"),
])
def test_was_eine_erzeugte_mail_nicht_enthalten_darf(html, erwartet):
    """Die Liste aus #104. Jeder Fall einzeln, sonst deckt ein Treffer den
    nächsten zu."""
    gefunden = " | ".join(emit_html.verstoesse(html))
    assert erwartet in gefunden, f"{erwartet!r} fehlt in: {gefunden!r}"


@pytest.mark.parametrize("html", [
    '<img src="cid:x" alt="x" width="120" height="40">',
    '<table role="presentation"><tr><td>a</td></tr></table>',
    '<table><tr><th>Kopf</th></tr><tr><td>a</td></tr></table>',
])
def test_und_was_sie_enthalten_darf(html):
    """Ohne die Gegenstücke wüsste man nur, dass die Prüfung meldet — nicht,
    ob sie trifft."""
    assert emit_html.verstoesse(html) == []


def test_eine_datentabelle_im_umschlag_wird_noch_gesehen():
    """Der Fall, an dem das erste Muster scheiterte: `<table>(.*?)</table>`
    fand beim Umschlag das Ende der INNEREN Tabelle und übersprang deren
    Anfang — eine Datentabelle ohne Kopf blieb dadurch unbemerkt."""
    html = ('<table role="presentation"><tr><td>'
            '<table><tr><td>ohne Kopf</td></tr></table>'
            "</td></tr></table>")
    assert emit_html.verstoesse(html), "die innere Tabelle wurde übersehen"


def test_der_umschlag_traegt_beide_breiten():
    """Die Word-Engine liest das Attribut, alle anderen lesen den Stil. Ein
    einzelner Wert könnte nur eines von beidem (#104)."""
    seite = emit_html.dokument("<p>Text</p>")
    assert 'width="600"' in seite, "das Attribut fehlt — Outlook liefe über die volle Breite"
    assert "max-width: 600px" in seite, "der Stil fehlt — alle anderen schrumpfen nicht mit"
    assert 'role="presentation"' in seite
    assert '<div style="max-width' not in seite, "der alte div-Umschlag steht noch da"
