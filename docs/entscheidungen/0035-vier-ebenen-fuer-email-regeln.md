# 0035 — Vier Ebenen für E-Mail-Regeln

**Datum:** 28.08.2026 · **Status:** angenommen · **Löst:** [#101](https://github.com/blitzsicht/falzmarke/issues/101)

## Entscheidung

Jede E-Mail-Regel trägt eine **Ebene**, und die Meldung nennt sie.

| Ebene | Woher die Regel stammt | Darf höchstens sein |
|---|---|---|
| **Norm** | DIN 5008, Abschnitte 22 und 25 | Fehler |
| **Recht** | § 37a HGB, § 125 HGB, § 35a GmbHG, § 80 AktG, § 25a GenG, § 7 UWG | Warnung |
| **Technik** | RFC 5322, 2045, 3676, 2047, 2231, 7763 | Fehler |
| **Praxis** | Darstellungsverhalten verbreiteter Mailprogramme | Warnung |

Acht Festlegungen folgen daraus.

### 1. Praxis ist nie ein Fehler

Ein Fehler ist die Zusage, dass etwas **nachweislich** verletzt wurde. Erfahrung mit einem
Programm trägt das nicht: Sie sagt, wie eine Fassung eines Mailprogramms an einem Tag auf einem
Rechner dargestellt hat. Das ist wertvoll — als Hinweis, nicht als Befund.

Es ist dieselbe Begründung, mit der `einzeln_belegt` seit v0.4.0 auf Warnung herabgestuft wird,
angewandt auf eine andere Achse. Dort geht es um die Zahl der Quellen, hier um ihre Art.

**Recht ist ebenfalls höchstens eine Warnung**, aus einem eigenen Grund: falzmarke prüft keine
Rechtsfragen (ADR 0005). Es kann sehen, ob ein Feld gesetzt ist; es kann nicht sehen, ob der
Inhalt für eine Rechtsform genügt. Eine Meldung, die als Fehler auftritt, würde genau das
behaupten. Deshalb bleibt es bei der Erinnerung, die `werkzeug.email_pflichtangaben` heute schon
ist.

### 2. Ebene und Herkunft sind zwei Achsen, nicht eine

`ebene:` sagt, **wovon** eine Regel redet. `herkunft:` sagt, **wie gut sie belegt** ist. Beide
sind Pflichtfelder, und beide begrenzen unabhängig voneinander, was der Linter tun darf. Es gilt
die **schärfere** der beiden Grenzen.

```yaml
- id: email.betreff_laenge
  ebene: technik
  herkunft: mehrfach_bestaetigt
  quellen: [rfc5322, rfc2047]
  wirkung: warnung        # Stufe, siehe Festlegung 6

- id: email.html_umschlagtabelle
  ebene: praxis
  herkunft: werkzeug
  quellen: []
  wirkung: warnung        # Ebene deckelt: nie Fehler
```

Damit hört die heutige Lage auf, in der **alle** E-Mail-Regeln `herkunft: werkzeug` und
`quellen: []` tragen. Die RFCs und die Handelsrechts-Paragraphen werden echte Einträge unter
`quellen:` mit `zaehlt: voll` — sie sind öffentlich, benannt und nachprüfbar, und damit besser
belegt als jede Sekundärquelle zur Norm. Eine Technik-Regel nennt künftig ihren Beleg, statt zu
behaupten, sie habe keinen.

Warum nicht eine einzige Skala: Die Herkunftsskala misst Belegstärke **innerhalb einer
Quellenwelt**. Bei E-Mail sind es vier, und eine RFC-Regel ist nicht „schwächer belegt" als eine
Normregel — sie redet über etwas anderes. Wer beides in eine Reihenfolge zwingt, muss eine
Rangfolge zwischen DIN und RFC behaupten, die niemand aufstellen kann.

### 3. Eigene Regeldatei, gemeinsames Quellen-Register

Die E-Mail-Regeln ziehen nach `skill/falzmarke/regeln/email.yaml`. Die Norm-Datei soll nichts
über RFCs behaupten, und `din5008.yaml` trägt den Namen der Norm im Dateinamen. Die Regel-IDs
heißen dabei `email.*` statt `werkzeug.email_*`; das heutige Präfix war eine Aussage über die
Herkunft und wird von der Ebene abgelöst.

Das Quellen-Register wird dabei **geteilt, nicht verdoppelt**: `quellen:` zieht aus
`din5008.yaml` nach `skill/falzmarke/regeln/quellen.yaml`, und beide Regeldateien verweisen
darauf. Der Grund ist die Ebene Norm — sie zitiert für Abschnitt 22 dieselben Sekundärquellen wie
die Briefregeln. Zwei Definitionen derselben Quelle können auseinanderlaufen, und dann steht die
Herkunft an zwei Stellen statt an einer. Genau das soll die Quellenlage verhindern.

### 4. Links sind in E-Mails erlaubt

In `typ: email` sind `https`, `http`, `mailto` und `tel` zugelassen. `javascript:`, `data:`,
`file:` und `vbscript:` bleiben Fehler — sie sind kein Verweis, sondern eine Anweisung an das
Programm des Empfängers.

**Im Brief ändert sich nichts.** Die heutige Begründung von `werkzeug.url_im_text` — „Auf Papier
gibt es nichts zum Anklicken" — ist richtig und gilt genau dort. Sie auf die E-Mail zu übertragen
war ein Fehler der Herkunft, nicht der Absicht: Eine Regel wurde mitgenommen, ihre Begründung
blieb beim Brief zurück.

### 5. Umschlagtabelle statt `div`

Der HTML-Teil wird in eine Tabelle gefasst, nicht in ein `div` mit `max-width`. Kein Flex, kein
Grid, keine Webfonts. Grund: Das klassische Outlook rendert mit der Word-Engine, und die kennt
`max-width` nicht — der Teil läuft dort über die volle Fensterbreite.

Diese Regel trägt die Ebene **Praxis** und ist damit eine Warnung, nie ein Fehler. Das ist die
erste Nagelprobe auf Festlegung 1, und sie wird bewusst nicht umgangen: Die Begründung ist eine
Beobachtung an einem Programm. Sie ist gut genug, um die Vorgabe zu bestimmen, und nicht gut
genug, um ein fremdes Dokument durchfallen zu lassen.

### 6. Grenzen sind Stufen, keine Wände

Betreff und Anhänge bekommen Schwellen statt einer einzigen Grenze, und jede Schwelle sagt, was
an ihr tatsächlich passiert.

Heute ist beides eine Wand mit einer Begründung, die nicht trägt. Ein Betreff über 78 Zeichen ist
kein Verstoß gegen RFC 5322 — die Vorschrift betrifft die **Zeilenlänge** einer Kopfzeile, und
längere Betreffs werden gefaltet, nicht abgelehnt. Was oberhalb wirklich passiert, ist eine
Anzeigefrage: Übersichten schneiden ab. Das ist Ebene Praxis, also eine Warnung. Bei Anhängen
ebenso: 10 MB sind keine Vorschrift, sondern eine verbreitete Annahmegrenze, und sie ist nicht
überall dieselbe.

Die Zahlen legt dieser Eintrag nicht fest — er legt die **Form** fest: Schwelle, Ebene, und eine
Begründung, die zutrifft.

### 7. Bilder nur eingebettet

Bilder kommen als eingebettete Ressource (`cid:`) und nur für das Logo des Profils, mit
Alt-Text. `data:`-URIs werden zum **Fehler**; heute sind sie erlaubt.

Der Grund ist nicht Ästhetik. Ein `data:`-Bild ist für den Empfänger nicht von einem
nachgeladenen zu unterscheiden, es umgeht die Zählpixel-Prüfung, und mehrere Mailprogramme
blockieren es ohnehin. Die Regel aus [ADR 0034](0034-email-ist-ausgabe.md) — „Bilder nur als
eingebettete Ressource mit Alt-Text" — war so gemeint; die Umsetzung hat `data:` durchgelassen.

### 8. Keine Werbemails

Newsletter, Abmelde-Kopfzeilen, Einwilligungslisten, Empfängerlisten: Dafür ist dieses Werkzeug
nicht gebaut, und es wird nicht dafür erweitert. Der Grund ist § 7 UWG und gehört benannt —
Werbung per E-Mail setzt eine Einwilligung voraus, deren Nachweis der Versender führen muss.

falzmarke kann diesen Nachweis nicht führen: Es kennt den Empfänger nicht, versendet nicht und
protokolliert nichts. Ein Werkzeug, das Serienmails erzeugt, aber die Einwilligung nicht kennt,
verleitet zu einem Vorgang, dessen Risiko allein beim Nutzer landet. Das ist derselbe Schnitt wie
in ADR 0034, eine Stufe früher gesetzt.

**Absender-Authentifizierung ist Sache des Versenders.** SPF, DKIM, DMARC und TLS gehören nicht
in ein Werkzeug, das nichts versendet. Der Nutzer soll aber erfahren, dass seine Domain sie
braucht — als Hinweis in der Dokumentation, nicht als Prüfung, die falzmarke gar nicht ausführen
könnte.

## Warum

Die E-Mail-Fassung erzeugt seit v0.8.0 gültige Nachrichten und misst sie nach. Woran sie sich
dabei hält, stand bisher nicht auseinander: Sechzehn Regeln, alle mit derselben Herkunftsangabe,
alle ohne Quelle. Die RFC-Regel, die handelsrechtliche Erinnerung und die Outlook-Erfahrung
wirkten gleich stark und sahen in der Meldung gleich aus.

Für den Brief gibt es diese Trennung längst. Sie entstand aus einem Befund: Am 25.08.2026
verfehlten **alle vierzehn** als mehrfach bestätigt geführten Regeln die eigene Definition, und
niemandem war es aufgefallen, weil nichts nachzählte. Die E-Mail-Regeln sind heute an derselben
Stelle — nur früher, bevor jemand sie zitiert hat.

Eine Meldung, die „DIN" sagt, wo Outlook-Praxis gemeint ist, sieht genauso aus wie eine, die ihr
Versprechen einlöst. Der Unterschied ist für den Empfänger der Meldung unsichtbar, und genau
deshalb muss ihn das Werkzeug aussprechen.

## Was daraus folgt

- **[#102](https://github.com/blitzsicht/falzmarke/issues/102)** setzt die Festlegungen 1 bis 3
  um: `email.yaml` und `quellen.yaml`, das Feld `ebene:`, die Umbenennung der Regel-IDs, die
  Ebene in der Meldung — und die drei Begründungen aus den Festlegungen 4, 6 und 7, die heute
  nicht zutreffen.
- **[#103](https://github.com/blitzsicht/falzmarke/issues/103)** baut Festlegung 4.
- **[#104](https://github.com/blitzsicht/falzmarke/issues/104)** baut Festlegung 5 und ist die
  Probe darauf, dass eine Praxis-Regel wirklich nur warnt.
- **[#105](https://github.com/blitzsicht/falzmarke/issues/105)** und
  **[#106](https://github.com/blitzsicht/falzmarke/issues/106)** setzen darauf auf; #106 nimmt
  § 7 UWG und die Absender-Authentifizierung in die Dokumentation.
- **[#107](https://github.com/blitzsicht/falzmarke/issues/107)** liefert die Gegenproben. Ohne
  sie ist keine der Festlegungen belegt: Eine Prüfung, die nie rot werden kann, ist kein Nachweis.
- **[#108](https://github.com/blitzsicht/falzmarke/issues/108)** prüft Festlegung 5 am
  klassischen Outlook nach — die Begründung stammt von dort und gehört dort belegt.
- **[#109](https://github.com/blitzsicht/falzmarke/issues/109)** wartet auf den erweiterten
  Dialekt und ändert an diesem Eintrag nichts.
- **Zwei Seiten widersprechen ab jetzt.** `docs/email.md` führt Betreff und Anhänge unter
  „Grenzen" als Wände und erlaubt `data:`-Bilder; `docs/recht.md` kennt weder § 7 UWG noch die
  Absender-Authentifizierung. Beides wird von #102 und #106 nachgezogen. Der Widerspruch steht
  hier, damit er nicht still bleibt.

## Was diese Entscheidung nicht ist

Sie sagt **nicht**, was aus den Abschnitten 22 und 25 der DIN 5008 tatsächlich gilt. Das ist
nicht erhoben. Die Ebene Norm ist damit vorerst eine Ebene ohne Insassen — sie steht bereit,
nicht in Gebrauch. ADR 0034 hat den Satz dafür schon geprägt: Die Abschnittsnummer ist eine
Adresse, kein Nachweis. Was von dort als Regel gilt, kommt mit dem Normabgleich
([#12](https://github.com/blitzsicht/falzmarke/issues/12)) und mit Quelle daneben.

Sie ist keine Rechtsberatung. Die Ebene Recht sagt, woher eine Regel stammt, nicht ob der Nutzer
seine Pflichten erfüllt.

Und sie ändert nichts am Versand: Es entsteht kein Versandbefehl. Das steht in ADR 0034 und wird
hier nicht neu verhandelt.
