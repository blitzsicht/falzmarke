# Fremde Schemas für die Metadaten-Prüfung

Die Tests laufen ohne Netz, deshalb liegen die Schemas hier. `tests/test_verzeichnis_metadaten.py`
prüft, dass `$schema`/`$id` jeder Datei noch zu dem passt, worauf die Manifeste zeigen.

| Datei | Quelle | Lizenz | Stand |
|---|---|---|---|
| `mcp-server-2025-12-11.schema.json` | `static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`, ausgeliefert aus [modelcontextprotocol/static](https://github.com/modelcontextprotocol/static) (`schemas/2025-12-11/server.schema.json`, Commit `a9ba437`) | [MIT](https://github.com/modelcontextprotocol/static/blob/main/LICENSE), Copyright (c) 2025 Model Context Protocol | abgerufen 02.11.2026, unverändert; Lizenz und Bytegleichheit geprüft 03.11.2026 |
| `agent-plugins-1.0.0.schema.json` | `agent-plugins.org/schemas/1.0.0/plugin.schema.json`, dieselbe Datei in [agentplugins/agent-plugins-spec](https://github.com/agentplugins/agent-plugins-spec) (`schemas/1.0.0/plugin.schema.json`, letzter Commit daran `d92e6f4`) | [Apache-2.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/LICENSES/Apache-2.0.txt), laut `LICENSE.md` des Repositorys für „Schemas, source code, scripts“ | abgerufen 02.11.2026, unverändert; Lizenz und Bytegleichheit geprüft 03.11.2026 |
| `skill-frontmatter.schema.json` | eigene Fassung der Prosa-Spezifikation `agentskills.io/specification` | wie das Repository (MIT) | gelesen 02.11.2026 |

Das MCP-Schema entsteht im Repository [modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry)
aus `docs/reference/api/openapi.yaml` und wird je Fassung nach `modelcontextprotocol/static` kopiert.
Die LICENSE des Registry-Repositorys beschreibt einen Übergang von MIT zu Apache-2.0: neue Beiträge
unter Apache-2.0, ältere ohne Zustimmung zur Umlizenzierung weiter unter MIT. Abgelegt ist hier die
Datei aus `static`, und dieses Repository steht unter MIT. Beide Lizenzen sind permissiv.

„Bytegleichheit geprüft“ heißt: Die SHA-256-Summe der Datei hier ist dieselbe wie die der
abgerufenen Adresse und die der Datei im genannten Repository.

Für SKILL.md veröffentlicht niemand ein JSON-Schema. Die eigene Fassung bildet die Regeln der
Spezifikation ab: Name höchstens 64 Zeichen, Beschreibung höchstens 1024, `metadata` als Abbildung
von Zeichenkette auf Zeichenkette und nur die sechs erlaubten Schlüssel. Deshalb steht die Version
unter `metadata.version`; ganz oben lehnt der Validator von Anthropic sie als unbekannten Schlüssel ab.
