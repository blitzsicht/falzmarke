# 0063 — Ein Antwortentwurf setzt das Fähnchen an der Ursprungsmail

**Datum:** 06.11.2026 · **Status:** angenommen · **Umsetzung:** [#549](https://github.com/blitzsicht/falzmarke/issues/549) ·
**Ergänzt:** [0061](0061-ablage-je-konto.md) (Nachtrag #478) ·
**Hält:** [0038](0038-oeffnen-ist-kein-versand.md) (falzmarke sendet nie)

## Anlass

`aufraeumen` legt eine Mail ab, sobald es im Gesendet-Ordner eine Antwort mit passendem
`In-Reply-To` gibt (ADR 0061). Ob die Antwort die Sache erledigt oder nur vertröstet („melde mich
Freitag“), kann der Lauf nicht unterscheiden. Bisher schützte nur ein Fähnchen, das man von Hand
setzt (#478). Seit `--alle` täglich im Zeitplan läuft (#541), reicht ein einziges vergessenes
Fähnchen, und eine offene Mail verschwindet aus dem Eingang.

Beim Entwurf ist die Unterscheidung bekannt. Wer mit falzmarke antwortet, weiß, ob die Antwort
abschließt, und der Entwurf kennt die Ursprungsmail über `antwort_auf`.

## Entscheidung

1. **falzmarke setzt das Fähnchen, nicht die Thunderbird-Erweiterung.** Es geschieht per IMAP im
   selben Lauf wie `email --oeffnen`, nachdem der Entwurf angelegt ist oder schon lag. Das lässt
   sich mit der IMAP-Attrappe prüfen, braucht keine neue XPI-Fassung und kein Recht
   `messagesUpdate`.
2. **Im Zweifel bleibt die Mail im Eingang.** Jeder Antwortentwurf setzt `\Flagged` an der
   Ursprungsmail, **außer** das Frontmatter sagt `erledigt: ja`. Ein vergessenes Feld lässt eine
   Mail zu viel im Eingang, keine zu wenig. Als erledigt zählt nur ein eindeutiges Ja: der Text `ja` oder
   ein YAML-Wahrwert (`true`, `yes`, `on` ohne Anführungszeichen). `"yes"` in Anführungszeichen,
   `1` oder jeder andere Wert setzt das Fähnchen, und `lint` warnt.
3. **Nur dieses eine Flag, nur hinzufügen, an genau einer Mail.** Der ändernde Befehl ist
   `UID STORE <uid> +FLAGS (\Flagged)`. Kein `-FLAGS`, kein `\Seen`, kein `\Deleted`, kein
   Verschieben. Ein Fähnchen, das schon steht, wird nicht noch einmal gesetzt. Entfernt wird es
   nie, auch nicht später: Ob die Sache inzwischen erledigt ist, weiß nur der Mensch.
4. **Genau eine Mail oder keine.** Gesucht wird im Eingang des Absenderkontos, mit exaktem
   Vergleich der `Message-ID`. Liegt die Mail dort nicht (abgelegt, an ein anderes Konto
   gegangen) oder tragen mehrere Mails dieselbe Kennung, wird nichts geändert und der Grund
   genannt. Zwischen Suche und Setzen wird die UIDVALIDITY verglichen wie vor jedem `UID MOVE`
   (#495).
5. **Nachgelesen, nicht geglaubt.** Nach dem `STORE` werden die Flags der Mail noch einmal
   gelesen. `OK` heißt „angenommen“; erst das Nachlesen sagt „gesetzt“.
6. **Nie ein Abbruch.** Der Entwurf steht schon. Jeder Fehler wird zu
   `HINWEIS  Fähnchen nicht gesetzt: <Grund>`, der Exit-Code bleibt, was er ohne das Fähnchen wäre.
7. **Ein eigenes Modul.** `falzmarke.faehnchen` steht neben `ablage` und `entwurfsablage`, nicht in
   `postfach`: Dessen Zusage „nur lesend, der einzige schreibende Befehl ist `APPEND`“ bleibt wahr.
   `tests/test_faehnchen.py` liest am Syntaxbaum nach, dass `STORE` dort der einzige ändernde
   Befehl ist.

## Nachtrag: Nachreview #553 (06.11.2026)

- **Das Fähnchen kommt mit dem Entwurf, nicht mit dem Senden.** Im Zweig mit dem
  Verfassen-Fenster (Thunderbird, Outlook) ist der Entwurf beim Setzen nur ein offenes Fenster.
  Wer ihn verwirft, oder wer einen Entwurf mit `--ersetzen` austauscht, behält das Fähnchen an der
  Ursprungsmail. Das ist die Richtung aus Punkt 2: eine Mail zu viel im Eingang.
- **`erledigt: ja` sieht nicht nach.** Hat ein früherer Entwurf derselben Antwort ohne `erledigt`
  das Fähnchen schon gesetzt, bleibt es (Punkt 3: entfernt wird nie). Die Zeile sagt das.
- **Nennt der Server keine Flags, wird gesetzt.** Ob schon eines steht, ist dann unbekannt;
  `+FLAGS` an einem stehenden ändert nichts. Die Zeile meldet „nicht nachgelesen“.
- **Gegen einen echten Server ist der Weg nicht gemessen** (Stand 06.11.2026), nur gegen die
  IMAP-Attrappe. Der erste Lauf gegen den emailproxy wird hier mit Datum nachgetragen.

## Nachtrag: Code-Review #553 (06.11.2026)

- **Auch bei ungewissem Entwurf und beim Rückfall auf die Datei.** Ist nach einem abgerissenen
  `APPEND` ungewiss, ob der Entwurf liegt, oder geht statt eines Entwurfs die `.eml` auf, wird das
  Fähnchen ebenfalls gesetzt. Beide können mit `In-Reply-To` gesendet werden; ohne Fähnchen legte
  `aufraeumen` die Ursprungsmail dann ab. Das ist Punkt 2: im Zweifel eine Mail zu viel im Eingang.
  Kein Fähnchen gibt es weiter, wo kein Entwurf entsteht: Gesendet-Sperre und `--kein-fenster`
  ohne Entwurf (Exit 3; der nächste Aufruf setzt es).
- **`erledigt: ja` verspricht das Ablegen nur für eine Antwort mit `In-Reply-To`.** Ein Entwurf aus
  dem Verfassen-Fenster trägt den Bezug nicht; die Ursprungsmail bleibt dann ohnehin liegen.
- **Verworfen:** das Fähnchen im Fenster-Zweig weglassen. Ob Thunderbird den Bezug über `-compose`
  annimmt, ist nicht gemessen (gemessen ist nur Outlook für Mac, 11.09.2026); ein überflüssiges
  Fähnchen ist sichtbar und mit einem Klick weg. Ebenso verworfen: das Fähnchen in der Sitzung des
  Entwurfs setzen statt in einer eigenen. Das spart eine Anmeldung, bindet aber den ändernden
  Befehl an `oeffnen`, und Punkt 7 hält ihn in einem eigenen Modul.

## Warum dieses Flag und warum ein voller Eingang

Das ist der erste Schreibzugriff auf eine **fremde** Mail im Eingang. `ablage` verschiebt nur, was
eine gesendete Antwort als erledigt ausweist; `entwurfsablage` räumt nur eigene Entwürfe. Hier
ändert falzmarke den Zustand einer Mail, die jemand anderes geschrieben hat. Deshalb so eng:

- `\Flagged` ist das einzige Flag, das `aufraeumen` liest (#478), und in jedem Mailprogramm
  sichtbar und mit einem Klick zu entfernen. Ein eigenes Schlüsselwort (`$Wartet`) zeigten die
  Programme nicht an, und `aufraeumen` müsste es zusätzlich kennen.
- Nur hinzufügen: Ein Fehler hinterlässt höchstens eine markierte Mail, nie eine verlorene
  Markierung, die der Mensch gesetzt hatte.
- Ein voller Eingang ist sichtbar und reparabel. Eine Mail, die in `Archiv/<Jahr>` verschwunden
  ist, obwohl sie noch auf etwas wartete, fällt niemandem auf.

## Nicht Teil davon

- Antworten, die direkt in Thunderbird geschrieben werden. Dort bleibt das Fähnchen Handarbeit.
- Das Fähnchen später automatisch wieder entfernen.
- Ein `--json` für `email`. Der Befehl hat keines; die vier Zustände trennen die Textzeilen
  (`OK  Fähnchen gesetzt`, `OK  Fähnchen stand schon`, `HINWEIS  erledigt: ja`,
  `HINWEIS  Fähnchen nicht gesetzt`). Entscheidung des Betreibers, 06.11.2026.
