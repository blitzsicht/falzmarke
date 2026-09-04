"""Brief und Begleitmail in einem Zug (#78).

Der häufigste Fall im Geschäftsverkehr: Das förmliche Schreiben geht als PDF im
Anhang, und die Mail daneben sagt in drei Sätzen, worum es geht. Bisher waren das
drei Schritte von Hand — rendern, Mail schreiben, den Dateinamen des eben
entstandenen PDF eintragen.

## Warum zwei Dateien und nicht eine

Der Vorgang lässt die Gestaltung offen und nennt zwei Wege. Gewählt ist der
zweite: **Die Mail nennt den Brief, nicht sein PDF.**

Der erste Weg — eine Datei mit zwei Teilen — bräuchte eine neue Trennung im
Dialekt, die er heute nicht kennt. Jede solche Trennung ist eine Stelle, an der
ein Brieftext versehentlich zum Mailtext wird oder umgekehrt; und der Dialekt
ist die Schnittstelle, an der dieses Werkzeug am teuersten ändert.

Der zweite Weg kostet ein Feld und lässt beides, was es ist: `brief:` zeigt auf
die **Quelle**, nicht auf das PDF. Was daraus folgt, ist der Kern von #78 — ein
veraltetes PDF kann nicht mitreisen, weil es keines gibt, das älter wäre als
dieser Aufruf. Der Brief wird beim Bauen der Nachricht gesetzt.

## Und was die Mail erbt

`betreff`, `profil`, `dialekt`, `sprache` — alles, was denselben Vorgang
beschreibt und zweimal gepflegt auseinanderdriftet.

**Nicht** `empfaenger`: Eine Postanschrift ist keine Mailadresse. **Nicht**
`datum`: Die Kopfzeile `Date` entsteht seit #236 beim Setzen der Nachricht und
beschreibt diese; ein geerbtes Briefdatum wäre eine Angabe über den falschen
Vorgang.
"""

from __future__ import annotations

import email
import email.policy
from datetime import date
from email.utils import parsedate_to_datetime

import pytest

from conftest import SKILL
from falzmarke import cli, lint

#: Das `datum:` im BRIEF unten. Steht hier, damit ein geänderter Brief
#: den Test bricht statt ihn still wirkungslos zu machen.
BRIEFDATUM = date(2026, 8, 29)

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

BRIEF = """---
profil: example
empfaenger: [Beispiel AG, Beispielweg 7, 54321 Beispielhausen]
datum: 2026-08-29
betreff: Kündigung des Wartungsvertrags Nr. 2026-0815
anrede: Sehr geehrte Damen und Herren,
---
hiermit kündige ich den Wartungsvertrag Nr. 2026-0815 fristgerecht zum
31. Dezember 2026.
"""

MAIL = """---
typ: email
an: service@example.de
brief: kuendigung.md
{extra}---
im Anhang finden Sie die Kündigung des Wartungsvertrags als PDF.
"""


def _aufbau(tmp_path, extra: str = "", brief: str = BRIEF):
    (tmp_path / "kuendigung.md").write_text(brief, encoding="utf-8")
    pfad = tmp_path / "begleitmail.md"
    pfad.write_text(MAIL.format(extra=extra), encoding="utf-8")
    return pfad


def _nachricht(tmp_path, **kwargs):
    pfad = _aufbau(tmp_path, **kwargs)
    ziel, _ = cli.setze_email(pfad, tmp_path / "ausgabe", profil_verzeichnis=PROFILE)
    return email.message_from_bytes(ziel.read_bytes(), policy=email.policy.default)


def _anhaenge(nachricht) -> list[tuple[str, bytes]]:
    return [(t.get_filename(), t.get_content())
            for t in nachricht.walk() if t.get_filename()]


# ── Ein Aufruf, beide Erzeugnisse ───────────────────────────────────────────

def test_das_pdf_haengt_an_der_nachricht(tmp_path):
    anhaenge = _anhaenge(_nachricht(tmp_path))
    assert len(anhaenge) == 1, anhaenge
    name, inhalt = anhaenge[0]
    assert name == "kuendigung.pdf", name
    assert inhalt[:5] == b"%PDF-", "der Anhang ist kein PDF"


