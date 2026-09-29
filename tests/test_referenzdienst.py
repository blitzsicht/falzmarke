"""Der öffentliche Referenzdienst liefert Maße und Regeln — und nichts vom Nutzer.

Zwei Zusagen, beide hier festgehalten:

1. Er gibt die Werte aus, die falzmarke selbst prüft. Die Erwartung steht hier
   als Zahl, nicht aus geometrie.py gelesen — ein Sollwert, der gegen sich
   selbst geprüft wird, bleibt bei jeder Änderung grün.
2. Er nimmt keinen Text des Nutzers an. Sonst stimmte der Satz „keine
   personenbezogenen Daten auf unserem Server“ nicht mehr. Geprüft am Quelltext
   per `ast`, nicht per Textsuche: Die Prosa im Modul nennt `lint` ja gerade,
   um zu sagen, dass es fehlt.

Die Tests mit HTTP brauchen das MCP-SDK; die CI installiert es (ci.yml).
"""

from __future__ import annotations

import ast
import inspect
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from conftest import REPO
from falzmarke import referenzdienst as rd
from falzmarke import regeln

MODUL = REPO / "skill" / "falzmarke" / "referenzdienst.py"
EINSTIEG = REPO / "mcp-dienst" / "api" / "index.py"

#: Module, deren Import einen Brief oder Nutzertext verarbeiten würde.
VERBOTEN = {"falzmarke.lint", "falzmarke.cli", "falzmarke.render", "falzmarke.email",
            "falzmarke.pruefung", "typst", "pdfplumber", "pypdf", "PIL"}
#: Parameternamen, unter denen Text des Nutzers hereinkäme.
TEXTPARAMETER = {"brief", "text", "nachricht", "adresse", "inhalt", "markdown", "pdf"}


# ── Werte ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(("form", "feld", "soll"), [
    ("A", "kopfhoehe", 27.0), ("A", "falzmarke_1", 87.0), ("A", "falzmarke_2", 192.0),
    ("B", "kopfhoehe", 45.0), ("B", "falzmarke_1", 105.0), ("B", "falzmarke_2", 210.0),
    ("B", "anschrift_zone", [62.7, 90.0]),
])
def test_sollwerte_stimmen(form, feld, soll):
    assert rd.sollwerte(form)["masse"][feld] == soll


def test_lochmarke_steht_bei_beiden_formen():
    assert rd.sollwerte("A")["gemeinsam"]["lochmarke"] == 148.5


def test_unbekannte_form_ist_eine_auskunft():
    with pytest.raises(rd.Unbekannt, match="erlaubt sind A, B"):
        rd.sollwerte("C")


def test_die_liste_nennt_jede_regel():
    liste = rd.regeln_auflisten()
    assert liste["anzahl"] == len(regeln.alle()) > 0
    assert {r["id"] for r in liste["regeln"]} == {r["id"] for r in regeln.alle()}


def test_bereich_filtert():
    liste = rd.regeln_auflisten("geometrie.form_b")
    assert liste["anzahl"] > 0
    assert all(r["id"].startswith("geometrie.form_b") for r in liste["regeln"])


def test_unbekannter_bereich_nennt_die_vorhandenen():
    with pytest.raises(rd.Unbekannt, match="Bereiche: .*geometrie"):
        rd.regeln_auflisten("gibtsnicht")


def test_eine_regel_kommt_mit_ihren_quellen():
    erklaert = rd.regel_erklaeren("geometrie.form_b.briefkopf")
    assert erklaert["titel"].startswith("Briefkopfhöhe Form B")
    assert erklaert["quellen"], "keine Quelle genannt"
    assert all(q["titel"] for q in erklaert["quellen"])


def test_jede_antwort_nennt_die_quellenlage():
    """Ein Werkzeug, das Maße ausgibt, sagt auch, wie belastbar sie sind."""
    kern = "der Abgleich mit dem Originaltext der DIN 5008:2020-03"
    for antwort in (rd.sollwerte("B"), rd.regeln_auflisten(),
                    rd.regel_erklaeren("geometrie.form_b.briefkopf")):
        assert kern in antwort["quellenlage"]


# ── Keine Nutzerdaten ───────────────────────────────────────────────────────

