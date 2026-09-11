# Datenvertrag: das Frontmatter einer Briefdatei

Eine Briefdatei besteht aus YAML-Frontmatter zwischen zwei `---`-Zeilen und dem Brieftext
darunter.

```yaml
---
typ: brief                       # brief (Vorgabe) oder email — siehe „Die E-Mail-Fassung"
profil: example                  # Pflicht. Dateiname (ohne .yaml) aus ~/.config/falzmarke/profiles/
form: B                          # A oder B. Ohne Angabe gilt der Wert aus dem Profil
norm: din5008                    # reserviert; derzeit nur din5008
dialekt: "1.1"                   # 1.0 (Vorgabe, wenn das Feld fehlt) oder 1.1
sprache: de                      # de oder en. Beschriftung und Datum, nicht die Maße
empfaenger:                      # Pflicht. 1 bis 6 Zeilen, keine Leerzeilen
  - Muster GmbH                  # Reihenfolge: Firma, Person, Straße, PLZ Ort, [LAND]
  - Frau Erika Muster
  - Musterstraße 1
  - 12345 Musterstadt
vermerke:                        # optional, höchstens 3 Zeilen
  - Einschreiben mit Rückschein
datum: 2026-08-25                # Pflicht, ISO. Die Ausgabe bestimmt das Profil
betreff: Angebot Nr. 2026-0815   # Pflicht, höchstens 2 Zeilen, ohne Schlusspunkt
betreff_kurz: Angebot 2026-0815  # optional, für die Kopfzeile ab Seite 2
infoblock:                       # optional; Leitwörter erscheinen in der Reihenfolge der Norm
  ihr_zeichen: ABC-12
  ihre_nachricht_vom: 2026-08-20
  unser_zeichen: EM
  unsere_nachricht_vom: 2026-08-22
  ansprechpartner: Erika Muster  # erscheint als „Name"
  telefon: 0941 620-9800
  fax: 0941 620-9801
  email: muster@example.de
anrede: Sehr geehrte Frau Muster,       # endet mit Komma. Ohne Angabe: „Sehr geehrte Damen und Herren,"
gruss: Mit freundlichen Grüßen          # ohne Komma. Ohne Angabe: Wert aus dem Profil
unterzeichner: i. A. Erika Muster       # ohne Angabe: Wert aus dem Profil
signatur: keine                         # `keine` = von Hand unterschreiben;
                                        # oder eine Bilddatei neben dem Brief
anlagen:                                # optional, der Vermerk im Brief
  - Angebot 2026-0815
anlagen_dateien:                        # optional, PDFs hinten anhängen
  - angebot-2026-0815.pdf               # relativ zur Briefdatei
eingebettet:                            # optional, Dateien IM PDF (dann PDF/A-3b)
  - datei: rechnung.xml                 # relativ zur Briefdatei
    typ: text/xml                       # Pflicht, PDF/A-3b verlangt ihn
    beschreibung: Rechnungsdaten        # Pflicht
    beziehung: data                     # optional: data, source, alternative, supplement
verteiler:                              # optional
  - Herrn Max Muster
---
```

