"""Das Plugin für ChatGPT muss die Einreichung bei OpenAI überstehen.

Anlass (29.09.2026): Im Browser und auf dem Handy mit privatem Tarif nimmt
ChatGPT eigene Skills nicht an, sondern nur Plugins aus dem Verzeichnis. Ein
Leser der Anleitung bekam genau diese Ablehnung. Derselbe Skill lief danach im
selben Browser-Chat (Plus) als Upload durch, `verify: 34/34`.

Die Grenzen stehen in `scripts/plugin_packen.py`. Jeder Test hier hat seine
Gegenprobe: Das Paket wird an genau einer Stelle kaputt gemacht, und die
Prüfung muss dort anschlagen. Kein Test geht ans Netz.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest
import yaml
from conftest import REPO

PACKER = REPO / "scripts" / "plugin_packen.py"
SKRIPT = REPO / "scripts" / "skill_packen.sh"
RELEASE = REPO / ".github" / "workflows" / "release.yml"
PLUGIN = "falzmarke-chatgpt-plugin.zip"

#: Wörter, bei denen der Skill auslösen muss. ChatGPT wie Claude lesen vor dem
#: Laden nur die description — was dort fehlt, löst nicht aus.
AUSLOESER = ["Brief", "Anschreiben", "Kündigung", "Mahnung", "Angebot", "Widerspruch",
             "Behördenschreiben", "Mieterschreiben", "E-Mail", "Mail", "Nachricht",
             "Serienbrief", "einlesen"]


def _packer():
    spec = importlib.util.spec_from_file_location("falzmarke_plugin_packen", PACKER)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _probewheel(ordner: Path) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ordner / "probe-1.0-py3-none-any.whl", "w") as z:
        z.writestr("probe.py", "")


def _skill(tmp_path: Path, *, mit_wheel: bool = True) -> Path:
    """Eine Kopie des echten Skills; das Wheel ist ein Platzhalter, weil das
    echte 33 MB wiegt und aus dem Netz käme."""
    ziel = tmp_path / "falzmarke"
    shutil.copytree(REPO / "skill", ziel,
                    ignore=shutil.ignore_patterns("__pycache__", "*.egg-info", "*.whl"))
    if mit_wheel:
        _probewheel(ziel / "vendor")
    return ziel


def _beschreibung() -> str:
    return _packer().skill_kopf(REPO / "skill")["description"]


# ── Die description ────────────────────────────────────────────────────────

def test_description_passt_in_die_grenze_von_openai():
    """1281 Zeichen waren es bis zum 29.09.2026 — die Einreichung hätte sie
    abgewiesen, ohne dass es vorher jemand merkt."""
    packer = _packer()
    laenge = len(_beschreibung())
    assert laenge <= packer.MAX_DESCRIPTION, (
        f"SKILL.md: description hat {laenge} Zeichen, OpenAI nimmt {packer.MAX_DESCRIPTION}.")


def test_zu_lange_description_bricht_das_packen_ab(tmp_path):
    """Gegenprobe zur Grenze: ein Zeichen darüber, und es entsteht kein Paket."""
    packer = _packer()
    skill = _skill(tmp_path)
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    lang = "x" * (packer.MAX_DESCRIPTION + 1)
    sabotiert = re.sub(r"description: >\n(  .*\n)+", f"description: {lang}\n", text, count=1)
    assert sabotiert != text, "die Sabotage greift nicht — der Kopf sieht anders aus"
    (skill / "SKILL.md").write_text(sabotiert, encoding="utf-8")
    with pytest.raises(packer.Abbruch, match="description hat 1025 Zeichen"):
        packer.pruefe_vorher(skill, packer.manifest(packer.projekt()))


@pytest.mark.parametrize("wort", AUSLOESER)
def test_description_nennt_jeden_ausloeser(wort):
    """Kürzen darf Merkmale streichen, keine Auslöser."""
    assert wort in _beschreibung(), f"„{wort}“ fehlt in der description von SKILL.md"


# ── Das Paket ──────────────────────────────────────────────────────────────

def _baue(tmp_path: Path, skill: Path) -> Path:
    packer = _packer()
    ziel = tmp_path / PLUGIN
    packer.pruefe_vorher(skill, packer.manifest(packer.projekt()))
    packer.packe(skill, ziel, packer.manifest(packer.projekt()))
    return ziel


def test_plugin_hat_manifest_an_der_wurzel_und_den_skill_darunter(tmp_path):
    ziel = _baue(tmp_path, _skill(tmp_path))
    namen = zipfile.ZipFile(ziel).namelist()
    assert "plugin.json" in namen
    assert "skills/falzmarke/SKILL.md" in namen
    assert any(n.startswith("skills/falzmarke/vendor/") and n.endswith(".whl") for n in namen), (
        "Kein Wheel im Plugin — ohne PyPI (wie in ChatGPT gemessen) fehlte typst.")
    verboten = [n for n in namen if Path(n).name in (".app.json", "mcp.json")]
    assert not verboten, f"Bei „Skills only“ nicht erlaubt: {verboten}"


def test_manifest_traegt_version_und_namen_aus_pyproject(tmp_path):
    packer = _packer()
    ziel = _baue(tmp_path, _skill(tmp_path))
    mani = json.loads(zipfile.ZipFile(ziel).read("plugin.json"))
    projekt = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert mani["$schema"] == packer.SCHEMA
    assert mani["name"] == projekt["name"]
    assert mani["version"] == projekt["version"]
    assert packer.NAME_MUSTER.match(mani["name"])
    oberflaeche = mani["extensions"]["com.openai"]["interface"]
    assert oberflaeche["privacyPolicyURL"].startswith("https://falzmarke.com/")


def test_ohne_wheel_entsteht_kein_plugin(tmp_path):
    packer = _packer()
    skill = _skill(tmp_path, mit_wheel=False)
    with pytest.raises(packer.Abbruch, match="Kein Wheel"):
        packer.pruefe_vorher(skill, packer.manifest(packer.projekt()))


def test_symlink_im_skill_bricht_ab(tmp_path):
    """OpenAI ignoriert Symlinks still; im Plugin fehlte dann die Datei."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlinks brauchen unter Windows Sonderrechte")
    packer = _packer()
    skill = _skill(tmp_path)
    (skill / "verweis.md").symlink_to(skill / "SKILL.md")
    with pytest.raises(packer.Abbruch, match="Symlinks"):
        packer.pruefe_vorher(skill, packer.manifest(packer.projekt()))


