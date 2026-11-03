"""Ein deutscher Schließsatz ist für GitHub kein Schließsatz.

WARUM ES DAS GIBT

PR #262 trug im Rumpf „Schließt #261." Nach dem Squash-Merge auf `main` meldete
`gh issue view 261` weiterhin `OPEN`; das Issue musste von Hand geschlossen
werden. GitHub wertet ausschließlich englische Keywords aus — `close`, `fix`,
`resolve` in ihren Beugungen. Dieses Repository schreibt deutsch, die Falle
wiederholt sich also bei jedem Vorgang, und sie fällt nur auf, wenn jemand
hinterher nachsieht (Issue #268).

WIE HIER GEPRÜFT WIRD

Jeder rote Fall hat seinen grünen Gegenpart, und beide unterscheiden sich in
**einer** Sache. Ohne den Gegenpart belegte ein Befund nur, dass der Prüfer
etwas meldet — nicht, dass er das Richtige meldet. Ein Prüfer, der immer rot
ist, wird nach dem zweiten Vorgang abgeschaltet.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import closing_keyword                                           # noqa: E402

SKRIPT = REPO / "scripts" / "closing_keyword.py"


# ── Der Befund ──────────────────────────────────────────────────────────────

def test_deutscher_satz_ohne_keyword_ist_ein_befund():
    gut, grund = closing_keyword.pruefe("Schließt #261.")
    assert not gut
    assert "#261" in grund
    assert "Closes #261" in grund, "die Abhilfe muss im Klartext dastehen"


def test_derselbe_satz_mit_keyword_geht_durch():
    """Der Gegenpart: eine Zeile mehr, sonst identisch."""
    gut, _ = closing_keyword.pruefe("Schließt #261.\n\nCloses #261")
    assert gut


def test_alle_deutschen_verben_werden_gesehen():
    """Ein Verb, das die Liste nicht kennt, ist eine stille Lücke."""
    for verb in closing_keyword.DEUTSCHE_VERBEN:
        gut, _ = closing_keyword.pruefe(f"{verb.capitalize()} #7.")
        assert not gut, f"„{verb}“ wird nicht als Zusage gelesen"


# ── Die Gegenpart-Fälle: der Prüfer ist nicht einfach immer rot ─────────────

def test_englisches_keyword_allein_geht_durch():
    gut, _ = closing_keyword.pruefe("Closes #261. Der Rest ist deutsch.")
    assert gut


def test_deutscher_satz_ohne_nummer_geht_durch():
    """„Schließt die Lücke" ist Prosa, keine Zusage an einen Vorgang."""
    gut, _ = closing_keyword.pruefe("Schließt die Lücke im Prüfer und behebt den Rest.")
    assert gut


def test_label_nimmt_aus():
    gut, grund = closing_keyword.pruefe("Schließt #261.",
                                        (closing_keyword.AUSNAHME_LABEL,))
    assert gut and closing_keyword.AUSNAHME_LABEL in grund


def test_leerer_rumpf_geht_durch():
    assert closing_keyword.pruefe("")[0]
    assert closing_keyword.pruefe(None)[0]


# ── Die beiden Fälle, die eine grobere Prüfung übersähe ─────────────────────

def test_keyword_auf_eine_andere_nummer_deckt_nichts():
    """Je Nummer, nicht als Menge.

    „Closes #99" neben „Schließt #261" ist kein Beleg für #261. Eine Prüfung,
    die nur fragt „steht irgendwo ein englisches Keyword?", ließe genau den
    Rumpf durch, der zwei Vorgänge nennt und einen davon vergisst.
    """
    gut, grund = closing_keyword.pruefe("Schließt #261. Closes #99")
    assert not gut
    assert "#261" in grund and "#99" not in grund.split("Ohne englisches Keyword:")[1][:40]


def test_satz_im_auszug_ist_ein_beispiel():
    """Ein Prüfer, der an seiner eigenen Beschreibung anschlägt, ist keiner."""
    gut, _ = closing_keyword.pruefe("So nicht:\n\n```\nSchließt #261\n```\n")
    assert gut


def test_ausgeschriebene_adresse_zaehlt():
    """GitHub liest die volle URL genauso — der Prüfer muss das auch."""
    gut, _ = closing_keyword.pruefe(
        "Schließt #261.\n\nCloses https://github.com/blitzsicht/falzmarke/issues/261")
    assert gut


# ── Nach der Korrektur bleibt der rote Lauf stehen (#437) ───────────────────

CI = REPO / ".github" / "workflows" / "ci.yml"

# Was GitHub für `pull_request` ohne `types:` einsetzt (Dokumentation „Events
# that trigger workflows", Abschnitt pull_request; an PR #432 bestätigt: nach
# `gh pr edit` lief nichts neu).
VORGABE_TYPEN = ("opened", "synchronize", "reopened")


def pull_request_typen(ci_text: str) -> tuple[str, ...]:
    """Die Ereignisarten, bei denen ci.yml für einen Pull Request startet."""
    import yaml

    daten = yaml.safe_load(ci_text)
    # PyYAML liest den Schlüssel `on` nach YAML 1.1 als True.
    ausloeser = daten["on"] if "on" in daten else daten[True]
    if isinstance(ausloeser, str):
        ausloeser = {ausloeser: None}
    elif isinstance(ausloeser, list):
        ausloeser = dict.fromkeys(ausloeser)
    typen = (ausloeser["pull_request"] or {}).get("types")
    if typen is None:
        return VORGABE_TYPEN
    return (typen,) if isinstance(typen, str) else tuple(typen)