def test_ohne_das_feld_haengt_nichts_dran(tmp_path):
    """Gegenprobe: Sonst wüsste man nicht, ob der Anhang vom Feld kommt."""
    (tmp_path / "kuendigung.md").write_text(BRIEF, encoding="utf-8")
    pfad = tmp_path / "m.md"
    pfad.write_text(
        "---\ntyp: email\nprofil: example\nan: a@example.de\n"
        "betreff: Ohne Anhang\n---\nNur Text.\n", encoding="utf-8")
    ziel, _ = cli.setze_email(pfad, tmp_path / "ohne", profil_verzeichnis=PROFILE)
    nachricht = email.message_from_bytes(ziel.read_bytes(), policy=email.policy.default)
    assert _anhaenge(nachricht) == []


def test_der_betreff_wird_geerbt(tmp_path):
    assert _nachricht(tmp_path)["Subject"] == "Kündigung des Wartungsvertrags Nr. 2026-0815"


def test_ein_eigener_betreff_gewinnt(tmp_path):
    """Geerbt wird nur, was fehlt. Wer in der Mail etwas anderes schreiben will,
    schreibt es — die Kopplung nimmt niemandem die Wahl."""
    nachricht = _nachricht(tmp_path, extra="betreff: Unterlagen zur Kündigung\n")
    assert nachricht["Subject"] == "Unterlagen zur Kündigung"


