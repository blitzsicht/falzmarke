"""Eine IMAP-Verbindung, deren Frist für die ganze Sitzung gilt (ADR 0051).

`imaplib` legt sein `timeout` auf jeden einzelnen Empfang. Bis zum Review von
#570 begann die Frist von `postfach.verbinde` deshalb erst nach dem
Konstruktor. Begrüßung und `CAPABILITY` durften je die volle Frist brauchen,
und ein Server, der knapp darunter Byte für Byte tröpfelt, hielt eine Sitzung
beliebig lange offen. Gemessen am 06.11.2026 mit einer Frist von 3 s: 8,8 s
(3.12) und 11,8 s (3.14, `logout` wartet nach einem Zeitlimit erneut) bei
langsamer Begrüßung, 35,6 s beim Tröpfeln.

Ein eigenes Modul, weil `postfach` zusagt, `socket` nur für zwei Fehlerklassen
zu lesen (`tests/test_postfach.py`). Hier wird kein Netzweg neben IMAP geöffnet.
Der Socket, den `imaplib` selbst aufbaut, wird nur umhüllt.
"""

from __future__ import annotations

import imaplib
import io
import socket
import time


class _SocketMitFrist:
    """Ein Socket, der vor jedem Empfangen und Senden nur noch die Restzeit wartet.

    Läuft die Frist ab, kommt `TimeoutError`, wie bei einem gewöhnlichen
    Zeitlimit. `postfach._vergeht` liest ihn deshalb als vorübergehend. Beide
    Lesewege von `imaplib` laufen hier durch. `IMAP4.open` ruft in jeder Fassung
    `makefile('rb')`. Bis 3.13 liest `imaplib` aus dieser Datei, und `SocketIO`
    holt die Bytes über `recv_into` der Hülle. Ab 3.14 liest es selbst über
    `sock.recv`; die Datei liegt dann nur noch in `_file`, für die veraltete
    Eigenschaft `file` und für `shutdown`, das sie schließt (gezählt am
    07.11.2026: 3.12 je einmal `makefile` und dreimal `recv_into`, 3.14 einmal
    `makefile` und dreimal `recv`). Alles andere reicht `__getattr__` unverändert
    durch.
    """

    def __init__(self, sock: socket.socket, bis: float):
        self._sock = sock
        self._bis = bis

    def _restzeit(self) -> None:
        rest = self._bis - time.monotonic()
        if rest <= 0:
            raise TimeoutError("die Frist der Sitzung ist abgelaufen")
        self._sock.settimeout(rest)

    def recv(self, *args):
        self._restzeit()
        return self._sock.recv(*args)

    def recv_into(self, *args):
        self._restzeit()
        return self._sock.recv_into(*args)

    def sendall(self, *args):
        self._restzeit()
        return self._sock.sendall(*args)

    def makefile(self, mode: str = "rb"):
        if mode != "rb":  # pragma: no cover — imaplib liest nur
            raise ValueError(f"nur lesend, nicht {mode!r}")
        return io.BufferedReader(socket.SocketIO(self, "rb"))

    def __getattr__(self, name):
        return getattr(self._sock, name)


class ImapMitFrist(imaplib.IMAP4):
    """`imaplib.IMAP4`, dessen `timeout` die Dauer der ganzen Sitzung begrenzt.

    Die Frist beginnt vor dem Verbindungsaufbau. Begrüßung, `CAPABILITY`, jeder
    Befehl und das Abmelden ziehen von derselben Zeit ab. Ohne `timeout` bleibt
    alles wie bei `imaplib.IMAP4`.
    """

    def __init__(self, host: str = "", port: int = 143, timeout: float | None = None):
        self._frist_bis = None if timeout is None else time.monotonic() + timeout
        super().__init__(host, port, timeout)

    def _create_socket(self, timeout):
        sock = super()._create_socket(timeout)
        return sock if self._frist_bis is None else _SocketMitFrist(sock, self._frist_bis)