def _importe(pfad: Path) -> set[str]:
    baum = ast.parse(pfad.read_text(encoding="utf-8"))
    namen = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            namen |= {a.name for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom) and knoten.module:
            namen.add(knoten.module)
            namen |= {f"{knoten.module}.{a.name}" for a in knoten.names}
    return namen


def test_der_dienst_importiert_nichts_was_briefe_verarbeitet():
    treffer = sorted(n for n in _importe(MODUL)
                     if any(n == v or n.startswith(v + ".") for v in VERBOTEN))
    assert not treffer, f"Der Referenzdienst importiert {treffer}"


def test_kein_werkzeug_nimmt_text_des_nutzers():
    for werkzeug in rd.WERKZEUGE:
        parameter = set(inspect.signature(werkzeug).parameters)
        assert not parameter & TEXTPARAMETER, (
            f"{werkzeug.__name__} nimmt {parameter & TEXTPARAMETER} — "
            "dann landen Nutzerdaten auf dem Server")


# ── Angaben für OpenAI ──────────────────────────────────────────────────────

def test_jede_annotation_hat_eine_begruendung():
    """OpenAI verlangt readOnlyHint, openWorldHint und destructiveHint je Werkzeug,
    jeweils begründet (Fehlercodes annotations_required, justification_required)."""
    assert rd.ANNOTATIONEN["read_only_hint"] is True
    assert rd.ANNOTATIONEN["open_world_hint"] is False
    assert rd.ANNOTATIONEN["destructive_hint"] is False
    assert set(rd.BEGRUENDUNG) == {"readOnlyHint", "openWorldHint", "destructiveHint"}
    assert all(rd.BEGRUENDUNG.values())


# ── Über HTTP, wie ein Client ihn sieht ─────────────────────────────────────

def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def dienst(monkeypatch):
    """Startet den echten Dienst mit uvicorn — kein Testclient: httpx gehört
    nicht zu den Abhängigkeiten des SDK, der Test liefe in der CI ins Leere."""
    pytest.importorskip("mcp", reason="optionales Extra falzmarke[mcp]")
    import uvicorn

    monkeypatch.setenv(rd.CHALLENGE_VARIABLE, "probe-token")
    port = _freier_port()
    server = uvicorn.Server(uvicorn.Config(rd.asgi_app(), host="127.0.0.1", port=port,
                                           log_level="warning"))
    faden = threading.Thread(target=server.run, daemon=True)
    faden.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "der Dienst ist nicht angelaufen"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    faden.join(timeout=5)


def _rpc(basis: str, methode: str, params: dict, host: str | None = None):
    anfrage = urllib.request.Request(
        basis + "/mcp",
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": methode,
                         "params": params}).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream",
                 "MCP-Protocol-Version": "2025-06-18",
                 **({"Host": host} if host else {})})
    try:
        with urllib.request.urlopen(anfrage, timeout=10) as antwort:
            return antwort.status, json.loads(antwort.read())
    except urllib.error.HTTPError as fehler:
        return fehler.code, None


def test_ueber_http_kommen_drei_werkzeuge_mit_annotations(dienst):
    status, antwort = _rpc(dienst, "tools/list", {})
    assert status == 200
    werkzeuge = {t["name"]: t for t in antwort["result"]["tools"]}
    assert set(werkzeuge) == {w.__name__ for w in rd.WERKZEUGE}
    for name, werkzeug in werkzeuge.items():
        hinweise = werkzeug.get("annotations") or {}
        for feld in ("readOnlyHint", "openWorldHint", "destructiveHint"):
            assert feld in hinweise, f"{name}: {feld} fehlt"


def test_ueber_http_liefert_ein_aufruf_die_masse(dienst):
    status, antwort = _rpc(dienst, "tools/call",
                           {"name": "sollwerte", "arguments": {"form": "B"}})
    assert status == 200
    inhalt = json.loads(antwort["result"]["content"][0]["text"])
    assert inhalt["masse"]["kopfhoehe"] == 45.0


def test_ueber_http_ist_eine_unbekannte_regel_eine_meldung(dienst):
    _, antwort = _rpc(dienst, "tools/call",
                      {"name": "regel_erklaeren", "arguments": {"id": "gibts.nicht"}})
    assert antwort["result"]["isError"] is True
    assert "gibt es nicht" in antwort["result"]["content"][0]["text"]


def test_fremder_host_wird_abgewiesen(dienst):
    status, _ = _rpc(dienst, "tools/list", {}, host="boese.example")
    assert status == 421


