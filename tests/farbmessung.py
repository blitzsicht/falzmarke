"""Die Farbmessung für E-Mail-HTML — eine Stelle, zwei Testdateien.

Gemessen wird gegen die beiden Gründe aus `farbe` (`GRUND_HELL`, `GRUND_DUNKEL`):
Schrift braucht 4,5:1 (WCAG 1.4.3), eine Linie 3:1 (WCAG 1.4.11), jeweils auf
**beiden**; ein Grund im Rumpf ist immer ein Befund. Stand bis zum 15.10.2026 in
`test_email_farbe_geerbt.py`; seit die mitgebrachte Signatur nach derselben
Regel gesetzt wird, misst `test_signatur_farbe_geerbt.py` mit. Zwei Kopien
derselben Messung liefen auseinander.

Die Messung hängt an keinem Symbol des Werkzeugs außer `farbe` — so läuft sie
auch auf einem alten Stand und wird dort rot.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from falzmarke import farbe

GRUENDE = (("hell", farbe.GRUND_HELL), ("dunkel", farbe.GRUND_DUNKEL))

#: Für die Meldung: „auf dunklem Grund“, nicht „dunkelem“.
DATIV = {"hell": "hellem", "dunkel": "dunklem"}

#: WCAG 1.4.3 für Fließtext, WCAG 1.4.11 für grafische Elemente.
SCHRIFT_MINDEST = 4.5
LINIE_MINDEST = 3.0

#: Werte, die keine eigene Farbe setzen.
KEINE_FARBE = {"inherit", "currentcolor", "transparent", "none", "initial", "unset", ""}

#: Rahmen-Eigenschaften, die eine Farbe tragen können.
LINIEN = ("border", "border-top", "border-right", "border-bottom", "border-left",
          "border-color")


def _rgb(wert: str) -> tuple[int, int, int] | None:
    treffer = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", wert.strip())
    if not treffer:
        return None
    ziffern = treffer.group(1)
    if len(ziffern) == 3:
        ziffern = "".join(z * 2 for z in ziffern)
    return int(ziffern[0:2], 16), int(ziffern[2:4], 16), int(ziffern[4:6], 16)


def _schwaechster_grund(rgb: tuple[int, int, int]) -> tuple[str, float]:
    return min(((name, farbe.kontrast(rgb, grund)) for name, grund in GRUENDE),
               key=lambda paar: paar[1])


def _deklarationen(stil: str) -> dict[str, str]:
    paare = {}
    for teil in stil.split(";"):
        if ":" in teil:
            name, wert = teil.split(":", 1)
            paare[name.strip().lower()] = wert.strip()
    return paare


class _Farbmesser(HTMLParser):
    """Sammelt jede Farbe, die ein Element inline setzt, und misst sie."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.befunde: list[str] = []

    def _melde(self, tag: str, was: str):
        self.befunde.append(f"<{tag}> {was}")

    def handle_starttag(self, tag, attrs):
        attribute = {k.lower(): (v or "") for k, v in attrs}
        if attribute.get("bgcolor", "").strip():
            self._melde(tag, f'setzt bgcolor="{attribute["bgcolor"]}" — ein Grund im Rumpf')
        stil = _deklarationen(attribute.get("style", ""))
        for name in ("background-color", "background"):
            if stil.get(name, "").lower() not in KEINE_FARBE:
                self._melde(tag, f"setzt {name}: {stil[name]} — ein Grund im Rumpf")
        if stil.get("color", "").lower() not in KEINE_FARBE:
            self._messe(tag, "color", stil["color"], SCHRIFT_MINDEST)
        for name in LINIEN:
            for token in stil.get(name, "").split():
                if token.startswith("#") or token.lower().startswith(("rgb", "hsl")):
                    self._messe(tag, name, token, LINIE_MINDEST)

    handle_startendtag = handle_starttag

    def _messe(self, tag: str, eigenschaft: str, wert: str, mindest: float):
        rgb = _rgb(wert)
        if rgb is None:
            self._melde(tag, f"{eigenschaft}: {wert} — nicht messbar")
            return
        grund, verhaeltnis = _schwaechster_grund(rgb)
        if verhaeltnis < mindest:
            self._melde(tag, f"{eigenschaft}: {wert} — {verhaeltnis:.2f}:1 auf {DATIV[grund]} Grund, "
                             f"verlangt {mindest}:1")


def farben_im_rumpf(dokument: str) -> list[str]:
    """Jeder Grund im Rumpf und jede Farbe, die auf einem der beiden Gründe nicht trägt."""
    messer = _Farbmesser()
    messer.feed(dokument)
    messer.close()
    return messer.befunde
