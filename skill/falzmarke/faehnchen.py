"""Das Fähnchen an der Ursprungsmail eines Antwortentwurfs (#549, ADR 0063).

`aufraeumen` legt eine Mail ab, sobald eine Antwort mit passendem `In-Reply-To`
gesendet ist (ADR 0061). Ob die Antwort die Sache erledigt oder nur vertröstet,
sieht der Lauf nicht. Eine Mail mit Fähnchen (`\\Flagged`) bleibt aber liegen
(#478). Beim Entwurf ist die Unterscheidung bekannt: Wer mit falzmarke antwortet,
schreibt `erledigt: ja` ins Frontmatter, wenn die Antwort abschließt. Fehlt das
Feld, setzt `email --oeffnen` das Fähnchen an der Mail, auf die geantwortet
wird. Ein vergessenes Feld lässt so eine Mail zu viel im Eingang, keine zu wenig.

Das dritte Modul des Pakets, das im Postfach etwas ändert, neben `ablage` und
`entwurfsablage`. Es steht nicht in `postfach`, damit dessen Zusage „nur lesend,
der einzige schreibende Befehl ist `APPEND`“ wahr bleibt.

**Ein ändernder Befehl: `UID STORE <uid> +FLAGS (\\Flagged)`.** Nur dieses Flag,
nur hinzufügen, an genau einer UID. Kein `-FLAGS`, kein `\\Deleted`, kein
`\\Seen`, kein Verschieben. Ein Fähnchen, das schon steht, wird nicht noch einmal
gesetzt. Entfernt wird es nie: Ob die Sache inzwischen erledigt ist, weiß nur der
Mensch. `tests/test_faehnchen.py` liest das am Syntaxbaum nach.

**Genau eine Mail oder keine.** Gesucht wird im Eingang des Absenderkontos nach
der `Message-ID`, exakt verglichen (`Postfach.suche_kennung`). Liegt sie dort
nicht (längst abgelegt, anderes Konto) oder tragen mehrere Mails dieselbe
Kennung, wird nichts geändert und der Grund genannt. Die UID gilt nur zusammen
mit der UIDVALIDITY des Eingangs (#495): Nennt das `SELECT` eine andere als das
`EXAMINE` der Suche, geht kein `STORE` hinaus.

**Nie ein Abbruch.** Der Entwurf steht schon, wenn dieses Modul läuft. Jeder
Fehler wird zu einem Zustand mit Grund. `setze` wirft nicht.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, NamedTuple

from falzmarke import postfach

#: Der Eingang. IMAP schreibt ihn groß und ohne Kennzeichen vor (RFC 3501, 5.1).
EINGANG = "INBOX"

#: Das eine Flag und die eine Art, es zu setzen.
FLAG = "\\Flagged"

#: Wie lange die ganze Sitzung dauern darf, Anmeldung eingeschlossen. Dieselbe
#: Frist wie für das Ablegen des Entwurfs (`oeffnen.FRIST_POSTFACH_S`).
FRIST_S = 30

Zustand = Literal["gesetzt", "schon_da", "nicht_noetig", "nicht_gesetzt"]


class Faehnchen(NamedTuple):
    """Was mit dem Fähnchen an der Ursprungsmail geschah."""

    zustand: Zustand
    #: Warum `nicht_gesetzt`; bei `gesetzt` ein Vorbehalt, falls nicht nachgelesen.
    grund: str | None = None
    #: Die UID der Ursprungsmail im Eingang, wo sie gefunden wurde.
    uid: str | None = None
    #: Ihr Betreff, für die Zeile im Lauf.
    betreff: str = ""


def ist_erledigt(wert: object) -> bool:
    """`erledigt: ja` aus dem Frontmatter. Alles andere heißt: nicht erledigt.

    PyYAML liest `ja` und `nein` als Text, `yes`, `true` und `on` als `True`.
    Gezählt wird nur ein eindeutiges Ja. Ein Tippfehler setzt das Fähnchen, und
    das ist die sichere Seite.
    """
    if wert is True:
        return True
    return isinstance(wert, str) and wert.strip().casefold() == "ja"


def setze(adresse: str, antwort_auf: str, *, erledigt: bool,
          umgebung: Mapping[str, str] | None = None) -> Faehnchen:
    """Setzt `\\Flagged` an der Mail im Eingang von `adresse`, deren Message-ID `antwort_auf` ist."""
    if erledigt:
        return Faehnchen("nicht_noetig")
    # Nicht den Leerraum zusammenziehen: Aus einem Umbruch würde ein Leerzeichen,
    # und `sendbar` ließe durch, was es abweisen soll. `kennungen` nimmt die
    # Kennungen in spitzen Klammern einzeln heraus, wie `ablage` es tut (#438).
    gefunden = postfach.kennungen(str(antwort_auf or ""))
    if not gefunden:
        return Faehnchen("nicht_gesetzt", "der Entwurf nennt keine Ursprungsmail")
    if len(gefunden) > 1:
        return Faehnchen("nicht_gesetzt",
                         f"`In-Reply-To` nennt {len(gefunden)} Kennungen — welche Mail gemeint "
                         "ist, wird nicht geraten")
    kennung = gefunden[0]
    if not postfach.sendbar(kennung):
        return Faehnchen("nicht_gesetzt",
                         "die Message-ID der Ursprungsmail ist kein ASCII oder enthält einen "
                         "Umbruch — so wird sie nicht gesucht")
    try:
        with postfach.verbinde(adresse, umgebung=umgebung, frist=FRIST_S) as sitzung:
            return _setze_in(sitzung, kennung)
    except postfach.PostfachFehler as fehler:
        return Faehnchen("nicht_gesetzt", str(fehler))
    except Exception as fehler:  # noqa: BLE001 — der Entwurf steht, nichts darf abbrechen
        return Faehnchen("nicht_gesetzt", f"{type(fehler).__name__}: {fehler}")


def _setze_in(sitzung: postfach.Postfach, kennung: str) -> Faehnchen:
    treffer = sitzung.suche_kennung(EINGANG, kennung)
    if not treffer:
        return Faehnchen("nicht_gesetzt",
                         f"die Ursprungsmail {kennung} liegt nicht im Eingang dieses Kontos "
                         "(abgelegt, gelöscht oder an ein anderes Konto gegangen)")
    if len(treffer) > 1:
        uids = ", ".join(k.uid for k in treffer)
        return Faehnchen("nicht_gesetzt",
                         f"{len(treffer)} Mails im Eingang tragen die Message-ID {kennung} "
                         f"(UIDs {uids}) — welche gemeint ist, wird nicht geraten")
    kopf = treffer[0]
    if kopf.fahnen is not None and "\\flagged" in kopf.fahnen:
        return Faehnchen("schon_da", uid=kopf.uid, betreff=kopf.betreff)
    geplant = sitzung.uidvalidity.get(EINGANG)
    if geplant is None:
        return Faehnchen("nicht_gesetzt",
                         "der Server nannte für den Eingang keine UIDVALIDITY — ob die UID "
                         "beim Setzen noch dieselbe Mail meint, ist nicht zu prüfen",
                         uid=kopf.uid, betreff=kopf.betreff)
    zitiert = postfach._zitiert
    # SELECT, nicht EXAMINE: In einem nur lesend geöffneten Ordner setzt der
    # Server keine Flags. Gewählt wird allein der Eingang.
    sitzung._befehl(f"Ordner „{EINGANG}“ nicht wählbar", sitzung._v.select, zitiert(EINGANG))
    jetzt = sitzung._lies_uidvalidity()
    if jetzt != geplant:
        return Faehnchen("nicht_gesetzt",
                         f"die UIDVALIDITY des Eingangs wechselte zwischen Suche und Setzen "
                         f"({geplant} → {jetzt}) — die UID könnte eine andere Mail meinen",
                         uid=kopf.uid, betreff=kopf.betreff)
    sitzung._befehl("Fähnchen setzen", sitzung._v.uid, "STORE", kopf.uid, "+FLAGS",
                    f"({FLAG})")
    # Nachlesen statt der Antwort glauben: `OK` heißt angenommen, nicht gesetzt.
    nach = [k for k in sitzung.koepfe(EINGANG, uids=[kopf.uid]) if k.uid == kopf.uid]
    fahnen = nach[0].fahnen if nach else None
    if fahnen is None:
        return Faehnchen("gesetzt", "der Server nannte danach keine Flags — nicht nachgelesen",
                         uid=kopf.uid, betreff=kopf.betreff)
    if "\\flagged" not in fahnen:
        return Faehnchen("nicht_gesetzt",
                         "der Server nahm den Befehl an, die Mail trägt danach aber kein "
                         "Fähnchen", uid=kopf.uid, betreff=kopf.betreff)
    return Faehnchen("gesetzt", uid=kopf.uid, betreff=kopf.betreff)


def zeile(ergebnis: Faehnchen, adresse: str) -> str:
    """Die eine Zeile für den Lauf. `OK` für gesetzt und schon da, sonst `HINWEIS`."""
    wo = f"„{ergebnis.betreff}“ im Eingang von {adresse}" if ergebnis.betreff else \
        f"der Ursprungsmail im Eingang von {adresse}"
    if ergebnis.zustand == "gesetzt":
        vorbehalt = f" ({ergebnis.grund})" if ergebnis.grund else ""
        return (f"OK  Fähnchen gesetzt an {wo}{vorbehalt} — `aufraeumen` lässt sie liegen, "
                "bis du es entfernst")
    if ergebnis.zustand == "schon_da":
        return f"OK  Fähnchen stand schon an {wo} — unverändert"
    if ergebnis.zustand == "nicht_noetig":
        # Nachgesehen wird nicht: Ein früherer Entwurf ohne `erledigt` kann das
        # Fähnchen schon gesetzt haben, und entfernt wird es nie (Nachreview #553).
        return ("HINWEIS  erledigt: ja — kein Fähnchen gesetzt. Ohne Fähnchen legt "
                "`aufraeumen` die Ursprungsmail ab, sobald die Antwort gesendet ist;\n"
                "         ein früher gesetztes bleibt stehen, bis du es entfernst")
    return (f"HINWEIS  Fähnchen nicht gesetzt: {ergebnis.grund}\n"
            "         Soll die Mail im Eingang bleiben, das Fähnchen von Hand setzen.")
