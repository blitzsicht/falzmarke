#!/usr/bin/env python3
"""Erneuert die Golden-Dateien der Rechnungsbeispiele (#119).

Ein Golden ist die Byte-für-Byte festgehaltene Ausgabe — sowohl des PDF als
auch der darin eingebetteten XML nach EN 16931/XRechnung. Es fällt auf, wenn
sich an einem der beiden etwas ändert, das niemand angesagt hat: eine
Tabellenspalte, ein Feld, eine Rundung.

Wie bei der `.eml` wird mit `SOURCE_DATE_EPOCH` gesetzt: Ohne die Variable
trägt das PDF die Rechnerzeit als `/CreationDate`, und zwei Läufe ergeben andere
Bytes (gemessen am 13.09.2026). Die eingebettete XML hängt nicht daran.

    python3 scripts/golden_rechnung.py            # schreibt Goldens neu
    python3 scripts/golden_rechnung.py --pruefen  # meldet nur Abweichungen

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

from conftest import RECHNUNG_BEISPIELE, PROFILE  # noqa: E402

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
    arbeit = Path(tempfile.mkdtemp(prefix="falzmarke-golden-"))
    try:
        pdf, _ = cli.rendere(quelle, arbeit / f"{quelle.stem}.pdf", profil_verzeichnis=PROFILE)
        return pdf.read_bytes(), _xml_bytes(pdf)
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)
        if alt is None:
            del os.environ["SOURCE_DATE_EPOCH"]
        else:
            os.environ["SOURCE_DATE_EPOCH"] = alt


def _aktualisiere(pfad: Path, neu: bytes, nur_pruefen: bool) -> bool:
    """Schreibt `pfad`, falls nötig. Gibt zurück, ob es eine Abweichung gab."""
    alt = pfad.read_bytes() if pfad.exists() else None
    if alt == neu:
        print(f"gleich     {pfad.relative_to(REPO)}")
        return False
    if nur_pruefen:
        grund = "fehlt" if alt is None else "weicht ab"
        print(f"{grund:10} {pfad.relative_to(REPO)}", file=sys.stderr)
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

    for quelle in RECHNUNG_BEISPIELE:
        pdf_bytes, xml_bytes = erzeuge(quelle)
        if _aktualisiere(ZIEL / f"{quelle.stem}.pdf", pdf_bytes, nur_pruefen):
            abweichungen += 1
        if _aktualisiere(ZIEL / f"{quelle.stem}.xml", xml_bytes, nur_pruefen):
            abweichungen += 1

    if nur_pruefen and abweichungen:
        print(f"\n{abweichungen} Golden-Datei(en) nicht auf Stand — "
              "`python3 scripts/golden_rechnung.py` läuft dagegen.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
