"""Nichts merkt, wenn die Repo-Einstellungen von den Sollwerten abweichen — bis jetzt.

WARUM ES DAS GIBT

Dreimal am 31.08.2026 ist eine Repo-Einstellung von ihrem Sollwert abgewichen
(#196 ein Pflicht-Check, #199 die Homepage, #201 die Ruleset-Durchsetzung).
Jedes Mal fand es ein Mensch beim Nachmessen, nie ein Test, nie die CI, nie
der Lauf selbst (#206). `scripts/repo_pruefung.py` vergleicht den gelebten
Zustand gegen die Sollwerte und schreibt nichts.

Diese Tests fahren gegen ein injiziertes `api`-Callable (Vorbild: `pruefen`
in `scripts/homepage.py`) — kein Netz, keine Admin-Rechte, kein `gh`. Jeder
Wert bekommt eine Gegenprobe: ein absichtlich verstellter Ist-Zustand MUSS
die Prüfung rot machen. Eine Prüfung, die dabei grün bleibt, ist kein Wächter
(Issue, Acceptance Criteria).
"""

from __future__ import annotations

import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import homepage                                                  # noqa: E402
import durchsetzung                                              # noqa: E402
import repo_pruefung                                              # noqa: E402
import topics                                                     # noqa: E402

REPO_NAME = "blitzsicht/falzmarke"
SKRIPT = REPO / "scripts" / "repo-einstellungen.sh"
CI = REPO / ".github" / "workflows" / "ci.yml"

#: Die echte Registry-Abfrage, zur Importzeit festgehalten.
#:
#: Die Autouse-Sperre unten ersetzt `repo_pruefung.registry_namen` durch eine
#: Attrappe. Ein Test, der die ECHTE Abfrage messen will, bekäme damit die
#: Attrappe und bestünde immer — gemessen am 11.09.2026, der erste Entwurf
#: dieser Datei hatte genau diesen Fehler.
ECHTE_REGISTRY_SUCHE = repo_pruefung.registry_namen

SOLL_CHECKS = sorted(repo_pruefung.pflicht_checks.pflicht_checks(CI))
EIN_CHECK_ZU_WENIG = SOLL_CHECKS[1:]


@pytest.fixture(autouse=True)
def kein_netz_zum_registry(monkeypatch):
    """Keine Registry-Abfrage verlässt den Test (#237).

    Autouse und nicht nur als Parameter von `_pruefen`: `pruefe()` wird in
    dieser Datei an fünf Stellen auch direkt aufgerufen, und ein Helfer, den man
    an einer Stelle vergessen kann, wird dort vergessen. Die Vorgabe ist
    „gelistet" — der Normalfall, damit die Tests, die „alles stimmt" erwarten,
    weiter über alle Werte laufen.

    Ein Test, der die Gegenrichtung messen will, injiziert sie über
    `_pruefen(im_registry=…)` und überschreibt damit diese Vorgabe.
    """
    monkeypatch.setattr(repo_pruefung, "registry_namen", lambda name, **_: [name])


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
    themen: list[str] | None = None,
    repo_fehler: Exception | None = None,
) -> dict[str, object]:
    """Ein Satz Antworten, in dem jeder Wert exakt dem Soll entspricht —
    Basis für die Gegenproben, die dann genau einen Wert verstellen."""
    if homepage_wert == "unveraendert":
        homepage_wert = homepage.STANDARD_DOMAIN
    if main_enforcement == "unveraendert":
        main_enforcement = durchsetzung.STANDARD
    if tags_enforcement == "unveraendert":
        tags_enforcement = durchsetzung.STANDARD
    if checks is None:
        checks = SOLL_CHECKS
    if themen is None:
        themen = list(topics.TOPICS)
    return {
        f"repos/{REPO_NAME}": (repo_fehler if repo_fehler is not None
                               else {"homepage": homepage_wert, "topics": themen}),
        f"repos/{REPO_NAME}/rulesets": [
            _ruleset("main", 1, main_enforcement),
            _ruleset("release-tags", 2, tags_enforcement),
        ],
        f"repos/{REPO_NAME}/rulesets/1": _ruleset_detail(checks),
    }


