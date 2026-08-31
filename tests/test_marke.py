"""Der Textkanon ist die einzige Quelle — und alle richten sich danach.

Anlass: Am 25.08.2026 trug dasselbe Produkt drei Beschreibungen. Der Banner sagte
„Briefe schreiben mit KI", der Auftrag „Normbriefe, nachgemessen", `pyproject`
„Geschaeftsbriefe nach DIN 5008 aus Markdown — mit nachgemessener Geometrie".
Keine war falsch, keine war die Quelle. Wer eine aenderte, aenderte die anderen
nicht mit, weil niemand wusste, dass es sie gibt.

Geprueft wird gegen `docs/marke/texte.yaml`. Jede Pruefung hier hat ihre
Gegenprobe: eine Pruefung, die nie rot werden kann, ist kein Nachweis.
"""

from __future__ import annotations

import re
import subprocess
import sys

import pytest
import yaml

from conftest import REPO

KANON_DATEI = REPO / "docs" / "marke" / "texte.yaml"
BANNER = REPO / "docs" / "marke" / "quelle" / "social-preview.html"
README = REPO / "README.md"
PYPROJECT = REPO / "pyproject.toml"

# Dieselbe Liste wie in test_textkanon.py, hier auf den Kanon selbst angewandt:
# was das Produkt nicht behaupten darf, darf auch der Kanon nicht anbieten.
VERBOTEN = re.compile(r"\b(normgerecht|DIN-konform|normkonform|zertifiziert)\w*", re.I)


@pytest.fixture(scope="module")
def kanon() -> dict:
    return yaml.safe_load(KANON_DATEI.read_text(encoding="utf-8"))


def flach(text: str) -> str:
    """Satzzeichen und Umbrueche raus — verglichen wird der Wortlaut, nicht die Typografie.

    Der Banner bricht den Claim mit <br> um, der Alt-Text der README setzt ein
    Komma, wo der Kanon einen Gedankenstrich hat. Beides ist in Ordnung; ein
    anderes Wort ist es nicht.
    """
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"[—–\-,.:;!?\"'„“]", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def html_text(klasse: str) -> str:
    roh = BANNER.read_text(encoding="utf-8")
    treffer = re.search(rf'class="{klasse}">(.*?)</div>', roh, re.S)
    assert treffer, f"Im Banner fehlt der Block .{klasse}"
    return treffer.group(1)


# ── Der Banner spricht den Kanon ────────────────────────────────────────────

def test_banner_traegt_den_claim(kanon):
    assert flach(kanon["claim"]["de"]) in flach(html_text("claim"))


def test_banner_traegt_den_untertitel(kanon):
    assert flach(kanon["untertitel"]["de"]) in flach(html_text("sub"))


def test_banner_traegt_den_zweitclaim(kanon):
    assert flach(kanon["claim"]["sekundaer"]) in flach(html_text("en"))


def test_banner_traegt_fusszeile_und_adresse(kanon):
    roh = flach(BANNER.read_text(encoding="utf-8"))
    assert flach(kanon["fusszeile"]) in roh
    assert flach(kanon["adresse"]) in roh


def test_die_bannerpruefung_wuerde_eine_abweichung_bemerken(kanon):
    """Gegenprobe: ein geaenderter Claim darf nicht mehr durchgehen."""
    verdreht = kanon["claim"]["de"].replace("Norm", "Gefuehl")
    assert flach(verdreht) not in flach(html_text("claim"))


# ── README und pyproject sprechen den Kanon ─────────────────────────────────

def test_readme_zeigt_den_claim_im_alternativtext(kanon):
    alt = re.search(r'<img[^>]*brand/banner\.png[^>]*alt="([^"]*)"', README.read_text(encoding="utf-8"))
    assert alt, "Im README-Kopf fehlt das Banner mit Alternativtext"
    assert flach(kanon["claim"]["de"]) in flach(alt.group(1))


def test_pyproject_summary_ist_der_kanon(kanon):
    treffer = re.search(r'^description\s*=\s*"(.*)"$', PYPROJECT.read_text(encoding="utf-8"), re.M)
    assert treffer, "pyproject.toml hat keine description"
    assert treffer.group(1) == kanon["github_beschreibung"]


def test_github_beschreibung_passt_in_das_feld(kanon):
    """GitHub schneidet ab 120 Zeichen ab."""
    assert len(kanon["github_beschreibung"]) <= 120


def test_github_beschreibung_nennt_die_pruefung_vor_dem_massenmerkmal(kanon):
    """Issue #204, wie schon #199/#205 fuer scripts/repo-einstellungen.sh:
    'DIN-5008-Briefe aus Markdown' gibt es laut Messung achtmal auf GitHub,
    das Nachmessen am fertigen PDF nirgends. Der Kanon muss deshalb mit der
    Pruefung beginnen, nicht mit dem, was es schon gibt."""
    beschreibung = kanon["github_beschreibung"]
    pos_pruefung = beschreibung.index("nachgemessen")
    pos_markdown = beschreibung.index("DIN-5008-Briefe aus Markdown")
    assert pos_pruefung < pos_markdown, beschreibung


def test_die_positionspruefung_wuerde_die_alte_reihenfolge_bemerken():
    """Gegenprobe: ohne sie belegt der Test oben nur, dass beide Woerter
    irgendwo im Satz stehen — nicht, dass die Reihenfolge wirklich geprueft
    wird."""
    alte_beschreibung = "DIN-5008-Briefe aus Markdown, am fertigen PDF nachgemessen. Sollwerte aus Sekundärquellen."
    pos_pruefung = alte_beschreibung.index("nachgemessen")
    pos_markdown = alte_beschreibung.index("DIN-5008-Briefe aus Markdown")
    assert pos_pruefung > pos_markdown


