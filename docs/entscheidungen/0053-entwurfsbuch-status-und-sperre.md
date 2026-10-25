# 0053 — Was aus einem Entwurf wurde: Entwurfsbuch, `status` und die Sperre beim Senden

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:** [0052](0052-entwurfsbruecke-in-thunderbird.md),
[0051](0051-gesendet-sperre-und-postfach-entwurf.md) · **Hält:** [0038](0038-oeffnen-ist-kein-versand.md), Punkt 5

## Anlass

Am 25.10.2026 schrieb der Betreiber: „Die Entwürfe an [zwei Anbieter] senden, falls noch nicht
geschehen. Solche Fragen werden auch immer wieder gestellt.“ Dazu: Er brauche eine Rückmeldung,
ob eine Mail versendet, gelöscht oder vor dem Senden geändert wurde. Jede dieser Fragen hieß
bisher: Eine Sitzung liest von Hand per IMAP drei Ordner und vergleicht Betreffe.

Die Prüfung aus ADR 0051 steht vor dem Entwurf. Das zweite Senden, um das es dort ging, geschieht
aber in Thunderbird, wo kein falzmarke läuft: ein Entwurf, der zweimal liegt, oder eine Mail, die
schon draußen ist und noch einmal geöffnet wird.

Zuordnen lässt sich eine gesendete Mail ihrem Entwurf nicht über Kopfzeilen. Thunderbird vergibt
beim Senden eine neue `Message-ID` und verwirft `X-Falzmarke-Fassung` (ADR 0052, Messung). Was
bleibt, sind Empfänger, Betreff und Text.

## Entscheidung

1. **Das Entwurfsbuch.** Jeder Entwurf, den `email --oeffnen` ins Postfach legt, bekommt eine
   Zeile JSON in `$XDG_STATE_HOME/falzmarke/entwuerfe.jsonl` (ohne die Variable
   `~/.local/state/…`): Zeit, Konto, Ordner, UID, Fassung, Betreff, Empfänger und der Klartext.
   Der Text steht darin, weil nur er Entwurf und gesendete Mail verbindet. `FALZMARKE_ENTWURFSBUCH`
   legt das Buch woanders hin, `=nie` schaltet es ab. Scheitert das Schreiben, liegt der Entwurf
   trotzdem; falzmarke meldet `HINWEIS  nicht im Entwurfsbuch: <Grund>`.
2. **`falzmarke status --absender <adresse>`** liest Entwürfe, Gesendet und Papierkorb nur
   lesend (`EXAMINE`, `BODY.PEEK`) und gleicht sie mit dem Buch und dem Tagebuch ab. Eine Zeile
   je Entwurf:

   | Zeile | heißt |
   |---|---|
   | `WARTET` | liegt in „Entwürfe“, nichts Passendes gesendet |
   | `OFFEN` | liegt dort und ist gerade in einem Fenster offen |
   | `SCHON RAUS` | liegt noch, derselbe Text ging aber schon hinaus: nicht noch einmal senden |
   | `GESENDET` | liegt nicht mehr; eine passende Mail liegt in Gesendet („Text unverändert“ oder „Text geändert“, `--diff` zeigt den Unterschied), oder das Tagebuch meldet das Senden |
   | `ERSETZT` | liegt nicht mehr, ein neuerer mit demselben Betreff an einen dieser Empfänger schon |
   | `GELÖSCHT` | liegt im Papierkorb |
   | `VERSCHWUNDEN` | nirgends, die Zeile nennt die Ordner, in denen gesucht wurde |

   `GESENDET … BELEGT` steht nur, wenn das Tagebuch das Senden meldet **und** die Mail in Gesendet
   liegt: zwei Quellen, die einander widersprechen könnten. Ohne Tagebuch ist es eine Quelle.
   Liegen zwei Entwürfe mit demselben Betreff an dieselben Empfänger, meldet `status` das mit
   `nur einen senden`. Ist das Postfach nicht erreichbar, heißt die Zeile `NICHT GEPRÜFT`, Exit 3,
   und kein Entwurf wird als verschwunden gemeldet.
3. **Das Tagebuch.** Ab 0.2.0 schreibt die Entwurfsbrücke `entwurfsbruecke-tagebuch.jsonl` in den
   Profilordner von Thunderbird. Für jedes Verfassen-Fenster hält sie fest, woher der Entwurf kam
   (Konto, UID, Fassung, Betreff) und was geschah: `geoeffnet`, `gespeichert` (mit der neuen UID),
   `gesendet` (mit der neuen `Message-ID`), `senden_fehlgeschlagen`, `geschlossen`, `gesperrt`,
   `trotzdem`, `pruefung_fehlgeschlagen`. `status` liest die Datei direkt, auch bei geschlossenem
   Thunderbird; einen weiteren Befehl am Port braucht es dafür nicht.
4. **Die Sperre beim Senden.** Vor dem Senden sieht das Add-on in den Gesendet-Ordnern des Kontos
   nach. Ging derselbe Text in den letzten 14 Tagen an einen dieser Empfänger, oder ging in den
   letzten 24 Stunden ein anderer Text mit demselben Betreff an sie und das Fenster ist ein Entwurf
   oder eine neue Mail, fragt Thunderbird nach. Antworten fallen unter die zweite Regel nicht, sie
   teilen ihren Betreff. Vorgewählt ist „Nicht senden“, und Escape oder das Schließen des Dialogs
   zählen ebenso. Der Vergleich steht als `vergleich.js` im Add-on und urteilt wie
   `gesendet.py`; `tests/test_vergleich_js.py` gibt beiden dieselben Eingaben.
