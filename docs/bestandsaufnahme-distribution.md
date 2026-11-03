# Bestandsaufnahme: Wie falzmarke zu den Nutzern kommt

Stand: 02.11.2026, Version 0.10.0, Nachträge zu v0.11.0, v0.11.1 und v0.11.2 sind ausgewiesen. Jede Zeile ist eine Messung von diesem Tag, wenn nichts anderes
dabeisteht. `✓` gelesen oder gelaufen, `✗` geprüft und nicht vorhanden, `?` nicht nachgemessen.

## Ergebnis

Sieben Formen existieren und laufen, eine existiert nur im Code, zwei gibt es nicht.

| Form | Stand | Beleg |
|---|---|---|
| ✓ PyPI-Paket | 0.11.2 liegt oben, hochgeladen am 03.11.2026 um 17:05 UTC (gemessen am selben Tag) | `pypi.org/pypi/falzmarke/json` |
| ✓ CLI | läuft, 17 Unterbefehle, `check` ist der frühere Name von `verify` | `pyproject.toml` `[project.scripts]`, `skill/falzmarke/cli.py` |
| ✓ Claude-Skill | `falzmarke.skill` im Release, 7 Downloads; dazu `falzmarke-offline.skill`, 5 Downloads | `skill/SKILL.md`, Release v0.10.0 |
| ✓ ChatGPT-Plugin (Paket) | `falzmarke-chatgpt-plugin.zip` im Release, 0 Downloads | `scripts/plugin_packen.py` |
| ? ChatGPT-Plugin (Einreichung) | zuletzt „wartet auf OpenAI“ (Stand 01.10.2026) | nur im OpenAI-Portal sichtbar |
| ✓ MCP-Server über stdio | Handschlag mit echtem Brief: 34/34 Maße | `skill/falzmarke/dienst.py`, `scripts/mcp_handschlag.py` |
| ✓ Docker-Image (Bauanleitung) | wird in der CI gebaut und angesprochen; kein veröffentlichtes Image | `Dockerfile`, CI-Job „MCP-Dienst im Container“ |
| ✓ GitHub Action | `action.yml` mit `branding` | Eintrag im Marketplace: `?` |
| ✗ MCP-Referenzdienst | Code da, `mcp.falzmarke.com` löst nicht auf | `mcp-dienst/`, `dig mcp.falzmarke.com` leer |
| ✓ Claude-Plugin | `skill/.claude-plugin/plugin.json` (#454), kein `marketplace.json` | `claude plugin validate ./skill` ohne Fehler, `plugin details`: ein Skill |
| ✗ npm | Paket gibt es nicht (404), kein `package.json` im Wurzelverzeichnis | `npm view falzmarke` |

Die Thunderbird-Erweiterung in `thunderbird/` gehört zum Mailweg und ist kein Verzeichnisziel.

## Finding 1: Der Registry-Eintrag startet den Dienst nicht

`server.json` nannte bis heute nur das Paket. Das offizielle Registry führt den Server (Status
`active`, Version 0.10.0). Ein Client baut daraus `uvx falzmarke`:

| Befehl | Ergebnis |
|---|---|
| `uvx falzmarke` (Stand im Registry) | Exit 2, `the following arguments are required: befehl` |
| `uvx falzmarke mcp` | bricht ab, das Python-Paket `mcp` fehlt |
| `uvx --with=mcp>=2,<3 falzmarke==0.10.0 mcp` | Handschlag grün, 4 Werkzeuge, Brief gesetzt, 34/34 |
| `uvx --with mcp~=2.0 falzmarke==0.10.0 mcp` | Handschlag grün, 4 Werkzeuge; dieselbe Grenze ohne Shell-Metazeichen |
| `sh -c 'uvx --with mcp>=2,<3 …'` (unquotiert kopiert) | `>` schreibt eine Datei `=2,`, `<3` scheitert |

Behoben in `server.json` über `runtimeArguments` und `packageArguments`. Das Registry liest die
Datei im Job `mcp-registry` am Versions-Tag. Das Dockerfile war nie betroffen.

**Nachtrag v0.11.0:** Das Registry führt 0.11.0 als `active`. Der Befehl aus dem Eintrag besteht
den Handschlag samt Brief, 34/34 Maße. Ohne `--with mcp~=2.0` endet er mit Exit 3.

**Nachtrag v0.11.1 (03.11.2026):** Das Registry führt 0.11.1 als `active`. Der Befehl aus dem
Eintrag besteht `initialize` und `tools/list` mit vier Werkzeugen. Ein Brief ist dabei nicht
gerendert worden. `serverInfo.version` kommt leer zurück.

**Nachtrag v0.11.2 (03.11.2026):** Das Registry führt 0.11.2 als `active` und `isLatest`. Der
Befehl aus dem Eintrag (`uvx --with mcp~=2.0 falzmarke==0.11.2 mcp`) besteht den Handschlag
samt Brief: 22 319 Byte PDF, 34/34 Maße. Gegenprobe ohne `--with mcp~=2.0`: Der Handschlag
scheitert, weil das Paket `mcp` fehlt. `serverInfo.version` kommt weiter leer zurück (#467).

## Finding 2: Das Anthropic-Plugin-Verzeichnis ist nicht erreichbar

Behoben mit #454. Der Text unten beschreibt den Stand davor, die Tabelle den Stand danach.

Im Verzeichnis gibt es keine Skills als eigene Art, nur Plugin-Bündel. Ein Bündel ist ein Ordner mit
`.claude-plugin/plugin.json`. Den gibt es nicht, und laut Auftrag ist das ein Befund und kein
Bauauftrag. Geprüft gegen die Vorab-Checkliste von Anthropic:

| Anforderung | Stand im Repository |
|---|---|
| Ordner enthält `.claude-plugin/plugin.json` | ✓ `skill/.claude-plugin/plugin.json` |
| README mit mindestens 40 Wörtern im Plugin-Ordner | ✓ `skill/README.md` |
| `LICENSE` im Plugin-Ordner oder `license` im Manifest | ✓ `license` im Manifest |
| Archiv unter 50 MiB, unter 10.000 Dateien | ✓ 18,9 MiB, 507 Dateien |
| kein `export-ignore`, kein `filter` in `.gitattributes` | ✓ |
| Dateien außer Bildern und Schriften unter 256 KiB, sonst Prüfer | ✓ größte Python-Datei 132 KiB |
| höchstens 512 Dateien im Plugin | ✓ 63 unter `skill/` |
| Paket-Starter auf exakte Version festgelegt | offen, gilt für ein künftiges `.mcp.json` |

Gangbar ist der Unterordner `skill/`: Das Portal nimmt einen Plugin-Pfad an und liest nur diesen.
Ein Manifest dort ändert auch den Namen, sonst hieße das Plugin nach dem Ordner „skill“. Im
Auslieferungspaket liegen die Dateien des Skills schon richtig; es fehlen Manifest und README.

Ein lokaler MCP-Server in einem Plugin wird zusätzlich einem Prüfer vorgelegt („Runs a pinned npx
or uvx package“). Ein Plugin nur mit dem Skill vermeidet das. Der Aufwand für Manifest und README
ist geschätzt, nicht gemessen: rund eine Stunde von Hand, 15 Minuten mit Agent. Die Prüfung bei
Anthropic hat keine feste Dauer.

## Finding 3: Website-Bausteine aus dem Auftrag waren schon live

`/llms.txt`, `/llms-full.txt` (generiert von der cw-core-Integration `ai-discovery`), FAQPage und
SoftwareApplication stehen auf falzmarke.com. Eine zweite, statische `llms.txt` hätte die generierte
überschrieben. Gefehlt haben nur die Vergleichsseite, in `llms.txt` jede Nennung von CLI und MCP und
ein Test mit JSON-LD-Parser; das liefert der eigene PR im Repo `customer-falzmarke`.

## Finding 4: Smithery ist kein Einreichungsziel mehr

Smithery hat Konten, API, CLI und SDKs am 31.10.2026 abgeschaltet und bleibt als Verzeichnis unter
Arcade bestehen (`smithery.ai/future`); `smithery.ai/new` antwortet 404. Einzelheiten stehen in
[listings.md](listings.md).

## Analytics

Die Website zählt mit Plausible über den Proxy `/js/script.js` und `/api/event`; das Skript liefert
200, der Aufruf mit UTM-Parametern läuft ohne Weiterleitung durch, die Parameter gehen also nicht
verloren. Ziel des Proxys ist `events.blitzsicht.com`, das Dashboard liegt auf
`stats.blitzsicht.com` hinter Cloudflare Access. **Dass die Parameter dort ankommen, ist nicht
geprüft:** Das Dashboard war aus dieser Sitzung nicht lesbar.

## Ausgangswerte für die Zielmetrik

| Messgröße | Wert | Einschränkung |
|---|---|---|
| Git-Clones, 14 Tage | 1722, davon 511 eindeutig | enthält CI und Bots |
| PyPI-Downloads, 30 Tage | 1410 | enthält Spiegel; `pypistats.org` |
| Sterne | 1 | sperrt `travisvn/awesome-claude-skills` (Grenze 10) |
| Downloads `falzmarke.skill`, v0.10.0 | 7 | seit 25.10.2026 |

Die Erwähnungen in KI-Antworten misst `scripts/ai-sichtbarkeit.mjs` im Repo `customer-falzmarke`.
