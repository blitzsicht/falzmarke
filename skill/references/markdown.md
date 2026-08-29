# falzmarke-Markdown — was im Brieftext möglich ist

Der Brieftext steht unter dem Frontmatter als Markdown. Gesetzt wird eine **dokumentierte
Teilmenge von [CommonMark](https://commonmark.org/) 0.31.2** — die Teilmenge, die in einen
Geschäftsbrief gehört.

Alles außerhalb dieser Teilmenge **bricht mit Zeile, Grund und Korrektur ab**. Es wird nie
still etwas anderes gesetzt und nie stillschweigend weggelassen: Ein Brief, der anders
aussieht als geschrieben, wäre der teuerste Ausgang.

Die Felder über dem Text stehen im [Datenvertrag](frontmatter.md).

## Zwei Fassungen

Der Dialekt trägt eine Fassung. Welche gilt, sagt das Feld `dialekt:` im Frontmatter:

| Fassung | Wofür |
|---|---|
| **1.0** | Der Standardbrief. **Gilt, wenn das Feld fehlt.** |
| **1.1** | Lange Schreiben — Schriftsätze, Stellungnahmen, ausführliche Behördenpost |

**Ein Brief ohne das Feld rendert unverändert weiter.** Das ist keine Nebenbemerkung, sondern
die Zusage, unter der 1.1 überhaupt hinzukam: Wer heute einen Brief geschrieben hat, bekommt
morgen dasselbe PDF. Was 1.1 zusätzlich setzt, steht unten in der Spalte „1.1".

`falzmarke init` schreibt `dialekt: "1.1"` in neue Briefe. Ein unbekannter Wert ist ein Fehler
und nennt die bekannten Fassungen — er fällt nicht stillschweigend auf 1.0 zurück, sonst sähe
der Brief anders aus als geschrieben, ohne dass es jemand erführe.

## Was du schreiben kannst

| Syntax | Ergebnis |
|---|---|
| Absätze, durch Leerzeile getrennt | je ein Absatz, eine Leerzeile Abstand |
| `**fett**`, `__fett__` | fett |
| `*kursiv*`, `_kursiv_` | kursiv |
| `***beides***` | fett und kursiv |
| `\` am Zeilenende | Zeilenumbruch innerhalb des Absatzes |
| `-` / `*` / `+` am Zeilenanfang | Aufzählung; **1.0** bis zwei Ebenen, **1.1** bis sechs |
| `1.` / `1)` | nummerierte Liste, beginnt bei deinem Startwert |
| Tabelle mit Trennzeile, Ausrichtung `:--`, `:-:`, `--:` | Tabelle; ohne Angabe linksbündig |
| `\* \_ \\ \# \. \- \[ \]` | das Zeichen selbst, ohne Bedeutung |
| `3 * 4`, `a _ b` (Zeichen mit Leerraum ringsum) | Text, keine Auszeichnung |
| `&nbsp;` `&amp;` `&copy;` | dekodiert |

