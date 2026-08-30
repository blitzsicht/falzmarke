"""pyproject.toml, requirements.txt und bootstrap.DEPS duerfen nicht auseinanderlaufen (#194).

`pyproject.toml` ist die kanonische Quelle der Laufzeitabhängigkeiten. Zwei weitere Stellen
tragen dieselbe Liste noch einmal von Hand: `skill/requirements.txt` (installiert die CI und
ein manuelles `pip install -r`) und `DEPS` in `skill/scripts/bootstrap.py` (installiert der
Bootstrap ohne Netz aus `vendor/`). Bisher konnte eine dieser drei Stellen eine Abhängigkeit
verlieren oder gewinnen, ohne dass etwas rot wurde — genau das ist `pillow` passiert: Es stand
in `pyproject.toml`, fehlte aber in den beiden anderen, und die CI blieb grün, weil `pdfplumber`
es transitiv mitbrachte.

`tests/test_vendor.py` prüft nur, dass zwei bestimmte Pakete *genannt* sind — kein
Listenvergleich. Dieser Test hält alle drei Quellen gegeneinander.
"""

from __future__ import annotations

import importlib.util
import re
import tomllib

from conftest import REPO

PYPROJECT = REPO / "pyproject.toml"
REQUIREMENTS = REPO / "skill" / "requirements.txt"
BOOTSTRAP = REPO / "skill" / "scripts" / "bootstrap.py"

# Anfang einer PEP-508-Anforderung: der Paketname, vor Version/Marker/Extras.
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def _name(anforderung: str) -> str:
    """Paketname aus einer Requirement-Zeile, PEP-503-normalisiert."""
    treffer = _NAME.match(anforderung.strip())
    assert treffer, f"keine gueltige Abhängigkeitsangabe: {anforderung!r}"
    return re.sub(r"[-_.]+", "-", treffer.group(0)).lower()


def _namen_aus_pyproject_text(text: str) -> set[str]:
    daten = tomllib.loads(text)
    return {_name(z) for z in daten["project"]["dependencies"]}


def _namen_aus_requirements_text(text: str) -> set[str]:
    return {_name(z) for z in text.splitlines() if z.strip() and not z.strip().startswith("#")}


def _bootstrap_modul():
    """`skill/scripts/` liegt nicht im sys.path — die Datei wird direkt geladen."""
    spec = importlib.util.spec_from_file_location("falzmarke_bootstrap_abgleich", BOOTSTRAP)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _namen_aus_deps(deps: dict[str, str]) -> set[str]:
    return {_name(z) for z in deps.values()}


def _abweichungen(kanon: set[str], andere: set[str], quelle: str) -> list[str]:
    meldungen = []
    fehlt = kanon - andere
    zusaetzlich = andere - kanon
    if fehlt:
        meldungen.append(f"{quelle}: es fehlt {', '.join(sorted(fehlt))}")
    if zusaetzlich:
        meldungen.append(f"{quelle}: zusätzlich genannt {', '.join(sorted(zusaetzlich))}")
    return meldungen


def test_pyproject_nennt_wirklich_mehrere_abhaengigkeiten():
    """Ohne diese Zeile wäre der Vergleich unten bei einer leeren Menge still grün."""
    kanon = _namen_aus_pyproject_text(PYPROJECT.read_text(encoding="utf-8"))
    assert len(kanon) >= 5, kanon
    assert "pillow" in kanon


def test_requirements_und_deps_nennen_dieselben_pakete_wie_pyproject():
    kanon = _namen_aus_pyproject_text(PYPROJECT.read_text(encoding="utf-8"))
    aus_requirements = _namen_aus_requirements_text(REQUIREMENTS.read_text(encoding="utf-8"))
    aus_deps = _namen_aus_deps(_bootstrap_modul().DEPS)

    meldungen = (
        _abweichungen(kanon, aus_requirements, "skill/requirements.txt")
        + _abweichungen(kanon, aus_deps, "skill/scripts/bootstrap.py DEPS")
    )
    assert not meldungen, "\n".join(meldungen)


def test_die_pruefung_wuerde_ein_fehlendes_paket_bemerken():
    """Gegenprobe: `pillow` aus requirements.txt streichen, ohne die Datei anzufassen.

    Ohne diesen Test belegt der Vergleich oben nur, dass gerade nichts fehlt — nicht, dass er
    eine echte Lücke auch findet und beim Namen nennt.
    """
    kanon = _namen_aus_pyproject_text(PYPROJECT.read_text(encoding="utf-8"))
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert "pillow>=10" in text, "Testannahme verletzt: pillow steht nicht (mehr) so in requirements.txt"
    saboliert = text.replace("pillow>=10\n", "")
    assert saboliert != text, "die Sabotage greift nicht — der Anker fehlt"

    meldungen = _abweichungen(kanon, _namen_aus_requirements_text(saboliert), "skill/requirements.txt")
    assert meldungen, "die Prüfung hat die Lücke nicht bemerkt"
    assert "pillow" in meldungen[0], meldungen


def test_die_pruefung_wuerde_ein_zusaetzliches_paket_bemerken():
    """Gegenprobe in die andere Richtung: ein Paket, das nur in einer Nebenliste steht."""
    kanon = _namen_aus_pyproject_text(PYPROJECT.read_text(encoding="utf-8"))
    deps = dict(_bootstrap_modul().DEPS)
    deps["erfunden"] = "erfundenes-paket>=1"

    meldungen = _abweichungen(kanon, _namen_aus_deps(deps), "skill/scripts/bootstrap.py DEPS")
    assert meldungen, "die Prüfung hat das zusätzliche Paket nicht bemerkt"
    assert "erfundenes-paket" in meldungen[0], meldungen
