# 0049 — Der Entwurf entsteht in Thunderbird

**Datum:** 13.10.2026 · **Status:** angenommen · **Ergänzt:** [0038](0038-oeffnen-ist-kein-versand.md) · **Betrifft:** [#305](https://github.com/blitzsicht/falzmarke/issues/305)

## Worum es geht

`--oeffnen` legte den Entwurf per AppleScript in Outlook für Mac an. Der Weg ist gemessen
und bleibt es — nur trägt er auf dem Rechner, für den er gebaut wurde, nicht mehr: Outlook
ist dort installiert, aber ohne Lizenz, und das neue Outlook zeigt der Programmsteuerung
kein einziges Konto (gemessen am 13.09.2026, #305). Der Absender war damit nie verlässlich,
und die Warnzeile `ABSENDER PRÜFEN` stand unter jeder Mail.

Thunderbird nimmt einen Entwurf über seine Befehlszeile an. Gemessen am 13.10.2026 mit
Thunderbird 154.0 auf macOS:

```
thunderbird -compose "from=…,to=…,cc=…,bcc=…,subject='Betreff, mit Komma und äöüß',format=html,body='<p>…</p>',attachment='/pfad/a.pdf,/pfad/b.txt'"
```

`from=` wählt die Identität — der Absender stimmt. Einfache Anführungszeichen schützen Kommas
im Wert. `format=html` mit `body=` kommt formatiert an, Umlaute und € richtig. Mehrere
Anhänge nur als **ein** Wert; ein zweiter `attachment=`-Schlüssel wird verworfen, ohne
Meldung, mit Exit 0. `message=<eml>` ist kein Import — der Rohtext landet im Textkörper.
Läuft Thunderbird, reicht das Binary den Auftrag an die laufende Instanz weiter und kehrt
sofort zurück; ohne eingerichtetes Konto öffnet sich der Konto-Assistent.

## Entscheidung 1: Thunderbird ist die Vorgabe, Outlook kommt nur auf Wahl

`--oeffnen` nimmt Thunderbird, wenn es installiert ist. Fehlt es, wird die `.eml`
übergeben wie bisher — **nicht** Outlook. Outlook braucht `--programm outlook`.

Der naheliegende andere Weg wäre eine Reihenfolge: Thunderbird, sonst Outlook. Er scheitert
an einem Wort: „fehlt“. Outlook *fehlt* auf dem Rechner des Betreibers nie — es ist
installiert, es ist nur unbrauchbar, und das sieht kein `NSWorkspace`. Jede Reihenfolge
landete dort, sobald Thunderbird einmal nicht da ist, und der Entwurf stünde wieder auf dem
falschen Konto. Eine Wahl ist ehrlicher als eine Vermutung.

`--programm` schließt `--oeffnen` ein: Wer ein Programm nennt, will den Entwurf.

## Entscheidung 2: Ein Aufruf, und die Prüfung steht davor

Beim Outlook-Weg zählt das Skript am fertigen Objekt nach — Empfänger, Kopien, Blindkopien,
Anhänge — und Python hält die Zählung gegen die Vorgabe. Thunderbird meldet nichts zurück:
keine Kennung, keine Zählung. **Exit 0 heißt „angenommen“, nicht „Fenster offen“.**

Was sich prüfen lässt, liegt deshalb auf dieser Seite der Grenze: `compose_zerlegen` liest
die Zeile so, wie Thunderbird sie liest — Anführungszeichen schützen Kommas, der erste
gleiche Schlüssel gewinnt, unzitierte Werte werden wie eine URL dekodiert —, und
`_compose_stimmt` hält das Gelesene gegen die Felder, **bevor** ein Prozess startet. Ein
Anhang, der in einem zweiten Schlüssel verschwände, fällt dort auf;
`tests/test_gegenbeweis.py` sabotiert genau diese Stelle.

Jeder Wert steht in einfachen Anführungszeichen, nicht nur der mit Komma: Einen
unzitierten Wert liest Thunderbird wie eine URL, und „100%ig“ bliebe nicht, was es ist.

Der Befehl sagt, was er nicht weiß: Nach `OK  Entwurf angelegt: Thunderbird` folgt die
Zeile, dass nichts nachgezählt ist und Empfänger, Anhänge und Absender im Fenster zu
prüfen sind. Die Outlook-Zeile `ABSENDER PRÜFEN` erscheint hier nicht — sie riete, in
einem Programm „Von“ umzustellen, das gar nicht offen ist.

## Grenzen

- **Das einfache Anführungszeichen.** Ob Thunderbird ein `'` *im* Wert übersteht, ist nicht
  gemessen; sicher ist, dass `'` vor einem Komma den Wert schließt. In Betreff, Rumpf und
  Dateinamen wird es zum Apostroph ’ — in deutschem Text ohnehin das richtige Zeichen, und
  falzmarkes HTML-Emitter setzt selbst keins (0 von 68 Anführungszeichen in
  `email-mahnung`). Adressen bleiben unverändert: Dort wäre `'` Teil der Adresse, und es
  kann nach RFC 5322 nie vor dem Komma stehen.
- **Ein Komma im Dateinamen eines Anhangs** ist ein Fehler, kein Rätselraten: Thunderbird
  trennt die Anhänge am Komma, Anführungszeichen helfen innerhalb des Werts nicht. Der
  Befehl nennt den Pfad, fällt auf die Datei zurück und behält seinen Exit-Code (0038, 4).
- **Thunderbird muss laufen.** Läuft es nicht, würde das Binary selbst zu Thunderbird und
  käme erst beim Beenden zurück — `subprocess.run` erschlüge es nach der Frist samt Fenster.
  `pgrep` entscheidet; läuft es nicht, startet `open -a Thunderbird.app --args -compose …`
  das Programm mit dem Auftrag. Gemessen ist nur die laufende Instanz. Der Start ist
  deshalb `ungewiss`: Der Befehl schiebt keine Datei nach und sagt, dass niemand das Fenster
  gesehen hat.
- **Die Anhänge bleiben liegen.** Thunderbird merkt sich Pfade und liest die Datei erst beim
  Senden oder Speichern. Sie liegen in einem Ordner `falzmarke-entwurf-…` im
  Temporärverzeichnis, den der Befehl nennt und nicht abräumt; das System räumt ihn
  irgendwann. Ein Entwurf, der tagelang offen liegt, kann die Anlage verlieren — was
  Thunderbird dann meldet, ist nicht gemessen.
- **Mehrere Empfänger** gehen als ein Wert mit Komma (`to='a@…,b@…'`), wie eine Kopfzeile.
  Am 13.10.2026 wurde ein Empfänger gemessen; die Syntax ist dieselbe, der Fall mit zweien
  nicht eigens gesehen.
- **Nur macOS.** Die Befehlszeile ist unter Linux dieselbe und dort nicht gemessen; der
  Entwurfsweg bleibt auf macOS begrenzt, wie bisher (0038, Nachtrag).
- **Gesucht wird unter `/Applications` und im `PATH`.** Ein Thunderbird woanders wird nicht
  gefunden — nicht über `NSWorkspace` wie Outlook, weil das Binary gebraucht wird und nicht
  das Bündel.
- **Was Thunderbird selbst hinzufügt**, steht in keiner Prüfung: die Signatur der Identität
  (erwartet, nicht gemessen) und kein `In-Reply-To` — `-compose` kennt dafür keinen
  Schlüssel; der Entwurf beginnt einen neuen Faden wie beim Outlook-Weg (#286).

## Was bleibt

**[0038](0038-oeffnen-ist-kein-versand.md) gilt unverändert: Entwurf ja, Senden nie.**
`-compose` setzt nur die acht Schlüssel aus `COMPOSE_SCHLUESSEL`; einen, der sendet, gibt es
dort nicht, und `tests/test_oeffnen.py` hält das fest. Opt-in, erst nach der Prüfung, kein
anderer Exit-Code bei Fehlschlag, genau ein Modul startet fremde Programme — alle vier
Punkte stehen.

Der Outlook-Weg bleibt im Code, gemessen und auf Wahl erreichbar. Er wird nicht entfernt,
solange er irgendwo trägt; was sich ändert, ist nur, dass niemand mehr ungefragt dort landet.
