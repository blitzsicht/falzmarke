"""Der Sollwert der Ruleset-Durchsetzung steht an genau einer Stelle (#212).

Bis zum 01.09.2026 stand er zweimal: als `DURCHSETZUNG="active"` in
`repo-einstellungen.sh`, wo er gesetzt wird, und als `SOLL_ENFORCEMENT` in
`repo_pruefung.py`, wogegen der Wächter prüft. Sie waren gleich; nichts hielt
sie gleich. Drei Sabotagen am 01.09.2026 zeigten es: eine am Wert im
Setz-Skript blieb **stumm** (Exit 0), weil `--pruefen` dort per `exec` in den
Prüfer springt und die Zeile nie erreicht.

Diese Tests halten fest, dass es die zweite Stelle nicht mehr gibt — und dass
die eine in beide Richtungen wirkt.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

from conftest import REPO, ohne_bash

sys.path.insert(0, str(REPO / "scripts"))

import durchsetzung                                              # noqa: E402

SKRIPT = REPO / "scripts" / "repo-einstellungen.sh"
PRUEFER = REPO / "scripts" / "repo_pruefung.py"


# ── Der Normalfall und der Sonderfall ───────────────────────────────────────


def test_ohne_variable_gilt_der_strenge_wert():
    assert durchsetzung.soll("main", {}) == "active"
    assert durchsetzung.soll("release-tags", {}) == "active"


def test_mit_variable_wird_nur_main_beobachtend():
    """Der Sonderfall betrifft main, nicht jedes Ruleset.

    `release-tags` schützt veröffentlichte Tags vor Löschung und Überschreiben;
    `repo-einstellungen.sh` setzt es fest auf den strengen Wert. Gälte der
    Sonderfall auch dort, erwartete der Wächter ein `evaluate`, das der
    Setz-Lauf nie schreibt — eine Abweichung, die niemand beheben kann.
    """
    umgebung = {durchsetzung.UMGEBUNGSVARIABLE: "1"}
    assert durchsetzung.soll("main", umgebung) == "evaluate"
    assert durchsetzung.soll("release-tags", umgebung) == "active"


def test_nur_der_wert_eins_zaehlt():
    """Gegenprobe: eine gesetzte, aber andere Belegung schaltet nichts frei.

    Sonst genügte ein leeres oder versehentlich gesetztes
    FALZMARKE_RULESET_EVALUATE, um main den Schutz zu nehmen.
    """
    for wert in ("", "0", "true", "ja", "2"):
        assert durchsetzung.soll("main", {durchsetzung.UMGEBUNGSVARIABLE: wert}) == "active", wert


# ── Die Ausnahme wird nicht verschwiegen ────────────────────────────────────


def test_ohne_sonderfall_gibt_es_nichts_zu_melden():
    assert durchsetzung.grund({}) is None


def test_der_sonderfall_bringt_seine_begruendung_mit():
    """Ein Wächter, der wegen einer Umgebungsvariable schweigt, ohne das zu
    sagen, ist genau der stille Ausfall, gegen den #206 gebaut wurde."""
    text = durchsetzung.grund({durchsetzung.UMGEBUNGSVARIABLE: "1"})
    assert text is not None
    assert durchsetzung.UMGEBUNGSVARIABLE in text
    assert "evaluate" in text and "active" in text


# ── Es gibt keine zweite Stelle mehr ────────────────────────────────────────


def test_der_pruefer_haelt_keinen_eigenen_sollwert_mehr():
    """Die Konstante aus dem Issue ist weg — nicht bloß gleichgesetzt.

    Stünde sie noch da, könnte sie wieder auseinanderlaufen; genau das war der
    Befund. Geprüft wird der Name, nicht der Wert: Ein `SOLL_ENFORCEMENT`, das
    zufällig dasselbe sagt, ist trotzdem die zweite Stelle.
    """
    text = PRUEFER.read_text(encoding="utf-8")
    assert "SOLL_ENFORCEMENT" not in text, "der Prüfer hält wieder einen eigenen Sollwert"
    assert "import durchsetzung" in text


