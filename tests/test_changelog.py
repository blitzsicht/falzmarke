"""Der Verlauf in der README ist eine Sicht auf CHANGELOG.md, keine zweite Fassung.

Anlass: Ein Changelog in der README ist bequem zu lesen — und driftet, sobald er
von Hand gepflegt wird. Wie weit das geht, zeigt dieses Repository an sich
selbst: `CHANGELOG.md` endet bei v0.6.0, veröffentlicht sind v0.7.0 und v0.7.1.
Zwei Fassungen desselben Verlaufs waeren derselbe Fehler noch einmal.

Der Abschnitt wird deshalb erzeugt (`scripts/changelog.py`), und hier wird
nachgehalten, dass er auf dem Stand ist und dass dabei nichts still unter den
Tisch faellt.
"""

from __future__ import annotations

import re
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import changelog                                                # noqa: E402


@pytest.fixture
def readme() -> str:
    return changelog.ZIEL.read_text(encoding="utf-8")


def _auszug(readme: str) -> str:
    anfang = readme.index(changelog.MARKE_START)
    ende = readme.index(changelog.MARKE_ENDE)
    return readme[anfang:ende]


def test_die_readme_ist_auf_dem_stand_des_changelogs(readme):
    assert changelog.eingesetzt(readme) == readme, (
        "Der Abschnitt in der README passt nicht mehr zu CHANGELOG.md.\n"
        "Neu erzeugen: python3 scripts/changelog.py"
    )


def test_kein_punkt_faellt_unter_den_tisch(readme):
    """Alle Punkte der gezeigten Versionen stehen auch im Auszug.

    Das ist eine Aktualitaetspruefung, kein Nachweis der Vollstaendigkeit: Beide
    gezeigten Versionen setzen jeden Punkt fett, also faende auch eine
    Kurzfassung „nur die fetten Anfaenge“ hier nichts zum Weglassen. Den Nachweis
    fuehrt test_ein_schmuckloser_punkt_ueberlebt_den_auszug.
    """
    auszug = _auszug(readme)
    alle = changelog.versionen(changelog.QUELLE.read_text(encoding="utf-8"))
    fehlend = [
        zeile.strip()
        for _, rumpf in alle[:changelog.VERSIONEN]
        for zeile in rumpf.splitlines()
        if zeile.startswith("- ") and zeile.strip() not in auszug
    ]
    assert not fehlend, (
        f"{len(fehlend)} Punkte stehen in CHANGELOG.md, aber nicht im Auszug:\n  "
        + "\n  ".join(fehlend[:5])
    )


def test_ein_schmuckloser_punkt_ueberlebt_den_auszug(tmp_path, monkeypatch):
    """Ein Punkt ohne fett gesetzten Anfang darf nicht verschwinden.

    Der naheliegende Weg zu einem kuerzeren Auszug waere gewesen, je Punkt nur
    den fetten Anfang zu uebernehmen. In CHANGELOG.md haben 19 der 73 Punkte
    keinen — alle in v0.2 und v0.3, also ausserhalb dessen, was der Auszug heute
    zeigt. Gegen die echte Datei liefe eine solche Kuerzung deshalb unbemerkt
    durch. Diese Pruefung stellt die Lage her, in der es auffaellt.
    """
    quelle = tmp_path / "CHANGELOG.md"
    quelle.write_text(
        "# Änderungen\n\n## v9.9.9 — 01.01.2027\n\n### Neu\n"
        "- **Mit fettem Anfang.** Erklärung.\n"
        "- Ohne fetten Anfang, nur ein Satz.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(changelog, "QUELLE", quelle)
    assert "- Ohne fetten Anfang, nur ein Satz." in changelog.abschnitt(), (
        "Ein Punkt ohne fett gesetzten Anfang steht nicht im Auszug — die Kürzung "
        "verschluckt ihn still."
    )


def test_die_ueberschriften_ordnen_sich_der_readme_unter(readme):
    """Jede Überschrift aus dem Changelog liegt unter der ihrer Version.

    Geprüft wird die Ebene, nicht nur das Vorkommen von `## `: Ohne das Anheben
    stünde `### Neu` auf derselben Ebene wie `### v0.6.0` und läse sich als
    Schwester der Version statt als deren Rubrik. Genau das ist die erste
    Fassung dieser Prüfung durchgelassen — sie sah nur nach `## ` und blieb
    grün, während der Auszug bereits falsch verschachtelt war.
    """
    ebenen = [
        (len(zeile) - len(zeile.lstrip("#")), zeile.strip())
        for zeile in _auszug(readme).splitlines()
        if zeile.startswith("#")
    ]
    assert ebenen[0] == (2, "## Was sich zuletzt getan hat"), ebenen[:1]

    version = None
    for ebene, zeile in ebenen[1:]:
        if re.match(r"^#+ v\d+\.\d+\.\d+", zeile):
            assert ebene == 3, f"Versionsüberschrift auf Ebene {ebene}: {zeile}"
            version = ebene
            continue
        assert version is not None, f"Rubrik „{zeile}“ steht vor jeder Version"
        assert ebene > version, (
            f"„{zeile}“ liegt auf Ebene {ebene}, die Version darüber auf {version} — "
            "die Rubrik liest sich damit als eigener Abschnitt neben der Version."
        )


def test_eine_aenderung_am_changelog_faellt_auf(tmp_path, monkeypatch, readme):
    """Gegenprobe: Ohne sie belegte der Aktualitätstest nur, dass zwei Dateien existieren."""
    # Eine ganze Version oben anfuegen statt eine Rubrik zu treffen: „### Neu“
    # gibt es nicht in jeder Version. Genau daran ist diese Gegenprobe nach dem
    # Merge von v0.7.x einmal gescheitert — sie ersetzte nichts und war deshalb
    # gruen, ohne etwas zu belegen.
    quelle = changelog.QUELLE.read_text(encoding="utf-8")
    kopf = changelog.VERSION_KOPF.search(quelle)
    assert kopf, "CHANGELOG.md hat keine Versionsüberschrift — dann greift hier nichts"
    gefaelscht = tmp_path / "CHANGELOG.md"
    gefaelscht.write_text(
        quelle[:kopf.start()]
        + "## v99.0.0 — 01.01.2099\n\n### Neu\n- **Ein Punkt, den die README nicht kennt.**\n\n"
        + quelle[kopf.start():],
        encoding="utf-8",
    )
    monkeypatch.setattr(changelog, "QUELLE", gefaelscht)
    assert changelog.eingesetzt(readme) != readme, (
        "Ein zusätzlicher Punkt in CHANGELOG.md ändert den Auszug nicht — "
        "der Aktualitätstest kann dann nicht rot werden."
    )


def test_eine_leere_quelle_bricht_ab_statt_zu_leeren(tmp_path, monkeypatch):
    """Ein leerer Abschnitt ist die teuerste Fehlerart: Er sieht aus wie „nichts passiert“."""
    leer = tmp_path / "CHANGELOG.md"
    leer.write_text("# Änderungen\n\nNoch nichts.\n", encoding="utf-8")
    monkeypatch.setattr(changelog, "QUELLE", leer)
    with pytest.raises(SystemExit) as fehler:
        changelog.abschnitt()
    assert "v1.2.3" in str(fehler.value)
