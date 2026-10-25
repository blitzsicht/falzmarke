"""Der Abschnitt `email.stil:` im Profil (ADR 0053).

Das Feld ist geteilt, und die Grenze ist die Zusage: `person:` und `floskeln:`
prüft `lint` am Text und meldet als **Warnung**; `hinweise:` prüft es nur auf
**Form**. Den Inhalt der Hinweise liest das Modell, das formuliert — falzmarke
überträgt die Vorgabe, es erzwingt sie nicht.

## Was hier mehr trägt als die Richtung

Drei Gegenrichtungen, ohne die die Tests unten grün wären, ohne etwas zu zeigen:

* **Der Datenvertrag.** Fehlt `stil` in `PROFIL_EMAIL_FELDER`, lehnt
  `_melde_unbekannte` das Feld als Tippfehler ab — das Profil erzeugt einen
  Befund, statt zu wirken. `test_ohne_den_eintrag_gilt_das_feld_als_tippfehler`
  nimmt den Eintrag weg und verlangt genau diesen Befund.
* **Der Auszug.** In einem wortgetreuen Auszug steht fremder Wortlaut. Dass
  dort „wir" oder „zeitnah" steht, sagt über den Stil des Absenders nichts.
* **Die Stufe.** Beide Textregeln sind Warnung, nie Fehler. Die Erwartung steht
  hier wörtlich und wird nicht aus derselben Datei gelesen, die sie festlegt.
"""

from __future__ import annotations

import yaml
import pytest

from falzmarke import cli as falzmarke
from falzmarke import lint as lint_modul
from falzmarke import regeln as regelsatz
from conftest import REPO, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

KOPF = """typ: email
profil: example
an: erika.muster@example.de
betreff: Angebot Nr. 2026-0815
anrede: Sehr geehrte Frau Muster,
"""


def _profil(stil, tmp_path):
    """Das Beispielprofil, um einen Abschnitt `email.stil:` ergänzt."""
    profil = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    if stil is not None:
        profil["email"]["stil"] = stil
    ziel = tmp_path / "profile"
    ziel.mkdir(exist_ok=True)
    (ziel / "example.yaml").write_text(yaml.safe_dump(profil, allow_unicode=True),
                                       encoding="utf-8")
    return ziel


def _linte(tmp_path, stil, body: str = "Text der Nachricht.\n"):
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(f"---\n{KOPF}---\n{body}", encoding="utf-8")
    return falzmarke.linte(pfad, profil_verzeichnis=_profil(stil, tmp_path))


def _regeln(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde}


def _stufen(bericht, regel: str) -> set[str]:
    return {b.schwere for b in bericht.befunde if b.regel == regel}


# ── Der gültige Fall ────────────────────────────────────────────────────────

def test_ein_profil_ohne_stil_bleibt_wie_bisher(tmp_path):
    """Ohne diesen Fall wüsste man nur, dass die Prüfung feuert."""
    bericht = _linte(tmp_path, None)
    assert bericht.befunde == [], bericht.als_text("nachricht.md")


def test_ein_vollstaendiger_abschnitt_meldet_nichts(tmp_path):
    bericht = _linte(tmp_path, {
        "person": "ich",
        "floskeln": ["zeitnah", "kurzfristig"],
        "hinweise": ["Fristen immer als Datum, nie als Dauer"],
    }, "Ich schicke das Angebot bis Freitag.\n")
    assert bericht.befunde == [], bericht.als_text("nachricht.md")


def test_das_beispielprofil_traegt_keinen_aktiven_stil():
    """Entscheidung 4: Ein Profil, das bei jedem Lauf warnt, ist Lärm."""
    profil = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    assert "stil" not in profil["email"]


def test_das_beispielprofil_zeigt_den_abschnitt_als_kommentar():
    """Undokumentiert wäre das Feld unbenutzbar — gezeigt, aber nicht aktiv."""
    text = (PROFILE / "example.yaml").read_text(encoding="utf-8")
    assert "# stil:" in text
    assert "#   person: ich" in text


# ── Der Datenvertrag: ohne den Eintrag wirkt nichts ─────────────────────────

def test_das_feld_steht_im_datenvertrag():
    assert "stil" in lint_modul.PROFIL_EMAIL_FELDER


