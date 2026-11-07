"""Die Aktion für fremde Repositories (action.yml).

Was hier geprüft wird, ist die Beschreibung — Eingaben, Ausgaben, gepinnte
Fremd-Actions, Erwähnung in der README. Ob sie *läuft*, kann kein lokaler Test
sagen: Dafür braucht es einen Runner, und dafür gibt es
`.github/workflows/aktion.yml`, der sie auf den eigenen Beispielbriefen
ausführt — samt einem Job, der verlangt, dass ein Muster ohne Treffer
abbricht.

Diese Trennung ist keine Bequemlichkeit. Ein Test, der `action.yml` nur parst
und für gut befindet, würde eine Aktion durchwinken, die auf jedem Runner
scheitert. Deshalb steht der Lauf in CI und nicht hier.
"""

from __future__ import annotations

import re

import pytest
import yaml

from conftest import REPO

AKTION = REPO / "action.yml"
SELBSTTEST = REPO / ".github" / "workflows" / "aktion.yml"
CI = REPO / ".github" / "workflows" / "ci.yml"
WORKFLOW_ORDNER = REPO / ".github" / "workflows"


def _pin_dateien(ordner) -> list:
    """Jede Datei, deren `uses:` GitHub ausführt: Workflows mit beiden Endungen, die
    GitHub annimmt (`.yml` und `.yaml`), dazu action.yml. AKTION wird erst beim Aufruf
    gelesen, damit die Gegenprobe es umbiegen kann."""
    return sorted([*ordner.glob("*.yml"), *ordner.glob("*.yaml")]) + [AKTION]


PIN_DATEIEN = _pin_dateien(WORKFLOW_ORDNER)
_USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)")


@pytest.fixture(scope="module")
def aktion() -> dict:
    return yaml.safe_load(AKTION.read_text(encoding="utf-8"))


def test_die_aktion_ist_gueltiges_yaml_mit_den_pflichtfeldern(aktion):
    for feld in ("name", "description", "runs"):
        assert feld in aktion, f"action.yml fehlt „{feld}“"
    assert aktion["runs"]["using"] == "composite"


def test_jede_eingabe_wird_auch_benutzt(aktion):
    """Eine Eingabe, die nirgends vorkommt, ist eine Zusage ohne Wirkung."""
    roh = AKTION.read_text(encoding="utf-8")
    schritte = roh[roh.index("runs:"):]
    unbenutzt = [name for name in aktion["inputs"]
                 if f"inputs.{name}" not in schritte]
    assert not unbenutzt, f"Eingaben ohne Wirkung: {unbenutzt}"


def test_jede_ausgabe_wird_auch_gesetzt(aktion):
    """`outputs` verspricht Werte — sie müssen aus einem Schritt kommen."""
    roh = AKTION.read_text(encoding="utf-8")
    for name, feld in aktion["outputs"].items():
        wert = str(feld["value"])
        treffer = re.search(r"steps\.([\w-]+)\.outputs\.(\w+)", wert)
        if not treffer:
            # Direkt aus einer Eingabe durchgereicht — auch gültig.
            assert "inputs." in wert, f"Ausgabe „{name}“ kommt aus dem Nichts: {wert}"
            continue
        schritt, schluessel = treffer.groups()
        assert f"id: {schritt}" in roh, f"Ausgabe „{name}“ nennt Schritt „{schritt}“, den es nicht gibt"
        assert f'echo "{schluessel}=' in roh, (
            f"Ausgabe „{name}“ erwartet „{schluessel}“ in GITHUB_OUTPUT, "
            "geschrieben wird es nirgends"
        )