5. **Scheitert die Prüfung, wird gesendet.** Fehlt der Gesendet-Ordner, wirft eine Abfrage, geht
   der Dialog nicht auf oder liegen mehr als 2000 gesendete Mails in 14 Tagen, lässt die Sperre die
   Mail hinaus und schreibt
   `pruefung_fehlgeschlagen` mit dem Grund ins Tagebuch. Eine Prüfung, die hängt, darf den
   Menschen nicht aufhalten; dass sie nicht geprüft hat, steht dann in `status`.
6. **Senden kann das Add-on weiter nicht.** Das Manifest verlangt genau `compose`, `messagesRead`
   und `accountsRead`, nicht `compose.send`, `compose.save`, `messagesDelete`, `messagesMove` oder
   `messagesModify`. `tests/test_entwurfsbruecke.py` prüft das Manifest und alle drei
   JS-Dateien auf verbotene Aufrufe, je mit Gegenprobe. Die Sperre kann ein Senden anhalten,
   auslösen kann sie keines.

### Was ADR 0038, Punkt 5 dazu sagt

`entwurfsbuch.py` startet kein Programm und importiert `subprocess` nicht. Den IMAP-Zugang holt es
erst in `abgleich()`. Der MCP-Dienst lädt das Modul nicht, `tests/test_befehl_email.py` misst das
im Kindprozess. Im Testlauf leitet `tests/conftest.py` das Buch in ein leeres Verzeichnis je Test
um, und Kindprozesse bekommen `FALZMARKE_ENTWURFSBUCH=nie`.

### Was hingenommen wird

- Das Buch enthält den Text jeder Mail im Klartext auf der lokalen Platte, wie die `.eml` daneben.
- Die Sperre sieht nur, was Thunderbird von den Gesendet-Ordnern kennt. Eine Mail, die von einem
  anderen Gerät hinausging, zählt erst, wenn Thunderbird den Ordner abgeglichen hat.
- Die Betreff-Regel warnt auch vor einer gewollten Korrektur. Das kostet einen Klick.
- Was älter als 14 Tage ist, sieht keine der beiden Seiten.
- Die Tests von `background.js` laufen in node gegen eine Attrappe der MailExtension-API. Sie
  zeigen, dass die Regeln stimmen, nicht, dass Thunderbird die API so liefert. Die vier Stellen,
  die die Attrappe nur annimmt, hat die Probe vom 25.10. in Thunderbird bestätigt (Messung).

## Messung 25.10.2026

- `status` lief nur lesend gegen zwei echte Postfächer (Bestellungen, Vertrieb). Je fünf Entwürfe
  lagen, keiner im Buch, denn das Buch beginnt mit dieser Fassung.
- Das Bestellpostfach hatte **550 gesendete Mails in 14 Tagen**. `postfach.GRENZE` (500, für die
  24-Stunden-Prüfung aus ADR 0051) schnitt die ältesten 50 ab, und `status` sagte es nicht. Jetzt
  sieht `status` bis zu 3000 an (`GRENZE_GESENDET`), holt die Kopfzeilen in Stücken zu 500 und
  meldet `nur die neuesten … von …`, wenn auch das nicht reicht. Danach: 543 angesehen, die übrigen
  lagen vor der genauen Zeitgrenze.
- In den beiden Postfächern lagen drei Gruppen gleicher Entwürfe (2, 2 und 3 Stück an jeweils
  dieselben Empfänger). Daher der Hinweis `nur einen senden`.
- Die zwei Entwürfe aus dem Anlass lagen nicht mehr in „Entwürfe“. Per IMAP, nur lesend: beide je
  einmal in Gesendet, am 25.10. um 13:16. `status` hätte das nicht gesagt, denn sie standen in
  keinem Buch. Für Entwürfe ab dieser Fassung schließt das Buch diese Lücke.
- Die Sperre in Thunderbird, Probe mit 0.2.0: ein Entwurf an die eigene Adresse, zweimal aus
  derselben Quelle abgelegt. Den einen gesendet. Beim Senden des anderen kam der Dialog „Diese
  Mail ging schon hinaus“ auf dem Verfassen-Fenster, „Nicht senden“ vorgewählt. Im
  Tagebuch standen `geoeffnet`, `gesendet` mit `Message-ID`, `gesperrt` (`gleicher_text`) und
  `geschlossen`, alle mit Konto und UID. `status` meldete den ersten `GESENDET`, „Text
  unverändert · BELEGT“, den zweiten `SCHON RAUS`.
- Damit bestätigt: `messageKey` ist die IMAP-UID (dieselbe Zahl im Buch und im Tagebuch),
  `tabs.onCreated` meldet Verfassen-Fenster, `folders.query` mit `specialUse` findet „Gesendet“,
  und der Dialog hängt am Verfassen-Fenster.
- Zwei Fehler, beide in 0.2.1 behoben. Erstens meldet Thunderbird ein angehaltenes Senden danach
  noch als gescheitertes („Send aborted by an onBeforeSend event“), und das Tagebuch schrieb hinter
  `gesperrt` ein `senden_fehlgeschlagen`. Jetzt merkt sich das Fenster das Anhalten, und die
  Attrappe meldet wie Thunderbird. Zweitens tragen zwei Entwürfe aus derselben Quelle dieselbe
  Fassung. `status` ordnete das Tagebuch über UID oder Fassung zu und zeigte beim einen die
  Einträge des anderen. Jetzt zählt die UID, samt der Kette, die `gespeichert` mit `neu_uid`
  bildet. Die Fassung zählt nur, wenn ein Eintrag keine UID hat.

## Was folgt

`entwurf-oeffnen` kann neben jedem Entwurf seinen Zustand aus `status` zeigen, damit niemand einen
Entwurf öffnet, der schon draußen ist.