def test_ohne_den_eintrag_gilt_das_feld_als_tippfehler(tmp_path, monkeypatch):
    """Die Gegenprobe zum Eintrag oben.

    `_melde_unbekannte` lehnt jedes Feld ab, das der Datenvertrag nicht kennt.
    Ohne `stil` in `PROFIL_EMAIL_FELDER` erzeugte ein Profil mit `stil:` also
    einen Fehler, statt zu wirken — und niemand hätte gemerkt, warum die
    Stilprüfungen nie anschlagen.
    """
    ohne = frozenset(lint_modul.PROFIL_EMAIL_FELDER - {"stil"})
    monkeypatch.setattr(lint_modul, "PROFIL_EMAIL_FELDER", ohne)
    bericht = _linte(tmp_path, {"person": "ich"})
    assert "email.profil" in _regeln(bericht), bericht.als_text("nachricht.md")


# ── Die Form: Fehler, denn das ist der Datenvertrag ─────────────────────────

def test_stil_als_zeichenkette_ist_ein_fehler(tmp_path):
    bericht = _linte(tmp_path, "ich schreibe knapp")
    assert "email.stil" in _regeln(bericht)
    assert _stufen(bericht, "email.stil") == {lint_modul.FEHLER}


def test_eine_unbekannte_angabe_im_abschnitt_ist_ein_fehler(tmp_path):
    bericht = _linte(tmp_path, {"persona": "ich"})
    assert "email.stil" in _regeln(bericht)


@pytest.mark.parametrize("wert", ["isch", "man", "Wir alle", ""])
def test_ein_unbekannter_wert_fuer_person_ist_ein_fehler(tmp_path, wert):
    bericht = _linte(tmp_path, {"person": wert})
    assert "email.stil" in _regeln(bericht), bericht.als_text("nachricht.md")
    assert _stufen(bericht, "email.stil") == {lint_modul.FEHLER}


@pytest.mark.parametrize("wert", ["ich", "wir", "Ich", "WIR", " ich "])
def test_die_bekannten_werte_fuer_person_melden_nicht(tmp_path, wert):
    bericht = _linte(tmp_path, {"person": wert},
                     "Die Unterlagen liegen bei.\n")
    assert "email.stil" not in _regeln(bericht), bericht.als_text("nachricht.md")


@pytest.mark.parametrize("feld", ["floskeln", "hinweise"])
def test_eine_zeichenkette_statt_einer_liste_ist_ein_fehler(tmp_path, feld):
    """Ohne diesen Fall liefe `in` über die Buchstaben des Wortes."""
    bericht = _linte(tmp_path, {feld: "zeitnah"})
    assert "email.stil" in _regeln(bericht)


@pytest.mark.parametrize("feld,hoechstens", [
    ("floskeln", lint_modul.STIL_FLOSKELN_MAX),
    ("hinweise", lint_modul.STIL_HINWEISE_MAX),
])
def test_eine_zu_lange_liste_meldet(tmp_path, feld, hoechstens):
    bericht = _linte(tmp_path, {feld: [f"Wendung {n}" for n in range(hoechstens + 1)]})
    assert "email.stil" in _regeln(bericht)
    assert f"höchstens {hoechstens}" in bericht.als_text("nachricht.md")


@pytest.mark.parametrize("feld,hoechstens", [
    ("floskeln", lint_modul.STIL_FLOSKELN_MAX),
    ("hinweise", lint_modul.STIL_HINWEISE_MAX),
])
def test_eine_liste_an_der_grenze_meldet_nicht(tmp_path, feld, hoechstens):
    """Die Gegenprobe: Genau an der Grenze ist noch kein Befund."""
    bericht = _linte(tmp_path, {feld: [f"Wendung {n}" for n in range(hoechstens)]})
    assert "email.stil" not in _regeln(bericht), bericht.als_text("nachricht.md")


@pytest.mark.parametrize("feld,zeichen", [
    ("floskeln", lint_modul.STIL_FLOSKEL_ZEICHEN),
    ("hinweise", lint_modul.STIL_HINWEIS_ZEICHEN),
])
def test_ein_zu_langer_eintrag_meldet(tmp_path, feld, zeichen):
    bericht = _linte(tmp_path, {feld: ["a" * (zeichen + 1)]})
    assert "email.stil" in _regeln(bericht)


