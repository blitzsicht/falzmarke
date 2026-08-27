# Zwei Maßzeichnungen, eine Quelle — Befund vom 27.08.2026

Die Regeldatei führt `massskizze_b` (Wikimedia Commons) und `onlineprinters` (Onlineprinters-
Magazin) als zwei Quellen. Neun Regeln stützen ihre Stufe **mehrfach bestätigt** auf genau dieses
Paar — die Stufe, die einen Lauf scheitern lassen darf.

Dieser Befund zeigt: Es sind keine zwei unabhängigen Belege.

Er ändert **nichts** an den Stufen. Was daraus folgt, ist ein eigener Schritt und eine eigene
Entscheidung; hier steht nur, was gemessen wurde.

## Die beiden Zeichnungen

| | Wikimedia Commons | Onlineprinters-Magazin |
|---|---|---|
| Datei | `File:DIN_5008_Form_B.svg` | `Vorlage_Geschaeftsbrief_DIN-5008_Form-B.jpg` |
| Hochgeladen | 02.04.2013, Benutzer „Flamon" | Pfad nennt Juli 2021 |
| Lizenz | **CC0**, als eigenes Werk angegeben | keine Angabe |
| Format | SVG, Text in Pfade konvertiert | JPEG, 599 × 846 |

## Nachfahren

Beide Dateien sind öffentlich abrufbar. Sie liegen **nicht** im Repository — die
Onlineprinters-Zeichnung ist urheberrechtlich geschützt, und für einen Befund über Herkunft
reicht der Vergleich:

```bash
# Die echte Upload-Adresse der Wikimedia-Datei über die API, nicht geraten:
curl -sSL "https://commons.wikimedia.org/w/api.php?action=query\
&titles=File:DIN_5008_Form_B.svg&prop=imageinfo&iiprop=url|user|timestamp|extmetadata&format=json"

curl -sSL -o wikimedia.svg \
  "https://upload.wikimedia.org/wikipedia/commons/0/00/DIN_5008_Form_B.svg"
rsvg-convert -w 700 -o wikimedia.png wikimedia.svg

curl -sSL -o onlineprinters.jpg -H "User-Agent: Mozilla/5.0" \
  "https://www.onlineprinters.de/magazin/wp-content/uploads/2021/07/Vorlage_Geschaeftsbrief_DIN-5008_Form-B.jpg"
```

Dann nebeneinanderlegen.

## Was übereinstimmt

- **Bemaßungsstruktur**: dieselben Maßpfeile an denselben Stellen — links 45 / 105 / 20 / 45 /
  148,5 / 87, oben 125 / 50, rechts 20 / 10 / 75.
- **Zahlenwerte** durchgängig gleich, einschließlich der ungewöhnlichen Nachkommastellen:
  17,7 · 27,3 · 80 · 85 · 8,46 · 25 · 4,23.
- **Beschriftungen** wortgleich: „Feld für Briefkopf, Form B", „Anschriftzone", „Faltmarke 1",
  „Faltmarke 2", „Lochmarke", „Seite x von y (Bei mehrseitigen Texten)".
- **Informationsblock**: dieselbe Zeilenfolge — Ihr Gesprächspartner / Abteilung / Telefon /
  Telefax / E-Mail / Datum.
- **Der Fußtext ist wortgleich**, über vier Zeilen:

  > Gesellschaftsrechtliche Angaben: Firmenname und Rechtsform, Sitz der Gesellschaft, Telefon,
  > Telefax, E-Mail, Internet (sofern nicht im Informationsblock), Bankverbindungen, USt-IdNr.,
  > Vorstandsmitglieder bzw. Geschäftsführung, Vorsitzende(r) des Aufsichtsrats, Eingetragen beim
  > Amtsgericht Ort, HRB-Nummer

  Das ist der stärkste Einzelbeleg. Eine Norm gibt vor, *welche Angaben* nötig sind — nicht diese
  Aufzählung in dieser Reihenfolge mit diesen Einschüben. So ein Satz entsteht nicht zweimal
  unabhängig gleich.

## Was sich unterscheidet

Nur Zutaten: Logo, graue Flächen, Beschriftungen im Textfeld („Betreff", „Anrede", „Grußformel",
„Anlage(n)"), der Hinweis „variabel gestaltbarer Informationsblock", die zusätzlich eingetragene
Betreffposition 103,46 mm — und ausgetauschte Musterdaten (2013 „Christian Schmidtberger,
muster-institut-hh.de" → 2021 „Max Mustermann, onlineprinters.de", Datum 2013-04-30 → 2021-07-20).

## Was daraus folgt — und was nicht

**Belegt ist:** Die beiden Zeichnungen sind nicht unabhängig voneinander entstanden.

**Nicht belegt ist die Richtung.** Die Wikimedia-Datei ist acht Jahre älter und steht unter CC0 —
eine Übernahme wäre ausdrücklich erlaubt und völlig legitim. Aber ob die jüngere von der älteren
abstammt oder beide auf eine dritte Vorlage zurückgehen, sagt dieser Vergleich nicht.

**Für die Frage der Beleglage ist das gleichgültig.** In beiden Fällen sind es nicht zwei
unabhängige Quellen, und die Stufe „mehrfach bestätigt" verlangt genau das.

Kein Vorwurf an irgendwen: CC0 heißt, dass Weiterverwendung ohne Nennung vorgesehen ist. Der
Fehler liegt bei uns — zwei Ansichten derselben Sache wurden als zwei Belege gezählt. Das ist die
Verwechslung von Kanal und Darstellung.

## Betroffen

Neun Regeln stehen auf `massskizze_b` + `onlineprinters`. Zwei weitere stehen auf
`massskizze_b` + `wikipedia` — zwei Projekte der Wikimedia Foundation, deren Unabhängigkeit
ebenfalls nicht geprüft ist:

| Regel | wirkt als |
|---|---|
| `geometrie.seitenformat` (A4, 210 × 297 mm) | Fehler |
| `geometrie.seitenraender` (25 / 20 mm, Textbreite 165 mm) | Fehler |

Die genaue, stets aktuelle Liste erzeugt `tests/test_quellenlage.py`; sie ist dort als erwarteter
Stand festgehalten, damit sie sich nicht unbemerkt ändert.

## Verwandt

- [`skill/falzmarke/regeln/din5008.yaml`](../skill/falzmarke/regeln/din5008.yaml) — die Quellen
  tragen jetzt eine `gruppe:`; Quellen derselben Gruppe sind kein zweiter Beleg.
- [`docs/recht.md`](recht.md) — was die Stufen bedeuten.
- [`docs/normmasse.md`](normmasse.md) — woher die Maße stammen.
