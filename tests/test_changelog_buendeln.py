"""Aus den Fragmenten wird beim Release ein Versionsabschnitt (Issue #229).

Der Gegenpart zu tests/test_changelog_pflicht.py: Dort wird verlangt, dass ein
Vorgang seinen Punkt ablegt, hier wird eingelöst, dass die abgelegten Punkte
auch ankommen. Ohne diese Seite wäre die Pflicht eine Sackgasse — Dateien, die
sich sammeln und die niemand einsammelt.
"""

from __future__ import annotations

import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import changelog                                                 # noqa: E402

WORTLAUT = ("- **`verify --email` schlug bei jeder nummerierten Liste fehl.** Der HTML-Teil\n"
            "  setzt die Liste als `<ol><li>`; die Ziffern erzeugt der Browser über\n"
            "  CSS-Counter. (#216)")


def verzeichnis_mit(tmp_path, **dateien):
    verzeichnis = tmp_path / "changelog.d"
    verzeichnis.mkdir()
    for name, inhalt in dateien.items():
        (verzeichnis / name.replace("__", ".")).write_text(inhalt, encoding="utf-8")
    return verzeichnis


def changelog_mit(tmp_path, text="## v0.9.1 — 01.09.2026\n\nAlt.\n"):
    quelle = tmp_path / "CHANGELOG.md"
    quelle.write_text("# Änderungen\n\n" + text, encoding="utf-8")
    return quelle


def test_die_rubriken_stehen_in_kanon_reihenfolge(tmp_path):
    """Nicht alphabetisch: „Neu" gehört nach oben, „Infrastruktur" nach unten."""
    verzeichnis = verzeichnis_mit(
        tmp_path,
        a__infrastruktur__md="- Ein Werkzeug.",
        b__neu__md="- Etwas Neues.",
        c__behoben__md="- Etwas Behobenes.",
        d__geaendert__md="- Etwas Geändertes.",
    )
    abschnitt = changelog.gebuendelt("v0.9.2", "02.09.2026", verzeichnis)
    stellen = [abschnitt.index(f"### {r}")
               for r in ("Neu", "Geändert", "Behoben", "Infrastruktur")]
    assert stellen == sorted(stellen)


def test_der_wortlaut_ueberlebt_ungekuerzt(tmp_path):
    """Er wandert von hier über CHANGELOG.md bis in die README auf PyPI."""
    verzeichnis = verzeichnis_mit(tmp_path, **{"216__behoben__md": WORTLAUT})
    abschnitt = changelog.gebuendelt("v0.9.2", "02.09.2026", verzeichnis)
    assert WORTLAUT in abschnitt


def test_der_abschnitt_kommt_vor_die_bisher_juengste_version(tmp_path):
    verzeichnis = verzeichnis_mit(tmp_path, **{"216__behoben__md": "- Etwas."})
    quelle = changelog_mit(tmp_path)
    changelog.buendeln("v0.9.2", "02.09.2026", verzeichnis, quelle)
    text = quelle.read_text(encoding="utf-8")
    assert text.index("## v0.9.2") < text.index("## v0.9.1")
    assert text.startswith("# Änderungen")


def test_die_fragmente_sind_danach_weg(tmp_path):
    """Sonst erschienen sie bei der nächsten Version ein zweites Mal."""
    verzeichnis = verzeichnis_mit(tmp_path, **{"216__behoben__md": "- Etwas."})
    changelog.buendeln("v0.9.2", "02.09.2026", verzeichnis, changelog_mit(tmp_path))
    assert list(verzeichnis.glob("*.md")) == []


def test_ohne_v_davor_geht_auch(tmp_path):
    verzeichnis = verzeichnis_mit(tmp_path, **{"216__behoben__md": "- Etwas."})
    quelle = changelog_mit(tmp_path)
    changelog.buendeln("0.9.2", "02.09.2026", verzeichnis, quelle)
    assert "## v0.9.2 — 02.09.2026" in quelle.read_text(encoding="utf-8")


# --- die drei Abbrüche -----------------------------------------------------

def test_ein_leeres_verzeichnis_bricht_ab_statt_zu_leeren(tmp_path):
    """Eine Version ohne einen einzigen Punkt wäre ein leerer Abschnitt."""
    verzeichnis = verzeichnis_mit(tmp_path)
    with pytest.raises(SystemExit, match="nichts zu bündeln"):
        changelog.gebuendelt("v0.9.2", "02.09.2026", verzeichnis)


