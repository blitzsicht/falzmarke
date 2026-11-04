# 0051 — Gesendet-Sperre, Entwurf im Postfach, Fassungs-Kopfzeile

**Datum:** 21.10.2026 · **Status:** angenommen · **Ergänzt:** [0049](0049-entwurf-in-thunderbird.md),
[0050](0050-signatur-aus-thunderbird.md) · **Bricht:** [0038](0038-oeffnen-ist-kein-versand.md), Punkt 4,
für einen Fall

## Anlass

Am 21.10.2026 ging eine Antwort **zweimal** an denselben Empfänger. Der Ablauf:

1. `email --oeffnen` legte den Entwurf per `thunderbird -compose` an. Der Entwurf trug kein
   `In-Reply-To`, denn `-compose` kennt kein Feld dafür. Die Antwort hätte einen neuen Thread
   begonnen.
2. Der Betreiber schickte die Mail deshalb aus einem „Antworten“-Fenster auf die
   Vorgängernachricht, mit dem Text aus dem Entwurf und dem Betreff `Re: <alter Betreff>`.
3. Das falzmarke-Fenster war damit zu. Eine spätere Sitzung sah in die Entwürfe, fand nichts,
   schloss daraus „nicht gesendet“ und legte neu an. Die Mail ging ein zweites Mal hinaus.

Zwei Lücken: Niemand sah im Gesendet-Ordner nach, und der Entwurf konnte den Bezug zur
Vorgängernachricht nicht tragen.

## Entscheidung 1: `--oeffnen` sieht vorher im Gesendet-Ordner nach

Bevor ein Entwurf entsteht, liest `email --oeffnen` den Gesendet-Ordner des Absenders über den
lokalen IMAP-Proxy (`127.0.0.1:1993`, `FALZMARKE_GESENDET_IMAP=host:port`). Es wird nur gelesen:
`EXAMINE` und `BODY.PEEK`, das Gelesen-Kennzeichen bleibt unverändert. Gesperrt wird, wenn in den
letzten **24 Stunden** (`FALZMARKE_GESENDET_STUNDEN`) eine Mail an **denselben Empfänger** ging
und zusätzlich eines davon gilt:

- **dieselbe Fassung:** Die Kopfzeile `X-Falzmarke-Fassung` stimmt überein (Entscheidung 3).
  Thunderbird verwirft sie beim Senden (gemessen 21.10.2026). Im Gesendet-Ordner tragen deshalb
  Betreff und Text; die Fassung greift dort nur, wenn eine Mail auf anderem Weg hinausging.
- **derselbe Text:** Der Text bis zur Grußformel stimmt überein, oder die gesendete Mail beginnt
  mit dem eigenen Text. Verglichen wird ohne Zitat, Signatur, Listenzeichen, URLs, Leerraum und
  Satzzeichen, Groß- und Kleinschreibung zählt nicht. Ein HTML-Teil wird erst zu Klartext. Damit
  fällt der Vorfall auf: anderer Betreff, derselbe Text.
- **derselbe Betreff ohne Vorsilben** (`Re:`, `AW:`, `Fwd:` …) mit anderem Text: Das ist eine
  geänderte Fassung. Sie sperrt ebenfalls, denn gemeint ist dann meist ein Nachtrag und kein
  zweites Original.

Die Meldungen:

| Lage | Ausgabe | Exit |
|---|---|---|
| derselbe Text oder dieselbe Fassung | `SCHON GESENDET  <Zeit> an <Empfänger>: „<Betreff>“ …` | 4 |
| derselbe Betreff, anderer Text | `GEÄNDERTE FASSUNG  „<Betreff>“ ging … schon hinaus … — als Nachtrag schicken?` | 4 |
| nichts gefunden | `OK  nicht gesendet: N Mails der letzten 24 h in „<Ordner>“ von <Adresse> angesehen` | 0 |
| nicht nachsehbar | letzte Zeile `GESENDET NICHT GEPRÜFT: <Grund>`, **sperrt nicht** | 0 |

`--trotz-gesendet` übergeht die Sperre. Wer es setzt, ist ein Mensch, keine Sitzung: Die
Anweisung in `skill/SKILL.md` verlangt, die Zeile wörtlich weiterzugeben und zu fragen.
`FALZMARKE_GESENDET=nie` schaltet die Prüfung ab. Wo kein Fenster aufgehen kann
(`FALZMARKE_OEFFNEN=nie`, `CI`), entsteht auch kein Entwurf, und es wird nicht nachgesehen.

