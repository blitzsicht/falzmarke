# Sagt diese Quelle zur Regel überhaupt etwas? — Prüfung vom 27.08.2026

[Issue #31](https://github.com/blitzsicht/falzmarke/issues/31) hält fest: Die Validierung prüft,
ob eine Regel ihre **Zählstufe** trägt — nicht, ob die genannte Quelle zur Sache etwas hergibt.
Für `wikipedia` war das nachgelesen; für `onlineprinters` stand es aus. Betroffen waren
25 Regeln.

Hier steht das Ergebnis. Es ändert **keine Stufe** und entfernt **keine Quelle**.

## Wie geprüft wurde

Der Artikel wurde vollständig gelesen — 7.035 Zeichen, nicht mit Stichwortsuche abgeklopft.
Das ist der Punkt: #31 warnt ausdrücklich davor, dass ein Treffer für „Datum" auch das
Beispieldatum in der abgebildeten Zeichnung sein kann.

Ein Beispiel dafür, warum das nötig war: „Anlage" kommt im Artikel genau einmal vor — in
*„Die Durchwahl wird mit Bindestrich an die **Anlagen**nummer angehängt"*. Das ist die
Telefonanlage. Eine Stichwortsuche hätte `text.anlagen_ohne_doppelpunkt` als belegt gemeldet.

**Negativbefunde sind gegen das rohe HTML gegengeprüft**, nicht nur gegen den extrahierten Text:
Wörter wie „Dreiergruppen", „geschützt", „Komma" und „Leerzeile" kommen in den 240 KB Quelltext
der Seite **null Mal** vor. Damit hängt der Befund nicht an der Textextraktion — die Sorge aus
#31, die Seite sei JS-lastig, ist für diese Wörter ausgeräumt. Gegenprobe in die andere Richtung:
Sätze, die im Artikel stehen („Postfachnummer", „Vierergruppen", „Bestimmungsland"), finden sich
auch im HTML. Der Text wird also nicht nachgeladen.

## Was die Quelle trägt

| Regel | Fundstelle |
|---|---|
| `schreibweise.telefon` | „+49 89 8521476", Durchwahl mit Bindestrich; national „09161 6209800", „09161 620980-XX", Sondernummern |
| `schreibweise.postfach` | „von rechts beginnend zweistellig gegliedert", Beispiel 89 09 32 |
| `schreibweise.iban` | Vierergruppen von links, Rest als Zweiergruppe, Beispiel DE62 7625 … |
| `schreibweise.uhrzeit` | „Nicht 11.30 Uhr, sondern 11:30 Uhr ist richtig" |
| `schreibweise.auslandsanschrift` | Ort und Land in Großbuchstaben, Ort in der Landessprache (FIRENZE), Land deutsch in der letzten Zeile, kein Länderkennzeichen |

Fünf Regeln, sauber belegt. Die Fundstellen stehen jetzt in der Regeldatei unter `belegt_durch:`.

## Was die Quelle nicht trägt

| Regel | wirkt als | warum nicht |
|---|---|---|
| `schreibweise.datum` | **Fehler** | „korrekte Schreibweisen von Datum" nur als Thema genannt, kein Format |
| `schreibweise.abkuerzungen` | **Fehler** | „die richtige Abkürzung von Titeln" als Thema, keine Schreibregel |
| `text.vermerke_max_3` | **Fehler** | Zonen erwähnt, Zeilenzahl nicht |
| `schreibweise.zahlengliederung` | Warnung | „Dreiergruppen" steht nicht auf der Seite |
| `schreibweise.geldbetrag` | Warnung | „Währungen" als Thema; das Kürzel „EUR" steht nirgends |
| `schreibweise.einheiten` | Warnung | nicht erwähnt |
| `text.anrede_komma` | Warnung | „Komma" steht nicht auf der Seite |
| `text.gruss_ohne_komma` | Warnung | „Grußformel" nur im Titel eines verwandten Artikels |
| `text.anlagen_ohne_doppelpunkt` | Warnung | einziger Treffer gehört zur Telefonanlage |
| `text.anschrift_ohne_leerzeilen` | Warnung | „Leerzeile" steht nicht auf der Seite |

## Was daraus folgen würde

**Die beiden Fehler-Regeln stehen nicht ohne Beleg da.** `schreibweise.datum` und
`schreibweise.abkuerzungen` tragen ihre Begründung ausdrücklich über Wikipedia — die Bemerkungen
nennen das seit jeher („Wikipedia nennt beide Formen ausdrücklich", „nennt „a. a. O., d. h.,
v. l. n. r., z. B." wörtlich"). Fällt `onlineprinters` weg, bleibt eine volle Quelle: Stufe
`einzeln_belegt`, Wirkung Warnung statt Fehler.

`text.vermerke_max_3` ist ohnehin **abgeleitet**, nicht zitiert: 12,7 mm Zonenhöhe bei 4,23 mm
Zeilenhöhe ergibt drei Zeilen. Das ist eine Rechnung aus zwei anderen Regeln, keine
Quellenaussage.

**Sechs Warnungen hätten gar keinen Beleg mehr** — `onlineprinters` ist bei ihnen die einzige
Quelle, und keine trägt eine Bemerkung mit einer anderen Herleitung:

```
schreibweise.zahlengliederung   text.gruss_ohne_komma
schreibweise.geldbetrag         text.anlagen_ohne_doppelpunkt
schreibweise.einheiten          text.anschrift_ohne_leerzeilen
```

Nach dem Datenmodell wären sie `offen` — und `offen` heißt: wird nicht geprüft. Ob diese sechs
Schreibregeln also verschwinden, aus einer anderen Quelle belegt oder bis zum Normabgleich als
ungeprüft geführt werden, ist eine Entscheidung und steht in #31.

## Nicht geprüft

44 weitere Quelle-Regel-Paare tragen noch kein `belegt_durch:` — darunter alle
Geometrie-Regeln, deren Beleg die **Zeichnung** ist und nicht der Artikeltext. Für sie gilt ein
anderer Maßstab: Eine Maßzeichnung sagt zu einem Maß etwas, zu einer Schreibregel nichts.
Nachgemessen ist sie im Einzelnen noch nicht.

`tests/test_quellenlage.py` hält die Zahl fest, damit sie fällt und nicht steigt.
