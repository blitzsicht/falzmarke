"""Das README ist die Projektseite auf PyPI — und dort gibt es kein Repository.

WARUM DAS EIN EIGENER TEST IST

`pyproject.toml` bindet die README als Langbeschreibung ein. Auf PyPI wird sie
gerendert, aber **relative Pfade lösen dort nicht auf**: `docs/assets/…` zeigt
ins Leere, weil es kein umgebendes Repository gibt. Vor dieser Prüfung standen
43 solche Verweise darin, darunter der Banner in Zeile 3 — ein kaputtes Bild als
erster Eindruck der Projektseite.

`twine check` fängt das **nicht**. Es prüft, ob die Beschreibung *rendert*, nicht
ob die Ziele *existieren*; es meldete für genau diesen Stand PASSED. Ein grüner
Check, der die Sache nicht berührt.

Das wiegt schwerer als ein gewöhnlicher Doku-Fehler: Die Projektseite einer
veröffentlichten Version lässt sich nicht ändern, ohne eine neue Version zu
veröffentlichen. Was beim ersten Upload falsch ist, bleibt für diese Version
falsch.
"""

from __future__ import annotations

import re

from conftest import REPO

README = REPO / "README.md"
BASIS = "https://github.com/blitzsicht/falzmarke"
BILDENDUNGEN = (".png", ".gif", ".jpg", ".jpeg", ".svg", ".webp")

# `](ziel)` und `src="ziel"`, ohne Protokoll, Anker oder mailto — also genau die
# Formen, die auf PyPI ins Leere zeigen.
RELATIV = re.compile(r'\]\((?!https?:|#|mailto:)([^)]+)\)|src="(?!https?:|#)([^"]+)"')
ABSOLUT = re.compile(rf'{re.escape(BASIS)}/(raw|blob|tree)/main/([^")\s#]+)')


def _text() -> str:
    return README.read_text(encoding="utf-8")


def test_keine_relativen_verweise():
    """Jeder relative Verweis ist auf PyPI ein toter Link oder ein kaputtes Bild."""
    treffer = [m.group(1) or m.group(2) for m in RELATIV.finditer(_text())]
    assert not treffer, (
        f"{len(treffer)} relative Verweise im README. Auf PyPI zeigen sie ins Leere: {treffer[:5]}"
    )


def test_alle_ziele_existieren_im_baum():
    """Ein absoluter Link auf eine gelöschte Datei ist genauso tot, nur unauffälliger.

    Geprüft wird gegen den Arbeitsbaum: Was hier fehlt, fehlt auch auf `main`.
    """
    ziele = {ziel for _, ziel in ABSOLUT.findall(_text())}
    fehlend = sorted(z for z in ziele if not (REPO / z).exists())
    assert not fehlend, f"README verlinkt Dateien, die es nicht gibt: {fehlend}"


def test_bilder_ueber_raw_dokumente_ueber_blob():
    """`/blob/` liefert bei einem Bild die HTML-Seite, nicht die Datei.

    Auf GitHub sieht man den Unterschied nicht — dort rendert die Seite das Bild.
    Auf PyPI schon: Dort landet ein `<img>` auf einer HTML-Seite und bleibt leer.
    """
    falsch = []
    for art, ziel in ABSOLUT.findall(_text()):
        ist_bild = ziel.lower().endswith(BILDENDUNGEN)
        if ist_bild and art != "raw":
            falsch.append(f"{ziel} steht unter /{art}/, Bilder brauchen /raw/")
        if not ist_bild and art == "raw":
            falsch.append(f"{ziel} steht unter /raw/, das ist für Bilder")
    assert not falsch, falsch


def test_der_banner_ganz_oben_ist_absolut():
    """Der erste Eindruck der Projektseite, einzeln geprüft.

    Er stand als einziger als HTML-`src` da und wäre einer Regex entgangen, die
    nur Markdown-Verweise kennt.
    """
    kopf = "\n".join(_text().splitlines()[:12])
    treffer = re.search(r'src="([^"]+banner[^"]*)"', kopf)
    assert treffer, "im README-Kopf steht kein Banner mehr"
    assert treffer.group(1).startswith(f"{BASIS}/raw/main/"), treffer.group(1)


def test_gegenprobe_die_pruefung_faengt_einen_relativen_verweis():
    """Belegt, dass die Prüfung oben trennt, statt nur zu laufen.

    Ohne das wüsste die Suite nur, dass das README heute sauber ist — nicht, dass
    ein Rückfall auffiele. Geprüft wird an der Regex selbst, mit beiden
    Richtungen an einem Beispiel, das dem echten Fall entspricht.
    """
    rueckfall = '<img src="docs/assets/brand/banner.png" alt="x">'
    assert RELATIV.search(rueckfall), "die Prüfung würde einen Rückfall nicht bemerken"

    repariert = f'<img src="{BASIS}/raw/main/docs/assets/brand/banner.png" alt="x">'
    assert not RELATIV.search(repariert)

    # und die Markdown-Form, die 41 der 43 Fälle ausmachte
    assert RELATIV.search("[Bild](docs/renders/demo.gif)")
    assert not RELATIV.search(f"[Bild]({BASIS}/raw/main/docs/renders/demo.gif)")
