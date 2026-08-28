"""Der Fassungsschalter des Dialekts.

Die eine Zusage, die diese Erweiterung trägt: **Ein Brief ohne `dialekt:`
rendert unverändert.** Alles andere darf sich ändern, das nicht — deshalb steht
hier zu jedem Fall die Gegenrichtung daneben. Ein Test, der nur zeigt, dass
1.1 etwas kann, belegt nicht, dass 1.0 es weiterhin nicht kann.
"""

from __future__ import annotations

import hashlib

import pytest

from falzmarke import cli as falzmarke
from falzmarke import markdown as markdown_modul
from falzmarke.markdown import MarkdownFehler, konvertiere, lies
from conftest import BEISPIELE, BEISPIELE_10, BEISPIELE_11, EMAIL_BEISPIELE, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

KOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""


def linte(tmp_path, kopf: str = KOPF, body: str = "Text des Briefes.\n"):
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{kopf}---\n{body}", encoding="utf-8")
    return falzmarke.linte(pfad, profil_verzeichnis=PROFILE)


def regeln(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde}


# ── Das Feld ────────────────────────────────────────────────────────────────

def test_fehlendes_feld_ist_fassung_10():
    """Der Kern der Zusage: Wer das Feld nicht kennt, bekommt den alten Brief."""
    assert markdown_modul.pruefe_fassung(None) == "1.0"
    assert markdown_modul.pruefe_fassung("") == "1.0"


@pytest.mark.parametrize("wert", ["1.0", "1.1", " 1.1 "])
def test_bekannte_fassungen_werden_angenommen(wert):
    assert markdown_modul.pruefe_fassung(wert) in markdown_modul.FASSUNGEN


@pytest.mark.parametrize("wert", ["1.2", "2.0", "1", "elf", "1,1"])
def test_unbekannte_fassung_bricht_ab_und_nennt_die_bekannten(wert):
    """Ein Tippfehler darf nicht still zur alten Fassung führen: Der Brief sähe
    anders aus als geschrieben, und die Meldung käme nie."""
    with pytest.raises(MarkdownFehler) as fehler:
        markdown_modul.pruefe_fassung(wert)
    for fassung in markdown_modul.FASSUNGEN:
        assert fassung in str(fehler.value)


def test_linter_meldet_unbekannte_fassung(tmp_path):
    bericht = linte(tmp_path, KOPF + 'dialekt: "1.7"\n')
    assert "dialekt" in regeln(bericht)
    assert bericht.anzahl_fehler >= 1


def test_linter_schweigt_bei_bekannter_fassung(tmp_path):
    """Die Gegenrichtung. Ohne sie wüsste man nur, dass die Regel feuert."""
    bericht = linte(tmp_path, KOPF + 'dialekt: "1.1"\n')
    assert "dialekt" not in regeln(bericht)


def test_linter_schweigt_ganz_ohne_feld(tmp_path):
    bericht = linte(tmp_path)
    assert "dialekt" not in regeln(bericht)


def test_dialekt_ist_kein_unbekanntes_feld(tmp_path):
    """Ohne Eintrag in der Feldliste meldete der Linter einen Tippfehler."""
    bericht = linte(tmp_path, KOPF + 'dialekt: "1.1"\n')
    assert "frontmatter" not in regeln(bericht)


# ── Die Zusage: 1.0 bleibt, wie es war ──────────────────────────────────────

def _abdruck(pfad) -> str:
    """Der erzeugte Satz eines Beispiels, als Prüfsumme."""
    kopf, body, versatz = falzmarke.lies_brief(pfad)
    return hashlib.sha256(
        konvertiere(body, versatz, dialekt=kopf.get("dialekt")).encode()).hexdigest()