Der Gesendet-Ordner kommt aus Thunderbird (`fcc_folder` der Identität), sonst aus dem
Sonderordner-Kennzeichen `\Sent` (RFC 6154), sonst heißt er „Gesendete Elemente“. Die Frist für
Verbindung und Lesen beträgt 5 s.

### Warum das ADR 0038, Punkt 4 bricht

Dort steht: Ein gescheitertes Öffnen ändert den Exit-Code nicht, denn die Datei ist geschrieben
und gemessen. Das gilt weiter für alles, was **scheitert**. Die Sperre scheitert nicht, sie
**verweigert**. Dass kein Fenster aufgeht, ist hier der Zweck, und eine Sitzung muss das von „ging
nicht auf“ unterscheiden können. Deshalb gibt es einen eigenen Code. Exit 4 war frei: In der Doku
stand er für „Fehler im Renderer“, aber kein Codepfad gab ihn zurück, denn ein Fehler im Renderer
endet als Python-Ausnahme mit 1. Die Doku ist angepasst.

`serie` bleibt unberührt: Ohne `--oeffnen` wird weder nachgesehen noch gesperrt.

## Entscheidung 2: Der Entwurf liegt im Postfach (Thunderbird-Weg)

Ist der Proxy erreichbar, legt `--oeffnen` die **fertige `.eml`** per `APPEND` mit den
Kennzeichen `(\Draft \Seen)` in den Entwürfe-Ordner des Absenders. Der Ordner kommt aus
Thunderbird (`draft_folder`), sonst aus `\Drafts`. Damit trägt der Entwurf alle Kopfzeilen der
gemessenen Datei, auch `In-Reply-To`, `References` und `X-Falzmarke-Fassung`, und alle Anhänge.
**Dann gibt es kein `-compose`**: Zwei Entwürfe wären der Fehler aus #287.

Das ist der **erste Schreibzugriff auf ein Postfach**. Er bleibt eng:

- Geschrieben wird nur mit `APPEND`, nur in den Entwürfe-Ordner, nur die eine Datei.
- Nie gesendet, nie gelöscht, nie verschoben, keine Kennzeichen geändert. `postfach.py` enthält
  dafür keinen Aufruf. `tests/test_postfach.py` liest das am Syntaxbaum nach, und die Attrappe
  wirft bei jedem solchen Befehl.
- **Doppel-Probe vorher:** Liegt schon ein Entwurf mit einem gemeinsamen Empfänger und demselben
  Betreff ohne Vorsilben, wird nichts abgelegt. Die Meldung lautet
  `ENTWURF LIEGT SCHON  <Zeit> „<Betreff>“ in „Entwürfe“ von <Adresse>`, und die Datei wird nicht
  nachgeschoben. `--noch-ein-entwurf` legt trotzdem ab.
- **Nachgezählt:** Vorher und nachher werden die passenden Entwürfe gezählt. Kommt nicht genau
  einer dazu oder reißt die Verbindung nach dem `APPEND`, ist der Entwurf **ungewiss**. Dann wird
  nichts nachgeschoben, wie in #287.
- Kein Proxy, keine Anmeldung, kein Entwürfe-Ordner oder `FALZMARKE_POSTFACH=nie`: Es bleibt bei
  `-compose`, mit der Zeile `kein Postfach-Entwurf: <Grund>`.

Die Ausgabe lautet `OK  Entwurf liegt in „Entwürfe“ von <Adresse>: <Betreff>`. Es geht kein
Fenster auf. Ob Thunderbird einen Server-Entwurf über die Befehlszeile **zum Bearbeiten**
öffnen kann, ist nachgelesen im Befehlszeilen-Handler von Thunderbird 158.0
(`modules/MessengerContentHandler.sys.mjs` in `omni.ja`, 21.10.2026). Einen solchen Weg gibt es
nicht:

- `mid:<Message-ID>` zeigt die Nachricht an (`MailUtils.openMessageForMessageId`), öffnet aber
  keinen Entwurf zum Bearbeiten.
- `-compose` legt nur neu an.
- Eine `.eml` mit `X-Unsent: 1` öffnet Thunderbird 158 laut Code als Entwurf
  (`OpenComposeWindow(…, Draft, …)`). Die Gegenprobe mit `X-Unsent: 1` in
  `docs/mailprogramme-2026-08-27.md` betraf nur Outlook für Mac. Für Thunderbird ist das **nicht
  gemessen** und bleibt offen. Es wäre ein Weg zu einem Fenster mit allen Kopfzeilen, ohne
  Schreibzugriff auf das Postfach.

