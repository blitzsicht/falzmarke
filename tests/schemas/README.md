# Fremde Schemas für die Metadaten-Prüfung

Die Tests laufen ohne Netz, deshalb liegen die Schemas hier. `tests/test_verzeichnis_metadaten.py`
prüft, dass `$schema`/`$id` jeder Datei noch zu dem passt, worauf die Manifeste zeigen.

| Datei | Quelle | Lizenz | Stand |
|---|---|---|---|
| `mcp-server-2025-12-11.schema.json` | `static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`, ausgeliefert aus [modelcontextprotocol/static](https://github.com/modelcontextprotocol/static) (`schemas/2025-12-11/server.schema.json`, Commit `a9ba437`) | MIT, Copyright (c) 2025 Model Context Protocol; Lizenztext: [`LICENSES/MIT-modelcontextprotocol-static.txt`](LICENSES/MIT-modelcontextprotocol-static.txt) | abgerufen 02.11.2026, unverändert; Lizenz und Bytegleichheit geprüft 03.11.2026 |
| `agent-plugins-1.0.0.schema.json` | `agent-plugins.org/schemas/1.0.0/plugin.schema.json`, dieselbe Datei in [agentplugins/agent-plugins-spec](https://github.com/agentplugins/agent-plugins-spec) (`schemas/1.0.0/plugin.schema.json`, letzter Commit daran `d92e6f4`) | Apache-2.0, laut `LICENSE.md` des Repositorys für „Schemas, source code, scripts“; Lizenztext: [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) | abgerufen 02.11.2026, unverändert; Lizenz und Bytegleichheit geprüft 03.11.2026 |
| `skill-frontmatter.schema.json` | eigene Fassung der Prosa-Spezifikation `agentskills.io/specification` | wie das Repository (MIT) | gelesen 02.11.2026 |

Das MCP-Schema entsteht im Repository [modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry)
aus `docs/reference/api/openapi.yaml` und wird je Fassung nach `modelcontextprotocol/static` kopiert.
Die LICENSE des Registry-Repositorys beschreibt einen Übergang von MIT zu Apache-2.0: neue Beiträge
unter Apache-2.0, ältere ohne Zustimmung zur Umlizenzierung weiter unter MIT. Abgelegt ist hier die
Datei aus `static`, und dieses Repository steht unter MIT. Beide Lizenzen sind permissiv.

„Bytegleichheit geprüft“ heißt: Die SHA-256-Summe der Datei hier ist dieselbe wie die der
abgerufenen Adresse und die der Datei im genannten Repository.

## Lizenztexte

Beide Lizenzen verlangen, dass der Lizenztext die Kopie begleitet. Er liegt deshalb unter
`LICENSES/`, Byte für Byte so, wie ihn das jeweilige Repository führt:

| Datei | Quelle | SHA-256 |
|---|---|---|
| `LICENSES/MIT-modelcontextprotocol-static.txt` | `LICENSE` in modelcontextprotocol/static, letzter Commit daran `7d82844` | `c86791c862db3e6a00c1d554f1d5ed72acaa5d56bf41e884eb864a2767d7d33a` |
| `LICENSES/Apache-2.0.txt` | `LICENSES/Apache-2.0.txt` in agentplugins/agent-plugins-spec, letzter Commit daran `978493b` | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |

Abgerufen am 04.11.2026 über `raw.githubusercontent.com` und gegengeprüft über die
GitHub-API: dieselbe Summe auf beiden Wegen. Eine NOTICE-Datei, die Apache-2.0 sonst
mitzugeben verlangt, führt agent-plugins-spec nicht (Wurzelverzeichnis und `LICENSES/`
nachgesehen am 04.11.2026).

Für SKILL.md veröffentlicht niemand ein JSON-Schema. Die eigene Fassung bildet die Regeln der
Spezifikation ab: Name höchstens 64 Zeichen, Beschreibung höchstens 1024, `metadata` als Abbildung
von Zeichenkette auf Zeichenkette und nur die sechs erlaubten Schlüssel. Deshalb steht die Version
unter `metadata.version`; ganz oben lehnt der Validator von Anthropic sie als unbekannten Schlüssel ab.