@pytest.mark.parametrize("feld", ["floskeln", "hinweise"])
@pytest.mark.parametrize("eintrag", [None, 42, "", "   ", ["verschachtelt"]])
def test_ein_eintrag_der_kein_satz_ist_meldet(tmp_path, feld, eintrag):
    bericht = _linte(tmp_path, {feld: [eintrag]})
    assert "email.stil" in _regeln(bericht), bericht.als_text("nachricht.md")


# ── Die Person am Text: Warnung, nie Fehler ─────────────────────────────────

@pytest.mark.parametrize("person,satz,gemeldet", [
    ("ich", "Wir schicken das Angebot bis Freitag.\n", True),
    ("ich", "Ich schicke das Angebot bis Freitag.\n", False),
    ("wir", "Ich melde mich wegen der Rechnung.\n", True),
    ("wir", "Wir melden uns wegen der Rechnung.\n", False),
])
def test_die_andere_person_wird_gemeldet(tmp_path, person, satz, gemeldet):
    bericht = _linte(tmp_path, {"person": person}, satz)
    assert ("email.stil_person" in _regeln(bericht)) is gemeldet, \
        bericht.als_text("nachricht.md")


@pytest.mark.parametrize("satz", [
    "Unser Angebot liegt bei.\n",
    "Mein Eindruck ist, dass die Lieferung steht.\n",
    "Die Unterlagen liegen uns vor.\n",
    "Bitte schicken Sie mir die Bestellnummer.\n",
])
def test_nur_die_subjektform_wird_geprueft(tmp_path, satz):
    """„unser Angebot" schreibt auch ein Einzelunternehmer.

    Eine Warnung, die bei gültigem Text anschlägt, kostet Vertrauen in alle
    anderen — die Lehre aus der Telefonprüfung (#133).
    """
    bericht = _linte(tmp_path, {"person": "ich"}, satz)
    assert "email.stil_person" not in _regeln(bericht), bericht.als_text("nachricht.md")


def test_die_meldung_nennt_das_gefundene_wort(tmp_path):
    bericht = _linte(tmp_path, {"person": "ich"}, "Wir schicken das Angebot.\n")
    text = bericht.als_text("nachricht.md")
    assert "stil.person: ich" in text and "wir" in text


def test_die_person_ist_warnung_nie_fehler(tmp_path):
    bericht = _linte(tmp_path, {"person": "ich"}, "Wir schicken das Angebot.\n")
    assert _stufen(bericht, "email.stil_person") == {lint_modul.WARNUNG}


# ── Die eigene Floskelliste ─────────────────────────────────────────────────

def test_eine_eigene_floskel_wird_gemeldet(tmp_path):
    bericht = _linte(tmp_path, {"floskeln": ["zeitnah"]},
                     "Ich melde mich zeitnah mit dem Angebot.\n")
    assert "email.stil_floskel" in _regeln(bericht), bericht.als_text("nachricht.md")


def test_die_eigene_floskel_ist_warnung_nie_fehler(tmp_path):
    bericht = _linte(tmp_path, {"floskeln": ["zeitnah"]},
                     "Ich melde mich zeitnah.\n")
    assert _stufen(bericht, "email.stil_floskel") == {lint_modul.WARNUNG}


def test_die_meldung_nennt_die_wendung(tmp_path):
    bericht = _linte(tmp_path, {"floskeln": ["kurzfristig"]},
                     "Das ist kurzfristig machbar.\n")
    assert "kurzfristig" in bericht.als_text("nachricht.md")


def test_ein_teilwort_wird_nicht_gemeldet(tmp_path):
    """Als Wort gesucht, nicht als Teilkette — sonst trifft `rat` in „Vorrat"."""
    bericht = _linte(tmp_path, {"floskeln": ["rat"]},
                     "Der Vorrat reicht bis Oktober.\n")
    assert "email.stil_floskel" not in _regeln(bericht), bericht.als_text("nachricht.md")


def test_eine_wendung_mit_klammer_bringt_den_lauf_nicht_um(tmp_path):
    """Aus dem Profil kommt eine Zeichenkette, kein Ausdruck.

    Ohne `re.escape` wäre `(` ein unvollständiger Ausdruck — der Lauf stürbe an
    einem `re.error`, statt eine Meldung zu schreiben.
    """
    bericht = _linte(tmp_path, {"floskeln": ["bzw. (sofern"]},
                     "Die Lieferung kommt am Freitag.\n")
    assert "email.stil_floskel" not in _regeln(bericht)


