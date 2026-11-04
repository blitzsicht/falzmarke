"""Überholte Entwürfe in den Papierkorb (#425, ADR 0062).

Neben `ablage` das zweite Modul des Pakets, das eine Nachricht im Postfach
**bewegt**, und aus demselben Grund neben `postfach` statt darin: Dessen Zusage
„nur lesend, der einzige schreibende Befehl ist `APPEND`“ bleibt wahr.

**Ein ändernder Befehl, und es ist `UID MOVE`, immer in den Ordner mit `\\Trash`.**
Kein `COPY`, kein `STORE \\Deleted`, kein `EXPUNGE`: Nichts wird hart gelöscht,
und ein Verschieben aus drei Schritten kann in der Mitte abbrechen. Nennt
`CAPABILITY` kein `MOVE` oder kennzeichnet der Server keinen Papierkorb, bewegt
sich nichts, und das wird gesagt. `tests/test_entwurfsablage.py` liest das am
Syntaxbaum nach, mit Gegenprobe. Gesendet wird hier nichts (ADR 0038).

**Weg darf nur, was belegt ist.** Zwei Regeln öffnen die Tür: dieselbe Fassung
ging hinaus (`status` sagt BELEGT), oder eine neuere Fassung an genau dieselben
Empfänger mit demselben Betreff ging hinaus. Davor steht `SPERREN`, und jede
Sperre schlägt beide Regeln. Die Sperren stehen als Liste da, damit die Tests
je eine herausnehmen können: Bewegt sich der Entwurf dann, trägt genau diese
Sperre den Fall.

**Fehlender Beleg ist kein Befund.** Ist das Postfach nicht zu erreichen, heißt
das `NICHT GEPRÜFT` und nie „nichts zu tun“.

**Was vor dem Zug noch einmal gelesen wird.** Zwischen Plan und `MOVE` liegen
Sekunden, in denen der Betreiber ein Fenster öffnen oder Thunderbird den Ordner
ändern kann. Deshalb wird je UID die Fensterliste neu erfragt und der Kopf neu
gelesen. Weicht etwas ab, bleibt die Nachricht liegen. Nach dem Zug wird
nachgesehen, ob sie weg ist: Ein `UID MOVE` auf eine UID, die es nicht gibt,
antwortet `OK`.
"""

from __future__ import annotations

import email
import os
from collections.abc import Mapping
from datetime import datetime
from email import policy
from pathlib import Path
from typing import NamedTuple

from falzmarke import entwurfsbuch, gesendet, postfach

#: Zeitlimit einer Sitzung, wie `entwurfsbuch.FRIST_S`.
FRIST_S = 120.0

#: Die Worte der beiden Regeln, in Ausgabe und JSON.
SCHON_RAUS = "schon_raus"
NEUERE_FASSUNG = "neuere_fassung"
REGEL_TEXT = {SCHON_RAUS: "dieselbe Fassung ging schon hinaus",
              NEUERE_FASSUNG: "eine neuere Fassung ging hinaus"}


class EntwurfsablageFehler(Exception):
    """Ein Grund in einem Satz. Er wandert unverändert in die Ausgabe."""


class Zug(NamedTuple):
    """Ein Entwurf, der weg darf."""

    uid: str
    betreff: str
    an: tuple[str, ...]
    fassung: str
    datum: datetime | None
    regel: str
    #: Die UIDs seiner Speicher-Kette: Ein Fenster auf einer davon hält ihn.
    kette: frozenset[str] = frozenset()


class Bleibt(NamedTuple):
    """Ein Entwurf, der liegen bleibt, und warum."""

    uid: str
    betreff: str
    #: Der Name der Sperre, an dem die Tests hängen.
    sperre: str
    grund: str
    #: Ob eine Regel ihn wegräumen würde und nur die Sperre ihn hält.
    ueberholt: bool = False


class Bericht(NamedTuple):
    """Was ein Lauf gefunden und getan hat."""

    adresse: str
    #: Gesetzt heißt: nichts bewegt, oder der Lauf brach ab; dann steht in
    #: `verschoben`, was bis dahin ging.
    grund: str = ""
    entwuerfe: str = ""
    papierkorb: str = ""
    zuege: tuple[Zug, ...] = ()
    bleibt: tuple[Bleibt, ...] = ()
    #: Tatsächlich bewegt und nachgesehen. Ohne `machen` immer leer.
    verschoben: tuple[str, ...] = ()
    hinweise: tuple[str, ...] = ()


