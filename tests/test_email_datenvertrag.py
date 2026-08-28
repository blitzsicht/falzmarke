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
    """Die Grenze selbst muss durchgehen — sonst prüft der Test daneben.

    Kein *Fehler*; die Vorschauwarnung ab 60 Zeichen greift hier sehr wohl und
    soll es auch (#64, E6).
    """
    grad = "A" * lint_modul.EMAIL_BETREFF_MAX
    bericht = linte(tmp_path, MAIL.replace("betreff: Angebot Nr. 2026-0815",
                                           f"betreff: {grad}"))
    assert bericht.anzahl_fehler == 0, bericht.als_text("nachricht.md")
    assert warnungen(bericht) == {"email.betreff"}


def test_kurzer_betreff_loest_keine_vorschauwarnung_aus(tmp_path):
    """Gegenprobe: Ohne sie wüsste man nur, dass die Warnung feuert."""
    kurz = "A" * (lint_modul.EMAIL_BETREFF_VORSCHAU - 1)
    assert linte(tmp_path, MAIL.replace("betreff: Angebot Nr. 2026-0815",
                                        f"betreff: {kurz}")).befunde == []


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


# ── Anlagen werden genannt, nicht eingefügt ─────────────────────────────────

def _mit_anlage(tmp_path, text: str):
    (tmp_path / "angebot-2026-0815.pdf").write_bytes(b"%PDF-1.4 x")
    return linte(tmp_path, MAIL + "anlagen_dateien: [angebot-2026-0815.pdf]\n", text)


def test_nicht_genannte_anlage_wird_gemeldet(tmp_path):
    bericht = _mit_anlage(tmp_path, "Hier ist etwas anderes.\n")
    assert "email.anlage" in warnungen(bericht)


def test_genannte_anlage_wird_nicht_gemeldet(tmp_path):
    """Ohne diesen Fall wüsste man nur, dass die Warnung feuert."""
    assert _mit_anlage(tmp_path, "Das Angebot 2026-0815 liegt bei.\n").befunde == []


def test_die_anlage_wird_nicht_von_selbst_erwaehnt(tmp_path):
    """Ein Werkzeug, das ungefragt Sätze in einen Brieftext schreibt, schreibt
    irgendwann den falschen. Gemeldet wird, eingefügt nicht."""
    pfad = tmp_path / "nachricht.md"
    (tmp_path / "angebot-2026-0815.pdf").write_bytes(b"%PDF-1.4 x")
    quelle = f"---\n{MAIL}anlagen_dateien: [angebot-2026-0815.pdf]\n---\nNur dieser Satz.\n"
    pfad.write_text(quelle, encoding="utf-8")
    falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert pfad.read_text(encoding="utf-8") == quelle


def test_die_warnung_haelt_den_lauf_nicht_an(tmp_path):
    assert _mit_anlage(tmp_path, "Hier ist etwas anderes.\n").anzahl_fehler == 0


# ── Vollständigkeit: keine Regel ohne Auslöser ──────────────────────────────
#
# Die Fälle oben stehen einzeln und von Hand. Kommt eine Regel dazu, fällt hier
# auf, dass niemand einen Auslöser dafür geschrieben hat — dasselbe Muster wie
# `test_emitter_kennt_jeden_knoten` in test_emit_html.py. Die Regelmenge kommt
# aus der Regeldatei, nicht aus einer zweiten Liste: Zwei gepflegte Listen
# laufen auseinander, und die falsche fällt niemandem auf.

def _profil_ohne(feld: str, tmp_path) -> Path:
    """Das Beispielprofil, an einer Stelle beschnitten."""
    profil = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    if feld == "email":
        del profil["email"]
    else:
        del profil["email"][feld]
    ziel = tmp_path / "profile"
    ziel.mkdir(exist_ok=True)
    (ziel / "example.yaml").write_text(yaml.safe_dump(profil, allow_unicode=True),
                                       encoding="utf-8")
    return ziel


