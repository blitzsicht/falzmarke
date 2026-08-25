#!/usr/bin/env bash
# Repository-Einstellungen als Code. Idempotent, mehrfach ausführbar.
#
#   scripts/repo-einstellungen.sh --trocken blitzsicht/falzmarke   # nur zeigen
#   scripts/repo-einstellungen.sh blitzsicht/falzmarke             # anwenden
#
# Voraussetzung: gh auth login mit Admin-Rechten auf dem Repository.
#
# Warum ein Trockenlauf: Ein Ruleset mit Status-Checks, die es nicht gibt,
# sperrt den Branch vollständig — kein Merge, kein Push, auch nicht für den
# Admin. Dieser Fehler fällt sonst erst auf, wenn niemand mehr arbeiten kann.
set -euo pipefail

TROCKEN=0
if [ "${1:-}" = "--trocken" ]; then TROCKEN=1; shift; fi
REPO="${1:?Aufruf: $0 [--trocken] OWNER/REPO}"
OWNER="${REPO%%/*}"

BESCHREIBUNG="DIN-5008-Briefe aus Markdown — als PDF/A gesetzt, auf den Millimeter geprüft. Skill für KI-Agenten und CLI."
HOMEPAGE_WUNSCH="${FALZMARKE_HOMEPAGE:-}"

tue() {
  if [ "$TROCKEN" = "1" ]; then printf '  [trocken] %s\n' "$*"; else "$@"; fi
}
hinweis() { printf '  %s\n' "$*"; }

echo "== Vorprüfung =="
if ! gh api "repos/$REPO" --jq '.permissions.admin' 2>/dev/null | grep -q true; then
  echo "FEHLER: keine Admin-Rechte auf $REPO." >&2
  exit 1
fi
hinweis "Admin-Rechte auf $REPO vorhanden."

