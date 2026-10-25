"""Die Zeichennamen im Add-on sind die von Python — erzeugt, nicht gepflegt.

`vergleich.js` muss denselben Textkern bilden wie `gesendet.py`, sonst schweigt
die Sperre beim Senden, wo `status` „SCHON RAUS“ sagt (ADR 0057). Bis 0.3.0
stand im Add-on eine Auswahl von zwanzig Namen; `&ndash;` blieb dort als Wort
„ndash“ im Kern, während Python „–“ daraus machte und es damit aus dem Kern
warf. Seither erzeugt `scripts/zeichennamen.py` alle 2231 Namen.

Hier wird dreierlei geprüft, und jedes mit einer Probe, die anschlagen muss:

1. Die Datei im Repo ist die, die der Erzeuger schreibt.
2. Eine Änderung von Hand fällt auf (dieselbe Datei wird dafür wirklich
   angefasst und danach zurückgeschrieben).
3. Der Sollwert kommt aus `html.entities`, nicht aus der Datei daneben — sonst
   prüfte sich die Tabelle gegen sich selbst.
"""

import importlib.util
import subprocess
import sys

from conftest import REPO

SKRIPT = REPO / "scripts" / "zeichennamen.py"
ZIEL = REPO / "thunderbird" / "entwurfsbruecke" / "zeichennamen.js"


def _pruefen() -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SKRIPT), "--pruefen"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)


def _erzeuger():
    """Das Skript als Modul — ohne es über den Suchpfad zu installieren."""
    spec = importlib.util.spec_from_file_location("zeichennamen_skript", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_die_tabelle_im_addon_ist_aktuell():
    lauf = _pruefen()
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert "2231 Namen" in lauf.stdout


def test_gegenprobe_eine_aenderung_von_hand_faellt_auf():
    """Sabotiert wird die Datei, die ausgeliefert wird — nicht eine Kopie."""
    vorher = ZIEL.read_text(encoding="utf-8")
    try:
        ZIEL.write_text(vorher.replace('"ndash;": "–",', '"ndash;": "ndash",'),
                        encoding="utf-8")
        assert ZIEL.read_text(encoding="utf-8") != vorher, "die Sabotage hat nichts verändert"
        lauf = _pruefen()
        assert lauf.returncode == 1, "eine geänderte Tabelle ging als aktuell durch"
        assert "VERALTET" in lauf.stderr
    finally:
        ZIEL.write_text(vorher, encoding="utf-8")
    assert _pruefen().returncode == 0, "die Rücknahme der Sabotage hat nicht gegriffen"


def test_der_sollwert_kommt_von_python_nicht_aus_der_datei(monkeypatch):
    """Nimmt Python einen Namen dazu, ändert sich die Erwartung — nicht die Datei."""
    import html.entities

    modul = _erzeuger()
    ohne = modul.erzeuge()
    monkeypatch.setitem(html.entities.html5, "gibtsnicht;", "❤")
    mit = modul.erzeuge()
    assert mit != ohne
    assert '"gibtsnicht;": "❤",' in mit
    assert '"gibtsnicht;"' not in ohne


def test_unsichtbare_zeichen_stehen_als_escape_in_der_datei():
    """Roh wären sie im Diff nicht zu prüfen — der Fall, den ADR 0052 meldet."""
    import unicodedata

    text = ZIEL.read_text(encoding="utf-8")
    # Der Nullbreiten-Verbinder belegt, dass der Escape-Weg wirklich lief.
    assert '"zwj;": "\\u200d",' in text
    roh = [hex(ord(z)) for z in text
           if z != "\n" and (unicodedata.category(z)[0] == "C"
                             or unicodedata.category(z) in ("Zl", "Zp"))]
    assert roh == [], f"unsichtbare Zeichen roh in der Datei: {roh[:5]}"
