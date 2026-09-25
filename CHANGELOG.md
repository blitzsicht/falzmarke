# Änderungen

Das Format folgt lose [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## v0.9.9 — 25.09.2026

### Neu

**Entschieden: falzmarke rechnet nicht** ([ADR 0039](docs/entscheidungen/0039-falzmarke-rechnet-nicht.md)).
Das Werkzeug überträgt, was ihm gegeben wurde — es summiert keine Positionen, bildet keine
Steuerbeträge und prüft nicht, ob Netto plus Steuer den Bruttobetrag ergibt. Wer rechnet, haftet
für das Ergebnis; wer überträgt, muss sagen, dass er nicht rechnet. Dieselbe Linie wie bei „keine
Zertifizierung", „kein Versand" und „falzmarke prüft die Pflichtangaben nicht".

Dazu die beiden Festlegungen, die erst nach der Erhebung aus #113 entscheidbar waren: **ZUGFeRD in
einer ausdrücklich benannten Fassung** (gemessen am 11.09.2026 ist 2.5.2 die aktuelle) — eine
Fassung, die sich zur Laufzeit ändert, ist kein Datenvertrag, denn jede schreibt Dateinamen,
XMP-Schema und Beziehungsangabe im PDF vor. Und **Profil EN 16931 (COMFORT) als Vorgabe**, weil
das genau der Umfang ist, den § 14 Absatz 1 Satz 6 UStG verlangt.

MINIMUM und BASIC WL erzeugt falzmarke **nicht**: Sie enthalten keine Rechnungspositionen und sind
keine Rechnung im umsatzsteuerlichen Sinn. Ein Werkzeug, das „Rechnung" in den Dateinamen schreibt
und eine Buchungshilfe erzeugt, behauptet zu viel.

Und die Zurückhaltung bleibt: Solange kein unabhängiges Prüfwerkzeug das Ergebnis durchlässt, sagt
falzmarke nicht „ZUGFeRD-konform" — dieselbe Regel wie beim Wort „normgerecht".

**Was das Umsatzsteuerrecht bei Rechnungen verlangt — erhoben, mit Fundstelle.** `docs/recht.md`
führte bisher keine einzige Frist zur E-Rechnung. Jetzt steht dort, was § 14 UStG als
**elektronische** Rechnung definiert (strukturiertes Format, elektronisch verarbeitbar) und was
als **sonstige** — und damit die Antwort auf die Frage, die den ganzen Vorgang ausgelöst hat: Ein
PDF ohne strukturierte Daten ist keine elektronische Rechnung. Das ist, was falzmarke heute
erzeugt.

Dazu die gestaffelten Fristen aus § 27 Absatz 38 UStG (allgemein bis Ende 2026, für Aussteller
mit höchstens 800 000 € Vorjahresumsatz bis Ende 2027), die zehn Pflichtangaben aus § 14 Absatz 4
und die drei Fälle, die **dauerhaft** als sonstige Rechnung gehen dürfen: Kleinbeträge bis 250 €
(§ 33 UStDV), Fahrausweise (§ 34) und Rechnungen von Kleinunternehmern (§ 34a).

Ein Befund, der keine eigene Norm hat: Eine **Empfangspflicht** ist nirgends formuliert. Sie
entsteht durch einen Wegfall — § 14 Absatz 1 Satz 5 verlangt die Zustimmung des Empfängers nur
„soweit keine Verpflichtung nach Absatz 2 Satz 2 Nummer 1 besteht". Wo die Ausstellungspflicht
greift, kann der Empfänger nicht mehr ablehnen.

Erhoben aus dem Volltext, nicht aus dem Gedächtnis: UStG und UStDV liegen seit heute im lokalen
Rechtstext-Spiegel. Der Anlass für diese Sorgfalt steht in derselben Datei — § 125a HGB stand
dort noch, als es ihn nicht mehr gab.

**Der Datenvertrag `typ: rechnung` steht — gesetzt wird noch nicht.** Die Felder leiten sich aus
§ 14 Absatz 4 UStG ab, den zehn Pflichtangaben einer Rechnung, erhoben in #113: Rechnungsnummer,
Leistungsdatum oder -zeitraum, Zahlungsziel, Positionen mit Bezeichnung, Menge, Steuersatz und
Betrag, dazu die Summen. Kein Feld ist erfunden. `falzmarke lint` prüft eine Rechnung vollständig,
meldet jedes unbekannte Feld — auch in einer Position — mit dem Vorschlag des nächstgelegenen
Namens, und lässt die Briefprüfungen weiterlaufen: Eine Rechnung ist ein Schreiben.

**Statt zu rechnen, macht das Werkzeug die Probe.** Es bildet keinen Positionsbetrag, keine
Summe und keinen Steuerbetrag (ADR 0039) — es rechnet die gegebenen Werte gegeneinander — Positionen gegen
Netto, Netto plus Steuer gegen Brutto —, die eine Abweichung als **Warnung** meldet und den Lauf
mit Code 0 beendet. Eine Rechnung mit widersprüchlichen Summen geht also durch, und
`skill/references/frontmatter.md` sagt das ausdrücklich.

**Der Renderer bricht bei einer Rechnung ab.** Das war ein Befund und keine Vorsorge: Ohne den
Abbruch fiel `typ: rechnung` in den Briefzweig und entstand als PDF — ohne Positionen und Summen,
die der Brief nicht kennt, und ohne ein Wort darüber. Genau die Fehlerart, gegen die das Werkzeug
antritt.

Beim Bauen gemessen und behoben: Ein Tippfehler in einer Position stand auf Zeile 1, weil die
Zeilensuche nur die oberste Ebene fand; eine leere Rechnungsnummer gab zwei Befunde für einen
Fehler. Vier Gegenproben machen je genau ihren Test rot — der Renderer-Abbruch, die Doppelmeldung,
der Zweig für Wahrheitswerte und die Zeilenangabe. Der Test für Wahrheitswerte stand im ersten
Entwurf an der falschen Stelle: PyYAML liest `ja` als Text, erst `true` trifft den Zweig.

**Die Rechnung trägt ihre Daten maschinenlesbar mit.** Aus `typ: rechnung` entsteht neben dem
gesetzten PDF eine XML nach EN 16931, eingebettet in dasselbe Dokument — ein Schreiben für
Menschen und ein Datensatz für Maschinen, aus einer Quelle. Das PDF wird dadurch PDF/A-3b
statt PDF/A-2b; die Datei heißt `factur-x.xml` und trägt die Beziehung `Alternative`.

**Die Positionstabelle setzt falzmarke selbst** aus `positionen:` und `summen:`. Sie gehört
nicht mehr in den Rumpf: Stünden dieselben Zahlen zweimal in der Quelle, liefen sie
auseinander — und ein PDF mit 1.190,00 € neben einer XML mit 1.109,00 € sieht zweimal richtig
aus, bis die Buchhaltung des Empfängers die XML einliest.

Neu im Datenvertrag, beides von der XML verlangt und nicht erfunden:

- `empfaenger_anschrift:` mit `name`, `strasse`, `plz`, `ort`, `land`. `empfaenger:` sind ein
  bis sechs freie Zeilen; ob die zweite die Straße ist oder eine zweite Namenszeile, lässt sich
  nicht ablesen. Geraten hieße, den Empfänger falsch zu adressieren, ohne dass es auffällt.
- `summen.steuer[].basis` — die Bemessungsgrundlage je Steuersatz. Sie aus den Positionen zu
  summieren wäre Rechnen, und falzmarke rechnet nicht (ADR 0039).

Im Absenderprofil kommt der Abschnitt `rechnung:` mit `ust_idnr:` oder `steuernummer:` und
`land:` dazu. Name und Anschrift kommen weiter aus `absender:`. Fehlt eine Angabe, meldet
`lint` das — aber erst, wenn ein Schreiben `typ: rechnung` trägt.

Geprüft wird, dass die Angaben da sind, nicht ob sie gelten: Eine USt-IdNr. gegen das
Bundeszentralamt abzugleichen hieße Netz (ADR 0005). Ob das Ergebnis als ZUGFeRD-Rechnung
durchgeht, sagt nicht falzmarke, sondern der fremde Prüfer in der CI (#118).

**Beträge werden übertragen, nicht gebildet — auch der Steuergesamtbetrag.** Bei mehreren
Steuersätzen gehört `steuer_gesamt:` unter `summen:`; falzmarke summiert die Einzelbeträge
nicht. Ein Betrag mit mehr als zwei Nachkommastellen und ein Summenfeld, das keine Zahl ist,
werden gemeldet statt gerundet oder übergangen — auch beim Setzen über den MCP-Dienst, der
ohne `lint` arbeitet. Eine Rechnung ohne Umsatzsteuer (etwa nach
[§ 19 UStG](https://www.gesetze-im-internet.de/ustg_1980/__19.html)) erzeugt falzmarke noch
nicht: Die XML zeichnet jede Steuer als Regelsatz aus.

**XRechnung für öffentliche Auftraggeber.** Mit `erechnung: xrechnung` und einer `leitweg_id:` im
Kopf entsteht XRechnung 3.0 in CII. Der neue Befehl `falzmarke xml` schreibt sie als reine
XML-Datei, ohne PDF — den Weg an Behörden; `render` setzt sie auch als PDF und sagt dabei, dass
eine Behörde die XML erwartet. `lint` prüft die Leitweg-ID nach der Format-Spezifikation 2.0.2
(Form und Prüfziffer) und nennt auf einmal alles, was XRechnung zusätzlich verlangt:
Käuferreferenz, Ansprechpartner, Konto und die elektronischen Adressen beider Seiten. Die CI hält
die eigene XRechnung gegen Mustang (XR_30), dazu eine Gegenprobe ohne Käuferreferenz, die an genau
BR-DE-15 scheitern muss. Welche Fassung ein Empfänger annimmt, entscheidet der Empfänger.

**Die E-Rechnung trägt Ansprechpartner, Konto und elektronische Adresse.** Die eingebettete XML
schreibt jetzt den Kontakt des Ausstellers aus dem Informationsblock (dieselbe Person wie im PDF),
einen Zahlungsweg per Überweisung aus dem neuen Profilfeld `rechnung.bank` und die elektronische
Adresse aus `rechnung.adresse`. `lint` prüft Form und Prüfziffer der IBAN und warnt, wenn sie
nicht auch in der Fußzeile steht. Unter EN 16931 ist alles freiwillig; XRechnung (#117) verlangt
alle drei Angaben. Außerdem liest die Zeile „E-Rechnung“ im Messbericht Beilage, Guideline-ID,
Profil und Factur-X-Fassung jetzt aus der fertigen Datei — vorher stammten sie aus Konstanten,
und die Zeile konnte nie rot werden.

**Beispiele und Goldens für Rechnungen.** Zwei neue Beispiele laufen in der CI mit: eine Rechnung
mit 19 % und 7 % und eine Kleinbetragsrechnung. Jedes Rechnungsbeispiel wird Byte für Byte gegen
ein festgehaltenes PDF und gegen seine eingebettete XML gehalten; `scripts/golden_rechnung.py`
erneuert beide. Wie bei der `.eml` setzt `SOURCE_DATE_EPOCH` die Erstellungszeit im PDF fest,
ohne die Variable bleibt es bei der Rechnerzeit. `lint` meldet zwei stille Abweichungen zwischen
PDF und XML als Fehler: einen Steuersatz einer Position ohne eigene Zeile in `summen.steuer` —
das PDF zeigt nur die Summenzeilen — und einen Ländercode, der kein amtlicher
ISO-3166-1-Alpha-2-Code ist, etwa `land: Deutschland`.

Behoben dabei: Unter Windows bettete `render` die Rechnungs-XML mit `\r\n` statt `\n` ein, dieselbe
Quelle ergab also je nach Rechner eine andere Datei. `falzmarke xml` war davon nicht betroffen.

**Eine Seite zu Rechnungen.** `docs/rechnung.md` sagt, was falzmarke bei `typ: rechnung` erzeugt:
ZUGFeRD als PDF/A-3b mit eingebetteter XML für Firmen, XRechnung 3.0 als reine XML für Behörden,
beide im Profil EN 16931. Die Seite nennt auch, wer das Ergebnis mit welcher Regelfassung prüft
und was falzmarke nicht tut: rechnen, Nummern vergeben, buchen, mahnen, versenden. README und
Skill unterscheiden die zwei Formate jetzt in einem Satz, und die PDF/A-Aussage im README ist
eine Fallunterscheidung: A-2b im Normalfall, A-3b, sobald eingebettet wird.

**Die Signatur liegt als Daten neben den Goldens.** `tests/golden/email/signatur-faelle.json`
trägt je Fall das vollständige Absenderprofil, den Kopf des Schreibens und die Blöcke, die
`eml.signatur_bloecke()` daraus macht. Der Anlass: `falzmarke.com` hat dieselbe Regel als
JavaScript-Port im Browser (Name und Anschrift sind personenbezogen und sollen das Gerät nicht
verlassen) und hält sie gegen die `.eml`-Goldens. Die laufen aber alle auf **einem** Profil, und
damit war genau ein Weg durch die Funktion belegt; für die übrigen hatte das Website-Repo eigene
Erwartungen aufgeschrieben, die nur zeigen, dass der Port sich nicht selbst widerspricht. Acht
Fälle deckeln das jetzt ab, darunter alle drei Quellen für den Namen und die Entdoppelung über
zwei Blöcke, die am mitgelieferten Profil leerläuft. **Jeder Fall muss sich von jedem anderen
unterscheiden** — beim Bauen fiel dadurch auf, dass zwei Fälle für zwei verschiedene
Rückgriffstufen identische Blöcke ergaben, also einen Port durchgelassen hätten, der nur eine
davon kennt. Das JSON entsteht im selben Lauf wie die Goldens; vier Gegenproben verfälschen je
eine Quellzeile in `signatur_bloecke()` und verlangen namentlich die Fälle, die rot werden.
Nebenwirkung: Das Website-Repo kann seine Abschrift von `typst/profiles/example.yaml` fallen
lassen — es hat keinen YAML-Parser, das Profil steht jetzt als JSON da.

**Ein englisches README.** Alle Verzeichnisse und Listen, in die das Werkzeug sachlich gehört,
sind englischsprachig — wer über eines davon kam, landete auf einer Seite, die er nicht liest
(#237). `README.en.md` ist bewusst eine Kurzfassung und keine Spiegelung der deutschen: Die
lange Fassung hängt an sechs Prüfungen, die eine Zweitfassung nicht hätte, und wäre ab dem
nächsten Merge still veraltet. Der Vorbehalt zur Quellenlage steht auch dort — eigens
geschrieben, nicht übersetzt —, und die gesperrten Konformitätswörter haben jetzt englische
Gegenstücke. Ohne sie hätte die Sperre aus ADR 0032 ausgerechnet dort nicht gegriffen, wo das
Werkzeug neu vor Publikum steht.

**Ein Mail-Beispiel mit Listen** — `examples/email/email-liste.md`. Bis dahin enthielt **kein**
Beispiel eine Liste, und damit belegte kein Golden, wie `<ul>`, `<ol>`, die eingerückte
Unterliste und `start` bei einer Nummerierung ab *n* aussehen. Aufgefallen ist das in #289, wo
die Breitenprüfung erst nachträglich von Absätzen auf Listen ausgeweitet werden musste — gefunden
hat es dort kein Golden, sondern ein eigens gebauter Test.

Zwei Prüfungen sichern nicht das Verhalten (das tut das Golden byteweise), sondern die
**Abdeckung**: dass das Beispiel alle vier Formen trägt und dass mindestens ein Listenpunkt
**länger als die Faltbreite** ist. Der zweite Punkt ist gemessen und nicht vorsorglich: Im ersten
Entwurf waren alle Punkte kürzer als 72 Zeichen, `format=flowed` hatte also nichts zu falten, und
eine Sabotage der Festzeilen-Logik in `emit_text.teile()` ließ jedes Golden unberührt. Das
Beispiel deckte die halbe Zusage nicht ab, und zwar unsichtbar.

**Rechnungen von Kleinunternehmern (§ 19 UStG).** Steht im Profil `rechnung.kleinunternehmer: true` und ein eigener `kleinunternehmer_hinweis:`, entsteht eine Rechnung ohne Umsatzsteuer:
- **PDF:** nur der Gesamtbetrag und darunter der Hinweis.
- **XML:** Kategorie E mit Satz 0 und Steuer 0, dazu derselbe Hinweis als BT-120 und BT-33.
- **Kein Vorgabetext:** falzmarke gibt keinen Wortlaut vor und bewertet ihn nicht.
- **`lint`-Fehler:** ein fehlender Hinweis, ein Steuersatz oder eine Steuerzeile trotz Status, und `brutto` ungleich `netto`.
- **Neue Beispiele:** eine Rechnung als ZUGFeRD und eine als XRechnung. Mustang prüft beide, der KoSIT-Validator die XRechnung, jeweils mit Gegenproben an BR-E-10 und BR-E-05.

Die Umsatzgrenzen prüft falzmarke nicht (ADR 0041).

### Geändert

**Tabellen stehen nicht auf dem Zeilenraster, und das ist beschlossen.** Die Lesbarkeit gewinnt: Der Innenabstand der Zellen bleibt bei 1,4 mm, die Rasterprüfung nimmt Tabellen weiter aus. Der rastertreue Wert (2,293 mm) ließe eine fünfzeilige Tabelle um 9 mm wachsen und änderte jedes Bild mit Tabelle, und die Übergänge blieben auch dann gebrochen. Messwerte und Begründung stehen an einer Stelle, im Docstring von `_tabellenbereiche`; die Referenz sagt nur noch, dass es so ist. Ein Test misst die Zeilenhöhe im gerenderten PDF gegen einen festen Sollwert, damit die Ausnahme nicht still wächst, mit Gegenprobe an drei verstellten Innenabständen.

**Die Form-A-Maße stehen jetzt auf zwei unabhängigen Quellen — mehr als die Form-B-Maße.** `geometrie.form_a.masse` trägt `mehrfach_bestaetigt` statt `einzeln_belegt`, getragen von der Form-A-Zeichnung im Onlineprinters-Magazin und dem Federwerk-Artikel: zwei voll zählende Quellen aus zwei Gruppen. Die fünf Form-B-Regeln stehen dagegen auf zwei Ansichten derselben Zeichnung, also auf einer Gruppe. An der Prüfung ändert sich nichts — die Maße am fertigen PDF wirkten seit jeher als Fehler, weil die Nachmessung den Regelkatalog gar nicht kennt; nachgemessen an einem Form-A-Brief, dessen Bericht mit alter und neuer Stufe byte-gleich ist. Was sich ändert, ist die Auskunft des Werkzeugs über die eigene Beleglage, und die war falsch. Die Entscheidung steht in ADR 0046; `docs/recht.md` sagt jetzt dazu, dass die Herkunftstabelle für die Briefmaße nicht gilt.

**Das Regelwerk sagt jetzt auch für GmbH, AG und eG, welche Angaben die Vorschrift aufzählt.** Bei `email.pflichtangaben` nannten `hgb_37a` und `hgb_125` den Inhalt der Pflicht, `gmbhg_35a`, `aktg_80` und `geng_25a` dagegen nur die Wendung „gleichviel welcher Form" — also den Grund, aus dem die Pflicht auch für E-Mails gilt. Für die häufigste Rechtsform überhaupt stand damit nirgends, was zu nennen ist. Die drei Belege führen die Aufzählung jetzt mit: Rechtsform, Sitz, Registergericht, Registernummer, die vertretungsberechtigten Personen mit ausgeschriebenem Vornamen, dazu die Unterschiede zwischen den drei Vorschriften (Grundkapital statt Stammkapital, der Vorstandsvorsitzende als solcher zu bezeichnen, keine Kapitalangaben im GenG). Am Werkzeug ändert das nichts — Stufe, Ebene und Wirkung der Regel sind unverändert, und der Inhalt von `pflichtangaben` wird weiterhin nicht geprüft (ADR 0005). Sichtbar wird es dort, wo die Daten gelesen werden: im Signatur-Baukasten auf falzmarke.com.

**Eine Mail geht ins Mailprogramm, nicht in den Browser.** `SKILL.md` hat den Umweg bis dahin
selbst empfohlen: „Diese Vorschau ist das, was gezeigt wird — nicht die `.eml`" machte die
HTML-Vorschau zum Regelfall, und „`--oeffnen` gehört im Gespräch dazu, sobald ein Mensch die
Nachricht wirklich abschicken will" überließ den Rest der Auslegung. Die Folge war, dass jede
Sitzung es anders machte und die fertige `.eml` unbenutzt neben der Vorschau lag. Jetzt ist
`--oeffnen` der Regelfall und legt den Entwurf im Mailprogramm an; die `.html` entsteht nur auf
ausdrückliche Nachfrage und wird nicht mehr von selbst gezeigt. Ohne das Flag laufen nur Serien,
Prüfläufe und Automatikläufe. Drei Prüfungen halten das fest, samt Gegenprobe gegen die
Rückkehr des alten Wortlauts.

**Der Entwurf sagt, dass er den Faden nicht trägt.** `antwort_auf:` setzt `In-Reply-To` und
`References` in die `.eml`; der Weg über das Mailprogramm nimmt beide nicht an — gemessen am
11.09.2026 für Outlook für Mac, drei Versuche, alle abgelehnt. Bis dahin fiel das still unter
den Tisch, und die Antwort begann einen neuen Thread, ohne dass jemand einen Grund sah. Der
Befehl meldet es jetzt, wenn ein Bezug gesetzt ist, und nennt die `.eml` als den Weg, der den
Faden hält. Nur dann — stünde die Warnung unter jeder Mail, läse sie niemand.

**Der Fließtext einer E-Mail nimmt die Breite des Lesefensters.** Bis dahin trugen Absätze und
Listen `max-width: 640px`. Die Überlegung dahinter stimmt — 640 px bei 16 px sind rund 75 Zeichen,
und lange Zeilen lesen sich schlechter —, nur hatte die Zahl keine Quelle: nicht in der DIN 5008,
nicht im Regelkatalog, kein Eintrag in `quellen.yaml`. Eine Setzung auf Ebene *Praxis* nach
ADR 0035, und Praxis ist nie ein Fehler — wirkte hier aber als einer, weil `Bericht` keine
Warnstufe kennt und `verify --email` mit Code 2 endete. Der Deckel fällt deshalb weg, und die
Prüfung steht in der Gegenrichtung: „Fließtext ohne Breitendeckel" schlägt an, wenn er
zurückkommt. Sie misst nur die eigenen Absätze — eine mitgebrachte Signatur behält ihre Breite,
sonst wäre es der Fehler aus #279 noch einmal. Die Gegenprobe setzt den Deckel wieder ein und ist
einzeln gegen eine wirkungslose Prüfung gefahren. Der Klartextteil bleibt, wie er war: Dort
faltet `format=flowed` nach RFC 3676 weich, und der Empfänger bricht neu um.

**Eine Prüfung der fertigen E-Mail kann jetzt warnen statt zu scheitern.** Bis hierher wirkten
alle 24 Prüfungen in `pruefung_eml.py` als Fehler — nicht aus Absicht, sondern weil keine einen
Regelnamen trug und `regeln.deckel(None)` vorsichtshalber `fehler` zurückgibt. Damit lief ADR 0035
an der halben Kette vorbei: Im Linter wird eine Regel auf der Ebene *Praxis* längst herabgestuft,
an der fertigen Datei gab es nur „Fehler" oder „gar nicht prüfen". Genau daran ist die Lesebreite
in #289 gestorben — eine Setzung ohne Quelle, die als harter Befund wirkte, und der einzige Ausweg
war, sie zu entfernen.

`regeln/email.yaml` trägt jetzt die Achse `pruefung:` neben `lint:` und `typografie:`, und alle 24
Prüfungen sind zugeordnet: zehn auf RFC-Primärquellen (3676 für `format=flowed`, `delsp`,
Space-Stuffing und die Signaturzeile; 2045 für Zeichensatz und Kodierung; 5322 für `Date` und die
Message-ID; 2046 für die Reihenfolge der Alternativen — jede mit nachgelesener Fundstelle), die
übrigen als Zusagen des Werkzeugs nach ADR 0034. `geometrie.Pruefung` trägt eine `stufe` mit der
Vorgabe `fehler`, `Bericht.ok` zählt nur Fehler, und eine Warnung erscheint auch im **knappen**
Bericht samt Schlusssatz — sonst wäre sie im grünen Lauf keine.

**Für keine einzige Prüfung ändert sich die Wirkung.** Das ist beabsichtigt: Der Gewinn ist nicht
eine mildere Prüfung, sondern eine begründete. Die Briefmaße bleiben ebenfalls unberührt, dort
warnt kein Maß. Drei Gegenproben halten das fest — dieselbe Regel einmal als Fehler und einmal als
Warnung über dieselbe Datei, und ein verschobenes Falzmaß, das weiterhin ein Fehler ist.
`tests/test_quellenlage.py` liest die Regelnamen aus dem Syntaxbaum von `pruefung_eml.py`: Eine
neue Prüfung ohne Katalogeintrag besteht nicht, und ein Katalogeintrag ohne Prüfung im Code auch
nicht.

**Leitwort und Schlusspunkt im Betreff haben eigene Regeln.** Bisher meldeten sie unter dem Namen `betreff` und hingen damit am Katalogeintrag der Betrefflänge, in Brief und E-Mail. Eine Herabstufung der Länge hätte beide stillschweigend mitgezogen. Jetzt gibt es vier eigene Einträge (`betreff.leitwort`, `betreff.schlusspunkt`, `email.betreff_leitwort`, `email.betreff_schlusspunkt`), alle mit `herkunft: werkzeug` und ohne Quelle, denn für beide Regeln hat niemand eine gefunden. Im Brief bleibt die Wirkung ein Fehler. **In der E-Mail sind Leitwort und Schlusspunkt jetzt eine Warnung** (Ebene `praxis`, das Leitwort steht im Vorschaufenster neben dem „Betreff“ des Clients) statt eines Fehlers. Die Ausgabe des Linters nennt die neuen Regelnamen; ein Skript, das sie nach `betreff` durchsucht, findet nur noch die Länge. Ein Test stuft die Länge herab und prüft, dass Leitwort und Schlusspunkt unverändert melden.

Eine Quelle, die zur Regel schweigt, zählt nicht mehr für ihre Stufe: Sieben Regeln gelten jetzt als Werkzeugprüfung, drei warnen statt Fehler zu werfen — und wo der Typografie-Pass deshalb nichts mehr setzt, sagt der Linter es an der Stelle.

Wo eine Regel seit der Quellenprüfung keine Quelle mehr hat, beruft sich ihre Meldung nicht länger auf die Norm: Anrede, Grußformel und Anschriftfeld sagen jetzt, dass das Werkzeug es so hält.

Das geschützte Leerzeichen hinter Kürzeln wie `Nr.` oder `Tel.` hat eine eigene Regel (`schreibweise.kuerzel_vor_angabe`); `schreibweise.zahlengliederung` bleibt den Dreiergruppen vorbehalten.

`text.anschrift_ohne_leerzeilen` ist keine Werkzeugprüfung mehr, sondern `einzeln belegt`: Der
Wikipedia-Artikel nennt beide Hälften der Regel — bis zu 6 Zeilen in der Anschriftzone, keine
Leerzeilen darin —, war aber nie als Quelle eingetragen. Die Meldung beruft sich deshalb wieder
auf die Quelle statt auf das Werkzeug. Die Wirkung bleibt eine Warnung; eine Quelle allein lässt
keinen Lauf scheitern ([ADR 0044](docs/entscheidungen/0044-woertlicher-beleg-schlaegt-werkzeugeinstufung.md)).

Die Regeldatei sagt jetzt, warum der Wikipedia-Artikel für das Anschriftfeld 32 mm (Form A) und
50 mm (Form B) nennt, während unsere Werte 27 und 45 mm lauten: Es sind zwei verschiedene Kanten
— der Artikel meint die Oberkante der Zusatz- und Vermerkzone, wir die des Briefkopfs, und
dazwischen liegen die 5 mm der Rücksendeangabe. Kein Widerspruch und keine geänderte Prüfung.

Die Maße, die falzmarke am fertigen PDF nachmisst, tragen jetzt die Stufe, mit der sie wirken.
Drei Geometrie-Regeln standen auf „einzeln belegt" und hätten nur warnen dürfen, ließen einen
Lauf aber scheitern — die Nachmessung kennt den Regelkatalog nicht. Aufgelöst über die
Beleglage: Die Mindesthöhe des Informationsblocks (40 mm) und die Heftrandgrenze der Marken
(20 mm) sind aus zwei neuen, unabhängigen Quellen belegt, die Schriftgrößen aus zwei weiteren.
Die Länge der Marken ist dagegen keine Aussage der Norm — zwei Quellen sagen das ausdrücklich —,
sondern eine Setzung des Werkzeugs; sie ist als solche ausgewiesen und aus der Regel
herausgelöst. Am Verhalten ändert sich nichts: Derselbe Brief ergibt denselben Bericht
([ADR 0047](docs/entscheidungen/0047-geometrie-regeln-tragen-ihre-stufe.md)).

### Behoben

**Ein doppelt vergebener Schlüssel in einer Regeldatei bricht den Lauf ab, statt den ersten Inhalt stillschweigend zu verwerfen.** `geometrie.form_a.masse` trug einen Tag lang zwei `bemerkung:`; YAML nimmt in diesem Fall den letzten, und die Erklärung der 32 mm war im geladenen Regelwerk nicht mehr vorhanden — ohne Meldung, denn die Datei lädt ja. `regeln._yaml_laden()` weist das jetzt mit Datei, Schlüssel und beiden Zeilennummern ab, in den Regeldateien wie im Quellen-Register. Drei Tests halten es fest, darunter die Gegenprobe, dass derselbe Inhalt ohne Duplikat weiter lädt.

veraPDF wird mit fester Version und geprüftem SHA-256 geladen; ein abweichender Digest bricht den Lauf ab, bevor das Archiv entpackt wird.

**Eine Mail geht in ein Fenster auf, nicht in zwei.** `--oeffnen` konnte zwei Fenster
hinterlassen: Das Steuerskript öffnete den Entwurf, *bevor* falzmarke seine Zählung gegen die
Vorgabe halten konnte — fiel sie durch, stand das Fenster schon offen, und der Rückfall legte
die `.eml` obendrauf. Das zweite Fenster ist ein Lesefenster ohne Senden-Knopf; derselbe Fehler
erklärte also beide Hälften der Meldung vom 11.09.2026. Jetzt legt das Skript die Nachricht nur
an und gibt ihre Kennung zurück; geöffnet wird erst nach bestandener Prüfung, und was durchfällt,
wird verworfen, bevor es jemand sieht. Kehrt das Skript gar nicht zurück, gilt der Zustand als
**ungewiss** — dann wird weder geöffnet noch verworfen noch nachgeschoben, sondern gesagt, dass
im Mailprogramm nachzusehen ist. Der Rückfall sagt außerdem dazu, dass die Datei als Lesefenster
erscheint und nicht als Entwurf.

**Der Outlook-Entwurf kommt vom Konto des Profils.** `--oeffnen` legte den Entwurf ohne Konto an,
und Outlook nahm sein Standardkonto — wer mehrere Postfächer hat, musste „Von" bei jeder Mail von
Hand umstellen und verschickte vom falschen, wenn er es vergaß. Jetzt sucht das Steuerskript das
Konto mit der Adresse aus `email.absender` und legt den Entwurf darauf an; welches Konto er
tatsächlich trägt, wird am fertigen Objekt zurückgelesen. Passt es nicht oder bietet Outlook keins
an, entsteht der Entwurf trotzdem, und die letzte Zeile der Ausgabe lautet `ABSENDER PRÜFEN: …`.
Belegt ist der Weg für das klassische Outlook für Mac; im neuen Outlook sieht die
Programmsteuerung keine Konten, dort bleibt es bei der Warnzeile.

Zwei Fehler im selben Weg sind mit behoben, beide am 13.09.2026 am echten Outlook aufgetreten: Die
Suche nach dem Mailprogramm hing über das laufende Outlook und endete nach 20 Sekunden mit einem
Traceback und Exit 1 — sie fragt jetzt `NSWorkspace` und meldet eine gerissene Frist als Satz. Und
das Öffnen des Entwurfs suchte ihn mit `whose` unter allen ausgehenden Nachrichten, was im
klassischen Outlook nicht in 90 Sekunden zurückkam; es greift jetzt direkt über die Kennung zu.

**Der Mail-Rumpf erscheint im klassischen Outlook nicht mehr kursiv.** Die Schriftfolge nannte
„Segoe UI“; die Schrift ist auf dem Mac nicht installiert, und der Editor des klassischen Outlook
für Mac ersetzte sie durch einen kursiven Schnitt — sichtbar in jedem Entwurf aus `--oeffnen`.
Gemessen am 13.09.2026 mit vier Schriftfolgen in einem Entwurf: beide mit Segoe kursiv, beide ohne
normal. Die Folge lautet jetzt `-apple-system, Roboto, Helvetica, Arial, sans-serif`; unter Windows
steht damit Arial statt Segoe UI.

**Ohne Outlook-Konto zur Profiladresse sagt die Warnzeile, was wirklich los ist.** Nannte das Profil
eine Adresse, für die Outlook kein Konto hat, lag der Entwurf auf dem Standardkonto, die Signatur im
Rumpf nannte trotzdem die Profiladresse, und die letzte Zeile riet „unter Von umstellen" — dort stand
die Adresse gar nicht zur Wahl. Das Steuerskript meldet jetzt in einer dritten Nachweiszeile, ob die
Suche das Konto gefunden hat (`gefunden`), ob Outlook Konten zeigte, aber keins mit dieser Adresse
(`fehlt`), oder ob es gar keine zeigte (`-`, nicht geprüft). Bei `fehlt` nennt die Warnzeile die
abweichende Signatur und rät zu einem anderen Profil oder einem eingerichteten Konto; ohne lesbare
Konten steht „nicht geprüft" da statt einer Behauptung.

**Rechnung aus einem Profil ohne USt-IdNr.** Trug das Profil nur `rechnung.steuernummer:`, fiel die eingebettete XML bei einem Prüfprogramm an der Regel BR-CO-26 durch: EN 16931 verlangt eine Verkäuferkennung, eine Registerkennung oder die USt-IdNr., und die Steuernummer zählt dafür nicht. falzmarke schreibt die Steuernummer in diesem Fall zusätzlich als Verkäuferkennung, wie es das Beispiel des FeRD vormacht. Mit USt-IdNr. bleibt die Datei, wie sie war. Mustang und der KoSIT-Validator prüfen den Fall jetzt in der CI, mit einer Gegenprobe, die an BR-CO-26 scheitern muss.

**`verify --email` sieht einen Knopf, der in Outlook zerfällt, und der Abstand unter einer Liste
ist kleiner.** Am 14.09.2026 meldete die Prüfung 27/27 und 29/29, während in Outlook für Mac der
Termin-Knopf der mitgebrachten Signatur die Zeile davor überlappte und in zwei Kästen zerfiel. Der
Knopf war ein `<a style="display:inline-block;padding:…">`; der Google-Knopf derselben Signatur
stand in einem `<table><td>`-Gerüst und hielt seine Form. Die eingebettete Signatur wurde bis dahin
nicht angesehen.

Neu ist die Prüfung „Kein Anker als Knopf": Sie findet `display:inline-block` zusammen mit `padding`
oder `margin` im `style` desselben `<a>` — in jeder Attributreihenfolge, mit einfachen oder doppelten
Anführungszeichen, über mehrere Zeilen. Jedes Merkmal allein und ein Kasten am `<span>` bleiben
unbeanstandet. Die Meldung nennt Linktext und Ziel und sagt, dass ein `<table><td>`-Gerüst an die
Stelle gehört. Sie ist eine **Warnung** (Ebene Praxis, ADR 0035): Beobachtet ist der Unterschied der
beiden Aufbauten, dass `inline-block`, `padding` und `margin` die einzelne Ursache sind, ist nicht
gemessen. Jede Nachricht trägt eine Prüfung mehr. Die Signatur selbst ändert falzmarke nicht.

Der letzte Punkt einer Liste trägt keinen unteren Abstand mehr, den setzt die Liste. Gemessen im
gesetzten HTML: Unter dem Listenende standen 16 px (Punkt 4 px plus Liste 12 px), unter einem Absatz
12 px. Ein Browser fasst die Ränder zusammen, die Word-Engine von Outlook addiert sie vermutlich —
ungeprüft, hier steht kein Outlook. Die 16 px erklären die beobachteten „etwa zwei Leerzeilen" allein
nicht; belegt ist nur, dass der Emitter unter dem Listenende nicht mehr Platz lässt als unter einem
Absatz.

**`docs/recht.md` zählt die Stufen nach und datiert sie.** Der Abschnitt „Was die Stufen derzeit wert sind“ beschrieb den Stand vom 27.08.2026: zwei Regeln, deren zweite Quelle schweigt, sechs Warnungen ohne tragende Quelle, und dass die Herabstufung „bewusst nicht geschehen“ sei. Seit #31 zählt eine schweigende Quelle nicht mehr, sieben Regeln führen `werkzeug`, drei fielen von Fehler auf Warnung. Der Abschnitt nennt jetzt die Zahlen von heute mit Standangabe (21.09.2026: 122 Regeln, 10 schweigende Paare, 7 Werkzeugprüfungen, 3 gefallene Regeln, 10 Regeln auf „mehrfach bestätigt“ davon 2 mit ungeprüfter Unabhängigkeit, 44 ungeprüfte Paare als offener Rest, Handarbeit). `tests/test_textkanon.py` zählt diese Zahlen aus den Regeldaten nach und wird rot, sobald eine Tabellenzelle des Abschnitts ihnen nicht mehr folgt oder der Abschnitt ohne Datum dasteht. (#329)

**`lint` meldet, was der Typografie-Pass zurückhält.** `typografie.vorschlaege()` sollte genau das sagen, hatte aber seit v0.4.0 keinen Aufrufer: Eine Regel aus einer einzigen Quelle ließ den Text unverändert, und niemand erfuhr, dass dort ein geschütztes Leerzeichen stünde, wenn sie es trüge. Jetzt wird aus jeder zurückgehaltenen Stelle eine Warnung mit Kennung der Regel, Quellzeile und der Stelle im Wortlaut (`Leerzeichen schützen: „5 kg“`); die zweite Zeile sagt, warum der Pass nicht selbst setzt. Trägt die Regel ihre Stufe, wird wie bisher ersetzt und nicht gewarnt — die Warnung ersetzt die Ersetzung, sie begleitet sie nicht. Wortlaut-Auszüge und das Frontmatter bleiben unberührt, eine Regel ohne Beleg schweigt. Die Warnung hält keinen Lauf an. Zurzeit betrifft das die Einheiten (`5 kg`, `10 EUR`, `8:00 Uhr`) und Kürzel vor einer Angabe (`Tel.`, `Nr.`, `Rechnung 4711`); `vorschlaege()` liefert je Stelle ein Paar aus Kennung und Stelle statt des ganzen geänderten Textes. (#330)

**Die Doku sagt, was der Typografie-Pass tatsächlich setzt.** SKILL.md, README und `references/markdown.md` behaupteten, der Pass setze geschützte Leerzeichen bei `10 %`, `5 kg` und `Nr.` von selbst. Das stimmt nur für Abkürzungen (`z. B.`), Datum (`25. August`) und `§ 5`; Einheiten und Kürzel vor einer Angabe stehen auf einer einzeln belegten Regel, der Pass lässt sie unverändert, und `lint` meldet sie seit #330 als Warnung. Alle drei Stellen sagen das jetzt mit dem Grund und mit dem Handgriff (`5&nbsp;km`). Ein Test liest die zurückgehaltenen Schritte aus den Regeldaten und lässt die Doku rot werden, sobald ein einzelner Schritt seine Stufe erhält oder verliert, statt sie von Hand altern zu lassen. (#331)

**Die Meldung nennt keine Quelle mehr, die zur Regel schweigt.** Der Zusatz „Quelle: sekundär,
einzeln belegt — …" nahm die erste Quelle unter `quellen:`, ohne zu lesen, ob sie zur Sache
etwas hergibt. Bei `text.vermerke_max_3` (Zusatz- und Vermerkzone fasst 3 Zeilen) stand dort die
Maßzeichnung zur Form B, und die ist in den Regeldaten ausdrücklich als schweigend vermerkt —
sie bemaßt die Zone, zählt aber keine Zeilen. Die Meldung führte damit als Beleg an, was keiner
ist. Sichtbar ändert sich genau diese eine Meldung: Sie nennt jetzt den Wikipedia-Artikel, der
die 3 Zeilen unmittelbar nennt. Schweigen alle genannten Quellen, nennt die Meldung keine, statt
auf die erstbeste zurückzufallen. Die **Stufe** einer Regel war davon nie betroffen — dass
schweigende Quellen nicht mitzählen, gilt seit #31 unverändert. Damit ist auch die Zusicherung
aus [ADR 0044](docs/entscheidungen/0044-woertlicher-beleg-schlaegt-werkzeugeinstufung.md)
hinfällig, die Reihenfolge unter `quellen:` sei inhaltlich; sie war die Umgehung, nicht die
Behebung. (#350)

### Infrastruktur

**Die fremde Prüfung für E-Rechnungen steht in der CI** — das Gegenstück zu veraPDF. Mustang
2.26.0 (Apache-2.0) prüft das PDF gegen PDF/A-3 und das eingebettete XML gegen die
Schematron-Regeln des Formats, und es rechnet die Summen nach; das bleibt eingeschaltet, denn
falzmarke rechnet nicht (ADR 0039) und lässt nachrechnen. Das Urteil kommt aus dem Exit-Code,
gemessen statt angenommen: 0 gültig, 255 ungültig, alles andere ist ein Werkzeugfehler und ergibt
NICHT GEPRÜFT. Die Regelfassung steht im Protokoll.

Die Gegenprobe ist Pflicht, und sie ist **inhaltlich** falsch: ein intaktes PDF, dessen XML eine
Regel verletzt. Mustang bringt auch eine kaputte Datei von 15 Byte mit — die fiele aus dem
banalsten Grund durch und sagte nichts über die Schematron-Prüfung.

Zwei Dinge, die gemessen und nicht übergangen sind: Auf macOS liegt unter `/usr/bin/java` ein
Platzhalter, den eine bloße Suche für Java hält — das Skript führt `java -version` deshalb aus. Und
Mustang prüft ZUGFeRD gegen die Regeln der Fassung **2.5.0**, während ADR 0039 2.5.2 als aktuelle
Fassung des Standards nennt; das Protokoll sagt, wogegen tatsächlich geprüft wurde.

Noch prüft der Job nur Referenzdateien des Werkzeugs: Eine eigene Rechnung erzeugt falzmarke erst
mit #116. Deshalb bleibt #118 offen, bis die eigenen Beispielrechnungen dazukommen.

**Der MCP-Dienst ist auffindbar: Themen, Dockerfile, Handschlag-Prüfung.** Das Repository
trägt jetzt `mcp`, `mcp-server` und `model-context-protocol` — bis dahin übersah jedes
Verzeichnis, das GitHub nach MCP-Servern durchsucht, das Werkzeug. Die Themenliste steht dafür
neu in `scripts/topics.py` und wird von `scripts/repo_pruefung.py` bewacht; sie war der einzige
Repo-Sollwert ohne Wächter, und deshalb ist nie aufgefallen, dass das Setz-Skript zehn Themen
nannte, während am Repository fünfzehn lagen. Dazu ein `Dockerfile` im Wurzelverzeichnis, wie
es die MCP-Verzeichnisse zum Bauen erwarten. Ein CI-Job baut das Image bei jedem Push, spricht
über stdio `initialize` und `tools/list`, lässt einen echten Brief im Container setzen und
prüft dessen Messbericht — samt Gegenprobe gegen ein Image ohne das MCP-SDK, in dem derselbe
Handschlag scheitern muss.

**Der MCP-Dienst geht ins offizielle Registry.** `server.json` liegt im Wurzelverzeichnis, und
der Release-Lauf trägt den Server unter `io.github.blitzsicht/falzmarke` ein — per OIDC, ohne
Token und ohne Konto. Der Job steht **hinter** dem PyPI-Job, und das ist keine Vorsicht: Das
Registry prüft die Eigentümerschaft, indem es `mcp-name: <servername>` in der Projektbeschreibung
auf PyPI sucht, und die entsteht erst mit dem Upload. Zwei Workflows auf dasselbe Tag liefen
parallel, und welcher zuerst fertig wäre, entschiede das Wetter. Der Eintrag konnte deshalb nicht
mit dem Vorgang selbst entstehen, sondern erst mit dem nächsten Release — also mit diesem.

Vier Wächter halten die Kette, jeder mit Gegenprobe: die Version in `server.json` gegen
`pyproject.toml` (bei jedem Push) und gegen den Tag (im Release-Lauf), der `identifier` gegen den
Paketnamen, und die `mcp-name`-Zeile im README gegen den Namen in `server.json` — samt der
Grenze dahinter, denn ein angeklebter Satzpunkt verhindert den Treffer des Registry.
`scripts/repo_pruefung.py` fragt zusätzlich das Registry selbst und meldet, solange der Eintrag
fehlt; diese Abweichung ist erwartet und benannt.

Was Glama angeht, bleibt #237 offen: Der Einreichungsweg ist nicht öffentlich dokumentiert (am
11.09.2026 gemessen), und ob Glama den Registry-Eintrag übernimmt, ist nicht zugesagt.
`docs/mcp-verzeichnisse.md` hält den Stand aller Verzeichnisse fest und beschreibt den
Fünf-Minuten-Weg über den Add-Server-Knopf, der ein Konto braucht.

**Der Verlauf in der README trägt keine toten Links mehr.** Die README ist zugleich die
Projektseite auf PyPI, und dort löst `docs/entscheidungen/…` nicht auf. Beim Bündeln dieser
Fassung verwiesen drei Fragmente relativ auf Entscheidungen; `scripts/paket_pruefen.sh` hat es
vor dem Tag gemeldet — die Projektseite einer veröffentlichten Version lässt sich nicht mehr
ändern. `scripts/changelog.py` schreibt solche Verweise beim Erzeugen des Auszugs jetzt auf
absolute Adressen um (Bilder auf `raw`, alles andere auf `blob`), Anker und `mailto:` bleiben
unberührt. Im CHANGELOG selbst bleiben sie relativ, dort sind sie richtig. Mit Gegenprobe: Ohne
die Umschreibung steht der relative Verweis wieder im Auszug.

**`.gstack/` steht in `.gitignore`.** Das Arbeitsverzeichnis der gstack-Skills lag im Baum und
tauchte bei jedem `git status` auf — eine uncommittete Zeile, die die nächste echte Änderung
verdeckt. Für das Werkzeug ändert sich nichts; der Eintrag steht hier, weil `.gitignore` nach der
Regel in `scripts/changelog_pflicht.py` keine Doku ist und die Ausnahme ausdrücklich ein
Maintainer setzt.

**17 der 44 offenen Quelle-Regel-Paare sind nachgelesen, dann wurde die Arbeit eingestellt.**
Der offene Rest aus #31 war bis dahin nur eine Zahl. Nachgelesen wurden die beiden Quellen, deren
Prüfung überhaupt etwas bewegen konnte: die Maßzeichnung `massskizze_b` (zwölf Paare — elf
tragen, eines schweigt) und der Wikipedia-Artikel (fünf Paare, alle tragend). Vier Belege nennen
jetzt ausdrücklich ihre Lücke, etwa bei `geometrie.form_b.zonen`: Die Zeichnung zeigt 17,7 mm als
**eine** Zone, die Aufteilung in 5 + 12,7 mm zeigt sie nicht.

Ein Fund verbessert die Beleglage: `text.vermerke_max_3` hing nach der Zeichnungsprüfung nur noch
an einer Implementierung, weil beide Sekundärquellen zur Zeilenzahl schweigen. Der
Wikipedia-Artikel nennt sie wörtlich („3 Zeilen für die Zusatz- und Vermerkzone") und war dort nie
als Quelle eingetragen.

Die verbleibenden 27 Paare werden nicht weiter geprüft (ADR 0042). Der Grund steht in der
Entscheidung: Ein ungeprüftes Paar wird bereits mitgezählt, Nachlesen kann eine Regel also nur
bestätigen oder herabstufen — und von den 27 liegen 16 bei Quellen, die gar keine Belegsgruppe
tragen, und 10 bei einer, die keine zweite liefern kann. Was dabei ungeprüft bleibt, steht in
`docs/recht.md` und in der erzeugten Liste `docs/offene-quellenpruefungen.md` mit Zahlen daneben.

An den Sollwerten und an der Wirkung der Regeln ändert sich nichts: Was heute Fehler ist, bleibt
Fehler, was Warnung ist, bleibt Warnung.

**Ein zweiter, unabhängiger Prüfer für XRechnung.** Die CI hält die eigene XRechnung jetzt auch
gegen den KoSIT-Validator (1.6.3, Konfiguration XRechnung 3.0.2 vom 31.08.2026) — das Werkzeug
der herausgebenden Stelle, mit einer neueren Schematron-Fassung als Mustang. Das Urteil liest
`scripts/erechnung_kosit.py` aus dem Bericht und nicht aus dem Exit-Code, verlangt das Szenario
„EN16931 XRechnung (CII)“ und lässt die eigene Gegenprobe ohne Käuferreferenz nur gelten, wenn
sie an genau BR-DE-15 scheitert. Validator und Konfiguration sind über Prüfsummen festgelegt;
fällt das Werkzeug aus, ist der Lauf nicht grün.

**Jeder Job in jedem Workflow hat jetzt ein Zeitlimit.** Bisher stand in keinem der sechs
Workflows ein einziges `timeout-minutes` — es galt überall der GitHub-Default von 360 Minuten
pro Job. Auf einem macOS-Runner kostet ein einzelner hängender Job damit rund 22 USD, auf Linux
knapp 2,20 USD, und niemand merkt es, bis die Abrechnung kommt. Betroffen waren 18 Jobs: die acht
in `ci.yml` und zehn weitere in `aktion.yml`, `release.yml`, `video.yml`, `roadmap.yml` und
`oeffentlichkeit.yml` — darunter der PyPI-Upload und zwei wöchentliche Cron-Jobs.

Die Limits liegen zwischen 5 und 15 Minuten. Wo Laufzeiten vorlagen, sind sie daran ausgerichtet
und mindestens dreifach großzügig: der längste Job über sechs CI-Läufe brauchte 3,8 Minuten, der
GIF-Bau 1,4, der PyPI-Upload 1,2. Die ungemessenen Cron- und Selbsttest-Jobs bekommen einheitlich
15 Minuten.

Ebenfalls hier, weil es zur selben Frage gehört: **kein `workflow_dispatch` in `ci.yml`.** Ein
erster Entwurf hatte es — ein Lauf ohne Commit ist bequem. Es hätte aber zwei Pflicht-Checks
aushebeln können: `Changelog-Eintrag` und `Closing-Keyword` laufen nur bei `pull_request`, melden
bei jedem anderen Ereignis `skipped`, und GitHub wertet einen übersprungenen Job als erfüllt. Weil
für die Mergebarkeit der jüngste Check-Run je Name zählt, hätte ein manueller Lauf auf dem
PR-Branch ein rotes Changelog-Gate durch ein grünes `skipped` ersetzt, ohne dass das Gate je
gelaufen wäre. Wer die Suite ohne Commit fahren will, nimmt einen Draft-PR.

Anlass war das erreichte Actions-Spending-Limit der Organisation am 21.09.2026, das in allen
blitzsicht-Repos jeden Job stoppte. falzmarke ist mit 45,72 USD brutto das teuerste Repo, und der
Grund sind die Runner-Preise, nicht die Rechenzeit: 430 macOS-Minuten kosten 26,66 USD, dieselbe
Zeit auf Linux 2,58 USD. Die Plattform-Matrix bleibt trotzdem unangetastet — sie im Pull Request
auf Linux zu kürzen würde `main` sperren, weil das Ruleset `tests (macos-latest)` und
`tests (windows-latest)` namentlich als Pflicht-Check verlangt. Der Umbau gehört in einen eigenen
Vorgang, in dem Workflow und Ruleset zusammen umgestellt werden; im Workflow stehen jetzt die drei
möglichen Wege samt ihrem gemeinsamen Haken.

## v0.9.8 — 10.09.2026

### Neu

- **Eine fertige Signatur mitbringen, statt eine zweite zu pflegen.** `email.signatur_html` im
  Profil zeigt auf eine HTML-Datei neben dem Profil, `email.signatur_text` auf ihre Textfassung.
  Ist das Feld gesetzt, **ersetzt** diese Signatur die aus dem Profil gebaute — sie tritt nicht
  daneben, denn zwei Signaturen unter einer Nachricht sind der Fehler, den dieser Weg abstellt.
  Aus demselben Grund bleibt `email.logo` dabei unbeachtet: Das Logo steckt schon darin.

  Der Anlass ist praktisch: Für Blitzsicht, Siluri und die Kunden erzeugt ein anderes Werkzeug
  längst eine gestaltete Signatur, und die steht in den Mailprogrammen. Wer eine hat, soll sie
  nicht ein zweites Mal beschreiben.

  Übernommen wird der **Rumpf**, nicht das Dokument: `<head>` und `<style>` fallen weg, der Stil
  wandert getrennt heraus und steht **hinter** dem eigenen Dunkelblock im Kopf der Nachricht.
  Ein zweiter `<style>` mitten im Rumpf wäre in mehreren Programmen wirkungslos — Gmail entfernt
  ihn — und in der eigenen Prüfung ein Verstoß.

  **Der Kanal gibt dabei nicht nach.** Die Regeln von ADR 0034 gelten für eine fremde Signatur
  wie für eigenen Satz: kein Skript, kein externes Stylesheet, kein Zählpixel, keine
  Layouttabelle ohne `role="presentation"`, kein Verweis nach außen im Stil. Was durchfällt,
  wird abgelehnt — mit Fundstelle und dem Namen der Datei, nicht stillschweigend eingesetzt.

  Damit ändert sich eine Zusage, und der ADR-Nachtrag sagt genau, um welches Maß: Der Stilblock
  war eine Konstante und sonst nichts. Er hat jetzt zwei Teile — der eigene steht vorn und wird
  weiter Zeichen für Zeichen verglichen, der mitgebrachte dahinter wird **geprüft**. Die
  Reihenfolge ist Teil der Zusage; etwas vor der Konstante bleibt ein Verstoß. (#275)

### Behoben

- **Eine Signatur darf ihre eigene Breite haben.** Die Prüfung aus #264 lehnte **jede**
  Layouttabelle mit `max-width` ab; gemeint war eine einzige — der Umschlag, den falzmarke selbst
  um die Nachricht legt. Er umfasst alles und quetscht deshalb alles, wenn er einen Deckel trägt.
  Eine mitgebrachte Signatur (#275) ist etwas anderes: ein kurzer Block am Ende, dessen eigene
  Breite niemanden quetscht. Die von `cw-core` erzeugten tragen 580 px, und eine Mail damit endete
  mit Exit-Code 2, obwohl inhaltlich nichts falsch war.

  Gemessen wird jetzt die **äußerste** Layouttabelle. Die Gegenprobe hält: Ein `max-width` am
  Umschlag selbst wird weiterhin rot — das ist der Fall aus #264, und er darf nicht mit
  durchrutschen. Die Prüfung heißt entsprechend „Umschlag ohne Breitendeckel". (#279)

### Infrastruktur

- **Die beiden Ausnahme-Labels der Prüfer gibt es jetzt wirklich.** `changelog_pflicht.py` und
  `closing_keyword.py` bieten je einen ausdrücklichen Fluchtweg an, und `CONTRIBUTING.md`
  beschreibt den ersten — nur existierte `ohne-changelog` im Repository überhaupt nicht (37
  Labels, keins mit dem Namen), und `ohne-autoschluss` war von Hand angelegt. Ein dokumentierter
  Fluchtweg ohne Label ist keiner. Beide stehen jetzt im `LABELS`-Block von
  `repo-einstellungen.sh`, und ein Test liest die Namen aus den **Prüfern** statt aus einer
  zweiten Liste: Wird eines umgetauft, fällt der Test, statt dass still eine Ausnahme zumacht.

- **`changelog_pflicht.py` bleibt unter Windows lesbar.** Dieselbe Falle, die den Windows-Lauf
  zu #268 rot gemacht hat: Der Prüfer druckt typografische Anführungszeichen, dort schreibt
  Python in cp1252, und beim Aufrufer kommt statt des Befundes gar nichts an. Aufgefallen wäre
  es hier nie von selbst — der Job läuft ausschließlich auf ubuntu. Der Regressionstest
  erzwingt cp1252 über `PYTHONIOENCODING` und läuft damit auf jedem System. (#276)

## v0.9.7 — 08.09.2026

### Neu

- **Ein ständiges Bcc aus dem Absender-Profil — und der Entwurf trägt es mit.** Wer jede
  ausgehende Nachricht im eigenen Archiv haben will, schreibt die Adresse einmal ins Profil
  statt in jede Datei:

  ```yaml
  email:
    absender: post@example.de
    bcc: archiv@example.de        # oder eine Liste
  ```

  Sie tritt **neben** ein `bcc:` im Frontmatter, nicht an dessen Stelle — die fachliche
  Blindkopie einer einzelnen Mail und die ständige ins Archiv haben nichts miteinander zu tun.
  Dieselbe Adresse in beiden steht einmal im Kopf, verglichen wird die Adresse und nicht die
  Schreibweise. Ohne das Feld ändert sich nichts.

  **Still passiert das nicht.** Der Hinweis auf eine gesetzte Blindkopie wird aus der fertigen
  Datei gelesen und nennt deshalb auch die Adresse aus dem Profil. Eine stille Kopie an einen
  Dritten wäre genau das, was er verhindern soll.

  Dabei fiel ein Mangel auf, der mit #263 entstanden war: **Der Entwurfsweg trug die Blindkopie
  nicht mit.** `--oeffnen` las `To` und `Cc`; das Bcc stand in der `.eml`, `verify --email` hatte
  es gemessen — und im Outlook-Entwurf fehlte es. Eine Zeile, die nie da war, vermisst niemand.
  Das Steuerskript setzt jetzt `bcc recipient`, und der Nachweis zählt vier Zahlen statt drei:
  Empfänger, Kopien, Blindkopien, Anhänge. Am echten Programm nachgezählt. (#272)

## v0.9.6 — 08.09.2026

### Geändert

- **Der Skill nennt jetzt alle seine Befehle.** `serie`, `einlesen`, `preview`, `init` und `mcp`
  standen bis hierher nur in `docs/cli.md` — und `docs/` liegt nicht im Skill-Paket
  (`scripts/skill_packen.sh` kopiert `skill/`). Wer den Skill hochlud, sah fünf Befehle
  nirgends, darunter den einzigen Weg von einem fremden PDF zurück in die Quelle. Der neue
  Abschnitt „Weitere Befehle" beschreibt sie; die Beschreibung im Kopf nennt zusätzlich den
  Serienbrief und das Zurücklesen, weil beide einen eigenen Anlass haben, bei dem niemand von
  sich aus an einen DIN-Skill denkt.

  Dabei fiel eine Lücke in Regel 0 auf: `preview` prüfte die Eingabe nicht. Sie ist im selben
  Zug geschlossen worden — siehe den Punkt zu #267 weiter unten.

  Damit die Liste nicht beim nächsten neuen Befehl wieder still altert, zieht ein Test seine
  Sollmenge aus `falzmarke --help` statt aus einer zweiten Aufzählung. Er wurde gegen drei
  Sabotagen gefahren: `serie` aus dem Dokument entfernt, `init` entfernt bei stehengelassenem
  `init-profil`, und ein erfundener Befehl in den Parser gehängt — jedes Mal rot mit Namen. (#261)

- **`--oeffnen` legt einen Entwurf an, keine Lesekopie mehr.** Auf macOS entsteht damit eine
  ausgehende Nachricht im Mailprogramm — Empfänger, Kopie, Betreff, HTML-Rumpf und alle Anhänge,
  mit Senden-Knopf. Gedrückt wird er von einem Menschen.

  Der Grund für die Änderung steht in der eigenen Messung: Eine `.eml` ist nach RFC 5322 eine
  Nachricht und kein Entwurf. Apple Mail, Thunderbird und Outlook für Mac zeigen sie als
  **Lesefenster**, und die Gegenprobe mit `X-Unsent: 1` ergab keinen Unterschied. Wer die
  Nachricht abschicken wollte, musste „Weiterleiten" nehmen — mit dem zitierten Kopf, den das
  mit sich bringt.

  **Entwurf ja, Senden nie.** ADR 0038 verbot Programmsteuerung bisher ganz; die Begründung ist
  geblieben und ein Glied weitergerückt. Was sie trägt, ist diesmal nicht nur ein Satz: kein
  Versandbefehl im Steuerskript (an jedem Skript und am ganzen Paket gemessen), das Skript eine
  Konstante mit `on run argv` statt einer aus Eingaben zusammengesetzten Zeichenkette, und ein
  **Gegenlesen des Ergebnisses** — das Skript zählt am fertigen Entwurf Empfänger, Kopien und
  Anhänge, und der Befehl hält die Zählung gegen die Vorgabe. Ein Exit-Code von 0 belegt nur,
  dass das Skript durchlief; ein stillschweigend abgelehnter Anhang fällt erst an dieser Zählung
  auf.

  Gemessen ist der Weg für **Outlook für Mac**. Wo er nicht trägt — Windows, Linux, Apple Mail,
  fehlende Automations-Berechtigung —, wird die `.eml` übergeben wie bisher, mit einer Meldung
  und unverändertem Exit-Code. `FALZMARKE_ENTWURF=nie` schaltet nur den Entwurf ab und lässt die
  Dateiübergabe stehen.

  Eine Grenze, die dazugehört und nicht messbar ist: **Das Mailprogramm setzt seine eigene
  Konto-Signatur in den Entwurf.** Trägt das Profil eine, steht sie zweimal darin. Der Befehl
  sagt das beim Anlegen — verhindern kann er es nicht, es geschieht nach seinem letzten
  Handgriff. (#263)

### Behoben

- **Die Nachricht steht linksbündig und wird nicht mehr in 600 px gequetscht.** Der Umschlag trug
  `align="center"` bei fester Breite — ein Newsletter-Idiom, das nie begründet wurde. Sichtbar
  wurde das am 08.09.2026 in Outlook für Mac: Die Nachricht saß mittig im Fenster, während die
  Signatur, die das Mailprogramm darunter anfügt, am linken Rand begann, und eine vierspaltige
  Rechnungstabelle wurde so weit in den Deckel gepresst, dass die Kopfzelle „Datum" **mitten im
  Wort** brach und Beträge zwischen Zahl und Währung. Das Fenster war dabei mehr als doppelt so
  breit wie die Spalte.

  Die Grenze ist nicht verschwunden, sie ist umgezogen: `max-width: 640px` sitzt jetzt an
  Absätzen und Listen, deren Zeilen sonst zu lang zum Lesen würden. Tabellen tragen sie nicht —
  eine Tabelle ist so breit, wie ihre Spalten es verlangen. Rechtsbündige Zellen brechen
  zusätzlich nicht mehr zwischen Zahl und Einheit; das ist eine Anweisung an die Darstellung und
  ausdrücklich **keine** Ersetzung im Text, denn das geschützte Leerzeichen vor „EUR" steht auf
  einer Einzelquelle und darf nach der Quellenlage nicht automatisch gesetzt werden.

  Dabei fiel die Prüfung auf, die das hätte melden sollen: „Breite begrenzt" suchte irgendein
  `max-width` im Dokument und konnte an der entscheidenden Stelle nie rot werden — sie war
  erfüllt, gerade weil der Deckel am Umschlag saß. An ihrer Stelle stehen zwei Prüfungen, die es
  können: „Lesebreite am Fließtext" und „Layouttabellen ohne Breitendeckel", jede mit ihrer
  eigenen Sabotage. (#264)

- **`preview` prüft die Eingabe jetzt vorweg — und schreibt bei einem Fehler kein Bild.** Es war
  der einzige Befehl, der setzte, ohne zu prüfen: `render`, `email` und `serie` rufen die
  Vorprüfung seit jeher auf, `befehl_preview` nicht. Ein Brief mit einem unbekannten
  Frontmatter-Feld endete unter `render` mit Code 1 und unter `preview` mit einem fertigen PNG.

  Das Bild sieht aus wie das Ergebnis. Wer es weitergibt, gibt einen Brief weiter, dessen
  Ablehnungsgrund darin nicht zu sehen ist — Regel 0 („kein PDF ohne grünen `check`") hatte
  damit eine Tür, die niemand für eine hielt. `preview` übernimmt jetzt denselben Block wie
  `render`: Vorprüfung, bei einem Fehler Code 1 und kein Bild, Warnungen weiterhin nur gedruckt.

  **Nachgemessen wird weiterhin nichts**, und das bleibt so: Es entsteht kein PDF, also gibt es
  keine Geometrie zu messen. Eine Vorschau ist ein Blick, kein Beleg — nur stand das bis hierher
  nirgends. Der Wechsel steht unter „Behoben", betrifft aber ein Verhalten, auf das sich jemand
  außerhalb des Repos verlassen haben könnte: Wer `preview` bisher auf einem unfertigen Entwurf
  laufen ließ, bekommt jetzt den Befund statt eines Bildes. (#267)

### Infrastruktur

- **Die CI meldet einen deutschen Schließsatz, den GitHub nicht liest.** „Schließt #261" im
  PR-Rumpf sieht aus wie eine Zusage und ist keine: GitHub wertet beim Merge ausschließlich
  englische Keywords aus. Gemessen an PR #262 — der Rumpf trug den Satz, nach dem Squash-Merge
  stand das Issue weiter offen und musste von Hand geschlossen werden. Aufgefallen ist es nur,
  weil jemand hinterher nachgesehen hat; das ist der teure Teil.

  `scripts/closing_keyword.py` prüft den Rumpf **je Nummer**, nicht als Menge: Ein englisches
  Keyword auf einen anderen Vorgang deckt den deutschen Satz nicht. Sätze in Auszügen zählen
  nicht mit — ein Prüfer, der an seiner eigenen Beschreibung anschlägt, ist keiner. Der neue
  Job „Closing-Keyword" in `ci.yml` ruft ihn auf; soll ein Vorgang bewusst offen bleiben, gibt
  ein Maintainer dem Pull Request das Label `ohne-autoschluss`.

  Die Meldung bleibt dabei unter Windows lesbar: Dort schreibt Python in cp1252, und die
  typografischen Anführungszeichen darin beendeten den ersten Lauf mit einem
  UnicodeEncodeError — der Aufrufer bekam gar nichts, obwohl der Befund richtig war. Dieselbe
  Vorkehrung wie in `falzmarke/cli.py` seit dem 25.08.2026. (`scripts/changelog_pflicht.py`
  druckt dieselben Zeichen und hat sie noch nicht; dort fällt es nur deshalb nicht auf, weil
  der Job ausschließlich auf ubuntu läuft.)

  Wirksam als Pflicht-Check wird er, sobald ein Maintainer einmal
  `bash scripts/repo-einstellungen.sh` fährt — `scripts/pflicht_checks.py` liest den Job aus
  `ci.yml` und trägt ihn dort ein. Bis dahin läuft er sichtbar, blockiert aber nicht. (#268)

## v0.9.5 — 08.09.2026

### Neu

- **`email.logo` nimmt jetzt auch eine Adresse und eine Data-URI.** Bisher nur einen Dateipfad,
  und der wird als CID-Anhang eingebettet — für `falzmarke email` die richtige Wahl, weil das
  Bild dann mitreist und auch ohne Netz ankommt. Der Signatur-Baukasten auf falzmarke.com
  erzeugt aber dieselbe Auszeichnung im Browser, und eine Webseite hat keinen MIME-Container:
  Dort fehlte das Logo deshalb ganz.

  Drei Formen, und die Wahl folgt aus dem Wert: ein Pfad wird eingebettet, `https://…` steht
  als Adresse im `src`, `data:image/…;base64,…` steckt im HTML-Teil. **Die Datei bleibt die
  Vorgabe.** Was die beiden anderen kosten, sagt das Werkzeug beim Setzen — auf der
  Kommandozeile unter der erzeugten Datei, im MCP-Dienst als Feld `logo.hinweis`: Eine Adresse
  wird von Outlook und Gmail standardmäßig blockiert, eine Data-URI zeigt Gmail in der
  Weiterleitungsansicht nicht an und Outlook hängt sie als namenlosen Anhang an. Gelesen wird
  dafür die fertige Nachricht, nicht das Profil — gemeldet werden soll, was drinsteht.

  Ein SVG bleibt in allen drei Formen ausgeschlossen; geprüft wird auch die Endung einer
  Adresse und der Typ einer Data-URI. Nennt eine Adresse keine Endung (`…/logo?id=7`), geht sie
  durch: Was dort liegt, weiß nur der Server, und danach zu fragen hieße, ihn abzurufen.

- **Der Linter schweigt nicht mehr, wenn er nicht messen kann.** `email.logo_kontrast` prüft,
  ob ein Logo auf hellem wie auf dunklem Grund trägt. Bei allem, was keine Datei war, kehrte
  die Prüfung bisher wortlos zurück — sie sah grün aus und hatte nichts angesehen. Eine
  Data-URI wird jetzt gemessen wie eine Datei; bei einer Adresse sagt die Warnung ausdrücklich,
  dass **nicht** gemessen wurde und warum: Messen hieße abrufen, und das tut dieses Werkzeug
  nicht (ADR 0034).

- **Höchstens ein Bild in einer erzeugten Mail.** ADR 0034 sagt das seit August — gemessen hat
  es niemand, drei Bilder mit `cid:` wären anstandslos durchgegangen. Aufgefallen ist die Lücke
  erst, als die Quellenregel fiel: Sie hielt die Anzahl nebenbei mit, weil ein Bild in der
  Nachricht dort erst hineingelegt werden muss. Aus demselben Grund wandert die
  Zählpixel-Erkennung vom Prüfer zum Emitter — sie war der zweite Zaun hinter dem ersten, und
  der erste ist weg. (#243)

### Geändert

- **Die Signatur mit Logo steht jetzt zweispaltig.** Bisher trug die Layouttabelle nur den
  Namen; Kontakt und Rechtsangaben standen darunter und liefen unter dem Bild hindurch — das
  sah aus wie ein Zitatblock mit einem Logo davor. Jetzt trägt die rechte Spalte alle drei
  Blöcke, getrennt durch eine dünne senkrechte Linie. Die Linie ist **neutral** und kommt nicht
  aus dem Profil: Eine gefärbte wäre die Marke des Werkzeugs in fremder Post, und eine
  profilabhängige Farbe kann nicht in den Dunkelregeln stehen, weil der Block eine zeichenweise
  verglichene Konstante ist. Ohne Logo ändert sich nichts — dann entsteht keine Tabelle, denn
  links stünde eine leere Spalte und ein Trenner ohne Gegenüber.

  Beim Bauen kam heraus, dass **jede Mail mit Logo schon vorher die eigene Prüfung verletzte**:
  Das Bild setzt `border: 0`, und `nicht_umschaltbar()` verlangte dafür eine umschaltbare
  Klasse. Gemerkt hat es niemand, weil kein Test und kein Golden je ein Logo führte. Die Prüfung
  sieht jetzt auf den Wert statt nur auf den Eigenschaftsnamen: Was die Eigenschaft abschaltet
  (`0`, `none`), setzt keine Farbe, die im Dunkeln hell bleiben könnte.

  Dazu zwei Einträge mehr in der Liste der umschaltpflichtigen Eigenschaften. `border-left:`
  ist neu und trägt die senkrechte Linie — ohne ihn hätte die Prüfung an genau der Stelle nie
  rot werden können, an der die Linie entsteht. Und `background-color:` steht jetzt eigens da,
  mit leerer Klassenliste: Er fiel bis hierher zufällig unter `color:`, weil der Name als
  Teilstring gesucht wurde; seit die Suche an der Deklaration ankert, wäre er still
  weggefallen. Umschalten kann ihn ohnehin keine Klasse, also ist jedes Vorkommen ein Befund.

- **Ein sechstes Mail-Beispiel, und es trägt ein Logo.** `examples/email/email-logo.md` mit
  eigenem Profil daneben — keines der ausgelieferten führt eines. Damit hält zum ersten Mal ein
  Golden fest, wie die Signatur mit Bild byteweise aussieht; der JS-Port des Signatur-Baukastens
  auf falzmarke.com prüft gegen genau diese Dateien und konnte den Zweig bisher nicht nachbauen.
  Dass das Beispielprofil eine reine Kopie mit genau einer geänderten Zeile ist, hält ein Test
  fest, damit es nicht still auseinanderdriftet. (#243)

- **Der Skill kennt die Signatur mit Logo jetzt auch in seiner Beschreibung.** `skill/SKILL.md`
  nannte weder die drei Formen von `email.logo` noch den Hinweis, den `email` dazu druckt — und
  eine Fähigkeit, die nur im Code steht, löst niemand aus: Ein Assistent wählt den Skill über
  Name und Beschreibung vor und liest den Rumpf erst danach. Der neue Abschnitt „Signatur und
  Logo" sagt außerdem, dass der Hinweis und die Warnung `email.logo_kontrast` weiterzugeben sind
  — sonst hält jemand ein Logo für zugestellt, das bei einem Teil der Empfänger ein leerer
  Kasten bleibt. (#243)

### Behoben

- **Kein `SyntaxWarning` mehr bei jedem Testlauf.** Ein Docstring in
  `tests/test_vollstaendigkeit.py` erklärte die Escape-Behandlung und schrieb dabei `\*` in
  einen gewöhnlichen String; Python warnt darüber und wird es in einer späteren Fassung als
  Fehler behandeln. Ein `r` vor den Anführungszeichen genügt.

  Der Grund, warum es zwei Wochen lang niemandem auffiel, ist der interessantere Teil: **Die
  Warnung erscheint nur beim Kompilieren.** Liegt die `.pyc` schon vor, bleibt sie stumm — wer
  die Suite zweimal fährt, sieht sie beim zweiten Mal nicht mehr. Deshalb bleibt es nicht beim
  Einzeiler: `tests/test_quelltext.py` übersetzt jede der 110 Python-Dateien selbst und meldet
  jede Warnung, unabhängig von jedem Cache. Ein Test, der sich auf pytest-Warnfilter verließe,
  hätte dieselbe Lücke gehabt. (#248)

## v0.9.4 — 07.09.2026

### Behoben

- **Fünf Stellen, an denen v0.9.3 die eigenen Regeln verletzte.** Ein Mehr-Augen-Review der
  Runde förderte sie zutage; jede ist am Code nachgemessen.

  Der Regelkatalog `regeln/email.yaml` behauptete weiter, den Zeitpunkt setze der Mailclient —
  dieselbe Aussage, die kurz zuvor an fünf anderen Stellen korrigiert worden war. Von dort
  wanderte sie über den Generator in die Referenz. `references/frontmatter.md` und `README.md`
  nannten „höchstens 32 Zeichen" für Werte im Informationsblock, während die Grenze auf 21
  steht: Wer sich danach richtete, lief in einen harten Abbruch. Und der Docstring von
  `eml.baue()` sagte „ohne Date", zwanzig Zeilen unter dem Modulkopf, der das Gegenteil erklärt.

  Zwei funktionale Befunde dazu. Der Hinweis auf eine gesetzte Blindkopie erreichte nur die
  Kommandozeile — der MCP-Dienst ruft `setze_email` direkt auf und gab nur „bestanden: true"
  zurück, also genau die Lage, die der Hinweis verhindern sollte, auf dem Hauptweg des Pakets.
  Er steht jetzt an einer einzigen Stelle (`eml.blindkopie_hinweis`) und wird von beiden Wegen
  benutzt. Außerdem meldete `verify --email` bei einem unlesbaren `Bcc` „steht nicht im
  sichtbaren Teil" — geprüft wurde dabei eine leere Adressmenge gegen den Text, also nichts.

  Damit die beiden Textbefunde nicht wiederkehren, hält `tests/test_textkanon.py` sie jetzt
  fest: eine Prüfung gegen die zurückgenommene `Date`-Behauptung über **alle** Textquellen
  einschließlich YAML — die Lücke, durch die der Regelkatalog gefallen war —, und eine, die die
  Zahl in der Doku gegen `INFOBLOCK_WERT_MAX` hält. Der Changelog-Verlauf bleibt ausgenommen:
  Dort steht die alte Aussage zu Recht, als Zitat dessen, was korrigiert wurde. (#253)

## v0.9.3 — 04.09.2026

### Neu

- **`falzmarke email --oeffnen` übergibt die fertige Nachricht dem Standardprogramm.** Bisher
  endete der Befehl damit, dass ein Pfad im Terminal stand; wer die `.eml` ansehen oder
  weiterleiten wollte, suchte sie im Dateimanager. Das Flag erspart diesen Weg — und sonst
  nichts: Es übergibt eine Datei an das Betriebssystem, sucht keine Anwendung aus und steuert
  kein Mailprogramm. Übergeben wird erst nach bestandener Prüfung, ohne Flag öffnet nichts, und
  ein Fehlschlag beim Öffnen lässt den Exit-Code bei 0 — die Nachricht ist ja geschrieben und
  gemessen. Dass sie im Mailprogramm als Lesefenster erscheint und nicht als Entwurf, bleibt
  wahr und steht in der Doku; der nächste Handgriff heißt weiterhin „Weiterleiten"
  ([ADR 0038](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0038-oeffnen-ist-kein-versand.md)). (#239)

- **`bcc:` im Frontmatter einer E-Mail.** Ein verbreitetes Muster in der Geschäftskorrespondenz
  ist eine Archivadresse im Blindverteiler, über die jede ausgehende Mail im
  Dokumentenmanagement landet. Bisher kannte der Datenvertrag nur `an:` und `cc:`, und die
  Adresse musste im Mailprogramm bei jeder einzelnen Nachricht von Hand nachgetragen werden —
  wird sie einmal vergessen, ist die Mail trotzdem raus und sieht in jeder Hinsicht erledigt
  aus, nur existiert kein Beleg.

  Die Adresse steht jetzt als `Bcc:` in der `.eml` und wird wie `an:` und `cc:` auf ihre Form
  geprüft. **In der `.html`-Vorschau erscheint sie nicht:** Die ist zum Ansehen und
  Herauskopieren da, und eine sichtbare Zeile „Blindkopie" ginge beim Kopieren mit — das Feld
  täte dann das Gegenteil dessen, wofür es da ist. `verify --email` misst eigens, dass keine
  ihrer Adressen im Text- oder HTML-Teil vorkommt.

  Ob ein Mailprogramm die Kopfzeile beim Weiterleiten übernimmt, entscheidet das Programm;
  falzmarke versendet nicht (ADR 0034) und kann es deshalb nicht zusagen. Der Befehl nennt die
  Adresse beim Erzeugen darum eigens — wer die Zeile liest, sieht im Programm nach, statt den
  Blindverteiler für erledigt zu halten.

  In einem Brief gibt es `bcc:` nicht. Anders als `cc:`, das dort `verteiler:` heißt, bekommt es
  keinen Ersatzvorschlag: Wer eine Kopie erhält, ohne im Verteiler zu stehen, ist auf Papier
  nicht vorgesehen. (#242)

### Geändert

- **Der Skill löst jetzt auch bei E-Mails aus.** Seine Beschreibung nannte ausschließlich
  Papier — Brief, Kündigung, Mahnung, „etwas zum Ausdrucken oder Verschicken" — und kein
  einziges E-Mail-Wort. Da ein Assistent den Skill allein über Name und Beschreibung
  vorauswählt, war die seit v0.8.0 fertige E-Mail-Fassung im Auslösepfad unsichtbar: Wer
  „schreib eine E-Mail an …" sagte, bekam eine frei getippte Nachricht statt einer geprüften
  `.eml`. Die Beschreibung nennt jetzt beide Ausgaben, führt die Auslöser für Mails mit und
  verbietet die selbstgebaute Nachricht so ausdrücklich, wie sie den frei gesetzten Brief
  schon verbot. (#238)

- **Der Name in der Signatur trägt jetzt Gewicht.** Er stand in derselben Größe da wie die
  Umsatzsteuer-Nummer drei Zeilen tiefer, und das Auge fand keinen Anker — beim Vergleich mit
  einem fremden Signaturgenerator fiel das als Erstes auf. Die erste Zeile des ersten Blocks
  ist jetzt 18px und halbfett. Bewusst ohne Akzentfarbe: Die Signatur gehört dem Absender,
  nicht dem Werkzeug, und eine profilabhängige Farbe kann nicht in den Dunkelregeln stehen —
  der Block ist eine Konstante, die zeichenweise verglichen wird. Größe und Gewicht tragen auf
  hellem wie auf dunklem Grund, ohne eine einzige Farbe zu setzen. (#243)

### Behoben

- **Jede Nachricht trägt jetzt ein `Date`.** Bisher fehlte die Kopfzeile — außer bei gesetztem
  `SOURCE_DATE_EPOCH` —, weil das Datum beim Versand entstehen sollte. Diese Begründung setzte
  voraus, dass das Mailprogramm die `.eml` als Entwurf übernimmt und den Zeitpunkt selbst
  einsetzt; nach der eigenen Messung in `docs/mailprogramme-2026-08-27.md` tut das keines der
  drei geprüften Programme. Der gangbare Weg ist „Weiterleiten", und dabei baut das Programm
  den zitierten Kopf aus den Feldern der Quelle: Das fehlende Feld erschien dort als
  `Datum: (null), (null)` und ging mit raus. RFC 5322, Abschnitt 3.6, führt `orig-date`
  ohnehin als Pflichtfeld. `SOURCE_DATE_EPOCH` behält den Vorrang und bleibt der Weg zum
  Golden-Vergleich; ohne die Variable steht der Zeitpunkt der Erzeugung in der Datei. Der
  eigentliche Befund war dabei der zweite: **`verify --email` meldete solche Dateien grün.**
  Die Prüfung misst jetzt beides — dass `Date` vorhanden und dass es nach RFC 5322 lesbar ist.
  (#236)

- **Profilangaben wirken nicht mehr still falsch.** Zwei Fälle aus einem echten Briefbau, beide
  daran erkennbar, dass das Werkzeug grün meldete und trotzdem etwas anderes tat als gemeint.

  `briefkopf.logo_hoehe_mm` ohne `briefkopf.logo` wirkt nie — die Höhe gehört zu einem Logo,
  das es nicht gibt. `lint` sagt das jetzt als Warnung; ein Fehler wäre es nicht, denn die Höhe
  kann für ein später ergänztes Logo schon dastehen. Der erste Treffer war das mitgelieferte
  `example.yaml` selbst, wo die Höhe aktiv neben einem auskommentierten `logo:` stand; beide
  sind jetzt auskommentiert.

  Der zweite Fall betrifft die Wertespalte des Informationsblocks. Ein zu langer Wert brach den
  Lauf mit einer Meldung ab, die nur das letzte Wort des überstehenden Textes nannte — nicht
  das Feld, aus dem es stammt. Kommt der Wert aus `infoblock_defaults:` des Profils, steht er
  nicht einmal in der Briefdatei, in der man ihn dann sucht. Die Meldung nennt jetzt Feld und
  Herkunft (`infoblock_defaults.ansprechpartner im Profil`), und rutscht ein Wert doch bis zum
  Prüfer am fertigen PDF durch, ordnet der den Überlauf der Wertespalte zu.

  Beim Nachmessen stellte sich heraus, dass die Grenze selbst zu hoch war: **21 Zeichen statt
  32.** Die alte Zahl kam aus „43 mm Spaltenbreite, 1,24 mm je Zeichen", und beides war zu groß
  — die Spalte beginnt bei 157 mm und der Satzspiegel endet bei 190, nutzbar sind also 33 mm,
  und ein Name braucht rund 1,55 mm je Zeichen statt 1,24. Schon „Dr. Anna Meyer-Schmidt" (22
  Zeichen) riss den Rand, ohne beanstandet zu werden. Beide Kopien der Konstanten sind dabei zu
  einer zusammengeführt; sie standen unabhängig in `cli.py` und `lint.py`, ohne dass ein Test
  sie zusammenhielt. (#244)

- **Die Warnung zu `datum:` in einer E-Mail erklärte das Gegenteil dessen, was geschieht.** Sie
  sagte „der Mailclient setzt es beim Versand" — seit der `Date`-Kopfzeile (#236) setzt
  falzmarke den Zeitpunkt selbst. Der Hinweis, dass das Feld in einer Mail nichts bewirkt,
  bleibt richtig; nur seine Begründung stimmte nicht mehr. Betroffen waren neben dem Nutzertext
  vier weitere Stellen mit derselben Aussage, darunter `references/frontmatter.md`, aus dem auch
  das Sprachmodell liest.

  Dabei kam ein Test heraus, der nie rot werden konnte: Er verglich die Kopfzeile mit der
  Zeichenkette `2026-08-29`, die ein RFC-5322-Datum (`Sat, 29 Aug 2026 …`) gar nicht enthalten
  kann. Er liest das Datum jetzt und hält es gegen den Tag des Briefes. (#249)

## v0.9.2 — 02.09.2026

### Infrastruktur

- **Ein Vorgang ohne Changelog-Eintrag lässt sich nicht mehr mergen.** Von 46 Vorgängen
  zwischen v0.8.2 und v0.9.0 hatte **einer** `CHANGELOG.md` angefasst; nach dem Nachtragen von
  39 Einträgen von Hand waren es bei den nächsten vier wieder null. Der Grund war strukturell:
  Es gab keinen Ort für einen Eintrag ohne Version. Den gibt es jetzt — je Vorgang eine Datei
  in `changelog.d/`, die beim Release zu einem Versionsabschnitt gebündelt wird
  (`scripts/changelog.py --buendeln`). Der Pflicht-Check „Changelog-Eintrag" verlangt sie;
  ausgenommen sind Abhängigkeits-Aktualisierungen, reine Doku, reine Tests und Vorgänge mit
  dem Label `ohne-changelog`. (#229)

- **Der Sammelpunkt für Abhängigkeits-Aktualisierungen entsteht von selbst.** Sie sind vom
  Changelog-Eintrag ausgenommen, und ADR 0037 versprach, sie erschienen beim Release „als
  Sammelpunkt" — den aber niemand schrieb: Er stand in keiner Anleitung, kein Werkzeug verlangte
  ihn. Damit war die Bauart wiederhergestellt, gegen die #229 gebaut wurde. Jetzt liest
  `scripts/changelog.py --buendeln` den git-Verlauf seit dem letzten Versions-Tag und erzeugt den
  Punkt selbst. Ist der Verlauf nicht lesbar, bricht es ab, statt stillschweigend nichts zu
  melden. (#233)

- **Abhängigkeiten aktualisiert.** action-gh-release von 2.6.2 auf 3.0.3 (#222)

## v0.9.1 — 01.09.2026

`verify` schlug bei zwei ganz gewöhnlichen Dingen fehl: einem Link und einer nummerierten Liste.
Beide Male fehlte inhaltlich nichts — die Prüfung verglich Darstellungsreste.

**v0.9.0 ist nicht auf PyPI erschienen.** Der Fehler unten (#213) war dreizehn Minuten vor dem
Tag gemeldet worden; die Veröffentlichung wurde deshalb angehalten. Auf PyPI folgt v0.9.0
zusammen mit dieser Fassung. Das GitHub-Release v0.9.0 mit den Skill-Paketen ist unverändert
gültig.

### Behoben

- **`verify --email` schlug bei jeder nummerierten Liste fehl.** Der HTML-Teil setzt die Liste
  als `<ol><li>`; die Ziffern erzeugt der Browser über CSS-Counter und stehen deshalb **nicht im
  Textstrom**. Der Textteil schreibt sie aus (`1. `, `2. `). Die Prüfung „Text und HTML sagen
  dasselbe" zählte sie als fehlende Wörter — einen je Listenpunkt. (#216)
- **`verify --mit-quelle` schlug bei jedem Markdown-Link fehl.** Verglichen wurde die rohe
  Quelle Token für Token gegen den gesetzten Text, und die Markdown-Schreibweise für Links
  überlebt das nicht:
  Gemeldet wurden Syntaxreste wie `Blitzsicht](https://…`, während inhaltlich nichts fehlte.
  Damit war Regel 0 — „kein Versand ohne grünen `verify --email`" — für jede Mail mit Link
  unerfüllbar. Das ist die schlechtere Sorte Fehlalarm: Sie trainiert darauf, ein rotes `verify`
  zu übergehen. (#213)

### Infrastruktur

- **Der Sollwert der Ruleset-Durchsetzung steht nur noch an einer Stelle.** Er stand zweimal:
  `DURCHSETZUNG` in `scripts/repo-einstellungen.sh` setzte ihn, `SOLL_ENFORCEMENT` in
  `scripts/repo_pruefung.py` prüfte dagegen — zwei unabhängige Konstanten, die nichts
  zusammenhielt. Der Wächter prüfte also gegen eine Kopie, die nichts setzt. Beide lesen jetzt
  aus `scripts/durchsetzung.py`. (#212)
- **Der Drift-Wächter schlägt keinen Fehlalarm mehr, wenn die Domain nicht antwortet.**
  Steht die Homepage dann auf der Release-Seite, ist das der dokumentierte Rückfall und keine
  Abweichung. Ein Wächter, der grundlos anschlägt, wird abgeschaltet. (#210)

## v0.9.0 — 01.09.2026

Aus einem Brief werden viele. Serienbriefe, Brief und Begleitmail in einem Zug, lange Schreiben
mit Überschriften und Zitaten — und ein Weg zurück aus einem bestehenden Brief ins Markdown.

### Neu

- **Serienbrief aus CSV oder JSON.** Eine Vorlage plus Datenquelle ergibt n Briefe:
  `falzmarke serie vorlage.md --daten empfaenger.csv --ziel briefe/`. (#3)
- **Brief und Begleitmail in einem Zug** — das PDF hängt an der eigenen Mail. Beides konnte das
  Werkzeug seit der E-Mail-Phase, bisher aber nur nacheinander. (#78)
- **Lange Schreiben: Überschriften, Listen, Zitate und wörtliche Auszüge.** Dialekt 1.1 führt
  ein Versionsfeld ein und schreibt nieder, was 1.0 und 1.1 jeweils zulassen; darauf bauen die
  neuen Elemente auf. Die Abnahme misst am fertigen PDF, ob ein langes Schreiben mit allem
  darin trägt — nicht nur jedes Element für sich. (#135, #136, #137, #138)
- **Einen bestehenden Brief einlesen.** Alle zwölf Befehle gingen bisher in eine Richtung:
  Markdown → PDF. Wer einen alten Brief neu setzen wollte, tippte ihn ab. Das Einlesen liefert
  ein Gerüst mit **benannten Lücken** statt geratener Inhalte — was es nicht weiß, behauptet es
  nicht. (#191)
- **PDF/A-3b: eine Datei im PDF statt dahinter.** Die Einbettung, die ADR 0033 als wählbare
  Stufe entschieden und in ein eigenes Issue verwiesen hatte. Sie ist die Vorbedingung für
  ZUGFeRD. (#114)
- **Die Signatur bekommt drei Blöcke — und ein Gesicht.** Person, Kontakt und Recht stehen
  getrennt statt in einem Block; dazu Logo, Farbe und ein dunkles Schema. Ob das Logo auf
  dunklem Grund trägt, wird seither gemessen, nicht angenommen. (#105, #142, #154)
- **Was in einer Geschäftsmail steht — und was nicht.** Ein Abschnitt in der Stilreferenz, wie
  es ihn für den Brief gibt: Betreff → Anrede → Grund des Schreibens → Information → gewünschte
  Handlung → Frist → Gruß → Signatur. (#106)
- **Links gibt es in E-Mails.** Im Brief bleiben sie ein Fehler — auf Papier gibt es keinen
  Link, in einer E-Mail gibt es ihn. Dazu ein Beispiel mit Links und sechs Prüfungen, die daran
  anschlugen. (#103, #107)
- **Ein Bildzeichen ohne Wortmarke**, für Browser-Tabs und überall dort, wo das volle Zeichen
  mit Schrift zu klein würde. (#82)
- **Vier Anlässe, die im Beispielbestand fehlten**, dazu eine Markenkarte im Hochformat. (#139,
  #146)

### Geändert

- **Form A steht nicht mehr auf der eigenen Layoutbasis.** Die Maße nannten als einzige Quelle
  `typst-letter-pro` — und die liegt unter `skill/falzmarke/typst/vendor/`. falzmarke setzte das
  Layout damit und belegte es mit sich selbst. Form A trägt jetzt einen externen Beleg. (#18)
- **Anhanggrenzen in Stufen statt einer Wand**, mit Fundstelle je Stufe statt einer einzigen
  Grenze ohne Begründung. (#183)
- **Adressen werden auf Form geprüft, nicht nur zerlegt.** `email.utils.parseaddr` aus der
  Standardbibliothek ließ vier von acht ungültigen Adressen durch. (#125)
- **Das 12-pt-Zeilenraster wird gemessen.** Der Briefsatz rechnet in einer Grundzeile von
  4,2333 mm, und jede „Leerzeile" der Norm ist genau eine Rasterzeile. Darauf beruhen alle
  Abstände zwischen Betreff, Anrede, Text und Gruß — geprüft wurde bisher alles außer dem
  Raster selbst. (#140)
- **Zitieren, ohne den Wortlaut anzufassen**, und ein Auszug, der über den Seitenwechsel läuft.
  (#137, #168)
- **Eine zweite freie Umsetzung als Quelle: dinbrief.** Die Quellenlage einer Regel wiegt
  schwerer, wenn sie nicht von einer einzigen fremden Umsetzung abhängt. (#134)
- **Was im PDF steht, ist jetzt auch als das ausgezeichnet, was es ist.** (#138)
- **Die Fundstellenprüfung wächst mit** dem Regelbestand, statt eine gepflegte Zahl zu führen.
  (#124)
- **PyPI-Freigabe: eine Wartezeit statt einer Freigabe von Hand** (ADR 0036). (#132)

### Behoben

- **Telefonnummern mit fünf- oder sechsstelliger Vorwahl wurden als abweichend gemeldet** — also
  die Vorwahlen kleinerer Orte und damit ein erheblicher Teil aller deutschen
  Festnetzanschlüsse. Gefunden beim ersten Einsatz an einem echten Absenderprofil. (#133)
- **Der HTML-Teil kam in Outlook nicht an, wie er gedacht war.** (#104)
- **Jede Frontmatter-Meldung nannte eine Zeile zu viel.** (#184)
- **Eine zu lange Auszugszeile wird gemeldet, bevor sie gesetzt wird** — vorher fiel sie erst
  im fertigen PDF auf. (#173)
- **Die Meldung nennt das Zeichen, das wirklich dasteht.** Eine einelementige Liste wurde als
  „einzelner Strich" gemeldet, auch wenn dort ein Stern stand. (#162)
- **Ein Befund nennt die Stelle in der Eingabe, nicht nur das Maß.** (#163)
- **`pillow` fehlte in `requirements.txt` und im Bootstrap** — es war nur transitiv vorhanden
  und hätte mit der nächsten Abhängigkeitsänderung still verschwinden können. (#194)
- **Auf PyPI zeigten alle sechs Links aufs Repository**, keiner auf die Website. (#178)
- **Der Kontrast des Grün-Textes war gegen die falsche Fläche gemessen.**
  `docs/marke/erscheinungsbild.md` nannte für `#2F8642` 4,56 : 1 und wies das als gemessen aus.
  Das stimmte — gegen Papier. Auf der Website steht grüner Text aber überwiegend auf `#F4F6F8`
  und `#EAF6EE`; dort fiel er auf 4,21 : 1 und 4,10 : 1 und verfehlte WCAG AA. Gefunden hat es
  axe-core auf falzmarke.com, nicht das Erscheinungsbild: 57 Verstöße auf zehn Seiten.

  Für Text auf hellem Grund gilt jetzt **`#2A783B`** — Papier 5,46 : 1, Karte 5,04 : 1, Marke
  4,92 : 1. Als Fläche bleibt `#3EB057` unverändert.

  Die eigentliche Ursache war nicht die Farbe, sondern die Messung: Die beiden hellen Flächen
  hatten **keinen Namen** und tauchten deshalb in keiner Tabelle auf. Sie stehen jetzt als
  eigene Zeilen im Erscheinungsbild, und das dort eingebettete Prüfskript rechnet gegen alle
  vier Flächen statt gegen zwei — mit einer Gegenprobe, die den abgelösten Wert weiterhin
  durchfallen lässt. Website-seitig behoben in `customer-falzmarke` #27. (#182)
- **Im Feed verlor der Film die Hälfte seiner Aussage**, und die Berichtszeile passte nicht mehr
  in die Aufnahme. (#164, #158)
- **Die Schaufensterbilder zeigten einen Wert, gemessen werden dreiunddreißig.** (#159)
- **Dass Tabellenzeilen nicht auf dem Raster stehen, steht jetzt in der Referenz.** Ob es so
  bleibt, ist offen (#151). (#177)

### Infrastruktur

Diese Punkte ändern nichts am erzeugten Brief. Sie stehen hier, weil vier davon dieselbe
Fehlerart betreffen: Eine Einstellung des Repositories wurde aus dem **Zustand des Aufrufs**
abgeleitet statt aus einem Wert im Repository — und fiel jedes Mal nur auf, weil ein Mensch
nachgemessen hat.

- **Kein Workflow schreibt mehr auf `main`.** (#188)
- **Die Pflicht-Checks des Rulesets kommen aus `ci.yml`, nicht aus dem letzten CI-Lauf.** Lief
  die CI beim Scharfstellen noch, fehlte ein Job in der Liste, ohne dass sich am Workflow etwas
  geändert hätte — das Ruleset verlor einen Pflicht-Check. (#196)
- **Das `main`-Ruleset bleibt scharf, wenn niemand etwas anderes verlangt.** `active` ist jetzt
  der Default; ein Herunterstufen braucht `FALZMARKE_RULESET_EVALUATE=1` und wird eigens
  gemeldet. Vorher hätte ein gewöhnlicher Lauf ohne Umgebungsvariablen den Schutz von `main`
  entwaffnet. (#201)
- **Die Homepage des Repositories hängt nicht mehr an einer ungesetzten Variablen.** (#199)
- **Ein Drift-Wächter meldet, wenn die gelebten Einstellungen von den Sollwerten abweichen** —
  `repo-einstellungen.sh --pruefen`, ohne zu schreiben. Er deckt Homepage, Ruleset-Durchsetzung
  und Pflicht-Check-Liste ab; Beschreibung, Topics und Labels folgen. (#206)
- **Die Lint-Regeln haben Gegenproben.** Bis dahin waren nur Geometrie und Emitter sabotiert:
  Eine Prüfung, deren Bedingung man versehentlich invertiert, wäre grün geblieben. (#197)
- **Ein externer Prüfkatalog wurde gegen den Bestand gemessen**, statt als Bauplan übernommen zu
  werden. (#193)
- **Die Textkanon-Beschreibung nennt die PDF-Prüfung zuerst**, nicht das, was es auf GitHub
  achtmal gibt. (#204)

## v0.8.2 — 28.08.2026

Das Skill-Paket ließ sich nicht mehr hochladen. Es gibt jetzt zwei.

### Behoben

- **`falzmarke.skill` war zu groß für claude.ai.** Mit dem `typst`-Wheel aus v0.8.1 wog die
  Datei 34,71 MB; der Upload-Dialog nimmt höchstens 30 MB und meldet wörtlich „Zip file must be
  less than 30MB". Der Fehler fiel erst beim Einspielen auf — das Bauen gelang. Damit war der in
  der README beschriebene Hauptweg seit v0.8.1 unbrauchbar.

  Das Release trägt jetzt **zwei Pakete**: `falzmarke.skill` (~0,8 MB, überall einspielbar, der
  erste Lauf lädt die Abhängigkeiten nach) und `falzmarke-offline.skill` (~34 MB, der
  Typst-Compiler reist mit, rendert ohne PyPI). Sie unterscheiden sich in genau einer Datei.

  Die Endung war nicht das Problem: Derselbe Dialog nennt `.zip` **und** `.skill` als zulässig.

### Geändert

- **Die 30 MB stehen als Sollwert im Packskript**, nicht als Fußnote. `scripts/skill_packen.sh`
  bricht ab, bevor ein Paket entsteht, das sich nicht einspielen lässt — und zwar vor dem
  34-MB-Download, nicht danach. Eine Prüfung hält fest, dass der Wert nur an dieser einen Stelle
  steht, und eine Gegenprobe, dass der Abbruch wirklich greift.
- Der Offline-Nachweis in der CI läuft gegen `falzmarke-offline.skill` — dort ist das Wheel.

## v0.8.1 — 28.08.2026

Das Skill-Paket rendert jetzt auch dort, wo es kein PyPI gibt.

### Behoben

- **Der Renderer kam in Sandboxen nie zustande.** Das Skill-Paket enthielt nur Quelltext;
  `scripts/bootstrap.py` holte die fünf Abhängigkeiten beim ersten Lauf per `pip` nach. Ohne
  Netzzugriff — und das ist der Normalfall in den Umgebungen, in denen ein Skill läuft —
  schlug das fehl. Gemessen: Entpacken, Befehlszeile, `profiles` und `check` liefen, nur
  `render` nicht, weil `typst` fehlte.

  Das Paket bringt das `typst`-Wheel jetzt mit (`cp38-abi3`, gilt für jedes Python ab 3.8), und
  `bootstrap.py` installiert **zuerst daraus** und erst danach von PyPI. Je Paket ein eigener
  Aufruf: `pip install --no-index` bricht sonst komplett ab, sobald für eines der genannten
  Pakete kein Wheel danebenliegt, und ein Vorrat mit nur `typst` hätte gar nichts ausgerichtet.
  Bleibt danach etwas offen, nennt die Meldung das fehlende Paket beim Namen, statt am Renderer
  zu scheitern. Das Paket wächst dadurch von 803 KB auf rund 34 MB. (#122)

### Geändert

- **Das Skill-Paket entsteht über ein Skript, das sich lokal ausführen lässt**
  (`scripts/skill_packen.sh`) — dieselbe Begründung wie bei der Paketprobe: Wer die Schritte im
  Workflow ausschreibt, hat zwei Fassungen, und die im Workflow lässt sich vor dem Tag nicht
  ausprobieren. Das Skript bricht ab, wenn kein Wheel im Paket landet; ein Paket mit leerem
  `vendor/` sähe von außen aus wie ein gelungener Lauf. (#122)
- **Das Wheel liegt nicht im Repository.** 32,6 MB je typst-Fassung, die jeder Klon mitzöge und
  die niemand je wieder aus der Historie bekäme — es wird beim Packen geladen. Ein Test hält
  fest, dass im Quellbaum keines liegt, und ein zweiter, dass `.gitignore` das abfängt. (#122)

## v0.8.0 — 27.08.2026

Der Brief bekommt eine zweite Ausgabeform: dieselbe Markdown-Datei wird zur E-Mail. Dazu kommen
Anlagen, eine englische Beschriftung, ein MCP-Dienst und eine GitHub-Aktion für fremde
Repositories.

### Neu

- **Dieselbe Datei als E-Mail.** Ein Schreiben mit `typ: email` im Frontmatter wird keine
  PDF-Seite, sondern eine `.eml` — dieselbe Quelle, dasselbe Profil, dieselbe Signatur.
  `falzmarke email nachricht.md --html` schreibt die Nachricht, dazu auf Wunsch eine
  HTML-Vorschau zum Kopieren und den Textteil, und misst das Ergebnis mit `verify --email` nach.
  Aufbau, Teile und Grenzen stehen in [`docs/email.md`](https://github.com/blitzsicht/falzmarke/blob/main/docs/email.md). (#59, #63, #65)
- **falzmarke versendet nichts.** Kein Versandbefehl, keine Option, die sendet, kein `smtplib`
  im Baum. Wer eine Datei erzeugt, haftet für ihren Inhalt; wer sie befördert, für Zustellung
  und Nachweis — das sind zwei Versprechen, und falzmarke gibt nur das erste
  ([ADR 0034](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0034-email-ist-ausgabe.md)). Die Abwesenheit ist testgesichert,
  nicht nur zugesagt. (#60)
- **`verify --email` misst die fertige Nachricht.** Es öffnet die `.eml`, parst sie und prüft —
  die Quelle wird nicht befragt. Ein Prüfer, der aus der Eingabe schließt, was herausgekommen
  sein müsste, bestätigt nur den eigenen Bauplan. Deshalb misst er auch Dateien, die von
  woanders kommen: MIME-Aufbau, Reihenfolge der Alternativen, `format=flowed` samt
  Space-Stuffing, Signaturtrennzeile, Gleichlaut von Text und HTML, und ob im HTML weder Skript
  noch externes Stylesheet noch Zählpixel steht. (#64)
- **Anlagen hängen hinten an den Brief.** `anlagen_dateien:` nimmt PDFs auf, Pfade relativ zur
  Briefdatei — ein Vorgang samt Anlagen bleibt ein Ordner, den man verschieben kann. Behauptet
  wird dabei keine Konformität, die die Anlage nicht hat: Mit veraPDF gemessen, welche Aussage
  nach dem Zusammenführen noch trägt. (#1)
- **Englische Beschriftung.** `sprache: en` im Brief oder im Profil setzt Leitwörter,
  Monatsnamen, „Anlagen", „Verteiler" und die Seitenzählung auf Englisch; der Brief schlägt das
  Profil, wie bei `form`. Von 32 Prüfwerten sind 31 in beiden Sprachen bitgleich — die eine
  Abweichung steht namentlich im Test, damit sie kein Freibrief wird. (#11)
- **falzmarke spricht MCP.** `falzmarke mcp` startet einen stdio-Dienst mit vier Werkzeugen:
  `brief_rendern`, `brief_pruefen`, `profile_auflisten` und `email_setzen`. Der Messbericht kommt
  bei jedem Rendern mit — ein Dienst, der ein PDF zurückgibt und offenlässt, ob die Maße stimmen,
  wäre ein PDF-Generator wie jeder andere. (#5, #65)
- **Eine Aktion für fremde Repositories.** Wer seine Briefe versioniert, lässt sie bei jedem Push
  setzen; die PDFs hängen als Artefakt am Lauf. Hält ein Brief die Maße nicht ein, wird der Lauf
  rot und nennt Datei und Maß — ein Serienbrief-Archiv merkt einen verrutschten Betreff damit
  beim Push und nicht beim Empfänger. (#6)
- **Die Falzmarke ist auf einem Bild zu sehen.** Das Werkzeug heißt so, und auf keinem
  Vorschaubild war eine zu erkennen: 0,25 pt sind bei 110 ppi 0,38 Pixel. `scripts/detailbild.py`
  rendert mit 600 ppi und schneidet 9 × 7 mm am Blattrand heraus; die Maßzahl daneben kommt aus
  `verify --json`, nicht aus dem Gedächtnis. (#13)

### Geändert

- **Der Markdown-Baum kennt keine Zielsprache mehr.** `markdown.py` gab fertigen Typst-Code
  zurück und rief den Emitter mitten in der Prüfung auf. Ein zweiter Emitter hätte damit die
  Prüfung verdoppeln müssen, und eine verdoppelte Prüfung ist eine, die auseinanderläuft. Jetzt
  baut `markdown.lies()` Knoten, und HTML-, Text- und Typst-Emitter gehen denselben Baum ab.
  Am Brief ändert sich dadurch nichts — nachgemessen, nicht angenommen. (#61)
- **Der Stil steht inline an jedem Element** der HTML-Fassung, nicht in einem `<style>`-Block:
  Gmail entfernt ihn, Outlook lädt nichts von außen, und was nicht ankommt, kann man nicht
  prüfen. (#61)

### Infrastruktur

- **Vier Mail-Beispiele mit Golden-Dateien.** `examples/email/` läuft in der CI mit; die `.eml`
  jedes Beispiels liegt byteweise in `tests/golden/email/` und fällt auf, wenn sich an der
  Ausgabe etwas ändert, das niemand angesagt hat. Erneuert mit `scripts/golden_email.py`. Dazu
  ein Wächter, der die `email`-Regeln aus der Regeldatei zieht und für jede einen Auslöser
  verlangt. (#66)
- **Pflichtangaben in E-Mails** stehen jetzt in [`docs/recht.md`](https://github.com/blitzsicht/falzmarke/blob/main/docs/recht.md) — seit dem EHUG
  (2007) dieselben wie im Brief, mit Fundstelle und mit dem Hinweis, dass falzmarke sie nicht
  prüft. (#66)
- [ADR 0033](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0033-pdfa-stufe.md): PDF/A-2b bleibt Vorgabe, A-3b wird
  wählbar und nur dort verwendet, wo tatsächlich eingebettet wird. Die Wahl fällt nicht zwischen
  den Formaten, sondern zwischen einer Zusage und einer zutreffenden. (#42)
- Die Aktion zählt Dateien statt Zeilen: `ls -1 | wc -l` zählt einen Dateinamen mit
  Zeilenumbruch doppelt und meldet eine Zahl, die es nicht gibt. (#58)

## v0.7.3 — 26.08.2026

### Behoben
- **Der Schritt „Prüfsummen ausgeben" hat den Upload verhindert.** Er schrieb die Summen mit
  `| tee dist/SHA256SUMS` in genau das Verzeichnis, das die Publish-Action vollständig
  hochlädt. Sie prüft vorher jede Datei darin und bricht an der ersten ab, die kein
  Distributions-Format ist — Lauf 32966455275:

  ```
  Checking dist/falzmarke-0.7.2-py3-none-any.whl: PASSED
  Checking dist/SHA256SUMS: ERROR InvalidDistribution: Unknown distribution format: 'SHA256SUMS'
  ```

  Das Paket selbst war in Ordnung. Die Summen stehen jetzt nur noch im Lauf-Protokoll; die
  Action gibt sie mit `print-hash: true` ohnehin ein zweites Mal aus.

### Hinzugefügt
- **Ein Wächter vor dem Upload.** Ein neuer Schritt bricht ab, wenn in `dist/` etwas liegt, das
  weder `.whl` noch `.tar.gz` ist. Das Entfernen des `tee` behebt diesen einen Fall; der
  Wächter behebt die Fehlerklasse. Er schlägt fehl, wo es nichts kostet — statt nach der
  Freigabe, im unumkehrbaren Job.

Lauf 32966455275 brach — wie die drei davor — **vor** dem Upload ab; auf PyPI war zu diesem
Zeitpunkt nichts gelandet.

### Angekommen
**v0.7.3 liegt auf [PyPI](https://pypi.org/project/falzmarke/)** — der fünfte Anlauf, Lauf
32972861001 am 26.08.2026. Gemessen, nicht vom grünen Job abgelesen:
`pypi.org/pypi/falzmarke/json` → HTTP 200, Version 0.7.3, Wheel und sdist. In einer frischen
Umgebung installiert (`pip install falzmarke`) und ein Brief gerendert: 33/33 Maße eingehalten.

Damit gelten die kurzen Befehle: `pipx install falzmarke`, `uvx falzmarke`. Die README nennt sie
jetzt, und `tests/test_installationswege.py` lässt sie zu (`AUF_PYPI = True`).

### Warum es diese Version gibt
Wie schon bei 0.7.1 und 0.7.2: Das Ruleset `release-tags` lässt Tags weder verschieben noch
löschen, und das Environment `pypi` erlaubt Deployments nur von Tags `v*`. Ein neuer Anlauf
braucht deshalb eine neue Versionsnummer — v0.7.2 ist verbraucht.

## v0.7.2 — 26.08.2026

### Behoben
- **Die Publish-Action konnte ihr eigenes Image nicht laden.** `pypa/gh-action-pypi-publish`
  laeuft als Docker-Container und zieht ihr Image mit dem `action_ref` als Tag. Beim
  SHA-Pinning ist das der Commit-SHA — und dafuer existiert im Registry kein Image, sie werden
  nur fuer Release-Tags gebaut (`manifest unknown`). Die Action ist damit die eine Stelle, an
  der die Hausregel „Actions auf Commit-SHAs pinnen" nicht anwendbar ist; sie steht jetzt als
  begruendete Ausnahme auf `v1.14.2`, der auf denselben Commit zeigt.

Auch dieser Lauf brach **vor** dem Upload ab. Auf PyPI ist weiterhin nichts gelandet.

## v0.7.1 — 26.08.2026

### Behoben
- **Der Publish-Job konnte nicht laufen.** Ihm fehlte `pytest`, obwohl er
  `tests/test_readme_auf_pypi.py` aufruft — der Lauf brach mit `No module named pytest` ab.
  Das geschah nach der Freigabe, aber **vor dem Upload**: Die Reihenfolge im Job prüft erst und
  lädt dann hoch, deshalb ist auf PyPI nichts gelandet und der Paketname blieb frei.

### Warum es diese Version gibt
v0.7.0 ist als Tag und GitHub-Release vorhanden, aber nie auf PyPI erschienen. Ein erneuter
Anlauf mit demselben Tag war nicht möglich: Das Environment `pypi` lässt Deployments nur von
Tags `v*` zu, ein `workflow_dispatch` von `main` wird abgewiesen — und ein Dispatch vom Tag
selbst hätte wieder die fehlerhafte Workflow-Datei geladen. Die Schutzregel zu lockern wäre der
falsche Weg gewesen; ein neuer Tag ist der richtige.

## v0.7.0 — 26.08.2026

### Neu
- **Die Konformität bestätigt ein fremdes Werkzeug.** Bisher schrieb falzmarke PDF/A und mass
  das Ergebnis selbst nach — Erzeuger und Prüfer waren dieselbe Codebasis. Das belegt
  Selbsttreue, nicht Konformität; in der Quellenlage trägt `eigene_messung` genau deshalb die
  Zählstufe `nie`. Jetzt läuft [veraPDF](https://verapdf.org/), die Referenzimplementierung der
  PDF Association, in CI bei jedem Push. Alle neun Beispielbriefe bestehen PDF/A-2b, die
  `--pdfua`-Fassung zusätzlich UA-1. Geprüft wird, was die Datei selbst deklariert — eine
  spätere Umstellung der Stufe trägt die Prüfung ohne Änderung mit. Fehlt veraPDF, endet der
  Lauf mit Exit 2 und `NICHT GEPRÜFT` statt mit 0. (#34)
- **Der Briefkörper wird auf jeder Seite gemessen.** Die Textprüfung lief auf `pages[0]`; ein
  mehrseitiger Brief konnte ab Seite 2 aus dem Satzspiegel laufen und trotzdem „Maße
  eingehalten" melden. Jetzt drei Messungen je Seite, und der Bericht nennt Seite **und**
  Element: `Seite 2, rechter Rand — 190.88 bei „1234567"`. (#35)
- **Die Quellenlage steht dort, wo kein README gelesen wird.** Paketbeschreibung,
  GitHub-Beschreibung und Skill-Beschreibung tragen den Vorbehalt jetzt selbst — testgesichert,
  mit Gegenprobe je Ort. Wer über einen Paketindex oder einen Prompt kommt, sieht kein README;
  ein Vorbehalt, der dort nicht ankommt, schützt den Herausgeber und nicht den Nutzer. (#40)

### Geändert
- **Die Paketbeschreibung wurde umgebaut, nicht ergänzt.** Sie belegte 107 Zeichen, GitHub
  schneidet bei 120 ab und die Paketsuche bei rund 100 — für einen Zusatz war kein Platz. Aus
  „auf den Millimeter geprüft" wurde „am fertigen PDF nachgemessen": dieselbe Leistung, keine
  Normaussage, und der Vorbehalt steht als eigener Satz dahinter. 90 Zeichen, also vor beiden
  Abschneidepunkten.
- **Das README ist als Projektseite lesbar.** Es wird als Langbeschreibung nach PyPI
  übernommen, wo relative Pfade nicht auflösen — 43 Verweise zeigten ins Leere, darunter der
  Banner in Zeile 3. Alle auf absolute URLs umgestellt, Bilder über `/raw/`, Dokumente über
  `/blob/`. `twine check` fängt das nicht: Es prüft, ob die Beschreibung rendert, nicht ob die
  Ziele existieren.
- **Die Maßzahl im README altert nicht mehr still.** Dort stand „30 Maße je PDF" — schon vorher
  ungenau. Jetzt „33 Maße je Seite", an einen echten Lauf gebunden: Wer eine Prüfung hinzufügt,
  sieht Rot statt einer stillen Abweichung.
- Trove-Classifier und vier zusätzliche Projekt-Adressen in `pyproject.toml`; ohne sie wäre das
  Paket auf PyPI praktisch unauffindbar. (#33)

### Infrastruktur
- Publish-Job für PyPI über OIDC (Trusted Publishing), ohne API-Token. Drei Bremsen: das
  Environment `pypi` mit Freigabe von Hand, eine Branch-Policy nur für Tags `v*`, und ein
  Abgleich von Tag und Paketversion vor dem Upload. (#7)
- ADR 0029 bis 0032; `docs/ROADMAP.md` wird wöchentlich aus Meilensteinen und Issues erzeugt.

## v0.6.0 — 25.08.2026

### Neu
- **Video aus Code.** Die README zeigt oben ein GIF der echten CLI, aufgezeichnet mit
  [vhs](https://github.com/charmbracelet/vhs) aus `docs/marke/video/readme.tape`. Dazu ein
  Erklärfilm von 60 Sekunden in 16:9 und 9:16
  (`docs/marke/video/erklaerfilm/`, Remotion). Nichts darin ist abgetippt: Die Szenentexte
  kommen aus dem Textkanon, die Messzeilen aus einem echten `verify --json`-Lauf, das Blatt
  ist der CI-Render von `examples/brief-mahnung.md`.
- **Der Textkanon ist eine Datei geworden.** `docs/marke/texte.yaml` ist ab jetzt die einzige
  Quelle für Claim, Untertitel und die Szenentexte; `docs/marke/texte.md` und die Szenendatei
  des Films werden daraus erzeugt (`python3 scripts/texte.py`). Vorher trug dasselbe Produkt
  drei Beschreibungen — im Banner, im Auftrag und in `pyproject` —, keine davon war die Quelle.
- **`docs/marke/erscheinungsbild.md`** schreibt Farben, Schriften und Verwendung fest, mit
  gemessenen Kontrastwerten und einem ausführbaren Rechenweg.
- **Mahnung als neuntes Beispiel** (`examples/brief-mahnung.md`).
- **`make`** als gemeinsamer Einstieg für Marke, Texte, GIF und Film.

### Behoben
- **Der Banner ließ sich nicht neu bauen.** Seine HTML-Quelle verwies auf `/tmp/sp/` und
  `/home/claude/fz/` — Pfade einer fremden Sandbox. Montserrat liegt jetzt als OFL-Schrift
  unter `docs/marke/fonts/`, und `bash scripts/marke.sh` erzeugt Banner und Vorschaubild
  reproduzierbar aus der HTML.
- **Marken-Grün war als Text nicht barrierefrei.** `#3EB057` erreicht auf Weiß nur 2,78 : 1
  und verfehlt WCAG AA — genau so stand der Zweitclaim im Banner. Für Text auf hellem Grund
  gilt jetzt `#2F8642` (4,56 : 1, gleicher Farbton). Als Fläche bleibt `#3EB057`.
- **`pyproject`-Beschreibung** entspricht dem Kanon statt einer vierten Formulierung.

### Hinweis zu Lizenzen
Der Erklärfilm wird mit [Remotion](https://www.remotion.dev) erzeugt, und das ist die erste
Komponente in diesem Repository, die **nicht** permissiv lizenziert ist. Sie ist am Programm
nicht beteiligt und wird nicht mitgeliefert. Die fertigen MP4-Dateien sind Ergebnis, nicht
Software, und stehen wie das übrige Repository unter MIT; wer den Film selbst neu rendert,
braucht ab vier Beschäftigten eine Company License. Deshalb wird lokal gerendert und das
Ergebnis eingecheckt, statt in CI zu bauen. Einzelheiten in `THIRD_PARTY_LICENSES.md`,
Abschnitt „Nur für die Videoerzeugung". Die Aussage „Alle Abhängigkeiten sind permissiv
lizenziert" heißt entsprechend jetzt „Alle Abhängigkeiten **des Programms**".
## v0.5.2 — 25.08.2026

### Geändert
- **Die CI-Aktionen hängen an vollständigen Commit-SHAs statt an Tags.** Ein Tag ist
  verschiebbar: `actions/checkout@v4` zeigt heute auf einen Commit und morgen womöglich auf
  einen anderen, ohne dass sich hier etwas ändert. Nur der SHA ist eine unveränderliche
  Referenz. Die Version steht als Kommentar dahinter, damit lesbar bleibt, was gepinnt ist.
  Alle sechs SHAs sind vor dem Festschreiben gegen ihr Repository geprüft worden — ein
  falscher SHA bricht jeden Lauf, und bei `release.yml` fiele das erst beim nächsten Release auf.
- **Voreinstellung `contents: read` je Workflow.** Die Jobs, die schreiben müssen, sagen das
  weiterhin selbst — jetzt sichtbar als Ausnahme statt als Normalfall.
- **Die README ist eine Produktseite statt einer Referenz.** Der erste Bildschirm beantwortet
  jetzt, was falzmarke ist, was es löst und woran man sieht, dass es stimmt — mit dem Satz, um
  den es geht: *Andere Werkzeuge erzeugen ein PDF. falzmarke prüft das Ergebnis.* Neu sind eine
  Beweisleiste aus belegten Angaben, ein Vergleich mit dem typischen Arbeitsablauf (nicht mit
  Produkten), Funktionen als Nutzen statt als Komponentenliste, und eine Beweissektion **vor**
  der Installation — an ihr entscheidet sich das Versprechen, also steht sie nicht am Ende.
- **Ein Abschnitt „Sicherheit"**, der ausschließlich nennt, was im Code steht und geprüft ist:
  `safe_load` durchgängig, Markdown-Positivliste, Brieftext als maskierte Zeichenkette statt
  Typst-Code, Ordnergrenze für Datei-Angaben samt Symlink-Auflösung, begrenztes
  Typst-Wurzelverzeichnis, abgeschaltete Systemschriften, keine Netzwerkbibliothek im
  Renderpfad. Ausdrücklich **nicht** „sicher", „gehärtet" oder „auditiert" — ein unabhängiges
  Audit gibt es nicht.
- **Referenzteile ausgelagert**: [`docs/cli.md`](docs/cli.md) (Befehle, Exit-Codes, was geprüft
  wird), [`docs/profiles.md`](docs/profiles.md) (Profil anlegen, Suchreihenfolge, eigener
  Briefkopf) und [`docs/architecture.md`](docs/architecture.md) (Schichten, Vendoring, warum das
  Paket unter `skill/` liegt). Die README behält je eine Kurzfassung und einen benannten Link,
  dazu eine Tabelle „Weiterlesen“.

### Neu
- **`.github/dependabot.yml`** für Versions-Updates von Actions und Python-Abhängigkeiten.
  Security-Updates liefen bereits über die Repository-Einstellung.
- **Das Release-Asset ist überprüfbar.** `falzmarke.skill` bekommt eine
  Herkunftsbestätigung (`actions/attest-build-provenance`) und eine SHA-256-Summe in der
  Release-Notiz sowie als eigene Datei. Der Prüfbefehl steht im README. Eine solche Bestätigung
  belegt **Herkunft und Bauweg, nicht Fehlerfreiheit** — genau so ist es dort formuliert.

### Behoben
- **Drei veraltete Zähler.** Die README nannte „alle sieben Beispiele" (es sind acht) und
  „28 Prüfungen" (es sind 30). Genau die Sorte Zahl, die bei jeder Änderung altert, ohne dass
  ein Test anschlägt — sie ist jetzt raus oder aus der Wirklichkeit abgeleitet.
- **Ein toter Verweis** in `docs/normmasse.md`: `skill/scripts/geometrie.py` gibt es nicht, die
  Datei liegt unter `skill/falzmarke/`. Gefunden beim Prüfen aller 66 internen Verweise.

## v0.5.1 — 25.08.2026

### Geändert
- **Die Belegregel wird jetzt nachgezählt, statt im Kommentar behauptet.** Die Regeldatei
  beschrieb seit v0.4.0, wann eine Regel `mehrfach_bestaetigt` heißen darf — gesetzt wurde die
  Stufe aber von Hand, und nichts prüfte sie. Am 25.08.2026 nachgemessen: **alle vierzehn** so
  geführten Regeln verfehlten die eigene Definition. Jede hatte zwei Sekundärquellen plus die
  vendorte Implementierung; verlangt waren drei Quellen beziehungsweise eine plus zwei
  Implementierungen. Diese vierzehn Regeln durften Läufe scheitern lassen.
- **`typst-letter-pro` zählt nicht mehr zur Bestätigung.** Die Layoutbasis ist eingebettet —
  falzmarke *setzt* damit das Layout. Ein Sollwert von dort wurde gegen ein PDF geprüft, das
  dieselbe Quelle erzeugt hat; die Prüfung konnte nicht rot werden. Als Beleg dafür, wie jemand
  anders die Norm gelesen hat, bleibt der Eintrag und trägt eine Regel weiterhin auf
  `einzeln_belegt` — auf `mehrfach_bestaetigt` hebt er sie nie. Jede Quelle trägt dafür eine
  Zählstufe (`voll`, `einzeln`, `nie`); fehlt sie, bricht die Regeldatei ab.
  **Für Briefe ändert sich nichts:** Die vierzehn Form-B-Regeln stehen auf zwei unabhängigen
  bemaßten Zeichnungen und bleiben Fehler. Form A stand schon vorher auf Warnung.
- **Der Normkanon nennt die Berichtigung.** Überall, wo „DIN 5008:2020-03“ den Bezugsrahmen
  benannte, steht jetzt „DIN 5008:2020-03 einschließlich Berichtigung 1:2020-07“. Wer nur die
  Ausgabe 2020-03 nennt, benennt die geltende Fassung unvollständig — und ein Abgleich, der die
  Berichtigung auslässt, wäre keiner ([#16](https://github.com/blitzsicht/falzmarke/issues/16)).

- **Zwei Aussagen im README zurückgenommen, die zu weit gingen.**
  „PDF/A-2b … archivfest für GoBD“ versprach eine Konformität, die ein Ausgabeformat nicht
  begründen kann: Die GoBD verlangen Aufbewahrung, Unveränderbarkeit, Nachvollziehbarkeit und
  eine Verfahrensdokumentation. Dort steht jetzt, was tatsächlich geprüft wird — das für die
  Langzeitarchivierung ausgelegte Profil und die nachgemessene Kennzeichnung.
  Und der Brief, den „die Post als nicht automationsfähig zurückgibt“, wird in Wahrheit
  zugestellt: Automationsfähigkeit betrifft Rabatt- und Massensendungen, nicht die Beförderung.
  Der echte Schaden trägt das Argument auch ohne Zuspitzung — die Anschrift steht nicht mehr im
  Fensterausschnitt, der Stapel muss neu gedruckt werden, der Automationsrabatt entfällt für
  diese Sendung. Dieselbe zu starke Aussage stand als „Archivfestigkeit“ auch in einem
  Test-Docstring, also dort, wo niemand eine Faktenbehauptung vermutet ([#17](https://github.com/blitzsicht/falzmarke/issues/17)).

## v0.5.0 — 25.08.2026

### Neu
- **`signatur:` gilt jetzt auch je Brief.** Bisher stand das Unterschriftsbild nur im Profil —
  ein Profil unterschrieb damit immer oder nie. Wer einen Brief „i. A.“ zeichnen ließ, bekam
  trotzdem die Unterschrift der Geschäftsführung ins PDF, und wer von Hand unterschreiben
  wollte, konnte das Faksimile nicht abschalten. Im Frontmatter schlägt `signatur:` jetzt das
  Profil, genau wie `unterzeichner:` schon vorher: `keine` lässt drei Leerzeilen Raum, eine
  Dateiangabe setzt ein anderes Bild.
- **Unbekannte Frontmatter-Felder brechen ab.** Bis v0.4.0 verwarf der Renderer jeden Schlüssel,
  den er nicht abfragte — stillschweigend. `signatur:` im Brief blieb damit wirkungslos, ohne
  ein Wort, und dasselbe galt für jeden Tippfehler. Der Linter kennt den Datenvertrag jetzt als
  Liste und nennt bei einem unbekannten Feld die Zeile und den nächstliegenden erlaubten Namen
  (`signature:` → `signatur`). Für den Informationsblock gilt dasselbe.
- **[`references/markdown.md`](skill/references/markdown.md)** — die Markdown-Teilmenge steht
  nicht mehr als Unterabschnitt im Datenvertrag, sondern als eigene Referenz, und sie beginnt
  mit dem, was möglich ist, statt mit dem, was verboten ist. Neu darin: was der Typografie-Pass
  von selbst erledigt. Zwei Tests fahren jede gelistete Zeile durch den Renderer — was dort als
  möglich steht, muss rendern; was als Fehler steht, muss abbrechen.

### Geändert
- **Die Ordnergrenze für Dateiangaben steht nur noch an einer Stelle** und wird von beiden
  Bezugspunkten benutzt: Profil-Assets (Logo, Unterschrift, eigener Briefkopf) bleiben im
  Profilordner, die Brief-Unterschrift bleibt beim Brief. Der Fund vom 25.08.2026 war nicht die
  fehlende Prüfung an sich, sondern dass dieselbe Fehlerklasse an einer von drei Stellen bedacht
  war — eine zweite Kopie hätte das wiederholt.
- **Die Grenzprüfung läuft jetzt vor der Existenzprüfung.** Andersherum verriet die Meldung, ob
  eine Datei außerhalb liegt: `../../../etc/shadow` antwortete mit „nicht gefunden“ oder „muss
  im Profilordner liegen" — je nachdem, und das ist ein Existenz-Orakel gegenüber einem Brief
  aus fremder Hand.
- **`INFOBLOCK_REIHENFOLGE` und `PFLICHTFELDER`** stehen jetzt in `lint.py` statt in `cli.py`;
  `cli` bezieht sie von dort. Zwei Listen für denselben Datenvertrag wären eine Kopie, die bei
  der nächsten Änderung still auseinanderläuft.
- **`CONTRIBUTING.md` und `SECURITY.md` sind wieder deutsch**, mit je einem kurzen englischen
  Absatz. Die Umstellung auf Englisch in v0.3.0 ist damit zurückgenommen — das Werkzeug, seine
  Meldungen und seine Dokumentation sind deutsch, und zwei Dateien in einer anderen Sprache
  waren ein Bruch ohne Gewinn. Die beim Übersetzen gefundenen vier veralteten Pfadangaben
  bleiben korrigiert.
- **`CONTRIBUTING.md`** nennt jetzt zusätzlich: Herkunftsbestätigung per DCO (`git commit -s`,
  kein CLA), einen Absatz zur KI-gestützten Entwicklung, die Beweispflicht am Pull Request und
  die Bedingungen für beigesteuerte Musterbriefe.
- **README-Kopf**: Banner aus der Markenwerkstatt statt selbstgebautem Logo-Arrangement.

## v0.4.0 — 25.08.2026

### Neu
- **Quellenlage je Regel.** Alle Maße und Schreibregeln stammen aus Sekundärquellen; der Abgleich
  mit dem Originaltext der DIN 5008:2020-03 steht aus ([#12](https://github.com/blitzsicht/falzmarke/issues/12)).
  Jede der 36 Regeln trägt jetzt ihre Herkunft — `mehrfach bestätigt`, `einzeln belegt`, `offen`
  oder `Werkzeugprüfung` — samt Quellen und Abrufdatum, gepflegt an einer Stelle in
  [`skill/falzmarke/regeln/din5008.yaml`](skill/falzmarke/regeln/din5008.yaml). Der Abschnitt
  „Quellenlage je Regel“ in der Normreferenz wird daraus erzeugt.
- **Warnstufe.** Nur eine mehrfach belegte Regel darf einen Lauf scheitern lassen. Aus einer
  einzigen Quelle wird eine Warnung, die ihre Quellenlage nennt; ohne Beleg wird nicht geprüft.
  Betroffen sind unter anderem die Grußformel ohne Komma und die Sechs-Zeilen-Grenze der
  Anschrift — beide bisher Fehler.
- **Der Typografie-Pass ändert nur, was er belegen kann.** Geschützte Leerzeichen zwischen Zahl
  und Einheit sowie die Zahlengliederung stehen nur in einer Quelle und werden nicht mehr still
  ersetzt. `typografie.vorschlaege()` sagt, was der Pass geändert hätte, ohne den Brief
  anzufassen.
- **Wortmarke.** Das Logo liegt als `docs/assets/brand/logo.svg` (hell) und `logo-dark.svg`
  (dunkler Grund) samt Illustrator-Quelle im Repository. Das Vorschaubild ist neu gesetzt.
- **`docs/recht.md`** — was das Werkzeug behauptet und was nicht. `tests/test_textkanon.py` hält
  den Satz zur ausstehenden Prüfung fest und meldet ungedeckte Konformitätsbehauptungen.
- **`CLAUDE.md`** — Arbeitsregeln, allen voran: Normtext wird nie geladen, gescannt oder zitiert.

### Bemerkenswert
Die Erhebung hat einen blinden Fleck sichtbar gemacht: **Form A ist deutlich schwächer belegt als
Form B.** Für Form B gibt es eine bemaßte Zeichnung, die alle Werte bestätigt; für Form A stützt
sich falzmarke auf eine einzige Implementierung. Beim Normabgleich zuerst dort nachsehen.

## v0.3.2 — 25.08.2026

### Behoben
- **Eine nicht eingebettete Schrift galt als eingebettet.** Schriften ohne `/FontDescriptor`
  wurden übersprungen — dabei ist der Deskriptor der einzige Ort, an dem eine `/FontFile` stehen
  kann. Genau so sehen die 14 PDF-Standardschriften aus: Ein fremdes PDF, das nur Helvetica
  benutzte, kam ohne Beanstandung durch, obwohl es beim Empfänger anders aussieht. Type-3-
  Schriften bleiben ausgenommen, ihre Glyphen stehen im PDF selbst.
- **Unlesbare Dateien endeten im Traceback.** `verify` prüft fremde PDFs, und was dabei
  hereinkommt, ist nicht immer eines: leere Datei, abgebrochener Download, umbenanntes
  Word-Dokument, PDF ohne Seiten — fünf von sechs Fällen zeigten einen Python-Stapelauszug statt
  einer Meldung. Jetzt: eine Zeile und Rückgabecode 1. Nebenbei schließt `pruefe()` das Dokument
  auch dann, wenn eine Prüfung dazwischen wirft.

Beide gefunden beim Angriff auf `verify`, Protokoll in
[`docs/angriff-2026-08-25.md`](docs/angriff-2026-08-25.md).

## v0.3.1 — 25.08.2026

### Behoben
- **Ein fremdes Profil las Bilder außerhalb seines Ordners.** `briefkopf_typ` prüfte, dass die
  angegebene Datei im Profilordner liegt — `logo` und `signatur` prüften es nicht. Weil ein Brief
  sein Profil im Frontmatter mitbringen darf, konnte ein zugeschickter Brief mit
  `logo: ../geheim/privat.png` jede Bilddatei einbetten, die der Empfänger lesen kann; der Lauf
  meldete dabei `30/30 Maße eingehalten`. Ein Symlink wirkte genauso. Die Prüfung sitzt jetzt an
  einer Stelle und wird von allen drei Feldern benutzt; ein Unterordner bleibt erlaubt.
  Gefunden beim Angriff auf v0.3.0, Protokoll in [`docs/angriff-2026-08-25.md`](docs/angriff-2026-08-25.md).

## v0.3.0 — 25.08.2026

### Geändert
- **normbrief heißt jetzt falzmarke.** Der Name musste vor dem Hybridbrief fallen, dessen
  Schema-URLs ab Veröffentlichung unveränderlich sind. Belegt vor dem Schnitt: TMview meldet
  weltweit keine eingetragene Marke „falzmarke“ (Kontrollprobe mit „falz“: 1.782 Treffer, die
  Suche misst also), und der Handelsregister-Bestand kennt kein Unternehmen dieses Namens.
- **Harter Schnitt, keine Aliase.** Mit umgezogen sind der CLI-Befehl, `FALZMARKE_PROFILES`,
  `~/.config/falzmarke/profiles/` und die PDF-Metadaten `/falzmarke_*`. Bestehende Profile
  wandern von Hand nach `~/.config/falzmarke/`. Bei null Fremdnutzern wäre eine
  Übergangsschicht toter Code gewesen.
- **`CONTRIBUTING.md` und `SECURITY.md` sind auf Englisch.** Das Werkzeug bleibt deutsch — DIN
  5008 ist eine deutsche Norm —, aber Fehler- und Sicherheitsmeldungen kommen von überall.

### Behoben
- **Bilder brachen `--pdfua`.** Sobald ein Profil ein Logo oder eine Unterschrift benutzte,
  brach der Satz mit `missing alt text` ab: PDF/UA-1 verlangt für jedes Bild eine Beschreibung.
  Logo und Signatur bekommen jetzt einen Alternativtext — der Absendername beziehungsweise
  „Unterschrift <Name>“, überschreibbar mit `logo_alt`. Aufgefallen ist es erst, als das
  Beispielprofil die Bilder tatsächlich benutzte.
- **Ein Installationsweg, den es nicht gab.** README und der v0.2.0-Eintrag unten versprachen
  `uvx normbrief` und `pipx install normbrief` — das Paket lag nie auf PyPI, beide Befehle
  schlugen fehl. Der Frischklon-Job der CI konnte das nie melden, weil er ein lokal gebautes
  Wheel testet. Die README nennt jetzt `uvx --from git+…`, nachgemessen, und
  `tests/test_installationswege.py` wacht darüber. Die PyPI-Veröffentlichung bleibt offen
  ([#7](https://github.com/blitzsicht/falzmarke/issues/7)).

### Neu
- **`example-grafik.yaml`** — ein zweites mitgeliefertes Profil mit Logo im Briefkopf und
  Unterschrift über dem Namen. `example.yaml` bleibt bewusst ohne Bilder: Dass eine einzelne
  YAML-Datei ohne Nachbardateien rendert, ist eine Eigenschaft, die Tests bewachen.
- **`scripts/demobilder.sh`** erzeugt die Bilder der README und das Vorschaubild aus den
  Renders. Sie lagen bisher als PNG im Repository, ohne dass irgendwo stand, wie sie entstanden
  sind — und veralteten deshalb still bei jeder Änderung am Beispielbrief.

## v0.2.0 — 25.08.2026

### Behoben
- **Stiller Textverlust.** `Az. 12//345` verlor den Rest der Zeile, weil `//` für Typst ein
  Zeilenkommentar ist — ohne Fehler, ohne Warnung. Der Regex-Konverter ist durch einen
  CommonMark-Parser mit Positivliste ersetzt; Text wird jetzt als Typst-Zeichenkette ausgegeben,
  wodurch es im Ergebnis keine Sonderzeichen mehr gibt.
- **Zweizeiliger Betreff wurde abgelehnt.** Die Messung nahm die erste statt der letzten
  Betreffzeile und hielt die zweite für die Anrede. Ein Angebot mit Vorgangsnummer und Gegenstand
  ist der Normalfall.
- **`datum: morgen`** stand wörtlich im Brief, **`datum: 2026-13-45`** endete in einem Traceback.
- **Systemschriften im PDF.** Ein Brief mit Emoji bettete die Apple-Schrift STSong ein — das
  Ergebnis hing am Rechner, auf dem gesetzt wurde.
- **Der `.typ`-Briefkopf** war seit v0.1.2 dokumentiert und nicht gebaut.
- **Der claude.ai-Weg endete nach dem ersten Chat**, weil Profile dort nicht überleben.

### Geändert
- **PyMuPDF (AGPL-3.0) ersetzt** durch pdfplumber (MIT) und pypdf (BSD-3). Alle Abhängigkeiten
  sind jetzt permissiv lizenziert; siehe [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Die
  Messung wurde dabei genauer: Abstände treffen jetzt auf 0,00 mm.
- Der Prüfbericht ist eine Zeile statt dreißig; `--verbose` zeigt alles.
- `check` heißt `verify` und braucht kein `--form` mehr — die Form steht in den Falzmarken.
- normbrief ist ein installierbares Paket: `pipx install normbrief`, `uvx normbrief`.

### Hinzugefügt
- `lint` prüft vor dem Render, ohne Typst.
- `pack --profil NAME` erzeugt ein Skill-Zip mit eingebackenen Absendern für claude.ai.
- `--pdfua` für barrierefreie PDFs (PDF/UA-1), Herkunftsvermerk im PDF, Fremd-PDF-Modus mit
  Millimeterangabe bei verschobenen Marken.

## v0.1.2 — 25.08.2026

### Geändert
- README neu aufgebaut: Wortmarke, Produktversprechen, getrennte Schnellstarts für Claude und
  Terminal, Bildergalerie. Alle Aufrufe zeigen jetzt den Pfad, unter dem der Befehl wirklich liegt.
- `docs/plan.md` ersetzt durch [`docs/normmasse.md`](docs/normmasse.md) — Herkunft der Maße,
  Gegenproben und Messmethodik statt interner Planung.
- Repo-Beschreibung auf den Nutzen statt die Implementierung.

### Hinzugefügt
- Wortmarke und Social Preview unter `docs/assets/brand/`.
- `CONTRIBUTING.md`, `SECURITY.md`, dieses Changelog, Issue- und PR-Vorlagen.
- Test, der die Version in `pyproject.toml` gegen den neuesten Git-Tag hält.

## v0.1.1 — 25.08.2026

### Behoben
- **Eigene Profile überleben jetzt ein Update.** Bis v0.1.0 lag der einzige vorgesehene Ort
  innerhalb der Installation (`skill/typst/profiles.local/`). Wer den Skill ersetzte — Zip neu
  hochladen, Verzeichnis austauschen —, verlor alle Absender und konnte keinen früheren Brief mehr
  setzen. Der Suchpfad kennt jetzt `./profiles/` und `~/.config/normbrief/profiles/`.

### Hinzugefügt
- `normbrief.py init-profil NAME` legt eine ausgefüllte Vorlage am updatefesten Ort an.

## v0.1.0 — 25.08.2026

Erste Fassung.

- Markdown mit YAML-Frontmatter wird zu einem Brief nach DIN 5008:2020, Form A und B, als PDF/A-2b.
- Anschriftfeld mit allen vier Zonen, Informationsblock bei 125 mm, Falz- und Lochmarken,
  12-pt-Raster, Mehrseitigkeit mit Kopfzeile und Seitenzählung.
- Geometrieprüfung des fertigen PDFs nach jedem Lauf; Abweichung ergibt Exit-Code 2.
- Absenderprofile als YAML, optionaler Typst-Hook für eigene Briefköpfe.
- Claude-Skill, eigenständige CLI, PNG-Vorschau.
- Testsuite mit Gegenproben gegen absichtlich verschobene Layouts.
