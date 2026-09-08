#!/usr/bin/env python3
"""Baut die E-Mail-Fassung: `.eml` und die Begleitdateien.

**Sie erzeugt eine Datei und versendet nichts** — ADR 0034. Es gibt hier keinen
Versandweg, keine Verbindung nach außen und keine Kopfzeile, die eine Mail zu
einer bereits verschickten machen würde.

Genau darum fehlt **`Message-ID`**: Eine `.eml` mit eigener Message-ID ist keine
Vorlage mehr, sondern eine Mail, die es nie gab. Zwei Läufe ergäben zwei
Nachrichten, die denselben Text tragen und sich als verschieden ausgeben. Die
Kennung gehört dem Versender.

**`Date` steht dagegen drin** — seit #236. Bis dahin fehlte es, mit der
Begründung, das Datum entstehe beim Versand. Die trug nur, solange man annahm,
das Mailprogramm übernehme die Datei als Entwurf und setze den Zeitpunkt selbst.
Nach der Messung in `docs/mailprogramme-2026-08-27.md` tut das keines der drei
geprüften Programme: Sie zeigen ein Lesefenster, und der gangbare Weg ist
„Weiterleiten". Dabei baut das Programm den zitierten Kopf aus den Feldern der
Quelle — ein fehlendes Feld wird dort nicht ersetzt, sondern als
`Datum: (null), (null)` angezeigt und mitverschickt. Dazu führt RFC 5322,
Abschnitt 3.6, `orig-date` als Pflichtfeld: Ohne `Date` ist die Datei keine
vollständige Nachricht.

`SOURCE_DATE_EPOCH` behält den Vorrang und ist der Weg zu einem
Golden-Vergleich: Mit der Variablen ist die Zeit festgenagelt, und sonst ist
nichts am Ergebnis veränderlich — die Trennstrings der Teile werden aus einem
Hash der Quelle gebildet, nicht gewürfelt. Zwei Läufe über dieselbe Datei
ergeben damit dieselben Bytes. **Ohne** die Variable gilt diese Zusage nicht
mehr, denn dann trägt jeder Lauf seinen eigenen Zeitpunkt.

Die Standardbibliothek reicht: `email.message.EmailMessage`. Keine neue
Abhängigkeit für etwas, das seit Python 3.6 im Kern liegt.
"""

from __future__ import annotations

import base64
import hashlib
import os
import tempfile
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, parseaddr
from pathlib import Path
from typing import NamedTuple

from falzmarke import baum, emit_html, emit_text

#: Reihenfolge der Signatur. Fest, nicht konfigurierbar: Eine Signatur, deren
#: Reihenfolge jeder selbst wählt, ist keine Signatur mehr, sondern ein
#: Textfeld — und die Pflichtangaben rutschen dann irgendwohin.
SIGNATUR_TRENNER = "-- "


def _als_liste(wert) -> list[str]:
    if wert is None:
        return []
    return [wert] if isinstance(wert, str) else [str(z) for z in wert]


def blindkopien(kopf: dict, profil: dict) -> list[str]:
    """Die Blindkopien einer Nachricht: aus dem Frontmatter UND aus dem Profil.

    Das Profilfeld `email.bcc` ist für den, der jede ausgehende Nachricht in
    einem Archiv haben will (#272). Es tritt **neben** ein `bcc:` im
    Frontmatter, nicht an dessen Stelle — die fachliche Blindkopie einer
    einzelnen Mail und die staendige ins Archiv haben nichts miteinander zu
    tun, und die eine duerfte die andere nie verdraengen.

    Doppelte Adressen fallen weg, verglichen ueber die Adresse selbst: „Archiv
    <a@example.de>" und „a@example.de" sind dieselbe Empfaengerin, und zweimal
    gesetzt stuende sie sichtbar doppelt im Kopf. Die zuerst genannte
    Schreibweise bleibt — das Frontmatter gewinnt vor dem Profil, weil es den
    Anzeigenamen fuer diesen einen Fall traegt.

    Der Hinweis auf eine gesetzte Blindkopie braucht hier nichts: Er wird aus
    der FERTIGEN DATEI gelesen, also erscheint er fuer eine Adresse aus dem
    Profil genauso wie fuer eine aus dem Frontmatter. Eine stille Kopie an
    einen Dritten waere genau das, was er verhindern soll.
    """
    gesehen: set[str] = set()
    zusammen = []
    for eintrag in [*_als_liste(kopf.get("bcc")),
                    *_als_liste((profil.get("email") or {}).get("bcc"))]:
        _, adresse = parseaddr(eintrag)
        schluessel = (adresse or eintrag).lower()
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        zusammen.append(eintrag)
    return zusammen


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