def test_die_leere_liste_meldet_nichts(tmp_path):
    bericht = _linte(tmp_path, {"floskeln": []}, "Die Lieferung kommt.\n")
    assert bericht.befunde == [], bericht.als_text("nachricht.md")


# ── Der Auszug: fremder Wortlaut zählt nicht ────────────────────────────────

def test_im_zaun_bleibt_die_floskel_stumm(tmp_path):
    bericht = _linte(tmp_path, {"floskeln": ["zeitnah"]},
                     "Der Kunde schrieb:\n\n```\nBitte zeitnah liefern.\n```\n")
    assert "email.stil_floskel" not in _regeln(bericht), bericht.als_text("nachricht.md")


def test_im_zaun_bleibt_die_person_stumm(tmp_path):
    bericht = _linte(tmp_path, {"person": "ich"},
                     "Der Kunde schrieb:\n\n```\nWir haben nichts erhalten.\n```\n")
    assert "email.stil_person" not in _regeln(bericht), bericht.als_text("nachricht.md")


def test_im_inline_auszug_bleibt_die_person_stumm(tmp_path):
    bericht = _linte(tmp_path, {"person": "ich"},
                     "Im Protokoll steht `wir haben nichts erhalten`.\n")
    assert "email.stil_person" not in _regeln(bericht), bericht.als_text("nachricht.md")


def test_derselbe_wortlaut_ausserhalb_des_auszugs_meldet(tmp_path):
    """Die Gegenprobe zu den drei Fällen oben.

    Ohne sie könnte `_ohne_auszuege` den ganzen Text verschlucken, und alle
    drei blieben grün, ohne dass die Prüfung noch etwas täte.
    """
    bericht = _linte(tmp_path, {"person": "ich"}, "Wir haben nichts erhalten.\n")
    assert "email.stil_person" in _regeln(bericht), bericht.als_text("nachricht.md")


def test_der_auszug_schluckt_den_rest_der_nachricht_nicht(tmp_path):
    """Ein Zaun mitten im Text — danach wird weiter geprüft."""
    bericht = _linte(tmp_path, {"floskeln": ["zeitnah"]},
                     "Der Kunde schrieb:\n\n```\nBitte liefern.\n```\n\n"
                     "Ich melde mich zeitnah.\n")
    assert "email.stil_floskel" in _regeln(bericht), bericht.als_text("nachricht.md")


# ── `hinweise:` wird nicht inhaltlich geprüft ───────────────────────────────

def test_hinweise_werden_inhaltlich_nicht_geprueft(tmp_path):
    """ADR 0053, Entscheidung 1.

    Der Text verstößt gegen den Hinweis so deutlich, wie es geht. Es bleibt
    still: falzmarke versteht keinen Satz, und eine Prüfung, die das Gegenteil
    behauptete, wäre eine Zusage ohne Deckung.
    """
    bericht = _linte(tmp_path, {"hinweise": ["Fristen immer als Datum, nie als Dauer"]},
                     "Bitte zahlen Sie innerhalb von 14 Tagen.\n")
    assert bericht.befunde == [], bericht.als_text("nachricht.md")


def test_die_hinweise_tauchen_nicht_in_einer_meldung_auf(tmp_path):
    """Sonst stünde Profiltext in einem Befund, der ihn nicht erklärt."""
    bericht = _linte(tmp_path, {
        "person": "ich",
        "hinweise": ["Preise ohne Begründung der eigenen Kalkulation"],
    }, "Wir schicken das Angebot.\n")
    assert "Kalkulation" not in bericht.als_text("nachricht.md")


# ── Die Stufen stehen in der Regeldatei ─────────────────────────────────────
#
# Die Erwartung steht hier wörtlich. Sie aus derselben Datei zu lesen, die sie
# festlegt, hieße den Sollwert gegen sich selbst prüfen — eine Änderung an der
# Stufe wäre dann grün.

@pytest.mark.parametrize("regel,deckel", [
    ("email.stil", regelsatz.DECKEL_FEHLER),
    ("email.stil_person", regelsatz.DECKEL_WARNUNG),
    ("email.stil_floskel", regelsatz.DECKEL_WARNUNG),
])
def test_die_regeldatei_kennt_die_stufe(regel, deckel):
    assert regelsatz.deckel_von_lint(regel) == deckel


