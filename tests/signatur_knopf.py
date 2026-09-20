#!/usr/bin/env python3
"""Signaturen mit Knopf — als Daten, für `verify --email` (#322).

Zwei Testdateien brauchen dieselben Fälle: `test_verify_email.py` misst, was die
Prüfung meldet und wie, `test_gegenbeweis.py` hält die zwei Proben fest, ohne
die sie nichts belegt. Eine eigene Fassung je Datei liefe auseinander — und die
Gegenprobe prüfte dann nicht mehr dieselbe Signatur wie der Test, den sie
absichert.

**Der Anlass.** Am 14.09.2026 gingen zwei Mails mit der Signatur `blitzsicht`
raus. `verify --email` meldete 27/27 und 29/29, in Outlook für Mac zerfiel der
Termin-Knopf: Outlook ignoriert `display:inline-block`, `margin` und `padding`
auf einem `<a>`. Der Google-Knopf derselben Signatur stand in einem
`<table><td>`-Gerüst und hielt seine Form. Beide Knöpfe stehen deshalb in jeder
Signatur hier: der richtig gebaute als Kontrolle, dass die Prüfung nicht jeden
Knopf beanstandet, der falsche als das, was sie treffen muss.

Die Signatur ist ein Fragment, kein Dokument: `mitgebrachte_signatur` nimmt ein
Fragment ohne `<body>` ganz, und so liefert `cw-core` sie auch aus.
"""

from __future__ import annotations

from pathlib import Path

from falzmarke import eml, markdown as md

QUELLE = "wie besprochen erhalten Sie das Angebot.\n"
KOPF = {"an": "erika.muster@example.de", "betreff": "Angebot Nr. 2026-0815",
        "anrede": "Sehr geehrte Frau Muster,", "unterzeichner": "Erika Muster"}

#: Jedes Wort steht auch im HTML unten. Die Prüfung „Text und HTML sagen
#: dasselbe" ist Teil des Berichts — eine Signatur, deren Textfassung Wörter
#: trägt, die im HTML fehlen, macht die Kontrolle rot, ohne dass es am Knopf
#: läge.
SIGNATUR_TEXT = "Erika Muster\nTermin vereinbaren\nBewertung abgeben\n"

NAME = ('<p style="margin: 0 0 2px; font-size: 14px; color: #1a1a1a;">Erika Muster</p>')

#: Der Google-Knopf, wie ihn `blitzsicht.html` trägt: Tabelle, Zelle mit Rahmen
#: und Innenabstand, der Anker darin nur mit Farbe. Gemessen am 14.09.2026: Er
#: hält in Outlook seine Form. Steht in JEDER Signatur unten und darf nie
#: beanstandet werden.
TABELLENKNOPF_BEWERTEN = (
    '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
    'style="margin: 8px 0 0;"><tr>'
    '<td style="padding: 6px 12px; border: 1px solid #1a3a5c;">'
    '<a href="https://example.de/bewerten" '
    'style="font-size: 13px; color: #1a3a5c; text-decoration: none;">Bewertung abgeben</a>'
    '</td></tr></table>'
)

#: Der Termin-Knopf im Zustand vom 14.09.2026: ein Anker, der selbst Kasten sein
#: will. Zeichengenau die Form aus `blitzsicht.html`.
ANKERKNOPF_TERMIN = (
    '<a href="https://example.de/termin" '
    'style="display:inline-block;margin-top:10px;padding:6px 12px;'
    'border:1px solid #1a3a5c;font-size:13px;color:#1a3a5c;text-decoration:none;">'
    'Termin vereinbaren</a>'
)

#: Derselbe Knopf im Gerüst des Google-Knopfes — gleiches Aussehen, gleicher Text,
#: gleiches Ziel, nur der Aufbau ist ein anderer. Genau das ist die zweite Probe
#: der Gegenbeweis-Pflicht: ohne sie wüsste man nicht, ob die Prüfung überhaupt
#: zwischen den beiden Aufbauten unterscheidet.
TABELLENKNOPF_TERMIN = (
    '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
    'style="margin: 10px 0 0;"><tr>'
    '<td style="padding: 6px 12px; border: 1px solid #1a3a5c;">'
    '<a href="https://example.de/termin" '
    'style="font-size: 13px; color: #1a3a5c; text-decoration: none;">Termin vereinbaren</a>'
    '</td></tr></table>'
)


def signatur(termin_knopf: str) -> str:
    """Eine Signatur: Name, Termin-Knopf nach Wahl, danach der Google-Knopf."""
    return f"{NAME}\n{termin_knopf}\n{TABELLENKNOPF_BEWERTEN}\n"


def eml_mit_signatur(tmp_path: Path, signatur_html: str) -> Path:
    """Eine echte `.eml` aus dem echten Erzeuger, mit dieser Signatur darin.

    Über `eml.baue` und nicht von Hand geschrieben: Eine selbst gebaute Datei
    bestünde die übrigen Prüfungen nicht, und dann wäre nicht zu sehen, welche
    den Ausschlag gibt. Das Profil ist so klein wie möglich — allein die
    Signatur soll den Unterschied machen.
    """
    (tmp_path / "sig.html").write_text(signatur_html, encoding="utf-8")
    (tmp_path / "sig.txt").write_text(SIGNATUR_TEXT, encoding="utf-8")
    profil = {"email": {"absender": "muster@example.de",
                        "signatur_html": "sig.html", "signatur_text": "sig.txt"}}
    nachricht = eml.baue(KOPF, profil, QUELLE, md.lies(QUELLE),
                         profil_pfad=tmp_path / "profil.yaml")
    pfad = tmp_path / "mit-signatur.eml"
    pfad.write_text(nachricht.as_string(), encoding="utf-8", newline="")
    return pfad


def html_der_eml(pfad: Path) -> str:
    """Der HTML-Teil, dekodiert — so wie ihn ein Mailprogramm liest.

    Für die Kontrollfrage jeder Sabotage: Steht sie in der fertigen Datei? Die
    Rohdatei ist quoted-printable und bricht Zeilen, ein `in` auf ihr fände den
    Anker nicht.
    """
    import email
    from email import policy

    nachricht = email.message_from_bytes(pfad.read_bytes(), policy=policy.default)
    return nachricht.get_body(preferencelist=("html",)).get_content()
