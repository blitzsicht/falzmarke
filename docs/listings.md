# Listings: Einreichungen zum Abhaken

Stand: 02.11.2026. Grundlage ist die [Bestandsaufnahme](bestandsaufnahme-distribution.md). Die
Einreichungen erledigt der Betreiber von Hand. Jeder Einreichtext hat höchstens 300 Zeichen und
trägt den Vorbehalt zur Quellenlage (ADR 0032); `tests/test_verzeichnis_metadaten.py` hält beides.

Grundregel aus [mcp-verzeichnisse.md](mcp-verzeichnisse.md): keine Einträge, die eine Gegenleistung
verlangen, und keine Mehrfacheinreichung.

| Ziel | Stand | Nächster Schritt |
|---|---|---|
| Anthropic-Plugin-Verzeichnis | **gesperrt**, Manifest fehlt | erst Plugin-Ordner bauen |
| mcp.so | nicht gelistet | anmelden, kostenlosen Weg suchen, nicht zahlen |
| Smithery | **abgeschaltet** am 31.10.2026 | nichts tun |
| Glama | gelistet, nicht beansprucht | Eintrag beanspruchen |
| awesome-mcp-servers | PR offen, hängt an Glama | erledigt sich nach Glama |
| awesome-claude-skills | **gesperrt**, 1 von 10 Sternen | warten |
| GitHub Topics | 18 von 20 gesetzt | zwei ergänzen |

## Anthropic-Plugin-Verzeichnis

- [ ] Plugin-Ordner gebaut (fehlt: `.claude-plugin/plugin.json`, README; siehe Finding 2)
- [ ] `claude plugin validate ./skill` grün
- [ ] im Portal **Validate** grün

**Ziel-URL:** https://claude.ai/directory/manage → Submit new → Plugin bundle

**Konto:** claude.ai Pro, Max, Ultra, Team oder Enterprise, dazu auf claude.ai verbundenes
GitHub-Konto mit Schreibrecht. Das Plugin gehört der Organisation, die zuerst einreicht.

Das Portal liest Name und Kurzbeschreibung aus `plugin.json` und dem README. Der Text gehört also
ins Manifest. `homepage` bleibt die nackte Adresse (siehe UTM-Konvention), der Link unten gehört ins
README des Plugin-Ordners.

**Link:** https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=anthropic-202611

**Text de**

```text
Brief nach DIN 5008 erstellen: Claude schreibt den Inhalt, falzmarke setzt ihn als PDF/A und misst das fertige PDF nach. Sitzt eine Falzmarke nicht, endet der Lauf mit einem Fehler. Dazu E-Mails als .eml und Serienbriefe. MIT-Lizenz. Sollwerte aus Sekundärquellen, Normabgleich steht aus.
```

**Text en**

```text
Create German DIN 5008 business letters in Claude: you describe the letter, falzmarke typesets PDF/A and measures the finished PDF. A misplaced folding mark ends the run with an error. Also emails and mail merge. MIT. Uses target values from secondary sources; the check against the standard is open.
```

## mcp.so

- [ ] angemeldet, kostenlosen Weg geprüft
- [ ] Eintrag sichtbar

**Ziel-URL:** https://mcp.so/submit?type=server

**Konto:** Anmeldung über `mcp.so/sign-in`. Felder: Repository-URL (Pflicht), Name.

Ohne Anmeldung zeigt das Formular nur **Paid submission, 39 $ einmalig**. Das ist eine Gegenleistung
und fällt unter die Grundregel: nicht zahlen. Ob es nach der Anmeldung einen kostenlosen Weg gibt,
ist nicht geprüft. Gibt es keinen, entfällt dieses Ziel.

**Link:** https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=mcpso-202611

**Text de**

