# 0055 — Was aus einem Entwurf wurde: Entwurfsbuch, `status` und die Sperre beim Senden

**Datum:** 25.10.2026 · **Status:** angenommen · **Ergänzt:** [0054](0054-entwurfsbruecke-in-thunderbird.md),
[0051](0051-gesendet-sperre-und-postfach-entwurf.md) · **Hält:** [0038](0038-oeffnen-ist-kein-versand.md), Punkt 5,
[0029](0029-falzmarke-ist-werkzeug-kein-kanal.md) („Versandzustände in einem Ausgangsbuch“)

## Anlass

Am 25.10.2026 schrieb der Betreiber: „Die Entwürfe an [zwei Anbieter] senden, falls noch nicht
geschehen. Solche Fragen werden auch immer wieder gestellt.“ Dazu: Er brauche eine Rückmeldung,
ob eine Mail versendet, gelöscht oder vor dem Senden geändert wurde. Jede dieser Fragen hieß
bisher: Eine Sitzung liest von Hand per IMAP drei Ordner und vergleicht Betreffe.

Die Prüfung aus ADR 0051 steht vor dem Entwurf. Das zweite Senden, um das es dort ging, geschieht
aber in Thunderbird, wo kein falzmarke läuft: ein Entwurf, der zweimal liegt, oder eine Mail, die
schon draußen ist und noch einmal geöffnet wird.

Zuordnen lässt sich eine gesendete Mail ihrem Entwurf nicht über Kopfzeilen. Thunderbird vergibt
beim Senden eine neue `Message-ID` und verwirft `X-Falzmarke-Fassung` (ADR 0054, Messung). Was
bleibt, sind Empfänger, Betreff und Text.

## Entscheidung

