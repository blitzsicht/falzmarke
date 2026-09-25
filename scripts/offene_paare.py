#!/usr/bin/env python3
"""Schreibt docs/offene-quellenpruefungen.md aus den Regeldaten.

Die Liste sagt, welche Quelle-Regel-Paare noch niemand nachgelesen hat und in
welcher Reihenfolge es sich lohnte, falls die Arbeit wieder aufgenommen wird —
sie ruht seit ADR 0042 (22.09.2026). Sie wird **erzeugt**, nicht gepflegt: Beim
ersten und zweiten Mal war sie von Hand geschrieben, und beide Male standen
falsche Zahlen darin — einmal eine veraltete Summe, einmal eine Folgenspalte,
die `zaehlt: einzeln` nicht mitzählte und deshalb Regeln fallen sah, die
bleiben.

    python3 scripts/offene_paare.py            # schreibt die Liste neu
    python3 scripts/offene_paare.py --pruefen  # meldet nur, ob sie aktuell ist

Die Reihenfolge der Portionen steht in REIHENFOLGE und ist eine Bewertung, kein
Messwert — sie gehört von Hand gepflegt. Alles andere kommt aus den Daten.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skill"))

from falzmarke import regeln                                    # noqa: E402

ZIEL = REPO / "docs" / "offene-quellenpruefungen.md"

#: Portionsnummer je Quelle und die Begründung dafür. Gleiche Nummer heißt: in
#: einem Durchgang erledigen. Wer eine Quelle abarbeitet, nimmt sie hier heraus
#: und trägt sie unter ERLEDIGT ein.
REIHENFOLGE: dict[str, tuple[str, str]] = {
    "onlineprinters": ("1",
        "Gleiche Gruppe wie die bereits geprüfte `massskizze_b`, bestätigt also keine "
        "zweite. Zwölf Paare derselben Quelle schwiegen schon — hier ist mit Schweigen "
        "zu rechnen, und genau das ist der Grund, es zu wissen."),
    "letter_pro": ("2",
        "`zaehlt: einzeln` — hebt keine Regel auf „mehrfach bestätigt“. Hält aber "
        "mehrere Warnungen allein am Leben und ist lokal vendort unter "
        "`skill/falzmarke/typst/vendor/`, also die billigste Arbeit der Liste."),
    "koma_script": ("3",
        "Betrifft nur `geometrie.form_a.masse`. Die Regel steht seit dem "
        "24.09.2026 auf `mehrfach_bestaetigt` (#180), getragen von "
        "`massskizze_a` und `federwerk` — `koma_script` zählt `einzeln` und "
        "kann an der Stufe nichts mehr bewegen."),
}

#: Was abgearbeitet ist, in der Reihenfolge der Erledigung. Prosa, weil der
#: Befund einer Quelle sich nicht aus Zahlen ergibt.
ERLEDIGT = [
    ("`onlineprinters` — zwei Paare, am 25.09.2026",
     "Nicht die Portion, sondern ein Anlass: Für #355 mussten die beiden Regeln geprüft "
     "werden, die allein auf dieser Quelle standen. Das Bild wurde geholt und abgelesen. "
     "Beide Paare schweigen — die Zeichnung bemaßt weder die Höhe des Informationsblocks "
     "noch die Marken; ihr „20“ gehört zur linken Kante des Anschriftfelds. Gekostet hat "
     "es keine Stufe: Zwei neue Quellen tragen die 40 mm und die Heftrandgrenze, die "
     "Länge der Marken ist seither `werkzeug` (ADR 0047). Nebenbefund aus demselben "
     "Bild: Der Textteil trägt „Schriftgröße 10 - 12 pt“ und belegt damit "
     "`geometrie.schriftgroessen` mit, was vorher niemand ausgewertet hatte."),
    ("`massskizze_b` — alle zwölf Paare, am 22.09.2026",
     "Die Zeichnung wurde gerendert und abgelesen; sie führt keine Textelemente, nur "
     "Pfade. Elf Paare tragen, eines schweigt: `text.vermerke_max_3` — die Zone ist mit "
     "17,7 mm bemaßt, eine Zeilenzahl nennt sie nicht. Zwei Belege tragen mit benannter "
     "Lücke: `geometrie.form_b.zonen` (die Zeichnung zeigt 17,7 mm als **eine** Zone, "
     "die Aufteilung 5 + 12,7 nicht) und `text.folgeseiten` (Seitenzahl ausdrücklich, "
     "zur empfohlenen Kopfzeile nichts)."),
    ("`wikipedia` — alle sechs Paare, am 22.09.2026",
     "Am selben Tag kam ein sechstes Paar dazu, das vorher gar nicht gezählt wurde: "
     "`text.anschrift_ohne_leerzeilen` nannte den Artikel nie als Quelle, obwohl er "
     "beide Hälften der Regel trägt. Eingetragen mit #344 — die Regel ist seither "
     "`einzeln_belegt` statt `werkzeug` (ADR 0044). Ein neu eingetragenes Paar ist der "
     "einzige Weg, auf dem eine Regel **aufsteigen** kann; Nachlesen kann sie nur "
     "bestätigen oder herabstufen. "
     "Die fünf ursprünglichen Paare: "
     "Über die API im Volltext geholt (13 020 Zeichen). Alle fünf tragen, keines "
     "schweigt. Drei wörtlich: Seitenformat („A4 (210 mm × 297 mm)“), Abkürzungen "
     "(„z. B.“ samt geschütztem Leerzeichen) und Datum (beide Formen). Zwei mit Lücke: "
     "`geometrie.seitenraender` (nur der linke Rand, 2,5 cm Fluchtlinie) und "
     "`geometrie.schriftgroessen` (nur die 8 Punkt, und die nur für die "
     "Rücksendeangabe)."),
]


def _lage():
    """(Paare je Quelle, Quellen je Regel, Regeln nach id)."""
    nach_quelle, nach_regel = defaultdict(list), defaultdict(list)
    for rid, quelle in regeln.ohne_belegpruefung():
        nach_quelle[quelle].append(rid)
        nach_regel[rid].append(quelle)
    return nach_quelle, nach_regel, {r["id"]: r for r in regeln.alle()}


def _folge(rid, nach_regel, alle) -> str:
    """Was mit der Regel geschieht, wenn ALLE ihre ungeprüften Quellen schweigen.

    Für `einzeln_belegt` trägt auch eine Quelle mit `zaehlt: einzeln`. Wer nur
    die vollen zählt, sieht Regeln fallen, die bleiben — der Fehler der ersten
    Fassung dieser Liste.
    """
    q = regeln.quellen()
    r = alle[rid]
    offen = set(nach_regel[rid])
    lebend = [n for n in regeln._quellennamen(r)
              if not regeln._schweigt(r, n) and n not in offen]
    gruppen = {q[n].get("gruppe", n) for n in lebend if q.get(n, {}).get("zaehlt") == "voll"}
    tragend = [n for n in lebend if q.get(n, {}).get("zaehlt") in ("voll", "einzeln")]
    herkunft = r.get("herkunft")
    if herkunft == "mehrfach_bestaetigt":
        return "bleibt" if len(gruppen) >= 2 else "**fällt auf Warnung**"
    if herkunft == "einzeln_belegt":
        return "bleibt" if tragend else "**verliert jeden Beleg**"
    return "unberührt"


def _tabelle(quelle, nach_quelle, nach_regel, alle) -> str:
    zeilen = []
    for rid in sorted(nach_quelle[quelle],
                      key=lambda r: (alle[r].get("wirkung") != "fehler", r)):
        r = alle[rid]
        wirkung = "**Fehler**" if r.get("wirkung") == "fehler" else "Warnung"
        zeilen.append(f"| `{rid}` | {wirkung} | {r.get('titel', '')} | "
                      f"{_folge(rid, nach_regel, alle)} |")
    return "\n".join(zeilen)


def dokument() -> str:
    q = regeln.quellen()
    nach_quelle, nach_regel, alle = _lage()
    offen = sorted(nach_quelle, key=lambda n: (REIHENFOLGE.get(n, ("9", ""))[0], n))
    fehlt = [n for n in offen if n not in REIHENFOLGE]
    if fehlt:
        raise SystemExit(
            "Diese Quellen haben offene Paare, stehen aber nicht in REIHENFOLGE: "
            + ", ".join(fehlt) + ".\nErst einordnen, dann erzeugen — sonst fällt die "
            "Portion stillschweigend aus der Liste.")

    gesamt = len(regeln.ohne_belegpruefung())
    fehler_regeln = sum(1 for r in nach_regel if alle[r].get("wirkung") == "fehler")
    faellt = sum(1 for r in nach_regel if _folge(r, nach_regel, alle).startswith("**"))

    teile = [f"""# Offene Quellenprüfungen — {gesamt} ungeprüfte Quelle-Regel-Paare

