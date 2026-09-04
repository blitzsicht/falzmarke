# Änderungen

Das Format folgt lose [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

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