#: Die Höhe des Logos in der Signatur, in Bildpunkten.
#:
#: Stand als Vorgabewert an `logo_masse()` und wurde daneben an drei Stellen
#: getippt. Bei einer Adresse als Quelle gibt es keine Datei zum Ausmessen —
#: dann ist dieser Wert das Einzige, was das Bild über seine Maße sagen kann,
#: und eine zweite Fassung davon wäre ein stiller Sprung im Layout.
LOGO_HOEHE = 40


#: Wie das Logo in die Nachricht kommt. Die Reihenfolge ist die Rangfolge:
#: `datei` reist als eigener Teil mit und kommt immer an; die beiden anderen
#: haben je einen Preis, den `logo_hinweis()` benennt.
LOGO_ARTEN = ("datei", "url", "daten")

#: Was am Anfang von `email.logo` steht, wenn es keine Datei ist.
LOGO_PRAEFIXE = {"http://": "url", "https://": "url", "data:": "daten"}


class Logo(NamedTuple):
    """Das Signaturlogo, aufgelöst — aber noch nicht vermessen.

    Art, Quelle und Pfad gehören zusammen: Wer die Quelle kennt, aber nicht die
    Art, weiß nicht, ob ein Anhang dazugehört.

    Die **Maße stehen bewusst nicht darin.** Sie zu holen heißt, das Bild zu
    öffnen, und das kann scheitern — ein unlesbares PNG, eine kaputte Data-URI.
    Stünden sie hier, führe jeder Aufrufer dieses Risiko mit, auch der Linter,
    der nur wissen will, welche Form gewählt wurde. Genau das ist beim ersten
    Anlauf passiert: `lint.pruefe_email_logo` fiel an einem unlesbaren Bild mit
    einem Traceback statt mit seiner Warnung. Wer die Maße braucht, ruft
    `logo_masse_fuer()` und fängt dort, was dort auftreten kann.
    """
    art: str
    #: Was ins `src`-Attribut kommt: `cid:…`, die Adresse oder die Data-URI.
    quelle: str
    #: Nur bei `datei` gesetzt. `baue()` hängt sie als `related`-Teil an.
    pfad: Path | None


def _logo_art(wert: str) -> str:
    for praefix, art in LOGO_PRAEFIXE.items():
        if wert.lower().startswith(praefix):
            return art
    return "datei"


def _format_aus_datenuri(wert: str) -> str:
    """Der Bildtyp einer Data-URI — oder ein Fehler mit Grund.

    Geprüft wird gegen dieselbe Liste wie bei einer Datei. Ein SVG als Data-URI
    ist genauso tot wie eines als Datei: Outlook stellt es nicht dar.
    """
    kopf = wert[len("data:"):].split(",", 1)[0]
    typ = kopf.split(";", 1)[0].strip().lower()
    if not typ.startswith("image/") or typ[len("image/"):] not in set(LOGO_FORMATE.values()):
        raise ValueError(
            f"`email.logo` bringt eine Data-URI vom Typ `{typ or 'ohne Angabe'}` mit — "
            f"für eine Mail wird ein Rasterbild gebraucht "
            f"({', '.join(sorted(set(LOGO_FORMATE.values())))}). Outlook stellt SVG nicht dar.")
    if ";base64," not in wert:
        raise ValueError(
            "`email.logo` als Data-URI muss base64-kodiert sein (`data:image/png;base64,…`). "
            "Die prozentkodierte Form überlebt den Weg durch quoted-printable nicht "
            "zuverlässig.")
    return typ[len("image/"):]


