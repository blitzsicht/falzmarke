"""Eine Vorlage plus Datenquelle ergibt n Briefe (Issue #3).

    falzmarke serie vorlage.md --daten empfaenger.csv --ziel briefe/

## Die Platzhaltersyntax und warum sie so aussieht

`{{spalte}}`. Drei Bedingungen musste sie erfüllen, und die letzte hat die
Entscheidung getragen:

* **Sie darf nicht mit Typst kollidieren.** Typst führt Code mit `#` ein; `{{`
  hat dort keine Bedeutung. `${…}` wäre ebenfalls frei gewesen, `#{…}` nicht.
* **Sie muss in der Vorlage sichtbar bleiben.** Wer `vorlage.md` öffnet, soll
  sehen, was gefüllt wird. Ein unsichtbarer Mechanismus — etwa ein Feld im
  Frontmatter, das auf Spalten zeigt — verlöre genau das.
* **Sie muss den Markdown-Parser unbeschadet überstehen.** Geschweifte Klammern
  sind in CommonMark bedeutungslos; `[[…]]` und `*…*` wären es nicht.

## Der Wert wird nie zu Markup

Das ist die wichtigste Entscheidung hier, und sie folgt derselben Überlegung wie
in `emit.py`: **Eine Fehlerklasse wird geschlossen, nicht verkleinert.**

Der naheliegende Weg wäre, `{{name}}` im Rohtext zu ersetzen und den Wert vorher
zu maskieren. Dann steht in der Maskierliste `*`, `_`, `#`, `[`, `` ` `` — und
irgendwann fehlt eines. Ein Empfänger namens `Müller & Söhne *GmbH*` stünde
kursiv im Brief, ein Wert mit `#` würde zur Überschrift.

Stattdessen wird **nach** dem Parsen ersetzt, im Baum. Der Platzhalter ist dort
gewöhnlicher Text; was an seine Stelle tritt, ist es auch. Ein Wert kann kein
Markup mehr werden, weil er nie durch den Parser läuft.

Aus demselben Grund läuft die Typografie nicht über ihn: Aus `Müller -- Söhne`
darf kein Halbgeviertstrich werden, und aus `"Zitat"` keine typografischen
Anführungszeichen. Das sind Daten, kein Fließtext — der Text-Knoten wird dafür
in drei geteilt.

## Ein Datensatz, ein Ergebnis

Bricht ein Datensatz ab, läuft die Serie weiter. Am Ende steht, welche Zeile
warum nicht ging. Der umgekehrte Weg — die ganze Serie anhalten — wäre bei
200 Empfängern und einem zu langen Namen die falsche Antwort.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from falzmarke import baum as baum_modul

#: `{{spalte}}` — Buchstaben, Ziffern, Unterstrich, Bindestrich.
#:
#: Kein Punkt und keine Klammern: Ein Platzhalter zeigt auf eine Spalte, nicht
#: auf einen Ausdruck. Wer rechnen will, rechnet in der Datenquelle.
PLATZHALTER = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\s*\}\}")


class Seriefehler(ValueError):
    """Etwas stimmt an der Vorlage oder der Datenquelle als Ganzes nicht.

    Abzugrenzen von einem Fehler in EINEM Datensatz — der bricht nur diesen ab
    und steht am Ende im Bericht.
    """


@dataclass
class Ergebnis:
    """Was aus einem Datensatz wurde."""

    zeile: int
    name: str
    pfad: Path | None = None
    fehler: str = ""

    @property
    def ok(self) -> bool:
        return self.pfad is not None and not self.fehler


@dataclass
class Bericht:
    ergebnisse: list[Ergebnis] = field(default_factory=list)

    @property
    def geschrieben(self) -> list[Ergebnis]:
        return [e for e in self.ergebnisse if e.ok]

    @property
    def gescheitert(self) -> list[Ergebnis]:
        return [e for e in self.ergebnisse if not e.ok]

    @property
    def ok(self) -> bool:
        return not self.gescheitert

    def als_text(self) -> str:
        zeilen = [f"FEHL  Zeile {e.zeile}: {e.fehler}" for e in self.gescheitert]
        zeilen.append(
            f"serie: {len(self.geschrieben)}/{len(self.ergebnisse)} Briefe geschrieben")
        return "\n".join(zeilen)


# ── Die Datenquelle ─────────────────────────────────────────────────────────

def lies_daten(pfad: Path) -> list[dict]:
    """CSV oder JSON — erkannt an der Endung, nicht am Inhalt.

    Am Inhalt zu raten wäre hier die schlechtere Wahl: Eine CSV-Datei mit einer
    einzigen Spalte namens `[` sähe aus wie JSON, und der Fehler fiele erst bei
    der Ausgabe auf.

    Die CSV wird mit `utf-8-sig` gelesen: Excel schreibt eine Byte-Order-Mark,
    und ohne diese Angabe hiesse die erste Spalte `\\ufeffanrede` statt `anrede`.
    Gemessen — der Fall kostet sonst eine halbe Stunde Suche.
    """
    if not pfad.is_file():
        raise Seriefehler(f"{pfad} gibt es nicht.")

    endung = pfad.suffix.lower()
    if endung == ".json":
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        if not isinstance(daten, list):
            raise Seriefehler(
                f"{pfad.name}: erwartet wird eine Liste von Datensätzen, "
                f"gefunden {type(daten).__name__}.")
        for nummer, satz in enumerate(daten, start=1):
            if not isinstance(satz, dict):
                raise Seriefehler(f"{pfad.name}: Datensatz {nummer} ist kein Objekt.")
        return [{k: "" if v is None else str(v) for k, v in satz.items()} for satz in daten]

    if endung == ".csv":
        with pfad.open(encoding="utf-8-sig", newline="") as offen:
            leser = csv.DictReader(offen)
            if not leser.fieldnames:
                raise Seriefehler(f"{pfad.name}: keine Kopfzeile gefunden.")
            leer = [n for n in leser.fieldnames if not (n or "").strip()]
            if leer:
                raise Seriefehler(
                    f"{pfad.name}: die Kopfzeile hat eine Spalte ohne Namen — "
                    "ein Platzhalter könnte nicht darauf zeigen.")
            return [{k: (v or "") for k, v in satz.items()} for satz in leser]

    raise Seriefehler(
        f"{pfad.name}: unbekannte Endung `{endung or '(keine)'}`. "
        "Erwartet wird `.csv` oder `.json`.")


# ── Die Vorlage ─────────────────────────────────────────────────────────────

def platzhalter(text: str) -> set[str]:
    """Alle Namen, die in diesem Text vorkommen."""
    return {m.group(1) for m in PLATZHALTER.finditer(text)}


def pruefe_vorlage(namen: set[str], spalten: set[str]) -> None:
    """Zeigt jeder Platzhalter auf eine Spalte?

    Gemeldet wird **vor** dem ersten Brief, nicht bei jedem einzelnen: Ein
    Tippfehler in der Vorlage betrifft alle 200 Datensätze, und 200-mal
    dieselbe Meldung ist keine Hilfe.

    Die Gegenrichtung ist ausdrücklich KEIN Fehler: Eine Spalte, auf die kein
    Platzhalter zeigt, ist im Serienbrief unbenutzt — das ist bei einer
    Adressliste der Normalfall, nicht ein Versehen.
    """
    fehlend = sorted(namen - spalten)
    if fehlend:
        raise Seriefehler(
            "Diese Platzhalter haben keine Spalte: "
            + ", ".join(f"`{{{{{n}}}}}`" for n in fehlend)
            + "\nVorhanden sind: " + ", ".join(sorted(spalten)))


def fuelle_text(text: str, satz: dict) -> str:
    """Platzhalter in einem einzelnen Wert ersetzen — für das Frontmatter.

    Hier ist die Ersetzung im Rohtext richtig: Ein YAML-Wert ist bereits Text
    und läuft nie durch den Markdown-Parser. Im **Brieftext** wäre sie es nicht
    — siehe `fuelle_bloecke`.
    """
    return PLATZHALTER.sub(lambda m: satz.get(m.group(1), ""), text)


def fuelle_kopf(kopf, satz: dict):
    """Dasselbe rekursiv über das ganze Frontmatter."""
    if isinstance(kopf, str):
        return fuelle_text(kopf, satz)
    if isinstance(kopf, dict):
        return {k: fuelle_kopf(v, satz) for k, v in kopf.items()}
    if isinstance(kopf, list):
        return [fuelle_kopf(v, satz) for v in kopf]
    return kopf


def fuelle_bloecke(bloecke, satz: dict):
    """Platzhalter im **geprüften Baum** ersetzen.

    Der Kern der Sache: Was hier eingesetzt wird, ist bereits Text und wird nie
    wieder geparst. Ein Wert wie `Müller & Söhne *GmbH*` bleibt genau das —
    kein Kursivsatz, keine Überschrift, keine Aufzählung.

    Der Text-Knoten wird dafür geteilt: Was um den Platzhalter steht, ist
    Fließtext und geht durch die Typografie; der Wert selbst nicht. Aus
    `Müller -- Söhne` darf kein Halbgeviertstrich werden.
    """
    return tuple(_fuelle_knoten(b, satz) for b in bloecke)


def _fuelle_knoten(knoten, satz: dict):
    if isinstance(knoten, baum_modul.Text):
        return _teile_text(knoten, satz)
    if isinstance(knoten, tuple):
        return tuple(_flach(_fuelle_knoten(k, satz) for k in knoten))
    for feld in ("kinder", "punkte"):
        if hasattr(knoten, feld):
            gefuellt = tuple(_flach(_fuelle_knoten(k, satz) for k in getattr(knoten, feld)))
            knoten = _ersetze_feld(knoten, feld, gefuellt)
    if isinstance(knoten, baum_modul.Tabelle):
        knoten = _ersetze_feld(knoten, "zeilen", tuple(
            tuple(tuple(_flach(_fuelle_knoten(z, satz) for z in zelle)) for zelle in zeile)
            for zeile in knoten.zeilen))
    if isinstance(knoten, baum_modul.Wortlaut):
        # Ein wortgetreuer Auszug bleibt wortgetreu — auch hier. Wer einen
        # Platzhalter in einen Auszug schreibt, zitiert etwas, das so nie
        # dastand; das ist genau die Änderung, die dieses Werkzeug nicht macht.
        return knoten
    return knoten


def _flach(knoten_folge):
    """Ein geteilter Text-Knoten ergibt mehrere — die Folge wird flach."""
    for k in knoten_folge:
        if isinstance(k, tuple):
            yield from k
        else:
            yield k


def _ersetze_feld(knoten, feld: str, wert):
    from dataclasses import replace

    return replace(knoten, **{feld: wert})


def _teile_text(knoten, satz: dict):
    """Ein Text-Knoten mit Platzhaltern wird zu mehreren.

    `Sehr geehrte {{anrede}} {{name}},` ergibt fünf Knoten — drei aus der
    Vorlage (mit Typografie) und zwei aus den Daten (ohne). Ohne die Teilung
    liefe die Typografie über den Wert, und ein Firmenname mit `--` käme mit
    einem Halbgeviertstrich im Brief an.
    """
    inhalt = knoten.inhalt
    if not PLATZHALTER.search(inhalt):
        return knoten

    teile = []
    stelle = 0
    for treffer in PLATZHALTER.finditer(inhalt):
        davor = inhalt[stelle:treffer.start()]
        if davor:
            teile.append(baum_modul.Text(davor, typografie=knoten.typografie))
        wert = satz.get(treffer.group(1), "")
        if wert:
            teile.append(baum_modul.Text(wert, typografie=False))
        stelle = treffer.end()
    rest = inhalt[stelle:]
    if rest:
        teile.append(baum_modul.Text(rest, typografie=knoten.typografie))
    return tuple(teile) if teile else baum_modul.Text("", typografie=False)


# ── Dateinamen ──────────────────────────────────────────────────────────────

#: Was in einem Dateinamen nichts zu suchen hat. Bewusst eine Positivliste in
#: der Umkehrung: Alles, was kein Buchstabe, keine Ziffer und kein Bindestrich
#: ist, wird ersetzt. Eine Sperrliste vergisst `:` auf macOS oder `?` auf
#: Windows — und der Fehler fällt erst auf dem anderen System auf.
UNGEEIGNET = re.compile(r"[^A-Za-z0-9ÄÖÜäöüß-]+")


def dateiname(satz: dict, nummer: int, spalte: str | None = None) -> str:
    """Wie der Brief für diesen Datensatz heißt.

    Führende Nummer, damit die Reihenfolge der Datenquelle im Ordner sichtbar
    bleibt — und damit zwei Empfänger gleichen Namens sich nicht überschreiben.
    Das ist bei einer Adressliste kein Randfall.
    """
    stamm = str(satz.get(spalte, "") if spalte else "").strip()
    sauber = UNGEEIGNET.sub("-", stamm).strip("-").lower()[:60]
    return f"{nummer:03d}-{sauber}" if sauber else f"{nummer:03d}"
