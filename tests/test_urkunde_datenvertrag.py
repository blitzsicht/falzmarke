"""Der Datenvertrag `typ: urkunde` — das Schriftstück ohne Anschriftfeld (ADR 0048).

Geprüft wird, was der Linter zur Eingabe sagt, bevor irgendetwas gesetzt wird:
welche Felder es gibt, welche es hier nicht gibt, und was an ihrer Stelle steht.
Dazu die Gegenrichtung, auf die es ankommt: Ein Brief bleibt ein Brief — er
verlangt seine Anschrift weiter unbedingt.
"""

from __future__ import annotations

import pytest
import yaml

from falzmarke import cli, lint
from conftest import REPO, URKUNDE_BEISPIELE

GUELTIG = """profil: example
typ: urkunde
dialekt: "1.2"
titel: Vereinbarung über eine Leihe
parteien:
  - name: Beispiel GmbH
    anschrift:
      - Musterweg 12
      - 93055 Regensburg
    zusatz: (im Folgenden „Verleiherin“)
  - name: Max Muster
    anschrift: Beispielgasse 3, 93047 Regensburg
ort_datum: Regensburg, den ______________
unterschriften:
  - name: Erika Muster
    rolle: Beispiel GmbH
  - name: Max Muster
anlagen:
  - Übergabeprotokoll
seiten_max: 1
"""


def _befunde(kopf_text: str) -> list[tuple[str, str, str]]:
    bericht = lint.Bericht()
    lint.pruefe_frontmatter(yaml.safe_load(kopf_text), "\n" + kopf_text, bericht)
    return [(b.regel, b.schwere, b.meldung) for b in bericht.befunde]


def _regeln(kopf_text: str) -> list[str]:
    return [regel for regel, schwere, _ in _befunde(kopf_text) if schwere == lint.FEHLER]


def _mit(zeile: str) -> str:
    return GUELTIG + zeile + "\n"


def _ohne(feld: str) -> str:
    """GUELTIG ohne das Feld der obersten Ebene — samt seiner eingerückten Zeilen."""
    aus, weg = [], False
    for zeile in GUELTIG.splitlines():
        if zeile.startswith(f"{feld}:"):
            weg = True
            continue
        if weg and zeile.startswith((" ", "-")):
            continue
        weg = False
        aus.append(zeile)
    assert len(aus) < len(GUELTIG.splitlines()), f"`{feld}:` steht nicht in GUELTIG"
    return "\n".join(aus) + "\n"


# ── Kontrollprobe ───────────────────────────────────────────────────────────

def test_die_gueltige_urkunde_ist_gueltig():
    """Ohne diese Probe wäre jeder Fehler unten auch ein Fehler der Vorlage."""
    assert _befunde(GUELTIG) == []


def test_urkunde_ist_ein_typ():
    assert "urkunde" in lint.TYPEN


@pytest.mark.parametrize("beispiel", URKUNDE_BEISPIELE, ids=lambda p: p.stem)
def test_beispiele_bestehen_den_linter(beispiel):
    bericht = cli.linte(beispiel)
    assert bericht.ok, bericht.als_text(beispiel.name)


def test_es_gibt_beispiele():
    """Ein leerer Glob ließe jeden parametrisierten Test oben still entfallen."""
    assert len(URKUNDE_BEISPIELE) >= 2, URKUNDE_BEISPIELE


# ── Unbekannte Felder werden weiter abgelehnt ───────────────────────────────

def test_unbekanntes_feld_ist_ein_fehler():
    befunde = _befunde(_mit("farbe: rot"))
    assert [(r, s) for r, s, _ in befunde] == [("frontmatter", lint.FEHLER)]
    assert "`farbe` ist kein Feld des Datenvertrags" in befunde[0][2]


def test_tippfehler_bekommt_einen_vorschlag():
    bericht = lint.Bericht()
    text = _mit("seitenmax: 2")
    lint.pruefe_frontmatter(yaml.safe_load(text), "\n" + text, bericht)
    assert "seiten_max" in bericht.befunde[0].korrektur


