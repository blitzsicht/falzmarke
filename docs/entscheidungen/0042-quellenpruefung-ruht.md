# 0042 — Die Quellenprüfung ruht, der erreichte Stand gilt

**Datum:** 22.09.2026 · **Status:** angenommen · **Betrifft:** den offenen Rest aus [#31](https://github.com/blitzsicht/falzmarke/issues/31)

## Entscheidung

Das Nachlesen der Quelle-Regel-Paare wird **eingestellt**. Der am 22.09.2026 erreichte Stand —
17 von 44 Paaren nachgelesen, 27 offen — gilt als ausreichend. Die verbleibenden 27 Paare
werden nicht weiter geprüft.

Die Wächter bleiben: `UNGEPRUEFTE_PAARE` darf nur sinken, `SCHWEIGENDE_QUELLEN` hält den Stand
fest, und wer eine Quelle neu einträgt, sagt weiterhin, wo sie die Regel hergibt. Was ruht, ist
das Abarbeiten der Liste — nicht die Sorgfalt bei neuen Einträgen.

## Warum

Nach zwei Portionen ist das Bild klar genug, um es zu beenden. Entscheidend ist eine Eigenschaft
der Prüfung selbst: **Ein ungeprüftes Paar wird bereits mitgezählt.** `unabhaengige_belege()`
nimmt jede Quelle mit `zaehlt: voll`, solange sie nicht ausdrücklich als schweigend vermerkt
ist. Nachlesen kann eine Regel deshalb nur bestätigen oder herabstufen — aufwerten nie.

Damit hängt der Ertrag allein daran, ob die Quelle überhaupt eine Belegsgruppe tragen kann.
Gemessen am 22.09.2026:

| Quelle | offene Paare | kann eine Gruppe tragen? |
|---|---:|---|
| `massskizze_b` | 0 — **abgearbeitet** | ja |
| `wikipedia` | 0 — **abgearbeitet** | ja |
| `onlineprinters` | 10 | ja, aber dieselbe Gruppe wie `massskizze_b` — also keine zweite |
| `letter_pro` | 15 | nein (`zaehlt: einzeln`) |
| `koma_script` | 1 | nein (`zaehlt: einzeln`) |
| `massskizze_a` | 1 | ja |

Abgearbeitet sind genau die beiden Quellen, deren Prüfung etwas bewegen konnte. Von den 27
verbliebenen Paaren liegen 16 bei Quellen, die gar keine Gruppe tragen, und 10 bei einer
Quelle, die keine **zweite** liefern kann. Bleibt ein einziges Paar mit offenem Ertrag
(`massskizze_a` an `geometrie.form_a.masse`).

Dazu kommt, dass die ganze Quellenlage ein Provisorium ist: Der Normabgleich
([#12](https://github.com/blitzsicht/falzmarke/issues/12)) ersetzt `herkunft:` durch
Fundstellen der Norm, und die Quellenliste entfällt dann vollständig
([Prüfliste](../normabgleich-pruefliste.md)). Jede weitere Stunde hier ist Arbeit an etwas, das
abgelöst werden soll.

## Was das kostet

Das wird hier nicht kleingeredet, weil es der Grund ist, warum die Frage überhaupt gestellt
wurde. Gemessen am 22.09.2026:

- **10 Regeln mit Wirkung `fehler`** hängen an mindestens einem ungeprüften Paar. Sie dürfen
  einen Lauf scheitern lassen, auf Grund, in den niemand gesehen hat.
- Schwiegen alle 27 verbliebenen Quellen, verlören **10 Regeln** ihre Stufe.

Das ist der ungünstigste Fall und nicht der erwartete — dass eine bemaßte Zeichnung zum
Seitenformat schweigt, ist unwahrscheinlich. Aber es ist die Größenordnung dessen, was
ungeprüft bleibt, und sie wird bewusst in Kauf genommen.

Zwei der 17 geprüften Paare zeigen, dass das Risiko real ist: `massskizze_b` schweigt zu
`text.vermerke_max_3`, und `onlineprinters` schwieg am 27.08.2026 in zehn von zehn Fällen —
drei Regeln fielen damals von Fehler auf Warnung.

## Was diese Entscheidung nicht ist

- Sie ändert **nichts** an den gesperrten Wörtern. Kein „normgerecht", kein „DIN-konform",
  keine Zertifizierung — `tests/test_textkanon.py` hält das fest.
- Sie hebt den Normabgleich **nicht** auf. #12 bleibt vorgesehen; er ist der Weg, auf dem die
  Quellenlage abgelöst wird, nicht ergänzt.
- Sie stuft **keine Regel um**. Was heute Fehler ist, bleibt Fehler; was Warnung ist, bleibt
  Warnung.
- Sie schließt die offenen Befunde **nicht**.
  [#344](https://github.com/blitzsicht/falzmarke/issues/344) (Einstufung von
  `text.anschrift_ohne_leerzeilen`) und
  [#345](https://github.com/blitzsicht/falzmarke/issues/345) (50 mm gegen 45 mm bei Form B)
  bleiben offen. Beide sind Befunde, keine Listenarbeit, und #345 ist ohnehin erst am Normtext
  auflösbar.

## Folgen

- **[`docs/offene-quellenpruefungen.md`](../offene-quellenpruefungen.md) bleibt bestehen und
  wird als ruhend geführt.** Sie ist der Einstiegspunkt, falls die Arbeit wieder aufgenommen
  wird — mit der Reihenfolge, die aus der Messung folgt, und mit dem, was je Portion auf dem
  Spiel steht. Erzeugt wird sie von `scripts/offene_paare.py`.
- **Die Schranke bleibt ein Wächter, kein Auftrag.** `UNGEPRUEFTE_PAARE = 27` verhindert, dass
  eine neu eingetragene Quelle ohne Fundstelle durchrutscht. Dass die Zahl nicht mehr sinkt,
  ist ab jetzt der Normalfall und kein Rückstand.
- **Wieder aufzunehmen wäre sie bei einem konkreten Anlass**, nicht nach Plan: wenn eine Regel
  in der Praxis falsch meldet, wenn eine neue Quelle hinzukommt, oder wenn #12 tatsächlich
  ansteht — dann allerdings als Normabgleich und nicht als Sekundärquellenarbeit.

## Nebenbefund: ADR 0032 und #12 widersprechen sich

Beim Schreiben dieser Entscheidung aufgefallen und hier nur festgehalten, nicht entschieden:
[ADR 0032](0032-verbreitung-vor-normabgleich.md) sagt unter „Folgen" ausdrücklich *„Die
100-Sterne-Bedingung an #12 entfällt."* Der Vorgang #12 trägt dagegen seit dem 20.09.2026 den
Abschnitt „Stand der Schwelle" mit dem Satz *„Die Schwelle bleibt"*.

Die Wiedereinführung ist in keiner ADR abgelegt. Nach der Regel im
[README](README.md) — „Eine Entscheidung wird nicht überschrieben — sie wird von einer späteren
abgelöst" — fehlt hier die ablösende Entscheidung.
