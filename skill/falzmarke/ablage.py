"""Beantwortete Eingangspost in die Ablage des Kontos (#431, ADR 0061).

Das einzige Modul des Pakets, das eine Nachricht im Postfach **bewegt**. Es
steht neben `postfach` und nicht darin, weil dessen Zusage „nur lesend, der
einzige schreibende Befehl ist `APPEND`" wahr bleiben soll — sie ist in
`postfach.py`, `tests/test_postfach.py` und `tests/imap_attrappe.py`
festgehalten.

**Ein ändernder Befehl, und es ist `UID MOVE`.** Kein `COPY`, kein
`STORE \\Deleted`, kein `EXPUNGE`, kein `DELETE`, kein `CREATE`: Ein
Verschieben, das aus drei Schritten besteht, kann in der Mitte abbrechen und
lässt die Nachricht dann zweimal oder nirgends liegen. Nennt `CAPABILITY` kein
`MOVE`, wird nichts verschoben und das gesagt — ein Nachbau wird nicht
gewagt. `tests/test_ablage.py` liest das am Syntaxbaum nach, mit Gegenprobe.

**Woraus „erledigt" folgt.** Jede gesendete Antwort trägt `In-Reply-To` mit der
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
#: Kennzeichen statt Namen, weil „Gesendete Elemente", „Sent Items" und
#: „Éléments envoyés" dasselbe sind und eine Namensliste immer eine Sprache
#: zu wenig kennt.
VERBOTENE_ZIELE = {
    "\\sent": "er ist Datenquelle der Sendesperre und von `status` (ADR 0051), keine Ablage",
    "\\drafts": "dort liegen die Entwürfe, aus denen `status` seine Aussage zieht",
    "\\trash": "der Papierkorb ist keine Ablage",
    "\\junk": "der Spam-Ordner ist keine Ablage",
}


class AblageFehler(Exception):
    """Ein Grund in einem Satz — er wandert unverändert in die Ausgabe."""


class Zug(NamedTuple):
    """Eine Nachricht im Eingang und die Antwort, die sie erledigt hat."""

    uid: str
    betreff: str
    datum: datetime | None
    #: Die `Message-ID`, über die die Zuordnung läuft.
    kennung: str
    antwort_betreff: str
    antwort_datum: datetime | None


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

def plane(sitzung: postfach.Postfach, *, wunsch: str | None = None,
          seit_tagen: int = SEIT_TAGEN, heute: date | None = None) -> Bericht:
    """Welche Nachricht im Eingang ist beantwortet — rein lesend.

    Reihenfolge: Ziel klären, dann die gesendeten Antworten des Fensters lesen,
    dann je `In-Reply-To` im Eingang suchen. Das Ziel zuerst, weil ein Lauf
    ohne Ziel nichts zu planen hat und das Postfach dann nicht gelesen wird.
    """
    leer = Bericht(adresse=sitzung.adresse, ziel=None, grund=None, seit=None, antworten=0,
                   nicht_im_eingang=0, zuege=(), verschoben=0)
    ziel, grund = ablageordner(sitzung, wunsch)
    if ziel is None:
        return leer._replace(grund=grund)

    gesendet = sitzung.sonderordner("\\Sent")
    if not gesendet:
        return leer._replace(
            ziel=postfach.utf7_dekodieren(ziel),
            grund="das Postfach kennzeichnet keinen Ordner mit `\\Sent` — ohne die "
                  "gesendeten Antworten ist nicht zu sagen, was beantwortet wurde")

    heute = heute or datetime.now(timezone.utc).date()
    if not 1 <= seit_tagen <= SEIT_MAX:
        return leer._replace(
            ziel=postfach.utf7_dekodieren(ziel), ziel_server=ziel,
            grund=f"ein Fenster von {seit_tagen} Tagen liegt außerhalb von 1 bis {SEIT_MAX}")
    seit = heute - timedelta(days=seit_tagen)
    grenze = datetime.combine(seit, datetime.min.time(), tzinfo=timezone.utc)
    antworten = [k for k in sitzung.koepfe(gesendet, seit=seit)
                 if k.antwort_auf and (k.datum is None or k.datum >= grenze)]

    # Mehrere Antworten auf dieselbe Nachricht ergeben einen Zug, nicht zwei.
    # Die jüngste Antwort steht dann im Bericht.
    gefunden: dict[str, Zug] = {}
    nicht_im_eingang = 0
    for antwort in antworten:
        # Je Kennung eine Suche. Der rohe Feldwert ist keine: Er trägt eine
        # Liste und bei Länge einen Umbruch (#438).
        traf = False
        for kennung in postfach.kennungen(antwort.antwort_auf):
            uids = sitzung.suche_kopfzeile(EINGANG, "Message-ID", kennung)
            if not uids:
                continue
            traf = True
            for kopf in sitzung.koepfe(EINGANG, uids=uids):
                vorher = gefunden.get(kopf.uid)
                if vorher is not None and _spaeter(vorher.antwort_datum, antwort.datum):
                    continue
                gefunden[kopf.uid] = Zug(uid=kopf.uid, betreff=kopf.betreff, datum=kopf.datum,
                                         kennung=kennung,
                                         antwort_betreff=antwort.betreff,
                                         antwort_datum=antwort.datum)
        if not traf:
            nicht_im_eingang += 1
    zuege = tuple(sorted(gefunden.values(), key=lambda z: int(z.uid)))
    return Bericht(adresse=sitzung.adresse, ziel=postfach.utf7_dekodieren(ziel), grund=None,
                   seit=seit, antworten=len(antworten), nicht_im_eingang=nicht_im_eingang,
                   zuege=zuege, verschoben=0, hinweise=_kappungen(sitzung), ziel_server=ziel)


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
    sitzung._befehl(f"MOVE nach „{postfach.utf7_dekodieren(ziel)}“",
                    sitzung._v.uid, "MOVE", ",".join(uids), zitiert(ziel))
    return len(uids)


def _kann_verschieben(sitzung: postfach.Postfach) -> bool:
    """Nennt der Server `MOVE`? Gelesen aus CAPABILITY, nicht angenommen."""
    faehig = getattr(sitzung._v, "capabilities", ()) or ()
    return "MOVE" in {str(f).upper() for f in faehig}


# ── Der Lauf ────────────────────────────────────────────────────────────────

def raeume_auf(adresse: str, *, wunsch: str | None = None, seit_tagen: int = SEIT_TAGEN,
               machen: bool = False, umgebung: Mapping[str, str] | None = None,
               frist: float = FRIST_S) -> Bericht:
    """Ein Absender, von der Anmeldung bis zum Zug. Ohne `machen` wird nur gelesen."""
    bericht = Bericht(adresse=adresse, ziel=None, grund=None, seit=None, antworten=0,
                      nicht_im_eingang=0, zuege=(), verschoben=0)
    try:
        sitzung = postfach.verbinde(adresse, umgebung=umgebung, frist=frist)
    except postfach.PostfachFehler as fehler:
        return bericht._replace(grund=str(fehler))
    with sitzung:
        try:
            bericht = plane(sitzung, wunsch=wunsch, seit_tagen=seit_tagen)
            if not machen or bericht.grund or not bericht.zuege:
                return bericht
            # Das Ziel steht im Bericht. Ein zweites `ablageordner` wäre eine
            # zweite Bestimmung, und die kann anders ausfallen als die erste.
            anzahl = verschiebe(sitzung, bericht.ziel_server, [z.uid for z in bericht.zuege])
            return bericht._replace(verschoben=anzahl)
        except (postfach.PostfachFehler, AblageFehler) as fehler:
            # `_replace`, kein frischer Bericht: Bricht der Zug ab, nachdem der
            # Server einen Teil bewegt hat, wäre „0 von 0" die stärkste Form
            # von „nichts geschehen" — für den einen Fall, in dem etwas
            # geschehen sein kann (#438).
            return bericht._replace(grund=str(fehler))


# ── Ausgabe: ein Bericht, zwei Darstellungen ────────────────────────────────

def zeilen(bericht: Bericht) -> list[str]:
    """Der Bericht als Text. `NICHT GEPRÜFT` gehört auf stderr, der Rest nicht."""
    nachspann = [f"HINWEIS  {h}" for h in bericht.hinweise]
    if bericht.grund:
        return [f"NICHT GEPRÜFT  {bericht.adresse}: {bericht.grund}"] + nachspann
    aus = [f"OK  {bericht.adresse}: {len(bericht.zuege)} von {bericht.antworten} Antworten "
           f"seit {bericht.seit.strftime('%d.%m.%Y')} haben ihre Nachricht noch im Eingang"
           + (f" — {bericht.verschoben} nach „{bericht.ziel}“ verschoben"
              if bericht.verschoben else f" → „{bericht.ziel}“")]
    for zug in bericht.zuege:
        wann = zug.datum.astimezone().strftime("%d.%m.%Y %H:%M") if zug.datum else "ohne Datum"
        aus.append(f"    UID {zug.uid}  {wann}  „{zug.betreff}“ "
                   f"— beantwortet mit „{zug.antwort_betreff}“")
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
        "hinweise": list(bericht.hinweise),
        "zuege": [{"uid": z.uid, "betreff": z.betreff,
                   "datum": z.datum.isoformat() if z.datum else None,
                   "kennung": z.kennung, "antwort_betreff": z.antwort_betreff,
                   "antwort_datum": z.antwort_datum.isoformat() if z.antwort_datum else None}
                  for z in bericht.zuege],
    }