def test_unbekanntes_feld_in_einer_partei_ist_ein_fehler():
    text = GUELTIG.replace("    zusatz: (im Folgenden „Verleiherin“)",
                           "    rolle: Verleiherin")
    assert text != GUELTIG
    assert _regeln(text) == ["urkunde.parteien"]


def test_unbekanntes_feld_in_einer_unterschrift_ist_ein_fehler():
    text = GUELTIG.replace("    rolle: Beispiel GmbH", "    zusatz: Beispiel GmbH")
    assert text != GUELTIG
    assert _regeln(text) == ["urkunde.unterschriften"]


def test_brief_lehnt_unbekannte_felder_weiter_ab():
    """Die Abnahme verlangt es ausdrücklich: Der neue Typ weicht den alten nicht auf."""
    brief = ("profil: example\nempfaenger:\n  - Muster GmbH\ndatum: 2026-10-12\n"
             "betreff: Probe\nfarbe: rot\n")
    assert ("frontmatter", lint.FEHLER) in [(r, s) for r, s, _ in _befunde(brief)]


# ── Felder des Briefes bedeuten hier nichts ─────────────────────────────────

@pytest.mark.parametrize("feld,ersatz", [
    ("betreff: Leihe", "titel"),
    ("unterzeichner: Erika Muster", "unterschriften"),
    ("datum: 2026-10-12", "ort_datum"),
    ("empfaenger: Max Muster", "parteien"),
])
def test_brieffeld_nennt_seinen_ersatz(feld, ersatz):
    bericht = lint.Bericht()
    text = _mit(feld)
    lint.pruefe_frontmatter(yaml.safe_load(text), "\n" + text, bericht)
    assert [(b.regel, b.schwere) for b in bericht.befunde] == [("typ", lint.FEHLER)]
    assert "in einer Urkunde nicht" in bericht.befunde[0].meldung
    assert f"`{ersatz}:`" in bericht.befunde[0].korrektur


@pytest.mark.parametrize("feld", [
    "anrede: Sehr geehrte Damen und Herren,", "gruss: Mit freundlichen Grüßen",
    "form: A", "signatur: keine", "an: muster@example.de", "betreff_kurz: Leihe",
])
def test_brieffeld_ohne_ersatz_wird_abgelehnt(feld):
    befunde = _befunde(_mit(feld))
    assert [(r, s) for r, s, _ in befunde] == [("typ", lint.FEHLER)]


def test_ein_ausgeschlossenes_feld_wird_einmal_gemeldet_nicht_zweimal():
    """Ohne den Filter stünde `betreff` zusätzlich als „kein Feld des Datenvertrags" da."""
    assert _regeln(_mit("betreff: Leihe")) == ["typ"]


def test_brief_mit_urkundenfeld_ist_ein_fehler():
    brief = ("profil: example\nempfaenger:\n  - Muster GmbH\ndatum: 2026-10-12\n"
             "betreff: Probe\ntitel: Vereinbarung\n")
    assert "frontmatter" in _regeln(brief)


# ── Pflichtfelder ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("feld", lint.URKUNDE_PFLICHTFELDER)
def test_pflichtfeld_fehlt(feld):
    assert feld in _regeln(_ohne(feld))


@pytest.mark.parametrize("feld", ["parteien", "ort_datum", "unterschriften", "anlagen",
                                  "seiten_max", "dialekt"])
def test_alles_andere_ist_freiwillig(feld):
    assert _regeln(_ohne(feld)) == []


def test_brief_ohne_empfaenger_nennt_den_anderen_typ():
    """Die Fundstelle: Wer ein Papier ohne Empfänger will, landet genau hier."""
    bericht = lint.Bericht()
    brief = "profil: example\ndatum: 2026-10-12\nbetreff: Probe\n"
    lint.pruefe_frontmatter(yaml.safe_load(brief), "\n" + brief, bericht)
    treffer = [b for b in bericht.befunde if b.regel == "empfaenger"]
    assert treffer and "typ: urkunde" in treffer[0].korrektur