Das Datum wird als ISO-Datum angegeben und vom Renderer ausgeschrieben („25. August 2026").
Steht dort bereits ein ausformulierter Text, bleibt er unverändert.

## Grenzen, die abbrechen statt still zu verrutschen

| Feld | Grenze | Grund |
|---|---|---|
| `empfaenger` | 1 bis 6 Zeilen, keine Leerzeile | Anschriftzone ist 27,3 mm hoch |
| `vermerke` | höchstens 3 Zeilen | Zusatz- und Vermerkzone ist 12,7 mm hoch |
| `betreff` | höchstens 2 Zeilen | Norm |
| `infoblock`-Werte | höchstens 21 Zeichen | die Wertespalte beginnt bei 157 mm, der Satzspiegel endet bei 190 — nutzbar sind 33 mm |
| `anrede` | endet mit Komma | Norm |
| `gruss` | ohne Komma | Norm |

## Die E-Mail-Fassung

Dieselbe Datei, mit `typ: email`. Sie erzeugt Dateien — `.eml`, `.html`, `.txt` — und versendet
nichts; warum das so bleibt, steht in
[ADR 0034](../../docs/entscheidungen/0034-email-ist-ausgabe.md).

```yaml
---
typ: email
profil: example
an:                                     # Pflicht. Eine Adresse oder eine Liste
  - erika.muster@example.de
  - Muster GmbH <post@example.de>       # Klammerform nach [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322)
cc: []                                  # optional, gleiche Form wie `an`
bcc: []                                 # optional, gleiche Form — siehe unten
betreff: Angebot Nr. 2026-0815          # Pflicht, höchstens 78 Zeichen
anrede: Sehr geehrte Frau Muster,
gruss: Mit freundlichen Grüßen
unterzeichner: Erika Muster
brief: kuendigung.md                    # optional, der Brief, der mitreist
#                                       Er wird beim Bauen gesetzt und als PDF
#                                       angehängt; Betreff und Profil erbt die
#                                       Mail von ihm (Issue #78).
anlagen_dateien:                        # optional, als Anhang der Mail
  - angebot-2026-0815.pdf
antwort_auf: "<kennung@example.de>"     # optional, wird zu In-Reply-To
dialekt: "1.1"                          # wie beim Brief; der HTML-Teil setzt 1.1 noch nicht
sprache: de
datum: 2026-08-25                       # wird NICHT übernommen — `lint` warnt, siehe unten
---
```

**Die beiden Welten schließen sich aus.** `empfaenger:` in einer Mail ist ein Fehler mit Hinweis
auf `an:`, `an:` in einem Brief einer mit Hinweis auf `empfaenger:`. Das ist kein Formalismus:
Eine Mail an eine Postanschrift und ein Brief an eine Mailadresse sind beides Dokumente, die
niemanden erreichen. Ebenso entfallen `form`, `vermerke`, `infoblock`, `betreff_kurz`,
`signatur`, `anlagen` und `norm` — sie beschreiben ein Blatt Papier.

`bcc:` steht als Kopfzeile in der `.eml`, damit das Mailprogramm die Adresse übernehmen kann,
ohne dass jemand sie abtippt — ein verbreitetes Muster ist die Archivadresse, über die jede
ausgehende Mail im Dokumentenmanagement landet. Zwei Dinge dazu:

* **In der `.html`-Vorschau erscheint sie nicht.** Die Vorschau ist zum Ansehen und
  Herauskopieren da; eine sichtbare Zeile „Blindkopie" ginge beim Kopieren mit, und das Feld
  täte das Gegenteil dessen, wofür es da ist. `verify --email` prüft eigens, dass die Adresse
  weder im Text- noch im HTML-Teil vorkommt.
* **Ob dein Mailprogramm die Kopfzeile beim Weiterleiten übernimmt, entscheidet das Programm.**
  falzmarke versendet nicht (ADR 0034) und kann es deshalb nicht zusagen. Der Befehl nennt die
  Adresse beim Erzeugen eigens, damit du im Programm nachsiehst, statt sie für erledigt zu
  halten.

**Immer dieselbe Adresse? Dann ins Profil.** Wer jede ausgehende Nachricht im Archiv haben will,
trägt sie einmal als `bcc:` in den `email:`-Block seines Absender-Profils ein (siehe die
Feldliste weiter unten) statt in jede Datei. Sie tritt **neben** ein `bcc:` im Frontmatter, nicht
an dessen Stelle; dieselbe Adresse zweimal genannt steht einmal im Kopf. Still passiert das
nicht — der Hinweis beim Erzeugen wird aus der fertigen Datei gelesen und nennt deshalb auch die
Adresse aus dem Profil (#272).

In einem Brief gibt es `bcc:` nicht — anders als `cc:`, das dort `verteiler:` heißt. Wer eine
Kopie bekommt, ohne im Verteiler zu stehen, ist auf Papier nicht vorgesehen.

`datum:` wird nicht übernommen: Die Kopfzeile `Date` entsteht beim Setzen der Nachricht und
beschreibt diese, nicht den Brief, aus dem das Feld stammt. Steht es trotzdem da, sagt `lint`
das, statt es still zu übergehen.

### Die fertige Datei prüfen

```
falzmarke verify --email nachricht.eml
```

Gemessen wird **die Datei, nicht die Absicht** — wie beim PDF. Geprüft werden MIME-Aufbau und
Reihenfolge der Alternativteile, Zeichensatz und Transfer-Encoding, `format=flowed`,
Space-Stuffing, die Signaturtrennzeile, das Verbot von Skripten, externen Stylesheets,
Zählpixeln und Layout-Tabellen im HTML, und ob Text- und HTML-Fassung dasselbe sagen.

Liegt der `text/markdown`-Teil bei, wird zusätzlich geprüft, ob beide Fassungen die Quelle
vollständig wiedergeben. Fehlt er, sagt der Bericht das ausdrücklich — eine übersprungene
Prüfung soll nicht wie eine bestandene aussehen.

Ausgabe und Exit-Codes sind die von `verify`; `--verbose` zeigt alle Prüfungen, `--json` gibt
sie strukturiert aus.

### Der Abschnitt `email:` im Profil

Die Absenderangaben stehen im Profil, nicht im einzelnen Schreiben:

```yaml
email:
  absender: muster@example.de          # Pflicht
  bcc: archiv@example.de               # optional, ständige Blindkopie — auch als Liste
  signatur_html: signatur/erika.html   # optional, fertige Signatur statt der gebauten
  signatur_text: signatur/erika.txt    # optional, ihre Textfassung
  anzeigename: Erika Muster            # optional, sonst der Unterzeichner
  position: Geschäftsführerin          # optional
  web: www.example.de                  # optional
  telefon: 0941 620-9800               # optional, sonst der Wert aus infoblock_defaults
  mobil: 0170 1234567                  # optional
  anrede: sie                          # sie oder du — steuert NUR Warnungen
  datenschutz: https://example.de/datenschutz   # optional, als Zeile in der Signatur
  pflichtangaben: fusszeile            # woher die Angaben je Rechtsform kommen
  zusatz:                              # optional, z. B. Vertraulichkeitshinweis
    - Diese E-Mail enthält vertrauliche Informationen.
  gruss: Mit freundlichen Grüßen       # ohne Angabe: `gruss` des Profils
  logo: false                          # false, true (nimmt briefkopf.logo), ein Pfad,
  #                                    eine Adresse oder eine Data-URI — siehe unten.
  #                                    Rasterbild (PNG/JPG/GIF) — Outlook zeigt kein SVG.
  #                                    Es muss auf hellem UND dunklem Grund tragen; `lint`
  #                                    misst das und warnt (Issue #154).
```

### Die drei Wege des Logos

`email.logo` nimmt neben `false`, `true` und einem Dateipfad auch eine Adresse und eine
Data-URI. Welchen Weg das Werkzeug nimmt, folgt aus dem Wert:

| Wert | Was passiert | Beim Empfänger |
|---|---|---|
| `assets/logo.png` | wird als eigener Teil eingebettet (`cid:`) | **kommt immer an** — auch ohne Netz |
| `https://…/logo.png` | steht als Adresse im `src` | Outlook und Gmail blockieren externe Bilder standardmäßig; bis der Empfänger sie freigibt, bleibt ein leerer Kasten |
| `data:image/png;base64,…` | steckt im HTML-Teil | kommt mit, vergrößert jede Nachricht; Gmail zeigt es in der Weiterleitungsansicht nicht, Outlook hängt es als namenlosen Anhang an |

**Die Datei ist die Vorgabe, und für `falzmarke email` bleibt sie die richtige Wahl.** Die
beiden anderen gibt es, weil der Signatur-Baukasten auf falzmarke.com dieselbe Auszeichnung im
Browser erzeugt — und eine Webseite hat keinen MIME-Container, kann also keinen Anhang bauen.

Das Werkzeug schweigt dazu nicht: Wer eine Adresse oder eine Data-URI setzt, bekommt beim
Setzen den Satz, der den Preis benennt — auf der Kommandozeile unter der erzeugten Datei, im
MCP-Dienst als Feld `logo.hinweis`. Zur Dateiform gibt es nichts zu sagen.

Ein SVG bleibt in allen drei Formen ausgeschlossen; die Prüfung greift auch an der Endung einer
Adresse und am Typ einer Data-URI. Nennt eine Adresse keine Endung (`…/logo?id=7`), geht sie
durch — was dort liegt, weiß nur der Server, und danach zu fragen hieße, ihn abzurufen.

**Der Kontrast wird bei einer Adresse nicht gemessen**, und `lint` sagt das ausdrücklich, statt
stillzuschweigen: Messen hieße abrufen, und das tut dieses Werkzeug nicht (ADR 0034). Eine
Data-URI wird gemessen wie eine Datei — sie bringt ihre Bytes mit.

### Warum das Logo im dunklen Schema nicht umschaltet

Text, gedämpfter Text und Trennlinie der Signatur wechseln ihre Farbe, sobald das
Mailprogramm dunkel steht. **Das Logo tut das nicht** — es ist ein Rasterbild, und ein
Rasterbild trägt keine Medienabfrage. Ein SVG könnte es, wird von Outlook in Mails aber nicht
dargestellt; ein Logo, das bei einem der drei großen Programme fehlt, ist schlechter als eines,
das überall gleich aussieht.

Zwei Wege stünden offen und sind bewusst nicht gegangen:

| Weg | Warum nicht |
|---|---|
| Zwei Bilder, eines per `display: none` verborgen | Der `<style>`-Block einer erzeugten Nachricht ist nach ADR 0034 auf **Farbangaben** beschränkt. Eine Ausnahme, die auch Sichtbarkeit steuern darf, ist keine enge Ausnahme mehr — und die Enge ist der Grund, warum es die Ausnahme überhaupt gibt. |
| `<picture>` mit `<source media="(prefers-color-scheme: dark)">` | Bräuchte keinen `<style>`-Block. Ob Outlook das darstellt, ist hier **nicht gemessen** — und eine Technik, die im wichtigsten Zielprogramm ungeprüft ist, wird nicht zur Vorgabe gemacht. Bleibt offen, falls jemand es misst. |

Es bleibt also die Wahl des Absenders. Neu ist, dass sie nicht mehr nur in dieser Anleitung
steht: `lint` öffnet das Bild, rechnet jeden sichtbaren Punkt gegen hellen (`#FFFFFF`) und
dunklen Grund (`#1E1E1E`) und meldet `email.logo_kontrast`, wenn auf einem der beiden weniger
als die Hälfte der Fläche 3,0:1 erreicht — die Schwelle aus WCAG 1.4.11 für grafische Elemente.

Eine **Warnung**, kein Fehler: Welchen Ton ein dunkles Schema genau setzt, nennt kein
Mailprogramm im Datenmodell; `#1E1E1E` ist ein begründeter Schätzwert. Nach ADR 0035 gehört
eine Aussage über die Praxis nie auf die Fehlerebene.


### Brief und Begleitmail in einem Zug

Der häufigste Fall im Geschäftsverkehr: Das förmliche Schreiben geht als PDF im Anhang, und die
Mail daneben sagt in drei Sätzen, worum es geht.

```yaml
# begleitmail.md
typ: email
an: service@example.de
brief: kuendigung.md      # die QUELLE, nicht das PDF
```

Ein Aufruf — `falzmarke email begleitmail.md` — setzt den Brief, hängt sein PDF an und schreibt
die `.eml`. Betreff, Profil, Dialekt und Sprache erbt die Mail vom Brief, wenn sie sie nicht
selbst nennt; wer in der Mail einen eigenen Betreff schreibt, bekommt seinen.

| erbt die Mail | erbt sie **nicht** | warum |
|---|---|---|
| `betreff`, `profil`, `dialekt`, `sprache` | | derselbe Vorgang, zweimal gepflegt driftet er |
| | `an` | eine Postanschrift ist keine Mailadresse — `an:` bleibt Pflicht |
| | `datum` | `Date` entsteht beim Setzen der Nachricht, nicht aus dem Briefdatum |

**`brief:` zeigt auf die Markdown-Quelle, nicht auf ein PDF.** Das ist der Unterschied zu
`anlagen_dateien:`, das vorhandene Dateien nimmt: Hier kann kein veraltetes PDF mitreisen, weil
es keines gibt, das älter wäre als dieser Aufruf. Ändert sich der Brief, ändert sich der Anhang.

Beides zusammen geht: `brief:` ergänzt `anlagen_dateien:`, es ersetzt sie nicht.

Versendet wird weiterhin nichts (ADR 0034). Und dass der Anhang im Text genannt wird, bleibt eine
Warnung von `lint` — ein Werkzeug, das ungefragt Sätze schreibt, schreibt irgendwann den falschen.

`pflichtangaben` ist eine **Erinnerung, keine Rechtsprüfung**: `lint` warnt, wenn das Feld leer
ist, und sonst nichts. Welche Angaben eine Rechtsform in jeder Geschäftsmail braucht, entscheidet
nicht das Werkzeug (ADR 0005).

## Die Rechnungsfassung

Dieselbe Datei, mit `typ: rechnung`. **Gesetzt wird sie noch nicht** — der Datenvertrag steht
(#115), der Emitter nicht. `falzmarke render` bricht bei einer Rechnung ab, statt sie als Brief zu
setzen: Als Brief fehlten ihr Positionen und Summen, und das ohne ein Wort darüber. `falzmarke
lint` prüft die Datei schon jetzt.

Die Felder leiten sich aus
[§ 14 Absatz 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html) ab — den zehn
Pflichtangaben einer Rechnung, erhoben in `docs/recht.md`. Kein Feld ist erfunden.

```yaml
---
typ: rechnung
profil: example
empfaenger:                             # Pflicht, wie im Brief
  - Muster GmbH
  - Musterstraße 1
  - 12345 Musterstadt
datum: 2026-09-11                       # Pflicht — das Ausstellungsdatum
rechnungsnummer: "2026-0042"            # Pflicht — falzmarke vergibt keine
leistungsdatum: 2026-10-03              # Zeitpunkt der Leistung …
# leistungszeitraum: {von: 2026-10-01, bis: 2026-10-31}   # … oder ein Zeitraum, nie beides
zahlungsziel: 2026-10-31                # optional, ein Datum
positionen:                             # Pflicht, mindestens eine
  - bezeichnung: Technik und Aufbau     # Pflicht
    menge: 1                            # Pflicht
    einheit: Stück                      # optional
    einzelpreis: 1240.00                # optional
    steuersatz: 19                      # Pflicht, in Prozent
    betrag: 1240.00                     # Pflicht — falzmarke bildet ihn nicht
summen:                                 # optional; steht es da, wird es geprüft
  netto: 1240.00
  steuer:
    - satz: 19
      betrag: 235.60
  brutto: 1475.60
betreff: Rechnung für die Veranstaltung am 3. Oktober
anrede: Sehr geehrte Damen und Herren,
---
```

**Eine Rechnung ist ein Schreiben.** Sie läuft durch dieselben Prüfungen wie der Brief —
Anschriftzone, Betreff, Datum, Vermerke — und trägt Anrede und Grußformel. Die Felder treten
neben den Text, sie ersetzen ihn nicht. Die Mailfelder (`an:`, `cc:`, `bcc:`, `antwort_auf:`)
bedeuten in ihr dasselbe wie im Brief: nichts, und `lint` sagt das.

**Zahlen stehen ohne Tausenderpunkt und mit Punkt als Dezimaltrenner** — `1240.00`, nicht
`1.240,00`. Die Schreibweise mit Tausenderpunkt ist die des gesetzten Schreibens; in der Quelle
wäre sie mehrdeutig, und `lint` meldet sie, statt sie still zu deuten. Ebenso wenig ist `true`
eine Menge, auch wenn Python es für die Zahl 1 hielte.

**Bankverbindung, Steuernummer und USt-IdNr. stehen im Profil**, nicht im einzelnen Schreiben —
wie die Absenderangaben.

### Was jedes Feld tut, und was ohne es passiert

| Feld | Pflicht | Ohne das Feld |
|---|---|---|
| `rechnungsnummer` | ja | `lint` meldet einen Fehler. Eine Nummer aus reinem Leerraum ebenso. |
| `positionen` | ja | `lint` meldet einen Fehler — eine Rechnung ohne Positionen ist keine. |
| `positionen[].bezeichnung` | ja | Fehler — § 14 Abs. 4 Nr. 5 verlangt „die Art". |
| `positionen[].menge` | ja | Fehler — ebenda, „die Menge". |
| `positionen[].steuersatz` | ja | Fehler — § 14 Abs. 4 Nr. 8. Außerhalb 0 bis 99 ebenso. |
| `positionen[].betrag` | ja | Fehler — falzmarke bildet den Betrag nicht aus Menge und Preis. |
| `positionen[].einheit`, `einzelpreis` | nein | Nichts. Sie stehen dann nicht auf der Rechnung. |
| `leistungsdatum` / `leistungszeitraum` | eines | Nichts wird gemeldet. Beide zugleich sind ein Fehler; ein Zeitraum braucht `von:` **und** `bis:`. |
| `zahlungsziel` | nein | Nichts. Steht es da und ist kein Datum, meldet `lint` einen Fehler. |
| `summen` | nein | Nichts wird geprüft. Steht es da, prüft `lint`, ob es zu den Positionen passt (siehe unten). |
| `gutschrift`, `aufbewahrungshinweis` | nein | Vorgesehen für § 14 Abs. 4 Nr. 10 und 9. Bis zum Emitter ohne Wirkung — wie die ganze Rechnung. |

Ein unbekanntes Feld — im Kopf, in einer Position, in den Summen — wird gemeldet, mit dem
Vorschlag des nächstgelegenen bekannten Namens. Ein Tippfehler bleibt nicht stumm.

### Was falzmarke nicht berechnet

**Das Werkzeug rechnet nicht**
([ADR 0039](../../docs/entscheidungen/0039-falzmarke-rechnet-nicht.md)). Wer rechnet, haftet
für das Ergebnis; wer überträgt, sagt, dass er nicht rechnet. Deshalb ausdrücklich:

- **Kein Positionsbetrag** wird aus Menge mal Einzelpreis gebildet. `betrag:` ist Pflicht.
- **Keine Summe** wird gebildet. `netto:`, `steuer:` und `brutto:` stehen in der Quelle oder
  gar nicht.
- **Kein Steuerbetrag** wird nachgerechnet. Das wäre Satz mal Bemessungsgrundlage, und damit
  stünde die Rundungsregel zur Wahl, die der Absender verantwortet.
- **Keine Rechnungsnummer** wird vergeben, und ob sie fortlaufend ist, prüft falzmarke nicht —
  es kennt die vorige Rechnung nicht.

Was `lint` stattdessen tut, ist eine **Rechenprobe über die gegebenen Werte**: Die Summe der
Positionsbeträge gegen `netto:`, und `netto:` plus die Steuerbeträge gegen `brutto:`. Weicht
eines ab, erscheint eine **Warnung** — kein Fehler, und der Lauf endet mit Code 0. Eine Rechnung
mit widersprüchlichen Summen geht also durch; das ist die unbequeme Seite dieser Entscheidung,
und sie steht hier, damit niemand etwas anderes erwartet. Ein Cent Abweichung je Steuersatz ist
Rundung und wird nicht gemeldet.

## Der Brieftext

Unter dem Frontmatter steht der Brieftext als Markdown — eine dokumentierte Teilmenge von
CommonMark. Welche Auszeichnungen möglich sind, was der Typografie-Pass von selbst erledigt
und was abbricht, steht in **[falzmarke-Markdown](markdown.md)**.

## Profildatei

Anlegen mit `falzmarke.py init-profil <name>`. Die Datei landet unter
`~/.config/falzmarke/profiles/<name>.yaml` — außerhalb der Installation, damit sie
Aktualisierungen übersteht.

```yaml
absender:                    # Pflicht
  name: Beispiel GmbH
  strasse: Musterweg 12
  plz: "93055"
  ort: Regensburg
ruecksendeangabe: Beispiel GmbH · Musterweg 12 · 93055 Regensburg   # Pflicht, einzeilig
form: B                      # Voreinstellung
sprache: de                  # Voreinstellung; der Brief darf sie überschreiben
font: Libertinus Serif       # oder "Source Sans 3" aus assets/fonts/
farbe: "#1a3a5c"
briefkopf:
  logo: assets/logo.png      # relativ zur Profildatei; ohne Logo erscheint der Name
  logo_hoehe_mm: 14
  zeilen: [Beispiel GmbH, "Musterweg 12 · 93055 Regensburg"]
fusszeile:                   # je Liste eine Spalte
  - [Beispiel GmbH, Musterweg 12, 93055 Regensburg]
  - ["Telefon 0941 620-9800", info@example.de]
datumsformat: lang           # lang oder iso
gruss: Mit freundlichen Grüßen
unterzeichner: Erika Muster
firma_ueber_unterschrift: false
signatur: assets/unterschrift.png   # optional, transparentes PNG
rand_unten_mm: 42            # optional; ohne Angabe aus der Fußzeilenhöhe berechnet
infoblock_defaults:
  ansprechpartner: Erika Muster
  telefon: 0941 620-9800
  email: muster@example.de
```

**Doppelpunkte in Textzeilen brauchen Anführungszeichen**, sonst liest YAML sie als Feld:

```yaml
- "Geschäftsführerin: Erika Muster"
```

Ohne Anführungszeichen bricht der Renderer mit einer entsprechenden Meldung ab.

## Sprache

`sprache: en` setzt die Beschriftung eines Briefes auf Englisch: die Leitwörter des
Informationsblocks, die Monatsnamen, „Anlagen", „Verteiler" und die Seitenzählung. Dazu
`text.lang`, wovon die Silbentrennung abhängt — ohne das bräche englischer Text nach
deutschen Regeln um.

**Die Maße ändern sich nicht.** Anschriftfeld, Informationsblock, Falzmarken und das
12-pt-Raster sind Werte der DIN 5008 und hängen nicht an der Sprache. `verify` misst
Zonen und Abstände, keine Wörter; ein englischer Brief besteht dieselben Prüfungen.

**Die englischen Wörter sind nicht normbelegt.** DIN 5008 ist eine deutsche Norm und
kennt kein „Your reference". Was `falzmarke` dort einsetzt, ist die im Geschäftsverkehr
übliche Entsprechung — eine Konvention, keine Fundstelle. Wer so einen Brief setzt,
bekommt ein Blatt, dessen Maße belegt sind und dessen Beschriftung es nicht ist.

| Feld | Deutsch | Englisch |
|---|---|---|
| `ihr_zeichen` | Ihr Zeichen | Your reference |
| `ihre_nachricht_vom` | Ihre Nachricht vom | Your letter of |
| `unser_zeichen` | Unser Zeichen | Our reference |
| `unsere_nachricht_vom` | Unsere Nachricht vom | Our letter of |
| `ansprechpartner` | Name | Contact |
| `telefon` | Telefon | Phone |
| `fax` | Fax | Fax |
| `email` | E-Mail | Email |
| — | Datum | Date |
| — | Anlage / Anlagen | Enclosure / Enclosures |
| — | Verteiler | Copies to |
| — | Seite x von y | Page x of y |

Das Datum folgt der britischen Schreibweise (`26 August 2026`), nicht der amerikanischen:
Ein DIN-5008-Brief ist ein europäischer Geschäftsbrief, und die Folge Tag–Monat–Jahr
bleibt damit dieselbe wie im deutschen Original. Wer die Zeile überfliegt, verwechselt
Tag und Monat nicht.

Ein vollständiges Beispiel: [`examples/brief-englisch.md`](../../examples/brief-englisch.md).

## Anlagen beilegen

### Eingebettete Dateien

```yaml
eingebettet:                            # optional, Dateien IM PDF
  - datei: rechnung.xml                 # Pfad relativ zur Briefdatei
    typ: text/xml                       # Medientyp — PDF/A-3b verlangt ihn
    beschreibung: Rechnungsdaten        # ebenfalls Pflicht
    beziehung: data                     # optional: data, source, alternative, supplement
```

**Das ist etwas anderes als `anlagen_dateien:`** und die Verwechslung wäre teuer:

| | was passiert | wer es liest |
|---|---|---|
| `anlagen_dateien:` | Seiten werden hinten angehängt, das PDF wird länger | ein Mensch, der blättert |
| `eingebettet:` | die Datei liegt **im** Dokument, sichtbar wird nichts | ein Programm |

Wer etwas einbettet, bekommt **PDF/A-3b** statt 2b. Das ist keine Bequemlichkeit: PDF/A-2 kennt
keine beliebigen Dateien im Dokument, PDF/A-3 lässt sie zu. Die Stufe wird **verlangt, nicht
stillschweigend umgestellt** — wer nichts einbettet, bekommt weiter 2b (ADR 0033).

`typ` und `beschreibung` sind Pflicht, und das kommt nicht von falzmarke: Der Satz bricht ohne
sie ab, weil PDF/A-3b beide verlangt. `beziehung` kennt genau vier Werte; `data` ist der, den
maschinenlesbare Daten zu einem Dokument tragen.

Fehlt die Datei, bricht der Lauf ab. Ein PDF ohne seine Beilage sieht von außen aus wie eines
mit — bei einer Rechnung wäre das der teure Fall.

`anlagen:` und `anlagen_dateien:` sind zweierlei und unabhängig voneinander:

- **`anlagen:`** schreibt den Anlagenvermerk unter den Brief. Er nennt, was beiliegt —
  auch dann, wenn die Anlage per Post beigelegt wird und es keine Datei gibt.
- **`anlagen_dateien:`** hängt PDF-Dateien hinten an das erzeugte PDF. Pfade sind
  relativ zur Briefdatei, damit ein Vorgang samt seinen Anlagen ein Ordner bleibt,
  den man verschieben kann.

Wer beides will, schreibt beides.

### Was das mit PDF/A macht

Ein Merge erhält die XMP-Metadaten des Briefes. Ohne Gegenmaßnahme behauptet die Datei
danach weiter PDF/A-2b, gleichgültig was in der Anlage steckt — gemessen mit veraPDF:

| Anlage | Ergebnis laut veraPDF | XMP sagt |
|---|---|---|
| aus Typst, Schriften eingebettet | PASS 2b | 2b |
| nicht eingebettete Schrift | **FAIL 2b** | 2b |

Der zweite Fall ist der teure: eine Datei, die PDF/A behauptet und es nicht ist. Sie
fällt erst auf, wenn im Archiv die Schrift fehlt.

falzmarke hat die Anlage nicht gesetzt und kann ihre Konformität nicht prüfen — das kann
nur ein Prüfwerkzeug wie veraPDF. Ohne fremdes Werkzeug feststellbar ist allein, was die
Anlage **über sich selbst sagt**. Daran richtet sich die Kennzeichnung aus:

| Lage | Kennzeichnung | Meldung |
|---|---|---|
| alle Anlagen deklarieren PDF/A | bleibt | Hinweis, dass das ihre Aussage ist, keine Prüfung |
| eine Anlage deklariert nichts | wird entfernt | nennt die Datei und den Grund |

Die Deklaration ist kein Beleg für Konformität. Eine Anlage, die nichts behauptet, ist
mit Sicherheit kein PDF/A; eine, die es behauptet, ist es wahrscheinlich. Auf dieser
Grundlage die Kennzeichnung zu *entfernen* ist sicher — sie stehen zu lassen bleibt eine
Aussage über die Anlage. Belegt ist die Konformität des Ergebnisses erst durch veraPDF
([`scripts/pdf_konformitaet.py`](../../scripts/pdf_konformitaet.py)).

### Die Anlage wird nicht nach Briefregeln gemessen

Eine Anlage trägt keine Kopfzeile mit Betreff, keine Seitenzählung und womöglich keine
eingebettete Schrift. `verify` misst deshalb nur die Seiten des Briefes; wo er endet,
vermerkt falzmarke beim Anhängen als `/falzmarke_Briefseiten` im PDF. Auch ein späteres
`verify` auf der fertigen Datei liest das und beurteilt die Anlage nicht.
