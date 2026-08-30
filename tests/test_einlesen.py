"""Einen bestehenden Brief einlesen (#191).

Der Rundlauf ist die Kontrollgruppe dieses Moduls: Ein Brief, den falzmarke
selbst gesetzt hat, muss beim Wiedereinlesen dieselben Frontmatter-Werte
ergeben. Das ist der einzige Fall, in dem die Erkennung vollstaendig sein MUSS
— an ihm misst sich, ob die uebrigen Luecken echte Luecken sind oder nur
Unvermoegen.

Die Gegenprobe dazu ist `altbrief.typ`: ein Word-artiger Brief ohne
DIN-Raster. Dort darf NICHTS gesetzt werden. Ohne diesen Fall saehe ein
Importer, der immer raet, genauso gruen aus wie einer, der es richtig macht.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
import yaml

from conftest import REPO

sys.path.insert(0, str(REPO / "skill"))

from falzmarke.einlesen import PdfUnlesbar, lies_pdf  # noqa: E402

BEISPIEL_B = REPO / "examples" / "brief-form-b.md"
BEISPIEL_A = REPO / "examples" / "brief-form-a.md"
ALTBRIEF = REPO / "tests" / "fixtures" / "einlesen" / "altbrief.typ"
CLI = REPO / "skill" / "scripts" / "falzmarke.py"


def _frontmatter(md_pfad):
    text = md_pfad.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


@pytest.fixture(scope="module")
def dinbrief_b(tmp_path_factory):
    ziel = tmp_path_factory.mktemp("einlesen") / "form-b.pdf"
    subprocess.run(
        [sys.executable, str(CLI), "render", str(BEISPIEL_B), "-o", str(ziel)],
        check=True, capture_output=True, encoding="utf-8",
    )
    return ziel


@pytest.fixture(scope="module")
def dinbrief_a(tmp_path_factory):
    ziel = tmp_path_factory.mktemp("einlesen") / "form-a.pdf"
    subprocess.run(
        [sys.executable, str(CLI), "render", str(BEISPIEL_A), "-o", str(ziel)],
        check=True, capture_output=True, encoding="utf-8",
    )
    return ziel


@pytest.fixture(scope="module")
def altbrief_pdf(tmp_path_factory):
    """Der Word-artige Brief. Uebersprungen wird hier NICHT: Ohne ihn fehlt die
    Gegenprobe, und die Suite waere gruen, ohne etwas zu belegen."""
    import typst

    ziel = tmp_path_factory.mktemp("einlesen") / "altbrief.pdf"
    typst.compile(str(ALTBRIEF), output=str(ziel))
    return ziel


# --------------------------------------------------------------------------
# Rundlauf — die Kontrollgruppe
# --------------------------------------------------------------------------

def test_rundlauf_form_b_traegt_dieselben_werte(dinbrief_b):
    soll = _frontmatter(BEISPIEL_B)
    ist = lies_pdf(dinbrief_b)

    assert ist.form == "B"
    assert ist.felder["empfaenger"] == soll["empfaenger"]
    assert ist.felder["datum"] == str(soll["datum"])
    assert ist.felder["betreff"] == soll["betreff"]
    assert ist.felder["anrede"] == soll["anrede"]


def test_rundlauf_form_a_wird_als_form_a_erkannt(dinbrief_a):
    """Form A und B unterscheiden sich um 18 mm in der Falzmarke. Wer sie
    verwechselt, legt alle Zonen falsch — und traeger Werte heraus, die
    plausibel aussehen."""
    soll = _frontmatter(BEISPIEL_A)
    ist = lies_pdf(dinbrief_a)

    assert ist.form == "A"
    assert ist.felder["empfaenger"] == soll["empfaenger"]
    assert ist.felder["betreff"] == soll["betreff"]


def test_der_koerper_traegt_den_text_ohne_briefkopf_und_fusszeile(dinbrief_b):
    koerper = lies_pdf(dinbrief_b).koerper
    assert "vielen Dank für Ihre Anfrage" in koerper
    # Fusszeile gehoert zum Absenderprofil, nicht zum Brieftext.
    assert "MIT-Lizenz" not in koerper
    assert "github.com/blitzsicht/falzmarke" not in koerper
    # Silbentrennung des Satzes ist zurueckgenommen.
    assert "Neuge- staltung" not in koerper
    assert "Neugestaltung" in koerper


def test_aufzaehlung_bleibt_eine_aufzaehlung(dinbrief_b):
    """Drei Listenpunkte duerfen nicht zu einem Absatz verschmelzen."""
    koerper = lies_pdf(dinbrief_b).koerper
    punkte = [z for z in koerper.splitlines() if z.startswith("- ")]
    assert len(punkte) == 3, koerper


# --------------------------------------------------------------------------
# Die Gegenprobe — hier darf nichts geraten werden
# --------------------------------------------------------------------------

def test_altbrief_ohne_din_raster_setzt_kein_einziges_feld(altbrief_pdf):
    """Der teure Fall. Der Absender des Altbriefs liegt bei y = 44,9-50,2 mm
    und damit ZUFAELLIG in der Form-A-Anschriftzone (44,7-72,0). Ein
    zonenbasierter Importer haette ihn mit voller Ueberzeugung als Empfaenger
    ausgegeben — den falschen Menschen auf einem Brief.

    Gemessen: Der Altbrief traegt keine Falz- und Lochmarken (0 gegen 3 beim
    DIN-Brief). Ohne dieses Raster ist keine Position aussagekraeftig.
    """
    ergebnis = lies_pdf(altbrief_pdf)

    assert ergebnis.form is None
    assert "empfaenger" not in ergebnis.felder
    assert "datum" not in ergebnis.felder
    assert "betreff" not in ergebnis.felder

    markdown = ergebnis.als_markdown()
    # Der Absender darf an keiner Stelle als gesetzter Wert auftauchen.
    for zeile in markdown.splitlines():
        if zeile.startswith("#") or not zeile.strip():
            continue
        assert "Hinterhuber" not in zeile, f"Absender als Wert gesetzt: {zeile}"
        if zeile.startswith("---"):
            break


def test_altbrief_bietet_den_richtigen_empfaenger_als_kandidat(altbrief_pdf):
    """Ein Kandidat ist nuetzlich, aber er ist KEIN Wert — er steht als
    Kommentar. Der Unterschied ist der ganze Zweck des Moduls."""
    ergebnis = lies_pdf(altbrief_pdf)
    luecke = next(l for l in ergebnis.luecken if l.feld == "empfaenger")

    assert luecke.kandidat is not None
    assert "Ledermann" in luecke.kandidat          # der echte Empfaenger
    assert "Hinterhuber" not in luecke.kandidat    # nicht der Absender

    zeile = f"#   Kandidat: Herrn Dr. Franz Ledermann"
    assert zeile in ergebnis.als_markdown()


def test_jede_luecke_traegt_eine_begruendung(altbrief_pdf, dinbrief_b):
    """Kein stiller Leerwert. Eine Luecke ohne Grund waere von einem
    vergessenen Feld nicht zu unterscheiden."""
    for pdf in (altbrief_pdf, dinbrief_b):
        for luecke in lies_pdf(pdf).luecken:
            assert luecke.grund.strip(), f"{luecke.feld} ohne Begruendung"
            assert len(luecke.grund) > 20, f"{luecke.feld}: Begruendung zu duenn"


def test_profil_ist_immer_eine_luecke(dinbrief_b, altbrief_pdf):
    """Auch bei einem Brief, den falzmarke selbst gesetzt hat: Das
    Absenderprofil ist eine lokale Datei und steht in keinem PDF. Es zu raten
    hiesse, einen Absender zu erfinden."""
    for pdf in (dinbrief_b, altbrief_pdf):
        ergebnis = lies_pdf(pdf)
        assert "profil" not in ergebnis.felder
        assert "profil" in ergebnis.fehlend()


# --------------------------------------------------------------------------
# Robustheit
# --------------------------------------------------------------------------

def test_kaputte_datei_meldet_sich_verstaendlich(tmp_path):
    kaputt = tmp_path / "kaputt.pdf"
    kaputt.write_bytes(b"%PDF-1.7\nnicht wirklich ein PDF\n")
    with pytest.raises(PdfUnlesbar):
        lies_pdf(kaputt)


def test_leere_datei_meldet_sich_verstaendlich(tmp_path):
    leer = tmp_path / "leer.pdf"
    leer.write_bytes(b"")
    with pytest.raises(PdfUnlesbar):
        lies_pdf(leer)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _cli(*argumente, erwarte=0):
    lauf = subprocess.run(
        [sys.executable, str(CLI), *argumente],
        capture_output=True, encoding="utf-8",
    )
    assert lauf.returncode == erwarte, f"exit={lauf.returncode}\n{lauf.stderr}"
    return lauf


def test_cli_schreibt_ein_geruest(altbrief_pdf, tmp_path):
    ziel = tmp_path / "geruest.md"
    lauf = _cli("einlesen", str(altbrief_pdf), "-o", str(ziel))
    assert ziel.exists()
    assert "Ledermann" in ziel.read_text(encoding="utf-8")
    # Die Luecken gehen auf stderr, damit `... > datei.md` sauber bleibt.
    assert "nicht belegt werden" in lauf.stderr


def test_cli_endet_mit_null_auch_bei_luecken(altbrief_pdf, tmp_path):
    """Luecken sind das erwartete Ergebnis, kein Fehler. Ein Skript soll nicht
    bei jedem Altbrief scheitern — und der Exit-Code-Vertrag in docs/cli.md
    (0-4) wird fuer dieses Feature nicht erweitert."""
    _cli("einlesen", str(altbrief_pdf), "-o", str(tmp_path / "x.md"), erwarte=0)


def test_cli_ueberschreibt_nicht_ungefragt(altbrief_pdf, tmp_path):
    ziel = tmp_path / "vorhanden.md"
    ziel.write_text("Finger weg\n", encoding="utf-8")
    _cli("einlesen", str(altbrief_pdf), "-o", str(ziel), erwarte=1)
    assert ziel.read_text(encoding="utf-8") == "Finger weg\n"
    _cli("einlesen", str(altbrief_pdf), "-o", str(ziel), "--ueberschreiben")
    assert "Finger weg" not in ziel.read_text(encoding="utf-8")


def test_cli_json_ist_parsebar_und_nennt_die_luecken(altbrief_pdf):
    import json

    lauf = _cli("einlesen", str(altbrief_pdf), "--json")
    daten = json.loads(lauf.stdout)
    assert daten["form"] is None
    assert daten["felder"] == {}
    felder = {l["feld"] for l in daten["luecken"]}
    assert {"profil", "empfaenger", "datum", "betreff"} <= felder
    for luecke in daten["luecken"]:
        assert luecke["grund"]


def test_cli_meldet_kaputte_datei_ohne_traceback(tmp_path):
    kaputt = tmp_path / "kaputt.pdf"
    kaputt.write_bytes(b"kein PDF")
    lauf = _cli("einlesen", str(kaputt), erwarte=1)
    assert "Traceback" not in lauf.stderr
    assert "lässt sich nicht als PDF lesen" in lauf.stderr


def test_einlesen_steht_in_der_hilfe():
    """Ein Befehl, der nicht in --help steht, existiert für den Benutzer nicht."""
    lauf = _cli("--help")
    assert "einlesen" in lauf.stdout
