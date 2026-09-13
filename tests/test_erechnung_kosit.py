"""Der KoSIT-Validator als zweiter Prüfer für XRechnung (#311).

Kein Test startet Java. Der Validator wird nachgestellt: Er schreibt einen
Bericht in das Ausgabeverzeichnis, wie es der echte tut — gekürzt aus einem
Bericht von KoSIT Validator 1.6.3 mit der Konfiguration 2026-08-31.
Geprüft wird, dass das Skript das Urteil aus dem BERICHT liest, die Regel der
Gegenprobe darin sucht und ein ausgefallenes Werkzeug nicht grün meldet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))
import erechnung_kosit as ek  # noqa: E402

CI = REPO / ".github" / "workflows" / "ci.yml"

BERICHT = """<?xml version="1.0" encoding="UTF-8"?><rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1" xmlns:s="http://www.xoev.de/de/validator/framework/1/scenarios" xmlns:svrl="http://purl.oclc.org/dsdl/svrl" valid="{valid}"><rep:engine><rep:name>KoSIT Validator 1.6.3</rep:name></rep:engine><rep:scenarioMatched><s:scenario><s:name>{szenario}</s:name></s:scenario>{befunde}</rep:scenarioMatched><rep:assessment><rep:{urteil}/></rep:assessment></rep:report>"""


def _bericht(urteil="accept", szenario="EN16931 XRechnung (CII)", regeln=()):
    # Aufbau aus einem echten Bericht abgeschrieben (13.09.2026): Die Regel steht als
    # `rep:message` mit `code` und `level`. Eine erste Fassung dieses Nachbaus nutzte
    # `svrl:failed-assert` — genau wie das Skript damals — und konnte deshalb nicht
    # zeigen, dass beide falsch lagen.
    befunde = "".join(
        f'<rep:validationStepResult id="val-sch.2" valid="false"><rep:message id="val-sch.2.1" '
        f'level="error" code="{r}">[{r}] …</rep:message></rep:validationStepResult>'
        for r in regeln)
    return BERICHT.format(valid="true" if urteil == "accept" else "false",
                          szenario=szenario, befunde=befunde, urteil=urteil)


def _validator(berichte: dict[str, str], java_ok=True, exit_code=None):
    """Stellt Java und den Validator nach. `berichte`: Dateiname -> Berichtstext."""
    def ausfuehren(befehl):
        if befehl[1:] == ["-version"]:
            return (0 if java_ok else 1), "openjdk"
        ziel = Path(befehl[befehl.index("-o") + 1])
        datei = Path(befehl[-1])
        text = berichte.get(datei.name)
        if text is not None:
            (ziel / f"{datei.stem}-report.xml").write_text(text, encoding="utf-8")
        code = exit_code if exit_code is not None else (0 if text and "<rep:accept" in text else 1)
        return code, "Results: …"
    return ausfuehren


@pytest.fixture
def werkzeug(tmp_path, monkeypatch):
    jar = tmp_path / "validator.jar"
    jar.write_bytes(b"jar")
    konf = tmp_path / "konf"
    konf.mkdir()
    (konf / "scenarios.xml").write_text(
        '<scenarios xmlns="http://www.xoev.de/de/validator/framework/1/scenarios">'
        "<name>Validator Configuration XRechnung 3.0.2</name></scenarios>", encoding="utf-8")
    monkeypatch.setattr(ek, "VALIDATOR_SHA256", ek.sha256(jar))
    return jar, konf


def _dateien(tmp_path, *namen):
    pfade = []
    for name in namen:
        p = tmp_path / name
        p.write_bytes(b"<x/>")
        pfade.append(p)
    return pfade


def _lauf(werkzeug, gut, schlecht, ausfuehren):
    jar, konf = werkzeug
    return ek.main(["--validator", str(jar), "--konfiguration", str(konf),
                    "--gut", *map(str, gut), "--schlecht", *schlecht], ausfuehren=ausfuehren)


def test_alles_wie_erwartet(werkzeug, tmp_path, capsys):
    gut, schlecht = _dateien(tmp_path, "gut.xml", "ohne.xml")
    code = _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({
        "gut.xml": _bericht(), "ohne.xml": _bericht("reject", regeln=["BR-DE-15"])}))
    ausgabe = capsys.readouterr().out
    assert code == 0, ausgabe
    assert "KoSIT Validator 1.6.3" in ausgabe and "Validator Configuration XRechnung 3.0.2" in ausgabe


