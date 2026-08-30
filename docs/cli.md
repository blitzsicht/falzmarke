# Befehle

Alle Befehle in einer Übersicht. Der Einstieg steht in der [README](../README.md).

```
falzmarke lint        BRIEF.md [--json]
falzmarke render      BRIEF.md [-o AUS.pdf] [--png] [--no-pdfa] [--pdfua] [--verbose]
falzmarke verify      AUS.pdf [--form A|B] [--json] [--verbose]
falzmarke verify      NACHRICHT.eml --email [--json] [--verbose]
falzmarke email       NACHRICHT.md [-o STAMM] [--html] [--txt] [--mit-quelle] [--verbose]
falzmarke serie       VORLAGE.md --daten DATEN.csv --ziel ORDNER/ [--benennen SPALTE] [--sammel]
falzmarke preview     BRIEF.md [-o AUS.png] [--ppi 120]
falzmarke init        ZIEL.md --profil NAME [--empfaenger "Zeile|Zeile"] [--betreff "..."]
falzmarke init-profil NAME [--ziel VERZEICHNIS]
falzmarke profiles
falzmarke pack        --profil NAME [-o ZIEL.skill]
falzmarke --version
```

Aus einem Clone ohne Installation: `python3 skill/scripts/falzmarke.py …` — dasselbe Programm,
nur ein anderer Aufrufweg.

## Serienbrief

```
falzmarke serie vorlage.md --daten empfaenger.csv --ziel briefe/ --benennen nachname
```

Die Vorlage ist ein gewöhnlicher Brief mit **`{{spalte}}`** an den Stellen, die aus den Daten
kommen — im Frontmatter wie im Text:

```markdown
---
profil: example
empfaenger:
  - "{{firma}}"
  - "{{strasse}}"
  - "{{plz}} {{ort}}"
datum: 2026-08-29
betreff: Ihre Anfrage vom 14. August 2026
anrede: "Sehr geehrte {{anrede}} {{nachname}},"
---
vielen Dank für Ihre Anfrage. Wir haben sie unter {{auftrag}} erfasst.
```

Die Datenquelle ist `.csv` oder `.json` — erkannt an der Endung, nicht am Inhalt. Eine CSV wird
mit `utf-8-sig` gelesen, damit die Byte-Order-Mark aus Excel nicht in den ersten Spaltennamen
gerät.

| Option | |
|---|---|
| `--benennen SPALTE` | woraus der Dateiname gebildet wird; die laufende Nummer steht ohnehin davor |
| `--sammel` | zusätzlich alle Briefe in einer Datei, für den Druck |

### Ein Wert wird nie zu Markup

Was aus der Datenquelle kommt, ist Text und bleibt Text. Ein Empfänger namens
`Müller & Söhne *GmbH*` steht mit Sternchen im Brief, kein Kursivsatz; ein Auftrag `# 2026-0815`
wird keine Überschrift.

