# 0062 — Überholte Entwürfe gehen von selbst in den Papierkorb

**Datum:** 02.11.2026 · **Status:** angenommen · **Umsetzung:** [#425](https://github.com/blitzsicht/falzmarke/issues/425) ·
**Ergänzt:** [0051](0051-gesendet-sperre-und-postfach-entwurf.md),
[0055](0055-entwurfsbuch-status-und-sperre.md), [0061](0061-ablage-je-konto.md) ·
**Berichtigt:** [0054](0054-entwurfsbruecke-in-thunderbird.md) ·
**Hält:** [0038](0038-oeffnen-ist-kein-versand.md) (falzmarke sendet nie)

## Anlass

Am 02.11.2026 räumte der Betreiber zwei Entwürfe mit einem Einmalskript weg:

1. **Fall 1:** Ein Entwurf wurde über die Entwurfsbrücke geöffnet und gesendet und blieb trotzdem
   im Ordner liegen, ohne `\Deleted`. `status` zeigte `SCHON RAUS`. ADR 0054 und `SKILL.md` sagten
   pauschal, Thunderbird räume ihn weg.
2. **Fall 2:** Die alte Textfassung lag als `WARTET`, die neue Fassung war längst hinaus. Das ist
   der Fall aus #425.

Beim Durchsehen trat ein dritter Weg zu Tage: Der Trockenlauf fand an zwei weiteren Konten drei
Entwürfe, die vier Tage und zwei Tage lang als überholt lagen, genau wie Fall 2.

## Warum Thunderbird den Entwurf im Fall 1 liegen ließ

**Belegt ist der Mechanismus, nicht der Auslöser.**

Von 118 `gesendet`-Zeilen im Tagebuch trägt genau eine keine `message_id`, und das ist genau dieser
Entwurf (Add-on 0.3.7, `sendNow`). Die Mail selbst liegt regulär im Gesendet-Ordner. Das Add-on
liest `sendInfo.headerMessageId`, und im Quelltext von Thunderbird hängen beide Symptome am selben
Punkt: `nsMsgComposeSendListener::OnStopSending` ruft bei Erfolg zuerst
`RemoveCurrentDraftMessage` und reicht danach an `msgCompose->OnStopSending` weiter, die einzige
Stelle, die `headerMessageId` setzt. Beides steht hinter `if (msgCompose)`. `onAfterSend` dagegen
feuert über den Fortschrittsstatus, also auch ohne dieses `OnStopSending`, und
`MessageSend.notifyListenerOnStopSending` schluckt Ausnahmen. Bleibt der Aufruf aus, ist die Mail
draußen, das Add-on meldet Erfolg, und es fehlen sowohl die Kennung als auch das Wegräumen.

Daraus folgt: Das Wegräumen geschieht auf dem Sendeweg, ist nicht gesichert und meldet nichts
zurück.

**Nicht gefunden** ist, warum der Aufruf bei dieser einen Mail ausblieb. Es gibt kein Sendelog
(`mailnews.send.loglevel` war nicht gesetzt), und der C++-Teil ist nur als `comm-central`-master
gelesen, nicht als Quelle von 158.0.1. Parallele Fenster scheiden als alleinige Ursache aus: Um
09:37 lief dieselbe Reihenfolge ohne Fehler. Dieser ADR rät hier nichts.

Eine zweite Messung begrenzt die Häufigkeit: Über fünf Konten seit dem 25.10. liegt keine gesendete
UID mehr in „Entwürfe“. Die Fassung des Falls 1 liegt im Papierkorb ohne `message_id`, drei andere
Fassungen dort tragen eine; zwei davon sind Proben, die dritte ist ungeprüft. Thunderbird räumt also
in der Regel weg, zugesagt ist es nicht. Das Wegräumen in falzmarke darf deshalb weder davon
abhängen noch von der `message_id`.

## Entscheidung

1. **Ein neues Modul `falzmarke.entwurfsablage`, nach dem Muster von `ablage`.** Ein ändernder
   Befehl: `UID MOVE`, immer in den Ordner mit `\Trash`. Kein `EXPUNGE`, kein Nachbau ohne `MOVE`.
   Fehlt `MOVE` oder `\Trash`, bewegt sich nichts, und der Grund steht da. `postfach.py` bleibt ohne
   ändernde Befehle. Die Add-on-Rechte bleiben, wie sie sind: Thunderbird wegräumen zu lassen,
   bräuchte `messagesDelete` und würde die Zusage aus ADR 0054 aufheben.

2. **Weg darf, was eine von zwei Regeln öffnet:**

   - `schon_raus`, `status` sagt BELEGT, das Tagebuch nennt für diesen Entwurf dieselbe Fassung,
     und im Gesendet-Ordner liegt die Mail an genau dieselben Empfänger, nicht älter als der Entwurf.
   - Ein Entwurf aus dem Buch, und eine **neuere Fassung** ging an genau dieselben Empfänger mit
     demselben Betreff und derselben Antwortstufe hinaus. Neuer heißt: später ins Buch gekommen als
     dieser Entwurf, und erst danach gesendet. Später gesendet allein reicht nicht: Liegen zwei
     Fassungen und geht die ältere hinaus, wird die jüngere vielleicht noch gebraucht.

   „Genau dieselben Empfänger“ heißt Menge, nicht Schnitt: Am 02.11. gingen zwei Mails mit gleichem
   Betreff an zwei Adressen desselben Hauses. Die Antwortstufe hält eine Antwort im Faden heraus.
   „Nicht älter“ hält die erneute Anlage mit `--trotz-gesendet` heraus.

3. **Jede Sperre schlägt beide Regeln.** Liegen bleibt, was gerade offen ist (auch wenn `schon_raus`
   den Zustand sticht), was keine Fassung trägt, was das Buch nicht unter UID und Fassung kennt, was
   laut Tagebuch in Thunderbird gespeichert wurde, dessen Text gekappt ist oder vom Buch abweicht,
   und alles, sobald Buch oder Tagebuch unlesbare Zeilen tragen oder die Fensterliste nicht zu
   erfragen ist. Ein Fall, in dem nur „vielleicht“ dasteht, bleibt liegen, mit Grund. Die Sperren
   stehen als Liste `SPERREN`, damit die Tests je eine herausnehmen können.

4. **Die Gegenrichtung des Falls 1: Die `Message-ID` ist kein Anker, auf den Verlass ist.** Ohne sie
   hängt die Fassung einer gesendeten Mail in der Luft, und das trifft nicht nur den Sonderfall:
   An outlook.de ersetzt der Server sie beim Senden. Gemessen 02.11.2026 fanden dort 12 von 26
   Tagebuchzeilen ihre Mail, an den vier anderen Konten 91 von 92. Deshalb gibt es einen zweiten
   Weg: dasselbe Konto, dieselbe Empfängermenge, derselbe Betreffkern, höchstens 120 s Abstand. Zeit
   und Empfänger allein trafen 26 von 26, aber zwölfmal mehrdeutig; darum der Betreff. Passen
   mehrere Einträge, zählen alle: Ein „vielleicht dieselbe“ ist kein „eine andere“.

5. **Unmittelbar vor dem Zug wird neu gelesen,** je UID Fensterliste samt Speicher-Kette und Kopf.
   Nach dem Zug wird nachgesehen, ob die Nachricht weg ist; ein `UID MOVE` auf eine fehlende UID
   antwortet `OK`.

6. **Der Befehl heißt `aufraeumen --entwuerfe`,** nicht `status --aufraeumen`, wie #425 vorschlug.
   `status` ist lesend zugesagt, und ein Schalter, der aus einer Auskunft eine Handlung macht, stellt
   diese Zusage jedes Mal in Frage. `aufraeumen` hat `--machen`, `--json` und den Exit 3 schon. Der
   Schalter räumt **nur** die Entwürfe, nicht zusätzlich den Eingang: Wer die Anzeige des einen
   gesehen hat, soll mit `--machen` nicht das andere bewegen. Ohne `--entwuerfe` bleibt alles wie in
   ADR 0061.

7. **`email --oeffnen` räumt für den eigenen Absender mit auf,** nachdem der Entwurf liegt, und sagt
   in einer Zeile, welche UIDs weg sind. Ist nichts geschehen, sagt es nichts. Ein Fehlschlag heißt
   `NICHT GEPRÜFT` und ändert den Exit-Code nicht (ADR 0038, Punkt 4). Den Entwurf, den derselbe
   Lauf gerade öffnet, fasst er nicht an: Ein Fenster, das noch aufgeht, steht in keiner Fensterliste.
   `FALZMARKE_AUFRAEUMEN=nie`
   schaltet das ab. `--kein-fenster` ist ausgenommen: Der Schalter ist für Schleifen über viele
   Briefe, ein solcher Lauf spricht die Brücke zugesagt gar nicht an (#415), und der Abgleich kostete
   dort je Brief Sekunden. Den nächsten Lauf ohne den Schalter holt das ein.

8. **Geänderter Text ersetzt den alten Entwurf von selbst, wenn alle passenden alten ablösbar sind.**
   Das ist die Antwort auf die Frage aus #425. Es ist sicher, weil der alte Text nirgends verloren
   geht: Er steht im Buch, in der Quelle und im Papierkorb. Und der bisherige Default war der
   Fehler selbst: Er öffnete den alten Text. Gleiche Fassung öffnet wie bisher den liegenden Entwurf.

   Ablösbar heißt: dieselben Sperren wie oben, dazu genau dieselbe Empfängermenge. Ist nur einer
   nicht ablösbar, bleibt es ohne Schalter bei `ENTWURF LIEGT SCHON`, denn dann ist unklar, was
   gemeint ist. **`--ersetzen`** ist genau für diesen Fall: Es legt den neuen trotzdem an, räumt
   weg, was weg darf, und nennt, was bleibt. Es schließt `--oeffnen` ein und schließt
   `--noch-ein-entwurf` aus.

   Die Reihenfolge ist die Zusage: erst der neue, nachgezählt, dann das Wegräumen. Scheitert es,
   liegen zwei da, und es ist keiner verloren.

## Korrekturen an früheren Aussagen

- **ADR 0054:** „nichts, Thunderbird räumt ihn weg“ gilt in der Regel, zugesagt ist es nicht.
- **ADR 0055, Punkt 2:** `status` bleibt lesend. Lesend ist nicht mehr das ganze Paket: `ablage`
  und `entwurfsablage` bewegen Nachrichten, `status` und die Sperre nicht.
- **ADR 0061:** `ablage` ist nicht mehr das einzige Modul, das eine Nachricht bewegt.

## Grenzen

- **Ein Entwurf, der in Thunderbird geändert und gesendet wurde und liegen blieb, bleibt liegen,**
  wenn der Text abweicht und die Kennung fehlt. Das ist der Fall 1 mal dem Fall outlook.de, zweimal
  selten, und im Zweifel gilt: stehen lassen.
- **Zwillinge derselben Quelle bleiben liegen.** Ging einer von zwei gleichen Entwürfen hinaus, sagt
  das Tagebuch nur für den einen BELEGT. Der andere bleibt als `nicht_belegt` mit Grund stehen.
- **Die neuere Fassung braucht einen Tagebuch- und einen Bucheintrag.** Eine von Hand geschriebene
  Mail überholt nichts. Sie könnte eine Rückfrage sein.
- **Der Abgleich kostet Zeit:** 8 bis 14 Sekunden je Lauf an zwei Konten, gemessen 02.11.2026.
- **`fassungen()` und damit `gesendet.pruefe` nutzen weiter nur die `Message-ID`.** Für die Sperre an
  outlook.de heißt das: Der Weg über die Fassung fällt dort oft aus, der Textvergleich bleibt.
  Das ist älter als dieser ADR und nicht sein Gegenstand.

## Folgen

- `email --oeffnen` kann eine Nachricht bewegen. Das ist die erste Handlung, die `email` ungefragt
  am Postfach vornimmt, außer dem `APPEND`, und deshalb die stärker abgesicherte: Sie ist abschaltbar,
  sagt jede UID und trifft nur den eigenen Absender.
- Der erste Lauf nach der Auslieferung räumt Altbestand weg, der die Regeln erfüllt.
- `tests/test_entwurfsablage.py` hält je Sperre einen Fall und seine Gegenprobe. Eine neue Sperre
  ohne Fall lässt `test_jede_sperre_hat_ihren_fall` scheitern.