def test_das_urteil_kommt_aus_dem_bericht_nicht_aus_dem_exit_code(werkzeug, tmp_path):
    """Exit 0, aber der Bericht sagt reject: Das ist ein Befund."""
    (gut,) = _dateien(tmp_path, "gut.xml")
    schlecht = _dateien(tmp_path, "ohne.xml")[0]
    code = _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({
        "gut.xml": _bericht("reject", regeln=["BR-CO-10"]),
        "ohne.xml": _bericht("reject", regeln=["BR-DE-15"])}, exit_code=0))
    assert code == 1


def test_ein_anderes_szenario_zaehlt_nicht(werkzeug, tmp_path, capsys):
    """Eine ZUGFeRD-Datei liefe unter einem anderen Szenario — dann prüfte der
    Validator nicht die XRechnung-Regeln, auch wenn er `accept` sagt."""
    gut, schlecht = _dateien(tmp_path, "gut.xml", "ohne.xml")
    code = _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({
        "gut.xml": _bericht(szenario="EN16931 CII"),
        "ohne.xml": _bericht("reject", regeln=["BR-DE-15"])}))
    assert code == 1
    assert "Szenario" in capsys.readouterr().out


def test_ein_hinweis_ist_kein_ablehnungsgrund(werkzeug, tmp_path):
    """`BR-DE-TMP-32` erscheint bei `validXRV30.xml` als Hinweis. Stünde nur ein
    Hinweis mit der gesuchten Regel da, darf die Gegenprobe nicht als belegt gelten."""
    gut, schlecht = _dateien(tmp_path, "gut.xml", "ohne.xml")
    hinweis = _bericht("reject").replace(
        "<rep:assessment>", '<rep:message level="warning" code="BR-DE-15">[BR-DE-15]</rep:message><rep:assessment>')
    code = _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({
        "gut.xml": _bericht(), "ohne.xml": hinweis}))
    assert code == 1


def test_die_gegenprobe_aus_anderem_grund_ist_ein_befund(werkzeug, tmp_path):
    gut, schlecht = _dateien(tmp_path, "gut.xml", "ohne.xml")
    code = _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({
        "gut.xml": _bericht(), "ohne.xml": _bericht("reject", regeln=["BR-CO-10"])}))
    assert code == 1


def test_ohne_bericht_ist_es_nicht_geprueft(werkzeug, tmp_path, capsys):
    gut, schlecht = _dateien(tmp_path, "gut.xml", "ohne.xml")
    code = _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({}, exit_code=0))
    assert code == 2
    assert "NICHT GEPRÜFT" in capsys.readouterr().out


def test_ohne_java_ist_es_nicht_geprueft(werkzeug, tmp_path):
    gut, schlecht = _dateien(tmp_path, "gut.xml", "ohne.xml")
    assert _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({}, java_ok=False)) == 2


def test_ein_anderes_jar_urteilt_nicht(werkzeug, tmp_path, monkeypatch):
    monkeypatch.setattr(ek, "VALIDATOR_SHA256", "0" * 64)
    gut, schlecht = _dateien(tmp_path, "gut.xml", "ohne.xml")
    assert _lauf(werkzeug, [gut], [f"{schlecht}::BR-DE-15"], _validator({
        "gut.xml": _bericht(), "ohne.xml": _bericht("reject", regeln=["BR-DE-15"])})) == 2


def test_ohne_gegenprobe_belegt_der_lauf_nichts(werkzeug, tmp_path):
    jar, konf = werkzeug
    (gut,) = _dateien(tmp_path, "gut.xml")
    code = ek.main(["--validator", str(jar), "--konfiguration", str(konf), "--gut", str(gut)],
                   ausfuehren=_validator({"gut.xml": _bericht()}))
    assert code == 1


def test_die_ci_laedt_die_gepinnten_fassungen():
    text = CI.read_text(encoding="utf-8")
    assert f"validator/releases/download/v{ek.VALIDATOR_VERSION}/validator-{ek.VALIDATOR_VERSION}-standalone.jar" in text
    assert f"validator-configuration-xrechnung/releases/download/v{ek.KONFIGURATION_STAND}/" in text
    assert ek.KONFIGURATION_SHA256 in text
    aufruf = text[text.index("scripts/erechnung_kosit.py"):][:500]
    assert "--gut" in aufruf and "--schlecht" in aufruf and "::BR-DE-15" in aufruf, aufruf
