"""Die HTML-Signatur steckt in `<div class="moz-signature">` (ADR 0051, Nachtrag).

ANLASS (21.10.2026, gemessen): Beim Senden des Postfach-Entwurfs fragte
Thunderbird „Haben Sie vergessen, einen Anhang anzufügen?“. Auslöser war das
Wort „Anhänge“ im Hinweis der Signatur. Die Anhang-Erinnerung nimmt vor ihrer
Suche alles mit der Klasse `moz-signature` heraus (`MsgComposeCommands.js`,
Thunderbird 158.0) — steht die Signatur darin, fragt sie nicht mehr.

Geprüft wird an jedem Mail-Beispiel: Gibt es eine Signatur (der Textteil trägt
den Trenner `-- `), steckt die HTML-Signatur in genau einem Element mit dieser
Klasse, und der Text der Nachricht steht nicht darin.
"""

from __future__ import annotations

import email
import re
from email import policy
from html.parser import HTMLParser
from pathlib import Path

import pytest

from conftest import EMAIL_BEISPIELE
from falzmarke import cli as falzmarke
from falzmarke import eml

LEERE = {"br", "img", "hr", "meta", "link", "input", "col", "wbr", "source"}


class _Signaturtext(HTMLParser):
    """Sammelt den Text in Elementen mit der Klasse `eml.KLASSE_SIGNATUR`."""

    def __init__(self, klasse: str):
        super().__init__()
        self.klasse = klasse
        self.tiefe = 0
        self.elemente = 0
        self.innen: list[str] = []
        self.aussen: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in LEERE:
            return
        if self.tiefe:
            self.tiefe += 1
            return
        klassen = (dict(attrs).get("class") or "").split()
        if self.klasse in klassen:
            self.elemente += 1
            self.tiefe = 1

    def handle_endtag(self, tag):
        if tag not in LEERE and self.tiefe:
            self.tiefe -= 1

    def handle_data(self, data):
        (self.innen if self.tiefe else self.aussen).append(data)


def _zeichen(text: str) -> str:
    """Nur Buchstaben und Ziffern. URLs fallen weg: Im Textteil steht die
    Adresse hinter dem Linktext, im HTML-Teil nur im `href`."""
    return re.sub(r"\W+", "", re.sub(r"https?://\S+", "", text)).casefold()


def signaturteile(html: str, klasse: str = "moz-signature") -> _Signaturtext:
    leser = _Signaturtext(klasse)
    leser.feed(html)
    return leser


def _teile(pfad: Path) -> tuple[str, str]:
    nachricht = email.message_from_bytes(pfad.read_bytes(), policy=policy.default)
    text = nachricht.get_body(("plain",)).get_content()
    html = nachricht.get_body(("html",)).get_content()
    return text, html


@pytest.fixture(scope="module")
def beispiele(tmp_path_factory) -> dict[str, tuple[str, str]]:
    ziel = tmp_path_factory.mktemp("moz")
    ergebnis = {}
    for quelle in EMAIL_BEISPIELE:
        pfad, _ = falzmarke.setze_email(quelle, ziel / quelle.stem)
        ergebnis[quelle.stem] = _teile(pfad)
    return ergebnis


def test_die_klasse_ist_die_von_thunderbird():
    assert eml.KLASSE_SIGNATUR == "moz-signature"


def test_es_gibt_beispiele_mit_signatur(beispiele):
    mit = [n for n, (text, _) in beispiele.items() if "\n-- \n" in text]
    assert len(mit) >= 3, mit
    assert "email-signatur" in mit, "die mitgebrachte Signatur (#275) muss dabei sein"


@pytest.mark.parametrize("name", [q.stem for q in EMAIL_BEISPIELE])
def test_die_signatur_steckt_genau_einmal_in_moz_signature(beispiele, name):
    text, html = beispiele[name]
    leser = signaturteile(html)
    if "\n-- \n" not in text:
        assert leser.elemente == 0, "ohne Signatur kein Signaturelement"
        return
    assert leser.elemente == 1, f"{leser.elemente} Elemente mit moz-signature"
    innen = _zeichen(" ".join(leser.innen))
    # Die letzte Zeile der Klartext-Signatur steht in der HTML-Signatur.
    letzte = [z for z in text.split("\n-- \n", 1)[1].splitlines() if _zeichen(z)][-1]
    assert _zeichen(letzte) in innen, (letzte, innen[:200])
    # Und die Nachricht selbst steht nicht darin: Die erste Zeile des Texts
    # (die Anrede) liegt außerhalb.
    erste = next(z for z in text.splitlines() if _zeichen(z))
    assert _zeichen(erste) not in innen
    assert _zeichen(erste) in _zeichen(" ".join(leser.aussen))


def test_gegenprobe_ohne_klasse_findet_der_leser_nichts(beispiele):
    _, html = beispiele["email-signatur"]
    assert signaturteile(html).elemente == 1
    assert signaturteile(html.replace("moz-signature", "fm-x")).elemente == 0
