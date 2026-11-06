# Listings: Einreichungen zum Abhaken

Der Stand gilt je Zeile, mit dem Datum seiner Messung; eine Zeile ohne Datum ist zuletzt am
02.11.2026 gemessen. Grundlage ist die [Bestandsaufnahme](bestandsaufnahme-distribution.md). Die
Einreichungen erledigt der Betreiber von Hand. Jeder Einreichtext hat höchstens 300 Zeichen und
trägt den Vorbehalt zur Quellenlage (ADR 0032); `tests/test_verzeichnis_metadaten.py` hält beides.

Grundregel aus [mcp-verzeichnisse.md](mcp-verzeichnisse.md): keine Einträge, die eine Gegenleistung
verlangen, und keine Mehrfacheinreichung.

| Ziel | Stand | Nächster Schritt |
|---|---|---|
| Anthropic-Plugin-Verzeichnis | eingereicht v0.11.2 @ 8d44c0d, Sicherheitsscan läuft, 2 Policy-Holds (06.11.2026) | Prüfung abwarten; Rückfragen kommen an servus@blitzsicht.com |
| mcp.so | eingereicht per Issue [chatmcp/mcpso#6843](https://github.com/chatmcp/mcpso/issues/6843), offen, kein Kommentar (06.11.2026) | abwarten, nicht zahlen |
| Smithery | **abgeschaltet** am 31.10.2026 | nichts tun |
| Glama | beansprucht; Badge „maintenance rated B“; **nicht deploybar** (06.11.2026) | Dockerfile in Glama eintragen, Reiter „Admin ⚠“ ansehen |
| awesome-mcp-servers | PR offen; Anspruch erfüllt, Glama-Prüfung offen (06.11.2026) | erst Glama deploybar machen, dann Maintainer antworten |
| awesome-claude-skills | **gesperrt**, 1 von 10 Sternen | Default: nicht verfolgen; `travisvn` bei 10 Sternen neu bewerten |
| GitHub Topics | 20 von 20 gesetzt | nichts zu tun |

## Anthropic-Plugin-Verzeichnis

- [x] Plugin-Ordner gebaut (`skill/.claude-plugin/plugin.json`, `skill/README.md`, Icon)
- [x] `claude plugin validate ./skill` ohne Fehler; eine Warnung bleibt, siehe unten
- [x] im Portal **Validate** ohne Fehler: 2 Warnungen, 2 Policy-Holds (06.11.2026)
- [x] eingereicht am 06.11.2026 um 11:43 MEZ: v0.11.2, `main @ 8d44c0d`, Plugin path `skill`
- [x] Push-Webhook in `blitzsicht/falzmarke` angelegt (nur push, `application/json`); Ping 200
- [ ] Sicherheitsscan und Prüfung bestanden
- [ ] veröffentlicht (die erste Version veröffentlicht der Betreiber oder ein Prüfer)

Stand nach dem Einreichen (Screenshot des Betreibers, 06.11.2026): Status „Wird gescannt“, Kontakt
`servus@blitzsicht.com`, gelistet werden soll es in Claude Code, Cowork und den Claude-Apps.
Auto-Publish ist an, greift aber erst nach der ersten freigegebenen Version.

**Antworten im Portal**, damit eine spätere Fassung sie nicht widerspricht:

- Personenbezogene Daten: *Reads and stores*. Briefe tragen Namen und Anschriften, Absenderprofile
  liegen als Dateien auf dem Rechner.
- Daten an Dienste außerhalb der Konnektoren: *Yes — listed in README*. PyPI beim ersten Lauf und,
  wenn eingerichtet, das eigene Postfach über den IMAP-Proxy (`skill/README.md`, „Wohin Daten
  gehen“, #554). Ändert sich einer dieser Wege, muss das README mitwandern.
- Aufbewahrung: *Not retained*. Unter 18: *Nein*.

**Die zwei Policy-Holds:** Der Credential-Hold kommt von `referenzdienst.py`. Die Datei liegt im
Plugin-Ordner, läuft aber nur auf falzmarke.com. Der Download-and-run-Hold ist ein Fehlalarm
(`emit.py` erwähnt `#eval` nur in einem Kommentar, und die `.otf` ist eine Binärdatei). Ein Feld für
eine Prüfer-Notiz gab es nicht. Fragt der Prüfer nach, steht die Antwort im Handoff vom 06.11.2026.
Default: `referenzdienst.py` erst dann aus dem Plugin-Ordner nehmen, wenn er es beanstandet.

**Ziel-URL:** https://claude.ai/directory/manage → Submit new → Plugin bundle

**Konto:** claude.ai Pro, Max, Ultra, Team oder Enterprise, dazu auf claude.ai verbundenes
GitHub-Konto mit Schreibrecht. Das Plugin gehört der Organisation, die zuerst einreicht.

Das Portal liest Name und Kurzbeschreibung aus `plugin.json` und dem README. Der Text gehört also
ins Manifest. `homepage` bleibt die nackte Adresse (siehe UTM-Konvention), der Link unten gehört ins
README des Plugin-Ordners.

Seit #467 nennt das Manifest eine `version`, die fünfte Stelle, die bei jedem Release mitwandert.
`tests/test_version.py` hält sie gegen `pyproject.toml` (siehe CONTRIBUTING.md, Abschnitt zum
Bump).

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

- [x] kostenlosen Weg gefunden: Einreichung als GitHub-Issue
  ([chatmcp/mcpso#6843](https://github.com/chatmcp/mcpso/issues/6843), 06.11.2026 08:32Z)
- [ ] Eintrag sichtbar

Gemessen am 06.11.2026: Das Issue ist offen und ohne Kommentar. Die Betreiber arbeiten die
Einreichungs-Issues von Hand ab; bei älteren dauerte das Tage bis Wochen. Nicht nachfassen und
nicht zusätzlich über das Formular einreichen (Grundregel: keine Mehrfacheinreichung).

**Ziel-URL:** https://mcp.so/submit?type=server

**Konto:** Anmeldung über `mcp.so/sign-in`. Felder: Repository-URL (Pflicht), Name.

Ohne Anmeldung zeigt das Formular nur **Paid submission, 39 $ einmalig**. Das ist eine Gegenleistung
und fällt unter die Grundregel: nicht zahlen. Ob das Formular nach der Anmeldung kostenlos wird, ist
nicht geprüft und seit dem Issue auch nicht mehr nötig.

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

- [x] Eintrag beansprucht (Screenshot des Betreibers, 05.11.2026 15:43 Ortszeit)
- [ ] Glama-Prüfung bestanden: Server startet in Glama und beantwortet die Introspektion
- [ ] Reiter „Admin ⚠“: was das Warndreieck bemängelt

**Ziel-URL:** https://glama.ai/mcp/servers/blitzsicht/falzmarke

**Konto:** Glama, Anmeldung mit GitHub; das Konto muss Zugriff auf `blitzsicht/falzmarke` haben.

Gemessen am 06.11.2026: Das Score-Badge (`…/badges/score.svg`) trägt den Text „claimed by its
maintainer, maintenance rated B“. Am 05.11.2026 stand dort „rated A“. Die Note ist die
Wartungsnote, sie schwankt und ist kein fester Stand; deshalb steht sie hier nur mit Datum. Eine
eigene Qualitäts- oder Lizenznote für falzmarke zeigt die Seite `…/score` nicht.

Damit ist nur die erste Hälfte dessen erfüllt, was der Bot im PR bei awesome-mcp-servers verlangt
(Kommentar vom 30.08.2026): gelistet und beansprucht. Die zweite Hälfte fehlt: Der Server soll
„alle Prüfungen bestehen“, und dazu muss das Dockerfile **direkt in Glama** eingetragen werden.
Glama übernimmt es nicht von selbst aus dem Repository. Am 06.11.2026 meldet die Serverseite
„This server cannot be deployed“. Das `Dockerfile` im Wurzelverzeichnis taugt als Vorlage: Der
CI-Job „MCP-Dienst im Container“ baut es und spricht den Dienst an. Ob das Warndreieck im Reiter
„Admin“ genau das bemängelt, ist nicht geprüft.

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

- [x] Glama beansprucht (Abschnitt oben)
- [ ] Glama-Prüfung bestanden (Abschnitt oben)
- [x] Maintainer im PR Bescheid gegeben (Kommentar 05.11.2026 15:34Z = 16:34 MEZ)
- [ ] nach bestandener Glama-Prüfung im PR richtigstellen: Der Kommentar nennt „rated A“ und
  „both Glama steps are done“; beides stimmt so nicht mehr (siehe Glama)
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

- [ ] Entscheidung `travisvn`: bei 10 Sternen neu bewerten, Default nicht verfolgen
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

- [x] `business-letter` und `document-generation` in `scripts/topics.py` ergänzt
- [x] am Repository gesetzt, mit `gh repo edit --add-topic` (das Skript schriebe auch Rulesets und Environment)
- [x] `python3 scripts/repo_pruefung.py --repo blitzsicht/falzmarke` ohne Abweichung

**Ziel-URL:** https://github.com/blitzsicht/falzmarke

**Konto:** Admin-Recht am Repository.

Es stehen 20 von 20 Themen, ein neues verlangt also, ein altes zu streichen. Die Liste lebt in
`scripts/topics.py`, die Prüfung vergleicht dagegen; von Hand gesetzte Themen stünden dort nicht.
Das Homepage-Feld bleibt ohne UTM: `repo_pruefung.py` hält es auf der nackten
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
