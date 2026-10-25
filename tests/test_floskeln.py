"""Wendungen, die nichts sagen — als Warnung, nie als Fehler (#106).

„Ich hoffe, diese E-Mail erreicht Sie wohlauf" ist nicht falsch. Es ist leer:
Die Zeile ließe sich streichen, ohne dass die Nachricht etwas verlöre. Genau das
ist die Aufnahmebedingung dieser Liste.

## Die Gegenrichtung trägt hier mehr als die Richtung

Eine Warnung, die bei gültigem Text anschlägt, kostet Vertrauen in alle anderen
— das war die Lehre aus der Telefonprüfung (#133), wo eine zu strenge Regel jede
Vorwahl kleinerer Orte meldete. Deshalb steht unten zu jeder Floskel eine
Wendung, die ihr **ähnlich sieht und bleiben muss**:

| gemeldet | bleibt |
|---|---|
| „vielen Dank für Ihre Zeit" | „vielen Dank für die Unterlagen" |
| „ich hoffe, es geht Ihnen gut" | „ich hoffe, der Termin passt Ihnen" |
| „wollte mich nur kurz melden" | „ich melde mich wegen der Rechnung" |
| „jederzeit gerne zur Verfügung" | „bei Rückfragen stehe ich zur Verfügung" |
| „es ist wichtig zu beachten" | „wichtig: die Frist endet am 15." |
| „wir würden uns freuen" | „wir freuen uns auf die Zusammenarbeit" |

Der Unterschied ist jedes Mal derselbe: Trägt der Satz eine Information oder
nicht.
"""

from __future__ import annotations

import pytest

from conftest import SKILL
from falzmarke import cli, lint

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

MAIL = """---
typ: email
profil: example
an: erika.muster@example.de
betreff: Angebot Nr. 2026-0815
---
{text}
"""

#: Was gemeldet werden muss. Je Muster mindestens einer, damit kein Eintrag der
#: Liste ungeprüft bleibt.
LEER = [
    "Ich hoffe, diese E-Mail erreicht Sie wohlauf.",
    "Ich hoffe, diese Nachricht erreicht dich gut.",
    "Ich hoffe, es geht Ihnen gut.",
    "ich hoffe, es geht dir gut.",
    "Ich wollte mich nur kurz melden.",
    "Wollte nur kurz nachfragen.",
    "Vielen Dank für Ihre Zeit.",
    "vielen Dank für deine Zeit.",
    "Ich freue mich auf Ihre Rückmeldung.",
    "Freue mich auf deine Antwort.",
    "Wie bereits erwähnt, möchte ich auf den Termin hinweisen.",
    "In diesem Sinne verbleibe ich.",
    # Seit #402.
    "Es ist wichtig zu beachten, dass die Frist am 15. September endet.",
    "Es ist wichtig zu wissen, dass die Ware vorab bezahlt wird.",
    "Zusammenfassend lässt sich sagen, dass die Lieferung steht.",
    "Abschließend lässt sich sagen, dass alles geklärt ist.",
    "In der heutigen schnelllebigen Geschäftswelt zählt Verlässlichkeit.",
    "Ich stehe Ihnen jederzeit gerne zur Verfügung.",
    "Für weitere Auskünfte stehe ich jederzeit zu Ihrer Verfügung.",
    "An dieser Stelle möchte ich auf die Frist hinweisen.",
    "Wie Sie sicher wissen, läuft der Vertrag Ende März aus.",
    "Wie Sie bereits wissen, ist die Ware unterwegs.",
    "Im Voraus vielen Dank für Ihre Mühe.",
    "Wir würden uns freuen, von Ihnen zu hören.",
    "Ich würde mich sehr freuen, wenn Sie zusagen.",
]

#: Was bleiben muss. Jede Zeile sieht einer Floskel ähnlich und trägt trotzdem
#: etwas — das ist der Fall, an dem eine zu grobe Regel scheitert.
TRAEGT = [
    "Vielen Dank für die Unterlagen vom 14. August.",
    "Ich hoffe, der Termin am 3. September passt Ihnen.",
    "Ich melde mich wegen der Rechnung Nr. 2026-0815.",
    "Im Anhang finden Sie das Angebot.",
    "Bei Rückfragen erreichen Sie mich unter 0941 620-9800.",
    "Wie besprochen sende ich Ihnen die Unterlagen.",
    "Bitte bestätigen Sie den Termin bis zum 1. September 2026.",
    "Die Frist läuft am 15. September 2026 ab.",
    "Ich freue mich, dass die Lieferung angekommen ist.",
    "Vielen Dank, dass Sie so schnell geantwortet haben.",
    # Seit #402. Jede Zeile sieht einem der neuen Muster aehnlich.
    "Wichtig: Die Frist endet am 15. September 2026.",
    "Zusammengefasst: drei Vorlagen, eine davon mit Logo.",
    "In diesem Jahr sind die Papierpreise um 8 % gestiegen.",
    "Bei Rückfragen stehe ich zur Verfügung.",
    "Für Rückfragen erreichen Sie mich montags bis donnerstags.",
    "An dieser Stelle fehlt die Unterschrift.",
    "Wie Sie am Lieferschein sehen, fehlen zwei Kartons.",
    "Vielen Dank für die schnelle Zusage.",
    "Wir freuen uns auf die Zusammenarbeit ab dem 1. Oktober.",
    "Es ist wichtig, dass die Kartons trocken stehen.",
]


