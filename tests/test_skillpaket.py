"""Das Skill-Paket muss auch ohne PyPI-Zugriff rendern können (#122).

Das Paket enthielt nur Quelltext. `scripts/bootstrap.py` holte beim ersten Lauf
fünf Pakete per `pip` nach — in einer Sandbox ohne Netz kam der Renderer damit
nie zustande. Gemessen: Entpacken, Befehlszeile, `profiles` und `check` liefen;
nur `render` nicht, weil `typst` fehlte.

Was hier festgehalten wird, ist beides: dass das Wheel mitreist **und** dass der
Weg dorthin ohne Netz trägt. Die zweite Hälfte ist die wichtigere — ein Paket,
das ein Wheel enthält, aus dem niemand installiert, sieht von außen genauso aus
wie eines, das funktioniert.

Kein Test hier geht ans Netz. Wo eine echte Installation nachgewiesen wird,
baut der Test sich ein winziges Wheel selbst.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from conftest import REPO

SKRIPT = REPO / "scripts" / "skill_packen.sh"
CI = REPO / ".github" / "workflows" / "ci.yml"
RELEASE = REPO / ".github" / "workflows" / "release.yml"
AUFRUF = "bash scripts/skill_packen.sh"
VENDOR = REPO / "skill" / "vendor"


def _bootstrap():
    """`skill/scripts/` liegt nicht im sys.path — die Datei wird direkt geladen."""
    pfad = REPO / "skill" / "scripts" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("falzmarke_bootstrap", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _probewheel(ziel: Path) -> Path:
    """Ein gültiges, winziges Wheel — gebaut statt geladen, damit der Test
    dasselbe kann wie die Sandbox: nämlich nicht ins Netz."""
    ziel.mkdir(parents=True, exist_ok=True)
    rad = ziel / "falzmarke_probe-1.0-py3-none-any.whl"
    with zipfile.ZipFile(rad, "w") as z:
        z.writestr("falzmarke_probe.py", "WERT = 'aus dem Paket'\n")
        z.writestr("falzmarke_probe-1.0.dist-info/METADATA",
                   "Metadata-Version: 2.1\nName: falzmarke-probe\nVersion: 1.0\n")
        z.writestr("falzmarke_probe-1.0.dist-info/WHEEL",
                   "Wheel-Version: 1.0\nGenerator: probe\n"
                   "Root-Is-Purelib: true\nTag: py3-none-any\n")
        z.writestr("falzmarke_probe-1.0.dist-info/RECORD", "")
    return rad


# ── Das Paket wird an einer Stelle gebaut, nicht an zweien ──────────────────

def test_das_skript_gibt_es_und_ist_ausfuehrbar():
    """Gefragt wird Git, nicht das Dateisystem — auf Windows gibt es kein
    Ausführbar-Bit, und der Linux-Runner richtet sich nach dem Git-Modus."""
    assert SKRIPT.is_file(), f"{SKRIPT} fehlt"
    eintrag = subprocess.run(
        ["git", "ls-files", "-s", "scripts/skill_packen.sh"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert eintrag.startswith("100755"), (
        f"Git führt das Skript nicht als ausführbar: {eintrag.strip() or '— nicht getrackt —'}")


@pytest.mark.parametrize("datei", [CI, RELEASE], ids=lambda p: p.name)
def test_beide_workflows_rufen_dasselbe_skript(datei):
    """Nicht nur der Release-Job, auch die CI.

    Der Pack-Schritt lief anfangs ausschließlich am Tag — und das Ruleset lässt
    Tags weder verschieben noch löschen. Ein Fehlschlag dort kostet eine
    Versionsnummer, die niemand je wieder verwenden kann. Dieselbe Lehre wie
    bei der Paketprobe (#76), nur eine Datei weiter.
    """
    assert AUFRUF in datei.read_text(encoding="utf-8"), (
        f"{datei.name} ruft {AUFRUF!r} nicht auf. Wer die Schritte dort wieder "
        "ausschreibt, hat zwei Fassungen, die auseinanderlaufen — und die im "
        "Release-Workflow lässt sich vor dem Tag nicht ausprobieren.")


def test_die_ci_weist_den_weg_ohne_netz_nach():
    """Das Wheel ist für manylinux gebaut und auf keiner anderen Plattform
    installierbar — der echte Nachweis kann nur auf dem Linux-Runner laufen.
    Hier wird festgehalten, dass er dort auch wirklich steht.
    """
    text = CI.read_text(encoding="utf-8")
    for satz, wozu in [
        ("PIP_INDEX_URL=http://127.0.0.1:1/simple", "PyPI wird nicht unerreichbar gemacht"),
        ("bootstrap.py", "bootstrap wird gar nicht aufgerufen"),
        ("typst war schon installiert", "die Vorbedingung wird nicht sichtbar gemacht"),
        ("rm -f falzmarke/vendor/*.whl", "die Gegenprobe ohne Wheel fehlt"),
    ]:
        assert satz in text, f"Der Nachweis in ci.yml trägt nicht: {wozu}"


def test_die_pruefung_wuerde_ein_auseinanderlaufen_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass es gerade dasteht."""
    ohne = RELEASE.read_text(encoding="utf-8").replace(AUFRUF, "zip -rq falzmarke.skill", 1)
    assert AUFRUF not in ohne, "die Sabotage greift nicht"


def test_der_workflow_packt_nicht_mehr_selbst():
    """Der alte Dreisatz aus cp, rm und zip darf nicht danebenstehen bleiben."""
    text = RELEASE.read_text(encoding="utf-8")
    assert not re.search(r"zip\s+-rq\s+\.\./falzmarke\.skill", text), (
        "release.yml packt noch selbst — dann gibt es das Paket in zwei Fassungen.")


# ── Ohne Wheel ist das Paket unbrauchbar, und das muss laut werden ──────────

def test_das_skript_bricht_ab_wenn_kein_wheel_dabei_ist(tmp_path):
    """Der teure Fehler ist nicht der Abbruch, sondern das stille Weiterlaufen:
    Ein Paket mit leerem `vendor/` ist genau der Zustand vor #122 — und sieht
    von außen aus wie ein gelungener Lauf.

    Nachgewiesen wird das am echten Skript mit ausgehängtem Download. Der Test
    braucht dafür kein Netz und fasst das Repo nicht an: Er baut sich einen
    eigenen Baum, in dem `skill/` auf das echte Verzeichnis zeigt.

    Gemessen am 28.08.2026, mit entferntem Wächter: Das Skript bricht dann
    **trotzdem** ab — aber erst weiter unten, am Exit-Code eines `grep`, und
    ohne ein Wort dazu. Der Wächter verhindert also nicht den Abbruch, sondern
    den unerklärten. Deshalb prüft dieser Test die Meldung und nicht nur den
    Rückgabewert; ohne diese zweite Zusicherung wäre er auch ohne Wächter grün.
    """
    if sys.platform.startswith("win"):
        pytest.skip("bash und Symlinks — der Nachweis läuft auf den anderen beiden Plattformen")

    (tmp_path / "scripts").mkdir()
    (tmp_path / "skill").symlink_to(REPO / "skill", target_is_directory=True)

    text = SKRIPT.read_text(encoding="utf-8")
    sabotiert = text.replace("python3 -m pip download", "true", 1)
    assert sabotiert != text, "die Sabotage greift nicht — der Download heißt anders"
    ziel = tmp_path / "scripts" / "skill_packen.sh"
    ziel.write_text(sabotiert, encoding="utf-8")

    lauf = subprocess.run(["bash", str(ziel)], capture_output=True, text=True,
                          encoding="utf-8", cwd=tmp_path)
    assert lauf.returncode != 0, (
        "Das Skript hat ein Offline-Paket ohne Wheel gebaut und nichts gesagt.\n" + lauf.stdout[-800:])
    assert "kein Wheel" in lauf.stderr, f"Die Meldung nennt den Grund nicht: {lauf.stderr!r}"


# ── Der Sollwert: 30 MB Uploadgrenze ────────────────────────────────────────

#: Gemessen am 28.08.2026 am Dialog „Fähigkeit hochladen" von claude.ai. Der
#: Wortlaut der Meldung steht hier, weil eine Zahl ohne ihren Anlass nach
#: einem halben Jahr wie eine Schätzung aussieht.
MELDUNG = "Zip file must be less than 30MB"
MAX_MB = 30


def test_die_grenze_steht_nur_an_einer_stelle():
    """Ein Sollwert, eine Quelle. Zwei laufen auseinander, und die falsche gilt."""
    text = SKRIPT.read_text(encoding="utf-8")
    assert re.search(r"^MAX_MB=30$", text, re.M), (
        "Die Uploadgrenze steht nicht als MAX_MB im Packskript.")
    assert MELDUNG in text, (
        f"Der Wortlaut der Meldung fehlt: {MELDUNG!r}. Eine Zahl ohne ihren "
        "Anlass sieht später wie eine Schätzung aus.")


def test_das_skript_baut_beide_pakete():
    """Zwei Dateien, zwei Zwecke — sonst ist eine der beiden Gruppen versorgt
    und die andere nicht."""
    text = SKRIPT.read_text(encoding="utf-8")
    for datei in ("falzmarke.skill", "falzmarke-offline.skill"):
        assert datei in text, f"{datei} entsteht nicht"


def test_das_skript_bricht_ab_wenn_das_schlanke_paket_zu_gross_wird(tmp_path):
    """Der teuerste Fall ist der stille: Ein zu großes Paket faellt erst beim
    Hochladen auf, also Tage nach dem Release — und dann steht die Datei schon
    unter einem Tag, der sich nicht verschieben laesst.

    Nachgewiesen am echten Skript mit auf 0 gesetzter Grenze. Das ist dieselbe
    Lage wie ein zu grosses Paket, nur ohne 34 MB zu erzeugen.
    """
    if sys.platform.startswith("win"):
        pytest.skip("bash und Symlinks — der Nachweis läuft auf den anderen beiden Plattformen")

    (tmp_path / "scripts").mkdir()
    (tmp_path / "skill").symlink_to(REPO / "skill", target_is_directory=True)

    text = SKRIPT.read_text(encoding="utf-8")
    sabotiert = text.replace("MAX_MB=30", "MAX_MB=0", 1)
    assert sabotiert != text, "die Sabotage greift nicht — die Grenze heißt anders"
    # Der Download kommt gar nicht mehr dran: Die Grenze wird geprueft, bevor
    # 34 MB geladen werden. Genau das ist der Sinn der Reihenfolge.
    ziel = tmp_path / "scripts" / "skill_packen.sh"
    ziel.write_text(sabotiert, encoding="utf-8")

    lauf = subprocess.run(["bash", str(ziel)], capture_output=True, text=True,
                          encoding="utf-8", cwd=tmp_path)
    assert lauf.returncode != 0, (
        "Das Skript hat ein Paket über der Grenze gebaut und nichts gesagt.\n"
        + lauf.stdout[-600:])
    assert "zu gross fuer den Upload" in lauf.stderr, lauf.stderr


def test_im_quellbaum_liegt_kein_wheel():
    """32,6 MB, die jeder Klon mitzöge und die niemand je wieder aus der
    Historie bekäme. Das Wheel entsteht beim Packen, nicht im Repository."""
    gefunden = list(VENDOR.glob("*.whl")) if VENDOR.is_dir() else []
    assert not gefunden, (
        "Im Quellbaum liegt ein Wheel: " + ", ".join(p.name for p in gefunden) +
        "\nEs gehört ins Paket, nicht ins Repository — siehe skill/vendor/README.md.")


def test_gitignore_haelt_wheels_draussen():
    """Der Test oben findet ein eingechecktes Wheel erst, wenn es da ist."""
    text = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert re.search(r"vendor/\*\.whl|\*\.whl", text), (
        ".gitignore lässt Wheels durch — dann ist der Wächter oben ein Nachruf.")


# ── Der Weg ohne Netz trägt wirklich ────────────────────────────────────────

def test_aus_dem_paket_wird_ohne_netz_installiert(tmp_path):
    """Der eigentliche Nachweis: `--no-index --find-links` installiert aus einem
    Verzeichnis, ohne PyPI zu fragen. Mit einem selbstgebauten Wheel, damit der
    Test dasselbe kann wie die Sandbox."""
    quelle = tmp_path / "vendor"
    _probewheel(quelle)
    ziel = tmp_path / "ziel"
    lauf = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--no-index",
         "--find-links", str(quelle), "--target", str(ziel), "falzmarke-probe"],
        capture_output=True, text=True, encoding="utf-8")
    assert lauf.returncode == 0, f"Installation ohne Netz schlug fehl:\n{lauf.stderr}"
    assert (ziel / "falzmarke_probe.py").is_file()


