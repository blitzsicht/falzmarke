# Die E-Mail-Fassung

Ein Schreiben mit `typ: email` im Frontmatter wird keine PDF-Seite, sondern eine `.eml`.
Dieselbe Quelle, dasselbe Profil, dieselbe Signatur wie im Brief — nur ein anderer Träger.
Warum das eine Ausgabe ist und kein Kanal, steht in
[ADR 0034](entscheidungen/0034-email-ist-ausgabe.md).

```bash
falzmarke email nachricht.md --html
```

Geschrieben werden bis zu drei Dateien mit demselben Stamm:

| Datei | Wofür | Wann |
|---|---|---|
| `.eml` | die Nachricht selbst, für das Mailprogramm | immer |
| `.html` | Vorschau zum Ansehen und Kopieren, mit Kopfzeile | mit `--html` |
| `.txt` | der Textteil allein | mit `--txt` |

Die `.html` ist **nicht** der HTML-Teil der Mail: Sie trägt zusätzlich einen Vorschaukopf mit
Empfänger und Betreff. Für Menschen, die eine `.eml` nicht öffnen können, ist sie die Brücke —
Text markieren, ins Mailprogramm einsetzen, fertig.

## Was in der Datei steht

```
multipart/mixed                     ← nur, wenn Anhänge dabei sind
└── multipart/alternative
    ├── text/plain    format=flowed, delsp=yes, quoted-printable
    ├── text/markdown nur mit --mit-quelle
    └── text/html     quoted-printable
└── application/pdf   je Anhang
```

Die Reihenfolge in `multipart/alternative` ist die Rangfolge von schlicht nach reich: Das
Mailprogramm zeigt den letzten Teil, den es darstellen kann. Steht HTML nicht am Ende, sehen
viele Empfänger den Textteil, obwohl beides da ist.

**Der Textteil ist nie base64.** Eine Mail, deren Text als base64 ankommt, ist in jedem
Rohansicht-Fenster unlesbar — und die Rohansicht ist das, was von einer `.eml` als Vorlage übrig
bleibt.

