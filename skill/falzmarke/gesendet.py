"""Ist diese Nachricht schon hinausgegangen? Die Gesendet-Sperre (ADR 0051).

ANLASS (21.10.2026): Eine Antwort ging zweimal an denselben Empfänger, kurz
hintereinander — nachdem eine Sitzung nur den Entwürfe-Ordner angesehen,
„nicht gesendet“ geschlossen und neu geöffnet hatte. Die zweite trug einen
**anderen Betreff** und denselben Text.

Bevor `email --oeffnen` einen Entwurf anlegt, sieht diese Prüfung deshalb im
Gesendet-Ordner des Absenders nach — live, über `falzmarke.postfach`, nur
lesend. Eine Mail der letzten 24 Stunden an denselben Empfänger sperrt, wenn

* ihr Text bis zur Grußformel derselbe ist (der Fall vom 21.10.),
* oder sie dieselbe Fassungs-Kopfzeile trägt (`X-Falzmarke-Fassung`),

→ `SCHON GESENDET`; und wenn nur der Betreff derselbe ist, der Text aber nicht,
→ `GEÄNDERTE FASSUNG` — Versendetes wird nicht geändert, sondern ergänzt.

Geht die Prüfung nicht (kein Proxy, ein Konto, das er nicht kennt, Zeitlimit),
wird **nicht** gesperrt: Ein abgeschalteter Proxy hielte sonst jede Mail auf.
Dann steht `GESENDET NICHT GEPRÜFT: <Grund>` als letzte Zeile da.

Der Vergleich ist bewusst grob. Thunderbird schreibt den Textteil aus dem
HTML neu: `*fett*`, `  * ` als Aufzählungszeichen, anderer Umbruch, die
Signatur ohne `-- `. Verglichen werden deshalb nur Buchstaben und Ziffern,
kleingeschrieben, ohne Adressen, bis zur Grußformel. Am 21.10.2026 ergab das
für die `.eml` und beide gesendeten Mails Zeichen für Zeichen denselben Kern.
"""

from __future__ import annotations

import email
import os
import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from email import policy
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple

STUNDEN_VORGABE = 24

#: Unter so vielen Zeichen gilt „derselbe Anfang“ nicht als Beleg: „Hallo Paula,
#: danke!“ steht am Anfang vieler verschiedener Mails.
ANFANG_MIN = 80

#: Ein Kern unter dieser Länge vergleicht nichts — eine leere Nachricht gliche
#: jeder anderen leeren.
KERN_MIN = 20

_GRUSS = re.compile(
    r"^(?:(?:viele|beste|liebe|herzliche|freundliche|schöne|sonnige|mit (?:freundlichen|"
    r"besten|herzlichen|lieben|vielen))\s+)?gr(?:ü|ue)(?:ß|ss)e?n?(?:\s+aus\s+.+)?$"
    r"|^(?:(?:best|kind|warm|warmest)\s+)?regards$|^(?:best|cheers|mfg|lg|vg|servus|ciao)$")

#: Was nach dem eigenen Text kommt: der Signaturtrenner, ein Zitat, die
#: Einleitung eines Zitats in deutscher und englischer Form, Outlooks Kopf.
_DANACH = re.compile(
    r"^--\s?$|^>|^(?:am|on)\s.+(?:schrieb|wrote)\b.*:$"
    r"|^-{2,}\s*(?:original|ursprüngliche)|^(?:von|from):\s")

_ADRESSE = re.compile(r"<?(?:https?|mailto):[^\s>]+>?")
_LISTE = re.compile(r"^\s*(?:[-*•·–+]|\d{1,3}[.)])\s+")
_VORSILBE = re.compile(r"^\s*(?:re|aw|wg|fw|fwd|antw|sv|vs|tr)\s*(?:\[\d+\])?\s*:\s*", re.I)


# ── Normalisieren ───────────────────────────────────────────────────────────

def _nur_zeichen(text: str) -> str:
    """Buchstaben und Ziffern, kleingeschrieben — alles andere fällt weg."""
    return "".join(z for z in text.casefold() if z.isalnum())


