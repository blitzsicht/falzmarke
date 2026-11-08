"""Der Erklärfilm unter docs/marke/video/erklaerfilm.

Gerendert wird er lokal, nicht in der CI; deshalb prüft hier nichts das Bild. Was sich
ohne Node prüfen lässt, ist, ob die Befehle in package.json zur Komposition passen.
"""

from __future__ import annotations

import json
import math
import re

from conftest import REPO

FILM = REPO / "docs" / "marke" / "video" / "erklaerfilm"
PAKET = FILM / "package.json"
TEXTE = FILM / "src" / "texte.json"
FILM_TSX = FILM / "src" / "Erklaerfilm.tsx"
WURZEL_TSX = FILM / "src" / "index.tsx"
LIESMICH = FILM / "README.md"

# So steht die Länge in Erklaerfilm.tsx. Steht sie dort anders, rechnet _gesamt_frames
# nicht mehr nach, was Remotion rechnet, und bricht ab, statt eine falsche Grenze zu liefern.
GESAMT_FORMEL = "export const GESAMT_FRAMES = Math.round(texte.dauer * FPS);"


def _gesamt_frames() -> int:
    """Wie Remotion sie zählt: `GESAMT_FRAMES = Math.round(texte.dauer * FPS)` in
    Erklaerfilm.tsx. Gelesen wird aus denselben Dateien, nicht aus einem Sollwert hier."""
    tsx = FILM_TSX.read_text(encoding="utf-8")
    assert tsx.count(GESAMT_FORMEL) == 1, (
        f"Erklaerfilm.tsx berechnet GESAMT_FRAMES nicht mehr als „{GESAMT_FORMEL}“: "
        "_gesamt_frames muss nachziehen"
    )
    fps = re.findall(r"export const FPS = (\d+);", tsx)
    assert len(fps) == 1, f"FPS in Erklaerfilm.tsx nicht eindeutig: {fps}"
    dauer = json.loads(TEXTE.read_text(encoding="utf-8"))["dauer"]
    # Math.round rundet .5 auf, Pythons round() zur geraden Zahl: 766,5 wird dort 766.
    gesamt = math.floor(dauer * int(fps[0]) + 0.5)
    assert gesamt > 0, f"Film ohne Länge: dauer {dauer!r} in texte.json, FPS {fps[0]}"
    return gesamt


def test_jeder_standbild_frame_liegt_in_der_komposition():
    """`bild-quer` und `bild-hoch` verlangten seit dem ersten Commit Frame 800; der Film
    hat 780 Frames (26 s × 30), der höchste ist 779. Beide Befehle brachen mit
    `RangeError` ab, und die Standbilder unter docs/renders blieben auf einem alten Stand.

    Remotion nimmt `--frame=N` und `--frame N`; beide Formen zählen. Ein Standbild ohne
    Frame wird rot: Es fiele still auf Frame 0, die leere Eingabe vor dem ersten Wort.
    """
    gesamt = _gesamt_frames()
    skripte = json.loads(PAKET.read_text(encoding="utf-8"))["scripts"]
    frames = [
        (name, int(treffer))
        for name, befehl in skripte.items()
        for treffer in re.findall(r"--frame[=\s]+(\d+)", befehl)
    ]
    assert frames, "kein `--frame` in package.json gefunden: Muster oder Skripte geändert?"
    mit_frame = {name for name, _ in frames}
    ohne = [name for name, befehl in skripte.items()
            if "remotion still" in befehl and name not in mit_frame]
    assert not ohne, f"Standbild ohne `--frame`: {', '.join(ohne)}"
    ausserhalb = [f"{name}: {frame}" for name, frame in frames if frame >= gesamt]
    assert not ausserhalb, (
        f"Frame außerhalb der Komposition (0 bis {gesamt - 1}): " + ", ".join(ausserhalb)
    )


def test_jede_komposition_laeuft_ueber_den_ganzen_film():
    """Die Grenze oben gilt nur, wenn index.tsx sie auch benutzt.

    `_gesamt_frames` rechnet `GESAMT_FRAMES` nach. Kürzte eine Komposition ihre Länge
    selbst (`durationInFrames={GESAMT_FRAMES - 30}`), läge ein Frame, den die Prüfung
    durchlässt, trotzdem hinter ihrem Ende.
    """
    wurzel = WURZEL_TSX.read_text(encoding="utf-8")
    kompositionen = wurzel.count("<Composition")
    assert kompositionen, "keine <Composition> in index.tsx gefunden: Datei verschoben?"
    for feld in ("durationInFrames={GESAMT_FRAMES}", "fps={FPS}"):
        assert wurzel.count(feld) == kompositionen, (
            f"nicht jede der {kompositionen} Kompositionen setzt {feld}"
        )


def test_die_readme_nennt_die_laenge_aus_texte_yaml():
    """Die README sagte „Sechzig Sekunden“, als der Film längst 26 lief. Die Länge steht
    in texte.yaml (`film.dauer`); die README nennt sie als Ziffer, damit hier ein
    Vergleich möglich ist. Gelesen wird nur der erste Absatz: Weiter unten stehen andere
    Zeitangaben („mindestens 2,5 Sekunden Lesezeit“)."""
    dauer = json.loads(TEXTE.read_text(encoding="utf-8"))["dauer"]
    absaetze = LIESMICH.read_text(encoding="utf-8").split("\n\n")
    erster = next(a for a in absaetze if a.strip() and not a.lstrip().startswith("#"))
    angaben = re.findall(r"(\d+(?:,\d+)?) Sekunden", erster)
    assert angaben, "der erste Absatz der README nennt keine Länge in Sekunden: Satz umgebaut?"
    falsch = [a for a in angaben if float(a.replace(",", ".")) != dauer]
    assert not falsch, f"README nennt {', '.join(falsch)} Sekunden, texte.yaml {dauer}"
