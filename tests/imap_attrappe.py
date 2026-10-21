"""Ein IMAP-Server im Speicher — die Attrappe für `falzmarke.postfach` (ADR 0051).

Sie wird so bedient wie `imaplib.IMAP4` und antwortet in dessen Form: `(typ,
daten)`, FETCH als Liste aus `(meta, literal)` und `b")"`. Damit läuft in den
Tests die **echte** Klasse `postfach.Postfach` gegen sie, nicht ein zweiter
Nachbau — geprüft wird, was später gegen den Proxy läuft.

Alles, was im Postfach etwas ändern würde außer `APPEND`, ist hier verboten und
wirft: `STORE`, `EXPUNGE`, `COPY`, `MOVE`, `DELETE`, `CREATE`, `RENAME`. Ein
Test, der einen solchen Aufruf auslöst, wird rot — das ist die Zusage „nie
löschen, nie verschieben, keine Flags ändern“ als Prüfung.
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


class ImapAttrappe:
    """Nimmt die Rolle von `imaplib.IMAP4` ein: aufrufen wie die Klasse, dann bedienen."""

    #: Kein Socket — `postfach` fragt danach, um die Frist nachzustellen.
    sock = None

    def __init__(self, ordner: dict[str, list[tuple[bytes, datetime]]] | None = None, *,
                 sonder: dict[str, str] | None = None,
                 verbindungsfehler: BaseException | None = None,
                 login_fehler: str | None = None,
                 append_wirkt: bool = True,
                 append_fehler: BaseException | None = None):
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
        self.protokoll.append(("LIST", directory, pattern))
        zeilen = []
        for name, kennzeichen in self.sonder.items():
            attribute = " ".join(a for a in ("\\HasNoChildren", kennzeichen) if a)
            zeilen.append(f'({attribute}) "/" "{name}"'.encode())
        return "OK", zeilen

    def select(self, mailbox="INBOX", readonly=False):
        name = self._name(mailbox)
        self.protokoll.append(("EXAMINE" if readonly else "SELECT", name))
        if not readonly:
            raise AssertionError(f"SELECT ohne readonly auf {name} — das Postfach wird nur gelesen")
        if name not in self.ordner:
            return "NO", [b"Folder not found."]
        self.ausgewaehlt = name
        return "OK", [str(len(self.ordner[name])).encode()]

    def uid(self, befehl, *args):
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
                    kopf, _, _ = n.roh.partition(b"\r\n\r\n")
                    if kopf == n.roh:
                        kopf, _, _ = n.roh.partition(b"\n\n")
                    zeilen = []
                    aktuell = None
                    for zeile in re.split(rb"\r?\n", kopf):
                        if zeile[:1] in (b" ", b"\t") and aktuell is not None:
                            zeilen[-1] += b"\r\n" + zeile
                            continue
                        name = zeile.split(b":", 1)[0].decode().upper()
                        aktuell = name if name in felder else None
                        if aktuell:
                            zeilen.append(zeile)
                    literal = b"\r\n".join(zeilen) + b"\r\n\r\n"
                    meta = (f'{nummer} (UID {n.uid} INTERNALDATE "{_internaldate(n.angekommen)}" '
                            f'BODY[HEADER.FIELDS ({" ".join(felder)})] {{{len(literal)}}}')
                else:
                    literal = n.roh
                    meta = f"{nummer} (UID {n.uid} BODY[] {{{len(literal)}}}"
                antwort += [(meta.encode(), literal), b")"]
            return "OK", antwort
        raise AssertionError(f"UID {befehl} ist hier nicht vorgesehen")

    def append(self, mailbox, flags, date_time, message):
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


def nachricht(*, an: str = "nico@example.org", betreff: str = "Angebot",
              text: str = "Hallo Nico,\n\ndanke.\n", datum: datetime | None = None,
              von: str = "joe@example.org", kopf: dict | None = None,
              html: str | None = None) -> bytes:
    """Eine gesendete Mail als Bytes — so, wie sie im Gesendet-Ordner liegt."""
    from email.message import EmailMessage

    m = EmailMessage()
    m["From"] = von
    m["To"] = an
    m["Subject"] = betreff
    m["Date"] = format_datetime(datum or datetime.now(timezone.utc))
    m["Message-ID"] = "<test@example.org>"
    for name, wert in (kopf or {}).items():
        m[name] = wert
    if text is not None:
        m.set_content(text)
        if html is not None:
            m.add_alternative(html, subtype="html")
    else:
        m.set_content(html or "", subtype="html")
    return m.as_bytes()
