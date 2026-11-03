"""Ein Vorgang, der das Werkzeug ändert, trägt einen Punkt in den Verlauf ein.

WARUM ES DAS GIBT

Von 46 Vorgängen zwischen v0.8.2 und v0.9.0 hat **einer** CHANGELOG.md
angefasst. Nach dem Nachtragen von 39 Einträgen von Hand (#214) waren es bei
den nächsten vier Vorgängen wieder **null**. Zweimal fiel damit die Nacharbeit
für ein halbes Hundert Vorgänge auf einmal an.

Der Grund war strukturell: Es gab keinen Ort für einen Eintrag ohne Version.
Den gibt es jetzt (`changelog.d/`), und dieser Prüfer sorgt dafür, dass er
benutzt wird (Issue #229).

WIE HIER GEPRÜFT WIRD

Jede Sabotage einzeln, nie gebündelt: Bei einem Lauf über mehrere zugleich
veränderte Stellen bliebe unbemerkt, wenn eine Prüfung gar nicht anschlägt —
die anderen färben das Ergebnis rot. Deshalb steht unten je Fall ein Test, und
zu jedem roten Fall der grüne Gegenpart, der belegt, dass die Prüfung nicht
einfach immer rot ist.
"""

from __future__ import annotations

import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import changelog                                                 # noqa: E402
import changelog_pflicht                                         # noqa: E402
import pytest                                                    # noqa: E402
from test_closing_keyword import CI, ci_mit_typen, pull_request_typen  # noqa: E402

CODE = "skill/falzmarke/geometrie.py"
EINTRAG = "changelog.d/230.behoben.md"


def leer(tmp_path):
    """Ein Fragmentverzeichnis ohne Fragmente — der Normalfall zwischen Releases."""
    verzeichnis = tmp_path / "changelog.d"
    verzeichnis.mkdir()
    return verzeichnis


def pruefe(pfade, tmp_path, **kwargs):
    return changelog_pflicht.pruefe(pfade, verzeichnis=leer(tmp_path), **kwargs)


# --- der Fall, um den es geht ----------------------------------------------

def test_eine_aenderung_am_werkzeug_ohne_eintrag_ist_rot(tmp_path):
    gut, grund = pruefe([CODE], tmp_path)
    assert not gut
    assert "changelog.d/" in grund


def test_gegenprobe_mit_eintrag_ist_dieselbe_aenderung_gruen(tmp_path):
    """Ohne diesen Test wäre nur belegt, dass der Prüfer rot werden kann."""
    gut, _ = pruefe([CODE, EINTRAG], tmp_path)
    assert gut


# --- die vier Ausnahmen, je einzeln ----------------------------------------

def test_abhaengigkeits_aktualisierung_braucht_keinen_eintrag(tmp_path):
    gut, _ = pruefe(["requirements.txt"], tmp_path, autor="dependabot[bot]")
    assert gut


def test_gegenprobe_derselbe_vorgang_von_einem_menschen_ist_rot(tmp_path):
    gut, _ = pruefe(["requirements.txt"], tmp_path, autor="siluri")
    assert not gut


def test_nur_doku_braucht_keinen_eintrag(tmp_path):
    gut, _ = pruefe(["docs/cli.md", "README.md"], tmp_path)
    assert gut


def test_nur_tests_brauchen_keinen_eintrag(tmp_path):
    gut, _ = pruefe(["tests/test_geometrie.py"], tmp_path)
    assert gut


def test_das_label_nimmt_ausdruecklich_aus(tmp_path):
    gut, _ = pruefe([CODE], tmp_path, labels=("ohne-changelog",))
    assert gut


def test_gegenprobe_ein_anderes_label_nimmt_nicht_aus(tmp_path):
    gut, _ = pruefe([CODE], tmp_path, labels=("P1", "ci"))
    assert not gut


# --- wo die Ausnahmen absichtlich nicht greifen ----------------------------

def test_code_und_doku_zusammen_brauchen_einen_eintrag(tmp_path):
    """Die Doku daneben macht aus einer Änderung am Werkzeug keine Doku-Änderung."""
    gut, _ = pruefe([CODE, "docs/cli.md"], tmp_path)
    assert not gut


def test_die_normregeln_sind_keine_doku(tmp_path):
    """`skill/references/din5008.md` ist die Quelle der Sollwerte.

    Fiele sie unter „nur Doku", ließe sich der Sollwert einer Regel ändern,
    ohne dass es im Verlauf erscheint — die Datei endet auf `.md`, und genau
    daran hängt die Doku-Ausnahme.
    """
    gut, _ = pruefe(["skill/references/din5008.md"], tmp_path)
    assert not gut


# --- die Fragmente selbst --------------------------------------------------

def test_eine_rubrik_ausserhalb_des_kanons_ist_rot(tmp_path):
    verzeichnis = leer(tmp_path)
    (verzeichnis / "230.quatsch.md").write_text("- Etwas.\n", encoding="utf-8")
    gut, grund = changelog_pflicht.pruefe([CODE, EINTRAG], verzeichnis=verzeichnis)
    assert not gut
    assert "quatsch" in grund