# Die Status-Checks werden aus dem letzten Lauf abgeleitet, nicht geraten.
# Ein Ruleset, das nicht existierende Checks verlangt, blockiert den Branch
# dauerhaft: GitHub wartet auf etwas, das nie kommt.
echo "== Status-Checks aus dem letzten CI-Lauf ableiten =="
LAUF=$(gh run list --repo "$REPO" --workflow=ci.yml --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)
CHECKS=()
if [ -n "$LAUF" ]; then
  # Nur Jobs, die auch bei einem Pull Request laufen. Ein Job mit
  # `if: github.ref == 'refs/heads/main'` erscheint bei einem PR nie — als
  # Pflicht-Check würde er jeden PR unbegrenzt warten lassen.
  NUR_MAIN=$(python3 - <<'PYEOF'
import re, sys, pathlib
try:
    import yaml
    daten = yaml.safe_load(pathlib.Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
except Exception:
    sys.exit(0)
for name, job in (daten.get("jobs") or {}).items():
    bedingung = str(job.get("if", ""))
    if "refs/heads/main" in bedingung or "event_name == 'push'" in bedingung:
        print(name)
PYEOF
)
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    ausgeschlossen=0
    while IFS= read -r nm; do
      [ -n "$nm" ] && [ "$name" = "$nm" ] && ausgeschlossen=1
    done <<< "$NUR_MAIN"
    if [ "$ausgeschlossen" = "1" ]; then
      hinweis "übersprungen (läuft nur auf main): $name"
    else
      CHECKS+=("$name")
    fi
  done < <(gh api "repos/$REPO/actions/runs/$LAUF/jobs" --jq '.jobs[] | select(.conclusion=="success") | .name')
fi
if [ ${#CHECKS[@]} -eq 0 ]; then
  hinweis "Kein erfolgreicher CI-Lauf gefunden — das Ruleset bekommt KEINE Status-Checks."
  hinweis "Sonst wäre der Branch gesperrt, bis die Checks das erste Mal laufen."
else
  hinweis "Gefunden: ${CHECKS[*]}"
fi

echo "== Homepage =="
if [ -z "$HOMEPAGE_WUNSCH" ]; then
  HOMEPAGE="https://github.com/$REPO/releases/latest"
  hinweis "Keine Domain angegeben (FALZMARKE_HOMEPAGE) — Homepage zeigt auf die Release-Seite."
elif curl -s -o /dev/null -w '%{http_code}' -L --max-time 10 "$HOMEPAGE_WUNSCH" | grep -qE '^(200|301|302)$'; then
  HOMEPAGE="$HOMEPAGE_WUNSCH"
  hinweis "$HOMEPAGE_WUNSCH antwortet — wird als Homepage gesetzt."
else
  HOMEPAGE="https://github.com/$REPO/releases/latest"
  hinweis "$HOMEPAGE_WUNSCH antwortet nicht — Homepage zeigt stattdessen auf die Release-Seite."
fi

echo "== Allgemein, Features, Merge-Regeln =="
tue gh repo edit "$REPO" \
  --description "$BESCHREIBUNG" \
  --homepage "$HOMEPAGE" \
  --enable-issues=true \
  --enable-discussions=true \
  --enable-wiki=false \
  --enable-projects=false \
  --enable-squash-merge=true \
  --enable-merge-commit=false \
  --enable-rebase-merge=false \
  --delete-branch-on-merge=true \
  --allow-update-branch=true \
  --enable-auto-merge=true

for t in falzmarke din5008 din-5008 geschaeftsbrief typst pdfa pdfua claude-skill agent-skills markdown; do
  tue gh repo edit "$REPO" --add-topic "$t"
done

echo "== Issue-Erstellung für Externe: Interaktionslimits entfernen =="
if [ "$TROCKEN" = "1" ]; then
  hinweis "[trocken] DELETE repos/$REPO/interaction-limits"
else
  gh api -X DELETE "repos/$REPO/interaction-limits" >/dev/null 2>&1 || true
fi

echo "== Sicherheit =="
if [ "$TROCKEN" = "1" ]; then
  hinweis "[trocken] Secret Scanning, Push Protection, Dependabot, private Meldungen, CodeQL"
else
  gh api -X PATCH "repos/$REPO" --input - >/dev/null <<'JSON'
{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}}
JSON
  gh api -X PUT "repos/$REPO/vulnerability-alerts" >/dev/null
  gh api -X PUT "repos/$REPO/automated-security-fixes" >/dev/null
  gh api -X PUT "repos/$REPO/private-vulnerability-reporting" >/dev/null || true
  gh api -X PATCH "repos/$REPO/code-scanning/default-setup" --input - >/dev/null <<'JSON' || true
{"state":"configured","query_suite":"default","languages":["python"]}
JSON
fi

echo "== Actions: nur GitHub- und verifizierte Actions =="
if [ "$TROCKEN" = "1" ]; then
  hinweis "[trocken] allowed_actions=selected, default_workflow_permissions=read"
else
  gh api -X PUT "repos/$REPO/actions/permissions" --input - >/dev/null <<'JSON'
{"enabled":true,"allowed_actions":"selected"}
JSON
  gh api -X PUT "repos/$REPO/actions/permissions/selected-actions" --input - >/dev/null <<'JSON'
{"github_owned_allowed":true,"verified_allowed":true,"patterns_allowed":["softprops/action-gh-release@*","pypa/gh-action-pypi-publish@*"]}
JSON
  # Der Standard ist "read"; Workflows, die mehr brauchen, fordern es selbst an
  # (renders-aktualisieren hat contents: write im Job).
  gh api -X PUT "repos/$REPO/actions/permissions/workflow" --input - >/dev/null <<'JSON'
{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}
JSON
fi

echo "== Ruleset main =="
# Enforcement: "evaluate" meldet Verstöße, blockiert aber nicht. Erst wenn die
# Regeln nachweislich zum Ablauf passen, auf "active" stellen — über
# FALZMARKE_RULESET_AKTIV=1.
DURCHSETZUNG="evaluate"
[ "${FALZMARKE_RULESET_AKTIV:-0}" = "1" ] && DURCHSETZUNG="active"
hinweis "Durchsetzung: $DURCHSETZUNG (mit FALZMARKE_RULESET_AKTIV=1 scharf schalten)"

CHECK_JSON="[]"
if [ ${#CHECKS[@]} -gt 0 ]; then
  CHECK_JSON=$(printf '%s\n' "${CHECKS[@]}" | python3 -c 'import json,sys; print(json.dumps([{"context": z.strip()} for z in sys.stdin if z.strip()]))')
fi

RULESET_MAIN=$(python3 - "$DURCHSETZUNG" "$CHECK_JSON" <<'PY'
import json, sys
durchsetzung, checks = sys.argv[1], json.loads(sys.argv[2])
regeln = [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {"type": "pull_request", "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": True,
        "require_code_owner_review": False,
        "require_last_push_approval": False,
        "required_review_thread_resolution": True}},
]
if checks:
    regeln.append({"type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": True,
        "required_status_checks": checks}})
print(json.dumps({
    "name": "main", "target": "branch", "enforcement": durchsetzung,
    "bypass_actors": [],
    "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
    "rules": regeln,
}))
PY
)

setze_ruleset() {
  local name="$1" inhalt="$2"
  local vorhanden
  vorhanden=$(gh api "repos/$REPO/rulesets" --jq ".[] | select(.name==\"$name\") | .id" 2>/dev/null || true)
  if [ "$TROCKEN" = "1" ]; then
    hinweis "[trocken] Ruleset '$name' $([ -n "$vorhanden" ] && echo "aktualisieren (id $vorhanden)" || echo anlegen)"
    printf '%s' "$inhalt" | python3 -m json.tool | sed 's/^/      /'
    return
  fi
  if [ -n "$vorhanden" ]; then
    printf '%s' "$inhalt" | gh api -X PUT "repos/$REPO/rulesets/$vorhanden" --input - >/dev/null
  else
    printf '%s' "$inhalt" | gh api -X POST "repos/$REPO/rulesets" --input - >/dev/null
  fi
}
setze_ruleset "main" "$RULESET_MAIN"

echo "== Ruleset release-tags =="
RULESET_TAGS='{"name":"release-tags","target":"tag","enforcement":"active","bypass_actors":[],
"conditions":{"ref_name":{"include":["refs/tags/v*"],"exclude":[]}},
"rules":[{"type":"deletion"},{"type":"non_fast_forward"},{"type":"update"}]}'
setze_ruleset "release-tags" "$RULESET_TAGS"

echo "== Labels =="
while IFS='|' read -r name farbe beschreibung; do
  [ -z "$name" ] && continue
  tue gh label create "$name" --repo "$REPO" --color "$farbe" --description "$beschreibung" --force
done <<'LABELS'
bug|d73a4a|Etwas verhält sich falsch — mit Reproduktion
feature|0e8a16|Neue Fähigkeit
doku|0075ca|README, Docs, Glossar, Fehlerkatalog
norm|5319e7|DIN-5008-Frage oder Maßabweichung
hybridbrief|1f5aa8|Spezifikation Hybridbrief
skill|fbca04|Claude-Skill und andere Agenten
verify|c5def5|Prüfung, Toleranzen, Gegenproben
good first issue|7057ff|Einstieg für neue Mitwirkende
help wanted|008672|Mitarbeit erwünscht
blockiert|b60205|Wartet auf etwas anderes
maintainer|ededed|Nur vom Maintainer erledigbar (Einstellungen, Recht, Domain)
LABELS

echo "== Environment pypi =="
if [ "$TROCKEN" = "1" ]; then
  hinweis "[trocken] Environment 'pypi' mit Freigabe durch den Maintainer, nur Tags v*"
else
  BENUTZER_ID=$(gh api user --jq .id)
  gh api -X PUT "repos/$REPO/environments/pypi" --input - >/dev/null <<JSON
{"reviewers":[{"type":"User","id":$BENUTZER_ID}],"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}
JSON
  gh api -X POST "repos/$REPO/environments/pypi/deployment-branch-policies" --input - >/dev/null 2>&1 <<'JSON' || true
{"name":"v*","type":"tag"}
JSON
fi

echo
echo "Fertig. Von Hand in der Weboberfläche (nicht per API setzbar):"
echo "  1. Settings › General › Social preview: docs/assets/brand/social-preview.png hochladen"
echo "  2. Discussions › Kategorien anlegen"
echo "  3. PyPI: Trusted Publisher für $REPO, Workflow release.yml, Environment pypi"
echo "  4. Organisation $OWNER: 2FA erzwingen, zweiten Owner eintragen"
echo
echo "Erst wenn die CI die endgültigen Jobnamen hat und ein Lauf grün war:"
echo "  FALZMARKE_RULESET_AKTIV=1 $0 $REPO   # schaltet das main-Ruleset scharf"
