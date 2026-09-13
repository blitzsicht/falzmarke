"""PDF und XML tragen dieselben Angaben — nachgemessen (#116, Abnahme 2 und 3).

Dass beide Ausgaben aus einer Quelle entstehen, ist ein Bauprinzip und kein
Nachweis. Abnahme 2 verlangt ausdrücklich, die Übereinstimmung zu **prüfen**,
„nicht durch Zusicherung": Der Mensch liest das PDF, die Maschine die XML, und
eine Abweichung fällt genau dann niemandem auf, wenn beide für sich stimmig
aussehen. Ein PDF mit 1.190,00 € neben einer XML mit 1.109,00 € ist der teure
Fall (#119).

Gemessen wird am **fertigen Dokument**: Text aus dem gesetzten PDF gegen die
eingebettete XML, nicht gegen die Quelle. Beide gegen die Quelle zu halten wäre
schwächer — dann prüften zwei Wege dasselbe Original und könnten trotzdem
voneinander abweichen.

**Die Zahlen stehen verschieden da, und das ist die Falle.** Im PDF steht
`1.240,00 EUR`, in der XML `1240.00`. Ein Vergleich der Zeichenketten fände nie
eine Übereinstimmung — und eine Prüfung, die „keine Abweichung" meldet, weil sie
nichts findet, wäre grün, ohne je etwas gemessen zu haben. Deshalb die
Gegenprobe unten: Ein verfälschter Betrag MUSS auffallen.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pypdf
import pytest

from falzmarke import cli as falzmarke
from falzmarke import emit_xml
from conftest import REPO, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"
QUELLE = REPO / "examples" / "rechnung.md"
RAM = emit_xml.RAM
RSM = emit_xml.RSM


def _setze(tmp_path, name: str = "rechnung.pdf"):
    return falzmarke.rendere(QUELLE, tmp_path / name, profil_verzeichnis=PROFILE)[0]


def _xml_aus(pdf) -> ET.Element:
    """Die eingebettete XML — aus dem PDF gezogen, nicht neu erzeugt."""
    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    anhaenge = wurzel.get("/AF", [])
    assert len(anhaenge) == 1, f"erwartet genau eine Beilage, gefunden {len(anhaenge)}"
    datei = anhaenge[0].get_object()["/EF"]["/F"]
    return ET.fromstring(datei.get_object().get_data().decode("utf-8"))


def _pdftext(pdf) -> str:
    import pdfplumber

    with pdfplumber.open(str(pdf)) as dokument:
        return "\n".join(seite.extract_text() or "" for seite in dokument.pages)


def _betraege_im_pdf(text: str) -> set[float]:
    """Alle Eurobeträge des gesetzten Schreibens, als Zahl.

    `1.240,00 EUR` wird 1240.0 — sonst verglichen wir Schreibweisen statt Werte
    und fänden nie eine Übereinstimmung.
    """
    heraus = set()
    for treffer in re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*EUR", text):
        heraus.add(float(treffer.replace(".", "").replace(",", ".")))
    return heraus


def _betraege_in_xml(baum: ET.Element) -> set[float]:
    heraus = set()
    # `TaxTotalAmount` fehlte hier bis zum Review von #116 — ausgerechnet das Feld,
    # das der Emitter damals als einziges bildete statt übertrug.
    for name in ("LineTotalAmount", "GrandTotalAmount", "DuePayableAmount",
                 "TaxBasisTotalAmount", "CalculatedAmount", "TaxTotalAmount"):
        for knoten in baum.iter(f"{{{RAM}}}{name}"):
            heraus.add(float(knoten.text))
    return heraus


@pytest.fixture(scope="module")
def gesetzt(tmp_path_factory):
    pdf = _setze(tmp_path_factory.mktemp("treue"))
    return pdf, _pdftext(pdf), _xml_aus(pdf)


# ── Abnahme 2: dieselben Angaben in beiden Wegen ────────────────────────────

def test_die_rechnungsnummer_steht_in_beiden(gesetzt):
    """Gezielt aus `ExchangedDocument`, nicht „die erste ID im Baum".

    Der erste Entwurf nahm `[k for k in baum.iter() if k.tag.endswith('}ID')][0]`
    — das ist die Guideline-ID `urn:cen.eu:en16931:2017`. Der Test hätte damit
    geprüft, ob eine Norm-Kennung im Anschriftfeld steht, und wäre grün geworden,
    sobald sie irgendwo im PDF auftaucht.
    """
    _, text, baum = gesetzt
    dokument = baum.find(f"{{{RSM}}}ExchangedDocument")
    assert dokument is not None, "die XML hat keinen ExchangedDocument-Block"
    nummer = dokument.find(f"{{{RAM}}}ID").text
    assert nummer and not nummer.startswith("urn:"), \
        f"{nummer!r} sieht nach der Guideline-ID aus, nicht nach einer Rechnungsnummer"
    assert nummer in text, f"{nummer!r} steht nicht im gesetzten Schreiben"


def test_der_empfaenger_steht_in_beiden(gesetzt):
    _, text, baum = gesetzt
    kaeufer = baum.find(f".//{{{RAM}}}BuyerTradeParty/{{{RAM}}}Name")
    assert kaeufer is not None and kaeufer.text
    assert kaeufer.text in text, f"{kaeufer.text!r} steht nicht im Anschriftfeld"


def test_jede_position_steht_in_beiden(gesetzt):
    _, text, baum = gesetzt
    # Über `SpecifiedTradeProduct` und nicht über alle `Name`-Knoten: Verkäufer
    # und Käufer tragen denselben Tag, und die stehen zwar auch im PDF, aber aus
    # einem anderen Grund. Der Test soll die Positionen messen.
    bezeichnungen = [k.find(f"{{{RAM}}}Name").text
                     for k in baum.iter(f"{{{RAM}}}SpecifiedTradeProduct")]
    assert bezeichnungen, "die XML trägt keine Positionen — dann prüft das hier nichts"
    for bezeichnung in bezeichnungen:
        assert bezeichnung in text, f"Position {bezeichnung!r} fehlt im PDF"


def test_jeder_betrag_der_xml_steht_auch_im_pdf(gesetzt):
    """Der Kern. Beträge, die nur die Maschine sieht, sind der teure Fall.

    **Die Prüfung ist absichtlich einseitig:** Sie verlangt, dass jeder Betrag
    der XML im gesetzten Schreiben steht — nicht umgekehrt. Das PDF zeigt mehr,
    etwa den Einzelpreis je Position (gemessen: 3,00 EUR steht im PDF, aber in
    keinem der hier gelesenen XML-Felder). Die andere Richtung zu verlangen
    hieße, jede Zahl des Schreibens in der XML wiederfinden zu müssen — auch
    Hausnummern und Datumsteile.

    Die teure Richtung ist ohnehin diese: Was der Mensch im PDF nicht sieht,
    aber die Buchhaltung des Empfängers einliest, fällt niemandem auf.
    """
    _, text, baum = gesetzt
    im_pdf = _betraege_im_pdf(text)
    assert im_pdf, "im PDF wurde kein einziger Betrag gefunden — die Probe misst nichts"
    fehlend = {b for b in _betraege_in_xml(baum) if b not in im_pdf}
    assert not fehlend, f"nur in der XML, nicht im gesetzten Schreiben: {sorted(fehlend)}"


# ── Abnahme 3: die Gegenprobe ───────────────────────────────────────────────

def test_ein_betrag_nur_im_pdf_faellt_auf(tmp_path, monkeypatch):
    """Ein Wert wird in genau EINEM der beiden Wege verändert — die Prüfung
    oben muss ihn finden. Ohne diese Probe wüsste man von ihr nur, dass sie
    grün ist: Fände sie gar nichts, wäre sie es auch.
    """
    echt = falzmarke._euro

    def verfaelscht(wert):
        # Nur der Gesamtbetrag, und nur im gesetzten Schreiben. Die XML entsteht
        # aus denselben Kopfdaten und bleibt unberührt.
        return echt(9999.0) if float(wert) == 1904.0 else echt(wert)

    monkeypatch.setattr(falzmarke, "_euro", verfaelscht)
    pdf = _setze(tmp_path, "verfaelscht.pdf")
    text, baum = _pdftext(pdf), _xml_aus(pdf)

    im_pdf = _betraege_im_pdf(text)
    assert 9999.0 in im_pdf, "die Sabotage hat das PDF gar nicht verändert"
    fehlend = {b for b in _betraege_in_xml(baum) if b not in im_pdf}
    assert 1904.0 in fehlend, \
        "der Gesamtbetrag steht nur noch in der XML — das hätte auffallen müssen"


# ── Drei Fehlerarten aus dem Tracker von e-invoice-eu ───────────────────────
#
# Alle drei hat dort ein strengerer Prüfer gefunden, nachdem Mustang sie
# durchgelassen hatte (#435, #283/#303, #165). Bei uns sind sie am 13.09.2026
# nicht aufgetreten — diese Tests halten fest, dass es so bleibt. Jeder trägt
# seine Vorbedingung: Ohne sie wäre „nichts gefunden" kein Befund.

def test_das_xmp_traegt_umlaute_unversehrt(gesetzt):
    """e-invoice-eu #435: Nicht-ASCII-Zeichen im XMP zerstört."""
    pdf, _, _ = gesetzt
    roh = bytes(pypdf.PdfReader(str(pdf)).trailer["/Root"]["/Metadata"]
                .get_object().get_data())
    text = roh.decode("utf-8")          # wirft, wenn das XMP kein UTF-8 mehr ist
    assert "für" in text, "Vorbedingung: der Betreff im XMP trägt einen Umlaut"
    assert "�" not in text, "das XMP enthält Ersatzzeichen"


