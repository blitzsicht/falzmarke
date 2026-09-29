#!/usr/bin/env bash
# Rollt den Referenzdienst auf mcp.falzmarke.com aus — Teil T des Umsetzplans.
#
#   bash mcp-dienst/ausrollen.sh                   nur prüfen (Vorgabe), ändert nichts
#   bash mcp-dienst/ausrollen.sh --live            Projekt, Deploy, Domain, DNS, Prüfung
#   bash mcp-dienst/ausrollen.sh --token <token>   Nachweis-Token von OpenAI setzen, neu deployen
#   bash mcp-dienst/ausrollen.sh --messen          nur die Prüfungen gegen die echte Adresse
#
# Prüfen und Handeln sind getrennte Aufrufe: Wer --live startet, hat die
# Ausgabe ohne --live vorher gesehen.
#
# Der Cloudflare-Token kommt aus 1Password und wird nie ausgegeben. Zone und
# Rückbau: customer-falzmarke/docs/cf-backup-2026-08-27/RESTORE.md.
set -euo pipefail

cd "$(dirname "$0")"

PROJEKT="falzmarke-mcp"
TEAM="siluris-projects"
HOST="mcp.falzmarke.com"
ZONE="0df58aac8942373241a99a6eec546bc4"
CNAME_ZIEL="cname.vercel-dns.com"
OP_PFAD="op://claude/siluri-ai-cloudflare_apikey/password"
BASIS="https://$HOST"

MODUS="pruefen"
TOKEN=""
case "${1:-}" in
  "") ;;
  --live) MODUS="live" ;;
  --messen) MODUS="messen" ;;
  --token) MODUS="token"; TOKEN="${2:?--token braucht den Token aus dem Portal}" ;;
  *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
esac

fehl() { echo "FEHL: $*" >&2; exit 1; }
ok()   { echo "OK    $*"; }
plan() { echo "PLAN  $*"; }

rpc() {
  curl -s --max-time 20 -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" -H "MCP-Protocol-Version: 2025-06-18" \
    "$@" "$BASIS/mcp"
}

messen() {
  echo "── Messung gegen $BASIS ─────────────────────────────"
  local anzahl
  anzahl=$(rpc -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
    | python3 -c "import sys,json;print(len(json.load(sys.stdin)['result']['tools']))") \
    || fehl "tools/list antwortet nicht mit JSON"
  [ "$anzahl" = "3" ] || fehl "tools/list meldet $anzahl Werkzeuge statt 3"
  ok "tools/list: 3 Werkzeuge"

  # Gegenprobe zum Host-Schutz. Unter `vercel dev` war er nicht messbar (der
  # Proxy schreibt den Host um) — hier, am echten Deploy, muss er greifen.
  local fremd
  fremd=$(rpc -o /dev/null -w "%{http_code}" -H "Host: boese.example" \
    -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' || true)
  case "$fremd" in
    421|400|403|404) ok "fremder Host abgewiesen ($fremd)" ;;
    *) fehl "fremder Host bekommt $fremd — Host-Schutz greift nicht" ;;
  esac

  local nachweis
  nachweis=$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" "$BASIS/.well-known/openai-apps-challenge")
  if [ -n "$TOKEN" ]; then
    [ "$(curl -s --max-time 10 "$BASIS/.well-known/openai-apps-challenge")" = "$TOKEN" ] \
      || fehl "der Nachweis liefert nicht den gesetzten Token"
    ok "Nachweis liefert den Token"
  else
    ok "Nachweis ohne Token: $nachweis (erwartet 404, solange kein Token gesetzt ist)"
  fi
}

cf() {  # Methode, Pfad, [JSON]
  local token
  token=$(op read "$OP_PFAD") || fehl "1Password: Token nicht lesbar (op signin?)"
  curl -s --max-time 20 -X "$1" "https://api.cloudflare.com/client/v4/zones/$ZONE$2" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" ${3:+--data "$3"}
}

