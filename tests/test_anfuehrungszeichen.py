"""Eine deutsche Anführung schließt mit “, nicht mit dem geraden Zeichen (#436).

WARUM ES DAS GIBT

Am 29.10.2026 war im Repo etwa jede zweite deutsche Anführung mit dem geraden
Zeichen geschlossen: 471 in Markdown, 912 über Markdown, Python und YAML. Das
öffnende „ stimmte fast immer, das schließende selten. Ein Hausstil war das nicht,
keine der beiden Fassungen überwog. Betroffen waren auch Meldungen, die auf dem
Bildschirm landen. Am 03.11.2026 wurden 1126 Stellen angeglichen. Ohne Prüfung
stünde derselbe Befund in drei Monaten wieder da.

WAS GEPRÜFT WIRD

Jede versionierte Textdatei (Markdown, YAML, Shell, HTML, Typst, Python). Ein
Treffer ist ein „, auf das vor dem nächsten „ oder “ ein gerades Zeichen folgt,
auch über einen Zeilenumbruch, aber nicht über eine Leerzeile hinweg.

In Python zählt nur, was in einem Kommentar oder im *Inhalt* eines Strings
steht. Das gerade Zeichen, das einen String beendet, gehört nicht zur Prosa: In
`scripts/quellenlage.py` endet ein Teilstring direkt hinter „mehrfach, der nächste
beginnt mit „bestätigt“ und schließt die Anführung richtig. Eine Textsuche hielte genau diese Stelle für einen Rückfall,
und eine Ersetzung nach ihr hätte den String zerbrochen. Deshalb liest die
Prüfung den Quelltext über `tokenize`, nicht als Text.

Die Gegenproben unten sabotieren je eine echte Datei an genau einer Stelle.
"""

from __future__ import annotations

import io
import re
import subprocess
import tokenize

import pytest

from conftest import REPO

GERADE = chr(34)          # das gerade Zeichen; als Literal träfe die Prüfung sich selbst

#: „…, dann ein gerades Zeichen. Ein Zeilenumbruch darf dazwischen liegen, eine
#: Leerzeile nicht, auch keine leere Kommentarzeile (`#` allein).
TREFFER = re.compile("„(?:[^„“\"\\n]|\\n(?![ \\t]*(?:#[ \\t]*)?\\r?\\n))*\"")

ENDUNGEN = {".md", ".py", ".yaml", ".yml", ".sh", ".html", ".typ"}
_PREFIX = re.compile(r"^([rRbBuUfFtT]*)('''|\"\"\"|'|\")")


def _offsets(text: str):
    anfaenge, pos = [0], 0
    for zeile in text.splitlines(keepends=True):
        pos += len(zeile)
        anfaenge.append(pos)
    return lambda stelle: anfaenge[stelle[0] - 1] + stelle[1]


def prosa_bereiche(text: str) -> list[tuple[int, int]]:
    """(anfang, ende) je Kommentar und String-Inhalt, ohne die Delimiter."""
    off = _offsets(text)
    bereiche: list[tuple[int, int]] = []
    offene_fstrings: list[tuple[int, str]] = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            bereiche.append((off(tok.start), off(tok.end)))
        elif tok.type == tokenize.STRING:
            m = _PREFIX.match(tok.string)
            kopf, delim = len(m.group(1)) + len(m.group(2)), len(m.group(2))
            bereiche.append((off(tok.start) + kopf, off(tok.end) - delim))
        elif tok.type == getattr(tokenize, "FSTRING_START", None):
            offene_fstrings.append((off(tok.start) + len(tok.string), tok.string))
        elif tok.type == getattr(tokenize, "FSTRING_END", None):
            anfang, _ = offene_fstrings.pop()
            bereiche.append((anfang, off(tok.end) - len(tok.string)))
    return bereiche


def _in_kommentaren(text: str, a: int, e: int, bereiche) -> bool:
    """Über mehrere `#`-Zeilen: außerhalb der Kommentare steht nur Leerraum."""
    kommentare = [(x, y) for x, y in bereiche if text[x:x + 1] == "#"]
    innen = lambda i: any(x <= i < y for x, y in kommentare)
    return innen(a) and innen(e - 1) and all(
        text[i].isspace() or innen(i) for i in range(a, e))


def stellen(pfad: str, text: str) -> list[str]:
    """Jeder Rückfall als „pfad:zeile: auszug“."""
    treffer = list(TREFFER.finditer(text))
    if pfad.endswith(".py") and treffer:
        bereiche = prosa_bereiche(text)
        treffer = [m for m in treffer
                   if any(x <= m.start() and m.end() <= y for x, y in bereiche)
                   or _in_kommentaren(text, m.start(), m.end(), bereiche)]
    return [f"{pfad}:{text.count(chr(10), 0, m.start()) + 1}: "
            + " ⏎ ".join(z.strip() for z in m.group().splitlines())[:120]
            for m in treffer]


