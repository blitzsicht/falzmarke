# 0056 — Die Entwurfsbrücke meldet Empfänger, die Fassung kommt aus dem Tagebuch

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:** [0055](0055-entwurfsbuch-status-und-sperre.md),
[0054](0054-entwurfsbruecke-in-thunderbird.md) · **Hält:** [0038](0038-oeffnen-ist-kein-versand.md), Punkt 5

## Anlass

Am 25.10.2026 ging eine Mail mit Bcc an das eigene Archiv hinaus. Ob An, Bcc und Text stimmten,
ließ sich mit der Entwurfsbrücke 0.2.1 nicht nachsehen: `fenster` nannte nur Titel, Betreff und
Entwurf, das Tagebuch bei `gesendet` nur Modus und `Message-ID`. Die Prüfung lief von Hand, per
IMAP im Gesendet-Ordner und über die Archivkopie (#407).

Dabei fiel ein zweiter Befund auf. `X-Falzmarke-Fassung` steht im Entwurf, fehlt aber in der
gesendeten Mail (gemessen in Gesendet und in der Archivkopie). Der Fassungsvergleich in
`gesendet.py`, in `status` und in der Sperre griff deshalb nie. Ändert der Mensch den Text in
Thunderbird, erkannte keiner der drei die gesendete Mail als dieselbe.

## Entscheidung

1. **`fenster` meldet, was das Fenster hinausschicken würde.** Das Add-on ruft dafür
   `GetComposeDetails()` im Fenster auf. Das ist dieselbe Funktion, die Thunderbirds eigene
   `compose.getComposeDetails` nutzt (`ext-compose.js`). Sie überträgt den Fensterinhalt in die
   Felder, ohne etwas zu ändern. Neu sind `identitaet`, `an`, `kopie`, `blindkopie`, `anhaenge`
   (Namen) und `text` (Klartext, höchstens 20.000 Zeichen, dann `text_gekuerzt`). Scheitert
   das Lesen, steht `live: false` mit `fehler` da. Das gilt auch in der ersten Sekunde nach
   dem Öffnen, solange der Editor noch lädt (gemessen 25.10.2026).
   Ob das Fenster ungespeicherte Änderungen hat, meldet `fenster` nicht. `gContentChanged`
   setzt Thunderbird beim Laden selbst (`LoadIdentity`, auch ohne Eingabe), in der Live-Probe
   stand der Wert bei einem unberührten Fenster einmal auf wahr und einmal auf falsch.
   `bruecke.MAX_ANTWORT` steigt dafür von 64 KiB auf 1 MiB.
2. **`gesendet` im Tagebuch trägt Absender, Empfänger und Anhänge.** Das Add-on liest sie in
   `onBeforeSend` aus den `details` und aus `compose.listAttachments`. Scheitert das, steht
   `versand_fehler` oder `anhaenge_fehler` im Eintrag, und gesendet wird trotzdem.
3. **`status` zeigt beides.** Unter einem offenen Entwurf steht eine Zeile mit Absender, An, Cc,
   Bcc, Anhängen und „Text wie angelegt“ oder „Text geändert“ (Kern bis zur Grußformel, wie in
   `gesendet.py`; die Konto-Signatur zählt nicht). Unter einem gesendeten steht, wohin die Mail
   ging, und „Empfänger wie angelegt“ oder `ABWEICHEND vom Entwurf: +x −y`. Ein fehlendes Bcc
   erscheint dort als `−adresse`. Dafür schreibt `email --oeffnen` das Bcc ins Entwurfsbuch.
   Einträge von vorher haben keines; bei ihnen zählt das Bcc auf keiner Seite. Dasselbe steht
   in `--json`.
4. **Die Fassung wird nicht in die ausgehende Mail zurückgeschrieben. Sie kommt aus dem
   Tagebuch.** Jeder Eintrag `gesendet` trägt `ursprung.fassung` aus dem Entwurf und die
   `Message-ID` der gesendeten Mail. `entwurfsbuch.fassungen()` macht daraus eine Zuordnung
   Message-ID → Fassung (ohne `<>` und Leerraum, in Python und JS gleich, `kennung()`). Fehlt
   die Kopfzeile, schlagen drei Stellen dort nach: `gesendet.pruefe_datei` vor dem Entwurf,
   `status` und die Sperre im Add-on (neue Experiment-Funktion `fassungen()`, Einträge der
   letzten 14 Tage).

### Warum nicht zurückschreiben

Thunderbird lässt sich die Kopfzeile wieder unterschieben: `onBeforeSend` darf `details`
zurückgeben, so wie `setComposeDetails`. Gerade das steht seit ADR 0054 auf der Verbotsliste:
Das Add-on liest das Fenster, es ändert es nicht. Ein Rückschreiben über die Rückgabe von
`onBeforeSend` wäre derselbe Eingriff durch die Hintertür. Dazu kommt, dass `customHeaders`
beim Setzen alle übrigen X-Kopfzeilen löscht (`ext-compose.js`).

Alle drei Stellen, die die Fassung brauchen, laufen auf dem Rechner, auf dem das
Thunderbird-Profil liegt. Für sie ist das Tagebuch so gut wie die Kopfzeile.
`tests/test_entwurfsbruecke.py` prüft das am Quelltext: `setComposeDetails`,
`SetComposeDetails` und `CompFields2Recipients` sind verboten, und kein `return { … details … }`
steht im Add-on, je mit Gegenprobe.

### Was hingenommen wird

- In Gesendet und in einer Archivkopie steht die Fassung weiterhin nicht. Wer die Mail auf
  einem anderen Rechner prüft, hat nur Empfänger, Betreff und Text.
- Das Tagebuch enthält jetzt Empfängeradressen und Dateinamen. Es liegt nur lokal im
  Thunderbird-Profil, wie das Entwurfsbuch, das den ganzen Text enthält.
- Ein Tagebuch, das sich nicht lesen lässt, kostet nur den Rückgriff: Die Sperre prüft dann
  ohne ihn, `status` und `pruefe_datei` ebenso.

## Belege

Thunderbird 158.0.1, `omni.ja`: `MsgComposeCommands.js` (`GetComposeDetails`),
`ext-compose.js` (Klartext aus dem Editor, `customHeaders`). Gemessen am 25.10.2026: Die
`message_id` im Tagebuch-Eintrag `gesendet` ist die der Mail in Gesendet; ein zweiter Eintrag
hat eine andere `message_id` und eine andere Fassung, die Zuordnung trennt also.
