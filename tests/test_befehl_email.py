"""Der Befehl `email`, das MCP-Werkzeug und die Zusage, nichts zu versenden (#65).

Die wichtigste Prüfung hier ist eine Abwesenheitsprüfung: **es gibt keinen
Versandweg.** Sie ist schwer zu formulieren und leicht zu vergessen, und genau
deshalb steht sie zuerst — eine Option, die sendet, entstünde nicht durch eine
Entscheidung, sondern durch einen naheliegenden Zusatz, den niemand bemerkt.
"""

from __future__ import annotations

import ast
import os
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


# ── Die Datei dem Betriebssystem übergeben (#239, ADR 0038) ─────────────────
#
# Kein Test hier darf ein Fenster öffnen. Die CI fährt `macos-latest` und
# `windows-latest`; dort wäre ein vergessener Patch kein roter Test, sondern
# ein aufgehendes Mailprogramm auf einem Läufer, der niemandem gehört.

@pytest.fixture(autouse=True)
def _kein_echtes_fenster(monkeypatch):
    """Sicherheitsnetz für die ganze Datei.

    Wer den Starter wirklich erreicht, ohne ihn ersetzt zu haben, bekommt
    einen roten Test statt eines Fensters. Tests, die den Aufruf beobachten
    wollen, überschreiben das mit ihrem eigenen Rekorder.
    """
    from falzmarke import oeffnen

    def _nein(*_a, **_k):
        raise AssertionError("ein Test wollte wirklich ein Programm starten")

    monkeypatch.setattr(oeffnen, "_fuehre_aus", _nein)


class _Starter:
    """Zählt, womit gestartet worden wäre."""

    def __init__(self, code=0, meldung=""):
        self.argv: list[list[str]] = []
        self._antwort = (code, meldung)

    def __call__(self, art, argv, **_kwargs):
        self.argv.append(list(argv))
        return self._antwort

    @property
    def anzahl(self) -> int:
        return len(self.argv)


@pytest.fixture
def starter(monkeypatch):
    from falzmarke import oeffnen

    gefaelscht = _Starter()
    monkeypatch.setattr(oeffnen, "_fuehre_aus", gefaelscht)
    monkeypatch.setenv("FALZMARKE_OEFFNEN", "immer")  # sonst blockt CI= den Lauf
    return gefaelscht


def test_ohne_flag_wird_nichts_geoeffnet(tmp_path, starter):
    pfad = _schreibe(tmp_path)
    code = falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE)])
    assert code == 0
    assert starter.anzahl == 0


def test_mit_flag_wird_genau_die_eml_uebergeben(tmp_path, starter):
    """Die tragende Gegenprobe zum Test darüber: Ohne sie wäre jener auch dann
    grün, wenn der Rekorder gar nicht verdrahtet ist."""
    pfad = _schreibe(tmp_path)
    code = falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE), "--oeffnen"])
    assert code == 0
    assert starter.anzahl == 1
    assert starter.argv[0][-1].endswith(".eml")


def test_auch_mit_html_wird_nur_die_eml_uebergeben(tmp_path, starter):
    """Zwei Dateien hießen zwei Fenster in zwei Programmen. Ungefragt."""
    pfad = _schreibe(tmp_path)
    falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE),
                    "--oeffnen", "--html"])
    assert starter.anzahl == 1
    assert starter.argv[0][-1].endswith(".eml")
    assert (tmp_path / "nachricht.html").is_file(), "die Vorschau liegt trotzdem da"


def test_eine_rote_pruefung_wird_nicht_geoeffnet(tmp_path, starter, monkeypatch):
    """Regel 0, angewandt auf den einzigen Schritt nach außen: Was seine eigene
    Prüfung nicht besteht, wird niemandem ins Mailprogramm gelegt."""
    from falzmarke import pruefung_eml

    class _Durchgefallen:
        ok = False

        def als_text(self, ausfuehrlich=False):
            return "verify: 1 Prüfung fehlgeschlagen"

    monkeypatch.setattr(pruefung_eml, "pruefe", lambda _pfad: _Durchgefallen())
    pfad = _schreibe(tmp_path)
    code = falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE), "--oeffnen"])
    assert code == 2
    assert starter.anzahl == 0


