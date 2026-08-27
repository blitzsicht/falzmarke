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

**`format=flowed` nach RFC 3676**: Weiche Umbrüche tragen ein Leerzeichen am Zeilenende und
dürfen vom Empfängerprogramm neu umbrochen werden; Tabellen und Listenpunkte tragen ihre
Bedeutung in der Form und bleiben fest. Zeilen, die mit einem Leerzeichen beginnen, werden
gestopft (space-stuffing) und beim Lesen wieder entstopft. Geprüft wird das gegen die Umkehrung:
falten, entfalten, muss gleich sein.

## Was fehlt — und warum

| Nicht in der Datei | Grund |
|---|---|
| `Message-ID` | gehört dem Versender. Wer sie beim Erzeugen setzt, vergibt eine Kennung für eine Nachricht, die vielleicht nie abgeschickt wird. |
| `Date` | entsteht beim Versand. Ein Entwurf von gestern, der heute rausgeht, wäre sonst auf gestern datiert. **Ausnahme:** ist `SOURCE_DATE_EPOCH` gesetzt, steht das Datum drin — das ist der Weg zu einem reproduzierbaren Vergleich. |
| ein Versandweg | falzmarke versendet nichts. Es gibt keinen Versandbefehl und keine Option, die sendet. |

## Grenzen

- **Betreff:** höchstens 78 Zeichen. Darüber schneiden viele Übersichten ab.
- **Zeilenlänge:** RFC 5322 erlaubt keine Zeile über 998 Zeichen.
- **Anhänge:** zusammen höchstens 10 MB. Größeres lehnen viele Server ab, ohne es zu sagen.
- **Bilder** dürfen nur aus der Nachricht selbst kommen (`cid:` oder `data:`) — kein externes
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

Vier Stück unter [`examples/email/`](../examples/email/): ein Angebot, eine Mahnung mit Anlage,
eine Antwort mit `antwort_auf` und eine Abrechnung mit Tabelle. Sie laufen in der CI mit; ihre
`.eml` liegt byteweise als Golden in `tests/golden/email/` und fällt auf, wenn sich an der
Ausgabe etwas ändert, das niemand angesagt hat.

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
