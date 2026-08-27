"""Gegenprobe: Ein Prüfmittel, das nie rot werden kann, ist kein Nachweis.

Jeder Test hier sabotiert das Layout an genau einer Stelle und verlangt, dass
die zugehörige Prüfung anschlägt — und nur sie. Ohne diese Datei wüsste die
Testsuite nur, dass sie grün ist, nicht dass sie misst.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from falzmarke import geometrie
from falzmarke import cli as falzmarke
from conftest import REPO

BEISPIEL = REPO / "examples" / "brief-form-b.md"


def _sabotiere(tmp_path: Path, datei: str, alt: str, neu: str) -> Path:
    """Legt eine Kopie des typst-Verzeichnisses an und ändert dort eine Stelle."""
    ziel = tmp_path / "typst"
    shutil.copytree(REPO / "skill" / "falzmarke" / "typst", ziel)
    pfad = ziel / datei
    inhalt = pfad.read_text(encoding="utf-8")
    assert alt in inhalt, f"Ankertext nicht gefunden in {datei}: {alt!r}"
    pfad.write_text(inhalt.replace(alt, neu, 1), encoding="utf-8")
    return ziel


def _rendere_mit(tmp_path: Path, typst_dir: Path) -> tuple[Path, str]:
    original = falzmarke.TYPST_DIR
    falzmarke.TYPST_DIR = typst_dir
    try:
        return falzmarke.rendere(BEISPIEL, tmp_path / "sabotiert.pdf",
                                 profil_verzeichnis=typst_dir / "profiles")
    finally:
        falzmarke.TYPST_DIR = original


def _gescheitert(pdf: Path, form: str) -> set[str]:
    bericht = geometrie.pruefe(pdf, form)
    return {p.name for p in bericht.pruefungen if not p.bestanden}


def test_unveraendert_ist_gruen(tmp_path):
    """Kontrollprobe: ohne Sabotage darf nichts anschlagen. Sonst misst die
    Sabotage nur die Kopie, nicht die Verschiebung."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let zeile = 4.2333mm",
                       "#let zeile = 4.2333mm  // unveraendert")
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert _gescheitert(pdf, form) == set()


def test_verschobene_falzmarke_faellt_auf(tmp_path):
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ",
        "folding-mark-1-pos: 105mm", "folding-mark-1-pos: 112mm",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Falzmarke 1, y" in _gescheitert(pdf, form)


def test_verschobene_lochmarke_faellt_auf(tmp_path):
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ", "dy: 148.5mm", "dy: 152mm",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Lochmarke, y" in _gescheitert(pdf, form)


def test_zu_tiefer_betreff_faellt_auf(tmp_path):
    """Der teure Fehler: der Betreff rutscht in den Text."""
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ", "let soll = unterkante + 2 * zeile",
        "let soll = unterkante + 3 * zeile",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Betreff, y-Oberkante" in _gescheitert(pdf, form)


def test_verschobene_anschrift_faellt_auf(tmp_path):
    """Ein um 10 mm verschobenes Anschriftfeld ist im Fensterumschlag nicht
    mehr lesbar — das muss die Messung fangen."""
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ",
        "#let recipient-box(content) = {\n  set text(size: 10pt)\n  set align(top)\n  \n  pad(left: 5mm, content)",
        "#let recipient-box(content) = {\n  set text(size: 10pt)\n  set align(top)\n  \n  pad(left: 15mm, content)",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Anschrift, x-links" in _gescheitert(pdf, form)


def test_zu_kleiner_unterrand_faellt_auf(tmp_path):
    """Die vierzeilige Fußzeile lief beim 20-mm-Standardrand aus dem Blatt."""
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        'profil.at("rand_unten_mm", default: 42)', "20",
    )
    original = falzmarke.baue_profil_daten

    def ohne_randberechnung(profil, pfad, arbeit):
        daten = original(profil, pfad, arbeit)
        daten.pop("rand_unten_mm", None)
        return daten

    falzmarke.baue_profil_daten = ohne_randberechnung
    try:
        pdf, form = _rendere_mit(tmp_path, kopie)
    finally:
        falzmarke.baue_profil_daten = original
    assert "Unterster Text, Abstand zur Blattkante" in _gescheitert(pdf, form)


