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


def signatur_bloecke(profil: dict, kopf: dict) -> list[list[str]]:
    """Die Signatur in drei Blöcken (#105).

    | Block | Inhalt |
    |---|---|
    | Person | Anzeigename, Position |
    | Kontakt | Telefon, Mobil, E-Mail, Web |
    | Recht | Firma, Anschrift, Pflichtangaben, Datenschutz, Zusatz |

    Bis hierher war alles ein Block — dreizehn Zeilen am Stück, in denen der
    Name so aussieht wie die Umsatzsteuer-Identifikationsnummer. Drei Blöcke
    trennen, was verschieden ist: wer schreibt, wie man ihn erreicht, was das
    Gesetz verlangt.

    Die Reihenfolge INNERHALB der Blöcke bleibt fest und ist nicht einstellbar:
    Eine Signatur, deren Reihenfolge jeder selbst wählt, ist keine Signatur
    mehr, sondern ein Textfeld — und die Pflichtangaben rutschen dann
    irgendwohin.

    Was fehlt, fällt weg — ohne Lücke. Ein leerer Block erscheint nicht; eine
    Leerzeile mitten in einer Signatur sieht aus wie ein Fehler des Absenders,
    nicht wie ein fehlendes Profilfeld.
    """
    email_teil = profil.get("email") or {}
    absender = profil.get("absender") or {}
    pflicht = email_teil.get("pflichtangaben")
    vorgaben = profil.get("infoblock_defaults") or {}

    # ── Person ──────────────────────────────────────────────────────────────
    person: list[str] = []
    name = email_teil.get("anzeigename") or kopf.get("unterzeichner") or profil.get("unterzeichner")
    if name:
        person.append(str(name))
    if email_teil.get("position"):
        person.append(str(email_teil["position"]))

    # ── Kontakt ─────────────────────────────────────────────────────────────
    #
    # `telefon` und `mobil` stehen im Abschnitt `email:`; fehlt `telefon`, gilt
    # der Wert aus dem Informationsblock. Kein Feld wurde umbenannt — wer nur
    # den Informationsblock pflegt, bekommt dieselbe Signatur wie bisher.
    kontakt: list[str] = []
    telefon = email_teil.get("telefon") or vorgaben.get("telefon")
    if telefon:
        kontakt.append(f"Telefon {telefon}")
    if email_teil.get("mobil"):
        kontakt.append(f"Mobil {email_teil['mobil']}")
    if email_teil.get("absender"):
        kontakt.append(str(email_teil["absender"]))
    if email_teil.get("web"):
        kontakt.append(str(email_teil["web"]))

    # ── Recht ───────────────────────────────────────────────────────────────
    #
    # Firma und Anschrift kommen aus genau einer Quelle. Steht `pflichtangaben:
    # fusszeile`, liefert die Fußzeile beides — sie ist die für den Fuß eines
    # Briefes kuratierte Fassung. Beide Quellen zu nehmen ergab am
    # Beispielprofil vier doppelte Zeilen, zwei davon so umgebrochen, dass ein
    # Vergleich auf Zeilenebene sie nicht fand.
    recht: list[str] = []
    if pflicht != "fusszeile":
        if absender.get("name"):
            recht.append(str(absender["name"]))
        strasse = str(absender["strasse"]) if absender.get("strasse") else ""
        ort = " ".join(str(absender[f]) for f in ("plz", "ort") if absender.get(f))
        if strasse or ort:
            recht.append(" · ".join(t for t in (strasse, ort) if t))

    if pflicht == "fusszeile":
        # Spalte 1 trägt Firma und Anschrift, Spalte 4 die Registerangaben.
        # Was dort nicht steht, steht auch hier nicht — falzmarke ergänzt keine
        # Rechtsangaben (ADR 0005).
        spalten = profil.get("fusszeile") or []
        for nummer in (0, 3):
            if nummer < len(spalten):
                recht.extend(str(z) for z in spalten[nummer])
    elif pflicht:
        recht.extend(_als_liste(pflicht))

    # Der Datenschutzhinweis stand bis #105 zwischen Web und Firma, also im
    # Kontaktteil. Er ist eine Rechtsangabe und steht jetzt bei den anderen.
    if email_teil.get("datenschutz"):
        recht.append(str(email_teil["datenschutz"]))
    recht.extend(_als_liste(email_teil.get("zusatz")))

    # Über ALLE Blöcke, nicht je Block.
    #
    # Der historische Anlass — die Fußzeile trägt die Anschrift ein zweites Mal,
    # vier doppelte Zeilen am Beispielprofil — ist heute schon durch die Weiche
    # oben erledigt: `pflichtangaben: fusszeile` holt Firma und Anschrift aus
    # genau einer Quelle. Am mitgelieferten Profil läuft diese Schleife deshalb
    # leer, und ein Test, der nur dort misst, belegt nichts.
    #
    # Sie bleibt für den Fall, den die Weiche nicht abdeckt: dieselbe Zeile in
    # ZWEI Blöcken. Wer seine Website in den Pflichtangaben wiederholt, hat sie
    # im Kontakt- und im Rechtsteil; block-lokal entdoppelt stünde sie zweimal
    # da. `tests/test_signatur.py` prüft genau diesen Fall — mit Gegenprobe.
    gesehen: set[str] = set()
    bloecke: list[list[str]] = []
    for block in (person, kontakt, recht):
        einmalig = []
        for zeile in block:
            schluessel = " ".join(zeile.split()).casefold()
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            einmalig.append(zeile)
        if einmalig:
            bloecke.append(einmalig)
    return bloecke