def logo_datei(profil: dict, profil_pfad: Path | None) -> Path | None:
    """Die Bilddatei für die Signatur — oder None.

    Bleibt der Weg für die Dateiform und damit die Vorgabe. Wer wissen will,
    **wie** das Logo in die Nachricht kommt, fragt `logo_quelle()`: Seit #243
    nimmt `email.logo` auch eine Adresse und eine Data-URI, und für die gibt es
    keine Datei.

    Der Pfad wird nicht selbst zusammengesetzt: `cli.datei_aus_dem_profilordner`
    hält die Grenze, dass eine Profildatei neben ihrem Profil liegt.
    """
    wert = _logo_wert(profil)
    if wert is None or profil_pfad is None or _logo_art(wert) != "datei":
        return None
    from falzmarke import cli

    pfad = cli.datei_aus_dem_profilordner(Path(profil_pfad), wert, "email.logo")
    if pfad.suffix.lower() not in LOGO_FORMATE:
        raise ValueError(
            f"`email.logo` zeigt auf {pfad.name} — für eine Mail wird ein Rasterbild "
            f"gebraucht ({', '.join(sorted(LOGO_FORMATE))}). Outlook stellt SVG nicht dar.")
    return pfad


def _logo_wert(profil: dict) -> str | None:
    """Der rohe Wert von `email.logo`, mit `true` schon aufgelöst.

    `email.logo` kennt: `false` (Vorgabe), `true` — dann gilt das Logo des
    Briefkopfs — einen Pfad, eine Adresse oder eine Data-URI.
    """
    email_teil = profil.get("email") or {}
    wert = email_teil.get("logo")
    if not wert:
        return None
    if wert is True:
        wert = (profil.get("briefkopf") or {}).get("logo")
        if not wert:
            return None
    return str(wert)


def logo_quelle(profil: dict, profil_pfad: Path | None) -> Logo | None:
    """Wie das Logo in die Nachricht kommt — Art, Quelle, Maße.

    Drei Formen, seit #243 (davor nur die erste):

    | Form | Wofür | Beim Empfänger |
    |---|---|---|
    | Dateipfad | `falzmarke email` | als eigener Teil mit `cid:` — kommt immer an |
    | `https://…` | Umgebungen ohne Anhang | blockiert, bis Bilder freigegeben sind |
    | `data:image/…` | Web-Baukasten ohne MIME-Container | kommt mit, vergrößert jede Mail |

    Die beiden neuen Formen haben je einen gemessenen Preis, und der wird
    **benannt** statt stillschweigend in Kauf genommen: `logo_hinweis()` liefert
    den Satz, den Kommandozeile und Dienst ausgeben.

    Warum sie überhaupt zulässig sind: Der Signatur-Baukasten auf falzmarke.com
    hat keinen MIME-Container und konnte das Logo deshalb gar nicht zeigen. Ein
    eigenes Design im Browser hätte den byte-genauen Port-Test entwertet — die
    Lücke gehört also hierher (#243, Punkt 2).
    """
    wert = _logo_wert(profil)
    if wert is None:
        return None
    art = _logo_art(wert)
    if art == "datei":
        pfad = logo_datei(profil, profil_pfad)
        if pfad is None or not pfad.is_file():
            return None
        return Logo("datei", f"cid:{LOGO_CID}", pfad)
    if art == "daten":
        _format_aus_datenuri(wert)
        return Logo("daten", wert, None)
    _format_aus_adresse(wert)
    return Logo("url", wert, None)


def logo_masse_fuer(logo: Logo) -> tuple[int, int]:
    """Breite und Höhe des Logos in der Nachricht.

    Eine Adresse lässt sich nicht ausmessen, ohne sie abzurufen — und genau das
    tut dieses Werkzeug nicht (ADR 0034). Dann bleibt die Breite offen:
    `_signaturtabelle()` setzt nur die Höhe und `width: auto`. Was das kostet,
    steht in `logo_hinweis()` — der Client kann die Breite nicht vorab
    freihalten, die Nachricht rückt beim Laden nach.
    """
    if logo.art == "datei" and logo.pfad is not None:
        return logo_masse(logo.pfad)
    if logo.art == "daten":
        return _masse_aus_datenuri(logo.quelle)
    return 0, LOGO_HOEHE


