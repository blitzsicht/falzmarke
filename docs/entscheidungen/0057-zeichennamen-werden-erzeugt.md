# 0057 — Die Zeichennamen im Add-on werden erzeugt, nicht gepflegt

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:** [0055](0055-entwurfsbuch-status-und-sperre.md),
[0051](0051-gesendet-sperre-und-postfach-entwurf.md)

## Anlass

Die Sperre beim Senden (ADR 0055) und die Prüfung vor dem Entwurf (ADR 0051) müssen dieselbe Mail
gleich beurteilen. Dafür gibt es zwei Fassungen derselben Regel: `vergleich.js` im Add-on und
`gesendet.py` in falzmarke. `tests/test_vergleich_js.py` hält sie zusammen.

Am 25.10.2026 wurde gemessen, dass sie bei HTML auseinanderlaufen. `vergleich.js` trug eine
Tabelle von zwanzig HTML-Zeichennamen und gab einen unbekannten Namen **unverändert** zurück;
Python löst über `html.unescape` 2231 Namen auf. Dieselbe Eingabe, zwei Textkerne:

```
<p>Preis &ndash; 5 &euro;, Bedingung &copy; 2026 &amp Rest</p>
gesendet.py   → 'preis5bedingung2026rest'
vergleich.js  → 'preisndash5bedingungcopy2026amprest'
```

Wirksam wird das bei einer **HTML-only**-Mail im Gesendet-Ordner — vom Telefon, aus Webmail.
Dann gehen beide Seiten in ihren HTML-Pfad, und die Sperre schweigt, wo `status` „SCHON RAUS“
sagt. Der Paritätstest konnte das nicht sehen: Seine HTML-Fälle benutzten ausschließlich Namen,
die **in** der Tabelle standen. Ein Prüfmittel, das nie rot werden kann, ist kein Nachweis.

## Entscheidung

1. **Die ganze Tabelle, erzeugt.** `scripts/zeichennamen.py` schreibt
   `thunderbird/entwurfsbruecke/zeichennamen.js` aus `html.entities.html5` und den beiden
   Ausnahmetabellen von `html.unescape`. Nicht von Hand ändern; `--pruefen` meldet Veralten.
2. **Der Algorithmus wird übertragen, nicht erzeugt.** `entschluesseln()` in `vergleich.js` ist
   eine Übertragung von `html.unescape`: dasselbe Muster, dieselben Ausnahmen für
   Zahlenverweise, dieselbe Längstübereinstimmung bei einem Namen ohne Semikolon. Nur die Daten
   kommen aus der erzeugten Datei.
3. **Geprüft wird über alle Namen, nicht über eine Auswahl.**
   `test_js_loest_jeden_zeichennamen_auf_wie_python` gibt jeden der 2231 Namen und 29 Grenzfälle
   an beide Seiten. Dazu fünf Gegenproben: zwei am Tabelleninhalt, drei am Algorithmus.

### Warum nicht „unbekannte verwerfen“

Das war der erste Entschluss, und er ist gemessen falsch. Der Textkern besteht aus Buchstaben und
Ziffern; ein Zeichenname hat deshalb drei mögliche Ausgänge, und nur mit derselben Tabelle sind
sie zu unterscheiden:

| Eingabe | Was Python daraus macht | Im Textkern |
|---|---|---|
| `&ndash;` `&copy;` `&euro;` | ein Satzzeichen | fällt ganz weg |
| `&ntilde;` `&oelig;` | ein Buchstabe | bleibt als dieser Buchstabe |
| `&gibtsnicht;` | nichts, bleibt Text | bleibt als eigenes Wort |

„Verwerfen“ hätte die erste Zeile gerichtet und für die zweite und dritte eine **neue**
Abweichung erzeugt: `Se&ntilde;or` wäre in JS zu „seor“ geworden, `&gibtsnicht;` zu nichts.
Gemessen an zehn Eingaben: alte Fassung fünf Abweichungen, erzeugte Tabelle null.

### Was hingenommen wird

- **Die Datei ist 48 KB groß** und liegt im `.xpi`. Das ist der Preis dafür, dass die Parität
  über die ganze Tabelle belegt ist und nicht über eine Stichprobe.
- **Die Tabelle hängt an der Python-Fassung, die sie erzeugt hat.** Gemessen am 25.10.2026 sind
  die drei Tabellen in Python 3.11 bis 3.15 byte-gleich (2231/34/126 Einträge, gleicher SHA-256
  der sortierten Namen); ein byte-genauer Test ist über die CI-Matrix deshalb tragfähig. Ändert
  eine künftige Fassung die Tabelle, wird der Test rot — das ist die Meldung, nicht der Fehler.
- **`casefold()` bleibt die bekannte Abweichung.** Python faltet auch Ligaturen und das lange s,
  `vergleich.js` nur `ß`. Das stand schon vorher im Kopf von `vergleich.js` und ist nicht Teil
  dieser Entscheidung.

## Belege

- Differenzmessung am 25.10.2026, zehn HTML-Eingaben durch `node vergleich.js` und durch
  `gesendet.py`: alte Fassung **5 von 10** abweichend (`&ndash;`, `&ntilde;`, `&amp` ohne
  Semikolon, `&notit;`, eine Mischung aus Anführungszeichen und Zeichen), neue Fassung **0 von
  10**. Dieselbe Messung ist die Gegenprobe: Sie schlägt an der alten Datei an.
- Fünf Sabotagen laufen einzeln gegen den Paritätstest und werden alle rot: ein geänderter
  Tabellenwert, ein entfernter Name ohne Semikolon, die fehlende Längstübereinstimmung, die
  übergangene Ausnahmetabelle für Zahlenverweise, die übergangene Liste verbotener Stellen.
- `tests/test_zeichennamen.py` sabotiert die ausgelieferte Datei selbst und nimmt sie zurück;
  eine dritte Probe belegt, dass der Sollwert aus `html.entities` kommt und nicht aus der Datei
  daneben.
