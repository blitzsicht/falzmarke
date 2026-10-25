# 0052 — Die Entwurfsbrücke: Thunderbird öffnet den Postfach-Entwurf

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:** [0051](0051-gesendet-sperre-und-postfach-entwurf.md),
[0049](0049-entwurf-in-thunderbird.md) · **Hält:** [0038](0038-oeffnen-ist-kein-versand.md), Punkt 5

## Anlass

Seit ADR 0051 legt `email --oeffnen` den Entwurf als fertige Nachricht in den Ordner „Entwürfe“
des Absenders. Ein Fenster geht dabei nicht auf. Am 25.10.2026 lagen vier solche Entwürfe bereit,
und der Betreiber schrieb: „Ich konnte die Entwürfe in Thunderbird nicht öffnen. Bitte klick sie
selbst an.“ Es war nicht das erste Mal. Eine Sitzung kann in Thunderbird nicht klicken, und
sie soll es auch nicht: Ein Tastendruck, der ins falsche Fenster geht, beantwortet womöglich
eine Rückfrage, die der Betreiber gerade liest.

Die Wege, die es schon gab, öffnen alle etwas anderes als den liegenden Entwurf:

| Weg | Was aufgeht | Was nach dem Senden übrig bleibt |
|---|---|---|
| `thunderbird -compose` (ADR 0049) | eine neue Nachricht mit demselben Inhalt | der Entwurf im Ordner, also zwei |
| die `.eml` öffnen, auch mit `X-Unsent: 1` | eine Kopie | der Entwurf im Ordner |
| „Entwurf bearbeiten“ im Ordner | der Entwurf selbst | nichts, Thunderbird räumt ihn weg |

Nur der dritte Weg lässt keinen zweiten Entwurf zurück, und ein zweiter Entwurf war der Anfang
des Doppelversands, der ADR 0051 auslöste. Von außen erreichbar ist dieser Weg aber nicht: Die
Befehlszeile kennt nur `-compose` und das Öffnen einer Datei.

## Entscheidung

Ein kleines Thunderbird-Add-on unter `thunderbird/entwurfsbruecke/` öffnet den Entwurf auf
Zuruf so, wie „Entwurf bearbeiten“ es tut. falzmarke ruft es, sobald der Entwurf im Postfach
liegt, und sagt, ob das Fenster steht.

1. **Eine Zeile hin, eine zurück.** Das Add-on lauscht auf `127.0.0.1:1994` (Einstellung
   `falzmarke.entwurfsbruecke.port`, auf der falzmarke-Seite `FALZMARKE_BRUECKE_PORT`). Eine
   Anfrage ist eine Zeile JSON in ASCII, die Antwort auch. Eine Zeile, die nicht mit `{` beginnt,
   wird abgewiesen: Eine Webseite kann den Browser an `localhost` schicken lassen, ihre erste
   Zeile ist aber immer `GET …` oder `POST …`.
2. **Vier Befehle, keiner sendet.** `ping`, `entwurf_oeffnen {konto, uid}`, `fenster` (welche
   Verfassen-Fenster offen sind) und `protokoll` (die letzten Vorgänge, zur Fehlersuche). Geöffnet
   wird mit `OpenComposeWindow(…, Ci.nsIMsgCompType.Draft, …)` auf der Nachricht im
   Entwürfe-Ordner, nach `updateFolderAsync`, wenn der Kopf noch nicht lokal liegt.
   `tests/test_entwurfsbruecke.py` prüft am Quelltext, dass kein Aufruf zum Senden, Löschen,
   Verschieben oder Flaggen darin steht, mit Gegenprobe. Das Manifest verlangt keine Berechtigung.
3. **Was das Add-on zurückmeldet, ist gesehen, nicht angenommen.** Nach dem Öffnen wartet es bis
   zu 20 s auf das Fenster und liest dessen Betreff. `geoeffnet` und `schon_offen` heißen: das
   Fenster steht, mit diesem Entwurf. `ungewiss` heißt: angestoßen, kein Fenster gesehen.
   `fenster_ohne_entwurf` heißt: ein Fenster, aber leer.