def _loese_aus(regel: str, tmp_path):
    """Ein Fall, der genau diese Regel melden muss."""
    if regel == "email.betreff":
        return linte(tmp_path, MAIL.replace("Angebot Nr. 2026-0815", "Angebot " + "sehr lang " * 9))
    if regel == "email.datum":
        return linte(tmp_path, MAIL + "datum: 2026-08-27\n")
    if regel == "infoblock.email":
        # Als **Brief**: Einen Informationsblock gibt es in einer Mail nicht,
        # der Datenvertrag weist ihn dort ab, bevor die Adresse geprüft würde.
        # Die Regel traegt trotzdem das Praefix `email`, weil sie eine
        # E-Mail-Adresse prueft — nicht, weil sie zur E-Mail-Fassung gehoert.
        return linte(tmp_path, BRIEF + "infoblock:\n  email: keine-adresse\n")
    if regel == "email.anlage":
        (tmp_path / "beleg-4711.pdf").write_bytes(b"%PDF-1.4 x")
        return linte(tmp_path, MAIL + "anlagen_dateien: [beleg-4711.pdf]\n",
                     "Kein Wort über den Anhang.\n")
    if regel == "typ":
        # Ein Briefeld in einer Mail: der Datenvertrag trennt die beiden.
        return linte(tmp_path, MAIL + "empfaenger: [Muster GmbH, Musterstraße 1]\n")
    if regel == "an":
        return linte(tmp_path, MAIL.replace("an: erika.muster@example.de",
                                            "an: keine-adresse"))
    if regel == "cc":
        return linte(tmp_path, MAIL + "cc: [auch-keine-adresse]\n")
    if regel == "email.adresse_international":
        # Nach RFC 6531 zulaessig, deshalb KEIN Fehler — die Regel liegt auf der
        # Ebene Praxis und warnt nur. Die Form muss stimmen, sonst schlaege
        # `an` zu und nicht diese Regel.
        return linte(tmp_path, MAIL.replace("an: erika.muster@example.de",
                                            "an: müller@münchen.de"))
    if regel == "antwort_auf":
        # Message-IDs stehen nach RFC 5322 in spitzen Klammern.
        return linte(tmp_path, MAIL + "antwort_auf: ohne-spitze-klammern@example.de\n")
    if regel in ("email.profil", "email.absender", "email.pflichtangaben"):
        feld = {"email.profil": "email", "email.absender": "absender",
                "email.pflichtangaben": "pflichtangaben"}[regel]
        pfad = tmp_path / "nachricht.md"
        pfad.write_text(f"---\n{MAIL}---\nText der Nachricht.\n", encoding="utf-8")
        return falzmarke.linte(pfad, profil_verzeichnis=_profil_ohne(feld, tmp_path))
    raise AssertionError(f"kein Auslöser für {regel} — bitte einen ergänzen")


def _regeln_der_regeldatei() -> set[str]:
    """Die Regeln der E-Mail-Fassung — gefragt wird die Herkunftsdatei.

    Bis v0.8.1 lief der Filter über das ID-Präfix `werkzeug.email`. Das war
    ein Behelf und hat sich an zwei Stellen gerächt: `werkzeug.email_im_infoblock`
    fiel hinein, obwohl es eine **Brief**regel ist (eine E-Mail-Adresse im
    Informationsblock), und `typ`, `an`, `cc` und `antwort_auf` fielen heraus,
    obwohl sie zum Datenvertrag der Mail gehören. Seit ADR 0035 stehen die
    E-Mail-Regeln in einer eigenen Datei, und die ist die genauere Auskunft.
    """
    from falzmarke import regeln as regelsatz
    return {r["lint"] for r in regelsatz.alle()
            if r.get("lint") and r.get("_datei") == "email.yaml"}


def test_die_regelmenge_ist_nicht_leer():
    """Sonst wäre die Parametrisierung unten still leer und damit grün."""
    assert len(_regeln_der_regeldatei()) >= 7, sorted(_regeln_der_regeldatei())


@pytest.mark.parametrize("regel", sorted(_regeln_der_regeldatei()))
def test_zu_jeder_email_regel_gibt_es_einen_ausloeser(regel, tmp_path):
    bericht = _loese_aus(regel, tmp_path)
    assert regel in regeln(bericht), \
        f"{regel} wurde nicht gemeldet, gemeldet wurde: {sorted(regeln(bericht))}"


def test_der_gueltige_fall_loest_keine_einzige_davon_aus(tmp_path):
    """Die Gegenrichtung. Ohne sie könnte jeder Auslöser oben auch ein Linter
    sein, der bei jeder Datei alles meldet."""
    bericht = linte(tmp_path, MAIL)
    assert regeln(bericht) & _regeln_der_regeldatei() == set(), bericht.als_text("nachricht.md")
