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

---

## Nachtrag 13.10.2026, 13:15 — zwei Befunde am echten Entwurf

Gemessen mit echten Entwürfen in Thunderbird 154.

**1. Das Logo der Signatur fehlte** — ein kaputtes Bild mit dem Alt-Text an seiner Stelle.
Der Rumpf verweist mit `<img src="cid:…">` auf einen `multipart/related`-Teil der `.eml`, und
`-compose body=` übergibt nur den Rumpf; diese Teile gibt es auf dem Weg nicht. Seither
ersetzt `oeffnen.eingebettet` jeden `cid:`-Verweis durch eine `data:<mime>;base64,…`-URI aus
den Bytes des Teils — `eml.entwurfsfelder` liefert sie aus der geschriebenen Datei, nichts
wird neu von Platte gelesen. Thunderbird zeigt Data-URIs im Editor; dass es sie beim Senden in
Anhänge wandelt, ist erwartet, nicht gemessen. Vor dem Aufruf prüft `_eingebettet_stimmt`,
dass kein `cid:` übrig ist und jedes Bild mit seinem Typ im Rumpf steht;
`tests/test_gegenbeweis.py` sabotiert die Umwandlung und den Typ.

Die Grenze dazu ist die **Länge des Befehls**: `getconf ARG_MAX` meldet 1 048 576 Byte, und
das Logo fährt jetzt in der Zeile mit. Über `COMPOSE_GRENZE_BYTE` (900 000) wird nicht
aufgerufen; der Grund nennt die gemessene Länge und die Grenze, und der Befehl fällt auf die
Datei zurück. Der Systemfehler hieße sonst nur „Argument list too long“.

**2. Rot gepunktete Hilfslinien** um die rahmenlosen Tabellen — Umschlag und Signatur. Das ist
die Anzeige des Editors für Tabellen ohne Rahmen, nicht Teil der gesendeten Nachricht:
**erwartet, ungemessen** — wer es belegen will, sendet an sich selbst und sieht nach. Nichts zu
bauen.

> **Überholt am 15.10.2026 durch [0050](0050-signatur-aus-thunderbird.md):** Trägt die Identität
> eine Signatur, lässt der Entwurf die aus dem Profil weg. Der folgende Absatz bleibt als Stand
> vom 13.10.2026 stehen.

**Kontosignaturen in Thunderbird leer lassen.** Der Hinweis des Befehls stimmt auch hier:
Thunderbird hängt die Signatur der Identität an, und falzmarke liefert die Signatur aus dem
Profil bereits mit. Wer beides stehen lässt, hat sie zweimal. Die Reparatur ist eine
Einstellung in Thunderbird (Konten-Einstellungen → Identität → Signaturtext leer), einmal
je Identität — nicht ein zweites Profil ohne Signaturblock.

---

## Nachtrag 13.10.2026, zweiter Lauf — Zeilenumbrüche im `body=`-Wert

Gemessen mit echten Entwürfen am Stand `5e93f42` (`email-signatur.md`): Zwischen Grußformel und
Signaturtabelle stand `style="border-collapse: collapse; …">` als sichtbarer Text, der Anfang
des `<table …`-Tags war weg; und über dem ersten Absatz lagen rund zehn Leerzeilen.

**Ursache, eine für beides:** Thunderbird macht aus jedem Zeilenumbruch im `body=`-Wert einen
Zeilenumbruch im Entwurf. Auf unserer Seite war die Zeile intakt — `compose_zerlegen` gab den
Rumpf byte-gleich zurück. Hinter der Grenze zerfiel er: Das Tag der Signaturtabelle geht in der
Datei über zwei Zeilen und wurde an der ersten abgeschnitten, der Rest wurde Text. Die Hülle der
Datei (`<!DOCTYPE>`, `<head>`, drei `<meta>`, `<style>`) ist zehn Zeilen lang und wurde zehn
Leerzeilen. Vor dem Nachtrag zum Logo fiel das nicht auf, weil es zufällig nicht gemessen war.

**Entscheidung:** `rumpf_fuer_compose` übergibt nur den Inhalt von `<body>`, getrimmt, und
macht aus jedem Umbruch samt Einrückung ein Leerzeichen — HTML liest ihn ohnehin so, und der
Emitter setzt kein `<pre>`, in dem ein Umbruch etwas hieße. Der `style` des `<body>` (Schrift,
Größe, Farbe) wandert auf ein umhüllendes `<div>`. Das `<style>` der Hülle mit dem dunklen
Farbschema fällt weg; das tat es im Entwurf vorher schon, nur unsichtbar.

**Prüfmittel vor dem Aufruf:** `_rumpf_stimmt` — kein Leerraum vorn, keine Hülle, kein
Zeilenumbruch (damit auch keine Data-URI mit Umbrüchen), jedes `<tag` kommt beim Parser als
Tag an, kein `attribut="…"` steht als Text. Dazu der Nachbau der Thunderbird-Lesart in den
Tests (`\n` → `<br>`, dann geparst): Er muss am alten Rumpf den gemessenen Fehler zeigen, sonst
belegte der grüne Test nichts. `tests/test_befehl_email.py` fährt die echte Kette mit
`email-signatur.md` und `email-logo.md` bis zur Zeile und liest sie zurück.

**Live geprüft:** `examples/email/email-logo.md` (Profil `email-logo.yaml`, Logo
`assets/mail-logo.png`) am Stand dieses Nachtrags mit `--oeffnen` in Thunderbird 154
geöffnet — Ergebnis im Vorgang, nicht hier: Was dieses Dokument zusagt, ist, dass die Zeile
die drei Prüfungen besteht.
