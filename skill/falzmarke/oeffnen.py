"""Eine fertige Datei an das Betriebssystem übergeben — mehr nicht.

Der einzige Ort im Paket, an dem ein fremdes Programm anläuft. Er kennt weder
E-Mail noch Brief, nur einen Pfad: *Was* übergeben wird, entscheidet der
Aufrufer, *womit* es geöffnet wird, das Betriebssystem.

**Öffnen ist kein Versand** (ADR 0038, in der Folge von 0034). Gemessen am
27.08.2026 — `docs/mailprogramme-2026-08-27.md` — erscheint eine `.eml` in
Apple Mail, Thunderbird und Outlook für Mac als *Lesefenster*: kein
Senden-Knopf, keine editierbaren Empfängerfelder. Der Weg zur ausgehenden Mail
heißt dort „Weiterleiten", und ihn geht ein Mensch. Dieses Modul sagt deshalb
zu, dass die Datei im Programm ankommt — nicht, dass sie dort ein Entwurf ist.

Warum das ein eigenes Modul ist und nicht drei Zeilen in `cli.py`: `dienst.py`
importiert `falzmarke.cli` auf Modulebene. Ein `import subprocess` dort läge in
jedem MCP-Prozess, in derselben Datei wie die Bibliotheksfunktionen. So bleibt
die Grenze eine Aussage, die ein Test prüfen kann — genau eine Datei im Paket
startet fremde Programme, und sie heißt so wie diese hier.
"""

from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import NamedTuple

# Der übliche Starter je System. Windows fehlt mit Absicht: Dort gibt es kein
# Programm dieser Art, sondern `os.startfile` — siehe `weg()`.
STARTER = {"darwin": "open", "linux": "xdg-open", "freebsd": "xdg-open"}

# Wie lange auf den Starter gewartet wird. Er soll sofort zurückkehren; bleibt
# er hängen, hat er ein Programm im Vordergrund gestartet statt es abzukoppeln.
FRIST_S = 20


def weg(pfad, plattform: str = sys.platform) -> tuple[str, list[str]] | None:
    """Wie diese Plattform öffnet — als Angabe, nicht als Tat.

    Reine Funktion: Die Plattform ist ein Parameter, kein Blick auf die eigene.
    Damit lässt sich die Weiche für jedes System auf jedem System prüfen, ohne
    dass ein Fenster aufginge und ohne `skipif` — eine übersprungene Prüfung
    sieht aus wie eine bestandene.

    `startswith` statt `==`, weil Linux je nach Bau `linux` oder `linux2`
    meldet und Windows auch auf 64 Bit `win32` heißt.

    Der Pfad wird aufgelöst, bevor er weiterwandert: `-o` nimmt jeden Zielnamen
    an, und ein relativer Name mit führendem Strich wäre für `open` ein
    Schalter statt einer Datei.
    """
    ziel = str(Path(pfad).resolve())
    if plattform.startswith("win"):
        return ("startfile", [ziel])
    for kennung, programm in STARTER.items():
        if plattform.startswith(kennung):
            return ("argv", [programm, ziel])
    return None


def kein_bildschirm(umgebung: Mapping[str, str] | None = None,
                    plattform: str = sys.platform) -> str | None:
    """Der Grund, warum hier nichts aufgehen kann — oder None.

    Rein über die übergebene Umgebung: Die Funktion liest nichts, was der
    Aufrufer ihr nicht mitgibt, und ist damit für jede Lage prüfbar, ohne dass
    diese Lage hergestellt werden müsste.

    `FALZMARKE_OEFFNEN` hat Vorrang vor allem anderen — `nie` für Rechner, auf
    denen nichts aufgehen soll, `immer` für den, der es besser weiß.
    """
    umgebung = os.environ if umgebung is None else umgebung
    wunsch = (umgebung.get("FALZMARKE_OEFFNEN") or "").strip().lower()
    if wunsch == "immer":
        return None
    if wunsch == "nie":
        return "FALZMARKE_OEFFNEN=nie ist gesetzt"
    if (umgebung.get("CI") or "").strip().lower() not in ("", "0", "false"):
        return "CI ist gesetzt — auf einem Baurechner gibt es kein Fenster"
    if plattform.startswith(("linux", "freebsd")) and not (
            umgebung.get("DISPLAY") or umgebung.get("WAYLAND_DISPLAY")):
        return ("weder DISPLAY noch WAYLAND_DISPLAY ist gesetzt — "
                "keine Sitzung, in der ein Fenster aufginge")
    return None


def _lauf(argv: list[str], frist: int, laufen=subprocess.run):
    """Die einzige Stelle im Paket, an der wirklich ein Prozess startet.

    Sie tut nichts als aufzurufen — und genau deshalb gibt es sie: Ein Test,
    der kein Fenster aufgehen lassen will, ersetzt EINE Funktion und ist damit
    fertig. Vor #263 lag der Aufruf an zwei Stellen; die zweite kam mit dem
    Entwurfsweg dazu und wäre am Sicherheitsnetz der Testdatei vorbeigelaufen
    — gemessen, mit einem echten Fenster auf dem Rechner des Entwicklers.
    """
    return laufen(argv, capture_output=True, text=True, timeout=frist, check=False)


def _fuehre_aus(art: str, argv: list[str], *,
                laufen=subprocess.run, startfile=None) -> tuple[int, str]:
    """Die einzige Stelle, an der ein fremdes Programm anläuft.

    **Ohne `shell=True`**, und das ist keine Vorsicht auf Vorrat: Mit einer
    Shell dazwischen läse ein Interpreter den Dateinamen. Ein Zielname mit
    Leerzeichen, `&`, `;`, `$(…)` — und `-o` nimmt jeden Namen — wäre dann
    nicht mehr ein Argument, sondern Text in einer Befehlszeile. Als Liste
    übergeben reicht das Betriebssystem jedes Element unverändert weiter: Es
    gibt nichts zu maskieren, weil nichts geparst wird. Aus demselben Grund
    kein `start` über cmd.exe — das ist ein Builtin und ginge nur mit Shell.

    `laufen` und `startfile` sind Einstiegspunkte für die Prüfung. Ohne sie
    ließe sich diese Funktion nur messen, indem man wirklich etwas startet.
    """
    if art == "startfile":
        oeffner = getattr(os, "startfile", None) if startfile is None else startfile
        if oeffner is None:  # pragma: no cover — nur außerhalb von Windows
            return 127, "os.startfile gibt es auf diesem System nicht"
        try:
            oeffner(argv[0])
        except OSError as fehler:
            return 1, str(fehler)
        return 0, ""
    try:
        lauf = _lauf(argv, FRIST_S, laufen)
    except FileNotFoundError:
        return 127, f"{argv[0]} gibt es auf diesem System nicht"
    except subprocess.TimeoutExpired:
        return 124, f"{argv[0]} kam in {FRIST_S} Sekunden nicht zurück"
    return lauf.returncode, (lauf.stderr or "").strip()


def oeffne(pfad, *, plattform: str = sys.platform,
           umgebung: Mapping[str, str] | None = None) -> str | None:
    """Übergibt die Datei — oder sagt in einem Satz, warum nicht.

    `None` heißt übergeben. Alles andere ist der Grund und wandert unverändert
    in die Meldung des Aufrufers.

    Es wird **nichts geworfen**: Wer hierher kommt, hat seine Datei bereits,
    und ein Fenster, das nicht aufgeht, macht sie nicht ungültig (ADR 0038,
    Punkt 4).

    Gemeldet wird, was das Programm selbst sagt, nicht eine eigene Deutung
    seines Exit-Codes: `xdg-open` dokumentiert seine Codes, `open` unter macOS
    nicht — eine eigene Tabelle wäre für die Hälfte der Fälle geraten.
    """
    grund = kein_bildschirm(umgebung, plattform)
    if grund:
        return grund
    gewaehlt = weg(pfad, plattform)
    if gewaehlt is None:
        return f"für {plattform} ist hier kein Weg zum Öffnen bekannt"
    code, meldung = _fuehre_aus(*gewaehlt)
    if code == 0:
        return None
    return meldung or f"{gewaehlt[1][0]} endete mit Code {code}"


# ── Der Entwurf: ein Glied weiter als die Dateiübergabe (#263) ───────────────
#
# ADR 0038 verbot Programmsteuerung ursprünglich ganz. Die Begründung ist
# geblieben und einen Schritt weitergerückt: **Entwurf ja, Senden nie.** Was
# hier steht, legt eine ausgehende Nachricht an und öffnet sie; es gibt in
# diesem Modul keinen Aufruf, der sie abschickt, und `tests/test_skillpaket.py`
# misst das am ganzen Paket.

#: Wie lange auf das Steuerskript gewartet wird. Großzügiger als `FRIST_S`:
#: Ein Mailprogramm, das erst starten muss, braucht länger als `open`.
FRIST_ENTWURF_S = 90