def _format_aus_adresse(wert: str) -> None:
    """Dieselbe Formatprüfung an der Adresse — soweit sie eine Endung nennt.

    Eine Adresse ohne Dateiendung (`…/logo?id=7`) geht durch: Was dort liegt,
    weiß nur der Server, und danach zu fragen hieße, sie abzurufen. Die Prüfung
    greift, wo sie greifen kann, und behauptet nicht mehr.
    """
    pfadteil = wert.split("?", 1)[0].split("#", 1)[0]
    endung = Path(pfadteil).suffix.lower()
    if endung and endung not in LOGO_FORMATE:
        raise ValueError(
            f"`email.logo` zeigt auf `{endung}` — für eine Mail wird ein Rasterbild "
            f"gebraucht ({', '.join(sorted(LOGO_FORMATE))}). Outlook stellt SVG nicht dar.")


def _masse_aus_datenuri(wert: str) -> tuple[int, int]:
    """Breite und Höhe einer Data-URI, aus den Bytes selbst.

    Gerechnet, nicht geraten — wie bei der Datei. Ohne Maße reserviert kein
    Client Platz, und `emit_html.verstoesse()` meldet ein Bild ohne sie.
    """
    from io import BytesIO

    from PIL import Image

    roh = base64.b64decode(wert.split(";base64,", 1)[1], validate=False)
    with Image.open(BytesIO(roh)) as bild:
        breite, hoch = bild.size
    return max(1, round(breite * LOGO_HOEHE / hoch)), LOGO_HOEHE


def logo_hinweis(logo: Logo) -> str | None:
    """Was zu einer Logo-Form zu sagen ist — an genau einer Stelle.

    Beide Aufrufwege brauchen denselben Satz: die Kommandozeile im Terminal,
    der MCP-Dienst als Feld seiner Antwort. Stünde er zweimal im Code,
    driftete er auseinander — genau das ist bei der `Date`-Begründung passiert,
    die nach #236 an sechs Stellen stand und an fünfen falsch war.

    Zur Dateiform gibt es nichts zu sagen: Sie ist die Vorgabe, sie kommt an,
    und ein Hinweis bei jedem Lauf wäre Lärm, der die beiden echten übertönt.
    """
    if logo.art == "url":
        return (f"Das Logo wird von {logo.quelle} nachgeladen. Outlook und Gmail blockieren "
                "externe Bilder standardmäßig — bei einem Teil der Empfänger bleibt an "
                "seiner Stelle ein leerer Kasten, bis sie Bilder freigeben. Die Breite steht "
                "nicht im Bild, der Client kann sie also nicht vorab freihalten.")
    if logo.art == "daten":
        return ("Das Logo steckt als Data-URI im HTML-Teil. Es reist mit, vergrößert aber "
                "jede Nachricht; Gmail zeigt solche Bilder in der Weiterleitungsansicht "
                "nicht an, und Outlook hängt sie als namenlosen Anhang an. Für den Versand "
                "aus einem Mailprogramm ist der Dateipfad der bessere Weg — er wird zum "
                "Anhang mit Namen und Typ.")
    return None


def logo_hinweis_aus_datei(eml_pfad: Path) -> str | None:
    """Derselbe Hinweis, aber aus der fertigen Nachricht gelesen.

    Dieselbe Regel wie beim Blindverteiler: Gemeldet wird, **was drinsteht**,
    nicht was gemeint war. Wer stattdessen das Profil befragte, meldete eine
    Absicht — und übersähe genau den Fall, in dem zwischen Absicht und Ergebnis
    etwas dazwischenkam.
    """
    import email as email_modul
    import email.policy
    import re

    nachricht = email_modul.message_from_bytes(
        Path(eml_pfad).read_bytes(), policy=email.policy.default)
    for teil in nachricht.walk():
        if teil.get_content_type() != "text/html":
            continue
        treffer = re.search(r'<img\b[^>]*\bsrc="([^"]*)"', teil.get_content(), re.IGNORECASE)
        if not treffer:
            return None
        quelle = treffer.group(1)
        art = _logo_art(quelle) if not quelle.startswith("cid:") else "datei"
        return logo_hinweis(Logo(art, quelle, None))
    return None


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