def _pruefen(*, domain_antwortet: bool = True, im_registry: bool | Exception = True,
             umgebung: dict[str, str] | None = None, **kwargs) -> list[repo_pruefung.Abgleich]:
    """`domain_antwortet` wird injiziert, nie wirklich abgefragt (Issue #210).

    Der Sollwert der Homepage hängt seither davon ab: Antwortet die Domain
    nicht, ist die Release-Seite der richtige Wert und nicht der falsche. Ohne
    diesen Parameter ginge jeder Test hier ins Netz — und wäre damit von der
    Erreichbarkeit von falzmarke.com abhängig statt von seiner eigenen Aussage.

    `im_registry` ist seit #237 aus demselben Grund dabei: Die Registry-Abfrage
    greift sonst bei **jedem** Test dieser Datei auf einen fremden Dienst zu.
    Ein `Exception` als Wert stellt den dritten Zustand her — nicht geprüft.
    """
    def suche(name: str) -> list[str]:
        if isinstance(im_registry, Exception):
            raise im_registry
        return [name] if im_registry else []

    return repo_pruefung.pruefe(REPO_NAME, api=_api(_vollstaendige_antworten(**kwargs)),
                                workflow=CI, domain_pruefen=lambda _: domain_antwortet,
                                registry_suche=suche,
                                umgebung=umgebung or {})


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


# ── Homepage: der legitime Rückfall (#210) ──────────────────────────────────
#
# `scripts/homepage.py` kennt einen dokumentierten Rückfall: Antwortet die
# Domain nicht, ist die Release-Seite der richtige Wert. Der Wächter verglich
# bis #210 unbedingt gegen STANDARD_DOMAIN und meldete dann ABWEICHUNG für
# genau diesen Normalfall. Ein Wächter, der grundlos anschlägt, wird
# abgeschaltet — dann ist er schlechter als keiner.


def test_der_rueckfall_auf_die_release_seite_ist_keine_abweichung():
    """Domain antwortet nicht, Homepage steht deshalb auf der Release-Seite."""
    ergebnisse = _pruefen(domain_antwortet=False,
                          homepage_wert=homepage.release_seite(REPO_NAME))
    abgleich = _finde(ergebnisse, "Homepage")
    assert abgleich.stimmt, abgleich
    assert repo_pruefung.austrittscode(ergebnisse) == 0


def test_die_release_seite_bei_erreichbarer_domain_ist_sehr_wohl_eine_abweichung():
    """Die Gegenprobe dazu — ohne sie hätte der Fix den Wächter an dieser
    Stelle nur blind gemacht: Dann wäre die Release-Seite immer in Ordnung,
    auch wenn jemand die Homepage von Hand darauf zurückgestellt hat."""
    ergebnisse = _pruefen(domain_antwortet=True,
                          homepage_wert=homepage.release_seite(REPO_NAME))
    abgleich = _finde(ergebnisse, "Homepage")
    assert not abgleich.stimmt, abgleich
    assert abgleich.soll == homepage.STANDARD_DOMAIN
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_bei_toter_domain_ist_die_domain_selbst_ebenso_in_ordnung():
    """Der Fall, den das Issue nicht bedacht hat — und der häufigere.

    Fällt die Domain aus, ohne dass jemand `repo-einstellungen.sh` fährt, steht
    die Homepage weiter auf der Domain. Verlangte der Wächter dann die
    Release-Seite, schlüge er bei jedem Netzhänger an: Der Fehlalarm aus #210
    wäre nicht behoben, sondern nur auf den anderen Fall verschoben.

    Welcher der beiden Werte dasteht, hängt allein am Zeitpunkt des letzten
    Setz-Laufs. Beide sind legitim; keiner ist eine Verstellung.
    """
    ergebnisse = _pruefen(domain_antwortet=False, homepage_wert=homepage.STANDARD_DOMAIN)
    abgleich = _finde(ergebnisse, "Homepage")
    assert abgleich.stimmt, abgleich
    assert repo_pruefung.austrittscode(ergebnisse) == 0


def test_bei_erreichbarer_domain_gibt_es_keine_zweite_gueltige_fassung():
    """Gegenprobe zur Nachsicht oben: Sie gilt nur bei toter Domain.

    Wäre `ebenso_gueltig` immer gefüllt, ginge die Release-Seite dauerhaft
    durch — und der Fall aus #199, bei dem der Verweis auf falzmarke.com still
    verloren ging, fiele nie wieder auf.
    """
    assert _finde(_pruefen(domain_antwortet=True), "Homepage").ebenso_gueltig == ()
    assert _finde(_pruefen(domain_antwortet=False), "Homepage").ebenso_gueltig \
        == (homepage.STANDARD_DOMAIN,)