**`format=flowed` nach [RFC 3676](https://www.rfc-editor.org/rfc/rfc3676)**: Weiche Umbrüche tragen ein Leerzeichen am Zeilenende und
dürfen vom Empfängerprogramm neu umbrochen werden; Tabellen und Listenpunkte tragen ihre
Bedeutung in der Form und bleiben fest. Zeilen, die mit einem Leerzeichen beginnen, werden
gestopft (space-stuffing) und beim Lesen wieder entstopft. Geprüft wird das gegen die Umkehrung:
falten, entfalten, muss gleich sein.

## Was fehlt — und warum

| Nicht in der Datei | Grund |
|---|---|
| `Message-ID` | gehört dem Versender. Wer sie beim Erzeugen setzt, vergibt eine Kennung für eine Nachricht, die vielleicht nie abgeschickt wird. |
| ein Versandweg | falzmarke versendet nichts. Es gibt keinen Versandbefehl und keine Option, die sendet. |

`Bcc` steht dagegen in der Datei, wenn `bcc:` im Frontmatter gesetzt ist — aber **nicht** in der
`.html`-Vorschau: Die ist zum Herauskopieren gedacht, und eine sichtbare Zeile „Blindkopie" wäre
das Gegenteil dessen, wofür das Feld da ist. `verify --email` misst beides: dass die Kopfzeile
auswertbar ist und dass keine ihrer Adressen im Text- oder HTML-Teil auftaucht. Ob ein
Mailprogramm die Zeile beim Weiterleiten übernimmt, entscheidet das Programm; der Befehl nennt
die Adresse beim Erzeugen eigens, damit man dort nachsieht.

`Date` stand bis #236 ebenfalls in dieser Tabelle, mit der Begründung, das Datum entstehe beim
Versand. Die trug nur unter der Annahme, das Mailprogramm übernehme die Datei als Entwurf und
setze den Zeitpunkt selbst — und die ist nach dem Protokoll unten falsch. Beim Weiterleiten baut
das Programm den zitierten Kopf aus den Feldern der Quelle; ein fehlendes `Date` erscheint dort
als `Datum: (null), (null)` und geht mit raus. Dazu führt
[RFC 5322](https://www.rfc-editor.org/rfc/rfc5322), Abschnitt 3.6, `orig-date` als Pflichtfeld. **Jede Nachricht trägt es jetzt.** Ist `SOURCE_DATE_EPOCH` gesetzt, gilt dieser
Wert — das ist der Weg zu einem reproduzierbaren Vergleich; sonst der Zeitpunkt der Erzeugung.

## Was ein Mailprogramm daraus macht

Eine `.eml` ist eine **Nachricht**, kein Entwurf. Gemessen am 27.08.2026 in Apple Mail 16.0,
Thunderbird 154.0 und Outlook für Mac 16.112.1: Alle drei öffnen die Datei in einem
**Lesefenster** — mit Antworten und Weiterleiten, ohne Senden-Knopf. Auch die dafür gedachte
Kopfzeile `X-Unsent: 1` ändert daran nichts; ausgerechnet Outlook, aus dessen Umfeld sie stammt,
befolgt sie in dieser Fassung nicht.

Wer aus der Datei eine ausgehende Mail machen will, hat zwei Wege:

- **Weiterleiten** — funktioniert in allen drei Programmen und übernimmt Text, HTML und Anlage.
- **Aus der `.html`-Vorschau kopieren** — dafür ist sie da, samt Vorschaukopf mit Empfänger und
  Betreff.

Das vollständige Protokoll mit Matrix und Gegenprobe:
[`docs/mailprogramme-2026-08-27.md`](mailprogramme-2026-08-27.md).

### Den Entwurf bekommen: `--oeffnen`

```bash
falzmarke email nachricht.md --oeffnen
```

```
OK  geschrieben: nachricht.eml
OK  verify: 25/25 Prüfungen bestanden
OK  Entwurf angelegt: Microsoft Outlook
```

Legt auf macOS einen **Entwurf** im Mailprogramm an — Empfänger, Kopie, **Blindkopie**, Betreff,
den HTML-Rumpf und alle Anhänge. Mit Senden-Knopf; gedrückt wird er von einem Menschen (#263).

**Warum nicht einfach die Datei?** Weil eine `.eml` kein Entwurf ist. Der Befund oben gilt
unverändert: In Apple Mail, Thunderbird und Outlook für Mac erscheint sie als Lesefenster, und
`X-Unsent: 1` ändert daran nachweislich nichts. Wer die Nachricht abschicken will, braucht
deshalb mehr als eine Dateiübergabe.

**Was es zusagt:** Die Nachricht steht als ausgehende Nachricht im Programm, und ihre Anzahl an
Empfängern, Kopien, Blindkopien und Anhängen ist am fertigen Objekt **nachgezählt** — ein Anhang
oder eine Blindkopie, die das Programm stillschweigend fallen ließe, fällt auf.

Die Blindkopie kam erst mit #272 dazu. Bis dahin las der Entwurfsweg nur `To` und `Cc`: Sie stand
in der `.eml`, `verify --email` hatte sie gemessen — und im Entwurfsfenster fehlte sie. Eine
Zeile, die nie da war, vermisst niemand.

**Was es nicht zusagt:**

- **Windows und Linux.** Dort bleibt es bei der Dateiübergabe. Ein Weg über COM ist ungemessen,
  und was ungemessen ist, wird nicht behauptet (#108).
- **Apple Mail.** Der `content` einer ausgehenden Nachricht nimmt dort keinen HTML-Rumpf an.
  Statt eine Nachricht ohne ihre Auszeichnung anzulegen, wird die Datei übergeben.
- **Was das Programm selbst hineinschreibt.** Outlook setzt die **Signatur des Kontos** in den
  Entwurf. Trägt das Profil eine eigene, steht sie zweimal darin — der Befehl sagt das beim
  Anlegen. Messen kann er es nicht: Es geschieht nach seinem letzten Handgriff.

Vier Eigenschaften, die dazugehören:

- **Nur auf Verlangen.** Ohne das Flag passiert nichts — sonst risse eine Serie von dreißig
  Nachrichten dreißig Fenster auf.
- **Erst nach der Prüfung.** Was `verify --email` nicht besteht, wird in kein Fenster gelegt.
- **Der Rückfall ist der alte Weg.** Kein passendes Programm, keine Automations-Berechtigung
  (macOS fragt beim ersten Mal), fremde Plattform: Dann wird die `.eml` übergeben wie vorher.
- **Ein Fehlschlag ist kein Fehler des Befehls.** Er meldet sich auf der Fehlerausgabe, nennt den
  Pfad und lässt den Exit-Code bei 0.

Auf einem Rechner ohne Bildschirm — gesetztes `CI`, unter Linux fehlendes `DISPLAY` — wird gar
nicht erst gestartet. `FALZMARKE_ENTWURF=nie` schaltet **nur den Entwurf** ab und lässt die
Dateiübergabe stehen; `FALZMARKE_OEFFNEN=nie` schaltet beides ab, `=immer` überstimmt die
Erkennung.

**Kein Versand.** Es gibt im Paket keinen Weg, eine Nachricht abzuschicken — auch nicht im
Steuerskript. ADR 0034 gilt unverändert, und ein Test misst es am ganzen Paket.

Die Begründung, wo die Grenze verläuft und warum sie sich am 08.09.2026 um ein Glied verschoben
hat, steht in [ADR 0038](entscheidungen/0038-oeffnen-ist-kein-versand.md).

### Eine fertige Signatur mitbringen

Wer seine Signatur schon hat — gestaltet, in den Mailprogrammen im Einsatz —, muss sie nicht ein
zweites Mal beschreiben:

`email.signatur_html` im Profil zeigt auf eine HTML-Datei **neben dem Profil**, `email.signatur_text`
auf ihre Textfassung. Ist das Feld gesetzt, **ersetzt** diese Signatur die aus dem Profil gebaute.
Sie tritt nicht daneben — zwei Signaturen unter einer Nachricht sind der Fehler, den dieser Weg
abstellt. Aus demselben Grund bleibt `email.logo` dabei unbeachtet: Das Logo steckt schon in der
mitgebrachten Fassung.

Übernommen wird der **Rumpf**, nicht das Dokument. Erzeugte Signaturdateien sind meist
vollständige HTML-Seiten; `<head>` und `<style>` fallen weg, der Stil wandert getrennt heraus und
steht **hinter** dem eigenen Dunkelblock im Kopf der Nachricht. Ein zweiter `<style>` mitten im
Rumpf wäre in mehreren Programmen wirkungslos — Gmail entfernt ihn — und in der eigenen Prüfung
ein Verstoß.

**Geprüft wird trotzdem.** Die Regeln oben gelten für eine fremde Signatur wie für eigenen Satz:
kein Skript, kein externes Stylesheet, kein Zählpixel, keine Layouttabelle ohne
`role="presentation"`, kein Verweis nach außen im Stil. Was durchfällt, wird **abgelehnt** — mit
Fundstelle und dem Namen der Datei, nicht stillschweigend eingesetzt. Der Kanal gibt nicht nach,
damit die Quelle nachbessert. Die Begründung steht im Nachtrag zu
[ADR 0034](entscheidungen/0034-email-ist-ausgabe.md).

Ohne `signatur_text` bleibt der Textteil die Signatur aus den Profilblöcken. Das ist Absicht: Ein
Textteil, der etwas anderes sagt als der HTML-Teil, fällt bei `verify --email` als fehlender
Gleichlaut auf.

Ein Beispiel liegt unter `examples/email/email-signatur.md`, die Signatur dazu in
`examples/email/profiles/signatur/`.

## Grenzen

- **Betreff:** ab 78 Zeichen eine **Warnung**, kein Fehler. Die Zahl stammt aus
  [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322), Abschnitt 2.1.1 — dort steht aber etwas anderes, als hier bis v0.8.1 behauptet wurde: Begrenzt
  ist die **Zeilenlänge** einer Kopfzeile („SHOULD be no more than 78 characters"), und ein
  längerer Betreff wird gefaltet, nicht abgelehnt. Was oberhalb wirklich passiert, ist eine
  Anzeigefrage: Übersichten schneiden ab, und wo genau, ist von Programm zu Programm verschieden.
  Damit ist es Erfahrung und keine Vorschrift — Ebene **Praxis** nach
  [ADR 0035](entscheidungen/0035-vier-ebenen-fuer-email-regeln.md), und Praxis ist nie ein Fehler.
- **Zeilenlänge:** RFC 5322, Abschnitt 2.1.1 erlaubt keine Zeile über 998 Zeichen.
- **Der Umschlag ist eine Tabelle**, keine `div` (Issue #104). Das klassische Outlook rechnet mit
  der Word-Engine und versteht von den beiden Breitenangaben nur das Attribut; beide sagen
  deshalb dasselbe — `width="100%"` und `width: 100%`. Er steht **linksbündig** und **deckelt
  nichts**: Bis Issue #264 trug er `align="center"` bei 600 px, und das hatte zwei sichtbare
  Folgen — die Nachricht saß mittig im Fenster, während die Signatur, die das Mailprogramm
  darunter anfügt, am linken Rand begann, und Datentabellen wurden in die 600 px gequetscht, bis
  sie mitten im Wort brachen (gemessen am 08.09.2026 in Outlook für Mac). Die Lesebreite sitzt
  seitdem an Absätzen und Listen, wo sie hingehört: `max-width: 640px` hält Zeilen lesbar kurz,
  Tabellen tragen sie nicht. Rechtsbündige Zellen brechen zusätzlich nicht zwischen Zahl und
  Einheit — das ist eine Anweisung an die Darstellung und **keine** Ersetzung im Text: Das
  geschützte Leerzeichen vor „EUR" steht auf einer Einzelquelle und darf nach der Quellenlage
  nicht automatisch gesetzt werden. Jede Layouttabelle trägt
  `role="presentation"`: Ohne die Marke liest ein Screenreader sie als Datensatz vor, und die
  Prüfung lehnt sie ab. Umgekehrt gilt dasselbe — eine Tabelle ohne `<th>` **und** ohne die Marke
  ist ein Befund, egal welche der beiden Absichten dahinterstand.
- **Tabellen ab fünf Spalten** werden gemeldet, mit dem Vorschlag, sie als PDF-Anlage
  beizulegen. Die Zahl ist eine Setzung, keine Messung — deshalb eine Warnung.
- **Anhänge:** in drei Stufen, jede mit ihrer Fundstelle (Issue #183). Gemessen wird die
  **Nachricht**, nicht die Datei: MIME kodiert base64, vier Byte je drei — eine 20-MB-Datei
  geht als 26,7-MB-Nachricht hinaus. Microsoft nennt denselben Aufschlag selbst.

  | über | wer sie dann nicht mehr annimmt |
  |---|---|
  | 10 MB | ein lokaler Exchange-Server im Standard |
  | 25 MB | auch ein persönliches Gmail-Konto |
  | 35 MB | auch ein Microsoft-365-Postfach im Standard |

  Warnung, nie Fehler: Welche Grenze gilt, hängt am Postfach des Empfängers, und das kennt der
  Absender nicht — Ebene **Praxis**. Die binäre 10-MB-Prüfung in `verify --email` bleibt
  vorerst daneben stehen; sie misst die entschlüsselte Größe und damit die falsche Zahl.
- **Bilder** dürfen nur aus der Nachricht selbst kommen, und zwar als eigener Teil mit `cid:`.
  `data:` stand hier bis Issue #104 daneben; es lädt zwar nichts nach, aber Gmail zeigt solche
  Bilder in der Weiterleitungsansicht nicht an und Outlook hängt sie als namenlosen Anhang an.
  Jedes Bild trägt Breite und Höhe als Attribut — ohne sie reserviert kein Client Platz. Kein externes
  Stylesheet, kein Zählpixel, keine Tabelle als Layout.
- Jede Anlage soll im Text vorkommen. Gemeldet wird nur, dass der Dateiname nirgends auftaucht;
  falzmarke schreibt dafür **keinen** Satz in den Text.

## Nachgemessen wird die Datei, nicht die Absicht

`falzmarke email` ruft `verify --email` selbst auf, und der Prüfer öffnet die geschriebene
`.eml` neu, statt den Erzeuger zu befragen. Das ist der Punkt: Ein Prüfer, der gegen den eigenen
Bauplan antritt, bestätigt nur, dass beide dasselbe meinen. Deshalb misst er auch Dateien, die
von woanders kommen:

```bash
falzmarke verify --email fremde-nachricht.eml --verbose
```

Ohne den optionalen `text/markdown`-Teil lässt sich nicht feststellen, ob Text- und HTML-Teil
denselben Brief wiedergeben. Dann **sagt** der Bericht das, statt die Prüfung stillschweigend zu
überspringen.

## Beispiele

Sieben Stück unter [`examples/email/`](../examples/email/): ein Angebot, eine Mahnung mit Anlage,
eine Antwort mit `antwort_auf`, eine Abrechnung mit Tabelle, eine Nachricht mit Links, eine mit
Logo in der Signatur und eine mit mitgebrachter Signatur. Sie laufen in der CI mit; ihre `.eml` liegt byteweise als Golden in
`tests/golden/email/` und fällt auf, wenn sich an der Ausgabe etwas ändert, das niemand angesagt
hat.

Das Logo-Beispiel bringt sein Profil neben sich mit (`examples/email/profiles/`), weil keines
der ausgelieferten eines führt. Ohne dieses Beispiel belegte kein Golden, wie die Signatur mit
Bild aussieht — und der JS-Port des Signatur-Baukastens auf falzmarke.com prüft byte-genau
gegen diese Goldens.

Die Zahl oben hält `tests/test_email_beispiele.py` fest. Sie stand von August bis September
2026 auf „Vier", während längst fünf Dateien dort lagen; eine Zahl in Prosa altert still.

Erneuert werden die Goldens mit `python3 scripts/golden_email.py`. Der Diff im Pull Request ist
dann der Befund.

Die Anlage `examples/email/anlagen/rechnung-2026-0815.pdf` ist **eingefroren**, nicht bei jedem
Lauf erzeugt: Ein zweiter Renderlauf derselben Quelle liefert andere Bytes, und das Golden der
Mahnungs-Mail enthält die Anlage. Wer die Anlage neu rendert, sieht das Golden auffliegen — so
ist es gemeint.

## Verwandt

- [Befehle](cli.md) — alle Unterbefehle und Exit-Codes
- [Datenvertrag: das Frontmatter](../skill/references/frontmatter.md) — die Felder von `typ: email`
- [Absenderprofile](profiles.md) — der Abschnitt `email:` im Profil
- [ADR 0034](entscheidungen/0034-email-ist-ausgabe.md) — E-Mail ist Ausgabe, nicht Kanal
- [Was falzmarke behauptet — und was nicht](recht.md) — auch zu den Pflichtangaben in E-Mails