**Outlook bleibt, wie es ist.** Der Betreiber nutzt seit Oktober 2026 nur noch Thunderbird. Der
Outlook-Weg wird deshalb nicht erweitert: Einen Postfach-Entwurf gibt es dort nicht. Die
Gesendet-Sperre aus Entscheidung 1 steht vor jedem Entwurf und gilt damit auch für Outlook.
Zurückgebaut wird der Weg in diesem Schritt nicht.

### Die Signatur je Weg

| Weg | Was im Entwurf steht | Belegt? |
|---|---|---|
| Postfach-Entwurf (Thunderbird) | die Signatur aus dem Profil, aus der `.eml`, genau einmal. Thunderbird ergänzt beim Bearbeiten des Entwurfs keine eigene, obwohl die Identität eine trägt. | gemessen 21.10.2026 |
| `-compose`, Identität mit eigener Signatur | die Signatur aus Thunderbird, die aus dem Profil fehlt | laut 0050 |
| `-compose`, Identität ohne Signatur | die Signatur aus dem Profil | laut 0049/0050 |
| Outlook | die Signatur aus dem Profil, dazu die Konto-Signatur von Outlook, also womöglich zweimal | gesehen 08.09.2026 (`cli.py`) |
| Datei übergeben | die Signatur aus dem Profil, im Lesefenster | — |

Beim Postfach-Entwurf greift 0050 **nicht**: Abgelegt wird die gemessene Datei, und die trägt
die Signatur aus dem Profil. Dass Thunderbird keine eigene dazusetzt, war beim Bau eine Annahme
und ist seit der Messung unten belegt.

### Die Signatur steckt in `<div class="moz-signature">`

Beim Senden des Postfach-Entwurfs fragte Thunderbird jedes Mal: „Haben Sie vergessen, einen
Anhang anzufügen?“. Auslöser war das Wort „Anhänge“ im Hinweis der Signatur („Diese E-Mail und
etwaige Anhänge …“). Die Anhang-Erinnerung sucht ihre Schlüsselwörter im Rumpf und nimmt vorher
heraus:

- Zitate (`blockquote`)
- alles mit der Klasse `moz-signature` (HTML)
- den Teil nach `-- ` (Klartext)

Fundstelle: `MsgComposeCommands.js`, Thunderbird 158.0, um Zeile 11052 (in `omni.ja`). Die
deutschen Schlüsselwörter stehen in
`chrome/de/locale/de/messenger/messengercompose/composeMsgs.properties`:
`.doc,.pdf,…,Anhang,Anhänge,angehängt,Wiedervorlage,Begleitschreiben,…,anbei`.

`eml.signatur_html` setzt die HTML-Signatur deshalb in eine Hülle mit dieser Klasse
(`eml.KLASSE_SIGNATUR`). Bei der mitgebrachten Signatur trägt das vorhandene `div` die Klasse.
Weil die Hülle Teil des Stücks ist, das `signatur_html` liefert, findet `oeffnen.ohne_signatur`
es weiter wörtlich, und ADR 0050 bleibt unberührt. Der Klartextteil trägt den Trenner `-- `
schon, `verify --email` prüft ihn (`signaturtrenner`); dort ändert sich nichts.

Die Grenze: „anbei“ oder „Anhang“ **im Text der Nachricht** löst die Erinnerung weiter aus, und
das ist richtig so. Beim **Bearbeiten eines Entwurfs** prüft Thunderbird zusätzlich den
**Betreff** (`MsgComposeCommands.js`, `checkForAttachmentKeywords`: „after reopening a draft“,
`gEditingDraft`). Ein Betreff wie „… Anhang-Erinnerung“ löst sie also aus, auch wenn die Signatur
gekennzeichnet ist. Gemessen 21.10.2026, siehe unten.

## Entscheidung 3: Die Fassungs-Kopfzeile

Jede `.eml` trägt `X-Falzmarke-Fassung: <12 Hex-Zeichen>`, die ersten 12 Zeichen des SHA-256 der
ganzen Quelldatei samt Frontmatter. Zeilenenden werden vorher auf `\n` gebracht. Ohne Pfad,
ohne Dateinamen: Die Kopfzeile reist mit der Mail zum Empfänger, und ein Pfad verriete Ordner
und Kundennamen. Dieselbe Quelle ergibt dieselbe Fassung, auch unter anderem Namen.

Die Kopfzeile übersteht den Weg ins Postfach unverändert, aber **nicht das Senden**: Thunderbird
verwirft sie (gemessen 21.10.2026). Sie dient deshalb nur, solange die Nachricht liegt. Nach dem
`APPEND` wird am abgelegten Entwurf nachgelesen, dass er die gemessene Datei ist. Die
Doppel-Probe vergleicht Empfänger und Betreff, nicht die Fassung. Im Gesendet-Ordner zählen
Betreff und Text.

