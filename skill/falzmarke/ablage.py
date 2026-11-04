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
Lauf.

**Benannte Mails** (`--uid`, #478) sind erledigt, weil der Bediener es sagt,
nicht wegen einer Antwort. Es bleibt bei denselben Sperren und demselben einen
`UID MOVE`. Fehlt eine der genannten UIDs im Eingang, wandert keine: Eine
Liste, die nicht mehr stimmt, ist kein Auftrag für den Rest.

**`{jahr}` im Ziel** (#478) wird je Mail zum Jahr ihrer Ankunft im Postfach
(INTERNALDATE, Ortszeit), so wie Thunderbird mit `archive_granularity 1`
ablegt. Fehlt einer der Jahresordner, wandert keine Mail des Laufs: Sonst
wäre die eine Hälfte abgelegt und die andere still nicht.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple

from falzmarke import postfach

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
    #: Warum nichts geht. Gesetzt heißt: nichts geprüft, nichts bewegt.
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
    #: War `UID MOVE` schon gesendet, als der Lauf abbrach? Nur dann kann der
    #: Server einen Teil bewegt haben. Ohne Grund immer `False`.
    zug_gesendet: bool = False
    #: Was erledigt wäre und bleibt — Fähnchen, unbekannte Flags, kein Jahr.
    liegen: tuple[Liegt, ...] = ()
    #: Kamen die Nachrichten aus `--uid` statt aus Antworten?
    benannt: bool = False


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
            vorhanden = ", ".join(f"„{postfach.utf7_dekodieren(n)}“" for n, _ in liste[:12])
            return None, (f"den Ordner „{wunsch}“ aus `email.ablage` gibt es im Postfach nicht "
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
            return None, (f"„{postfach.utf7_dekodieren(name)}“ ({herkunft}) trägt "
                          f"`{verboten}`: {grund}")
    if name.upper() == EINGANG:
        return None, "der Eingang kann nicht seine eigene Ablage sein"
    return name, None


# ── Der Plan ────────────────────────────────────────────────────────────────

def _ziel_vorab(sitzung: postfach.Postfach,
                wunsch: str | None) -> tuple[str | None, str | None, str | None]:
    """`(lesbar, server, grund)` — das Ziel des Laufs, bevor gelesen wird.

    Mit `{jahr}` steht der Ordner erst je Nachricht fest. Dann ist `server`
    leer, und `_ziele_zuordnen` prüft jeden Jahresordner einzeln — mit
    denselben Sperren wie hier.
    """
    if wunsch and JAHR in wunsch:
        return wunsch, None, None
    ziel, grund = ablageordner(sitzung, wunsch)
    if ziel is None:
        return None, None, grund
    return postfach.utf7_dekodieren(ziel), ziel, None


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
        zugeordnet.append(zug._replace(ziel=name, ziel_server=ordner))
    grund = None
    if fehlend:
        grund = ("; ".join(fehlend) + " — keine Mail dieses Laufs wandert, auch nicht "
                 "die mit vorhandenem Jahresordner")
    return tuple(zugeordnet), tuple(liegen), grund


def plane_benannt(sitzung: postfach.Postfach, uids: list[str], *, wunsch: str | None = None,
                  trotz_faehnchen: bool = False) -> Bericht:
    """Genau diese Eingangsmails, auch ohne Antwort (`--uid`, #478) — rein lesend."""
    uids = list(dict.fromkeys(str(u) for u in uids))
    leer = Bericht(adresse=sitzung.adresse, ziel=None, grund=None, seit=None, antworten=0,
                   nicht_im_eingang=0, zuege=(), verschoben=0, benannt=True)
    ziel, ziel_server, grund = _ziel_vorab(sitzung, wunsch)
    if grund:
        return leer._replace(grund=grund)
    gefunden = {k.uid: k for k in sitzung.koepfe(EINGANG, uids=uids, grenze=len(uids))}
    zuege = [_als_zug(gefunden[u], ziel=ziel, ziel_server=ziel_server)
             for u in uids if u in gefunden]
    zuege, liegen, grund = _ziele_zuordnen(sitzung, wunsch, zuege,
                                           trotz_faehnchen=trotz_faehnchen)
    fehlen = [u for u in uids if u not in gefunden]
    if fehlen:
        # Vor dem Grund des Jahresordners: Eine Liste, die nicht stimmt, ist der
        # schwerere Befund — sie sagt, dass der Bediener etwas anderes meinte.
        grund = (f"{'UID' if len(fehlen) == 1 else 'die UIDs'} {', '.join(fehlen)} "
                 f"{'liegt' if len(fehlen) == 1 else 'liegen'} nicht im Eingang — "
                 "verschoben wird nur, wenn jede genannte UID da ist")
    return leer._replace(ziel=ziel, ziel_server=ziel_server, grund=grund,
                         zuege=tuple(sorted(zuege, key=lambda z: int(z.uid))), liegen=liegen,
                         hinweise=_kappungen(sitzung))


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
            for kopf in sitzung.suche_kennung(EINGANG, kennung):
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
                   hinweise=_kappungen(sitzung) + _unsendbare(unsendbar))


def _kappungen(sitzung: postfach.Postfach) -> tuple[str, ...]:
    """Je Ordner, in dem `koepfe` mehr fand als es ansah, ein Satz.

    Derselbe Wortlaut wie in `entwurfsbuch` (ADR 0055): Dort steht er für
    dieselben Ordner, und zwei Formulierungen für dieselbe Lücke wären für den
    Leser zwei verschiedene Lücken.
    """
    return tuple(
        f"„{postfach.utf7_dekodieren(ordner)}“: nur die neuesten {angesehen} von {alle} "
        "Mails angesehen — was davor liegt, fehlt im Abgleich"
        for ordner, (alle, angesehen) in sorted(sitzung.gekappt.items()))


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

def verschiebe(sitzung: postfach.Postfach, ziel: str, uids: list[str]) -> int:
    """`UID MOVE` aus dem Eingang in den Ablageordner. Gibt die Anzahl zurück.

    Hier greift das Modul auf `postfach.Postfach._v` und `._befehl` zu, also
    auf Nichtöffentliches des Nachbarmoduls. Das ist Absicht: Der ändernde
    Befehl soll in **dieser** Datei stehen, wo die Quellprüfung von
    `tests/test_ablage.py` ihn sieht — und nicht in `postfach`, dessen Zusage
    sonst fiele. Zeitlimit und Form der Fehlermeldung bleiben dabei die
    gemeinsamen.
    """
    if not uids:
        return 0
    if not ziel:
        raise AblageFehler("ohne Ablageordner wird nichts verschoben")
    if not _kann_verschieben(sitzung):
        raise AblageFehler(
            "der Server nennt in CAPABILITY kein MOVE (RFC 6851) — falzmarke baut es nicht "
            "aus COPY, STORE und EXPUNGE nach: ein Verschieben in drei Schritten kann in der "
            "Mitte abbrechen und die Nachricht zweimal liegen lassen")
    zitiert = postfach._zitiert
    # SELECT, nicht EXAMINE: Aus einem nur lesend geöffneten Ordner bewegt
    # der Server nichts. Gewählt wird allein der Eingang.
    sitzung._befehl(f"Ordner „{EINGANG}“ nicht wählbar", sitzung._v.select, zitiert(EINGANG))
    try:
        sitzung._befehl(f"MOVE nach „{postfach.utf7_dekodieren(ziel)}“",
                        sitzung._v.uid, "MOVE", ",".join(uids), zitiert(ziel))
    except postfach.PostfachFehler as fehler:
        raise ZugAbgebrochen(str(fehler)) from None
    return len(uids)


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
               trotz_faehnchen: bool = False) -> Bericht:
    """Ein Absender, von der Anmeldung bis zum Zug. Ohne `machen` wird nur gelesen.

    Mit `uids` sind es genau diese Eingangsmails statt der beantworteten.
    """
    bericht = Bericht(adresse=adresse, ziel=None, grund=None, seit=None, antworten=0,
                      nicht_im_eingang=0, zuege=(), verschoben=0, benannt=uids is not None)
    try:
        sitzung = postfach.verbinde(adresse, umgebung=umgebung, frist=frist)
    except postfach.PostfachFehler as fehler:
        return bericht._replace(grund=str(fehler))
    verschoben = 0
    with sitzung:
        try:
            if uids is not None:
                bericht = plane_benannt(sitzung, uids, wunsch=wunsch,
                                        trotz_faehnchen=trotz_faehnchen)
            else:
                bericht = plane(sitzung, wunsch=wunsch, seit_tagen=seit_tagen,
                                trotz_faehnchen=trotz_faehnchen)
            if not machen or bericht.grund or not bericht.zuege:
                return bericht
            # Das Ziel steht an jedem Zug. Ein zweites `ablageordner` wäre eine
            # zweite Bestimmung, und die kann anders ausfallen als die erste.
            for ziel, gruppe in _je_ziel(bericht.zuege):
                verschoben += verschiebe(sitzung, ziel, gruppe)
            return bericht._replace(verschoben=verschoben)
        except (postfach.PostfachFehler, AblageFehler) as fehler:
            # `_replace`, kein frischer Bericht: Bricht der Zug ab, nachdem der
            # Server einen Teil bewegt hat, wäre „0 von 0“ die stärkste Form
            # von „nichts geschehen“ — für den einen Fall, in dem etwas
            # geschehen sein kann (#438). Bei `{jahr}` kann ein früherer Zug
            # schon durch sein, wenn ein späterer abbricht (#478).
            return bericht._replace(grund=str(fehler), verschoben=verschoben,
                                    zug_gesendet=isinstance(fehler, ZugAbgebrochen)
                                    or verschoben > 0)


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
            if bericht.verschoben:
                stand = (f"{bericht.verschoben} davon verschoben, ob der Server vom Rest "
                         "schon etwas bewegt hat, ist nicht geprüft")
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
            aus.append("    nichts bewegt — mit --machen verschieben")
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
        aus.append("    nichts bewegt — mit --machen verschieben")
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