def signatur_zeilen(profil: dict, kopf: dict) -> list[str]:
    """Dieselbe Signatur, flach — für alles, was keine Blöcke braucht.

    Bleibt, weil die Frage „steht diese Zeile in der Signatur?" häufiger ist
    als die nach ihrer Gliederung.
    """
    return [zeile for block in signatur_bloecke(profil, kopf) for zeile in block]


#: Die Kennung, unter der das Logo in der Nachricht steckt. Fest, weil sie an
#: zwei Stellen gebraucht wird: im `<img src="cid:…">` und am Anhang selbst.
LOGO_CID = "falzmarke-logo"

#: Rasterformate. SVG steht bewusst nicht dabei: Outlook stellt es in Mails
#: nicht dar, und ein Logo, das bei einem der drei großen Programme fehlt, ist
#: schlimmer als keines — dann fehlt es überall gleich.
#:
#: Der Preis dafür steht in Issue #154: Ein Rasterbild schaltet seine Farbe im
#: dunklen Schema nicht um. Wer ein Logo einschaltet, waehlt eines, das auf
#: beiden Gruenden traegt — das Werkzeug prueft es nicht.
LOGO_FORMATE = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif"}


def logo_datei(profil: dict, profil_pfad: Path | None) -> Path | None:
    """Die Bilddatei für die Signatur — oder None.

    `email.logo` kennt drei Werte, und die Doku versprach sie, lange bevor es
    sie gab: `false` (Vorgabe), `true` — dann gilt das Logo des Briefkopfs —
    oder ein eigener Pfad.

    Der Pfad wird nicht selbst zusammengesetzt: `cli.datei_aus_dem_profilordner`
    hält die Grenze, dass eine Profildatei neben ihrem Profil liegt.
    """
    email_teil = profil.get("email") or {}
    wert = email_teil.get("logo")
    if not wert or profil_pfad is None:
        return None
    if wert is True:
        wert = ((profil.get("briefkopf") or {}).get("logo"))
        if not wert:
            return None
    from falzmarke import cli

    pfad = cli.datei_aus_dem_profilordner(Path(profil_pfad), str(wert), "email.logo")
    if pfad.suffix.lower() not in LOGO_FORMATE:
        raise ValueError(
            f"`email.logo` zeigt auf {pfad.name} — für eine Mail wird ein Rasterbild "
            f"gebraucht ({', '.join(sorted(LOGO_FORMATE))}). Outlook stellt SVG nicht dar.")
    return pfad


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
    bloecke = signatur_bloecke(profil, kopf)
    if bloecke:
        # Eine Leerzeile zwischen den Blöcken — im Klartext ist das die einzige
        # Gliederung, die es gibt, und sie überlebt jedes Mailprogramm.
        gesetzt = "\n\n".join("\n".join(block) for block in bloecke)
        teile.append(f"{SIGNATUR_TRENNER}\n" + gesetzt + "\n")
    return "\n".join(teile)


