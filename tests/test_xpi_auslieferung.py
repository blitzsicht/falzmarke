"""Die Entwurfsbrücke kommt als Release-Anhang und aktualisiert sich selbst.

Thunderbird fragt `update_url` aus dem Manifest ab. Die Adresse zeigt auf
`updates.json` am jüngsten Release; diese Datei nennt Fassung, Link und
Prüfsumme der `.xpi`. Drei Dinge müssen zusammenpassen: das Manifest, das
Skript, das `updates.json` schreibt, und der Release-Lauf, der beides anhängt.
Jeder Test hat seine Gegenprobe. Kein Test geht ans Netz.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path

import yaml
from conftest import REPO

ADDON = REPO / "thunderbird" / "entwurfsbruecke"
RELEASE = REPO / ".github" / "workflows" / "release.yml"


def _modul(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _umgepackt(xpi: Path, ziel: Path, **manifest_neu) -> Path:
    """Dieselbe `.xpi`, nur mit geändertem Manifest."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(xpi) as alt, zipfile.ZipFile(ziel, "w") as neu:
        for name in alt.namelist():
            inhalt = alt.read(name)
            if name == "manifest.json":
                manifest = json.loads(inhalt)
                manifest.update(manifest_neu)
                inhalt = json.dumps(manifest).encode("utf-8")
            neu.writestr(name, inhalt)
    return ziel


def test_updates_json_beschreibt_genau_das_paket(tmp_path):
    xpi = _modul("xpi_packen").packe(ziel=tmp_path)
    datei = _modul("xpi_updates").schreibe(xpi, "v9.9.9")
    eintraege = json.loads(datei.read_text(encoding="utf-8"))["addons"]["entwurfsbruecke@falzmarke"]["updates"]
    assert len(eintraege) == 1
    eintrag = eintraege[0]
    manifest = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))
    assert eintrag["version"] == manifest["version"]
    assert eintrag["update_link"] == (
        f"https://github.com/blitzsicht/falzmarke/releases/download/v9.9.9/{xpi.name}")
    assert eintrag["update_hash"] == "sha256:" + hashlib.sha256(xpi.read_bytes()).hexdigest()
    gecko = manifest["browser_specific_settings"]["gecko"]
    assert eintrag["applications"]["gecko"]["strict_min_version"] == gecko["strict_min_version"]


def test_der_hash_gehoert_zur_datei_nicht_zum_namen(tmp_path):
    """Gegenprobe: Ein Byte mehr in der Datei, und der Hash muss ein anderer sein."""
    updates = _modul("xpi_updates").updates
    xpi = _modul("xpi_packen").packe(ziel=tmp_path)
    vorher = updates(xpi, "v1.0.0")["addons"]["entwurfsbruecke@falzmarke"]["updates"][0]
    xpi.write_bytes(xpi.read_bytes() + b"\0")
    nachher = updates(xpi, "v1.0.0")["addons"]["entwurfsbruecke@falzmarke"]["updates"][0]
    assert vorher["update_hash"] != nachher["update_hash"]


def test_die_fassung_kommt_aus_dem_paket_nicht_aus_dem_quellordner(tmp_path):
    """Gegenprobe: Ein Paket mit anderer Fassung im Manifest als im Quellordner.
    `updates.json` muss die des Pakets nennen."""
    xpi = _modul("xpi_packen").packe(ziel=tmp_path / "echt")
    fremd = _umgepackt(xpi, tmp_path / "fremd" / "entwurfsbruecke-7.7.7.xpi", version="7.7.7")
    eintrag = _modul("xpi_updates").updates(fremd, "v1.0.0")["addons"]["entwurfsbruecke@falzmarke"]["updates"][0]
    assert eintrag["version"] == "7.7.7"
    assert eintrag["update_link"].endswith("/v1.0.0/entwurfsbruecke-7.7.7.xpi")


def test_das_manifest_fragt_das_juengste_release_ab():
    gecko = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))["browser_specific_settings"]["gecko"]
    assert gecko["update_url"] == _modul("xpi_updates").UPDATE_URL
    assert gecko["update_url"] == (
        "https://github.com/blitzsicht/falzmarke/releases/latest/download/updates.json")


def _schritte() -> list[dict]:
    return yaml.safe_load(RELEASE.read_text(encoding="utf-8"))["jobs"]["skill-paket"]["steps"]


def _mit(uses_praefix: str) -> dict:
    treffer = [s for s in _schritte() if str(s.get("uses", "")).startswith(uses_praefix)]
    assert len(treffer) == 1, f"{uses_praefix}: {len(treffer)} Schritte statt einem"
    return treffer[0]["with"]


def test_jedes_release_haengt_paket_pruefsumme_und_updates_json_an():
    """Gemessen an der `files`-Liste, nicht am ganzen Text: `updates.json`
    steht auch im Kommentar, eine Textsuche bliebe grün, wenn nur der Anhang fehlt."""
    dateien = _mit("softprops/action-gh-release")["files"].split()
    for datei in ("entwurfsbruecke-*.xpi", "entwurfsbruecke-*.xpi.sha256", "updates.json"):
        assert datei in dateien, f"release.yml hängt {datei} nicht an"
    assert "entwurfsbruecke-*.xpi" in _mit("actions/attest-build-provenance")["subject-path"].split()