@pytest.mark.parametrize("pfad", BEISPIELE_10, ids=[p.stem for p in BEISPIELE_10])
def test_beispiel_ohne_feld_setzt_wie_in_fassung_10(pfad):
    """Ein Beispiel ohne `dialekt:` muss dasselbe ergeben wie 1.0 ausdrücklich.

    Der Test misst nicht gegen eine eingefrorene Zahl, sondern gegen die
    angeforderte Fassung. Eine eingefrorene Zahl wäre beim ersten gewollten
    Satzwechsel nur noch Arbeit.
    """
    kopf, body, versatz = falzmarke.lies_brief(pfad)
    assert kopf.get("dialekt") is None
    assert _abdruck(pfad) == hashlib.sha256(
        konvertiere(body, versatz, dialekt="1.0").encode()).hexdigest()


@pytest.mark.parametrize("pfad", BEISPIELE_11, ids=[p.stem for p in BEISPIELE_11])
def test_beispiel_mit_11_braucht_das_feld_wirklich(pfad):
    """Die Gegenrichtung: Ohne das Feld muss dasselbe Beispiel abbrechen.

    Ohne diese Hälfte wüsste man nicht, ob `dialekt: 1.1` überhaupt etwas tut —
    ein Beispiel, das auch als 1.0 durchginge, belegte den Schalter nicht.
    """
    kopf, body, versatz = falzmarke.lies_brief(pfad)
    assert kopf.get("dialekt") == "1.1"
    konvertiere(body, versatz, dialekt="1.1")          # geht
    with pytest.raises(MarkdownFehler):
        konvertiere(body, versatz, dialekt="1.0")      # geht nicht


def test_die_beispielauswahl_ist_weder_leer_noch_vollstaendig():
    """Gegenprobe zu beiden Listen oben.

    `BEISPIELE_10` steuert auch die Emitter-Tests der E-Mail. Wäre die Liste
    versehentlich leer, liefen die über die leere Menge und wären immer grün;
    wäre `BEISPIELE_11` leer, prüfte der Test darüber nichts.
    """
    assert len(BEISPIELE_10) >= 10, "zu wenige 1.0-Beispiele — Emitter-Tests messen kaum etwas"
    assert BEISPIELE_11, "kein Beispiel in Fassung 1.1 — dann ist 1.1 unbelegt"
    assert len(BEISPIELE_10) + len(BEISPIELE_11) == len(BEISPIELE)
    assert len(EMAIL_BEISPIELE) >= 3


# ── Der Rückweg für Warnungen ───────────────────────────────────────────────

def test_hinweise_landen_als_warnung_im_linterbericht(tmp_path):
    """Die Prüfung selbst kann nur abbrechen oder durchlassen. Damit eine
    Meldung überhaupt jemanden erreicht, muss der Linter sie zeigen."""
    bericht = linte(tmp_path, body="2. Mahnung zur Rechnung 4711\n")
    warnungen = [b for b in bericht.befunde if b.regel == "markdown"]
    assert warnungen, f"keine Markdown-Warnung, Befunde: {bericht.befunde}"
    assert bericht.anzahl_fehler == 0, "die Zeile wird gesetzt, nicht abgelehnt"


def test_ohne_auffaelligkeit_kommt_keine_warnung(tmp_path):
    """Die Gegenrichtung: Der Rückweg darf nicht bei jedem Brief anschlagen."""
    bericht = linte(tmp_path, body="Ein gewöhnlicher Absatz.\n")
    assert not [b for b in bericht.befunde if b.regel == "markdown"]


def test_lies_nimmt_die_hinweisliste_entgegen():
    hinweise: list = []
    lies("2. Mahnung\n", hinweise=hinweise)
    assert len(hinweise) == 1
    assert hinweise[0].zeile == 1


def test_zeilenversatz_gilt_auch_fuer_hinweise():
    """Eine Meldung mit falscher Zeile schickt den Schreibenden ins Leere."""
    hinweise: list = []
    lies("2. Mahnung\n", zeilenversatz=18, hinweise=hinweise)
    assert hinweise[0].zeile == 19


