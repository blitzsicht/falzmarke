#!/usr/bin/env python3
"""Traegt die juengsten Aenderungen in die README ein — aus CHANGELOG.md.

Anlass: Viele Projekte fuehren ihren Verlauf in der README, damit man ihn sieht,
ohne eine zweite Datei zu oeffnen. Das ist ein echter Gewinn — aber eine zweite
Fassung derselben Sache driftet auseinander. Dieses Repository hat dafuer schon
ein Muster: docs/ROADMAP.md kommt aus den Issues, die Quellenlage aus
din5008.yaml. Der README-Abschnitt kommt also aus CHANGELOG.md.

    python3 scripts/changelog.py                  # Abschnitt in die README schreiben
    python3 scripts/changelog.py --pruefen        # nur melden, ob er auf dem Stand ist
    python3 scripts/changelog.py --buendeln v0.9.2  # changelog.d/ zur Version buendeln

Uebernommen wird der WORTLAUT der juengsten Versionen, nicht eine Kurzfassung.
Der naheliegende Weg waere gewesen, je Punkt nur den fett gesetzten Anfang zu
zeigen. 19 der 73 Punkte in CHANGELOG.md haben keinen — sie stehen allerdings
alle in v0.2 und v0.3, also ausserhalb dessen, was der Auszug heute zeigt. Eine
solche Kuerzung liefe hier also unbemerkt durch und faellt erst auf, wenn eine
kuenftige Version einen schmucklosen Punkt enthaelt. Genau dafuer steht
tests/test_changelog.py::test_ein_schmuckloser_punkt_ueberlebt_den_auszug.

Angepasst wird allein die Ueberschriftenebene, damit die Gliederung der README
heil bleibt.
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUELLE = REPO / "CHANGELOG.md"
ZIEL = REPO / "README.md"
MARKE_START = "<!-- changelog:anfang -->"
MARKE_ENDE = "<!-- changelog:ende -->"

# Absolut, nicht relativ: Die README wird auch auf PyPI gerendert, und dort
# zeigt ein relativer Verweis ins Leere. tests/test_readme_auf_pypi.py haelt
# das fest — diese Zeile ist einmal dagegen gelaufen.
CHANGELOG_URL = "https://github.com/blitzsicht/falzmarke/blob/main/CHANGELOG.md"

# Zwei Versionen. Mehr macht aus der Produktseite ein Archiv; weniger zeigt
# keine Bewegung. Wer alles will, folgt dem Link auf CHANGELOG.md.
VERSIONEN = 2

# Kleine Zahlen im Fließtext werden ausgeschrieben.
ZAHLWORT = {2: "zwei", 3: "drei", 4: "vier", 5: "fünf"}

VERSION_KOPF = re.compile(r"^## (v\d+\.\d+\.\d+.*)$", re.MULTILINE)

# --- Fragmente -------------------------------------------------------------
#
# CHANGELOG.md hat keinen Ort fuer einen Vorgang ohne Version: Wer eintragen
# will, muesste eine Versionsueberschrift erfinden. Also trug niemand ein — von
# 46 Vorgaengen zwischen v0.8.2 und v0.9.0 hat einer die Datei angefasst, und
# nach dem Nachtragen von Hand waren es bei den naechsten vier wieder null.
#
# Deshalb legt jeder Vorgang seinen Punkt als eigene Datei ab. Kein
# `## Unveroeffentlicht`-Abschnitt: Mehrere Zweige gleichzeitig traefen dort
# dieselben Zeilen, Konflikte waeren der Normalfall statt der Ausnahme
# (Issue #229).

FRAGMENTE = REPO / "changelog.d"

# Die vier Rubriken — die eine Stelle. Sowohl der Buendler unten als auch der
# Pruefer in scripts/changelog_pflicht.py lesen von hier. Derselbe Sollwert an
# zwei Stellen war die Fehlerklasse aus #212: Sie waren gleich, aber nichts
# hielt sie gleich.
#
# Der Bestand kannte fuenf Ueberschriften. "Neu" (8x) und "Hinzugefuegt" (4x)
# meinten dasselbe und sind hier zusammengefuehrt; die Schreibweise im Dateinamen
# ist umlautfrei, damit sie auf jedem Dateisystem gleich heisst.
RUBRIKEN = {
    "neu": "Neu",
    "geaendert": "Geändert",
    "behoben": "Behoben",
    "infrastruktur": "Infrastruktur",
}

FRAGMENT_NAME = re.compile(r"^(?P<vorgang>[A-Za-z0-9_-]+)\.(?P<rubrik>[a-z]+)\.md$")

# Abhaengigkeits-Vorgaenge sind vom Eintrag ausgenommen (ADR 0037) — sie kommen
# im Dutzend und tragen einzeln nichts bei. Die Begruendung dort lautet, sie
# erschienen beim Release als Sammelpunkt. Genau den schrieb niemand: Er stand
# in keiner Anleitung, und kein Werkzeug verlangte ihn. Damit war die Bauart
# wiederhergestellt, gegen die #229 gebaut wurde — eine Erwartung ohne
# Durchsetzung. Jetzt erzeugt ihn `--buendeln` selbst (Issue #233).
#
# Der Anker ist der Autor des Squash-Commits, nicht sein Betreff: Den Betreff
# schreibt beim Merge ein Mensch, den Autor uebernimmt GitHub vom Vorgang. Am
# 02.09.2026 an f626515 gemessen — dort steht `dependabot[bot]`.
#
# Drei Schreibweisen, weil derselbe Bot je nach Kanal anders heisst: `gh pr view`
# meldet `app/dependabot`, git-Autor und REST-API `dependabot[bot]`. Wer nur eine
# eintraegt, baut einen Filter, der nie trifft — und ein nie treffender Filter
# sieht aus wie „keine Aktualisierungen".
BOT_AUTOREN = ("dependabot[bot]", "app/dependabot", "dependabot-preview[bot]")


def bot_vorgaenge(seit: str | None = None, repo: Path | None = None) -> list[str]:
    """Betreffzeilen der Abhaengigkeits-Vorgaenge seit dem letzten Versions-Tag.

    Liest den git-Verlauf, nicht das Netz. Bricht ab, wenn der Verlauf nicht
    lesbar ist: Eine leere Liste aus einem fehlgeschlagenen Aufruf ist von einer
    leeren Liste aus „nichts passiert" nicht zu unterscheiden, und der Unterschied
    entscheidet, ob ein Punkt im Changelog fehlt.
    """
    import subprocess

    def git(*args: str) -> str:
        fertig = subprocess.run(("git", "-C", str(repo or REPO)) + args,
                                capture_output=True, text=True, encoding="utf-8")
        if fertig.returncode != 0:
            raise SystemExit(
                "Der git-Verlauf ist nicht lesbar — „git " + " ".join(args) + "“ "
                f"endete mit {fertig.returncode}:\n{fertig.stderr.strip()}\n\n"
                "Ohne ihn liesse sich nicht sagen, ob seit der letzten Version "
                "Abhängigkeiten aktualisiert wurden. Ein stillschweigend fehlender "
                "Punkt fällt niemandem auf; deshalb hier Abbruch statt leerer Liste."
            )
        return fertig.stdout.strip()

    seit = seit or git("describe", "--tags", "--abbrev=0", "--match", "v*")
    zeilen: list[str] = []
    for autor in BOT_AUTOREN:
        # -F, sonst ist das Muster ein Regex: In `dependabot[bot]` waere `[bot]`
        # eine Zeichenklasse, und der Filter faende nichts. Die leere Liste sieht
        # dann aus wie „keine Aktualisierungen" — gemessen am 02.09.2026:
        # ohne -F null Treffer, mit -F einer (f626515).
        ausgabe = git("log", "-F", f"{seit}..HEAD", f"--author={autor}", "--format=%s")
        zeilen += [z for z in ausgabe.splitlines() if z.strip()]
    return sorted(dict.fromkeys(zeilen))


def sammelpunkt(zeilen: list[str]) -> str | None:
    """Der eine Punkt fuer alle Abhaengigkeits-Vorgaenge — oder None."""
    if not zeilen:
        return None
    if len(zeilen) == 1:
        return f"- **Abhängigkeiten aktualisiert.** {zeilen[0]}"
    return ("- **Abhängigkeiten aktualisiert.**\n"
            + "\n".join(f"  - {z}" for z in zeilen))


def fragment_mangel(pfad: Path) -> str | None:
    """Was an diesem Fragment nicht stimmt — oder None, wenn es taugt.

    Geprueft wird beides, Name und Rumpf. Ein Fragment mit unbekannter Rubrik
    fiele beim Buendeln stillschweigend unter den Tisch, ein leeres erzeugte
    einen leeren Punkt: beides faellt erst auf, wenn die Version schon draussen
    ist.
    """
    treffer = FRAGMENT_NAME.match(pfad.name)
    if not treffer:
        return (f"{pfad.name}: Name muss „<vorgang>.<rubrik>.md“ lauten, "
                f"z. B. „229.infrastruktur.md“.")
    rubrik = treffer.group("rubrik")
    if rubrik not in RUBRIKEN:
        return (f"{pfad.name}: „{rubrik}“ ist keine Rubrik. Gültig: "
                + ", ".join(RUBRIKEN) + ".")
    if not pfad.read_text(encoding="utf-8").strip():
        return f"{pfad.name}: leer. Ein leeres Fragment wird zu einem leeren Punkt."
    return None


def fragmente(verzeichnis: Path = FRAGMENTE) -> list[tuple[str, str, str]]:
    """(rubrik, vorgang, rumpf) je Fragment — in Kanon-Reihenfolge, dann nach Name.

    Bricht ab, sobald eines nicht taugt: Ein uebergangenes Fragment waere ein
    Punkt, den niemand vermisst, weil niemand weiss, dass er fehlt.
    """
    gefunden = sorted(p for p in verzeichnis.glob("*.md") if p.is_file())
    maengel = [m for m in (fragment_mangel(p) for p in gefunden) if m]
    if maengel:
        raise SystemExit("Fragmente in changelog.d/ sind unbrauchbar:\n  "
                         + "\n  ".join(maengel))
    eintraege = []
    for pfad in gefunden:
        treffer = FRAGMENT_NAME.match(pfad.name)
        assert treffer  # oben geprueft
        eintraege.append((treffer.group("rubrik"), treffer.group("vorgang"),
                          pfad.read_text(encoding="utf-8").strip("\n")))
    reihenfolge = list(RUBRIKEN)
    return sorted(eintraege, key=lambda e: (reihenfolge.index(e[0]), e[1]))


def versionen(text: str) -> list[tuple[str, str]]:
    """Zerlegt CHANGELOG.md in (Ueberschrift, Rumpf), juengste zuerst."""
    treffer = list(VERSION_KOPF.finditer(text))
    if not treffer:
        raise SystemExit(
            f"{QUELLE.name} enthält keine Überschrift der Form „## v1.2.3“.\n"
            "Entweder hat sich das Format geändert oder die Datei ist leer — "
            "beides muss auffallen, statt einen leeren Abschnitt zu erzeugen."
        )
    abschnitte = []
    for nummer, kopf in enumerate(treffer):
        ende = treffer[nummer + 1].start() if nummer + 1 < len(treffer) else len(text)
        abschnitte.append((kopf.group(1), text[kopf.end():ende].strip("\n")))
    return abschnitte


def _tiefer(rumpf: str) -> str:
    """Jede Überschrift eine Ebene tiefer — sonst zerschneidet der Auszug die README."""
    return re.sub(r"^(#{1,5}) ", r"#\1 ", rumpf, flags=re.MULTILINE)


def abschnitt() -> str:
    alle = versionen(QUELLE.read_text(encoding="utf-8"))
    gezeigt = alle[:VERSIONEN]
    zeilen = [
        MARKE_START,
        "",
        "## Was sich zuletzt getan hat",
        "",
        f"Die {'letzte Version' if len(gezeigt) == 1 else 'letzten ' + ZAHLWORT.get(len(gezeigt), str(len(gezeigt))) + ' Versionen'}"
        f" im Wortlaut. **Erzeugt aus [`CHANGELOG.md`]({CHANGELOG_URL}) — dort ändern, dann"
        " `python3 scripts/changelog.py`.**",
        "",
    ]
    for kopf, rumpf in gezeigt:
        zeilen += [f"### {kopf}", "", _tiefer(rumpf), ""]
    aeltere = len(alle) - len(gezeigt)
    if aeltere:
        zeilen += [
            f"Davor liegen {aeltere} weitere Versionen — der vollständige Verlauf steht in"
            f" [`CHANGELOG.md`]({CHANGELOG_URL}).",
            "",
        ]
    zeilen.append(MARKE_ENDE)
    return "\n".join(zeilen)


def eingesetzt(text: str) -> str:
    neu = abschnitt()
    if MARKE_START in text and MARKE_ENDE in text:
        vorher = text[: text.index(MARKE_START)]
        nachher = text[text.index(MARKE_ENDE) + len(MARKE_ENDE):]
        return vorher + neu + nachher
    # Ans Ende zu haengen waere falsch: Der Verlauf gehoert vor die Lizenz, nicht
    # dahinter. Wer den Abschnitt neu anlegt, setzt die Marken selbst.
    raise SystemExit(
        f"In {ZIEL.name} fehlen die Marken {MARKE_START} und {MARKE_ENDE}.\n"
        "Beide dort einsetzen, wo der Abschnitt stehen soll — vor „## Lizenz“."
    )


def gebuendelt(version: str, datum: str, verzeichnis: Path = FRAGMENTE,
               zusatz: str | None = None) -> str:
    """Der Versionsabschnitt aus den Fragmenten — schreibt nichts.

    `zusatz` ist der Sammelpunkt der Abhaengigkeits-Vorgaenge. Er kommt als
    Argument herein statt aus dem git-Verlauf, damit diese Funktion rein bleibt:
    gleiche Eingabe, gleiche Ausgabe, kein Unterprozess. Beschafft wird er in
    `buendeln()`.
    """
    eintraege = fragmente(verzeichnis)
    if not eintraege and not zusatz:
        raise SystemExit(
            f"{verzeichnis.name}/ ist leer — es gibt nichts zu bündeln.\n"
            "Eine Version ohne einen einzigen Punkt wäre ein leerer Abschnitt, "
            "und der fällt erst auf, wenn sie draußen ist."
        )
    zeilen = [f"## {version} — {datum}", ""]
    letzte_rubrik = None
    for rubrik, _vorgang, rumpf in eintraege:
        if rubrik != letzte_rubrik:
            zeilen += [f"### {RUBRIKEN[rubrik]}", ""]
            letzte_rubrik = rubrik
        zeilen += [rumpf, ""]
    if zusatz:
        # Ans Ende von „Infrastruktur" — der Rubrik, unter der solche Punkte
        # seit jeher stehen. Fehlt sie, wird sie hier angelegt; sie ist die
        # letzte im Kanon, also stimmt die Reihenfolge in beiden Faellen.
        if letzte_rubrik != "infrastruktur":
            zeilen += [f"### {RUBRIKEN['infrastruktur']}", ""]
        zeilen += [zusatz, ""]
    return "\n".join(zeilen)


def buendeln(version: str, datum: str | None = None,
             verzeichnis: Path = FRAGMENTE, quelle: Path = QUELLE) -> int:
    """Fragmente zu einem Versionsabschnitt in CHANGELOG.md — und dann weg.

    Die Fragmente werden geloescht, weil sie sonst bei der naechsten Version ein
    zweites Mal erschienen. Sie stehen ab jetzt im Changelog; das ist die Quelle.
    """
    if not version.startswith("v"):
        version = f"v{version}"
    datum = datum or datetime.date.today().strftime("%d.%m.%Y")
    eintraege = fragmente(verzeichnis)
    zusatz = sammelpunkt(bot_vorgaenge())
    abschnitt_neu = gebuendelt(version, datum, verzeichnis, zusatz)

    text = quelle.read_text(encoding="utf-8")
    treffer = VERSION_KOPF.search(text)
    if not treffer:
        raise SystemExit(f"{quelle.name} enthält keine Versionsüberschrift.")
    if f"## {version} " in text:
        raise SystemExit(
            f"{quelle.name} kennt {version} schon. Eine Versionsnummer wird nie "
            "wiederverwendet — auf PyPI ist sie unwiderruflich belegt (ADR 0036)."
        )
    quelle.write_text(
        text[: treffer.start()] + abschnitt_neu + "\n" + text[treffer.start():],
        encoding="utf-8",
    )
    uebernommen = len(eintraege)
    for pfad in sorted(verzeichnis.glob("*.md")):
        pfad.unlink()
    rubriken = sorted({r for r, _, _ in eintraege}, key=list(RUBRIKEN).index)
    print(f"OK  {quelle.name} trägt {version} — "
          f"{uebernommen} {'Punkt' if uebernommen == 1 else 'Punkte'} aus "
          f"{verzeichnis.name}/ in {len(rubriken)} "
          f"{'Rubrik' if len(rubriken) == 1 else 'Rubriken'} "
          f"({', '.join(RUBRIKEN[r] for r in rubriken) or 'keine'})")
    if zusatz:
        print("    dazu ein Sammelpunkt für die Abhängigkeits-Vorgänge "
              "aus dem git-Verlauf")
    return 0


def main() -> int:
    if "--buendeln" in sys.argv:
        stelle = sys.argv.index("--buendeln")
        if stelle + 1 >= len(sys.argv):
            raise SystemExit(
                "--buendeln braucht die Version, z. B. „--buendeln v0.9.2“."
            )
        buendeln(sys.argv[stelle + 1])
        # Weiter im Standardpfad: Der Auszug in der README muss die frisch
        # gebuendelte Version zeigen, sonst steht sie nur in CHANGELOG.md.
    text = ZIEL.read_text(encoding="utf-8")
    neu = eingesetzt(text)
    if "--pruefen" in sys.argv:
        if neu != text:
            print(f"{ZIEL.name} ist nicht auf dem Stand von {QUELLE.name} — "
                  "python3 scripts/changelog.py ausführen.", file=sys.stderr)
            return 1
        print(f"{ZIEL.name} ist aktuell.")
        return 0
    ZIEL.write_text(neu, encoding="utf-8")
    gezeigt = versionen(QUELLE.read_text(encoding="utf-8"))[:VERSIONEN]
    print(f"OK  {ZIEL.relative_to(REPO)} zeigt "
          + ", ".join(kopf.split(" ")[0] for kopf, _ in gezeigt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