def test_gepackt_wird_vor_dem_release_und_ueber_die_skripte():
    schritte = _schritte()
    namen = [s.get("name", s.get("uses", "")) for s in schritte]
    packen = namen.index("Entwurfsbruecke packen")
    release = next(i for i, s in enumerate(schritte)
                   if str(s.get("uses", "")).startswith("softprops/action-gh-release"))
    assert packen < namen.index("Pruefsummen bilden") < release
    lauf = schritte[packen]["run"]
    assert "python3 scripts/xpi_packen.py ." in lauf
    assert re.search(r'python3 scripts/xpi_updates\.py entwurfsbruecke-\*\.xpi "\$TAG"', lauf)
    # Was angehängt wird, muss der Prüfsummen-Schritt auch so benennen.
    summen = schritte[namen.index("Pruefsummen bilden")]["run"]
    assert "xpi=$(ls entwurfsbruecke-*.xpi)" in summen
    assert 'sha256sum "$xpi" | tee "$xpi.sha256"' in summen
    # Der Tag kommt aus der Umgebung, nie als Ausdruck in die Shell.
    assert "${{" not in lauf
    assert schritte[packen]["env"]["TAG"] == "${{ inputs.tag || github.ref_name }}"


def test_gitignore_haelt_die_gepackte_bruecke_draussen():
    text = (REPO / ".gitignore").read_text(encoding="utf-8")
    for zeile in ("entwurfsbruecke-*.xpi", "entwurfsbruecke-*.xpi.sha256", "/updates.json"):
        assert re.search(rf"^{re.escape(zeile)}$", text, re.MULTILINE), f"{zeile} fehlt in .gitignore"


# ── Die Mindestfassung ist gemessen, nicht geraten ──────────────────────────
#
# Bis 0.3.0 stand im Manifest `strict_min_version: "128.0"` — eine Zahl, die
# nie gemessen wurde. Der privilegierte Teil hängt an internen Pfaden von
# Thunderbird (`MailServices.sys.mjs`, `folderLookup`) und an
# WebExtension-Teilen, die jünger sein dürften als 128
# (`folders.query({specialUse})`, `messages.continueList`). Wer 128 fährt,
# bekäme kein klares „zu alt“, sondern ein halb gestartetes Add-on: Der Fehler
# aus `starten()` landet in der Fehlerkonsole, und falzmarke meldet nur
# „Thunderbird ist zu oder das Add-on fehlt“ (ADR 0054).

#: Wo die Fassung steht, in der die Brücke gemessen wurde.
MESSUNGEN = ("0054-entwurfsbruecke-in-thunderbird.md",
             "0055-entwurfsbuch-status-und-sperre.md",
             "0056-entwurfsbruecke-empfaenger-und-fassung.md")


def _gemessene_fassungen() -> list[tuple[int, int]]:
    """Jede Thunderbird-Fassung, die eine Brücken-Entscheidung als gemessen nennt."""
    aus = []
    for name in MESSUNGEN:
        text = (REPO / "docs" / "entscheidungen" / name).read_text(encoding="utf-8")
        aus += [(int(a), int(b)) for a, b in re.findall(r"Thunderbird (\d+)\.(\d+)", text)]
    return aus


def test_die_mindestfassung_ist_die_niedrigste_gemessene():
    """Zwei Stellen, eine Wahrheit: Manifest gegen die Messung in den ADRs."""
    gemessen = _gemessene_fassungen()
    assert len(gemessen) >= 2, "keine gemessene Thunderbird-Fassung in den ADRs gefunden"
    gecko = json.loads((ADDON / "manifest.json").read_text(
        encoding="utf-8"))["browser_specific_settings"]["gecko"]
    niedrigste = min(gemessen)
    assert gecko["strict_min_version"] == f"{niedrigste[0]}.0", (
        f"Manifest verlangt {gecko['strict_min_version']}, gemessen ist frühestens "
        f"{niedrigste[0]}.{niedrigste[1]}")


def test_gegenprobe_eine_ungemessene_mindestfassung_faellt_auf():
    """Die Probe muss rot werden, wenn das Manifest wieder 128.0 behauptet."""
    niedrigste = min(_gemessene_fassungen())
    assert f"{niedrigste[0]}.0" != "128.0", (
        "eine Brücken-Entscheidung nennt Thunderbird 128 als gemessen — dann ist der "
        "Sollwert dieses Tests falsch, nicht das Manifest")
    gecko = {"strict_min_version": "128.0"}
    assert gecko["strict_min_version"] != f"{niedrigste[0]}.0"


def test_der_update_kanal_traegt_dieselbe_mindestfassung():
    """`xpi_updates.py` schreibt sie ab; eine zweite Zahl gibt es nicht."""
    quelle = (REPO / "scripts" / "xpi_updates.py").read_text(encoding="utf-8")
    assert 'gecko["strict_min_version"]' in quelle
    assert not re.search(r'strict_min_version"\]\s*=\s*"', quelle), (
        "xpi_updates.py setzt die Mindestfassung selbst — dann gibt es zwei Zahlen")
