# 0052 — Unsichtbare Zeichen werden gemeldet, nicht geändert

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:** [0029](0029-falzmarke-ist-werkzeug-kein-kanal.md), [0035](0035-vier-ebenen-fuer-email-regeln.md), [0039](0039-falzmarke-rechnet-nicht.md)

## Worum es geht

Ein Absatz, der aus einem Browser, einem Chatfenster oder einem PDF in den Entwurf kopiert wird,
bringt Zeichen mit, die niemand sieht: Zero-Width-Marken, weiche Trennstriche, Bidi-Steuerzeichen,
Variantenselektoren. Sie überlebten jeden Weg, den falzmarke baut — gemessen am 25.10.2026 ergab
die Suche nach `u200`, `u00ad`, `\xa0`, `zero.?width`, `bidi` und `NBSP` in `lint.py`,
`markdown.py`, `pruefung_eml.py` und `eml.py` **einen Kommentar und sonst keinen Treffer**. Ein
U+200B mitten in einem Wort stand hinterher in der `.eml` und im PDF, und weder Absender noch
Empfänger erfuhr davon.

Das ist nicht nur Kosmetik. Ein Zero-Width-Zeichen in einer Rechnungsnummer macht die Suche
danach erfolglos. Eines in einem wortgetreuen Auszug verändert den zitierten Wortlaut — genau das,
wogegen der Auszug gebaut ist ([#173](https://github.com/blitzsicht/falzmarke/issues/173)). Ein
Right-to-Left Override kann die Leserichtung einer Zeile umkehren, ohne eine Spur zu hinterlassen.

## Entscheidung 1: Melden, nie ändern

`skill/falzmarke/zeichen.py` gibt Befunde zurück. Sie löscht nichts, ersetzt nichts, normalisiert
nichts.

Der naheliegende andere Weg wäre, die Zeichen beim Einlesen einfach zu entfernen. Er ist der
falsche, und zwar aus demselben Grund, der schon in `skill/references/stil.md` steht: „Ein
Werkzeug, das ungefragt in einen Text schreibt, schreibt irgendwann den falschen." Wer ein
arabisches Zitat einfügt, braucht die Bidi-Marken; wer eine Emoji-Folge schreibt, braucht den
Zero-Width-Joiner. Eine stille Bereinigung wäre in diesen Fällen eine Textänderung, die niemand
sieht und niemand nachvollziehen kann.

Die Trennung ist dieselbe wie bisher: `typografie.py` **setzt** Zeichen, `lint.py` **meldet** sie.
`zeichen.py` liegt auf der meldenden Seite.

**Das stärkste Gegenargument:** Eine Fehlermeldung, die der Nutzer nicht beheben kann, ist
wertlos — und ein Zeichen, das man nicht sieht, lässt sich schwer löschen. Deshalb nennt jede
Meldung die Zeile **und die Stelle in Zeichen**: `U+200B ZERO WIDTH SPACE steht unsichtbar im
Text (Zeichen 15)`. Damit ist die Stelle auffindbar, ohne dass das Werkzeug sie anfasst.

## Entscheidung 2: Fehler für das Zwecklose, Warnung für das Ermessen

Zwei Regeln, nicht eine, weil die Wirkung sich unterscheidet:

| Regel | Was | Wirkung |
|---|---|---|
| `zeichen.unsichtbar` | Kategorien `Cf`, `Cc`, `Co`, `Zl`, `Zp`, Variantenselektoren ohne Bildzeichen davor, Nichtzeichen, einzelne Füllzeichen | Fehler |
| `zeichen.geschuetzt` | geschütztes Leerzeichen an unerwarteter Stelle, Leerzeichen, die nicht wie eines aussehen | Warnung |

Beide tragen `herkunft: werkzeug`. Die Norm sagt zu Unicode-Steuerzeichen nichts, und die beiden
genannten Unicode-Quellen belegen die **Liste**, nicht die Regel: Dass ein Nichtzeichen in einem
deutschen Geschäftsbrief ein Defekt ist, steht in keinem Standard. Es ist der eigene Datenvertrag
— und nach [ADR 0035](0035-vier-ebenen-fuer-email-regeln.md) darf `werkzeug` ein Fehler sein.

Dass die Fehlerstufe hier gerechtfertigt ist, hängt an einer Prüfung, die kein Ermessen braucht:
Ein Zero-Width-Zeichen mitten in einem deutschen Wort hat keinen legitimen Zweck. Was einen haben
**kann**, fällt nicht unter diese Regel — darüber entscheidet die zweite.

`zeichen.geschuetzt` steht auf `deckel: warnung`. Der Umweg über die Ebene `praxis` in
`email.yaml` wäre der naheliegende gewesen und ist falsch: `praxis` heißt in diesem Repository
„Darstellungsverhalten von Mailprogrammen", und davon redet die Regel nicht. Unter jeder Meldung
stünde dann „Erfahrung mit Mailprogrammen, kein Nachweis" — ein Grund, den es nicht gibt. Beide
Regeln stehen deshalb in `din5008.yaml`: Die Prüfung redet über die **Eingabe jeder Dokumentart**,
nicht über die E-Mail.

## Entscheidung 3: Die erlaubten Stellen kommen aus `typografie.py`

falzmarke setzt selbst geschützte Leerzeichen — bei `z. B.`, `§ 7`, `12 kg`, `25. August`,
`Nr. 4711` (`typografie.py`, `ABKUERZUNGEN`, `EINHEITEN`, `MONATE`, `VOR_ANGABE`). Eine Prüfung
mit eigener Liste dieser Stellen würde genau dann falsch, wenn es darauf ankommt: Sie meldete die
Ausgabe, die das Werkzeug gerade erzeugt hat.

`zeichen._positivmuster()` baut die erlaubten Stellen deshalb **aus diesen Listen**. Wächst eine
davon, wächst die Positivregel mit. `test_die_eigene_typografie_wird_nie_gemeldet` hält die
komplette Ausgabe des Typografie-Passes gegen die Prüfung — 51 Proben am 25.10.2026, keine
gemeldet. `test_die_positivregel_liest_aus_typografie` ist die Gegenprobe dazu: Nimmt
`typografie.EINHEITEN` die Einheit `kg`, muss `12 kg` gemeldet werden.

Eine Warnung, die am eigenen Ergebnis anschlägt, kostet Vertrauen in alle anderen. Das ist in
diesem Repository schon einmal teuer geworden
([#133](https://github.com/blitzsicht/falzmarke/issues/133), die Telefonprüfung, die jede Vorwahl
kleinerer Orte meldete).

## Entscheidung 4: Kein fremder Code, kein `--fix`, keine Normalisierung

Sechs Fremdrepositorien wurden daraufhin gelesen. Übernommen wurde die **Dreiteilung** in
`actionable / contextual / informational` (als Fehler / Warnung / keine Meldung) und die
Kontextlogik für Bildzeichen. Übernommen wurde **kein Code**, und zwar aus gemessenen Gründen:

* Der eine Kandidat behandelt U+00A0 als „safe: space" und ersetzt es beim Bereinigen — er würde
  genau das zerstören, was `typografie.py` absichtlich setzt. Derselbe Fehler steckt im zweiten
  Kandidaten als **Standardverhalten** (`normalize_spaces=True`).
* Eine Confusables-Tabelle bildet U+2013 auf `-` und U+201C/201D auf `"` ab. Das wäre das Ende
  der deutschen Typografie, die dieses Werkzeug gerade herstellt.
* Beide bringen Abhängigkeiten mit, die falzmarke nicht hat (`requests`), oder eine zweite
  Lizenz. Die Prüfung braucht nichts außer `unicodedata` aus der Standardbibliothek.

Eine Unicode-Normalisierung (NFC/NFKC) findet **nicht** statt. NFKC ändert sichtbaren Text —
`㎏` wird zu `kg`, Ligaturen werden aufgelöst, Brüche umgeschrieben. Das ist eine Textänderung
und fällt unter Entscheidung 1.

## Was ausdrücklich nicht geprüft wird

**Die Kategorie `Cn`** (unzugewiesen) wäre der bequeme Weg zu einer vollständigen Liste und ist
der falsche: Sie ist in [UAX #44](https://www.unicode.org/reports/tr44/) der Standardwert für
alles Unzugewiesene. In einer älteren Python-Fassung trifft sie auch ein neues, gültiges Zeichen —
ein Fehlalarm, der mit dem Alter des Interpreters kommt und nicht mit dem Text. Die Nichtzeichen
stehen deshalb wörtlich im Code, belegt aus der Unicode-FAQ: 66 Codepunkte, „formally immutable".

**Das Wagenrücklaufzeichen** am Zeilenende. Eine unter Windows geschriebene Datei trägt es in
jeder Zeile; ohne diese Ausnahme meldete die Prüfung jede davon.

**Tabulator und Zeilenumbruch.** `lint` meldet sie schon als Regeln `tabulator` und `umbruch`.
Zweimal dasselbe zu melden macht die Meldung nicht wahrer.

**Ein BOM am Dateianfang.** Der Plan sah dafür eine Ausnahme vor. Sie ist nicht gebaut, weil
`pruefe_body` den **Textteil** bekommt und nicht die Datei: Am Anfang des Textteils ist ein BOM
genauso Fracht wie mitten im Satz, und eine Ausnahme dafür wäre eine Bedingung, die im
ausgeführten Pfad nie zutrifft — ein Zweig, den kein Test rot bekommen kann.

## Folgen

* Ein Entwurf mit einem unsichtbaren Steuerzeichen bricht ab, statt ins PDF zu wandern. Das ist
  eine Verhaltensänderung für Entwürfe, die bisher durchliefen.
* Die 66 Beispiele unter `examples/` bleiben befundfrei (gemessen am 25.10.2026 über
  `falzmarke lint`, nicht nur im Test).
* Die Prüfung gilt auch **im wortgetreuen Auszug**. Dort wird sie nicht ausgenommen, obwohl der
  Auszug sonst unangetastet bleibt: Ein unsichtbares Zeichen verändert gerade dort den zitierten
  Wortlaut.
