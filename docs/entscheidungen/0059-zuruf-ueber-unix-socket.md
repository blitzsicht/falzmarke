# 0059 — Der Zuruf an die Entwurfsbrücke läuft über einen Unix-Socket mit 0600

**Datum:** 25.10.2026 · **Status:** angenommen ·
**Nimmt zurück:** [0054](0054-entwurfsbruecke-in-thunderbird.md), Punkt 1, für den Weg

## Anlass

ADR 0054 legte den Zuruf auf `127.0.0.1:1994`. Die Gegenprobe vom 25.10.2026 zeigt, was das
heißt: Ein fremder Prozess — gestartet ohne Zugangsdaten, ohne Anmeldung, mit `python3 -I` —
bekam eine vollständige Antwort:

```
{"ok":true,"name":"entwurfsbruecke","version":"0.2.1","thunderbird":"158.0.1"}
```

Dieselbe Verzweigung bedient ohne weitere Prüfung `fenster` — Betreffe, `draft_id` und
`originalMsgURI` aller offenen Verfassen-Fenster, seit 0.3.0 dazu Empfänger, Anhänge und der
Text bis 20.000 Zeichen — und `protokoll`, die letzten sechzig Vorgänge samt Konto, UID,
Betreff und Fehlermeldungen. `entwurf_oeffnen` holt über `nsIMacDockSupport` die ganze Anwendung
nach vorn.

