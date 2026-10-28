# 0060 — Der Anker der Zuordnung hat zwei Wege und nennt seinen

**Datum:** 28.10.2026 · **Status:** angenommen ·
**Ergänzt:** [0055](0055-entwurfsbuch-status-und-sperre.md), Punkt zur Kette ·
**Nimmt nichts zurück:** [0054](0054-entwurfsbruecke-in-thunderbird.md) und
[0056](0056-entwurfsbruecke-empfaenger-und-fassung.md) bleiben in Kraft, einschließlich des
Verbots, in die ausgehende Mail zurückzuschreiben

## Anlass

`falzmarke status` beantwortet „ist das raus, und ging genau das raus?" aus drei Quellen —
Entwurfsbuch, Postfach, Tagebuch der Entwurfsbrücke. Die Zuordnung zwischen ihnen hängt an
**einer** Zahl: `ursprung.uid` im Tagebuch. Fehlt sie, hängt die Versandzeile an keinem Eintrag
des Entwurfsbuchs: kein „Ging an … · Empfänger wie angelegt", kein `BELEGT`, und die Sendesperre
erkennt den Entwurf nicht über seine Fassung. Genau das ist #420.

Gezählt am Tagebuch dieses Rechners am 28.10.2026 — 258 Zeilen, geschrieben von den Fassungen
0.3.3 bis 0.3.6:

| Befund | Zahl |
|---|---|
| `geoeffnet` mit `typ: "draft"` **und** UID | 117 |
| `typ: "draft"`, aber **weder** UID **noch** Fassung — der Fall aus #420 | 1 Paar (`geoeffnet` 26.10. 11:03:52, `gesendet` 11:04:26) |
| `typ: "draft"` mit UID, aber ohne Fassung | 1 Paar (UID 1172) |
| `typ: "new"` / `typ: "reply"` — von Natur aus ohne UID | 3 + 3 |

Drei Dinge stehen damit fest. `typ` ist in dem Fall **„draft"**, der Zweig im Hintergrundskript
wird also betreten. `kennung()` scheitert **nicht systematisch**, sonst stünden nicht 117 Zeilen
mit UID daneben. Und die Kette selbst fehlt nicht: `_kette()` verbindet
`gespeichert.ursprung.uid` mit `neu_uid` und ist durch Tests gedeckt.

Was fehlt, ist der **Anker** der Kette. `ursprung.uid` entstand aus genau einem Aufruf — ohne
Rückfallebene und ohne Grundangabe —, und `ursprung.fassung` nur aus der Kopfzeile
`X-Falzmarke-Fassung`, die Thunderbird beim Speichern wegwirft.

**Warum `kennung()` in dem einen Fall `null` lieferte, ist mit dieser Entscheidung nicht
erklärt.** Es ist umgangen und künftig benannt.

## Entscheidung

1. **Zwei Wege zur UID, und gemessen werden immer beide.** Weg 1 bleibt
   `messageManager.get(relatedMessageId).messageKey` (bei IMAP ist das die UID, ADR 0055). Weg 2
   ist neu: `gMsgCompose.compFields.draftId` am Verfassen-Fenster, Anfrageteil abgeschnitten,
   `#(\d+)$` gelesen — **dieselbe Regel**, über die `status` offene Fenster schon heute per UID
   findet. Beide Ergebnisse stehen bei jedem Öffnen im Tagebuch (`uid_kennung`, `uid_draft_id`),
   nicht nur das verwendete. Ein Lauf, der den Fehler nicht auslöst, würde den Fallweg sonst
   nicht belegen: Der Fall trat in 258 Zeilen **einmal** auf. So belegt ein normaler Lauf den
   zweiten Weg, ohne den Fehler erzwingen zu müssen. **Dieselbe** Zahl tragen beide nur beim
   ersten Öffnen — nach einer Speicherung durch Thunderbird gehen sie auseinander, und das ist
   richtig so (siehe Nachtrag).
2. **Der Eintrag nennt, welcher Weg getragen hat und warum der andere nicht.** `uid_quelle` ist
   `"kennung"` oder `"draft_id"`, `uid_grund` nennt den Ausfall in einem Wort — `kein_related`,
   `kennung_null`, `kennung_wurf`, `kein_fenster`, `kein_draft_id`, `draft_id_ohne_uid`. **Diese
   Diagnose bleibt stehen**, sie ist kein Gerüst für eine Messung: Das Tagebuch ist die einzige
   Stelle, an der ein Rückfall überhaupt zu sehen wäre. Die Fehlerdatei trägt absichtlich keine
   UIDs (ADR 0059, Punkt 4), und `protokoll` steht nur im Speicher.
3. **Ein zweiter Anlauf vor dem Senden.** Blieb die UID beim Öffnen leer, wird sie in
   `onBeforeSend` erneut aufgelöst — dort liegt `relatedMessageId` vor, und der Eintrag
   `gesendet` ist der, auf den es für `status` ankommt. Schon geschriebene Zeilen bleiben
   unberührt; folgende tragen die Werte.