## Messung 21.10.2026, 21:00 (Betreiber, danach nur lesend per IMAP)

Ein Test-Entwurf an die eigene Adresse, mit `antwort_auf`, per `--oeffnen` ins Postfach gelegt,
in Thunderbird bearbeitet und gesendet:

| Was | Ergebnis |
|---|---|
| Entwurf in Thunderbird sichtbar | ja, sobald der Ordner „Entwürfe“ angeklickt wird |
| Signatur beim Bearbeiten | genau einmal |
| `In-Reply-To`, `References` in der gesendeten Mail | erhalten |
| Pflichtangabe „USt-IdNr.“ | je einmal im Text- und im HTML-Teil |
| `X-Falzmarke-Fassung` in der gesendeten Mail | **fehlt**, Thunderbird verwirft die Zeile |
| Sperre danach, dieselbe Quelle | `SCHON GESENDET  21.10.2026 21:00`, Exit 4, kein Entwurf |
| Anhang-Erinnerung beim Senden | **kam**, ausgelöst durch die Signatur (oben) |
| Zweiter Entwurf, Hülle `moz-signature`, Betreff „[falzmarke-test] Anhang-Erinnerung“ | **kam** — ausgelöst durch den Betreff, Test damit ungültig |
| Dritter Entwurf, Hülle `moz-signature`, Betreff und Text ohne Schlüsselwort | **kam nicht**; die Klasse steht auch in der gesendeten Mail (1×) |
| Sperre beim dritten Entwurf (gleicher Text wie der zweite, neuer Betreff) | `SCHON GESENDET  21.10.2026 21:27`, erst mit `--trotz-gesendet` abgelegt |

## Tests: ein Wächter für jeden Test

Beim Bau dieser Entscheidung lief ein neuer Test über den Datei-Rückfall bis zu einem echten
`open`. Auf dem Bildschirm des Betreibers ging die Test-`.eml` in Thunderbird auf. Der Riegel
hing bis dahin an jeder einzelnen Testdatei. Seitdem gilt in `tests/conftest.py` ein Wächter für
**jeden** Test:

- `subprocess.Popen` startet kein Programm, das ein Fenster öffnet oder ein Mailprogramm
  steuert (`open`, `xdg-open`, `osascript`, `thunderbird`, alles in einem `.app`-Paket …).
- `imaplib.IMAP4` und `smtplib.SMTP` verbinden nicht.
- Kindprozesse erben `FALZMARKE_OEFFNEN=nie`, `FALZMARKE_GESENDET=nie` und
  `FALZMARKE_POSTFACH=nie`.
- Jeder abgefangene Versuch macht den Test beim Abbau rot, auch wenn der Code den Fehler
  geschluckt hat.

`tests/test_waechter.py` ist die Gegenprobe. Die Versuche dort zielen ins Leere: `open` auf eine
Datei, die es nicht gibt, IMAP auf Port 9. Fiele der Wächter aus, scheiterten sie harmlos, und
die Tests würden rot.

## Was gleich bleibt

- **Kein Versand.** Weder `postfach.py` noch `gesendet.py` kennt einen Sende-Befehl. `smtplib`
  wird nirgends importiert.
- ADR 0038, Punkt 5: `subprocess` importiert weiter nur `oeffnen.py`. Der MCP-Dienst lädt weder
  `gesendet` noch `postfach` noch `imaplib` (`tests/test_befehl_email.py`).

## Offen

- Konten, die nicht über den Proxy laufen (etwa Gmail): Dort gilt „nicht geprüft“ und
  `-compose`.
- Der Befund zu `X-Unsent: 1` (oben).

## Nachtrag 04.11.2026 — Frist der Gesendet-Prüfung (#441)

Die Frist für Verbindung und Lesen beträgt seit #441 30 s statt 5 s (`postfach.FRIST_S`).
Anmeldung und LIST am Proxy dauerten am 30.10.2026 einmal 20,6 s, einmal 18,1 s und einmal
3,6 s. Mit 5 s endete die Prüfung an einem gesunden Proxy oft in `GESENDET NICHT GEPRÜFT`.
Einstellbar ist die Frist nicht. Kommt ein Fall, in dem 30 s zu kurz oder zu lang sind, wird sie
es.

