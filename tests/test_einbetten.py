"""Eine Datei IM PDF statt dahinter — PDF/A-3b (#114).

`anlagen_dateien:` hängt Seiten hinten an: Das PDF wird länger, ein Mensch
blättert hin. `eingebettet:` legt eine Datei **in** das Dokument; sichtbar wird
nichts, lesbar ist sie für ein Programm. Das ist der Weg, auf dem später eine
Rechnung im XML-Format mitreist (#111) — ohne ihn gibt es kein ZUGFeRD.

## Die Stufe wird verlangt, nicht umgestellt

Wer nichts einbettet, bekommt weiter PDF/A-2b. Das ist der Kern von ADR 0033,
und beide Richtungen stehen hier als eigene Prüfung: Eine Umstellung, die
stillschweigend passiert, wäre eine Änderung an jeder Datei, die jemand ins
Archiv legt.

## Was Typst selbst erzwingt

Gemessen am 29.08.2026 mit typst-py 0.15: `pdf.attach` bricht ohne `mime-type`
und ohne `description` ab, und es kennt genau vier Beziehungswerte. Der
Datenvertrag wiederholt das trotzdem — `lint` soll den Fehler mit Feld und
Zeile nennen, statt einen Compilerfehler durchzureichen.
"""

from __future__ import annotations


import pytest

import pypdf

from conftest import REPO, SKILL
from falzmarke import cli, geometrie, lint

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

BRIEF = """---
profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-29
betreff: Rechnung mit maschinenlesbaren Daten
{eingebettet}---
im Anhang die Rechnung, die Daten liegen ihr maschinenlesbar bei.
"""

MIT = """eingebettet:
  - datei: daten.xml
    typ: text/xml
    beschreibung: Rechnungsdaten
    beziehung: data
"""


def _brief(tmp_path, eingebettet: str = "", inhalt: str = "<?xml version=\"1.0\"?><r/>"):
    (tmp_path / "daten.xml").write_text(inhalt, encoding="utf-8")
    pfad = tmp_path / "brief.md"
    pfad.write_text(BRIEF.format(eingebettet=eingebettet), encoding="utf-8")
    return pfad


def _rendere(tmp_path, eingebettet: str = ""):
    pdf, _ = cli.rendere(_brief(tmp_path, eingebettet), tmp_path / "brief.pdf",
                         profil_verzeichnis=PROFILE)
    return pdf


def _anhaenge(pdf) -> list[dict]:
    """Die eingebetteten Dateien mit ihren Angaben — so, wie ein Leser sie sieht."""
    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    heraus = []
    for eintrag in wurzel.get("/AF", []):
        objekt = eintrag.get_object()
        datei = objekt.get("/EF", {}).get("/F")
        heraus.append({
            "name": str(objekt.get("/F", "")),
            "beziehung": str(objekt.get("/AFRelationship", "")),
            "beschreibung": str(objekt.get("/Desc", "")),
            "typ": str(datei.get_object().get("/Subtype", "")) if datei is not None else "",
        })
    return heraus


# ── Die Stufe folgt dem Inhalt ──────────────────────────────────────────────

def test_ohne_einbettung_bleibt_es_bei_2b(tmp_path):
    """Der Bestand ändert sich nicht. Das ist die wichtigere der beiden
    Richtungen: Eine stille Umstellung träfe jede Datei im Archiv."""
    assert geometrie.pdfa_stufe(_rendere(tmp_path)) == "2b"


def test_mit_einbettung_wird_es_3b(tmp_path):
    assert geometrie.pdfa_stufe(_rendere(tmp_path, MIT)) == "3b"


def test_die_datei_steckt_wirklich_drin(tmp_path):
    anhaenge = _anhaenge(_rendere(tmp_path, MIT))
    assert len(anhaenge) == 1, anhaenge
    assert anhaenge[0]["name"].endswith(".xml"), anhaenge
    assert anhaenge[0]["beziehung"] == "/Data", anhaenge
    assert anhaenge[0]["beschreibung"] == "Rechnungsdaten", anhaenge
    assert anhaenge[0]["typ"] == "/text/xml", anhaenge


def test_ohne_einbettung_ist_nichts_drin(tmp_path):
    """Gegenprobe: Ohne sie belegte der Test darüber nur, dass `_anhaenge`
    etwas findet — nicht, dass es vom Feld kommt."""
    assert _anhaenge(_rendere(tmp_path)) == []


def test_der_inhalt_kommt_unveraendert_an(tmp_path):
    """Eine Datei, die beim Einbetten verändert wird, ist keine Beilage mehr.

    Das ist bei einer Rechnung der Unterschied zwischen einem Beleg und einem
    Papier, das so aussieht.
    """
    inhalt = '<?xml version="1.0"?><rechnung><betrag>2380.00</betrag></rechnung>'
    pdf = cli.rendere(_brief(tmp_path, MIT, inhalt), tmp_path / "b.pdf",
                      profil_verzeichnis=PROFILE)[0]
    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    datei = wurzel["/AF"][0].get_object()["/EF"]["/F"].get_object()
    assert datei.get_data().decode("utf-8") == inhalt


# ── Der Datenvertrag meldet, bevor gesetzt wird ─────────────────────────────

