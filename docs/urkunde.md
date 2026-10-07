# Urkunden mit falzmarke

Ein Schreiben mit `typ: urkunde` im Frontmatter ist kein Brief. Es hat kein Anschriftfeld,
keinen Betreff, keine Anrede und keinen Gruß — dafür einen Titel, auf Wunsch zwei Parteien und
Linien zum Unterschreiben von Hand. Gemeint sind Schriftstücke, die für sich stehen: eine
Vereinbarung, eine einseitige Erklärung, ein Nachweis, eine Vollmacht.

Warum es dafür einen eigenen Typ gibt und keinen Brief mit abschaltbarem Anschriftfeld, steht in
[ADR 0048](entscheidungen/0048-urkunde-ein-schriftstueck-ohne-anschriftfeld.md); wie die Felder
aussehen, in [„Urkunde"](../skill/references/frontmatter.md#urkunde). Diese Seite sagt, was am
fertigen Blatt dabei herauskommt — und was nicht.

```bash
falzmarke render vereinbarung.md --png    # setzt, misst nach, zeigt die Vorschau
falzmarke verify vereinbarung.pdf         # misst die fertige Datei noch einmal
```

## Was das Blatt mit dem Brief teilt

Briefkopf, Fußzeile, Schrift und Farbe kommen aus demselben Profil. Die Ränder sind dieselben
(links 25 mm, rechts 20 mm), der Text steht auf demselben 12-pt-Raster, und eine Folgeseite
trägt eine Kopfzeile und „Seite 2 von 3". Zwei Blätter desselben Absenders sehen
nebeneinandergelegt aus wie aus einer Hand.

## Was anders ist

| | Brief | Urkunde |
|---|---|---|
| Über dem Text | Anschriftfeld, Informationsblock, Betreff, Anrede | Titel in 16 pt, auf Wunsch die Parteien in 12 pt, eine Linie über die Satzbreite |
| Kopfhöhe | nach der Form: 27 mm (A) oder 45 mm (B) | nach dem Briefkopf: 27 mm, wenn er hineinpasst, sonst 45 mm |
| Falz- und Lochmarken | ja | nein — es gibt kein Fenster, auf das zu falten wäre |
| Unter dem Text | Gruß, Unterschriftsraum, Name | Zeile für Ort und Datum, ein oder zwei Unterschriftslinien |
| Gliederung | Betreff, dann Überschriften ab `#` (mit `dialekt: "1.1"`) | der Titel ist die erste Ebene, Abschnitte ab `##` (mit `dialekt: "1.2"`) |
| Seitenzahl | so viele, wie der Text braucht | auf Wunsch begrenzt: `seiten_max:` |

**`dialekt: "1.2"` gehört in jede Urkunde.** Ohne das Feld gilt auch hier Fassung 1.0, und die
kennt weder Abschnittsüberschriften noch Ausfüllfelder. `falzmarke init --typ urkunde` schreibt
das Feld in die Vorlage.

## Kopf, Blocksatz und Paraphen

Der Kopf folgt dem Vertrag zwischen Bund und DIN von 1975, wie er als Abdruck auf din.de steht:
ein großer Titel ohne Fett, die Parteien in etwas größerer Schrift als der Text, darunter eine
Linie über die Satzbreite. Das Dokument ist ein Vorbild für die Gestaltung, keine Norm.

Mit `blocksatz: true` steht der Text im Blocksatz. Das ist Gestaltung: Gegen nachträgliche
Einfügungen schützt Blocksatz nicht, das täte nur ein Blatt ohne Leerräume.

Mit `paraphen: true` steht bei mehr als einer Seite auf jeder Seite außer der letzten neben der
Seitenzahl je Unterschrift ein Feld „Paraphe“. Die Initialen zeigen, dass die Blätter
zusammengehören; was das rechtlich bewirkt, sagt falzmarke nicht.

**Nicht übernommen** aus verbreiteten Layoutempfehlungen für Verträge: eine Pflicht zu
serifenloser Schrift (die Schrift kommt aus dem Profil) und 1,15- oder 1,5-zeiliger Satz (er
bräche das 12-pt-Raster, das Brief und Urkunde teilen).

## Ausfüllfelder und Angaben

Beides gehört zu [Dialekt 1.2](../skill/references/markdown.md#was-nur-fassung-12-setzt) und
geht auch im Brief.

Ein **Ausfüllfeld** ist eine Kette aus Unterstrichen im Text: `Übergeben am: ______________`.
Daraus wird eine Linie fester Länge, 2 mm je Unterstrich — unabhängig von der Schrift, und sie
bricht nicht mitten durch um. Sie ist für einen Stift gedacht; ein Formularfeld, das ein Programm
ausfüllt, ist sie nicht.

Eine **Angabentabelle** ist eine Tabelle mit leerer Kopfzeile: links die Bezeichnung, rechts
der Wert, ohne Rahmen. Die linke Spalte ist so breit wie ihr längster Eintrag.

## Was gemessen wird

`render` misst die fertige Urkunde, und `verify` kann es an der Datei wiederholen. Dass sie
eine Urkunde ist, steht als Vermerk im PDF, zusammen mit der Kopfhöhe, der Zahl der
Unterschriften und der erlaubten Seitenzahl.

| Prüfung | Was sie misst |
|---|---|
| Seitengröße, Satzspiegel, Zeilenraster, Schriften | wie beim Brief, mit denselben Funktionen |
| Keine Marken im Heftrand | das Blatt ist kein Brief |
| Seitenzahl | höchstens `seiten_max`; ohne das Feld nennt der Bericht nur die Zahl |
| Titel | 16 pt, am linken Rand, zwei Leerzeilen unter dem Kopf |
| Kopf | Parteien in 12 pt, darunter eine Linie über die Satzbreite |
| Paraphen (mit `paraphen: true`) | je Unterschrift ein Feld auf jeder Seite außer der letzten |
| Linien im Satzspiegel | keine waagerechte Linie reicht über die Ränder — auch kein Ausfüllfeld |
| Unterschriftslinien | Anzahl, 65 mm Länge, auf der letzten Seite, gleiche Höhe, mindestens 10 mm Abstand, drei Zeilen Raum darüber, der Name darunter |

Der Vermerk ist eine Behauptung der Datei. Ein Brief, der sich als Urkunde ausgibt, fällt an
seinen Falzmarken auf, und `verify --form A` oder `--form B` erzwingt die Prüfliste des
Briefes.

## Was ausdrücklich nicht behauptet wird

- **Die Maße der Urkunde stammen nicht aus der DIN 5008.** Die Norm beschreibt den
  Geschäftsbrief. Zu einem Blatt ohne Anschriftfeld, zu Unterschriftslinien und zu einer
  Obergrenze für die Seitenzahl sagt keine der geführten Quellen etwas. Es sind Setzungen des
  Werkzeugs, und so stehen sie im [Regelkatalog](../skill/falzmarke/regeln/urkunde.yaml).
- **Keine Aussage über Form oder Wirksamkeit.** Der Name beschreibt, wie das Blatt aussieht.
  Ob ein Schriftstück eine gesetzliche Form wahrt, etwas beweist oder wirksam ist, entscheidet
  nicht falzmarke. Die Unterschriftslinie ist Erscheinungsbild, kein Nachweis.
- **Keine Inhalte.** falzmarke kennt keine Klauseln und keine Muster. Die festen Wörter des
  Werkzeugs sind „zwischen", „und" und „Ort, Datum"; alles andere schreibt der Verfasser. Die
  Beispiele zeigen die Form — sie sind keine Vorlage für einen Vertrag und keine Rechtsberatung.
- **Keine Zertifikate.** „Urkunde“ meint hier ein unterschriebenes Schriftstück, keine
  Ehren- oder Teilnahmeurkunde auf Karton oder in A3.
- **Keine digitale Signatur.** Siehe [#14](https://github.com/blitzsicht/falzmarke/issues/14)
  (Digitale Signatur des PDF, PAdES).

## Grenzen

Höchstens zwei Parteien und zwei Unterschriften, nebeneinander. Kein Signaturbild. Keine
E-Mail-Fassung und kein Serienlauf — `email` und `serie` brechen mit einer Meldung ab. In der
Angabentabelle sind die Bezeichnungen im PDF gewöhnliche Zellen, keine Zeilenköpfe: Die
Satzmaschine kennt in der eingesetzten Fassung keine Kopfzelle je Zeile.

## Beispiele

Zwei Musterdokumente liegen unter [`examples/urkunde/`](../examples/urkunde/): eine
Vereinbarung zwischen zwei Parteien und eine einseitige Erklärung mit Angabentabelle und
Ausfüllfeldern. Alle Angaben darin sind erfunden.