**Berichtigt im Nachreview von #491:** Hier stand, ein hängender Proxy halte `--oeffnen` „bis zu
30 s“ auf. Das unterschätzt die Lage. Je Sitzung darf schon der Verbindungsaufbau `frist`
Sekunden warten (`IMAP_KLASSE(…, timeout=frist)` in `postfach.verbinde`), erst danach beginnt das
Budget für die Befehle, noch einmal `frist`. Gesendet-Prüfung (`postfach.FRIST_S`, 30 s) und
Postfach-Entwurf (`oeffnen.FRIST_POSTFACH_S`, 30 s) laufen nacheinander, jede in eigener Sitzung.
Ein hängender Proxy kann `--oeffnen` also im schlimmsten Fall rund 120 s aufhalten. Das ist aus
dem Quelltext abgeleitet, nicht gemessen. Ob der Abholer in siluri-angebote mit seinem
180-s-Takt das verträgt, ist eine eigene Frage.

## Nachtrag 04.11.2026 — Der Absender der gefundenen Mail (#434)

Die Sperre fragte nur, an wen eine Mail im Gesendet-Ordner ging und welchen Betreff und Text sie
trug. Von wem sie kam, prüfte sie nicht. Eingegangene Post, die eine Regel oder eine Hand nach
„Gesendet“ legt, sah damit aus wie eine eigene Sendung: Eine Antwort des Kunden mit Paula in Cc
und demselben Betreffkern ergab `GEÄNDERTE FASSUNG`, und `status` meldete den Entwurf als
`SCHON RAUS`.

**Entscheidung.** Eine Mail im Gesendet-Ordner zählt nur, wenn ihr From eine Identität des
Thunderbird-Profils ist, über **alle Konten** hinweg. Gelesen wird `prefs.js` des Profils, in dem
der Socket der Brücke liegt (`entwurfsbuch.profiladressen`), nicht geraten. Das gilt an drei
Stellen gleich: `gesendet.pruefe` (Sperre bei `email --oeffnen`), `entwurfsbuch.abgleich`
(`status`) und `befund` in der Entwurfsbrücke ab 0.3.9, dort über `browser.accounts.list`.

**Warum alle Identitäten, nicht nur die des Kontos.** Die Zählung zeigte, dass der Konto-Maßstab
echte Sendungen übergangen hätte. Gemessen am 04.11.2026, 13:03 UTC, nur lesend über den Proxy,
die letzten 90 Tage, höchstens 3000 Mails je Ordner:

| Konto | Mails in „Gesendet“ | davon From ≠ Konto | woher |
|---|---|---|---|
| joe@ | 370 | 7 | order@ (Kalendermails) |
| servus@ | 171 | 0 | |
| order@ | 3000 (gekappt, 3409 im Fenster) | 651 | 406 buchhaltung@, 245 info@: Odoo verschickt über das Postfach von order@ |
| info@ | 234 | 0 | |
| buchhaltung@ | 450 | 0 | |
| drei weitere Konten | 209 | 1 | eine eingegangene Mail von außen |

Mails ohne From: keine. Das Gmail-Konto läuft nicht über den Proxy und blieb ungezählt. Von 659
Mails mit fremdem From kamen 658 von einer Identität desselben Profils. Ein Filter am Konto hätte
sie alle als eingegangen übergangen, darunter 651 Odoo-Sendungen an Kunden. Der Maßstab „alle
Identitäten des Profils“ übergeht genau die eine echte eingegangene Mail.

**Wo der Filter nachgibt.** Ohne From oder ohne lesbare Identitäten zählt die Mail wie bisher.
Die übersehene eigene Sendung ist der teure Irrtum, die übersehene fremde kostet eine Rückfrage.
`status` nennt den Fall: `HINWEIS  Identitäten des Profils nicht gelesen (…)` mit der Zahl der
Mails, die einen anderen Absender tragen und trotzdem zählen. Die OK-Zeilen beider Befehle
nennen, wie viele Mails übergangen wurden, `status --json` im Feld `fremde`.

**Restrisiko.** Eine Mail, die über ein anderes Programm von einer Adresse hinausging, die in
diesem Thunderbird keine Identität hat, zählt nicht mehr. Die Messung fand keine. `vergleich.js`
bleibt unverändert; der Absender wird vor dem Vergleich ausgesiebt, in `background.js`.

Gegenproben in `tests/test_gegenbeweis.py`, Abschnitt ADR 0051: Ohne den Filter ergibt die
eingegangene Mail wieder `GEÄNDERTE FASSUNG` beziehungsweise `SCHON RAUS`; die eigene Mail als
Kontrolle sperrt vorher wie nachher. Für das Add-on steht die Sabotage in
`tests/test_entwurfsbruecke_hintergrund.py`.