def test_eine_schon_vergebene_version_bricht_ab(tmp_path):
    """Auf PyPI ist eine Nummer unwiderruflich belegt (ADR 0036)."""
    verzeichnis = verzeichnis_mit(tmp_path, **{"216__behoben__md": "- Etwas."})
    with pytest.raises(SystemExit, match="schon"):
        changelog.buendeln("v0.9.1", "02.09.2026", verzeichnis, changelog_mit(tmp_path))


def test_ein_untaugliches_fragment_bricht_ab_statt_es_zu_uebergehen(tmp_path):
    """Ein übergangener Punkt fehlt, ohne dass es jemand merkt."""
    verzeichnis = verzeichnis_mit(tmp_path, **{"216__quatsch__md": "- Etwas."})
    with pytest.raises(SystemExit, match="quatsch"):
        changelog.gebuendelt("v0.9.2", "02.09.2026", verzeichnis)


# --- gegen das echte Verzeichnis -------------------------------------------

def test_die_wirklich_abgelegten_fragmente_taugen():
    """Nicht die erfundenen von oben, sondern die, die gerade im Repo liegen.

    Ohne diesen Test fiele ein unbrauchbares Fragment erst beim Bündeln auf —
    also beim Release, wenn die Version schon feststeht und niemand mehr Lust
    hat, den Lauf abzubrechen.
    """
    if not changelog.FRAGMENTE.is_dir():
        return
    maengel = [m for m in (changelog.fragment_mangel(p)
                           for p in sorted(changelog.FRAGMENTE.glob("*.md"))) if m]
    assert maengel == []


def test_das_verzeichnis_ueberlebt_ein_leeres_release():
    """`.gitkeep` hält es im Git, sonst wäre es nach dem Bündeln verschwunden."""
    assert (changelog.FRAGMENTE / ".gitkeep").is_file()


# --- der Weg zum Release ---------------------------------------------------

def test_das_release_bricht_ab_wenn_eintraege_liegenbleiben():
    """Wer `--buendeln` vergisst, veröffentlicht eine Version mit Lücken.

    Die Punkte der letzten Vorgänge fehlten dann still — und auf PyPI ist die
    Nummer unwiderruflich belegt (ADR 0036), die Lücke bleibt. Der Schritt steht
    vor dem Packen, damit gar kein Release entsteht.

    Dieser Test hält ihn fest: Ohne ihn ließe sich der Wächter aus release.yml
    entfernen, ohne dass etwas rot wird.
    """
    import yaml

    release = REPO / ".github" / "workflows" / "release.yml"
    daten = yaml.safe_load(release.read_text(encoding="utf-8"))
    schritte = daten["jobs"]["skill-paket"]["steps"]
    namen = [s.get("name", "") for s in schritte]

    assert "Kein Eintrag darf liegenbleiben" in namen
    waechter = schritte[namen.index("Kein Eintrag darf liegenbleiben")]
    assert "changelog.d" in waechter["run"]
    assert "exit 1" in waechter["run"]

    # Vor dem Packen, nicht danach: Ein Abbruch hinterher hätte das
    # GitHub-Release schon erzeugt.
    assert namen.index("Kein Eintrag darf liegenbleiben") < namen.index("Skill packen")


def test_das_makefile_kennt_den_buendel_aufruf():
    """Sonst steht der Handgriff nur in der Doku und niemand findet ihn."""
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "buendeln:" in makefile
    assert "--buendeln" in makefile


# --- der Sammelpunkt der Abhängigkeits-Vorgänge (#233) ---------------------

def _bot_repo(tmp_path, *autoren):
    """Ein winziges git-Repo mit einem Tag und je einem Commit pro Autor."""
    import subprocess

    def git(*args):
        subprocess.run(("git", "-C", str(tmp_path)) + args, check=True,
                       capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "probe@example.de")
    git("config", "user.name", "Probe")
    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "Anfang")
    git("tag", "v0.0.1")
    for nummer, autor in enumerate(autoren, start=1):
        (tmp_path / "a.txt").write_text(str(nummer + 1), encoding="utf-8")
        git("add", "-A")
        git("commit", "-qm", f"paket-{nummer} von 1 auf 2 (#{nummer})",
            f"--author={autor} <bot@example.de>")
    return tmp_path