def test_das_setz_skript_haelt_keinen_eigenen_sollwert_mehr():
    """Dasselbe für die andere Seite: keine Zuweisung eines Literals.

    Der Wert darf im Skript nur noch aus dem Modul kommen. Kommentare, die
    "active" erwähnen, sind erlaubt — sie erklären, sie wirken nicht.

    Die erste Fassung dieses Tests suchte wörtlich nach `DURCHSETZUNG="` und
    übersah dadurch `DURCHSETZUNG_TAGS="active"` — in der Sabotage-Probe blieb
    er grün, wo er hätte anschlagen müssen. Geprüft wird deshalb JEDE Zuweisung
    an eine `DURCHSETZUNG…`-Variable und jedes eingebettete `enforcement`-Feld.
    """
    zeilen = [z for z in SKRIPT.read_text(encoding="utf-8").splitlines()
              if not z.lstrip().startswith("#")]

    # Eine Zuweisung ist erlaubt, wenn sie aus einer Kommando-Substitution
    # kommt; ein Literal in Anführungszeichen ist die zweite Stelle.
    literal_zuweisung = re.compile(r'^\s*DURCHSETZUNG[A-Z_]*=(?!\$\()')
    verstoesse = [z for z in zeilen if literal_zuweisung.match(z)]

    # Und das Feld darf in keinem Ruleset-JSON fest ausgeschrieben stehen.
    festes_feld = re.compile(r'"enforcement"\s*:\s*"(active|evaluate)"')
    verstoesse += [z for z in zeilen if festes_feld.search(z)]

    assert not verstoesse, verstoesse
    assert any("durchsetzung.py" in z for z in zeilen), "das Skript fragt die Quelle nicht"


def test_der_pruefer_gibt_die_ausnahme_auch_aus():
    """`grund()` zu haben genügt nicht — sie muss beim Lauf auch erscheinen.

    Ein Struktur-Test, kein Lauf: `main()` braucht `gh` und Netz. Er hält
    fest, dass die Ausgabe verdrahtet ist; dass der Satz stimmt, prüft
    `test_der_sonderfall_bringt_seine_begruendung_mit` eine Ebene tiefer.
    """
    text = PRUEFER.read_text(encoding="utf-8")
    assert "durchsetzung.grund()" in text, "main() fragt die Begründung nicht ab"
    assert "AUSNAHME" in text, "die Begründung wird nirgends ausgegeben"


def test_die_warnschwelle_haelt_mit_dem_sollwert_schritt():
    """`warne_bei_herunterstufung` traegt "active" als Literal — mit Grund.

    Die Funktion wird von tests/test_ruleset_durchsetzung.py aus der Datei
    ausgeschnitten und einzeln gefahren; eine globale Variable waere dort leer,
    und die Warnung erschiene faelschlich schon beim ERSTEN Anlegen eines
    Rulesets. Der Preis dafuer ist ein Literal — dieser Test ist die Klammer,
    die verhindert, dass es vom Sollwert abdriftet.

    Wer STANDARD aendert und diese Stelle vergisst, bekommt hier rot statt eine
    Warnung, die nie mehr ausloest.
    """
    text = SKRIPT.read_text(encoding="utf-8")
    start = text.index("warne_bei_herunterstufung() {")
    funktion = text[start:text.index("\n}\n", start)]
    schwellen = re.findall(r'\$(?:vorher|nachher)"?\s*!?=\s*"([a-z]+)"', funktion)
    assert schwellen, f"keine Schwelle gefunden in:\n{funktion}"
    assert set(schwellen) == {durchsetzung.STANDARD}, (schwellen, durchsetzung.STANDARD)


# ── Beide Richtungen aus derselben Quelle ───────────────────────────────────


