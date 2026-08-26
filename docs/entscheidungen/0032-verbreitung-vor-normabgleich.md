# 0032 — Verbreitung darf dem Normabgleich vorausgehen

**Datum:** 26.08.2026 · **Status:** angenommen · **Löst auf:** die offene Spannung in [ADR 0030](0030-reihenfolge-der-roadmap.md)

## Entscheidung

falzmarke darf verbreitet und bekannt gemacht werden, **bevor** der Abgleich mit dem
Originaltext der DIN 5008:2020-03 vorliegt — unter einer Bedingung: Die Quellenlage bleibt
überall ausgewiesen, wo jemand auf das Werkzeug trifft.

Damit werden die Kanäle frei: Paketveröffentlichung, MCP-Server, Aktion für andere
Repositories, Website. Der Meilenstein „Vor Verbreitung" sperrt sie nicht mehr.

## Warum

ADR 0030 hat einen Kreislauf benannt und ausdrücklich **nicht** entschieden: Der Meilenstein
„Vor Verbreitung" sperrte die Bewerbung bis zum Normabgleich; der Normabgleich wartete auf 100
Sterne im Repository; Sterne entstehen durch Verbreitung. Stand bei dieser Entscheidung: **0
Sterne.** Die Bedingung war damit nicht schwer erfüllbar, sondern unerfüllbar — und ein
Werkzeug, das niemand benutzt, schützt niemanden.

Die Abwägung dagegen ist real und wird hier nicht kleingeredet: Wer sich auf ein Maß verlässt
und eine Frist verpasst, hat einen Schaden, den kein Haftungsausschluss zurückholt. Sie fällt
trotzdem für die Verbreitung aus, weil die Ehrlichkeit über den Belegstand hier **erzwungen**
ist und nicht auf gutem Willen beruht:

- `tests/test_textkanon.py` verlangt in `README.md` und `docs/recht.md` den Satz, dass der
  Abgleich mit dem Originaltext aussteht, und den Satz, dass Regeln aus einzelnen Quellen nur
  als Warnung wirken.
- Derselbe Test sperrt die Wörter „normgerecht", „DIN-konform", „normkonform" und
  „zertifiziert" — auch in gebeugter Form, mit Ausnahme verneinender Verwendungen.
- `skill/falzmarke/regeln/din5008.yaml` führt zu jeder Regel ihre Herkunft, und
  `tests/test_quellenlage.py` lässt nur mehrfach belegte Regeln als Fehler wirken. Stand heute:
  16 Regeln wirken als Fehler, 19 als Warnung, eine wird nicht geprüft.

Das ist mehr Offenlegung, als ein Nutzer bei vergleichbaren Werkzeugen bekommt. Die Zurückhaltung
im Wortlaut bleibt zugleich das Unterscheidungsmerkmal: In einem Feld, in dem „DIN-konform"
behauptet wird, ist der Verzicht darauf die Aussage.

## Was diese Entscheidung nicht ist

- Sie entscheidet **nicht**, ob der Normabgleich gemacht wird. Er bleibt vorgesehen (#12); nur
  seine Stellung in der Reihenfolge ändert sich.
- Sie ändert **nichts** an den gesperrten Wörtern. Die bleiben gesperrt, bis der Abgleich
  vorliegt — die Verbreitung erkauft keine stärkere Behauptung.
- Sie hebt die Belegarbeit **nicht** auf. #16, #18, #31, #34 und #35 behalten ihren Rang.

## Folgen

- **Die 100-Sterne-Bedingung an #12 entfällt.** Sie war die Ursache des Kreislaufs. Wann der
  Abgleich stattfindet, entscheidet der Maintainer ohne diese Schwelle.
- **Der Meilenstein „Vor Verbreitung" bekommt einen neuen Zuschnitt.** Er hieß so, weil er die
  Bewerbung sperrte. Was ihn jetzt füllt, ist Belegarbeit, die vor einer *starken Behauptung*
  stehen muss — nicht vor der Verbreitung.
- **Die Quellenlage muss dorthin, wo sie ohne README ankommt.** Das ist die schwächste Stelle
  dieser Entscheidung: Wer über ein Verzeichnis, einen Paketindex oder eine Skill-Beschreibung
  auf falzmarke trifft, sieht das README oft nie. Solange die Warnstufe nur dort steht, schützt
  sie den Herausgeber und nicht den Nutzer. Nachzuziehen in Paketbeschreibung, Skill-Beschreibung
  und Verzeichniseinträgen — als eigenes Issue geführt und Voraussetzung für den jeweiligen Kanal.
