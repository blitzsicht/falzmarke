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
   Mail zu viel im Eingang, keine zu wenig. Als erledigt zählt nur ein eindeutiges Ja (`ja`, `yes`,
   `true`); jeder andere Wert setzt das Fähnchen, und `lint` warnt.
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