Ein Port auf 127.0.0.1 nimmt **jeden Prozess jedes Kontos** dieses Rechners an; die
Zeilenprüfung („muss mit `{` beginnen") hält nur einen Browser ab, keinen Prozess, der eine
Zeile schreiben kann. Und wer zuerst lauscht, besitzt den Port: Ein fremder Dienst, der vor
Thunderbird startet, bekommt die Zurufe und kann sich als Brücke ausgeben.

## Entscheidung

1. **Unix-Socket im Thunderbird-Profil, Rechte 0600.** `bruecke.sock` im Profilordner, angelegt
   mit `nsIServerSocket.initWithFilename(datei, 0o600, -1)`. Damit entscheiden die Dateirechte,
   und die gelten für das Konto, das Thunderbird fährt. Kein geteiltes Geheimnis: Ein Token wäre
   eine zweite Wahrheit neben den Rechten, und es müsste irgendwo liegen.
2. **Kurzer Name, weil `sun_path` kurz ist.** macOS fasst 104 Byte. Gemessen am 25.10.2026 ist
   der Profilordner dieses Rechners 74 Byte lang — mit `falzmarke-entwurfsbruecke.sock` wären es
   105 Byte gewesen, **eins zu viel**. Mit `bruecke.sock` sind es 87. falzmarke prüft die Länge
   selbst und sagt, was zu tun ist, statt ein nacktes `OSError` weiterzugeben;
   `FALZMARKE_BRUECKE_SOCKET` setzt notfalls einen kürzeren Pfad.
3. **Wer sich nicht ausweist, ist nicht die Brücke.** Meldet eine Antwort ein `name`, das nicht
   `entwurfsbruecke` lautet, gilt sie nicht als Aussage der Brücke. Vorher druckte `falzmarke`
   die gemeldete Fassung ungeprüft.
4. **Steuerzeichen gehen nicht in die Ausgabe.** Betreff, Grund und Fenstertext aus der Antwort
   verlieren ihre Steuer- und Formatzeichen, bevor sie in `print` gehen — `json.loads` lässt
   echte ESC-Sequenzen durch, und ein Betreff mit `ESC[2K` überschreibt im Terminal die Zeile,
   in der er steht. Der Fenstertext behält Umbruch und Tabulator, sonst stünde er als eine
   Zeile da.
5. **Leerlauffrist und Obergrenze.** Eine Verbindung ohne vollständige Zeile wird nach zehn
   Sekunden getrennt; mehr als acht gleichzeitig nimmt die Brücke nicht an. Vorher blieb eine
   Verbindung, die nichts schickt, für immer in `verbindungen` stehen.
6. **Ein altes Socket blockiert den Start nicht.** `initWithFilename` legt sich nicht über eine
   bestehende Datei; nach einem Abbruch wird der Name weggeräumt, beim Stoppen ebenfalls.

### Was nicht geändert wurde, und warum

`vorholen` holt Thunderbird auch dann nach vorn, wenn das Fenster schon offen war. Der
Abhilfe-Plan wollte das auf neu entstandene Fenster begrenzen, weil ein fremder Rufer sonst die
Anwendung beliebig oft nach vorn ziehen kann. Mit dem Socket ist dieser Rufer dasselbe Konto,
das vor dem Rechner sitzt — und wer `falzmarke email --oeffnen` auf einen schon offenen Entwurf
ruft, will genau dieses Fenster sehen. Der Schutz hätte hier den Nutzen gekostet, den er
schützen soll. **Bewusst unverändert**, nicht vergessen.

### Was hingenommen wird

- **Nur macOS.** Der ganze Thunderbird-Weg ist auf macOS gemessen und läuft nur dort
  (`oeffnen.py` prüft `darwin`, #108). Ein Unix-Socket kostet also keine Plattform. Unter
  Windows gäbe es `AF_UNIX` erst mit Einschränkungen — das wird gelöst, wenn der Weg dort
  überhaupt öffnet.
- **Wer unter demselben Konto Schadcode fährt, kommt an den Socket.** Dagegen schützen
  Dateirechte nicht. Sie trennen Konten, nicht Prozesse eines Kontos; wer als derselbe Benutzer
  läuft, kann ohnehin die Mails im Profil lesen.
- **`FALZMARKE_BRUECKE_SOCKET` zeigt, wohin man den Socket stellt.** Deshalb bleibt die
  Namensprüfung aus Punkt 3 nötig, auch wenn die Rechte eine Fremdantwort unwahrscheinlich
  machen.
- **Die Rechte des Sockets sind seit dem 26.10.2026 am laufenden Thunderbird nachgemessen**
  (Nachtrag unten). Vorher galt dieser Punkt als nicht geprüft, weil nur der Aufruf im
  Quelltext belegt war.

## Nachtrag 26.10.2026 — am Gerät gemessen, und was dabei auffiel

**1. Die Rechte stimmen.** Am installierten Add-on im Profil: `srw------- 600`, Eigentümer das
Konto, das Thunderbird fährt. Der Pfad ist 87 von 104 Byte lang, wie gerechnet. Der alte Weg ist
zu: auf 1994 horcht nichts, ein fremder `python3 -I` bekommt `ConnectionRefusedError`, `lsof`
auf den Port ist leer. Damit ist Punkt 1 nicht mehr nur im Quelltext belegt.

**2. 0.3.1 und 0.3.2 haben auf keine Anfrage geantwortet.** Der Socket nahm die Verbindung an
und schloss nach zwei Millisekunden mit null Byte, fünfmal in Folge gleich. Ursache war
`clearTimeout` ohne Import: im Experiment gibt es keine Uhr-Funktionen als globale Namen, und
der Aufruf stand im Annahmepfad. Behoben in 0.3.3, nachgemessen am 26.10.2026: `ping` antwortet
dreimal in je einer Millisekunde, `fenster` und `protokoll` ebenso, ein unbekannter Befehl wird
mit `befehl_unbekannt` abgewiesen. Die Vermutung, es liege an
`openOutputStream(OPEN_BLOCKING, 0, 0)` statt an Flags `0`, war **falsch** — der Ausgang ist
unverändert und trägt. Sie steht hier, weil sie gekostet hat: Ein Verdacht auf unveränderten
Code erklärt nicht, warum derselbe Code vorher trug.

**3. Für den Transport gibt es keine automatische Gegenprobe.** Kein Test der Suite kann einen
Thunderbird-Socket öffnen. Dass die Brücke antwortet, ist nur am Gerät messbar, und zwar nach
jeder Installation. Die Proben in `tests/test_entwurfsbruecke.py` prüfen den Quelltext; sie
haben am 26.10. durchgehend grün gestanden, während keine einzige Anfrage beantwortet wurde.

**4. Defekte gehen auf Platte** (0.3.4, #421). Das Protokoll stand allein im Speicher und war
allein über den Socket lesbar — also über genau den Kanal, der im Fehlerfall ausfällt. Darum
`entwurfsbruecke-fehler.jsonl` im Profil, 200 Zeilen gedeckelt, Inhalt begrenzt auf Zeitstempel,
Art, Ausnahmetext und Fassung. Keine Betreffe, keine Adressen, keine UIDs, kein Mailtext: der
Eintrag wird aus einer Positivliste gebaut, nicht aus den Angaben des Protokolls. Jeder Rückruf
des Transports liegt jetzt in einer Hülle, die wirft, meldet und aufräumt, statt still
abzureißen.

**Zu den Rechten dieser Datei:** `IOUtils` kennt keinen Modus-Parameter, die Datei entsteht also
mit der Vorgabe des Systems — gemessen `-rw-r--r-- 644`, wie das Tagebuch daneben. Geschützt ist
sie über den Ordner: der Profilordner liegt auf `drwx------ 700`, fremde Konten kommen nicht
hinein. Das ist der Unterschied zum Entwurfsbuch, das in einem 755er Ordner liegt und deshalb
0600 an der Datei selbst braucht.

## Belege

- Gegenprobe des Befundes am 25.10.2026: fremder Prozess, kein Geheimnis, vollständige
  `ping`-Antwort über den Port (Ausgabe oben).
- Fünf Sabotagen, einzeln gefahren, jede mit vorher benanntem Ziel, jede trifft genau einen
  Test: Rechte `0o644` statt `SOCKET_RECHTE`; weggelassene Obergrenze; Leerlauffrist, die nicht
  trennt; übergangene Namensprüfung; `_zahm`, das den Text unverändert zurückgibt.
- Die Pfadlänge ist gemessen, nicht geschätzt: 105 Byte mit dem ersten Namen, 87 mit diesem,
  Grenze 104.
- Der Testriegel lag auf dem falschen Referenten: `tests/conftest.py` verglich den Port mit
  `bruecke.PORT`, also fiel er mit gesetztem `FALZMARKE_BRUECKE_PORT` lautlos aus. Er liegt
  jetzt auf `bruecke._sockel`, der Funktion, die wirklich verbindet. Die Prüfungen am Socketpfad
  stehen eine Schicht darüber, damit sie im Testlauf überhaupt laufen — der autouse-Riegel
  `_keine_echte_bruecke` besetzt `VERBINDEN` und hätte sie sonst nie erreicht.