def logo_masse(pfad: Path, hoehe: int = 0) -> tuple[int, int]:
    """Breite und Höhe des Logos in der Mail, auf `hoehe` skaliert.

    Beide Werte gehören als Attribut an das Bild (Issue #104): Ohne sie
    reserviert kein Client Platz. Die Nachricht springt beim Laden, und wo
    Bilder blockiert sind — der Normalfall in Outlook — steht der
    Alternativtext in einem Kasten von null Pixeln.

    Gerechnet statt geraten: Die Breite folgt aus dem Seitenverhältnis der
    Datei. Ein fester Wert wäre bei jedem anderen Logo verzerrt.
    """
    from PIL import Image

    hoehe = hoehe or LOGO_HOEHE
    with Image.open(pfad) as bild:
        breite, hoch = bild.size
    return max(1, round(breite * hoehe / hoch)), hoehe


#: Der Abstand zwischen Nachricht und Signatur, und der zwischen den Blöcken.
#: Als Konstanten, weil sie an zwei Stellen gebraucht werden — im Absatz ohne
#: Logo und in der Tabelle mit einem. Zwei getippte Werte driften auseinander.
SIGNATUR_ABSTAND = "16px"
SIGNATUR_LUFT = "8px"

#: Der Abstand zwischen Logospalte und Angaben, links und rechts der Linie.
LOGO_SPALTENABSTAND = "14px"


def _signaturtabelle(profil: dict, logo: Logo, inhalt: str) -> str:
    """Die Signatur mit Logo: zwei Spalten, dünne Linie dazwischen (#243).

    Bis hierher steckte nur der erste Block in dieser Tabelle; Kontakt und
    Rechtsangaben standen darunter und liefen unter dem Logo hindurch. Das sah
    aus wie ein Zitatblock mit einem Bild davor, nicht wie eine Signatur.
    Jetzt trägt die rechte Spalte alle drei Blöcke.

    Tabelle und nicht Rasterlayout, weil das klassische Outlook mit der
    Word-Engine setzt und moderne Layoutverfahren ignoriert (#104). Die
    Trennlinie ist **neutral** und kommt nicht aus dem Profil: Eine gefärbte
    Linie wäre unsere Marke in fremder Post, und eine profilabhängige Farbe
    könnte nicht in `DUNKELREGELN` stehen — der Block ist eine Konstante, die
    `emit_html.verstoesse()` Zeichen für Zeichen vergleicht.

    `role="presentation"`: Das ist Layout, keine Daten. Ohne die Marke liest
    ein Screenreader „Tabelle, zwei Spalten, Zelle eins" vor, bevor der Name
    kommt — und `verify --email` lehnt sie ab. Gemessen am 29.08.2026: Jede
    Mail mit Logo im Profil fiel dort durch, und niemandem war es aufgefallen,
    weil das Beispielprofil kein Logo trägt.
    """
    name = emit_html.as_text(str((profil.get("absender") or {}).get("name") or ""))
    breite, hoehe = logo_masse_fuer(logo)
    # Beide Maße gehören als Attribut an das Bild (#104): Ohne sie reserviert
    # kein Client Platz. Die Nachricht springt beim Laden, und wo Bilder
    # blockiert sind — der Normalfall in Outlook — steht der Alternativtext in
    # einem Kasten von null Pixeln.
    #
    # Bei einer Adresse als Quelle fehlt die Breite: Sie stünde nur im Bild,
    # und dafür müsste das Werkzeug die Adresse abrufen — das tut es nicht.
    # Die Höhe bleibt, damit wenigstens eine Angabe dasteht; was fehlt, sagt
    # `logo_hinweis()`.
    masse = f'width="{breite}" height="{hoehe}" ' if breite else f'height="{hoehe}" '
    linie = f"1px solid {emit_html.RAHMEN}"
    # Die waagerechte Linie hängt an der Tabelle statt am ersten Absatz: Sie
    # trennt die Signatur von der Nachricht, und die Signatur ist jetzt die
    # Tabelle. Am Absatz gezeichnet liefe sie nur über die rechte Spalte.
    return (
        f'<table role="presentation" class="{emit_html.KLASSE_TEXT} {emit_html.KLASSE_LINIE}" '
        f'cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse: collapse; margin: {SIGNATUR_ABSTAND} 0 0; '
        f'border-top: {linie};"><tr>'
        f'<td style="padding: {SIGNATUR_LUFT} {LOGO_SPALTENABSTAND} 0 0; '
        f'vertical-align: top;">'
        f'<img src="{logo.quelle}" alt="{name}" {masse}'
        f'style="display: block; border: 0; height: {hoehe}px; '
        f'width: {"auto" if not breite else f"{breite}px"};"></td>'
        f'<td class="{emit_html.KLASSE_TEXT} {emit_html.KLASSE_LINIE}" '
        f'style="padding: {SIGNATUR_LUFT} 0 0 {LOGO_SPALTENABSTAND}; '
        f'vertical-align: top; border-left: {linie}; '
        f'{emit_html.TEXTSTIL}">{inhalt}</td></tr></table>'
    )


