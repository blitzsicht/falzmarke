"""Was aus einem Postfach-Entwurf wurde — `falzmarke status` (ADR 0055).

Die Frage kam immer wieder: Ist das schon raus? Hat er etwas geändert? Liegt
der Entwurf noch, oder ist er gelöscht? Drei Quellen beantworten sie, und
keine reicht allein:

* **das Entwurfsbuch** — falzmarke trägt jeden Entwurf ein, den es per
  `APPEND` ins Postfach legt (ADR 0051): Konto, UID, Fassung, Betreff,
  Empfänger und den Text. Eine Datei auf diesem Rechner, nicht im Postfach.
  Nur so ist nach dem Senden noch bekannt, was im Entwurf stand.
* **das Postfach** — was jetzt in „Entwürfe“, „Gesendete Elemente“ und im
  Papierkorb liegt, nur lesend über den Proxy (`postfach.py`). Es sieht auch,
  was vom Handy gesendet wurde.
* **das Tagebuch der Entwurfsbrücke** — was Thunderbird selbst gesehen hat:
  geöffnet, gespeichert, gesendet, ohne Senden geschlossen, von der Sperre
  angehalten. Das Add-on schreibt es als Datei ins Thunderbird-Profil; gelesen
  wird es hier direkt, auch wenn Thunderbird zu ist.

**BELEGT** heißt: Postfach und Tagebuch sagen beide „gesendet“. Thunderbird
wirft `X-Falzmarke-Fassung` beim Senden weg und vergibt eine neue Message-ID
(gemessen am 25.10.2026). Die gesendete Mail findet sich deshalb über
Empfänger und Text, wie in der Prüfung vor dem Entwurf (`gesendet.py`), und
über die Fassung, die das Tagebuch zu ihrer Message-ID kennt (ADR 0056).

Ab Add-on 0.3.0 nennt `status` außerdem, was ein offenes Fenster hinausschicken
würde (Absender, Empfänger samt Bcc, Anhänge, ob der Text noch der angelegte
ist), und wohin eine gesendete Mail laut Tagebuch ging.

Kein `subprocess` (ADR 0038, Punkt 5). Der MCP-Dienst lädt dieses Modul nicht.
"""

from __future__ import annotations

import difflib
import email
import json
import os
import re
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email import policy
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote

#: Die Dateisperre des Betriebssystems. Auf keiner Plattform gibt es beide, und
#: auf einer dritten gibt es keine — dann wird ohne Sperre geschrieben und der
#: Grund geht in die Rückgabe von `eintragen`.
try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None

#: Wo das Entwurfsbuch liegt, wenn `FALZMARKE_ENTWURFSBUCH` nichts sagt. Eine
#: Modulkonstante, damit `conftest.py` sie für jeden Test umlegt: Kein Testlauf
#: schreibt in das Buch des Rechners, auf dem er läuft.
BUCH_VORGABE = (Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
                / "falzmarke" / "entwuerfe.jsonl")

#: Der Name des Tagebuchs im Thunderbird-Profil. Schreibt nur das Add-on.
TAGEBUCH = "entwurfsbruecke-tagebuch.jsonl"

#: Was das Add-on ins Tagebuch schreibt, und wie `status` es nennt.
#: `tests/test_entwurfsbruecke_hintergrund.py` hält beide Seiten gleich.
TAGEBUCH_WORTE = {
    "geoeffnet": "geöffnet", "gespeichert": "gespeichert", "gesendet": "gesendet",
    "geschlossen": "ohne Senden geschlossen", "gesperrt": "Sperre hielt an",
    "trotzdem": "trotz Sperre gesendet", "senden_fehlgeschlagen": "Senden scheiterte",
    "pruefung_fehlgeschlagen": "Sperre konnte nicht prüfen",
    "pruefung_teilweise": "Sperre hat nicht alles gesehen"}

#: So weit zurück sieht `status` ohne `--tage`.
TAGE_VORGABE = 14

#: So lange bleibt eine Zeile im Entwurfsbuch. Vier Mal die Spanne, die
#: `status` ohne `--tage` ansieht: Wer weiter zurückfragt, bekommt eine
#: Antwort, aber das Buch wächst nicht zum dauerhaften Archiv der
#: Geschäftspost. Es trägt den Brieftext im Klartext (ADR 0055, ADR 0058).
AUFBEWAHRUNG_TAGE = TAGE_VORGABE * 4

#: Rechte für Buch und Ordner: nur das eigene Konto. `os.open` mit diesem Modus
#: legt die Datei gleich so an; ein vorhandenes Buch wird beim nächsten
#: Schreiben nachgezogen. Unter Windows sagen die Bits nichts — dort schützt
#: das Benutzerprofil, und `os.chmod` kennt die Gruppenbits gar nicht.
BUCH_RECHTE = 0o600
ORDNER_RECHTE = 0o700

#: So viele Bytes hat eine Buchzeile höchstens. Darüber wird allein `text`
#: gekürzt, das einzige Feld ohne natürliche Grenze, und `text_gekappt` hält
#: die ursprüngliche Länge fest.
#:
#: Die Zahl ist eine eigene Schranke, keine Zusage der Plattform: POSIX sichert
#: für `O_APPEND` allein zu, dass Dateiende-Suche und Schreiben nicht getrennt
#: werden — nicht, dass ein einzelner `write` ungeteilt bleibt. Deshalb sieht
#: `_anhaengen` zusätzlich nach, wie viele Bytes ankamen. Auf einem Netzpfad
#: ist auch das nicht zugesagt (ADR 0055).
#:
#: Gemessen am 27.10.2026: Die längste Beispielmail ergibt eine Buchzeile weit
#: unter dieser Schranke; `tests/test_entwurfsbuch.py` hält den Abstand fest.
ZEILE_MAX = 32 * 1024

#: So lange wird auf die Schreibsperre gewartet, dann wird ohne sie geschrieben.
#: Dieselbe Frist wie die der Sperre beim Senden (ADR 0058, Punkt 3) und aus
#: demselben Grund: Ein Buch, das wartet, hält den Menschen auf.
SPERRE_FRIST_S = 10.0

#: So viele gesendete Mails sieht `status` höchstens an. Nur Kopfzeilen; ein
#: Bestellpostfach verschickt in vierzehn Tagen leicht mehr als die 500 von
#: `postfach.GRENZE` (gemessen 25.10.2026: 550).
GRENZE_GESENDET = 3000

#: Zeitlimit der ganzen Sitzung. Länger als beim Ablegen: Wer vierzehn Tage
#: Gesendetes an denselben Empfänger liest, lädt auch dessen Anhänge.
FRIST_S = 120

#: Eine gesendete Mail, die kurz vor dem Eintrag datiert ist, gehört noch dazu:
#: `Date` der gesendeten Mail stammt nicht unbedingt von der Uhr, die den Eintrag schrieb.
SPIEL = timedelta(minutes=5)

#: Höchstens so viele Zeilen zeigt `--diff` je Entwurf.
DIFF_ZEILEN = 60

#: Wie die UID aus der Adresse einer Nachricht gelesen wird
#: (`imap-message://…/Entwürfe#4711`). Dasselbe Muster steht im Add-on als
#: `UID_AUS_URI` und liefert dort den zweiten Weg zur UID eines Entwurfs
#: (ADR 0060); `tests/test_entwurfsbruecke.py` hält beide Seiten gleich.
UID_AUS_URI = re.compile(r"#(\d+)$")


# ── Das Entwurfsbuch ────────────────────────────────────────────────────────

