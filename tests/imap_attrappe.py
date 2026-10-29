"""Ein IMAP-Server im Speicher — die Attrappe für `falzmarke.postfach` (ADR 0051).

Sie wird so bedient wie `imaplib.IMAP4` und antwortet in dessen Form: `(typ,
daten)`, FETCH als Liste aus `(meta, literal)` und `b")"`. Damit läuft in den
Tests die **echte** Klasse `postfach.Postfach` gegen sie, nicht ein zweiter
Nachbau — geprüft wird, was später gegen den Proxy läuft.

Alles, was im Postfach etwas ändern würde außer `APPEND`, ist hier verboten und
wirft: `STORE`, `EXPUNGE`, `COPY`, `MOVE`, `DELETE`, `CREATE`, `RENAME`. Ein
Test, der einen solchen Aufruf auslöst, wird rot — das ist die Zusage „nie
löschen, nie verschieben, keine Flags ändern“ als Prüfung.

**Eine Ausnahme, und sie ist einzeln einzuschalten:** `verschieben_erlaubt=True`
öffnet `SELECT` ohne `readonly` und `UID MOVE` — für `falzmarke.ablage` (#431),
das eine beantwortete Nachricht aus dem Eingang legt. Ohne den Schalter wirft
die Attrappe beides weiter, und `test_postfach.py` prüft genau das: Sonst wäre
die Erweiterung hier eine Hintertür für jeden anderen Test.

**Sie ist an zwei Stellen strenger als ein bequemer Nachbau** (#438), und beide
sind gemessen, nicht vorsorglich: Kopfzeilen werden vor dem Vergleich entfaltet,
weil ein Server den ganzen Feldwert sucht und nicht dessen erste Zeile; und
Steuerzeichen in Argumenten lehnt sie selbst ab, weil `imaplib` das erst ab
Python 3.14 tut — die CI fährt 3.12. Ohne diese zwei Strengen wäre hier eine
Attrappe, die jede Zusage bestätigt, die sie nicht prüfen kann.
"""

from __future__ import annotations

import imaplib
import re
from datetime import datetime, timezone
from email.utils import format_datetime


class Eintrag:
    def __init__(self, uid: int, roh: bytes, angekommen: datetime, flags: str = ""):
        self.uid, self.roh, self.angekommen, self.flags = uid, roh, angekommen, flags


def _internaldate(zeit: datetime) -> str:
    return zeit.strftime("%d-%b-%Y %H:%M:%S %z")


def _kopfzeilen(roh: bytes) -> list[bytes]:
    """Die Kopfzeilen, Fortsetzungen an ihrer Zeile — so liest ein Server sie.

    RFC 5322 erlaubt jedem Feld, über mehrere physische Zeilen zu laufen
    (`\\r\\n` und dahinter Leerraum). Wer nur die erste ansieht, sucht in einem
    anderen Text als der Server — und eine Attrappe, die das nachbaut, kann
    den Fehler nicht finden, den sie belegen soll (#438).
    """
    kopf, _, _ = roh.partition(b"\r\n\r\n")
    if kopf == roh:
        kopf, _, _ = roh.partition(b"\n\n")
    zeilen: list[bytes] = []
    for zeile in re.split(rb"\r?\n", kopf):
        if zeile[:1] in (b" ", b"\t") and zeilen:
            zeilen[-1] += b"\r\n" + zeile
        else:
            zeilen.append(zeile)
    return zeilen


def _entfaltet(wert: str) -> str:
    """Ein Feldwert in einer Zeile: Umbruch samt folgendem Leerraum wird ein Leerzeichen."""
    return re.sub(r"\r?\n[ \t]+", " ", wert).strip()


