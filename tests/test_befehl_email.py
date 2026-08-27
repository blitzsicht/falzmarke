"""Der Befehl `email`, das MCP-Werkzeug und die Zusage, nichts zu versenden (#65).

Die wichtigste Prüfung hier ist eine Abwesenheitsprüfung: **es gibt keinen
Versandweg.** Sie ist schwer zu formulieren und leicht zu vergessen, und genau
deshalb steht sie zuerst — eine Option, die sendet, entstünde nicht durch eine
Entscheidung, sondern durch einen naheliegenden Zusatz, den niemand bemerkt.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from falzmarke import cli as falzmarke
from falzmarke import dienst
from conftest import REPO, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"
SKRIPT = SKILL / "scripts" / "falzmarke.py"

MAIL = """---
typ: email
profil: example
an: erika.muster@example.de
betreff: Angebot Nr. 2026-0815
anrede: Sehr geehrte Frau Muster,
---
wie besprochen erhalten Sie unser Angebot.

- Technik und Aufbau
- Betreuung vor Ort
"""

BRIEF = """---
profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-27
betreff: Angebot Nr. 2026-0815
---
Text des Briefes.
"""


def _schreibe(tmp_path, inhalt=MAIL, name="nachricht.md") -> Path:
    pfad = tmp_path / name
    pfad.write_text(inhalt, encoding="utf-8")
    return pfad


def _cli(*argumente) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SKRIPT), *argumente],
                          capture_output=True, text=True, encoding="utf-8")


# ── Es gibt keinen Versandweg ───────────────────────────────────────────────

def test_kein_versandbefehl():
    """ADR 0034: kein Versandbefehl, keine Option, die sendet."""
    hilfe = _cli("--help").stdout
    assert not re.search(r"\b(send|senden|versend|smtp|mail-?server)\b", hilfe, re.I), hilfe


def test_keine_option_die_sendet():
    hilfe = _cli("email", "--help").stdout
    assert "--html" in hilfe and "--mit-quelle" in hilfe, hilfe
    assert not re.search(r"--(send|senden|versenden|smtp)\b", hilfe, re.I), hilfe


def test_kein_netzwerk_im_erzeugenden_code():
    """Ein Modul, das `smtplib` importiert, hat einen Versandweg — auch wenn
    ihn heute niemand aufruft. Die Prüfung liest die Quelle, nicht die Doku.
    """
    for name in ("eml.py", "cli.py", "dienst.py", "pruefung_eml.py"):
        quelle = (SKILL / "falzmarke" / name).read_text(encoding="utf-8")
        assert "smtplib" not in quelle, f"{name} importiert smtplib"
        assert not re.search(r"\bsend_message\b|\bSMTP\b", quelle), name


def test_das_mcp_werkzeug_sagt_es_ausdruecklich():
    ergebnis = dienst.email_setzen(MAIL, profil="example")
    assert ergebnis["versendet"] is False


# ── Der Befehl ──────────────────────────────────────────────────────────────

def test_email_schreibt_eml_und_misst_nach(tmp_path):
    pfad = _schreibe(tmp_path)
    lauf = _cli("email", str(pfad), "--profiles", str(PROFILE))
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert (tmp_path / "nachricht.eml").is_file()
    assert "verify:" in lauf.stdout, lauf.stdout


def test_ohne_flags_bleibt_nur_die_eml(tmp_path):
    """Die Begleitdateien entstehen immer — behalten werden sie auf Wunsch.
    Sonst liegen nach jedem Lauf drei Dateien statt einer."""
    pfad = _schreibe(tmp_path)
    _cli("email", str(pfad), "--profiles", str(PROFILE))
    vorhanden = {p.suffix for p in tmp_path.iterdir()}
    assert vorhanden == {".md", ".eml"}, vorhanden


@pytest.mark.parametrize("flag, endung", [("--html", ".html"), ("--txt", ".txt")])
def test_die_begleitdateien_auf_wunsch(tmp_path, flag, endung):
    pfad = _schreibe(tmp_path)
    _cli("email", str(pfad), "--profiles", str(PROFILE), flag)
    assert (tmp_path / f"nachricht{endung}").is_file()


def test_eigener_zielname(tmp_path):
    pfad = _schreibe(tmp_path)
    _cli("email", str(pfad), "--profiles", str(PROFILE), "-o", str(tmp_path / "angebot"))
    assert (tmp_path / "angebot.eml").is_file()


def test_mit_quelle_haengt_die_quelle_an(tmp_path):
    pfad = _schreibe(tmp_path)
    _cli("email", str(pfad), "--profiles", str(PROFILE), "--mit-quelle")
    roh = (tmp_path / "nachricht.eml").read_text(encoding="utf-8")
    assert "text/markdown" in roh


def test_ohne_mit_quelle_nicht(tmp_path):
    """Gegenprobe: ADR 0034 Punkt 3 macht den Teil zur Ausnahme."""
    pfad = _schreibe(tmp_path)
    _cli("email", str(pfad), "--profiles", str(PROFILE))
    assert "text/markdown" not in (tmp_path / "nachricht.eml").read_text(encoding="utf-8")


# ── Was schiefgehen kann ────────────────────────────────────────────────────

def test_ein_brief_wird_nicht_zur_mail(tmp_path):
    pfad = _schreibe(tmp_path, BRIEF, "brief.md")
    lauf = _cli("email", str(pfad), "--profiles", str(PROFILE))
    assert lauf.returncode == 1
    assert "typ: email" in lauf.stderr and "render" in lauf.stderr


def test_ein_lintfehler_kostet_kein_setzen(tmp_path):
    """Dieselbe Reihenfolge wie beim Brief: Exit 1, und nichts wird
    geschrieben."""
    pfad = _schreibe(tmp_path, MAIL.replace("an: erika.muster@example.de", "an: keine-adresse"))
    lauf = _cli("email", str(pfad), "--profiles", str(PROFILE))
    assert lauf.returncode == 1
    assert not (tmp_path / "nachricht.eml").exists()


def test_ohne_text_bricht_es_ab(tmp_path):
    pfad = _schreibe(tmp_path, MAIL.split("---\n")[0] + "---\n" + MAIL.split("---\n")[1] + "---\n")
    lauf = _cli("email", str(pfad), "--profiles", str(PROFILE))
    assert lauf.returncode == 1


def test_setze_email_lehnt_einen_brief_ab(tmp_path):
    pfad = _schreibe(tmp_path, BRIEF, "brief.md")
    with pytest.raises(falzmarke.Eingabefehler, match="typ: email"):
        falzmarke.setze_email(pfad, profil_verzeichnis=PROFILE)


# ── Der MCP-Dienst ──────────────────────────────────────────────────────────

def test_email_setzen_ist_im_werkzeugkasten():
    namen = [w.__name__ for w in dienst.WERKZEUGE]
    assert "email_setzen" in namen, namen


def test_email_setzen_gibt_pfad_und_bericht():
    ergebnis = dienst.email_setzen(MAIL, profil="example")
    assert ergebnis["bestanden"] is True
    assert Path(ergebnis["pfad"]).is_file()
    assert Path(ergebnis["vorschau"]).is_file()
    assert "verify:" in ergebnis["zusammenfassung"]
    assert ergebnis["bericht"]["pruefungen"], "der Messbericht kommt mit"


def test_email_setzen_als_base64():
    ergebnis = dienst.email_setzen(MAIL, profil="example", als="base64")
    import base64 as b64
    roh = b64.b64decode(ergebnis["eml_base64"]).decode("utf-8")
    assert roh.startswith("From:") or "From:" in roh.split("\n\n", 1)[0]


def test_email_setzen_meldet_einen_erwarteten_fehler_als_meldung():
    """Ein erwarteter Fehler erreicht den Client als Meldung, nicht als
    maskierter Absturz — dieselbe Zusage wie bei `brief_rendern`."""
    with pytest.raises(dienst.Eingabefehler):
        dienst.email_setzen(MAIL, profil="example", als="postkarte")


def test_email_setzen_lehnt_einen_brief_ab():
    with pytest.raises(dienst.Eingabefehler, match="typ: email"):
        dienst.email_setzen(BRIEF, profil="example")


# ── Doku ────────────────────────────────────────────────────────────────────

def test_der_befehl_steht_im_skill():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "falzmarke.py email" in text
    assert "verify --email" in text, "Regel 0 muss die Mail einschließen"


def test_der_befehl_steht_in_der_readme():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "falzmarke email" in text
    assert "versendet nichts" in text


def test_der_stil_unterscheidet_mail_und_brief():
    text = (SKILL / "references" / "stil.md").read_text(encoding="utf-8")
    assert "E-Mail vom Brief unterscheidet" in text
