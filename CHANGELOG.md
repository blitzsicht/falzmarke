# Änderungen

Das Format folgt lose [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

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
