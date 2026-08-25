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
        capture_output=True, text=True,
    )
    tags = [z for z in ergebnis.stdout.splitlines() if re.fullmatch(r"v\d+\.\d+\.\d+", z)]
    return tags[0] if tags else None


def test_paket_und_pyproject_nennen_dieselbe_version():
    """Zwei Quellen, ein Wert. Beim Wheel-Bau fiel auf, dass sie
    auseinanderlaufen können, ohne dass irgendetwas rot wird: pyproject stand
    auf 0.1.2, das Paket meldete 0.2.0."""
    from normbrief import __version__

    assert __version__ == version_aus_pyproject(), (
        f"normbrief/__init__.py sagt {__version__}, pyproject.toml "
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