#: Das Skript für Outlook. Eine **Konstante** — nichts daran wird aus Eingaben
#: zusammengesetzt. Jeder Wert kommt über `on run argv` als Argument herein,
#: und `osascript` bekommt die Argumente als Liste. Damit gibt es nichts zu
#: maskieren, weil nichts geparst wird: derselbe Grund wie beim fehlenden
#: `shell=True` eine Ebene höher. Ein Betreff mit Anführungszeichen wäre in
#: einem zusammengesetzten Skript eine Programmzeile — hier ist er ein Wert.
#:
#: Die Reihenfolge ist fest: 1 Betreff, 2 HTML-Rumpf, 3 Empfänger (mit Komma
#: getrennt), 4 Kopie, 5 Blindkopie, 6 Absender, ab 7 die Anhänge als Pfade.
#:
#: **Der Absender (#305).** Ohne Konto legt Outlook den Entwurf auf sein
#: Standardkonto, und wer mehrere hat, verschickt vom falschen Postfach. Das
#: Skript sucht deshalb das Konto mit der Adresse des Profils und legt den
#: Entwurf darauf an. Gemessen am 13.09.2026, Outlook für Mac 16.112.4: Im
#: klassischen Outlook kommt das Konto im Fenster an. Im neuen Outlook sieht
#: AppleScript kein einziges Konto — die drei Suchen laufen dort leer, der
#: Entwurf entsteht auf dem Standardkonto, und die zweite Zeile des Nachweises
#: sagt das. Die dritte Zeile sagt, ob die Suche das Konto fand (#315):
#: `gefunden`, `fehlt` — Outlook zeigte Konten, aber keins mit dieser
#: Adresse — oder `-`, wenn es gar keine zeigte. Nur `fehlt` belegt, dass es das
#: Konto nicht gibt; `-` ist „nicht geprüft“. `sender` statt `account` ist kein Ausweg: Es wird im neuen Outlook
#: angenommen und zurückgelesen, das Fenster zeigt trotzdem ein anderes Konto.
#:
#: `open` steht **nach** dem Auslesen, und das ist gemessen: Danach meldet
#: Outlook „outgoing message id … kann nicht gelesen werden" (-1728). Wer erst
#: öffnet und dann nachsieht, bekommt einen Fehler statt eines Nachweises.
SKRIPT_OUTLOOK = """\
on run argv
\tset betreff to item 1 of argv
\tset rumpf to item 2 of argv
\tset anListe to my zerlege(item 3 of argv)
\tset kopieListe to my zerlege(item 4 of argv)
\tset blindListe to my zerlege(item 5 of argv)
\tset absender to item 6 of argv
\ttell application "Microsoft Outlook"
\t\tset konto to missing value
\t\tset gesehen to 0
\t\tif absender is not "" then
\t\t\ttry
\t\t\t\trepeat with a in (every exchange account)
\t\t\t\t\tset gesehen to gesehen + 1
\t\t\t\t\tif (email address of a) is absender then set konto to contents of a
\t\t\t\tend repeat
\t\t\tend try
\t\t\ttry
\t\t\t\trepeat with a in (every imap account)
\t\t\t\t\tset gesehen to gesehen + 1
\t\t\t\t\tif (email address of a) is absender then set konto to contents of a
\t\t\t\tend repeat
\t\t\tend try
\t\t\ttry
\t\t\t\trepeat with a in (every pop account)
\t\t\t\t\tset gesehen to gesehen + 1
\t\t\t\t\tif (email address of a) is absender then set konto to contents of a
\t\t\t\tend repeat
\t\t\tend try
\t\tend if
\t\tif konto is missing value then
\t\t\tset entwurf to make new outgoing message with properties {subject:betreff, content:rumpf}
\t\telse
\t\t\tset entwurf to make new outgoing message with properties {account:konto, subject:betreff, content:rumpf}
\t\tend if
\t\trepeat with adresse in anListe
\t\t\tmake new recipient at entwurf with properties {email address:{address:adresse}}
\t\tend repeat
\t\trepeat with adresse in kopieListe
\t\t\tmake new cc recipient at entwurf with properties {email address:{address:adresse}}
\t\tend repeat
\t\trepeat with adresse in blindListe
\t\t\tmake new bcc recipient at entwurf with properties {email address:{address:adresse}}
\t\tend repeat
\t\trepeat with i from 7 to (count of argv)
\t\t\tmake new attachment at entwurf with properties {file:POSIX file (item i of argv)}
\t\tend repeat
\t\tset nachweis to "" & (id of entwurf) & " " & (count of to recipients of entwurf) & " " & (count of cc recipients of entwurf) & " " & (count of bcc recipients of entwurf) & " " & (count of attachments of entwurf)
\t\tset kontoadresse to "-"
\t\ttry
\t\t\tset kontoadresse to email address of (account of entwurf)
\t\tend try
\t\tset suche to "-"
\t\tif konto is not missing value then
\t\t\tset suche to "gefunden"
\t\telse if gesehen > 0 then
\t\t\tset suche to "fehlt"
\t\tend if
\t\tset nachweis to nachweis & linefeed & kontoadresse & linefeed & suche
\tend tell
\treturn nachweis
end run

on zerlege(roh)
\tif roh is "" then return {}
\tset alte to AppleScript's text item delimiters
\tset AppleScript's text item delimiters to ","
\tset teile to text items of roh
\tset AppleScript's text item delimiters to alte
\treturn teile
end zerlege
"""

#: Öffnet die angelegte Nachricht — ein eigener Aufruf, und das ist der Kern
#: der Änderung von #287.
#:
#: Bis dahin stand `open entwurf` im Anlegeskript, also **vor** jeder
#: Entscheidung auf Python-Seite. Fiel `_nachweis_stimmt` danach durch, war das
#: Fenster längst offen — und `cli.py` legte im Rückfall die `.eml` obendrauf.
#: Zwei Fenster aus einem Lauf, das zweite ein Lesefenster ohne Senden-Knopf.
#: Genau das hat der Betreiber am 11.09.2026 gemeldet.
#:
#: Die Kennung kommt als Argument, nicht in den Skripttext: dieselbe Regel wie
#: beim Betreff — ein Wert wird übergeben, nie zusammengesetzt.
#:
#: **Über den Verweis, nicht über `whose` (#305).** `first outgoing message
#: whose id = kennung` durchsucht alle ausgehenden Nachrichten. Im klassischen
#: Outlook mit mehreren synchronisierten Postfächern kam das am 13.09.2026 nicht
#: innerhalb von 90 Sekunden zurück — der Entwurf lag angelegt da, und der
#: Rückfall schob die `.eml` hinterher. `outgoing message id kennung` greift
#: direkt zu und lief in derselben Umgebung ohne Wartezeit.
SKRIPT_OUTLOOK_OEFFNEN = """\
on run argv
\tset kennung to (item 1 of argv) as integer
\ttell application "Microsoft Outlook"
\t\topen (outgoing message id kennung)
\t\tactivate
\tend tell
end run
"""

#: Verwirft eine Nachricht, die die Prüfung nicht bestanden hat.
#:
#: Über die `id`, nicht über eine Schleife: `delete m` in einem
#: `repeat with m in (every outgoing message)` greift nicht — gemessen am
#: 11.09.2026, „geloescht: 0 von 3"; über die Kennung danach „3 von 3".
#:
#: Gelöscht wird ausschließlich, was dieser Lauf Sekunden zuvor selbst angelegt
#: hat und was nie ein Fenster hatte. Eine Nachricht, die jemand sehen konnte,
#: fasst dieses Modul nicht an.
SKRIPT_OUTLOOK_VERWERFEN = """\
on run argv
\tset kennung to (item 1 of argv) as integer
\ttell application "Microsoft Outlook"
\t\tdelete (outgoing message id kennung)
\tend tell
end run
"""


# ── Thunderbird: ein Aufruf statt dreier Skripte (ADR 0049) ─────────────────
#
# Gemessen am 13.10.2026, Thunderbird 154.0 auf macOS:
#
#     thunderbird -compose "from=…,to=…,cc=…,bcc=…,subject='Betreff, mit Komma',
#                           format=html,body='<p>…</p>',attachment='/a.pdf,/b.txt'"
#
# `from=` wählt die Identität — der Absender stimmt damit, was Outlook seit
# #305 nur im klassischen Modus zusagen konnte. Einfache Anführungszeichen
# schützen Kommas im Wert; Umlaute und € kommen an; `format=html` übernimmt den
# Rumpf formatiert. Mehrere Anhänge gehen nur als EIN Wert — ein zweiter
# `attachment=`-Schlüssel wird verworfen, stillschweigend, mit Exit 0.
# `message=<eml>` ist kein Import: Der Rohtext landet im Textkörper.
#
# Läuft Thunderbird, reicht der Aufruf den Auftrag an die laufende Instanz
# weiter und kehrt sofort mit Exit 0 zurück. **Exit 0 heißt „angenommen“, nicht
# „Fenster offen“**: Thunderbird meldet nichts zurück, es gibt keine Kennung
# und keine Zählung am fertigen Objekt. Was sich prüfen lässt, liegt auf dieser
# Seite der Grenze — ob die Zeile alles trägt, was sie tragen soll
# (`_compose_stimmt`), gelesen so, wie Thunderbird sie liest.

#: Das Binary, wo macOS es hinlegt. Nicht über `NSWorkspace` wie bei Outlook:
#: Gebraucht wird das Binary selbst, nicht das Bündel, und eine zweite
#: `osascript`-Frage je Lauf wäre der Preis für Rechner, die ihre Programme
#: woanders halten — die deckt `which` ab, wenn das Binary im PATH liegt.
THUNDERBIRD_MACOS = "/Applications/Thunderbird.app/Contents/MacOS/thunderbird"

#: Die Schlüssel, die `-compose` versteht und die hier gesetzt werden. Eine
#: feste Liste, kein Durchreichen: Ein Schlüssel, der sendet, gibt es dort
#: nicht — und käme es ihn, stünde er nicht hier (ADR 0034).
COMPOSE_SCHLUESSEL = ("from", "to", "cc", "bcc", "subject", "format", "body", "attachment")

#: Wie lang die `-compose`-Zeile sein darf, in Byte. `getconf ARG_MAX` meldet
#: auf macOS 1 048 576 (gemessen 13.10.2026), und darin müssen Umgebung, Pfad
#: und die übrigen Argumente mitfahren. Ein Logo wird als Data-URI Teil der
#: Zeile (`eingebettet`); ein großes sprengt sie, und der Fehler des Systems
#: hieße nur „Argument list too long“. Deshalb vorher zählen und sagen, wie
#: viel es ist.
COMPOSE_GRENZE_BYTE = 900_000


def eingebettet(html: str, inline) -> str:
    """Jedes `<img src="cid:…">` wird zur Data-URI aus dem zugehörigen Teil.

    `-compose body=` übergibt nur den Rumpf; die `multipart/related`-Teile der
    `.eml`, auf die `cid:` zeigt, gibt es auf diesem Weg nicht. Gemessen am
    13.10.2026: Das Logo der Signatur erschien in Thunderbird als kaputtes Bild
    mit Alt-Text. Thunderbird zeigt Data-URIs im Editor an und macht beim
    Senden Anhänge daraus (erwartet; gemessen ist die Anzeige).

    `inline` kommt aus `eml.entwurfsfelder`: `(kennung, mime, bytes)` je Teil —
    die Bytes aus der geschriebenen Datei, nicht neu von Platte gelesen.
    Ersetzt wird nur der Verweis selbst, und nur bis zum schließenden
    Anführungszeichen: `cid:logo` darf `cid:logo2` nicht treffen.
    """
    for kennung, mime, daten in inline:
        uri = f"data:{mime};base64,{base64.b64encode(daten).decode('ascii')}"
        html = re.sub(rf"cid:{re.escape(kennung)}(?=[\"'])", lambda _: uri, html)
    return html


