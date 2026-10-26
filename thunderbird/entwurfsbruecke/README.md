# Entwurfsbrücke

Ein Thunderbird-Add-on mit drei Aufgaben:

- Es öffnet einen Entwurf aus dem Ordner „Entwürfe“, wenn falzmarke darum bittet, so wie
  „Entwurf bearbeiten“. Nach dem Senden räumt Thunderbird den Entwurf dann selbst weg
  ([ADR 0054](../../docs/entscheidungen/0054-entwurfsbruecke-in-thunderbird.md)).
- Es hält im Tagebuch fest, was aus jedem Verfassen-Fenster wurde. `falzmarke status` liest es.
- Es fragt nach, bevor dieselbe Mail ein zweites Mal hinausgeht
  ([ADR 0055](../../docs/entscheidungen/0055-entwurfsbuch-status-und-sperre.md)).

Ein Senden anhalten kann es, auslösen nicht. Löschen, verschieben und Kennzeichen setzen kann es
auch nicht, und `tests/test_entwurfsbruecke.py` hält das an Manifest und Quelltext fest.

## Installieren

Die `.xpi` hängt an jedem Release, mit Prüfsumme und Herkunftsbeleg. Anleitung für Installieren,
Prüfen und Updates: [docs/entwurfsbruecke.md](../../docs/entwurfsbruecke.md). Selbst packen:

```bash
python3 scripts/xpi_packen.py          # schreibt dist/entwurfsbruecke-<fassung>.xpi
```

In Thunderbird: Menü → Add-ons und Themes → Zahnrad → „Add-on aus Datei installieren…“ → die
`.xpi` wählen. Danach holt Thunderbird neue Fassungen selbst: `update_url` im Manifest zeigt auf
`updates.json` am jüngsten Release, `scripts/xpi_updates.py` schreibt die Datei im Release-Lauf.
0.3.0 ist die erste Fassung mit `update_url`: Wer 0.2.x hat, installiert sie einmal von Hand.

Ab 0.2.0 fragt Thunderbird beim Installieren nach drei Rechten: `compose` für das
Verfassen-Fenster und den Moment vor dem Senden, `messagesRead` und `accountsRead`, um in
„Gesendet“ nachzusehen. Thunderbird beschreibt `compose` weiter, als das Add-on es nutzt: Es liest
das Fenster und hält höchstens an. Mehr verlangt das Add-on nicht.

Zweimal gepackt gibt dieselben Bytes. Welche Fassung in Thunderbird antwortet, steht unter der
Liste der Entwürfe:

```bash
falzmarke entwurf-oeffnen --absender ich@example.de      # braucht den IMAP-Proxy
```

```
OK  2 Entwürfe in „Entwürfe“ von ich@example.de
    UID 4711  25.10.2026 12:20  Nachtrag  → du@example.org
    …
OK  Entwurfsbrücke 0.3.3 in Thunderbird 158.0.1
```

## Das Tagebuch

`entwurfsbruecke-tagebuch.jsonl` im Profilordner von Thunderbird, eine Zeile JSON je Ereignis:

```
{"art": "gesendet", "ursprung": {"typ": "draft", "konto": "ich@example.de", "betreff": "Nachtrag",
 "uid": 4711, "fassung": "…"}, "identitaet": "ich@example.de", "an": ["paula@example.org"],
 "kopie": [], "blindkopie": ["archiv@example.de"], "anhaenge": ["Lageplan.pdf"],
 "modus": "sendNow", "message_id": "…", "zeit": "…", "version": "0.3.3"}
```

Ab 0.3.0 stehen bei `gesendet` Absender, Empfänger samt Bcc und die Namen der Anhänge. Das
Tagebuch enthält damit Adressen; es liegt nur lokal im Profil. Über `message_id` und
`ursprung.fassung` erkennen falzmarke und die Sperre eine gesendete Mail als ihren Entwurf,
auch wenn der Text geändert wurde: Thunderbird übernimmt `X-Falzmarke-Fassung` nicht in die
gesendete Mail (ADR 0056).

| `art` | heißt |
|---|---|
| `geoeffnet` | ein Verfassen-Fenster ging auf |
| `gespeichert` | als Entwurf gespeichert, mit der neuen UID |
| `gesendet` / `senden_fehlgeschlagen` | Thunderbird hat gesendet / es scheiterte |
| `geschlossen` | ohne Senden zu |
| `gesperrt` / `trotzdem` | die Sperre hielt an / „Trotzdem senden“ |
| `pruefung_fehlgeschlagen` | die Sperre konnte nicht prüfen, die Mail ging hinaus |

Das Tagebuch schreibt nur das Add-on. Gelesen wird es von `falzmarke status`, auch bei
geschlossenem Thunderbird.

## Die Sperre

Vor dem Senden sieht das Add-on in „Gesendet“ des Kontos nach. Es fragt nach, wenn

- derselbe Text in den letzten 14 Tagen schon an einen dieser Empfänger ging, oder
- bei einem Entwurf oder einer neuen Mail derselbe Betreff mit anderem Text in den letzten 24
  Stunden. Antworten teilen ihren Betreff und fallen nicht darunter.

Vorgewählt ist „Nicht senden“; Escape und Schließen zählen ebenso. Verglichen wird wie in
falzmarke (`vergleich.js` ist das Gegenstück zu `gesendet.py`). Kann das Add-on nicht prüfen,
geht die Mail hinaus, und das Tagebuch hält den Grund fest.

## Wie falzmarke es ruft

Eine Zeile JSON an den Socket `bruecke.sock` im Profilordner, eine zurück:

```
{"befehl": "entwurf_oeffnen", "konto": "ich@example.de", "uid": 4711}
{"ok": true, "zustand": "geoeffnet", "betreff": "Nachtrag", ...}
```

| Befehl | Antwort |
|---|---|
| `ping` | Name, Fassung, Thunderbird-Version |
| `entwurf_oeffnen` | `geoeffnet`, `schon_offen`, `ungewiss`, `fenster_ohne_entwurf` oder ein Fehler |
| `fenster` | die offenen Verfassen-Fenster mit Betreff und Entwurf; ab 0.3.0 auch Absender, An, Cc, Bcc, Anhänge, Text (bis 20.000 Zeichen) |
| `protokoll` | die letzten 60 Vorgänge |

Der Socket heißt `bruecke.sock` und liegt im Profilordner von Thunderbird; das Add-on legt ihn
mit Rechten 0600 an und räumt ihn beim Beenden weg. Nur das Konto, das Thunderbird fährt, kommt
daran — bis 0.3.0 lief der Zuruf über 127.0.0.1:1994, und dort kam jeder Prozess jedes Kontos
heran (ADR 0059). Einen anderen Pfad nimmt falzmarke über `FALZMARKE_BRUECKE_SOCKET`; der Name
bleibt kurz, weil ein Unix-Socketpfad auf macOS nur 104 Byte fassen darf.
`FALZMARKE_BRUECKE=nie` schaltet den Zuruf ab.

Eine Verbindung, die binnen zehn Sekunden keine vollständige Zeile schickt, wird getrennt; mehr
als acht gleichzeitig nimmt das Add-on nicht an. falzmarke stellt immer genau eine.