@pytest.mark.parametrize("regel,ebene", [
    ("email.stil", "werkzeug"),
    ("email.stil_person", "praxis"),
    ("email.stil_floskel", "praxis"),
])
def test_die_regeldatei_kennt_die_ebene(regel, ebene):
    assert regelsatz.ebene_von_lint(regel) == ebene


@pytest.mark.parametrize("regel", ["email.stil", "email.stil_person", "email.stil_floskel"])
def test_keine_der_regeln_behauptet_eine_quelle(regel):
    """Werkzeugverhalten, keine Normaussage — `quellen: []` sagt das."""
    eintrag = regelsatz.fuer_lint(regel)
    assert eintrag is not None, regel
    assert eintrag["herkunft"] == "werkzeug"
    assert eintrag.get("quellen") in (None, [], ())


# ── Gegen den stillen Ausfall ───────────────────────────────────────────────

def test_die_formpruefung_wird_wirklich_aufgerufen(tmp_path, monkeypatch):
    """Ohne diesen Fall könnte der Aufruf fehlen, und alles oben wäre grün.

    Die Form-Tests weiter oben laufen über `cli.linte`; fiele der Aufruf in
    `pruefe_email_profil` weg, fehlten dort nur Befunde — und ein fehlender
    Befund sieht aus wie ein sauberes Profil.
    """
    gesehen = []
    echt = lint_modul.pruefe_email_stil

    def merken(abschnitt, bericht):
        gesehen.append(sorted(abschnitt.keys()))
        return echt(abschnitt, bericht)

    monkeypatch.setattr(lint_modul, "pruefe_email_stil", merken)
    _linte(tmp_path, {"person": "ich"})
    assert gesehen, "pruefe_email_stil wurde nicht aufgerufen"


def test_die_textpruefung_laeuft_auf_dem_entwurf(tmp_path):
    """Am Datenpfad gemessen, nicht nur an der Funktion.

    Beide Textregeln hängen am Body des Entwurfs. Dass sie dort ankommen,
    zeigen die Fälle oben — dieser hält fest, dass sie es in EINEM Lauf
    zusammen tun, wie in einer echten Nachricht.
    """
    bericht = _linte(tmp_path, {"person": "ich", "floskeln": ["zeitnah"]},
                     "Wir melden uns zeitnah.\n")
    assert {"email.stil_person", "email.stil_floskel"} <= _regeln(bericht), \
        bericht.als_text("nachricht.md")


# ── Dokumentation: ein Feld, das niemand findet, ist unbenutzbar ────────────

def test_der_datenvertrag_dokumentiert_das_feld():
    text = (SKILL / "references" / "frontmatter.md").read_text(encoding="utf-8")
    assert "email.stil" in text
    for feld in sorted(lint_modul.PROFIL_STIL_FELDER):
        assert feld in text, feld


def test_die_profildoku_nennt_das_feld():
    text = (REPO / "docs" / "profiles.md").read_text(encoding="utf-8")
    assert "email.stil" in text or "stil:" in text
    assert "0053" in text


def test_der_skill_laesst_den_abschnitt_lesen():
    """Der Inhalt von `hinweise:` wirkt nur, weil hier steht, dass er gelesen wird."""
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "email.stil" in text


def test_die_entscheidung_liegt_als_datei():
    pfad = REPO / "docs" / "entscheidungen" / "0053-email-stil-im-profil.md"
    assert pfad.exists()
    text = pfad.read_text(encoding="utf-8")
    assert "hinweise" in text
    assert "erzwingt sie nicht" in text


def test_die_entscheidung_steht_im_index():
    text = (REPO / "docs" / "entscheidungen" / "README.md").read_text(encoding="utf-8")
    assert "0053-email-stil-im-profil.md" in text


def test_die_stilreferenz_nennt_den_profilabschnitt():
    """Was das Modell vor dem Schreiben liest, muss den Abschnitt erwähnen.

    `stil.md` sagt, wie eine Geschäftsmail aufgebaut ist; `email.stil:` sagt,
    wie dieser Absender schreibt. Stünde der Verweis nicht hier, hinge die
    Wirkung des Feldes allein an `SKILL.md` — einer Stelle, die beim Umschreiben
    einer Mail nicht noch einmal gelesen wird.
    """
    text = (SKILL / "references" / "stil.md").read_text(encoding="utf-8")
    assert "email.stil" in text
    assert "0053" in text
