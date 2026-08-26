---
name: falzmarke
description: >
  Erzeugt Geschäftsbriefe nach DIN 5008:2020 (Form A und B) als PDF mit Falz- und Lochmarken,
  Anschriftfeld für Fensterumschläge, Informationsblock, Briefkopf und Fußzeile aus
  Absender-Profilen, standardmäßig als PDF/A-2b. Immer verwenden, wenn ein Brief, Anschreiben,
  Schreiben, Kündigung, Mahnung, Angebot als Brief, Mieterschreiben, Behördenschreiben,
  Widerspruch, Bestätigung oder "etwas zum Ausdrucken oder Verschicken" gewünscht ist — auch
  wenn DIN 5008 nicht genannt wird. Nie Briefe als .docx oder frei gesetztes PDF bauen, wenn
  dieser Skill verfügbar ist.
  Die Sollwerte stammen aus Sekundärquellen; der Abgleich mit dem Originaltext der DIN 5008:2020-03 einschließlich Berichtigung 1:2020-07 steht aus, und Regeln aus einzelnen Quellen wirken nur als Warnung.
---

# falzmarke

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
   python3 scripts/falzmarke.py profiles
   ```
   Gibt es mehrere und ist aus dem Gespräch nicht klar, welcher Absender gemeint ist, einmal
   nachfragen. Gibt es nur eines, dieses nehmen.

3. **Angaben sammeln.** Pflicht sind Empfänger, Datum und Betreff. Fehlende Angaben **einmal
   gesammelt** erfragen, nicht einzeln nacheinander. Bei Feldern siehe `references/frontmatter.md`.

   **Unterschrift:** Trägt das Profil eine `signatur:`, erscheint sie auf jedem Brief. Wird
   der Brief von jemand anderem gezeichnet (`unterzeichner: i. A. …`) oder soll er von Hand
   unterschrieben werden, gehört `signatur: keine` ins Frontmatter — sonst steht die fremde
   Unterschrift darunter. Eine andere Unterschrift: `signatur: <datei>` neben dem Brief.

4. **Text formulieren** nach `references/stil.md`. Diese Datei vor dem Schreiben lesen — sie
   regelt Anrede, Betreffbildung und den Aufbau je Brieftyp.

5. **Datei schreiben** als `briefe/JJJJ-MM-TT_<empfänger-slug>_<betreff-slug>.md`.
   Die Markdown-Datei ist die Quelle der Wahrheit, nicht das PDF.

6. **Rendern und prüfen**:
   ```bash
   python3 scripts/falzmarke.py render briefe/2026-08-25_muster-gmbh_angebot.md --png
   ```

7. **Vorschau zeigen** und das PDF bereitstellen. Änderungswünsche in der `.md` einarbeiten und
   neu rendern — nie im PDF nachbessern.

## Grenzen

- **Markdown-Teilmenge** (`references/markdown.md`): Absätze, `**fett**`, `*kursiv*`,
  Aufzählungen, nummerierte Listen, harter Umbruch (`\` am Zeilenende), Pipe-Tabellen.
  Alles andere bricht mit Zeilenangabe ab —
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
  Ein Feld, das dort nicht steht, lehnt `lint` ab — es gibt keine stillen Zusatzfelder.
- `references/markdown.md` — **was im Brieftext erlaubt ist.** Vor dem ersten Brief lesen:
  Überschriften, Links, Bilder, Code und HTML brechen ab, und der Typografie-Pass setzt
  geschützte Leerzeichen von selbst — von Hand eingefügte sind überflüssig.
- `references/stil.md` — **vor dem Formulieren lesen.**
- `references/din5008.md` — die Maßtabelle. Nur lesen, wenn nach Normdetails gefragt wird oder
  `check` fehlschlägt.

## Profil auf claude.ai

Dort überlebt kein Verzeichnis den nächsten Chat: Ein Profil unter
`~/.config/falzmarke/profiles/` ist im zweiten Chat weg, und das Release-Asset enthält nur das
Beispiel. Zwei Wege, damit der Absender bleibt:

1. **Skill mit eingebackenem Profil** — einmal am eigenen Rechner:
   ```bash
   python3 scripts/falzmarke.py pack --profil meinefirma -o falzmarke-meinefirma.skill
   ```
   Dieses Zip statt des Release-Assets hochladen. Es enthält Absenderdaten und gehört nicht in ein
   öffentliches Repository.
2. **Profil im Brief** — `profil:` nimmt statt eines Namens auch die Felder selbst. Dann trägt der
   Brief alles Nötige und funktioniert überall.

Hochgeladene Dateien sucht falzmarke auch unter `/mnt/user-data/uploads`; Brief und Profil lassen
sich also zusammen in einen Chat legen.

## Wenn es bricht

| Exit | Was zu tun ist |
|---|---|
| 1 | Eingabefehler. Die Meldung nennt Feld und Zeile — dort korrigieren und erneut `lint`. |
| 2 | Verifikation. Den Bericht wörtlich weitergeben. **Nach einem Versuch aufhören**, nicht am Layout herumprobieren. |
| 3 | Umgebung. `python3 scripts/bootstrap.py`, danach abbrechen, wenn es wieder scheitert. |
| 4 | Renderer. Das ist ein Fehler im Werkzeug — als Issue melden, mit der `.md`. |

## Eigenes Profil anlegen

```bash
python3 scripts/falzmarke.py init-profil meinefirma
```

Das legt eine ausgefüllte Vorlage unter `~/.config/falzmarke/profiles/meinefirma.yaml` an.
Die Pfade in diesem Dokument sind relativ zum Skill-Ordner; auf claude.ai liegt er unter
`/mnt/skills/user/falzmarke`.
**Dieser Ort überlebt Aktualisierungen des Skills** — ein Profil innerhalb des Skill-Ordners tut
das nicht: wird der Skill ersetzt, sind die Absender weg und keiner der alten Briefe lässt sich
mehr setzen.

Gesucht wird in dieser Reihenfolge:

1. `--profiles VERZEICHNIS`
2. `FALZMARKE_PROFILES` (mehrere Pfade mit Doppelpunkt getrennt)
3. `./profiles/` neben den Briefen — für Profile, die zu einem Vorgang gehören
4. `~/.config/falzmarke/profiles/` — die eigenen Absender
5. die mitgelieferten Beispiele

Achtung bei YAML: Eine Zeile mit Doppelpunkt braucht Anführungszeichen, sonst liest YAML sie als
Feld statt als Text:

```yaml
- "Geschäftsführerin: Erika Muster"
```