def ci_mit_typen(tmp_path, typen: str):
    """ci.yml mit einer `types:`-Zeile unter `pull_request:`, als Sabotage."""
    text = CI.read_text(encoding="utf-8")
    alt = "\n  pull_request:\n"
    assert text.count(alt) == 1, "der Trigger steht nicht mehr in der erwarteten Form"
    datei = tmp_path / "ci.yml"
    datei.write_text(text.replace(alt, f"{alt}    types: [{typen}]\n"), encoding="utf-8")
    return datei


def test_die_meldung_sagt_wie_der_check_neu_laeuft():
    gut, grund = closing_keyword.pruefe("Schließt #261.")
    assert not gut
    assert "gh run rerun --job" in closing_keyword.NEUSTART
    assert closing_keyword.NEUSTART in grund, "NEUSTART fehlt in der Meldung"


def test_gegenprobe_ohne_befund_kein_hinweis_auf_den_neustart():
    _, grund = closing_keyword.pruefe("Closes #261.")
    assert closing_keyword.NEUSTART not in grund


def test_gegenprobe_ohne_den_satz_in_pruefe_wird_die_meldung_rot(monkeypatch):
    from test_gegenbeweis import _zeile_ersetzt

    monkeypatch.setattr(closing_keyword, "pruefe", _zeile_ersetzt(
        closing_keyword, "pruefe", '"\\n" + NEUSTART', '""'))
    with pytest.raises(AssertionError, match="NEUSTART"):
        test_die_meldung_sagt_wie_der_check_neu_laeuft()


def test_der_hinweis_stimmt_solange_edited_und_labeled_nicht_ausloesen():
    """Der Satz behauptet etwas über ci.yml. Ändert sich der Trigger, ist er falsch.

    Kommt `edited` oder `labeled` dazu (#437, Weg 1), startet der Check von
    selbst neu, und der Hinweis schickt jeden zu einem Neustart, den es nicht
    mehr braucht. Dann gehört er aus beiden Skripten heraus.
    """
    typen = pull_request_typen(CI.read_text(encoding="utf-8"))
    for typ in ("edited", "labeled"):
        assert typ not in typen, (
            f"ci.yml startet jetzt bei „{typ}“ ({', '.join(typen)}): NEUSTART in "
            "scripts/closing_keyword.py und scripts/changelog_pflicht.py ist überholt")


@pytest.mark.parametrize("typ", ["edited", "labeled"])
def test_gegenprobe_mit_dem_ereignis_im_trigger_wird_der_hinweis_rot(typ, tmp_path, monkeypatch):
    """Jede Sabotage einzeln: eine Probe, die nur `edited` sähe, fiele hier auf."""
    test_der_hinweis_stimmt_solange_edited_und_labeled_nicht_ausloesen()   # Kontrolle
    monkeypatch.setattr(sys.modules[__name__], "CI",
                        ci_mit_typen(tmp_path, f"opened, synchronize, reopened, {typ}"))
    with pytest.raises(AssertionError, match=f"bei „{typ}“"):
        test_der_hinweis_stimmt_solange_edited_und_labeled_nicht_ausloesen()


# ── Der Weg, den die CI tatsächlich geht ───────────────────────────────────

def test_pr_json_wird_gelesen(tmp_path):
    """Nicht die Funktion, sondern der Aufruf aus ci.yml — mit echtem Exit-Code."""
    datei = tmp_path / "pr.json"
    datei.write_text('{"body": "Schließt #261.", "labels": []}', encoding="utf-8")
    ergebnis = subprocess.run([sys.executable, str(SKRIPT), "--pr-json", str(datei)],
                              capture_output=True, text=True, encoding="utf-8")
    assert ergebnis.returncode == 1
    assert "#261" in ergebnis.stderr

    datei.write_text('{"body": "Closes #261.", "labels": []}', encoding="utf-8")
    kontrolle = subprocess.run([sys.executable, str(SKRIPT), "--pr-json", str(datei)],
                               capture_output=True, text=True, encoding="utf-8")
    assert kontrolle.returncode == 0, kontrolle.stderr


def test_die_meldung_bleibt_unter_cp1252_lesbar(tmp_path):
    """Die Meldung traegt „ und “ — unter Windows schreibt Python in cp1252.

    Gemessen am 08.09.2026: Der Windows-Lauf zu #268 scheiterte nicht am
    Pruefer, sondern an seiner Ausgabe. `stderr` kam als None zurueck, weil sich
    die Bytes nicht als UTF-8 lesen liessen — der Aufrufer bekam also nichts,
    obwohl der Befund richtig war.

    Der Test erzwingt cp1252 ueber PYTHONIOENCODING und laeuft damit auf jedem
    System. Ohne `_ausgabe_auf_utf8()` endet er mit genau der Meldung aus der
    CI: „'utf-8' codec can't decode byte 0xdf".
    """
    datei = tmp_path / "pr.json"
    datei.write_text('{"body": "Schließt #261.", "labels": []}', encoding="utf-8")
    ergebnis = subprocess.run(
        [sys.executable, str(SKRIPT), "--pr-json", str(datei)],
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "cp1252"})
    assert ergebnis.returncode == 1
    assert "#261" in ergebnis.stderr


def test_der_job_steht_in_ci_yml():
    """Ein Prüfer ohne Aufrufer prüft nichts.

    `scripts/pflicht_checks.py` leitet die Pflicht-Checks des Rulesets aus
    ci.yml ab — steht der Job dort nicht, wird er nie zu einem.
    """
    import yaml

    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"))
    job = workflow["jobs"]["closing-keyword"]
    assert job["name"] == "Closing-Keyword"
    assert "closing_keyword.py" in yaml.dump(job)

    sys.path.insert(0, str(REPO / "scripts"))
    import pflicht_checks

    assert "Closing-Keyword" in pflicht_checks.pflicht_checks(
        REPO / ".github" / "workflows" / "ci.yml")
