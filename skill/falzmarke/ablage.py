"""Beantwortete Eingangspost in die Ablage des Kontos (#431, ADR 0061).

Eines von zwei Modulen des Pakets, die eine Nachricht im Postfach **bewegen**;
das andere ist `entwurfsablage` (ADR 0062). Es steht neben `postfach` und nicht
darin, weil dessen Zusage „nur lesend, der einzige schreibende Befehl ist
`APPEND`“ wahr bleiben soll — sie ist in `postfach.py`, `tests/test_postfach.py`
und `tests/imap_attrappe.py` festgehalten.

**Ein ändernder Befehl, und es ist `UID MOVE`.** Kein `COPY`, kein
`STORE \\Deleted`, kein `EXPUNGE`, kein `DELETE`, kein `CREATE`: Ein
Verschieben, das aus drei Schritten besteht, kann in der Mitte abbrechen und
lässt die Nachricht dann zweimal oder nirgends liegen. Nennt `CAPABILITY` kein
`MOVE`, wird nichts verschoben und das gesagt — ein Nachbau wird nicht
gewagt. `tests/test_ablage.py` liest das am Syntaxbaum nach, mit Gegenprobe.

**Woraus „erledigt“ folgt.** Jede gesendete Antwort trägt `In-Reply-To` mit der
`Message-ID` der Nachricht, die sie beantwortet. Liegt diese Nachricht noch im
Eingang, ist sie bearbeitet. Das Tagebuch der Entwurfsbrücke taugt dafür nicht:
Es benennt bei einer Antwort die Quelle nicht (`ursprung.uid` ist dort `null`,
gemessen 28.10.2026 an 90 `gesendet`-Zeilen). Nebenwirkung, und sie ist
gewollt: Auch eine von Hand aus Thunderbird geschriebene Antwort räumt auf.

**Das Ziel wird nie geraten und nie angelegt.** Es kommt aus `email.ablage` im
Profil; fehlt die Zeile, gilt der Sonderordner `\\Archive` (RFC 6154), und den
kennzeichnet an den Microsoft-Konten des Betreibers keiner. Dann wandert
nichts. Ausgeschlossen sind der Gesendet-Ordner, die Entwürfe, der Papierkorb,
der Spam-Ordner und der Eingang selbst — geprüft an den Kennzeichen des
Servers, nicht an Namen in einer Liste.

**Was liegen bleibt, auch wenn es beantwortet ist** (#478). Eine Mail mit
Fähnchen (`\\Flagged`) wartet auf etwas und gehört in den Eingang. Nennt der
Server ihre Flags nicht, ist das Fähnchen unbekannt, und auch dann bleibt sie
liegen. `--trotz-faehnchen` hebt beides auf, ausdrücklich und nur für diesen
Lauf. Das Fähnchen wandert dann mit ins Archiv.

**`--faehnchen-weg`** (#566) gilt nur mit `--uid`. Es legt ab wie
`--trotz-faehnchen` und nimmt vorher das Fähnchen von den genannten Mails. Der
Befehl dafür steht nicht hier, sondern in `faehnchen.nimm_weg`: Dieses Modul
bleibt beim einen `UID MOVE`. Steht das Fähnchen danach noch, wandert keine Mail.

**Benannte Mails** (`--uid`, #478) sind erledigt, weil der Bediener es sagt,
nicht wegen einer Antwort. Es bleibt bei denselben Sperren und demselben einen
`UID MOVE`. Fehlt eine der genannten UIDs im Eingang, wandert keine: Eine
Liste, die nicht mehr stimmt, ist kein Auftrag für den Rest. Dasselbe gilt,
wenn eine genannte Mail liegen bliebe, etwa wegen eines Fähnchens
(Nachreview von #494, Befund 5): Wer die UID nannte, hat das Fähnchen
vermutlich übersehen. Eine UID gilt nur zusammen mit der UIDVALIDITY des
Eingangs (#495). `--machen` nimmt deshalb den Wert der Anzeige mit, und
weicht er ab, wandert keine. Vor jedem `UID MOVE` wird er am `SELECT` noch
einmal verglichen.

**`{jahr}` im Ziel** (#478) wird je Mail zum Jahr ihrer Ankunft im Postfach
(INTERNALDATE, Ortszeit). Thunderbird legt mit `archive_granularity 1` anders
ab: Es nimmt `msgHdr.date` (`MessageArchiver.sys.mjs`). falzmarke bleibt bei
der Ankunft, weil der Absender sie nicht fälschen kann und der Server sie zu
jeder Nachricht führt. Eine Mail vom 31.12. um 23:50, die erst am 01.01.
ankommt, liegt deshalb bei falzmarke im neuen Jahr und bei Thunderbird
womöglich im alten. Fehlt einer der Jahresordner, wandert keine Mail des
Laufs: Sonst wäre die eine Hälfte abgelegt und die andere still nicht.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple

from falzmarke import faehnchen, postfach

#: Der Eingang. IMAP schreibt ihn groß und ohne Kennzeichen vor (RFC 3501, 5.1).
EINGANG = "INBOX"

#: Wie weit zurück gesendete Antworten angesehen werden, in Tagen. Die
#: beantwortete Nachricht darf beliebig alt sein — gesucht wird sie über die
#: `Message-ID`, nicht über ein Datum.
SEIT_TAGEN = 30

#: Das längste Fenster, das `--seit` annimmt. Zehn Jahre: Darüber bricht
#: `heute - timedelta(days=…)` mit `OverflowError`, und ein Fenster dieser
#: Länge liest ohnehin nur die jüngsten `postfach.GRENZE` Mails (#438).
SEIT_MAX = 3650

#: Zeitlimit der ganzen Sitzung. Großzügiger als `postfach.FRIST_S`: Dort hält
#: ein hängender Proxy das Öffnen eines Entwurfs auf, hier läuft ein Befehl,
#: den jemand bewusst gestartet hat.
FRIST_S = 60.0

#: Ordner, die nie eine Ablage sind — Kennzeichen (RFC 6154) auf den Grund.
#: Kennzeichen statt Namen, weil „Gesendete Elemente“, „Sent Items“ und
#: „Éléments envoyés“ dasselbe sind und eine Namensliste immer eine Sprache
#: zu wenig kennt.
VERBOTENE_ZIELE = {
    "\\sent": "er ist Datenquelle der Sendesperre und von `status` (ADR 0051), keine Ablage",
    "\\drafts": "dort liegen die Entwürfe, aus denen `status` seine Aussage zieht",
    "\\trash": "der Papierkorb ist keine Ablage",
    "\\junk": "der Spam-Ordner ist keine Ablage",
}

#: Das Fähnchen, wie `postfach.Kopf.fahnen` es führt (klein).
FAEHNCHEN = "\\flagged"

#: Der eine Platzhalter in `email.ablage`: das Jahr der Ankunft (#478).
JAHR = "{jahr}"


class AblageFehler(Exception):
    """Ein Grund in einem Satz — er wandert unverändert in die Ausgabe."""


class ZugAbgebrochen(AblageFehler):
    """`UID MOVE` war gesendet, als der Lauf abbrach.

    Nur dann kann der Server schon etwas bewegt haben. Bricht der Lauf vorher
    ab — kein MOVE in CAPABILITY, der Eingang nicht wählbar —, ist sicher nichts
    geschehen, und der Bericht soll das auch so sagen (Review von #459).
    """


class Zug(NamedTuple):
    """Eine Nachricht im Eingang und die Antwort, die sie erledigt hat.

    Bei `--uid` gibt es keine Antwort: `antwort_betreff` ist dann leer.
    """

    uid: str
    betreff: str
    datum: datetime | None
    #: Die `Message-ID`, über die die Zuordnung läuft.
    kennung: str
    antwort_betreff: str
    antwort_datum: datetime | None
    #: Der Absender der Nachricht im Eingang.
    von: str = ""
    #: Ankunft im Postfach (INTERNALDATE) — sie bestimmt `{jahr}`.
    ankunft: datetime | None = None
    #: Die Flags, klein; `None`, wenn der Server sie nicht nannte.
    fahnen: tuple[str, ...] | None = None
    #: Das Ziel dieser Nachricht, lesbar und wie der Server es führt. Bei
    #: `{jahr}` je Nachricht verschieden, sonst das eine Ziel des Laufs.
    ziel: str | None = None
    ziel_server: str | None = None


class Liegt(NamedTuple):
    """Eine Nachricht, die erledigt wäre und trotzdem im Eingang bleibt."""

    zug: Zug
    grund: str


class Bericht(NamedTuple):
    """Was `aufraeumen` für einen Absender gefunden und getan hat."""

    adresse: str
    #: Der Ablageordner, lesbar. `None`, wenn keiner feststeht.
    ziel: str | None
    #: Warum es nicht weitergeht. Gesetzt heißt: der Lauf ist nicht zu Ende
    #: gekommen; was trotzdem geschah, steht in `verschoben` und `zug_gesendet`.
    grund: str | None
    seit: date | None
    #: Gesendete Antworten im Fenster — die Grundmenge.
    antworten: int
    #: Antworten, deren Quelle nicht (mehr) im Eingang liegt: längst erledigt.
    nicht_im_eingang: int
    zuege: tuple[Zug, ...]
    #: Tatsächlich bewegt. Ohne `--machen` immer 0.
    verschoben: int
    #: Was den Befund einschränkt, ohne ihn zu verhindern — eine gekappte
    #: Suche etwa. Geht in **beide** Darstellungen: Ein Kanal, den nur der
    #: Text hat, schweigt unter `--json` (#438).
    hinweise: tuple[str, ...] = ()
    #: Das Ziel, wie der Server es führt (UTF-7). `ziel` daneben ist dasselbe,
    #: nur lesbar. Steht hier, damit der Zug den Ordner nicht ein zweites Mal
    #: bestimmen muss — zwei Bestimmungen können verschieden ausfallen.
    ziel_server: str | None = None
    #: Brach der Lauf an einem gesendeten `UID MOVE` ab? Nur dann kann der
    #: Server vom Rest einen Teil bewegt haben. Was ein früherer Zug schon
    #: bewegt hat, zählt `verschoben`, nicht dieses Feld (Nachreview #494,
    #: Befund 3). Ohne Grund immer `False`.
    zug_gesendet: bool = False
    #: Was erledigt wäre und bleibt — Fähnchen, unbekannte Flags, kein Jahr.
    liegen: tuple[Liegt, ...] = ()
    #: Kamen die Nachrichten aus `--uid` statt aus Antworten?
    benannt: bool = False
    #: Die UIDVALIDITY des Eingangs beim Planen; `None`, wenn der Server keine
    #: nannte oder der Eingang nicht gelesen wurde. Die UIDs der Züge gelten
    #: nur zusammen mit ihr, und `verschiebe` vergleicht sie am SELECT (#495).
    uidvalidity: str | None = None
    #: War `--faehnchen-weg` gesetzt (#566)? Dann zeigt die Anzeige, an welcher
    #: Mail das Fähnchen mit `--machen` wegkommt.
    faehnchen_weg: bool = False
    #: Die UIDs, an denen das Fähnchen nachgelesen weg ist. Ohne `--machen` leer.
    faehnchen_entfernt: tuple[str, ...] = ()


# ── Das Ziel ────────────────────────────────────────────────────────────────

def ablageordner(sitzung: postfach.Postfach, wunsch: str | None) -> tuple[str | None, str | None]:
    """`(ordner, grund)` — der Ablageordner oder der Satz, warum es keinen gibt.

    `wunsch` ist `email.ablage` aus dem Profil, der Name wie der Server ihn
    führt. Ohne Wunsch wird `\\Archive` genommen, falls der Server ihn
    kennzeichnet. Geraten wird nie.
    """
    liste = sitzung.ordner_liste()
    nach_name = {name: kennzeichen for name, kennzeichen in liste}

    if wunsch:
        name = wunsch if wunsch in nach_name else postfach.utf7_kodieren(wunsch)
        if name not in nach_name:
            vorhanden = ", ".join(f"„{postfach.utf7_anzeige(n)}“" for n, _ in liste[:12])
            return None, (f"den Ordner „{_lesbar(wunsch)}“ aus `email.ablage` gibt es im Postfach nicht "
                          f"— falzmarke legt keinen an. Vorhanden sind: {vorhanden}")
        herkunft = "`email.ablage`"
    else:
        name = sitzung.sonderordner("\\Archive")
        if not name:
            return None, ("das Postfach kennzeichnet keinen Ordner mit `\\Archive`, und "
                          "`email.ablage` steht nicht im Profil — ohne Ziel wird nichts "
                          "verschoben, geraten wird nicht")
        herkunft = "das Kennzeichen `\\Archive`"

    kennzeichen = nach_name.get(name, ())
    for verboten, grund in VERBOTENE_ZIELE.items():
        if verboten in kennzeichen:
            return None, (f"„{postfach.utf7_anzeige(name)}“ ({herkunft}) trägt "
                          f"`{verboten}`: {grund}")
    if name.upper() == EINGANG:
        return None, "der Eingang kann nicht seine eigene Ablage sein"
    return name, None


# ── Der Plan ────────────────────────────────────────────────────────────────

def _lesbar(wunsch: str) -> str:
    """Der Wunsch aus dem Profil in Klartext — er darf in beiden Schreibweisen dastehen.

    `ablageordner` nimmt den Namen wörtlich oder kodiert ihn. Ein lesbarer Name
    mit `&` („R&D-Projekte“, „AT&T-Rechnungen“) ist kein gültiges UTF-7; dann
    bleibt er, wie er ist, statt den Lauf mit einem Traceback zu beenden.

    Bekannte Grenze (#515, Befund 4; genauer #522, Punkt 1): Ein lesbarer Name
    ist zugleich gültiges UTF-7 und wird still dekodiert, wenn er `&-` trägt
    („Kunden &-Co“ → „Kunden &Co“) oder zwischen `&` und `-` eine Base64-Folge,
    die ganze UTF-16-Einheiten ergibt. Das hängt an der Länge n der Folge: 6·n
    Bits, und der Rest nach den 16er-Einheiten muss unter 6 bleiben, also
    n = 3, 6, 8, 11, 14, 16, 19 … Drei Buchstaben reichen: Aus „R&Dev-Team“ wird
    „R“, U+0DEB, „Team“, aus „B&Bau-Rechnungen“ „B“, U+05AB, „Rechnungen“. Bei
    allen anderen Längen bleibt der Name stehen („R&D-Projekte“, „Q&A-Ablage“,
    „R&Devs-Team“). Gemessen am 05.11.2026 an je 2000 Zufallsfolgen aus
    Buchstaben, n = 1 bis 16: 3 → 100 %, 6 → 96 %, 8 → 94 %, 11 → 95 %,
    14 → 90 %, 16 → 89 %, alle übrigen 0 %. Die abgelehnten Folgen ergaben eine
    Surrogat-Einheit (geprüft bei 6 und 8).

    Welche Schreibweise gemeint war, sagt erst die Ordnerliste. Gemessen am
    05.11.2026: In zehn Profilen steht bei `email.ablage` kein `&`. Der Fall kommt
    nicht vor, und `ziel_server` bleibt davon unberührt, gezeigt wird nur der Name.
    Ist der Ordner gefunden, zeigt `_ziele_zuordnen` seinen Servernamen dekodiert;
    geraten wird hier nur noch für den Kopf des Berichts und für einen fehlenden
    Ordner (Nachreview von #527, Befund 3).

    Gerechnet wird wie bei einem Servernamen, mit `postfach.utf7_anzeige`. Die
    Grenze oben gilt nur hier: Ein Servername ist modified UTF-7, und was gültig
    dekodiert, ist so gemeint. Ein Name aus dem Profil kann lesbar gemeint sein.
    """
    return postfach.utf7_anzeige(wunsch)


def _ziel_vorab(sitzung: postfach.Postfach,
                wunsch: str | None) -> tuple[str | None, str | None, str | None]:
    """`(lesbar, server, grund)` — das Ziel des Laufs, bevor gelesen wird.

    Mit `{jahr}` steht der Ordner erst je Nachricht fest. Dann ist `server`
    leer, und `_ziele_zuordnen` prüft jeden Jahresordner einzeln — mit
    denselben Sperren wie hier.
    """
    if wunsch and JAHR in wunsch:
        # Lesbar wie ohne `{jahr}`: Steht der Wunsch in Server-Schreibweise
        # (`&APw-`) im Profil, zeigten Text und JSON sonst den kodierten Namen
        # (Nachreview #494, Befund 8).
        return _lesbar(wunsch), None, None
    ziel, grund = ablageordner(sitzung, wunsch)
    if ziel is None:
        return None, None, grund
    return postfach.utf7_anzeige(ziel), ziel, None


def _als_zug(kopf: postfach.Kopf, *, kennung: str = "", antwort: postfach.Kopf | None = None,
             ziel: str | None = None, ziel_server: str | None = None) -> Zug:
    return Zug(uid=kopf.uid, betreff=kopf.betreff, datum=kopf.datum, kennung=kennung,
               antwort_betreff=antwort.betreff if antwort else "",
               antwort_datum=antwort.datum if antwort else None,
               von=kopf.von, ankunft=kopf.ankunft, fahnen=kopf.fahnen,
               ziel=ziel, ziel_server=ziel_server)


def _ziele_zuordnen(sitzung: postfach.Postfach, wunsch: str | None, zuege: list[Zug], *,
                    trotz_faehnchen: bool) -> tuple[tuple[Zug, ...], tuple[Liegt, ...],
                                                    str | None]:
    """`(zuege, liegen, grund)` — wer wandert, wer bleibt, und ob der Lauf steht.

    Erst das Fähnchen, dann das Jahr: Eine Mail mit Fähnchen bleibt, auch
    wenn ihr Jahresordner fehlt, und soll dann nicht den Lauf anhalten.
    """
    gehen: list[Zug] = []
    liegen: list[Liegt] = []
    for zug in zuege:
        if not trotz_faehnchen and zug.fahnen is None:
            liegen.append(Liegt(zug, "Fähnchen unbekannt, der Server nannte keine Flags"))
        elif not trotz_faehnchen and FAEHNCHEN in zug.fahnen:
            liegen.append(Liegt(zug, "Fähnchen"))
        else:
            gehen.append(zug)
    if not (wunsch and JAHR in wunsch):
        return tuple(gehen), tuple(liegen), None

    geprueft: dict[str, tuple[str | None, str | None]] = {}
    zugeordnet: list[Zug] = []
    fehlend: list[str] = []
    for zug in gehen:
        if zug.ankunft is None:
            liegen.append(Liegt(zug, f"ohne Ankunftsdatum, das Jahr für „{wunsch}“ fehlt"))
            continue
        name = wunsch.replace(JAHR, str(zug.ankunft.astimezone().year))
        if name not in geprueft:
            geprueft[name] = ablageordner(sitzung, name)
        ordner, grund = geprueft[name]
        if ordner is None and grund not in fehlend:
            fehlend.append(grund)
        # Gefunden sagt der Server, wie der Ordner heißt; `_lesbar` rät nur, wenn er
        # fehlt (Nachreview von #527, Befund 3).
        lesbar = postfach.utf7_anzeige(ordner) if ordner else _lesbar(name)
        zugeordnet.append(zug._replace(ziel=lesbar, ziel_server=ordner))
    grund = None
    if fehlend:
        grund = ("; ".join(fehlend) + " — keine Mail dieses Laufs wandert, auch nicht "
                 "die mit vorhandenem Jahresordner")
    return tuple(zugeordnet), tuple(liegen), grund


#: Das Ende des Satzes, wenn der Zug am SELECT abbricht. Nicht „verschoben wird
#: nichts“: Bei `{jahr}` kann eine frühere Gruppe schon gewandert sein, und die
#: Zeile darunter sagt dann „1 davon verschoben“ (Nachreview #502, Befund 4).
#: Am Zug läuft immer `--machen`; der Satz nennt deshalb beides, was für die Neuanzeige wegfällt.
_SCHLUSS_AM_ZUG = ("kein weiterer Zug geht hinaus, erst ohne --machen und ohne --uidvalidity "
                   "neu anzeigen lassen")


def _schluss_der_anzeige(machen: bool) -> str:
    """Das Ende des Wechselgrundes in der Planung: passt zum Lauf (#504, Befund 8)."""
    if machen:
        return ("verschoben wird nichts, erst ohne --machen und ohne --uidvalidity neu "
                "anzeigen lassen")
    return "verschoben wird nichts, erst mit --uid ohne --uidvalidity neu anzeigen lassen"


def _uidvalidity_grund(vorher: str, ist: str | None, *, schluss: str,
                       quelle: str = "die Anzeige nannte") -> str:
    """Der Satz, wenn die UIDs nicht mehr sicher dieselben Mails meinen (#495)."""
    if ist is None:
        return (f"der Server nennt für den Eingang keine UIDVALIDITY, {quelle} {vorher} — "
                f"ob die UIDs noch dieselben Mails meinen, ist nicht zu prüfen; {schluss}")
    return (f"die UIDVALIDITY des Eingangs ist jetzt {ist}, {quelle} {vorher} — "
            "der Server hat die UIDs neu vergeben, dieselbe Zahl kann eine andere Mail sein; "
            f"{schluss}")


def plane_benannt(sitzung: postfach.Postfach, uids: list[str], *, wunsch: str | None = None,
                  trotz_faehnchen: bool = False, uidvalidity: str | None = None,
                  machen: bool = False) -> Bericht:
    """Genau diese Eingangsmails, auch ohne Antwort (`--uid`, #478) — rein lesend.

    `uidvalidity` ist der Wert, den die Anzeige nannte (#495). Weicht der des
    Eingangs ab oder nennt der Server keinen, wandert keine: Eine UID gilt nur
    zusammen mit ihm, und dieselbe Zahl kann dann eine fremde Mail sein.
    """
    uids = list(dict.fromkeys(str(u) for u in uids))
    leer = Bericht(adresse=sitzung.adresse, ziel=None, grund=None, seit=None, antworten=0,
                   nicht_im_eingang=0, zuege=(), verschoben=0, benannt=True)
    ziel, ziel_server, grund = _ziel_vorab(sitzung, wunsch)
    if grund:
        return leer._replace(grund=grund)
    gefunden = {k.uid: k for k in sitzung.koepfe(EINGANG, uids=uids, grenze=len(uids))}
    ist = sitzung.uidvalidity.get(EINGANG)
    gewechselt = uidvalidity is not None and ist != uidvalidity
    # Nach einem Wechsel meinen die gefundenen Mails nicht die der Anzeige: Das LIST zum
    # Jahresordner entfällt, sein Ergebnis würde ohnehin verworfen (#504, Befund 9).
    zuege = [_als_zug(gefunden[u], ziel=ziel, ziel_server=ziel_server)
             for u in uids if u in gefunden]
    zuege, liegen, jahr_grund = ((zuege, (), None) if gewechselt else
                                 _ziele_zuordnen(sitzung, wunsch, zuege,
                                                 trotz_faehnchen=trotz_faehnchen))
    fehlen = [u for u in uids if u not in gefunden]
    grund = None
    if gewechselt:
        # Vor allem anderen und allein: Nach einem Wechsel sagt weder eine
        # fehlende noch eine gefundene UID etwas über die Mail, die gemeint war.
        # Was unter der neuen Nummerierung gefunden wurde, ist nicht die Mail, die
        # die Anzeige meinte. Als „gefunden für …“ gezeigt, sähe der Bediener eine
        # fremde Mail unter seiner UID (Nachreview #502, Befund 3).
        grund = _uidvalidity_grund(uidvalidity, ist, schluss=_schluss_der_anzeige(machen))
        zuege, liegen = [], ()
    elif fehlen:
        # Vor dem Grund des Jahresordners: Eine Liste, die nicht stimmt, ist der
        # schwerere Befund — sie sagt, dass der Bediener etwas anderes meinte.
        grund = (f"{'UID' if len(fehlen) == 1 else 'die UIDs'} {', '.join(fehlen)} "
                 f"{'liegt' if len(fehlen) == 1 else 'liegen'} nicht im Eingang — "
                 "verschoben wird nur, wenn jede genannte UID da ist")
    elif liegen:
        # Nachreview von #494, Befund 5: Eine genannte Mail, die liegen bliebe,
        # zählt wie eine fehlende UID. Sonst wanderte der Rest mit Exit 0, und
        # die Liste des Bedieners wäre nur zum Teil erledigt.
        bleiben = sorted(liegen, key=lambda l: int(l.zug.uid))
        grund = ("; ".join(f"UID {l.zug.uid} bliebe liegen ({l.grund})" for l in bleiben)
                 + " — verschoben wird nur, wenn jede genannte UID wandern kann")
        # Nur ohne den Schalter: Mit ihm liegt keine Mail mehr wegen ihrer Flags,
        # und der Rat nennte einen Schalter, der schon gesetzt ist (Review von #496).
        if not trotz_faehnchen and any(l.zug.fahnen is None or FAEHNCHEN in l.zug.fahnen
                                       for l in bleiben):
            # Mit der UIDVALIDITY der Anzeige: `--uid` und `--machen` verlangen sie, sonst
            # endete der Befehl aus dem Rat auf Exit 1 (#504, Befund 1).
            wert = f" --uidvalidity {ist}" if ist is not None else ""
            grund += (f"; mit --trotz-faehnchen{wert} hebt das Fähnchen für diesen Lauf auf, "
                      f"mit --faehnchen-weg{wert} nimmt es vor dem Ablegen ab")
    if jahr_grund:
        # Der Grund des Jahresordners wird angehängt, nicht vorangestellt: Ein fehlender
        # Jahresordner kommt dazu, statt zu verschwinden. Sonst erführe der Bediener
        # erst im nächsten Lauf davon (Review von #496).
        grund = f"{grund}; {jahr_grund}" if grund else jahr_grund
    return leer._replace(ziel=ziel, ziel_server=ziel_server, grund=grund,
                         zuege=tuple(sorted(zuege, key=lambda z: int(z.uid))), liegen=liegen,
                         hinweise=_kappungen(sitzung), uidvalidity=ist)


def plane(sitzung: postfach.Postfach, *, wunsch: str | None = None,
          seit_tagen: int = SEIT_TAGEN, heute: date | None = None,
          trotz_faehnchen: bool = False) -> Bericht:
    """Welche Nachricht im Eingang ist beantwortet — rein lesend.

    Reihenfolge: Ziel klären, dann die gesendeten Antworten des Fensters lesen,
    dann je `In-Reply-To` im Eingang suchen. Das Ziel zuerst, weil ein Lauf
    ohne Ziel nichts zu planen hat und das Postfach dann nicht gelesen wird.
    """
    leer = Bericht(adresse=sitzung.adresse, ziel=None, grund=None, seit=None, antworten=0,
                   nicht_im_eingang=0, zuege=(), verschoben=0)
    lesbar, ziel, grund = _ziel_vorab(sitzung, wunsch)
    if grund:
        return leer._replace(grund=grund)

    gesendet = sitzung.sonderordner("\\Sent")
    if not gesendet:
        return leer._replace(
            ziel=lesbar,
            grund="das Postfach kennzeichnet keinen Ordner mit `\\Sent` — ohne die "
                  "gesendeten Antworten ist nicht zu sagen, was beantwortet wurde")

    heute = heute or datetime.now(timezone.utc).date()
    if not 1 <= seit_tagen <= SEIT_MAX:
        return leer._replace(
            ziel=lesbar, ziel_server=ziel,
            grund=f"ein Fenster von {seit_tagen} Tagen liegt außerhalb von 1 bis {SEIT_MAX}")
    seit = heute - timedelta(days=seit_tagen)
    grenze = datetime.combine(seit, datetime.min.time(), tzinfo=timezone.utc)
    antworten = [k for k in sitzung.koepfe(gesendet, seit=seit)
                 if k.antwort_auf and (k.datum is None or k.datum >= grenze)]

    # Mehrere Antworten auf dieselbe Nachricht ergeben einen Zug, nicht zwei.
    # Die jüngste Antwort steht dann im Bericht.
    gefunden: dict[str, Zug] = {}
    # Je Kennung eine Suche, auch wenn mehrere Antworten sie tragen (#522, Befund 3).
    # Geschlüsselt ohne Klammerpaar, so wie `gleiche_kennung` vergleicht: `<abc@x>`
    # und `abc@x` sind eine Message-ID und kosten eine Suche, nicht zwei (#522/11).
    # Dieselbe Kennung trägt dann auch nur einen Satz in `suchkappungen`.
    # Gesucht wird mit dem Schlüssel, nicht mit der Form der ersten Antwort: Die
    # Teilkettensuche nach `abc@x` trifft beide Schreibweisen im Eingang, die nach
    # `<abc@x>` nur eine. Mit der ersten Form gesucht, bekam die zweite Antwort ein
    # leeres Ergebnis, wenn die Kopfzeile keine Klammern trug (Nachreview von #524,
    # Befund 1). Die breitere Suche kann mehr fremde Treffer bringen; über
    # `SUCHGRENZE` (2000) kommt das bei einer echten Message-ID nicht.
    gesucht_je_kennung: dict[str, list[postfach.Kopf]] = {}
    nicht_im_eingang = 0
    unsendbar = 0
    for antwort in antworten:
        # Je Kennung eine Suche. Der rohe Feldwert ist keine: Er trägt eine
        # Liste und bei Länge einen Umbruch (#438).
        traf = False
        gesucht = False
        for kennung in postfach.kennungen(antwort.antwort_auf):
            # Von außen gekommen: Sie darf nur sich selbst kosten, nicht das Konto (#442).
            if not postfach.sendbar(kennung):
                unsendbar += 1
                continue
            gesucht = True
            # Der Server sucht Teilketten, verschoben wird nur der exakte Treffer (#442).
            # `suche_kennung` vergleicht selbst und kappt nicht vorher (#468).
            schluessel = postfach._ohne_klammerpaar(kennung)
            if schluessel not in gesucht_je_kennung:
                # `<>` hat einen leeren Schlüssel, und die Suche nach „“ träfe jede Mail.
                gesucht_je_kennung[schluessel] = sitzung.suche_kennung(
                    EINGANG, schluessel or kennung)
            for kopf in gesucht_je_kennung[schluessel]:
                traf = True
                vorher = gefunden.get(kopf.uid)
                if vorher is not None and _spaeter(vorher.antwort_datum, antwort.datum):
                    continue
                gefunden[kopf.uid] = _als_zug(kopf, kennung=kennung, antwort=antwort,
                                              ziel=lesbar, ziel_server=ziel)
        # Ohne Suche ist nichts über den Eingang bekannt: „längst weggeräumt“ wäre erfunden.
        if gesucht and not traf:
            nicht_im_eingang += 1
    zuege, liegen, grund = _ziele_zuordnen(
        sitzung, wunsch, sorted(gefunden.values(), key=lambda z: int(z.uid)),
        trotz_faehnchen=trotz_faehnchen)
    return Bericht(adresse=sitzung.adresse, ziel=lesbar, grund=grund,
                   seit=seit, antworten=len(antworten), nicht_im_eingang=nicht_im_eingang,
                   zuege=zuege, verschoben=0, ziel_server=ziel, liegen=liegen,
                   hinweise=_kappungen(sitzung) + _unsendbare(unsendbar),
                   uidvalidity=sitzung.uidvalidity.get(EINGANG))


def _kappungen(sitzung: postfach.Postfach) -> tuple[str, ...]:
    """Je Ordner, in dem `koepfe` mehr fand als es ansah, ein Satz; dazu je
    gekappter Kennungssuche einer.

    Derselbe Wortlaut wie in `entwurfsbuch` (ADR 0055): Dort steht er für
    dieselben Ordner, und zwei Formulierungen für dieselbe Lücke wären für den
    Leser zwei verschiedene Lücken.
    """
    ordner_saetze = tuple(
        f"„{postfach.utf7_anzeige(ordner)}“: nur die neuesten {angesehen} von {alle} "
        "Mails angesehen — was davor liegt, fehlt im Abgleich"
        for ordner, (alle, angesehen) in sorted(sitzung.gekappt.items()))
    # Eine gekappte Kennungssuche ist eine andere Lücke als ein gekappter Ordner
    # und bekommt ihren eigenen Satz (Nachreview von #492, Befund 1).
    such_saetze = tuple(
        f"Kennung „{kennung}“ in „{postfach.utf7_anzeige(ordner)}“: nur {verglichen} von "
        f"{alle} Teiltreffern verglichen, die neuesten — eine ältere Nachricht mit dieser "
        "Kennung fehlt womöglich im Abgleich"
        for ordner, kennung, alle, verglichen in sitzung.suchkappungen)
    return ordner_saetze + such_saetze


def _unsendbare(anzahl: int) -> tuple[str, ...]:
    """Der Satz zu Kennungen, nach denen nicht gesucht werden konnte."""
    if not anzahl:
        return ()
    return ((f"{anzahl} Kennungen in `In-Reply-To` übersprungen: Steuerzeichen oder Nicht-ASCII "
             "lassen sich nicht als Suchbegriff senden. Ihre Nachrichten bleiben im Eingang"),)


def _spaeter(a: datetime | None, b: datetime | None) -> bool:
    """Ist `a` nicht älter als `b`? Ohne Datum gilt als älter."""
    if a is None:
        return False
    return b is None or a >= b


# ── Der eine ändernde Befehl ────────────────────────────────────────────────

def verschiebe(sitzung: postfach.Postfach, ziel: str, uids: list[str], *,
               uidvalidity: str | None = None) -> int:
    """`UID MOVE` aus dem Eingang in den Ablageordner. Gibt die Anzahl zurück.

    Hier greift das Modul auf `postfach.Postfach._v` und `._befehl` zu, also
    auf Nichtöffentliches des Nachbarmoduls. Das ist Absicht: Der ändernde
    Befehl soll in **dieser** Datei stehen, wo die Quellprüfung von
    `tests/test_ablage.py` ihn sieht — und nicht in `postfach`, dessen Zusage
    sonst fiele. Zeitlimit und Form der Fehlermeldung bleiben dabei die
    gemeinsamen.

    `uidvalidity` ist der Wert, unter dem die UIDs geplant wurden. Nennt das
    SELECT einen anderen, geht kein MOVE hinaus (#495): Zwischen dem EXAMINE
    des Plans und diesem SELECT kann der Server den Eingang neu nummeriert
    haben. Ohne Planwert geht ebenso keines hinaus: Unbekannt ist nicht
    „gleich“, und die UIDs ließen sich gegen nichts prüfen (Nachreview #502,
    Befund 1).
    """
    if not uids:
        return 0
    if not ziel:
        raise AblageFehler("ohne Ablageordner wird nichts verschoben")
    if uidvalidity is None:
        # Vor dem SELECT: Ohne Planwert ist der Eingang nicht einmal zum Schreiben zu wählen.
        raise AblageFehler("der Plan dieses Laufs las für den Eingang keine UIDVALIDITY — "
                           "ob die UIDs noch dieselben Mails meinen, ist nicht zu prüfen; "
                           + _SCHLUSS_AM_ZUG)
    if not _kann_verschieben(sitzung):
        raise AblageFehler(_KEIN_MOVE)
    zitiert = postfach._zitiert
    # SELECT, nicht EXAMINE: Aus einem nur lesend geöffneten Ordner bewegt
    # der Server nichts. Gewählt wird allein der Eingang.
    sitzung._befehl(f"Ordner „{EINGANG}“ nicht wählbar", sitzung._v.select, zitiert(EINGANG))
    jetzt = sitzung._lies_uidvalidity()
    if jetzt != uidvalidity:
        raise AblageFehler(_uidvalidity_grund(uidvalidity, jetzt,
                                              quelle="der Plan dieses Laufs las",
                                              schluss=_SCHLUSS_AM_ZUG))
    try:
        sitzung._befehl(f"MOVE nach „{postfach.utf7_anzeige(ziel)}“",
                        sitzung._v.uid, "MOVE", ",".join(uids), zitiert(ziel))
    except postfach.PostfachFehler as fehler:
        raise ZugAbgebrochen(str(fehler)) from None
    return len(uids)


#: Warum ohne `MOVE` in CAPABILITY nichts wandert — und kein Fähnchen wegkommt (#566).
_KEIN_MOVE = ("der Server nennt in CAPABILITY kein MOVE (RFC 6851) — falzmarke baut es nicht "
              "aus COPY, STORE und EXPUNGE nach: ein Verschieben in drei Schritten kann in der "
              "Mitte abbrechen und die Nachricht zweimal liegen lassen")


def _kann_verschieben(sitzung: postfach.Postfach) -> bool:
    """Nennt der Server `MOVE`? Gelesen aus CAPABILITY, nicht angenommen."""
    faehig = getattr(sitzung._v, "capabilities", ()) or ()
    return "MOVE" in {str(f).upper() for f in faehig}


# ── Der Lauf ────────────────────────────────────────────────────────────────

def _je_ziel(zuege: tuple[Zug, ...]) -> list[tuple[str, list[str]]]:
    """Die UIDs je Zielordner, in fester Reihenfolge — bei `{jahr}` mehrere Züge."""
    gruppen: dict[str, list[str]] = {}
    for zug in zuege:
        gruppen.setdefault(zug.ziel_server or "", []).append(zug.uid)
    return sorted(gruppen.items())


def raeume_auf(adresse: str, *, wunsch: str | None = None, seit_tagen: int = SEIT_TAGEN,
               machen: bool = False, umgebung: Mapping[str, str] | None = None,
               frist: float = FRIST_S, uids: list[str] | None = None,
               trotz_faehnchen: bool = False, uidvalidity: str | None = None,
               faehnchen_weg: bool = False) -> Bericht:
    """Ein Absender, von der Anmeldung bis zum Zug. Ohne `machen` wird nur gelesen.

    Mit `uids` sind es genau diese Eingangsmails statt der beantworteten, und
    `uidvalidity` ist dann der Wert, den die Anzeige nannte (#495).
    `faehnchen_weg` gilt nur mit `uids` (#566).
    """
    bericht = Bericht(adresse=adresse, ziel=None, grund=None, seit=None, antworten=0,
                      nicht_im_eingang=0, zuege=(), verschoben=0, benannt=uids is not None,
                      faehnchen_weg=faehnchen_weg)
    if faehnchen_weg and uids is None:
        # Dieselbe Pflicht wie in `cli.py`: Das Fähnchen kommt nur von Mails, die
        # der Bediener genannt hat, nie von allen beantworteten.
        return bericht._replace(
            grund="faehnchen_weg gilt nur mit UIDs — das Fähnchen kommt nur von Mails, die "
                  "jemand genannt hat; verschoben wird nichts")
    if uids is not None and machen and uidvalidity is None:
        # Dieselbe Pflicht wie in `cli.py`, hier für jeden Aufrufer: Ohne den Wert der
        # Anzeige verglich der Lauf die aktuelle Nummerierung mit sich selbst und
        # verschob nach einem Wechsel eine fremde Mail (Nachreview #502, Befund 2).
        # Vor der Anmeldung, wie dort: Es wird kein Postfach geöffnet.
        return bericht._replace(
            grund="mit UIDs und machen fehlt die UIDVALIDITY, die die Anzeige nannte — "
                  "ohne sie ist nicht zu prüfen, ob die UIDs noch dieselben Mails meinen; "
                  "verschoben wird nichts")
    try:
        sitzung = postfach.verbinde(adresse, umgebung=umgebung, frist=frist)
    except postfach.PostfachFehler as fehler:
        return bericht._replace(grund=str(fehler))
    verschoben = 0
    with sitzung:
        try:
            if uids is not None:
                # Wer das Fähnchen abnimmt, legt auch die Mail mit Fähnchen ab.
                bericht = plane_benannt(sitzung, uids, wunsch=wunsch,
                                        trotz_faehnchen=trotz_faehnchen or faehnchen_weg,
                                        uidvalidity=uidvalidity, machen=machen)
                bericht = bericht._replace(faehnchen_weg=faehnchen_weg)
            else:
                bericht = plane(sitzung, wunsch=wunsch, seit_tagen=seit_tagen,
                                trotz_faehnchen=trotz_faehnchen)
            if not machen or bericht.grund or not bericht.zuege:
                return bericht
            if faehnchen_weg:
                # Vor dem Verschieben: Danach trägt die Mail im Ablageordner eine
                # neue UID, und das Fähnchen wäre dort nur noch über COPYUID zu
                # finden. Steht es nachher noch, wandert keine (#566). Ohne MOVE
                # bliebe die Mail ohne Fähnchen im Eingang, also vorher fragen.
                if not _kann_verschieben(sitzung):
                    raise AblageFehler(_KEIN_MOVE)
                try:
                    entfernt = faehnchen.nimm_weg(
                        sitzung, [z.uid for z in bericht.zuege if _mit_faehnchen(z)],
                        uidvalidity=bericht.uidvalidity)
                except faehnchen.FaehnchenFehler as fehler:
                    raise AblageFehler(str(fehler)) from None
                bericht = bericht._replace(faehnchen_entfernt=entfernt)
            # Das Ziel steht an jedem Zug. Ein zweites `ablageordner` wäre eine
            # zweite Bestimmung, und die kann anders ausfallen als die erste.
            for ziel, gruppe in _je_ziel(bericht.zuege):
                verschoben += verschiebe(sitzung, ziel, gruppe,
                                         uidvalidity=bericht.uidvalidity)
            return bericht._replace(verschoben=verschoben)
        except (postfach.PostfachFehler, AblageFehler) as fehler:
            # `_replace`, kein frischer Bericht: Bricht der Zug ab, nachdem der
            # Server einen Teil bewegt hat, wäre „0 von 0“ die stärkste Form
            # von „nichts geschehen“ — für den einen Fall, in dem etwas
            # geschehen sein kann (#438). Bei `{jahr}` kann ein früherer Zug
            # schon durch sein, wenn ein späterer abbricht (#478).
            # Für den Rest zählt nur, ob **sein** MOVE hinausging. Brach der
            # Lauf davor ab, etwa am SELECT der zweiten Jahresgruppe, ist für
            # ihn sicher nichts gesendet (Nachreview von #494, Befund 3).
            grund = str(fehler)
            if bericht.faehnchen_entfernt:
                # Das Fähnchen ist dann schon weg, die Mail aber womöglich nicht
                # abgelegt (#566). Bei `{jahr}` kann ein Teil schon gewandert sein.
                # Die UIDs zählen nach der UIDVALIDITY des Plans. Brach der Lauf an
                # einem Wechsel ab, meinen sie jetzt womöglich andere Mails
                # (Nachreview #585, Befund 9).
                grund += (f"; UIDs nach UIDVALIDITY {bericht.uidvalidity}: das Fähnchen an UID "
                          f"{', '.join(bericht.faehnchen_entfernt)} ist schon entfernt — was "
                          "davon nicht verschoben ist, liegt ohne Fähnchen im Eingang")
            return bericht._replace(grund=grund, verschoben=verschoben,
                                    zug_gesendet=isinstance(fehler, ZugAbgebrochen))


def _mit_faehnchen(zug: Zug) -> bool:
    """Trägt die Mail ein Fähnchen, oder ist das unbekannt? Beides nimmt `--faehnchen-weg` ab."""
    return zug.fahnen is None or FAEHNCHEN in zug.fahnen


# ── Ausgabe: ein Bericht, zwei Darstellungen ────────────────────────────────

def _kopfzeile(zug: Zug) -> str:
    wann = zug.datum.astimezone().strftime("%d.%m.%Y %H:%M") if zug.datum else "ohne Datum"
    von = f"{zug.von}  " if zug.von else ""
    return f"    UID {zug.uid}  {wann}  {von}„{zug.betreff}“"


def _zugzeilen(bericht: Bericht) -> list[str]:
    aus = []
    for zug in bericht.zuege:
        zeile = _kopfzeile(zug)
        if zug.antwort_betreff:
            zeile += f" — beantwortet mit „{zug.antwort_betreff}“"
        if zug.ziel and zug.ziel != bericht.ziel:
            zeile += f" → „{zug.ziel}“"
        if bericht.faehnchen_weg and zug.uid in bericht.faehnchen_entfernt:
            zeile += " — Fähnchen entfernt"
        elif bericht.faehnchen_weg and _mit_faehnchen(zug):
            zeile += " — Fähnchen kommt mit --machen weg"
        aus.append(zeile)
    aus += [f"{_kopfzeile(liegt.zug)} — liegt, {liegt.grund}" for liegt in bericht.liegen]
    return aus


def zeilen(bericht: Bericht) -> list[str]:
    """Der Bericht als Text. Mit Grund gehört er ganz auf stderr, sonst auf stdout.

    Ein Grund *mit* Zügen entsteht nur, wenn der Lauf nach dem Plan abbricht.
    Bis #442 (N2) standen die UIDs dann nur im JSON. Ob der Server schon etwas
    bewegt haben kann, sagt `zug_gesendet`: Nur wenn `UID MOVE` hinausging,
    ist das offen. Vorher abgebrochen heißt sicher nichts bewegt, und die
    Handprüfung des Ablageordners wäre vergeblich (Review von #459).

    Die Zeilen nach dem Grund gehören zu ihm. Die Weiche in `cli.py` schickt
    deshalb den ganzen Bericht auf stderr, nicht nur die erste Zeile: Ein
    `2>/dev/null` ließe sonst UIDs ohne Konto und Grund stehen.
    """
    nachspann = [f"HINWEIS  {h}" for h in bericht.hinweise]
    if bericht.grund:
        aus = [f"NICHT GEPRÜFT  {bericht.adresse}: {bericht.grund}"]
        if bericht.zuege:
            zahl = len(bericht.zuege)
            gefunden = (f"    {zahl} {'Nachricht' if zahl == 1 else 'Nachrichten'} "
                        f"für „{bericht.ziel}“ gefunden; ")
            if bericht.verschoben and bericht.zug_gesendet:
                stand = (f"{bericht.verschoben} davon verschoben, ob der Server vom Rest "
                         "schon etwas bewegt hat, ist nicht geprüft")
            elif bericht.verschoben:
                stand = (f"{bericht.verschoben} davon verschoben, der Rest nicht, weil der "
                         "Lauf vor seinem Zug abbrach")
            elif bericht.zug_gesendet:
                stand = "ob der Server davon schon etwas bewegt hat, ist nicht geprüft"
            else:
                stand = "nichts bewegt, der Zug war noch nicht gesendet"
            aus.append(gefunden + stand)
        if bericht.zuege or bericht.liegen:
            aus += _zugzeilen(bericht)
        return aus + nachspann
    wohin = (f" — {bericht.verschoben} nach „{bericht.ziel}“ verschoben"
             if bericht.verschoben else f" → „{bericht.ziel}“")
    if bericht.benannt:
        zahl = len(bericht.zuege) + len(bericht.liegen)
        aus = [f"OK  {bericht.adresse}: {zahl} benannte "
               f"{'Nachricht' if zahl == 1 else 'Nachrichten'} im Eingang, "
               f"{len(bericht.zuege)} zum Ablegen" + wohin]
        aus += _zugzeilen(bericht)
        if bericht.zuege and not bericht.verschoben:
            # Der Folgebefehl trägt den Wert, unter dem die UIDs eben galten:
            # `--uid … --machen` verlangt ihn (#495).
            if bericht.uidvalidity:
                aus.append(f"    nichts bewegt — mit --machen --uidvalidity "
                           f"{bericht.uidvalidity} verschieben")
            else:
                aus.append("    nichts bewegt — der Server nennt für den Eingang keine "
                           "UIDVALIDITY, mit --uid lässt sich deshalb nicht verschieben")
        return aus + nachspann
    im_eingang = len(bericht.zuege) + len(bericht.liegen)
    aus = [f"OK  {bericht.adresse}: {im_eingang} von {bericht.antworten} Antworten "
           f"seit {bericht.seit.strftime('%d.%m.%Y')} haben ihre Nachricht noch im Eingang"
           + (f", {len(bericht.liegen)} davon bleiben liegen" if bericht.liegen else "")
           + wohin]
    aus += _zugzeilen(bericht)
    if bericht.nicht_im_eingang:
        aus.append(f"    {bericht.nicht_im_eingang} Antworten ohne Nachricht im Eingang "
                   "(längst weggeräumt)")
    if bericht.zuege and not bericht.verschoben:
        aus.append("    nichts bewegt — mit --machen verschieben" if bericht.uidvalidity else
                   "    nichts bewegt — der Server nennt für den Eingang keine UIDVALIDITY, "
                   "auch mit --machen wird deshalb nicht verschoben")
    return aus + nachspann


def als_json(bericht: Bericht) -> dict:
    """Derselbe Bericht als Datenstruktur. Dieselbe Aussage wie `zeilen`."""
    return {
        "absender": bericht.adresse,
        "ablage": bericht.ziel,
        "grund": bericht.grund,
        "seit": bericht.seit.isoformat() if bericht.seit else None,
        "antworten": bericht.antworten,
        "nicht_im_eingang": bericht.nicht_im_eingang,
        "verschoben": bericht.verschoben,
        "zug_gesendet": bericht.zug_gesendet,
        "benannt": bericht.benannt,
        "uidvalidity": bericht.uidvalidity,
        "faehnchen_weg": bericht.faehnchen_weg,
        "faehnchen_entfernt": list(bericht.faehnchen_entfernt),
        "hinweise": list(bericht.hinweise),
        "zuege": [{"uid": z.uid, "betreff": z.betreff,
                   "datum": z.datum.isoformat() if z.datum else None,
                   "von": z.von, "ziel": z.ziel,
                   "kennung": z.kennung, "antwort_betreff": z.antwort_betreff,
                   "antwort_datum": z.antwort_datum.isoformat() if z.antwort_datum else None}
                  for z in bericht.zuege],
        "liegen": [{"uid": liegt.zug.uid, "betreff": liegt.zug.betreff,
                    "datum": liegt.zug.datum.isoformat() if liegt.zug.datum else None,
                    "von": liegt.zug.von, "grund": liegt.grund}
                   for liegt in bericht.liegen],
    }