def test_zu_grosses_plugin_wird_nicht_gebaut(tmp_path):
    """Die 100-MB-Grenze, abgesenkt per Umgebungsvariable, am echten Aufruf."""
    skill = _skill(tmp_path)
    ziel = tmp_path / PLUGIN
    lauf = subprocess.run([sys.executable, str(PACKER), str(skill), str(ziel)],
                          capture_output=True, text=True, encoding="utf-8", check=False,
                          env={**os.environ, "FALZMARKE_PLUGIN_MAX_BYTES": "1000"})
    assert lauf.returncode == 1, lauf.stdout + lauf.stderr
    assert "erlaubt sind 1000" in lauf.stderr, lauf.stderr
    assert not ziel.exists(), "Das zu große Paket blieb liegen."


def test_unter_der_grenze_baut_derselbe_aufruf(tmp_path):
    """Gegenprobe zum Test darüber: ohne abgesenkte Grenze Code 0 und ein Paket."""
    skill = _skill(tmp_path)
    ziel = tmp_path / PLUGIN
    umgebung = {k: v for k, v in os.environ.items() if k != "FALZMARKE_PLUGIN_MAX_BYTES"}
    lauf = subprocess.run([sys.executable, str(PACKER), str(skill), str(ziel)],
                          capture_output=True, text=True, encoding="utf-8", check=False, env=umgebung)
    assert lauf.returncode == 0, lauf.stderr
    assert ziel.exists()


# ── Eingebunden in Bau und Release ─────────────────────────────────────────

def test_das_packskript_baut_das_plugin():
    text = SKRIPT.read_text(encoding="utf-8")
    assert "python3 scripts/plugin_packen.py paket/falzmarke " + PLUGIN in text


def _schritt(uses_praefix: str) -> dict:
    jobs = yaml.safe_load(RELEASE.read_text(encoding="utf-8"))["jobs"]
    schritte = [s for s in jobs["skill-paket"]["steps"]
                if str(s.get("uses", "")).startswith(uses_praefix)]
    assert len(schritte) == 1, f"{uses_praefix}: {len(schritte)} Schritte statt einem"
    return schritte[0]["with"]


def test_das_release_haengt_das_plugin_an():
    """Gemessen an der `files`-Liste des Release-Schritts, nicht am ganzen Text:
    Der Dateiname steht auch in `subject-path` und in der Prüfsummenzeile, und
    eine Textsuche bliebe grün, wenn nur der Anhang fehlt (Sabotage 29.09.2026)."""
    dateien = _schritt("softprops/action-gh-release")["files"].split()
    assert PLUGIN in dateien, "release.yml hängt das Plugin nicht an"
    assert f"{PLUGIN}.sha256" in dateien, "release.yml hängt die Prüfsumme nicht an"


def test_die_herkunft_des_plugins_wird_belegt():
    pfade = _schritt("actions/attest-build-provenance")["subject-path"].split()
    assert PLUGIN in pfade, "Für das Plugin entsteht keine Attestation"


def test_gitignore_haelt_die_pakete_draussen():
    text = (REPO / ".gitignore").read_text(encoding="utf-8")
    for datei in ("falzmarke-offline.skill", PLUGIN):
        assert re.search(rf"^{re.escape(datei)}$", text, re.MULTILINE), f"{datei} fehlt in .gitignore"