1. **Das Entwurfsbuch.** Jeder Entwurf, den `email --oeffnen` ins Postfach legt, bekommt eine
   Zeile JSON in `$XDG_STATE_HOME/falzmarke/entwuerfe.jsonl` (ohne die Variable
   `~/.local/state/…`): Zeit, Konto, Ordner, UID, Fassung, Betreff, Empfänger und der Klartext.
   Der Text steht darin, weil nur er Entwurf und gesendete Mail verbindet. `FALZMARKE_ENTWURFSBUCH`
   legt das Buch woanders hin, `=nie` schaltet es ab. Scheitert das Schreiben, liegt der Entwurf
   trotzdem; falzmarke meldet `HINWEIS  nicht im Entwurfsbuch: <Grund>`.

   **Was geschrieben wird, kommt an (Nachtrag 27.10.2026, #411).** „Scheitert das Schreiben“
   deckte den dritten Fall nicht: geschrieben und unlesbar. Drei Festlegungen dazu.

   - **Eine Zeile kommt ganz oder nicht an.** Geschrieben wird mit genau einem `os.write` auf
     einen `O_APPEND`-Deskriptor, und der Rückgabewert sagt, wie viele Bytes ankamen. Über
     `ZEILE_MAX` (32 KiB) wird allein der Mailtext gekappt — das einzige Feld ohne natürliche
     Grenze —, und `text_gekappt` hält seine ursprüngliche Länge fest. Ein gekappter Text belegt
     dann kein „Text geändert“ mehr: `status` sagt, dass nur sein Anfang verglichen ist.
   - **Das Ausdünnen läuft unter einer Sperre.** `entwuerfe.jsonl.sperre` neben dem Buch, über
     Ausdünnen und Anhängen gehalten (`flock`, unter Windows `msvcrt.locking`). Bekommt sie
     niemand binnen zehn Sekunden, wird ohne sie geschrieben und der Grund gemeldet — wie bei der
     Sperre beim Senden (Punkt 5): Eine Prüfung, die hängt, darf den Menschen nicht aufhalten.
   - **Unlesbare Zeilen werden gezählt.** Jede Zeile, aus der kein Eintrag wird — kaputtes JSON,
     keine Zeit, kein Konto, eine UID, die keine Zahl ist —, geht in einen Zähler, und `status`
     nennt ihn (`HINWEIS  2 Zeilen im Entwurfsbuch sind unlesbar`). Auch dann, wenn das Postfach
     schweigt: `NICHT GEPRÜFT` und „eine Zeile ist weg“ sind zwei verschiedene Lücken.

   **Der ungewisse Lauf steht im Buch.** Reißt die Verbindung hinter dem `APPEND` oder liegt
   danach eine andere Zahl passender Entwürfe (ADR 0051), gibt es keine UID — sie ist nach dem
   Abriss nicht zu ermitteln, und `APPENDUID` wird nicht gelesen. Die Zeile trägt deshalb keine,
   dafür den Grund und den Text. Ohne sie wäre der Text verloren, sobald der Entwurf aus
   „Entwürfe“ verschwindet — der Fall, für den dieses ADR angetreten ist. `status` nennt sie als
   Hinweis, nicht als Zustand: Liegt der Entwurf doch, meldet ihn das Postfach selbst.

   **Was dabei nachgemessen wurde (27.10.2026).** #411 nannte als Verlustweg den gepufferten
   Schreibvorgang: Über ~8 KiB zerfalle er in mehrere Syscalls, die sich verschränken könnten.
   Das trifft für diesen Pfad nicht zu — `TextIOWrapper` über `BufferedWriter` gibt eine Zeile von
   20 KB in einem Stück weiter, auch mit etwas im Puffer davor (`tests/test_entwurfsbuch.py`,
   `test_der_gepufferte_wrapper_war_nicht_der_verlustweg`). `os.write` bleibt der richtige Weg,
   aber aus einem anderen Grund: ein Syscall, ein prüfbarer Rückgabewert, keine Abhängigkeit von
   Pufferinterna. Der belegte Verlustweg ist das Ausdünnen — zwei Läufe zugleich, ohne Sperre
   fehlt die Zeile des zweiten, mit Sperre bleiben beide
   (`test_zwei_laeufe_zugleich_verlieren_keine_zeile` samt Gegenprobe, fünf Läufe). Dabei zeigte
   sich ein zweiter Schaden: Ohne Sperre schreiben beide Läufe dieselbe Zwischendatei
   `entwuerfe.jsonl.neu` und ziehen sie einander weg. Ein dritter Schaden fiel erst beim Lauf am
   echten Befehl auf: `zeilen()` stieg bei gesetztem `grund` nach der einen `NICHT GEPRÜFT`-Zeile
   aus, der Hinweis stand im Bericht und in keiner Ausgabe. Der Test dazu maß bis dahin das
   Berichtsobjekt — das falsche Objekt; er liest jetzt die Zeilen, die `status` ausgibt.
2. **`falzmarke status --absender <adresse>`** liest Entwürfe, Gesendet und Papierkorb nur
   lesend (`EXAMINE`, `BODY.PEEK`) und gleicht sie mit dem Buch und dem Tagebuch ab. Eine Zeile
   je Entwurf:

   | Zeile | heißt |
   |---|---|
   | `WARTET` | liegt in „Entwürfe“, nichts Passendes gesendet |
   | `OFFEN` | liegt dort und ist gerade in einem Fenster offen |
   | `SCHON RAUS` | liegt noch, derselbe Text ging aber schon hinaus: nicht noch einmal senden |
   | `GESENDET` | liegt nicht mehr; eine passende Mail liegt in Gesendet („Text unverändert“ oder „Text geändert“, `--diff` zeigt den Unterschied), oder das Tagebuch meldet das Senden. „Text geändert“ heißt derselbe Betreff mit nicht mehr `AW:` als der Entwurf; eine Antwort im selben Faden zählt nicht. Liegt der Entwurf selbst (seine Fassung) im Papierkorb, zählt nur derselbe Text |
   | `ERSETZT` | liegt nicht mehr, ein neuerer mit demselben Betreff an einen dieser Empfänger schon |
   | `GELÖSCHT` | liegt im Papierkorb (dieselbe Fassung oder derselbe Betreff an einen dieser Empfänger, nicht älter als der Entwurf). Ging derselbe Betreff mit anderem Text hinaus, nennt die Zeile das. Gesendet ist er nicht: Nach dem Senden löscht Thunderbird einen Entwurf, ohne ihn in den Papierkorb zu legen |
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

   „Derselbe Text“ hat zwei Schwellen, und sie gelten auf beiden Seiten gleich: Ein Textkern —
   alles bis zur Grußformel — zählt erst ab **20 Zeichen Textkern**, und ein eigener Text, der
   bloß der Anfang der gesendeten Mail ist, erst ab **80 Zeichen Anfang** (`KERN_MIN` und
   `ANFANG_MIN` in `gesendet.py` und `vergleich.js`). Darunter vergleicht die Regel nichts: Eine
   leere Nachricht gliche jeder anderen leeren, und „Hallo Paula, danke!“ steht am Anfang vieler
   verschiedener Mails.
5. **Scheitert die Prüfung, wird gesendet.** Fehlt der Gesendet-Ordner, wirft eine Abfrage, geht
   der Dialog nicht auf oder liegen mehr als 2000 gesendete Mails in 14 Tagen, lässt die Sperre die
   Mail hinaus und schreibt
   `pruefung_fehlgeschlagen` mit dem Grund ins Tagebuch. Eine Prüfung, die hängt, darf den
   Menschen nicht aufhalten; dass sie nicht geprüft hat, steht dann in `status`.
6. **Senden kann das Add-on weiter nicht.** Das Manifest verlangt genau `compose`, `messagesRead`
   und `accountsRead`, nicht `compose.send`, `compose.save`, `messagesDelete`, `messagesMove` oder
   `messagesModify`. `tests/test_entwurfsbruecke.py` prüft das Manifest und alle vier
   JS-Dateien auf verbotene Aufrufe, je mit Gegenprobe. Die Sperre kann ein Senden anhalten,
   auslösen kann sie keines.

   **Wie weit diese Prüfung trägt (Nachtrag 27.10.2026, #412).** Sie ist eine Rückfallsicherung
   gegen das Versehen, keine technische Grenze: Der privilegierte Teil des Add-ons — das
   Experiment in `implementation.js` — läuft in Thunderbird mit vollen Rechten und dürfte
   technisch auch senden oder löschen; die Rechteliste des Manifests bindet allein `background.js`.
   Was die Prüfung seit #412 hält:

   - Die Rechte werden als **Positivliste über das ganze Manifest** gelesen, nicht nur unter
     `permissions`. Ein weiterer Schlüssel ist ein Fehler, auch `optional_permissions`,
     `content_scripts`, `web_accessible_resources`, `content_security_policy` oder `cloud_file`,
     und ebenso ein zweiter Eintrag unter `experiment_apis`. Je Schlüssel eine eigene Gegenprobe.
   - Die Namensliste der Sendewege vergleicht **ohne Rücksicht auf Groß- und Kleinschreibung** und
     kennt den privilegierten Weg `goDoCommand("cmd_sendNow")`. Gesucht wird im Code, nicht in
     Kommentaren — die eigene Begründung ist kein Aufruf.
   - Die Dateiliste des Pakets wird am Manifest abgelesen (`scripts/xpi_packen.py`, `dateien()`),
     der Sollwert der Prüfung steht davon getrennt im Test.

   Was weiter durchgeht: ein zur Laufzeit gebildeter Name (`obj["send" + "Message"]`). Dagegen
   hilft keine Textsuche. Wer dem Add-on nicht traut, liest die vier Dateien — es sind unter
   3000 Zeilen — oder installiert es nicht.

### Was ADR 0029 dazu sagt

[0029](0029-falzmarke-ist-werkzeug-kein-kanal.md) nennt **Versandzustände in einem Ausgangsbuch**
ausdrücklich als nicht Teil von falzmarke und verweist sie in ein eigenes Repository. Gemeint ist
dort der Nachweis über den Weg einer Nachricht: dass sie befördert und dass sie zugestellt wurde,
samt Verwahrung dieses Nachweises. Diesen Nachweis führt das Entwurfsbuch nicht, und `status`
behauptet ihn an keiner Stelle.

Das Buch hält fest, was aus einem **lokalen Entwurf** wurde — aus einer Datei, die falzmarke
selbst erzeugt und ins eigene Postfach gelegt hat. `GESENDET` heißt dort „liegt in Gesendet“,
nicht „ist angekommen“: gelesen wird allein das eigene Postfach, nie ein Empfänger, kein
Zustellbericht und kein Dritter. Die Zusicherung, um die es 0029 ging, bleibt damit unangetastet
— wer eine Datei erzeugt, haftet für ihren Inhalt; wer sie befördert, für Zustellung und
Nachweis, und falzmarke befördert weiterhin nichts.

Die Grenze bleibt deshalb, wo 0029 sie gezogen hat: Einlieferungsbeleg, Empfangsbestätigung und
Aufbewahrungsfrist gehören nicht hierher. Die Zustände, die `status` meldet, lesen das
eigene Postfach; sie sind kein Ausgangsbuch, sondern die Antwort auf die Frage „habe ich
das schon geschickt?“.

### Was ADR 0038, Punkt 5 dazu sagt

`entwurfsbuch.py` startet kein Programm und importiert `subprocess` nicht. Den IMAP-Zugang holt es
erst in `abgleich()`. Der MCP-Dienst lädt das Modul nicht, `tests/test_befehl_email.py` misst das
im Kindprozess. Im Testlauf leitet `tests/conftest.py` das Buch in ein leeres Verzeichnis je Test
um, und Kindprozesse bekommen `FALZMARKE_ENTWURFSBUCH=nie`.

### Was hingenommen wird

- Das Buch enthält den Text jeder Mail im Klartext auf der lokalen Platte, wie die `.eml`
  daneben. **Nachtrag 25.10.2026:** Der Vergleich mit der `.eml` trug nicht weit genug. Die
  `.eml` ist eine Datei je Vorgang, das Buch ist das wachsende Archiv aller — und es lag
  gemessen als `-rw-r--r--` in `drwxr-xr-x`, also für jedes Konto des Rechners lesbar, ohne
  Obergrenze und ohne Aufbewahrungsfrist. Seit 0.11 legt `os.open` es mit 0600 in einem
  Ordner mit 0700 an, ein vorhandenes Buch wird beim nächsten Schreiben nachgezogen, und
  Zeilen älter als `AUFBEWAHRUNG_TAGE` (vier Mal die Spanne von `status`) verlassen es beim
  Schreiben. `O_NOFOLLOW` verhindert dabei, dass ein Symlink an dieser Stelle die Zeile in
  eine fremde Datei hängt (ADR 0058). Unter Windows sagen die Rechtebits nichts; dort
  schützt das Benutzerprofil.
- Auf einem Netzpfad bleibt „ganz oder nicht“ unzugesagt: Weder `O_APPEND` noch ein einzelner
  `write` sind dort atomar, und `flock` wirkt über NFS nur, wo der Server es unterstützt. Der
  Rückgabewert von `os.write` wird trotzdem geprüft — eine halb angekommene Zeile wird gemeldet,
  statt still zu stehen.
- Zeilen, die vor dieser Fassung verloren gingen, bleiben verloren. Der Zähler sieht allein, was
  als beschädigte Zeile im Buch steht, nicht, was nie hineinkam.
- Unter Windows ist die Sperre nicht gemessen. Die Probe mit zwei Läufen fährt auf POSIX; dort
  liegt `msvcrt.locking` an derselben Stelle, aber ohne Messung ist das NICHT GEPRÜFT.
- Die Sperre sieht nur, was Thunderbird von den Gesendet-Ordnern kennt. Eine Mail, die von einem
  anderen Gerät hinausging, zählt erst, wenn Thunderbird den Ordner abgeglichen hat.
- Die Betreff-Regel warnt auch vor einer gewollten Korrektur. Das kostet einen Klick.
- Kurze Mails deckt die Textregel nicht ab. Unter den beiden Schwellen — **20 Zeichen Textkern**,
  **80 Zeichen Anfang** — bleibt allein die Betreff-Regel, also 24 Stunden und nur bei einem
  Entwurf oder einer neuen Mail. „Anbei die Rechnung, viele Grüße“ zweimal zu senden ist von zwei
  verschiedenen kurzen Mails nicht zu unterscheiden; eine Sperre, die bei jeder Kurznachricht
  fragt, erzieht zum Wegklicken. Die Lücke bleibt bewusst offen.
- Was älter als 14 Tage ist, sieht keine der beiden Seiten.
- Liegen zwei Entwürfe mit demselben Text, heißen beide `GESENDET`, sobald einer hinausging, auch
  wenn der andere danach gelöscht wurde. Der Text ist draußen; was mit dem zweiten geschah, steht
  in seinen Tagebuchzeilen.
- Legt ein anderes Mailprogramm einen Entwurf nach dem Senden in den Papierkorb, heißt er
  `GELÖSCHT`. Ging er mit anderem Text hinaus, nennt die Zeile die gesendete Mail daneben.
- Als der Entwurf selbst gilt im Papierkorb nur eine Mail mit seiner Fassung, die nicht älter ist
  als sein Eintrag im Buch (fünf Minuten Spiel, denn `Date` steht vor dem Eintrag). Lag dieselbe
  Quelle zweimal als Entwurf, ging einer geändert hinaus und landete der andere im Papierkorb,
  heißt der gesendete `GELÖSCHT`, wenn der weggeworfene der spätere war oder beide binnen fünf
  Minuten entstanden; welcher gesendet wurde, steht dann nur im Tagebuch. Ob Thunderbird
  `X-Falzmarke-Fassung` beim erneuten Speichern eines Entwurfs behält, ist nicht gemessen. Fehlt
  sie, gilt ein weggeworfener Entwurf wieder als „gesendet, Text geändert“, sobald derselbe
  Betreff mit anderem Text hinausging.
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