# ── Die Sperren ─────────────────────────────────────────────────────────────

def _offen(z, _b) -> str:
    # Ausdrücklich auch bei `schon_raus`, das `offen` als Zustand sticht.
    return ("gerade in einem Fenster offen"
            if z.art == "offen" or z.fenster is not None or z.kette_offen else "")


def _ohne_fassung(z, _b) -> str:
    return "" if z.fassung else "trägt keine Fassung, also nicht von falzmarke angelegt"


def _nicht_im_buch(z, _b) -> str:
    return ("" if z.im_buch else
            "nicht im Entwurfsbuch: von Hand geschrieben, in Thunderbird gespeichert "
            "oder älter als das Fenster dieses Laufs")


def _in_thunderbird_gespeichert(z, _b) -> str:
    return ("in Thunderbird gespeichert, also womöglich geändert"
            if any(t.get("art") == "gespeichert" for t in z.tagebuch) else "")


def _text_gekappt(z, _b) -> str:
    return "Text im Entwurfsbuch gekappt, also nicht vergleichbar" if z.text_gekappt else ""


def _text_weicht_ab(z, _b) -> str:
    return "Text weicht vom Entwurfsbuch ab, also geändert" if z.text_wie_buch is False else ""


def _beleg_unlesbar(_z, b) -> str:
    return f"Beleg nicht lesbar: {b.beleg_grund}" if b.beleg_grund else ""


def _fenster_ungeprueft(_z, b) -> str:
    return b.fenster_grund


#: In dieser Reihenfolge gefragt. Die erste, die etwas sagt, nennt den Grund.
SPERREN = (
    ("offen", _offen),
    ("ohne_fassung", _ohne_fassung),
    ("nicht_im_buch", _nicht_im_buch),
    ("gespeichert", _in_thunderbird_gespeichert),
    ("gekappt", _text_gekappt),
    ("text_weicht_ab", _text_weicht_ab),
    ("beleg_unlesbar", _beleg_unlesbar),
    ("fenster_ungeprueft", _fenster_ungeprueft),
)


# ── Die Regeln ──────────────────────────────────────────────────────────────

def _selbe_fassung_raus(z) -> bool:
    """`status` sagt BELEGT, und die Mail im Gesendet-Ordner ist diese Fassung.

    Eine leere `message_id` im Tagebuch stört nicht: Der Eintrag hängt über die
    UID am Entwurf, und genau diese Mail ist die, die liegen blieb (#425, Fall 1).
    Eine Sendung, die älter ist als der Entwurf, kann er nicht gewesen sein: So
    sieht `--trotz-gesendet` aus, wenn jemand dieselbe Nachricht neu anlegt.
    """
    if z.art != "schon_raus" or not z.belegt:
        return False
    if not any(t.get("art") == "gesendet" and isinstance(t.get("ursprung"), Mapping)
               and t["ursprung"].get("fassung") == z.fassung for t in z.tagebuch):
        return False
    seit = z.buch_zeit or z.angelegt
    return any(s.gleich and s.an == frozenset(z.an) and s.datum is not None
               and seit is not None and s.datum >= seit for s in z.sendungen)


def _neuere_fassung_raus(z) -> bool:
    """Eine neuere Fassung ging an genau dieselben Empfänger hinaus.

    „Andere Fassung“ kommt aus dem Tagebuch. Ohne Eintrag ist nichts bewiesen:
    Eine von Hand geschriebene Mail mit demselben Betreff kann eine Rückfrage
    sein. Gleiche Empfänger heißt gleiche Menge, nicht Schnitt, und gleicher
    Betreff schließt die Antwortstufe ein: Ein `AW:` mehr ist eine Antwort im
    Faden, keine neue Fassung.

    „Neuer“ heißt: später ins Buch gekommen als dieser Entwurf. Später gesendet
    reicht nicht. Liegen zwei Fassungen und geht die ältere hinaus, ist die
    jüngere nicht überholt, sie wird vielleicht noch gebraucht.
    """
    seit = z.buch_zeit or z.angelegt
    kern, stufe = gesendet.betreff_kern(z.betreff), gesendet.antwortstufe(z.betreff)
    return seit is not None and any(
        s.an == frozenset(z.an) and s.betreff_kern == kern and s.stufe == stufe
        and s.datum is not None and s.datum > seit
        and s.buch_zeit is not None and s.buch_zeit > seit for s in z.sendungen)


