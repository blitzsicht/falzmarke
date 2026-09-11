#!/usr/bin/env python3
"""Die Fälle, an denen die Signatur hängt — als Daten, an einer Stelle (#221).

`eml.signatur_bloecke()` existiert zweimal: hier in Python und als Port in
JavaScript, den `falzmarke.com` für seinen Signatur-Baukasten braucht (der
rechnet im Browser, weil Name, Telefon und Anschrift personenbezogen sind und
das Gerät nicht verlassen sollen, blitzsicht-ops#750).

Dagegen hält die Website die Goldens aus diesem Repo. Das trägt byte-genau —
aber alle Goldens laufen auf **einem** Profil, und damit belegen sie genau die
Zweige, die dieses Profil durchläuft. Für die übrigen hatte das Website-Repo
eigene Erwartungen aufgeschrieben: Die prüfen, dass der Port sich nicht selbst
widerspricht, nicht dass er dasselbe täte wie dieses Werkzeug.

Deshalb diese Datei. Sie beschreibt jeden Fall als **Abwandlung** des
Beispielprofils; `scripts/golden_email.py` wendet sie an und schreibt Profil,
Kopf und erwartete Blöcke als JSON nach
`tests/golden/email/signatur-faelle.json`. Beide Seiten lesen dieselbe Datei:
dieses Repo als zweite Sicht auf vorhandene Tests, jeder weitere Umsetzer als
Unterschied zwischen „prüft sich selbst" und „prüft gegen das Werkzeug".

**Jeder Fall muss sich von jedem anderen unterscheiden.** Das ist keine
Ordnungsliebe, sondern der Kern: Der erste Entwurf hatte einen Fall
`ohne-anzeigename`, der dieselben Blöcke ergab wie der Basisfall — weil
`unterzeichner` denselben Namen trug. Ein Port, der `anzeigename` überhaupt
nicht liest, hätte beide Fälle bestanden. Ein Fall ohne Trennschärfe ist kein
Beleg, er sieht nur wie einer aus. `tests/test_signatur_fixture.py` hält das
fest, indem es die Blöcke aller Fälle gegeneinander vergleicht.

**Die Zweige sind gemessen, nicht aus #221 übernommen.** Der Vorgangstext nennt
den Telefon-Rückgriff auf `infoblock_defaults` als ungedeckt — am Beispielprofil
greift er aber schon, weil dort `email.telefon` gar nicht steht und
`infoblock_defaults.telefon` gesetzt ist. Ungedeckt ist die Gegenrichtung: ein
eigenes `email.telefon`, das gewinnt. Entsprechend heißt der Fall unten
`telefon-eigen` und nicht `telefon-rueckgriff`.

Wer einen Fall hinzufügt: Eintrag hier, dann `python3 scripts/golden_email.py`.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import NamedTuple

#: Der Kopf, wie ihn ein Brief mitbringt. Nur `unterzeichner` ist für die
#: Signatur von Belang — er ist die zweite von drei Quellen für den Namen.
KOPF = {"unterzeichner": "Erika Muster", "anrede": "Sehr geehrte Frau Muster,"}

#: Zwei Namen, die im Beispielprofil NICHT vorkommen — einer je Rückgriffstufe.
#:
#: Zwei und nicht einer: Mit demselben Namen für beide Stufen ergaben
#: `ohne-anzeigename` und `name-aus-dem-profil` identische Blöcke, und ein Port,
#: der nur eine der beiden Stufen kennt, hätte beide Fälle bestanden. Gefunden
#: hat das nicht das Lesen, sondern der Vergleich aller Fälle gegeneinander in
#: `tests/test_signatur_fixture.py`.
NAME_AUS_KOPF = "Dr. Anna Beispiel"
NAME_AUS_PROFIL = "Jonas Hoffmann"

#: Das Profil, aus dem alle Fälle abgeleitet werden.
BASISPROFIL = "example"


class Fall(NamedTuple):
    """Ein Fall: was am Profil anders ist, was am Kopf, und warum.

    `zweck` steht nicht im JSON — er ist für den, der diese Datei liest. Im JSON
    steht der Name, und der ist der Schlüssel, über den ein anderer Umsetzer
    seinen Fall wiederfindet. Namen werden deshalb nicht umbenannt.
    """

    zweck: str
    profil: Callable[[dict], dict]
    kopf: dict = KOPF


def _unveraendert(profil: dict) -> dict:
    return profil


def _pflichtangaben_liste(profil: dict) -> dict:
    profil["email"]["pflichtangaben"] = [
        "Amtsgericht Regensburg HRB 12345",
        "USt-IdNr. DE123456789",
    ]
    return profil


def _doppelte_zeile(profil: dict) -> dict:
    profil["email"]["pflichtangaben"] = [
        "www.example.de",
        "Amtsgericht Regensburg HRB 12345",
    ]
    return profil


def _ohne_pflichtangaben(profil: dict) -> dict:
    profil["email"].pop("pflichtangaben", None)
    return profil


def _telefon_eigen(profil: dict) -> dict:
    profil["email"]["telefon"] = "030 123456"
    return profil


def _ohne_anzeigename(profil: dict) -> dict:
    profil["email"].pop("anzeigename", None)
    return profil


def _name_aus_dem_profil(profil: dict) -> dict:
    profil["email"].pop("anzeigename", None)
    profil["unterzeichner"] = NAME_AUS_PROFIL
    return profil


def _karg(profil: dict) -> dict:
    return {"absender": {"name": "Muster GmbH"},
            "email": {"absender": "post@example.de"}}


FAELLE: dict[str, Fall] = {
    "fusszeile": Fall(
        "Der Basisfall — `pflichtangaben: fusszeile`. Firma und Anschrift kommen "
        "aus Spalte 1 der Fußzeile, die Registerangaben aus Spalte 4. Der einzige "
        "Zweig, den die Goldens schon belegen.",
        _unveraendert),

    "pflichtangaben-liste": Fall(
        "`pflichtangaben` als Liste. Der Unterschied ist nicht die Liste, sondern "
        "die Weiche darüber: Firma und Anschrift kommen jetzt aus `absender:` — am "
        "Beispielprofil dieselbe Adresse in anderer Schreibweise, „Musterweg 12 · "
        "93055 Regensburg“ in einer Zeile statt in drei.",
        _pflichtangaben_liste),

    "doppelte-zeile-in-zwei-bloecken": Fall(
        "Dieselbe Zeile in zwei Blöcken — der Fall, für den es die Entdoppelung "
        "gibt. `eml.py` sagt über diese Schleife selbst: „Am mitgelieferten Profil "
        "läuft diese Schleife deshalb leer, und ein Test, der nur dort misst, "
        "belegt nichts.“ Wer seine Website in den Pflichtangaben wiederholt, hat "
        "sie im Kontakt- und im Rechtsteil; block-lokal entdoppelt stünde sie "
        "zweimal da.",
        _doppelte_zeile),

    "ohne-pflichtangaben": Fall(
        "Kein `pflichtangaben` — der Rechtsblock trägt Firma und Anschrift aus "
        "`absender:`, aber keine Registerangaben. falzmarke ergänzt keine "
        "(ADR 0005).",
        _ohne_pflichtangaben),

    "telefon-eigen": Fall(
        "Ein eigenes `email.telefon` gewinnt über `infoblock_defaults`. Die "
        "Gegenrichtung zum Basisfall: Dort fehlt `email.telefon`, und der "
        "Rückgriff greift — deshalb ist *er* von den Goldens gedeckt und diese "
        "Richtung nicht.",
        _telefon_eigen),

    "ohne-anzeigename": Fall(
        "Kein `email.anzeigename` — der Name kommt aus `unterzeichner` des "
        "**Kopfes**. Der Kopf trägt hier bewusst einen anderen Namen als das "
        "Profil: Mit demselben wäre der Fall nicht vom Basisfall zu "
        "unterscheiden, und ein Port, der `anzeigename` ignoriert, bestünde beide.",
        _ohne_anzeigename,
        {"unterzeichner": NAME_AUS_KOPF, "anrede": "Sehr geehrte Frau Beispiel,"}),

    "name-aus-dem-profil": Fall(
        "Die dritte und letzte Stufe: weder `email.anzeigename` noch ein "
        "`unterzeichner` im Kopf — dann gilt der des Profils. Auch hier ein "
        "abweichender Name, aus demselben Grund.",
        _name_aus_dem_profil,
        {"anrede": "Sehr geehrte Damen und Herren,"}),

    "karg": Fall(
        "Fast nichts — weniger Blöcke statt leerer. Ein leerer Block erschiene "
        "als Leerzeile mitten in der Signatur und sähe aus wie ein Fehler des "
        "Absenders, nicht wie ein fehlendes Profilfeld.",
        _karg),
}


def wandle(name: str, basis: dict) -> tuple[dict, dict]:
    """Profil und Kopf eines Falles. `basis` bleibt unberührt."""
    fall = FAELLE[name]
    return fall.profil(copy.deepcopy(basis)), fall.kopf
