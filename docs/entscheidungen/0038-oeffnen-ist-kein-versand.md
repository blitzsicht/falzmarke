# 0038 — Öffnen ist kein Versand

**Datum:** 04.09.2026 · **Status:** angenommen · **Löst:** [#239](https://github.com/blitzsicht/falzmarke/issues/239)

## Entscheidung

falzmarke darf eine fertige Datei **dem Betriebssystem übergeben** — einen Pfad an `open`,
`xdg-open` oder `os.startfile`, mehr nicht. Was damit geschieht, entscheidet die Zuordnung des
Systems, nicht das Werkzeug.

Es darf **kein Mailprogramm steuern**: kein AppleScript, kein COM, kein Anlegen von Entwürfen,
kein Ausfüllen von Feldern, kein Auslösen von Aktionen. Und kein Versand, wie schon in
[0034](0034-email-ist-ausgabe.md) festgelegt.

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
