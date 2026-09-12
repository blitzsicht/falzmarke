"""Tests für die fremde Prüfung von E-Rechnungen (Issue #118).

Hier läuft nur, was das Skript **selbst** entscheidet: ob Java wirklich läuft,
ob das vereinbarte Werkzeug vorliegt, wie ein Exit-Code zu einem Urteil wird,
was aus der Ausgabe als Regelfassung gelesen wird, und welchen Zustand der Lauf
am Ende meldet. Das Werkzeug selbst wird durch einen Aufrufer ersetzt, der
festgelegte Exit-Codes liefert.

**Keine Tests mit dem echten Werkzeug.** Sie liefen nirgends: lokal fehlt Java,
in der Plattform-Matrix fehlt Mustang, und ein übersprungener Test ist kein
Grün. Den Nachweis erbringt der CI-Job „E-Rechnung (Mustang, fremdes Werkzeug)"
— er fährt das Skript gegen echte Dateien, mit Gegenprobe.

Die Exit-Codes, gegen die hier getestet wird (0 gültig, 255 ungültig), sind am
11.09.2026 an Mustang 2.26.0 gemessen, nicht angenommen.
"""

from __future__ import annotations

import re
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))
import erechnung_pruefen as ep  # noqa: E402

CI = REPO / ".github" / "workflows" / "ci.yml"

#: Ausschnitt einer echten Mustang-Ausgabe (2.26.0, EN16931_Einfach.pdf).
AUSGABE_GUT = """\
[main] INFO com.helger.schematron.xslt.SchematronResourceXSLTCache - Compiling XSLT instance \
[cpPath=/xslt/ZF_250/FACTUR-X_EN16931.xslt; urlResolved=true]
[main] INFO com.helger.schematron.xslt.SchematronResourceXSLTCache - Compiling XSLT instance \
[cpPath=/xslt/XR_30/XRechnung-CII-validation.xslt; urlResolved=true]
      <validator version="2.26.0"/>
    <summary status="valid"/>
"""


def _aufrufer(java_exit: int = 0, urteile: dict[str, int] | None = None, standard: int = 0):
    """Ersetzt Java und Mustang. `urteile`: Dateiname -> Exit-Code."""
    urteile = urteile or {}

    def ausfuehren(befehl: list[str]) -> tuple[int, str]:
        if befehl[1:] == ["-version"]:
            return java_exit, "openjdk version \"21\""
        quelle = befehl[befehl.index("--source") + 1]
        name = quelle.rsplit("/", 1)[-1]
        return urteile.get(name, standard), AUSGABE_GUT
    return ausfuehren


@pytest.fixture
def jar(tmp_path, monkeypatch):
    """Ein JAR, dessen Prüfsumme als die vereinbarte gilt."""
    pfad = tmp_path / "Mustang-CLI.jar"
    pfad.write_bytes(b"kein echtes jar, aber ein festgelegter Inhalt")
    monkeypatch.setattr(ep, "MUSTANG_SHA256", ep.sha256(pfad))
    return pfad


@pytest.fixture
def pdfs(tmp_path):
    gut = tmp_path / "gut.pdf"
    schlecht = tmp_path / "schlecht.pdf"
    gut.write_bytes(b"%PDF-1.4 gut")
    schlecht.write_bytes(b"%PDF-1.4 schlecht")
    return gut, schlecht


def _lauf(jar, gut, schlecht, ausfuehren, extra=()) -> int:
    argv = ["--mustang", str(jar), "--gut", str(gut), "--schlecht", str(schlecht), *extra]
    return ep.main(argv, ausfuehren=ausfuehren)


# ── Java, das keines ist ─────────────────────────────────────────────────────

def test_ein_platzhalter_ist_kein_java():
    """Der macOS-Fall: Unter /usr/bin/java liegt etwas, das nicht läuft."""
    assert ep.java_funktioniert(ausfuehren=_aufrufer(java_exit=1)) is False


def test_ein_laufendes_java_ist_java():
    """Die Gegenrichtung — ohne sie belegte der Test darüber nur, dass die
    Funktion immer False sagt."""
    assert ep.java_funktioniert(ausfuehren=_aufrufer(java_exit=0)) is True


def test_ohne_java_ist_der_lauf_nicht_geprueft(jar, pdfs):
    assert _lauf(jar, *pdfs, _aufrufer(java_exit=1)) == 2


# ── Das vereinbarte Werkzeug ─────────────────────────────────────────────────

def test_ein_fehlendes_jar_ist_nicht_geprueft(tmp_path, pdfs):
    assert _lauf(tmp_path / "gibt-es-nicht.jar", *pdfs, _aufrufer()) == 2


def test_ein_anderes_jar_urteilt_nicht(tmp_path, pdfs):
    """Andere Prüfsumme heißt: ein anderes Werkzeug als vereinbart."""
    fremd = tmp_path / "anderes.jar"
    fremd.write_bytes(b"ein anderer Inhalt")
    with pytest.raises(ep.Fehlt, match="vereinbarte Prüfsumme"):
        ep.pruefe_jar(fremd)
    assert _lauf(fremd, *pdfs, _aufrufer()) == 2