Das ist kein Zufall, sondern der Grund für den Weg: Ersetzt wird **nach** dem Parsen, im
geprüften Baum. Was dort eingesetzt wird, läuft nie wieder durch den Parser — dieselbe
Überlegung wie beim Typst-Emitter, der Text als Zeichenkette ausgibt statt als Markup. Eine
Maskierliste (`*`, `_`, `#`, `[`, `` ` ``) wäre einfacher und irgendwann unvollständig.

Aus demselben Grund läuft die Typografie nicht über den Wert: Aus `Nord -- Süd` wird kein
Halbgeviertstrich. Im Vorlagentext greift sie weiterhin.

### Ein Datensatz, ein Ergebnis

Ein Datensatz, der nicht durchgeht, bricht **diesen** ab und nicht die Serie:

```
FEHL  Zeile 3: empfaenger: Leerzeilen sind im Anschriftfeld nicht zulässig.
serie: 2/3 Briefe geschrieben
```

Die Zeilennummer ist die der Datenquelle, inklusive Kopfzeile — die Zeile, die man dort sucht.
Der Rückgabewert ist 1, sobald ein Satz fehlt; die übrigen Briefe liegen trotzdem im Zielordner.

Was den **ganzen** Lauf anhält, ist ein Fehler an der Vorlage oder der Datenquelle: ein
Platzhalter ohne Spalte, eine fehlende Kopfzeile. Der beträfe jeden Datensatz, und
zweihundertmal dieselbe Meldung ist keine Hilfe. Die Gegenrichtung ist ausdrücklich kein Fehler:
Eine Spalte, auf die kein Platzhalter zeigt, ist bei einer Adressliste der Normalfall.

## Wie die Befehle zusammenhängen

```
brief.md
   ↓ lint      Eingabe prüfen, ohne zu setzen
   ↓ render    setzen — ruft lint vorweg und verify danach selbst auf
brief.pdf/a
   ↓ verify    ein fertiges PDF nachmessen, auch ein fremdes

nachricht.md  (typ: email)
   ↓ lint      dieselbe Vorprüfung, andere Felder
   ↓ email     .eml setzen — ruft lint vorweg und verify --email danach auf
nachricht.eml
   ↓ verify --email   eine fertige Nachricht nachmessen, auch eine fremde
```

`email` und `render` schließen einander aus, und zwar an der Datei: `typ: email` lässt `render`
mit Code 1 abbrechen, ein Schreiben ohne `typ: email` ebenso `email`. Die Meldung nennt beide
Male, welcher Befehl der richtige wäre.

`render` prüft die Eingabe vorweg und misst das Ergebnis nach. **Ein Eingabefehler kostet
deshalb keinen Renderlauf** — er endet mit Code 1, bevor Typst überhaupt startet.

`verify` funktioniert auch auf PDFs, die nicht von falzmarke stammen. Ohne `--form` erkennt es
die Form an den Falzmarken.

`email` schreibt die `.eml`; `--html` und `--txt` behalten zusätzlich die Vorschau und den
Textteil. **Versendet wird nichts** — es gibt keinen Versandbefehl und keine Option, die sendet
(ADR 0034). Einzelheiten in [Die E-Mail-Fassung](email.md).

## Einen bestehenden Brief zurücklesen

```bash
falzmarke einlesen alter-brief.pdf -o neu.md
falzmarke einlesen alter-brief.pdf --json
```

Erzeugt aus einem fertigen PDF ein falzmarke-Markdown — **als Gerüst mit benannten Lücken, nicht
als fertigen Brief.** Ein Frontmatter-Feld wird nur gesetzt, wenn es belegbar ist; sonst steht es
als Kommentar mit Begründung im Gerüst:

```yaml
# empfaenger: <nicht erkannt: keine Falz- und Lochmarken im Heftrand — das Blatt
#              trägt kein DIN-5008-Raster, Positionen sagen hier nichts>
#   Kandidat: Steuerberatung Dr. Ledermann
```

Ein **Kandidat ist kein Wert.** Er steht im Kommentar, weil er so aussieht wie einer — entschieden
wird er von dem, der den Brief liest. Der Grund dafür ist keine Vorsicht um ihrer selbst willen:
Ein falsch erkannter Empfänger fällt erst im gedruckten Brief auf, und dann beim Falschen.

Wie viel erkannt wird, hängt am Raster: Trägt das Blatt Falz- und Lochmarken, sind seine
Positionen aussagekräftig und Empfänger, Datum, Betreff und Anrede werden gelesen. Ohne sie —
also bei den meisten alten Briefen aus Word — kommt der Text mit, und die Felder bleiben Lücken
mit Kandidaten.

`profil` ist **immer** eine Lücke, auch bei einem Brief, den falzmarke selbst gesetzt hat: Das
Absenderprofil ist eine lokale Datei und steht in keinem PDF.

Der Befehl endet mit `0`, auch wenn Lücken bleiben — sie sind das erwartete Ergebnis, kein
Fehler. Für die maschinelle Auswertung gibt es `--json`.

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | PDF geschrieben, alle Maße eingehalten |
| 1 | Eingabefehler — mit Feldname und Zeilennummer |
| 2 | Geometrieprüfung gescheitert — mit Soll, Ist und Toleranz |
| 3 | Umgebung unvollständig |
| 4 | Fehler im Renderer — bitte als Issue melden |

Die Codes sind für Automatisierung gedacht: `lint` und `verify` geben mit `--json` denselben
Befund maschinenlesbar aus.

## Was geprüft wird

Seitenformat, Falz- und Lochmarken, alle vier Zonen des Anschriftfelds, Position und Breite des
Informationsblocks, die Betreffposition relativ zum tiefer reichenden der beiden Blöcke,
Satzspiegel, die Zeilenabstände im 12-pt-Raster, eingebettete Schriften, die PDF/A-Kennzeichnung
und die Folgeseiten.

Bei einer Nachricht: der MIME-Aufbau und die Reihenfolge der Alternativen, `format=flowed` samt
Space-Stuffing, die Signaturtrennzeile, dass Text- und HTML-Teil dasselbe sagen, dass im HTML
weder Skript noch externes Stylesheet noch Zählpixel steht, und die Grenzen für Zeilenlänge und
Anhänge.

Woher die Sollwerte stammen und wie belastbar sie sind, steht in
[`docs/recht.md`](recht.md) und in der
[Quellenlage je Regel](../skill/references/din5008.md#quellenlage-je-regel).

## Verwandt

- [Datenvertrag: das Frontmatter](../skill/references/frontmatter.md) — alle Felder
- [falzmarke-Markdown](../skill/references/markdown.md) — was im Brieftext erlaubt ist
- [Absenderprofile](profiles.md)
- [Die E-Mail-Fassung](email.md) — Aufbau der `.eml`, Teile, Grenzen
