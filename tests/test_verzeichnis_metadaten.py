"""Was Verzeichnisse von falzmarke lesen, gegen deren eigene Schemas.

WARUM ES DAS GIBT

Ein Fehler in `server.json` fällt erst im Release-Lauf auf, nach dem PyPI-Upload
(#365). Und ein schema-gültiger Eintrag kann trotzdem nicht starten: Bis zum
02.11.2026 stand im Registry nur das Paket, also `uvx falzmarke`. Das endet mit
Exit 2, weil der Unterbefehl `mcp` und das optionale SDK fehlen. Der Handschlag
unten spricht deshalb mit dem Prozess, den der Eintrag beschreibt.

Die Schemas liegen unter `tests/schemas/`; ihre Herkunft steht dort im README.
Jede Prüfung hat eine Gegenprobe, die rot werden muss.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import tomllib
from urllib.parse import parse_qs, urlsplit

import jsonschema
import pytest
import yaml
from conftest import REPO

SCHEMAS = REPO / "tests" / "schemas"
SERVER_JSON = REPO / "server.json"
SKILL_MD = REPO / "skill" / "SKILL.md"
LISTINGS = REPO / "docs" / "listings.md"
HANDSCHLAG = REPO / "scripts" / "mcp_handschlag.py"
PACKER = REPO / "scripts" / "plugin_packen.py"

#: Dieselben sieben Ziele wie im Auftrag; die Reihenfolge ist die der Datei.
ZIELE = ["Anthropic-Plugin-Verzeichnis", "mcp.so", "Smithery", "Glama",
         "awesome-mcp-servers", "awesome-claude-skills", "GitHub Topics"]
MAX_EINREICHTEXT = 300

#: Der Vorbehalt, ohne den kein Kanal live geht (ADR 0032, tests/test_textkanon.py).
VORBEHALT_DE = "Sollwerte aus Sekundärquellen"
VORBEHALT_EN = "target values from secondary sources"

WEBSITE_LINK = re.compile(r"https?://(?:www\.)?falzmarke\.com[^\s)\"'>`]*")
KAMPAGNE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-20\d{2}(?:0[1-9]|1[0-2])$")
#: Zwei Paare, nicht vier Kombinationen: `listing` kommt aus einem Verzeichnis,
#: `footer` aus dem Produkt selbst.
UTM_PAARE = {("listing", "directory"), ("footer", "product")}


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _pruefer(name: str) -> jsonschema.Draft202012Validator:
    schema = _schema(name)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def _fehler(pruefer, objekt) -> list[str]:
    return [f"{'/'.join(map(str, f.path))}: {f.message}" for f in pruefer.iter_errors(objekt)]


def _server() -> dict:
    return json.loads(SERVER_JSON.read_text(encoding="utf-8"))


def _skill_kopf() -> dict:
    return yaml.safe_load(SKILL_MD.read_text(encoding="utf-8").split("---", 2)[1])


def _plugin_manifest() -> dict:
    spec = importlib.util.spec_from_file_location("falzmarke_plugin_packen", PACKER)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul.manifest(modul.projekt())


# ── MCP-Definition ──────────────────────────────────────────────────────────

def test_server_json_zeigt_auf_das_abgelegte_schema():
    """Sonst prüfte der Test unten gegen ein Schema, das niemand mehr liest."""
    assert _server()["$schema"].endswith("/2025-12-11/server.schema.json")


def test_server_json_gilt_nach_dem_schema():
    fehler = _fehler(_pruefer("mcp-server-2025-12-11.schema.json"), _server())
    assert not fehler, fehler


@pytest.mark.parametrize("sabotage, erwartet", [
    (lambda s: s.update(description="x" * 101), "too long"),
    (lambda s: s.pop("version"), "'version' is a required property"),
    (lambda s: s["packages"][0]["packageArguments"][0].pop("value"), "not valid under any"),
], ids=["beschreibung-zu-lang", "version-fehlt", "argument-ohne-wert"])
def test_gegenprobe_schema_der_mcp_definition(sabotage, erwartet):
    kaputt = copy.deepcopy(_server())
    sabotage(kaputt)
    meldung = str(_fehler(_pruefer("mcp-server-2025-12-11.schema.json"), kaputt))
    assert erwartet in meldung, meldung


def _startbefehl(paket: dict) -> list[str]:
    """Der Prozess, den ein Client aus dem Paketeintrag baut, ohne `uvx`.

    `uvx` holt das Paket aus dem Netz; hier läuft der Stand aus dem Repository.
    Was der Eintrag entscheidet, bleibt gleich: die Argumente hinter dem Paket.
    """
    start = "import sys; from falzmarke.cli import main; sys.exit(main())"
    return [sys.executable, "-c", start,
            *(a["value"] for a in paket.get("packageArguments", []))]


def _handschlag(paket: dict) -> subprocess.CompletedProcess:
    pytest.importorskip("mcp")
    return subprocess.run(
        [sys.executable, str(HANDSCHLAG), "--ohne-render", "--", *_startbefehl(paket)],
        capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        env={**os.environ, "PYTHONPATH": str(REPO / "skill"), "PYTHONUTF8": "1"},
    )


def test_der_eintrag_startet_den_mcp_dienst():
    lauf = _handschlag(_server()["packages"][0])
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert "tools/list" in lauf.stdout


def test_gegenprobe_ohne_paketargument_startet_kein_dienst():
    """Genau der Stand bis zum 02.11.2026: Der Eintrag nannte nur das Paket."""
    paket = copy.deepcopy(_server()["packages"][0])
    del paket["packageArguments"]
    lauf = _handschlag(paket)
    assert lauf.returncode != 0, lauf.stdout + lauf.stderr


def test_der_eintrag_zieht_das_sdk_mit_der_pyproject_grenze():
    """`mcp` ist ein Extra. Ohne `--with` fehlt es im Lauf von uvx.

    Soll ist `pyproject.toml`, nicht `server.json`: Zieht jemand die Grenze dort
    nach, wird dieser Test rot, statt mit der Änderung mitzuwandern.
    """
    extra = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    soll = extra["project"]["optional-dependencies"]["mcp"]
    argumente = _server()["packages"][0]["runtimeArguments"]
    ist = [a["value"] for a in argumente if a["name"] == "--with"]
    assert ist == soll, f"server.json zieht {ist}, pyproject.toml verlangt {soll}"


# ── Skill-Manifest ──────────────────────────────────────────────────────────

def test_skill_kopf_gilt_nach_der_spezifikation():
    fehler = _fehler(_pruefer("skill-frontmatter.schema.json"), _skill_kopf())
    assert not fehler, fehler


def test_skill_kopf_traegt_name_version_und_lizenz():
    kopf = _skill_kopf()
    assert kopf["name"] == "falzmarke"
    assert kopf["license"] == "MIT"
    assert kopf["metadata"]["version"]


@pytest.mark.parametrize("sabotage, erwartet", [
    (lambda k: k.update(version="1.0"), "Additional properties"),
    (lambda k: k.update(description="x" * 1025), "too long"),
    (lambda k: k["metadata"].update(version=1.0), "is not of type 'string'"),
    (lambda k: k.update(name="Falzmarke"), "does not match"),
], ids=["version-oben", "beschreibung-zu-lang", "version-als-zahl", "name-gross"])
def test_gegenprobe_skill_schema(sabotage, erwartet):
    kaputt = copy.deepcopy(_skill_kopf())
    sabotage(kaputt)
    meldung = str(_fehler(_pruefer("skill-frontmatter.schema.json"), kaputt))
    assert erwartet in meldung, meldung


# ── Plugin-Manifest für ChatGPT (Agent Plugins 1.0.0) ───────────────────────

def test_plugin_manifest_gilt_nach_dem_schema():
    mani = _plugin_manifest()
    assert mani["$schema"] == _schema("agent-plugins-1.0.0.schema.json")["$id"]
    fehler = _fehler(_pruefer("agent-plugins-1.0.0.schema.json"), mani)
    assert not fehler, fehler


def test_gegenprobe_plugin_schema():
    kaputt = copy.deepcopy(_plugin_manifest())
    kaputt["autor"] = "unbekanntes Feld"
    meldung = str(_fehler(_pruefer("agent-plugins-1.0.0.schema.json"), kaputt))
    assert "Additional properties" in meldung, meldung


# ── Listing-Texte ───────────────────────────────────────────────────────────

def _abschnitte() -> dict[str, str]:
    """`## <Ziel>`-Abschnitte aus docs/listings.md."""
    text = LISTINGS.read_text(encoding="utf-8")
    teile = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return {titel.strip(): rumpf for titel, rumpf in zip(teile[1::2], teile[2::2])}


def _einreichtexte(rumpf: str) -> dict[str, str]:
    muster = r"^\*\*Text (de|en)\*\*\n\n```text\n(.*?)\n```$"
    return dict(re.findall(muster, rumpf, re.MULTILINE | re.DOTALL))


def _alle_texte() -> list[tuple[str, str, str]]:
    abschnitte = _abschnitte()
    return [(ziel, sprache, text)
            for ziel in ZIELE
            for sprache, text in _einreichtexte(abschnitte[ziel]).items()]


def test_jedes_ziel_hat_seinen_abschnitt_mit_url_und_konto():
    abschnitte = _abschnitte()
    for ziel in ZIELE:
        assert ziel in abschnitte, f"docs/listings.md: Abschnitt „{ziel}“ fehlt"
        assert "**Ziel-URL:**" in abschnitte[ziel], ziel
        assert "**Konto:**" in abschnitte[ziel], ziel


def test_jedes_ziel_ausser_den_topics_hat_beide_sprachen():
    """GitHub Topics nehmen Schlagwörter, keinen Text; alle anderen beide Sprachen."""
    abschnitte = _abschnitte()
    for ziel in ZIELE:
        if ziel != "GitHub Topics":
            assert set(_einreichtexte(abschnitte[ziel])) == {"de", "en"}, ziel


def test_einreichtexte_bleiben_unter_der_grenze():
    texte = _alle_texte()
    assert len(texte) >= 12, f"nur {len(texte)} Einreichtexte gefunden"
    zu_lang = [(z, s, len(t)) for z, s, t in texte if len(t) > MAX_EINREICHTEXT]
    assert not zu_lang, zu_lang


def test_einreichtexte_tragen_den_vorbehalt():
    fehlend = [(z, s) for z, s, t in _alle_texte()
               if (VORBEHALT_DE if s == "de" else VORBEHALT_EN) not in t]
    assert not fehlend, f"Ohne Vorbehalt geht kein Kanal live (ADR 0032): {fehlend}"


def test_gegenprobe_die_textsuche_findet_bloecke():
    rumpf = "**Text de**\n\n```text\nAbc\n```\n\n**Text en**\n\n```text\nDef\n```\n"
    assert _einreichtexte(rumpf) == {"de": "Abc", "en": "Def"}
    assert _einreichtexte("**Text de**\n\nAbc\n") == {}


# ── UTM-Konvention ──────────────────────────────────────────────────────────

def utm_fehler(url: str) -> list[str]:
    """Was an einem Website-Link gegen die Konvention verstößt."""
    abfrage = parse_qs(urlsplit(url).query)
    paar = (abfrage.get("utm_source", [""])[0], abfrage.get("utm_medium", [""])[0])
    fehler = []
    if paar not in UTM_PAARE:
        fehler.append(f"utm_source/utm_medium {paar}")
    if not KAMPAGNE.match(abfrage.get("utm_campaign", [""])[0]):
        fehler.append(f"utm_campaign {abfrage.get('utm_campaign')}")
    return fehler


@pytest.mark.parametrize("datei, mindestens", [
    ("README.md", 2), ("skill/SKILL.md", 0), ("docs/listings.md", 6),
])
def test_website_links_tragen_die_utm_parameter(datei, mindestens):
    links = WEBSITE_LINK.findall((REPO / datei).read_text(encoding="utf-8"))
    assert len(links) >= mindestens, f"{datei}: nur {len(links)} Website-Links gefunden"
    falsch = {url: utm_fehler(url) for url in links if utm_fehler(url)}
    assert not falsch, falsch


@pytest.mark.parametrize("url", [
    "https://falzmarke.com",
    "https://falzmarke.com/?utm_source=listing&utm_medium=product&utm_campaign=x-202611",
    "https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=glama",
    "https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=x-202613",
    "https://falzmarke.com/?utm_source=reddit&utm_medium=directory&utm_campaign=x-202611",
], ids=["ohne", "paar-gekreuzt", "ohne-datum", "monat-13", "quelle-fremd"])
def test_gegenprobe_utm_pruefung(url):
    assert utm_fehler(url), f"{url} hätte beanstandet werden müssen"


def test_utm_pruefung_laesst_die_konvention_durch():
    url = "https://falzmarke.com/?utm_source=footer&utm_medium=product&utm_campaign=readme-202611"
    assert utm_fehler(url) == []


def test_deutscher_claim_bleibt_im_readme():
    """Der englische Abschnitt ergänzt den Claim, er ersetzt ihn nicht."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    claim = readme.index("**Andere Werkzeuge erzeugen ein PDF. falzmarke prüft das Ergebnis.**")
    englisch = readme.index("**DIN 5008 business letters from Markdown, PDF/A, MCP + CLI.**")
    assert claim < englisch
