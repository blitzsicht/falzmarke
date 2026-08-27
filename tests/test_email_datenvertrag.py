"""Der Datenvertrag der E-Mail-Fassung: `typ: email` (#62, ADR 0034).

Je Regel ein Fall, der sie auslöst, und einer, der sie nicht auslösen darf —
dasselbe Vorgehen wie in `test_lint.py`. Der zweite ist der wichtigere: Eine
Prüfung, die immer feuert, ist so wertlos wie eine, die nie feuert.
"""

from __future__ import annotations

import re

import pytest
import yaml

from falzmarke import cli as falzmarke
from falzmarke import lint as lint_modul
from conftest import REPO, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

MAIL = """typ: email
profil: example
an: erika.muster@example.de
betreff: Angebot Nr. 2026-0815
anrede: Sehr geehrte Frau Muster,
"""

BRIEF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Angebot Nr. 2026-0815
"""


def linte(tmp_path, kopf: str, body: str = "Text der Nachricht.\n"):
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(f"---\n{kopf}---\n{body}", encoding="utf-8")
    return falzmarke.linte(pfad, profil_verzeichnis=PROFILE)


def regeln(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde}


def warnungen(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde if b.schwere == lint_modul.WARNUNG}


# ── Der gültige Fall ────────────────────────────────────────────────────────

def test_gueltige_mail_ist_sauber(tmp_path):
    """Ohne diesen Fall wüsste man nur, dass die Prüfungen feuern."""
    bericht = linte(tmp_path, MAIL)
    assert bericht.befunde == [], bericht.als_text("nachricht.md")


def test_der_brief_bleibt_unberuehrt(tmp_path):
    assert linte(tmp_path, BRIEF).befunde == []


# ── Die beiden Welten schließen sich aus ────────────────────────────────────

def test_empfaenger_in_einer_mail_verweist_auf_an(tmp_path):
    bericht = linte(tmp_path, MAIL + "empfaenger: [Muster GmbH]\n")
    assert "typ" in regeln(bericht)
    text = bericht.als_text("nachricht.md")
    assert "`an:`" in text, text


def test_an_in_einem_brief_verweist_auf_empfaenger(tmp_path):
    bericht = linte(tmp_path, BRIEF + "an: post@example.de\n")
    assert "typ" in regeln(bericht)
    assert "`empfaenger:`" in bericht.als_text("nachricht.md")


@pytest.mark.parametrize("feld", ["form: B", "vermerke: [Einschreiben]", "betreff_kurz: kurz",
                                  "signatur: keine", "anlagen: [Angebot]", "norm: din5008"])
def test_papierfelder_gibt_es_in_einer_mail_nicht(tmp_path, feld):
    """Sie beschreiben ein Blatt Papier. Eine Mail hat keins."""
    assert "typ" in regeln(linte(tmp_path, MAIL + feld + "\n"))


def test_unbekannter_typ_bricht_ab(tmp_path):
    bericht = linte(tmp_path, MAIL.replace("typ: email", "typ: fax"))
    assert "typ" in regeln(bericht)
    assert "brief, email" in bericht.als_text("nachricht.md")


# ── Adressen ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("wert", [
    "erika.muster@example.de",
    "Muster GmbH <post@example.de>",
    "[a@example.de, Zweiter <b@example.de>]",
])
def test_gueltige_adressen_gehen_durch(tmp_path, wert):
    assert linte(tmp_path, MAIL.replace("an: erika.muster@example.de", f"an: {wert}")).befunde == []


@pytest.mark.parametrize("wert", ['"Erika Muster"', '"erika@"', '"@example.de"',
                                  '"erika example de"'])
def test_ungueltige_adressen_fallen_auf(tmp_path, wert):
    bericht = linte(tmp_path, MAIL.replace("an: erika.muster@example.de", f"an: {wert}"))
    assert "an" in regeln(bericht), bericht.als_text("nachricht.md")


def test_an_ist_pflicht(tmp_path):
    bericht = linte(tmp_path, MAIL.replace("an: erika.muster@example.de\n", ""))
    assert "an" in regeln(bericht)


def test_cc_wird_genauso_geprueft(tmp_path):
    assert "cc" in regeln(linte(tmp_path, MAIL + "cc: kein-adresse\n"))
    assert linte(tmp_path, MAIL + "cc: [zweiter@example.de]\n").befunde == []


# ── Betreff und Datum ───────────────────────────────────────────────────────

def test_betreff_ueber_78_zeichen(tmp_path):
    lang = "A" * (lint_modul.EMAIL_BETREFF_MAX + 1)
    bericht = linte(tmp_path, MAIL.replace("betreff: Angebot Nr. 2026-0815", f"betreff: {lang}"))
    assert "email.betreff" in regeln(bericht)


def test_betreff_genau_auf_der_grenze_ist_erlaubt(tmp_path):
    """Die Grenze selbst muss durchgehen — sonst prüft der Test daneben."""
    grad = "A" * lint_modul.EMAIL_BETREFF_MAX
    assert linte(tmp_path, MAIL.replace("betreff: Angebot Nr. 2026-0815",
                                        f"betreff: {grad}")).befunde == []


def test_datum_in_einer_mail_ist_eine_warnung_kein_fehler(tmp_path):
    """Die Zeile kann aus einem Brief stammen, der zur Mail umgeschrieben
    wurde. Ein Fehler hielte den Lauf an, obwohl nichts kaputt ist."""
    bericht = linte(tmp_path, MAIL + "datum: 2026-08-25\n")
    assert "email.datum" in warnungen(bericht)
    assert bericht.anzahl_fehler == 0


@pytest.mark.parametrize("wert, sauber", [
    ("<kennung@example.de>", True),
    ("kennung@example.de", False),
    ("<kennung@example.de", False),
])
def test_antwort_auf_ist_eine_message_id(tmp_path, wert, sauber):
    bericht = linte(tmp_path, MAIL + f'antwort_auf: "{wert}"\n')
    assert ("antwort_auf" in regeln(bericht)) != sauber


# ── Das Profil ──────────────────────────────────────────────────────────────

def test_das_beispielprofil_traegt_den_abschnitt():
    profil = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    bericht = lint_modul.Bericht()
    lint_modul.pruefe_email_profil(profil, bericht)
    assert bericht.befunde == [], bericht.als_text("example.yaml")


@pytest.mark.parametrize("profil, regel", [
    ({}, "email.profil"),
    ({"email": {"tippfehlr": 1, "absender": "a@b.de", "pflichtangaben": "x"}}, "email.profil"),
    ({"email": {"pflichtangaben": "x"}}, "email.absender"),
    ({"email": {"absender": "kein-adresse", "pflichtangaben": "x"}}, "email.absender"),
    ({"email": {"absender": "a@b.de"}}, "email.pflichtangaben"),
])
def test_profilfehler_fallen_auf(profil, regel):
    bericht = lint_modul.Bericht()
    lint_modul.pruefe_email_profil(profil, bericht)
    assert regel in {b.regel for b in bericht.befunde}, [b.regel for b in bericht.befunde]


def test_pflichtangaben_sind_eine_erinnerung_kein_fehler():
    """falzmarke prüft keine Rechtsform (ADR 0005). Ein Fehler wäre eine
    Zusage, die es nicht einlösen kann."""
    bericht = lint_modul.Bericht()
    lint_modul.pruefe_email_profil({"email": {"absender": "a@b.de"}}, bericht)
    assert bericht.anzahl_fehler == 0
    assert "email.pflichtangaben" in {b.regel for b in bericht.befunde}


def test_ein_brief_braucht_keinen_email_abschnitt(tmp_path):
    """Die Profilprüfung darf nur bei `typ: email` greifen — sonst würde jeder
    Brief mit einem Profil ohne `email:` plötzlich meckern."""
    ohne = tmp_path / "ohne-email.yaml"
    profil = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    del profil["email"]
    ohne.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{BRIEF.replace('profil: example', f'profil: {ohne}')}---\nText.\n",
                    encoding="utf-8")
    assert falzmarke.linte(pfad).befunde == []


# ── Code und Doku halten zusammen ───────────────────────────────────────────

def _dokumentierte_felder(block_nummer: int) -> set[str]:
    vertrag = (REPO / "skill" / "references" / "frontmatter.md").read_text(encoding="utf-8")
    block = vertrag.split("```yaml")[block_nummer].split("```", 1)[0]
    return set(re.findall(r"^\s*([a-z_]+):", block, flags=re.M))


def test_die_email_felder_stehen_in_der_doku():
    dokumentiert = _dokumentierte_felder(2)
    assert dokumentiert, "der Doku-Block wurde nicht gefunden — der Test misst nichts"
    fehlend = lint_modul.EMAIL_FRONTMATTER_FELDER - dokumentiert
    assert not fehlend, f"vom Linter erlaubt, aber nirgends dokumentiert: {sorted(fehlend)}"


def test_die_doku_erfindet_keine_email_felder():
    zuviel = _dokumentierte_felder(2) - lint_modul.EMAIL_FRONTMATTER_FELDER
    assert not zuviel, f"in der Doku, aber vom Linter abgewiesen: {sorted(zuviel)}"


def test_die_briefliste_ist_auch_rueckwaerts_gedeckt():
    """Der Abgleich in `test_lint.py` prüft nur Doku -> Code. Ein Feld, das der
    Linter neu erlaubt und das niemand dokumentiert, fiele dort nicht auf —
    genau die Alterung, gegen die dieser Abgleich gebaut wurde.
    """
    dokumentiert = _dokumentierte_felder(1)
    assert dokumentiert, "der Doku-Block wurde nicht gefunden — der Test misst nichts"
    fehlend = lint_modul.FRONTMATTER_FELDER - dokumentiert
    assert not fehlend, f"vom Linter erlaubt, aber nirgends dokumentiert: {sorted(fehlend)}"


def test_die_profilfelder_stehen_in_der_doku():
    dokumentiert = _dokumentierte_felder(3)
    assert dokumentiert, "der Doku-Block wurde nicht gefunden — der Test misst nichts"
    assert lint_modul.PROFIL_EMAIL_FELDER - dokumentiert == set()


def test_eine_mail_wird_nicht_als_brief_gesetzt(tmp_path):
    """Die Meldung muss die Ursache nennen, nicht die Folge.

    Vorher meldete der Renderer „Pflichtfelder fehlen: empfaenger, datum" für
    ein Schreiben, das als E-Mail vollständig ist. Wer daraufhin `empfaenger:`
    ergänzt, bekommt den Ausschluss des Linters — zwei Fehler hintereinander,
    und keiner sagt, was los ist.
    """
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(f"---\n{MAIL}---\nText.\n", encoding="utf-8")
    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        falzmarke.rendere(pfad, tmp_path / "aus.pdf", profil_verzeichnis=PROFILE)
    text = str(fehler.value)
    assert "typ: email" in text
    assert "Pflichtfelder fehlen" not in text, text


def test_der_brief_wird_weiterhin_gesetzt(tmp_path):
    """Kontrollprobe: Der Abbruch darf nur E-Mails treffen."""
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{BRIEF}---\nText.\n", encoding="utf-8")
    pdf, _ = falzmarke.rendere(pfad, tmp_path / "aus.pdf", profil_verzeichnis=PROFILE)
    assert pdf.exists() and pdf.stat().st_size > 0
