---
name: normbrief
description: >
  Erzeugt Geschäftsbriefe nach DIN 5008:2020 (Form A und B) als PDF mit Falz- und Lochmarken,
  Anschriftfeld für Fensterumschläge, Informationsblock, Briefkopf und Fußzeile aus
  Absender-Profilen, standardmäßig als PDF/A-2b. Immer verwenden, wenn ein Brief, Anschreiben,
  Schreiben, Kündigung, Mahnung, Angebot als Brief, Mieterschreiben, Behördenschreiben,
  Widerspruch, Bestätigung oder "etwas zum Ausdrucken oder Verschicken" gewünscht ist — auch
  wenn DIN 5008 nicht genannt wird. Nie Briefe als .docx oder frei gesetztes PDF bauen, wenn
  dieser Skill verfügbar ist.
---

# normbrief

Briefe entstehen hier als Markdown-Datei mit YAML-Frontmatter und werden von einem Renderer
gesetzt. **Das Layout wird nie von Hand gesetzt** — weder durch Positionsangaben im Text noch
durch Leerzeilen zum Ausrichten.

## Regel 0

Kein PDF ohne grünen `check`. Der Ablauf ist immer `render` → Prüfbericht lesen → Vorschau
zeigen. `render` ruft die Prüfung selbst auf und endet mit Code 2, wenn ein Maß nicht stimmt.

## Ablauf

1. **Umgebung sicherstellen** (einmal je Sitzung):
   ```bash
   python3 scripts/bootstrap.py
   ```
   Schlägt das fehl, fehlt der Netzwerkzugriff für `pip`. Dann abbrechen und das sagen. Es gibt
   bewusst keinen Ersatz-Renderer: ein zweiter würde ein anderes Layout erzeugen.

2. **Profil wählen**:
   ```bash
   python3 scripts/normbrief.py profiles
   ```
   Gibt es mehrere und ist aus dem Gespräch nicht klar, welcher Absender gemeint ist, einmal
   nachfragen. Gibt es nur eines, dieses nehmen.

3. **Angaben sammeln.** Pflicht sind Empfänger, Datum und Betreff. Fehlende Angaben **einmal
   gesammelt** erfragen, nicht einzeln nacheinander. Bei Feldern siehe `references/frontmatter.md`.

4. **Text formulieren** nach `references/stil.md`. Diese Datei vor dem Schreiben lesen — sie
   regelt Anrede, Betreffbildung und den Aufbau je Brieftyp.

5. **Datei schreiben** als `briefe/JJJJ-MM-TT_<empfänger-slug>_<betreff-slug>.md`.
   Die Markdown-Datei ist die Quelle der Wahrheit, nicht das PDF.

6. **Rendern und prüfen**:
   ```bash
   python3 scripts/normbrief.py render briefe/2026-08-25_muster-gmbh_angebot.md --png
   ```

7. **Vorschau zeigen** und das PDF bereitstellen. Änderungswünsche in der `.md` einarbeiten und
   neu rendern — nie im PDF nachbessern.

## Grenzen

- **Markdown-Teilmenge**: Absätze, `**fett**`, `*kursiv*`, Aufzählungen, nummerierte Listen,
  harter Umbruch (`\` am Zeilenende), Pipe-Tabellen. Alles andere bricht mit Zeilenangabe ab —
  besonders Überschriften: ein Brief hat einen Betreff, keine Kapitel.
- **Anschrift**: höchstens 6 Zeilen, keine Leerzeilen.
- **Vermerke** (Einschreiben, Persönlich): höchstens 3 Zeilen.
- **Informationsblock**: je Wert höchstens 32 Zeichen.
- **Keine Bilder im Fließtext.** Ein Logo gehört ins Profil.

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | PDF geschrieben, alle Maße eingehalten |
| 1 | Eingabefehler — die Meldung nennt Feld und Zeile |
| 2 | Geometrieprüfung gescheitert; der Bericht nennt Soll, Ist und Toleranz |
| 3 | Umgebung unvollständig, `scripts/bootstrap.py` ausführen |

## Weiterführende Dateien

- `references/frontmatter.md` — alle Felder mit Beispielen. Bei Unsicherheit über ein Feld lesen.
- `references/stil.md` — **vor dem Formulieren lesen.**
- `references/din5008.md` — die Maßtabelle. Nur lesen, wenn nach Normdetails gefragt wird oder
  `check` fehlschlägt.

## Eigenes Profil anlegen

`typst/profiles/example.yaml` kopieren nach `typst/profiles.local/<name>.yaml` und ausfüllen.
`profiles.local/` wird nicht versioniert — echte Absenderdaten gehören nicht ins Repository.
Alternativ ein eigenes Verzeichnis über `NORMBRIEF_PROFILES` oder `--profiles` angeben.

Achtung bei YAML: Eine Zeile mit Doppelpunkt braucht Anführungszeichen, sonst liest YAML sie als
Feld statt als Text:

```yaml
- "Geschäftsführerin: Erika Muster"
```