def _befunde(tmp_path, text: str) -> list[str]:
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(MAIL.format(text=text), encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    return [b.regel for b in bericht.befunde]


# ── Was gemeldet wird ───────────────────────────────────────────────────────

@pytest.mark.parametrize("satz", LEER)
def test_eine_leere_wendung_wird_gemeldet(tmp_path, satz):
    assert "email.floskel" in _befunde(tmp_path, f"{satz}\n\nAnbei das Angebot.\n")


def test_jedes_muster_hat_einen_fall():
    """Ein Muster ohne Auslöser wäre nie gemessen — und stünde da, ohne dass
    jemand wüsste, ob es überhaupt greift."""
    ungedeckt = [name for muster, name in lint.FLOSKELN
                 if not any(muster.search(s) for s in LEER)]
    assert not ungedeckt, ungedeckt


# ── Und was bleibt ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("satz", TRAEGT)
def test_ein_satz_der_etwas_traegt_bleibt(tmp_path, satz):
    """Die wichtigere Richtung.

    Eine Warnung, die bei gültigem Text anschlägt, kostet Vertrauen in alle
    anderen — dann schaltet man sie ab, und die echten Befunde gehen mit.
    """
    assert "email.floskel" not in _befunde(tmp_path, f"{satz}\n")


def test_die_beispiele_bleiben_ohne_befund():
    """Der Bestand ändert sich durch die neue Regel nicht."""
    from conftest import EMAIL_BEISPIELE

    for beispiel in EMAIL_BEISPIELE:
        bericht = cli.linte(beispiel, profil_verzeichnis=PROFILE)
        assert "email.floskel" not in [b.regel for b in bericht.befunde], beispiel.name


# ── Sie hält den Lauf nicht an ──────────────────────────────────────────────

def test_eine_floskel_ist_kein_fehler(tmp_path):
    """Nach ADR 0035 gehört eine Aussage über den Stil nie auf die Fehlerebene.

    Sie ändert auch nichts: Der Text kommt unverändert durch. Ein Werkzeug, das
    ungefragt Sätze streicht, streicht irgendwann den falschen.

    Dieser Test misst mehr, als es beim Schreiben aussah — gemerkt beim
    Sabotieren: `bericht.warnung` gegen `bericht.fehler` zu tauschen ändert
    **nichts**. `Bericht.fehler` deckelt selbst, anhand der Ebene aus dem
    Regelwerk; eine Regel auf Ebene `praxis` KANN kein Fehler werden. Erst wer
    die Ebene in `regeln/email.yaml` hochsetzt, bringt diesen Test zu Fall —
    und genau das ist die Stelle, an der die Entscheidung steht.
    """
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(MAIL.format(text="Ich hoffe, es geht Ihnen gut.\n\nAnbei das Angebot.\n"),
                    encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    assert bericht.ok, "eine Floskel darf den Lauf nicht anhalten"

    ziel, _ = cli.setze_email(pfad, tmp_path / "nachricht", profil_verzeichnis=PROFILE)
    assert "Ich hoffe, es geht Ihnen gut." in ziel.read_text(encoding="utf-8", errors="replace")


def test_die_meldung_nennt_die_wendung(tmp_path):
    """Sonst weiß niemand, welche Zeile gemeint ist."""
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(MAIL.format(text="Vielen Dank für Ihre Zeit.\n"), encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    meldungen = [b.meldung for b in bericht.befunde if b.regel == "email.floskel"]
    assert meldungen and "Ihre Zeit" in meldungen[0], meldungen


# ── Und die Stilreferenz sagt dasselbe ──────────────────────────────────────

def test_die_stilreferenz_nennt_den_aufbau():
    text = (SKILL / "references" / "stil.md").read_text(encoding="utf-8")
    for schritt in ("Grund des Schreibens", "gewünschte Handlung", "Frist", "Signatur"):
        assert schritt in text, f"„{schritt}“ fehlt im Aufbau"


def test_die_stilreferenz_nennt_die_grenze_der_floskelregel():
    """Die Regel ist nur brauchbar, wenn jemand sie nachvollziehen kann."""
    text = (SKILL / "references" / "stil.md").read_text(encoding="utf-8")
    assert "Vielen Dank für die Unterlagen" in text, "der Gegenfall fehlt"


def test_und_dass_kein_fliesstext_in_bilder_gehoert():
    text = (SKILL / "references" / "stil.md").read_text(encoding="utf-8")
    assert "Kein Fließtext in Bildern" in text