def versionierte_texte() -> dict[str, str]:
    ausgabe = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True,
                             check=True).stdout.decode("utf-8")
    texte = {}
    for pfad in filter(None, ausgabe.split("\0")):
        datei = REPO / pfad
        if datei.suffix in ENDUNGEN and datei.is_file():
            texte[pfad] = datei.read_text(encoding="utf-8")
    return texte


@pytest.fixture(scope="module")
def texte() -> dict[str, str]:
    return versionierte_texte()


# ── Der Befund ──────────────────────────────────────────────────────────────

def test_keine_anfuehrung_schliesst_gerade(texte):
    funde = [s for pfad, text in texte.items() for s in stellen(pfad, text)]
    assert not funde, ("Gerade geschlossen, statt mit “:\n  " + "\n  ".join(funde))


def test_die_pruefung_sieht_etwas(texte):
    """Kann sie überhaupt rot werden? Nur, wenn sie Dateien und Anführungen sieht."""
    assert len(texte) > 300 and any(p.endswith(".py") for p in texte)
    richtig = sum(t.count("“") for t in texte.values())
    assert richtig > 1000, f"nur {richtig} richtig geschlossene Anführungen gesehen"


# ── Gegenproben: je eine echte Datei, an genau einer Stelle sabotiert ──────

def _sabotiert(texte, pfad: str, alt: str, neu: str) -> str:
    text = texte[pfad]
    assert text.count(alt) == 1, f"„{alt}“ steht nicht genau einmal in {pfad}"
    assert not stellen(pfad, text), "Kontrolle: unsabotiert ohne Befund"
    return text.replace(alt, neu)


@pytest.mark.parametrize("pfad, alt", [
    ("skill/references/stil.md", "„…“ sind hier richtig gesetzt"),
    ("skill/falzmarke/regeln/quellen.yaml", "„experimentellen“"),
    ("scripts/pruefe-video.sh", "„Messen statt behaupten“"),
    ("skill/falzmarke/typst/falzmarke.typ", "„0.92 Zeilen“"),
])
def test_gegenprobe_ein_rueckfall_in_einer_textdatei_wird_gemeldet(texte, pfad, alt):
    text = _sabotiert(texte, pfad, alt, alt.replace("“", GERADE))
    assert len(stellen(pfad, text)) == 1


def test_gegenprobe_ein_rueckfall_ueber_einen_zeilenumbruch_wird_gemeldet(texte):
    text = _sabotiert(texte, "skill/falzmarke/regeln/quellen.yaml",
                      "Variante A, der „nur eine einzige Interpretation der Norm“",
                      "Variante A, der „nur eine einzige\n      Interpretation der Norm" + GERADE)
    assert len(stellen("skill/falzmarke/regeln/quellen.yaml", text)) == 1


def test_gegenprobe_eine_leerzeile_trennt(texte):
    """Ein „ allein und ein gerades Zeichen im nächsten Absatz sind keine Anführung."""
    text = "Das Zeichen „ steht hier allein.\n\nDann folgt `" + GERADE + "` als Code.\n"
    assert stellen("x.md", text) == []
    assert stellen("x.md", text.replace("\n\n", "\r\n\r\n")) == [], "Windows-Zeilenenden"
    assert len(stellen("x.md", text.replace("\n\n", " "))) == 1, "ohne Leerzeile ein Treffer"


#: Im `"`-String ist der Rückfall `\\"`; ein nacktes gerades Zeichen beendete
#: dort den String, und das wäre ein Syntaxfehler, kein Rückfall.
MASKIERT = "\\" + GERADE


@pytest.mark.parametrize("pfad, alt, zu", [
    ("scripts/closing_keyword.py", "Ein „Closes #99“ neben", GERADE),            # Kommentar
    ("scripts/closing_keyword.py", "Linking a\n# pull request to an issue“", GERADE),
    ("skill/falzmarke/eml.py", "„schaut nach Behoerde\n        # aus“", GERADE),
    ("tests/test_closing_keyword.py", "neben „Schließt #261“ ist kein", GERADE),   # Docstring
    ("scripts/offene_paare.py", "Spalte „Folge“\\n> rechnet", MASKIERT),        # String
    ("tests/test_email_beispiele.py", "sagt „{_anzahl_in_der_doku()}“", MASKIERT),  # f-String
])
def test_gegenprobe_ein_rueckfall_in_python_wird_gemeldet(texte, pfad, alt, zu):
    text = _sabotiert(texte, pfad, alt, alt.replace("“", zu))
    assert len(stellen(pfad, text)) == 1


def test_gegenprobe_ein_stringende_ist_kein_rueckfall(texte):
    """Die Stelle, an der eine Textsuche danebenläge: Hinter „mehrfach endet der String."""
    pfad = "scripts/quellenlage.py"
    text = texte[pfad]
    zeile = "hebt eine Regel aber nie auf „mehrfach" + GERADE + ","
    assert zeile in text
    assert "„mehrfach" + GERADE in [m.group() for m in TREFFER.finditer(text)], \
        "Kontrolle: die bloße Textsuche träfe die Stelle"
    assert stellen(pfad, text) == []
