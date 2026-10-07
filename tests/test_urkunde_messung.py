"""Die Urkunde am fertigen PDF: gesetzt, vermerkt, nach eigener Liste gemessen (ADR 0048).

Zwei Dinge hält diese Datei fest. Erstens, dass eine Urkunde ihre Maße hält —
und dass `verify` das an der fertigen Datei wissen kann, ohne die Quelle zu
sehen. Zweitens die Gegenrichtung: dass der Brief davon nichts merkt. Er trägt
keinen neuen Vermerk, verlangt seine Anschrift weiter unbedingt, und ein Brief,
der sich als Urkunde ausgibt, fällt auf.

Die Sabotagen am Satz stehen in `tests/test_gegenbeweis.py`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pdfplumber
import pypdf
import pytest

from falzmarke import cli, geometrie
from conftest import REPO, SKILL, URKUNDE_BEISPIELE

CLI = SKILL / "scripts" / "falzmarke.py"
TYPST = (SKILL / "falzmarke" / "typst" / "falzmarke.typ").read_text(encoding="utf-8")

KOPF = """---
profil: example
typ: urkunde
dialekt: "1.2"
titel: Probe
{zusatz}---

## 1. Abschnitt

{text}
"""


def rufe(*argumente) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *map(str, argumente)],
                          capture_output=True, text=True, encoding="utf-8")


def setze(tmp_path: Path, zusatz: str = "", text: str = "Ein Absatz.", name: str = "u") -> Path:
    quelle = tmp_path / f"{name}.md"
    quelle.write_text(KOPF.format(zusatz=zusatz, text=text), encoding="utf-8")
    pdf, _ = cli.rendere(quelle, tmp_path / f"{name}.pdf")
    return pdf


def gescheitert(pdf: Path, **kw) -> set[str]:
    return {p.name for p in geometrie.pruefe(pdf, kw.pop("form", ""), **kw).pruefungen
            if not p.bestanden}


def vermerke(pdf: Path) -> dict:
    return {k: str(v) for k, v in (pypdf.PdfReader(str(pdf)).metadata or {}).items()
            if str(k).startswith("/falzmarke_")}


@pytest.fixture(scope="module")
def muster(tmp_path_factory) -> dict[str, Path]:
    ziel = tmp_path_factory.mktemp("urkunden")
    return {p.stem: cli.rendere(p, ziel / f"{p.stem}.pdf")[0] for p in URKUNDE_BEISPIELE}


# ── Abnahme: Die Musterdokumente bestehen ───────────────────────────────────

@pytest.mark.parametrize("beispiel", URKUNDE_BEISPIELE, ids=lambda p: p.stem)
def test_musterdokument_haelt_alle_masse(muster, beispiel):
    bericht = geometrie.pruefe(muster[beispiel.stem], "")
    assert bericht.ok, bericht.als_text()
    # Zählwert statt bloßer Fehlerfreiheit: Ein leerer Bericht wäre auch „ok".
    assert len(bericht.pruefungen) >= 18, [p.name for p in bericht.pruefungen]


@pytest.mark.parametrize("beispiel", URKUNDE_BEISPIELE, ids=lambda p: p.stem)
def test_render_endet_mit_null_und_verify_auch(tmp_path, beispiel):
    """Der Weg, den ein Mensch geht: `render`, danach `verify` auf der fertigen Datei."""
    pdf = tmp_path / "aus.pdf"
    render = rufe("render", beispiel, "-o", pdf)
    assert render.returncode == 0, render.stdout + render.stderr
    verify = rufe("verify", pdf)
    assert verify.returncode == 0, verify.stdout + verify.stderr
    treffer = re.search(r"OK  verify: (\d+)/(\d+) Maße eingehalten", verify.stdout)
    assert treffer and treffer.group(1) == treffer.group(2) and int(treffer.group(1)) >= 18


def test_die_musterdokumente_decken_die_elemente(muster):
    """Zusammen zeigen sie, wofür der Typ da ist — sonst prüft die Abnahme zu wenig."""
    namen = {s: {p.name for p in geometrie.pruefe(pdf, "").pruefungen} for s, pdf in muster.items()}
    alle = set().union(*namen.values())
    for erwartet in ("Seitenzahl", "Keine Marken im Heftrand", "Titel, y-Oberkante",
                     "Seite 1, Linien im Satzspiegel", "Seite 1, Zeilenraster",
                     "Unterschriftslinien, Anzahl", "Unterschriftslinien, Raum darüber",
                     "Unterschriftslinien, Abstand", "Unterschriftslinien, gleiche Höhe"):
        assert erwartet in alle, f"{erwartet} wird an keinem Musterdokument gemessen"
    quellen = "".join(p.read_text(encoding="utf-8") for p in URKUNDE_BEISPIELE)
    assert "parteien:" in quellen and "|   |   |" in quellen and "____" in quellen


def test_die_urkunde_ist_pdfa_2b(muster):
    for pdf in muster.values():
        assert geometrie.pdfa_stufe(pdf) == "2b"


# ── Der Vermerk: was `verify` an der fertigen Datei weiß ────────────────────

def test_die_urkunde_weist_sich_aus(muster):
    v = vermerke(muster["urkunde-vereinbarung"])
    assert v["/falzmarke_Typ"] == "urkunde"
    assert v["/falzmarke_Kopf_mm"] == "27"
    assert v["/falzmarke_Unterschriften"] == "2"
    assert v["/falzmarke_Seiten_max"] == "1"
    assert geometrie.typ_aus_metadaten(muster["urkunde-vereinbarung"]) == "urkunde"


def test_der_brief_traegt_keinen_neuen_vermerk(gerendert):
    """Jeder zusätzliche Schlüssel hätte die Bytes aller bestehenden Briefe geändert."""
    pdf, _ = gerendert["brief-form-b"]
    assert set(vermerke(pdf)) == {"/falzmarke_Version", "/falzmarke_Profil",
                                  "/falzmarke_Form", "/falzmarke_Quelle"}
    assert geometrie.typ_aus_metadaten(pdf) == "brief"


def test_ohne_seiten_max_steht_keine_grenze_im_pdf_und_im_bericht(tmp_path):
    pdf = setze(tmp_path, zusatz="unterschriften:\n  - name: Erika Muster\n")
    assert "/falzmarke_Seiten_max" not in vermerke(pdf)
    zeile = next(p for p in geometrie.pruefe(pdf, "").pruefungen if p.name == "Seitenzahl")
    assert (zeile.soll, zeile.ist, zeile.bestanden) == ("keine Grenze gesetzt", "1", True)


# ── Der Vermerk ist eine Behauptung, kein Befund ────────────────────────────

def _mit_vermerken(quelle: Path, ziel: Path, aendern) -> Path:
    leser = pypdf.PdfReader(str(quelle))
    schreiber = pypdf.PdfWriter(clone_from=leser)
    angaben = {str(k): str(v) for k, v in (leser.metadata or {}).items()}
    aendern(angaben)
    schreiber.metadata = None
    schreiber.add_metadata(angaben)
    with ziel.open("wb") as datei:
        schreiber.write(datei)
    return ziel


def test_ein_brief_der_sich_als_urkunde_ausgibt_faellt_auf(tmp_path, gerendert):
    """Sonst entginge er mit einem einzigen Metadatenfeld allen Briefprüfungen."""
    brief, form = gerendert["brief-form-b"]
    assert gescheitert(brief, form=form) == set()          # Kontrollprobe: Der Brief ist gut.
    falsch = _mit_vermerken(brief, tmp_path / "falsch.pdf",
                            lambda a: a.update({"/falzmarke_Typ": "urkunde"}))
    assert geometrie.typ_aus_metadaten(falsch) == "urkunde"   # Die Fälschung greift.
    rot = gescheitert(falsch)
    assert "Keine Marken im Heftrand" in rot, rot
    assert rufe("verify", falsch).returncode == 2


def test_form_erzwingt_die_briefliste(muster):
    """`--form` übersteuert den Vermerk — und eine Urkunde ist kein Brief."""
    pdf = muster["urkunde-vereinbarung"]
    assert rufe("verify", pdf).returncode == 0
    mit_form = rufe("verify", pdf, "--form", "B")
    assert mit_form.returncode == 2, mit_form.stdout
    # Namentlich: Die Marken fehlen, und daran erkennt die Briefliste es zuerst.
    assert "FEHL  Falzmarke 1, y" in mit_form.stdout


def test_ohne_vermerk_ist_die_urkunde_nicht_gruen(tmp_path, muster):
    """Geht der Vermerk verloren, weiß `verify` nicht mehr, was es misst.

    Es rät dann nicht: Ohne Marken und ohne Vermerk endet der Lauf mit Exit 1
    und sagt, was fehlt. Grün wird er nicht.
    """
    nackt = _mit_vermerken(
        muster["urkunde-vereinbarung"], tmp_path / "nackt.pdf",
        lambda a: [a.pop(k) for k in list(a) if k.startswith("/falzmarke_")])
    assert vermerke(nackt) == {}
    lauf = rufe("verify", nackt)
    assert lauf.returncode == 1, lauf.stdout + lauf.stderr
    assert "Urkunde" in lauf.stderr


def test_fehlt_nur_die_zahl_der_unterschriften_ist_das_ein_befund(tmp_path, muster):
    ohne = _mit_vermerken(muster["urkunde-vereinbarung"], tmp_path / "ohne.pdf",
                          lambda a: a.pop("/falzmarke_Unterschriften"))
    assert gescheitert(ohne) == {"Unterschriftslinien, Anzahl"}


def test_eine_erfundene_kopfhoehe_ist_ein_befund(tmp_path, muster):
    """Der Vermerk wählt zwischen 27 und 45 mm. Ein Soll liefert er nicht."""
    falsch = _mit_vermerken(muster["urkunde-vereinbarung"], tmp_path / "kopf.pdf",
                            lambda a: a.update({"/falzmarke_Kopf_mm": "36"}))
    assert "Kopfhöhe laut Vermerk" in gescheitert(falsch)


def test_die_falsche_der_zwei_kopfhoehen_ist_ein_befund(tmp_path, muster):
    falsch = _mit_vermerken(muster["urkunde-vereinbarung"], tmp_path / "kopf45.pdf",
                            lambda a: a.update({"/falzmarke_Kopf_mm": "45"}))
    assert "Titel, y-Oberkante" in gescheitert(falsch)


# ── Seitenzahl ──────────────────────────────────────────────────────────────

FUELLUNG = "\n\n".join(f"Absatz {i}: " + "Dieser Text füllt die Seite. " * 6 for i in range(1, 22))


def test_zwei_seiten_bei_erlaubten_zwei_sind_in_ordnung(tmp_path):
    pdf = setze(tmp_path, zusatz="seiten_max: 2\nunterschriften:\n  - name: Erika Muster\n",
                text=FUELLUNG)
    assert len(pypdf.PdfReader(str(pdf)).pages) == 2          # Die Füllung reicht wirklich.
    assert gescheitert(pdf) == set()


def test_zwei_seiten_bei_erlaubter_einer_sind_rot(tmp_path):
    pdf = setze(tmp_path, zusatz="seiten_max: 1\nunterschriften:\n  - name: Erika Muster\n",
                text=FUELLUNG)
    assert len(pypdf.PdfReader(str(pdf)).pages) == 2
    assert gescheitert(pdf) == {"Seitenzahl"}


def test_render_meldet_die_ueberschreitung_ohne_din(tmp_path):
    quelle = tmp_path / "lang.md"
    quelle.write_text(KOPF.format(zusatz="seiten_max: 1\n", text=FUELLUNG), encoding="utf-8")
    lauf = rufe("render", quelle, "-o", tmp_path / "lang.pdf")
    assert lauf.returncode == 2
    assert "FEHL  Seitenzahl: soll ≤ 1 ist 2" in lauf.stdout
    assert "seiten_max: 1" in lauf.stdout                     # die Ursache, nicht nur das Symptom
    # Die Norm sagt zu diesem Blatt nichts — die Schlussmeldung darf sie nicht nennen.
    assert "DIN" not in lauf.stderr, lauf.stderr
    assert "für eine Urkunde setzt" in lauf.stderr


def test_die_folgeseite_traegt_titel_und_seitenzahl(tmp_path):
    pdf = setze(tmp_path, text=FUELLUNG)
    with pdfplumber.open(str(pdf)) as dokument:
        zweite = dokument.pages[1].extract_text()
    assert zweite.startswith("Probe")
    assert "Seite 2 von 2" in zweite


def test_eine_seite_traegt_keine_seitenzahl(muster):
    with pdfplumber.open(str(muster["urkunde-vereinbarung"])) as dokument:
        assert "Seite 1 von" not in dokument.pages[0].extract_text()


# ── Unterschriften ──────────────────────────────────────────────────────────

ZWEI_PARTEIEN = ("parteien:\n  - name: Erika Muster\n    anschrift: [Musterweg 1, 93055 Regensburg]\n"
                 "  - name: Max Muster\n")


def _linien(pdf: Path) -> list[tuple[float, float]]:
    with pdfplumber.open(str(pdf)) as dokument:
        return [(w[1], w[2]) for w in geometrie._waagerechte(dokument.pages[-1])
                if w[3] and abs((w[2] - w[1]) - 65.0) <= 0.3]


def test_ohne_unterschriften_unterschreibt_jede_partei(tmp_path):
    pdf = setze(tmp_path, zusatz=ZWEI_PARTEIEN)
    assert vermerke(pdf)["/falzmarke_Unterschriften"] == "2"
    assert len(_linien(pdf)) == 2
    assert gescheitert(pdf) == set()


def test_leere_unterschriftenliste_heisst_keine(tmp_path):
    pdf = setze(tmp_path, zusatz=ZWEI_PARTEIEN + "unterschriften: []\n")
    assert vermerke(pdf)["/falzmarke_Unterschriften"] == "0"
    assert _linien(pdf) == []
    assert gescheitert(pdf) == set()


def test_eine_unterschrift_steht_links(tmp_path):
    pdf = setze(tmp_path, zusatz="unterschriften:\n  - name: Erika Muster\n")
    (links, rechts), = _linien(pdf)
    assert links == pytest.approx(25.0, abs=0.3) and rechts == pytest.approx(90.0, abs=0.3)


def test_zwei_unterschriften_stehen_nebeneinander(muster):
    a, b = sorted(_linien(muster["urkunde-vereinbarung"]))
    assert a == pytest.approx((25.0, 90.0), abs=0.3)
    assert b == pytest.approx((112.5, 177.5), abs=0.3)


def test_ohne_ort_datum_steht_eine_leere_linie_mit_beschriftung(tmp_path):
    pdf = setze(tmp_path, zusatz="unterschriften:\n  - name: Erika Muster\n")
    with pdfplumber.open(str(pdf)) as dokument:
        assert "Ort, Datum" in dokument.pages[0].extract_text()
    assert gescheitert(pdf) == set()


def test_ort_datum_wird_woertlich_gesetzt(tmp_path):
    """Kein Datumsformat des Profils, keine Typografie: Die Zeile steht da, wie sie dasteht."""
    pdf = setze(tmp_path, zusatz='ort_datum: "Musterstadt, den 12.10.2026"\n'
                                 "unterschriften:\n  - name: Erika Muster\n")
    with pdfplumber.open(str(pdf)) as dokument:
        assert "Musterstadt, den 12.10.2026" in dokument.pages[0].extract_text()


# ── Die Sollwerte stehen an zwei Stellen — und stimmen überein ──────────────

def test_unterschriftslinie_misst_in_satz_und_messung_dasselbe():
    """Die Zahl steht hier ein drittes Mal, als Literal: Sonst prüfte der Test
    die Messung gegen den Satz und merkte nicht, wenn beide gemeinsam wandern."""
    assert re.search(r"#let unterschrift-linie = 65mm\b", TYPST)
    assert geometrie.UNTERSCHRIFT_LINIE == 65.0


def test_ausfuellfeld_misst_zwei_millimeter_je_unterstrich(tmp_path):
    assert re.search(r"#let feld-einheit = 2mm\b", TYPST)
    assert geometrie.FELD_EINHEIT == 2.0
    pdf = setze(tmp_path, text="Schrank Nr. ______________ der Werkstatt.")     # 14 Unterstriche
    with pdfplumber.open(str(pdf)) as dokument:
        felder = [w for w in geometrie._waagerechte(dokument.pages[0]) if not w[3] and w[0] > 27]
    assert len(felder) == 1
    assert felder[0][2] - felder[0][1] == pytest.approx(28.0, abs=0.1)


def test_die_zwei_kopfhoehen_sind_die_des_briefes():
    assert geometrie.URKUNDE_KOPFHOEHEN == (27.0, 45.0)
    assert {geometrie.FORM["A"]["kopfhoehe"], geometrie.FORM["B"]["kopfhoehe"]} == {27.0, 45.0}


@pytest.mark.parametrize("profil,erwartet", [
    ({"briefkopf": {"zeilen": ["a", "b", "c"]}}, 27),                 # Name und drei Zeilen
    ({"briefkopf": {"logo": "l.svg", "logo_hoehe_mm": 14}}, 27),      # flaches Logo
    ({"briefkopf": {"logo": "l.svg"}}, 45),                           # Logo in Vorgabehöhe, 42 mm
    ({"briefkopf": {"logo": "l.svg", "logo_hoehe_mm": 19}}, 27),      # 8 + 19 = 27, passt genau
    ({"briefkopf": {"logo": "l.svg", "logo_hoehe_mm": 20}}, 45),      # 8 + 20 = 28, passt nicht
    ({"briefkopf": {"zeilen": list("abcde")}}, 45),                   # fünf Zeilen rechts
    ({"briefkopf_typ": "kopf.typ"}, 45),                              # eigener Kopf: nicht berechenbar
    ({}, 27),
])
def test_kopfhoehe_folgt_dem_briefkopf(profil, erwartet):
    assert cli.urkunde_kopf_mm(profil) == erwartet


def test_der_titel_steht_bei_beiden_kopfhoehen_richtig(tmp_path, monkeypatch):
    """45 mm kommt in keinem Musterdokument vor — also hier, sonst wäre die Hälfte ungemessen."""
    monkeypatch.setattr(cli, "urkunde_kopf_mm", lambda profil: 45)
    pdf = setze(tmp_path, zusatz="unterschriften:\n  - name: Erika Muster\n")
    assert vermerke(pdf)["/falzmarke_Kopf_mm"] == "45"
    titel = next(p for p in geometrie.pruefe(pdf, "").pruefungen if p.name == "Titel, y-Oberkante")
    assert titel.bestanden and float(titel.ist) == pytest.approx(53.8, abs=0.3)


# ── Ausfüllfelder verstecken keinen Rasterfehler ────────────────────────────

DREI_FELDER = ("Name: ____________________\n\nStraße: ____________________\n\n"
               "Wohnort: ____________________\n\nEin Absatz danach.")


def test_drei_gleich_lange_felder_gelten_nicht_als_tabelle(tmp_path):
    """Drei gleich breite *Linien* untereinander hält die Messung für einen
    Tabellenrahmen und nimmt den Bereich vom Raster aus. Felder sind deshalb
    keine Linien — sonst versteckte ein Formular jeden Rasterfehler in sich."""
    pdf = setze(tmp_path, text=DREI_FELDER)
    with pdfplumber.open(str(pdf)) as dokument:
        seite = dokument.pages[0]
        felder = [w for w in geometrie._waagerechte(seite) if not w[3] and w[0] > 27]
        assert len(felder) == 3 and len({round(f[2] - f[1], 1) for f in felder}) == 1
        assert geometrie._tabellenbereiche(seite) == []
    assert gescheitert(pdf) == set()


def test_als_linien_gesetzt_waeren_sie_eine_tabelle(tmp_path, monkeypatch):
    """Die Gegenprobe zur Bauweise: Mit `line()` statt Kastenrand greift die Tabellenerkennung."""
    import shutil
    kopie = tmp_path / "typst"
    shutil.copytree(SKILL / "falzmarke" / "typst", kopie)
    datei = kopie / "falzmarke.typ"
    inhalt = datei.read_text(encoding="utf-8")
    alt = "  stroke: (bottom: 0.5pt + black),\n)"
    assert alt in inhalt
    datei.write_text(inhalt.replace(
        alt, "  place(bottom, line(length: 100%, stroke: 0.5pt + black)),\n)"), encoding="utf-8")
    monkeypatch.setattr(cli, "TYPST_DIR", kopie)
    pdf = setze(tmp_path, text=DREI_FELDER, name="linien")
    with pdfplumber.open(str(pdf)) as dokument:
        assert geometrie._tabellenbereiche(dokument.pages[0]) != []


# ── Dialekt 1.2 im Brief: Der Brief bleibt ein Brief ────────────────────────

BRIEF = """---
profil: example
dialekt: "{dialekt}"
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-10-12
betreff: Rückmeldebogen
anrede: Sehr geehrte Damen und Herren,
---
bitte tragen Sie ein:

