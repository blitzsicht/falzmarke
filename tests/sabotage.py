"""Eine Funktion aus ihrem eigenen Quelltext neu übersetzt, mit genau einer Änderung.

Für Gegenproben, die nicht eine ganze Funktion durch einen Nachbau ersetzen,
sondern eine einzelne Zeile im heutigen Code kippen (#442, N5). Der Nachbau
belegt nur, dass eine Probe den alten Code erkennt. Die gekippte Zeile belegt,
dass sie anschlägt, wenn der heutige Code an genau dieser Stelle bricht.

Die Zeilennummern bleiben die der Datei (#468): Bis dahin wurde ab Zeile 1
übersetzt, und ein Traceback unter Sabotage zeigte auf den Modulkopf statt auf
die Zeile, die gekippt war. Ändert `neu` die Zahl der Zeilen, verschieben sich
nur die Nummern hinter der Ersetzung.
"""

from __future__ import annotations

import __future__
import ast
import inspect
import textwrap


def zeile_ersetzt(modul, name: str, alt: str, neu: str):
    """`modul.name`, übersetzt mit `alt` → `neu`. `alt` muss genau einmal vorkommen.

    `name` darf eine Methode sein (`"Postfach.suche_kennung"`). Zurück kommt dann
    die bloße Funktion, gesetzt wird sie mit `monkeypatch.setattr` an der Klasse.
    Ihre Globals bleiben die des Moduls, nicht die der Klasse.

    Grenzen (Nachreview von #479, gemessen am 04.11.2026): `alt` wird im Quelltext
    ohne die Einrückung der Klasse gesucht, so, als stünde die Methode auf
    Modulebene. Ein `super()` ohne Argumente trägt nicht: Außerhalb des
    Klassenrumpfs fehlt die Zelle `__class__`, Python meldet beim Aufruf
    `RuntimeError: super(): __class__ cell not found`.
    """
    ziel = modul
    for teil in name.split("."):
        ziel = getattr(ziel, teil)
    zeilen, erste = inspect.getsourcelines(ziel)
    quelle = textwrap.dedent("".join(zeilen))
    assert quelle.count(alt) == 1, f"„{alt.strip()}“ steht nicht genau einmal in {name}"
    baum = ast.parse(quelle.replace(alt, neu))
    ast.increment_lineno(baum, erste - 1)
    raum: dict = {}
    exec(compile(baum, inspect.getsourcefile(modul), "exec",
                 flags=__future__.annotations.compiler_flag, dont_inherit=True),
         modul.__dict__, raum)
    return raum[name.rpartition(".")[2]]