def bewerte(z: entwurfsbuch.Zustand, b: entwurfsbuch.Bericht) -> Zug | Bleibt:
    """Darf dieser liegende Entwurf weg? Rein rechnend, ohne Postfach."""
    regel = (SCHON_RAUS if _selbe_fassung_raus(z)
             else NEUERE_FASSUNG if _neuere_fassung_raus(z) else "")
    for name, sperre in SPERREN:
        grund = sperre(z, b)
        if grund:
            return Bleibt(z.uid, z.betreff, name, grund, bool(regel))
    if regel:
        return Zug(z.uid, z.betreff, z.an, z.fassung, z.angelegt, regel, z.kette)
    if z.art == "schon_raus":
        return Bleibt(z.uid, z.betreff, "nicht_belegt",
                      "Text ging hinaus, aber Tagebuch und Gesendet-Ordner belegen nicht, "
                      "dass es dieser Entwurf war")
    return Bleibt(z.uid, z.betreff, "wartet", "wartet: keine neuere Fassung gesendet")


# ── Der eine ändernde Befehl ────────────────────────────────────────────────

def _kann_verschieben(sitzung: postfach.Postfach) -> bool:
    """Nennt der Server `MOVE`? Gelesen aus CAPABILITY, nicht angenommen."""
    faehig = getattr(sitzung._v, "capabilities", ()) or ()
    return "MOVE" in {str(f).upper() for f in faehig}


def papierkorb(sitzung: postfach.Postfach, quelle: str) -> str:
    """Der Ordner mit `\\Trash` — oder der Satz, warum nichts geht, als Ausnahme."""
    if not _kann_verschieben(sitzung):
        raise EntwurfsablageFehler(
            "der Server nennt in CAPABILITY kein MOVE (RFC 6851) — falzmarke baut es nicht "
            "aus COPY, STORE und EXPUNGE nach")
    ziel = sitzung.sonderordner("\\Trash")
    if not ziel:
        raise EntwurfsablageFehler(
            "das Postfach kennzeichnet keinen Ordner mit `\\Trash` — ohne Papierkorb wird "
            "nichts verschoben, geraten wird nicht")
    if ziel == quelle:
        raise EntwurfsablageFehler("Entwürfe-Ordner und Papierkorb sind derselbe Ordner")
    return ziel


def verschiebe(sitzung: postfach.Postfach, quelle: str, ziel: str, uid: str) -> None:
    """`UID MOVE` einer Nachricht aus „Entwürfe“ in den Papierkorb.

    Wie in `ablage.verschiebe` greift das auf Nichtöffentliches von `postfach`
    zu: Der ändernde Befehl soll in **dieser** Datei stehen, wo die Quellprüfung
    ihn sieht. `SELECT` statt `EXAMINE`, weil der Server aus einem nur lesend
    geöffneten Ordner nichts bewegt.
    """
    zitiert = postfach._zitiert
    sitzung._befehl(f"Ordner „{postfach.utf7_dekodieren(quelle)}“ nicht wählbar",
                    sitzung._v.select, zitiert(quelle))
    sitzung._befehl(f"MOVE nach „{postfach.utf7_dekodieren(ziel)}“",
                    sitzung._v.uid, "MOVE", str(uid), zitiert(ziel))


def _noch_derselbe(sitzung: postfach.Postfach, ordner: str, zug: Zug) -> str:
    """Leer, wenn unter der UID noch die geplante Nachricht liegt, sonst der Grund."""
    koepfe = sitzung.koepfe(ordner, uids=[zug.uid])
    if not koepfe:
        return "liegt nicht mehr im Ordner"
    kopf = koepfe[0]
    if (kopf.fassung, set(kopf.an), kopf.betreff) != (zug.fassung, set(zug.an), zug.betreff):
        return "unter dieser UID liegt inzwischen eine andere Nachricht"
    return ""


