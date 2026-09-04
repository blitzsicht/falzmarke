"""Die vier Mail-Beispiele — gemessen, nicht nur vorhanden (#66).

`tests/test_eml.py` prüft den Erzeuger an je einem konstruierten Fall.
Hier laufen dieselben Zusagen über die Dateien, die im Repository stehen und
die jemand abtippt, der das Werkzeug zum ersten Mal benutzt. Ein Beispiel, das
nicht mitgeprüft wird, altert still — und altert sichtbar, weil es das erste
ist, was jemand liest.

Das **Golden** ist die Byte-für-Byte festgehaltene `.eml`. Es fällt auf, wenn
sich an der Ausgabe etwas ändert, das niemand angesagt hat. Erneuert wird es
mit `python3 scripts/golden_email.py`; der Diff im PR ist dann der Befund,
nicht die Nacharbeit.

Jede Prüfung hier hat ihre Gegenprobe: eine Sabotage, die anschlagen **muss**,
und davor ein `assert`, dass die Sabotage überhaupt etwas verändert hat. Ein
Prüfmittel, das nie rot werden kann, ist kein Nachweis.
"""

from __future__ import annotations

import email
import shutil
from email import policy
from pathlib import Path

import pytest

from falzmarke import cli as falzmarke
from falzmarke import emit_text as text
from falzmarke import markdown as md
from falzmarke import pruefung_eml
from conftest import EMAIL_BEISPIELE, REPO

GOLDEN = REPO / "tests" / "golden" / "email"
ANLAGE = REPO / "examples" / "email" / "anlagen" / "rechnung-2026-0815.md"

#: Derselbe Zeitpunkt wie in `scripts/golden_email.py` und `test_eml.py`.
#: Seit #236 trägt jede Nachricht ein `Date`; ohne diesen festen Zeitpunkt
#: wäre es der Erzeugungszeitpunkt und damit jedes Golden bei jedem Lauf rot.
#: Mit einem anderen Wert wäre es beim ersten Lauf rot.
EPOCH = "1788134400"

IDS = dict(ids=lambda p: p.stem)


@pytest.fixture(autouse=True)
def fester_zeitpunkt(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)


def _setze(beispiel: Path, tmp_path: Path, **args) -> Path:
    eml, _ = falzmarke.setze_email(beispiel, tmp_path / beispiel.stem, **args)
    return eml


