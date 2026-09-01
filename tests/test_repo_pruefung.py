"""Nichts merkt, wenn die Repo-Einstellungen von den Sollwerten abweichen — bis jetzt.

WARUM ES DAS GIBT

Dreimal am 31.08.2026 ist eine Repo-Einstellung von ihrem Sollwert abgewichen
(#196 ein Pflicht-Check, #199 die Homepage, #201 die Ruleset-Durchsetzung).
Jedes Mal fand es ein Mensch beim Nachmessen, nie ein Test, nie die CI, nie
der Lauf selbst (#206). `scripts/repo_pruefung.py` vergleicht den gelebten
Zustand gegen die drei Sollwerte und schreibt nichts.

Diese Tests fahren gegen ein injiziertes `api`-Callable (Vorbild: `pruefen`
in `scripts/homepage.py`) — kein Netz, keine Admin-Rechte, kein `gh`. Jeder
Wert bekommt eine Gegenprobe: ein absichtlich verstellter Ist-Zustand MUSS
die Prüfung rot machen. Eine Prüfung, die dabei grün bleibt, ist kein Wächter
(Issue, Acceptance Criteria).
"""

from __future__ import annotations

import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import homepage                                                  # noqa: E402
import repo_pruefung                                              # noqa: E402

REPO_NAME = "blitzsicht/falzmarke"
SKRIPT = REPO / "scripts" / "repo-einstellungen.sh"
CI = REPO / ".github" / "workflows" / "ci.yml"

SOLL_CHECKS = sorted(repo_pruefung.pflicht_checks.pflicht_checks(CI))
EIN_CHECK_ZU_WENIG = SOLL_CHECKS[1:]


def _api(antworten: dict[str, object]):
    """Ein `api`-Fake: fester Pfad -> Antwort. Ein nicht vorgesehener Pfad ist
    ein Testfehler, keine stille Annahme."""
    def aufruf(pfad: str):
        if pfad not in antworten:
            raise AssertionError(f"unerwarteter API-Pfad: {pfad!r}")
        wert = antworten[pfad]
        if isinstance(wert, BaseException):
            raise wert
        return wert
    return aufruf


def _ruleset(name: str, ruleset_id: int, enforcement: str) -> dict:
    return {"id": ruleset_id, "name": name, "enforcement": enforcement}


def _ruleset_detail(checks: list[str]) -> dict:
    return {
        "rules": [
            {"type": "deletion"},
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{"context": c} for c in checks]},
            },
        ]
    }


def _vollstaendige_antworten(
    *, homepage_wert: str = "unveraendert",
    main_enforcement: str = "unveraendert",
    tags_enforcement: str = "unveraendert",
    checks: list[str] | None = None,
) -> dict[str, object]:
    """Ein Satz Antworten, in dem alle drei Werte exakt dem Soll entsprechen —
    Basis für die Gegenproben, die dann genau einen Wert verstellen."""
    if homepage_wert == "unveraendert":
        homepage_wert = homepage.STANDARD_DOMAIN
    if main_enforcement == "unveraendert":
        main_enforcement = repo_pruefung.SOLL_ENFORCEMENT
    if tags_enforcement == "unveraendert":
        tags_enforcement = repo_pruefung.SOLL_ENFORCEMENT
    if checks is None:
        checks = SOLL_CHECKS
    return {
        f"repos/{REPO_NAME}": {"homepage": homepage_wert},
        f"repos/{REPO_NAME}/rulesets": [
            _ruleset("main", 1, main_enforcement),
            _ruleset("release-tags", 2, tags_enforcement),
        ],
        f"repos/{REPO_NAME}/rulesets/1": _ruleset_detail(checks),
    }


def _pruefen(**kwargs) -> list[repo_pruefung.Abgleich]:
    return repo_pruefung.pruefe(REPO_NAME, api=_api(_vollstaendige_antworten(**kwargs)), workflow=CI)


def _finde(ergebnisse: list[repo_pruefung.Abgleich], teilname: str) -> repo_pruefung.Abgleich:
    treffer = [e for e in ergebnisse if teilname in e.name]
    assert len(treffer) == 1, f"{teilname!r} nicht eindeutig unter {[e.name for e in ergebnisse]}"
    return treffer[0]


# ── Deckungsgleichheit ───────────────────────────────────────────────────────


def test_stimmt_alles_ueberein_ist_jeder_abgleich_gruen():
    ergebnisse = _pruefen()
    assert all(e.stimmt for e in ergebnisse), ergebnisse
    assert repo_pruefung.austrittscode(ergebnisse) == 0


# ── Homepage: Gegenprobe ─────────────────────────────────────────────────────


