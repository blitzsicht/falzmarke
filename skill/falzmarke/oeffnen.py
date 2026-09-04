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
from collections.abc import Mapping
from pathlib import Path

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
        lauf = laufen(argv, capture_output=True, text=True,
                      timeout=FRIST_S, check=False)
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
