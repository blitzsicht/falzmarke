# falzmarke-Markdown — was im Brieftext möglich ist

Der Brieftext steht unter dem Frontmatter als Markdown. Gesetzt wird eine **dokumentierte
Teilmenge von [CommonMark](https://commonmark.org/) 0.31.2** — die Teilmenge, die in einen
Geschäftsbrief gehört.

Alles außerhalb dieser Teilmenge **bricht mit Zeile, Grund und Korrektur ab**. Es wird nie
still etwas anderes gesetzt und nie stillschweigend weggelassen: Ein Brief, der anders
aussieht als geschrieben, wäre der teuerste Ausgang.

Die Felder über dem Text stehen im [Datenvertrag](frontmatter.md).

## Was du schreiben kannst

| Syntax | Ergebnis |
|---|---|
| Absätze, durch Leerzeile getrennt | je ein Absatz, eine Leerzeile Abstand |
| `**fett**`, `__fett__` | fett |
| `*kursiv*`, `_kursiv_` | kursiv |
| `***beides***` | fett und kursiv |
| `\` am Zeilenende | Zeilenumbruch innerhalb des Absatzes |
| `-` / `*` / `+` am Zeilenanfang | Aufzählung, bis zwei Ebenen |
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

## Was abbricht — und warum

| Syntax | Grund |
|---|---|
| Überschriften `#`, auch `===`/`---` darunter | Der Betreff steht im Frontmatter. Ein Brief hat keine Zwischenüberschriften. |
| Links `[t](u)`, `[t][id]`, `<url>` | Auf Papier gibt es keinen Link. Die Adresse gehört ausgeschrieben in den Text. |
| Bilder `![]()` | Logo und Unterschrift gehören ins Profil, nicht in den Fließtext. |
| Code: `` `x` ``, eingerückt, ``` | Ein Geschäftsbrief setzt keinen Code. Text ohne Backticks schreiben. |
| Blockzitat `>` | Kein Element des Geschäftsbriefs. |
| HTML | Wird nie durchgereicht — weder gesetzt noch entfernt, sondern gemeldet. |
| Trennlinie `---` allein | Wäre im Brief ein Fremdkörper und kollidiert mit dem Frontmatter-Trenner. |
| `~~durchgestrichen~~`, `[^1]`, `- [ ]` | Nicht Teil der Teilmenge; die Meldung nennt die erkannte Syntax. |
| Tabelle ohne Trennzeile | Sonst stünde die Kopfzeile als gewöhnlicher Text im Brief. |

## Drei bewusste Abweichungen von CommonMark

1. **Eine einzelne Zeile, die wie ein Listenpunkt aussieht, ist keine Liste.**
   `2. Mahnung zur Rechnung 4711` würde nach CommonMark eine nummerierte Liste — die `2.`
   verschwände in der Nummerierung. falzmarke lehnt das ab und schlägt `2\. Mahnung` vor.
   Dasselbe gilt für einen einzelnen Strich: `- 5 °C` würde ein Aufzählungspunkt.
2. **HTML wird nie durchgereicht.** CommonMark erlaubt eingebettetes HTML; hier ist es ein
   Fehler.
3. **Links werden nie gesetzt.**

## Warum eine Teilmenge

Der Inhalt kommt als Markdown, das Layout setzt der Renderer. Jedes Element, das im Brieftext
frei gestaltbar wäre, hebelt diese Trennung aus: Eine Überschrift im Text verschöbe den
Satzspiegel, ein Bild die Geometrie, ein Link führte ins Leere. Was die Teilmenge auslässt,
lässt sie deshalb aus — nicht, weil es schwer wäre.