def test_abweichende_homepage_wird_erkannt():
    ergebnisse = _pruefen(homepage_wert="https://verstellt.example")
    abgleich = _finde(ergebnisse, "Homepage")
    assert not abgleich.stimmt
    assert abgleich.soll == homepage.STANDARD_DOMAIN
    assert abgleich.ist == "https://verstellt.example"
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_gegenprobe_unveraenderte_homepage_ist_gruen():
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass IRGENDEIN
    Wert rot wird — nicht, dass die Homepage-Prüfung selbst trennscharf ist."""
    abgleich = _finde(_pruefen(), "Homepage")
    assert abgleich.stimmt


# ── Ruleset-Durchsetzung: Gegenprobe je Ruleset ─────────────────────────────


def test_zurueckgestuftes_main_ruleset_wird_erkannt():
    ergebnisse = _pruefen(main_enforcement="evaluate")
    abgleich = _finde(ergebnisse, "'main': enforcement")
    assert not abgleich.stimmt
    assert abgleich.soll == "active"
    assert abgleich.ist == "evaluate"
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_zurueckgestuftes_release_tags_ruleset_wird_erkannt():
    ergebnisse = _pruefen(tags_enforcement="disabled")
    abgleich = _finde(ergebnisse, "'release-tags': enforcement")
    assert not abgleich.stimmt
    assert abgleich.ist == "disabled"
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_gegenprobe_unveraenderte_rulesets_sind_gruen():
    ergebnisse = _pruefen()
    assert _finde(ergebnisse, "'main': enforcement").stimmt
    assert _finde(ergebnisse, "'release-tags': enforcement").stimmt


def test_fehlendes_ruleset_ist_eine_abweichung_nicht_ein_absturz():
    """Die Rulesets-Abfrage lief durch (kein Netz-/Admin-Fehler) — das Fehlen
    von 'release-tags' steht damit fest und ist eine echte Abweichung, kein
    dritter Zustand. Sonst würde ein gelöschtes Pflicht-Ruleset harmloser
    behandelt als ein bloß zurückgestuftes (Exit 2 statt Exit 1)."""
    antworten = _vollstaendige_antworten()
    antworten[f"repos/{REPO_NAME}/rulesets"] = [_ruleset("main", 1, "active")]
    ergebnisse = repo_pruefung.pruefe(REPO_NAME, api=_api(antworten), workflow=CI)
    abgleich = _finde(ergebnisse, "'release-tags': enforcement")
    assert not abgleich.unbekannt
    assert not abgleich.stimmt
    assert repo_pruefung.austrittscode(ergebnisse) == 1


# ── Pflicht-Check-Liste: Gegenprobe ─────────────────────────────────────────


def test_fehlender_pflicht_check_wird_erkannt():
    ergebnisse = _pruefen(checks=EIN_CHECK_ZU_WENIG)
    abgleich = _finde(ergebnisse, "Pflicht-Check-Liste")
    assert not abgleich.stimmt
    assert abgleich.soll == SOLL_CHECKS
    assert abgleich.ist == sorted(EIN_CHECK_ZU_WENIG)
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_zusaetzlicher_pflicht_check_wird_erkannt():
    ergebnisse = _pruefen(checks=SOLL_CHECKS + ["ein-check-den-es-in-ci-yml-nicht-gibt"])
    abgleich = _finde(ergebnisse, "Pflicht-Check-Liste")
    assert not abgleich.stimmt


def test_gegenprobe_unveraenderte_checkliste_ist_gruen():
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass IRGENDEINE
    Checkliste rot macht — nicht, dass die echte, unveränderte grün bleibt."""
    assert _finde(_pruefen(), "Pflicht-Check-Liste").stimmt


def test_reihenfolge_allein_ist_keine_abweichung():
    """required_status_checks kommt von der API nicht notwendig in derselben
    Reihenfolge zurück, in der sie gesetzt wurden — das ist keine Drift."""
    ergebnisse = _pruefen(checks=list(reversed(SOLL_CHECKS)))
    assert _finde(ergebnisse, "Pflicht-Check-Liste").stimmt


# ── Dritter Zustand: nicht abfragbar ist nicht dasselbe wie "stimmt" ────────


def test_api_fehler_bei_der_homepage_ergibt_unbekannt_nicht_gruen():
    antworten = _vollstaendige_antworten()
    antworten[f"repos/{REPO_NAME}"] = RuntimeError("kein Netz")
    ergebnisse = repo_pruefung.pruefe(REPO_NAME, api=_api(antworten), workflow=CI)
    abgleich = _finde(ergebnisse, "Homepage")
    assert abgleich.unbekannt
    assert not abgleich.stimmt
    assert "kein Netz" in abgleich.fehler


def test_api_fehler_bei_rulesets_betrifft_enforcement_und_checkliste():
    """Ein Endpunkt (rulesets) trägt zu zwei Abgleichen bei — fällt er aus,
    müssen beide den dritten Zustand zeigen, nicht nur einer."""
    antworten = _vollstaendige_antworten()
    antworten[f"repos/{REPO_NAME}/rulesets"] = RuntimeError("HTTP 403: keine Admin-Rechte")
    ergebnisse = repo_pruefung.pruefe(REPO_NAME, api=_api(antworten), workflow=CI)
    for teilname in ("'main': enforcement", "'release-tags': enforcement", "Pflicht-Check-Liste"):
        abgleich = _finde(ergebnisse, teilname)
        assert abgleich.unbekannt, teilname
        assert not abgleich.stimmt, teilname
    assert _finde(ergebnisse, "Homepage").stimmt


