#!/usr/bin/env python3
"""Prüfung vor dem Render — ohne Typst, in Millisekunden.

Warum eine eigene Stufe: Ein Fehler in der Eingabe ist etwas anderes als ein
Fehler im Ergebnis. Bis v0.1.2 meldete der Betreff mit Schlusspunkt „das PDF
hält die Maße aus DIN 5008 nicht ein" — falsche Fehlerklasse, falscher
Exit-Code, und ein Render, der umsonst lief.

Befunde haben zwei Schweregrade. **Fehler** halten den Render an; **Warnungen**
nennen etwas, das gesetzt wird, aber vermutlich nicht gemeint war (zwei
Leerzeichen als Zeilenumbruch etwa — unsichtbar in jeder Vorschau).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from email.utils import parseaddr
from urllib.parse import urlparse

from falzmarke import regeln

FEHLER = "Fehler"
WARNUNG = "Warnung"

# Größen der Zonen, gegen die geprüft wird. Quelle: references/din5008.md
ANSCHRIFT_MAX_ZEILEN = 6
VERMERKE_MAX_ZEILEN = 3
INFOBLOCK_WERT_MAX = 32
BETREFF_MAX_ZEICHEN = 150      # zwei Zeilen bei 165 mm Satzbreite, 11 pt

# Leitwörter des Informationsblocks in der Reihenfolge der Norm.
# Steht hier und nicht in cli.py, weil cli lint importiert und nicht umgekehrt:
# So gibt es EINE Liste statt einer Kopie, die still veraltet.
#
# Die Reihenfolge ist die der Norm und gilt für jede Sprache. Wie das Leitwort
# heisst, steht in sprachen.LEITWOERTER — die deutsche Fassung hier ist die
# Vorgabe. tests/test_sprachen.py hält beide Mengen zusammen.
INFOBLOCK_REIHENFOLGE = [
    ("ihr_zeichen", "Ihr Zeichen"),
    ("ihre_nachricht_vom", "Ihre Nachricht vom"),
    ("unser_zeichen", "Unser Zeichen"),
    ("unsere_nachricht_vom", "Unsere Nachricht vom"),
    ("ansprechpartner", "Name"),
    ("telefon", "Telefon"),
    ("fax", "Fax"),
    ("email", "E-Mail"),
]

PFLICHTFELDER = ("profil", "empfaenger", "datum", "betreff")
EMAIL_PFLICHTFELDER = ("profil", "an", "betreff")

#: Was eine Begleitmail von ihrem Brief erben kann und deshalb nicht selbst
#: sagen muss (Issue #78). Die Liste steht doppelt — hier für den Datenvertrag,
#: in `cli.ERBT_VOM_BRIEF` für das Erben selbst; ein Test hält beide zusammen.
#: Zusammenzulegen hiesse, dass `lint` das ganze CLI-Modul lädt.
ERBBARE_FELDER = ("betreff", "profil")

# Der vollständige Datenvertrag: was im Frontmatter einer Briefdatei stehen darf.
# Dokumentiert in references/frontmatter.md; ein Test hält beide zusammen.
FRONTMATTER_FELDER = frozenset({
    "profil", "typ", "form", "norm", "dialekt", "sprache", "empfaenger", "vermerke",
    "datum", "betreff", "betreff_kurz", "infoblock", "anrede", "gruss",
    "unterzeichner", "signatur", "anlagen", "anlagen_dateien", "verteiler",
    "eingebettet",
})

#: Die Beziehungswerte, die PDF/A-3 fuer eine eingebettete Datei kennt.
#:
#: Vier, nicht mehr — Typst setzt dieselbe Liste durch und bricht bei allem
#: anderen ab (gemessen am 29.08.2026). Sie hier zu wiederholen ist trotzdem
#: kein Doppel: `lint` soll den Fehler VOR dem Rendern nennen, mit Feld und
#: Zeile, statt ihn als Compilerfehler durchzureichen.
EINBETTUNG_BEZIEHUNGEN = ("data", "source", "alternative", "supplement")

#: Was ein Eintrag unter `eingebettet:` tragen darf.
EINBETTUNG_FELDER = frozenset({"datei", "typ", "beschreibung", "beziehung"})

#: Und was er tragen MUSS. Alle drei verlangt PDF/A-3b, nicht falzmarke:
#: Typst bricht ohne `mime-type` und ohne `description` ab. Die Datei versteht
#: sich von selbst.
EINBETTUNG_PFLICHT = ("datei", "typ", "beschreibung")

# Dasselbe für `typ: email`. Bewusst eine eigene Liste statt einer gemeinsamen
# mit Ausnahmen: Die beiden Erzeugnisse teilen sich zwar Felder, aber wer die
# Listen zusammenlegt, muss an jeder Prüfung wieder unterscheiden — und vergisst
# es an einer.
EMAIL_FRONTMATTER_FELDER = frozenset({
    "profil", "typ", "dialekt", "sprache", "an", "cc", "betreff", "anrede", "gruss",
    "unterzeichner", "anlagen_dateien", "antwort_auf", "brief",
    # `datum` ist hier bekannt, damit es die eigene Warnung auslöst statt als
    # unbekanntes Feld zu gelten. Es wird nicht gesetzt — das tut der Client.
    "datum",
})

TYPEN = ("brief", "email")

#: Ein Feld des einen Erzeugnisses, das im anderen nichts bedeutet — mit dem
#: Namen, der stattdessen gemeint ist. Ein Brief an eine Mailadresse und eine
#: Mail an eine Postanschrift sind beides Dokumente, die niemanden erreichen.
STATTDESSEN = {"brief": {"an": "empfaenger", "cc": "verteiler", "antwort_auf": None},
               "email": {"empfaenger": "an", "verteiler": "cc", "vermerke": None,
                         "form": None, "betreff_kurz": None, "infoblock": None,
                         "signatur": None, "anlagen": None, "norm": None}}

#: Betreffgrenze der Mail. RFC 5322 begrenzt die Kopfzeile auf 78 Zeichen; was
#: darüber steht, wird gefaltet und in der Übersicht vieler Programme
#: abgeschnitten. Das ist keine Aussage der Norm, sondern eine des Mediums.
EMAIL_BETREFF_MAX = 78

#: Ab hier warnt der Linter. Die Vorschaufenster der gängigen Programme
#: zeigen rund 60 Zeichen; was dahinter steht, liest niemand vor dem Öffnen.
EMAIL_BETREFF_VORSCHAU = 60

#: Der Abschnitt `email:` im Profil. Ohne Liste bliebe ein Tippfehler dort
#: stumm — dieselbe Fehlerart, gegen die `_melde_unbekannte` im Frontmatter
#: gebaut wurde.
PROFIL_EMAIL_FELDER = frozenset({
    "absender", "anzeigename", "position", "web", "datenschutz",
    "pflichtangaben", "zusatz", "gruss", "logo",
    # Seit #105: eigene Nummern für die Signatur. Fehlt `telefon`, gilt der
    # Wert aus dem Informationsblock — kein Feld wurde umbenannt, wer nur den
    # Informationsblock pflegt, bekommt dieselbe Signatur wie bisher.
    "telefon", "mobil",
    # Ob gesiezt oder geduzt wird. Steuert NUR Warnungen, nie eine Änderung am
    # Text: Wie jemand seine Leser anspricht, entscheidet er selbst.
    "anrede",
})

#: Die beiden Anreden, die das Profil kennt.
ANREDEN = ("sie", "du")

#: Wörter in Versalien, die keine sind: Rechtsformen, Bank- und Registerangaben.
#: Sie stehen so im Handelsregister und lesen sich nicht wie Geschrei.
VERSALIEN_ERLAUBT = frozenset({
    "GMBH", "AG", "KG", "OHG", "UG", "EG", "EV", "SE", "GBR", "MBH",
    "IBAN", "BIC", "HRA", "HRB", "USTID", "USTIDNR", "ID", "PLZ",
    "EUR", "USD", "CHF", "AGB", "DIN", "ISO", "PDF", "URL", "EU", "DE",
})

#: Ab so vielen Buchstaben gilt ein Wort in Versalien als Geschrei. Zwei- und
#: dreistellige Kürzel gibt es zu viele, um sie alle aufzuzählen.
VERSALIEN_AB = 4

INFOBLOCK_FELDER = frozenset(schluessel for schluessel, _ in INFOBLOCK_REIHENFOLGE)

URL_MUSTER = re.compile(r"\bhttps?://\S*", re.I)
#: Grobform einer E-Mail-Adresse. Was sie offenlässt, prüft `adresse_grund()`.
EMAIL_MUSTER = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
#: Telefonnummer in der Schreibweise der Norm.
#:
#: Bis Issue #133 stand hier `^\+?[\d]{2,4}(\s\d+)*(-\d+)?$` — zwei bis vier
#: Ziffern für die Vorwahl. Deutsche Ortsnetzkennzahlen sind zwei- bis
#: fünfstellig, mit der führenden Null also drei- bis sechsstellig. Alles ab
#: `09401` wurde damit gemeldet, obwohl es richtig war: die Vorwahlen kleinerer
#: Orte, ein erheblicher Teil aller Festnetzanschlüsse. Die Quelle der Regel
#: nennt selbst `09161 6209800`.
#:
#: International steht die Kennzahl OHNE die Null hinter der Ländervorwahl —
#: deshalb zwei Zweige statt einem. Vorher ging `+49 9401 …` durch und
#: `09401 …` nicht: dieselbe Nummer, je nach Notation anders beurteilt.
TELEFON_MUSTER = re.compile(r"^(?:\+\d{1,3}\s\d{1,5}|0\d{2,5})(?:\s\d+)*(?:-\d+)?$")

#: Zeichen, die in einer Telefonnummer nach der Norm nicht vorkommen.
TELEFON_FREMDZEICHEN = ("(", ")", "/", ".", ",", ";")


def telefon_grund(text: str) -> str:
    """Was an dieser Nummer nicht passt — als Satz, nicht als Musterform.

    Die alte Meldung wiederholte nur die Sollform („Vorwahl mit Leerzeichen,
    Durchwahl mit Bindestrich"). Im Fall, der Issue #133 auslöste, war beides
    erfüllt; sie nannte also zwei Dinge, die stimmten, und verschwieg das
    Eigentliche. Wer das liest — auch eine Maschine — fügt einen Bindestrich
    ein, der dort nicht hingehört.
    """
    fremd = [z for z in TELEFON_FREMDZEICHEN if z in text]
    if fremd:
        return ("enthält " + ", ".join(f"`{z}`" for z in fremd)
                + " — die Norm setzt Vorwahl und Rufnummer nur durch ein Leerzeichen ab")
    if text != text.strip():
        return "beginnt oder endet mit einem Leerzeichen"
    if not text.startswith(("0", "+")):
        return "beginnt weder mit `0` noch mit `+` — die Vorwahl fehlt"
    if " " not in text:
        return "hat kein Leerzeichen zwischen Vorwahl und Rufnummer"
    if text.startswith("0") and not re.match(r"^0\d{2,5}\s", text):
        return ("hat eine Vorwahl von " + str(len(text.split(" ")[0]))
                + " Stellen — mit der führenden Null sind drei bis sechs vorgesehen")
    return "folgt nicht der Schreibweise der Norm"


#: Ein Domain-Label: Buchstaben, Ziffern, Bindestriche — aber nicht am Rand.
#:
#: `\w` statt `[A-Za-z0-9]`, damit internationale Namen (`ö.de`) hier NICHT
#: durchfallen: Sie sind nach RFC 6531 zulässig und gehören nach ADR 0035 auf
#: die Ebene Praxis, also zur Warnung — nicht zum Fehler. Der Unterstrich, den
#: `\w` mitbringt, ist ausgeschlossen: In Domänennamen kommt er nicht vor.
DOMAIN_LABEL = re.compile(r"^(?!-)(?!.*_)[\w-]+(?<!-)$")


def adresse_grund(eintrag: str, adresse: str) -> str | None:
    """Was an dieser Adresse nicht stimmt — oder None, wenn sie taugt.

    `parseaddr` zerlegt die Klammerform nach RFC 5322; das bleibt so, ein
    eigener Ausdruck träfe weniger Fälle. Geprüft wird hier, was `parseaddr`
    **offenlässt** — und das ist mehr, als es auf den ersten Blick scheint.

    Gemessen am 28.08.2026 gegen achtzehn Eingaben: Acht ungültige kamen durch,
    darunter der doppelte Punkt (`max@firma..de`) und ein Bindestrich am Rand
    eines Labels. Issue #125 nannte vier andere; zwei davon fing die Grobform
    schon ab. Wer nur `parseaddr` betrachtet, unterschätzt die eine Hälfte und
    übersieht die andere.
    """
    # `parseaddr` entfernt Leerzeichen aus der Adresse: „max@firma .de" wird zu
    # „max@firma.de". Ein Tippfehler würde damit still zu einer ANDEREN, gültigen
    # Adresse repariert und der Brief ginge dorthin. Genau das darf nicht sein.
    innen = eintrag.strip()
    if innen.endswith(">") and "<" in innen:
        innen = innen[innen.rindex("<") + 1:-1].strip()
    if innen != adresse and innen.replace(" ", "") == adresse:
        return "enthält ein Leerzeichen — gemeint ist vermutlich " + f"`{adresse}`"

    if adresse.count("@") != 1:
        return "hat nicht genau ein `@`"
    lokal, _, domain = adresse.partition("@")

    if not lokal:
        return "hat keinen Empfängerteil vor dem `@`"
    if lokal.startswith(".") or lokal.endswith("."):
        return "beginnt oder endet vor dem `@` mit einem Punkt"
    if ".." in lokal:
        return "hat zwei Punkte hintereinander vor dem `@`"

    if "." not in domain:
        return "hat keinen Punkt im Domänenteil — die Endung fehlt"
    labels = domain.split(".")
    if any(not teil for teil in labels):
        return "hat einen leeren Teil im Domänennamen — zwei Punkte oder ein Punkt am Rand"
    fehlerhaft = [teil for teil in labels if not DOMAIN_LABEL.match(teil)]
    if fehlerhaft:
        teil = fehlerhaft[0]
        # Den tatsaechlichen Grund nennen, nicht den haeufigsten: Wer bei einem
        # Unterstrich liest, Bindestriche stuenden falsch, sucht an der falschen
        # Stelle.
        if "_" in teil:
            warum = "Unterstriche kommen in Domänennamen nicht vor"
        elif teil.startswith("-") or teil.endswith("-"):
            warum = "Bindestriche stehen nicht am Anfang oder Ende"
        else:
            warum = "erlaubt sind Buchstaben, Ziffern und Bindestriche"
        return f"hat einen unzulässigen Teil im Domänennamen: `{teil}` — {warum}"
    if len(labels[-1]) < 2 or not labels[-1].isalpha():
        return "hat keine gültige Endung"
    return None


def adresse_ist_international(adresse: str) -> bool:
    """Nicht-ASCII in der Adresse.

    Nach RFC 6531 zulässig, von vielen Servern aber abgelehnt. Das ist eine
    Aussage über die Praxis, nicht über die Technik — nach ADR 0035 also nie
    ein Fehler, sondern eine Warnung.
    """
    return not adresse.isascii()
ISO_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Befund:
    zeile: int
    regel: str
    schwere: str
    meldung: str
    korrektur: str = ""

    def als_zeile(self, datei: str) -> str:
        marke = "FEHLER " if self.schwere == FEHLER else "WARNUNG"
        ort = f"{datei}:{self.zeile}" if self.zeile else datei
        text = f"{marke} {ort} {self.regel} — {self.meldung}"
        return f"{text}\n         Korrektur: {self.korrektur}" if self.korrektur else text

    def als_dict(self) -> dict:
        return {
            "zeile": self.zeile, "regel": self.regel, "schwere": self.schwere,
            "meldung": self.meldung, "korrektur": self.korrektur,
        }


@dataclass
class Bericht:
    befunde: list[Befund] = field(default_factory=list)

    def fehler(self, zeile: int, regel: str, meldung: str, korrektur: str = "") -> None:
        """Meldet einen Fehler — soweit die Quellenlage das trägt.

        Alle Maße und Schreibregeln stammen aus Sekundärquellen; der Abgleich
        mit dem Originaltext der DIN 5008:2020-03 steht aus. Solange das so
        ist, darf nur als Fehler gelten, was mehrfach belegt ist. Eine Regel
        aus einer einzigen Quelle wird hier zur Warnung und nennt das in der
        Meldung; eine Regel ohne Beleg wird gar nicht gemeldet.

        Die Herabstufung sitzt bewusst an dieser einen Stelle: Jeder Fehler im
        Linter läuft hier durch, und eine neue Prüfung erbt die Regel, ohne
        dass jemand daran denken muss.
        """
        stufe = regeln.deckel_von_lint(regel)
        if stufe == regeln.DECKEL_KEINE:
            return
        if stufe == regeln.DECKEL_WARNUNG:
            hinweis = regeln.quellenhinweis(regel)
            self.befunde.append(Befund(
                zeile, regel, WARNUNG,
                f"{meldung} — {hinweis}" if hinweis else meldung, korrektur))
            return
        self.befunde.append(Befund(zeile, regel, FEHLER, meldung, korrektur))

    def warnung(self, zeile: int, regel: str, meldung: str, korrektur: str = "") -> None:
        self.befunde.append(Befund(zeile, regel, WARNUNG, meldung, korrektur))

    @property
    def anzahl_fehler(self) -> int:
        return sum(1 for b in self.befunde if b.schwere == FEHLER)

    @property
    def anzahl_warnungen(self) -> int:
        return sum(1 for b in self.befunde if b.schwere == WARNUNG)

    @property
    def ok(self) -> bool:
        return self.anzahl_fehler == 0

    def als_text(self, datei: str) -> str:
        zeilen = [b.als_zeile(datei) for b in self.befunde]
        zeilen.append(f"lint: {self.anzahl_fehler} Fehler, {self.anzahl_warnungen} Warnungen")
        return "\n".join(zeilen)

    def als_dict(self) -> dict:
        return {
            "ok": self.ok,
            "fehler": self.anzahl_fehler,
            "warnungen": self.anzahl_warnungen,
            "befunde": [b.als_dict() for b in self.befunde],
        }


# ── Frontmatter ─────────────────────────────────────────────────────────────

def _feldzeile(kopf_roh: str, feld: str) -> int:
    """Die Zeile, in der ein Feld im Frontmatter steht — für die Meldung."""
    for nummer, zeile in enumerate(kopf_roh.splitlines(), start=1):
        if zeile.strip().startswith(f"{feld}:"):
            return nummer + 1
    return 1


def pruefe_datum(wert, zeile: int, bericht: Bericht) -> None:
    """Nur ein existierendes ISO-Datum.

    Bis v0.1.2 rutschte `datum: morgen` unbemerkt durch und stand wörtlich im
    Brief; `2026-13-45` endete in einem Traceback aus PyYAML.
    """
    if isinstance(wert, dt.date):
        return
    text = str(wert).strip()
    # `fromisoformat` nimmt seit Python 3.11 auch das Basisformat `20260825`.
    # Der Datenvertrag nennt JJJJ-MM-TT — was dort steht, gilt.
    try:
        if not ISO_DATUM.match(text):
            raise ValueError(text)
        dt.date.fromisoformat(text)
    except ValueError:
        bericht.fehler(
            zeile, "datum",
            f"„{text}“ ist kein Datum",
            "als ISO-Datum schreiben, z. B. 2026-08-25 — die Ausgabeform bestimmt das Profil",
        )


def pruefe_dialekt(kopf: dict, kopf_roh: str, bericht: Bericht) -> None:
    """Der Wert des Feldes `dialekt`.

    Ein Tippfehler darf nicht stillschweigend zur alten Fassung führen: Der
    Brief sähe dann anders aus als geschrieben, und die Meldung, die erklärt
    warum, käme nie. Die Liste der Fassungen steht in `markdown.py` — hier
    stünde sie ein zweites Mal und liefe auseinander.
    """
    from falzmarke import markdown as markdown_modul

    wert = kopf.get("dialekt")
    if wert is None:
        return
    try:
        markdown_modul.pruefe_fassung(wert)
    except markdown_modul.MarkdownFehler as fehler:
        bericht.fehler(
            _feldzeile(kopf_roh, "dialekt"), "dialekt", fehler.meldung,
            "ohne das Feld gilt die Fassung 1.0 — bestehende Briefe ändern sich nicht")


def _melde_unbekannte(
    schluessel, erlaubt: frozenset, regel: str, kopf_roh: str, bericht: Bericht
) -> None:
    """Ein Feld, das niemand liest, ist ein Fehler — kein Grund zum Schweigen.

    Bis v0.4.0 verwarf der Renderer jeden Schlüssel, den er nicht abfragte.
    `signatur:` im Brief blieb damit wirkungslos, ohne ein Wort. Das
    widerspricht der Zusage, mit der das Werkzeug antritt: abbrechen statt
    still etwas anderes zu setzen.
    """
    import difflib

    for feld in schluessel:
        if feld in erlaubt:
            continue
        nah = difflib.get_close_matches(str(feld).lower(), sorted(erlaubt), n=1, cutoff=0.6)
        rat = (f"meintest du `{nah[0]}`?" if nah
               else "erlaubt sind: " + ", ".join(sorted(erlaubt)))
        bericht.fehler(
            _feldzeile(kopf_roh, str(feld)), regel,
            f"`{feld}` ist kein Feld des Datenvertrags", rat,
        )


def _adressen(wert) -> list[str]:
    return [wert] if isinstance(wert, str) else [str(z) for z in (wert or [])]


def pruefe_adressfeld(wert, feld: str, kopf_roh: str, bericht: Bericht) -> None:
    """`erika@example.de` oder `Muster GmbH <post@example.de>` — sonst nichts.

    Geparst wird mit `email.utils.parseaddr` aus der Standardbibliothek, nicht
    mit einem eigenen Ausdruck: Die Klammerform ist in RFC 5322 festgelegt und
    hat mehr Fälle, als ein handgeschriebenes Muster trifft.
    """
    from email.utils import parseaddr

    for eintrag in _adressen(wert):
        _, adresse = parseaddr(eintrag)
        ort = _feldzeile(kopf_roh, feld)
        if not adresse or not EMAIL_MUSTER.match(adresse):
            bericht.fehler(
                ort, feld,
                f"„{eintrag}“ ist keine E-Mail-Adresse",
                "erwartet wird `name@beispiel.de` oder `Name <name@beispiel.de>`")
            continue
        grund = adresse_grund(eintrag, adresse)
        if grund:
            bericht.fehler(ort, feld, f"„{eintrag}“ {grund}",
                           "erwartet wird `name@beispiel.de` oder `Name <name@beispiel.de>`")
            continue
        if adresse_ist_international(adresse):
            bericht.warnung(
                ort, "email.adresse_international",
                f"„{adresse}“ enthält Zeichen ausserhalb von ASCII",
                "nach RFC 6531 zulässig, aber viele Server nehmen solche Adressen nicht an")


def _pruefe_ausschluss(kopf: dict, typ: str, kopf_roh: str, bericht: Bericht) -> None:
    """Felder des jeweils anderen Erzeugnisses melden, mit dem gemeinten Namen.

    Ohne diese Prüfung liefe der Fall über `_melde_unbekannte` und läse sich als
    „`empfaenger` ist kein Feld des Datenvertrags" — was in einem Briefwerkzeug
    schlicht falsch klingt. Der Fehler ist nicht, dass es das Feld nicht gibt,
    sondern dass es hier nichts bedeutet.
    """
    for feld, ersatz in STATTDESSEN[typ].items():
        if kopf.get(feld) is None:
            continue
        womit = "Brief" if typ == "brief" else "E-Mail"
        rat = f"`{feld}:` durch `{ersatz}:` ersetzen" if ersatz else f"`{feld}:` entfernen"
        bericht.fehler(
            _feldzeile(kopf_roh, feld), "typ",
            f"`{feld}:` gibt es in einem {womit} nicht", rat)


def pruefe_begleitbrief(kopf: dict, kopf_roh: str, bericht: Bericht) -> None:
    """`brief:` — der Brief, der als PDF an dieser Nachricht hängt (#78).

    Geprüft wird hier nur, was ohne Dateizugriff feststeht. Ob die Datei
    existiert und ob sie selbst eine Nachricht ist, meldet `setze_email` beim
    Setzen: Der Linter soll eine Briefdatei nicht nebenbei mitlesen, sonst
    wandert die halbe Prüfkette hierher.
    """
    wert = kopf.get("brief")
    if not isinstance(wert, str) or not wert.strip():
        bericht.fehler(
            _feldzeile(kopf_roh, "brief"), "brief",
            "`brief:` braucht den Pfad einer Briefdatei",
            "relativ zur Nachricht, etwa `brief: kuendigung.md`")
        return
    if not wert.strip().lower().endswith(".md"):
        bericht.fehler(
            _feldzeile(kopf_roh, "brief"), "brief",
            f"`brief: {wert}` ist keine Markdown-Datei",
            "erwartet wird die QUELLE des Briefes, nicht sein PDF — gesetzt wird "
            "er beim Bauen der Nachricht. Ein fertiges PDF gehört in "
            "`anlagen_dateien:`")


def pruefe_email_frontmatter(kopf: dict, kopf_roh: str, bericht: Bericht) -> None:
    """Der Datenvertrag der E-Mail-Fassung (ADR 0034)."""
    _melde_unbekannte(kopf.keys(), EMAIL_FRONTMATTER_FELDER, "frontmatter", kopf_roh, bericht)
    pruefe_dialekt(kopf, kopf_roh, bericht)
    _pruefe_ausschluss(kopf, "email", kopf_roh, bericht)

    # `brief:` bringt Betreff und Profil mit (#78). Sie hier trotzdem zu
    # verlangen hiesse, dieselbe Angabe zweimal zu fordern — genau das, wogegen
    # die Kopplung gebaut ist. `an:` bleibt Pflicht: Eine Postanschrift ist
    # keine Mailadresse, und der Brief trägt keine.
    # `"brief" in kopf` und nicht `kopf.get("brief")`: Ein leeres Feld ist ein
    # Tippfehler, kein fehlendes Feld — es wird unten gemeldet. Geerbt wird
    # natürlich nur von einem echten Pfad.
    genannt = "brief" in kopf
    erbt = bool(kopf.get("brief"))
    for feld in EMAIL_PFLICHTFELDER:
        if kopf.get(feld):
            continue
        if erbt and feld in ERBBARE_FELDER:
            continue
        bericht.fehler(1, feld, "Pflichtfeld fehlt", f"`{feld}:` im Frontmatter ergänzen")

    if genannt:
        pruefe_begleitbrief(kopf, kopf_roh, bericht)

    for feld in ("an", "cc"):
        if kopf.get(feld):
            pruefe_adressfeld(kopf[feld], feld, kopf_roh, bericht)

    betreff = str(kopf.get("betreff") or "").strip()
    if betreff:
        ort = _feldzeile(kopf_roh, "betreff")
        # Dieselben zwei Regeln wie im Brief. Sie stehen hier noch einmal, weil
        # der E-Mail-Zweig früh zurückkehrt — und weil sie in einer Mail aus
        # einem anderen Grund gelten: Das Leitwort „Betreff:" steht im
        # Vorschaufenster neben dem, was der Client ohnehin „Betreff" nennt.
        if betreff.lower().startswith(("betreff:", "betreff ")):
            bericht.fehler(ort, "betreff", "beginnt mit dem Leitwort „Betreff“",
                           "das Leitwort entfällt — der Client schreibt es davor")
        if betreff.endswith("."):
            bericht.fehler(ort, "betreff", "endet mit einem Punkt",
                           "der Betreff steht ohne Schlusspunkt")
        if len(betreff) > EMAIL_BETREFF_MAX:
            bericht.fehler(
                ort, "email.betreff",
                f"{len(betreff)} Zeichen — mehr als {EMAIL_BETREFF_MAX}",
                "kürzen; viele Programme schneiden die Übersicht früher ab")
        elif len(betreff) > EMAIL_BETREFF_VORSCHAU:
            bericht.warnung(
                ort, "email.betreff",
                f"{len(betreff)} Zeichen — das Vorschaufenster zeigt oft "
                f"nur {EMAIL_BETREFF_VORSCHAU}",
                "was hinten steht, liest niemand vor dem Öffnen")

    anrede = str(kopf.get("anrede") or "").strip()
    if anrede and not anrede.endswith(","):
        bericht.fehler(_feldzeile(kopf_roh, "anrede"), "anrede", "endet nicht mit Komma",
                       "nach DIN endet die Anrede mit einem Komma")

    gruss = str(kopf.get("gruss") or "").strip()
    if gruss.endswith(","):
        bericht.fehler(_feldzeile(kopf_roh, "gruss"), "gruss", "endet mit Komma",
                       "die Grußformel steht ohne Komma")

    # Zweimal dieselbe Adresse heißt: Der Empfänger bekommt die Mail zweimal,
    # oder sein Server verwirft eine — beides bemerkt der Absender nicht.
    for feld in ("an", "cc"):
        adressen = [parseaddr(e)[1].casefold() for e in _adressen(kopf.get(feld))]
        doppelt = sorted({a for a in adressen if adressen.count(a) > 1 and a})
        if doppelt:
            bericht.fehler(
                _feldzeile(kopf_roh, feld), feld,
                "dieselbe Adresse steht mehrfach: " + ", ".join(doppelt),
                "jede Adresse einmal nennen")

    antwort = kopf.get("antwort_auf")
    if antwort and not (str(antwort).startswith("<") and str(antwort).endswith(">")):
        bericht.fehler(
            _feldzeile(kopf_roh, "antwort_auf"), "antwort_auf",
            f"„{antwort}“ ist keine Message-ID",
            "eine Message-ID steht in spitzen Klammern: `<kennung@beispiel.de>`")


#: Höflichkeitsformen, großgeschrieben. `Ihr` fehlt bewusst: „Ihr" ist auch
#: das Possessiv der dritten Person Plural und am Satzanfang nicht von der
#: Anrede zu unterscheiden.
SIEZEN = re.compile(r"(?<![.!?]\s)\b(Sie|Ihnen|Ihre[nmrs]?)\b")

#: Dieselbe Vorsicht andersherum: `deren`, `dessen` und `da` fangen nicht mit
#: `du` an, aber `dein` steckt in nichts anderem.
DUZEN = re.compile(r"\b(du|dir|dich|dein(e[nmrs]?)?)\b")

#: Ein Wort in Versalien. Bindestriche gehören dazu (`USt-IdNr`), Ziffern nicht.
VERSALIEN = re.compile(r"\b[A-ZÄÖÜ][A-ZÄÖÜ-]{%d,}\b" % (VERSALIEN_AB - 2))


#: Wendungen, die nichts sagen — als Muster, nicht als Wortliste.
#:
#: Jede steht hier, weil sie **leer** ist: Sie liesse sich streichen, ohne dass
#: die Nachricht etwas verloere. Das ist die Aufnahmebedingung, und sie ist eng
#: gemeint. „Vielen Dank fuer die Unterlagen" bleibt draussen — der Dank gilt
#: einer Sache. „Vielen Dank fuer Ihre Zeit" steht drin: Er gilt nichts.
#:
#: Warum Muster und keine Liste: Dieselbe Floskel kommt in Varianten —
#: „ich hoffe, es geht Ihnen gut" und „ich hoffe, es geht dir gut". Sie einzeln
#: aufzuzaehlen hiesse, beim naechsten Duzen eine zu vergessen.
#:
#: Bewusst NICHT dabei: „im Anhang finden Sie", „bei Rueckfragen stehe ich zur
#: Verfuegung", „mit freundlichen Gruessen". Die ersten beiden tragen eine
#: Information, die dritte ist die Grussformel. Eine Warnung, die bei
#: gueltigem Text anschlaegt, kostet Vertrauen in alle anderen (#133).
FLOSKELN = [
    (re.compile(r"\bich hoffe,?\s+(?:diese|die)\s+(?:e-?mail|nachricht|zeilen)\b", re.I),
     "„ich hoffe, diese E-Mail …“"),
    (re.compile(r"\bich hoffe,?\s+es geht\s+(?:ihnen|dir|euch)\b", re.I),
     "„ich hoffe, es geht Ihnen gut“"),
    (re.compile(r"\bwollte (?:mich )?nur (?:kurz )?(?:melden|nachfragen|nachhaken)\b", re.I),
     "„wollte mich nur kurz melden“"),
    (re.compile(r"\bvielen dank für\s+(?:ihre|deine|eure)\s+zeit\b", re.I),
     "„vielen Dank für Ihre Zeit“"),
    (re.compile(r"\b(?:ich )?freue mich auf\s+(?:ihre|deine|eure)\s+(?:rückmeldung|antwort)\b", re.I),
     "„ich freue mich auf Ihre Rückmeldung“"),
    (re.compile(r"\bwie bereits (?:erwähnt|gesagt|besprochen)\s*,?\s*(?:möchte|wollte) ich\b", re.I),
     "„wie bereits erwähnt, möchte ich …“"),
    (re.compile(r"\bin diesem sinne\b", re.I), "„in diesem Sinne“"),
]


def pruefe_email_ton(profil: dict, kopf: dict, body: str, bericht: Bericht) -> None:
    """Anrede und Lautstärke — beides nur als Warnung (#105).

    **Es wird nie etwas geändert.** Wie jemand seine Leser anspricht, entscheidet
    er selbst; das Werkzeug sagt nur, wenn Profil und Text auseinandergehen.

    Die Prüfung ist bewusst schmal gehalten. Eine Warnung, die bei gültigem Text
    anschlägt, kostet Vertrauen in alle anderen — das war die Lehre aus der
    Telefonprüfung (#133). Deshalb kein `Ihr` am Satzanfang und keine Kürzel
    unter vier Buchstaben.
    """
    abschnitt = profil.get("email") or {}
    anrede = str(abschnitt.get("anrede") or "").strip().lower()
    text = "\n".join([str(kopf.get("anrede") or ""), body])

    if anrede == "du":
        treffer = sorted({m.group(0) for m in SIEZEN.finditer(text)})
        if treffer:
            bericht.warnung(
                1, "email.anrede_ton",
                "das Profil sagt `anrede: du`, im Text steht "
                + ", ".join(f"„{w}“" for w in treffer[:3]),
                "entweder das Profil oder den Text angleichen — geändert wird hier nichts")
    elif anrede == "sie":
        treffer = sorted({m.group(0).lower() for m in DUZEN.finditer(text)})
        if treffer:
            bericht.warnung(
                1, "email.anrede_ton",
                "das Profil sagt `anrede: sie`, im Text steht "
                + ", ".join(f"„{w}“" for w in treffer[:3]),
                "entweder das Profil oder den Text angleichen — geändert wird hier nichts")

    # Floskeln (#106). Warnung, nie Fehler: Ob ein Satz leer ist, ist eine
    # Aussage ueber den Stil und nicht ueber die Technik — nach ADR 0035 die
    # Ebene Praxis. Geaendert wird nichts; wie jemand schreibt, entscheidet er.
    leer = []
    for muster, name in FLOSKELN:
        if muster.search(body):
            leer.append(name)
    if leer:
        bericht.warnung(
            1, "email.floskel",
            "sagt nichts: " + ", ".join(leer[:3]),
            "die Zeile liesse sich streichen, ohne dass die Nachricht etwas "
            "verliert — dann sollte sie es auch")

    geschrien = sorted({w for w in VERSALIEN.findall(body)
                        if len(w.replace("-", "")) >= VERSALIEN_AB
                        and w.replace("-", "").replace(".", "") not in VERSALIEN_ERLAUBT})
    if geschrien:
        bericht.warnung(
            1, "email.versalien",
            "in Großbuchstaben geschrieben: " + ", ".join(f"„{w}“" for w in geschrien[:3]),
            "das liest sich wie Schreien — für Betonung reicht **fett**")


def pruefe_email_profil(profil: dict, bericht: Bericht,
                       profil_pfad=None) -> None:
    """Der Abschnitt `email:` eines Profils.

    Die Pflichtangaben je Rechtsform bleiben Hinweistext mit Quelle (ADR 0005).
    Gemeldet wird nur, dass das Feld leer ist — welche Angaben eine GmbH
    braucht, ist eine Rechtsfrage, und falzmarke beantwortet keine.
    """
    abschnitt = profil.get("email")
    if not isinstance(abschnitt, dict):
        bericht.fehler(
            1, "email.profil", "das Profil hat keinen Abschnitt `email:`",
            "`email:` mit mindestens `absender:` ergänzen — siehe references/frontmatter.md")
        return

    _melde_unbekannte(abschnitt.keys(), PROFIL_EMAIL_FELDER, "email.profil", "", bericht)

    if not abschnitt.get("absender"):
        bericht.fehler(
            1, "email.absender", "`email.absender:` fehlt im Profil",
            "die Absenderadresse steht im Profil, nicht im einzelnen Schreiben")
    else:
        pruefe_adressfeld(abschnitt["absender"], "email.absender", "", bericht)

    anrede = abschnitt.get("anrede")
    if anrede is not None and str(anrede).strip().lower() not in ANREDEN:
        bericht.fehler(
            1, "email.anrede", f"`email.anrede: {anrede}` gibt es nicht",
            "bekannt sind " + " und ".join(f"`{a}`" for a in ANREDEN))

    pruefe_email_logo(profil, profil_pfad, bericht)

    if not abschnitt.get("pflichtangaben"):
        bericht.warnung(
            1, "email.pflichtangaben", "`email.pflichtangaben:` ist leer",
            "je nach Rechtsform verlangt § 37a HGB bzw. § 35a GmbHG Angaben in "
            "jeder Geschäftsmail — falzmarke prüft das nicht, es erinnert nur")


def pruefe_eingebettet(kopf: dict, kopf_roh: str, bericht: Bericht) -> None:
    """`eingebettet:` — Dateien, die IM PDF stecken, nicht dahinter.

    Der Unterschied zu `anlagen_dateien:` ist der ganze Punkt: Jene haengt
    Seiten hinten an, das PDF wird laenger und ein Mensch blaettert hin. Diese
    hier legt eine Datei **in** das PDF; sichtbar wird nichts, lesbar ist sie
    fuer ein Programm. Das ist der Weg, auf dem spaeter eine Rechnung im
    XML-Format mitreist (Issue #114, Grundlage fuer #111).

    Wer etwas einbettet, bekommt PDF/A-**3b** statt 2b. Das ist keine
    Bequemlichkeit, sondern die Stufe, die Einbettung ueberhaupt zulaesst:
    PDF/A-2 kennt keine beliebigen Dateien im Dokument. Umgestellt wird nur auf
    Verlangen — wer nichts einbettet, bekommt weiter 2b (ADR 0033).
    """
    eintraege = kopf.get("eingebettet")
    if eintraege is None:
        return
    zeile = _feldzeile(kopf_roh, "eingebettet")
    if not isinstance(eintraege, list) or not eintraege:
        bericht.fehler(
            zeile, "eingebettet", "`eingebettet:` braucht eine Liste von Einträgen",
            "je Eintrag `datei:`, `typ:` und `beschreibung:` — siehe references/frontmatter.md")
        return

    for nummer, eintrag in enumerate(eintraege, start=1):
        wo = f"Eintrag {nummer} unter `eingebettet:`"
        if not isinstance(eintrag, dict):
            bericht.fehler(zeile, "eingebettet", f"{wo} ist kein Abschnitt",
                           "erwartet werden `datei:`, `typ:` und `beschreibung:`")
            continue
        _melde_unbekannte(eintrag.keys(), EINBETTUNG_FELDER, "eingebettet", kopf_roh, bericht)
        for feld in EINBETTUNG_PFLICHT:
            if not eintrag.get(feld):
                bericht.fehler(
                    zeile, "eingebettet", f"{wo}: `{feld}:` fehlt",
                    "PDF/A-3b verlangt Dateiname, Medientyp und eine Beschreibung — "
                    "ohne sie lehnt schon der Satz ab")
        beziehung = eintrag.get("beziehung")
        if beziehung is not None and str(beziehung).lower() not in EINBETTUNG_BEZIEHUNGEN:
            bericht.fehler(
                zeile, "eingebettet", f"{wo}: `beziehung: {beziehung}` gibt es nicht",
                "PDF/A-3 kennt " + ", ".join(f"`{b}`" for b in EINBETTUNG_BEZIEHUNGEN))


def pruefe_email_logo(profil: dict, profil_pfad, bericht: Bericht) -> None:
    """Ein Logo in der Signatur muss auf hellem UND dunklem Grund tragen.

    Die Signatur schaltet ihre Farben um, sobald das Schema dunkel ist — Text,
    gedaempfter Text und Trennlinie. **Das Logo kann das nicht.** Es ist ein
    Rasterbild, und ein Rasterbild hat keine Farbe, die eine Medienabfrage
    aendern koennte; SVG waere umschaltbar, wird von Outlook aber nicht
    dargestellt (`eml.LOGO_FORMATE`).

    Der Ausweg ueber zwei Bilder und eine `display`-Regel steht nicht offen: Der
    `<style>`-Block einer erzeugten Nachricht ist nach ADR 0034 auf Farbangaben
    beschraenkt, und eine Ausnahme, die auch Sichtbarkeit steuert, ist keine
    enge Ausnahme mehr. Es bleibt die Wahl des Absenders — und die wird hier
    gemessen statt vorausgesetzt (Issue #154).

    Warnung, nicht Fehler: Ob ein Logo traegt, ist eine Aussage ueber die
    Wahrnehmung auf einem Grund, den kein Mailprogramm im Datenmodell nennt.
    Nach ADR 0035 gehoert das auf die Ebene Praxis.
    """
    if profil_pfad is None:
        return
    from falzmarke import eml

    try:
        bild = eml.logo_datei(profil, profil_pfad)
    except ValueError:
        # Das Format meldet `eml.baue` beim Setzen mit eigener Meldung. Hier
        # nochmal zu melden hiesse, denselben Fehler zweimal zu erzaehlen.
        return
    if bild is None or not bild.is_file():
        return

    from falzmarke import farbe

    try:
        ohne = farbe.logo_grund_ohne_halt(bild)
    except Exception as fehler:                      # noqa: BLE001
        # Ein unlesbares Bild ist NICHT stillschweigend in Ordnung: Es faellt
        # sonst erst beim Empfaenger auf, und dort als fehlendes Logo.
        bericht.warnung(
            1, "email.logo_kontrast", f"`{bild.name}` liess sich nicht messen: {fehler}",
            "das Bild muss ein lesbares Rasterbild sein — sonst kommt es beim "
            "Empfaenger gar nicht an")
        return
    if not ohne:
        return

    bericht.warnung(
        1, "email.logo_kontrast",
        f"`{bild.name}` traegt auf {' und '.join(ohne)} Grund nicht "
        f"(unter {int(farbe.ANTEIL_MINDEST * 100)} % der sichtbaren Flaeche "
        f"erreichen {farbe.SCHWELLE:.0f}:1 nach WCAG 1.4.11)",
        "ein Logo in der Mail schaltet seine Farben nicht um — es muss auf "
        "beiden Gruenden lesbar sein, oder `email.logo` bleibt aus")


def pruefe_email_anlagen(kopf: dict, body: str, bericht: Bericht) -> None:
    """Jede Anlage soll im Text vorkommen — als Hinweis, nicht als Eingriff.

    Ein Werkzeug, das ungefragt Sätze in einen Brieftext schreibt, schreibt
    irgendwann den falschen. Gemeldet wird deshalb nur, dass der Dateiname
    nirgends auftaucht; was daraus folgt, entscheidet der Absender.

    Gesucht wird nach dem Namen **ohne** Endung: Im Fließtext steht „das
    Angebot 2026-0815", nicht „angebot-2026-0815.pdf".
    """
    from pathlib import Path as _Pfad

    unten = body.casefold()
    for eintrag in _adressen(kopf.get("anlagen_dateien")):
        stamm = _Pfad(str(eintrag)).stem
        kerne = [stamm.casefold()] + [t for t in re.split(r"[-_.]", stamm.casefold()) if len(t) > 3]
        if not any(k in unten for k in kerne):
            bericht.warnung(
                _feldzeile("", "anlagen_dateien"), "email.anlage",
                f"„{eintrag}“ wird im Text nicht genannt",
                "Anlagen im Text erwähnen — falzmarke fügt dafür keinen Satz ein")


def pruefe_frontmatter(kopf: dict, kopf_roh: str, bericht: Bericht) -> None:
    typ = str(kopf.get("typ") or "brief")
    if typ not in TYPEN:
        bericht.fehler(
            _feldzeile(kopf_roh, "typ"), "typ", f"`typ: {typ}` ist unbekannt",
            "möglich sind: " + ", ".join(TYPEN))
        typ = "brief"
    if typ == "email":
        pruefe_email_frontmatter(kopf, kopf_roh, bericht)
        # `datum:` setzt der Mailclient beim Versand. Still übergehen wäre die
        # Fehlerart, gegen die dieses Werkzeug antritt.
        if kopf.get("datum") is not None:
            bericht.warnung(
                _feldzeile(kopf_roh, "datum"), "email.datum",
                "`datum:` wird in einer E-Mail nicht gesetzt",
                "der Mailclient setzt es beim Versand; die Zeile kann weg")
        return

    _melde_unbekannte(kopf.keys(), FRONTMATTER_FELDER, "frontmatter", kopf_roh, bericht)
    _pruefe_ausschluss(kopf, "brief", kopf_roh, bericht)
    pruefe_dialekt(kopf, kopf_roh, bericht)
    if isinstance(kopf.get("infoblock"), dict):
        _melde_unbekannte(
            kopf["infoblock"].keys(), INFOBLOCK_FELDER, "infoblock", kopf_roh, bericht)

    for feld in PFLICHTFELDER:
        if not kopf.get(feld):
            bericht.fehler(1, feld, "Pflichtfeld fehlt", f"`{feld}:` im Frontmatter ergänzen")

    if kopf.get("datum") is not None:
        pruefe_datum(kopf["datum"], _feldzeile(kopf_roh, "datum"), bericht)

    pruefe_eingebettet(kopf, kopf_roh, bericht)

    empfaenger = kopf.get("empfaenger")
    if empfaenger:
        zeilen = [empfaenger] if isinstance(empfaenger, str) else list(empfaenger)
        ort = _feldzeile(kopf_roh, "empfaenger")
        if len(zeilen) > ANSCHRIFT_MAX_ZEILEN:
            bericht.fehler(
                ort, "empfaenger", f"{len(zeilen)} Zeilen",
                f"die Anschriftzone fasst {ANSCHRIFT_MAX_ZEILEN} Zeilen — Angaben zusammenfassen",
            )
        if any(not str(z).strip() for z in zeilen):
            bericht.fehler(ort, "empfaenger", "Leerzeile im Anschriftfeld",
                           "die Norm lässt im Anschriftfeld keine Leerzeilen zu")
        if len(zeilen) >= 2:
            letzte = str(zeilen[-1]).strip()
            vorletzte = str(zeilen[-2]).strip()
            if letzte.isupper() and len(letzte) > 3 and not vorletzte.isupper():
                bericht.warnung(
                    ort, "empfaenger",
                    f"„{letzte}“ sieht nach einer Auslandsanschrift aus",
                    "bei Auslandspost gehören Bestimmungsort und Land in Großbuchstaben",
                )

    vermerke = kopf.get("vermerke") or []
    if isinstance(vermerke, str):
        vermerke = [vermerke]
    if len(vermerke) > VERMERKE_MAX_ZEILEN:
        bericht.fehler(
            _feldzeile(kopf_roh, "vermerke"), "vermerke", f"{len(vermerke)} Zeilen",
            f"die Zusatz- und Vermerkzone fasst {VERMERKE_MAX_ZEILEN} Zeilen",
        )

    betreff = str(kopf.get("betreff") or "").strip()
    if betreff:
        ort = _feldzeile(kopf_roh, "betreff")
        if betreff.lower().startswith("betreff"):
            bericht.fehler(ort, "betreff", "beginnt mit dem Leitwort „Betreff“",
                           "das Leitwort entfällt — der Betreff steht für sich")
        if betreff.endswith("."):
            bericht.fehler(ort, "betreff", "endet mit einem Punkt",
                           "der Betreff steht ohne Schlusspunkt")
        if len(betreff) > BETREFF_MAX_ZEICHEN:
            bericht.fehler(
                ort, "betreff", f"{len(betreff)} Zeichen",
                f"höchstens zwei Zeilen, das sind rund {BETREFF_MAX_ZEICHEN} Zeichen",
            )

    anrede = str(kopf.get("anrede") or "").strip()
    if anrede and not anrede.endswith(","):
        bericht.fehler(_feldzeile(kopf_roh, "anrede"), "anrede", "endet nicht mit Komma",
                       "nach DIN endet die Anrede mit einem Komma")

    gruss = str(kopf.get("gruss") or "").strip()
    if gruss.endswith(","):
        bericht.fehler(_feldzeile(kopf_roh, "gruss"), "gruss", "endet mit Komma",
                       "die Grußformel steht ohne Komma")

    infoblock = kopf.get("infoblock") or {}
    if isinstance(infoblock, dict):
        ort = _feldzeile(kopf_roh, "infoblock")
        for schluessel, wert in infoblock.items():
            if wert is None:
                continue
            text = str(wert)
            if len(text) > INFOBLOCK_WERT_MAX:
                bericht.fehler(
                    ort, f"infoblock.{schluessel}", f"{len(text)} Zeichen",
                    f"höchstens {INFOBLOCK_WERT_MAX} — sonst passt die Zeile nicht in die 75 mm",
                )
            if schluessel == "email" and not EMAIL_MUSTER.match(text):
                bericht.fehler(ort, "infoblock.email", f"„{text}“ ist keine E-Mail-Adresse",
                               "Form: name@example.de")
            if schluessel in ("telefon", "fax") and not TELEFON_MUSTER.match(text):
                bericht.warnung(
                    ort, f"infoblock.{schluessel}",
                    f"„{text}“ {telefon_grund(text)}",
                    "Schreibweise der Norm: 0941 620-9800, international +49 941 620-9800",
                )


# ── Body ────────────────────────────────────────────────────────────────────

def pruefe_body(body: str, versatz: int, bericht: Bericht) -> None:
    for nummer, zeile in enumerate(body.splitlines(), start=1 + versatz):
        if zeile.endswith("  ") and zeile.strip():
            bericht.warnung(
                nummer, "umbruch", "zwei Leerzeichen am Zeilenende erzeugen einen Umbruch",
                "besser einen Backslash setzen — zwei Leerzeichen sieht man in keiner Vorschau",
            )
        if "\t" in zeile:
            bericht.warnung(nummer, "tabulator", "Tabulator im Text wird zu einem Leerzeichen",
                            "Tabulatoren entfernen")
        for treffer in URL_MUSTER.finditer(zeile):
            roh = treffer.group().rstrip(".,;:)")
            zerlegt = urlparse(roh)
            if not zerlegt.netloc or " " in roh:
                bericht.fehler(nummer, "url", f"„{roh}“ ist keine wohlgeformte Adresse",
                               "Schema und Hostname prüfen")


# Keine eigene Glyphenprüfung.
#
# Der Auftrag sah vor, jedes Zeichen gegen die cmap der Profilschrift zu halten.
# Gemessen am 25.08.2026 ist das überflüssig und wäre die schlechtere Lösung:
#
#   1. Mit `ignore_system_fonts` und PDF/A bricht Typst selbst ab und nennt das
#      Zeichen: `the text "🙂" could not be displayed with font "Libertinus Serif"`.
#   2. Ohne PDF/A entsteht Tofu — und weil das Zeichen dann im PDF-Text fehlt,
#      schlägt die Vollständigkeitsprüfung in `verify` an.
#
# Eine selbst gepflegte Zeichenliste könnte dagegen von der Wirklichkeit
# abweichen: Sie veraltet mit jeder Schriftversion und meldet dann Zeichen als
# fehlend, die es gibt — oder umgekehrt. Der Renderer weiß es genau.
#
# Der Preis ist Zeit: Der Befund kommt nach dem Render statt in Millisekunden.
