# Urkunden, die absichtlich falsch sind

Wie die Briefe unter `tests/fixtures/satzspiegel/` gehören diese Dateien
**nicht** nach `examples/urkunde/`: Dort wird jede Urkunde in der CI gesetzt
und muss bestehen.

Hier sind sie Prüfgegenstand. `tests/test_gegenbeweis.py` verlangt, dass die
genannte Prüfung an ihnen **anschlägt** — wird eine von ihnen grün, ist nicht
die Urkunde in Ordnung, dann misst die Prüfung nicht mehr.

| Datei | Was sie auslöst |
|---|---|
| `zwei-seiten-bei-einer.md` | `seiten_max: 1`, aber Text für zwei Seiten: `Seitenzahl` schlägt an |