def betreff_kern(betreff: str) -> str:
    """Der Betreff ohne `AW:`, `Re:`, `WG:` … und ohne Satzzeichen.

    Halbgeviertstrich und Bindestrich sind dann dasselbe: Thunderbird schrieb
    am 21.10.2026 im Antwortfenster „-“, wo die Quelle „–“ trug.
    """
    rest = betreff or ""
    while True:
        kuerzer = _VORSILBE.sub("", rest, count=1)
        if kuerzer == rest:
            break
        rest = kuerzer
    return _nur_zeichen(rest)


def antwortstufe(betreff: str) -> int:
    """Wie viele `AW:`, `Re:`, `WG:` … vor dem Betreff stehen."""
    stufe, rest = 0, betreff or ""
    while (kuerzer := _VORSILBE.sub("", rest, count=1)) != rest:
        stufe, rest = stufe + 1, kuerzer
    return stufe


class _Klartext(HTMLParser):
    BLOCK = {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table",
             "ul", "ol", "blockquote", "pre", "hr"}
    STILL = {"style", "script", "head", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.teile: list[str] = []
        self._still = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.STILL:
            self._still += 1
        if tag in self.BLOCK:
            self.teile.append("\n")

    def handle_endtag(self, tag):
        if tag in self.STILL:
            self._still = max(0, self._still - 1)
        if tag in self.BLOCK:
            self.teile.append("\n")

    def handle_data(self, data):
        if not self._still:
            self.teile.append(data)


def klartext(nachricht) -> str:
    """Der Text einer Nachricht: der Textteil, sonst der HTML-Teil ohne Auszeichnung."""
    teil = nachricht.get_body(preferencelist=("plain", "html"))
    if teil is None:
        return ""
    try:
        inhalt = teil.get_content()
    except (LookupError, UnicodeError, KeyError):
        inhalt = (teil.get_payload(decode=True) or b"").decode("utf-8", "replace")
    if teil.get_content_subtype() == "html":
        leser = _Klartext()
        leser.feed(inhalt)
        leser.close()
        return "".join(leser.teile)
    return inhalt


def _schnitt(text: str, *, gruss: bool) -> str:
    """Der Text bis zur ersten Zeile, die nicht mehr zur Nachricht gehört."""
    zeilen = []
    for zeile in text.splitlines():
        rein = zeile.strip().casefold()
        if _DANACH.match(rein) or (gruss and _GRUSS.match(rein.rstrip(",.!"))):
            break
        zeilen.append(_LISTE.sub("", zeile))
    return _nur_zeichen(_ADRESSE.sub("", "\n".join(zeilen)))


class Merkmale(NamedTuple):
    """Was an einer Nachricht verglichen wird."""

    #: To und Cc, klein — bei gesendeten Mails auch Bcc.
    empfaenger: frozenset
    betreff: str
    #: Der Text bis zur Grußformel, nur Buchstaben und Ziffern.
    kern: str
    #: Der Text bis zur Signatur oder zum Zitat — mit Grußformel. Für eine
    #: Grußformel, die `_GRUSS` nicht kennt („Servus und bis bald“).
    bis_signatur: str
    #: Der ganze Text, nur Buchstaben und Ziffern.
    voll: str
    fassung: str


def merkmale_aus(*, empfaenger, betreff: str, text: str, fassung: str = "") -> Merkmale:
    """Die Merkmale aus Adressen, Betreff und Klartext — für einen Entwurf, der
    nur noch im Entwurfsbuch steht (ADR 0055), nicht mehr im Postfach."""
    return Merkmale(empfaenger=frozenset(a.strip().lower() for a in empfaenger if a.strip()),
                    betreff=betreff_kern(betreff),
                    kern=_schnitt(text, gruss=True), bis_signatur=_schnitt(text, gruss=False),
                    voll=_nur_zeichen(_ADRESSE.sub("", "\n".join(
                        _LISTE.sub("", z) for z in text.splitlines()))),
                    fassung=(fassung or "").strip())


def merkmale(nachricht, *, mit_bcc: bool = False) -> Merkmale:
    from email.utils import getaddresses

    felder = ("To", "Cc", "Bcc") if mit_bcc else ("To", "Cc")
    werte = [str(w) for f in felder for w in nachricht.get_all(f, [])]
    return merkmale_aus(empfaenger=[a for _, a in getaddresses(werte)],
                        betreff=str(nachricht.get("Subject") or ""), text=klartext(nachricht),
                        fassung=str(nachricht.get("X-Falzmarke-Fassung") or ""))


def gleicher_text(eigen: Merkmale, fremd: Merkmale) -> bool:
    """Derselbe Text — gleich bis zur Grußformel, oder der eigene ist der Anfang der fremden.

    Der zweite Weg fängt eine Grußformel, die `_GRUSS` nicht kennt: Dann reicht
    der eigene Kern bis zur Signatur, und die gesendete Mail beginnt damit.
    """
    if len(eigen.kern) >= KERN_MIN and eigen.kern == fremd.kern:
        return True
    return any(len(anfang) >= ANFANG_MIN and fremd.voll.startswith(anfang)
               for anfang in (eigen.kern, eigen.bis_signatur))


def vergleiche(eigen: Merkmale, fremd: Merkmale) -> str:
    """`gesendet`, `geaendert` oder `frei` — der Empfänger ist schon geprüft."""
    if eigen.fassung and eigen.fassung == fremd.fassung:
        return "gesendet"
    if gleicher_text(eigen, fremd):
        return "gesendet"
    if eigen.betreff and eigen.betreff == fremd.betreff:
        return "geaendert"
    return "frei"


# ── Prüfen ──────────────────────────────────────────────────────────────────

class Befund(NamedTuple):
    """Das Ergebnis der Prüfung.

    `zustand` ist einer von fünf Werten: `gesendet` und `geaendert` sperren;
    `frei` heißt nachgesehen und nichts gefunden; `nicht_geprueft` heißt
    **nicht** „frei“ — `grund` sagt, warum; `aus` heißt abgeschaltet.
    """

    zustand: str
    grund: str = ""
    datum: datetime | None = None
    an: str = ""
    betreff: str = ""
    ordner: str = ""
    adresse: str = ""
    #: Wie viele Mails im Zeitfenster angesehen wurden. Eine Zahl, kein „ok“:
    #: 0 bei einem Ordner, der sonst voll ist, wäre selbst ein Befund.
    angesehen: int = 0
    stunden: float = STUNDEN_VORGABE

    @property
    def sperrt(self) -> bool:
        return self.zustand in ("gesendet", "geaendert")


def _stunden(umgebung: Mapping[str, str]) -> float:
    wert = (umgebung.get("FALZMARKE_GESENDET_STUNDEN") or "").strip()
    try:
        return float(wert) if wert else STUNDEN_VORGABE
    except ValueError:
        return STUNDEN_VORGABE


def pruefe(eigen: Merkmale, absender: str, *, verbindung=None, ordner: str | None = None,
           jetzt: datetime | None = None, stunden: float = STUNDEN_VORGABE,
           umgebung: Mapping[str, str] | None = None) -> Befund:
    """Sieht im Gesendet-Ordner nach. Wirft nichts — ein Fehlschlag ist ein Befund.

    `verbindung` ist eine offene `postfach.Postfach`-Sitzung; ohne sie wird
    eine aufgebaut und danach wieder abgemeldet. `ordner` ist der IMAP-Name
    des Gesendet-Ordners; ohne ihn das Kennzeichen `\\Sent`, sonst
    „Gesendete Elemente“.
    """
    from falzmarke import postfach

    jetzt = jetzt or datetime.now(timezone.utc)
    grenze = jetzt - timedelta(hours=stunden)
    if not absender:
        return Befund("nicht_geprueft", "die Nachricht hat keinen Absender", stunden=stunden)
    eigene_sitzung = verbindung is None
    try:
        if eigene_sitzung:
            verbindung = postfach.verbinde(absender, umgebung=umgebung)
    except postfach.PostfachFehler as fehler:
        return Befund("nicht_geprueft", str(fehler), adresse=absender, stunden=stunden)
    try:
        ordner = ordner or verbindung.sonderordner("\\Sent") or "Gesendete Elemente"
        anzeige = postfach.utf7_dekodieren(ordner)
        koepfe = [k for k in verbindung.koepfe(ordner, seit=grenze.date())
                  if k.datum is None or k.datum >= grenze]
        geaendert = None
        for kopf in sorted(koepfe, key=lambda k: k.datum or jetzt, reverse=True):
            if not eigen.empfaenger & set(kopf.an):
                continue
            roh = verbindung.nachricht(ordner, kopf.uid)
            fremd = merkmale(email.message_from_bytes(roh, policy=policy.default), mit_bcc=True)
            urteil = vergleiche(eigen, fremd)
            if urteil == "frei":
                continue
            befund = Befund(urteil, datum=kopf.datum, an=", ".join(sorted(eigen.empfaenger
                                                                           & set(kopf.an))),
                            betreff=kopf.betreff, ordner=anzeige, adresse=absender,
                            angesehen=len(koepfe), stunden=stunden)
            if urteil == "gesendet":
                return befund
            geaendert = geaendert or befund
        if geaendert is not None:
            return geaendert
        return Befund("frei", ordner=anzeige, adresse=absender, angesehen=len(koepfe),
                      stunden=stunden)
    except postfach.PostfachFehler as fehler:
        return Befund("nicht_geprueft", str(fehler), adresse=absender, stunden=stunden)
    finally:
        if eigene_sitzung:
            verbindung.abmelden()


def pruefe_datei(eml_pfad, *, umgebung: Mapping[str, str] | None = None, verbindung=None,
                 jetzt: datetime | None = None, thunderbird_ordner: Path | None = None) -> Befund:
    """Die Prüfung für eine fertige `.eml` — gelesen wird die geschriebene Datei.

    `FALZMARKE_GESENDET=nie` schaltet ab, `FALZMARKE_GESENDET_STUNDEN` weitet
    oder verengt das Fenster (Vorgabe 24). Den Gesendet-Ordner nennt, wenn
    vorhanden, Thunderbird (`fcc_folder` der Identität, ADR 0050 liest
    dieselben Dateien).
    """
    umgebung = os.environ if umgebung is None else umgebung
    if (umgebung.get("FALZMARKE_GESENDET") or "").strip().lower() == "nie":
        return Befund("aus", "FALZMARKE_GESENDET=nie ist gesetzt")
    nachricht = email.message_from_bytes(Path(eml_pfad).read_bytes(), policy=policy.default)
    from email.utils import parseaddr

    absender = parseaddr(str(nachricht.get("From") or ""))[1].strip()
    ordner = None
    if absender:
        from falzmarke import oeffnen

        ordner = oeffnen.thunderbird_ordner(absender, "fcc_folder", thunderbird_ordner)
    return pruefe(merkmale(nachricht), absender, verbindung=verbindung, ordner=ordner,
                  jetzt=jetzt, stunden=_stunden(umgebung), umgebung=umgebung)


# ── Melden ──────────────────────────────────────────────────────────────────

def _zeit(datum: datetime | None, zeitzone) -> str:
    if datum is None:
        return "(ohne Datum)"
    return datum.astimezone(zeitzone).strftime("%d.%m.%Y %H:%M")


def meldung(befund: Befund, *, zeitzone=None) -> str:
    """Die Zeilen für die Ausgabe. Sperrt der Befund, beginnt die erste mit dem Urteil."""
    if befund.zustand == "gesendet":
        kopf = "SCHON GESENDET  "
        zeile = (f"{kopf}{_zeit(befund.datum, zeitzone)} an {befund.an}: „{befund.betreff}“"
                 f" (Ordner „{befund.ordner}“ von {befund.adresse})" if befund.ordner else
                 f"{kopf}{_zeit(befund.datum, zeitzone)} an {befund.an}: „{befund.betreff}“")
        return (zeile + "\n" + " " * len(kopf)
                + "Kein Entwurf angelegt. Trotzdem öffnen: --trotz-gesendet")
    if befund.zustand == "geaendert":
        kopf = "GEÄNDERTE FASSUNG  "
        return (f"{kopf}„{befund.betreff}“ ging {_zeit(befund.datum, zeitzone)} an "
                f"{befund.an} schon hinaus, mit anderem Text — als Nachtrag schicken?\n"
                + " " * len(kopf) + "Kein Entwurf angelegt. Trotzdem öffnen: --trotz-gesendet")
    if befund.zustand == "nicht_geprueft":
        return f"GESENDET NICHT GEPRÜFT: {befund.grund}"
    if befund.zustand == "frei":
        anzahl = "1 Mail" if befund.angesehen == 1 else f"{befund.angesehen} Mails"
        return (f"OK  nicht gesendet: {anzahl} der letzten {befund.stunden:g} h in "
                f"„{befund.ordner}“ von {befund.adresse} angesehen")
    return f"HINWEIS  Gesendet nicht geprüft: {befund.grund}"