def htmlteil(kopf: dict, profil: dict, bloecke, sprache: str = "de",
             logo: Logo | None = None, vorspann: str = "") -> str:
    """Dasselbe als HTML — derselbe Baum, andere Zielsprache."""
    email_teil = profil.get("email") or {}
    gruss = kopf.get("gruss") or email_teil.get("gruss") or profil.get("gruss")

    stuecke = [emit_html.setze(_mit_rahmen(kopf, gruss, bloecke)).rstrip("\n")]
    absaetze: list[str] = []
    for nummer, block in enumerate(signatur_bloecke(profil, kopf)):
        # Innerhalb eines Blocks `<br>` statt eigener Absätze: Eine Signatur ist
        # kein Fließtext, sondern eine Folge kurzer Zeilen — mit Absätzen risse
        # sie im Client auseinander. ZWISCHEN den Blöcken ist der Absatz genau
        # richtig, denn dort soll Luft sein.
        # Die erste Zeile des ersten Blocks ist der Name. Sie stand bisher wie
        # jede andere da — dieselbe Groesse wie die Umsatzsteuer-Nummer, und das
        # Auge fand keinen Anker (Operator, 04.09.2026: „schaut nach Behoerde
        # aus"). Sie bekommt deshalb Gewicht und eine Spur mehr Groesse.
        #
        # Bewusst KEINE Akzentfarbe: Die Signatur gehoert dem Absender, nicht
        # uns — eine gefaerbte Linie waere unsere Marke in fremder Post. Und
        # eine profilabhaengige Farbe kann nicht in DUNKELREGELN stehen, denn
        # der Block ist eine Konstante, die emit_html.verstoesse() Zeichen fuer
        # Zeichen vergleicht. Groesse und Gewicht tragen auf hellem wie auf
        # dunklem Grund, ohne eine einzige Farbe zu setzen.
        zeilen = [emit_html.as_text(z) for z in block]
        if nummer == 0 and zeilen:
            zeilen[0] = (
                f'<span style="font-size: 18px; font-weight: 600; '
                f'letter-spacing: -0.01em;">{zeilen[0]}</span>'
            )
        inhalt = emit_html.umbruch().join(zeilen)
        # Der Rechtsblock steht kleiner und leiser: Pflichtangaben und
        # Vertraulichkeitshinweis sind Beiwerk, nicht die Botschaft.
        leise = nummer == 2
        klassen = [emit_html.KLASSE_LEISE if leise else emit_html.KLASSE_TEXT]
        # Die Trennlinie zur Nachricht gehört an den ersten Block — aber nur,
        # solange er allein steht. Mit Logo trägt sie die Tabelle, und der
        # Absatz beginnt bündig oben in seiner Zelle: Eine zweite Linie quer
        # durch die rechte Spalte wäre ein Strich zu viel.
        if nummer == 0 and logo is None:
            rahmen = f"border-top: 1px solid {emit_html.RAHMEN}; padding-top: {SIGNATUR_LUFT}; "
            oben = SIGNATUR_ABSTAND
            klassen.append(emit_html.KLASSE_LINIE)
        else:
            rahmen = ""
            oben = "" if nummer == 0 else "10px"
        rand = f"margin: {oben} 0 0; " if oben else "margin: 0; "
        stil = (f"{rand}{rahmen}{emit_html.TEXTSTIL}"
                + (" font-size: 13px; color: #666;" if leise else ""))
        absaetze.append(
            f'<p class="{" ".join(klassen)}" style="{stil}">{inhalt}</p>'
        )

    if absaetze and logo is not None:
        stuecke.append(_signaturtabelle(profil, logo, "\n".join(absaetze)))
    else:
        stuecke.extend(absaetze)
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


