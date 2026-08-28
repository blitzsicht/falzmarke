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

Was das **nicht** aufweicht: Externe Stylesheets, Skripte, Hintergrundbilder, Zählpixel und
Verweise auf Ressourcen im Stil bleiben verboten. Die Dunkelfarben sind fest und kommen nicht
aus dem Profil — eine Markenfarbe, die auf Weiß trägt, trägt auf Dunkel selten, und ein Profil,
das eigene Dunkelfarben mitbrächte, müsste jede davon gegen den dunklen Grund messen.

Dazu eine zweite Prüfung, `emit_html.nicht_umschaltbar()`: Wer eine Farbe inline setzt, muss die
Klasse tragen, die sie umschaltet. Der Fehler, gegen den sie gebaut ist, heißt **halb
umgeschaltet** — beim Bildzeichen der Marke stand die helle Grundregel einmal nach der
Medienabfrage, und das Blatt schaltete um, die Kontur nicht.

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