def test_rechnung_ohne_empfaenger_nennt_ihn_nicht():
    """Eine Rechnung ohne Empfänger ist keine Urkunde — der Rat wäre dort falsch."""
    bericht = lint.Bericht()
    rechnung = "profil: example\ntyp: rechnung\ndatum: 2026-10-12\n"
    lint.pruefe_frontmatter(yaml.safe_load(rechnung), "\n" + rechnung, bericht)
    treffer = [b for b in bericht.befunde if b.regel == "empfaenger"]
    assert treffer and "urkunde" not in treffer[0].korrektur


# ── Die einzelnen Felder ────────────────────────────────────────────────────

def test_drei_parteien_sind_eine_zu_viel():
    text = GUELTIG.replace("ort_datum:", "  - name: Dritte Person\nort_datum:")
    assert _regeln(text) == ["urkunde.parteien"]


def test_partei_ohne_namen():
    text = GUELTIG.replace("  - name: Max Muster\n    anschrift: Beispielgasse 3",
                           "  - anschrift: Beispielgasse 3")
    assert text != GUELTIG
    assert _regeln(text) == ["urkunde.parteien"]


def test_anschrift_als_abbildung_ist_die_falsche_form():
    """`empfaenger_anschrift` der Rechnung ist eine Abbildung — hier nicht."""
    text = GUELTIG.replace("    anschrift: Beispielgasse 3, 93047 Regensburg",
                           "    anschrift:\n      strasse: Beispielgasse 3")
    assert text != GUELTIG
    assert _regeln(text) == ["urkunde.parteien"]


def test_drei_unterschriften_sind_eine_zu_viel():
    text = GUELTIG.replace("anlagen:", "  - name: Dritte Person\nanlagen:")
    assert _regeln(text) == ["urkunde.unterschriften"]


def test_unterschrift_ohne_namen():
    text = GUELTIG.replace("  - name: Max Muster\nanlagen:", "  - rolle: Entleiher\nanlagen:")
    assert text != GUELTIG
    assert _regeln(text) == ["urkunde.unterschriften"]


@pytest.mark.parametrize("wert", ["0", "-1", "zwei", "1.5", "true"])
def test_seiten_max_ist_eine_ganze_zahl_ab_eins(wert):
    text = GUELTIG.replace("seiten_max: 1", f"seiten_max: {wert}")
    assert _regeln(text) == ["urkunde.seiten_max"]


@pytest.mark.parametrize("wert", ["1", "2", "12"])
def test_seiten_max_gueltig(wert):
    assert _regeln(GUELTIG.replace("seiten_max: 1", f"seiten_max: {wert}")) == []


def test_ort_datum_als_blosses_datum_liest_yaml_als_datum():
    """`ort_datum: 2026-10-12` ist für YAML ein Datum und kein Text — das fällt auf."""
    text = GUELTIG.replace("ort_datum: Regensburg, den ______________", "ort_datum: 2026-10-12")
    assert _regeln(text) == ["urkunde.ort_datum"]


@pytest.mark.parametrize("zeile", [
    "Regensburg, den ____,__",       # die zwei Unterstriche lehnen am Komma
    "Regensburg, den___________",    # klebt am Wort
])
def test_ort_datum_mit_kette_die_kein_feld_wird(zeile):
    text = GUELTIG.replace("Regensburg, den ______________", zeile)
    assert text != GUELTIG
    assert _regeln(text) == ["urkunde.ort_datum"]


def test_titel_mit_doppelpunkt_ohne_anfuehrungszeichen_ist_kein_text():
    text = GUELTIG.replace("titel: Vereinbarung über eine Leihe", "titel:\n  Empfang: Gerät")
    assert _regeln(text) == ["urkunde.titel"]


def test_ueberlanger_titel():
    text = GUELTIG.replace("titel: Vereinbarung über eine Leihe",
                           "titel: " + "Vereinbarung " * 20)
    assert _regeln(text) == ["urkunde.titel"]