def _kopfzeile_enthaelt(roh: bytes, feld: str, wert: str) -> bool:
    """Wie `SEARCH HEADER <feld> <wert>`: Teilzeichenkette, ohne Groß/Klein.

    Verglichen wird der **entfaltete** Feldwert. Ein Server, der nach einer
    `Message-ID` sucht, sieht den ganzen Wert; die erste physische Zeile ist
    nur bei kurzen Feldern dasselbe.
    """
    gesucht = wert.lower()
    for zeile in _kopfzeilen(roh):
        name, trenner, inhalt = zeile.decode("utf-8", "replace").partition(":")
        if trenner and name.strip().lower() == feld.lower():
            if gesucht in _entfaltet(inhalt).lower():
                return True
    return False


class ImapAttrappe:
    """Nimmt die Rolle von `imaplib.IMAP4` ein: aufrufen wie die Klasse, dann bedienen."""

    #: Kein Socket — `postfach` fragt danach, um die Frist nachzustellen.
    sock = None

    #: Wie `imaplib._control_chars` — hier aber festgeschrieben statt von dort
    #: geholt: Diese Prüfung gibt es in `imaplib.IMAP4._command` erst ab
    #: Python 3.14. Gemessen am 29.10.2026 schicken 3.12.9 und 3.13.12 ein
    #: Argument mit `\r\n` ungefiltert auf die Leitung, und auf der Leitung
    #: sind es dann zwei Befehle. Die CI fährt 3.12 — eine Probe, die sich auf
    #: `imaplib` stützt, wäre lokal rot und dort grün (#438).
    _STEUERZEICHEN = re.compile(r"[\x00\r\n]")

    def _pruefe(self, *args) -> None:
        """Dieselbe Ablehnung wie `imaplib.IMAP4._command`, mit deren Wortlaut."""
        for arg in args:
            if arg is None:
                continue
            if isinstance(arg, (bytes, bytearray)):
                arg = bytes(arg).decode("utf-8", "replace")
            if self._STEUERZEICHEN.search(str(arg)):
                raise ValueError("NUL, CR and LF not allowed in commands")

    def __init__(self, ordner: dict[str, list[tuple[bytes, datetime]]] | None = None, *,
                 sonder: dict[str, str] | None = None,
                 verbindungsfehler: BaseException | None = None,
                 login_fehler: str | None = None,
                 append_wirkt: bool = True,
                 append_fehler: BaseException | None = None,
                 verschieben_erlaubt: bool = False,
                 faehigkeiten: tuple[str, ...] = ("IMAP4REV1", "UIDPLUS", "MOVE")):
        self.ordner: dict[str, list[Eintrag]] = {}
        self._naechste_uid = 100
        for name, nachrichten in (ordner or {}).items():
            self.ordner[name] = []
            for roh, zeit in nachrichten:
                self._lege_ab(name, roh, zeit)
        self.sonder = sonder if sonder is not None else {
            "INBOX": "", "Gesendete Elemente": "\\Sent", "Entw&APw-rfe": "\\Drafts"}
        for name in self.sonder:
            self.ordner.setdefault(name, [])
        self.verbindungsfehler = verbindungsfehler
        self.login_fehler = login_fehler
        self.append_wirkt = append_wirkt
        self.append_fehler = append_fehler
        self.verschieben_erlaubt = verschieben_erlaubt
        #: Wie `imaplib.IMAP4.capabilities` — `falzmarke.ablage` liest daraus,
        #: ob der Server `MOVE` kennt, statt es anzunehmen.
        self.capabilities = tuple(faehigkeiten)
        #: Jeder Befehl mit seinen Argumenten, in Reihenfolge.
        self.protokoll: list[tuple] = []
        self.verbindungen: list[tuple] = []
        self.angemeldet: list[tuple[str, str]] = []
        self.ausgewaehlt: str | None = None
        self.abgemeldet = 0

    # ── als Klasse aufrufbar, wie imaplib.IMAP4(host, port, timeout=…) ──────
    def __call__(self, host, port=143, timeout=None):
        self.verbindungen.append((host, port, timeout))
        if self.verbindungsfehler is not None:
            raise self.verbindungsfehler
        return self

    def _lege_ab(self, name: str, roh: bytes, zeit: datetime, flags: str = "") -> Eintrag:
        self._naechste_uid += 1
        eintrag = Eintrag(self._naechste_uid, roh, zeit, flags)
        self.ordner.setdefault(name, []).append(eintrag)
        return eintrag

    @staticmethod
    def _name(mailbox: str) -> str:
        if len(mailbox) >= 2 and mailbox[0] == mailbox[-1] == '"':
            return mailbox[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        return mailbox

    # ── erlaubte Befehle ──────────────────────────────────────────────────
    def login(self, user, password):
        self.protokoll.append(("LOGIN", user))
        if self.login_fehler:
            raise imaplib.IMAP4.error(self.login_fehler)
        self.angemeldet.append((user, password))
        return "OK", [b"LOGIN completed."]

    def list(self, directory='""', pattern="*"):
        self._pruefe(directory, pattern)
        self.protokoll.append(("LIST", directory, pattern))
        zeilen = []
        for name, kennzeichen in self.sonder.items():
            attribute = " ".join(a for a in ("\\HasNoChildren", kennzeichen) if a)
            zeilen.append(f'({attribute}) "/" "{name}"'.encode())
        return "OK", zeilen

    def select(self, mailbox="INBOX", readonly=False):
        self._pruefe(mailbox)
        name = self._name(mailbox)
        self.protokoll.append(("EXAMINE" if readonly else "SELECT", name))
        if not readonly and not self.verschieben_erlaubt:
            raise AssertionError(f"SELECT ohne readonly auf {name} — das Postfach wird nur gelesen")
        if name not in self.ordner:
            return "NO", [b"Folder not found."]
        self.ausgewaehlt = name
        return "OK", [str(len(self.ordner[name])).encode()]

    def uid(self, befehl, *args):
        self._pruefe(befehl, *args)
        befehl = befehl.upper()
        self.protokoll.append(("UID " + befehl, *args))
        if self.ausgewaehlt is None:
            raise imaplib.IMAP4.error("kein Ordner ausgewählt")
        nachrichten = self.ordner[self.ausgewaehlt]
        if befehl == "SEARCH":
            kriterien = [a for a in args if a is not None]
            if kriterien and kriterien[0].upper() == "SINCE":
                seit = datetime.strptime(kriterien[1], "%d-%b-%Y").date()
                treffer = [n for n in nachrichten if n.angekommen.date() >= seit]
            elif kriterien and kriterien[0].upper() == "HEADER":
                feld, wert = kriterien[1], self._name(kriterien[2])
                treffer = [n for n in nachrichten if _kopfzeile_enthaelt(n.roh, feld, wert)]
            else:
                treffer = list(nachrichten)
            return "OK", [" ".join(str(n.uid) for n in treffer).encode()]
        if befehl == "FETCH":
            menge, teile = args
            if "BODY.PEEK" not in teile:
                raise AssertionError(f"FETCH ohne PEEK setzt \\Seen: {teile}")
            uids = {int(u) for u in str(menge).split(",") if u}
            antwort: list = []
            for nummer, n in enumerate(nachrichten, 1):
                if n.uid not in uids:
                    continue
                if "HEADER.FIELDS" in teile:
                    felder = re.search(r"HEADER\.FIELDS \(([^)]*)\)", teile).group(1).split()
                    zeilen = [z for z in _kopfzeilen(n.roh)
                              if z.split(b":", 1)[0].decode("utf-8", "replace").upper() in felder]
                    literal = b"\r\n".join(zeilen) + b"\r\n\r\n"
                    meta = (f'{nummer} (UID {n.uid} INTERNALDATE "{_internaldate(n.angekommen)}" '
                            f'BODY[HEADER.FIELDS ({" ".join(felder)})] {{{len(literal)}}}')
                else:
                    literal = n.roh
                    meta = f"{nummer} (UID {n.uid} BODY[] {{{len(literal)}}}"
                antwort += [(meta.encode(), literal), b")"]
            return "OK", antwort
        if befehl == "MOVE":
            if not self.verschieben_erlaubt:
                raise AssertionError("UID MOVE ändert das Postfach — verboten")
            menge, ziel = args
            ziel = self._name(ziel)
            if ziel not in self.ordner:
                return "NO", [b"Folder not found."]
            uids = {int(u) for u in str(menge).split(",") if u}
            bewegt = [n for n in nachrichten if n.uid in uids]
            self.ordner[self.ausgewaehlt] = [n for n in nachrichten if n.uid not in uids]
            self.ordner[ziel].extend(bewegt)
            return "OK", [f"[COPYUID 1 {menge} {menge}] MOVE completed.".encode()]
        raise AssertionError(f"UID {befehl} ist hier nicht vorgesehen")

    def append(self, mailbox, flags, date_time, message):
        self._pruefe(mailbox, flags)
        name = self._name(mailbox)
        self.protokoll.append(("APPEND", name, flags))
        if self.append_fehler is not None:
            raise self.append_fehler
        if name not in self.ordner:
            return "NO", [b"Folder not found."]
        if self.append_wirkt:
            self._lege_ab(name, bytes(message), datetime.now(timezone.utc), flags)
        return "OK", [b"[APPENDUID 1 999] APPEND completed."]

    def logout(self):
        self.protokoll.append(("LOGOUT",))
        self.abgemeldet += 1
        return "BYE", [b"bye"]

    # ── verboten ──────────────────────────────────────────────────────────
    def _verboten(self, name):
        def wirf(*_a, **_k):
            raise AssertionError(f"{name} ändert das Postfach — verboten")
        return wirf

    def __getattr__(self, name):
        if name in {"store", "expunge", "copy", "move", "delete", "create", "rename",
                    "subscribe", "unsubscribe", "setacl", "deleteacl", "setquota"}:
            return self._verboten(name.upper())
        raise AttributeError(name)

    # ── Auswertung ────────────────────────────────────────────────────────
    def befehle(self, art: str) -> list[tuple]:
        return [p for p in self.protokoll if p[0] == art]


def nachricht(*, an: str = "paula@example.org", betreff: str = "Angebot",
              text: str = "Hallo Paula,\n\ndanke.\n", datum: datetime | None = None,
              von: str = "joe@example.org", kopf: dict | None = None,
              html: str | None = None, kennung: str | None = None,
              roh_kopf: dict | None = None) -> bytes:
    """Eine gesendete Mail als Bytes — so, wie sie im Gesendet-Ordner liegt.

    `kopf` geht durch `EmailMessage`, `roh_kopf` **nicht**: Dessen Zeilen werden
    wortgetreu vorangestellt, mit dem Umbruch, den der Aufrufer hineinschreibt.

    Beides gibt es, weil die Policy von `EmailMessage` nicht über Fassungen
    hinweg gleich arbeitet: Eine `Message-ID` von über 78 Zeichen schreibt
    Python 3.12 als `=?utf-8?q?=3Ckunde-…?=` und faltet das kodierte Wort,
    Python 3.14 lässt die ID stehen und faltet daneben (gemessen 29.10.2026).
    Eine Probe über einen gefalteten Bezug wäre damit auf der CI-Fassung eine
    andere Probe als lokal — `roh_kopf` nimmt ihr diese Abhängigkeit (#438).
    """
    from email.message import EmailMessage

    m = EmailMessage()
    m["From"] = von
    m["To"] = an
    m["Subject"] = betreff
    m["Date"] = format_datetime(datum or datetime.now(timezone.utc))
    # Über `kennung` ersetzbar, nicht ergänzbar: `m[name] = wert` hängt bei
    # EmailMessage eine ZWEITE Kopfzeile an, und zwei Message-IDs machen jede
    # Zuordnung über sie wertlos (#431).
    m["Message-ID"] = kennung or "<test@example.org>"
    for name, wert in (kopf or {}).items():
        m[name] = wert
    if text is not None:
        m.set_content(text)
        if html is not None:
            m.add_alternative(html, subtype="html")
    else:
        m.set_content(html or "", subtype="html")
    vorweg = b"".join(f"{name}: {wert}\r\n".encode()
                      for name, wert in (roh_kopf or {}).items())
    return vorweg + m.as_bytes()