def test_eine_fremde_domain_faellt_auch_bei_totem_netz_auf():
    """Die zweite Gegenprobe: Der Rückfall entschuldigt die Release-Seite, nicht
    jeden beliebigen Wert. Steht dort etwas Drittes, hat jemand verstellt — und
    das bleibt eine Abweichung, ob die Domain nun antwortet oder nicht."""
    ergebnisse = _pruefen(domain_antwortet=False,
                          homepage_wert="https://verstellt.example")
    abgleich = _finde(ergebnisse, "Homepage")
    assert not abgleich.stimmt, abgleich
    assert abgleich.soll == homepage.release_seite(REPO_NAME)


def test_bei_erreichbarer_domain_bleibt_der_sollwert_die_domain():
    """Kontrollprobe: Der eingebaute Rückfall darf den Normalfall nicht
    verschieben. Sonst prüfte der Wächter dauerhaft gegen die Release-Seite."""
    assert _finde(_pruefen(domain_antwortet=True), "Homepage").soll == homepage.STANDARD_DOMAIN


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
    ergebnisse = repo_pruefung.pruefe(REPO_NAME, api=_api(antworten), workflow=CI,
                                      domain_pruefen=lambda _: True)
    abgleich = _finde(ergebnisse, "'release-tags': enforcement")
    assert not abgleich.unbekannt
    assert not abgleich.stimmt
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_fehlendes_main_ruleset_wird_ebenso_erkannt():
    """Derselbe Fall wie oben, nur für `main` — den Fall, für den der Wächter
    überhaupt existiert.

    Beide laufen durch `_pruefe_durchsetzung`, nur anders parametrisiert; das
    Regressionsrisiko ist klein. Aber `main` war der einzige Sollwert ohne
    eigenen Testfall, und ein Fehler, den kein Testfall auslösen kann, ist von
    einem behobenen nicht zu unterscheiden.

    Fehlt `main`, betrifft das zwei Abgleiche: die Durchsetzung steht fest als
    Abweichung, die Pflicht-Check-Liste wird unbekannt (ohne Ruleset gibt es
    keine Liste). Exit 1 — die Abweichung wiegt schwerer als der fehlende Wert.
    """
    antworten = _vollstaendige_antworten()
    antworten[f"repos/{REPO_NAME}/rulesets"] = [_ruleset("release-tags", 2, "active")]
    ergebnisse = repo_pruefung.pruefe(REPO_NAME, api=_api(antworten), workflow=CI,
                                      domain_pruefen=lambda _: True)

    durchsetzung = _finde(ergebnisse, "'main': enforcement")
    assert not durchsetzung.unbekannt, durchsetzung
    assert not durchsetzung.stimmt
    assert durchsetzung.ist == "fehlt"

    checkliste = _finde(ergebnisse, "Pflicht-Check-Liste")
    assert checkliste.unbekannt, checkliste

    assert repo_pruefung.austrittscode(ergebnisse) == 1


# ── Der bewusst gewählte Sonderfall (#212) ──────────────────────────────────
#
# `FALZMARKE_RULESET_EVALUATE=1` ist der Weg, den #201 geschaffen hat, um main
# beobachtend zu fahren. Verlangte der Wächter dann weiter `active`, meldete er
# dauerhaft eine Abweichung für einen Zustand, den der Maintainer gewählt hat —
# dieselbe Falle wie #210. Er trägt den Sonderfall deshalb mit, sagt ihn aber.


def test_beobachtend_gefahrenes_main_ist_keine_abweichung():
    """Der Fall aus der Acceptance-Criteria-Zeile: Variable gesetzt UND main
    tatsächlich auf evaluate — Setz-Lauf und Wächter sind sich einig."""
    ergebnisse = _pruefen(umgebung={durchsetzung.UMGEBUNGSVARIABLE: "1"},
                          main_enforcement="evaluate")
    assert _finde(ergebnisse, "'main': enforcement").stimmt
    assert repo_pruefung.austrittscode(ergebnisse) == 0


def test_release_tags_bleibt_streng_auch_im_sonderfall():
    """Die Ausnahme gilt nur für main.

    `repo-einstellungen.sh` setzt release-tags fest auf den strengen Wert.
    Erwartete der Wächter dort ebenfalls `evaluate`, meldete er eine Abweichung
    gegen einen Zustand, den der Setz-Lauf nie herstellt — ein Fehlalarm, den
    niemand beheben kann, ohne den Tag-Schutz aufzugeben.
    """
    ergebnisse = _pruefen(umgebung={durchsetzung.UMGEBUNGSVARIABLE: "1"},
                          main_enforcement="evaluate")
    assert _finde(ergebnisse, "'release-tags': enforcement").stimmt
    assert repo_pruefung.austrittscode(ergebnisse) == 0