def logo_masse(pfad: Path, hoehe: int = 40) -> tuple[int, int]:
    """Breite und Höhe des Logos in der Mail, auf `hoehe` skaliert.

    Beide Werte gehören als Attribut an das Bild (Issue #104): Ohne sie
    reserviert kein Client Platz. Die Nachricht springt beim Laden, und wo
    Bilder blockiert sind — der Normalfall in Outlook — steht der
    Alternativtext in einem Kasten von null Pixeln.

    Gerechnet statt geraten: Die Breite folgt aus dem Seitenverhältnis der
    Datei. Ein fester Wert wäre bei jedem anderen Logo verzerrt.
    """
    from PIL import Image

    with Image.open(pfad) as bild:
        breite, hoch = bild.size
    return max(1, round(breite * hoehe / hoch)), hoehe


def htmlteil(kopf: dict, profil: dict, bloecke, sprache: str = "de",
             mit_logo: bool = False, logo_pfad: Path | None = None,
             vorspann: str = "") -> str:
    """Dasselbe als HTML — derselbe Baum, andere Zielsprache."""
    email_teil = profil.get("email") or {}
    gruss = kopf.get("gruss") or email_teil.get("gruss") or profil.get("gruss")

    stuecke = [emit_html.setze(_mit_rahmen(kopf, gruss, bloecke)).rstrip("\n")]
    for nummer, block in enumerate(signatur_bloecke(profil, kopf)):
        # Innerhalb eines Blocks `<br>` statt eigener Absätze: Eine Signatur ist
        # kein Fließtext, sondern eine Folge kurzer Zeilen — mit Absätzen risse
        # sie im Client auseinander. ZWISCHEN den Blöcken ist der Absatz genau
        # richtig, denn dort soll Luft sein.
        inhalt = emit_html.umbruch().join(emit_html.as_text(z) for z in block)
        # Die Trennlinie gehört an den ersten Block: Sie trennt die Signatur von
        # der Nachricht, nicht die Blöcke voneinander.
        rahmen = (f"border-top: 1px solid {emit_html.RAHMEN}; padding-top: 8px; "
                  if nummer == 0 else "")
        oben = "16px" if nummer == 0 else "10px"
        # Der Rechtsblock steht kleiner und leiser: Pflichtangaben und
        # Vertraulichkeitshinweis sind Beiwerk, nicht die Botschaft.
        leise = nummer == 2
        stil = (f"margin: {oben} 0 0; {rahmen}{emit_html.TEXTSTIL}"
                + (" font-size: 13px; color: #666;" if leise else ""))
        klassen = [emit_html.KLASSE_LEISE if leise else emit_html.KLASSE_TEXT]
        if nummer == 0:
            klassen.append(emit_html.KLASSE_LINIE)
        if nummer == 0 and mit_logo:
            # Das Logo steht IM ersten Block, nicht darüber: Sonst hinge es
            # zwischen Grußformel und Trennlinie und sähe aus wie Teil der
            # Nachricht. Als Tabelle, weil Outlook mit der Word-Engine rechnet
            # und moderne Layoutverfahren ignoriert (#104).
            name = emit_html.as_text(str((profil.get("absender") or {}).get("name") or ""))
            breite, hoehe = logo_masse(logo_pfad) if logo_pfad else (0, 40)
            # `role="presentation"`: Das ist Layout, keine Daten. Ohne die
            # Marke liest ein Screenreader „Tabelle, zwei Spalten, Zelle eins"
            # vor, bevor der Name kommt — und `verify --email` lehnt sie ab.
            # Gemessen am 29.08.2026: Jede Mail mit Logo im Profil fiel dort
            # durch („Tabellen sind Datentabellen: 1 ohne <th>"), und niemandem
            # war es aufgefallen, weil das Beispielprofil kein Logo trägt.
            masse = f'width="{breite}" height="{hoehe}" ' if breite else f'height="{hoehe}" '
            inhalt = (
                f'<table role="presentation" class="{emit_html.KLASSE_TEXT}" '
                f'cellpadding="0" cellspacing="0" border="0" '
                f'style="border-collapse: collapse;"><tr>'
                f'<td style="padding: 0 12px 0 0; vertical-align: top;">'
                f'<img src="cid:{LOGO_CID}" alt="{name}" {masse}'
                f'style="display: block; border: 0; height: {hoehe}px; '
                f'width: {"auto" if not breite else f"{breite}px"};"></td>'
                f'<td class="{emit_html.KLASSE_TEXT}" style="vertical-align: top; '
                f'{emit_html.TEXTSTIL}">{inhalt}</td></tr></table>'
            )
        stuecke.append(
            f'<p class="{" ".join(klassen)}" style="{stil}">{inhalt}</p>'
        )
    return emit_html.dokument("\n".join(stuecke) + "\n", sprache=sprache, vorspann=vorspann)


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
        f'<p class="{emit_html.KLASSE_LEISE}" style="{stil}">'
        f"<strong>{emit_html.as_text(name)}:</strong> {emit_html.as_text(wert)}</p>"
        for name, wert in zeilen if wert
    )
    vorschau = (f'<div class="{emit_html.KLASSE_LINIE}" '
                f'style="border-bottom: 1px solid {emit_html.RAHMEN}; '
                f'margin-bottom: 16px; padding-bottom: 10px;">{kopfzeilen}</div>')
    return htmlteil(kopf, profil, bloecke, sprache=sprache, vorspann=vorschau)


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
         brief_pfad: Path | None = None, mit_quelle: bool = False,
         profil_pfad: Path | None = None) -> EmailMessage:
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

    logo = logo_datei(profil, profil_pfad)
    text = textteil(kopf, profil, bloecke)
    html = htmlteil(kopf, profil, bloecke, sprache=sprache,
                    mit_logo=logo is not None, logo_pfad=logo)

    # quoted-printable, nie base64: Eine Mail, deren Textteil als base64
    # ankommt, ist in jedem Rohansicht-Fenster unlesbar — und die Rohansicht
    # ist das, was von einer .eml als Vorlage übrig bleibt.
    nachricht.set_content(text, subtype="plain", charset="utf-8", cte="quoted-printable",
                          params={"format": "flowed", "delsp": "yes"})
    if mit_quelle:
        nachricht.add_alternative(quelle_md, subtype="markdown", charset="utf-8",
                                  cte="quoted-printable", params={"variant": "CommonMark"})
    nachricht.add_alternative(html, subtype="html", charset="utf-8", cte="quoted-printable")

    if logo is not None:
        # `add_related` auf den HTML-Teil, nicht auf die Nachricht: Das Bild
        # gehört zu dieser einen Darstellung. Als Anhang der Nachricht stünde es
        # in jedem Client in der Anlagenliste — neben der Rechnung, die jemand
        # wirklich verschickt hat.
        #
        # Es reist MIT. Eine Signatur, die ihr Logo über eine Adresse nachlädt,
        # erscheint ohne Netz gar nicht, wartet auf „Bilder anzeigen" — und
        # meldet dem Absender, wann und wo geöffnet wurde. Eine Adresse, die bei
        # jedem Öffnen abgerufen wird, ist ein Zählpixel, ob so gemeint oder nicht.
        html_teil = nachricht.get_payload()[-1]
        html_teil.add_related(logo.read_bytes(), maintype="image",
                              subtype=LOGO_FORMATE[logo.suffix.lower()],
                              cid=f"<{LOGO_CID}>")

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
