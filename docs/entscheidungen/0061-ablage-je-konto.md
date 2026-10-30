# 0061 — Die Ablage je Konto: `In-Reply-To` sagt, was erledigt ist

**Datum:** 28.10.2026 · **Status:** angenommen · **Umsetzung:** [#431](https://github.com/blitzsicht/falzmarke/issues/431) ·
**Ergänzt:** [0051](0051-gesendet-sperre-und-postfach-entwurf.md),
[0055](0055-entwurfsbuch-status-und-sperre.md) · **Hält:** [0054](0054-entwurfsbruecke-in-thunderbird.md), Punkt 2

## Anlass

Nach dem Beantworten bleibt die eingegangene Nachricht im Eingang liegen. Von Hand wandert sie je
Konto anders weg — gemessen am 28.10.2026 liegt bei einem Konto ein Ordner `INBOX/#GELESEN`, beim
anderen `# Gelesene Nachrichten` —, und damit beantwortet der Eingang die Frage „ist das
erledigt?" nicht: Er trägt Bearbeitetes und Unbearbeitetes nebeneinander.

Der Vorgang #431 nannte als Auslöser das Tagebuch der Entwurfsbrücke: Es schreibe bei einer
Antwort, welche Nachricht beantwortet wurde. **Das ist nachgemessen falsch.** `ursprung.uid` wird
nur bei `details.type === "draft"` gefüllt und ist dann die UID des *Entwurfs*
(`thunderbird/entwurfsbruecke/background.js`); bei `typ: "reply"` bleibt sie `null`. Im Tagebuch
des Betreibers stehen 345 Zeilen, 90 davon `gesendet` — 86 `draft`, 3 `reply`, 1 `new` —, und alle
drei Antworten nennen keine Quelle. ADR 0056 sagt zum Ursprung einer Antwort nichts.

## Entscheidung

1. **Erledigt heißt: eine gesendete Antwort nennt die Nachricht in `In-Reply-To`.** Der
   Gesendet-Ordner wird im Fenster `--seit` gelesen (Vorgabe 30 Tage), und je `In-Reply-To` wird
   im Eingang gesucht. `postfach.KOPFZEILEN` holt die Kopfzeile längst, `Kopf.antwort_auf` trägt
   sie — es entsteht kein neuer Datenweg.

   Am Konto gemessen, nur lesend (Stand 28.10.2026): 14 gesendete Antworten in 30 Tagen, 5 davon
   mit ihrer Quelle noch im Eingang. `UID SEARCH HEADER "Message-ID"` fand genau diese 5; ein Kopfvergleich von
   Hand fand dieselben 5 und dieselben UIDs, und eine erfundene Message-ID fand nichts. Gesucht
   wird deshalb über den Server, nicht über alle Köpfe des Eingangs: Sonst würde die Kappung bei
   `postfach.GRENZE` gerade die lange liegende Nachricht verlieren, um die es geht.

   **Die Nebenwirkung ist gewollt:** Auch eine von Hand in Thunderbird geschriebene Antwort räumt
   auf. Der Zweck ist Ordnung im Eingang, nicht Buchführung über falzmarke.

2. **Das Add-on bleibt unberührt.** Es um die Quelle einer Antwort zu erweitern wäre der teurere
   Weg (neue Felder, neue Fassung, neue `.xpi`) und hätte erst künftige Daten; verschieben dürfte
   es ohnehin nicht — ADR 0054 Punkt 2 und `tests/test_entwurfsbruecke.py` halten am Quelltext
   fest, dass darin kein Aufruf zum Senden, Löschen, Verschieben oder Flaggen steht. Keine
   Berechtigung `messagesMove`.

3. **Der ändernde Befehl steht in einem eigenen Modul**, `skill/falzmarke/ablage.py`, und es ist
   genau einer: `UID MOVE` (RFC 6851). `postfach.py` bleibt, was es zusagt — nur lesend, mit
   `APPEND` als einziger Ausnahme —, und diese Zusage ist dreifach verankert (Modulkopf,
   `tests/test_postfach.py`, `tests/imap_attrappe.py`). Dort einen zweiten schreibenden Befehl
   unterzubringen hätte alle drei entwertet.

   **Kein Nachbau aus `COPY`, `STORE \Deleted` und `EXPUNGE`.** Ein Verschieben in drei Schritten
   kann in der Mitte abbrechen und die Nachricht zweimal oder nirgends liegen lassen. Nennt
   `CAPABILITY` kein `MOVE`, wird nichts verschoben und der Grund gesagt. Am Konto des Betreibers
   gemessen: `MOVE` und `UIDPLUS` sind da.

   `tests/test_ablage.py` liest das am Syntaxbaum nach, und zwar an den **Textliteralen**, nicht
   an den Argumenten von `uid(...)`: `postfach.Postfach._befehl` nimmt die Methode und reicht die
   Argumente weiter, also steht `"MOVE"` gar nicht im Aufruf von `uid`. Eine Prüfung über Aufrufe
   wäre hier eine, die nie rot werden kann — das ist gemessen, nicht vermutet: Genau so fiel der
   Positivteil beim ersten Lauf. Docstrings sind ausgenommen, sonst meldete die Prüfung
   ausgerechnet den Modulkopf, der das Verbot erklärt.

4. **Das Ziel wird nie geraten und nie angelegt.** Es kommt aus `email.ablage` im Profil. Fehlt
   die Zeile, gilt der Sonderordner `\Archive` — und der trägt hier nicht: An beiden Konten des
   Betreibers kennzeichnet ihn keiner, obwohl ein Ordner „Archiv" dort liegt (`\Sent`, `\Drafts`,
   `\Junk` und `\Trash` kamen im selben Lauf zurück). Dann wandert nichts, und das wird gesagt.
   Eine Fallback-Liste aus Ordnernamen („Archiv", „Erledigt", „Archive") wurde **verworfen**: Ein
   falsch getroffener Ordner ist nur von Hand zurückzuholen.

   Als Ziel ausgeschlossen sind der Gesendet-Ordner — er ist Datenquelle der Sendesperre und von
   `status` (ADR 0051), eine eingegangene Mail dort erzeugt Fehltreffer —, dazu die Entwürfe, der
   Papierkorb, der Spam-Ordner und der Eingang selbst. Geprüft wird am **Kennzeichen** des
   Servers, nicht an einem Namen: „Gesendete Elemente", „Sent Items" und „Éléments envoyés" sind
   dasselbe, und eine Namensliste kennt immer eine Sprache zu wenig.

5. **Erst zeigen, dann tun.** Ohne `--machen` wird nur gelesen. Dass der Trockenlauf hält, prüft
   ein Test, der gegen eine Attrappe läuft, die jedes Verschieben verbietet — er wird von selbst
   rot, sobald der Trockenlauf fällt, ohne dass irgendwo sabotiert werden muss.

   Am Gerät nachgefahren (29.10.2026, `servus@blitzsicht.com`, Zählstand jeweils **vor** der
   Handlung genommen): Der Lauf ohne `--machen` ließ INBOX bei 25 und „Gesendete Elemente“ bei 205.
   Mit `--machen` fiel INBOX von 27 auf 22 — die beiden zusätzlichen Nachrichten kamen über Nacht —,
   Gesendet blieb bei 205. Der zweite Lauf über dieselbe Lage meldete 0 Züge und bewegte nichts.

   Der Zählstand der Ablage belegt das **nicht**: `INBOX/#GELESEN` zeigt 500, die Kappung bei
   `postfach.GRENZE`. Ein Löschen hätte dieselbe Zahl erzeugt. Belegt wurde die Ankunft deshalb
   über die Message-ID: Alle fünf lagen anschließend in der Ablage (neue UIDs 1338–1342) und keine
   mehr im Eingang; eine erfundene Message-ID fand in beiden Ordnern nichts — die Suche kann also
   leer werden.

6. **Kein Protokoll der Züge.** Der Vorgang verlangte „jeder Zug kommt ins Tagebuch". Das wird
   nicht umgesetzt: falzmarke schreibt nie in das Tagebuch der Brücke (ADR 0054/0056), und eine
   neue Zustandsdatei braucht es nicht. Die Idempotenz kommt aus dem Postfach selbst — ein
   zweiter Lauf findet die Nachricht nicht mehr im Eingang und meldet das. Nachweis über `--json`.

## Warum nicht anders

**Warum nicht `\Seen` statt eines Ordners?** „Gelesene Elemente" ist kein Ordner, sondern das
Merkmal `\Seen`. Soll „Ordnung" nur heißen „schon gesehen", ist dafür nichts zu bauen.

**Warum nicht nur Antworten über die Brücke?** Die Schnittmenge aus Gesendet-Ordner und Tagebuch
wäre enger und überraschungsärmer — aber sie umfasst drei Zeilen aus Monaten, und der Befehl
räumte fast nichts auf. Eine Abnahme, die sich daran nicht messen lässt, ist keine.

**Was offen bleibt:** Sperre und `status` prüfen den Absender der im Gesendet-Ordner gefundenen
Nachricht nicht. Das ist ein eigener Mangel, unabhängig von dieser Entscheidung, und steht in
[#434](https://github.com/blitzsicht/falzmarke/issues/434). Diese Entscheidung legt nichts in
„Gesendete Elemente" ab und verschärft ihn nicht.

## Nachtrag (29.10.2026, #438)

Das Review der Umsetzung hat drei Festlegungen nachgeschärft. Keine widerspricht dem Beschluss
oben; sie schließen Lücken, die beim Schreiben nicht gesehen wurden.

**Die Zuordnung läuft über die einzelnen Kennungen, nicht über den Feldwert.** `In-Reply-To`
trägt nach RFC 5322 eine Liste, und ein langer Wert liegt gefaltet in der Nachricht — der rohe
Feldwert ist also kein Suchbegriff. `postfach.kennungen` zerlegt ihn, und gesucht wird je
Kennung. Eine Antwort gilt erst als erledigt, wenn **keine** ihrer Kennungen im Eingang liegt.

**Ein Umbruch in einem IMAP-Argument wird abgelehnt, nicht entschärft.** In IMAP trennt `\r\n`
zwei Befehle. Der rohe Feldwert einer fremden Nachricht erreichte die Befehlszeile, und `imaplib`
fängt das erst ab Python 3.14 ab: Auf 3.12.9 und 3.13.12 gingen zwei Zeilen auf die Leitung
(gemessen mit abgefangenem `send`), und die CI fährt 3.12. `postfach._zitiert` lehnt jetzt selbst
ab — die engste Stelle, sie liegt vor jedem `SEARCH`, `SELECT` und `FETCH`. Für die Proben folgt
daraus, dass die Attrappe die Ablehnung ebenfalls selbst mitbringen muss; eine Probe, die sich
auf `imaplib` stützt, wäre lokal rot und auf der CI stumm.

**Eine mehrdeutige `email.ablage` ist ein Grund, kein Rückfall.** Nennen zwei Profile derselben
Absenderadresse verschiedene Ordner, gab `cli.ablage_aus_profil` ein blankes `None` zurück — für
`ablageordner` nicht von „kein Profil nennt das Feld" zu unterscheiden. Der Lauf nahm dann
`\Archive` und verschob die Post mit `--machen` dorthin, während die Ausgabe sagte, es sei keines
genommen worden; unter `--json` stand davon nichts. Jetzt steht der Satz als `grund` im Bericht,
es wird kein Postfach geöffnet, und beide Darstellungen tragen ihn.

Dazu zwei kleinere Festlegungen: Der Ablageordner wird je Lauf **einmal** bestimmt und über den
Bericht an den Zug gegeben (zwei Bestimmungen können verschieden ausfallen), und ein Fehler beim
Zug lässt den gefundenen Plan stehen, statt ihn durch Nullen zu ersetzen — „0 von 0" wäre die
stärkste Form von „nichts geschehen" für den einen Fall, in dem etwas geschehen sein kann.
