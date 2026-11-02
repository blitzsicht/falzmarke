# Fremde Schemas für die Metadaten-Prüfung

Die Tests laufen ohne Netz, deshalb liegen die Schemas hier. `tests/test_verzeichnis_metadaten.py`
prüft, dass `$schema`/`$id` jeder Datei noch zu dem passt, worauf die Manifeste zeigen.

| Datei | Quelle | Stand |
|---|---|---|
| `mcp-server-2025-12-11.schema.json` | `static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json` | abgerufen 02.11.2026, unverändert |
| `agent-plugins-1.0.0.schema.json` | `agent-plugins.org/schemas/1.0.0/plugin.schema.json` | abgerufen 02.11.2026, unverändert |
| `skill-frontmatter.schema.json` | eigene Fassung der Prosa-Spezifikation `agentskills.io/specification` | gelesen 02.11.2026 |

Für SKILL.md veröffentlicht niemand ein JSON-Schema. Die eigene Fassung bildet die Regeln der
Spezifikation ab: Name höchstens 64 Zeichen, Beschreibung höchstens 1024, `metadata` als Abbildung
von Zeichenkette auf Zeichenkette und nur die sechs erlaubten Schlüssel. Deshalb steht die Version
unter `metadata.version`; ganz oben lehnt der Validator von Anthropic sie als unbekannten Schlüssel ab.