def blindkopie_hinweis(adressen: str) -> str:
    """Was zu einem gesetzten Bcc zu sagen ist — an genau einer Stelle.

    Beide Aufrufwege brauchen denselben Satz: die Kommandozeile im Terminal,
    der MCP-Dienst als Feld seiner Antwort. Stünde er zweimal im Code,
    driftete er auseinander — genau das ist bei der `Date`-Begründung
    passiert, die nach #236 an sechs Stellen stand und an fünfen falsch war.
    """
    return (f"Blindkopie an {adressen} — steht als `Bcc:` in der Datei. "
            "Im Mailprogramm nachsehen, ob das Feld gefüllt ist.")


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
    """Die fertige Nachricht — ohne Message-ID und ohne Versandweg.

    `Date` steht seit #236 drin; die Begründung dafür und für das weiterhin
    fehlende `Message-ID` trägt der Modulkopf.

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
    # Bcc steht in der Datei, damit das Mailprogramm die Adresse übernehmen
    # kann, ohne dass sie jemand abtippt. Sie erscheint bewusst NICHT in der
    # `.html`-Vorschau — die ist zum Herauskopieren gedacht, und eine sichtbare
    # Zeile „Blindkopie" wäre genau das Gegenteil dessen, wofür das Feld da ist.
    # Frontmatter UND Profil (#272) - `blindkopien()` fuehrt beide zusammen.
    verdeckt = blindkopien(kopf, profil)
    if verdeckt:
        nachricht["Bcc"] = _adressliste(verdeckt)
    nachricht["Subject"] = str(kopf.get("betreff") or "")
    if kopf.get("antwort_auf"):
        nachricht["In-Reply-To"] = str(kopf["antwort_auf"])
        nachricht["References"] = str(kopf["antwort_auf"])

    # Date immer — RFC 5322 führt es als Pflichtfeld, und ein fehlendes zeigt
    # das Mailprogramm beim Weiterleiten als „(null), (null)" im Text an (#236).
    # SOURCE_DATE_EPOCH behält den Vorrang: Es macht den Golden-Vergleich
    # möglich, indem es das einzig Veränderliche festnagelt.
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    nachricht["Date"] = (formatdate(float(epoch), localtime=False) if epoch
                         else formatdate(localtime=True))

    logo = logo_quelle(profil, profil_pfad)
    text = textteil(kopf, profil, bloecke)
    html = htmlteil(kopf, profil, bloecke, sprache=sprache, logo=logo)

    # quoted-printable, nie base64: Eine Mail, deren Textteil als base64
    # ankommt, ist in jedem Rohansicht-Fenster unlesbar — und die Rohansicht
    # ist das, was von einer .eml als Vorlage übrig bleibt.
    nachricht.set_content(text, subtype="plain", charset="utf-8", cte="quoted-printable",
                          params={"format": "flowed", "delsp": "yes"})
    if mit_quelle:
        nachricht.add_alternative(quelle_md, subtype="markdown", charset="utf-8",
                                  cte="quoted-printable", params={"variant": "CommonMark"})
    nachricht.add_alternative(html, subtype="html", charset="utf-8", cte="quoted-printable")

    if logo is not None and logo.art == "datei":
        # `add_related` auf den HTML-Teil, nicht auf die Nachricht: Das Bild
        # gehört zu dieser einen Darstellung. Als Anhang der Nachricht stünde es
        # in jedem Client in der Anlagenliste — neben der Rechnung, die jemand
        # wirklich verschickt hat.
        #
        # Es reist MIT, und das bleibt die Vorgabe: Eine Signatur, die ihr Logo
        # über eine Adresse nachlädt, erscheint ohne Netz gar nicht und meldet
        # dem Absender, wann und wo geöffnet wurde. Seit #243 lässt sich das
        # ausdrücklich anders wählen — `email.logo` nimmt auch eine Adresse und
        # eine Data-URI, weil der Signatur-Baukasten im Browser keinen
        # MIME-Container hat. Gewählt wird es im Profil, nicht hier, und
        # `logo_hinweis()` sagt beim Setzen, was die Wahl kostet.
        html_teil = nachricht.get_payload()[-1]
        html_teil.add_related(logo.pfad.read_bytes(), maintype="image",
                              subtype=LOGO_FORMATE[logo.pfad.suffix.lower()],
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


def entwurfsfelder(pfad) -> dict:
    """Was aus einer fertigen `.eml` in einen Entwurf wandert (#263).

    Gelesen wird die **geschriebene Datei**, nicht der Baum, aus dem sie
    entstand: Der Entwurf soll das tragen, was gemessen wurde, und nicht eine
    zweite Ableitung derselben Quelle, die daneben laufen kann.

    Eine reine Funktion — sie startet nichts und kennt kein Mailprogramm. Was
    mit den Feldern geschieht, entscheidet `falzmarke.oeffnen`; die Grenze
    zwischen „E-Mail verstehen" und „ein fremdes Programm starten" bleibt damit
    dieselbe wie vorher (ADR 0038, Punkt 5).

    Anhänge kommen als Name und Inhalt zurück, nicht als Pfad: In der `.eml`
    stehen sie base64-kodiert, und ihre ursprünglichen Pfade kennt die Datei
    nicht mehr. Wer sie an ein Programm übergeben will, schreibt sie vorher
    heraus — das tut `oeffnen.entwurf()` in einem Verzeichnis, das es danach
    wieder abräumt.
    """
    import email as email_modul
    from email import policy as policy_modul

    nachricht = email_modul.message_from_bytes(Path(pfad).read_bytes(),
                                               policy=policy_modul.default)

    def _adressen(feld: str) -> list[str]:
        wert = nachricht.get(feld)
        if not wert:
            return []
        # Über `addresses` des Headers statt über einen Split an Kommas: In
        # einem Anzeigenamen darf ein Komma stehen („Gottl, Franz <x@y.de>"),
        # und ein naiver Split zerlegte genau die Adressen, die einen Namen
        # tragen. Der Name selbst bleibt hier draußen — in den Entwurf geht die
        # Adresse, den Namen kennt das Adressbuch des Programms.
        return [teil.addr_spec for teil in wert.addresses if teil.addr_spec]

    html = ""
    anhaenge: list[tuple[str, bytes]] = []
    for teil in nachricht.walk():
        if teil.get_content_maintype() == "multipart":
            continue
        if teil.get_content_disposition() == "attachment":
            name = teil.get_filename() or "Anlage"
            anhaenge.append((name, teil.get_payload(decode=True) or b""))
        elif teil.get_content_type() == "text/html" and not html:
            html = teil.get_payload(decode=True).decode(
                teil.get_content_charset() or "utf-8")

    return {
        "betreff": str(nachricht.get("Subject") or ""),
        "an": _adressen("To"),
        "kopie": _adressen("Cc"),
        # Bcc gehoert dazu, seit der Entwurf der uebliche Weg ist (#272). Bis
        # dahin fehlte es: Die Blindkopie stand in der `.eml`, `verify --email`
        # hatte sie gemessen - und im Entwurfsfenster fehlte sie, ohne dass es
        # jemandem auffiel. Eine Zeile, die nie da war, vermisst niemand.
        "blindkopie": _adressen("Bcc"),
        "html": html,
        "anhaenge": anhaenge,
    }
