# Befehle

Alle Befehle in einer Übersicht. Der Einstieg steht in der [README](../README.md).

```
falzmarke lint        BRIEF.md [--json]
falzmarke render      BRIEF.md [-o AUS.pdf] [--png] [--no-pdfa] [--pdfua] [--verbose]
falzmarke verify      AUS.pdf [--form A|B] [--json] [--verbose]
falzmarke verify      NACHRICHT.eml --email [--json] [--verbose]
falzmarke email       NACHRICHT.md [-o STAMM] [--html] [--txt] [--mit-quelle] [--verbose]
falzmarke preview     BRIEF.md [-o AUS.png] [--ppi 120]
falzmarke init        ZIEL.md --profil NAME [--empfaenger "Zeile|Zeile"] [--betreff "..."]
falzmarke init-profil NAME [--ziel VERZEICHNIS]
falzmarke profiles
falzmarke pack        --profil NAME [-o ZIEL.skill]
falzmarke --version
```

Aus einem Clone ohne Installation: `python3 skill/scripts/falzmarke.py …` — dasselbe Programm,
nur ein anderer Aufrufweg.

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
