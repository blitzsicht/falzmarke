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

import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
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
#: getrennt), 4 Kopie, 5 Blindkopie, ab 6 die Anhänge als Pfade.
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
\ttell application "Microsoft Outlook"
\t\tset entwurf to make new outgoing message with properties {subject:betreff, content:rumpf}
\t\trepeat with adresse in anListe
\t\t\tmake new recipient at entwurf with properties {email address:{address:adresse}}
\t\tend repeat
\t\trepeat with adresse in kopieListe
\t\t\tmake new cc recipient at entwurf with properties {email address:{address:adresse}}
\t\tend repeat
\t\trepeat with adresse in blindListe
\t\t\tmake new bcc recipient at entwurf with properties {email address:{address:adresse}}
\t\tend repeat
\t\trepeat with i from 6 to (count of argv)
\t\t\tmake new attachment at entwurf with properties {file:POSIX file (item i of argv)}
\t\tend repeat
\t\tset nachweis to "" & (id of entwurf) & " " & (count of to recipients of entwurf) & " " & (count of cc recipients of entwurf) & " " & (count of bcc recipients of entwurf) & " " & (count of attachments of entwurf)
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
SKRIPT_OUTLOOK_OEFFNEN = """\
on run argv
\tset kennung to (item 1 of argv) as integer
\ttell application "Microsoft Outlook"
\t\topen (first outgoing message whose id = kennung)
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
\t\tdelete (first outgoing message whose id = kennung)
\tend tell
end run
"""


class Entwurfsprogramm(NamedTuple):
    """Ein Mailprogramm und die drei Skripte, die es versteht.

    Ein NamedTuple und keine Dataclass: Der Zugriff über den Index bleibt
    erhalten, und die Felder haben trotzdem Namen.
    """

    kennung: str
    name: str
    anlegen: str
    oeffnen: str
    verwerfen: str


#: Programme, die hier einen Entwurf annehmen.
#:
#: Die Liste ist kurz und ehrlich: Für Outlook ist der Weg gemessen (08.09.2026,
#: Outlook für Mac 16.112.1 — Betreff, ein Empfänger und ein Anhang aus dem
#: erzeugten Objekt zurückgelesen). Für Apple Mail ist er es **nicht**: Dort
#: nimmt `content` einer ausgehenden Nachricht keinen HTML-Rumpf an, und eine
#: Nachricht, die ihre Auszeichnung unterwegs verliert, wäre schlechter als die
#: Datei. Bis das jemand misst, bleibt es bei der Dateiübergabe.
ENTWURFSPROGRAMME = (
    Entwurfsprogramm("com.microsoft.Outlook", "Microsoft Outlook",
                     SKRIPT_OUTLOOK, SKRIPT_OUTLOOK_OEFFNEN,
                     SKRIPT_OUTLOOK_VERWERFEN),
)


def entwurfsweg(plattform: str = sys.platform, *,
                laufen=subprocess.run) -> Entwurfsprogramm | None:
    """Welches Programm hier einen Entwurf annimmt — als Angabe, nicht als Tat.

    Gefragt wird das System, nicht der Ordner: `path to application id` löst
    eine Kennung über die Datenbank auf, die auch der Finder benutzt, und
    **startet das Programm nicht**. Ein fest verdrahteter Pfad unter
    `/Applications` ginge daran vorbei, sobald jemand seine Programme woanders
    hält.

    Nur macOS. Für Windows gibt es einen Weg über COM und für Linux keinen;
    beide sind ungemessen und werden deshalb nicht behauptet (#108).
    """
    if not plattform.startswith("darwin"):
        return None
    for programm in ENTWURFSPROGRAMME:
        frage = f'POSIX path of (path to application id "{programm.kennung}")'
        lauf = _lauf(["osascript", "-e", frage], FRIST_S, laufen)
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
    teile = ausgabe.split()
    if len(teile) != 5 or not all(s.isdigit() for s in teile):
        return None, None, (f"das Steuerskript meldete "
                            f"„{ausgabe.strip()[:60]}“ statt einer Zählung")
    return teile[0], tuple(int(s) for s in teile[1:]), None


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


def entwurf(felder: Mapping, *, plattform: str = sys.platform,
            umgebung: Mapping[str, str] | None = None,
            laufen=subprocess.run) -> tuple[str | None, str]:
    """Legt den Entwurf an — oder sagt in einem Satz, warum nicht.

    Rückgabe: `(Programmname, "")`, wenn er steht, sonst `(None, Grund)`. Der
    Grund wandert unverändert in die Meldung des Aufrufers, der daraufhin die
    Datei übergibt. **Geworfen wird nichts** und der Exit-Code des Befehls
    ändert sich nicht (ADR 0038, Punkt 4): Wer hierher kommt, hat seine
    geprüfte `.eml` bereits.

    `FALZMARKE_ENTWURF=nie` schaltet den Weg ab, ohne `--oeffnen` aufzugeben —
    für den, der die Datei will und nicht das Fenster.

    Die Anhänge stehen in der `.eml` als Bytes; das Programm will Pfade. Sie
    werden deshalb in ein eigenes Verzeichnis geschrieben, das erst nach dem
    Lauf verschwindet: Ein Programm, das die Datei noch liest, während sie
    gelöscht wird, hängt eine leere Anlage an.
    """
    umgebung = os.environ if umgebung is None else umgebung
    if (umgebung.get("FALZMARKE_ENTWURF") or "").strip().lower() == "nie":
        return Entwurfslage(None, "FALZMARKE_ENTWURF=nie ist gesetzt")
    grund = kein_bildschirm(umgebung, plattform)
    if grund:
        return Entwurfslage(None, grund)
    programm = entwurfsweg(plattform, laufen=laufen)
    if programm is None:
        return Entwurfslage(
            None, "kein Mailprogramm gefunden, das hier einen Entwurf annimmt")

    with tempfile.TemporaryDirectory(prefix="falzmarke-entwurf-") as ordner:
        pfade = []
        for dateiname, inhalt in felder.get("anhaenge") or []:
            # Nur der Name, nie ein Pfad aus der Nachricht: Ein Anhang, der
            # „../../etc/x" heißt, dürfte nicht aus dem Ordner zeigen.
            ziel = Path(ordner) / Path(str(dateiname)).name
            ziel.write_bytes(inhalt)
            pfade.append(str(ziel))
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

    return Entwurfslage(programm.name, "")