```text
MCP-Server für Briefe nach DIN 5008: Vier Werkzeuge setzen einen Brief als PDF/A, bauen eine .eml, prüfen eine fertige Datei und listen Absenderprofile. Der Messbericht kommt mit jedem PDF mit. Lokal über stdio, MIT-Lizenz. Sollwerte aus Sekundärquellen, Normabgleich steht aus.
```

**Text en**

```text
MCP server for German DIN 5008 letters: four tools render a letter to PDF/A, build an .eml, verify a finished file and list sender profiles. Every PDF comes with its measurement report. Local over stdio, MIT. Uses target values from secondary sources; the check against the standard is open.
```

## Smithery

- [x] geprüft: nichts einzureichen

**Ziel-URL:** https://smithery.ai (Einreichung `smithery.ai/new` antwortet 404)

**Konto:** keines möglich. Konten, API-Schlüssel, API, CLI und SDKs sind seit 31.10.2026
abgeschaltet (`smithery.ai/future`). Die Seite bleibt als öffentliches Verzeichnis unter Arcade
bestehen, mit einer kuratierten Auswahl. Einen neuen Einreichweg nennt die Ankündigung nicht.

Die Texte stehen nur für den Fall, dass Arcade wieder einen Weg öffnet.

**Link:** https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=smithery-202611

**Text de**

```text
falzmarke setzt Briefe nach DIN 5008 aus Markdown als PDF/A und misst jedes fertige PDF nach. Als MCP-Server über stdio, dazu CLI und Claude-Skill. MIT-Lizenz. Sollwerte aus Sekundärquellen, Normabgleich steht aus.
```

**Text en**

```text
falzmarke typesets German DIN 5008 letters from Markdown as PDF/A and measures every finished PDF. MCP server over stdio, plus CLI and Claude skill. MIT. Uses target values from secondary sources; the check against the standard is open.
```

## Glama

- [ ] Eintrag beansprucht
- [ ] Quality Score ausgewertet

**Ziel-URL:** https://glama.ai/mcp/servers/blitzsicht/falzmarke

**Konto:** Glama, Anmeldung mit GitHub; das Konto muss Zugriff auf `blitzsicht/falzmarke` haben.

Der Eintrag und der Badge antworten 200. Es fehlen die beiden Schritte oben, und genau die verlangt
der Maintainer im PR bei awesome-mcp-servers. Glama baut aus dem `Dockerfile` im Wurzelverzeichnis.

**Link:** https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=glama-202611

**Text de**

```text
Geschäftsbriefe nach DIN 5008 aus Markdown: PDF/A setzen, .eml bauen, fertige Dateien prüfen. Das PDF wird nach dem Setzen nachgemessen, eine verrutschte Falzmarke ist ein Fehler. Läuft lokal über stdio, ohne Konto. MIT-Lizenz. Sollwerte aus Sekundärquellen, Normabgleich steht aus.
```

**Text en**

```text
German DIN 5008 business letters from Markdown: render PDF/A, build .eml, verify finished files. The PDF is measured after rendering and a misplaced folding mark is an error. Runs locally over stdio, no account. MIT. Uses target values from secondary sources; the check against the standard is open.
```

## awesome-mcp-servers

- [ ] Glama erledigt (Abschnitt oben)
- [ ] Merge abwarten, kein neuer PR

**Ziel-URL:** https://github.com/punkpeye/awesome-mcp-servers/pull/13221 (offen seit 30.08.2026)

**Konto:** GitHub, vorhanden.

Der Maintainer hat zweimal nachgefragt: Der Server muss auf Glama beansprucht sein und einen
Quality Score haben. Der Text unten ersetzt die Beschreibung im PR nur, wenn der Maintainer sie
beanstandet; die Liste führt englische Zeilen und verlinkt das Repository, nicht die Website.

**Link:** https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=awesome-mcp-202611

**Text de**

```text
Deutsche Geschäftsbriefe (DIN 5008) aus Markdown als PDF/A über Typst. Vier Werkzeuge: Brief setzen, .eml bauen, fertige Datei prüfen, Profile listen. Das fertige PDF wird nachgemessen. Sollwerte aus Sekundärquellen, Normabgleich steht aus.
```