<!-- Erzeugt von scripts/offene_paare.py — nicht von Hand ändern.
     Reihenfolge und Erledigt-Abschnitt stehen als REIHENFOLGE bzw. ERLEDIGT dort. -->

> **Diese Arbeit ruht.** [ADR 0042](entscheidungen/0042-quellenpruefung-ruht.md) vom
> 22.09.2026: Der erreichte Stand gilt als ausreichend, die verbliebenen Paare werden nicht
> weiter nachgelesen. Dieses Dokument bleibt als Einstiegspunkt, falls die Arbeit wieder
> aufgenommen wird — es ist kein Rückstand und keine Aufgabenliste.

Erhoben aus `skill/falzmarke/regeln/din5008.yaml`. Begonnen wurde mit 44 Paaren.

Ein *Paar* ist eine Regel und eine Quelle, die sie nennt. Geprüft heißt: Jemand hat in der
Quelle nachgesehen und das Ergebnis in `belegt_durch:` eingetragen — eine Fundstelle oder
`SCHWEIGT` mit Begründung.

## Was offen bleibt und was das heißt

Ein ungeprüftes Paar wird **mitgezählt**: `unabhaengige_belege()` nimmt jede Quelle mit
`zaehlt: voll`, solange sie nicht ausdrücklich als schweigend vermerkt ist. Nachlesen kann die
Lage deshalb nur bestätigen oder verschlechtern — aufwerten kann es keine Regel. Genau das ist
der Grund, warum die Arbeit ruht: Die beiden Quellen, deren Prüfung etwas bewegen konnte, sind
abgearbeitet.

