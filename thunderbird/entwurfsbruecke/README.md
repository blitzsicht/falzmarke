# Entwurfsbrücke

Ein Thunderbird-Add-on, das einen Entwurf aus dem Ordner „Entwürfe“ öffnet, wenn falzmarke
darum bittet, so wie „Entwurf bearbeiten“. Nach dem Senden räumt Thunderbird den Entwurf dann
selbst weg. Warum es das gibt: [ADR 0052](../../docs/entscheidungen/0052-entwurfsbruecke-in-thunderbird.md).

Es kann nur öffnen. Senden, löschen, verschieben und Kennzeichen setzen kann es nicht, und
`tests/test_entwurfsbruecke.py` hält das am Quelltext fest.

## Installieren

```bash
python3 scripts/xpi_packen.py          # schreibt dist/entwurfsbruecke-<fassung>.xpi
```

In Thunderbird: Menü → Add-ons und Themes → Zahnrad → „Add-on aus Datei installieren…“ → die
`.xpi` wählen. Eine neue Fassung wird genauso installiert und ersetzt die alte.

Zweimal gepackt gibt dieselben Bytes. Welche Fassung in Thunderbird antwortet, steht unter der
Liste der Entwürfe:

```bash
falzmarke entwurf-oeffnen --absender ich@example.de      # braucht den IMAP-Proxy
```

```
OK  2 Entwürfe in „Entwürfe“ von ich@example.de
    UID 4711  25.10.2026 12:20  Nachtrag  → du@example.org
    …
OK  Entwurfsbrücke 0.1.1 in Thunderbird 158.0.1
```

## Wie falzmarke es ruft

Eine Zeile JSON an `127.0.0.1:1994`, eine zurück:

```
{"befehl": "entwurf_oeffnen", "konto": "ich@example.de", "uid": 4711}
{"ok": true, "zustand": "geoeffnet", "betreff": "Nachtrag", ...}
```

| Befehl | Antwort |
|---|---|
| `ping` | Name, Fassung, Thunderbird-Version |
| `entwurf_oeffnen` | `geoeffnet`, `schon_offen`, `ungewiss`, `fenster_ohne_entwurf` oder ein Fehler |
| `fenster` | die offenen Verfassen-Fenster mit Betreff und Entwurf |
| `protokoll` | die letzten 60 Vorgänge |

Der Port lässt sich in Thunderbird über die Einstellung `falzmarke.entwurfsbruecke.port` ändern
(Einstellungen → Allgemein → Konfiguration bearbeiten), auf der falzmarke-Seite über
`FALZMARKE_BRUECKE_PORT`. `FALZMARKE_BRUECKE=nie` schaltet den Zuruf ab.