def test_verschobener_infoblock_faellt_auf(tmp_path):
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ",
        "pad(top: 5mm, information-box)", "pad(top: 12mm, information-box)",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Infoblock, y-Oberkante" in _gescheitert(pdf, form)


def test_bild_ohne_alternativtext_wird_von_pdfua_abgelehnt(tmp_path):
    """Ein Logo im Briefkopf ist für PDF/UA-1 nur zulässig, wenn es beschrieben
    ist. Ohne den alt-Text bricht Typst den Satz ab — genau das soll er.

    Anlass: Beim Aktivieren des Beispielprofils mit Logo scheiterte `--pdfua`
    mit 'missing alt text'. Ohne diesen Test wüsste die Suite nur, dass der
    alt-Text heute dasteht, nicht dass er gebraucht wird.
    """
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        'alt: k.at("logo_alt", default: profil.absender.name),', "",
    )
    original = falzmarke.TYPST_DIR
    falzmarke.TYPST_DIR = kopie
    try:
        with pytest.raises(falzmarke.Eingabefehler) as fehler:
            falzmarke.rendere(BEISPIEL, tmp_path / "ohne-alt.pdf",
                              profil_verzeichnis=kopie / "profiles", pdfua=True)
    finally:
        falzmarke.TYPST_DIR = original
    assert "alt text" in str(fehler.value).lower(), (
        f"Erwartet wurde eine PDF/UA-Beschwerde über den fehlenden alt-Text, "
        f"bekommen: {fehler.value}"
    )


# ── Die Grenze des HTML-Emitters (ADR 0034, Punkt 4) ────────────────────────
#
# Die Sabotagen hier setzen nicht am fertigen Text an, sondern am Emitter: Sie
# lassen ihn erzeugen, was er nicht erzeugen darf. Ein Detektor, der nur gegen
# handgeschriebene Beispielzeichenketten geprüft wird, belegt nicht, dass er
# eine echte Ausgabe des Werkzeugs beanstanden würde.

from falzmarke import emit_html as _html                       # noqa: E402
from falzmarke import markdown as _md                          # noqa: E402


def _seite_mit_sabotiertem_emitter(monkeypatch, name, ersatz) -> str:
    """Ersetzt eine Funktion des Emitters und lässt ihn einen Brief setzen."""
    quelle = BEISPIEL.read_text(encoding="utf-8").split("---", 2)[2]
    vorher = _html.dokument(_html.setze(_md.lies(quelle)))
    monkeypatch.setattr(_html, name, ersatz)
    nachher = _html.dokument(_html.setze(_md.lies(quelle)))
    assert nachher != vorher, (
        f"Die Sabotage an {name} hat die Ausgabe nicht verändert — "
        "ein grünes Ergebnis würde hier nichts belegen"
    )
    return nachher


def test_unsabotierter_emitter_ist_gruen():
    """Kontrollprobe. Ohne sie misst die Sabotage nur die Kopie."""
    quelle = BEISPIEL.read_text(encoding="utf-8").split("---", 2)[2]
    seite = _html.dokument(_html.setze(_md.lies(quelle)))
    assert _html.verstoesse(seite) == []


def test_externes_stylesheet_faellt_auf(monkeypatch):
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f'<link rel="stylesheet" href="https://example.invalid/mail.css"><p>{inhalt}</p>',
    )
    assert "externes Stylesheet oder externe Ressource" in _html.verstoesse(seite)


def test_zaehlpixel_faellt_auf(monkeypatch):
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f'<p>{inhalt}</p><img src="https://example.invalid/p.gif" alt="" width="1" height="1">',
    )
    verstoesse = _html.verstoesse(seite)
    assert any("Zählpixel" in v for v in verstoesse), verstoesse


def test_bild_ohne_alternativtext_faellt_auf(monkeypatch):
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f'<p>{inhalt}</p><img src="cid:logo">',
    )
    assert "Bild ohne Alternativtext" in _html.verstoesse(seite)


def test_style_block_faellt_auf(monkeypatch):
    """Der naheliegendste Rückfall beim Erweitern: den Stil aus den Elementen
    in einen `<style>`-Block ziehen, weil das HTML kürzer wird. Gmail entfernt
    ihn, und die Mail käme unformatiert an."""
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f"<style>p {{ color: #000 }}</style><p>{inhalt}</p>",
    )
    assert "Style-Block statt Inline-Stil" in _html.verstoesse(seite)