def rumpf_fuer_compose(html: str) -> str:
    """Nur der Inhalt von `<body>`, auf einer Zeile — so, wie `body=` es verträgt.

    Gemessen am 13.10.2026 (zweiter Lauf, echte Entwürfe in Thunderbird 154):
    **Thunderbird macht aus jedem Zeilenumbruch im `body=`-Wert einen
    Zeilenumbruch im Entwurf.** Zwei Folgen, beide gesehen: Ein Tag, das über
    zwei Zeilen geht (`<table …\n style="…">`), wird an der ersten Zeile
    abgeschnitten, und der Rest steht als sichtbarer Text im Entwurf —
    `style="border-collapse: …">` zwischen Grußformel und Signatur. Und die
    Hülle der Datei — `<!DOCTYPE>`, `<head>`, `<meta>`, `<style>` — wird zu rund
    zehn Leerzeilen über dem ersten Absatz.

    Deshalb: nur der Inhalt von `<body>`, und jeder Umbruch samt Einrückung
    wird ein Leerzeichen. HTML liest ihn ohnehin so — zwischen Blöcken ohne
    Bedeutung, im Tag der Abstand zwischen Attributen, im Text ein Wortabstand.
    Der Emitter setzt kein `<pre>`, in dem ein Umbruch etwas hieße; das
    `<style>` der Hülle ist das einzige, was Umbrüche im Text trägt, und es
    fällt mit der Hülle weg. Der `style` des `<body>` (Schrift, Größe, Farbe)
    wandert auf ein umhüllendes `<div>`, damit der Entwurf nicht die Schrift
    der Datei verliert.
    """
    treffer = re.search(r"<body(?P<attribute>[^>]*)>(?P<inhalt>.*?)</body>", html,
                        re.S | re.I)
    if treffer:
        inhalt = treffer.group("inhalt").strip()
        stil = re.search(r'style="([^"]*)"', treffer.group("attribute"))
        if stil:
            inhalt = f'<div style="{stil.group(1)}">{inhalt}</div>'
    else:
        inhalt = html
    return re.sub(r"[ \t]*\n[ \t]*", " ", inhalt).strip()


class _Tagzaehler(HTMLParser):
    """Zählt Start-Tags und sammelt den Text — für `_rumpf_stimmt`."""

    def __init__(self):
        super().__init__()
        self.tags = 0
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags += 1

    def handle_startendtag(self, tag, attrs):
        self.tags += 1

    def handle_data(self, daten):
        self.text.append(daten)


def _rumpf_stimmt(rumpf: str) -> str | None:
    """Verträgt `body=` diesen Rumpf? Sonst der Grund — vor dem Aufruf.

    Drei Dinge, je eines pro gemessenem Fehler: keine Hülle und kein führender
    Leerraum (die Leerzeilen), kein Zeilenumbruch (das abgeschnittene Tag; eine
    Data-URI mit Umbrüchen fiele hier ebenfalls auf), und jedes `<tag` kommt
    als Tag beim Parser an — kein `attribut="…"` steht als Text da.
    """
    fehlt = []
    if rumpf != rumpf.strip():
        fehlt.append("führender oder abschließender Leerraum")
    if re.match(r"\s*<(!doctype|html|head|body)\b", rumpf, re.I):
        fehlt.append("die Hülle der Datei steht noch im Rumpf")
    if "\n" in rumpf:
        fehlt.append("ein Zeilenumbruch — Thunderbird macht daraus eine Zeile")
    zaehler = _Tagzaehler()
    zaehler.feed(rumpf)
    zaehler.close()
    gemeint = len(re.findall(r"<[a-zA-Z]", rumpf))
    if zaehler.tags != gemeint:
        fehlt.append(f"{gemeint} Tags geschrieben, {zaehler.tags} beim Parser angekommen")
    text = "".join(zaehler.text)
    if re.search(r'[a-zA-Z-]+="', text):
        fehlt.append("ein Attribut steht als Text im Rumpf")
    if not fehlt:
        return None
    return "der Rumpf verträgt `body=` nicht — " + ", ".join(fehlt)


def _eingebettet_stimmt(html: str, inline) -> str | None:
    """Ist kein `cid:` übrig, und trägt der Rumpf jedes Bild — mit seinem Typ?

    Vor dem Aufruf, wie `_compose_stimmt`: Danach kommt nichts zurück, und ein
    kaputtes Bild im Entwurf sieht ein Exit-Code nie.
    """
    fehlt = []
    if "cid:" in html:
        fehlt.append("ein cid:-Verweis bleibt im Rumpf")
    for kennung, mime, daten in inline:
        uri = f"data:{mime};base64,{base64.b64encode(daten).decode('ascii')}"
        if uri not in html:
            fehlt.append(f"Bild {kennung} fehlt als data:{mime}")
    if not fehlt:
        return None
    return "der Rumpf trägt die Bilder nicht — " + ", ".join(fehlt)


# ── Die Signatur der Identität (ADR 0050) ────────────────────────────────────
#
# Thunderbird setzt beim Öffnen des Entwurfs die Signatur der Identität unter
# den Rumpf, den `body=` mitbringt — und der trägt schon die aus dem Profil.
# Bis ADR 0050 hieß die Reparatur „Kontosignatur in Thunderbird leer lassen“.
# Wer seine Identitäten aber aus derselben Datei bestückt wie das Profil, will
# sie dort stehen haben: Dann kommt die Signatur aus Thunderbird, und die aus
# dem Profil bleibt aus dem Rumpf des Entwurfs. Die `.eml` behält sie.
#
# Gelesen wird nur, nie geschrieben, und gestartet wird nichts: `profiles.ini`,
# `prefs.js` und `user.js` des Standardprofils.

#: Wo Thunderbird auf macOS seine Profile hält. Eine Modulkonstante, damit die
#: Tests sie auf ein Attrappenverzeichnis umlegen können — keine Prüfung soll
#: davon abhängen, welches Thunderbird auf dem Läufer eingerichtet ist.
THUNDERBIRD_ORDNER = Path.home() / "Library" / "Thunderbird"

_PREF_ZEILE = re.compile(r'^\s*user_pref\(\s*("(?:[^"\\]|\\.)*")\s*,\s*(.+?)\s*\)\s*;\s*$')


class Signaturlage(NamedTuple):
    """Ob Thunderbird für die Absenderadresse selbst eine Signatur setzt.

    `zustand` ist einer von drei Werten — und der dritte ist kein „nein“:

    * `"thunderbird"` — die Identität trägt eine; `quelle` nennt Datei oder
      Signaturtext.
    * `"keine"` — die Identität ist gefunden und trägt keine.
    * `"unbestimmt"` — kein Profil, keine oder mehrdeutige Identität, eine
      Signaturdatei, die sich nicht lesen lässt; `grund` sagt, was.
    """

    zustand: str
    identitaet: str = ""
    adresse: str = ""
    quelle: str = ""
    grund: str = ""


def _unbestimmt(grund: str) -> Signaturlage:
    return Signaturlage("unbestimmt", grund=grund)


def thunderbird_standardprofil(ordner: Path) -> Path | None:
    """Das Profil, mit dem Thunderbird startet — aus `profiles.ini`, oder None.

    `[Install…] Default=` geht vor `[Profile…] Default=1`: Seit Thunderbird 68
    hat jede Installation ihr eigenes Standardprofil, und das `Default=1` am
    Profil bleibt oft von früher stehen. Beim Betreiber zeigt es am 15.10.2026
    auf ein anderes Profil als die Installation. Mehrere Installationen mit
    verschiedenen Profilen sind nicht zu entscheiden — None.
    """
    import configparser

    ini = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        if not ini.read(Path(ordner) / "profiles.ini", encoding="utf-8"):
            return None
    except configparser.Error:
        return None

    def aufgeloest(pfad: str, relativ: bool = True) -> Path:
        return Path(ordner) / pfad if relativ and not Path(pfad).is_absolute() else Path(pfad)

    installiert = {ini[s]["default"] for s in ini.sections()
                   if s.startswith("Install") and ini[s].get("default")}
    if len(installiert) == 1:
        return aufgeloest(installiert.pop())
    if installiert:
        return None
    profile = [ini[s] for s in ini.sections() if s.startswith("Profile") and ini[s].get("path")]
    gewaehlt = [p for p in profile if p.get("default") == "1"]
    if len(gewaehlt) != 1:
        gewaehlt = profile if len(profile) == 1 else []
    if not gewaehlt:
        return None
    return aufgeloest(gewaehlt[0]["path"], gewaehlt[0].get("isrelative", "1") == "1")