def test_ein_leeres_fragment_ist_rot(tmp_path):
    """Es würde beim Bündeln zu einem leeren Punkt — und fällt dann niemandem auf."""
    verzeichnis = leer(tmp_path)
    (verzeichnis / "230.behoben.md").write_text("\n  \n", encoding="utf-8")
    gut, grund = changelog_pflicht.pruefe([CODE, EINTRAG], verzeichnis=verzeichnis)
    assert not gut
    assert "leer" in grund


def test_ein_falsch_benanntes_fragment_ist_rot(tmp_path):
    verzeichnis = leer(tmp_path)
    (verzeichnis / "notizen.md").write_text("- Etwas.\n", encoding="utf-8")
    gut, _ = changelog_pflicht.pruefe([CODE, EINTRAG], verzeichnis=verzeichnis)
    assert not gut


def test_gegenprobe_ein_taugliches_fragment_ist_gruen(tmp_path):
    verzeichnis = leer(tmp_path)
    (verzeichnis / "230.behoben.md").write_text("- **Etwas.** Warum. (#230)\n",
                                                encoding="utf-8")
    gut, _ = changelog_pflicht.pruefe([CODE, EINTRAG], verzeichnis=verzeichnis)
    assert gut


# --- die Meldung ist eine Anleitung, keine Absage --------------------------

def test_die_meldung_sagt_wie_es_geht(tmp_path):
    """Wer sie liest, muss ohne Rückfrage handeln können.

    Der Empfänger ist oft ein Worker, der weder Issue-Kommentare noch die
    Beitragsseite sieht — die Meldung ist alles, was er bekommt.
    """
    _, grund = pruefe([CODE], tmp_path)
    for rubrik in changelog.RUBRIKEN:
        assert rubrik in grund
    assert "changelog.d/" in grund
    assert changelog_pflicht.AUSNAHME_LABEL in grund


def test_die_meldung_nennt_die_datei_die_den_eintrag_verlangt(tmp_path):
    _, grund = pruefe([CODE, "docs/cli.md"], tmp_path)
    assert CODE in grund
    assert "docs/cli.md" not in grund


def test_die_meldung_sagt_wie_der_check_nach_dem_label_neu_laeuft(tmp_path):
    """#437: Das Label setzt ein Maintainer nachträglich, und der Lauf bleibt rot."""
    gut, grund = pruefe([CODE], tmp_path)
    assert not gut
    assert "gh run rerun --job" in changelog_pflicht.NEUSTART
    assert changelog_pflicht.NEUSTART in grund, "NEUSTART fehlt in der Meldung"


def test_gegenprobe_mit_eintrag_kein_hinweis_auf_den_neustart(tmp_path):
    _, grund = pruefe([CODE, EINTRAG], tmp_path)
    assert changelog_pflicht.NEUSTART not in grund


def test_gegenprobe_ohne_den_satz_in_pruefe_wird_die_meldung_rot(tmp_path, monkeypatch):
    from test_gegenbeweis import _zeile_ersetzt

    monkeypatch.setattr(changelog_pflicht, "pruefe", _zeile_ersetzt(
        changelog_pflicht, "pruefe", '"\\n" + NEUSTART', '""'))
    with pytest.raises(AssertionError, match="NEUSTART"):
        test_die_meldung_sagt_wie_der_check_nach_dem_label_neu_laeuft(tmp_path)


def test_der_hinweis_stimmt_solange_labeled_nicht_ausloest_ein_push_aber_schon():
    """Der Satz sagt zweierlei über ci.yml, und beides muss stimmen.

    `labeled` startet nichts, darum der Hinweis. Ein Push (`synchronize`) startet
    neu, darum gilt er nur für das Label und nicht für das nachgereichte Fragment.
    """
    typen = pull_request_typen(CI.read_text(encoding="utf-8"))
    assert "labeled" not in typen, (
        f"ci.yml startet jetzt bei „labeled“ ({', '.join(typen)}): "
        "NEUSTART in scripts/changelog_pflicht.py ist überholt")
    assert "synchronize" in typen, (
        f"ci.yml startet nicht mehr bei „synchronize“ ({', '.join(typen)}): "
        "dann läuft auch nach dem Push mit dem Fragment nichts neu")


@pytest.mark.parametrize("typen, erwartet", [
    ("opened, synchronize, reopened, labeled", "bei „labeled“"),
    ("opened, reopened", "nicht mehr bei „synchronize“"),
])
def test_gegenprobe_mit_anderem_trigger_wird_der_hinweis_rot(typen, erwartet, tmp_path,
                                                             monkeypatch):
    """Jede Sabotage einzeln, je eine der beiden Aussagen des Satzes."""
    test_der_hinweis_stimmt_solange_labeled_nicht_ausloest_ein_push_aber_schon()  # Kontrolle
    monkeypatch.setattr(sys.modules[__name__], "CI", ci_mit_typen(tmp_path, typen))
    with pytest.raises(AssertionError, match=erwartet):
        test_der_hinweis_stimmt_solange_labeled_nicht_ausloest_ein_push_aber_schon()


