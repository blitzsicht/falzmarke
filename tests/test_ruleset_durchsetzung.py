"""Das main-Ruleset bleibt scharf, wenn niemand etwas anderes verlangt.

WARUM ES DAS GIBT

Bis zum 31.08.2026 stand in `scripts/repo-einstellungen.sh`:

    DURCHSETZUNG="evaluate"
    [ "${FALZMARKE_RULESET_AKTIV:-0}" = "1" ] && DURCHSETZUNG="active"

Der scharfe Zustand war damit der Sonderfall. Als der Kommentar darüber
geschrieben wurde, war das richtig — es war noch offen, ob die Regeln zum
Ablauf passen. Seit #190 passen sie, und beide Rulesets stehen auf "active".
Ein gewöhnlicher Lauf ohne Umgebungsvariablen hätte `main` trotzdem auf
"evaluate" zurückgestuft: Verstöße werden dann noch gemeldet, aber nichts
blockiert mehr. Der einzige Hinweis darauf war eine Zeile mitten in langer
Ausgabe (Issue #201).

Gemessen wurde das im Trockenlauf, nicht vermutet — er kündigte
`"enforcement": "evaluate"` für ein Ruleset an, das laut API `active` ist.

Diese Tests lesen die Entscheidungszeilen aus der echten Datei und führen sie
in `bash` aus. Eine Textzusicherung würde nur den Wortlaut festhalten; wer den
Default zurückdreht, käme daran vorbei. Diese Tests werden rot.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from conftest import REPO

SKRIPT = REPO / "scripts" / "repo-einstellungen.sh"


def _entscheidungszeilen() -> str:
    """Die Zeilen aus dem echten Skript, die DURCHSETZUNG festlegen.

    Bewusst aus der Datei gelesen statt abgetippt: Ein Test gegen eine Kopie
    misst die Kopie. Kommentarzeilen fallen raus, damit ein erklärender Text
    mit dem Wort DURCHSETZUNG den Test nicht verfälscht.
    """
    zeilen = [
        z
        for z in SKRIPT.read_text(encoding="utf-8").splitlines()
        if "DURCHSETZUNG=" in z and not z.lstrip().startswith("#")
    ]
    assert zeilen, "Keine Zeile setzt DURCHSETZUNG — das Skript hat sich grundlegend geändert"
    return "\n".join(zeilen)


def _durchsetzung(**umgebung: str) -> str:
    """Fährt die Entscheidungszeilen in bash und gibt DURCHSETZUNG zurück.

    Die Umgebung wird geerbt und nur um die FALZMARKE_RULESET_*-Variablen
    bereinigt, nicht ersetzt. Ein `env={"PATH": …}` ohne den Rest ließ die
    Windows-CI scheitern: Git Bash startet dort, findet aber seine eigene
    Laufzeitumgebung nicht mehr und endet mit Exit 1 (gemessen in Lauf
    33382792073, PR #202). Das Bereinigen ist trotzdem nötig — sonst würde
    eine im Terminal gesetzte Variable den Standardfall verfälschen.
    """
    basis = {
        schluessel: wert
        for schluessel, wert in os.environ.items()
        if not schluessel.startswith("FALZMARKE_RULESET")
    }
    fertig = subprocess.run(
        ["bash", "-c", _entscheidungszeilen() + '\nprintf "%s" "$DURCHSETZUNG"'],
        capture_output=True,
        text=True,
        env={**basis, **umgebung},
        check=True,
    )
    return fertig.stdout


def test_ohne_jede_umgebungsvariable_bleibt_active():
    assert _durchsetzung() == "active", (
        "Ein Lauf ohne Umgebungsvariablen würde main entwaffnen — genau der "
        "Zustand, den Issue #201 beschreibt."
    )


def test_gegenprobe_die_variable_stuft_herunter():
    """Ohne diesen Fall belegt der erste Test nur, dass irgendwas 'active' sagt."""
    assert _durchsetzung(FALZMARKE_RULESET_EVALUATE="1") == "evaluate"


def test_leere_variable_stuft_nicht_herunter():
    assert _durchsetzung(FALZMARKE_RULESET_EVALUATE="") == "active"


def test_die_alte_variable_hat_keine_wirkung_mehr():
    """`FALZMARKE_RULESET_AKTIV=1` war der alte Weg zum Scharfschalten.

    Sie darf nicht still weiterwirken: Wer sie aus Gewohnheit setzt, soll
    denselben scharfen Zustand bekommen wie jeder andere Lauf auch.
    """
    assert _durchsetzung(FALZMARKE_RULESET_AKTIV="1") == "active"


def test_die_alte_variable_kommt_nirgends_mehr_vor():
    assert "FALZMARKE_RULESET_AKTIV" not in SKRIPT.read_text(encoding="utf-8"), (
        "Ein Rest der alten Variablen im Skript wäre ein zweiter, "
        "widersprechender Schalter."
    )


@pytest.mark.parametrize(
    "vorher,nachher,erwartet_warnung",
    [
        ("active", "evaluate", True),
        ("active", "active", False),
        ("evaluate", "evaluate", False),
        ("", "active", False),
    ],
)
def test_herunterstufung_wird_gemeldet(vorher, nachher, erwartet_warnung, tmp_path):
    """Die Warnung ist der zweite Teil von #201.

    Der Default allein reicht nicht: Wer bewusst herunterstuft, soll es sehen,
    und wer es versehentlich tut, erst recht. Die Funktion wird aus der echten
    Datei ausgeschnitten und einzeln gefahren.
    """
    text = SKRIPT.read_text(encoding="utf-8")
    start = text.index("warne_bei_herunterstufung() {")
    ende = text.index("\n}\n", start) + len("\n}\n")
    funktion = text[start:ende]

    fertig = subprocess.run(
        ["bash", "-c", funktion + f'\nwarne_bei_herunterstufung main "{vorher}" "{nachher}"'],
        capture_output=True,
        text=True,
        check=True,
    )
    hat_warnung = "ACHTUNG" in fertig.stdout
    assert hat_warnung is erwartet_warnung, (
        f"vorher={vorher!r} nachher={nachher!r}: Warnung={hat_warnung}, "
        f"erwartet={erwartet_warnung}. Ausgabe: {fertig.stdout!r}"
    )


def test_die_warnung_nennt_die_folge_nicht_nur_den_zustandswechsel():
    """'active -> evaluate' sagt einem Menschen um 23 Uhr nichts.

    Die Meldung muss benennen, was verlorengeht.
    """
    text = SKRIPT.read_text(encoding="utf-8")
    start = text.index("warne_bei_herunterstufung() {")
    ende = text.index("\n}\n", start)
    funktion = text[start:ende]
    assert "NICHT mehr geschuetzt" in funktion