Dass das Risiko nicht theoretisch ist, zeigt der bisherige Verlauf. Bei `onlineprinters` wurden
am 27.08.2026 zehn Paare nachgelesen, alle zehn schwiegen, und drei Regeln fielen von Fehler auf
Warnung ([Befund](quellenpruefung-onlineprinters-2026-08-27.md)).

Derzeit hängen **{fehler_regeln} Regeln mit Wirkung `fehler`** an mindestens einem ungeprüften
Paar; schwiegen alle ungeprüften Quellen, verlören **{faellt} Regeln** ihre Stufe. Das ist der
ungünstigste Fall, nicht der erwartete — dass eine bemaßte Zeichnung zum Seitenformat schweigt,
ist unwahrscheinlich. Die Zahl sagt, wie viel auf ungeprüftem Grund steht, und sie ist mit
ADR 0042 bewusst in Kauf genommen.

## Erledigt
"""]
    for titel, text in ERLEDIGT:
        teile.append(f"\n**{titel}.** {text}\n")

    teile.append("""
## Was liegen bleibt

Die Reihenfolge stünde so, wenn die Arbeit wieder aufgenommen würde — sortiert nach Wirkung je
Aufwand, nicht nach Stückzahl. Die Spalte „Folge" ist regelbezogen: Sie gilt, wenn **alle**
ungeprüften Quellen dieser Regel schweigen, nicht nur die der Portion.

