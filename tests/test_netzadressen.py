"""Eine Mail-Adresse, Domain oder URL wird im Brief nicht getrennt.

Anlass, an versendeten Briefen beobachtet:

- 14.10.2026: „servus@blitzsicht.com“ stand als „ser-“ am Zeilenende und
  „vus@blitzsicht.com“ in der nächsten Zeile.
- 14.10.2026: „blitzsicht.com/da-“ / „tenschutz“ — eine URL mit Pfad.
- 17.10.2026: wieder „ser-vus@…“ und „daten-schutz“ in einer URL.

`verify` meldete jedes Mal grün: Alle Maße stimmten. Diese Datei hält fest,
dass der Emitter jedes Wort mit Adresse unteilbar setzt
(`emit.as_text`, `netzadressen.zerlege`), dass normaler Text weiter getrennt
wird, und dass `verify` eine getrennte Adresse im fertigen PDF findet
(`netzadressen.getrennt`, Prüfung „Netzadressen ungetrennt“).

Der Satz wird an `tests/fixtures/trennung/adressen.md` gemessen, und zwar
zweimal: mit dem Schutz und ohne. Ohne Schutz müssen alle vier Adressen
getrennt sein — sonst belegte das grüne Ergebnis mit Schutz nur, dass die
Adressen zufällig nicht am Zeilenende stehen. Die Sabotage für `verify` steht
in `tests/test_gegenbeweis.py`.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytest

from falzmarke import cli, emit, geometrie, netzadressen
from conftest import REPO, URKUNDE_BEISPIELE

QUELLE = REPO / "tests" / "fixtures" / "trennung" / "adressen.md"

#: Was in der Quelle steht und im PDF in EINER Zeile stehen muss.
ADRESSEN = (
    "servus@blitzsicht.com",               # Mail-Adresse
    "blitzsicht.com/datenschutz",          # Domain mit Pfad
    "https://blitzsicht.com/datenschutz",  # URL mit Schema
    "muster-sanierungen.de",               # Domain mit eigenem Bindestrich
)

PRUEFUNG = "Netzadressen ungetrennt"


def _zeilen(pdf: Path) -> list[list[str]]:
    """Je Seite die Textzeilen, so wie pdfplumber sie liest."""
    with pdfplumber.open(str(pdf)) as dokument:
        return [(seite.extract_text() or "").splitlines() for seite in dokument.pages]


def _ohne_schutz(text: str) -> list[tuple[str, bool]]:
    """Der Stand vor dem Fix: kein Wort gilt als Adresse."""
    return [(text, False)]


@pytest.fixture(scope="module")
def gesetzt(tmp_path_factory) -> dict[str, Path]:
    """Die Probe einmal mit und einmal ohne Schutz gesetzt."""
    ziel = tmp_path_factory.mktemp("netzadressen")
    mit, _ = cli.rendere(QUELLE, ziel / "mit.pdf")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(netzadressen, "zerlege", _ohne_schutz)
        ohne, _ = cli.rendere(QUELLE, ziel / "ohne.pdf")
    return {"mit": mit, "ohne": ohne}


# ── Die Probe trennt ohne Schutz wirklich ───────────────────────────────────

def test_ohne_schutz_ist_jede_adresse_getrennt(gesetzt):
    """Gegenprobe zur Probe: Sie reproduziert alle vier Fälle.

    Mail-Adresse und URL-Pfad per Silbentrennung, die URL mit Schema ohne
    Strich am Punkt, die Domain an ihrem eigenen Bindestrich.
    """
    befunde = [t for seite in _zeilen(gesetzt["ohne"]) for t in netzadressen.getrennt(seite)]
    gefunden = {(t.ende, t.anfang, t.art) for t in befunde}
    assert gefunden == {
        ("ser-", "vus@blitzsicht.com", "trennstrich"),
        ("blitzsicht.com/daten-", "schutz", "trennstrich"),
        ("https://blitzsicht.", "com/datenschutz.", "umbruch"),
        ("muster-", "sanierungen.de", "trennstrich"),
    }, befunde


def test_ohne_schutz_meldet_verify_die_trennung(gesetzt):
    bericht = geometrie.pruefe(gesetzt["ohne"], "B")
    pruefung = next(p for p in bericht.pruefungen if p.name == PRUEFUNG)
    assert not pruefung.bestanden
    assert "ser- ⏎ vus@blitzsicht.com" in pruefung.ist
    assert "(+3 weitere)" in pruefung.ist
    assert not bericht.ok


# ── Mit Schutz: keine Adresse getrennt, normaler Text schon ─────────────────

def test_mit_schutz_ist_keine_adresse_getrennt(gesetzt):
    befunde = [t for seite in _zeilen(gesetzt["mit"]) for t in netzadressen.getrennt(seite)]
    assert befunde == []


@pytest.mark.parametrize("adresse", ADRESSEN)
def test_mit_schutz_steht_jede_adresse_in_einer_zeile(gesetzt, adresse):
    """Nicht nur „kein Befund“: Jede Adresse steht ganz in einer Zeile, so oft wie in der Quelle."""
    zeilen = [z for seite in _zeilen(gesetzt["mit"]) for z in seite]
    quelle = QUELLE.read_text(encoding="utf-8").split("\n---\n", 1)[1]
    erwartet = quelle.count(adresse)
    assert erwartet > 0
    assert sum(z.count(adresse) for z in zeilen) == erwartet


def test_mit_schutz_wird_normaler_text_weiter_getrennt(gesetzt):
    """Der Schutz gilt der Adresse, nicht dem Absatz: „Daten-“ / „schutz“ bleibt."""
    for seite in _zeilen(gesetzt["mit"]):
        for oben, unten in zip(seite, seite[1:]):
            if oben.endswith("im Daten-") and unten.startswith("schutz unter"):
                return
    pytest.fail("Das Wort „Datenschutz“ im Fließtext ist nicht mehr getrennt — "
                "der Schutz greift über die Adresse hinaus.")


def test_mit_schutz_besteht_verify(gesetzt):
    bericht = geometrie.pruefe(gesetzt["mit"], "B")
    pruefung = next(p for p in bericht.pruefungen if p.name == PRUEFUNG)
    assert pruefung.bestanden, pruefung
    assert pruefung.ist == "keine"
    assert bericht.ok, [p for p in bericht.pruefungen if not p.bestanden]


def test_die_urkunde_misst_dasselbe():
    """Auch die Urkunde setzt ihren Text über `emit` — sie wird ebenso gemessen."""
    assert URKUNDE_BEISPIELE
    pdf, _ = cli.rendere(URKUNDE_BEISPIELE[0], None)
    namen = {p.name for p in geometrie.pruefe(pdf, "").pruefungen}
    assert PRUEFUNG in namen


# ── Der Emitter ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("wort", [
    "servus@blitzsicht.com",
    "blitzsicht.com",
    "muster-sanierungen.de",
    "blitzsicht.com/datenschutz",
    "https://blitzsicht.com/datenschutz",
    "www.example.de",
    "bäckerei-zink.de",
])
def test_ein_wort_mit_adresse_ist_unteilbar(wort):
    assert emit.as_text(f"Bitte an {wort} schreiben.") == (
        f'#text("Bitte an ")#box(text(hyphenate: false, "{wort}"))#text(" schreiben.")')


def test_satzzeichen_bleiben_an_der_adresse():
    """Ein Komma oder eine Klammer darf nicht allein am nächsten Zeilenanfang stehen."""
    assert emit.as_text("(servus@blitzsicht.com), danach") == (
        '#box(text(hyphenate: false, "(servus@blitzsicht.com),"))#text(" danach")')


@pytest.mark.parametrize("text", [
    "Fragen gern an mich.",
    "z. B. 5 kg, Nr. 3.5 und u. a. m.",
    "Ende.Die nächste Zeile",          # fehlender Leerschritt, keine Domain
    "Version 1.2.3 und 3.14 Euro",
    "",
])
def test_text_ohne_adresse_wird_gesetzt_wie_bisher(text):
    """Byte für Byte die Ausgabe von vorher: ein einziges `#text(…)`."""
    assert emit.as_text(text, typografie_anwenden=False) == f"#text({emit.zeichenkette(text)})"


def test_eine_ueberlange_adresse_bekommt_nur_keine_silbentrennung():
    """Als Box ragte sie über den Satzspiegel.

    Ohne Box darf Typst sie umbrechen, aber nicht mit Trennstrich trennen.
    """
    lang = "https://example.de/" + "a" * netzadressen.UNTEILBAR_BIS
    gesetzt = emit.as_text(f"Siehe {lang} dort")
    assert f'#text(hyphenate: false, "{lang}")' in gesetzt
    assert "#box(" not in gesetzt
    grenze = "https://example.de/" + "a" * (netzadressen.UNTEILBAR_BIS - len("https://example.de/"))
    assert len(grenze) == netzadressen.UNTEILBAR_BIS
    assert f'#box(text(hyphenate: false, "{grenze}"))' in emit.as_text(f"Siehe {grenze} dort")


def test_die_typografie_laeuft_weiter_ueber_den_ganzen_text():
    """Anführungszeichen um eine Adresse werden als Paar erkannt und mit ihr zusammengehalten."""
    assert emit.as_text('Siehe "blitzsicht.com" dort') == (
        '#text("Siehe ")#box(text(hyphenate: false, "„blitzsicht.com“"))#text(" dort")')


# ── Die Erkennung ───────────────────────────────────────────────────────────

def test_zerlege_haelt_den_text_vollstaendig():
    text = "Fragen an servus@blitzsicht.com, oder (blitzsicht.com/datenschutz). Danke"
    teile = netzadressen.zerlege(text)
    assert "".join(t for t, _ in teile) == text
    assert [t for t, adresse in teile if adresse] == [
        "servus@blitzsicht.com,", "(blitzsicht.com/datenschutz)."]


@pytest.mark.parametrize("zeilen, erwartet", [
    # Die beobachteten Fälle, einmal wie pdftotext sie liest (weiches
    # Trennzeichen), einmal wie pdfplumber (Bindestrich).
    (["unter ser­", "vus@blitzsicht.com oder"], "trennstrich"),
    (["unter ser-", "vus@blitzsicht.com oder"], "trennstrich"),
    (["unter blitzsicht.com/da-", "tenschutz und"], "trennstrich"),
    (["auf https://blitzsicht.", "com/datenschutz."], "umbruch"),
    (["auf https://", "blitzsicht.com/datenschutz."], "umbruch"),
    (["an servus@blitzsicht.", "com schreiben"], "umbruch"),
    (["mehr unter muster-", "sanierungen.de und"], "trennstrich"),
    (["an info@muster-", "sanierungen.de schreiben"], "trennstrich"),
])
def test_eine_getrennte_adresse_wird_gefunden(zeilen, erwartet):
    befunde = netzadressen.getrennt(zeilen)
    assert [t.art for t in befunde] == [erwartet]
    assert befunde[0].zeile == 0


@pytest.mark.parametrize("zeilen", [
    ["die Neuge-", "staltung Ihrer Seite"],              # normale Silbentrennung
    ["Fragen gern unter", "servus@blitzsicht.com oder"],  # Umbruch VOR der Adresse
    ["unter servus@blitzsicht.com", "oder telefonisch"],  # Umbruch NACH der Adresse
    ["Siehe https://blitzsicht.com.", "Die Seite"],       # ganze URL, Satzende
    ["Siehe https://blitzsicht.com/", "finden Sie"],      # ganze URL mit Schrägstrich
    ["das ist z. B.", "die Frage"],
    ["ca.", "drei Wochen"],
    ["und/", "oder"],
    ["die E-Mail-", "Adresse"],
    ["Ihre Website -", "servus@blitzsicht.com"],          # Strich als Gedankenstrich
    ["", "servus@blitzsicht.com"],
])
def test_richtig_umbrochener_text_ist_kein_befund(zeilen):
    assert netzadressen.getrennt(zeilen) == []