def test_fremde_actions_sind_auf_sha_gepinnt(aktion):
    """Ein beweglicher Tag ist eine fremde Hand im eigenen Lauf.

    Das Repository pinnt seine Actions seit c1300c0 auf Commit-SHAs. Eine
    Aktion, die *andere* Repositories in ihre Läufe einbauen, darf davon am
    wenigsten abweichen: Wer sie benutzt, erbt jede Fassung, die sie zieht.
    """
    # Kommentarzeilen ausnehmen: Der Kopf von action.yml zeigt als Beispiel
    # `uses: blitzsicht/falzmarke@main` — ein Verweis auf diese Aktion selbst,
    # keine fremde Abhängigkeit. Die erste Fassung dieser Prüfung hat ihn
    # mitgezählt und action.yml damit für ungepinnt erklärt.
    ungepinnt = [
        zeile.strip()
        for zeile in AKTION.read_text(encoding="utf-8").splitlines()
        if "uses:" in zeile
        and not zeile.lstrip().startswith("#")
        and not re.search(r"uses:\s*\S+@[0-9a-f]{40}", zeile)
    ]
    assert not ungepinnt, f"nicht auf SHA gepinnt: {ungepinnt}"


def test_jede_action_in_den_workflows_ist_auf_einen_commit_sha_gepinnt():
    """Die Hausregel gilt für jeden Workflow, nicht nur für action.yml.

    Bis zum 07.11.2026 stand die Publish-Action in release.yml als begründete
    Ausnahme auf einem Tag. Die Begründung beruhte auf einer Verwechslung: Am
    26.08. war die SHA des annotierten Tag-Objekts eingetragen, nicht die des
    Commits, und für die gibt es kein Image. Ohne diese Prüfung kehrte eine
    solche Ausnahme still zurück.

    Ob eine SHA ein Commit ist und kein Tag-Objekt, sieht der Test nicht; das
    steht als Messanleitung am Pin in release.yml.

    Seit dem Nachreview von #580 gehören `.yaml`-Dateien und action.yml dazu. Die
    ältere Prüfung oben sucht in action.yml nur nach 40 Hex-Zeichen irgendwo hinter
    dem @, diese verlangt genau 40.
    """
    aus_workflows = 0
    ungepinnt = []
    for datei in PIN_DATEIEN:
        for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
            treffer = _USES.search(zeile.split("#", 1)[0])
            if not treffer or treffer.group(1).startswith("./"):
                continue
            aus_workflows += datei != AKTION
            if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", treffer.group(1)):
                ungepinnt.append(f"{datei.name}:{nr}: {treffer.group(1)}")
    # Gezählt wird nur, was aus den Workflows kommt: action.yml allein hielte den
    # Zählwert über null, auch wenn der Glob nichts mehr findet.
    assert aus_workflows, "keine fremde Action in .github/workflows gefunden: Glob oder Muster kaputt?"
    assert not ungepinnt, "nicht auf Commit-SHA gepinnt: " + ", ".join(ungepinnt)


def test_jede_action_steht_in_allen_dateien_auf_derselben_sha():
    """Eine vergessene Stelle beim Anheben fällt sonst nicht auf.

    #580 hob setup-python an 14 Stellen in sieben Dateien von Hand an. Bliebe eine
    stehen, liefe etwa der Release mit einer anderen Fassung als die CI, und jede
    andere Prüfung bliebe grün: Beide SHAs sind voll und gepinnt. Die Prüfung
    darunter vergleicht nur action.yml mit ci.yml.
    """
    fundstellen: dict[str, dict[str, list[str]]] = {}
    for datei in PIN_DATEIEN:
        for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
            treffer = _USES.search(zeile.split("#", 1)[0])
            ziel = re.fullmatch(r"([\w.-]+/[\w./-]+)@([0-9a-f]{40})", treffer.group(1)) if treffer else None
            if ziel:
                fundstellen.setdefault(ziel.group(1), {}).setdefault(ziel.group(2), []).append(
                    f"{datei.name}:{nr}")
    assert fundstellen, "keine gepinnte Action gefunden: Glob oder Muster kaputt?"
    abweichend = [
        f"{name}: " + "; ".join(f"{sha[:8]} in {', '.join(orte)}" for sha, orte in shas.items())
        for name, shas in sorted(fundstellen.items())
        if len(shas) > 1
    ]
    assert not abweichend, "dieselbe Action auf verschiedenen SHAs: " + " | ".join(abweichend)


