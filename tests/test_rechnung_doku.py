"""Issue #120: Was falzmarke bei Rechnungen behauptet — und was nicht.

`docs/rechnung.md` gibt es noch nicht. Diese Datei prüft die vier Akzeptanzkriterien aus
`.agent/task.md`:

1. `docs/rechnung.md` steht und ist von der README aus erreichbar.
2. Der Unterschied zwischen ZUGFeRD und XRechnung steht in einem Satz.
3. Die PDF/A-Aussage im README ist eine zutreffende Fallunterscheidung (ADR 0033:
   A-2b im Normalfall, A-3b wenn eingebettet wird), keine pauschale Zusage.
4. Der Textkanon hält — dafür ist `docs/rechnung.md` in
   `tests/test_textkanon.py::test_keine_ungedeckte_konformitaetsbehauptung` aufgenommen.

Dazu die Inhalte, die laut Vorgang ausdrücklich in `docs/rechnung.md` stehen sollen: welche
Formatfassung und welches Profil erzeugt werden, dass ein fremdes Prüfwerkzeug mit welcher
Regelfassung prüft, dass falzmarke keine Rechnungsnummern vergibt/bucht/mahnt/versendet, und ob
das Werkzeug rechnet oder nur überträgt (ADR 0039, ADR 0040).
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO

RECHNUNG_MD = REPO / "docs" / "rechnung.md"
README = REPO / "README.md"
SKILL_MD = REPO / "skill" / "SKILL.md"


def _fliesstext(pfad) -> str:
    """Wie in test_textkanon.py: Markdown bricht Zeilen frei um — für die Suche ist
    der Umbruch ein Leerzeichen."""
    roh = pfad.read_text(encoding="utf-8")
    return re.sub(r"\s*\n>?\s*", " ", roh)


def _saetze(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


# ── AC 1: docs/rechnung.md steht und ist von der README aus erreichbar ─────

def test_docs_rechnung_md_existiert():
    assert RECHNUNG_MD.exists(), (
        "docs/rechnung.md fehlt — die Seite, die erklärt, was falzmarke bei Rechnungen "
        "tut und was nicht (Issue #120)")


def test_die_readme_verlinkt_docs_rechnung_md():
    """Wie bei docs/email.md steht der Verweis als volle GitHub-URL — relative Pfade
    zeigen auf PyPI ins Leere (test_readme_auf_pypi.py)."""
    text = README.read_text(encoding="utf-8")
    assert "https://github.com/blitzsicht/falzmarke/blob/main/docs/rechnung.md" in text, (
        "README verweist nicht auf docs/rechnung.md — ohne Verlinkung ist die Seite "
        "nicht von dort aus erreichbar")


# ── AC 2: der Unterschied zwischen ZUGFeRD und XRechnung in einem Satz ──────
#
# Beide Begriffe irgendwo im Dokument zu nennen reicht nicht — die AC verlangt einen
# Satz, der sie *unterscheidet*. Das Unterscheidende ist gemessen (ADR 0039, ADR 0040):
# ZUGFeRD ist ein PDF mit eingebetteter XML für Firmen, XRechnung ist reine XML für
# öffentliche Auftraggeber. Ein Satz, der alle vier Begriffe trägt, hält beides
# auseinander; einer, der nur die beiden Formatnamen nennt, könnte auch nur eine
# Aufzählung sein.

def _unterscheidender_satz(text: str) -> str | None:
    for satz in _saetze(text):
        if all(begriff in satz for begriff in ("ZUGFeRD", "XRechnung", "PDF", "XML")):
            return satz
    return None


@pytest.mark.parametrize("pfad", [README, SKILL_MD], ids=["README.md", "skill/SKILL.md"])
def test_ein_satz_haelt_zugferd_und_xrechnung_auseinander(pfad):
    assert pfad.exists()
    satz = _unterscheidender_satz(_fliesstext(pfad))
    assert satz, (
        f"{pfad.relative_to(REPO)}: kein Satz nennt ZUGFeRD, XRechnung, PDF und XML "
        "zusammen — der Unterschied zwischen den Formaten bleibt unbenannt (Issue #120)")


def test_gegenprobe_beide_woerter_getrennt_zaehlen_nicht_als_unterscheidung():
    """Ohne diese Gegenprobe misst der Test oben nur, ob beide Wörter irgendwo im
    Dokument stehen — nicht, ob ein Satz sie tatsächlich unterscheidet."""
    text = "falzmarke kennt XRechnung. Es kennt auch ZUGFeRD. Beides sind Formate."
    assert _unterscheidender_satz(text) is None


def test_gegenprobe_ein_satz_mit_allen_vier_begriffen_zaehlt_sehr_wohl():
    text = ("An Behörden geht die XRechnung als reine XML, an Firmen reicht ZUGFeRD "
            "als PDF mit eingebetteter XML.")
    assert _unterscheidender_satz(text) is not None


# ── AC 3: die PDF/A-Aussage im README ist eine Fallunterscheidung ──────────
#
# ADR 0033: A-2b bleibt der Normalfall, A-3b wird gewählt, wenn eingebettet wird.
# "Der Satz im README wird dadurch länger" (task.md) — die zwei Stufen gehören also in
# denselben Satz, nicht irgendwo verteilt ins Dokument.

def _fallunterscheidung_satz(text: str) -> str | None:
    for satz in _saetze(text):
        if "PDF/A-2b" in satz and "PDF/A-3b" in satz:
            return satz
    return None


def test_readme_nennt_beide_pdfa_stufen():
    text = _fliesstext(README)
    assert "PDF/A-2b" in text and "PDF/A-3b" in text, (
        "README nennt nicht beide PDF/A-Stufen — die Aussage bleibt eine pauschale "
        "Zusage statt der Fallunterscheidung aus ADR 0033 (Issue #120)")


def test_readme_pdfa_aussage_ist_eine_fallunterscheidung():
    satz = _fallunterscheidung_satz(_fliesstext(README))
    assert satz, (
        "README: kein Satz nennt A-2b und A-3b zusammen — ohne das ist es keine "
        "erkennbare Fallunterscheidung, sondern zwei getrennte Erwähnungen")


def test_gegenprobe_die_heutige_pauschale_zusage_faellt_durch():
    """Der Ist-Zustand von README.md, Zeile 126 (vor #120): eine Zusage ohne
    Fallunterscheidung. Die Prüfung muss das erkennen, sonst misst sie nichts."""
    pauschal = "PDF/A-2b ohne zusätzliches Flag. Dass die Datei die Konformität einhält, prüft veraPDF."
    assert _fallunterscheidung_satz(pauschal) is None


def test_gegenprobe_eine_echte_fallunterscheidung_besteht():
    satz = ("Im Normalfall entsteht ein PDF/A-2b, wird eine Datei eingebettet, "
            "entsteht stattdessen ein PDF/A-3b.")
    assert _fallunterscheidung_satz(satz) is not None


# ── Inhalt: was in docs/rechnung.md ausdrücklich dastehen soll ─────────────
#
# Aus dem Abschnitt "Was ausdrücklich dasteht" in .agent/task.md. Jeder Test liest die
# Datei direkt — existiert sie noch nicht, ist das ein gültiges Rot (FileNotFoundError).

def test_formatfassung_und_profil_stehen_da():
    text = _fliesstext(RECHNUNG_MD)
    assert "ZUGFeRD" in text, "docs/rechnung.md nennt nicht, welche Formatfassung erzeugt wird"
    assert "EN 16931" in text, "docs/rechnung.md nennt nicht, welches Profil erzeugt wird"


@pytest.mark.parametrize("werkzeug", ["Mustang", "KoSIT"])
def test_fremdes_pruefwerkzeug_und_seine_regelfassung_stehen_da(werkzeug):
    """ADR 0040: Mustang 2.26.0 und der KoSIT-Validator 1.6.3 prüfen in der CI gegen
    eine benannte Regelfassung (XR_30 / XRechnung 3.0.2). Die AC verlangt beides:
    dass geprüft wird, und mit welcher Fassung."""
    text = _fliesstext(RECHNUNG_MD)
    stelle = text.find(werkzeug)
    assert stelle != -1, f"docs/rechnung.md nennt kein Prüfwerkzeug '{werkzeug}'"
    umfeld = text[stelle:stelle + 120]
    assert re.search(r"\d+\.\d+", umfeld), (
        f"'{werkzeug}' steht da, aber keine Versions-/Regelfassung in der Nähe — "
        "welche Fassung geprüft hat, bleibt offen")


GRENZEN_MUSS = {
    "Rechnungsnummer": re.compile(
        r"keine[rn]?\s+\S*\s*Rechnungsnummer|Rechnungsnummer\w*[^.]{0,30}(nicht|keine)", re.I),
    "Buchführung": re.compile(r"bucht\s+nicht|keine\s+Buchführung|kein[e]?\s+Buchhaltung", re.I),
    "Mahnwesen": re.compile(r"mahnt\s+nicht|kein\s+Mahnwesen", re.I),
    "Versand": re.compile(r"versendet\s+nichts|kein[en]?\s+Versand", re.I),
}


@pytest.mark.parametrize("was", list(GRENZEN_MUSS), ids=list(GRENZEN_MUSS))
def test_die_vier_grenzen_stehen_ausdruecklich_da(was):
    """AC: 'Dass falzmarke keine Rechnungsnummern vergibt, nichts bucht, nichts mahnt
    und nichts versendet.' Vier eigene Fälle, weil jeder für sich fehlen kann."""
    text = _fliesstext(RECHNUNG_MD)
    assert GRENZEN_MUSS[was].search(text), (
        f"docs/rechnung.md sagt nicht ausdrücklich, dass falzmarke {was.lower()} nicht "
        "übernimmt")


def test_gegenprobe_die_vier_regeln_greifen_an_ihrem_eigenen_beispiel():
    """Ohne sie belegen die vier Tests oben nur, dass gerade nichts dasteht — nicht,
    dass die Regex das Gesuchte überhaupt erkennen würde."""
    beispiele = {
        "Rechnungsnummer": "falzmarke vergibt keine Rechnungsnummern.",
        "Buchführung": "Es bucht nicht und führt keine Buchführung.",
        "Mahnwesen": "falzmarke kennt kein Mahnwesen.",
        "Versand": "falzmarke versendet nichts.",
    }
    for was, satz in beispiele.items():
        assert GRENZEN_MUSS[was].search(satz), f"Regex für {was} greift nicht am eigenen Beispiel"


def test_gegenprobe_die_vier_regeln_schlagen_nicht_grundlos_an():
    neutral = "falzmarke setzt Briefe nach DIN 5008 und misst das fertige PDF nach."
    for was, regex in GRENZEN_MUSS.items():
        assert not regex.search(neutral), f"Regex für {was} feuert auch ohne Bezug"


def test_ob_gerechnet_oder_nur_uebertragen_wird_steht_da():
    """AC: 'Ob das Werkzeug rechnet oder nur überträgt — mit derselben Klarheit […]'.
    ADR 0039, Entscheidung 1: 'falzmarke rechnet nicht' und 'überträgt', was ihm
    gegeben wurde."""
    text = _fliesstext(RECHNUNG_MD)
    assert re.search(r"rechnet\s+nicht", text, re.I), (
        "docs/rechnung.md sagt nicht, dass falzmarke nicht rechnet")
    assert re.search(r"überträgt", text, re.I), (
        "docs/rechnung.md sagt nicht, dass falzmarke nur überträgt")


def test_gegenprobe_rechnet_nicht_regex_greift():
    assert re.search(r"rechnet\s+nicht", "falzmarke rechnet nicht.", re.I)
    assert not re.search(r"rechnet\s+nicht", "falzmarke rechnet die Summe.", re.I)