class Eintrag(NamedTuple):
    """Ein Entwurf, den falzmarke ins Postfach gelegt hat."""

    zeit: datetime
    konto: str
    uid: str
    fassung: str
    betreff: str
    an: tuple[str, ...]
    text: str
    ordner: str = ""
    #: Bcc des Entwurfs. None bei Einträgen von vor 0.11 (ADR 0056): Dann ist
    #: unbekannt, ob ein Bcc geplant war, und `status` vergleicht ohne.
    blindkopie: tuple[str, ...] | None = None
    #: Ursprüngliche Zeichenzahl, wenn `text` gekappt wurde (0 sonst). Ein
    #: gekappter Text belegt kein „Text geändert“ — verglichen ist nur der Anfang.
    text_gekappt: int = 0
    #: Warum das Ablegen ungewiss blieb (leer bei einem Entwurf, der liegt).
    #: Eine solche Zeile hat keine UID: Nach dem Abriss ist sie nicht zu ermitteln.
    ungewiss: str = ""


class Buch(NamedTuple):
    """Was im Entwurfsbuch steht — und was sich daraus nicht lesen ließ."""

    eintraege: list[Eintrag]
    #: Zeilen, die kein Eintrag sind: kaputtes JSON, keine lesbare Zeit, kein
    #: Konto, eine UID, die keine Zahl ist. Gezählt statt übergangen, sonst
    #: wäre eine verlorene Zeile von „es gab sie nie“ nicht zu unterscheiden.
    unlesbar: int = 0
    #: Läufe, bei denen das Ablegen ungewiss blieb — ohne UID, nicht abgleichbar.
    ungewiss: tuple[Eintrag, ...] = ()


def buchpfad(umgebung: Mapping[str, str] | None = None) -> Path | None:
    """Die Datei des Entwurfsbuchs — oder None bei `FALZMARKE_ENTWURFSBUCH=nie`."""
    umgebung = os.environ if umgebung is None else umgebung
    wert = (umgebung.get("FALZMARKE_ENTWURFSBUCH") or "").strip()
    if wert.lower() == "nie":
        return None
    return Path(wert).expanduser() if wert else BUCH_VORGABE


def eintragen(ablage, felder: Mapping, *, umgebung: Mapping[str, str] | None = None,
              jetzt: datetime | None = None) -> str:
    """Hängt den eben abgelegten Entwurf ans Buch. Rückgabe: leer, sonst der Grund.

    Geworfen wird nichts — der Entwurf liegt schon im Postfach, und ein Buch,
    das sich nicht schreiben lässt, macht ihn nicht ungültig. Der Aufrufer
    meldet den Grund, damit `status` später nicht still weniger weiß.
    """
    pfad = buchpfad(umgebung)
    if pfad is None:
        return "FALZMARKE_ENTWURFSBUCH=nie ist gesetzt"
    zeile, grund = _zeile_bauen(felder, konto=ablage.adresse, ordner=ablage.ordner,
                                uid=str(ablage.uid), jetzt=jetzt)
    return _schreiben(pfad, zeile, grund)


def eintragen_ungewiss(adresse: str, ordner: str, felder: Mapping, *, grund: str,
                       umgebung: Mapping[str, str] | None = None,
                       jetzt: datetime | None = None) -> str:
    """Hält einen Lauf fest, bei dem das Ablegen ungewiss blieb (ADR 0055, #411).

    Nach einem Abriss hinter dem `APPEND` gibt es keine UID: Ob der Entwurf im
    Postfach liegt, ist offen. Was in ihm stand, ist dann nur hier noch zu
    finden — ohne diese Zeile wäre der Text verloren, sobald der Entwurf aus
    „Entwürfe“ verschwindet. `status` nennt sie als Hinweis, nicht als Zustand:
    Liegt der Entwurf doch, meldet ihn das Postfach selbst.
    """
    pfad = buchpfad(umgebung)
    if pfad is None:
        return "FALZMARKE_ENTWURFSBUCH=nie ist gesetzt"
    zeile, kappgrund = _zeile_bauen(felder, konto=adresse, ordner=ordner, uid="",
                                    jetzt=jetzt, ungewiss=grund or "ohne Grund")
    return _schreiben(pfad, zeile, kappgrund)


def _zeile_bauen(felder: Mapping, *, konto: str, ordner: str, uid: str,
                 jetzt: datetime | None = None, ungewiss: str = "") -> tuple[str, str]:
    """Die JSON-Zeile des Buchs und ein Grund, falls an ihr etwas offen blieb.

    Über `ZEILE_MAX` wird allein `text` gekürzt: Betreff und Adressen haben ihre
    Grenze in der Sache, der Mailtext nicht. `text_gekappt` hält fest, wie lang
    er war — eine gekappte Zeile ist etwas anderes als eine kurze Mail.
    """
    from falzmarke import gesendet

    roh = felder.get("roh") or b""
    text = gesendet.klartext(email.message_from_bytes(bytes(roh), policy=policy.default))
    zeile = {
        "zeit": (jetzt or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "konto": konto.strip().lower(),
        "ordner": ordner,
        "uid": uid,
        "fassung": str(felder.get("fassung") or "").strip(),
        "betreff": str(felder.get("betreff") or ""),
        "an": [str(a).lower() for a in (felder.get("an") or []) + (felder.get("kopie") or [])],
        "blindkopie": [str(a).lower() for a in felder.get("blindkopie") or []],
        "text": text,
    }
    if ungewiss:
        zeile["ungewiss"] = ungewiss
    fertig = json.dumps(zeile, ensure_ascii=False) + "\n"
    if len(fertig.encode("utf-8")) <= ZEILE_MAX:
        return fertig, ""
    zeile["text_gekappt"] = len(text)
    behalten = len(text)
    while behalten > 0:
        ueberschuss = len(fertig.encode("utf-8")) - ZEILE_MAX
        if ueberschuss <= 0:
            break
        behalten = max(0, behalten - max(ueberschuss, 1))
        zeile["text"] = text[:behalten]
        fertig = json.dumps(zeile, ensure_ascii=False) + "\n"
    if len(fertig.encode("utf-8")) > ZEILE_MAX:
        return fertig, (f"die Zeile bleibt mit {len(fertig.encode('utf-8'))} Bytes über "
                        f"{ZEILE_MAX} — sie kommt unter Umständen nicht ganz an")
    return fertig, ""


def _schreiben(pfad: Path, zeile: str, grund: str) -> str:
    """Legt Ordner und Buch an und hängt die Zeile an. Rückgabe: leer, sonst der Grund."""
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True, mode=ORDNER_RECHTE)
        offen = _anhaengen(pfad, zeile)
    except OSError as fehler:
        return f"{pfad}: {fehler.strerror or fehler}"
    return " · ".join(g for g in (offen, grund) if g)


#: `O_NOFOLLOW` gibt es nur dort, wo es Symlinks gibt; unter Windows ist der
#: Wert 0 und der Aufruf fällt auf das gewöhnliche Anhängen zurück.
_SCHREIBEN = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)


@contextmanager
def _sperre(pfad: Path) -> Iterator[str]:
    """Hält die Schreibsperre des Buchs; liefert den Grund, wenn es keine gibt.

    Gesperrt wird eine eigene Datei neben dem Buch, nicht das Buch selbst:
    `_ausduennen` tauscht es per `os.replace`, und eine Sperre auf dem alten
    Deskriptor hält danach nichts mehr — der nächste Schreiber öffnet eine
    andere Datei. Die Sperrdatei wird nie ersetzt und nie gelöscht.
    """
    wache = pfad.with_name(pfad.name + ".sperre")
    kennung = os.open(wache, os.O_WRONLY | os.O_CREAT, BUCH_RECHTE)
    try:
        grund = _greifen(kennung, wache)
        try:
            yield grund
        finally:
            if not grund:
                _loesen(kennung)
    finally:
        os.close(kennung)