def _ziehe(sitzung: postfach.Postfach, ordner: str, ziel: str, zug: Zug, *, adresse: str,
           umgebung: Mapping[str, str], machen: bool) -> str:
    """Prüft einen Zug unmittelbar davor und führt ihn aus. Leer heißt: geht/ging."""
    offen, grund = entwurfsbuch._offene_uids(adresse, umgebung)
    if grund:
        return grund
    if zug.uid in offen or zug.kette & set(offen):
        return "gerade in einem Fenster offen"
    grund = _noch_derselbe(sitzung, ordner, zug)
    if grund or not machen:
        return grund
    verschiebe(sitzung, ordner, ziel, zug.uid)
    if sitzung.koepfe(ordner, uids=[zug.uid]):
        raise EntwurfsablageFehler(
            f"UID {zug.uid} liegt nach dem MOVE noch im Ordner — der Server sagte OK, "
            "bewegt hat er nichts")
    return ""


# ── Die Läufe ───────────────────────────────────────────────────────────────

def raeume_auf(adresse: str, *, machen: bool = False,
               tage: int = entwurfsbuch.TAGE_VORGABE,
               umgebung: Mapping[str, str] | None = None, jetzt: datetime | None = None,
               profilordner: Path | None = None, frist: float = FRIST_S,
               ausser: frozenset[str] = frozenset()) -> Bericht:
    """Ein Konto, vom Abgleich bis zum Zug. Wirft nichts; ohne `machen` wird nur gelesen.

    `ausser` nennt UIDs, die dieser Lauf nicht anfasst: `email --oeffnen` hat die
    Brücke gerade gebeten, sie zu öffnen, und ein Fenster, das noch aufgeht,
    steht in keiner Fensterliste.
    """
    umgebung = os.environ if umgebung is None else umgebung
    try:
        stand = entwurfsbuch.abgleich(adresse, tage=tage, umgebung=umgebung, jetzt=jetzt,
                                      profilordner=profilordner)
    except Exception as fehler:  # noqa: BLE001
        return Bericht(adresse, grund=f"Abgleich gescheitert: {fehler}")
    bericht = Bericht(stand.adresse, grund=stand.grund, entwuerfe=stand.entwuerfe,
                      papierkorb=stand.papierkorb, hinweise=stand.hinweise)
    if stand.grund:
        return bericht
    wertung = [bewerte(z, stand) for z in stand.zustaende
               if z.art in ("wartet", "offen", "schon_raus")]
    zuege = tuple(w for w in wertung if isinstance(w, Zug) and w.uid not in ausser)
    bleibt = [w for w in wertung if isinstance(w, Bleibt)]
    bleibt += [Bleibt(w.uid, w.betreff, "offen", "eben geöffnet", True) for w in wertung
               if isinstance(w, Zug) and w.uid in ausser]
    bericht = bericht._replace(zuege=zuege, bleibt=tuple(bleibt))
    if not zuege:
        return bericht

    weg: list[str] = []
    gelungen: list[Zug] = []
    try:
        with postfach.verbinde(stand.adresse, umgebung=umgebung, frist=frist) as sitzung:
            ziel = papierkorb(sitzung, stand.entwuerfe_server)
            for zug in zuege:
                grund = _ziehe(sitzung, stand.entwuerfe_server, ziel, zug,
                               adresse=stand.adresse, umgebung=umgebung, machen=machen)
                if grund:
                    bleibt.append(Bleibt(zug.uid, zug.betreff, "neu_gelesen", grund, True))
                    continue
                gelungen.append(zug)
                if machen:
                    weg.append(zug.uid)
    except Exception as fehler:  # noqa: BLE001
        # `verschoben` bleibt stehen: Bricht der Lauf nach dem ersten von zwei Zügen
        # ab, wäre „nichts bewegt“ die falsche Aussage (#438).
        return bericht._replace(grund=str(fehler), verschoben=tuple(weg),
                                bleibt=tuple(bleibt))
    return bericht._replace(zuege=tuple(gelungen), bleibt=tuple(bleibt), verschoben=tuple(weg))


class Wertung(NamedTuple):
    """Was aus den passenden alten Entwürfen wird, wenn ein neuer Text kommt."""

    weg: tuple[Zug, ...] = ()
    bleibt: tuple[Bleibt, ...] = ()


