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

### In E-Mails noch nicht

`typ: email` lehnt diese Elemente ab, auch mit `dialekt: "1.1"`. Brief, HTML-Teil und Textteil
entstehen aus derselben geprüften Quelle, und der HTML-Teil setzt sie noch nicht. Die Meldung
sagt das mit Zeile und Grund; es entsteht keine halb gesetzte Mail.

## Was abbricht — und warum

| Syntax | Grund |
|---|---|
| Überschriften `#` **in Fassung 1.0** | Der Standardbrief hat keine Zwischenüberschriften — der Betreff steht im Frontmatter. Für lange Schreiben: `dialekt: "1.1"`. |
| `===`/`---` unter einer Zeile | Auch in 1.1 nicht: Der Unterstrich kollidiert mit dem Frontmatter-Trenner. `#` schreiben. |
| Links `[t](u)`, `[t][id]`, `<url>` | Auf Papier gibt es keinen Link. Die Adresse gehört ausgeschrieben in den Text. |
| Bilder `![]()` | Logo und Unterschrift gehören ins Profil, nicht in den Fließtext. |
| Code: `` `x` ``, eingerückt, ``` | Ein Geschäftsbrief setzt keinen Code. Text ohne Backticks schreiben. |
| Blockzitat `>` | Kein Element des Geschäftsbriefs. |
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