| # | Quelle | Paare | trägt Gruppe? | Fehler-Regeln | Warum hier |
|---|---|---|---|---|---|
""")
    for name in offen:
        nummer, grund = REIHENFOLGE[name]
        traegt = "ja" if q[name].get("zaehlt") == "voll" else "**nein**"
        fehler = sum(1 for r in nach_quelle[name] if alle[r].get("wirkung") == "fehler")
        teile.append(f"| {nummer} | `{name}` | {len(nach_quelle[name])} | {traegt} | "
                     f"{fehler} | {grund} |\n")

    for name in offen:
        d = q[name]
        anzahl = len(nach_quelle[name])
        hinweis = ""
        if d.get("zaehlt") != "voll":
            hinweis = ("\n> Diese Quelle zählt `einzeln` und trägt keine Belegsgruppe. Die "
                       "Spalte „Folge\"\n> rechnet die **übrigen** ungeprüften Quellen "
                       "derselben Regel mit — ein Schweigen\n> ausgerechnet hier fällt keine "
                       "dieser Regeln.\n")
        teile.append(f"""
## {REIHENFOLGE[name][0]}. `{name}` — {anzahl} {'Paar' if anzahl == 1 else 'Paare'}

{d.get('titel', '')}
`{d.get('url', '')}`
Zählstufe `{d.get('zaehlt')}`, Gruppe `{d.get('gruppe', name)}`.
{hinweis}
| Regel | Wirkung heute | Titel | Folge, wenn alle ungeprüften Quellen der Regel schweigen |
|---|---|---|---|
{_tabelle(name, nach_quelle, nach_regel, alle)}
""")

    teile.append("""
## Wie eine Prüfung abläuft

1. Quelle öffnen, zur Regel nachsehen. Eine Maßzeichnung führt ihre Zahlen oft als Pfade, nicht
   als Text — dann rendern (`rsvg-convert -w 2400 …`) und ablesen, nicht im Quelltext suchen.
2. Ergebnis in `din5008.yaml` unter der Regel eintragen:

   ```yaml
   belegt_durch:
     massskizze_b: "Bemaßt mit 45 mm von der oberen Blattkante …"   # trägt
     wikipedia: "SCHWEIGT — Artikel nennt nur Form B"               # trägt nicht
   ```

   Trägt eine Quelle den Kern, aber nicht jedes Detail, gehört die Lücke in denselben Satz.
3. `python3 -m pytest tests/test_quellenlage.py` — die Schranke `UNGEPRUEFTE_PAARE` darf nur
   sinken und will dann von Hand nachgezogen werden; `SCHWEIGENDE_QUELLEN` ebenso.
4. `python3 scripts/quellenlage.py` erzeugt den Doku-Abschnitt in der Normreferenz neu.
5. Die Zahlen in `docs/recht.md` („Was die Stufen derzeit wert sind") nachziehen — sie werden
   von `tests/test_textkanon.py` gegen die Regeldaten gezählt.
6. `python3 scripts/offene_paare.py` — diese Liste neu erzeugen, die abgearbeitete Quelle aus
   `REIHENFOLGE` nehmen und unter `ERLEDIGT` eintragen.
7. Fällt dabei eine Regel unter ihre Stufe, bricht die Regeldatei ab. Das ist gewollt.
""")
    return "".join(teile)


def main() -> int:
    neu = dokument()
    if "--pruefen" in sys.argv:
        alt = ZIEL.read_text(encoding="utf-8") if ZIEL.exists() else ""
        if alt == neu:
            print(f"OK  {ZIEL.relative_to(REPO)} ist aktuell.")
            return 0
        print(f"FEHL  {ZIEL.relative_to(REPO)} ist veraltet — "
              "`python3 scripts/offene_paare.py` ausführen.")
        return 1
    ZIEL.write_text(neu, encoding="utf-8")
    anzahl = len(regeln.ohne_belegpruefung())
    print(f"OK  {ZIEL.relative_to(REPO)} mit {anzahl} offenen Paaren geschrieben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