def ersetzbar(sitzung: postfach.Postfach, ordner: str, koepfe: list, felder: Mapping, *,
              umgebung: Mapping[str, str], profilordner: Path | None = None) -> Wertung:
    """Welche alten Entwürfe darf der neue Text ablösen? Liest nur.

    Dieselben Sperren wie beim Aufräumen, plus eine: Gleich müssen die
    Empfänger als Menge sein. `oeffnen._gleicher_entwurf` lässt einen Schnitt
    gelten, das reicht, um keinen zweiten anzulegen, aber nicht zum Wegräumen.

    Was sich nicht prüfen lässt, bleibt liegen, mit Grund. Ein `PostfachFehler`
    geht durch: Darüber entscheidet der Aufrufer wie bei jedem Lesefehler.
    """
    try:
        return _werte_alte_aus(sitzung, ordner, koepfe, felder, umgebung=umgebung,
                               profilordner=profilordner)
    except postfach.PostfachFehler:
        raise
    except Exception as fehler:  # noqa: BLE001
        return Wertung(bleibt=tuple(
            Bleibt(k.uid, k.betreff, "beleg_unlesbar", f"nicht prüfbar: {fehler}")
            for k in koepfe))


def _werte_alte_aus(sitzung: postfach.Postfach, ordner: str, koepfe: list, felder: Mapping, *,
                    umgebung: Mapping[str, str], profilordner: Path | None) -> Wertung:
    adresse = str(felder.get("absender") or "").strip().lower()
    stand = entwurfsbuch.lesen(umgebung)
    eintraege, tagebuch_grund = entwurfsbuch.tagebuch(profilordner, umgebung)
    offen, offen_grund = entwurfsbuch._offene_uids(adresse, umgebung)
    bericht = entwurfsbuch.Bericht(adresse, fenster_grund=offen_grund, beleg_grund=" · ".join(
        g for g in (tagebuch_grund, f"{stand.unlesbar} Zeilen im Entwurfsbuch unlesbar"
                    if stand.unlesbar else "") if g))
    neu = postfach.kopf_aus(bytes(felder.get("roh") or b""), "0", None)
    weg, bleibt = [], []
    for kopf in koepfe:
        eintrag = next((e for e in stand.eintraege if e.konto == adresse and e.uid == kopf.uid
                        and kopf.fassung and e.fassung == kopf.fassung), None)
        kette = entwurfsbuch._kette(eintraege, adresse, kopf.uid)
        z = entwurfsbuch.Zustand(
            "wartet", kopf.betreff, kopf.an, kopf.datum, kopf.uid, im_buch=eintrag is not None,
            fassung=kopf.fassung, buch_zeit=eintrag.zeit if eintrag else None,
            text_gekappt=bool(eintrag and eintrag.text_gekappt),
            fenster=offen.get(kopf.uid), kette_offen=bool(kette & set(offen)),
            tagebuch=tuple(t for t in eintraege
                           if entwurfsbuch._gehoert_dazu(t, adresse, kette, kopf.fassung)))
        grund = next(((n, g) for n, g in ((n, s(z, bericht)) for n, s in SPERREN) if g), None)
        if grund is None and set(kopf.an) != set(neu.an):
            grund = ("andere_empfaenger", "die Empfänger sind nicht genau dieselben")
        if grund is None and eintrag is not None and not eintrag.text_gekappt:
            nachricht = email.message_from_bytes(sitzung.nachricht(ordner, kopf.uid),
                                                 policy=policy.default)
            if not entwurfsbuch.wortlaut_gleich(eintrag.text, gesendet.klartext(nachricht)):
                grund = ("text_weicht_ab", "Text weicht vom Entwurfsbuch ab, also geändert")
        if grund:
            bleibt.append(Bleibt(kopf.uid, kopf.betreff, *grund))
        else:
            weg.append(Zug(kopf.uid, kopf.betreff, kopf.an, kopf.fassung, kopf.datum,
                           NEUERE_FASSUNG, frozenset(kette)))
    return Wertung(tuple(weg), tuple(bleibt))


def ersetze(sitzung: postfach.Postfach, ordner: str, zuege: tuple[Zug, ...], *, adresse: str,
            umgebung: Mapping[str, str]) -> tuple[tuple[str, ...], tuple[Bleibt, ...], str, str]:
    """Räumt die abgelösten Entwürfe weg: `(uids, stehen geblieben, Abbruchgrund, Papierkorb)`.

    Läuft erst, wenn der neue Entwurf nachgezählt im Ordner liegt: Scheitert
    hier etwas, liegen zwei Entwürfe da, und es ist keiner verloren. Wirft nichts:
    Der neue Entwurf steht schon, und was bis zum Abbruch ging, muss gesagt werden.
    """
    weg, bleibt = [], []
    ziel = ""
    try:
        ziel = papierkorb(sitzung, ordner)
        for zug in zuege:
            grund = _ziehe(sitzung, ordner, ziel, zug, adresse=adresse, umgebung=umgebung,
                           machen=True)
            if grund:
                bleibt.append(Bleibt(zug.uid, zug.betreff, "neu_gelesen", grund, True))
            else:
                weg.append(zug.uid)
    except Exception as fehler:  # noqa: BLE001
        return tuple(weg), tuple(bleibt), str(fehler), ziel
    return tuple(weg), tuple(bleibt), "", ziel


