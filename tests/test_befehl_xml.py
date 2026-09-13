"""`falzmarke xml` — die Rechnung als reine XML, ohne PDF (#117).

An öffentliche Auftraggeber geht XRechnung als XML-Datei. Der Befehl prüft wie
`render` erst mit `lint`, erzeugt dann die XML und schreibt sie — Typst läuft
dabei nicht. Abnahme 3 aus #117 wird am Dateisystem gemessen: Nach dem Lauf
liegt kein PDF im Zielordner.
"""

from __future__ import annotations

import shutil

from falzmarke import cli as falzmarke
from falzmarke import emit_xml
from conftest import REPO, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"
XRECHNUNG = REPO / "examples" / "xrechnung.md"
RECHNUNG = REPO / "examples" / "rechnung.md"


def _kopie(tmp_path, quelle=XRECHNUNG, ersetzen=None):
    ziel = tmp_path / quelle.name
    text = quelle.read_text(encoding="utf-8")
    if ersetzen:
        assert ersetzen[0] in text
        text = text.replace(*ersetzen)
    ziel.write_text(text, encoding="utf-8")
    return ziel


def test_die_xml_entsteht_und_kein_pdf(tmp_path, capsys):
    quelle = _kopie(tmp_path)
    ziel = tmp_path / "aus" / "rechnung.xml"
    ziel.parent.mkdir()
    code = falzmarke.main(["xml", str(quelle), "-o", str(ziel), "--profiles", str(PROFILE)])
    ausgabe = capsys.readouterr()
    assert code == 0, ausgabe.err
    assert ziel.is_file()
    assert list(tmp_path.rglob("*.pdf")) == [], "es ist ein PDF entstanden"
    assert emit_xml.GUIDELINE_XRECHNUNG in ziel.read_text(encoding="utf-8")
    assert "XRechnung 3.0" in ausgabe.out


def test_ohne_ziel_liegt_die_xml_neben_der_quelle(tmp_path):
    quelle = _kopie(tmp_path)
    assert falzmarke.main(["xml", str(quelle), "--profiles", str(PROFILE)]) == 0
    assert (tmp_path / "xrechnung.xml").is_file()


def test_die_datei_hat_keine_windows_zeilenenden(tmp_path):
    quelle = _kopie(tmp_path)
    ziel = tmp_path / "r.xml"
    falzmarke.main(["xml", str(quelle), "-o", str(ziel), "--profiles", str(PROFILE)])
    assert b"\r\n" not in ziel.read_bytes()


def test_die_ausgabe_nennt_die_gelesene_fassung_auch_fuer_en16931(tmp_path, capsys):
    quelle = _kopie(tmp_path, RECHNUNG)
    ziel = tmp_path / "r.xml"
    assert falzmarke.main(["xml", str(quelle), "-o", str(ziel), "--profiles", str(PROFILE)]) == 0
    ausgabe = capsys.readouterr().out
    assert "EN 16931" in ausgabe and emit_xml.GUIDELINE in ausgabe


def test_ein_lint_fehler_bricht_ab_und_schreibt_nichts(tmp_path, capsys):
    quelle = _kopie(tmp_path, ersetzen=('leitweg_id: "04011000-1234512345-06"\n', ""))
    ziel = tmp_path / "r.xml"
    code = falzmarke.main(["xml", str(quelle), "-o", str(ziel), "--profiles", str(PROFILE)])
    assert code == falzmarke.EXIT_EINGABE
    assert not ziel.exists()
    assert "rechnung.xrechnung" in capsys.readouterr().err


def test_ein_brief_ist_keine_rechnung(tmp_path, capsys):
    brief = REPO / "examples" / "brief.md"
    if not brief.is_file():
        brief = next(p for p in (REPO / "examples").glob("*.md")
                     if "typ: rechnung" not in p.read_text(encoding="utf-8")
                     and "typ: email" not in p.read_text(encoding="utf-8"))
    quelle = tmp_path / "brief.md"
    shutil.copy(brief, quelle)
    code = falzmarke.main(["xml", str(quelle), "-o", str(tmp_path / "b.xml"), "--profiles", str(PROFILE)])
    assert code == falzmarke.EXIT_EINGABE
    assert "typ: rechnung" in capsys.readouterr().err


def test_render_sagt_bei_xrechnung_wohin_die_datei_gehoert():
    hinweis = falzmarke.xrechnung_hinweis(XRECHNUNG)
    assert hinweis and "falzmarke xml xrechnung.md" in hinweis


def test_gegenprobe_bei_en16931_kein_hinweis():
    assert falzmarke.xrechnung_hinweis(RECHNUNG) is None