def test_gegenprobe_die_gruene_wird_geoeffnet(tmp_path, starter):
    """Ohne sie beliese der Test darüber nur, dass irgendetwas den Aufruf
    verhindert — nicht, dass es die rote Prüfung war."""
    pfad = _schreibe(tmp_path)
    code = falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE), "--oeffnen"])
    assert (code, starter.anzahl) == (0, 1)


# ── Die Blindkopie wird eigens genannt (#242) ───────────────────────────────

def test_ein_bcc_wird_in_der_ausgabe_genannt(tmp_path, capsys):
    """Er steht in der Kopfzeile der Datei, aber nicht in der `.html`-Vorschau,
    und ob ein Mailprogramm ihn beim Weiterleiten übernimmt, entscheidet das
    Programm. Wer die Zeile liest, weiß, dass er nachsehen muss; wer sie nicht
    bekäme, hielte den Bcc für erledigt."""
    pfad = _schreibe(tmp_path, MAIL.replace(
        "an: erika.muster@example.de",
        "an: erika.muster@example.de\nbcc: [Archiv <archiv@example.com>]"))
    code = falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE)])
    ausgabe = capsys.readouterr().out
    assert code == 0, ausgabe
    assert "archiv@example.com" in ausgabe
    assert "nachsehen" in ausgabe, "der Hinweis fehlt, was zu tun ist"


def test_ohne_bcc_schweigt_die_ausgabe(tmp_path, capsys):
    """Gegenprobe. Eine Zeile, die immer erscheint, sagt nichts — und der
    Normalfall ist die Mail ohne Blindkopie."""
    falzmarke.main(["email", str(_schreibe(tmp_path)), "--profiles", str(PROFILE)])
    assert "Blindkopie" not in capsys.readouterr().out


def test_ein_fehlgeschlagenes_oeffnen_entwertet_die_datei_nicht(
        tmp_path, monkeypatch, capsys):
    """ADR 0038, Punkt 4: Die .eml ist geschrieben und gemessen — das ist die
    Zusage. Ein Fenster, das nicht aufgeht, macht sie nicht ungültig."""
    from falzmarke import oeffnen

    monkeypatch.setattr(oeffnen, "_fuehre_aus",
                        lambda *a, **k: (3, "kein Programm zugeordnet"))
    monkeypatch.setenv("FALZMARKE_OEFFNEN", "immer")
    pfad = _schreibe(tmp_path)
    code = falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE), "--oeffnen"])
    ausgabe = capsys.readouterr()
    assert code == 0, "ein gescheitertes Öffnen ist kein Fehler des Befehls"
    assert "nicht geöffnet" in ausgabe.err
    assert "kein Programm zugeordnet" in ausgabe.err
    assert (tmp_path / "nachricht.eml").is_file()


def test_gegenprobe_ein_gelungenes_oeffnen_meldet_es(tmp_path, starter, capsys):
    """Ohne sie wäre nicht belegt, dass die Meldung oben vom Fehlschlag kommt."""
    pfad = _schreibe(tmp_path)
    falzmarke.main(["email", str(pfad), "--profiles", str(PROFILE), "--oeffnen"])
    ausgabe = capsys.readouterr()
    assert "OK  geöffnet" in ausgabe.out
    assert "nicht geöffnet" not in ausgabe.err


def test_das_flag_steht_in_der_hilfe():
    assert "--oeffnen" in _cli("email", "--help").stdout