4. **Die Fassung kommt aus der Kette, nicht aus einer zurückgeschriebenen Kopfzeile.** Ist
   `fassung` leer und die UID bekannt, liest das Add-on einen Auszug des Tagebuchs, bildet die
   Kette und nimmt die jüngste Zeile darin mit nichtleerer `ursprung.fassung` →
   `fassung_quelle: "kette"` statt `"kopf"`. Zurückschreiben über die Rückgabe von
   `onBeforeSend` wäre der kürzere Weg und bleibt verboten (ADR 0054, ADR 0056).
5. **Der Konto-Filter in der Kette ist nicht Kosmetik.** Eine UID gilt je Ordner. Ohne ihn kettet
   UID 150 von Konto A an UID 150 von Konto B. Deshalb ist `kette()` in `vergleich.js` ein
   Zwilling von `_kette()` — mit demselben Filter, und gegen die Python-Fassung auf denselben
   JSON-Zeilen geprüft.
6. **Scheitert die Diagnose, geht die Mail hinaus.** Der Grund steht im Eintrag. Eine Diagnose,
   die scheitert, darf den Menschen nicht aufhalten (ADR 0055).
7. **`status` meldet einen Eintrag, der sich nicht zuordnen lässt.** Genau die Signatur aus #420
   — `typ: "draft"`, keine UID, keine Fassung — wird zur `HINWEIS`-Zeile, mit dem Hinweis auf
   `uid_grund` ab 0.3.7. `typ: "new"` und `typ: "reply"` haben von Natur aus keine UID und zählen
   nicht. Die Zahl steht auch in `--json`.

### Die Zahl der Experiment-Funktionen bleibt fünf

`kennung` wird zu `entwurfskennung`, `fassungen` zu `tagebuchauszug` — ersetzt, nicht ergänzt.
`tests/test_entwurfsbruecke.py` hält die Positivliste und ihre Zahl fest; eine wachsende
Experiment-Fläche ist der teuerste Teil dieses Add-ons, weil sie mit Chrome-Rechten läuft.

`tagebuchauszug()` liefert **weniger** Daten als heute die Datei: nur
`{ art, zeit, message_id, neu_uid, ursprung: { konto, uid, fassung } }`, kein Betreff, keine
Empfänger. Die **Form** bleibt die des Tagebuchs — das ist der Punkt, denn nur so bekommen
`kette()` und `_kette()` dieselbe Struktur und sind gegeneinander prüfbar.

## Was hingenommen wird

- **Die Rückgewinnung der Fassung setzt voraus, dass das *erste* Öffnen des Entwurfs mit UID im
  Tagebuch steht.** Ist schon dort beides leer, findet auch die Kette nichts. Der zweite Weg zur
  UID macht genau diesen Fall seltener, schließt ihn aber nicht aus.
- **Frage 2 aus #420 bleibt offen.** Im Gerätelauf vom 28.10.2026 stand `uid_quelle` in allen
  acht Zeilen auf `"kennung"` und `uid_grund` durchgehend leer — der Fallweg wurde also nicht
  ausgelöst, und warum `kennung()` am 26.10. `null` lieferte, ist weiter unbekannt. Tritt der
  Fall wieder auf, nennt `uid_grund` ihn beim Namen. Das ist der Unterschied zu vorher, nicht
  eine Erklärung.
- **Den Vorrang selbst prüft kein Test der Suite.** Er sitzt in `entwurfskennung` im
  Chrome-Teil, und dort kann kein Test laufen (wie ADR 0059, Punkt 3 für den Transport). Die
  Attrappe im node-Lauf baut ihn nach — sie belegt, dass `ankern` die Felder unverfälscht
  weiterträgt, nicht dass der Vorrang stimmt. Dafür steht allein der Gerätelauf.
- **`draftId` ist kein öffentliches WebExtension-Feld.** Es kommt über `nativeTab` aus dem
  Chrome-Teil, wie `fragen()` es schon tut. Ändert Thunderbird die Form der Adresse, fällt Weg 2
  aus — sichtbar an `uid_grund: "draft_id_ohne_uid"`, nicht still.
- **Der Konto-Filter und die Kette schirmten sich im Attrappen-Lauf gegenseitig ab.** Zwei
  Sabotagen blieben grün, obwohl sie je eine Prüfung trafen; erst der direkte Vergleich der
  JS- gegen die Python-Fassung macht sie rot. Das steht in den Belegen, weil es die Art Lücke
  ist, die ein Prüfmittel wertlos macht, ohne dass ein Test rot wird.

## Belege

- Die Zählung oben, am Tagebuch dieses Rechners (258 Zeilen), nicht geschätzt.
- Sieben Sabotagen, **jede einzeln** gefahren, Rücknahme je per `sha256` verglichen, pytest-ID
  je vorher benannt: beide UID-Wege entfernt · der zweite Anlauf in `onBeforeSend` entfernt ·
  Konto-Filter in `fassungAusKette` entfernt · Vorrang der Kopfzeile aufgehoben ·
  Konto-Filter in `kette()` entfernt · Transitivität auf einen Durchgang gekürzt ·
  Listenprüfung an `neu_uid` entfernt.