# ── Wörter, unter denen jemand den Typ sucht ────────────────────────────────

@pytest.mark.parametrize("wort", ["vertrag", "vereinbarung", "Erklärung", "nachweis", "vollmacht"])
def test_verwandtes_wort_fuehrt_zum_typ(wort):
    bericht = lint.Bericht()
    text = GUELTIG.replace("typ: urkunde", f"typ: {wort}")
    lint.pruefe_frontmatter(yaml.safe_load(text), "\n" + text, bericht)
    assert [(b.regel, b.schwere) for b in bericht.befunde] == [("typ", lint.FEHLER)]
    assert "typ: urkunde" in bericht.befunde[0].korrektur


def test_fremdes_wort_bekommt_die_liste():
    bericht = lint.Bericht()
    text = "profil: example\ntyp: fax\n"
    lint.pruefe_frontmatter(yaml.safe_load(text), "\n" + text, bericht)
    assert "möglich sind" in bericht.befunde[0].korrektur
    assert "urkunde" in bericht.befunde[0].korrektur


# ── Der Text: die erste Ebene ist der Titel ─────────────────────────────────

def _body(text: str) -> list[tuple[int, str]]:
    bericht = lint.Bericht()
    lint.pruefe_urkunde_body(text, 10, bericht)
    return [(b.zeile, b.regel) for b in bericht.befunde]


def test_ueberschrift_erster_ebene_im_text_ist_ein_fehler():
    assert _body("Vorwort.\n\n# Abschnitt\n\nText.\n") == [(13, "urkunde.ueberschrift")]


def test_ueberschrift_zweiter_ebene_ist_der_normalfall():
    assert _body("## 1. Gegenstand\n\nText.\n\n### Einzelheiten\n") == []


def test_setext_ueberschrift_wird_auch_gefunden():
    assert _body("Abschnitt\n=========\n\nText.\n") == [(12, "urkunde.ueberschrift")]


def test_raute_im_auszug_ist_keine_ueberschrift():
    assert _body("```\n# nur ein Kommentar\n```\n\n## Abschnitt\n") == []


def test_linte_meldet_die_ueberschrift_an_der_datei(tmp_path):
    """Der Weg über `cli.linte` — sonst wäre die Prüfung gebaut und nie gerufen."""
    datei = tmp_path / "u.md"
    datei.write_text("---\n" + GUELTIG + "---\n\n# Falsche Ebene\n\nText.\n", encoding="utf-8")
    bericht = cli.linte(datei)
    assert "urkunde.ueberschrift" in [b.regel for b in bericht.befunde]


# ── Jede Regel steht im Katalog ─────────────────────────────────────────────

def test_jede_urkundenregel_ist_werkzeugregel_und_darf_fehler_sein():
    from falzmarke import regeln

    eigene = [r for r in regeln.alle() if "urkunde" in r["id"]]
    assert len(eigene) >= 12, [r["id"] for r in eigene]
    for regel in eigene:
        assert regel["herkunft"] == regeln.WERKZEUG, regel["id"]
        assert regel["ebene"] == regeln.EBENE_WERKZEUG, regel["id"]
        assert regel["quellen"] == [], regel["id"]
        assert regeln.deckel(regel) == regeln.DECKEL_FEHLER, regel["id"]


def test_die_doku_nennt_jedes_feld():
    """`references/frontmatter.md` ist der Vertrag, den ein Agent liest."""
    text = (REPO / "skill" / "references" / "frontmatter.md").read_text(encoding="utf-8")
    abschnitt = text.split("## Urkunde", 1)
    assert len(abschnitt) == 2, "Abschnitt „## Urkunde“ fehlt in frontmatter.md"
    for feld in sorted(lint.URKUNDE_FRONTMATTER_FELDER | lint.PARTEI_FELDER
                       | lint.UNTERSCHRIFT_FELDER):
        assert f"`{feld}`" in abschnitt[1] or f"{feld}:" in abschnitt[1], feld
