"""Die Roadmap ist eine Sicht auf die Issues — sie darf nichts verschweigen.

`docs/ROADMAP.md` wird erzeugt, nicht gepflegt. Damit verschiebt sich die
Fehlerart: Nicht mehr „jemand hat vergessen, die Seite nachzuziehen", sondern
„die Seite sieht gepflegt aus und lässt etwas weg". Genau darauf zielen die
Gegenproben hier — jede prüft, dass ein Vorgang, der nirgends hingehört,
trotzdem sichtbar wird.

Geprüft wird die Darstellung gegen feste Daten, nicht gegen die GitHub-API. Der
Netzweg (`hole()`) ist bewusst von der Darstellung getrennt; ein Test, der ans
Netz ginge, wäre bei jeder Backlog-Änderung rot und würde deshalb abgeschaltet.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import roadmap                                                  # noqa: E402


def _issue(nummer, titel, meilenstein, labels=(), typ=None):
    vorgang = {
        "number": nummer,
        "title": titel,
        "html_url": f"https://github.com/blitzsicht/falzmarke/issues/{nummer}",
        "labels": [{"name": n} for n in labels],
        "milestone": {"title": meilenstein} if meilenstein else None,
    }
    if typ:
        vorgang["type"] = {"name": typ}
    return vorgang


def _probe(**abweichung):
    """Zwei Phasen, drei Issues — absichtlich in verkehrter Reihenfolge."""
    daten = {
        "milestones": [
            {"title": "Beweis", "description": "proof", "closed_issues": 0},
            {"title": "Vor Verbreitung", "description": "vor der Werbung", "closed_issues": 1},
        ],
        "issues": [
            _issue(7, "Auf PyPI veröffentlichen", "Vor Verbreitung", ["ci", "P1"]),
            _issue(12, "Normabgleich", "Vor Verbreitung", ["norm", "P0", "blockiert"]),
            _issue(14, "Signatur", "Beweis", ["recht", "P2"]),
        ],
    }
    daten.update(abweichung)
    return daten


# ── Positivproben ───────────────────────────────────────────────────────────

def test_die_probe_ergibt_ueberhaupt_etwas():
    """Ohne diesen Test liefen die Gegenproben unten gegen die leere Menge."""
    text = roadmap.rendere(_probe())
    assert text.count("|") > 10, text


def test_alle_vorgaenge_stehen_in_der_seite():
    text = roadmap.rendere(_probe())
    for nummer in (7, 12, 14):
        assert f"#{nummer}" in text, f"#{nummer} fehlt in der Roadmap"


def test_die_phasen_stehen_in_der_reihenfolge_von_adr_0030():
    """Die Probe liefert Beweis vor Vor Verbreitung — die Seite dreht das um."""
    text = roadmap.rendere(_probe())
    assert text.index("Vor Verbreitung") < text.index("Beweis"), text


def test_innerhalb_einer_phase_steht_die_hoehere_prioritaet_oben():
    text = roadmap.rendere(_probe())
    assert text.index("#12") < text.index("#7"), "P0 muss vor P1 stehen"


def test_zustand_und_bereich_werden_getrennt_ausgewiesen():
    zeile = [z for z in roadmap.ordne(_probe())[0][0]["zeilen"] if z["nummer"] == 12][0]
    assert zeile["bereiche"] == ["norm"]
    assert zeile["zustaende"] == ["blockiert"]
    assert zeile["prioritaet"] == "P0"


# ── Gegenproben: was still verschwinden könnte ──────────────────────────────

def test_ein_unbekannter_meilenstein_verschwindet_nicht():
    """ADR 0030 kennt sechs Phasen. Legt jemand eine siebte an, darf sie nicht
    aus der Seite fallen, nur weil das Skript sie nicht erwartet."""
    daten = _probe()
    daten["milestones"].append({"title": "Ganz neu", "description": "", "closed_issues": 0})
    daten["issues"].append(_issue(99, "Etwas Neues", "Ganz neu", ["P3"]))

    text = roadmap.rendere(daten)
    assert "Ganz neu" in text, "Der unbekannte Meilenstein fehlt ganz"
    assert "#99" in text, "Sein Issue fehlt"
    assert roadmap.FREMDE_PHASE in text, "Er steht da, aber ohne Hinweis darauf"


def test_gegenprobe_die_markierung_erscheint_nicht_ohne_anlass():
    """Sonst bestünde der Test darüber auch bei einer Seite, die alles markiert."""
    assert roadmap.FREMDE_PHASE not in roadmap.rendere(_probe())


def test_ein_issue_ohne_meilenstein_bekommt_eine_eigene_phase():
    daten = _probe()
    daten["issues"].append(_issue(50, "Vergessen zuzuordnen", None, ["doku"]))

    text = roadmap.rendere(daten)
    assert roadmap.OHNE_PHASE in text, "Der Abschnitt fehlt"
    assert "#50" in text, "Das nicht zugeordnete Issue wurde verschluckt"


def test_gegenprobe_ohne_phase_bleibt_weg_wenn_alles_zugeordnet_ist():
    """Ein leerer Abschnitt „Ohne Phase" auf jeder Seite wäre Rauschen und
    würde beim echten Fall nicht mehr auffallen."""
    assert roadmap.OHNE_PHASE not in roadmap.rendere(_probe())


def test_pull_requests_zaehlen_nicht_als_planungspunkte():
    """`repos/:nwo/issues` liefert auch Pull Requests. Ohne Filter stünde jeder
    offene PR als Vorhaben in der Roadmap."""
    daten = _probe()
    pr = _issue(33, "Trove-Classifier", "Vor Verbreitung", ["ci"])
    pr["pull_request"] = {"url": "..."}
    daten["issues"].append(pr)

    text = roadmap.rendere(daten)
    assert "#33" not in text, "Ein Pull Request steht in der Roadmap"
    assert "3 offene Vorgänge" in text, "Der PR wurde mitgezählt"


def test_ohne_meilensteine_gibt_es_keine_leere_seite():
    """Eine Roadmap mit null Phasen sähe aus wie ein gepflegter Stand, an dem
    nichts offen ist. Sie muss scheitern, nicht erscheinen."""
    with pytest.raises(roadmap.Roadmapfehler):
        roadmap.rendere({"milestones": [], "issues": []})


# ── Die Typ-Spalte, sobald die Organisation Typen führt ─────────────────────

def test_ohne_issue_typen_gibt_es_keine_typ_spalte():
    """Stand heute: die Organisation kennt die verlangten Typen nicht."""
    assert "| Typ |" not in roadmap.rendere(_probe())


def test_mit_issue_typen_erscheint_die_spalte_von_selbst():
    """Gegenprobe zum Test darüber — sonst belegte er nur, dass nie eine Spalte
    erscheint, auch wenn Typen da wären."""
    daten = _probe()
    daten["issues"][0]["type"] = {"name": "Epic"}
    text = roadmap.rendere(daten)
    assert "| Typ |" in text
    assert "Epic" in text


# ── Die Seite im Repo bleibt am Stand des Skripts ───────────────────────────

def test_die_roadmap_im_repo_ist_erzeugt_und_nicht_von_hand_geschrieben():
    """Wer die Datei von Hand ändert, verliert es beim nächsten Lauf. Der
    Hinweis darauf muss in der Datei stehen, nicht nur im Skript."""
    datei = REPO / "docs" / "ROADMAP.md"
    assert datei.exists(), "docs/ROADMAP.md fehlt — der README-Link zeigt ins Leere"
    text = datei.read_text(encoding="utf-8")
    assert "scripts/roadmap.py" in text
    assert "0030" in text, "Der Verweis auf ADR 0030 fehlt"


def test_die_readme_verlinkt_die_roadmap():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "docs/ROADMAP.md" in text


def test_das_skript_laeuft_ohne_netz_durch():
    """Der Aufruf, den die CI macht — nur mit Daten aus einer Datei."""
    import json
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fh:
        json.dump(_probe(), fh)
        pfad = fh.name

    lauf = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "roadmap.py"), "--aus", pfad, "--nach", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert "# Roadmap" in lauf.stdout
