#!/usr/bin/env python3
"""Prüft den gelebten Repo-Zustand gegen die Sollwerte — schreibt nichts.

WARUM ES DAS GIBT

Dreimal am 31.08.2026 ist eine Repo-Einstellung von ihrem Sollwert abgewichen
(#196 ein Pflicht-Check, #199 die Homepage, #201 die Ruleset-Durchsetzung).
Alle drei Ursachen sind behoben — aber nichts hätte gemerkt, wenn der gelebte
Zustand danach wieder abweicht: jemand verstellt die Homepage in der
Weboberfläche, ein alter Lauf stuft ein Ruleset zurück, oder ein Jobname in
`ci.yml` ändert sich, ohne dass das Ruleset nachzieht. Bisher fiel das nur auf,
wenn zufällig jemand nachmaß (#206).

Dieses Skript setzt nichts. Es vergleicht die Sollwerte — dieselben, die
`scripts/repo-einstellungen.sh` auch anwendet — gegen den über die GitHub-API
gelebten Zustand:

    Homepage                        scripts/homepage.py (bestimme(): STANDARD_DOMAIN,
                                    bei toter Domain die Release-Seite — #210)
    Themen des Repositories          scripts/topics.py (TOPICS — #237)
    Ruleset-`enforcement` je Ruleset  scripts/durchsetzung.py (soll())
    Pflicht-Check-Liste (Ruleset main) scripts/pflicht_checks.py
    Eintrag im MCP-Registry          server.json (name — #237)

Der letzte Wert ist der einzige, der nicht bei GitHub liegt, und **er steht
absichtlich auf Abweichung, solange kein Release mit `mcp-name` im README
veroeffentlicht ist**. Das ist kein Defekt des Repositories: Der Eintrag
entsteht im Release-Lauf (`.github/workflows/release.yml`, Job `mcp-registry`),
und die Eigentumspruefung des Registry liest die Projektbeschreibung auf PyPI.
Bis dahin meldet der Waechter genau das, was zutrifft — offen.

Die API-Abfrage steckt hinter dem injizierbaren `api`-Callable (Vorbild:
`pruefen` in homepage.py) — die Vergleichslogik selbst braucht dadurch weder
Netz noch Admin-Rechte, um getestet zu werden. Ein Callable, das eine
Ausnahme wirft (kein Netz, keine Admin-Rechte, API-Fehler), ergibt für den
betroffenen Wert einen dritten Zustand ("unbekannt") — nicht stilles Grün.

    python3 scripts/repo_pruefung.py --repo blitzsicht/falzmarke

Exit 0: alle Werte stimmen. Exit 1: mindestens eine Abweichung. Exit 2:
keine Abweichung, aber mindestens ein Wert war nicht abfragbar.

Verwendet von scripts/repo-einstellungen.sh (--pruefen).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

import durchsetzung                                               # noqa: E402
import homepage                                                   # noqa: E402
import pflicht_checks                                             # noqa: E402
import topics                                                     # noqa: E402

# Der Sollwert der Durchsetzung steht in scripts/durchsetzung.py — derselben
# Datei, aus der auch repo-einstellungen.sh ihn liest (Issue #212). Bis dahin
# stand er hier ein zweites Mal, und eine Sabotage am Wert im Setz-Skript blieb
# stumm: `--pruefen` macht dort ein `exec` auf dieses Skript, die Zeile wird nie
# erreicht. Zwei Werte, die gleich sein müssen, ohne dass etwas sie gleich hält.
RULESET_NAMEN = ("main", "release-tags")

#: Die Quelle des Servernamens — dieselbe Datei, die der Release-Lauf
#: veroeffentlicht (#237).
SERVER_JSON = Path(__file__).resolve().parent.parent / "server.json"


@dataclass(frozen=True)
class Abgleich:
    """Ein einzelner Sollwert gegen seinen gelebten Zustand.

    `ist` ist None genau dann, wenn `fehler` gesetzt ist — der dritte Zustand
    aus dem Issue: "nicht geprüft" ist nicht dasselbe wie "stimmt".
    """

    name: str
    soll: Any
    ist: Any | None
    fehler: str | None = None
    #: Weitere Werte, die ebenso in Ordnung sind — leer, wo es genau einen
    #: richtigen gibt. Gebraucht bei toter Domain (#210): Dann sind Domain UND
    #: Release-Seite legitim, weil der Setz-Lauf je nach Zeitpunkt das eine
    #: oder das andere hinterlassen hat. Nur den einen zu verlangen hiesse,
    #: den Fehlalarm bloss auf den anderen Fall zu verschieben.
    ebenso_gueltig: tuple[Any, ...] = ()

    @property
    def unbekannt(self) -> bool:
        return self.fehler is not None

    @property
    def stimmt(self) -> bool:
        return not self.unbekannt and self.ist in (self.soll, *self.ebenso_gueltig)


def gh_api_json(pfad: str) -> Any:
    """Ein GET gegen die GitHub-API, geparst als JSON. Nie schreibend — kein
    `-X`, damit --pruefen strukturell nichts verändern kann."""
    fertig = subprocess.run(
        ["gh", "api", pfad], capture_output=True, text=True
    )
    if fertig.returncode != 0:
        raise RuntimeError(
            fertig.stderr.strip() or f"gh api {pfad} endete mit Exit {fertig.returncode}"
        )
    return json.loads(fertig.stdout)


def _fehlertext(fehler: Exception) -> str:
    return f"{type(fehler).__name__}: {fehler}"


def _checks_aus_regeln(regeln: list[dict]) -> list[str]:
    for regel in regeln:
        if regel.get("type") == "required_status_checks":
            return [
                c["context"]
                for c in regel.get("parameters", {}).get("required_status_checks", [])
            ]
    return []


#: Die Suche des offiziellen MCP-Registry. Gemessen am 11.09.2026:
#: `?search=falzmarke` antwortet `{"servers":[],"metadata":{"count":0}}`,
#: `?limit=2` liefert echte Eintraege — die Abfrage taugt also als Pruefung UND
#: hat eine Gegenprobe, die nicht nur die leere Menge sieht.
REGISTRY_SUCHE = "https://registry.modelcontextprotocol.io/v0/servers?search={name}"


def registry_namen(name: str, *, zeit: float = 10.0) -> list[str]:
    """Die Servernamen, die das Registry zu dieser Suche liefert.

    Eigene Funktion und kein Einzeiler im Abgleich: So ist sie in den Tests
    austauschbar, wie `api` und `domain_pruefen` es schon sind. Sonst hinge das
    Testergebnis an der Erreichbarkeit eines fremden Dienstes statt an seiner
    Aussage.
    """
    import urllib.parse
    import urllib.request

    adresse = REGISTRY_SUCHE.format(name=urllib.parse.quote(name))
    with urllib.request.urlopen(adresse, timeout=zeit) as antwort:   # noqa: S310
        daten = json.loads(antwort.read().decode("utf-8"))
    return [e["server"]["name"] for e in daten.get("servers", [])
            if "server" in e and "name" in e["server"]]


def _pruefe_mcp_registry(suche: Callable[[str], list[str]],
                         server_json: Path) -> Abgleich:
    """Steht der Server im offiziellen MCP-Registry (#237)?

    Der Sollwert kommt aus `server.json` — derselben Datei, die der
    Release-Lauf veroeffentlicht. Zwei Quellen fuer denselben Namen liefen
    auseinander, sobald einer von beiden umbenannt wird.
    """
    try:
        name = json.loads(server_json.read_text(encoding="utf-8"))["name"]
    except Exception as fehler:                                   # noqa: BLE001
        return Abgleich("Eintrag im MCP-Registry", "gelistet", None,
                        f"server.json nicht lesbar — {_fehlertext(fehler)}")
    try:
        gefunden = suche(name)
    except Exception as fehler:                                   # noqa: BLE001
        return Abgleich(f"Eintrag im MCP-Registry ({name})", "gelistet", None,
                        _fehlertext(fehler))
    return Abgleich(f"Eintrag im MCP-Registry ({name})", "gelistet",
                    "gelistet" if name in gefunden else "nicht gelistet")


def _pruefe_homepage(repo: str, api: Callable[[str], Any],
                     domain_pruefen: Callable[[str], bool]) -> Abgleich:
    """Der Sollwert ist nicht unbedingt STANDARD_DOMAIN (Issue #210).

    `homepage.bestimme()` kennt einen dokumentierten Rückfall: Antwortet die
    Domain nicht, ist die Release-Seite der richtige Wert und nicht der
    falsche. Bis #210 verglich diese Stelle unbedingt gegen STANDARD_DOMAIN
    und meldete für genau diesen Normalfall eine ABWEICHUNG — ein Fehlalarm,
    der wie "jemand hat die Homepage verstellt" aussieht.

    Solange `--pruefen` nur von Hand läuft, liest ein Mensch die Ausgabe im
    Zusammenhang. Automatisiert (#211) wird der Fehlalarm real, und ein
    Wächter, der grundlos anschlägt, wird abgeschaltet — dann ist er
    schlechter als keiner.

    Dieselbe Entscheidung wie im Setz-Lauf zu treffen heisst nicht, sie
    aufzuweichen: Steht dort etwas Drittes, bleibt es eine Abweichung, und bei
    erreichbarer Domain ist die Release-Seite weiterhin eine.
    """
    try:
        daten = api(f"repos/{repo}")
    except Exception as fehler:                                   # noqa: BLE001
        return Abgleich("Homepage", homepage.STANDARD_DOMAIN, None, _fehlertext(fehler))
    ist = daten.get("homepage") or ""
    soll, _ = homepage.bestimme(repo, homepage.STANDARD_DOMAIN, ist, pruefen=domain_pruefen)
    # Antwortet die Domain nicht, hat `bestimme` die Release-Seite gewählt —
    # aber die Domain selbst ist dann genauso in Ordnung: Sie steht dort, bis
    # der nächste Setz-Lauf umstellt, und ein Ausfall ist keine Verstellung.
    # Beides zuzulassen ist der Unterschied zwischen einem Wächter und einem
    # Wecker, der bei jedem Netzhänger klingelt.
    ebenso = () if soll == homepage.STANDARD_DOMAIN else (homepage.STANDARD_DOMAIN,)
    return Abgleich("Homepage", soll, ist, ebenso_gueltig=ebenso)


def _pruefe_topics(repo: str, api: Callable[[str], Any]) -> Abgleich:
    """Stehen alle Themen aus scripts/topics.py wirklich am Repository?

    Verglichen wird die **Schnittmenge**, nicht die ganze Liste: Ein Thema, das
    jemand zusätzlich gesetzt hat, ist keine Abweichung. `gh repo edit
    --add-topic` nimmt nie etwas weg, ein Setz-Lauf stellt den Zustand also
    ohnehin nie exakt her — verlangte diese Stelle Gleichheit, meldete sie
    genau das als Verstellung und wäre nach dem ersten zusätzlichen Thema
    dauerhaft rot. Was sie fangen soll, ist die andere Richtung: ein Thema aus
    der Liste, das am Repository fehlt.

    Der Abstand zwischen `soll` und `ist` benennt dabei von selbst, welches
    Thema fehlt — die Ausgabe braucht keinen Sonderfall.
    """
    soll = sorted(topics.TOPICS)
    try:
        daten = api(f"repos/{repo}")
    except Exception as fehler:                                   # noqa: BLE001
        return Abgleich("Themen", soll, None, _fehlertext(fehler))
    vorhanden = set(daten.get("topics") or ())
    return Abgleich("Themen", soll, sorted(vorhanden & set(topics.TOPICS)))


def _pruefe_durchsetzung(name: str, rulesets: list[dict] | None,
                         rulesets_fehler: str | None, soll_wert: str) -> Abgleich:
    label = f"Ruleset '{name}': enforcement"
    if rulesets is None:
        return Abgleich(label, soll_wert, None, rulesets_fehler)
    gefunden = next((r for r in rulesets if r.get("name") == name), None)
    if gefunden is None:
        # Die Rulesets-Abfrage lief durch — das Fehlen ist keine unbekannte
        # Größe, sondern eine feststehende Abweichung vom Sollwert.
        return Abgleich(label, soll_wert, "fehlt")
    return Abgleich(label, soll_wert, gefunden.get("enforcement"))


def _pruefe_pflicht_checks(
    repo: str,
    rulesets: list[dict] | None,
    rulesets_fehler: str | None,
    api: Callable[[str], Any],
    workflow: Path,
) -> Abgleich:
    name = "Pflicht-Check-Liste (Ruleset main)"
    soll = sorted(pflicht_checks.pflicht_checks(workflow))
    if rulesets is None:
        return Abgleich(name, soll, None, rulesets_fehler)
    haupt = next((r for r in rulesets if r.get("name") == "main"), None)
    if haupt is None:
        return Abgleich(name, soll, None, "Ruleset 'main' existiert nicht im Repo")
    try:
        detail = api(f"repos/{repo}/rulesets/{haupt['id']}")
    except Exception as fehler:                                   # noqa: BLE001
        return Abgleich(name, soll, None, _fehlertext(fehler))
    ist = sorted(_checks_aus_regeln(detail.get("rules", [])))
    return Abgleich(name, soll, ist)


def pruefe(
    repo: str,
    *,
    api: Callable[[str], Any] = gh_api_json,
    workflow: Path = pflicht_checks.STANDARD_WORKFLOW,
    domain_pruefen: Callable[[str], bool] = homepage.domain_antwortet,
    # Kein Default-Objekt, sondern None: Ein zur Definitionszeit gebundener
    # Default laesst sich nicht per monkeypatch ersetzen — gemessen am
    # 11.09.2026, der Patch auf das Modulattribut ging ins Leere und die
    # Tests haetten weiter ins Netz gegriffen.
    registry_suche: Callable[[str], list[str]] | None = None,
    server_json: Path = SERVER_JSON,
    umgebung: Mapping[str, str] | None = None,
) -> list[Abgleich]:
    """Alle Abgleiche — nie schreibend, nie CI-Lauf-abhängig.

    `domain_pruefen` ist austauschbar wie `api` (Vorbild: `pruefen` in
    homepage.py). Die Tests kommen dadurch ohne Netz aus — sonst hinge ihr
    Ergebnis an der Erreichbarkeit von falzmarke.com statt an ihrer Aussage.
    """
    ergebnisse = [_pruefe_homepage(repo, api, domain_pruefen),
                  _pruefe_topics(repo, api)]

    rulesets: list[dict] | None
    try:
        rulesets = api(f"repos/{repo}/rulesets")
    except Exception as fehler:                                   # noqa: BLE001
        rulesets, rulesets_fehler = None, _fehlertext(fehler)
    else:
        rulesets_fehler = None

    # Je Ruleset gefragt, nicht einmal für alle: Der Sonderfall gilt nur für
    # main. `release-tags` setzt repo-einstellungen.sh fest auf den strengen
    # Wert — erwartete der Wächter dort ebenfalls `evaluate`, meldete er eine
    # Abweichung gegen einen Zustand, den der Setz-Lauf nie herstellt.
    for name in RULESET_NAMEN:
        ergebnisse.append(_pruefe_durchsetzung(
            name, rulesets, rulesets_fehler, durchsetzung.soll(name, umgebung)))
    ergebnisse.append(_pruefe_pflicht_checks(repo, rulesets, rulesets_fehler, api, workflow))
    ergebnisse.append(_pruefe_mcp_registry(registry_suche or registry_namen, server_json))
    return ergebnisse


def austrittscode(ergebnisse: list[Abgleich]) -> int:
    """0: alles stimmt. 1: mindestens eine Abweichung — schlägt "unbekannt"
    immer, weil eine echte Abweichung schwerer wiegt als ein fehlender Wert.
    2: keine Abweichung, aber mindestens ein Wert war nicht abfragbar — der
    dritte Zustand darf nicht als grün durchgehen."""
    if any(not e.unbekannt and not e.stimmt for e in ergebnisse):
        return 1
    if any(e.unbekannt for e in ergebnisse):
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="OWNER/REPO")
    args = parser.parse_args()

    # Eine Ausnahme, die niemand sieht, ist der stille Ausfall, gegen den
    # dieses Skript gebaut ist. Steht sie vor den Ergebnissen, liest sie auch,
    # wer nur die erste Zeile ansieht (Issue #212).
    if text := durchsetzung.grund():
        print(f"AUSNAHME        Ruleset-Durchsetzung: {text}")

    ergebnisse = pruefe(args.repo)
    for e in ergebnisse:
        if e.unbekannt:
            print(f"NICHT GEPRUEFT  {e.name}: {e.fehler}")
        elif e.stimmt:
            print(f"OK              {e.name}: {e.ist}")
        else:
            print(f"ABWEICHUNG      {e.name}: soll={e.soll!r} ist={e.ist!r}")

    return austrittscode(ergebnisse)


if __name__ == "__main__":
    raise SystemExit(main())
