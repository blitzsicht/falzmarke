"""Die Themen des Repositories — die Liste selbst, nicht ihr Abgleich.

Der Abgleich gegen den gelebten Zustand steht in `tests/test_repo_pruefung.py`.
Hier geht es um die Quelle: Sie kann still ihre Wirkung verlieren, ohne dass
dort etwas rot wird — wer `mcp` aus `scripts/topics.py` streicht, macht Setzen
und Prüfen wieder deckungsgleich, und beide sind sich dann einig über den
Zustand, den #237 gerade behebt.

Zweiter Fall, ebenso still: GitHub nimmt höchstens 20 Themen an. Das 21. wird
verworfen, ohne Fehler und ohne Meldung — ein neuer Eintrag könnte einen alten
hinauswerfen, und niemand sähe es.
"""

from __future__ import annotations

import subprocess
import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import topics                                                     # noqa: E402

SKRIPT = REPO / "scripts" / "repo-einstellungen.sh"


def test_die_mcp_themen_stehen_drin():
    """Der Anlass von #237: Kein Verzeichnis fand den MCP-Server, weil keines
    der drei Themen gesetzt war."""
    for thema in ("mcp", "mcp-server", "model-context-protocol"):
        assert thema in topics.TOPICS, f"{thema} fehlt — #237 wäre zurückgenommen"


def test_die_liste_bleibt_unter_der_grenze_von_github():
    assert len(topics.TOPICS) <= topics.HOECHSTZAHL, (
        f"{len(topics.TOPICS)} Themen — GitHub nimmt höchstens "
        f"{topics.HOECHSTZAHL} an und verwirft den Rest wortlos.")


def test_kein_thema_steht_doppelt():
    doppelt = sorted({t for t in topics.TOPICS if topics.TOPICS.count(t) > 1})
    assert not doppelt, f"doppelte Themen: {', '.join(doppelt)}"


def test_die_themen_sind_gueltige_github_themen():
    """GitHub nimmt Kleinbuchstaben, Ziffern und Bindestriche, höchstens 50
    Zeichen. Ein Thema mit Unterstrich oder Großbuchstabe wird stillschweigend
    umgeschrieben oder abgelehnt — der Setz-Lauf meldete trotzdem Erfolg."""
    import re
    for thema in topics.TOPICS:
        assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", thema), (
            f"{thema!r} ist kein gültiges GitHub-Thema")


def test_das_skript_liest_die_liste_und_zaehlt_sie_nicht_selbst():
    """Gegenprobe gegen die Lage vor #237: Dort stand die Aufzählung im
    Skript, nannte zehn Themen — und auf dem Repository lagen fünfzehn."""
    text = SKRIPT.read_text(encoding="utf-8")
    assert "python3 scripts/topics.py" in text, (
        "repo-einstellungen.sh liest die Themen nicht aus scripts/topics.py")
    assert "for t in falzmarke din5008" not in text, (
        "Die alte, hartkodierte Themen-Schleife steht wieder im Skript.")


def test_das_skript_gibt_jedes_thema_im_trockenlauf_aus():
    """Der Weg von der Liste bis zum `gh`-Aufruf, einmal wirklich gegangen.

    Ohne diesen Lauf belegten die Tests darüber nur, dass eine Python-Liste
    die richtigen Wörter enthält — nicht, dass das Skript sie auch setzt.
    """
    fertig = subprocess.run(
        ["bash", str(SKRIPT), "--trocken", "blitzsicht/falzmarke"],
        capture_output=True, text=True, encoding="utf-8", cwd=REPO,
    )
    if "keine Admin-Rechte" in fertig.stderr or fertig.returncode not in (0, 1):
        import pytest
        pytest.skip("Trockenlauf braucht `gh` mit Admin-Rechten auf dem Repo")
    if fertig.returncode != 0:
        import pytest
        pytest.skip(f"Trockenlauf nicht durchführbar: {fertig.stderr.strip()[:120]}")
    for thema in topics.TOPICS:
        assert f"--add-topic {thema}" in fertig.stdout, (
            f"{thema} taucht im Trockenlauf nicht auf")