def _greifen(kennung: int, wache: Path) -> str:
    """Wartet bis `SPERRE_FRIST_S` auf die Sperre. Rückgabe: leer, sonst der Grund."""
    if fcntl is not None:
        ende = time.monotonic() + SPERRE_FRIST_S
        while True:
            try:
                fcntl.flock(kennung, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return ""
            except OSError as fehler:
                if time.monotonic() >= ende:
                    was = fehler.strerror or fehler
                    return (f"{wache} war {SPERRE_FRIST_S:.0f} s gesperrt ({was}) — "
                            "geschrieben wurde ohne Sperre")
                time.sleep(0.02)
    if msvcrt is not None:
        try:
            msvcrt.locking(kennung, msvcrt.LK_LOCK, 1)
            return ""
        except OSError as fehler:
            return f"{wache}: {fehler.strerror or fehler} — geschrieben wurde ohne Sperre"
    return "diese Plattform kennt keine Dateisperre — zwei Läufe zugleich können eine Zeile kosten"


def _loesen(kennung: int) -> None:
    if fcntl is not None:
        fcntl.flock(kennung, fcntl.LOCK_UN)
    elif msvcrt is not None:
        os.lseek(kennung, 0, os.SEEK_SET)
        msvcrt.locking(kennung, msvcrt.LK_UNLCK, 1)


def _anhaengen(pfad: Path, zeile: str) -> str:
    """Hängt eine Zeile an: ganz oder nicht, mit 0600, ohne einem Symlink zu folgen.

    **Eine Zeile kommt ganz oder nicht an.** Geschrieben wird mit genau einem
    `os.write` auf einen `O_APPEND`-Deskriptor, nicht durch einen `TextIOWrapper`:
    Der puffert 8 KiB, und eine Buchzeile trägt den ganzen Mailtext — darüber
    zerfiel der Schreibvorgang in mehrere Syscalls, die sich mit denen eines
    zweiten Laufs verschränken konnten. Wie viele Bytes ankamen, wird nachgesehen.

    Die Sperre liegt über dem Ausdünnen **und** dem Anhängen. Ohne sie verlor ein
    Lauf seine Zeile, sobald ein zweiter zwischen Lesen und `os.replace` anhängte.

    `O_NOFOLLOW` verhindert, dass ein Symlink an dieser Stelle die Zeile in eine
    fremde Datei hängt. Rückgabe: leer, sonst was offen blieb.
    """
    daten = zeile.encode("utf-8")
    with _sperre(pfad) as sperrgrund:
        _ausduennen(pfad)
        kennung = os.open(pfad, _SCHREIBEN, BUCH_RECHTE)
        try:
            # Ein Buch aus einer früheren Fassung trägt noch die Umask-Rechte. Am
            # offenen Deskriptor nachziehen, nicht am Pfad: Dazwischen könnte die
            # Datei eine andere sein.
            nachziehen = getattr(os, "fchmod", None)
            if nachziehen is not None:
                nachziehen(kennung, BUCH_RECHTE)
            geschrieben = os.write(kennung, daten)
        finally:
            os.close(kennung)
    if geschrieben != len(daten):
        return (f"{pfad}: nur {geschrieben} von {len(daten)} Bytes angekommen — "
                "die Zeile steht halb im Buch")
    return sperrgrund


def _ausduennen(pfad: Path, jetzt: datetime | None = None) -> int:
    """Verwirft Zeilen, die älter sind als `AUFBEWAHRUNG_TAGE`. Rückgabe: wie viele.

    Eine Zeile ohne lesbare Zeit bleibt stehen. Verwerfen wäre die falsche
    Richtung: `status` wüsste dann weniger, weil eine Zeile kaputt war.
    Geschrieben wird daneben und dann umbenannt — sonst stünde das Buch
    mitten im Schreiben leer da. Der Aufrufer hält dabei die Sperre: Lesen,
    Schreiben und Umbenennen sind drei Schritte, und wer dazwischen anhängt,
    verliert seine Zeile.
    """
    if not pfad.is_file():
        return 0
    grenze = (jetzt or datetime.now(timezone.utc)) - timedelta(days=AUFBEWAHRUNG_TAGE)
    behalten, verworfen = [], 0
    for roh in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        zeit = None
        try:
            wert = json.loads(roh)
        except ValueError:
            wert = None
        if isinstance(wert, dict):
            zeit = _zeit(wert.get("zeit"))
        if zeit is not None and zeit < grenze:
            verworfen += 1
            continue
        behalten.append(roh)
    if not verworfen:
        return 0
    neben = pfad.with_name(pfad.name + ".neu")
    kennung = os.open(neben, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, BUCH_RECHTE)
    with os.fdopen(kennung, "w", encoding="utf-8") as datei:
        datei.write("".join(z + "\n" for z in behalten))
    os.replace(neben, pfad)
    return verworfen


def _zeit(wert) -> datetime | None:
    try:
        zeit = datetime.fromisoformat(str(wert))
    except ValueError:
        return None
    return zeit if zeit.tzinfo else zeit.replace(tzinfo=timezone.utc)


def _zuordnungswort(anzahl: int) -> str:
    """„2 Tagebuch-Einträge … lassen sich keinem Entwurf zuordnen“ (#420)."""
    viele = anzahl != 1
    # „Eintrag“ + „e“ gäbe „Eintrage“: Der Plural trägt einen Umlaut, also steht
    # das ganze Wort da.
    return (f"{anzahl} {'Tagebuch-Einträge' if viele else 'Tagebuch-Eintrag'} zu einem Entwurf "
            f"{'tragen' if viele else 'trägt'} weder UID noch Fassung — "
            f"{'sie stehen' if viele else 'er steht'} unter keinem Entwurf; "
            "ab Entwurfsbrücke 0.3.7 nennt `uid_grund` im Tagebuch den Grund")


def _zeilenwort(anzahl: int, wo: str) -> str:
    """„2 Zeilen im Entwurfsbuch sind unlesbar — …“ (ADR 0055, #411)."""
    viele = anzahl != 1
    return (f"{anzahl} Zeile{'n' if viele else ''} {wo} {'sind' if viele else 'ist'} unlesbar"
            " — was dort stand, fehlt im Abgleich")


def _jsonzeilen(pfad: Path | None) -> tuple[list[dict], int]:
    """Die Zeilen einer JSONL-Datei, die sich lesen lassen — und wie viele nicht.

    Eine unlesbare Zeile wird gezählt, nicht übergangen: Sonst meldet `status`
    eine zu kleine Zahl statt eines Hinweises, und „die Zeile ist weg“ wäre von
    „es gab sie nie“ nicht zu unterscheiden (#411). Fehlt die Datei: keine Zeilen
    und keine unlesbare — das ist etwas anderes als eine beschädigte Datei.
    """
    if pfad is None or not pfad.is_file():
        return [], 0
    zeilen, unlesbar = [], 0
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        if not zeile.strip():
            continue  # eine leere Zeile trägt keinen Eintrag und ist keine Beschädigung
        try:
            wert = json.loads(zeile)
        except ValueError:
            unlesbar += 1  # halb geschrieben oder verschränkt
            continue
        if isinstance(wert, dict):
            zeilen.append(wert)
        else:
            unlesbar += 1
    return zeilen, unlesbar


def lesen(umgebung: Mapping[str, str] | None = None) -> Buch:
    """Das Entwurfsbuch: die Einträge, die Zahl der unlesbaren Zeilen, die ungewissen Läufe."""
    zeilen, unlesbar = _jsonzeilen(buchpfad(umgebung))
    eintraege: list[Eintrag] = []
    ungewiss: list[Eintrag] = []
    for zeile in zeilen:
        zeit = _zeit(zeile.get("zeit"))
        if zeit is None or not zeile.get("konto"):
            unlesbar += 1
            continue
        kappung = zeile.get("text_gekappt")
        eintrag = Eintrag(
            zeit=zeit, konto=str(zeile["konto"]).lower(), uid=str(zeile.get("uid") or ""),
            fassung=str(zeile.get("fassung") or ""), betreff=str(zeile.get("betreff") or ""),
            an=tuple(str(a).lower() for a in zeile.get("an") or []),
            text=str(zeile.get("text") or ""), ordner=str(zeile.get("ordner") or ""),
            blindkopie=(tuple(str(a).lower() for a in zeile["blindkopie"])
                        if isinstance(zeile.get("blindkopie"), list) else None),
            text_gekappt=kappung if isinstance(kappung, int) else 0,
            ungewiss=str(zeile.get("ungewiss") or ""))
        if eintrag.ungewiss:
            ungewiss.append(eintrag)  # ohne UID, siehe `eintragen_ungewiss`
        elif eintrag.uid.isdigit():
            eintraege.append(eintrag)
        else:
            # Eine UID ist eine Zahl; eine andere Zeile hat nicht falzmarke geschrieben
            # — oder sie ist beschädigt. Beides wird gezählt, nicht verschwiegen.
            unlesbar += 1
    return Buch(eintraege, unlesbar, tuple(ungewiss))


def bruecken_profil(profilordner: Path | None = None,
                    umgebung: Mapping[str, str] | None = None) -> tuple[Path | None, str]:
    """Das Thunderbird-Profil, aus dem die Entwurfsbrücke antwortet.

    Nicht „das Standardprofil": Der Socket der Brücke bestimmt das Profil, und
    `FALZMARKE_BRUECKE_SOCKET` sticht die Auflösung des Standardprofils. Wer
    hier stur das Standardprofil nähme, läse bei gesetztem Schalter eine Datei,
    die niemand schreibt — `BELEGT` könnte nicht entstehen, `gesperrt` und
    `gesendet` blieben unsichtbar, und der einzige Hinweis lautete „kein
    Tagebuch", was nach einem zu alten Add-on klingt statt nach dem falschen
    Profil (#410).

    Weil Socket und Tagebuch jetzt aus **einer** Quelle kommen, kann das Paar
    nicht mehr auseinanderlaufen. Ein ausdrücklich übergebener `profilordner`
    geht vor — daran hängen `gesendet.fassungen` und die Proben.
    """
    from falzmarke import bruecke, oeffnen

    if profilordner is None:
        sock = bruecke.socketpfad(umgebung)
        if sock:
            return Path(sock).parent, ""
        return None, f"kein Thunderbird-Standardprofil unter {oeffnen.THUNDERBIRD_ORDNER}"
    ordner = Path(profilordner)
    profil = oeffnen.thunderbird_standardprofil(ordner)
    if profil is None:
        return None, f"kein Thunderbird-Standardprofil unter {ordner}"
    return profil, ""


def tagebuch(profilordner: Path | None = None,
             umgebung: Mapping[str, str] | None = None) -> tuple[list[dict], str]:
    """Die Einträge des Add-on-Tagebuchs und ein Hinweis, warum es fehlt (sonst leer).

    Gelesen wird das Profil, in dem der Socket der Brücke liegt
    (`bruecken_profil`) — nicht blind das Standardprofil.
    """
    profil, grund = bruecken_profil(profilordner, umgebung)
    if profil is None:
        return [], grund
    pfad = profil / TAGEBUCH
    if not pfad.is_file():
        # Das Profil **beim Namen nennen**: Der Hinweis soll die Frage „welches
        # Profil wurde gelesen?" beantworten, nicht offenlassen (#410).
        return [], (f"kein Tagebuch im Thunderbird-Profil „{profil.name}“ — "
                    "die Entwurfsbrücke ab 0.2.0 schreibt es")
    zeilen, unlesbar = _jsonzeilen(pfad)
    return zeilen, (_zeilenwort(unlesbar, "im Tagebuch der Entwurfsbrücke") if unlesbar else "")


def fassungen(eintraege: list[dict]) -> dict[str, str]:
    """Message-ID → Fassung aus den Einträgen „gesendet“ des Tagebuchs (ADR 0056).

    Thunderbird übernimmt `X-Falzmarke-Fassung` beim Senden nicht in die
    gesendete Mail (gemessen 25.10.2026); das Tagebuch kennt sie aus dem Entwurf.
    """
    from falzmarke import gesendet

    aus = {}
    for tag in eintraege:
        ursprung = tag.get("ursprung")
        fassung = str(ursprung.get("fassung") or "") if isinstance(ursprung, Mapping) else ""
        kennung = gesendet.kennung(tag.get("message_id"))
        if tag.get("art") == "gesendet" and kennung and fassung:
            aus[kennung] = fassung
    return aus


# ── Der Abgleich ────────────────────────────────────────────────────────────

class Zustand(NamedTuple):
    """Was aus einem Entwurf wurde.

    `art`:

    - `wartet` — liegt in „Entwürfe“, nicht gesendet
    - `offen` — liegt dort und ist gerade in einem Fenster offen
    - `schon_raus` — liegt noch, aber derselbe Text ging schon hinaus
    - `gesendet` — liegt nicht mehr, und eine gesendete Mail passt;
      `text_gleich` sagt, ob mit dem Text des Entwurfs
    - `ersetzt` — liegt nicht mehr, ein neuerer Entwurf mit demselben Betreff schon
    - `geloescht` — liegt im Papierkorb
    - `verschwunden` — weder in „Entwürfe“ noch gesendet noch im Papierkorb
    """

    art: str
    betreff: str
    an: tuple[str, ...]
    angelegt: datetime | None
    uid: str
    #: Zeiten der gesendeten Mails mit demselben Text, älteste zuerst.
    gesendet: tuple[datetime | None, ...] = ()
    #: Zeiten der gesendeten Mails mit demselben Betreff und anderem Text.
    anders: tuple[datetime | None, ...] = ()
    text_gleich: bool | None = None
    #: Ob das Entwurfsbuch den Entwurf kennt.
    im_buch: bool = False
    #: Die Einträge des Tagebuchs zu diesem Entwurf, in Reihenfolge.
    tagebuch: tuple[dict, ...] = ()
    nachfolger: str = ""
    diff: tuple[str, ...] = ()
    #: Was das offene Fenster jetzt hinausschicken würde (`fenster` der Brücke, ADR 0056).
    fenster: Mapping | None = None
    #: Ob der Text im Fenster noch der des angelegten Entwurfs ist.
    fenster_text_gleich: bool | None = None
    #: Absender, Empfänger und Anhänge laut Tagebuch-Eintrag „gesendet“ (Add-on ab 0.3.0).
    versand: Mapping | None = None
    #: Gesendet, aber nicht im Entwurf / im Entwurf, aber nicht gesendet.
    empfaenger_plus: tuple[str, ...] = ()
    empfaenger_minus: tuple[str, ...] = ()
    #: Ob der Text im Buch gekappt ist. Dann belegt er kein „Text geändert“.
    text_gekappt: bool = False

    @property
    def belegt(self) -> bool:
        """Postfach und Tagebuch sagen beide „gesendet“.

        Ein Treffer mit nur gleichem Betreff (`anders`) trägt das allein im
        Zustand `gesendet`. Liegt der Entwurf im Papierkorb, sagt ADR 0055
        ausdrücklich „Gesendet ist er nicht“, und die Zeile nennt bloß, dass
        derselbe Betreff mit anderem Text hinausging — das ist keine zweite
        Quelle für diesen Entwurf (#414).
        """
        if not any(t.get("art") == "gesendet" for t in self.tagebuch):
            return False
        return bool(self.gesendet) or (self.art == "gesendet" and bool(self.anders))


class Bericht(NamedTuple):
    adresse: str
    zustaende: tuple[Zustand, ...] = ()
    #: Leer heißt geprüft. Sonst ist nichts geprüft, und das ist kein „nichts gefunden“.
    grund: str = ""
    entwuerfe: str = ""
    gesendet: str = ""
    papierkorb: str = ""
    angesehen: int = 0
    tage: int = TAGE_VORGABE
    im_buch: int = 0
    tagebuch: int = 0
    hinweise: tuple[str, ...] = ()
    #: Zeilen des Entwurfsbuchs, aus denen kein Eintrag wurde (#411).
    unlesbar: int = 0
    #: Läufe dieses Kontos, bei denen das Ablegen ungewiss blieb — ohne UID.
    ungewiss: tuple[Eintrag, ...] = ()
    #: Tagebuch-Einträge zu einem Entwurf ohne UID und ohne Fassung (#420).
    ohne_zuordnung: int = 0


def fenster_des_kontos(fenster: list[dict], adresse: str) -> dict[str, dict]:
    """UID → das Fenster, in dem ein Entwurf dieses Kontos offen steht.

    Das Konto wird **nicht** aus der `draft_id` geraten. Deren Autoritätsteil
    trägt den IMAP-Anmeldenamen, und der muss die Adresse nicht enthalten:
    Lautet der Login `m0123456` oder `order`, während die Adresse
    `order@example.de` ist, traf die alte Teilketten-Prüfung `adresse in ziel`
    nie — ein Entwurf, der gerade in einem Fenster stand, hieß dann `WARTET`,
    und `OFFEN` konnte an solchen Einrichtungen überhaupt nicht entstehen.
    Umgekehrt traf die Teilkette auch ein fremdes Konto, dessen URI die Adresse
    als Teilstück enthielt (#410).

    Gefragt wird stattdessen das Add-on: Es meldet ab 0.3.0 unter `identitaet`
    die Absenderadresse des Fensters (`implementation.js`, aus `from`) — eine
    Identität, kein Anmeldename. Wo sie dasteht, entscheidet sie allein.

    Fehlt sie — älteres Add-on, oder `live: false`, weil sich das Fenster nicht
    lesen ließ —, bleibt die UID der einzige Anker. Sie trägt für sich: Die
    Fensterliste wird je Konto gegen dessen Entwürfe-Ordner abgeglichen, und
    eine UID ohne Fenster bleibt einfach `WARTET`. Die Adresse in der URI darf
    dann nicht mehr ausschließen; sie entscheidet nur noch, wenn zwei Fenster
    dieselbe UID melden.
    """
    nach_uid: dict[str, list[tuple[bool, bool, dict]]] = {}
    for eintrag in fenster:
        ziel = unquote(str(eintrag.get("draft_id") or "").split("?")[0]).lower()
        treffer = UID_AUS_URI.search(ziel)
        if not treffer:
            continue
        gemeldet = str(eintrag.get("identitaet") or "").strip().lower()
        if gemeldet and gemeldet != adresse.strip().lower():
            continue
        nach_uid.setdefault(treffer.group(1), []).append(
            (not gemeldet, adresse.strip().lower() not in ziel, eintrag))
    # Je UID das beste Fenster: gemeldete Identität vor Treffer in der URI vor
    # erstem Fund. `sorted` ist stabil, der letzte Rang ist damit die Reihenfolge
    # der Liste.
    return {uid: sorted(liste, key=lambda e: e[:2])[0][2] for uid, liste in nach_uid.items()}


def _offene_uids(adresse: str, umgebung: Mapping[str, str]) -> tuple[dict[str, dict], str]:
    """UID → was die Brücke über das Fenster meldet, in dem dieser Entwurf offen ist."""
    from falzmarke import bruecke

    try:
        fenster = bruecke.offene_entwuerfe(umgebung=umgebung)
    except bruecke.BrueckenFehler as fehler:
        return {}, f"offene Fenster nicht geprüft: {fehler}"
    return fenster_des_kontos(fenster, adresse), ""


def _ursprung(tag: Mapping, adresse: str) -> Mapping | None:
    ursprung = tag.get("ursprung")
    if not isinstance(ursprung, Mapping):
        return None
    return ursprung if str(ursprung.get("konto") or "").lower() == adresse else None


def ohne_zuordnung(eintraege: list[dict], adresse: str) -> int:
    """Einträge dieses Kontos zu einem Entwurf **ohne** UID und **ohne** Fassung (#420).

    Genau diese Signatur ist ein Fehler und kein Sonderfall. Ein Fenster vom Typ
    `new` oder `reply` hat von Natur aus keine UID — der Entwurf, von dem es
    käme, gibt es nicht. Ein Entwurf hat eine. Fehlen bei ihm beide
    Zuordnungsmerkmale, hängt die Zeile an keinem Eintrag im Entwurfsbuch:
    `status` zeigt die Mail dann ohne „Ging an …“ und ohne BELEGT, und die
    Sperre erkennt sie nicht über die Fassung.

    Gezählt statt übergangen, aus demselben Grund wie die unlesbaren Zeilen
    (#411): Am 26.10.2026 lag genau ein solches Paar im Tagebuch, und zu sehen
    war es allein daran, dass eine Versandzeile fehlte.
    """
    treffer = 0
    for tag in eintraege:
        ursprung = _ursprung(tag, adresse)
        if ursprung is None or str(ursprung.get("typ") or "") != "draft":
            continue
        if not str(ursprung.get("uid") or "") and not str(ursprung.get("fassung") or ""):
            treffer += 1
    return treffer


def _kette(tagebuch: list[dict], adresse: str, uid: str) -> set[str]:
    """Die UID und alle, unter denen Thunderbird denselben Entwurf neu gespeichert hat.

    Speichern legt einen neuen Entwurf mit neuer UID an; `gespeichert` trägt die
    alte im Ursprung und die neue in `neu_uid`. Gilt in beide Richtungen: Ein
    liegender Entwurf findet so auch, was vor dem Speichern geschah.
    """
    kette = {uid}
    gewachsen = True
    while gewachsen:
        gewachsen = False
        for tag in tagebuch:
            ursprung = _ursprung(tag, adresse)
            neu = tag.get("neu_uid")
            if tag.get("art") != "gespeichert" or ursprung is None or not isinstance(neu, list):
                continue
            glieder = {str(ursprung.get("uid") or "")} | {str(n) for n in neu if n is not None}
            glieder.discard("")
            if glieder & kette and not glieder <= kette:
                kette |= glieder
                gewachsen = True
    return kette


def _gehoert_dazu(tag: Mapping, adresse: str, kette: set[str], fassung: str) -> bool:
    """Über die UID. Die Fassung zählt nur, wenn der Eintrag keine UID kennt:
    Zwei Entwürfe aus derselben Quelle tragen dieselbe (gemessen 25.10.2026)."""
    ursprung = _ursprung(tag, adresse)
    if ursprung is None:
        return False
    uid = str(ursprung.get("uid") or "")
    if uid:
        return uid in kette
    return bool(fassung and str(ursprung.get("fassung") or "") == fassung)


def _fenstertext_gleich(fenster: Mapping | None, vorlage: str) -> bool | None:
    """Ob der Text im offenen Fenster noch der angelegte ist. None: nicht prüfbar.

    Verglichen wird der Kern bis zur Grußformel wie in `gesendet.py`: Thunderbird
    setzt die Konto-Signatur darunter und schreibt Aufzählungszeichen um.
    """
    from falzmarke import gesendet

    if not fenster or not fenster.get("live") or "text" not in fenster or not vorlage:
        return None
    eigen = gesendet.merkmale_aus(empfaenger=(), betreff="", text=vorlage)
    jetzt = gesendet.merkmale_aus(empfaenger=(), betreff="", text=str(fenster["text"]))
    if len(eigen.kern) >= gesendet.KERN_MIN:
        return eigen.kern == jetzt.kern
    return eigen.voll == jetzt.voll


def _versand(eintrag: Eintrag, tagebuch: tuple[dict, ...]) -> dict:
    """Empfänger laut letztem Tagebuch-Eintrag „gesendet“ gegen die des Entwurfs.

    Leer, wenn das Tagebuch keine Empfänger nennt (Add-on vor 0.3.0). Kennt das
    Entwurfsbuch kein Bcc (Eintrag vor 0.11), zählt das Bcc auf keiner Seite.
    """
    versand = next((t for t in reversed(tagebuch)
                    if t.get("art") == "gesendet" and isinstance(t.get("an"), list)), None)
    if versand is None:
        return {}
    gesendet_an = {str(a).lower() for f in ("an", "kopie") for a in versand.get(f) or []}
    geplant = set(eintrag.an)
    if eintrag.blindkopie is not None:
        gesendet_an |= {str(a).lower() for a in versand.get("blindkopie") or []}
        geplant |= set(eintrag.blindkopie)
    return {"versand": versand, "empfaenger_plus": tuple(sorted(gesendet_an - geplant)),
            "empfaenger_minus": tuple(sorted(geplant - gesendet_an))}


def abgleich(adresse: str, *, tage: int = TAGE_VORGABE, mit_diff: bool = False,
             umgebung: Mapping[str, str] | None = None, jetzt: datetime | None = None,
             profilordner: Path | None = None) -> Bericht:
    """Gleicht Entwurfsbuch, Postfach und Tagebuch für eine Absenderadresse ab.

    Wirft nichts: Ist das Postfach nicht zu erreichen, trägt der Bericht den
    Grund, und kein Entwurf gilt als geprüft.
    """
    from falzmarke import gesendet, oeffnen, postfach

    umgebung = os.environ if umgebung is None else umgebung
    adresse = adresse.strip().lower()
    jetzt = jetzt or datetime.now(timezone.utc)
    grenze = jetzt - timedelta(days=tage)
    stand = lesen(umgebung)
    buch = [e for e in stand.eintraege if e.konto == adresse and e.zeit >= grenze]
    ungewiss = tuple(e for e in stand.ungewiss if e.konto == adresse and e.zeit >= grenze)
    # `umgebung` mit: Sie entscheidet über `FALZMARKE_BRUECKE_SOCKET` und damit
    # über das Profil. Ohne sie läse `tagebuch` `os.environ` — ein anderes
    # Objekt als das, das dieser Lauf benutzt.
    tage_eintraege, tagebuch_grund = tagebuch(profilordner, umgebung)
    tage_eintraege = [t for t in tage_eintraege
                      if (_zeit(t.get("zeit")) or grenze) >= grenze]
    # Das Tagebuch führt alle Konten des Profils, die Zeile stellt die Zahl aber hinter
    # einem einzelnen Absender dar. Also auch nur dessen Einträge zählen (#414).
    tagebuch_eigene = sum(_ursprung(t, adresse) is not None for t in tage_eintraege)
    # Vor dem Postfach, wie die unlesbaren Zeilen: Dass das Add-on einen Entwurf
    # nicht zuordnen konnte, weiß das Tagebuch unabhängig davon, ob das Postfach
    # antwortet (#411, #420).
    verwaist = ohne_zuordnung(tage_eintraege, adresse)
    hinweise = [tagebuch_grund] if tagebuch_grund else []
    if verwaist:
        hinweise.append(_zuordnungswort(verwaist))
    # Vor `leer`: Ist das Postfach nicht erreichbar, nimmt `leer._replace(grund=…)` nur
    # mit, was jetzt schon in `hinweise` steht — und gerade dann zählt, was das Buch weiß.
    if stand.unlesbar:
        hinweise.append(_zeilenwort(stand.unlesbar, "im Entwurfsbuch"))
    offen, offen_grund = _offene_uids(adresse, umgebung)
    if offen_grund:
        hinweise.append(offen_grund)

    leer = Bericht(adresse, tage=tage, im_buch=len(buch), tagebuch=tagebuch_eigene,
                   hinweise=tuple(hinweise), unlesbar=stand.unlesbar, ungewiss=ungewiss,
                   ohne_zuordnung=verwaist)
    try:
        sitzung = postfach.verbinde(adresse, umgebung=umgebung, frist=FRIST_S)
    except postfach.PostfachFehler as fehler:
        return leer._replace(grund=str(fehler))
    with sitzung:
        try:
            ordner_e = (oeffnen.thunderbird_ordner(adresse, "draft_folder", profilordner)
                        or sitzung.sonderordner("\\Drafts"))
            ordner_g = (oeffnen.thunderbird_ordner(adresse, "fcc_folder", profilordner)
                        or sitzung.sonderordner("\\Sent") or "Gesendete Elemente")
            ordner_p = sitzung.sonderordner("\\Trash")
            if not ordner_e:
                return leer._replace(grund=f"im Postfach von {adresse} ist kein "
                                           "Entwürfe-Ordner gekennzeichnet")
            liegend = sitzung.koepfe(ordner_e)
            raus = [k for k in sitzung.koepfe(ordner_g, seit=grenze.date(),
                                                 grenze=GRENZE_GESENDET)
                    if k.datum is None or k.datum >= grenze]
            weg = (sitzung.koepfe(ordner_p, seit=grenze.date(), grenze=GRENZE_GESENDET)
                   if ordner_p else [])
            if not ordner_p:
                hinweise.append("kein Papierkorb gekennzeichnet — „gelöscht“ ist nicht prüfbar")
            for name in (ordner_e, ordner_g, ordner_p):
                if name and name in sitzung.gekappt:
                    gefunden, angesehen = sitzung.gekappt[name]
                    hinweise.append(
                        f"„{postfach.utf7_dekodieren(name)}“: nur die neuesten "
                        f"{angesehen} von {gefunden} Mails angesehen — "
                        "was davor liegt, fehlt im Abgleich")
            gleiche: dict[tuple, list] = {}
            for kopf in liegend:
                kern = gesendet.betreff_kern(kopf.betreff)
                if kern:
                    gleiche.setdefault((kern, frozenset(kopf.an)), []).append(kopf)
            for doppelt in gleiche.values():
                if len(doppelt) > 1:
                    hinweise.append(
                        f"{len(doppelt)} Entwürfe „{doppelt[0].betreff}“ an "
                        f"{', '.join(sorted(doppelt[0].an))} liegen (UID "
                        f"{', '.join(k.uid for k in doppelt)}) — nur einen senden")

            gelesen: dict[str, tuple] = {}
            bekannt = fassungen(tage_eintraege)

            def gesendete(kopf):
                if kopf.uid not in gelesen:
                    nachricht = email.message_from_bytes(sitzung.nachricht(ordner_g, kopf.uid),
                                                         policy=policy.default)
                    gelesen[kopf.uid] = (gesendet.merkmale(nachricht, mit_bcc=True,
                                                           fassungen=bekannt),
                                         gesendet.klartext(nachricht))
                return gelesen[kopf.uid]

            def treffer(eigen, ab, stufe):
                gleich, anders = [], []
                for kopf in raus:
                    if not eigen.empfaenger & set(kopf.an):
                        continue
                    if ab is not None and kopf.datum is not None and kopf.datum < ab - SPIEL:
                        continue
                    fremd, text = gesendete(kopf)
                    urteil = gesendet.vergleiche(eigen, fremd)
                    if urteil == "gesendet":
                        gleich.append((kopf, text))
                    # Eine Antwort im selben Faden ist keine geänderte Fassung des Entwurfs:
                    # Sie trägt ein `AW:` mehr (wie die Sperre Antworten auslässt, ADR 0055).
                    elif urteil == "geaendert" and gesendet.antwortstufe(kopf.betreff) <= stufe:
                        anders.append((kopf, text))
                return gleich, anders

            zustaende = []
            erledigt: set[int] = set()
            for kopf in liegend:
                nummer = next((i for i, e in enumerate(buch) if e.uid == kopf.uid
                               and (not e.fassung or e.fassung == kopf.fassung)), None)
                if nummer is not None:
                    erledigt.add(nummer)
                gleich, anders = [], []
                nachricht = None
                fenster = offen.get(kopf.uid)
                if any(set(kopf.an) & set(k.an) for k in raus) or fenster is not None:
                    nachricht = email.message_from_bytes(sitzung.nachricht(ordner_e, kopf.uid),
                                                         policy=policy.default)
                if any(set(kopf.an) & set(k.an) for k in raus):
                    gleich, anders = treffer(gesendet.merkmale(nachricht), None,
                                             gesendet.antwortstufe(kopf.betreff))
                # `schon_raus` sticht `offen`: Dass derselbe Text schon hinausging, ist die
                # Nachricht, auf die es ankommt — dass ein Fenster offen steht, sagt die Zeile
                # daneben (#414, ADR 0055).
                art = ("schon_raus" if gleich else "offen" if fenster is not None else "wartet")
                kette = _kette(tage_eintraege, adresse, kopf.uid)
                # Verglichen wird mit dem Text aus dem Buch, auch wenn Thunderbird den Entwurf
                # inzwischen unter neuer UID gespeichert hat: Der gespeicherte ist HTML, und
                # sein Klartext trägt die Signatur ohne erkennbare Grußformel (gemessen 25.10.).
                quelle = (nummer if nummer is not None
                          else max((i for i, e in enumerate(buch) if e.uid in kette), default=None))
                vorlage = (buch[quelle].text if quelle is not None
                           else gesendet.klartext(nachricht) if nachricht is not None else "")
                zustaende.append(Zustand(
                    art, kopf.betreff, kopf.an, kopf.datum, kopf.uid,
                    gesendet=tuple(sorted((k.datum for k, _ in gleich), key=_sortzeit)),
                    anders=tuple(sorted((k.datum for k, _ in anders), key=_sortzeit)),
                    im_buch=nummer is not None,
                    tagebuch=tuple(t for t in tage_eintraege
                                   if _gehoert_dazu(t, adresse, kette, kopf.fassung)),
                    fenster=fenster, fenster_text_gleich=_fenstertext_gleich(fenster, vorlage)))

            for nummer, eintrag in enumerate(buch):
                if nummer in erledigt:
                    continue
                eigen = gesendet.merkmale_aus(empfaenger=eintrag.an, betreff=eintrag.betreff,
                                              text=eintrag.text, fassung=eintrag.fassung)
                gleich, anders = treffer(eigen, eintrag.zeit,
                                         gesendet.antwortstufe(eintrag.betreff))
                kette = _kette(tage_eintraege, adresse, eintrag.uid)
                tagebuch_hier = tuple(t for t in tage_eintraege
                                      if _gehoert_dazu(t, adresse, kette, eintrag.fassung))
                nachfolger = next((k.uid for k in sorted(liegend, key=lambda k: -int(k.uid))
                                   if int(k.uid) > int(eintrag.uid)
                                   and set(k.an) & set(eintrag.an)
                                   and gesendet.betreff_kern(k.betreff) == eigen.betreff), "")
                # Was vor diesem Entwurf im Papierkorb lag, ist ein anderer.
                neuer = [k for k in weg if k.datum is None or k.datum >= eintrag.zeit - SPIEL]
                # Der Entwurf selbst: dieselbe Fassung. Derselbe Betreff allein kann auch ein
                # anderer Entwurf sein und reicht nur für „gelöscht“ statt „verschwunden“.
                selbst = bool(eintrag.fassung) and any(k.fassung == eintrag.fassung for k in neuer)
                im_papierkorb = selbst or any(
                    set(k.an) & set(eintrag.an)
                    and gesendet.betreff_kern(k.betreff) == eigen.betreff for k in neuer)
                if gleich or any(t.get("art") == "gesendet" for t in tagebuch_hier):
                    art = "gesendet"
                # Liegt der Entwurf selbst im Papierkorb, hat ihn jemand weggeworfen: Nach dem
                # Senden löscht Thunderbird ihn ohne Papierkorb (`deleteStorage`). Derselbe
                # Betreff mit anderem Text ist dann eine andere Mail, etwa eine Antwort, die kein
                # `AW:` mehr bekam, weil der Betreff schon eines trug (ADR 0055).
                elif anders and not selbst:
                    art = "gesendet"
                elif nachfolger:
                    art = "ersetzt"
                elif im_papierkorb:
                    art = "geloescht"
                else:
                    art = "verschwunden"
                if gleich:
                    text_gleich = True
                elif anders and not eintrag.text_gekappt:
                    text_gleich = False
                else:
                    # Ein gekappter Text belegt kein „geändert“: Verglichen war nur sein Anfang.
                    text_gleich = None
                diff = ()
                if mit_diff and anders and not gleich and not eintrag.text_gekappt:
                    spaeteste = max(anders, key=lambda t: _sortzeit(t[0].datum))
                    diff = tuple(difflib.unified_diff(
                        eintrag.text.splitlines(), spaeteste[1].splitlines(),
                        "Entwurf", "gesendet", lineterm="", n=1))[:DIFF_ZEILEN]
                zustaende.append(Zustand(
                    art, eintrag.betreff, eintrag.an, eintrag.zeit, eintrag.uid,
                    gesendet=tuple(sorted((k.datum for k, _ in gleich), key=_sortzeit)),
                    anders=tuple(sorted((k.datum for k, _ in anders), key=_sortzeit)),
                    text_gleich=text_gleich, text_gekappt=bool(eintrag.text_gekappt),
                    im_buch=True, tagebuch=tagebuch_hier, nachfolger=nachfolger, diff=diff,
                    **_versand(eintrag, tagebuch_hier)))
        except postfach.PostfachFehler as fehler:
            return leer._replace(grund=str(fehler), hinweise=tuple(hinweise))

    zustaende.sort(key=lambda z: _sortzeit(z.angelegt), reverse=True)
    return Bericht(adresse, tuple(zustaende), entwuerfe=postfach.utf7_dekodieren(ordner_e),
                   gesendet=postfach.utf7_dekodieren(ordner_g),
                   papierkorb=postfach.utf7_dekodieren(ordner_p) if ordner_p else "",
                   angesehen=len(raus), tage=tage, im_buch=len(buch),
                   tagebuch=tagebuch_eigene, hinweise=tuple(hinweise),
                   unlesbar=stand.unlesbar, ungewiss=ungewiss, ohne_zuordnung=verwaist)


def _sortzeit(zeit: datetime | None) -> datetime:
    return zeit or datetime.min.replace(tzinfo=timezone.utc)


# ── Melden ──────────────────────────────────────────────────────────────────

KOPF = {"wartet": "WARTET", "offen": "OFFEN", "schon_raus": "SCHON RAUS",
        "gesendet": "GESENDET", "ersetzt": "ERSETZT", "geloescht": "GELÖSCHT",
        "verschwunden": "VERSCHWUNDEN"}


def _wann(zeit: datetime | None, zeitzone=None) -> str:
    return zeit.astimezone(zeitzone).strftime("%d.%m. %H:%M") if zeit else "ohne Datum"


def _tagebuchzeile(tagebuch: tuple[dict, ...], zeitzone=None) -> str:
    teile = []
    for eintrag in tagebuch[-4:]:
        art = str(eintrag.get("art"))
        wort = TAGEBUCH_WORTE.get(art, art)
        teile.append(f"{wort} {_wann(_zeit(eintrag.get('zeit')), zeitzone)}")
    return "Tagebuch: " + " · ".join(teile) if teile else ""


def _liste(werte) -> str:
    return ", ".join(str(w) for w in werte or []) or "—"


def _empfaengerzeilen(z: Zustand) -> list[str]:
    """Was im offenen Fenster steht und wohin die Mail laut Tagebuch ging (ADR 0056)."""
    aus = []
    f = z.fenster
    if f and f.get("live"):
        teile = [f"Fenster: von {f.get('identitaet') or '—'}", f"An {_liste(f.get('an'))}"]
        teile += [f"Cc {_liste(f.get('kopie'))}"] if f.get("kopie") else []
        teile += [f"Bcc {_liste(f.get('blindkopie'))}", f"Anhänge {_liste(f.get('anhaenge'))}"]
        if z.fenster_text_gleich is not None:
            teile.append("Text wie angelegt" if z.fenster_text_gleich else "Text geändert")
        aus.append(" · ".join(teile))
    elif f:
        aus.append(f"Fenster nicht lesbar: {f.get('fehler') or 'Add-on vor 0.3.0'}")
    v = z.versand
    if v:
        teile = [f"Ging an {_liste(v.get('an'))}"]
        teile += [f"Cc {_liste(v.get('kopie'))}"] if v.get("kopie") else []
        teile += [f"Bcc {_liste(v.get('blindkopie'))}"]
        if "anhaenge" in v:
            teile.append(f"Anhänge {_liste(v.get('anhaenge'))}")
        if z.empfaenger_plus or z.empfaenger_minus:
            abw = ([f"+{a}" for a in z.empfaenger_plus] + [f"−{a}" for a in z.empfaenger_minus])
            teile.append("ABWEICHEND vom Entwurf: " + " ".join(abw))
        else:
            teile.append("Empfänger wie angelegt")
        aus.append(" · ".join(teile))
    return aus


def _hinweiszeilen(bericht: Bericht, zeitzone=None) -> list[str]:
    """Die `HINWEIS`-Zeilen: ungewisse Läufe zuerst, dann die Hinweise des Abgleichs.

    Sie stehen auch unter `NICHT GEPRÜFT`: Was das Buch weiß, weiß es unabhängig
    davon, ob das Postfach antwortet — und eine unlesbare Buchzeile ist eine
    andere Lücke als ein stummes Postfach (#411).
    """
    aus = [f"HINWEIS  {_wann(e.zeit, zeitzone)} „{e.betreff}“ → {', '.join(e.an) or '—'}: "
           f"das Ablegen blieb ungewiss ({e.ungewiss}) — ob der Entwurf in „{e.ordner}“ "
           "liegt, ist offen; was in ihm stand, steht im Entwurfsbuch"
           for e in bericht.ungewiss]
    return aus + [f"HINWEIS  {h}" for h in bericht.hinweise]


def zeilen(bericht: Bericht, *, zeitzone=None) -> list[str]:
    """Die Ausgabe von `falzmarke status`, eine Zeile je Entwurf."""
    if bericht.grund:
        return ([f"NICHT GEPRÜFT  {bericht.adresse}: {bericht.grund}"]
                + _hinweiszeilen(bericht, zeitzone))
    liegen = sum(z.art in ("wartet", "offen", "schon_raus") for z in bericht.zustaende)
    aus = [(f"OK  {bericht.adresse}: {liegen} in „{bericht.entwuerfe}“, {bericht.im_buch} im "
            f"Entwurfsbuch, {bericht.angesehen} Mails der letzten {bericht.tage} Tage in "
            f"„{bericht.gesendet}“ angesehen, {bericht.tagebuch} Tagebucheinträge")]
    for z in bericht.zustaende:
        an = ", ".join(z.an) or "—"
        kopf = f"{KOPF[z.art]:<13}{_wann(z.angelegt, zeitzone)}  „{z.betreff}“ → {an}"
        if z.art in ("wartet", "offen", "schon_raus"):
            rest = f"liegt in „{bericht.entwuerfe}“ (UID {z.uid})"
            if z.fenster is not None:
                rest += ", gerade im Fenster offen"
            if z.gesendet:
                rest += (f" — ging aber {_wann(z.gesendet[-1], zeitzone)} schon raus"
                         + (f" ({len(z.gesendet)}×)" if len(z.gesendet) > 1 else "")
                         + ", nicht noch einmal senden")
            elif z.anders:
                rest += (f" — gleicher Betreff ging {_wann(z.anders[-1], zeitzone)} "
                         "mit anderem Text raus")
        elif z.art == "gesendet":
            zeiten = z.gesendet or z.anders
            if zeiten:
                if z.text_gleich is None:
                    wie = ", Text im Buch gekappt — verglichen ist nur sein Anfang"
                else:
                    wie = ", Text unverändert" if z.text_gleich else ", Text geändert"
                rest = (f"{_wann(zeiten[0], zeitzone)}"
                        + (f", {len(zeiten)}×" if len(zeiten) > 1 else "") + wie)
            else:
                rest = f"laut Tagebuch, nicht in „{bericht.gesendet}“ gefunden"
        elif z.art == "ersetzt":
            rest = f"neuer Entwurf UID {z.nachfolger} in „{bericht.entwuerfe}“"
        elif z.art == "geloescht":
            rest = f"in „{bericht.papierkorb}“"
            if z.anders:
                rest += (f" — gleicher Betreff ging {_wann(z.anders[-1], zeitzone)} "
                         "mit anderem Text raus")
        else:
            orte = [bericht.entwuerfe, bericht.gesendet] + ([bericht.papierkorb]
                                                            if bericht.papierkorb else [])
            rest = "weder in " + " noch in ".join(f"„{o}“" for o in orte)
        # Eine Entscheidung, eine Stelle: Vorher hing „· BELEGT“ allein im Zweig `gesendet`,
        # während `als_json` `belegt` für jeden Zustand meldete (#414).
        if z.belegt:
            rest += " · BELEGT"
        aus.append(f"{kopf} · {rest}")
        aus.extend(" " * 13 + zeile for zeile in _empfaengerzeilen(z))
        tagebuchzeile = _tagebuchzeile(z.tagebuch, zeitzone)
        if tagebuchzeile:
            aus.append(" " * 13 + tagebuchzeile)
        aus.extend(" " * 13 + d for d in z.diff)
    aus.extend(_hinweiszeilen(bericht, zeitzone))
    return aus


def als_json(bericht: Bericht) -> dict:
    """Dasselbe als JSON, für Sitzungen, die damit weiterrechnen."""
    def zeit(z):
        return z.isoformat() if z else None

    return {
        "adresse": bericht.adresse, "geprueft": not bericht.grund, "grund": bericht.grund,
        "tage": bericht.tage, "angesehen": bericht.angesehen, "hinweise": list(bericht.hinweise),
        "unlesbar": bericht.unlesbar, "ohne_zuordnung": bericht.ohne_zuordnung,
        "ungewiss": [{"zeit": zeit(e.zeit), "betreff": e.betreff, "an": list(e.an),
                      "ordner": e.ordner, "grund": e.ungewiss} for e in bericht.ungewiss],
        "entwuerfe": [{
            "zustand": z.art, "betreff": z.betreff, "an": list(z.an), "angelegt": zeit(z.angelegt),
            "uid": z.uid, "gesendet": [zeit(t) for t in z.gesendet],
            "anders_gesendet": [zeit(t) for t in z.anders], "text_gleich": z.text_gleich,
            "text_gekappt": z.text_gekappt,
            "im_buch": z.im_buch, "belegt": z.belegt, "nachfolger": z.nachfolger,
            "tagebuch": list(z.tagebuch), "fenster": dict(z.fenster) if z.fenster else None,
            "fenster_text_gleich": z.fenster_text_gleich,
            "versand": dict(z.versand) if z.versand else None,
            "empfaenger_plus": list(z.empfaenger_plus),
            "empfaenger_minus": list(z.empfaenger_minus)} for z in bericht.zustaende],
    }