def test_die_beilage_steht_im_embeddedfiles_verzeichnis(gesetzt):
    """e-invoice-eu #283/#303: ohne `/EmbeddedFiles` fand ein Prüfer die Beilage nicht."""
    pdf, _, _ = gesetzt
    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    assert "/Names" in wurzel, "der Katalog hat kein Names-Verzeichnis"
    verzeichnis = wurzel["/Names"].get_object().get("/EmbeddedFiles")
    assert verzeichnis is not None, "kein /EmbeddedFiles im Names-Verzeichnis"
    namen = [str(n) for n in verzeichnis.get_object().get("/Names", [])[::2]]
    assert namen == ["factur-x.xml"], namen


def test_alle_schriften_sind_eingebettet(gesetzt):
    """e-invoice-eu #165 (dort offen): PDF/A verlangt eingebettete Schriften.

    Gezählt werden die Schriften der Seiten-Ressourcen. Verbindlich prüft das
    veraPDF in der CI; dieser Test ist der schnellere Vorbote.
    """
    pdf, _, _ = gesetzt
    schriften = {}
    for seite in pypdf.PdfReader(str(pdf)).pages:
        ressourcen = seite.get("/Resources")
        for eintrag in ((ressourcen.get_object().get("/Font") or {}).values()
                        if ressourcen else []):
            schrift = eintrag.get_object()
            beschreibung = schrift.get("/FontDescriptor")
            if beschreibung is None and schrift.get("/DescendantFonts"):
                beschreibung = schrift["/DescendantFonts"][0].get_object().get("/FontDescriptor")
            beschreibung = beschreibung.get_object() if beschreibung is not None else {}
            schriften[str(schrift.get("/BaseFont"))] = any(
                k in beschreibung for k in ("/FontFile", "/FontFile2", "/FontFile3"))
    assert schriften, "Vorbedingung: das PDF trägt überhaupt Schriften"
    assert all(schriften.values()), {n: e for n, e in schriften.items() if not e}