def _brieftext(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8").split("---", 2)[2]


def _kopie(beispiel: Path, tmp_path: Path, alt: str, neu: str) -> Path:
    """Das Beispiel verändert im tmp_path — die Vorlage bleibt unberührt.

    Über eine Kopie, nie über eine Änderung am Original mit anschließendem
    `git checkout`: Der stellt HEAD wieder her und nimmt uncommittete Arbeit
    daneben mit.
    """
    ziel = tmp_path / "sabotiert"
    ziel.mkdir(exist_ok=True)
    if (anlagen := beispiel.parent / "anlagen").is_dir():
        shutil.copytree(anlagen, ziel / "anlagen", dirs_exist_ok=True)
    quelle = beispiel.read_text(encoding="utf-8")
    assert alt in quelle, f"die Sabotage findet „{alt}“ nicht — sie kann nicht greifen"
    pfad = ziel / beispiel.name
    pfad.write_text(quelle.replace(alt, neu, 1), encoding="utf-8")
    assert pfad.read_text(encoding="utf-8") != quelle, "Sabotage wirkungslos"
    return pfad


# ── Es gibt überhaupt etwas zu messen ───────────────────────────────────────

def test_es_gibt_beispiele():
    """Ohne diese Prüfung wäre jede Parametrisierung unten bei leerem Glob grün."""
    assert EMAIL_BEISPIELE, "keine Beispiele unter examples/email/"
    assert len(EMAIL_BEISPIELE) >= 4, [p.name for p in EMAIL_BEISPIELE]


def test_zu_jedem_beispiel_ein_golden():
    fehlend = [b.stem for b in EMAIL_BEISPIELE if not (GOLDEN / f"{b.stem}.eml").exists()]
    assert not fehlend, (f"ohne Golden: {fehlend} — "
                         "`python3 scripts/golden_email.py` legt sie an")


def test_kein_golden_ohne_beispiel():
    """Die Gegenrichtung: ein gelöschtes Beispiel darf sein Golden nicht überleben."""
    staemme = {b.stem for b in EMAIL_BEISPIELE}
    verwaist = [g.stem for g in GOLDEN.glob("*.eml") if g.stem not in staemme]
    assert not verwaist, f"Golden ohne Beispiel: {verwaist}"


# ── Der Byte-Vergleich ──────────────────────────────────────────────────────

@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
def test_die_nachricht_entspricht_ihrem_golden(beispiel, tmp_path):
    ist = _setze(beispiel, tmp_path).read_bytes()
    soll = (GOLDEN / f"{beispiel.stem}.eml").read_bytes()
    assert ist == soll, (
        f"{beispiel.name} ergibt andere Bytes als das Golden. Ist die Änderung "
        "gewollt: `python3 scripts/golden_email.py`, dann den Diff mitlesen.")


def test_der_vergleich_kann_rot_werden(tmp_path):
    """Gegenprobe: eine geänderte Quelle darf nicht zum alten Golden passen."""
    beispiel = EMAIL_BEISPIELE[0]
    sabotiert = _kopie(beispiel, tmp_path, "betreff: ", "betreff: Nachtrag — ")
    ist = _setze(sabotiert, tmp_path).read_bytes()
    assert ist != (GOLDEN / f"{beispiel.stem}.eml").read_bytes()


def test_zwei_laeufe_ueber_dasselbe_beispiel_sind_gleich(tmp_path):
    """Ohne Determinismus wäre der Golden-Vergleich oben ein Zufallsgenerator."""
    beispiel = EMAIL_BEISPIELE[0]
    erst = _setze(beispiel, tmp_path / "a").read_bytes()
    zweit = _setze(beispiel, tmp_path / "b").read_bytes()
    assert erst == zweit


# ── Die Beispiele halten, was das Werkzeug prüft ────────────────────────────

@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
def test_lint_ist_sauber(beispiel):
    bericht = falzmarke.linte(beispiel, None)
    assert bericht.ok, bericht.als_text(beispiel.name)
    assert not bericht.befunde, bericht.als_text(beispiel.name)


def test_lint_kann_an_einem_beispiel_rot_werden(tmp_path):
    """Gegenprobe: sonst belegt „0 Fehler“ nur, dass der Linter lief."""
    sabotiert = _kopie(EMAIL_BEISPIELE[0], tmp_path, "an: ", "an: keine-adresse\nempfaenger: ")
    assert not falzmarke.linte(sabotiert, None).ok


@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
def test_die_fertige_nachricht_ist_gruen(beispiel, tmp_path):
    bericht = pruefung_eml.pruefe(_setze(beispiel, tmp_path))
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)
    assert len(bericht.pruefungen) >= 20, "zu wenige Prüfungen — das misst kaum etwas"


def test_die_pruefung_kann_an_einem_beispiel_rot_werden(tmp_path):
    """Gegenprobe zur Zeile darüber, an der fertigen Datei statt an der Quelle."""
    eml = _setze(EMAIL_BEISPIELE[0], tmp_path)
    roh = eml.read_text(encoding="utf-8")
    assert "Subject:" in roh, "die Sabotage kann nicht greifen"
    eml.write_text(roh.replace("Subject:", "X-Subject:", 1), encoding="utf-8", newline="")
    assert not pruefung_eml.pruefe(eml).ok


# ── Rundläufe ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
def test_der_parser_bekommt_alle_teile_zurueck(beispiel, tmp_path):
    """Was gebaut wurde, muss ein fremder Parser wiederfinden."""
    roh = _setze(beispiel, tmp_path).read_bytes()
    nachricht = email.message_from_bytes(roh, policy=policy.default)
    arten = [t.get_content_type() for t in nachricht.walk()]
    assert "text/plain" in arten and "text/html" in arten, arten
    for kopfzeile in ("From", "To", "Subject", "Date", "Content-Language"):
        assert nachricht.get(kopfzeile), f"{kopfzeile} fehlt nach dem Parsen"
    assert nachricht.get("Message-ID") is None, "eine Message-ID gehört dem Versender"