- Zwei dieser Sabotagen — `fassungAusKette` ohne Konto-Filter und `kette()` ohne Konto-Filter —
  blieben am Attrappen-Lauf grün. Die erste führte zu einer neuen Probe (dieselbe UID unter
  fremdem Konto), die zweite zum Vergleich gegen `_kette()` in `tests/test_vergleich_js.py`. Erst
  danach war jede der sieben rot.
- Suite **4290 bestanden / 11 übersprungen** (vorher 4263/11).
- Der Gerätelauf, gefahren am 28.10.2026 mit installiertem 0.3.7 (`ping` meldet 0.3.7 in
  Thunderbird 158.0.1). Was die alte Fassung nicht erzeugen kann: `uid_draft_id`, `uid_quelle`,
  `uid_grund` und `fassung_quelle` gibt es in 0.3.6 nicht, und `fassung` war bei einem von
  Thunderbird gespeicherten Entwurf leer. Der Lauf ist deshalb Beleg, nicht Bestätigung.

## Nachtrag 28.10.2026 — am Gerät gemessen

Probe „Probe UID-Anker 0.3.7" an die eigene Adresse, acht Tagebuchzeilen:

| Zeit | `art` | `uid` | `uid_kennung` | `uid_draft_id` | `fassung_quelle` |
|---|---|---|---|---|---|
| 16:57:07 | `geoeffnet` | 1218 | 1218 | 1218 | `kopf` |
| 17:02:47 | `gespeichert` | 1218 | 1218 | 1218 | `kopf` (`neu_uid` 1219) |
| 17:05:10 | `gespeichert` | 1218 | 1218 | 1218 | `kopf` (`neu_uid` 1220) |
| 17:05:21 | `geoeffnet` | 1218 | 1218 | **1220** | **`kette`** |
| 17:06:50 | `gesendet` | 1218 | 1218 | 1220 | `kette` |

**1. Weg 2 trägt.** Beim ersten Öffnen meldeten beide Wege 1218 — dieselbe Zahl, bei einem
gewöhnlichen Lauf, ohne den Fehler zu erzwingen. Genau das war der Zweck von Punkt 1.

**2. Die Fassung kam über die Kette.** Beim Öffnen des neu angelegten Entwurfs war
`X-Falzmarke-Fassung` weg, und `fassung_quelle` sprang von `kopf` auf `kette`. Die Fassung
`d64377bad4ae` stand danach so im Eintrag `gesendet` wie im Entwurfsbuch. Das ist der Kern von
#420.

**3. Der Vorrang auf `kennung` ist richtig — gemessen, nicht gewählt.** Thunderbird legte den
Entwurf zweimal neu an und löschte die alten: Im Postfach lebte danach **nur** UID 1220, das
Entwurfsbuch kannte 1218. `kennung` meldete weiter 1218, also die Zahl, an der `status` die
Zeile aufhängt; `draft_id` meldete 1220, die lebende Nachricht. Beide sind über die Kette
1218 → 1219 → 1220 verbunden. Hätte `draft_id` den Vorrang, müsste `status` die Kette rückwärts
gehen, um in das Buch zu treffen. **Die Aussage „beide Wege tragen dieselbe Zahl" gilt also nur
vor der ersten Speicherung** — Punkt 1 ist entsprechend abgeschwächt, und
`test_am_geraet_gemessen_zeigt_kennung_aufs_buch_und_draft_id_auf_die_lebende` hält den Fall
fest.

**4. `status` zeigt, was #420 vermisste.** Nach dem Senden:

```
GESENDET  28.10. 17:57  „Probe UID-Anker 0.3.7" → servus@blitzsicht.com · 28.10. 18:06,
          Text unverändert · BELEGT
          Ging an servus@blitzsicht.com · Bcc — · Anhänge — · Empfänger wie angelegt
```

**5. Der Hinweis trifft den richtigen Referenten.** `ohne_zuordnung` meldete **2** Einträge, und
das sind die Zeilen 64 und 65 des Tagebuchs — `geoeffnet` 26.10. 11:03:52 und `gesendet`
11:04:26, beide „Empfängerprobe – nicht anfassen". Also genau das Paar aus der Diagnose, nicht
irgendwelche zwei Zeilen. Nachgezählt von Hand am echten Tagebuch, nicht aus dem Bericht
abgelesen.

**Drei Grenzen dieser Messung.** Der Fallweg `draft_id` wurde nicht ausgelöst (Punkt 2 unter
„Was hingenommen wird"). Der Vorrang ist nur hier belegt, nicht in der Suite. Und zwei Läufe
meldeten `schon_offen` und schrieben keine Zeile — das Messskript hielt die alte Zeile zunächst
für die neue, bis es den Tagebuchstand **vor** dem Öffnen nahm und bei ausbleibendem Wachstum
abbricht. Ein Messaufbau, der nicht wachsen kann, meldet sonst den letzten Fund als neuen.
