"""Die Version in pyproject.toml muss zum neuesten Release-Tag passen.

Anlass: Bei Release v0.1.1 stand dort noch `0.1.0.dev0`. Das fällt niemandem auf,
weil nichts davon abhängt — bis jemand das Paket installiert und sich über die
Version wundert, oder bis eine Fehlermeldung die falsche Version nennt.
"""

from __future__ import annotations

import re
import subprocess
import tomllib

import pytest

from conftest import REPO

PYPROJECT = REPO / "pyproject.toml"


def version_aus_pyproject(text: str | None = None) -> str:
    roh = text if text is not None else PYPROJECT.read_text(encoding="utf-8")
    return tomllib.loads(roh)["project"]["version"]


def neuester_tag() -> str | None:
    ergebnis = subprocess.run(
        ["git", "-C", str(REPO), "tag", "--list", "v*", "--sort=-v:refname"],
        capture_output=True, text=True, encoding="utf-8",
    )
    tags = [z for z in ergebnis.stdout.splitlines() if re.fullmatch(r"v\d+\.\d+\.\d+", z)]
    return tags[0] if tags else None


def test_paket_und_pyproject_nennen_dieselbe_version():
    """Zwei Quellen, ein Wert. Beim Wheel-Bau fiel auf, dass sie
    auseinanderlaufen können, ohne dass irgendetwas rot wird: pyproject stand
    auf 0.1.2, das Paket meldete 0.2.0."""
    from falzmarke import __version__

    assert __version__ == version_aus_pyproject(), (
        f"falzmarke/__init__.py sagt {__version__}, pyproject.toml "
        f"{version_aus_pyproject()}"
    )


def test_changelog_kennt_die_version():
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    version = version_aus_pyproject()
    assert f"## v{version}" in changelog, (
        f"CHANGELOG.md hat keinen Abschnitt für v{version} — "
        "eine Version ohne Eintrag ist eine unerklärte Änderung"
    )


def test_version_ist_eine_freigegebene_fassung():
    """Kein `.dev`, kein `.post` — was hier steht, wird ausgeliefert."""
    version = version_aus_pyproject()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
        f"Version '{version}' ist keine freigegebene Fassung"
    )


def als_tupel(version: str) -> tuple[int, ...]:
    return tuple(int(z) for z in version.split("."))


def test_version_laeuft_dem_tag_nicht_hinterher():
    """Voraus darf sie sein — das ist ein vorbereitetes Release. Hinterher nie:
    dann trägt ein veröffentlichter Stand eine Version, die es schon gab."""
    tag = neuester_tag()
    if tag is None:
        pytest.skip("keine Tags vorhanden (flacher Klon oder frisches Repo)")
    version = version_aus_pyproject()
    assert als_tupel(version) >= als_tupel(tag.lstrip("v")), (
        f"pyproject.toml steht auf {version}, veröffentlicht ist bereits {tag}.\n"
        "Beim Taggen die Version mitziehen — sonst laufen beide auseinander."
    )


def test_pruefung_wuerde_eine_falsche_version_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass gerade nichts kaputt ist."""
    kaputt = PYPROJECT.read_text(encoding="utf-8").replace(
        f'version = "{version_aus_pyproject()}"', 'version = "0.0.1.dev0"'
    )
    falsche = version_aus_pyproject(kaputt)
    assert falsche == "0.0.1.dev0"
    assert not re.fullmatch(r"\d+\.\d+\.\d+", falsche), "Die Formatprüfung schlägt hier nicht an"
    tag = neuester_tag()
    if tag is not None:
        assert als_tupel("0.0.1") < als_tupel(tag.lstrip("v")), (
            "Der Tag-Vergleich schlägt hier nicht an"
        )


# ── Die dritte Stelle: server.json fürs MCP-Registry (#237) ─────────────────

SERVER_JSON = REPO / "server.json"


def _server() -> dict:
    import json

    return json.loads(SERVER_JSON.read_text(encoding="utf-8"))


def test_server_json_nennt_dieselbe_version():
    """Seit #237 steht die Versionsnummer an einer dritten Stelle.

    Der Release-Workflow hält sie gegen den Tag; hier zählt pyproject, und zwar
    bei jedem Push. Sonst fiele die Abweichung erst am Tag auf — nach dem
    PyPI-Upload, der sich nicht zurücknehmen lässt.

    Zweimal geprüft, weil `server.json` die Nummer selbst zweimal trägt: oben
    für den Server, im Paketeintrag für das PyPI-Paket. Das Registry liest
    beide.
    """
    version = version_aus_pyproject()
    server = _server()
    assert server["version"] == version, (
        f"server.json sagt {server['version']}, pyproject.toml {version}")
    paket = server["packages"][0]
    assert paket["version"] == version, (
        f"server.json/packages sagt {paket['version']}, pyproject.toml {version}")


def test_server_json_nennt_das_eigene_paket():
    """Ein falscher `identifier` zeigte auf ein fremdes PyPI-Paket.

    Das Registry prüft die Eigentümerschaft über dessen Beschreibung — und
    fände dort die `mcp-name`-Zeile nicht. Der Befund käme also erst im
    Release-Lauf, und zwar als Fehlschlag nach dem Upload.
    """
    paket = _server()["packages"][0]
    assert paket["identifier"] == tomllib.loads(
        PYPROJECT.read_text(encoding="utf-8"))["project"]["name"]
    assert paket["registryType"] == "pypi"
    assert paket["transport"]["type"] == "stdio", "der Dienst spricht über stdio"


def test_das_readme_weist_den_servernamen_nach():
    """Die Eigentumsprüfung des Registry hängt an einer Zeile im README.

    Das Registry sucht `mcp-name: <servername>` in der Projektbeschreibung auf
    PyPI — und die ist `README.md`. Fehlt die Zeile oder weicht sie vom Namen
    in `server.json` ab, lehnt das Registry die Veröffentlichung ab. Das fiele
    ohne diesen Test erst im Release-Lauf auf, nach dem PyPI-Upload.

    Geprüft wird auch die **Grenze** dahinter: Das Registry verlangt nach dem
    Namen einen Zeilenumbruch, Leerraum, ein HTML-Tag oder das Kommentarende.
    Ein angeklebter Satzpunkt verhindert den Treffer.
    """
    name = _server()["name"]
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    treffer = re.search(r"mcp-name:\s*(\S+?)(?=\s|-->|<|$)", readme, re.M)
    assert treffer, "keine `mcp-name:`-Zeile in README.md"
    assert treffer.group(1) == name, (
        f"README.md nennt `{treffer.group(1)}`, server.json `{name}`")
