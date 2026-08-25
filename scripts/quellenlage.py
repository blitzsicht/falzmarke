#!/usr/bin/env python3
"""Schreibt den Abschnitt „Quellenlage je Regel“ in references/din5008.md.

Die Herkunft wird an genau einer Stelle gepflegt: in
`skill/falzmarke/regeln/din5008.yaml`. Dieser Abschnitt der Normreferenz ist
eine Ausgabe davon, keine zweite Quelle — sonst laufen beide auseinander, und
niemand merkt es.

    python3 scripts/quellenlage.py            # schreibt den Abschnitt neu
    python3 scripts/quellenlage.py --pruefen  # meldet nur, ob er aktuell ist

`--pruefen` benutzt tests/test_quellenlage_doku.py; im CI reicht der Testlauf.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skill"))

from falzmarke import regeln                                    # noqa: E402

ZIEL = REPO / "skill" / "references" / "din5008.md"
MARKE_START = "<!-- quellenlage:anfang -->"
MARKE_ENDE = "<!-- quellenlage:ende -->"

WORT = {
    regeln.MEHRFACH: "mehrfach bestätigt",
    regeln.EINZELN: "einzeln belegt",
    regeln.OFFEN: "offen",
    regeln.WERKZEUG: "Werkzeugprüfung",
}

WIRKUNG = {"fehler": "Fehler", "warnung": "Warnung", "keine": "wird nicht geprüft"}


def abschnitt() -> str:
    quellen = regeln.quellen()
    zeilen = [
        MARKE_START,
        "",
        "## Quellenlage je Regel",
        "",
        "**Erzeugt aus [`skill/falzmarke/regeln/din5008.yaml`](../falzmarke/regeln/din5008.yaml)"
        " — dort ändern, dann `python3 scripts/quellenlage.py`.**",
        "",
        "Alle Werte auf dieser Seite stammen aus Sekundärquellen. Der Abgleich mit dem",
        "Originaltext der DIN 5008:2020-03 einschließlich Berichtigung 1:2020-07 steht aus.",
        "Bis dahin wirkt nur als Fehler, was mehrfach belegt ist; eine Regel aus einer",
        "einzigen Quelle ist eine Warnung, und eine Regel ohne Beleg wird nicht geprüft.",
        "",
        "**Nicht jede genannte Quelle zählt zur Bestätigung.** `typst-letter-pro` ist unter",
        "`skill/falzmarke/typst/vendor/` eingebettet — falzmarke *setzt* damit das Layout.",
        "Ein Sollwert von dort würde gegen ein PDF geprüft, das dieselbe Quelle erzeugt hat;",
        "die Prüfung könnte nicht rot werden. Die Quelle bleibt als Hinweis darauf wertvoll,",
        "wie jemand anders die Norm gelesen hat, hebt eine Regel aber nie auf „mehrfach",
        "bestätigt“. Dasselbe gilt für die eigene Messung: Sie belegt, dass das Werkzeug",
        "einhält, was es sich vornimmt — nicht, dass das Vorgenommene der Norm entspricht.",
        "",
        "Ab v0.5.1 zählt `skill/falzmarke/regeln/__init__.py` das nach. Zuvor stand die",
        "Regel nur in einem Kommentar, und **alle vierzehn** als mehrfach bestätigt",
        "geführten Regeln verfehlten sie.",
        "",
        "| Regel | Herkunft | wirkt als | Quellen |",
        "|---|---|---|---|",
    ]
    for regel in regeln.alle():
        namen = regel.get("quellen") or []
        belege = ", ".join(quellen[n]["titel"].strip('"') for n in namen) if namen else "—"
        zeilen.append(
            f"| {regel['titel']} | {WORT[regel['herkunft']]} | "
            f"{WIRKUNG.get(regel.get('wirkung'), '—')} | {belege} |")

    zeilen += ["", "### Die Quellen", ""]
    for name, quelle in quellen.items():
        art = {"sekundaerquelle": "Sekundärquelle", "implementierung": "Implementierung",
               "eigene_messung": "eigene Messung"}.get(quelle["art"], quelle["art"])
        titel = quelle["titel"].strip('"')
        url = quelle["url"]
        zaehlt = {
            "voll": "zählt zur Bestätigung",
            "einzeln": "**zählt nicht zur Bestätigung**",
            "nie": "**zählt nie**",
        }.get(quelle.get("zaehlt"), "Zählstufe fehlt")
        beschriftung = f"{art}, {zaehlt}, abgerufen {quelle['abgerufen']}"
        kopf = f"- **{titel}** ({beschriftung})"
        if url.startswith("http"):
            kopf = f"- **[{titel}]({url})** ({beschriftung})"
        zeilen.append(kopf)
        if quelle.get("bemerkung"):
            zeilen.append(f"  {quelle['bemerkung'].strip()}")
    zeilen += ["", MARKE_ENDE]
    return "\n".join(zeilen)


def eingesetzt(text: str) -> str:
    neu = abschnitt()
    if MARKE_START in text and MARKE_ENDE in text:
        vorher = text[: text.index(MARKE_START)]
        nachher = text[text.index(MARKE_ENDE) + len(MARKE_ENDE):]
        return vorher + neu + nachher
    return text.rstrip() + "\n\n" + neu + "\n"


def main() -> int:
    text = ZIEL.read_text(encoding="utf-8")
    neu = eingesetzt(text)
    if "--pruefen" in sys.argv:
        if neu != text:
            print(f"{ZIEL.name} ist nicht auf dem Stand der Regeldatei — "
                  "python3 scripts/quellenlage.py ausführen.", file=sys.stderr)
            return 1
        print(f"{ZIEL.name} ist aktuell.")
        return 0
    ZIEL.write_text(neu, encoding="utf-8")
    print(f"OK  {ZIEL.relative_to(REPO)} mit {len(regeln.alle())} Regeln aktualisiert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