def test_die_mailadresse_wird_nicht_geerbt(tmp_path):
    """`an:` bleibt Pflicht — eine Postanschrift ist keine Mailadresse.

    Ohne `an:` muss der Datenvertrag anschlagen, auch wenn ein Brief dranhängt.
    """
    (tmp_path / "kuendigung.md").write_text(BRIEF, encoding="utf-8")
    pfad = tmp_path / "ohne-an.md"
    pfad.write_text("---\ntyp: email\nbrief: kuendigung.md\n---\nText.\n", encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    assert "an" in {b.regel for b in bericht.befunde}, bericht.als_text(pfad.name)


def test_und_das_briefdatum_auch_nicht(tmp_path):
    """`Date` beschreibt die Nachricht, nicht den Brief, der ihr anhängt.

    Der Vergleich lief bis #236 gegen die Zeichenkette „2026-08-29" — die ein
    RFC-5322-Datum („Fri, 04 Sep 2026 …") gar nicht enthalten kann. Der Test
    war doppelt wirkungslos: Damals stand ohnehin kein `Date` in der Datei, und
    selbst mit einem geerbten Briefdatum wäre er grün geblieben.

    Jetzt wird das Datum gelesen und gegen den Tag des Briefes gehalten.
    """
    datum = parsedate_to_datetime(str(_nachricht(tmp_path)["Date"]))
    assert datum.date() != BRIEFDATUM, (
        f"Die Nachricht trägt das Datum des Briefes ({BRIEFDATUM}) — `Date` soll "
        "den Zeitpunkt beschreiben, an dem die Nachricht entstand")
    assert datum.date() >= BRIEFDATUM, (
        "Gegenprobe zum assert darüber: Das Datum muss ein echter Zeitpunkt sein, "
        f"nicht irgendein Wert ungleich {BRIEFDATUM}")


# ── Das PDF ist immer frisch ────────────────────────────────────────────────

def test_ein_geaenderter_brief_aendert_den_anhang(tmp_path):
    """Der Kern von #78: „ein veraltetes PDF in einer frischen Mail muss
    auffallen und nicht stillschweigend mitreisen."

    Es kann gar nicht veralten — es entsteht bei jedem Aufruf neu.
    """
    erste = _anhaenge(_nachricht(tmp_path))[0][1]
    geaendert = BRIEF.replace("31. Dezember 2026", "30. Juni 2027")
    zweite = _anhaenge(_nachricht(tmp_path, brief=geaendert))[0][1]
    assert erste != zweite, "der Anhang blieb gleich, obwohl der Brief sich änderte"


def test_daneben_beigelegte_dateien_bleiben(tmp_path):
    """`brief:` ergänzt `anlagen_dateien:`, es ersetzt sie nicht."""
    (tmp_path / "beleg.pdf").write_bytes(b"%PDF-1.4 Beleg")
    anhaenge = _anhaenge(_nachricht(tmp_path, extra="anlagen_dateien: [beleg.pdf]\n"))
    namen = sorted(n for n, _ in anhaenge)
    assert namen == ["beleg.pdf", "kuendigung.pdf"], namen


# ── Was abgewiesen wird ─────────────────────────────────────────────────────

def test_eine_fehlende_briefdatei_bricht_ab(tmp_path):
    pfad = tmp_path / "m.md"
    pfad.write_text("---\ntyp: email\nan: a@example.de\nbrief: gibtsnicht.md\n"
                    "betreff: X\nprofil: example\n---\nText.\n", encoding="utf-8")
    with pytest.raises(cli.Eingabefehler, match="gibt es nicht"):
        cli.setze_email(pfad, tmp_path / "x", profil_verzeichnis=PROFILE)


def test_eine_nachricht_kann_keine_nachricht_begleiten(tmp_path):
    """Sonst entstünde eine Mail, die eine Mail als PDF anhängt — und `rendere`
    bräche mit einer Meldung ab, die von einem Brief spricht."""
    (tmp_path / "andere.md").write_text(
        "---\ntyp: email\nprofil: example\nan: b@example.de\nbetreff: X\n---\nText.\n",
        encoding="utf-8")
    pfad = tmp_path / "m.md"
    pfad.write_text("---\ntyp: email\nan: a@example.de\nbrief: andere.md\n"
                    "betreff: X\nprofil: example\n---\nText.\n", encoding="utf-8")
    with pytest.raises(cli.Eingabefehler, match="keine Nachricht begleiten"):
        cli.setze_email(pfad, tmp_path / "x", profil_verzeichnis=PROFILE)


def test_ein_pdf_im_feld_wird_abgewiesen(tmp_path):
    """`brief:` zeigt auf die Quelle, nicht auf das Ergebnis.

    Ein fertiges PDF gehört in `anlagen_dateien:` — dort ist es richtig
    aufgehoben, und die Meldung sagt das.
    """
    (tmp_path / "kuendigung.md").write_text(BRIEF, encoding="utf-8")
    pfad = tmp_path / "m.md"
    pfad.write_text("---\ntyp: email\nan: a@example.de\nbrief: kuendigung.pdf\n"
                    "betreff: X\nprofil: example\n---\nText.\n", encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    befunde = [b for b in bericht.befunde if b.regel == "brief"]
    assert befunde, bericht.als_text(pfad.name)
    assert "anlagen_dateien" in befunde[0].korrektur


def test_ein_leeres_feld_ebenso(tmp_path):
    (tmp_path / "kuendigung.md").write_text(BRIEF, encoding="utf-8")
    pfad = tmp_path / "m.md"
    pfad.write_text("---\ntyp: email\nan: a@example.de\nbrief: \"\"\n"
                    "betreff: X\nprofil: example\n---\nText.\n", encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    assert "brief" in {b.regel for b in bericht.befunde}


# ── Beide Zusagen bleiben gültig ────────────────────────────────────────────

def test_verify_email_misst_die_nachricht_weiter(tmp_path):
    """Aus #78: „keine wird durch die Kopplung schwächer."""
    from falzmarke import pruefung_eml

    pfad = _aufbau(tmp_path)
    ziel, _ = cli.setze_email(pfad, tmp_path / "ausgabe", profil_verzeichnis=PROFILE)
    bericht = pruefung_eml.pruefe(ziel)
    gescheitert = [p.name for p in bericht.pruefungen if not p.bestanden]
    assert not gescheitert, gescheitert


def test_das_angehaengte_pdf_haelt_die_masse(tmp_path):
    """Und der Brief bleibt ein geprüfter Brief — nicht weniger, weil er
    diesmal in einer Mail steckt."""
    from falzmarke import geometrie

    pfad = _aufbau(tmp_path)
    ziel, _ = cli.setze_email(pfad, tmp_path / "ausgabe", profil_verzeichnis=PROFILE)
    nachricht = email.message_from_bytes(ziel.read_bytes(), policy=email.policy.default)
    inhalt = _anhaenge(nachricht)[0][1]
    (tmp_path / "aus.pdf").write_bytes(inhalt)
    bericht = geometrie.pruefe(tmp_path / "aus.pdf", "B")
    gescheitert = [p.name for p in bericht.pruefungen if not p.bestanden]
    assert not gescheitert, gescheitert


# ── Die beiden Listen bleiben zusammen ──────────────────────────────────────

def test_der_linter_und_das_setzen_kennen_dieselben_erbbaren_felder():
    """Sie stehen an zwei Stellen — `lint.ERBBARE_FELDER` und
    `cli.ERBT_VOM_BRIEF`. Zusammenzulegen hiesse, dass `lint` das ganze
    CLI-Modul lädt; auseinanderlaufen dürfen sie trotzdem nicht.

    `lint` darf die kürzere Liste haben: Es geht dort nur um Pflichtfelder, und
    `dialekt` und `sprache` sind keine.
    """
    assert set(lint.ERBBARE_FELDER) <= set(cli.ERBT_VOM_BRIEF)
    assert set(lint.ERBBARE_FELDER) == set(lint.EMAIL_PFLICHTFELDER) - {"an"}