# ── Die Grenze zur E-Mail ───────────────────────────────────────────────────
#
# `baum.NUR_BRIEF` nimmt Knoten von der Vollständigkeitsprüfung der
# E-Mail-Emitter aus. Das ist nur zulässig, solange die Grenze bewacht ist —
# hier steht der Nachweis, und zwar in beide Richtungen: Der Emitter muss
# abbrechen, UND der Weg dorthin muss versperrt sein. Fehlt eine der beiden
# Richtungen, ist die Ausnahme genau die Lücke, gegen die der Wächter gebaut
# wurde: ein Absatz, der aus einer E-Mail verschwindet, ohne dass etwas rot wird.

from falzmarke import baum, emit_html, emit_text  # noqa: E402

#: Je Knoten aus `baum.NUR_BRIEF` die Markdown-Syntax, die ihn erzeugt.
NUR_BRIEF_PROBEN = {
    baum.Ueberschrift: ("# Ein Abschnitt\n", baum.Ueberschrift(1, (baum.Text("x"),))),
    baum.Zitat: ("> Ein Zitat.\n", baum.Zitat((baum.Absatz((baum.Text("x"),)),))),
    baum.Wortlaut: ("```\nein Auszug\n```\n", baum.Wortlaut("x", block=True)),
}


def test_jeder_nur_brief_knoten_hat_eine_probe():
    """Sonst liefe der Nachweis unten über die leere Menge."""
    fehlend = [k.__name__ for k in baum.NUR_BRIEF if k not in NUR_BRIEF_PROBEN]
    assert not fehlend, f"ohne Probe in dieser Datei: {fehlend}"
    assert baum.NUR_BRIEF, "NUR_BRIEF ist leer — dann gehört diese Prüfung weg"


@pytest.mark.parametrize("klasse", list(NUR_BRIEF_PROBEN),
                         ids=[k.__name__ for k in NUR_BRIEF_PROBEN])
def test_die_email_emitter_uebergehen_den_knoten_nicht_still(klasse):
    """Richtung 1: Käme er doch an, bräche es — er verschwindet nicht."""
    _, knoten = NUR_BRIEF_PROBEN[klasse]
    for modul, name in ((emit_html, "HTML-Emitter"), (emit_text, "Text-Emitter")):
        with pytest.raises(TypeError, match=name):
            modul._block(knoten)


@pytest.mark.parametrize("klasse", list(NUR_BRIEF_PROBEN),
                         ids=[k.__name__ for k in NUR_BRIEF_PROBEN])
def test_der_weg_in_die_email_ist_versperrt(klasse):
    """Richtung 2: Er kommt gar nicht erst an — mit Zeile, Grund und Ausweg.

    Ohne diese Hälfte wäre die Ausnahme nur die Zusage, dass der Absturz
    ordentlich aussieht. Der Punkt ist, dass es keinen Absturz gibt.
    """
    quelle, _ = NUR_BRIEF_PROBEN[klasse]
    for fassung in markdown_modul.FASSUNGEN:
        with pytest.raises(MarkdownFehler) as fehler:
            lies(quelle, dialekt=fassung, ziel="email")
        assert "E-Mail" in str(fehler.value)
        assert fehler.value.zeile == 1


@pytest.mark.parametrize("klasse", list(NUR_BRIEF_PROBEN),
                         ids=[k.__name__ for k in NUR_BRIEF_PROBEN])
def test_im_brief_kommt_derselbe_knoten_durch(klasse):
    """Die Gegenrichtung zur Sperre: Sie darf nicht überall greifen."""
    quelle, _ = NUR_BRIEF_PROBEN[klasse]
    bloecke = lies(quelle, dialekt="1.1", ziel="brief")
    assert any(isinstance(b, klasse) for b in bloecke), \
        f"{klasse.__name__} fehlt im Brief-Baum: {bloecke}"