def _setz_zeile() -> str:
    """Die Zeile, mit der repo-einstellungen.sh den Wert holt — aus der Datei
    gelesen statt nachgebaut. Ein nachgebauter Aufruf bewiese nur, dass das
    Modul funktioniert, nicht dass das Skript es benutzt."""
    for zeile in SKRIPT.read_text(encoding="utf-8").splitlines():
        if zeile.startswith("DURCHSETZUNG=$("):
            return zeile
    raise AssertionError("keine Zuweisung DURCHSETZUNG=$(...) im Skript gefunden")


def _verstellte_werkstatt(tmp_path) -> Path:
    """Eine Kopie von scripts/ mit verstelltem Sollwert.

    Das ganze Verzeichnis, nicht nur die eine Datei: `repo_pruefung.py` stellt
    beim Import sein EIGENES Verzeichnis an den Anfang von sys.path. Laege dort
    die echte durchsetzung.py, verdraengte sie die verstellte — der Test waere
    gruen, ohne die Sabotage je gesehen zu haben.
    """
    werkstatt = tmp_path / "scripts"
    shutil.copytree(REPO / "scripts", werkstatt)
    ziel = werkstatt / "durchsetzung.py"
    verstellt = ziel.read_text(encoding="utf-8").replace(
        'STANDARD = "active"', 'STANDARD = "verstellt"', 1)
    assert 'STANDARD = "verstellt"' in verstellt, "die Sabotage hat nicht gegriffen"
    ziel.write_text(verstellt, encoding="utf-8")
    return werkstatt


def test_die_pruef_richtung_folgt_der_quelle(tmp_path, monkeypatch):
    """Wird der eine Sollwert verstellt, verlangt der Waechter den verstellten.

    Diese Haelfte braucht kein bash und laeuft deshalb auf jeder Plattform —
    die Setz-Richtung unten wird auf den Windows-Runnern uebersprungen, und ein
    Test, der nur uebersprungen wird, belegt nichts.
    """
    monkeypatch.syspath_prepend(str(_verstellte_werkstatt(tmp_path)))
    for modul in ("durchsetzung", "repo_pruefung"):
        sys.modules.pop(modul, None)
    try:
        import repo_pruefung as frisch                            # noqa: PLC0415
        ergebnisse = frisch.pruefe(
            "blitzsicht/falzmarke",
            api=lambda pfad: [] if pfad.endswith("/rulesets") else {"homepage": ""},
            workflow=REPO / ".github" / "workflows" / "ci.yml",
            domain_pruefen=lambda _: True)
        soll_werte = {e.soll for e in ergebnisse if "enforcement" in e.name}
        assert soll_werte == {"verstellt"}, soll_werte
    finally:
        # Die echten Module zurueck in den Cache, sonst erbt der naechste Test
        # die verstellte Fassung. Eine Sabotage, die ueberlebt, ist schlimmer
        # als keine — sie macht fremde Tests gruen oder rot aus falschem Grund.
        for modul in ("durchsetzung", "repo_pruefung"):
            sys.modules.pop(modul, None)


@ohne_bash
def test_die_setz_richtung_folgt_derselben_quelle(tmp_path):
    """Und der Setz-Lauf schreibt denselben verstellten Wert.

    Zusammen mit dem Test darueber ist das die Gegenprobe aus dem Issue: Ginge
    nur eine Richtung mit, gaebe es die zweite Stelle noch — dann belegte der
    Test bloss, dass irgendwo eine Zeichenkette steht.

    Gefahren wird die ECHTE Zeile aus repo-einstellungen.sh, aus der Datei
    gelesen statt nachgebaut. Ein nachgebauter Aufruf bewiese nur, dass das
    Modul funktioniert, nicht dass das Skript es benutzt.
    """
    _verstellte_werkstatt(tmp_path)
    fertig = subprocess.run(["bash", "-c", f"{_setz_zeile()}\nprintf '%s' \"$DURCHSETZUNG\""],
                            cwd=tmp_path, capture_output=True, text=True)
    assert fertig.returncode == 0, fertig.stderr
    assert fertig.stdout == "verstellt", (fertig.stdout, fertig.stderr)