def test_der_bot_wird_im_verlauf_gefunden(tmp_path):
    """Der Anker ist der Autor des Squash-Commits, nicht sein Betreff.

    Den Betreff schreibt beim Merge ein Mensch; den Autor übernimmt GitHub vom
    Vorgang. Am 02.09.2026 an `f626515` gemessen: dort steht `dependabot[bot]`.
    """
    repo = _bot_repo(tmp_path, "dependabot[bot]")
    assert changelog.bot_vorgaenge("v0.0.1", repo) == ["paket-1 von 1 auf 2 (#1)"]


def test_die_eckigen_klammern_sind_kein_regex(tmp_path):
    """Der Fehler, der diesen Test erzwungen hat.

    `git log --author` nimmt einen **Regex**. In `dependabot[bot]` wäre `[bot]`
    eine Zeichenklasse — der Filter fände nichts, und die leere Liste sähe aus
    wie „keine Aktualisierungen". Erst `-F` macht daraus einen festen Text.
    Gemessen: ohne `-F` null Treffer, mit `-F` einer.

    Ein Autor, den das Regex-Muster fälschlich träfe, gibt es hier nicht — der
    Test prüft die Gegenrichtung: Der echte Name MUSS gefunden werden.
    """
    repo = _bot_repo(tmp_path, "dependabot[bot]")
    assert changelog.bot_vorgaenge("v0.0.1", repo), "der Filter trifft nicht"


def test_ein_mensch_landet_nicht_im_sammelpunkt(tmp_path):
    """Sonst wäre der Punkt immer voll und niemals aussagekräftig."""
    repo = _bot_repo(tmp_path, "siluri")
    assert changelog.bot_vorgaenge("v0.0.1", repo) == []


def test_ein_unlesbarer_verlauf_bricht_ab_statt_leer_zu_melden(tmp_path):
    """„Nicht geprüft" ist kein „nichts passiert" (claim-verification)."""
    kein_repo = tmp_path / "leer"
    kein_repo.mkdir()
    with pytest.raises(SystemExit, match="nicht lesbar"):
        changelog.bot_vorgaenge("v0.0.1", kein_repo)


def test_ein_vorgang_wird_eine_zeile():
    assert changelog.sammelpunkt(["a von 1 auf 2 (#1)"]) == \
        "- **Abhängigkeiten aktualisiert.** a von 1 auf 2 (#1)"


def test_mehrere_vorgaenge_werden_eine_unterliste():
    punkt = changelog.sammelpunkt(["a (#1)", "b (#2)"])
    assert punkt.startswith("- **Abhängigkeiten aktualisiert.**\n")
    assert "  - a (#1)" in punkt and "  - b (#2)" in punkt


def test_ohne_vorgang_entsteht_kein_punkt():
    """Sonst stünde in jeder Version eine leere Überschrift „Infrastruktur"."""
    assert changelog.sammelpunkt([]) is None


def test_der_sammelpunkt_legt_die_rubrik_an_wenn_sie_fehlt(tmp_path):
    verzeichnis = verzeichnis_mit(tmp_path, **{"1__behoben__md": "- Etwas."})
    abschnitt = changelog.gebuendelt("v0.9.2", "02.09.2026", verzeichnis,
                                     "- **Abhängigkeiten aktualisiert.** x (#1)")
    assert abschnitt.count("### Infrastruktur") == 1
    assert abschnitt.index("### Behoben") < abschnitt.index("### Infrastruktur")


def test_der_sammelpunkt_verdoppelt_die_rubrik_nicht(tmp_path):
    verzeichnis = verzeichnis_mit(tmp_path, **{"1__infrastruktur__md": "- Etwas."})
    abschnitt = changelog.gebuendelt("v0.9.2", "02.09.2026", verzeichnis,
                                     "- **Abhängigkeiten aktualisiert.** x (#1)")
    assert abschnitt.count("### Infrastruktur") == 1


def test_allein_der_sammelpunkt_traegt_eine_version(tmp_path):
    """Eine Version, in der nur Abhängigkeiten stiegen, ist keine leere Version."""
    verzeichnis = verzeichnis_mit(tmp_path)
    abschnitt = changelog.gebuendelt("v0.9.2", "02.09.2026", verzeichnis,
                                     "- **Abhängigkeiten aktualisiert.** x (#1)")
    assert "### Infrastruktur" in abschnitt and "x (#1)" in abschnitt