4. **Ungewiss wird nie wiederholt.** `falzmarke.bruecke.entwurf_oeffnen()` wirft nicht; ein
   fehlendes Fenster ist ein Hinweis, der Entwurf liegt ja im Ordner. Ist die Lage ungewiss, ruft
   niemand ein zweites Mal, denn das öffnete womöglich ein zweites Fenster. Die Zeile dafür lautet
   `HINWEIS  Fenster ungewiss: … Erst in Thunderbird nachsehen, nicht noch einmal öffnen.`
5. **Liegt der Entwurf schon, wird er geöffnet.** Meldet ADR 0051 `ENTWURF LIEGT SCHON`, öffnet
   die Brücke den vorhandenen statt nichts zu tun.
6. **`entwurf-oeffnen` für später.** Der Befehl listet die Entwürfe eines Absenders oder öffnet
   einen nach `--betreff` oder `--uid`. Passen mehrere, öffnet er keinen. Die UID stammt aus dem
   Ordner, den falzmarke auf dem Server liest; das Add-on öffnet aus dem Entwürfe-Ordner der
   Identität. Beide sind nur dann sicher derselbe, wenn das Profil genau einen im eigenen Konto
   nennt. Fällt falzmarke auf das Kennzeichen `\Drafts` des Servers zurück (kein Profil, ein
   Ordner in einem anderen Konto, zwei Identitäten mit verschiedenen Ordnern), öffnet der Befehl
   nichts.

### Was ADR 0038, Punkt 5 dazu sagt

`bruecke.py` startet kein Programm und importiert weder `subprocess` noch `imaplib`; es öffnet
eine Verbindung zu einem Programm, das schon läuft. `oeffnen.py` und `cli.py` holen es erst,
wenn ein Fenster aufgehen soll. Der MCP-Dienst lädt es nicht, `tests/test_befehl_email.py` misst
das im Kindprozess. Im Testlauf blockt `tests/conftest.py` jede Verbindung zum Brückenport.

### Was hingenommen wird

Jeder Prozess auf dem Rechner kann einen Entwurf öffnen lassen; ein Kennwort gibt es nicht.
Öffnen verschickt nichts und ändert am Entwurf nichts, solange niemand im Fenster speichert. Ein
Kennwort müsste irgendwo liegen, wo falzmarke es liest, und dort läge es für denselben Prozess.

## Messung 25.10.2026

- Add-on 0.1.0 in Thunderbird 158.0.1, installiert vom Betreiber. Ein Postfach-Entwurf an einen
  Dienstleister ging in **1,2 s** als Verfassen-Fenster auf: Von, An, Blindkopie, Tabelle und
  Signatur einmal (Bildschirmfoto). Der Kopf lag noch nicht lokal und wurde nachgeladen.
- Der Betreiber sandte ihn um 13:14. Per IMAP, nur lesend: Im Gesendet-Ordner steht er genau
  einmal, in „Entwürfe“ ist er weg. Die gesendete Mail trägt eine neue `Message-ID`, und
  `X-Falzmarke-Fassung` fehlt wie in ADR 0051 gemessen. Entwurf und gesendete Mail lassen sich
  deshalb nur im Add-on sicher einander zuordnen.
- **Fehler in 0.1.0:** Etwa 4 von 10 Anfragen kamen ohne Antwort zurück. `transport.close()`
  direkt nach dem Schreiben verwarf, was noch im Puffer lag. 0.1.1 schließt nur den Ausgang und
  den Transport erst, wenn die Gegenseite auflegt oder nach 3 s. Nachmessung mit 0.1.1 steht aus.
- **Offen:** Bei einem zweiten Konto ging ein leeres Fenster „(kein Betreff)“ auf, die Ursache ist
  nicht gefunden. Dafür gibt es in 0.1.1 `fenster` und `protokoll`, und `fenster_ohne_entwurf`
  meldet den Fall, statt `geoeffnet` zu behaupten.

## Was folgt

Das Add-on sieht als Einziges, ob ein Entwurf gesendet, verworfen oder geändert wurde. Eine
Rückmeldung darüber und eine Warnung vor dem zweiten Senden derselben Mail sind die nächsten
Schritte; senden wird das Add-on auch dann nicht. Beides beschreibt
[ADR 0053](0053-entwurfsbuch-status-und-sperre.md).
