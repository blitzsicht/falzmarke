"""Gemeinsame Fixtures. Die Beispiele werden einmal je Testlauf gerendert.

Wo Tests die CLI über `subprocess` aufrufen, steht dort `encoding="utf-8"`.
Ohne das liest Python die Ausgabe unter Windows in cp1252, und jeder Vergleich
mit einem Text, der `—` oder `ß` enthält, scheitert an Mojibake statt an der
Sache. Das Programm selbst schreibt seit v0.2.0 immer UTF-8.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skill"
# Der Skill-Ordner ist zugleich das Paketverzeichnis.
sys.path.insert(0, str(SKILL))

BEISPIELE = sorted((REPO / "examples").glob("*.md"))

# Die Mail-Beispiele liegen bewusst eine Ebene tiefer. `examples/*.md` wird in
# der CI und oben in BEISPIELE als **Brief** gerendert; eine Datei mit
# `typ: email` bricht dort absichtlich ab (cli.py, `rendere`). Der Glob ist
# nicht rekursiv — der Unterordner ist damit die Trennung, nicht eine
# Ausnahmeliste, die jemand pflegen muesste.
EMAIL_BEISPIELE = sorted((REPO / "examples" / "email").glob("*.md"))


# Dasselbe für die Urkunde (ADR 0048): Sie hat kein Anschriftfeld und fiele in
# jeder Briefabnahme durch — zu Recht. Der Unterordner hält sie aus `BEISPIELE`
# heraus; gemessen wird sie in `tests/test_urkunde_messung.py` nach ihrer
# eigenen Liste.
URKUNDE_BEISPIELE = sorted((REPO / "examples" / "urkunde").glob("*.md"))


def _typ(pfad: Path) -> str:
    """`typ:` aus dem Frontmatter, ohne YAML zu laden — wie `_fassung()` unten."""
    for zeile in pfad.read_text(encoding="utf-8").split("\n---", 1)[0].splitlines():
        if zeile.startswith("typ:"):
            return zeile.split(":", 1)[1].strip().strip("\"'")
    return "brief"


#: Die Rechnungsbeispiele unter `examples/*.md` — am Frontmatter erkannt, nicht an
#: einem eigenen Unterordner wie bei `EMAIL_BEISPIELE`: `rechnung.md` und
#: `xrechnung.md` liegen bewusst neben den Briefen, weil sie in der CI auch als
#: Briefe der Kategorie „Rechnung" laufen (#119).
RECHNUNG_BEISPIELE = sorted(p for p in BEISPIELE if _typ(p) == "rechnung")

#: Die ausgelieferten Profile. Ein Beispiel darf sein Profil auch neben sich
#: legen — `cli.finde_profile` sucht dort zuerst (Punkt 3 der Suchreihenfolge).
PROFILE = SKILL / "falzmarke" / "typst" / "profiles"


def profilpfad(beispiel: Path, name: str) -> Path:
    """Wo das Profil eines Beispiels liegt — neben ihm oder bei den ausgelieferten.

    Steht hier und nicht in einer Testdatei, weil zwei Dateien dieselbe
    Auflösung brauchten und beide sie abkürzten: Sie sahen nur im
    ausgelieferten Ordner nach. Das ging gut, solange alle Mail-Beispiele
    dasselbe Profil trugen — mit `email-logo.md` (#243) lief es ins Leere,
    und zwar in beiden Kopien gleichzeitig.

    Kein YAML hier: conftest bleibt frei von Abhängigkeiten, die Tests laden
    selbst.
    """
    for ordner in (Path(beispiel).parent / "profiles", PROFILE):
        pfad = ordner / f"{name}.yaml"
        if pfad.is_file():
            return pfad
    raise AssertionError(f"kein Profil `{name}` neben {beispiel} und nicht in {PROFILE}")


def ohne_typografiehinweise(bericht) -> list:
    """Die Befunde eines Lint-Berichts, ohne die Hinweise des Typografie-Passes (#330).

    Seit #330 meldet der Linter, was der Typografie-Pass zurückhält: eine
    Warnung je Schritt, dessen Regel nur einzeln belegt ist, unter der Kennung
    dieser Regel (`schreibweise.einheiten`, …). Ein Test, der „keine Befunde"
    fordert, meint damit die Eingabe — nicht die Frage, ob das Beispiel ein
    „5 kg" oder ein „Rechnung Nr." enthält.

    Die Ausnahme ist eng: nur Befunde unter der Kennung einer Regel mit
    `typografie:`-Zuordnung. Jede andere Warnung zählt weiter. Lazy importiert,
    weil conftest sonst schon beim Sammeln das Paket laden müsste.
    """
    from falzmarke import regeln

    kennungen = {r["id"] for r in regeln.alle() if r.get("typografie")}
    assert kennungen, "keine Regel trägt `typografie:` — der Filter nähme nichts aus"
    return [b for b in bericht.befunde if b.regel not in kennungen]


def _fassung(pfad: Path) -> str:
    """Die Dialektfassung eines Beispiels, ohne YAML zu laden.

    Reicht für die Auswahl unten und hält conftest frei von Abhängigkeiten.
    """
    for zeile in pfad.read_text(encoding="utf-8").split("\n---", 1)[0].splitlines():
        if zeile.startswith("dialekt:"):
            return zeile.split(":", 1)[1].strip().strip("\"'")
    return "1.0"


#: Beispiele in Fassung 1.0. Nur sie taugen als Eingang für die E-Mail-Emitter:
#: Was 1.1 braucht, lehnt `markdown.py` bei `ziel="email"` ab, solange der
#: HTML-Teil es nicht setzt.
#:
#: Bewusst eine eigene Liste statt eines `skipif` im Test: Eine übersprungene
#: Prüfung sieht aus wie eine bestandene. So steht die Zahl daneben, und
#: `tests/test_dialekt.py` hält fest, dass die Auswahl weder leer noch
#: vollständig ist.
BEISPIELE_10 = [p for p in BEISPIELE if _fassung(p) == "1.0"]
BEISPIELE_11 = [p for p in BEISPIELE if _fassung(p) != "1.0"]


@pytest.fixture(autouse=True)
def _kein_echtes_thunderbird_profil(monkeypatch, tmp_path_factory):
    """Kein Test liest das Thunderbird-Profil des Rechners, auf dem er läuft (ADR 0050).

    Der Entwurfsweg sieht dort nach, ob die Identität eine eigene Signatur
    trägt. Ohne diese Umleitung hinge ein Test davon ab, welche Konten der
    Entwickler eingerichtet hat — grün bei dem einen, rot bei dem anderen.
    Wer ein Profil braucht, baut sich eine Attrappe und reicht sie durch.
    """
    from falzmarke import oeffnen

    monkeypatch.setattr(oeffnen, "THUNDERBIRD_ORDNER",
                        tmp_path_factory.getbasetemp() / "kein-thunderbird")


class _KeinPostfach:
    """Steht für `imaplib.IMAP4`, solange ein Test keine Attrappe einsetzt."""

    def __init__(self, host, port=143, timeout=None):
        raise ConnectionRefusedError(61, "Testlauf: keine echte IMAP-Verbindung")


@pytest.fixture(autouse=True)
def _kein_echtes_postfach(monkeypatch):
    """Kein Test spricht mit einem echten Postfach (ADR 0051).

    Auf dem Rechner des Betreibers läuft der IMAP-Proxy unter 127.0.0.1:1993 —
    ein vergessener Patch wäre dort kein roter Test, sondern ein Blick in einen
    echten Gesendet-Ordner oder ein Entwurf im echten Postfach. Deshalb zwei
    Riegel: Die Gesendet-Prüfung ist abgeschaltet (`FALZMARKE_GESENDET=nie`),
    und wer trotzdem verbindet, landet bei einer Verbindung, die abgelehnt
    wird. Tests, die das Postfach brauchen, setzen ihre Attrappe ein und
    nehmen die Variable zurück.
    """
    from falzmarke import postfach

    monkeypatch.setattr(postfach, "IMAP_KLASSE", _KeinPostfach)
    monkeypatch.setenv("FALZMARKE_GESENDET", "nie")


# ── Der Wächter: kein Test öffnet ein Fenster oder erreicht ein Postfach ──────
#
# ANLASS (21.10.2026, beim Bau von ADR 0051): Ein neuer Test lief über den
# Datei-Rückfall bis zu `oeffne()`, und das echte `open` reichte die Test-`.eml`
# an Thunderbird — auf dem Bildschirm des Betreibers ging ein Fenster mit
# „Hallo Nico, … Erika Muster“ auf. Bis dahin hing das an einem Riegel je
# Testdatei; wer ihn vergaß, merkte es nicht an einem roten Test, sondern an
# einem Fenster. `CI` und `FALZMARKE_OEFFNEN=nie` greifen auf dem Rechner des
# Entwicklers nicht, und viele Tests reichen ihre Umgebung ausdrücklich herein
# (`umgebung={"DISPLAY": ":0"}`) — dort käme keine Variable an.
#
# Deshalb sitzt der Riegel eine Ebene tiefer und gilt für jeden Test: an
# `subprocess.Popen`, über das jedes `subprocess.run` geht, auch das, was als
# Vorgabewert `laufen=subprocess.run` schon beim Import gebunden wurde. Ein
# Programm, das ein Fenster öffnet oder ein Mailprogramm steuert, startet
# nicht; der Versuch wird vermerkt, und der Test wird beim Abbau rot, auch wenn
# der Code den Fehler unterwegs geschluckt hat. Dasselbe für `imaplib` und
# `smtplib` unterhalb von `postfach.IMAP_KLASSE`.

#: Programme, die auf dem Rechner eines Menschen etwas aufgehen lassen oder ein
#: Mailprogramm steuern. Verglichen wird der Name ohne Pfad und ohne `.exe`.
FENSTER_PROGRAMME = frozenset({
    "open", "xdg-open", "gio", "gnome-open", "kde-open", "kde-open5", "wslview",
    "osascript", "thunderbird", "thunderbird-bin", "outlook", "explorer", "start",
})

#: Kindprozesse (etwa `python -m falzmarke`) erben den Riegel über die
#: Umgebung — dort greift der Patch nicht, `kein_bildschirm` aber schon.
KIND_UMGEBUNG = {"FALZMARKE_OEFFNEN": "nie", "FALZMARKE_GESENDET": "nie",
                 "FALZMARKE_POSTFACH": "nie"}


class WaechterFehler(AssertionError):
    """Ein Test wollte wirklich ein Fenster öffnen oder ein Postfach erreichen."""


#: Was der Wächter im laufenden Test abgefangen hat. Der Abbau verlangt, dass
#: es leer ist. Wer den Wächter absichtlich auslöst, leert die Liste selbst.
ABGEFANGEN: list[str] = []


def fenster_programm(args) -> str | None:
    """Der Grund, warum `args` nicht starten darf — oder None."""
    if isinstance(args, (str, bytes)):
        text = args.decode() if isinstance(args, bytes) else args
        erstes = text.split()[:1]
    else:
        erstes = [str(a) for a in list(args)[:1]]
    if not erstes:
        return None
    programm = erstes[0]
    name = re.split(r"[\\/]", programm)[-1].lower().removesuffix(".exe")
    if name in FENSTER_PROGRAMME:
        return f"`{programm}` öffnet ein Fenster oder steuert ein Mailprogramm"
    if ".app/" in programm:
        return f"`{programm}` liegt in einem macOS-Programmpaket"
    return None


_ECHTES_POPEN = subprocess.Popen


class _WaechterPopen(_ECHTES_POPEN):
    def __init__(self, args, *a, **k):
        import os

        grund = fenster_programm(args)
        if grund:
            ABGEFANGEN.append(grund)
            raise WaechterFehler(f"Testlauf: {grund} — nicht gestartet")
        umgebung = dict(os.environ if k.get("env") is None else k["env"])
        umgebung.update(KIND_UMGEBUNG)
        k["env"] = umgebung
        super().__init__(args, *a, **k)


def _verboten(was: str):
    def _nein(*_a, **_k):
        ABGEFANGEN.append(was)
        raise WaechterFehler(f"Testlauf: {was} ist gesperrt")
    return _nein


@pytest.fixture(autouse=True)
def _waechter(monkeypatch):
    """Hart für jeden Test: kein Fenster, kein Mailprogramm, kein Postfach."""
    import imaplib
    import os
    import smtplib

    ABGEFANGEN.clear()
    monkeypatch.setattr(subprocess, "Popen", _WaechterPopen)
    monkeypatch.setattr(os, "system", _verboten("os.system"))
    if hasattr(os, "startfile"):  # pragma: no cover — nur unter Windows
        monkeypatch.setattr(os, "startfile", _verboten("os.startfile"))
    monkeypatch.setattr(imaplib.IMAP4, "__init__", _verboten("imaplib.IMAP4"))
    monkeypatch.setattr(smtplib.SMTP, "__init__", _verboten("smtplib.SMTP"))
    yield
    pruefe_abgefangen()


def pruefe_abgefangen() -> None:
    """Rot, wenn im Test etwas abgefangen wurde — auch ein geschluckter Fehler."""
    abgefangen = list(ABGEFANGEN)
    ABGEFANGEN.clear()
    assert not abgefangen, f"der Wächter hat abgefangen: {abgefangen}"


@pytest.fixture(scope="session")
def gerendert(tmp_path_factory) -> dict[str, tuple[Path, str]]:
    """Name des Beispiels -> (PDF-Pfad, Form)."""
    from falzmarke import cli as falzmarke

    ziel = tmp_path_factory.mktemp("renders")
    ergebnis = {}
    for quelle in BEISPIELE:
        pdf, form = falzmarke.rendere(quelle, ziel / f"{quelle.stem}.pdf")
        ergebnis[quelle.stem] = (pdf, form)
    return ergebnis


@pytest.fixture(scope="session")
def beispiel_pfade() -> list[Path]:
    return BEISPIELE


# ── bash-Sonde ──────────────────────────────────────────────────────────────
#
# Stand bis #212 in tests/test_ruleset_durchsetzung.py. Sie hierher zu ziehen
# statt sie ein zweites Mal zu schreiben, ist dieselbe Regel, die dieser
# Vorgang im Produktivcode durchsetzt: zwei Kopien, die gleich sein muessen,
# halten sich nicht von selbst gleich.

def _bash_taugt() -> tuple[bool, str]:
    """Laesst sich `bash` hier ueberhaupt fuer einen Einzeiler benutzen?

    Auf den Windows-Runnern von GitHub scheitert `subprocess.run(["bash", ...])`
    mit Exit 1 und ohne Ausgabe (PR #202, Laeufe 33382792073 und 33383227023).
    Die Ursache ist von hier aus nicht feststellbar — deshalb wird sie nicht
    geraten, sondern gemessen: Diese Sonde faehrt einen trivialen Befehl und
    nimmt die Fehlerausgabe in den Skip-Grund auf. Der erscheint im
    pytest-Bericht (`-rs`) und benennt damit die Ursache dort, wo sie auftritt.

    Uebersprungen wird nur die *Verhaltens*pruefung. Dass der Default auf
    "active" steht, prueft `test_der_default_ist_active_strukturell` ohne bash
    auf jeder Plattform — ein Test, der nur uebersprungen wird, belegt nichts.
    """
    try:
        fertig = subprocess.run(
            ["bash", "-c", 'printf ok'], capture_output=True, text=True
        )
    except OSError as fehler:
        return False, f"bash nicht startbar: {fehler}"
    if fertig.returncode != 0 or fertig.stdout != "ok":
        return False, (
            f"bash antwortet nicht wie erwartet: rc={fertig.returncode} "
            f"stdout={fertig.stdout!r} stderr={fertig.stderr!r}"
        )
    return True, ""


BASH_TAUGT, BASH_GRUND = _bash_taugt()
ohne_bash = pytest.mark.skipif(not BASH_TAUGT, reason=BASH_GRUND)
