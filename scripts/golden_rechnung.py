#!/usr/bin/env python3
"""Erneuert die Golden-Dateien der Rechnungsbeispiele (#119).

Ein Golden ist die Byte-für-Byte festgehaltene Ausgabe — sowohl des PDF als
auch der darin eingebetteten XML nach EN 16931/XRechnung. Es fällt auf, wenn
sich an einem der beiden etwas ändert, das niemand angesagt hat: eine
Tabellenspalte, ein Feld, eine Rundung.

Wie bei der `.eml` wird mit `SOURCE_DATE_EPOCH` gesetzt: Ohne die Variable
trägt das PDF die Rechnerzeit als `/CreationDate`, und zwei Läufe ergeben andere
Bytes (gemessen am 13.09.2026). Die eingebettete XML hängt nicht daran.

Ebenso fest ist die Fassung in `/Producer` und `/falzmarke_Version`
(`conftest.GOLDEN_VERSION`, #467). Ein Versionssprung ändert deshalb kein
Golden mehr. Meldet das Skript nach einem Release „erneuert“, hat sich etwas
anderes geändert.

Was typst selbst ins PDF schreibt und mit jeder Fassung wechselt (Fassung in
`/Creator` und XMP, InstanceID), vergleicht das Skript wie die Tests nur maskiert
(`conftest.ohne_typst_kennung`, #533). Eine neue typst-Fassung ohne sichtbare
Änderung schreibt deshalb kein Golden neu.

Greift die Maske nicht, etwa weil typst sein XMP umgebaut hat oder eine Kennung öfter
auftritt als erwartet, hält sie das Neu-Erzeugen nicht auf (Review #568): Ohne Schalter
wird diese Datei roh verglichen und, wo sie abweicht, geschrieben. Je Datei sagt eine
Zeile auf stderr, warum, am Ende fasst eine Liste alle roh verglichenen Dateien
zusammen, und der Lauf endet mit Exit 2 statt 0 (Review #575). Das kann eine echte
Änderung sein: den Diff prüfen und die Maske nachziehen. Die Tests vergleichen weiter
durch die Maske und bleiben rot, bis sie nachgezogen ist.

Mit `--pruefen` zählt eine solche Datei als Abweichung, und ihre Zeile nennt den Grund.
Der Lauf vergleicht die übrigen Goldens weiter und endet mit der Zusammenfassung.

    python3 scripts/golden_rechnung.py            # schreibt Goldens neu
    python3 scripts/golden_rechnung.py --pruefen  # meldet nur Abweichungen

Exit-Codes: 0 alles auf Stand bzw. geschrieben; 1 mit `--pruefen` mindestens eine
Abweichung, oder keine Beispiele; 2 ohne `--pruefen` geschrieben, aber mindestens eine
Datei roh verglichen, weil die Maske nicht griff.

Nach einer *gewollten* Änderung an Emitter oder Positionstabelle: einmal ohne
Schalter laufen lassen und den Diff der Goldens im PR mitlesen. Er ist der
eigentliche Befund — nicht lästige Nacharbeit.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skill"))
sys.path.insert(0, str(REPO / "tests"))

from conftest import (GOLDEN_VERSION, RECHNUNG_BEISPIELE, PROFILE,  # noqa: E402
                      TypstMaskeGreiftNicht, ohne_typst_kennung)

#: Derselbe Zeitpunkt wie in `scripts/golden_email.py` und in den Tests.
EPOCH = "1788134400"

ZIEL = REPO / "tests" / "golden" / "rechnung"


def _xml_bytes(pdf: Path) -> bytes:
    """Die im PDF eingebettete XML — dieselbe Extraktion wie im Test."""
    import pypdf

    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    datei = wurzel["/AF"][0].get_object()["/EF"]["/F"]
    return bytes(datei.get_object().get_data())


def erzeuge(quelle: Path) -> tuple[bytes, bytes]:
    """(PDF-Bytes, eingebettete-XML-Bytes) zu einem Rechnungsbeispiel."""
    from falzmarke import cli

    alt = os.environ.get("SOURCE_DATE_EPOCH")
    os.environ["SOURCE_DATE_EPOCH"] = EPOCH
    alte_version, cli.VERSION = cli.VERSION, GOLDEN_VERSION
    arbeit = Path(tempfile.mkdtemp(prefix="falzmarke-golden-"))
    try:
        pdf, _ = cli.rendere(quelle, arbeit / f"{quelle.stem}.pdf", profil_verzeichnis=PROFILE)
        return pdf.read_bytes(), _xml_bytes(pdf)
    finally:
        cli.VERSION = alte_version
        shutil.rmtree(arbeit, ignore_errors=True)
        if alt is None:
            del os.environ["SOURCE_DATE_EPOCH"]
        else:
            os.environ["SOURCE_DATE_EPOCH"] = alt


def _gleich(alt: bytes, neu: bytes, maske, nur_pruefen: bool, pfad: Path,
            roh: dict[Path, str]) -> bool:
    """Ob `alt` und `neu` gleich sind, mit `maske` durch sie verglichen.

    Scheitert die Maske, kommt ihr Grund unter `pfad` nach `roh`. Mit `--pruefen`
    gilt die Datei dann als abweichend: Gleich ist nur, was die Maske gleich nennt.
    Ohne den Schalter soll das Skript gerade dann schreiben können: Eine typst-Fassung,
    die ihr XMP umbaut, bricht die Maske, und das Neu-Erzeugen ist die Antwort darauf.
    Es vergleicht dann roh, und `main` endet mit Exit 2."""
    if maske is None:
        return alt == neu
    try:
        return maske(alt) == maske(neu)
    except TypstMaskeGreiftNicht as fehler:
        roh[pfad] = str(fehler)
        if nur_pruefen:
            return False
        print(f"Maske griff nicht bei {pfad.relative_to(REPO)}, roh verglichen: {fehler}",
              file=sys.stderr)
        return alt == neu


def _aktualisiere(pfad: Path, neu: bytes, nur_pruefen: bool, *, maske=None,
                  roh: dict[Path, str] | None = None) -> bool:
    """Schreibt `pfad`, falls nötig. Gibt zurück, ob es eine Abweichung gab.

    Mit `maske` werden beide Seiten erst durch sie verglichen (`_gleich`). Greift sie
    nicht, steht der Grund danach in `roh`."""
    roh = {} if roh is None else roh
    alt = pfad.read_bytes() if pfad.exists() else None
    if alt is not None and _gleich(alt, neu, maske, nur_pruefen, pfad, roh):
        print(f"gleich     {pfad.relative_to(REPO)}")
        return False
    if nur_pruefen:
        grund = "fehlt" if alt is None else "weicht ab"
        zusatz = f" — Maske greift nicht: {roh[pfad]}" if pfad in roh else ""
        print(f"{grund:10} {pfad.relative_to(REPO)}{zusatz}", file=sys.stderr)
    else:
        pfad.write_bytes(neu)
        print(f"{'neu' if alt is None else 'erneuert':10} {pfad.relative_to(REPO)}")
    return True


def main(argv: list[str]) -> int:
    if not RECHNUNG_BEISPIELE:
        print("keine Beispiele mit `typ: rechnung` unter examples/ — nichts zu tun",
              file=sys.stderr)
        return 1

    nur_pruefen = "--pruefen" in argv
    ZIEL.mkdir(parents=True, exist_ok=True)
    abweichungen = 0
    roh: dict[Path, str] = {}
    geschrieben: set[Path] = set()

    for quelle in RECHNUNG_BEISPIELE:
        pdf_bytes, xml_bytes = erzeuge(quelle)
        pdf = ZIEL / f"{quelle.stem}.pdf"
        if _aktualisiere(pdf, pdf_bytes, nur_pruefen, maske=ohne_typst_kennung, roh=roh):
            abweichungen += 1
            geschrieben.add(pdf)
        if _aktualisiere(ZIEL / f"{quelle.stem}.xml", xml_bytes, nur_pruefen):
            abweichungen += 1

    if nur_pruefen and abweichungen:
        print(f"\n{abweichungen} Golden-Datei(en) nicht auf Stand — "
              "`python3 scripts/golden_rechnung.py` läuft dagegen.", file=sys.stderr)
        return 1
    if roh:
        print(f"\n{len(roh)} PDF-Golden(s) roh verglichen, weil die Maske nicht griff:",
              file=sys.stderr)
        for pfad, grund in roh.items():
            wie = "geschrieben" if pfad in geschrieben else "unverändert"
            print(f"  {pfad.relative_to(REPO)} ({wie}): {grund}", file=sys.stderr)
        print("Hat typst sein XMP umgebaut, oder tritt eine Kennung öfter auf als erwartet? "
              "Das kann auch eine echte Änderung sein: den Diff der Goldens prüfen und "
              "`ohne_typst_kennung` in tests/conftest.py nachziehen. Bis dahin bleiben die "
              "Tests rot.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
