# 0038 — Öffnen ist kein Versand

**Datum:** 04.09.2026 · **Status:** angenommen, geändert am 08.09.2026 ·
**Löst:** [#239](https://github.com/blitzsicht/falzmarke/issues/239),
[#263](https://github.com/blitzsicht/falzmarke/issues/263)

> **Der Kern hat sich am 08.09.2026 verschoben.** Das Werkzeug darf jetzt einen **Entwurf**
> anlegen. Alles, was unten steht, gilt unverändert weiter — außer dem Verbot der
> Programmsteuerung, und der Nachtrag am Ende sagt, was an seine Stelle tritt und warum die
> Begründung dabei nicht verlorengeht.

## Entscheidung

falzmarke darf eine fertige Datei **dem Betriebssystem übergeben** — einen Pfad an `open`,
`xdg-open` oder `os.startfile`, mehr nicht. Was damit geschieht, entscheidet die Zuordnung des
Systems, nicht das Werkzeug.

Es darf **kein Mailprogramm steuern**: kein AppleScript, kein COM, kein Anlegen von Entwürfen,
kein Ausfüllen von Feldern, kein Auslösen von Aktionen. Und kein Versand, wie schon in
[0034](0034-email-ist-ausgabe.md) festgelegt.

> **Geändert am 08.09.2026 (#263).** Der erste Satz gilt so nicht mehr: Ein **Entwurf** wird
> angelegt, per AppleScript, mit Empfänger, Betreff, Rumpf und Anhängen. Nicht geändert hat sich
> der zweite: **kein Versand.** Siehe den Nachtrag am Ende.

Das ist die Einlösung eines Satzes, der in 0034 bereits steht: „Wer die erzeugte `.eml`
versenden will, **öffnet sie in seinem Mailprogramm** — das ist der Punkt, an dem falzmarkes
Zuständigkeit endet." Bis jetzt musste der Mensch diesen Satz selbst ausführen. Jetzt darf das
Werkzeug ihn zu Ende sprechen — und keine Silbe weiter.

Fünf Festlegungen folgen daraus.

### 1. Ein Pfad, kein Programmname

Übergeben wird an das **Standardprogramm** des Systems. falzmarke sucht keine Anwendungen,
kennt keinen Programmnamen und trägt keine Liste bevorzugter Mailprogramme.

Das ist keine Bequemlichkeit, sondern die Zuständigkeitsgrenze in ihrer schmalsten Form. Welches
Programm eine `.eml` öffnet, hat der Mensch längst entschieden — im Betriebssystem, für alle
Programme, ein einziges Mal. Ein Werkzeug, das diese Wahl überstimmt, weil sein Autor ein
anderes Mailprogramm mag, nimmt eine Entscheidung an sich, die ihm nicht gehört.

Wer ein anderes Programm will, ändert die Zuordnung im System. Das wirkt dann überall, nicht nur
hier.

### 2. Opt-in, immer

Ohne ausdrückliches Flag öffnet sich nichts. `serie` erzeugt Nachrichten im Dutzend, die
Testsuite hundertfach, die GitHub-Aktion läuft ohne Bildschirm. Ein Öffnen als Vorgabe hieße
dort Fensterlawine oder Fehlschlag — und beides fiele demjenigen zur Last, der das Flag nie
verlangt hat.

Dieselbe Begründung wie beim `text/markdown`-Teil in 0034, Punkt 3: Eine Fähigkeit mit Wirkung
nach außen wird verlangt, nicht stillschweigend geliefert.

### 3. Erst messen, dann öffnen

Der Aufruf steht **hinter** der Prüfung. Was `verify --email` nicht besteht, wird niemandem ins
Mailprogramm gelegt, wo der nächste Handgriff „Weiterleiten" heißt.

Das ist Regel 0 des Skills, angewandt auf den einzigen Schritt, der den Prozess verlässt.

### 4. Ein Fehlschlag entwertet die Datei nicht

Kein zugeordnetes Programm, kein Bildschirm, ein Starter, den es nicht gibt: Das ergibt eine
Meldung auf der Fehlerausgabe und **keinen anderen Exit-Code**. Die `.eml` ist geschrieben und
gemessen — das ist die Zusage des Befehls, und sie ist erfüllt. Ein Fenster, das nicht aufgeht,
macht sie nicht ungültig.

Der zweite Grund wiegt schwerer als der erste: `--oeffnen` in ein Skript aufzunehmen darf
dessen Fehlersemantik nicht ändern. Gäbe das Öffnen einen Exit-Code, hinge der Erfolg eines
Serienlaufs plötzlich an der Fensterverwaltung des Rechners.

Stillschweigend scheitert es trotzdem nie. Die Meldung nennt, was versucht wurde, was zurückkam
und wo die Datei liegt.

### 5. Genau ein Modul startet fremde Programme

Der Aufruf lebt in `skill/falzmarke/oeffnen.py` und wird aus der Befehlsschicht **spät**
importiert. `eml.py`, die Bibliothek und der MCP-Dienst bleiben frei davon.

Der Grund ist nachmessbar, nicht ästhetisch: `dienst.py` importiert `falzmarke.cli` auf
Modulebene. Ein `import subprocess` am Kopf von `cli.py` läge damit in jedem MCP-Prozess — in
derselben Datei, die auch `setze_email()` hält, also die Funktion, die der Dienst aufruft.
Nichts hielte die nächste Änderung davon ab, den Seiteneffekt eine Ebene tiefer zu ziehen.

Mit eigenem Modul wird die Grenze zu zwei Sätzen, die ein Test prüfen kann:

> Genau eine Datei im Paket importiert `subprocess`, und sie heißt `oeffnen.py`.
> Wer `falzmarke.dienst` importiert und `email_setzen()` aufruft, hat `falzmarke.oeffnen`
> nicht in `sys.modules`.

Als eingestreuter Code in `cli.py` wäre keiner der beiden Sätze formulierbar.

## Warum das eine eigene Entscheidung braucht

0034 begründet selbst, warum diese Grenze eine geschriebene Fassung braucht: Der Senden-Knopf
„liegt als Bibliotheksaufruf herum, ist in zwanzig Zeilen erledigt und wird bei jedem zweiten
Vorschlag mitgedacht".

Für das Öffnen gilt dasselbe eine Stufe früher. Sobald das Werkzeug ein fremdes Programm starten
darf, steht die nächste Frage im Raum, und sie klingt jedes Mal vernünftig: *Wenn es Outlook
öffnen darf, warum legt es nicht gleich einen Entwurf an? Und wenn es einen Entwurf anlegen
darf — der Senden-Knopf ist doch nur noch eine Zeile.*

Die Kette ist deshalb verlockend, weil jedes Glied klein aussieht. Sie wird hier an ihrem ersten
Glied durchtrennt: **Dateiübergabe ja, Programmsteuerung nein.**

## Was gemessen wurde, bevor das entschieden wurde

Am 27.08.2026 (`docs/mailprogramme-2026-08-27.md`) wurde eine erzeugte `.eml` in Apple Mail 16.0,
Thunderbird 154.0 und Outlook für Mac 16.112.1 geöffnet. Alle drei zeigen ein **Lesefenster**:
Antworten, Weiterleiten, Archivieren — kein Senden-Knopf, keine editierbaren Empfängerfelder.
Die Gegenprobe mit `X-Unsent: 1`, der Konvention aus dem Outlook-Umfeld, ergab **keinen
Unterschied**.

Daraus folgt für dieses Flag eine Zusage und eine Nicht-Zusage:

- **Zugesagt:** Die Nachricht ist danach im Mailprogramm, mit Empfänger, Betreff, beiden Teilen
  und den Anhängen.
- **Nicht zugesagt:** dass sie dort als Entwurf erscheint. Der Weg zur ausgehenden Mail heißt
  weiterhin „Weiterleiten", und ihn geht ein Mensch.

Ein Werkzeug kann nicht zusagen, was das Programm des Nutzers entscheidet. Diese Grenze gehört
in die Doku, nicht in eine Hoffnung.

## Was daraus folgt

- **[#239](https://github.com/blitzsicht/falzmarke/issues/239)** baut `--oeffnen` an
  `falzmarke email` nach diesen fünf Punkten.
- **[#108](https://github.com/blitzsicht/falzmarke/issues/108) bleibt offen.** Die dort
  vorgeschlagene Brücke ist eine andere: ein Verweis in der `.html`-Vorschau für Web-Clients,
  die keine lokale `.eml` öffnen können. Sie trägt keine Anhänge und hat eine Längengrenze;
  dieses Flag trägt Anhänge und braucht dafür ein installiertes Programm. Beide behalten einen
  eigenen Zweck.
- **Kein `--oeffnen` am MCP-Dienst.** Ein Werkzeugaufruf über MCP kommt womöglich von einem
  anderen Rechner; dort ein Fenster zu öffnen wäre kein Dienst, sondern ein Übergriff.
- **Für `render` ist nichts entschieden.** `oeffnen.py` kennt nur einen Pfad und wäre für ein
  PDF ebenso brauchbar. Ob der Brief das bekommt, ist eine eigene Frage und wird hier nicht
  mitbeantwortet.

## Was diese Entscheidung nicht ist

Sie hebt 0034 nicht auf und weicht ihn nicht auf. Es entsteht kein Versandbefehl, kein SMTP,
keine Zustellung — die vier Festlegungen von 0034 gelten unverändert. Was sich ändert, ist
allein, dass der letzte Handgriff vor dem Mailprogramm nicht mehr von Hand getan werden muss.

Sie sagt auch nicht, dass Programmsteuerung technisch unmöglich wäre. Sie ist es nicht: Ein
Entwurf ließe sich per AppleScript anlegen. Sie sagt, dass ein Werkzeug, das die eigene Ausgabe
„auf den Millimeter geprüft" nennt, nicht nebenbei in fremden Programmen Zustand herstellen
sollte, den es nicht messen kann.

---

## Nachtrag 08.09.2026 — der Entwurf (#263)

### Was den Anlass gab

Am 08.09.2026 hat eine Sitzung außerhalb dieses Repos genau das getan, was hier verboten war:
Sie hat eine erzeugte Nachricht per AppleScript als Outlook-Entwurf geöffnet — mit Anhängen,
Tabelle und Signatur, Senden-Knopf vorhanden. Der Betreiber hat daraufhin entschieden, dass das
der Weg von `--oeffnen` wird.

Damit steht diese Entscheidung vor der Frage, für die sie geschrieben wurde. Sie hat sie nicht
überlebt — und das ist in Ordnung, solange die **Begründung** nicht mit verlorengeht.

### Die neue Fassung in einem Satz

> **Entwurf ja, Senden nie.**

`--oeffnen` legt auf macOS eine ausgehende Nachricht im Mailprogramm an und öffnet sie. Was
danach geschieht, entscheidet ein Mensch am Senden-Knopf.

### Was von den fünf Festlegungen bleibt

| Punkt | Stand |
|---|---|
| 1 — Ein Pfad, kein Programmname | **eingeschränkt.** Für einen Entwurf braucht es ein Skript je Programm; ein Programm, für das keines vorliegt, bekommt weiterhin nur die Datei. Gemessen ist genau eines: Outlook für Mac. |
| 2 — Opt-in, immer | **unverändert.** Ohne Flag passiert nichts. `FALZMARKE_ENTWURF=nie` schaltet zusätzlich nur den Entwurf ab und lässt die Dateiübergabe stehen. |
| 3 — Erst messen, dann öffnen | **unverändert.** Was `verify --email` nicht besteht, wird in kein Fenster gelegt. |
| 4 — Ein Fehlschlag entwertet die Datei nicht | **unverändert und wichtiger als vorher.** Kein Programm, keine Automations-Berechtigung, fremde Plattform: Der Befehl fällt auf die Dateiübergabe zurück, meldet den Grund und behält seinen Exit-Code. |
| 5 — Genau ein Modul startet fremde Programme | **unverändert.** Der Aufruf lebt weiter in `skill/falzmarke/oeffnen.py`. Was aus der `.eml` in den Entwurf wandert, liest `eml.entwurfsfelder()` — eine reine Funktion, die nichts startet. |

### Wo die Kette jetzt durchtrennt wird

Die alte Fassung fürchtete die Kette „öffnen → Entwurf → senden", weil jedes Glied klein
aussieht. Sie hat recht behalten: Das zweite Glied wurde verlangt, keine fünf Tage nach dem
ersten. Es liegt jetzt auf der anderen Seite der Grenze, und die Grenze liegt am dritten Glied.

Was sie trägt, ist diesmal nicht nur ein Satz in einem Dokument:

- **Kein Versandbefehl im Steuerskript.** `tests/test_oeffnen.py` misst das an jedem Skript in
  `ENTWURFSPROGRAMME`, `tests/test_skillpaket.py` am ganzen Paket.
- **Der Entwurf wird gegengelesen.** Das Skript zählt am fertigen Objekt Empfänger, Kopien und
  Anhänge; Python hält die Zählung gegen die Vorgabe. Ein Exit-Code von 0 belegt nur, dass das
  Skript durchlief — nicht, dass die Nachricht trägt, was sie tragen soll.
- **Nichts wird aus Eingaben zusammengesetzt.** Das Skript ist eine Konstante mit `on run argv`;
  Betreff, Rumpf, Adressen und Pfade kommen als Argumente. Derselbe Grund wie beim fehlenden
  `shell=True`: Was nicht geparst wird, muss nicht maskiert werden.

### Was das Werkzeug weiterhin nicht zusagt

- **Windows.** Weder COM noch `X-Unsent: 1` ist gemessen; dort bleibt es bei der Datei (#108).
- **Apple Mail.** Der `content` einer ausgehenden Nachricht nimmt dort keinen HTML-Rumpf an. Eine
  Nachricht, die ihre Auszeichnung unterwegs verliert, wäre schlechter als die Datei — also
  Datei, bis jemand es besser misst.
- **Was das Programm selbst hinzufügt.** Outlook setzt die Signatur des Kontos in den Entwurf.
  Steht im Profil eine eigene, steht sie zweimal darin. Der Befehl sagt das beim Anlegen; messen
  kann er es nicht, denn es geschieht nach seinem letzten Handgriff.
- **Kein Entwurfsweg im MCP-Dienst.** Unverändert: Ein Aufruf über MCP kommt womöglich von einem
  anderen Rechner.