def test_ohne_die_variable_bleibt_evaluate_eine_abweichung():
    """Die Gegenprobe — ohne sie wäre `evaluate` immer in Ordnung und der
    Schutz von main könnte still verschwinden, genau wie in #201."""
    ergebnisse = _pruefen(main_enforcement="evaluate")
    abgleich = _finde(ergebnisse, "'main': enforcement")
    assert not abgleich.stimmt, abgleich
    assert abgleich.soll == "active"
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_die_variable_allein_macht_active_nicht_falsch_ohne_meldung():
    """Umgekehrt: Variable gesetzt, main steht aber noch auf active.

    Das ist eine echte Abweichung — der Setz-Lauf hätte herabgestuft. Sie zu
    melden ist richtig; verschwiegen würde sonst, dass die gewählte Ausnahme
    gar nicht angekommen ist.
    """
    ergebnisse = _pruefen(umgebung={durchsetzung.UMGEBUNGSVARIABLE: "1"})
    abgleich = _finde(ergebnisse, "'main': enforcement")
    assert not abgleich.stimmt
    assert abgleich.soll == "evaluate" and abgleich.ist == "active"


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


# ── Die Fluchtwege der Prüfer müssen es als Label wirklich geben (#276) ──────

def test_beide_ausnahme_labels_stehen_im_einstellungs_skript():
    """Ein dokumentierter Fluchtweg ohne Label ist keiner.

    `changelog_pflicht.py` und `closing_keyword.py` nennen je ein Label als
    ausdrückliche Ausnahme, und `CONTRIBUTING.md` beschreibt den ersten. Gemessen
    am 08.09.2026 gab es `ohne-changelog` im Repository überhaupt nicht — 37
    Labels, keins mit dem Namen. Wer die Ausnahme setzen wollte, fand sie nicht.

    Der Test liest die Namen aus den **Prüfern**, nicht aus einer zweiten Liste:
    Eine Kopie hier driftete genauso still wie die fehlende Zeile im Skript. Wird
    ein Label umgetauft, fällt der Test — statt dass ein Fluchtweg zumacht.
    """
    import changelog_pflicht
    import closing_keyword

    skript = (REPO / "scripts" / "repo-einstellungen.sh").read_text(encoding="utf-8")
    for name in (changelog_pflicht.AUSNAHME_LABEL, closing_keyword.AUSNAHME_LABEL):
        assert f"\n{name}|" in skript, (
            f"„{name}“ wird von einem Prüfer als Ausnahme angeboten, steht aber "
            f"nicht im LABELS-Block von repo-einstellungen.sh — das Label "
            f"existiert dann nur, wenn es jemand von Hand anlegt.")


# ── Themen des Repositories (#237) ──────────────────────────────────────────
#
# Der einzige Repo-Sollwert, der bis #237 gar keinen Wächter hatte. Aufgefallen
# ist die Lücke daran, dass `mcp` fehlte, obwohl das Paket einen MCP-Server
# mitbringt — gemessen am 03.09. und noch einmal am 07.09.2026, beide Male
# unbemerkt geblieben.


def test_ein_fehlendes_thema_wird_erkannt():
    ohne_mcp = [t for t in topics.TOPICS if t != "mcp"]
    themen = _finde(_pruefen(themen=ohne_mcp), "Themen")
    assert not themen.stimmt
    assert "mcp" in themen.soll and "mcp" not in themen.ist


def test_gegenprobe_vollstaendige_themen_sind_gruen():
    """Ohne sie belegte der Test darüber nur, dass die Prüfung überhaupt rot
    werden kann — nicht, dass sie den richtigen Zustand grün lässt."""
    themen = _finde(_pruefen(), "Themen")
    assert themen.stimmt, themen


def test_ein_zusaetzliches_thema_ist_keine_abweichung():
    """`gh repo edit --add-topic` nimmt nie etwas weg. Verlangte die Prüfung
    Gleichheit, wäre sie nach dem ersten von Hand gesetzten Thema dauerhaft rot
    — und ein Wächter, der grundlos anschlägt, wird abgeschaltet."""
    themen = _finde(_pruefen(themen=[*topics.TOPICS, "briefpapier"]), "Themen")
    assert themen.stimmt, themen


def test_nicht_abfragbare_themen_sind_unbekannt_nicht_gruen():
    ergebnisse = _pruefen(repo_fehler=RuntimeError("HTTP 403"))
    themen = _finde(ergebnisse, "Themen")
    assert themen.unbekannt and not themen.stimmt
    assert repo_pruefung.austrittscode(ergebnisse) == 2


# ── Eintrag im MCP-Registry (#237) ───────────────────────────────────────────
#
# Der einzige Sollwert, der nicht bei GitHub liegt. Drei Zustände wie bei den
# anderen: gelistet, nicht gelistet, nicht abfragbar — und der dritte darf nicht
# als grün durchgehen.


