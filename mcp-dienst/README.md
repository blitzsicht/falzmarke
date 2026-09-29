# MCP-Referenzdienst (mcp.falzmarke.com)

Ein öffentlicher MCP-Server über HTTPS, der **nur Referenzdaten** liefert: die Maße von Form A und B,
die Regeln, gegen die falzmarke prüft, und ihre Quellen. Er setzt keine Briefe und nimmt keinen Text
des Nutzers an. Gesetzt wird mit dem Skill in der Sandbox des Nutzers.

Anlass: Das Plugin-Portal von OpenAI bot am 29.09.2026 nur „With MCP“ an. Dieser Dienst ist der
MCP-Teil eines solchen Plugins; der Code steht in `skill/falzmarke/referenzdienst.py`.

| Pfad | Was |
|---|---|
| `/mcp` | MCP über Streamable HTTP, zustandslos, JSON-Antworten |
| `/.well-known/openai-apps-challenge` | Nachweis-Token für OpenAI aus der Umgebungsvariable `OPENAI_APPS_CHALLENGE`, sonst 404 |

Umgebungsvariablen auf Vercel:

- `FALZMARKE_MCP_HOSTS=mcp.falzmarke.com`: Ohne sie weist das SDK jeden Host außer localhost ab
  (Schutz gegen DNS-Rebinding).
- `OPENAI_APPS_CHALLENGE=<token>`: kommt aus dem Portal, steht nie im Repository.

## Lokal

    cd skill && python -c "import uvicorn; from falzmarke.referenzdienst import asgi_app; uvicorn.run(asgi_app(), port=8765)"

## Ausrollen

    bash mcp-dienst/ausrollen.sh                   prüfen, ändert nichts
    bash mcp-dienst/ausrollen.sh --live            Projekt, Deploy, Domain, DNS, Messung
    bash mcp-dienst/ausrollen.sh --token <token>   Nachweis-Token von OpenAI setzen
    bash mcp-dienst/ausrollen.sh --messen          nur messen

Vor jedem Deploy legt `packen.sh` die vier Module, die der Dienst lädt, nach `_skill/`. Die
Vercel-CLI lädt nur dieses Verzeichnis hoch; `../skill` wäre dort nicht vorhanden.

## Gemessen am 29.09.2026

- `vercel build` baut die Funktion (python3.12, `_skill` enthalten).
- Unter `vercel dev` liefern `tools/list` und `sollwerte` die richtigen Werte, der Nachweis ohne
  Token gibt 404.
- **Nicht messbar unter `vercel dev`:** der Host-Schutz. Der Dev-Proxy schreibt den Host um, ein
  fremder Host bekam dort 200. Deshalb prüft `ausrollen.sh` ihn am echten Deploy und bricht ab,
  wenn er nicht greift.
- Vorsicht mit `vercel dev --yes`: Es legt im Team ein Projekt an, auch wenn eine lokale
  `.vercel/project.json` etwas anderes sagt. So entstand am 29.09.2026 das leere Projekt
  `mcp-dienst`.
