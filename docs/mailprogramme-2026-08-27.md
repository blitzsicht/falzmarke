# Die `.eml` in drei Mailprogrammen — Protokoll vom 27.08.2026

Punkt 4 der Abnahme von [#59](https://github.com/blitzsicht/falzmarke/issues/59) verlangt eine
Sichtprüfung: Was zeigt ein Mailprogramm, wenn jemand eine von falzmarke erzeugte `.eml`
öffnet? Das lässt sich nicht automatisieren — geprüft werden soll genau das, was ein Mensch
sieht.

## Was geprüft wurde

Die vier Beispiele aus `examples/email/`, gesetzt mit `falzmarke email … --html` aus dem Stand
`da4723e` (v0.8.0). Ohne `SOURCE_DATE_EPOCH`, also ohne `Date` — der Normalfall.

| Programm | Fassung |
|---|---|
| Apple Mail | 16.0 |
| Mozilla Thunderbird | 154.0 |
| Microsoft Outlook für Mac | 16.112.1 |

macOS 26.5.2 (25F84), am 27.08.2026.

## Ergebnis

| | Apple Mail | Thunderbird | Outlook |
|---|---|---|---|
| Öffnet die Datei | ja | ja | ja |
| Absender, Empfänger, Kopie | richtig | richtig | richtig |
| Betreff, auch mit Umlaut | richtig | richtig | richtig |
| HTML-Teil wird gezeigt | ja | ja | ja |
| Tabelle mit Rahmen, Beträge rechtsbündig | ja | ja | nicht geprüft |
| Signatur | **einmal** | **einmal** | **einmal** |
| Anlage der Mahnung | ja, inline gerendert | nicht geprüft | ja, „40,6 KB" mit Vorschau |
| Öffnet als **Entwurf** | **nein** | **nein** | **nein** |

Die ersten sieben Zeilen sind das, was die Fassung zusagt, und sie halten überall dort, wo
gemessen wurde. Die letzte ist der Befund.

„Nicht geprüft" heißt genau das und wird nicht zu „ja" aufgerundet: Die Abrechnung mit der
Tabelle lief nicht durch Outlook, und im Thunderbird-Fenster war der untere Rand mit der
Anhangleiste nicht zu sehen. Dass die Anlage technisch einwandfrei in der Datei steckt, ist
belegt (`application/pdf`, 41.640 Byte, `disposition=attachment`) — dass Thunderbird sie
*anzeigt*, ist damit nicht belegt.

## Der Befund: eine `.eml` ist kein Entwurf

Alle drei Programme zeigen ein **Lesefenster** — Antworten, Allen antworten, Weiterleiten,
Archivieren. Kein Senden-Knopf, keine editierbaren Empfängerfelder. Das ist kein Fehler der
Datei, sondern die Natur des Formats: Eine `.eml` nach [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322) ist eine *Nachricht*. Ob ein
Programm sie als Entwurf anlegt oder als eingegangene Post darstellt, entscheidet das Programm.

### Gegenprobe mit `X-Unsent: 1`

Für genau diesen Zweck gibt es eine Konvention — die Kopfzeile `X-Unsent: 1`, aus dem klassischen
Outlook für Windows. Statt darüber zu spekulieren, wurde sie ausprobiert: dieselbe Nachricht,
eine zusätzliche Kopfzeile im Umschlag, sonst byteweise gleich.

**Ergebnis: kein Unterschied.** Outlook für Mac 16.112.1 öffnet die Fassung mit `X-Unsent: 1`
genauso als Lesefenster wie die ohne. Ausgerechnet das Programm, aus dessen Umfeld die
Konvention stammt, befolgt sie in dieser Fassung nicht.

**Grenze dieses Belegs:** Geprüft wurde auf macOS, in den oben genannten Fassungen. Über das
klassische Outlook für Windows sagt das nichts — dort kann `X-Unsent: 1` durchaus wirken. Wer
die Kopfzeile einbauen will, braucht dafür einen eigenen Beleg auf Windows; dieser hier trägt
ihn nicht.

### Was daraus folgt

Ein Werkzeug kann nicht zusagen, was das Programm des Empfängers entscheidet. Die Datei liefert
lesbar und vollständig, was sie liefern soll; wer aus ihr eine ausgehende Mail machen will,
nimmt in jedem der drei Programme **Weiterleiten** — oder kopiert den Text aus der
`.html`-Vorschau, wofür sie gedacht ist.

Die Abnahme von #59 verlangt in Punkt 4 „öffnet als Entwurf". Nach dieser Messung ist das keine
Eigenschaft, die eine `.eml` erzwingen kann. Der Punkt gehört umformuliert; die Entscheidung
liegt beim Maintainer und steht im Vorgang.

## Was hier nicht geprüft wurde

- **Outlook für Windows**, klassisch wie neu — siehe oben.
- **Weboberflächen** (Gmail, Outlook Web): Sie öffnen keine lokalen `.eml`-Dateien; dort ist der
  Weg über die `.html`-Vorschau der vorgesehene.
- **Der Umbruch bei schmalem Fenster** wurde nur beiläufig gesehen, nicht systematisch gemessen.
  `format=flowed` ist im Textteil vorhanden und gegen seine Umkehrung geprüft
  (`tests/test_email_beispiele.py`); wie ein Programm damit umgeht, ist dessen Sache.
- **Client-Matrix-Tests** (Litmus) — laut #59 ausdrücklich nicht Teil der Sache.