{text}

Vielen Dank.
"""


def test_brief_mit_feldern_und_angaben_haelt_alle_briefmasse(tmp_path):
    quelle = tmp_path / "b.md"
    quelle.write_text(BRIEF.format(dialekt="1.2", text=(
        "Name: ____________________\n\n|   |   |\n|---|---|\n| Kundennummer | 4711 |\n"
        "| Rückruf unter | ______________ |")), encoding="utf-8")
    pdf, form = cli.rendere(quelle, tmp_path / "b.pdf")
    bericht = geometrie.pruefe(pdf, form)
    assert bericht.ok, bericht.als_text()
    assert "Anschrift, x-links" in {p.name for p in bericht.pruefungen}     # die Briefliste
    assert "/falzmarke_Typ" not in vermerke(pdf)


def test_unter_dialekt_11_bleiben_unterstriche_text(tmp_path):
    """Die Zusage des Dialekts: Was heute geschrieben ist, setzt morgen gleich."""
    quelle = tmp_path / "alt.md"
    quelle.write_text(BRIEF.format(dialekt="1.1", text="Name: ____________________"),
                      encoding="utf-8")
    pdf, _ = cli.rendere(quelle, tmp_path / "alt.pdf")
    with pdfplumber.open(str(pdf)) as dokument:
        seite = dokument.pages[0]
        assert "____________________" in seite.extract_text()
        assert not [w for w in geometrie._waagerechte(seite) if not w[3] and 100 < w[0] < 250]


# ── Was es für eine Urkunde nicht gibt ──────────────────────────────────────

@pytest.fixture
def urkunde_datei(tmp_path) -> Path:
    datei = tmp_path / "u.md"
    datei.write_text(KOPF.format(zusatz="", text="Ein Absatz."), encoding="utf-8")
    return datei


def test_keine_email_fassung(urkunde_datei, tmp_path):
    with pytest.raises(cli.Eingabefehler, match="typ: urkunde"):
        cli.setze_email(urkunde_datei, tmp_path / "aus.eml")


def test_keine_begleitmail_zu_einer_urkunde(urkunde_datei, tmp_path):
    mail = tmp_path / "mail.md"
    mail.write_text("---\nprofil: example\ntyp: email\nan: muster@example.de\n"
                    f"betreff: Anbei\nbrief: {urkunde_datei.name}\n---\nGuten Tag,\n\nanbei.\n",
                    encoding="utf-8")
    with pytest.raises(cli.Eingabefehler, match="typ: urkunde"):
        cli.setze_email(mail, tmp_path / "aus.eml")


def test_kein_serienlauf(urkunde_datei, tmp_path):
    with pytest.raises(cli.Eingabefehler, match="Serienlauf"):
        cli.rendere(urkunde_datei, tmp_path / "s.pdf", ersetzungen={"name": "x"})


def test_keine_xml(urkunde_datei):
    lauf = rufe("xml", urkunde_datei)
    assert lauf.returncode == 1 and "typ: rechnung" in lauf.stderr


def test_ueberschrift_erster_ebene_bricht_auch_ohne_lint_ab(tmp_path):
    """`cli.rendere` ist der Weg des MCP-Dienstes, und der lintet nicht."""
    datei = tmp_path / "h1.md"
    datei.write_text(KOPF.format(zusatz="", text="# Falsche Ebene\n\nText."), encoding="utf-8")
    with pytest.raises(cli.Eingabefehler, match="erster Ebene"):
        cli.rendere(datei, tmp_path / "h1.pdf")


def test_unbekanntes_feld_bricht_auch_ohne_lint_ab(tmp_path):
    datei = tmp_path / "f.md"
    datei.write_text(KOPF.format(zusatz="farbe: rot\n", text="Text."), encoding="utf-8")
    with pytest.raises(cli.Eingabefehler, match="farbe"):
        cli.rendere(datei, tmp_path / "f.pdf")


def test_der_dienst_setzt_und_misst_eine_urkunde(tmp_path):
    from falzmarke import dienst

    ergebnis = dienst.brief_rendern(
        KOPF.format(zusatz="seiten_max: 1\nunterschriften:\n  - name: Erika Muster\n",
                    text="Ein Absatz."), ziel=str(tmp_path / "d.pdf"))
    assert ergebnis["typ"] == "urkunde" and ergebnis["bestanden"], ergebnis["zusammenfassung"]
    geprueft = dienst.brief_pruefen(pdf_pfad=str(tmp_path / "d.pdf"))
    assert geprueft["typ"] == "urkunde" and geprueft["bestanden"]


# ── Struktur: Was das PDF über sich sagt ────────────────────────────────────

def _strukturtypen(pdf: Path) -> list[str]:
    gefunden: list[str] = []

    def gehe(knoten):
        knoten = knoten.get_object() if hasattr(knoten, "get_object") else knoten
        if isinstance(knoten, list):
            for k in knoten:
                gehe(k)
            return
        if not hasattr(knoten, "get"):
            return
        if knoten.get("/S"):
            gefunden.append(str(knoten["/S"]))
        if "/K" in knoten:
            gehe(knoten["/K"])

    gehe(pypdf.PdfReader(str(pdf)).trailer["/Root"]["/StructTreeRoot"])
    return gefunden


def test_titel_ist_ueberschrift_erster_ebene_und_die_angaben_sind_eine_tabelle(muster):
    typen = _strukturtypen(muster["urkunde-erklaerung"])
    ueberschriften = [t for t in typen if re.fullmatch(r"/H\d", t)]
    assert ueberschriften[0] == "/H1" and ueberschriften.count("/H1") == 1, ueberschriften
    assert "/H2" in ueberschriften
    assert "/Table" in typen and "/TD" in typen
    # Ohne Kopfzeile gibt es keine Kopfzellen — und das ist hier richtig so.
    assert "/TH" not in typen


def test_die_urkunde_laesst_sich_als_pdfua_setzen(tmp_path):
    """Typst bricht bei `ua-1` ab, wenn die erste Überschrift nicht Ebene 1 ist."""
    pdf, _ = cli.rendere(URKUNDE_BEISPIELE[0], tmp_path / "ua.pdf", pdfua=True)
    assert geometrie.pruefe(pdf, "").ok
