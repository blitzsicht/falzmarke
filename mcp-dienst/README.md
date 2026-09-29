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

## Noch nicht gemessen

Der Betrieb auf Vercel: ob die Python-Funktion die Dateien unter `../skill` über `includeFiles`
mitnimmt und ob der Lifespan der ASGI-App dort läuft. Beides zeigt erst der erste Deploy (Teil B).
Scheitert er, ist der Ausweg ein Container.
