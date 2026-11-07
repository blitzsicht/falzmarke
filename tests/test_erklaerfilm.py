"""Der Erklärfilm unter docs/marke/video/erklaerfilm.

Gerendert wird er lokal, nicht in der CI; deshalb prüft hier nichts das Bild. Was sich
ohne Node prüfen lässt, ist, ob die Befehle in package.json zur Komposition passen.
"""

from __future__ import annotations

import json
import re

from conftest import REPO

FILM = REPO / "docs" / "marke" / "video" / "erklaerfilm"
PAKET = FILM / "package.json"
TEXTE = FILM / "src" / "texte.json"
FILM_TSX = FILM / "src" / "Erklaerfilm.tsx"


def _gesamt_frames() -> int:
    """Wie Remotion sie zählt: `GESAMT_FRAMES = Math.round(texte.dauer * FPS)` in
    Erklaerfilm.tsx. Gelesen wird aus denselben Dateien, nicht aus einem Sollwert hier."""
    fps = re.findall(r"export const FPS = (\d+);", FILM_TSX.read_text(encoding="utf-8"))
    assert len(fps) == 1, f"FPS in Erklaerfilm.tsx nicht eindeutig: {fps}"
    dauer = json.loads(TEXTE.read_text(encoding="utf-8"))["dauer"]
    return round(dauer * int(fps[0]))


def test_jeder_standbild_frame_liegt_in_der_komposition():
    """`bild-quer` und `bild-hoch` verlangten seit dem ersten Commit Frame 800; der Film
    hat 780 Frames (26 s × 30), der höchste ist 779. Beide Befehle brachen mit
    `RangeError` ab, und die Standbilder unter docs/renders blieben auf einem alten Stand.
    """
    gesamt = _gesamt_frames()
    skripte = json.loads(PAKET.read_text(encoding="utf-8"))["scripts"]
    frames = [
        (name, int(treffer))
        for name, befehl in skripte.items()
        for treffer in re.findall(r"--frame=(\d+)", befehl)
    ]
    assert frames, "kein `--frame=` in package.json gefunden: Muster oder Skripte geändert?"
    ausserhalb = [f"{name}: {frame}" for name, frame in frames if frame >= gesamt]
    assert not ausserhalb, (
        f"Frame außerhalb der Komposition (0 bis {gesamt - 1}): " + ", ".join(ausserhalb)
    )