def thunderbird_einstellungen(profil: Path) -> dict:
    """`prefs.js`, dann `user.js` — der zweite gewinnt, wie in Thunderbird.

    Thunderbird liest `user.js` bei jedem Start nach `prefs.js` und übernimmt
    dessen Werte. Wer seine Identitäten über `user.js` pflegt, steht deshalb
    dort richtig, auch wenn `prefs.js` noch den alten Wert führt.

    Jede Zeile `user_pref("name", wert);` für sich; Wert und Name sind
    JSON-kompatibel geschrieben. Was sich nicht lesen lässt, fällt weg — eine
    Zeile, die Thunderbird selbst nicht verstünde, ist kein Grund, die
    übrigen zu verwerfen.
    """
    import json

    werte: dict = {}
    for name in ("prefs.js", "user.js"):
        try:
            text = (Path(profil) / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for zeile in text.splitlines():
            treffer = _PREF_ZEILE.match(zeile)
            if not treffer:
                continue
            try:
                werte[json.loads(treffer.group(1))] = json.loads(treffer.group(2))
            except ValueError:
                continue
    return werte


def _identitaeten(werte: dict) -> list[str]:
    """Die Identitäten der eingerichteten Konten, in deren Reihenfolge.

    Über `mail.accountmanager.accounts`, nicht über jede `mail.identity.*`-Zeile:
    Thunderbird wählt mit `from=` nur unter Identitäten, die zu einem Konto
    gehören. Fehlt die Kontoliste, zählen alle, die eine Adresse tragen.
    """
    konten = [k.strip() for k in str(werte.get("mail.accountmanager.accounts") or "").split(",")
              if k.strip()]
    if not konten:
        return sorted({n.split(".")[2] for n in werte
                       if n.startswith("mail.identity.") and n.endswith(".useremail")})
    ids: list[str] = []
    for konto in konten:
        for kennung in str(werte.get(f"mail.account.{konto}.identities") or "").split(","):
            if kennung.strip() and kennung.strip() not in ids:
                ids.append(kennung.strip())
    return ids


def _signatur_der_identitaet(werte: dict, kennung: str, adresse: str) -> Signaturlage:
    """Was Thunderbird für diese eine Identität unter einen neuen Entwurf setzt."""
    vorn = f"mail.identity.{kennung}."
    if werte.get(vorn + "attach_signature") is True:
        # Mit `attach_signature` nimmt Thunderbird die Datei und nicht den
        # Signaturtext. Eine Datei, die sich nicht lesen lässt, ist nicht
        # „keine Signatur“, sondern unbekannt — was Thunderbird dann einsetzt,
        # ist nicht gemessen.
        datei = str(werte.get(vorn + "sig_file") or "")
        if not datei:
            return _unbestimmt(f"{kennung} soll eine Signaturdatei anhängen, nennt aber keine")
        try:
            inhalt = Path(datei).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return _unbestimmt(f"die Signaturdatei von {kennung} ist nicht lesbar: {datei}")
        if inhalt.strip():
            return Signaturlage("thunderbird", kennung, adresse, datei)
        return Signaturlage("keine", kennung, adresse)
    if str(werte.get(vorn + "htmlSigText") or "").strip():
        return Signaturlage("thunderbird", kennung, adresse, "Signaturtext der Identität")
    return Signaturlage("keine", kennung, adresse)


def kontosignatur(adresse: str, ordner: Path | None = None) -> Signaturlage:
    """Setzt Thunderbird für diese Absenderadresse selbst eine Signatur?

    Liest das Standardprofil unter `ordner` (Vorgabe `THUNDERBIRD_ORDNER`),
    schreibt nichts und startet nichts. Mehrere Identitäten mit derselben
    Adresse sind nur dann eindeutig, wenn sie dasselbe sagen — welche
    Thunderbird mit `from=` nimmt, ist nicht gemessen.
    """
    adresse = (adresse or "").strip()
    if not adresse:
        return _unbestimmt("ohne Absenderadresse keine Identität")
    ordner = THUNDERBIRD_ORDNER if ordner is None else Path(ordner)
    profil = thunderbird_standardprofil(ordner)
    if profil is None or not profil.is_dir():
        return _unbestimmt(f"kein Standardprofil unter {ordner}")
    werte = thunderbird_einstellungen(profil)
    treffer = [k for k in _identitaeten(werte)
               if str(werte.get(f"mail.identity.{k}.useremail") or "").strip().lower()
               == adresse.lower()]
    if not treffer:
        return _unbestimmt(f"keine Identität mit {adresse} im Profil {profil.name}")
    lagen = [_signatur_der_identitaet(werte, k, adresse) for k in treffer]
    if len({(lage.zustand, lage.quelle) for lage in lagen}) > 1:
        return _unbestimmt(f"{len(treffer)} Identitäten mit {adresse}, nicht mit derselben "
                           "Signatur: " + ", ".join(treffer))
    return lagen[0]


def thunderbird_ordner(adresse: str, art: str, ordner: Path | None = None) -> str | None:
    """Der IMAP-Name des Entwürfe- oder Gesendet-Ordners dieser Identität — oder None.

    `art` ist `draft_folder` oder `fcc_folder`. Gelesen wird dasselbe
    Standardprofil wie für die Signatur (ADR 0050), nur lesend. None heißt
    „Thunderbird sagt nichts Verwertbares“: kein Profil, keine oder
    mehrdeutige Identität, kein Eintrag — oder ein Ordner in einem **anderen**
    Konto. Dort ist die Sitzung nicht angemeldet; der Aufrufer fragt dann den
    Server nach dem Kennzeichen (`\\Drafts`, `\\Sent`).
    """
    from falzmarke import postfach

    adresse = (adresse or "").strip().lower()
    if not adresse:
        return None
    ordner = THUNDERBIRD_ORDNER if ordner is None else Path(ordner)
    profil = thunderbird_standardprofil(ordner)
    if profil is None or not profil.is_dir():
        return None
    werte = thunderbird_einstellungen(profil)
    gefunden = set()
    for kennung in _identitaeten(werte):
        if str(werte.get(f"mail.identity.{kennung}.useremail") or "").strip().lower() != adresse:
            continue
        gelesen = postfach.ordner_aus_url(str(werte.get(f"mail.identity.{kennung}.{art}") or ""))
        if gelesen is None or gelesen[0].strip().lower() != adresse:
            return None
        gefunden.add(gelesen[1])
    return gefunden.pop() if len(gefunden) == 1 else None


def ohne_signatur(html: str, unterschrift: str) -> str | None:
    """Der HTML-Teil ohne das Signaturstück — oder None, wenn es nicht genau einmal dasteht.

    Gesucht wird das Stück, das `eml.signatur_html` geliefert hat, mit dem
    Zeilenumbruch, mit dem `eml.htmlteil` es anfügt. Kein Muster: Steht es nicht
    genau einmal da, wird nichts entfernt — lieber die Signatur zweimal im
    Entwurf als ein Stück Nachricht zu wenig.
    """
    if not unterschrift:
        return html
    stueck = "\n" + unterschrift
    if html.count(stueck) != 1:
        return None
    return html.replace(stueck, "", 1)


def _leerraum(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _ohne_signatur_stimmt(rumpf_mit: str, rumpf_ohne: str, signatur_rumpf: str) -> str | None:
    """Fehlt dem Rumpf genau die Signatur — und sonst nichts? Sonst der Grund.

    Gemessen an den fertigen `body=`-Werten, nicht am HTML der Datei: der mit
    Signatur, wie er vor ADR 0050 gesendet wurde, der ohne, wie er jetzt
    gesendet wird, und die Signatur durch dieselbe Aufbereitung geschickt.
    Schneidet `ohne_signatur` zu viel ab — die Grußformel, einen Absatz —, zu
    wenig, oder an der falschen Stelle, fällt es hier auf, bevor ein Fenster
    aufgeht.
    """
    fehlt = []
    if not signatur_rumpf:
        fehlt.append("die Signatur ist nach der Aufbereitung leer")
    elif rumpf_mit.count(signatur_rumpf) != 1:
        fehlt.append(f"die Signatur steht {rumpf_mit.count(signatur_rumpf)}-mal im Rumpf "
                     "mit Signatur")
    elif signatur_rumpf in rumpf_ohne:
        fehlt.append("die Signatur steht noch im Rumpf")
    elif _leerraum(rumpf_mit.replace(signatur_rumpf, " ", 1)) != _leerraum(rumpf_ohne):
        fehlt.append("der Rumpf verliert mehr als die Signatur")
    if not fehlt:
        return None
    return "die Signatur aus dem Profil ließ sich nicht sauber herausnehmen — " + ", ".join(fehlt)


def anhang_paare(anhangpfade: list[str]) -> list[tuple[str, str]]:
    """Die Anhänge als Schlüssel-Wert-Paare: **genau eins**, alle Pfade darin.

    Die naheliegende Fassung — ein `attachment=` je Datei — verliert ab dem
    zweiten Anhang alles außer dem ersten, mit Exit 0 (gemessen 13.10.2026).
    Eine eigene Funktion, damit die Gegenprobe in `tests/test_gegenbeweis.py`
    genau diese eine Stelle gegen die naheliegende Fassung tauschen kann — und
    `_compose_stimmt` dann anschlagen muss.
    """
    return [("attachment", ",".join(anhangpfade))] if anhangpfade else []


def thunderbird_binaer(existiert=os.path.isfile, which=shutil.which) -> str | None:
    """Wo Thunderbird liegt — oder None. Startet nichts, fragt nur das Dateisystem.

    `existiert` und `which` sind Einstiegspunkte für die Prüfung: Ohne sie
    hinge jeder Test davon ab, was auf dem Läufer gerade installiert ist.
    """
    if existiert(THUNDERBIRD_MACOS):
        return THUNDERBIRD_MACOS
    return which("thunderbird") or None


def _compose_wert(wert: str) -> str:
    """Ein Wert für die `-compose`-Zeile, in einfachen Anführungszeichen.

    Jeder Wert wird zitiert, nicht nur der mit Komma: Einen unzitierten Wert
    liest Thunderbird wie eine URL (`%20` wird ein Leerzeichen), einen
    zitierten wörtlich. „100%ig“ bliebe sonst nicht, was es ist.

    Ein einfaches Anführungszeichen **im** Wert wird zum Apostroph ’. Ob
    Thunderbird ein `'` im Wert übersteht, ist nicht gemessen (am 13.10.2026
    offen geblieben); sicher ist nur, dass `'` vor einem Komma den Wert
    schließt. Statt zu raten, wird das Zeichen ersetzt — in deutschem Text ist
    ’ ohnehin das richtige Zeichen, und falzmarkes eigener HTML-Emitter setzt
    kein `'` (gemessen an `examples/email/email-mahnung.md`: 0 von 68
    Anführungszeichen). Adressen laufen nicht hier durch: Dort wäre ein `'`
    Teil der Adresse, und es kann nach RFC 5322 nie vor dem Komma stehen.
    """
    return "'" + wert.replace("'", "’") + "'"


def compose_argumente(felder: Mapping, anhangpfade: list[str]) -> list[str]:
    """`["-compose", "<zeile>"]` aus den Feldern — rein und ohne Seiteneffekt.

    Wirft `ValueError`, wo die Zeile nicht tragen kann, was sie soll:

    * **ohne Absender.** `from=` wählt die Identität; ohne sie nähme
      Thunderbird seine Vorgabe — der Fehler aus #305 in einem anderen Programm.
    * **Anhangpfad mit Komma.** Thunderbird trennt die Anhänge am Komma, und
      Anführungszeichen helfen innerhalb des Werts nicht. Aus einem Pfad würden
      zwei, die es nicht gibt, ohne Meldung.

    Der Aufrufer macht aus der Ausnahme einen Grund; nach außen wird nichts
    geworfen (ADR 0038, Punkt 4).
    """
    absender = str(felder.get("absender") or "").strip()
    if not absender:
        raise ValueError("ohne Absender kein Entwurf in Thunderbird — `from=` wählt dort "
                         "die Identität, und ohne ihn nähme es die Vorgabe (#305)")
    for pfad in anhangpfade:
        if "," in pfad:
            raise ValueError(f"Anhangpfad mit Komma: „{pfad}“ — Thunderbird trennt die "
                             "Anhänge am Komma; die Datei ohne Komma benennen")
    html = str(felder.get("html") or "")
    paare = [
        ("from", absender),
        ("to", ",".join(felder.get("an") or [])),
        ("cc", ",".join(felder.get("kopie") or [])),
        ("bcc", ",".join(felder.get("blindkopie") or [])),
        ("subject", str(felder.get("betreff") or "")),
        ("format", "html" if html else "text"),
        ("body", html),
        *anhang_paare(anhangpfade),
    ]
    zeile = ",".join(f"{schluessel}={_compose_wert(wert)}"
                     for schluessel, wert in paare if wert)
    return ["-compose", zeile]


def compose_zerlegen(zeile: str) -> dict[str, str]:
    """Liest eine `-compose`-Zeile so, wie Thunderbird sie liest.

    Nachgebaut aus dem, was am 13.10.2026 gemessen wurde — Anführungszeichen
    schützen Kommas, der zweite gleiche Schlüssel wird verworfen — und aus der
    Leseroutine `GetArgs` im Compose-Fenster von Thunderbird: Ein Wert ist
    zitiert, wenn hinter dem `=` ein `'` oder `"` steht, und das Zitat endet
    erst an demselben Zeichen vor einem Komma oder am Ende. Unzitierte Werte
    werden wie eine URL dekodiert. Die Paare werden von hinten gelesen, der
    erste gewinnt.

    Ein Prüfmittel auf **dieser** Seite der Grenze: Es belegt, dass die Zeile
    alles trägt — nicht, was Thunderbird daraus macht.
    """
    from urllib.parse import unquote

    trenner = "\x01"
    umgebaut: list[str] = []
    zitat = ""
    vorher = ""
    for i, zeichen in enumerate(zeile):
        naechstes = zeile[i + 1] if i + 1 < len(zeile) else ""
        if zitat and zeichen == zitat and naechstes in (",", ""):
            zitat = ""
            umgebaut.append(zeichen)
        elif zeichen in ("'", '"') and vorher == "=" and not zitat:
            zitat = zeichen
            umgebaut.append(zeichen)
        elif zeichen == "," and not zitat:
            umgebaut.append(trenner)
        else:
            umgebaut.append(zeichen)
        vorher = zeichen
    werte: dict[str, str] = {}
    for paar in reversed("".join(umgebaut).split(trenner)):
        if "=" not in paar:
            continue
        name, wert = paar.split("=", 1)
        if len(wert) >= 2 and wert[0] == "'" and wert[-1] == "'":
            wert = wert[1:-1]
        else:
            wert = unquote(wert)
        werte[name] = wert
    return werte


def _compose_stimmt(zeile: str, felder: Mapping, anhangpfade: list[str]) -> str | None:
    """Trägt die Zeile, gelesen wie Thunderbird sie liest, was sie tragen soll?

    Das Gegenstück zu `_nachweis_stimmt` beim Outlook-Weg — nur dass hier vor
    dem Aufruf gemessen wird, weil danach nichts zurückkommt. Ein verschluckter
    Anhang fällt so auf, bevor ein Fenster aufgeht.
    """
    gelesen = compose_zerlegen(zeile)
    fehlt = []
    if gelesen.get("from", "") != str(felder.get("absender") or "").strip():
        fehlt.append("Absender")
    for schluessel, name, liste in (("to", "Empfänger", felder.get("an")),
                                    ("cc", "Kopien", felder.get("kopie")),
                                    ("bcc", "Blindkopien", felder.get("blindkopie"))):
        ist = [a for a in gelesen.get(schluessel, "").split(",") if a]
        if ist != list(liste or []):
            fehlt.append(f"{name}: {len(ist)} statt {len(liste or [])}")
    anhaenge = [a for a in gelesen.get("attachment", "").split(",") if a]
    if len(anhaenge) != len(anhangpfade):
        fehlt.append(f"Anhänge: {len(anhaenge)} statt {len(anhangpfade)}")
    elif anhaenge != list(anhangpfade):
        fehlt.append("Anhänge: nicht die vorgegebenen Pfade")
    html = str(felder.get("html") or "")
    if gelesen.get("format") != ("html" if html else "text"):
        fehlt.append("Format")
    if html and gelesen.get("body") != html.replace("'", "’"):
        fehlt.append("Rumpf")
    if not fehlt:
        return None
    return "die -compose-Zeile trägt nicht, was sie tragen soll — " + ", ".join(fehlt)


class Entwurfsprogramm(NamedTuple):
    """Ein Mailprogramm und der Weg, auf dem es einen Entwurf annimmt.

    Ein NamedTuple und keine Dataclass: Der Zugriff über den Index bleibt
    erhalten, und die Felder haben trotzdem Namen.

    Zwei Wege: `applescript` — drei Skripte, und der Entwurf wird am fertigen
    Objekt nachgezählt — und `compose` — ein Aufruf des Binarys, Exit 0 heißt
    „angenommen“. Beim zweiten Weg sind die Skriptfelder leer.
    """

    kennung: str
    name: str
    anlegen: str
    oeffnen: str
    verwerfen: str
    weg: str = "applescript"
    #: Das Wort für `--programm`.
    schluessel: str = ""
    #: Ob das Programm ohne `--programm` in Frage kommt.
    vorgabe: bool = False
    #: Nur `compose`: das gefundene Binary, von `entwurfsweg()` eingesetzt.
    pfad: str = ""


#: Programme, die hier einen Entwurf annehmen — in der Reihenfolge, in der sie
#: ohne `--programm` befragt werden.
#:
#: **Thunderbird ist die Vorgabe** (13.10.2026, Thunderbird 154.0: Absender,
#: Betreff mit Komma, HTML-Rumpf mit Umlauten und zwei Anhänge im Fenster
#: gesehen). **Outlook kommt nur auf Wahl.** Es ist auf dem Rechner des
#: Betreibers installiert, aber ohne Lizenz — und das neue Outlook zeigt
#: AppleScript kein Konto (#305). „fehlt“ träfe also nie zu, und ohne die Wahl
#: landete jeder Entwurf dort, sobald Thunderbird fehlt. Der Weg selbst ist
#: gemessen (08.09.2026, Outlook für Mac 16.112.1 — Betreff, ein Empfänger und
#: ein Anhang aus dem erzeugten Objekt zurückgelesen) und bleibt, wie er ist.
#:
#: Für Apple Mail gibt es keinen: Dort nimmt `content` einer ausgehenden
#: Nachricht keinen HTML-Rumpf an, und eine Nachricht, die ihre Auszeichnung
#: unterwegs verliert, wäre schlechter als die Datei.
ENTWURFSPROGRAMME = (
    Entwurfsprogramm("thunderbird", "Thunderbird", "", "", "",
                     weg="compose", schluessel="thunderbird", vorgabe=True),
    Entwurfsprogramm("com.microsoft.Outlook", "Microsoft Outlook",
                     SKRIPT_OUTLOOK, SKRIPT_OUTLOOK_OEFFNEN,
                     SKRIPT_OUTLOOK_VERWERFEN, schluessel="outlook"),
)


def entwurfsweg(plattform: str = sys.platform, *, laufen=subprocess.run,
                wahl: str | None = None,
                binaer=thunderbird_binaer) -> Entwurfsprogramm | None:
    """Welches Programm hier einen Entwurf annimmt — als Angabe, nicht als Tat.

    `wahl` ist das Wort aus `--programm`. Ohne Wahl kommen nur die Programme
    mit `vorgabe` in Frage — also Thunderbird; Outlook braucht die Wahl, aus
    dem Grund, der bei `ENTWURFSPROGRAMME` steht. Ein Wort, das kein Programm
    trägt, ist ein Programmierfehler, kein Grund: `argparse` lässt es nicht
    bis hierher.

    Für Thunderbird wird kein Prozess gestartet — `binaer` sieht nur ins
    Dateisystem (`thunderbird_binaer`). Für Outlook wird das System gefragt,
    nicht der Ordner: `NSWorkspace` löst eine Kennung über die Datenbank auf,
    die auch der Finder benutzt, und **startet das Programm nicht**.

    Bis #305 stand hier `path to application id`. Am 13.09.2026 hing genau diese
    Frage über 120 Sekunden, während Outlook selbst nach 12 Sekunden antwortete —
    sie geht offenbar doch über das laufende Programm. `NSWorkspace` kam in
    derselben Minute nach 5 Sekunden zurück. Ein fest verdrahteter Pfad unter
    `/Applications` ginge daran vorbei, sobald jemand seine Programme woanders
    hält.

    Nur macOS. Für Windows gibt es einen Weg über COM und für Linux keinen;
    beide sind ungemessen und werden deshalb nicht behauptet (#108).
    """
    bekannt = {programm.schluessel for programm in ENTWURFSPROGRAMME}
    if wahl is not None and wahl not in bekannt:
        raise ValueError(f"kein Entwurfsprogramm „{wahl}“ — bekannt: "
                         + ", ".join(sorted(bekannt)))
    if not plattform.startswith("darwin"):
        return None
    for programm in ENTWURFSPROGRAMME:
        if (wahl is None and not programm.vorgabe) or (wahl is not None
                                                       and programm.schluessel != wahl):
            continue
        if programm.weg == "compose":
            pfad = binaer()
            if pfad:
                return programm._replace(pfad=pfad)
            continue
        frage = ('ObjC.import("AppKit"); $.NSWorkspace.sharedWorkspace'
                 f'.URLForApplicationWithBundleIdentifier("{programm.kennung}").path.js')
        lauf = _lauf(["osascript", "-l", "JavaScript", "-e", frage], FRIST_S, laufen)
        if lauf.returncode == 0 and lauf.stdout.strip():
            return programm
    return None


def entwurfsargumente(felder: Mapping, anhangpfade: list[str]) -> list[str]:
    """Die Argumentliste für das Steuerskript — rein und ohne Seiteneffekt.

    Die Adressen werden mit Komma verbunden, und das ist hier gefahrlos: In
    `felder` steht die reine Adresse ohne Anzeigenamen (`eml.entwurfsfelder`),
    und ein Komma darf darin nach RFC 5322 nicht vorkommen.
    """
    return [
        str(felder.get("betreff") or ""),
        str(felder.get("html") or ""),
        ",".join(felder.get("an") or []),
        ",".join(felder.get("kopie") or []),
        ",".join(felder.get("blindkopie") or []),
        str(felder.get("absender") or ""),
        *anhangpfade,
    ]


class Entwurfslage(NamedTuple):
    """Was aus einem Entwurfsversuch wurde — mit einem dritten Zustand.

    `programm` gesetzt heißt: Der Entwurf steht offen im Mailprogramm.
    `programm is None` heißt: Er steht nicht — `grund` sagt, warum.

    `ungewiss` ist der Zustand, den es bis #287 nicht gab und der den
    gemeldeten Fehler erst möglich machte: Das Steuerskript ist nicht
    zurückgekehrt, also weiß niemand, ob eine Nachricht entstand und ob ein
    Fenster offen ist. Wer in diesem Fall die `.eml` nachschiebt, bekommt
    womöglich ein zweites Fenster — und das zweite ist ein Lesefenster ohne
    Senden-Knopf. „Nicht geprüft" ist eben nicht dasselbe wie „nichts da".
    """

    programm: str | None
    grund: str
    ungewiss: bool = False
    #: Die Adresse des Kontos, auf dem der Entwurf liegt — so, wie das Skript sie
    #: am fertigen Objekt gelesen hat. `None`, wenn das Programm keins nennt
    #: (#305). Ein Beleg nur im klassischen Outlook; siehe `SKRIPT_OUTLOOK`.
    konto: str | None = None
    #: Ob die Suche ein Konto zur Adresse des Profils fand: `"gefunden"`,
    #: `"fehlt"` oder `None` — nicht geprüft, weil Outlook keine Konten zeigte
    #: oder das Skript die Zeile nicht liefert (#315).
    suche: str | None = None
    #: Ob Empfänger, Kopien, Blindkopien und Anhänge am fertigen Objekt
    #: nachgezählt wurden (Outlook) — oder das Programm den Auftrag nur
    #: angenommen hat (Thunderbird, Exit 0; ADR 0049). `False` heißt: Was im
    #: Fenster steht, hat niemand gemessen, und der Aufrufer sagt das.
    nachgezaehlt: bool = True
    #: Der Ordner mit den Anhängen, wenn das Programm sie erst später liest
    #: (Thunderbird: beim Senden oder Speichern). `None`, wenn keiner angelegt
    #: wurde oder er schon wieder weg ist.
    ablage: str | None = None
    #: Nur Thunderbird: ob die Identität selbst eine Signatur setzt und welche
    #: dann im Entwurf steht (ADR 0050). `None` auf jedem anderen Weg.
    signatur: Signaturlage | None = None
    #: Der Entwurf liegt im Postfach statt in einem Fenster (ADR 0051) — wo,
    #: und was dort nachgelesen wurde. `None` auf jedem anderen Weg.
    postfach: "Postfachablage | None" = None
    #: Warum es kein Postfach-Entwurf wurde, wenn es einer hätte werden können
    #: (Proxy aus, Konto unbekannt, abgeschaltet). Leer, wenn es keiner sein sollte.
    postfach_grund: str = ""
    #: Ein Entwurf an dieselben Empfänger mit demselben Betreff liegt schon im
    #: Postfach — Zeit und Betreff. Dann wurde nichts angelegt (ADR 0051).
    schon_da: str = ""
    #: Die UID dieses liegenden Entwurfs, damit die Brücke ihn öffnen kann.
    schon_da_uid: str = ""
    #: Ob der Postfach-Entwurf über die Entwurfsbrücke als Fenster aufging
    #: (ADR 0052) — eine `bruecke.Oeffnung`. `None`, wenn es nicht versucht
    #: wurde: kein Postfach-Entwurf, oder einer, dessen Lage ungewiss ist.
    fenster: object | None = None
    #: Warum der Postfach-Entwurf nicht ins Entwurfsbuch kam (ADR 0053). Leer,
    #: wenn er drinsteht oder es keiner war. Dann weiß `falzmarke status` später
    #: nicht, was im Entwurf stand — das soll der Aufrufer sagen.
    buch_grund: str = ""


class Postfachablage(NamedTuple):
    """Ein Entwurf, der per `APPEND` im Postfach liegt — und was nachgezählt ist."""

    adresse: str
    #: Der Ordner im Klartext („Entwürfe“), wie Thunderbird ihn zeigt.
    ordner: str
    betreff: str
    #: Passende Entwürfe (Empfänger und Betreff) vor und nach dem Ablegen.
    vorher: int
    nachher: int
    #: Ob der abgelegte Entwurf `In-Reply-To` trägt — `None`, wenn die Quelle
    #: keine Antwort ist. Nachgelesen am Server, nicht angenommen.
    bezug: bool | None
    #: Ob er die Fassungs-Kopfzeile trägt.
    fassung: bool | None
    #: Die UID des abgelegten Entwurfs im Ordner — die Kennung, mit der die
    #: Entwurfsbrücke ihn öffnet (ADR 0052). Leer, wenn sie nicht feststeht.
    uid: str = ""


#: Zeitlimit für den Postfach-Entwurf. Länger als die Gesendet-Prüfung: Eine
#: Nachricht mit PDF im Anhang ist schnell ein paar Megabyte.
FRIST_POSTFACH_S = 30


def _gleicher_entwurf(kopf, felder: Mapping) -> bool:
    """Liegt hier ein Entwurf an dieselben Empfänger mit demselben Betreff?"""
    from falzmarke import gesendet

    eigene = {a.lower() for a in (felder.get("an") or []) + (felder.get("kopie") or [])}
    return (bool(eigene & set(kopf.an))
            and gesendet.betreff_kern(kopf.betreff)
            == gesendet.betreff_kern(str(felder.get("betreff") or "")))


def _entwurf_postfach(felder: Mapping, *, umgebung: Mapping[str, str],
                      profilordner: Path | None, noch_ein_entwurf: bool,
                      ) -> tuple["Entwurfslage | None", str]:
    """Legt die `.eml` als Entwurf ins Postfach des Absenders (ADR 0051).

    Rückgabe `(Lage, "")`, wenn der Weg zu Ende ging — abgelegt, schon da oder
    ungewiss —, sonst `(None, Grund)`: Dann darf der Aufrufer `-compose`
    nehmen, denn im Postfach ist nichts entstanden.

    Die Reihenfolge ist die Zusage. Erst nachsehen, ob schon ein passender
    Entwurf liegt (dann keinen zweiten); dann ablegen; dann nachzählen. Was
    nach dem Absenden des `APPEND` schiefgeht, ist **ungewiss**, nicht
    gescheitert: Der Entwurf kann angekommen sein, und ein `-compose` danach
    wäre der zweite Entwurf aus #287.
    """
    from falzmarke import postfach

    if (umgebung.get("FALZMARKE_POSTFACH") or "").strip().lower() == "nie":
        return None, "FALZMARKE_POSTFACH=nie ist gesetzt"
    roh = felder.get("roh")
    adresse = str(felder.get("absender") or "")
    if not roh or not adresse:
        return None, ""
    ordner = thunderbird_ordner(adresse, "draft_folder", profilordner)
    try:
        sitzung = postfach.verbinde(adresse, umgebung=umgebung, frist=FRIST_POSTFACH_S)
    except postfach.PostfachFehler as fehler:
        return None, str(fehler)
    with sitzung:
        try:
            ordner = ordner or sitzung.sonderordner("\\Drafts")
            if not ordner:
                return None, f"im Postfach von {adresse} ist kein Entwürfe-Ordner gekennzeichnet"
            vorher = [k for k in sitzung.koepfe(ordner) if _gleicher_entwurf(k, felder)]
        except postfach.PostfachFehler as fehler:
            return None, str(fehler)
        anzeige = postfach.utf7_dekodieren(ordner)
        if vorher and not noch_ein_entwurf:
            juengster = max(vorher, key=lambda k: (k.datum is not None, k.datum, int(k.uid)))
            zeit = (juengster.datum.astimezone().strftime("%d.%m.%Y %H:%M")
                    if juengster.datum else "(ohne Datum)")
            return Entwurfslage(None, "", schon_da=(
                f"{zeit} „{juengster.betreff}“ in „{anzeige}“ von {adresse}"
                + (f" ({len(vorher)} Stück)" if len(vorher) > 1 else "")),
                schon_da_uid=str(juengster.uid)), ""
        try:
            sitzung.ablegen(ordner, bytes(roh))
            nachher = [k for k in sitzung.koepfe(ordner) if _gleicher_entwurf(k, felder)]
        except postfach.PostfachFehler as fehler:
            return Entwurfslage(None, f"Ablegen im Postfach abgebrochen ({fehler}) — ob der "
                                      f"Entwurf in „{anzeige}“ angekommen ist, ist offen",
                                ungewiss=True), ""
    if len(nachher) != len(vorher) + 1:
        return Entwurfslage(None, f"der Server nahm den Entwurf an, aber in „{anzeige}“ "
                                  f"liegen danach {len(nachher)} passende statt "
                                  f"{len(vorher) + 1}", ungewiss=True), ""
    alte = {k.uid for k in vorher}
    neu = max((k for k in nachher if k.uid not in alte), key=lambda k: int(k.uid))
    soll_bezug = str(felder.get("antwort_auf") or "").strip()
    soll_fassung = str(felder.get("fassung") or "").strip()
    ablage = Postfachablage(
        adresse=adresse, ordner=anzeige, betreff=str(felder.get("betreff") or ""),
        vorher=len(vorher), nachher=len(nachher),
        bezug=(neu.antwort_auf == soll_bezug) if soll_bezug else None,
        fassung=(neu.fassung == soll_fassung) if soll_fassung else None,
        uid=str(neu.uid))
    from falzmarke import entwurfsbuch

    return Entwurfslage("Thunderbird", "", konto=adresse, postfach=ablage,
                        buch_grund=entwurfsbuch.eintragen(ablage, felder,
                                                          umgebung=umgebung)), ""


def _fenster_auf(lage: Entwurfslage, felder: Mapping, umgebung: Mapping[str, str],
                 ) -> Entwurfslage:
    """Öffnet den Postfach-Entwurf über die Entwurfsbrücke (ADR 0052).

    Nur, wenn feststeht, welcher es ist: der eben abgelegte oder der, der schon
    lag. Ist die Lage ungewiss, bleibt es beim Hinweis — ein Fenster auf einen
    Entwurf, von dem niemand weiß, ob es ihn gibt, hülfe niemandem.
    """
    if lage.postfach is not None and lage.postfach.uid:
        konto, uid = lage.postfach.adresse, lage.postfach.uid
    elif lage.schon_da and lage.schon_da_uid:
        konto, uid = str(felder.get("absender") or ""), lage.schon_da_uid
    else:
        return lage
    from falzmarke import bruecke

    return lage._replace(fenster=bruecke.entwurf_oeffnen(konto, uid, umgebung=umgebung))


def _steuere(skript: str, kennung: str, *, laufen=subprocess.run) -> str | None:
    """Führt ein Skript aus, das nur eine Kennung braucht — öffnen, verwerfen.

    `None` heißt gelaufen; alles andere ist der Grund. Geworfen wird nichts:
    Auch hier gilt ADR 0038, Punkt 4 — die geprüfte Datei liegt bereits, und
    ein Fenster, das nicht aufgeht, macht sie nicht ungültig.
    """
    with tempfile.TemporaryDirectory(prefix="falzmarke-entwurf-") as ordner:
        datei = Path(ordner) / "schritt.applescript"
        datei.write_text(skript, encoding="utf-8")
        try:
            lauf = _lauf(["osascript", str(datei), str(kennung)], FRIST_ENTWURF_S, laufen)
        except FileNotFoundError:
            return "osascript gibt es auf diesem System nicht"
        except subprocess.TimeoutExpired:
            return f"osascript kam in {FRIST_ENTWURF_S} Sekunden nicht zurück"
    if lauf.returncode != 0:
        meldung = (lauf.stderr or "").strip().splitlines()
        letzte = meldung[-1] if meldung else f"osascript endete mit Code {lauf.returncode}"
        return letzte[:200]
    return None


def zerlege_nachweis(ausgabe: str) -> tuple[str | None, tuple[int, ...] | None, str | None]:
    """Die Antwort des Steuerskripts: Kennung, vier Zählwerte — oder ein Grund.

    Seit #287 gibt das Anlegeskript die `id` der Nachricht mit zurück. Sie wird
    gebraucht, um dieselbe Nachricht danach zu öffnen oder zu verwerfen; ohne
    sie müsste man sie über den Betreff suchen, und zwei Entwürfe mit
    demselben Betreff wären nicht auseinanderzuhalten.

    Gibt `(kennung, (an, kopie, blindkopie, anhaenge), None)` — oder
    `(None, None, Grund)`.
    """
    # Nur die erste Zeile: Die zweite trägt seit #305 das Konto.
    zeilen = ausgabe.strip().splitlines()
    teile = zeilen[0].split() if zeilen else []
    if len(teile) != 5 or not all(s.isdigit() for s in teile):
        return None, None, (f"das Steuerskript meldete "
                            f"„{ausgabe.strip()[:60]}“ statt einer Zählung")
    return teile[0], tuple(int(s) for s in teile[1:]), None


def konto_aus_nachweis(ausgabe: str) -> str | None:
    """Die zweite Zeile des Nachweises: das Konto am Entwurf, oder `None` (#305)."""
    zeilen = ausgabe.strip().splitlines()
    if len(zeilen) < 2:
        return None
    wert = zeilen[1].strip()
    return None if wert in ("", "-") else wert


def suche_aus_nachweis(ausgabe: str) -> str | None:
    """Die dritte Zeile: `"gefunden"`, `"fehlt"` oder `None` für nicht geprüft (#315)."""
    zeilen = ausgabe.strip().splitlines()
    if len(zeilen) < 3:
        return None
    wert = zeilen[2].strip()
    return wert if wert in ("gefunden", "fehlt") else None


def skript_setzt_konto(skript: str) -> bool:
    """Legt das Skript den Entwurf auf ein Konto? Für die Gegenprobe (#305)."""
    return "properties {account:konto," in skript


def absender_warnung(soll: str, ist: str | None, suche: str | None = None) -> str | None:
    """Die Zeile, die nicht überlesen werden darf — oder `None`, wenn alles passt.

    Der Entwurf entsteht auch bei falschem Konto: So hat es der Betreiber am
    13.09.2026 entschieden. Ein Fenster, dessen Absender man umstellen muss, ist
    besser als keins — solange man es gesagt bekommt.

    Drei Fälle, weil es drei verschiedene Reparaturen sind (#315):

    * `suche == "fehlt"` — Outlook zeigte Konten, aber keins mit dieser Adresse.
      „Von“ umstellen geht dann nicht, und die Signatur im Rumpf nennt trotzdem
      die Adresse des Profils. Am 14.09.2026 so verschickt: Absender das
      Standardkonto, Signatur eine andere Adresse. Die Reparatur ist ein anderes
      Profil oder ein eingerichtetes Konto.
    * das Konto am Entwurf weicht ab, obwohl es das gesuchte gibt — umstellen.
    * nichts lesbar (neues Outlook) — nicht geprüft, und das steht auch so da.
    """
    if not soll:
        return None
    if ist and ist.strip().lower() == soll.strip().lower():
        return None
    von = ist or "dem Standardkonto"
    if suche == "fehlt":
        return (f"ABSENDER PRÜFEN: In Outlook gibt es kein Konto {soll}. Der Entwurf geht "
                f"von {von} raus, die Signatur nennt aber {soll}. „Von“ umstellen geht "
                "nicht — ein Profil mit einem vorhandenen Konto wählen oder das Konto in "
                "Outlook einrichten.")
    if ist:
        return (f"ABSENDER PRÜFEN: Der Entwurf kommt von {ist}, das Profil sagt {soll}. "
                "In Outlook unter „Von“ umstellen.")
    return (f"ABSENDER PRÜFEN: Outlook zeigte keine Konten — ob es {soll} dort gibt, ist "
            "nicht geprüft. Der Entwurf liegt auf dem Standardkonto. In Outlook unter "
            "„Von“ umstellen, falls die Adresse dort steht.")


def _nachweis_stimmt(ausgabe: str, felder: Mapping) -> str | None:
    """Sagt die Antwort des Skripts dasselbe wie die Vorgabe? Sonst der Grund.

    Ein Exit-Code von 0 belegt, dass das Skript durchlief — nicht, dass die
    Nachricht trägt, was sie tragen soll. Deshalb zählt das Skript am fertigen
    Objekt nach, und hier wird die Zählung gegen die Vorgabe gehalten. Fehlt
    ein Anhang, weil das Programm ihn stillschweigend abgelehnt hat, fällt es
    genau hier auf.
    """
    _, ist, fehler = zerlege_nachweis(ausgabe)
    if fehler:
        return fehler
    soll = (len(felder.get("an") or []), len(felder.get("kopie") or []),
            len(felder.get("blindkopie") or []), len(felder.get("anhaenge") or []))
    if ist != soll:
        benennung = ("Empfänger", "Kopien", "Blindkopien", "Anhänge")
        fehlt = [f"{n}: {i} statt {z}" for n, i, z in zip(benennung, ist, soll) if i != z]
        return "der Entwurf trägt nicht, was er tragen soll — " + ", ".join(fehlt)
    return None


def _anhaenge_ausschreiben(ordner, anhaenge, *, typografisch: bool = False) -> list[str]:
    """Die Anhänge aus der `.eml` als Dateien — das Programm will Pfade.

    Nur der Name, nie ein Pfad aus der Nachricht: Ein Anhang, der
    „../../etc/x“ heißt, dürfte nicht aus dem Ordner zeigen. `typografisch`
    macht aus `'` im Namen ein ’ — für den Weg, auf dem der Pfad in einer
    zitierten Zeile landet (`_compose_wert`).
    """
    pfade = []
    for dateiname, inhalt in anhaenge:
        name = Path(str(dateiname)).name
        if typografisch:
            name = name.replace("'", "’")
        ziel = Path(ordner) / name
        ziel.write_bytes(inhalt)
        pfade.append(str(ziel))
    return pfade


def _app_buendel(binaer: str) -> str | None:
    """Das `.app`, in dem ein Binary liegt — für `open -a`. Sonst None.

    `PurePosixPath`, nicht `Path`: Das ist ein macOS-Pfad, der als Argument an
    `open` geht, und er wird auf jedem Rechner gleich gebaut. `Path` des Hosts
    machte daraus auf Windows `\\Applications\\Thunderbird.app` — gemessen in der
    CI auf windows-latest (PR #390).
    """
    pfad = PurePosixPath(binaer)
    if (len(pfad.parents) >= 3 and pfad.parent.name == "MacOS"
            and pfad.parents[1].name == "Contents" and pfad.parents[2].suffix == ".app"):
        return str(pfad.parents[2])
    return None


def _thunderbird_laeuft(binaer: str, laufen) -> bool:
    """Ob eine Instanz dieses Binarys läuft — per `pgrep`, ohne Berechtigung.

    Die Frage entscheidet den Weg: Läuft Thunderbird, reicht das Binary den
    Auftrag weiter und kehrt zurück. Läuft es nicht, **wird das Binary selbst
    zu Thunderbird** — es käme erst beim Beenden zurück, und `subprocess.run`
    erschlüge es nach der Frist samt Fenster. Im Zweifel gilt „läuft nicht“:
    Der Irrtum in diese Richtung kostet ein Fenster, der andere das Programm.
    """
    try:
        lauf = _lauf(["pgrep", "-f", re.escape(binaer)], FRIST_S, laufen)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return lauf.returncode == 0


def _zahl(n: int) -> str:
    """1234567 → „1.234.567“ — Tausenderpunkt, wie im Deutschen üblich."""
    return f"{n:,}".replace(",", ".")


def _nicht_gefunden(wahl: str | None) -> str:
    """Der Grund, wenn kein Programm da ist — und er nennt, was gesucht wurde.

    „kein Mailprogramm gefunden“ wäre auf einem Rechner mit Outlook eine
    Lüge: Es ist da, es wurde nur nicht gewählt.
    """
    if wahl == "outlook":
        return "Microsoft Outlook ist auf diesem Rechner nicht zu finden"
    grund = ("Thunderbird ist nicht installiert — weder unter "
             f"{THUNDERBIRD_MACOS} noch als `thunderbird` im PATH")
    if wahl is None:
        grund += "; Outlook nur auf Wahl mit --programm outlook (ADR 0049)"
    return grund


def _signatur_im_entwurf(roh: str, rumpf: str, felder: Mapping, inline,
                         ordner: Path | None) -> tuple[Signaturlage, str, str]:
    """Welche Signatur der Entwurf trägt — und der `body=`-Wert dazu (ADR 0050).

    `roh` ist der HTML-Teil der Datei, `rumpf` derselbe, fertig für `body=`.
    Nur wenn die Identität in Thunderbird selbst eine Signatur setzt, die aus
    dem Profil bekannt ist und sich sauber herausnehmen lässt, kommt ein
    anderer Rumpf zurück. In jedem anderen Fall bleibt er, wie er war — mit
    der Signatur aus dem Profil, wie vor ADR 0050.

    Zurück kommen Lage, `body=`-Wert und der HTML-Teil, aus dem er entstand —
    den braucht `_eingebettet_stimmt`: Ein Logo, das nur in der Signatur
    stand, fehlt dann zu Recht.
    """
    lage = kontosignatur(str(felder.get("absender") or ""), ordner)
    if lage.zustand != "thunderbird":
        return lage, rumpf, roh
    unterschrift = felder.get("signatur_html")
    if unterschrift is None:
        return _unbestimmt("die Signatur aus dem Profil ist hier nicht bekannt, sie bleibt im "
                           f"Rumpf — und {lage.identitaet} setzt ihre dazu"), rumpf, roh
    if not unterschrift:
        # Das Profil ergibt keine Signatur: nichts herauszunehmen, die aus
        # Thunderbird ist die einzige.
        return lage, rumpf, roh
    ohne = ohne_signatur(roh, str(unterschrift))
    if ohne is None:
        return _unbestimmt("die Signatur aus dem Profil steht nicht genau einmal im HTML-Teil, "
                           f"sie bleibt im Rumpf — und {lage.identitaet} setzt ihre dazu"), rumpf, roh
    rumpf_ohne = rumpf_fuer_compose(eingebettet(ohne, inline))
    schief = _ohne_signatur_stimmt(rumpf, rumpf_ohne,
                                   rumpf_fuer_compose(eingebettet(str(unterschrift), inline)))
    if schief:
        return _unbestimmt(f"{schief}; sie bleibt im Rumpf"), rumpf, roh
    return lage, rumpf_ohne, ohne


def _entwurf_compose(programm: Entwurfsprogramm, felder: Mapping, *,
                     laufen, ablage, thunderbird_ordner=None) -> "Entwurfslage":
    """Der Thunderbird-Weg: eine Zeile prüfen, einmal aufrufen (ADR 0049).

    Die Anhänge kommen in einen Ordner, der **liegen bleibt**: Thunderbird
    merkt sich Pfade und liest die Datei erst beim Senden oder Speichern — ein
    Verzeichnis, das nach dem Aufruf verschwindet, wäre eine leere Anlage.
    Abgeräumt wird nur, wenn sicher nichts angenommen wurde.
    """
    anhaenge = felder.get("anhaenge") or []
    ordner = tempfile.mkdtemp(prefix="falzmarke-entwurf-", dir=ablage) if anhaenge else None

    def abgeraeumt(lage: Entwurfslage) -> Entwurfslage:
        if ordner:
            shutil.rmtree(ordner, ignore_errors=True)
        return lage

    pfade = _anhaenge_ausschreiben(ordner, anhaenge, typografisch=True) if ordner else []
    inline = felder.get("inline") or []
    roh = str(felder.get("html") or "")
    html = eingebettet(roh, inline)
    signatur = None
    if html:
        html = rumpf_fuer_compose(html)
        signatur, html, roh = _signatur_im_entwurf(roh, html, felder, inline,
                                                   thunderbird_ordner)
        # Ein Bild, auf das der verwendete HTML-Teil nicht mehr zeigt — das Logo
        # einer herausgenommenen Signatur —, muss auch nicht im Rumpf stehen.
        inline = [teil for teil in inline if f"cid:{teil[0]}" in roh]
    schief = _eingebettet_stimmt(html, inline) or (html and _rumpf_stimmt(html))
    if schief:
        return abgeraeumt(Entwurfslage(None, schief))
    felder = {**felder, "html": html}
    try:
        argumente = compose_argumente(felder, pfade)
    except ValueError as fehler:
        return abgeraeumt(Entwurfslage(None, str(fehler)))
    groesse = len(argumente[1].encode("utf-8"))
    if groesse > COMPOSE_GRENZE_BYTE:
        return abgeraeumt(Entwurfslage(
            None, f"die -compose-Zeile ist {_zahl(groesse)} Byte lang, mehr als die "
                  f"{_zahl(COMPOSE_GRENZE_BYTE)} Byte, die ein Befehl auf macOS tragen darf "
                  "(ARG_MAX 1.048.576 abzüglich Umgebung) — das Logo im Profil verkleinern "
                  "oder die Datei übergeben"))
    schief = _compose_stimmt(argumente[1], felder, pfade)
    if schief:
        return abgeraeumt(Entwurfslage(None, schief))

    laeuft = _thunderbird_laeuft(programm.pfad, laufen)
    if laeuft:
        argv, frist = [programm.pfad, *argumente], FRIST_ENTWURF_S
    else:
        buendel = _app_buendel(programm.pfad)
        if buendel is None:
            return abgeraeumt(Entwurfslage(
                None, f"Thunderbird läuft nicht, und {programm.pfad} liegt in keinem "
                      ".app-Bündel — Thunderbird starten und --oeffnen wiederholen"))
        argv, frist = ["open", "-a", buendel, "--args", *argumente], FRIST_S
    try:
        lauf = _lauf(argv, frist, laufen)
    except FileNotFoundError:
        return abgeraeumt(Entwurfslage(None, f"{argv[0]} gibt es auf diesem System nicht"))
    except subprocess.TimeoutExpired:
        return Entwurfslage(None, f"{Path(argv[0]).name} kam in {frist} Sekunden nicht zurück",
                            ungewiss=True, ablage=ordner, signatur=signatur)
    if lauf.returncode != 0:
        meldung = (lauf.stderr or "").strip().splitlines()
        letzte = meldung[-1] if meldung else (
            f"{Path(argv[0]).name} endete mit Code {lauf.returncode}")
        return abgeraeumt(Entwurfslage(None, letzte[:200]))
    if not laeuft:
        # `open` hat Thunderbird mit dem Auftrag gestartet. Gemessen ist am
        # 13.10.2026 nur die laufende Instanz; ob das Fenster nach dem Start
        # aufgeht, weiß hier niemand — und „nicht geprüft“ ist nicht „nichts
        # da“: Keine Datei nachschieben, sonst stehen womöglich zwei Fenster.
        return Entwurfslage(
            None, "Thunderbird lief nicht und wurde mit dem Auftrag gestartet; ob das "
                  "Fenster aufgeht, ist nicht gemessen (13.10.2026 nur mit laufendem "
                  "Thunderbird)", ungewiss=True, ablage=ordner, signatur=signatur)
    return Entwurfslage(programm.name, "", nachgezaehlt=False, ablage=ordner, signatur=signatur)


def entwurf(felder: Mapping, *, plattform: str = sys.platform,
            umgebung: Mapping[str, str] | None = None,
            laufen=subprocess.run, wahl: str | None = None,
            binaer=thunderbird_binaer, ablage=None,
            thunderbird_ordner: Path | None = None,
            noch_ein_entwurf: bool = False) -> "Entwurfslage":
    """Legt den Entwurf an — oder sagt in einem Satz, warum nicht.

    Rückgabe: `(Programmname, "")`, wenn er steht, sonst `(None, Grund)`. Der
    Grund wandert unverändert in die Meldung des Aufrufers, der daraufhin die
    Datei übergibt. **Geworfen wird nichts** und der Exit-Code des Befehls
    ändert sich nicht (ADR 0038, Punkt 4): Wer hierher kommt, hat seine
    geprüfte `.eml` bereits.

    `FALZMARKE_ENTWURF=nie` schaltet den Weg ab, ohne `--oeffnen` aufzugeben —
    für den, der die Datei will und nicht das Fenster.

    `wahl` ist das Wort aus `--programm` (siehe `entwurfsweg`), `binaer` die
    Suche nach Thunderbird und `ablage` das Verzeichnis, unter dem dessen
    Anhangordner entsteht — ohne Angabe das Temporärverzeichnis des Systems.
    `thunderbird_ordner` ist der Profilordner, in dem nachgesehen wird, ob die
    Identität selbst eine Signatur setzt (ADR 0050) — ohne Angabe
    `THUNDERBIRD_ORDNER`.

    Im Thunderbird-Weg kommt seit ADR 0051 zuerst der **Postfach-Entwurf**:
    Ist der IMAP-Proxy erreichbar, liegt die `.eml` danach im Entwürfe-Ordner
    des Absenders, und es geht **kein** `-compose`-Fenster auf. Nur wenn dort
    nichts entstanden ist, folgt `-compose` wie bisher. `noch_ein_entwurf`
    legt ab, obwohl ein passender Entwurf schon liegt. Seit ADR 0052 geht der
    Postfach-Entwurf trotzdem als Fenster auf, wenn in Thunderbird das Add-on
    Entwurfsbrücke läuft — als „Entwurf bearbeiten“, nicht als zweiter Entwurf.

    Die Anhänge stehen in der `.eml` als Bytes; das Programm will Pfade. Für
    Outlook werden sie in ein Verzeichnis geschrieben, das erst nach dem Lauf
    verschwindet: Ein Programm, das die Datei noch liest, während sie gelöscht
    wird, hängt eine leere Anlage an. Für Thunderbird bleibt der Ordner liegen
    — siehe `_entwurf_compose`.
    """
    umgebung = os.environ if umgebung is None else umgebung
    if (umgebung.get("FALZMARKE_ENTWURF") or "").strip().lower() == "nie":
        return Entwurfslage(None, "FALZMARKE_ENTWURF=nie ist gesetzt")
    grund = kein_bildschirm(umgebung, plattform)
    if grund:
        return Entwurfslage(None, grund)
    try:
        programm = entwurfsweg(plattform, laufen=laufen, wahl=wahl, binaer=binaer)
    except FileNotFoundError:
        return Entwurfslage(None, "osascript gibt es auf diesem System nicht")
    except subprocess.TimeoutExpired:
        # Gesehen am 13.09.2026, kurz nach dem Wechsel ins klassische Outlook:
        # Die Suche kam nach über 20 Sekunden zurück, und der Befehl endete mit
        # einem Traceback und Exit 1 — obwohl die `.eml` geprüft dalag. Hier ist
        # noch nichts angelegt, der Rückfall auf die Datei ist also sicher.
        return Entwurfslage(
            None, f"das Mailprogramm antwortete nicht in {FRIST_S} Sekunden")
    if programm is None:
        return Entwurfslage(None, _nicht_gefunden(wahl))
    if programm.weg == "compose":
        lage, grund = _entwurf_postfach(felder, umgebung=umgebung,
                                        profilordner=thunderbird_ordner,
                                        noch_ein_entwurf=noch_ein_entwurf)
        if lage is not None:
            return _fenster_auf(lage, felder, umgebung)
        return _entwurf_compose(programm, felder, laufen=laufen, ablage=ablage,
                                thunderbird_ordner=thunderbird_ordner)._replace(
                                    postfach_grund=grund)

    with tempfile.TemporaryDirectory(prefix="falzmarke-entwurf-") as ordner:
        pfade = _anhaenge_ausschreiben(ordner, felder.get("anhaenge") or [])
        skriptdatei = Path(ordner) / "entwurf.applescript"
        skriptdatei.write_text(programm.anlegen, encoding="utf-8")
        argv = ["osascript", str(skriptdatei), *entwurfsargumente(felder, pfade)]
        try:
            lauf = _lauf(argv, FRIST_ENTWURF_S, laufen)
        except FileNotFoundError:
            return Entwurfslage(None, "osascript gibt es auf diesem System nicht")
        except subprocess.TimeoutExpired:
            # Der dritte Zustand (#287): Das Skript ist nicht zurückgekehrt,
            # also ist UNBEKANNT, ob eine Nachricht entstand. Wer hier die
            # `.eml` nachschöbe, riskierte genau das gemeldete zweite Fenster —
            # und wer verwürfe, hätte keine Kennung, gegen die er es täte.
            return Entwurfslage(
                None, f"osascript kam in {FRIST_ENTWURF_S} Sekunden nicht zurück",
                ungewiss=True)

    if lauf.returncode != 0:
        meldung = (lauf.stderr or "").strip().splitlines()
        letzte = meldung[-1] if meldung else f"osascript endete mit Code {lauf.returncode}"
        return Entwurfslage(None, letzte[:200])

    kennung, _, fehler = zerlege_nachweis(lauf.stdout or "")
    schief = fehler or _nachweis_stimmt(lauf.stdout or "", felder)
    if schief:
        # Angelegt, aber nicht tragfähig — und noch von niemandem gesehen, weil
        # das Anlegeskript seit #287 nicht mehr öffnet. Wegräumen, dann darf der
        # Aufrufer die `.eml` übergeben: ein Fenster, nicht zwei.
        if kennung:
            _steuere(programm.verwerfen, kennung, laufen=laufen)
        return Entwurfslage(None, schief)

    nicht_geoeffnet = _steuere(programm.oeffnen, kennung, laufen=laufen)
    if nicht_geoeffnet:
        # Die Nachricht trägt alles, ließ sich aber nicht zeigen. Sie unsichtbar
        # im Postfach zu lassen wäre die schlechteste Fassung: Der Aufrufer
        # übergibt gleich die `.eml`, und dann läge beides da.
        _steuere(programm.verwerfen, kennung, laufen=laufen)
        return Entwurfslage(None, f"angelegt, aber nicht zu öffnen: {nicht_geoeffnet}")

    return Entwurfslage(programm.name, "", konto=konto_aus_nachweis(lauf.stdout or ""),
                        suche=suche_aus_nachweis(lauf.stdout or ""))