Ein einfacher Zeilenwechsel wird zum Leerzeichen — zwei Zeilen Quelltext ergeben einen Absatz.
Wer eine Zeile umbrechen will, setzt `\` ans Ende.

## Was von selbst passiert

Ein Typografie-Pass wendet die Schreibregeln der Norm an, ohne dass du daran denken musst:

| Du schreibst | Im PDF steht |
|---|---|
| `z. B.`, `u. a.`, `d. h.` | mit geschütztem Leerzeichen — bricht nie um |
| `10 %`, `5 km`, `1.234,56 EUR` | Zahl und Einheit bleiben zusammen |
| `§ 5` | Paragraphenzeichen bleibt am Wert |
| `25. August` | Tag und Monat bleiben zusammen |
| `--` | – (Halbgeviertstrich) |
| `"Wort"` | „Wort“ |

Geändert wird nur, wo die Regel **mehrfach belegt** ist. Was der Pass sonst geändert hätte,
kann er als Vorschlag ausgeben, ohne den Brief anzufassen — siehe
[Quellenlage je Regel](din5008.md#quellenlage-je-regel).

## Was nur Fassung 1.1 setzt

Für Schriftsätze, Stellungnahmen und längere Behördenpost. Alles hier braucht
`dialekt: "1.1"` im Frontmatter; ohne das Feld bleibt es ein Fehler.

| Syntax | Ergebnis | Grenze |
|---|---|---|
| `#` bis `####` | Zwischenüberschrift, vier Ebenen | ab `#####` Fehler |
| Aufzählung tiefer als zwei Ebenen | eingerückte Unterpunkte | ab Ebene 5 Warnung, ab 7 Fehler |
| `>` am Zeilenanfang | Blockzitat, eingerückt mit Balken | ab Ebene 3 Fehler |
| `` `Text` `` | Festbreitenschrift im Satz | siehe Zeilenlänge unten |
| ```` ``` ```` oder vier Leerzeichen Einzug | abgesetzter Auszug, Festbreite | siehe Zeilenlänge unten |

**Alle vier Überschriftebenen stehen in derselben Schriftgröße** — fett, ab Ebene 3 kursiv. Das
ist keine Sparsamkeit: Der Satz läuft auf einem 12-pt-Raster, und eine größere Zeile ist höher
als eine Rasterzeile; alles darunter verlöre seine Position. Ein Geschäftsbrief zeichnet ohnehin
mit Fett und Kursiv aus, nicht mit Schriftgrößen.

Die Ebenen bleiben trotzdem vier: Sie stehen als **Struktur** im PDF, und davon lebt ein
Screenreader. Eine juristische Gliederungskennzeichnung (`A.`, `I.`, `1.`, `a)`) schreibst du
selbst in die Überschrift — es wird nichts automatisch nummeriert und damit auch nichts still
umnummeriert.

**Was eine Überschrift nicht tut:** den Brief gliedern. Der Betreff steht im Frontmatter,
Anschriftfeld, Informationsblock und Betreffposition bleiben, wo sie sind. Nachgemessen an
27 Vordruck-Maßen, mit und ohne Überschriften: identisch.

**Vorsicht bei langen Wörtern in Überschriften.** Steht ein Wort ohne Trennstelle am Anfang der
Zeile, kann Typst es nicht umbrechen, und es läuft aus dem Satzspiegel. `render` fängt das und
bricht mit Exit-Code 2 ab — der Bericht nennt Seite und Element.

### Zitate

`>` gibt fremden Wortlaut wieder. Darin dürfen Absätze und Aufzählungen stehen, und ein Zitat
darf ein weiteres enthalten — mehr nicht: Ab der dritten Ebene ist nicht mehr erkennbar, wer
wen wiedergibt, und genau das ist beim Zitieren der Punkt.

### Wortgetreue Auszüge

Backticks setzen Text in Festbreitenschrift: ein Aktenzeichen mitten im Satz, eine
Protokollzeile als abgesetzter Block.

**Was darin steht, bleibt Zeichen für Zeichen stehen.** Der Typografie-Pass läuft hier nicht —
aus `"` wird kein „, aus `--` kein –. Ein Auszug, den das Werkzeug unterwegs verschönert, gibt
nicht mehr wieder, was dastand.

Aus demselben Grund **fügt das Werkzeug keinen Umbruch ein**. Den Satz daran hindern kann es
nicht — was mit einer zu langen Zeile geschieht, hängt daran, ob sie ein Leerzeichen hat:

| | passt bis | ohne Leerzeichen | mit Leerzeichen |
|---|---|---|---|
| abgesetzter Block | 68 Zeichen | läuft aus dem Satzspiegel | Typst bricht sie um |
| im Satz | 70 Zeichen | läuft aus dem Satzspiegel | Typst bricht sie um |

Beides ist ein Befund, und beide werden gemeldet — aber an verschiedenen Stellen. Den Überlauf
misst `render` am fertigen PDF und bricht mit Exit-Code 2 ab. Den Umbruch sieht dort niemand:
Das PDF hält alle Maße ein, nur der Wortlaut ist ein anderer. **Deshalb meldet `lint` jede zu
lange Auszugszeile an der Quelle**, mit ihrer Zeilennummer, bevor gesetzt wird — als Warnung,
der Brief entsteht trotzdem.