def test_der_nachweis_liefert_den_token(dienst):
    with urllib.request.urlopen(dienst + rd.CHALLENGE_PFAD, timeout=5) as antwort:
        assert antwort.read().decode() == "probe-token"


def test_ohne_token_gibt_es_keinen_nachweis(monkeypatch):
    pytest.importorskip("mcp", reason="optionales Extra falzmarke[mcp]")
    import uvicorn

    monkeypatch.delenv(rd.CHALLENGE_VARIABLE, raising=False)
    port = _freier_port()
    server = uvicorn.Server(uvicorn.Config(rd.asgi_app(), host="127.0.0.1", port=port,
                                           log_level="warning"))
    faden = threading.Thread(target=server.run, daemon=True)
    faden.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        with pytest.raises(urllib.error.HTTPError) as fehler:
            urllib.request.urlopen(f"http://127.0.0.1:{port}{rd.CHALLENGE_PFAD}", timeout=5)
        assert fehler.value.code == 404
    finally:
        server.should_exit = True
        faden.join(timeout=5)


def test_der_einstieg_fuer_vercel_findet_den_dienst():
    pytest.importorskip("mcp", reason="optionales Extra falzmarke[mcp]")
    import importlib.util

    spec = importlib.util.spec_from_file_location("vercel_einstieg", EINSTIEG)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    assert callable(modul.app)


# ── Was wirklich geladen wird, und was nach Vercel geht ─────────────────────
# Der ast-Test oben sieht nur direkte Importe. Am 29.09.2026 importierte der
# Dienst `_mcp_modul` aus `dienst` — und zog damit cli, lint, markdown und emit
# in den Prozess, ohne dass der ast-Test anschlug. Gemessen wird deshalb auch
# zur Laufzeit, in einem frischen Interpreter.

ERLAUBT = {"falzmarke", "falzmarke.geometrie", "falzmarke.regeln", "falzmarke.referenzdienst"}
PACKER = REPO / "mcp-dienst" / "packen.sh"

_PROBE = """
import sys, json
sys.path.insert(0, sys.argv[1])
vorher = set(sys.modules)
import falzmarke
from falzmarke import referenzdienst as rd
rd.sollwerte("B"); rd.regeln_auflisten(); rd.regel_erklaeren("geometrie.form_b.briefkopf")
try:
    import mcp  # noqa: F401
    rd.asgi_app()
    mit_mcp = True
except ImportError:
    mit_mcp = False
print(json.dumps({"datei": falzmarke.__file__, "mit_mcp": mit_mcp,
                  "geladen": sorted(m for m in set(sys.modules) - vorher
                                    if m.split(".")[0] == "falzmarke")}))
"""


def _probe(pfad: Path) -> dict:
    import subprocess
    import sys

    lauf = subprocess.run([sys.executable, "-c", _PROBE, str(pfad)], capture_output=True,
                          text=True, encoding="utf-8", check=False)
    assert lauf.returncode == 0, lauf.stderr[-1500:]
    return json.loads(lauf.stdout.strip().splitlines()[-1])


def test_zur_laufzeit_laedt_der_dienst_nur_seine_vier_module():
    ergebnis = _probe(REPO / "skill")
    zu_viel = set(ergebnis["geladen"]) - ERLAUBT
    assert not zu_viel, f"Der Dienst lädt zusätzlich {sorted(zu_viel)}"


def test_der_gepackte_stand_laeuft_fuer_sich_allein(tmp_path):
    """Genau das, was nach Vercel geht, in einem frischen Interpreter — ohne
    Quellbaum daneben. Fehlt beim Packen eine Datei, bricht es hier."""
    import subprocess
    import sys

    if sys.platform.startswith("win"):
        pytest.skip("bash — der Nachweis läuft auf den anderen beiden Plattformen")
    ziel = tmp_path / "_skill"
    lauf = subprocess.run(["bash", str(PACKER), str(ziel)], capture_output=True, text=True,
                          encoding="utf-8", check=False)
    assert lauf.returncode == 0, lauf.stderr
    ergebnis = _probe(ziel)
    assert Path(ergebnis["datei"]).resolve().is_relative_to(ziel.resolve()), (
        f"geladen wurde {ergebnis['datei']}, nicht der gepackte Stand")