def test_die_gepinnten_fassungen_stimmen_mit_der_ci_ueberein():
    """Zwei Orte, dieselbe Action, verschiedene SHAs — das driftet still.

    Wenn die CI ihre Actions hochzieht und action.yml nicht, benutzt die
    Aktion für fremde Repositories ab da eine ältere Fassung als das eigene
    Haus. Auffallen würde das nie.
    """
    def sha_je_action(text: str) -> dict[str, str]:
        return {
            treffer.group(1): treffer.group(2)
            for treffer in re.finditer(r"uses:\s*([\w.-]+/[\w.-]+)@([0-9a-f]{40})", text)
        }

    in_aktion = sha_je_action(AKTION.read_text(encoding="utf-8"))
    in_ci = sha_je_action(CI.read_text(encoding="utf-8"))
    assert in_aktion, "action.yml benutzt gar keine fremde Action — Test veraltet?"

    abweichend = {
        name: (sha, in_ci[name])
        for name, sha in in_aktion.items()
        if name in in_ci and in_ci[name] != sha
    }
    assert not abweichend, (
        "action.yml und ci.yml pinnen dieselbe Action auf verschiedene Fassungen: "
        + ", ".join(f"{n}: {a[:8]} vs {b[:8]}" for n, (a, b) in abweichend.items())
    )


def test_der_selbsttest_prueft_auch_den_leeren_fall():
    """Ohne Gegenprobe belegte der Selbsttest nur, dass es bei gutem Wetter läuft.

    Ein Muster ohne Treffer muss abbrechen. Stillschweigend null Briefe zu
    rendern und grün zu melden wäre der teuerste Ausgang: Der Betreiber glaubt,
    seine Briefe seien gesetzt und geprüft.
    """
    inhalt = SELBSTTEST.read_text(encoding="utf-8")
    plan = yaml.safe_load(inhalt)
    assert "gegenprobe" in plan["jobs"], "der Selbsttest hat keine Gegenprobe"
    assert "continue-on-error" in inhalt
    assert 'outcome }}" != "failure"' in inhalt, (
        "die Gegenprobe verlangt keinen Fehlschlag — dann kann sie nicht rot werden"
    )


def test_der_selbsttest_benutzt_die_aktion_aus_diesem_baum():
    """`uses: ./` — sonst prüft er eine fremde Fassung."""
    plan = yaml.safe_load(SELBSTTEST.read_text(encoding="utf-8"))
    verwendet = [
        schritt.get("uses")
        for job in plan["jobs"].values()
        for schritt in job["steps"]
    ]
    assert "./" in verwendet, f"der Selbsttest benutzt nicht ./: {verwendet}"


def test_der_selbsttest_nimmt_den_code_dieses_zweiges():
    """Sonst prüft er die letzte Veröffentlichung, nicht den Stand im PR.

    Am 26.08.2026 hat genau das zugeschlagen: Der Selbsttest installierte
    v0.7.3 von PyPI und scheiterte an `examples/brief-englisch.md`, weil das
    Feld `sprache` erst nach dieser Fassung dazukam. Die Beispiele im
    Repository laufen der Veröffentlichung voraus — der Selbsttest muss
    deshalb den Zweig nehmen, und der PyPI-Weg bekommt einen eigenen Job mit
    einem Brief, der sich nicht mitbewegt.
    """
    plan = yaml.safe_load(SELBSTTEST.read_text(encoding="utf-8"))
    schritte = [s for s in plan["jobs"]["selbsttest"]["steps"] if s.get("uses") == "./"]
    assert schritte, "der Selbsttest benutzt die Aktion gar nicht"
    assert schritte[0]["with"].get("paket") == ".", (
        "der Selbsttest installiert nicht den Code dieses Zweiges"
    )
    assert "mit-pypi" in plan["jobs"], "der Weg über PyPI wird nirgends geprüft"


def test_die_readme_nennt_die_aktion():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "action.yml" in readme or "blitzsicht/falzmarke@" in readme, (
        "Die Aktion steht nicht in der README — dann findet sie niemand."
    )
