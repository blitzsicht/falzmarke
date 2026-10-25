#!/usr/bin/env python3
"""Schreibt `thunderbird/entwurfsbruecke/zeichennamen.js` aus Pythons `html`.

`vergleich.js` muss denselben Text bilden wie `skill/falzmarke/gesendet.py`
(ADR 0057). Python löst HTML-Zeichennamen über `html.unescape` auf und kennt
dabei 2231 Namen. Eine von Hand gepflegte Auswahl davon im Add-on lief
auseinander, ohne dass es auffiel: `&ndash;` blieb dort als Wort „ndash“ im
Textkern stehen, während Python es zu „–“ auflöste und damit aus dem Kern
warf. Deshalb steht die Tabelle nicht mehr in `vergleich.js`, sondern wird
hier erzeugt — eine Liste, die veralten kann, war die Ursache.

    python3 scripts/zeichennamen.py            # schreibt die Datei neu
    python3 scripts/zeichennamen.py --pruefen  # Exit 1, wenn sie veraltet ist

Der Algorithmus wird **nicht** erzeugt. Er steht als `entschluesseln()` in
`vergleich.js` und ist eine Übertragung von `html.unescape`; nur die Daten
kommen von hier. `tests/test_zeichennamen.py` hält beides zusammen.

Gemessen am 25.10.2026: Die drei Tabellen sind in Python 3.11 bis 3.15
byte-gleich (SHA-256 der sortierten Namen `d7ed3f33f59f35a1…`, 2231/34/126
Einträge). Eine erzeugte Datei im Repo kann deshalb über die ganze
CI-Matrix byte-genau geprüft werden.
"""

from __future__ import annotations

import html
import html.entities
import json
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ZIEL = REPO / "thunderbird" / "entwurfsbruecke" / "zeichennamen.js"

KOPF = '''/* Die HTML-Zeichennamen, die Python auflöst — ERZEUGT, nicht von Hand ändern.
 *
 * Quelle: `html.entities.html5` und die beiden Ausnahmetabellen von
 * `html.unescape`. Erneuern mit `python3 scripts/zeichennamen.py`, prüfen mit
 * `--pruefen`; `tests/test_zeichennamen.py` erzeugt die Datei im Testlauf neu
 * und vergleicht sie Byte für Byte. Eine Hand-Änderung hier fällt damit auf.
 *
 * Warum die ganze Tabelle und nicht die zwanzig häufigen Namen: Der Textkern
 * entsteht aus Buchstaben und Ziffern. Ein Name, der auf ein Satzzeichen
 * zeigt (`&ndash;`), verschwindet dadurch ganz; einer, der auf einen
 * Buchstaben zeigt (`&ntilde;`), bleibt als dieser Buchstabe; ein erfundener
 * (`&gibtsnicht;`) bleibt als sein eigenes Wort. Diese drei Fälle lassen sich
 * nur unterscheiden, wenn man dieselben Namen kennt wie Python (ADR 0057).
 */
"use strict";

(function (wurzel) {
'''

FUSS = '''
  const api = { NAMEN, UNGUELTIGE_KENNZIFFER, UNGUELTIGE_STELLE };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    wurzel.FalzmarkeZeichennamen = api;
  }
})(this);
'''


#: Diese Zeichen stehen nicht roh in der erzeugten Datei, sondern als
#: `\\uXXXX`: Steuer- und Formatzeichen (`&zwj;` ist ein Nullbreiten-Verbinder,
#: `&#129;` ein C1-Steuerzeichen), die anderen Zeilen- und Leerzeichenarten.
#: Roh wären sie in der Datei nicht zu sehen und im Diff nicht zu prüfen —
#: genau der Fall, den ADR 0052 für Brieftext meldet.
def _sichtbar(zeichen: str) -> bool:
    art = unicodedata.category(zeichen)
    return not (art[0] == "C" or art in ("Zl", "Zp") or (art == "Zs" and zeichen != " "))


def _js_text(wert: str) -> str:
    """Ein JS-Zeichenkettenliteral; Unsichtbares als `\\uXXXX`."""
    aus = []
    for zeichen in wert:
        if _sichtbar(zeichen):
            aus.append(json.dumps(zeichen, ensure_ascii=False)[1:-1])
        else:
            # JS zählt in UTF-16-Einheiten; ein Zeichen jenseits der BMP wird
            # dort zu zwei `\\uXXXX`.
            roh = zeichen.encode("utf-16-be", "surrogatepass")
            aus.extend(f"\\u{int.from_bytes(roh[i:i + 2], 'big'):04x}"
                       for i in range(0, len(roh), 2))
    return '"' + "".join(aus) + '"'


def _js_objekt(name: str, werte: dict, einzug: str = "  ") -> str:
    """Ein JS-Objektliteral, eine Zeile je Eintrag, Schlüssel sortiert."""
    zeilen = [f"{einzug}const {name} = {{"]
    for schluessel in sorted(werte):
        k = _js_text(str(schluessel))
        v = _js_text(werte[schluessel])
        zeilen.append(f"{einzug}  {k}: {v},")
    zeilen.append(f"{einzug}}};")
    return "\n".join(zeilen)


def _js_menge(name: str, werte, einzug: str = "  ") -> str:
    """Ein `new Set([…])`, zwölf Zahlen je Zeile."""
    sortiert = sorted(werte)
    zeilen = [f"{einzug}const {name} = new Set(["]
    for anfang in range(0, len(sortiert), 12):
        teil = ", ".join(str(z) for z in sortiert[anfang:anfang + 12])
        zeilen.append(f"{einzug}  {teil},")
    zeilen.append(f"{einzug}]);")
    return "\n".join(zeilen)


def erzeuge() -> str:
    """Der Inhalt, den `zeichennamen.js` haben muss."""
    # Die beiden Ausnahmetabellen sind nicht öffentlich. Fehlen sie einmal,
    # soll das hier auffallen und nicht als leere Tabelle durchgehen.
    kennziffern = getattr(html, "_invalid_charrefs", None)
    stellen = getattr(html, "_invalid_codepoints", None)
    if not kennziffern or not stellen:
        raise SystemExit("html._invalid_charrefs oder _invalid_codepoints fehlt — "
                         "diese Python-Fassung löst Zahlenverweise anders auf")
    teile = [
        KOPF,
        _js_objekt("NAMEN", dict(html.entities.html5)),
        "",
        _js_objekt("UNGUELTIGE_KENNZIFFER", dict(kennziffern)),
        "",
        _js_menge("UNGUELTIGE_STELLE", stellen),
        FUSS,
    ]
    return "\n".join(teile)


def main(argv: list[str]) -> int:
    inhalt = erzeuge()
    if "--pruefen" in argv:
        alt = ZIEL.read_text(encoding="utf-8") if ZIEL.exists() else ""
        if alt == inhalt:
            print(f"OK  {ZIEL.relative_to(REPO)} ist aktuell "
                  f"({len(html.entities.html5)} Namen)")
            return 0
        print(f"VERALTET  {ZIEL.relative_to(REPO)} — neu schreiben mit "
              "python3 scripts/zeichennamen.py", file=sys.stderr)
        return 1
    ZIEL.write_text(inhalt, encoding="utf-8")
    print(f"OK  {ZIEL.relative_to(REPO)} geschrieben "
          f"({len(html.entities.html5)} Namen, {len(inhalt)} Zeichen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