@pytest.mark.parametrize("fehlt", ["datei", "typ", "beschreibung"])
def test_jede_pflichtangabe_wird_verlangt(tmp_path, fehlt):
    felder = {"datei": "daten.xml", "typ": "text/xml", "beschreibung": "Daten"}
    del felder[fehlt]
    block = "eingebettet:\n  - " + "\n    ".join(f"{k}: {v}" for k, v in felder.items()) + "\n"
    bericht = cli.linte(_brief(tmp_path, block), profil_verzeichnis=PROFILE)
    assert "eingebettet" in {b.regel for b in bericht.befunde}, bericht.als_text()


def test_ein_vollstaendiger_eintrag_wird_nicht_gemeldet(tmp_path):
    """Gegenprobe. Ohne sie könnte die Prüfung jeden Eintrag melden."""
    bericht = cli.linte(_brief(tmp_path, MIT), profil_verzeichnis=PROFILE)
    assert "eingebettet" not in {b.regel for b in bericht.befunde}, bericht.als_text()


def test_eine_erfundene_beziehung_wird_abgewiesen(tmp_path):
    block = MIT.replace("beziehung: data", "beziehung: rechnung")
    bericht = cli.linte(_brief(tmp_path, block), profil_verzeichnis=PROFILE)
    befunde = [b for b in bericht.befunde if b.regel == "eingebettet"]
    assert befunde, bericht.als_text()
    assert "rechnung" in befunde[0].meldung


@pytest.mark.parametrize("beziehung", lint.EINBETTUNG_BEZIEHUNGEN)
def test_und_die_vier_echten_gehen_durch(tmp_path, beziehung):
    """Gegenprobe zur Liste selbst — sie darf nicht alles ablehnen."""
    block = MIT.replace("beziehung: data", f"beziehung: {beziehung}")
    bericht = cli.linte(_brief(tmp_path, block), profil_verzeichnis=PROFILE)
    assert "eingebettet" not in {b.regel for b in bericht.befunde}, bericht.als_text()


def test_ein_unbekanntes_feld_faellt_auf(tmp_path):
    block = MIT + "    version: 2.3\n"
    bericht = cli.linte(_brief(tmp_path, block), profil_verzeichnis=PROFILE)
    assert "eingebettet" in {b.regel for b in bericht.befunde}, bericht.als_text()


def test_eine_fehlende_datei_bricht_ab_statt_still_zu_fehlen(tmp_path):
    """Ein PDF, dem die Beilage fehlt, sieht aus wie eines mit — von außen.

    Bei einer Rechnung wäre das der teure Fall: Der Empfänger bekommt ein
    Papier, das aussieht wie ein Beleg, und sein Programm findet nichts.
    """
    pfad = tmp_path / "brief.md"
    pfad.write_text(BRIEF.format(eingebettet=MIT), encoding="utf-8")   # ohne daten.xml
    with pytest.raises(cli.Eingabefehler, match="gibt es nicht"):
        cli.rendere(pfad, tmp_path / "b.pdf", profil_verzeichnis=PROFILE)


# ── Die Konformitätsprüfung kennt die neue Stufe ────────────────────────────

def test_die_stufenerkennung_liest_beide(tmp_path):
    """Bis #114 stand hier fest die 2, und ein A-3b galt als „fehlt"."""
    assert geometrie.pdfa_stufe(_rendere(tmp_path)) == "2b"
    assert geometrie.pdfa_stufe(_rendere(tmp_path, MIT)) == "3b"


def test_ein_pdf_ohne_kennzeichnung_gibt_none(tmp_path):
    """Gegenprobe: Die Erkennung darf nicht jedem PDF eine Stufe zusprechen."""
    pdf, _ = cli.rendere(_brief(tmp_path), tmp_path / "roh.pdf",
                         profil_verzeichnis=PROFILE, pdfa=False)
    assert geometrie.pdfa_stufe(pdf) is None


def test_das_konformitaetsskript_erkennt_3b(tmp_path):
    """Es liest die Stufe aus dem XMP und hält sie gegen veraPDF. Ohne diesen
    Schritt liefe die CI für ein A-3b gegen das falsche Profil."""
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    import pdf_konformitaet

    assert pdf_konformitaet.deklarierte_standards(_rendere(tmp_path, MIT)) == ["3b"]
    assert pdf_konformitaet.deklarierte_standards(_rendere(tmp_path)) == ["2b"]


# ── Und der Datenvertrag ist dokumentiert ───────────────────────────────────

def test_das_feld_steht_in_der_anleitung():
    text = (REPO / "skill" / "references" / "frontmatter.md").read_text(encoding="utf-8")
    assert "eingebettet:" in text, "das Feld fehlt in references/frontmatter.md"
    for pflicht in ("datei", "typ", "beschreibung"):
        assert pflicht in text


def test_die_anleitung_haelt_beide_felder_auseinander():
    """`anlagen_dateien:` und `eingebettet:` tun Verschiedenes, und die
    Verwechslung wäre teuer: einmal Seiten, einmal eine Datei im Dokument."""
    text = (REPO / "skill" / "references" / "frontmatter.md").read_text(encoding="utf-8")
    stelle = text[text.index("### Eingebettete Dateien"):]
    assert "anlagen_dateien" in stelle[:1500], "die Abgrenzung fehlt"