def _importiert_subprocess(quelle: str) -> bool:
    """Ob dieses Modul `subprocess` wirklich einbindet — über den Syntaxbaum.

    Nicht als Textsuche: In `cli.py` steht das Wort in einem Kommentar, der
    genau erklärt, warum es dort *nicht* importiert wird. Ein Textgrep machte
    ausgerechnet diese Erklärung zum Verstoß.
    """
    for knoten in ast.walk(ast.parse(quelle)):
        if isinstance(knoten, ast.Import):
            if any(a.name.split(".")[0] == "subprocess" for a in knoten.names):
                return True
        elif isinstance(knoten, ast.ImportFrom):
            if (knoten.module or "").split(".")[0] == "subprocess":
                return True
    return False


def test_nur_ein_modul_startet_fremde_programme():
    """Die Grenze aus ADR 0038, Punkt 5 — als messbare Aussage.

    Ein `import subprocess` in `cli.py` läge über `dienst.py` in jedem
    MCP-Prozess. Deshalb ist das hier eine Prüfung und keine Zusicherung.
    """
    mit_subprocess = {p.name for p in sorted((SKILL / "falzmarke").glob("*.py"))
                      if _importiert_subprocess(p.read_text(encoding="utf-8"))}
    assert mit_subprocess == {"oeffnen.py"}, mit_subprocess


def test_gegenprobe_die_menge_ist_nicht_leer():
    """Ohne sie ginge der Test oben auch dann durch, wenn der Glob nichts
    findet — leere Menge gegen leere Menge belegt nichts."""
    module = sorted((SKILL / "falzmarke").glob("*.py"))
    assert len(module) >= 15, len(module)
    assert any(p.name == "oeffnen.py" for p in module)
    # Und die Prüfung selbst muss anschlagen können, sonst wäre die leere
    # Menge oben auch bei kaputtem Helfer grün.
    assert _importiert_subprocess("import subprocess\n")
    assert _importiert_subprocess("from subprocess import run\n")
    assert not _importiert_subprocess("# subprocess waere hier falsch\n")


def test_der_mcp_dienst_laedt_das_oeffnen_nicht():
    """Ein Werkzeugaufruf über MCP kommt womöglich von einem anderen Rechner.
    Dort ein Fenster zu öffnen wäre kein Dienst, sondern ein Übergriff.

    Im Kindprozess, weil diese Testdatei `falzmarke.oeffnen` längst geladen
    hat — in-process gemessen wäre das Ergebnis ein Artefakt der Testdatei.
    """
    programm = (
        "import sys;"
        "sys.path.insert(0, %r);"
        "from falzmarke import dienst;"
        "dienst.email_setzen(%r, profil='example');"
        "print('oeffnen' if 'falzmarke.oeffnen' in sys.modules else 'sauber')"
        % (str(SKILL), MAIL)
    )
    lauf = subprocess.run([sys.executable, "-c", programm],
                          capture_output=True, text=True, encoding="utf-8")
    assert lauf.returncode == 0, lauf.stderr
    assert lauf.stdout.strip() == "sauber", lauf.stdout


def test_gegenprobe_die_cli_laedt_es_sehr_wohl(tmp_path):
    """Sonst belegte der Test oben nur, dass der Kindprozess irgendetwas nicht
    lädt. `FALZMARKE_OEFFNEN=nie` hält dabei das Fenster zu."""
    pfad = _schreibe(tmp_path)
    programm = (
        "import sys;"
        "sys.path.insert(0, %r);"
        "from falzmarke import cli;"
        "cli.main(['email', %r, '--profiles', %r, '--oeffnen']);"
        "print('geladen' if 'falzmarke.oeffnen' in sys.modules else 'sauber')"
        % (str(SKILL), str(pfad), str(PROFILE))
    )
    lauf = subprocess.run([sys.executable, "-c", programm],
                          capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "FALZMARKE_OEFFNEN": "nie"})
    assert lauf.returncode == 0, lauf.stderr
    assert lauf.stdout.strip().endswith("geladen"), lauf.stdout