# ── Der Kanon behauptet nichts Unbelegtes ───────────────────────────────────

def alle_texte(wert) -> list[str]:
    """Alle Zeichenketten aus dem geladenen Kanon, rekursiv."""
    if isinstance(wert, str):
        return [wert]
    if isinstance(wert, dict):
        return [s for v in wert.values() for s in alle_texte(v)]
    if isinstance(wert, list):
        return [s for v in wert for s in alle_texte(v)]
    return []


def test_kanon_behauptet_keine_normkonformitaet(kanon):
    """Geprueft werden die Werte, nicht die Datei.

    Die YAML erklaert in einem Kommentar, welche Woerter verboten sind, und nennt
    sie dabei. Ein Kommentar ist Metatext und keine Behauptung des Produkts —
    wer die Rohdatei durchsucht, laesst genau die Erklaerung auffliegen, die vor
    dem Fehler warnt.
    """
    for text in alle_texte(kanon):
        assert not VERBOTEN.search(text), text


def test_die_wortpruefung_wuerde_anschlagen():
    """Gegenprobe zur Wortliste."""
    assert VERBOTEN.search("Diese Briefe sind DIN-konform gesetzt.")


def test_kanon_nennt_nur_befehle_die_es_gibt(kanon):
    """Der Kanon nennt nur Befehle mit ausdruecklicher Herkunft.

    Bis v0.7.2 lag der Grund darin, dass es `pipx install falzmarke` gar nicht
    gab. Seit v0.7.3 (26.08.2026) liegt das Paket auf PyPI, den Befehl gibt es
    also — der Kanon bleibt trotzdem beim `git+`-Weg: Er trifft auch den
    unveroeffentlichten Stand von `main` und ist im gerenderten Film verbaut.

    Dieselbe Falle, die test_installationswege.py fuer die README stellt, hier
    fuer den Kanon. Der Abbinder des Films zeigt seit dem dritten Schnitt keinen
    Befehl mehr — auf einer Endkarte ist ein `uvx --from git+https://…` weder
    lesbar noch merkbar. Der Eintrag bleibt trotzdem geprueft: Er speist
    kuenftige Verwendungen, und ein ungeprueftes Feld im Kanon ist eine Falle,
    die beim naechsten Gebrauch zuschnappt.
    """
    nackt = re.compile(r"(?<![\w./-])(?:uvx\s+falzmarke\b|pipx\s+install\s+falzmarke\b)")
    for zweck, befehl in kanon["installation"].items():
        assert not nackt.search(befehl), f"{zweck}: {befehl}"
        assert "git+https://" in befehl, f"{zweck} nennt keine Herkunft: {befehl}"


def test_die_befehlspruefung_wuerde_anschlagen():
    """Gegenprobe."""
    nackt = re.compile(r"(?<![\w./-])(?:uvx\s+falzmarke\b|pipx\s+install\s+falzmarke\b)")
    assert nackt.search("pipx install falzmarke")


# ── Der Claim, in zwei Stufen ───────────────────────────────────────────────

def test_claim_stufen_ergeben_wieder_den_claim(kanon):
    """Der Abbinder zeigt den Claim in zwei Stufen — abgeleitet, nicht gepflegt.

    Zwei von Hand gepflegte Fassungen desselben Satzes laufen auseinander, und
    zwar unbemerkt: Der Banner traegt dann den einen, der Film den anderen.
    scripts/texte.py trennt am Geviertstrich; hier wird gegengerechnet.
    """
    import sys as _sys
    _sys.path.insert(0, str(REPO / "scripts"))
    from texte import claim_stufen

    erste, zweite = claim_stufen(kanon["claim"]["de"])
    assert erste and zweite
    assert flach(f"{erste} — {zweite}") == flach(kanon["claim"]["de"])


def test_die_stufenpruefung_wuerde_eine_abweichung_bemerken():
    """Gegenprobe: ein Claim ohne Geviertstrich laesst sich nicht teilen."""
    import sys as _sys
    _sys.path.insert(0, str(REPO / "scripts"))
    from texte import claim_stufen

    with pytest.raises(SystemExit):
        claim_stufen("Ein Satz ohne Trennzeichen")


# ── Zeitleiste des Films ────────────────────────────────────────────────────

def test_szenen_decken_die_laufzeit_lueckenlos(kanon):
    szenen = kanon["film"]["szenen"]
    assert szenen[0]["von"] == 0
    assert szenen[-1]["bis"] == kanon["film"]["dauer"]
    for vorher, nachher in zip(szenen, szenen[1:]):
        assert vorher["bis"] == nachher["von"], f"Luecke nach Szene {vorher['name']}"


def test_jede_szene_steht_lang_genug_zum_lesen(kanon):
    """Unter 2,5 Sekunden liest niemand eine Zeile zu Ende."""
    for szene in kanon["film"]["szenen"]:
        assert szene["bis"] - szene["von"] >= 2.5, szene["name"]


# ── Die Ausgaben sind am Stand der Quelle ───────────────────────────────────

def test_erzeugte_dateien_sind_aktuell():
    """docs/marke/texte.md und texte.json muessen zur YAML passen."""
    ergebnis = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "texte.py"), "--pruefen"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
