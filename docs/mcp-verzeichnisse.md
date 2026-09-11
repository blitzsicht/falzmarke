# MCP-Verzeichnisse: wo falzmarke steht und was noch aussteht

falzmarke bringt seit v0.9.x einen MCP-Dienst mit (`falzmarke mcp`, vier Werkzeuge). Dass ein
Werkzeug existiert, heißt nicht, dass es gefunden wird — Issue #237 entstand, weil die
Verzeichnisse den Server nicht kannten.

Dieses Dokument hält fest, was erledigt ist, was **automatisch** läuft und was einen Menschen
braucht. Es ist bewusst eine Bestandsliste und keine Anleitung zum Bewerben.

## Stand

| Verzeichnis | Wie der Eintrag entsteht | Stand |
|---|---|---|
| **Offizielles MCP-Registry** | `server.json` + Job `mcp-registry` im Release-Lauf, OIDC | läuft beim nächsten Release von selbst |
| **Glama** | Konto nötig, „Add Server" in der Weboberfläche | **offen** — siehe unten |
| **awesome-mcp-servers** | PR [punkpeye/awesome-mcp-servers#13221](https://github.com/punkpeye/awesome-mcp-servers/pull/13221) | offen; der Score-Badge setzt den Glama-Eintrag voraus |
| Repo-Themen (`mcp`, `mcp-server`, `model-context-protocol`) | `scripts/topics.py`, Wächter `repo_pruefung.py` | erledigt |
| `Dockerfile` im Wurzelverzeichnis | liegt dort; CI-Job „MCP-Dienst im Container" baut und spricht ihn an | erledigt |
| Englisches README | `README.en.md` | erledigt |

## Das offizielle Registry — und warum es beim Release passiert

Der Job `mcp-registry` in [`.github/workflows/release.yml`](../.github/workflows/release.yml)
läuft am Versions-Tag, **nach** dem PyPI-Job. Das ist keine Vorsicht, sondern Notwendigkeit:

> Das Registry prüft die Eigentümerschaft eines PyPI-Pakets, indem es die Zeichenkette
> `mcp-name: <servername>` in der **Projektbeschreibung auf PyPI** sucht.

Diese Beschreibung ist unsere `README.md`, und sie entsteht dort erst mit dem Upload. Ein
eigener Workflow auf dasselbe Tag liefe parallel zum PyPI-Job, und welcher zuerst fertig wäre,
entschiede das Wetter.

**Folge:** Der Eintrag entsteht beim **nächsten** Release, nicht beim Merge von #237. Die
Fassung auf PyPI muss die `mcp-name`-Zeile tragen, und das tut erst die nächste — v0.9.8 lag
vor dieser Änderung oben.

Die Anmeldung läuft über `mcp-publisher login github-oidc`: Der Lauf weist sich mit einem
kurzlebigen Token aus, aus dem das Registry den erlaubten Namensraum `io.github.<owner>/<repo>`
ableitet. Kein Token, kein Konto, kein Geheimnis, das abfließen könnte.

Nachmessen lässt sich der Stand jederzeit:

```bash
python3 scripts/repo_pruefung.py --repo blitzsicht/falzmarke
# ABWEICHUNG  Eintrag im MCP-Registry (io.github.blitzsicht/falzmarke): soll='gelistet' ist='nicht gelistet'
```

Diese Abweichung ist **erwartet**, solange kein Release mit der `mcp-name`-Zeile
veröffentlicht ist. Sie ist kein Defekt des Repositories, sondern die offene Hälfte von #237 —
und sie steht dort, damit niemand sie für erledigt hält.

## Glama — der Schritt, der ein Konto braucht

Glama nennt seinen Einreichungsweg nicht öffentlich. Gemessen am 11.09.2026: Weder
`glama.ai/mcp/servers` noch die API-Referenz beschreiben ein Verfahren; die Referenz nennt als
Aufnahmequellen „Community submissions", automatische Entdeckung, die
Awesome-MCP-Servers-Liste und das offizielle Registry.

Damit gibt es zwei Wege, und der erste läuft schon: Ein Eintrag im offiziellen Registry ist
eine von Glamas eigenen Quellen. **Zugesagt ist er dadurch nicht** — ob und wann Glama daraus
einen Eintrag macht, steht nirgends.

Der zweite Weg ist der Knopf, und er dauert fünf Minuten:

1. Auf [glama.ai](https://glama.ai) anmelden (GitHub-Login genügt).
2. Auf `glama.ai/mcp/servers` den Knopf **Add Server** drücken.
3. Das Repository angeben: `blitzsicht/falzmarke`. Glama baut es selbst — das `Dockerfile`
   liegt im Wurzelverzeichnis, genau dafür.
4. Fertig, wenn `glama.ai/mcp/servers/blitzsicht/falzmarke` **200** statt 404 liefert:

   ```bash
   curl -o /dev/null -s -w '%{http_code}\n' https://glama.ai/mcp/servers/blitzsicht/falzmarke
   ```

   Gegenprobe, damit die 404 nicht an der Adressform liegt — ein gelisteter Server muss 200
   geben. Gemessen am 11.09.2026:

   ```bash
   curl -o /dev/null -s -w '%{http_code}\n' https://glama.ai/mcp/servers/modelcontextprotocol/servers
   #  200  — die Adressform ist richtig
   curl -o /dev/null -s -w '%{http_code}\n' https://glama.ai/mcp/servers/blitzsicht/falzmarke
   #  404  — der Eintrag fehlt wirklich
   ```

   Die Gegenprobe ist nötig und nicht Zierde: Von drei an diesem Tag probierten Adressen
   antworteten zwei mit 404, weil **sie** nicht gelistet sind — eine 404 allein belegt also
   nichts über die Adressform.

5. Danach den Score-Badge im offenen PR bei `punkpeye/awesome-mcp-servers` nachtragen.

## Was nicht getan wird

Keine Einträge in Verzeichnisse, die eine Gegenleistung verlangen, keine Mehrfacheinreichung
desselben Servers unter verschiedenen Namen, und keine Listen, die den Server beschreiben,
ohne ihn gebaut zu haben. Ein Eintrag soll jemandem helfen, der ein Werkzeug sucht — nicht eine
Zahl erhöhen.

## Verwandt

- [`server.json`](../server.json) — der Eintrag, den das Registry liest
- [`Dockerfile`](../Dockerfile) — wie die Verzeichnisse den Server bauen
- [Befehle](cli.md) — `falzmarke mcp` und die vier Werkzeuge