# ── Ausgabe: ein Bericht, zwei Darstellungen ────────────────────────────────

def _wann(zeit: datetime | None) -> str:
    return zeit.astimezone().strftime("%d.%m.%Y %H:%M") if zeit else "ohne Datum"


def zeilen(bericht: Bericht) -> list[str]:
    """Der Bericht als Text. `NICHT GEPRÜFT` und `HINWEIS` gehören auf stderr."""
    nachspann = [f"HINWEIS  {h}" for h in bericht.hinweise]
    teile = []
    if bericht.grund:
        teile.append(f"NICHT GEPRÜFT  {bericht.adresse}: {bericht.grund}")
        if bericht.verschoben:
            teile.append(f"HINWEIS  vor dem Abbruch verschoben: UID "
                         f"{', '.join(bericht.verschoben)}")
    if not bericht.entwuerfe:
        return teile + nachspann
    if not bericht.grund:
        wirkung = (f" — {len(bericht.verschoben)} nach „{bericht.papierkorb}“ verschoben"
                   if bericht.verschoben else "")
        teile.append(f"OK  {bericht.adresse}: {len(bericht.zuege)} von "
                     f"{len(bericht.zuege) + len(bericht.bleibt)} in „{bericht.entwuerfe}“ "
                     f"sind überholt{wirkung}")
    for zug in bericht.zuege:
        stehen = " — nicht bewegt" if bericht.grund and zug.uid not in bericht.verschoben else ""
        teile.append(f"    UID {zug.uid}  {_wann(zug.datum)}  „{zug.betreff}“ — "
                     f"{REGEL_TEXT[zug.regel]}{stehen}")
    for rest in bericht.bleibt:
        teile.append(f"    BLEIBT UID {rest.uid}  „{rest.betreff}“ — {rest.grund}")
    if bericht.zuege and not bericht.verschoben and not bericht.grund:
        teile.append("    nichts bewegt — mit --machen verschieben")
    return teile + nachspann


def kurzzeilen(bericht: Bericht) -> list[str]:
    """Was `email --oeffnen` sagt: nur, was geschah oder was nicht geprüft wurde."""
    aus = []
    if bericht.grund:
        aus.append(f"NICHT GEPRÜFT  Entwürfe von {bericht.adresse} nicht aufgeräumt: "
                   f"{bericht.grund}")
    if bericht.verschoben:
        aus.append(f"OK  aus „{bericht.entwuerfe}“ von {bericht.adresse} weggeräumt: "
                   f"UID {', '.join(bericht.verschoben)} → „{bericht.papierkorb}“")
    gehalten = [r for r in bericht.bleibt if r.ueberholt]
    if gehalten:
        aus.append("HINWEIS  überholt, aber stehen gelassen: " + "; ".join(
            f"UID {r.uid} ({r.grund})" for r in gehalten))
    return aus


def als_json(bericht: Bericht) -> dict:
    """Derselbe Bericht als Datenstruktur. Dieselbe Aussage wie `zeilen`."""
    return {
        "absender": bericht.adresse, "geprueft": not bericht.grund, "grund": bericht.grund,
        "entwuerfe": bericht.entwuerfe, "papierkorb": bericht.papierkorb,
        "verschoben": list(bericht.verschoben), "hinweise": list(bericht.hinweise),
        "zuege": [{"uid": z.uid, "betreff": z.betreff, "an": list(z.an), "fassung": z.fassung,
                   "datum": z.datum.isoformat() if z.datum else None, "regel": z.regel}
                  for z in bericht.zuege],
        "bleibt": [{"uid": r.uid, "betreff": r.betreff, "sperre": r.sperre, "grund": r.grund,
                    "ueberholt": r.ueberholt} for r in bericht.bleibt],
    }