def test_das_vereinbarte_jar_wird_angenommen(jar):
    ep.pruefe_jar(jar)                      # wirft nicht


# ── Vom Exit-Code zum Urteil ─────────────────────────────────────────────────

@pytest.mark.parametrize("code, erwartet", [
    (0, ep.GUELTIG), (255, ep.UNGUELTIG), (1, ep.WERKZEUGFEHLER), (137, ep.WERKZEUGFEHLER)])
def test_der_exit_code_ist_das_urteil(jar, pdfs, code, erwartet):
    gut, _ = pdfs
    ist, _ = ep.urteil(gut, jar, ausfuehren=_aufrufer(standard=code))
    assert ist == erwartet


# ── Die Regelfassung steht im Protokoll (Abnahme 2) ─────────────────────────

def test_die_regelfassung_wird_aus_der_ausgabe_gelesen():
    assert ep.regelfassung(AUSGABE_GUT) == "Mustang 2.26.0 · Schematron XR_30, ZF_250"


def test_ohne_angaben_sagt_die_regelfassung_das():
    """Nicht still leer — sonst stünde im Protokoll eine Zeile ohne Aussage."""
    assert "unbekannt" in ep.regelfassung("keine Angaben")


def test_die_regelfassung_steht_in_der_ausgabe(jar, pdfs, capsys):
    _lauf(jar, *pdfs, _aufrufer(urteile={"schlecht.pdf": 255}))
    assert "Regelfassung: Mustang 2.26.0 · Schematron XR_30, ZF_250" in capsys.readouterr().out


# ── Der Zustand am Ende ──────────────────────────────────────────────────────

def test_alles_wie_erwartet_ist_exit_null(jar, pdfs):
    assert _lauf(jar, *pdfs, _aufrufer(urteile={"gut.pdf": 0, "schlecht.pdf": 255})) == 0


def test_eine_gute_datei_die_durchfaellt_ist_ein_befund(jar, pdfs):
    assert _lauf(jar, *pdfs, _aufrufer(urteile={"gut.pdf": 255, "schlecht.pdf": 255})) == 1


def test_eine_schlechte_datei_die_besteht_ist_ein_befund(jar, pdfs):
    """Die Gegenprobe greift: Lässt Mustang die schlechte Datei durch, belegt der
    Lauf nichts mehr."""
    assert _lauf(jar, *pdfs, _aufrufer(urteile={"gut.pdf": 0, "schlecht.pdf": 0})) == 1


def test_ein_absturz_ist_nicht_geprueft_und_nicht_gruen(jar, pdfs):
    assert _lauf(jar, *pdfs, _aufrufer(urteile={"gut.pdf": 1, "schlecht.pdf": 255})) == 2


def test_ohne_gegenprobe_ist_der_lauf_ein_befund(jar, pdfs):
    gut, _ = pdfs
    argv = ["--mustang", str(jar), "--gut", str(gut)]
    assert ep.main(argv, ausfuehren=_aufrufer(urteile={"gut.pdf": 0})) == 1


def test_ohne_gute_datei_ist_der_lauf_ein_befund(jar, pdfs):
    _, schlecht = pdfs
    argv = ["--mustang", str(jar), "--schlecht", str(schlecht)]
    assert ep.main(argv, ausfuehren=_aufrufer(urteile={"schlecht.pdf": 255})) == 1


def test_eine_fehlende_datei_ist_ein_befund(jar, pdfs, tmp_path):
    _, schlecht = pdfs
    ausfuehren = _aufrufer(urteile={"schlecht.pdf": 255})
    assert _lauf(jar, tmp_path / "fehlt.pdf", schlecht, ausfuehren) == 1


# ── Der CI-Job und das Skript meinen dasselbe Werkzeug ───────────────────────

def test_die_ci_laedt_die_version_die_das_skript_erwartet():
    """Eine Quelle für den Pin: das Skript. Die CI lädt nur — und zwar genau
    die Fassung, deren Prüfsumme das Skript kennt. Weichen sie ab, lehnt das
    Skript das JAR ab (Exit 2), und dieser Test sagt vorher, warum."""
    text = CI.read_text(encoding="utf-8")
    muster = r"mustangproject/releases/download/core-([\d.]+)/Mustang-CLI-([\d.]+)\.jar"
    geladen = re.findall(muster, text)
    assert geladen, ("die CI lädt kein Mustang — der Job fehlt oder die Adresse "
                     "hat sich geändert")
    assert all(a == b == ep.MUSTANG_VERSION for a, b in geladen), geladen


def test_die_ci_faehrt_das_skript_mit_gegenprobe():
    text = CI.read_text(encoding="utf-8")
    assert "scripts/erechnung_pruefen.py" in text
    aufruf = text[text.index("scripts/erechnung_pruefen.py"):][:400]
    assert "--gut" in aufruf and "--schlecht" in aufruf, aufruf