def test_api_fehler_beim_ruleset_detail_betrifft_nur_die_checkliste():
    antworten = _vollstaendige_antworten()
    antworten[f"repos/{REPO_NAME}/rulesets/1"] = RuntimeError("API-Fehler")
    ergebnisse = repo_pruefung.pruefe(REPO_NAME, api=_api(antworten), workflow=CI)
    assert _finde(ergebnisse, "Pflicht-Check-Liste").unbekannt
    assert _finde(ergebnisse, "'main': enforcement").stimmt


def test_gegenprobe_ohne_fehler_ist_nichts_unbekannt():
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass EIN Fehler
    irgendwas auf unbekannt setzt — nicht, dass der Normalfall frei davon ist."""
    assert not any(e.unbekannt for e in _pruefen())


# ── austrittscode(): reine Entscheidungslogik ───────────────────────────────


def _abgleich(soll="x", ist: str | None = "x", fehler: str | None = None) -> repo_pruefung.Abgleich:
    return repo_pruefung.Abgleich("t", soll, ist, fehler)


def test_austrittscode_null_wenn_alles_stimmt():
    assert repo_pruefung.austrittscode([_abgleich(), _abgleich()]) == 0


def test_austrittscode_eins_bei_abweichung():
    assert repo_pruefung.austrittscode([_abgleich(), _abgleich(ist="y")]) == 1


def test_austrittscode_zwei_bei_nur_unbekannt():
    assert repo_pruefung.austrittscode([_abgleich(), _abgleich(ist=None, fehler="kein Netz")]) == 2


def test_austrittscode_eins_wenn_abweichung_und_unbekannt_zusammentreffen():
    """Eine echte Abweichung wiegt schwerer als ein fehlender Wert — sie darf
    nicht hinter einem harmloseren Exit-Code verschwinden."""
    ergebnisse = [_abgleich(ist="y"), _abgleich(ist=None, fehler="kein Netz")]
    assert repo_pruefung.austrittscode(ergebnisse) == 1


# ── Das Skript: --pruefen setzt nichts ──────────────────────────────────────


def test_skript_kennt_das_pruefen_flag():
    text = SKRIPT.read_text(encoding="utf-8")
    assert "--pruefen" in text
    assert "python3 scripts/repo_pruefung.py" in text


def test_pruefen_zweig_endet_vor_dem_admin_check():
    """--pruefen braucht keine Admin-Rechte (AC: dritter Zustand statt Abbruch)
    — der Zweig muss vor der Admin-Vorprüfung abzweigen, sonst bricht ein Lauf
    ohne Admin-Rechte hart ab, bevor überhaupt etwas verglichen wurde."""
    text = SKRIPT.read_text(encoding="utf-8")
    pruefen_zweig = text.index("if [ \"$PRUEFEN\" = \"1\" ]")
    admin_check = text.index("keine Admin-Rechte auf")
    assert pruefen_zweig < admin_check


def test_pruefen_zweig_ruft_keine_schreibende_gh_operation_auf():
    """Gegenprobe zur ersten Acceptance-Criteria-Zeile: strukturell kann
    --pruefen nichts schreiben, weil der ganze Zweig vor jedem `tue()`/
    `gh api -X ...`/`gh repo edit`/`gh label create` per `exec` beendet."""
    text = SKRIPT.read_text(encoding="utf-8")
    start = text.index("if [ \"$PRUEFEN\" = \"1\" ]")
    ende = text.index("\nfi\n", start) + len("\nfi\n")
    zweig = text[start:ende]
    for verbotenes_muster in ("tue ", "gh api -X", "gh repo edit", "gh label create"):
        assert verbotenes_muster not in zweig, zweig


def test_repo_pruefung_ruft_selbst_keine_schreibende_gh_operation_auf():
    """`-X` taucht im Docstring als Erklärung auf ('kein `-X`') — geprüft wird
    deshalb das quotierte Argument, wie es ein echter `subprocess.run`-Aufruf
    bräuchte, nicht die bloße Zeichenkette."""
    text = (REPO / "scripts" / "repo_pruefung.py").read_text(encoding="utf-8")
    assert '"gh", "api"' in text
    assert '"-X"' not in text
    assert "'-X'" not in text


def test_beispiel_im_docstring_ist_lauffaehig_aufgebaut():
    """Regressionsschutz: Das im Modul-Docstring dokumentierte Aufrufmuster
    muss zum echten argparse-Interface passen."""
    text = (REPO / "scripts" / "repo_pruefung.py").read_text(encoding="utf-8")
    assert "python3 scripts/repo_pruefung.py --repo" in text