# --- die Angaben, wie `gh` sie wirklich liefert ----------------------------

# Wörtlich die Ausgabe von `gh pr view 222 --json files,author,labels`, gemessen
# am 02.09.2026. Sie steht hier als Text und nicht als nachgebautes Objekt, weil
# genau die Schreibweise des Autors die Falle war: Die Ausnahme war zuerst auf
# „dependabot[bot]" gestellt — den Wert, den `github.actor` und die REST-API
# liefern. `gh pr view` sagt „app/dependabot". Eine Ausnahme, die nie greift,
# fühlt sich wie ein strenger Prüfer an und fällt darum nicht auf.
PR_222 = ('{"author":{"is_bot":true,"login":"app/dependabot"},'
          '"files":[{"path":".github/workflows/release.yml"}],'
          '"labels":[{"name":"maintainer"}]}')


def test_der_autor_aus_gh_pr_view_wird_erkannt(tmp_path):
    pfade, autor, labels = changelog_pflicht.aus_pr_json(PR_222)
    assert autor == "app/dependabot"
    gut, _ = changelog_pflicht.pruefe(pfade, autor, labels, verzeichnis=leer(tmp_path))
    assert gut


def test_gegenprobe_derselbe_vorgang_ohne_den_bot_ist_rot(tmp_path):
    """Ohne diesen Test bewiese der obige nur, dass irgendetwas grün ist."""
    pfade, _, labels = changelog_pflicht.aus_pr_json(PR_222)
    gut, _ = changelog_pflicht.pruefe(pfade, "siluri", labels, verzeichnis=leer(tmp_path))
    assert not gut


def test_ein_label_mit_leerzeichen_bleibt_ein_label(tmp_path):
    """Als Wortliste durch die Shell gereicht, zerfiele es in drei."""
    _, _, labels = changelog_pflicht.aus_pr_json(
        '{"author":{"login":"siluri"},"files":[{"path":"a.py"}],'
        '"labels":[{"name":"good first issue"},{"name":"ohne-changelog"}]}')
    assert labels == ("good first issue", "ohne-changelog")
    gut, _ = changelog_pflicht.pruefe(["a.py"], "siluri", labels,
                                      verzeichnis=leer(tmp_path))
    assert gut


def test_ein_pr_ohne_labels_bricht_nicht_ab(tmp_path):
    """`gh` liefert dann `null`, nicht `[]` — beides muss durchgehen."""
    pfade, autor, labels = changelog_pflicht.aus_pr_json(
        '{"author":{"login":"siluri"},"files":[{"path":"a.py"}],"labels":null}')
    assert labels == ()
    gut, _ = changelog_pflicht.pruefe(pfade, autor, labels, verzeichnis=leer(tmp_path))
    assert not gut


# ── Die Meldung muss beim Aufrufer ankommen (#276) ──────────────────────────

def test_die_meldung_bleibt_unter_cp1252_lesbar(tmp_path):
    """Die Meldung trägt „ und “ — unter Windows schreibt Python in cp1252.

    Gemessen am 08.09.2026 am Schwester-Prüfer `closing_keyword.py`: Der
    Windows-Lauf zu PR #270 scheiterte nicht am Prüfer, sondern an seiner
    Ausgabe. `stderr` kam als None zurück, weil sich die Bytes nicht als UTF-8
    lesen ließen — der Aufrufer bekam nichts, obwohl der Befund richtig war.

    Hier fiel es bisher nicht auf, weil der Job „Changelog-Eintrag"
    ausschließlich auf ubuntu läuft. Der Test erzwingt cp1252 über
    PYTHONIOENCODING und läuft damit auf jedem System, nicht nur auf einem
    Windows-Läufer. Ohne `_ausgabe_auf_utf8()` endet er mit der Meldung aus der
    CI: „'utf-8' codec can't decode byte 0xdf".
    """
    import os
    import subprocess

    skript = REPO / "scripts" / "changelog_pflicht.py"
    umgebung = {**os.environ, "PYTHONIOENCODING": "cp1252"}

    # Ein Vorgang, der das Werkzeug ändert und keinen Eintrag mitbringt: Der
    # Prüfer MUSS hier melden, sonst prüfte der Test eine leere Ausgabe.
    befund = subprocess.run(
        [sys.executable, str(skript), "--verzeichnis", str(tmp_path), CODE],
        capture_output=True, text=True, encoding="utf-8", env=umgebung)
    assert befund.returncode == 1, befund.stdout + (befund.stderr or "")
    assert "changelog.d" in befund.stderr

    # Gegenpart im selben Lauf: mit Eintrag geht derselbe Aufruf durch — sonst
    # bewiese der rote Fall nur, dass irgendetwas fehlschlägt.
    frei = subprocess.run(
        [sys.executable, str(skript), "--verzeichnis", str(tmp_path), CODE, EINTRAG],
        capture_output=True, text=True, encoding="utf-8", env=umgebung)
    assert frei.returncode == 0, frei.stderr
