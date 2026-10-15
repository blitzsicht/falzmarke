# 0034 — E-Mail ist Ausgabe, nicht Kanal

**Datum:** 27.08.2026 · **Status:** angenommen · **Löst:** [#60](https://github.com/blitzsicht/falzmarke/issues/60)

## Entscheidung

falzmarke erzeugt E-Mails als **Dateien** — `.eml`, `.html`, `.txt` — aus derselben Quelle und
demselben Profil wie Briefe. Der Versand bleibt außerhalb: kein SMTP, keine Konten, keine
Zustellung, keine Option, die sendet. Das Feld `an:` füllt den Kopf der Datei, mehr nicht.

Das ist die Anwendung von [0029](0029-falzmarke-ist-werkzeug-kein-kanal.md) auf einen Fall, den
0029 selbst schon nennt: Dort steht, die E-Mail-Fassung bleibe, „sie erzeugt eine Ausgabe und
versendet nichts". Warum das eine eigene Entscheidung braucht, steht unter [Warum](#warum).

Vier Festlegungen folgen daraus.

### 1. Ausgabe statt Kanal

Es entsteht kein Versandbefehl. Nicht als Unterbefehl, nicht als Schalter, nicht als „nur für
den Test". Wer die erzeugte `.eml` versenden will, öffnet sie in seinem Mailprogramm — das ist
der Zweck des Formats, und es ist der Punkt, an dem falzmarkes Zuständigkeit endet.

### 2. Struktur bleibt, Umbruch nicht

Betreff, Anrede, Absätze, Grußformel und Signatur sind dieselben wie im Brief. Sie kommen aus
demselben geprüften Markdown-Baum, nicht aus einer zweiten Quelle.

Der Zeilenumbruch ist es nicht. Ein Brief kennt seine Seitenbreite; eine E-Mail kennt sie nicht:
Das Programm des Empfängers bricht um, und jede feste Breite kämpft dagegen. Deshalb
`format=flowed` (RFC 3676) im Textteil und einspaltiges HTML ohne feste Breiten.

Die Norm behandelt die E-Mail in Abschnitt 22. Diese Zuordnung stammt aus Sekundärquellen und ist
**nicht gegen den Originaltext geprüft** — sie steht hier als Fundstelle, nicht als Beleg. Was aus
Abschnitt 22 tatsächlich als Regel gilt, gehört nach `skill/references/din5008.md` mit Quelle
daneben, und zwar erst dann, wenn es dort mit derselben Sorgfalt eingetragen wird wie die
Briefregeln. Bis dahin ist die Nummer eine Adresse, kein Nachweis.

### 3. Die Quelle reist mit — auf Verlangen

Ein `text/markdown`-Teil (RFC 7763, `variant=CommonMark`) kann die Quelle mitführen. Er entsteht
**nur, wenn er ausdrücklich verlangt wird**; die Vorgabe ist ohne ihn. Den Namen der Option legt
[#63](https://github.com/blitzsicht/falzmarke/issues/63) fest.

Das weicht von der Vorlage in #60 ab, wo der Teil ohne Bedingung mitreisen sollte. Der Grund für
die Abweichung ist derselbe wie bei der PDF/A-Stufe in [0033](0033-pdfa-stufe.md): Eine Fähigkeit,
die den Empfängerkreis verengt oder mehr preisgibt, wird verlangt, nicht stillschweigend geliefert.

Konkret kostet der Teil zweierlei. Er vergrößert jede Mail um die volle Quelle. Und er macht
sichtbar, was im Brief nicht sichtbar wäre: Frontmatter-Felder, Kommentare, Reste früherer
Fassungen — alles, was in der Datei steht und nicht gesetzt wird. Wer eine Mail schreibt, rechnet
mit dem, was er liest, nicht mit dem, was er geschrieben hat.

Wenn der Teil greift, gelten dieselben Vertraulichkeitsregeln wie beim Hybridbrief: Whitelist,
nur sichtbar Gesetztes.

### 4. Kein Marketing

Keine Spalten, keine Buttons, keine Zählpixel, keine Hintergrundbilder, keine Skripte, keine
externen Stylesheets. Bilder nur als eingebettete Ressource mit Alt-Text, und auch das nur für
das Logo des Profils.

Das ist keine Geschmacksfrage. Zurückhaltendes HTML mit Textalternative ist die einzige Form,
die in Outlook, Gmail und Apple Mail gleich ankommt — jede Mail-Umgebung streicht etwas anderes
weg, und der Schnitt durch alle drei ist schmal. Ein Zählpixel ist zusätzlich ein
Datenschutzvorgang, den ein Werkzeug seinem Nutzer nicht unterschieben darf.

#### Ergänzung vom 28.08.2026: ein `<style>`-Block für das dunkle Farbschema

Oben steht „keine externen Stylesheets". Die Prüffunktion `emit_html.verstoesse()` verbot
darüber hinaus **jeden** `<style>`-Block — eine Verschärfung, die hier nie beschlossen wurde.
Sie fiel auf, als der dunkle Modus dazukam.

**Inline-Stile können keine Medienabfrage tragen.** Das ist eine Eigenschaft der Sprache, keine
Bequemlichkeit: Ohne `<style>` erscheint jede erzeugte Nachricht in einem dunklen Client als
weißer Kasten mit hellem Text auf hellem Grund. Dunkle Clients sind längst der Normalfall.

Zulässig ist deshalb **genau ein** Block, und er ist eine Konstante des Werkzeugs:

- Er schaltet ausschließlich **Farben** um — Text, gedämpfter Text, Rahmen.
- Er trägt zwei Mechanismen: `prefers-color-scheme` und `[data-ogsc]`, das Outlook stattdessen
  setzt. Mit nur einem bleibt genau ein Programm hell.
- **Nichts daran wird aus Eingabe oder Profil zusammengesetzt.** Das Werkzeug erzeugt ihn und
  kennt seinen Inhalt vollständig.

`verstoesse()` vergleicht ihn **Zeichen für Zeichen** gegen die Konstante. Ein zweiter Block, ein
geänderter Block, ein zusätzliches Leerzeichen — alles bleibt ein Verstoß. Damit ist die
Ausnahme nicht dehnbar, und sie ist geprüft statt zugesichert.

##### Nachtrag vom 09.09.2026: ein mitgebrachter Teil darf dahinter (#275)

Der Satz „nichts daran wird aus Eingabe oder Profil zusammengesetzt" hielt, solange falzmarke
die einzige Quelle für Gestaltung war. Seit ein Profil eine **fertige Signatur** mitbringen darf
(`email.signatur_html`), bringt es auch deren Dunkelregeln mit — und Medienabfragen gehen nicht
inline, aus demselben Grund wie oben.

Der Block hat deshalb zwei Teile, und sie werden **verschieden behandelt**:

| Teil | Behandlung |
|---|---|
| der eigene, **vorn** | unverändert Zeichen für Zeichen gegen die Konstante verglichen |
| der mitgebrachte, dahinter | **geprüft** statt verglichen: `emit_html.fremdstil_verstoesse()` |

Geprüft wird auf das, was einen Stilblock zu etwas anderem macht als eine Sammlung von Regeln:
ein Verweis nach außen (`url(`, `@import`), ein zweites Dokument (`<`) oder ausführbarer Inhalt
(`expression(`, `javascript:`, `behavior:`). Farben, Größen, Abstände und Medienabfragen sind
genau das, wofür der Block da ist.

**Die Reihenfolge ist Teil der Zusage.** Stünde der fremde Teil vorn, könnte er den eigenen
überschreiben; ein Test hält fest, dass etwas **vor** der Konstante ein Verstoß bleibt.

Was das nicht ändert: Die Regeln dieses Abschnitts gelten für eine mitgebrachte Signatur wie für
eigenen Satz. Sie durchläuft `verstoesse()` vollständig, und was durchfällt, wird **abgelehnt** —
mit Fundstelle, nicht stillschweigend eingesetzt. Der Kanal gibt nicht nach, damit die Quelle
nachbessert.

Was das **nicht** aufweicht: Externe Stylesheets, Skripte, Hintergrundbilder, Zählpixel und
Verweise auf Ressourcen im Stil bleiben verboten. Die Dunkelfarben sind fest und kommen nicht
aus dem Profil — eine Markenfarbe, die auf Weiß trägt, trägt auf Dunkel selten, und ein Profil,
das eigene Dunkelfarben mitbrächte, müsste jede davon gegen den dunklen Grund messen.

Dazu eine zweite Prüfung, `emit_html.nicht_umschaltbar()`: Wer eine Farbe inline setzt, muss die
Klasse tragen, die sie umschaltet. Der Fehler, gegen den sie gebaut ist, heißt **halb
umgeschaltet** — beim Bildzeichen der Marke stand die helle Grundregel einmal nach der
Medienabfrage, und das Blatt schaltete um, die Kontur nicht.

##### Nachtrag vom 15.10.2026: der Rumpf erbt seine Farben

Oben steht, der Block schalte Text, gedämpften Text und Rahmen um. Das setzte voraus, dass er
ankommt. Er kommt nicht überall an: `--oeffnen` übergibt Thunderbird nur den Inhalt von `<body>`
([0049](0049-entwurf-in-thunderbird.md)), und manche Empfängerprogramme entfernen `<style>`.
Beobachtet am 15.10.2026 im Thunderbird-Entwurf bei dunklem Thema: Die Inline-Farbe `#1a1a1a`
blieb stehen, der Grund war das Dunkelgrau des Programms, der ganze Rumpf war unlesbar.

Ein erster Umbau gab dem Umschlag einen weißen Grund, der im dunklen Schema mit umschaltete. Lesbar
war das in jedem Weg, aber im dunklen Editor stand ein weißer Kasten. Der Betreiber hat ihn am
selben Tag verworfen.

Die Regel seither: **Der Rumpf setzt keine Farbe, die auf einem der beiden Gründe unlesbar wäre.**
Gemessen gegen `farbe.GRUND_HELL` (`#ffffff`) und `farbe.GRUND_DUNKEL` (`#1e1e1e`), dieselben
Gründe, gegen die `lint` das Logo misst:

| Was | Schwelle auf beiden Gründen | Folge |
|---|---|---|
| Schrift, auch Nebentext | 4,5:1 (WCAG 1.4.3) | erreicht keine Farbe; das beste Grau liegt bei rund 4,1:1. Die Schrift erbt die Farbe des Mailprogramms, Nebentext unterscheidet sich nur durch die Größe |
| Grund | — | keiner; Körper, Umschlag und Zelle setzen weder `bgcolor` noch `background-color` |
| Linie | 3:1 (WCAG 1.4.11) | `#7e7e7e`, 4,06:1 auf Weiß und 4,11:1 auf `#1e1e1e` |

Der Block bleibt, aber er schaltet nur noch die Linie: im dunklen Schema auf `#696969`, das
dunkelste Grau mit 3:1 auf `#1e1e1e`. Kommt er nicht an, trägt der helle Wert auf beiden Gründen.
Die Regeln für Text und gedämpften Text sind entfallen, es gibt dort keine Farbe mehr umzuschalten.
Der eigene Teil ist weiterhin eine Konstante, Zeichen für Zeichen verglichen.

`nicht_umschaltbar()` meldet seither jede inline gesetzte Schriftfarbe und jeden Hintergrund,
`bgcolor` eingeschlossen, mit welcher Klasse auch immer. `color: inherit` am Link setzt keine
Farbe und bleibt erlaubt.

Was das zunächst nicht löste: Eine **mitgebrachte Signatur** blieb unangetastet. Ihre Farben trugen
nur auf Weiß, und ihr Dunkelblock kam im Entwurf nicht an. Das holt der nächste Nachtrag nach.

##### Nachtrag vom 15.10.2026: die Signatur erbt ihre Farben (#275)

Mit dem Profil `gottl-gbr` blieben im dunklen Thunderbird-Entwurf Name und E-Mail-Link (`#1f2a37`,
1,15:1 auf `#1e1e1e`), Firma (`#333333`, 1,32:1) und Labels (`#888888`, auf Weiß 3,54:1) dunkel auf
dunkel. Die Dunkelregeln der Signatur stehen in ihrem eigenen `<style>`, und das bekommt der
Entwurf nicht.

Die Vorlage in `cw-core` wird **nicht** geändert: Aus ihr entstehen auch Kundensignaturen für
Outlook. Stattdessen gilt beim Einsetzen dieselbe Regel wie für den Rumpf. **Übernommen werden
Aufbau und Inhalt, die Farben erbt die Mail vom Mailprogramm.** #275 hatte festgelegt, dass der Rumpf
übernommen und der Stil hinter den eigenen Block gesetzt wird. Das bleibt, jetzt eben ohne Farben:

| Was | Beim Einsetzen |
|---|---|
| Schriftfarbe (`color`, auch `!important`; `<font color>`) | fällt weg; keine Farbe trägt Schrift auf beiden Gründen |
| Grund (`background`, `background-color`, `bgcolor`) | fällt weg; `transparent` bleibt |
| Linie unter 3:1 auf einem der beiden Gründe | wird `#7e7e7e`; eine Linie, die trägt, bleibt |
| Stilregel für Schrift oder Grund, auch unter `[data-ogsc]` | fällt weg, die Klassen setzen keine Farbe mehr |
| Dunkle Linienregel unter 3:1 auf `#1e1e1e` | fällt weg; im Dunkeln gilt die Linie, die inline steht |
| alles andere — Tags, Text, Links, Logo, Schrift, Größen, Abstände, Rundungen | bleibt Byte für Byte |

Ein Knopf mit eigener Fläche und weißer Schrift verliert damit Fläche und Schriftfarbe. Was bleibt,
ist ein Link in Größe und Gewicht der Vorlage; der Platz des Knopfs bleibt.

Die Datei im Profilordner bleibt unberührt. Geprüft wird weiterhin, **was die Quelle schreibt**:
`verstoesse()` läuft vor dem Bereinigen, und eine unsaubere Signatur wird abgelehnt wie bisher.
Bereinigt wird nur in Attributwerten, deren Stelle der HTML-Parser bestimmt hat
(`emit_html.fremdrumpf_ohne_farben`, `fremdstil_ohne_farben`). Ein Ersetzen über den ganzen Text
gibt es nicht; ein `style="color:…"`, das als Wortlaut im Text steht, bleibt stehen.

#### Ergänzung vom 07.09.2026: drei Wege für das Logo, und eine Grenze dafür

Oben steht „keine Spalten" und „Bilder nur als eingebettete Ressource". Beides braucht einen
Nachtrag, und beide Male aus demselben Grund: Der Satz beschreibt, was die Regel verhindern
soll, nicht jeden Fall, auf den er wörtlich passt.

**„Keine Spalten" meint kein mehrspaltiges Textlayout, keine Layouttabelle um ein Logo.** Der
Code führt seit [#104](https://github.com/blitzsicht/falzmarke/issues/104) eine zweispaltige
Tabelle um das Signaturlogo, und seit #243 trägt sie die ganze Signatur. Das ist kein
Marketing-Raster, sondern das Mittel, mit dem ein Bild neben Text steht, wenn das klassische
Outlook mit der Word-Engine setzt. Die Regel bleibt: keine Spalten für **Inhalt**.

**Bilder dürfen jetzt auch von außerhalb kommen — für das Logo, und nur dafür.** Bis hierher
war `cid:` die einzige zulässige Quelle; `emit_html.verstoesse()` meldete `data:` und jede
Adresse als Verstoß. Das war richtig für den Weg, den 0034 vor Augen hatte — und es machte
einen zweiten unmöglich, den es inzwischen gibt: Der Signatur-Baukasten auf falzmarke.com
erzeugt dieselbe Auszeichnung im Browser, und eine Webseite hat keinen MIME-Container. Dort
fehlte das Logo deshalb ganz.

`email.logo` nimmt seither drei Formen:

| Form | Wofür | Beim Empfänger |
|---|---|---|
| Dateipfad (Vorgabe) | `falzmarke email` | eigener Teil mit `cid:` — kommt immer an |
| `https://…` | Umgebungen ohne Anhang | blockiert, bis der Empfänger Bilder freigibt |
| `data:image/…;base64,…` | der Baukasten im Browser | kommt mit, vergrößert jede Nachricht |

**Die gemessenen Nachteile sind damit nicht verschwunden.** Gmail zeigt `data:`-Bilder in der
Weiterleitungsansicht nicht an, Outlook hängt sie als namenlosen Anhang an, und eine Adresse
wird in beiden standardmäßig blockiert. Sie sind jetzt die Sache dessen, der die Form wählt —
und `eml.logo_hinweis()` sagt sie ihm beim Setzen, auf der Kommandozeile wie im MCP-Dienst.
Aus der fertigen Datei gelesen, nicht aus dem Profil: gemeldet wird, was drinsteht.

**Was die Grenze jetzt hält, ist die Anzahl.** Solange nur `cid:` zulässig war, hielt die
Quellenregel sie nebenbei mit — was in der Nachricht steckt, muss dort erst hineingelegt
werden. Deshalb steht in `emit_html.BILDER_MAX` jetzt ausdrücklich, was oben schon als Satz
stand: höchstens ein Bild, nämlich das Logo des Profils. Gemessen hatte das bis dahin
**niemand**; drei Bilder mit `cid:` wären anstandslos durchgegangen.

Ebenso wandert die Zählpixel-Erkennung zum Emitter. Sie stand nur in `pruefung_eml`, weil ein
Zählpixel dort ohnehin schon als „Bild von außerhalb" auffiel — mit der Quellenregel fällt
dieser erste Zaun weg, und ein einzelnes externes 1×1-Bild wäre für den Emitter unsichtbar
geworden.

Was das **nicht** aufweicht: Skripte, Formulare, externe Stylesheets, Hintergrundbilder und
Verweise auf Ressourcen im Stil bleiben verboten, Alt-Text und Maßangaben Pflicht, und ein
Zählpixel bleibt ein Zählpixel. Und die Kontrastmessung schweigt bei einer Adresse nicht,
sondern sagt, dass sie nicht messen konnte — sie abzurufen wäre genau der Schritt nach außen,
den diese Entscheidung ausschließt.

## Warum

0029 hätte gereicht, wenn E-Mail wie ein Brief wäre. Sie ist es nicht — an genau einer Stelle:

**Eine `.eml` ist einen Knopfdruck vom Versand entfernt.** Ein PDF muss jemand ausdrucken,
falten, frankieren; dazwischen liegen Handgriffe, in denen niemand auf die Idee kommt, das
Werkzeug solle das übernehmen. Bei einer Mail liegt der Versand als Bibliotheksaufruf herum, ist
in zwanzig Zeilen erledigt und wird bei jedem zweiten Vorschlag mitgedacht. Genau dieser Knopf
entsteht hier nicht, und der Grund steht als eigene Entscheidung da, damit er nicht bei jedem
Vorschlag neu verhandelt wird.

Der zweite Grund ist die Haftung, und sie ist dieselbe wie in 0029: Wer eine Datei erzeugt,
haftet für ihren Inhalt; wer sie befördert, für Zustellung und Nachweis. Bei E-Mail kommt hinzu,
dass Zustellbarkeit von Dingen abhängt, die falzmarke nie kontrollieren kann — SPF, DKIM,
Reputation der sendenden Adresse, Spamfilter des Empfängers. Ein Werkzeug, das „auf den
Millimeter geprüft" sagt, kann daneben nicht „kommt an" sagen.

## Was daraus folgt

- **Die Phase E-Mail bleibt, wo sie steht.** [0030](0030-reihenfolge-der-roadmap.md) führt sie
  im Nachtrag vom 27.08.2026 als dritte Phase nach den langen Schreiben. Diese Entscheidung
  ändert daran nichts, sie begründet nur, warum die Phase kein Versandvorgang ist.
- **[#61](https://github.com/blitzsicht/falzmarke/issues/61) ist damit entsperrt.** HTML- und
  Text-Emitter setzen den bestehenden Baum; Punkt 2 und 4 sind ihre Vorgabe.
- **[#63](https://github.com/blitzsicht/falzmarke/issues/63)** baut die `.eml` mehrteilig
  (`text/plain` und `text/html`), den `text/markdown`-Teil nur auf Verlangen, und legt den Namen
  der Option fest.
- **[#64](https://github.com/blitzsicht/falzmarke/issues/64)** macht Punkt 4 prüfbar: Die
  Lint-Regeln E7xx und `verify --email` schlagen an, wenn eine erzeugte Mail ein externes
  Stylesheet, ein Zählpixel oder ein Bild ohne Alt-Text enthält.
- **[#65](https://github.com/blitzsicht/falzmarke/issues/65)** gibt dem Befehl `email` keine
  Empfängerauflösung und keinen Versandpfad. Der MCP-Dienst gibt Dateien zurück, keine
  Sendequittungen.
- **Kein `falzmarke-versand`.** Der Arbeitsname aus 0029 bleibt unangelegt. Sollte er einmal
  entstehen, verwendet er falzmarke als Bibliothek — nicht umgekehrt.

## Was diese Entscheidung nicht ist

Sie sagt nicht, dass die erzeugten Mails ungeprüft blieben. Für sie gilt dasselbe wie für die
Briefe: Die E-Mail-Regeln tragen ihre Herkunft wie alle anderen, und bis zum Normabgleich
([#12](https://github.com/blitzsicht/falzmarke/issues/12)) stammen sie aus Sekundärquellen. Was
aus einer einzelnen Quelle stammt, wirkt als Warnung, nicht als Fehler.

Sie sagt auch nicht, dass Versand unwichtig wäre — sie sagt, dass er ein eigenes Versprechen ist.
Das ist der Satz aus 0029, und er gilt für E-Mail schärfer als für den Brief, weil die Grenze
hier bequemer zu überschreiten wäre.