**Text en**

```text
German business letters (DIN 5008) from Markdown as PDF/A via Typst. Four tools: render a letter, build an .eml, verify a finished file, list profiles. The finished PDF is measured. Uses target values from secondary sources; the check against the standard is open.
```

## awesome-claude-skills

- [ ] `travisvn`: ab 10 Sternen einreichen
- [ ] Entscheidung `ComposioHQ`: Default nicht verfolgen

**Ziel-URL:** https://github.com/travisvn/awesome-claude-skills

**Konto:** GitHub, vorhanden.

Unter dem Namen laufen zwei Listen:

| Liste | Sterne | letzte Änderung | Tor |
|---|---|---|---|
| `travisvn/awesome-claude-skills` | 15,7k | 28.04.2026 | unter 10 Sternen wird automatisch geschlossen; falzmarke hat 1 |
| `ComposioHQ/awesome-claude-skills` | 78,6k | 18.09.2026 | verlangt einen Skill-Ordner im fremden Repository |

Bei `travisvn` lohnt das Warten kaum: Die Liste ruht seit einem halben Jahr. `ComposioHQ` hieße eine
zweite Fassung des Skills in einem fremden Repository, die altert. Vorschlag: keine von beiden
aktiv verfolgen und die Zeit in den Plugin-Ordner stecken.

**Link:** https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=awesome-skills-202611

**Text de**

```text
Claude-Skill für deutsche Geschäftspost: Briefe nach DIN 5008 als PDF/A, am fertigen PDF nachgemessen, dazu E-Mails als .eml und Urkunden mit Unterschriftslinien. Rechnet in der Sandbox, ohne Dienst und ohne Konto. MIT-Lizenz. Sollwerte aus Sekundärquellen, Normabgleich steht aus.
```

**Text en**

```text
Claude skill for German business mail: DIN 5008 letters as PDF/A, measured on the finished PDF, plus emails as .eml and agreements with signature lines. Runs in the sandbox, no service and no account. MIT. Uses target values from secondary sources; the check against the standard is open.
```

## GitHub Topics

- [ ] `business-letter` und `document-generation` in `scripts/topics.py` ergänzt
- [ ] `bash scripts/repo-einstellungen.sh` gelaufen
- [ ] `python3 scripts/repo_pruefung.py --repo blitzsicht/falzmarke` ohne Abweichung

**Ziel-URL:** https://github.com/blitzsicht/falzmarke

**Konto:** Admin-Recht am Repository.

Es stehen 18 von 20 Themen. Die Liste lebt in `scripts/topics.py`, die Prüfung vergleicht dagegen;
von Hand gesetzte Themen stünden dort nicht. Die zwei freien Plätze füllen die englischen Begriffe,
die noch fehlen. Das Homepage-Feld bleibt ohne UTM: `repo_pruefung.py` hält es auf der nackten
Domain, und die Canonical-URL gehört nicht in ein Metadatenfeld.

## UTM-Konvention

| Parameter | Listing | Produkt |
|---|---|---|
| `utm_source` | `listing` | `footer` |
| `utm_medium` | `directory` | `product` |
| `utm_campaign` | `<ziel>-YYYYMM` | `<ort>-YYYYMM` |

`utm_source` trennt nur Listing und Produkt, das einzelne Verzeichnis steckt deshalb in
`utm_campaign`. Betroffen sind `README.md` und diese Datei; `skill/SKILL.md` enthält keinen
Website-Link. `pyproject.toml` und `server.json` bleiben ohne Parameter: Dort steht die kanonische
Adresse, die Verzeichnisse und Assistenten übernehmen.

Ausgewertet wird im Plausible-Dashboard unter *Sources* und *Campaigns*. Ein Monatswechsel ändert
nur neue Einreichungen; bestehende Links bleiben, wie sie sind.
