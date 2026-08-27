# Wie ein Brief formuliert wird

Diese Datei vor dem Schreiben lesen. Sie regelt, was in den Text kommt — nicht, wo er steht.

## Grundhaltung

Ein Geschäftsbrief hat ein Anliegen und nennt es. Wer den Brief liest, soll nach dem ersten
Absatz wissen, worum es geht, und nach dem letzten, was zu tun ist.

- **Ein Anliegen pro Absatz.** Vier bis sechs Zeilen, dann Absatz.
- **Kein Vorgeplänkel.** Der erste Satz sagt die Sache. „Hiermit teilen wir Ihnen mit, dass"
  ist keine Sache.
- **Handlung und Frist in den letzten Absatz.** Was soll wann geschehen.
- **Keine Floskeln.** Nicht „Wir würden uns freuen", nicht „Selbstverständlich stehen wir Ihnen
  jederzeit gerne zur Verfügung", nicht „Im Voraus vielen Dank".
- **Keine Ausrufezeichen, keine Emojis, keine Fettung zur Betonung** im Fließtext. Fett ist für
  Zahlen und Fristen, die man wiederfinden muss.
- **Sie, Ihnen, Ihr** groß. **Wir** nur, wenn wirklich mehrere handeln — sonst ich.
- Aktiv statt passiv: „Wir liefern am 1. September" statt „Die Lieferung erfolgt".

## Betreff

Nominalstil, konkret, ohne das Wort „Betreff", ohne Schlusspunkt, höchstens 60 Zeichen.
Er enthält das, wonach der Empfänger später sucht: Vorgangsnummer, Vertrag, Datum.

| Gut | Schlecht |
|---|---|
| `Kündigung des Wartungsvertrags Nr. 2024-0042` | `Kündigung` |
| `Widerspruch gegen den Bescheid vom 11. August 2026` | `Ihr Schreiben` |
| `Angebot Nr. 2026-0815 über die Neugestaltung Ihrer Website` | `Unser Angebot für Sie!` |

## Anrede

- Mit Namen: `Sehr geehrte Frau Muster,` · `Sehr geehrter Herr Dr. Muster,`
- Ohne Ansprechpartner: `Sehr geehrte Damen und Herren,`
- Akademischer Grad gehört dazu, Berufsbezeichnungen nicht.
- Die Anrede endet mit Komma, der erste Absatz beginnt deshalb klein.

## Aufbau nach Brieftyp

**Angebot** — Bezug auf die Anfrage mit Datum · Leistung in wenigen Punkten · Preis und was darin
enthalten ist · Gültigkeitsdauer · was der Empfänger tun soll.

**Mahnung, erste Stufe** — sachlich, kein Vorwurf: Rechnungsnummer, Betrag, Fälligkeitsdatum ·
Hinweis, dass sich die Zahlung überschnitten haben kann · neue Frist mit Datum.
**Zweite Stufe** — Verweis auf die erste Mahnung mit Datum · neue Frist · Ankündigung der
nächsten Schritte, ohne Drohgebärde. **Dritte Stufe** — letzte Frist, konkrete Folge, Datum.

**Kündigung** — Vertrag mit Nummer und Datum · Kündigung zum konkreten Termin · Rechtsgrundlage
oder Frist · Bitte um schriftliche Bestätigung. Kein Grund nötig; wenn einer genannt wird, dann
sachlich.

**Widerspruch** — Bescheid mit Datum und Aktenzeichen · „lege ich fristgerecht Widerspruch ein" ·
Begründung mit Belegen · Antrag, was geschehen soll.

**Mieterschreiben** — Objekt und Wohnung eindeutig benennen · Sachverhalt mit Datum · Frist zur
Abhilfe · Erreichbarkeit für Rückfragen.

**Behördenschreiben** — Aktenzeichen zuerst · Sachverhalt in zeitlicher Reihenfolge · Antrag klar
formuliert · Anlagen auflisten.

**Bestätigung** — was wann vereinbart wurde · was daraus folgt · bis wann Widerspruch möglich ist.

## Schreibweisen

Die Regeln zu Datum, Telefonnummern, Beträgen und Anschriften stehen in `din5008.md`. Sie gelten
auch im Fließtext: `am 1. September 2026`, `unter 0941 620-9800`, `1.234,56 EUR`.

Fristen immer mit Datum, nie nur mit Dauer: „bis zum 15. September 2026", nicht „innerhalb von
14 Tagen" — der Empfänger soll nicht rechnen müssen.

## Was eine E-Mail vom Brief unterscheidet

Der Ton bleibt derselbe — sachlich, ohne Floskeln, in der Sprache des Empfängers. Anders ist die
Form, und zwar aus einem Grund: Ein Brief wird gelesen, weil jemand ihn aufgemacht hat. Eine Mail
steht in einer Liste mit dreißig anderen.

**Ein Anliegen je Nachricht.** Wer zwei Dinge will, schreibt zwei Mails. Der Brief kann mehrere
Punkte tragen, weil er als Ganzes gelesen wird; eine Mail wird überflogen, und der zweite Punkt
geht verloren.

**Kürzer.** Was im Brief drei Absätze braucht, hat in einer Mail zwei. Höflichkeitsschleifen —
„ich hoffe, es geht Ihnen gut", „vielen Dank für Ihre Zeit" — entfallen ersatzlos.

**Der Betreff nennt das Thema, nicht die Gattung.** „Angebot Nr. 2026-0815" statt „Angebot",
„Termin am 3. September verschieben" statt „Terminanfrage". Er steht in einer Liste neben
dreißig anderen und muss dort erkennbar sein. Über 60 Zeichen sieht ihn niemand ganz.

**Am Ende steht eine konkrete Bitte**, mit Datum: „Bitte bestätigen Sie den Termin bis zum
1. September 2026." Nicht „Ich freue mich auf Ihre Rückmeldung" — daraus folgt nichts.

**Anlagen werden im Text genannt.** Der Empfänger soll wissen, dass etwas dabei ist, bevor er es
sucht. `lint` erinnert daran, fügt aber keinen Satz ein: Ein Werkzeug, das ungefragt in einen
Text schreibt, schreibt irgendwann den falschen.

**Zitate nur bei einer Antwort.** Trägt das Frontmatter `antwort_auf:`, wird der beantwortete
Punkt kurz aufgegriffen — in eigenen Worten, nicht als eingerückter Block. Ohne `antwort_auf:`
gibt es nichts zu zitieren.

**Keine Gestaltung.** Keine Farben, keine Schriftgrößen, keine Buttons, keine Logos außer dem des
Profils. Was in Outlook, Gmail und Apple Mail gleich ankommen soll, ist schmal
([ADR 0034](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/0034-email-ist-ausgabe.md)).
