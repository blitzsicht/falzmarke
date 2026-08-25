# Prüfliste für den Normabgleich

Diese Liste wird **von Hand am gekauften Normtext** ausgefüllt. Sie ist der einzige Weg, wie die
DIN 5008:2020-03 in dieses Projekt einfließt.

## Regel: kein Wortlaut

Übertragen werden **Fundstellen** und **Zahlenwerte** — nie Text, nie Tabellen, nie Abbildungen.
In die Spalte „Fundstelle" gehört `Abschnitt 5.2` oder `Tabelle 3`, nicht das, was dort steht.
Ein abgetippter Satz aus der Norm im Repository wäre eine Urheberrechtsverletzung und macht die
Datei unbrauchbar.

## Wie es abläuft

1. Praxispaket besorgen: **DIN 5008:2020-03 Praxispaket**, ISBN 978-3-410-29877-9, 58 €.
   Im Buchhandel portofrei, auch über [DIN Media](https://www.dinmedia.de).
2. Diese Liste ausfüllen: je Regel die Fundstelle, den Wert laut Norm, und ob er mit unserem
   übereinstimmt.
3. Die ausgefüllte Liste ins Repository (sie enthält dann Fundstellen, keinen Text).
4. Claude Code aktualisiert `skill/falzmarke/regeln/din5008.yaml`: `herkunft:` wird zu
   `DIN 5008:2020-03, Abschnitt …`, die Quellenliste entfällt, herabgestufte Regeln steigen zu
   Fehlern auf.
5. `python3 scripts/quellenlage.py` erzeugt den Doku-Abschnitt neu.
6. Der Satz zur ausstehenden Prüfung verschwindet aus README, `docs/recht.md` und
   `tests/test_textkanon.py`.

## Spalten

- **Regel** — die id aus `din5008.yaml`
- **unser Wert** — was falzmarke heute annimmt
- **Fundstelle** — Abschnitt/Tabelle in der Norm. *Kein Wortlaut.*
- **Wert laut Norm** — die Zahl, sonst nichts
- **stimmt?** — ja · nein · Norm sagt dazu nichts

---

## Geometrie

| Regel | unser Wert | Fundstelle | Wert laut Norm | stimmt? |
|---|---|---|---|---|
| `geometrie.seitenformat` | A4, 210 × 297 mm | | | |
| `geometrie.form_b.briefkopf` | 45 mm | | | |
| `geometrie.form_b.anschriftfeld` | 85 × 45 mm, links 20 mm, Text ab 25 mm | | | |
| `geometrie.form_b.zonen` | 5 / 12,7 / 27,3 mm | | | |
| `geometrie.form_b.infoblock` | x = 125 mm, Breite 75 mm, Oberkante 50 mm | | | |
| `geometrie.form_b.falzmarken` | 105 und 210 mm | | | |
| `geometrie.form_a.masse` | Briefkopf 27 mm, Falzmarken 87 / 192 mm | | | |
| `geometrie.lochmarke` | 148,5 mm | | | |
| `geometrie.seitenraender` | links 25, rechts 20, Textbreite 165 mm | | | |
| `geometrie.grundzeilenhoehe` | 4,23 mm (12 pt) | | | |
| `geometrie.betreffabstand` | 2 Leerzeilen = 8,46 mm | | | |
| `geometrie.infoblock_mindesthoehe` | mindestens 40 mm | | | |
| `geometrie.markenlaenge` | 2,5–5 mm, Heftrand bis 20 mm | | | |
| `geometrie.schriftgroessen` | Text ≥ 10 pt, Anschrift/Block ≥ 8 pt | | | |

**Form A ist der schwächste Punkt.** Für Form B gibt es eine bemaßte Zeichnung; für Form A stützt
sich falzmarke auf eine einzige Implementierung. Hier zuerst nachsehen.

## Aufbau des Textteils

| Regel | unser Wert | Fundstelle | Wert laut Norm | stimmt? |
|---|---|---|---|---|
| `text.anrede_komma` | Anrede mit Komma, Text darunter klein | | | |
| `text.gruss_ohne_komma` | Grußformel ohne Komma | | | |
| `text.anlagen_ohne_doppelpunkt` | „Anlagen" ohne Doppelpunkt | | | |
| `text.folgeseiten` | Seitenzahl, Kopfzeile empfohlen | | | |
| `text.anschrift_ohne_leerzeilen` | bis 6 Zeilen, keine Leerzeilen | | | |
| `text.vermerke_max_3` | bis 3 Zeilen | | | |

## Schreibweisen

| Regel | unser Wert | Fundstelle | Wert laut Norm | stimmt? |
|---|---|---|---|---|
| `schreibweise.datum` | `25. August 2026` / `2026-08-25` | | | |
| `schreibweise.abkuerzungen` | `z. B.` mit geschütztem Leerzeichen | | | |
| `schreibweise.telefon` | `0941 620-9800` | | | |
| `schreibweise.zahlengliederung` | Dreiergruppen | | | |
| `schreibweise.iban` | Vierergruppen | | | |
| `schreibweise.postfach` | Zweiergruppen von rechts | | | |
| `schreibweise.uhrzeit` | `11:30 Uhr` | | | |
| `schreibweise.geldbetrag` | `1.234,56 EUR` | | | |
| `schreibweise.auslandsanschrift` | Ort und Land in Großbuchstaben | | | |
| `schreibweise.akademischer_grad` | Grad vor dem Namen | | | |
| `schreibweise.einheiten` | Zahl und Einheit nicht trennen | | | |

## Offene Fragen an den Normtext

Punkte, an denen unsere Sekundärquellen schweigen oder sich widersprechen:

1. Ist die Mindesthöhe des Informationsblocks (40 mm) eine Vorgabe der Norm oder eine Konvention?
2. Nennt die Norm eine Länge für Falz- und Lochmarken, oder nur ihre Position?
3. Gibt es eine Vorgabe zur Zeichenzahl des Betreffs — oder nur die Begrenzung auf zwei Zeilen?
4. Gilt die Zusammenfassung „Zusatz- und Vermerkzone mit integrierter Rücksendeangabe" (17,7 mm)
   oder die feinere Aufteilung 5 + 12,7 mm?
5. Wie behandelt die Norm den akademischen Grad — Vorgabe oder Empfehlung?