*Gemessen am 28.08.2026 (die Grenzen) und am 29.08.2026 (was darüber geschieht) mit der
Festbreitenschrift, die der Renderer wählt; steht sie auf einem System nicht bereit, greift die
nächste und der Wert weicht leicht ab. Der Block verliert die zwei Zeichen an seinen Einzug.*

Für einen Auszug **im Satz** ist die Zahl nur eine obere Schranke: Er beginnt mitten in einer
Zeile, und was vor ihm steht, nimmt ihm Platz — ein Auszug unter 70 Zeichen kann also trotzdem
umbrechen. Sicher ist nur, dass alles darüber nirgends passt, und genau das meldet `lint`.

Wer längere Zeilen zitieren muss, teilt sie selbst — das Werkzeug tut es nicht für dich, weil
jede Stelle, an der es umbräche, eine Entscheidung über fremden Wortlaut wäre.

**Keine Einfärbung.** Eine Sprachangabe (```` ```python ````) wird nicht ausgewertet und
gemeldet: Ein Geschäftsbrief zitiert wortgetreu, er stellt keinen Quelltext aus. Farbe wäre
eine Deutung, die der Zitierende nicht getroffen hat — und auf einem Schwarzweißdruck ohnehin
verloren.

**Nichts darin wird ausgeführt.** Ein Auszug, der Anweisungen des Satzsystems enthält, wird
sichtbar gesetzt und sonst nichts. Das ist geprüft, und zwar gegen einen absichtlich
unsicheren Renderer, bei dem die Anweisung nachweislich ausgeführt *wird*.

### Links — nur in E-Mails

```markdown
Die [Geschäftsbedingungen](https://example.de/agb) gelten seit August.
Schreiben Sie an [info@example.de](mailto:info@example.de).
```

**Im Brief bleibt jeder Link ein Fehler.** Auf Papier gibt es nichts zum Anklicken; ein Wort,
hinter dem sich eine Adresse verbirgt, ist dort ein Wort und sonst nichts. Wer eine Adresse
nennen will, schreibt sie aus.

Zugelassen sind `https:`, `http:`, `mailto:` und `tel:` — eine Positivliste, und das ist
Absicht: Eine Sperrliste vergisst immer eines. `javascript:`, `data:`, `vbscript:` und `file:`
stehen deshalb nirgends; sie sind nicht aufgezählt, sie sind schlicht nicht dabei. Ein relatives
Ziel (`/seite`, `#anker`) ist ebenfalls ein Fehler: Eine E-Mail hat keine Seite, zu der ein Pfad
gehören könnte.

Gemeldet, aber nicht abgelehnt:

| Warnung | Warum |
|---|---|
| Linktexte wie „hier" oder „klicken Sie hier" | Ein Bildschirmleseprogramm liest Links oft als Liste vor, losgelöst vom Satz. „hier" ist dort nichts. |
| `http://` statt `https://` | überträgt unverschlüsselt |
| Kurz-URL-Dienste (`bit.ly` und ähnliche) | Wer eine Geschäftsmail schreibt, verbirgt sein Ziel nicht |

So kommt der Link an:

| Fassung | Ergebnis |
|---|---|
| HTML-Teil | `<a href="…">` — ohne Nachverfolgung, ohne Umleitung, in der Textfarbe und unterstrichen (Farbe allein ist kein Unterscheidungsmerkmal) |
| Klartext | `Bedingungen: <https://example.de/agb>` |

Die spitzen Klammern im Klartext halten das Satzzeichen von der Adresse fern. Ohne sie steht
dort `…/agb.html, die seit August` — wer die Adresse doppelklickt, nimmt das Komma mit, und
Mailprogramme, die Adressen selbst erkennen, ziehen es in den Verweis.

**Die Adresse geht nie durch die Typografie.** Aus einem `-` darf kein Halbgeviertstrich werden
und aus `...` kein Auslassungszeichen — sonst kopiert der Empfänger eine Adresse, die es nicht
gibt.

### In E-Mails noch nicht

`typ: email` lehnt diese Elemente ab, auch mit `dialekt: "1.1"`. Brief, HTML-Teil und Textteil
entstehen aus derselben geprüften Quelle, und der HTML-Teil setzt sie noch nicht. Die Meldung
sagt das mit Zeile und Grund; es entsteht keine halb gesetzte Mail.

## Wie es im PDF ankommt

Ein Element ist im PDF nicht dasselbe wie sein Aussehen. Neben dem, was man sieht, führt
ein PDF einen **Strukturbaum** — dort steht, *was* jedes Stück ist. Für einen Screenreader
ist das die einzige Quelle: Eine Überschrift, die nur größer und fetter gesetzt ist, liest er
als gewöhnlichen Satz vor.

Gemessen am 29.08.2026 mit pypdf, festgehalten in `tests/test_struktur.py`:

| Was du schreibst | Auszeichnung im PDF |
|---|---|
| `# …` bis `#### …` | `/H1` … `/H4` |
| `* …` und `1. …` | `/L` mit `/LI` |
| `> …` | `/BlockQuote` |
| ` ``` ` und `` ` `` | `/Code` |
| Tabelle | `/Table` mit `/THead`, `/TH`, `/TR`, `/TD` |
| `**…**` und `*…*` | `/Strong` und `/Em` |

Das gilt **in beiden Fassungen** und unabhängig von `--pdfua`. Die Option ändert nur, ob sich
das PDF im XMP als PDF/UA-1 zu erkennen gibt; die Struktur, auf die sie sich beruft, ist ohnehin
da. In CI hält veraPDF beide Fassungen gegen ihre Standards.

Zwei dieser Zeilen stimmten bis zu dieser Messung nicht: Ein Blockzitat war ein Kasten ohne
Bedeutung, und die Kopfzeile einer Tabelle war fett gesetzt und sonst nichts (Issue #138).

### Eine Tabelle steht nicht auf dem Zeilenraster

Der Briefkörper steht auf einem 12-pt-Raster: Jede „Leerzeile" der Norm ist genau eine
Rasterzeile, und seit Issue #140 wird das gemessen. **Tabellen sind davon ausgenommen** — und das
steht hier, weil es sonst still gälte.

Gemessen am Beispiel mit Tabelle:

| Abstand | in Rasterzeilen |
|---|---|
| Absatz → erste Tabellenzeile | 2,33 |
| Tabellenzeile → Tabellenzeile | 1,58 |
| letzte Tabellenzeile → Absatz | 2,33 |

Alles unterhalb einer Tabelle steht damit auf einem anderen Raster als alles darüber. Auf einem
einzelnen Blatt fällt das nicht auf; zwei nebeneinandergelegte Ausdrucke zeigen es sofort.

Der Grund ist die Zeilenhöhe: Sie ist die Texthöhe plus zweimal der Innenabstand der Zelle. Bei
11 pt und 1,4 mm Innenabstand ergibt das 6,68 mm — das 1,58-fache einer Rasterzeile. Rastertreu
wäre sie erst bei 2,293 mm Innenabstand (dann wächst jede fünfzeilige Tabelle um 9 mm) oder bei
0,176 mm (dann kleben die Zellen aneinander).

**Ob es dabei bleibt, ist offen** — die Abwägung zwischen Raster und Lesbarkeit steht als
[Issue #151](https://github.com/blitzsicht/falzmarke/issues/151) und gehört entschieden, nicht
von einer Prüfung erzwungen. Bis dahin beschreibt dieser Abschnitt, was ist.

### Eine Überschrift bleibt bei ihrem Absatz

Sie rutscht nie allein ans Seitenende. Das ist keine eigene Vorkehrung: Typst setzt
Überschriften in einen Block, der ohne den folgenden Absatz nicht umbricht. Weil es die Zusage
einer fremden Fassung ist und keine eigene, steht sie als Messung mit Gegenprobe in
`tests/test_struktur.py` — zieht Typst sie zurück, wird der Test rot, statt dass es jemand an
einem Ausdruck bemerkt.

Ein **Zitat** darf dagegen umbrechen. Ein langer Auszug über einen Seitenwechsel zu verbieten
hieße, ihn auf eine Seite zwingen zu müssen — und dafür gäbe es nur zwei Wege: die Schrift
verkleinern oder den Wortlaut kürzen. Beides ändert, was dasteht, und genau das tut dieses
Werkzeug nicht.

## Was abbricht — und warum

| Syntax | Grund |
|---|---|
| Überschriften `#` **in Fassung 1.0** | Der Standardbrief hat keine Zwischenüberschriften — der Betreff steht im Frontmatter. Für lange Schreiben: `dialekt: "1.1"`. |
| `===`/`---` unter einer Zeile | Auch in 1.1 nicht: Der Unterstrich kollidiert mit dem Frontmatter-Trenner. `#` schreiben. |
| Links `[t](u)`, `[t][id]`, `<url>` | Auf Papier gibt es keinen Link. Die Adresse gehört ausgeschrieben in den Text. |
| Bilder `![]()` | Logo und Unterschrift gehören ins Profil, nicht in den Fließtext. |
| Code **in Fassung 1.0** | Der Standardbrief setzt keinen Code. Für Auszüge: `dialekt: "1.1"`. |
| Blockzitat `>` **in Fassung 1.0** | Dasselbe — mit `dialekt: "1.1"` möglich. |
| HTML | Wird nie durchgereicht — weder gesetzt noch entfernt, sondern gemeldet. |
| Trennlinie `---` allein | Wäre im Brief ein Fremdkörper und kollidiert mit dem Frontmatter-Trenner. |
| `~~durchgestrichen~~`, `[^1]`, `- [ ]` | Nicht Teil der Teilmenge; die Meldung nennt die erkannte Syntax. |
| Tabelle ohne Trennzeile | Sonst stünde die Kopfzeile als gewöhnlicher Text im Brief. |

## Drei bewusste Abweichungen von CommonMark

1. **Eine einzelne Zeile, die wie ein Listenpunkt aussieht, wird gemeldet.**
   `2. Mahnung zur Rechnung 4711` ist nach CommonMark eine nummerierte Liste — gemeint ist
   fast immer ein Satz. falzmarke setzt die Zeile **mit erhaltenem Startwert** und meldet es
   als Warnung; wer die Zahl zum Satz ziehen will, schützt den Punkt: `2\. Mahnung`. Nichts
   wird still umnummeriert, und der Brief steht trotzdem.

   Beim **einzelnen Strich** bleibt es beim Abbruch: `- 5 °C` würde ein Aufzählungspunkt, und
   anders als bei einer Zahl ist dort nicht erkennbar, was gemeint war. Auch dieser Fall hat
   seinen Schutz: `\- 5 °C`.
2. **HTML wird nie durchgereicht.** CommonMark erlaubt eingebettetes HTML; hier ist es ein
   Fehler.
3. **Links werden nie gesetzt.**

## Warum eine Teilmenge

Der Inhalt kommt als Markdown, das Layout setzt der Renderer. Jedes Element, das im Brieftext
frei gestaltbar wäre, hebelt diese Trennung aus: ein Bild verschöbe die Geometrie, ein Link
führte ins Leere. Was die Teilmenge auslässt, lässt sie deshalb aus — nicht, weil es schwer wäre.

**Überschriften waren nie falsch, sie waren für den Standardbrief unnötig.** Hier stand, sie
verschöben den Satzspiegel; das trifft auf eine frei gestaltete Überschrift zu, nicht auf eine,
deren Abstände im Raster des Renderers liegen. Für ein langes Schreiben sind sie das Mittel,
mit dem der Leser sich zurechtfindet — deshalb setzt Fassung 1.1 sie, und der Renderer behält
die Gestaltung.