# ── Vorbedingungen (immer, nur lesend) ─────────────────────────────────────
echo "── Vorbedingungen ───────────────────────────────────"
command -v vercel >/dev/null || fehl "vercel-CLI fehlt"
command -v op >/dev/null || fehl "1Password-CLI (op) fehlt"
wer=$(vercel whoami 2>/dev/null | tail -1) || fehl "vercel: nicht angemeldet"
ok "vercel angemeldet als $wer"
[ -f api/index.py ] && [ -x packen.sh ] || fehl "api/index.py oder packen.sh fehlt"
ok "Einstieg und Packer vorhanden"

if [ "$MODUS" = "messen" ]; then messen; exit 0; fi
if [ "$MODUS" = "token" ]; then
  printf '%s' "$TOKEN" | vercel env add OPENAI_APPS_CHALLENGE production --scope "$TEAM" --force >/dev/null
  ok "OPENAI_APPS_CHALLENGE gesetzt"
  bash packen.sh >/dev/null && vercel deploy --prod --yes --scope "$TEAM" >/dev/null
  ok "neu deployt"
  messen
  exit 0
fi

zone=$(cf GET "" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['result']['name'] if d.get('success') else 'FEHLER')")
[ "$zone" = "falzmarke.com" ] || fehl "Cloudflare-Zone nicht lesbar (Antwort: $zone)"
ok "Cloudflare-Zone $zone lesbar"
vorhanden=$(cf GET "/dns_records?name=$HOST" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['result']))")
ok "DNS-Einträge für $HOST: $vorhanden"

if [ "$MODUS" = "pruefen" ]; then
  plan "vercel link --project $PROJEKT --scope $TEAM (legt das Projekt an, falls es fehlt)"
  plan "vercel env add FALZMARKE_MCP_HOSTS=$HOST (production)"
  plan "bash packen.sh && vercel deploy --prod"
  plan "vercel domains add $HOST"
  [ "$vorhanden" = "0" ] && plan "Cloudflare: CNAME $HOST → $CNAME_ZIEL, DNS only" \
    || plan "Cloudflare: Eintrag für $HOST besteht schon — wird NICHT angefasst, erst ansehen"
  plan "Messung: tools/list, fremder Host, Nachweis"
  echo "Nichts geändert. Scharf schalten: bash mcp-dienst/ausrollen.sh --live"
  exit 0
fi

# ── live ───────────────────────────────────────────────────────────────────
echo "── Ausrollen ────────────────────────────────────────"
vercel link --project "$PROJEKT" --scope "$TEAM" --yes >/dev/null
ok "verknüpft mit $TEAM/$PROJEKT"
printf '%s' "$HOST" | vercel env add FALZMARKE_MCP_HOSTS production --scope "$TEAM" --force >/dev/null
ok "FALZMARKE_MCP_HOSTS=$HOST"
bash packen.sh
vercel deploy --prod --yes --scope "$TEAM" >/dev/null
ok "deployt"
vercel domains add "$HOST" "$PROJEKT" --scope "$TEAM" >/dev/null 2>&1 || true
ok "Domain $HOST am Projekt"
if [ "$vorhanden" = "0" ]; then
  antwort=$(cf POST "/dns_records" \
    "{\"type\":\"CNAME\",\"name\":\"mcp\",\"content\":\"$CNAME_ZIEL\",\"proxied\":false,\"ttl\":1}")
  echo "$antwort" | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if d.get('success') else 1)" \
    || fehl "Cloudflare hat den CNAME nicht angelegt: $antwort"
  ok "CNAME mcp → $CNAME_ZIEL angelegt (DNS only)"
else
  echo "HINWEIS: DNS-Eintrag für $HOST bestand schon und wurde nicht verändert."
fi

echo "Warte auf TLS (bis 5 min) …"
for _ in $(seq 1 30); do
  curl -s --max-time 5 -o /dev/null "$BASIS/.well-known/openai-apps-challenge" && break
  sleep 10
done
messen