def test_ohne_wheel_schlaegt_dieselbe_installation_fehl(tmp_path):
    """Gegenprobe zum Test darüber. Ohne sie belegt er nur, dass pip läuft."""
    leer = tmp_path / "leer"
    leer.mkdir()
    lauf = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--no-index",
         "--find-links", str(leer), "--target", str(tmp_path / "ziel"), "falzmarke-probe"],
        capture_output=True, text=True, encoding="utf-8")
    assert lauf.returncode != 0, "pip fand ein Paket, das es nicht geben kann"


# ── bootstrap.py nimmt den Vorrat vor dem Netz ──────────────────────────────

def test_bootstrap_findet_die_wheels_im_paket(tmp_path, monkeypatch):
    b = _bootstrap()
    monkeypatch.setattr(b, "VENDOR", tmp_path)
    assert b.wheels() == []
    rad = _probewheel(tmp_path)
    assert b.wheels() == [rad]


def test_bootstrap_fragt_je_paket_einzeln_ohne_index(tmp_path, monkeypatch):
    """`pip install --no-index` bricht komplett ab, sobald für **ein** genanntes
    Paket kein Wheel danebenliegt — es installiert dann auch die anderen nicht.
    Ein Vorrat, der nur `typst` enthält, hätte damit gar nichts ausgerichtet.
    """
    b = _bootstrap()
    monkeypatch.setattr(b, "VENDOR", tmp_path)
    aufrufe = []

    class Ergebnis:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(b.subprocess, "run", lambda cmd, **k: aufrufe.append(cmd) or Ergebnis())

    b.aus_dem_paket({"typst": "typst>=0.15,<0.16", "yaml": "pyyaml>=6"})

    assert len(aufrufe) == 2, f"erwartet ein Aufruf je Paket, waren {len(aufrufe)}"
    for cmd in aufrufe:
        assert "--no-index" in cmd, "ohne --no-index fragt pip doch das Netz"
        assert "--find-links" in cmd and str(tmp_path) in cmd
        # Genau ein Requirement je Aufruf — sonst reisst ein fehlendes Wheel
        # die anderen mit.
        assert len([t for t in cmd if ">=" in t]) == 1, cmd


def test_bootstrap_meldet_was_fehlt_statt_am_renderer_zu_scheitern(monkeypatch):
    """Der dritte Zustand: nicht installierbar ist nicht dasselbe wie fertig."""
    b = _bootstrap()
    quelle = b.__loader__.get_source("falzmarke_bootstrap")
    for satz in ("Diese Pakete fehlen weiterhin", "keinen Ersatz-Renderer"):
        assert satz in quelle, f"Die Fehlermeldung sagt {satz!r} nicht mehr"


def test_der_vorrat_kommt_vor_dem_netz():
    """Reihenfolge im Quelltext: erst `vendor/`, dann PyPI. Andersherum wäre der
    Vorrat nur ein Rückfall für den Fall, dass PyPI langsam ist."""
    quelle = (REPO / "skill" / "scripts" / "bootstrap.py").read_text(encoding="utf-8")
    ohne_netz = quelle.index("aus_dem_paket(offen)")
    mit_netz = quelle.index("versuche PyPI")
    assert ohne_netz < mit_netz, "PyPI wird vor dem mitgelieferten Vorrat gefragt"
