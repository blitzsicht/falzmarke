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

from markdown_it import MarkdownIt

from conftest import REPO

README = REPO / "README.md"
BASIS = "https://github.com/blitzsicht/falzmarke"
BILDENDUNGEN = (".png", ".gif", ".jpg", ".jpeg", ".svg", ".webp")

# Ziele ohne Protokoll, Anker oder mailto — also genau die, die auf PyPI ins Leere zeigen.
OHNE_HERKUNFT = re.compile(r"(?!https?:|#|mailto:)", re.IGNORECASE)
#: `src=` und `href=` in HTML — in doppelten, einfachen oder ohne Anführungszeichen,
#: wie ein Browser sie liest (Nachreview von #484: bis dahin nur doppelte).
HTML_ZIEL = re.compile(r"""(?:src|href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""",
                       re.IGNORECASE)
ABSOLUT = re.compile(rf'{re.escape(BASIS)}/(raw|blob|tree)/main/([^")\s#]+)')


def _text() -> str:
    return README.read_text(encoding="utf-8")


def html_ziele(html: str) -> list[str]:
    """Jedes `src`- und `href`-Ziel in einem Stück HTML."""
    return [next(ziel for ziel in treffer.groups() if ziel is not None)
            for treffer in HTML_ZIEL.finditer(html)]


def verweisziele(text: str) -> list[str]:
    """Jedes Ziel, das ein Markdown-Leser als Link oder Bild rendert.

    Gelesen wird wie auf PyPI, über einen CommonMark-Parser, nicht über eine
    Textsuche. Bis #480 suchte hier eine Regex nach `](ziel)` im ganzen Text,
    auch im Code. `scripts/changelog.py` muss Code aber wörtlich lassen, und
    `` `[Text](url)` `` ist auf PyPI kein Verweis. Die Ausklammerung steht
    absichtlich nicht ein zweites Mal hier: Erkennt `changelog.py` Code, wo
    keiner ist, bleibt ein echter Verweis relativ, und der Parser findet ihn.
    """
    ziele: list[str] = []

    def sammeln(marken) -> None:
        for marke in marken:
            if marke.type == "link_open":
                ziele.append(marke.attrGet("href"))
            elif marke.type == "image":
                ziele.append(marke.attrGet("src"))
            elif marke.type in ("html_block", "html_inline"):
                ziele.extend(html_ziele(marke.content))
            if marke.children:
                sammeln(marke.children)

    sammeln(MarkdownIt("commonmark").enable("table").parse(text))
    return ziele


def relative_ziele(text: str) -> list[str]:
    return [ziel for ziel in verweisziele(text) if OHNE_HERKUNFT.match(ziel)]


def test_keine_relativen_verweise():
    """Jeder relative Verweis ist auf PyPI ein toter Link oder ein kaputtes Bild."""
    treffer = relative_ziele(_text())
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
    ein Rückfall auffiele. Geprüft wird an `relative_ziele` selbst, mit beiden
    Richtungen an einem Beispiel, das dem echten Fall entspricht.
    """
    rueckfall = '<img src="docs/assets/brand/banner.png" alt="x">'
    assert relative_ziele(rueckfall), "die Prüfung würde einen Rückfall nicht bemerken"

    repariert = f'<img src="{BASIS}/raw/main/docs/assets/brand/banner.png" alt="x">'
    assert not relative_ziele(repariert)

    # und die Markdown-Form, die 41 der 43 Fälle ausmachte
    assert relative_ziele("[Bild](docs/renders/demo.gif)")
    assert not relative_ziele(f"[Bild]({BASIS}/raw/main/docs/renders/demo.gif)")

    # ein Verweis über eine Definition: die alte Textsuche sah ihn nie
    assert relative_ziele("Siehe [ADR][a].\n\n[a]: docs/entscheidungen/0001.md\n")

    # einfache Anführungszeichen und ein groß geschriebenes Protokoll (Nachreview von #484)
    assert relative_ziele("<img src='docs/x.png'>") == ["docs/x.png"], \
        "ein Ziel in einfachen Anführungszeichen wurde nicht gesehen"
    assert not relative_ziele("[A](HTTPS://example.org/a)"), \
        "ein groß geschriebenes Protokoll gilt als relativ"


def test_code_ist_kein_verweis():
    """`` `[Text](url)` `` rendert auf PyPI als Code, nicht als Link (#480).

    Die Textsuche vor #480 meldete das als relativen Verweis. Hätte
    `scripts/changelog.py` Code wörtlich gelassen, wäre der nächste Release-PR an
    dieser Prüfung rot geworden statt an `test_kein_punkt_faellt_unter_den_tisch`.
    Derselbe Absatz trägt einen echten Verweis: Er wird weiter gemeldet.
    """
    absatz = (
        "Die Schreibweise `[Text](url)` und ``[a](b)`` bleiben Code, "
        "[ADR](docs/x.md) ist ein Verweis.\n\n"
        "```md\n[Bild](docs/renders/demo.gif)\n```\n"
    )
    treffer = relative_ziele(absatz)
    assert treffer == ["docs/x.md"], f"als relativer Verweis gemeldet: {treffer}"