@pytest.mark.parametrize("delsp", [True, False], ids=["delsp=yes", "delsp=no"])
@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
def test_die_faltung_ist_umkehrbar(beispiel, delsp):
    # `ziel="email"`: Ohne das gilt die Vorgabe `brief`, und dort ist ein
    # Link ein Fehler (#103). Dieser Test misst die Mail-Fassung.
    bloecke = md.lies(_brieftext(beispiel), ziel="email")
    gefaltet = text.falte(bloecke, delsp=delsp)
    assert text.entfalte(gefaltet, delsp=delsp) == text.setze(bloecke)


def test_die_faltung_misst_ueberhaupt_etwas():
    """Ein Rundlauf über nie gefalteten Text ist trivial grün."""
    marken = sum(
        zeile.endswith(" ")
        for beispiel in EMAIL_BEISPIELE
        for zeile in text.falte(md.lies(_brieftext(beispiel), ziel="email")).split("\n")
    )
    assert marken > 0, "kein einziger weicher Umbruch — der Rundlauf belegt nichts"


# ── Der Quellteil trägt die Quelle und sonst nichts ─────────────────────────

@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
def test_ohne_flag_kein_quellteil(beispiel, tmp_path):
    """Vorgabe ist aus (ADR 0034, Punkt 3) — das Frontmatter bleibt drin."""
    roh = _setze(beispiel, tmp_path).read_bytes()
    arten = [t.get_content_type()
             for t in email.message_from_bytes(roh, policy=policy.default).walk()]
    assert "text/markdown" not in arten


@pytest.mark.parametrize("beispiel", EMAIL_BEISPIELE, **IDS)
def test_der_quellteil_traegt_genau_die_quelle(beispiel, tmp_path):
    roh = _setze(beispiel, tmp_path, mit_quelle=True).read_bytes()
    nachricht = email.message_from_bytes(roh, policy=policy.default)
    teil = next(t for t in nachricht.walk() if t.get_content_type() == "text/markdown")
    assert teil.get_content() == _brieftext(beispiel).lstrip("\n"), \
        "im text/markdown-Teil steht etwas anderes als der Brieftext"
    assert teil.get_param("variant") == "CommonMark"


# ── Anhänge ─────────────────────────────────────────────────────────────────

def test_die_anlage_haengt_an_der_mahnung(tmp_path):
    beispiel = next(b for b in EMAIL_BEISPIELE if b.stem == "email-mahnung")
    roh = _setze(beispiel, tmp_path).read_bytes()
    nachricht = email.message_from_bytes(roh, policy=policy.default)
    namen = [t.get_filename() for t in nachricht.walk() if t.get_filename()]
    assert namen == ["rechnung-2026-0815.pdf"], namen
    anhang = next(t for t in nachricht.walk() if t.get_filename())
    assert anhang.get_content_type() == "application/pdf"
    assert anhang.get_content().startswith(b"%PDF-"), "der Anhang ist kein PDF"


def test_die_quelle_der_anlage_bleibt_setzbar():
    """Die Anlage ist eingefroren; ihre Quelle darf trotzdem nicht vergammeln."""
    assert ANLAGE.is_file(), f"{ANLAGE} fehlt"
    bericht = falzmarke.linte(ANLAGE, None)
    assert bericht.ok, bericht.als_text(ANLAGE.name)


def test_ein_zu_grosser_anhang_faellt_auf(tmp_path):
    """Gegenprobe zur Grenze: ohne sie belegt „<= 10 MB“ nur, dass gerechnet wurde."""
    arbeit = tmp_path / "gross"
    arbeit.mkdir()
    dick = arbeit / "rechnung-2026-0815.pdf"
    dick.write_bytes(b"%PDF-1.4\n" + b"0" * (11 * 1_048_576))
    (arbeit / "nachricht.md").write_text(
        "---\ntyp: email\nprofil: example\nan: post@example.de\n"
        "betreff: Rechnung Nr. 2026-0815\nanrede: Sehr geehrte Damen und Herren,\n"
        "anlagen_dateien: [rechnung-2026-0815.pdf]\n---\n"
        "die Rechnung Nr. 2026-0815 liegt bei.\n", encoding="utf-8")
    eml, _ = falzmarke.setze_email(arbeit / "nachricht.md", arbeit / "nachricht")
    bericht = pruefung_eml.pruefe(eml)
    gescheitert = {p.name for p in bericht.pruefungen if not p.bestanden}
    assert "Gesamtgröße der Anhänge" in gescheitert, gescheitert