def test_ein_gelisteter_server_ist_gruen():
    """Die Kontrollprobe. Ohne sie belegte der Test darunter nur, dass die
    Prüfung rot werden KANN — nicht, dass sie den richtigen Zustand grün lässt."""
    abgleich = _finde(_pruefen(im_registry=True), "MCP-Registry")
    assert abgleich.stimmt, abgleich
    assert "io.github.blitzsicht/falzmarke" in abgleich.name, \
        "der Servername steht nicht in der Meldung — dann sagt sie nicht, was gesucht wurde"


def test_ein_fehlender_eintrag_wird_erkannt():
    ergebnisse = _pruefen(im_registry=False)
    abgleich = _finde(ergebnisse, "MCP-Registry")
    assert not abgleich.stimmt
    assert abgleich.ist == "nicht gelistet"
    assert repo_pruefung.austrittscode(ergebnisse) == 1


def test_ein_nicht_erreichbares_registry_ist_unbekannt_nicht_gruen():
    """Kein Netz ist nicht dasselbe wie „nicht gelistet".

    Der Unterschied wiegt hier mehr als bei den GitHub-Werten: Das Registry ist
    ein fremder Dienst, und ein Ausfall dort würde sonst als Befund über dieses
    Repository gelesen.
    """
    ergebnisse = _pruefen(im_registry=OSError("Name or service not known"))
    abgleich = _finde(ergebnisse, "MCP-Registry")
    assert abgleich.unbekannt and not abgleich.stimmt
    assert abgleich.ist is None, "bei einem Fehler darf kein Ist-Wert behauptet werden"
    assert repo_pruefung.austrittscode(ergebnisse) == 2


def test_der_servername_kommt_aus_server_json(tmp_path):
    """Eine zweite Quelle für denselben Namen liefe auseinander.

    Gemessen wird hier, dass der Abgleich wirklich `server.json` liest und
    nicht einen im Code wiederholten Namen: Eine abweichende Datei muss eine
    abweichende Suche ergeben.
    """
    import json

    eigen = tmp_path / "server.json"
    eigen.write_text(json.dumps({"name": "io.github.beispiel/anders"}), encoding="utf-8")
    gefragt: list[str] = []

    ergebnisse = repo_pruefung.pruefe(
        REPO_NAME, api=_api(_vollstaendige_antworten()), workflow=CI,
        domain_pruefen=lambda _: True, server_json=eigen,
        registry_suche=lambda name: gefragt.append(name) or [name], umgebung={})

    assert gefragt == ["io.github.beispiel/anders"], gefragt
    assert "io.github.beispiel/anders" in _finde(ergebnisse, "MCP-Registry").name


def test_eine_unlesbare_server_json_ist_unbekannt(tmp_path):
    """Auch das ist „nicht geprüft" und nicht „nicht gelistet"."""
    fehlt = tmp_path / "gibt-es-nicht.json"
    ergebnisse = repo_pruefung.pruefe(
        REPO_NAME, api=_api(_vollstaendige_antworten()), workflow=CI,
        domain_pruefen=lambda _: True, server_json=fehlt,
        registry_suche=lambda name: [name], umgebung={})
    abgleich = _finde(ergebnisse, "MCP-Registry")
    assert abgleich.unbekannt and abgleich.ist is None
    assert repo_pruefung.austrittscode(ergebnisse) == 2


def test_die_echte_abfrage_trifft_ueberhaupt_etwas():
    """Die Gegenprobe zur Attrappe: Die echte Suche muss Treffer liefern können.

    **Nicht** über `repo_pruefung.registry_namen`: Das ist hier die Attrappe der
    Autouse-Sperre, und der Test hätte sie gemessen statt des Registry.
    Deshalb `ECHTE_REGISTRY_SUCHE`, zur Importzeit festgehalten.

    Ohne diesen Test belegte jeder darüber nur das Verhalten der Attrappe. Gefragt
    wird nach einem Namensbestandteil, den das Registry vielfach führt — nicht
    nach falzmarke, denn dessen Abwesenheit ist genau der offene Punkt und
    taugt nicht als Beleg, dass die Abfrage funktioniert.
    """
    try:
        treffer = ECHTE_REGISTRY_SUCHE("mcp", zeit=15.0)
    except Exception as fehler:                                   # noqa: BLE001
        pytest.skip(f"Registry nicht erreichbar: {fehler}")
    assert treffer, "die Suche liefert nichts — dann prüft der Wächter ins Leere"
