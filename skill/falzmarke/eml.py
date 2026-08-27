#!/usr/bin/env python3
"""Baut die E-Mail-Fassung: `.eml` und die Begleitdateien.

**Sie erzeugt eine Datei und versendet nichts** — ADR 0034. Es gibt hier keinen
Versandweg, keine Verbindung nach außen und keine Kopfzeile, die eine Mail zu
einer bereits verschickten machen würde.

Genau darum fehlen zwei Kopfzeilen, die jeder Mailclient selbst setzt:

* **`Message-ID`** — eine `.eml` mit eigener Message-ID ist keine Vorlage mehr,
  sondern eine Mail, die es nie gab. Zwei Läufe ergäben zwei Nachrichten, die
  denselben Text tragen und sich als verschieden ausgeben.
* **`Date`** — außer bei gesetztem `SOURCE_DATE_EPOCH`. Das Datum entsteht beim
  Versand, nicht beim Setzen; ein Entwurf von gestern, der heute rausgeht, wäre
  sonst auf gestern datiert.

`SOURCE_DATE_EPOCH` ist zugleich der Weg zu einem Golden-Vergleich. Ohne ihn
bleibt nur die Zeit veränderlich — die Trennstrings der Teile sind es nicht:
Sie werden aus einem Hash der Quelle gebildet, nicht gewürfelt. Zwei Läufe über
dieselbe Datei ergeben damit dieselben Bytes.

Die Standardbibliothek reicht: `email.message.EmailMessage`. Keine neue
Abhängigkeit für etwas, das seit Python 3.6 im Kern liegt.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, parseaddr
from pathlib import Path

from falzmarke import baum, emit_html, emit_text

#: Reihenfolge der Signatur. Fest, nicht konfigurierbar: Eine Signatur, deren
#: Reihenfolge jeder selbst wählt, ist keine Signatur mehr, sondern ein
#: Textfeld — und die Pflichtangaben rutschen dann irgendwohin.
SIGNATUR_TRENNER = "-- "


def _als_liste(wert) -> list[str]:
    if wert is None:
        return []
    return [wert] if isinstance(wert, str) else [str(z) for z in wert]


def _adressliste(wert) -> str:
    """`an:`/`cc:` als Kopfzeilenwert. Umlaute im Namen kodiert `EmailMessage`."""
    teile = []
    for eintrag in _als_liste(wert):
        name, adresse = parseaddr(eintrag)
        nutzer, _, wirt = adresse.partition("@")
        teile.append(str(Address(name, nutzer, wirt)))
    return ", ".join(teile)


def signatur_zeilen(profil: dict, kopf: dict) -> list[str]:
    """Die Signatur als Liste von Zeilen, in der Reihenfolge aus #62.

    Grußformel · Name · Position · Firma · Anschrift · Telefon · E-Mail · Web ·
    Pflichtangaben · Datenschutz · Zusatz.

    Was fehlt, fällt weg — ohne Lücke. Eine leere Zeile mitten in einer
    Signatur sieht aus wie ein Fehler des Absenders, nicht wie ein fehlendes
    Profilfeld.
    """
    email_teil = profil.get("email") or {}
    absender = profil.get("absender") or {}
    pflicht = email_teil.get("pflichtangaben")
    vorgaben = profil.get("infoblock_defaults") or {}
    zeilen: list[str] = []

    name = email_teil.get("anzeigename") or kopf.get("unterzeichner") or profil.get("unterzeichner")
    if name:
        zeilen.append(str(name))
    if email_teil.get("position"):
        zeilen.append(str(email_teil["position"]))

    # Firma und Anschrift kommen aus genau einer Quelle. Steht `pflichtangaben:
    # fusszeile`, liefert die Fußzeile beides — sie ist die für den Fuß eines
    # Briefes kuratierte Fassung. Beide Quellen zu nehmen ergab am
    # Beispielprofil vier doppelte Zeilen, zwei davon so umgebrochen, dass ein
    # Vergleich auf Zeilenebene sie nicht fand.
    if pflicht != "fusszeile":
        if absender.get("name"):
            zeilen.append(str(absender["name"]))
        strasse = str(absender["strasse"]) if absender.get("strasse") else ""
        ort = " ".join(str(absender[f]) for f in ("plz", "ort") if absender.get(f))
        if strasse or ort:
            zeilen.append(" · ".join(t for t in (strasse, ort) if t))

    if vorgaben.get("telefon"):
        zeilen.append(f"Telefon {vorgaben['telefon']}")
    if email_teil.get("absender"):
        zeilen.append(str(email_teil["absender"]))
    for wert in (email_teil.get("web"), email_teil.get("datenschutz")):
        if wert:
            zeilen.append(str(wert))

    if pflicht == "fusszeile":
        # Spalte 1 trägt Firma und Anschrift, Spalte 4 die Registerangaben.
        # Was dort nicht steht, steht auch hier nicht — falzmarke ergänzt keine
        # Rechtsangaben (ADR 0005).
        spalten = profil.get("fusszeile") or []
        for nummer in (0, 3):
            if nummer < len(spalten):
                zeilen.extend(str(z) for z in spalten[nummer])
    elif pflicht:
        zeilen.extend(_als_liste(pflicht))

    zeilen.extend(_als_liste(email_teil.get("zusatz")))

    # Die Fußzeile eines Briefes trägt die Anschrift ein zweites Mal — auf
    # Papier steht sie in einer anderen Spalte, in einer Signatur stünde sie
    # zweimal untereinander. Gemessen am Beispielprofil: vier doppelte Zeilen.
    gesehen: set[str] = set()
    einmalig = []
    for zeile in zeilen:
        schluessel = " ".join(zeile.split()).casefold()
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        einmalig.append(zeile)
    return einmalig


def _mit_rahmen(kopf: dict, gruss, bloecke) -> list:
    """Anrede und Grußformel als Absätze in den Baum.

    Sie durch die Emitter zu schicken statt sie fertig davorzukleben, hält sie
    an derselben Kette: dieselbe Typografie, dieselbe Faltung, dieselbe
    Escape-Schicht. Eine lange Anrede wird damit umgebrochen wie jeder andere
    Satz — davorgeklebt bliebe sie eine überlange Zeile.
    """
    vorne = [baum.Absatz((baum.Text(str(kopf["anrede"])),))] if kopf.get("anrede") else []
    hinten = [baum.Absatz((baum.Text(str(gruss)),))] if gruss else []
    return vorne + list(bloecke) + hinten


def textteil(kopf: dict, profil: dict, bloecke, breite: int = emit_text.BREITE) -> str:
    """Anrede, Brieftext, Grußformel, Signatur — als `format=flowed`.

    Der Signaturtrenner `-- ` und die Signatur werden **nach** dem Falten
    angehängt: Ihre Zeilen sind fest, und der Trenner endet auf ein Leerzeichen,
    das ein Faltlauf für eine weiche Marke halten müsste.
    """
    email_teil = profil.get("email") or {}
    gruss = kopf.get("gruss") or email_teil.get("gruss") or profil.get("gruss")

    kern = emit_text.falte(_mit_rahmen(kopf, gruss, bloecke), breite=breite)

    teile = [kern]
    signatur = signatur_zeilen(profil, kopf)
    if signatur:
        teile.append(f"{SIGNATUR_TRENNER}\n" + "\n".join(signatur) + "\n")
    return "\n".join(teile)


def htmlteil(kopf: dict, profil: dict, bloecke, sprache: str = "de") -> str:
    """Dasselbe als HTML — derselbe Baum, andere Zielsprache."""
    email_teil = profil.get("email") or {}
    gruss = kopf.get("gruss") or email_teil.get("gruss") or profil.get("gruss")

    stuecke = [emit_html.setze(_mit_rahmen(kopf, gruss, bloecke)).rstrip("\n")]
    signatur = signatur_zeilen(profil, kopf)
    if signatur:
        # Eine Signatur ist kein Absatz, sondern eine Folge kurzer Zeilen.
        # `<br>` statt eigener Absätze, sonst reißt sie im Client auseinander.
        inhalt = emit_html.umbruch().join(emit_html.as_text(z) for z in signatur)
        stuecke.append(
            f'<p style="margin: 16px 0 0; border-top: 1px solid {emit_html.RAHMEN}; '
            f'padding-top: 8px; {emit_html.TEXTSTIL}">{inhalt}</p>'
        )
    return emit_html.dokument("\n".join(stuecke) + "\n", sprache=sprache)


def begleit_html(kopf: dict, profil: dict, bloecke, sprache: str = "de") -> str:
    """Die `.html` zum Öffnen im Browser — mit An und Betreff als Vorschau.

    Derselbe Rumpf wie in der Mail, davor ein Kopf. Er gehört **nicht** in den
    HTML-Teil der Nachricht: Dort stünden An und Betreff ein zweites Mal, unter
    denen, die der Mailclient ohnehin anzeigt.
    """
    zeilen = [("An", _adressliste(kopf.get("an"))),
              ("Kopie", _adressliste(kopf.get("cc"))),
              ("Betreff", str(kopf.get("betreff") or ""))]
    stil = f"margin: 0 0 2px; {emit_html.TEXTSTIL} font-size: 14px; color: #555;"
    kopfzeilen = "".join(
        f'<p style="{stil}"><strong>{emit_html.as_text(name)}:</strong> '
        f"{emit_html.as_text(wert)}</p>"
        for name, wert in zeilen if wert
    )
    seite = htmlteil(kopf, profil, bloecke, sprache=sprache)
    vorschau = (f'<div style="border-bottom: 1px solid {emit_html.RAHMEN}; '
                f'margin-bottom: 16px; padding-bottom: 10px;">{kopfzeilen}</div>')
    return seite.replace(f'<div style="max-width: {emit_html.BREITE_MAX};">',
                         f'<div style="max-width: {emit_html.BREITE_MAX};">{vorschau}', 1)


def _trennstring(quelle: str, zweck: str) -> str:
    """Der Trennstring der MIME-Teile, aus der Quelle abgeleitet.

    `EmailMessage` würfelt ihn sonst. Dann unterscheiden sich zwei Läufe über
    dieselbe Datei in jeder Zeile, an der ein Teil beginnt — und ein
    Golden-Vergleich ist unmöglich, obwohl sich inhaltlich nichts geändert hat.
    """
    kern = hashlib.sha256(f"{zweck}\0{quelle}".encode("utf-8")).hexdigest()[:24]
    return f"==falzmarke-{zweck}-{kern}=="


def _quellenhash(quelle: str) -> str:
    return hashlib.sha256(quelle.encode("utf-8")).hexdigest()


def baue(kopf: dict, profil: dict, quelle_md: str, bloecke, *,
         brief_pfad: Path | None = None, mit_quelle: bool = False) -> EmailMessage:
    """Die fertige Nachricht — ohne Message-ID, ohne Date, ohne Versandweg.

    `mit_quelle` hängt die Markdown-Quelle als eigenen Teil an (RFC 7763).
    Vorgabe ist aus: Der Teil vergrößert jede Mail und macht sichtbar, was im
    Brief nicht sichtbar wäre — Frontmatter, Kommentare, Reste früherer
    Fassungen (ADR 0034, Punkt 3).
    """
    email_teil = profil.get("email") or {}
    absender = email_teil.get("absender")
    if not absender:
        raise ValueError("Das Profil hat keinen `email.absender:` — ohne ihn gibt es kein From.")

    sprache = str(kopf.get("sprache") or profil.get("sprache") or "de")
    nachricht = EmailMessage()
    nachricht["From"] = _adressliste(
        f"{email_teil['anzeigename']} <{absender}>" if email_teil.get("anzeigename") else absender)
    nachricht["To"] = _adressliste(kopf.get("an"))
    if kopf.get("cc"):
        nachricht["Cc"] = _adressliste(kopf["cc"])
    nachricht["Subject"] = str(kopf.get("betreff") or "")
    if kopf.get("antwort_auf"):
        nachricht["In-Reply-To"] = str(kopf["antwort_auf"])
        nachricht["References"] = str(kopf["antwort_auf"])

    # Date nur, wenn die Umgebung einen festen Zeitpunkt vorgibt. Sonst setzt
    # ihn der Client beim Versand — ein Entwurf von gestern, der heute
    # rausgeht, wäre sonst auf gestern datiert.
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        nachricht["Date"] = formatdate(float(epoch), localtime=False)

    text = textteil(kopf, profil, bloecke)
    html = htmlteil(kopf, profil, bloecke, sprache=sprache)

    # quoted-printable, nie base64: Eine Mail, deren Textteil als base64
    # ankommt, ist in jedem Rohansicht-Fenster unlesbar — und die Rohansicht
    # ist das, was von einer .eml als Vorlage übrig bleibt.
    nachricht.set_content(text, subtype="plain", charset="utf-8", cte="quoted-printable",
                          params={"format": "flowed", "delsp": "yes"})
    if mit_quelle:
        nachricht.add_alternative(quelle_md, subtype="markdown", charset="utf-8",
                                  cte="quoted-printable", params={"variant": "CommonMark"})
    nachricht.add_alternative(html, subtype="html", charset="utf-8", cte="quoted-printable")

    anhaenge = _als_liste(kopf.get("anlagen_dateien"))
    if anhaenge:
        basis = Path(brief_pfad).parent if brief_pfad else Path.cwd()
        for name in anhaenge:
            _haenge_an(nachricht, basis / name)

    # Content-Language erst jetzt: `set_content` und `add_alternative` räumen
    # jede `Content-*`-Kopfzeile aus dem Umschlag — vorher gesetzt, ist sie am
    # Ende spurlos weg. Gemessen: weder im Umschlag noch in einem der Teile.
    nachricht["Content-Language"] = sprache

    _feste_trennstrings(nachricht, _quellenhash(quelle_md))
    return nachricht


def _haenge_an(nachricht: EmailMessage, pfad: Path) -> None:
    import mimetypes

    if not pfad.is_file():
        raise FileNotFoundError(f"Anlage nicht gefunden: {pfad}")
    typ, _ = mimetypes.guess_type(pfad.name)
    haupt, _, unter = (typ or "application/octet-stream").partition("/")
    nachricht.add_attachment(pfad.read_bytes(), maintype=haupt, subtype=unter,
                             filename=pfad.name)


def _feste_trennstrings(nachricht: EmailMessage, hash_: str) -> None:
    """Trennstrings aus dem Quellenhash statt gewürfelt — sonst kein Golden.

    Durchnummeriert nach Tiefe: Zwei geschachtelte Ebenen dürfen nicht
    denselben Trennstring tragen, sonst endet die äußere dort, wo die innere
    beginnt.
    """
    def _gehe(teil, tiefe: int) -> None:
        if teil.get_content_maintype() == "multipart":
            teil.set_boundary(f"==falzmarke-{tiefe}-{hash_[:24]}==")
            for unterteil in teil.iter_parts():
                _gehe(unterteil, tiefe + 1)

    _gehe(nachricht, 0)


def schreibe(nachricht: EmailMessage, ziel: Path, *, html: str, text: str) -> list[Path]:
    """`.eml` und die beiden Begleitdateien, atomar.

    Atomar heißt hier: erst vollständig in eine Nachbardatei schreiben, dann
    an ihren Platz umbenennen. Ein abgebrochener Lauf hinterlässt damit die
    alte Fassung, keine halbe — `os.replace` ist auf einem Dateisystem
    unteilbar. (Der PDF-Pfad tut das noch nicht; Typst schreibt direkt ans
    Ziel.)
    """
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    geschrieben = []
    for pfad, inhalt in (
        (ziel.with_suffix(".eml"), nachricht.as_bytes(policy=nachricht.policy)),
        (ziel.with_suffix(".html"), html.encode("utf-8")),
        (ziel.with_suffix(".txt"), text.encode("utf-8")),
    ):
        with tempfile.NamedTemporaryFile(dir=pfad.parent, delete=False,
                                         prefix=f".{pfad.name}.", suffix=".teil") as roh:
            roh.write(inhalt)
            vorlaeufig = Path(roh.name)
        os.replace(vorlaeufig, pfad)
        geschrieben.append(pfad)
    return geschrieben
