"""Die Doku sagt, was der Typografie-Pass tatsächlich tut (#331).

WARUM ES DAS GIBT

`typografie.anwenden()` setzt geschützte Leerzeichen nur dort, wo die Regel
mehrfach belegt ist (`_abkuerzungen`, `_datum`). `_einheiten` (`10 %`, `5 kg`)
und `_vor_angabe` (`Tel.`, `Nr.`) stehen auf `einzeln_belegt` und ändern den
Text nicht — seit #330 meldet `lint` dort eine Warnung. README, SKILL.md und
`references/markdown.md` sagten weiter, der Pass setze sie alle von selbst.
Wer SKILL.md las, hielt die Warnung für überflüssig.

WAS HIER GEMESSEN WIRD

* AC 1: Kein Absatz verspricht ein Setzen, ohne die Warnung zu nennen; und jede
  der drei Dateien sagt, welche Schritte nur gemeldet werden.
* AC 1 („und warum"): Derselbe Absatz nennt den Grund — die Regel ist nur
  einzeln belegt.
* AC 2: Die Auskunft ist die Warnung, nicht bloß „setzt nicht“.
* AC 3: Eine Zahl über die Schritte trägt ein Datum im selben Absatz.

WAS „ZURÜCKGEHALTEN“ HEISST, STEHT NICHT HIER

Welche Schritte zurückgehalten werden, wird aus den Daten gelesen
(`regeln.darf_automatisch_ersetzen`), nicht in diesem Test festgeschrieben.
Kippt die Quellenlage (#31), ändert sich, was die Doku sagen muss — und die
Proben unten werden rot, bis sie nachzieht. Eine Doku, die von Hand altert,
war der Anlass.

Gemessen wird am **Absatz** (bzw. an der Tabellenzeile oder dem Listenpunkt),
nicht an der Datei: Ein „Warnung“ irgendwo auf der Seite hält keinen falschen
Satz in einer Tabelle zurecht.
"""

from __future__ import annotations

import re

import pytest

from falzmarke import regeln, typografie
from conftest import REPO

#: Die drei Stellen aus dem Befund. Der Verlauf im README bleibt außen vor:
#: Dort steht die alte Aussage zu Recht, als Zitat dessen, was korrigiert wurde.
DOKUS = ["README.md", "skill/SKILL.md", "skill/references/markdown.md"]

WARNUNG = re.compile(r"warn", re.I)

#: Worum es geht. Ohne diese Eingrenzung träfe die Suche jedes `10 %` im
#: Handbuch — auch das in `- 5 °C`, das vom Listenmarker handelt.
THEMA = re.compile(r"Leerzeichen|Typografie|Einheit|zusammen|ersetz|\bPass\b")

#: Was der Beleg für die Zurückhaltung sagt: nur eine Quelle, deshalb nicht
#: selbsttätig. Dieselben Wörter trägt die Meldung des Linters.
GRUND = re.compile(r"einzeln|einzig|Quelle|mehrfach|automatisch", re.I)

#: Ein Absatz, der ein Setzen zusagt.
ZUSAGE = re.compile(r"geschützt\w*\s+Leerzeichen")
VERB = re.compile(r"selbst|bekommen|automatisch|setzt", re.I)

#: Je Schritt: woran man ihn in der Doku erkennt — als Beispiel in Code-Spannen
#: (aus den Mustern des Passes abgeleitet, nicht ein zweites Mal geführt) und
#: als Wort im Fließtext. Ein neuer Schritt ohne Eintrag lässt die Probe
#: unten rot werden, statt still ungeprüft zu bleiben.
_MONATE = "|".join(typografie.MONATE)
BEISPIEL = {
    "_abkuerzungen": re.compile("|".join(p for p, _ in typografie.ABKUERZUNGEN)),
    "_datum": re.compile(rf"\d{{1,2}}\.\s+(?:{_MONATE})"),
    "_einheiten": re.compile(
        r"\d\s+(?:" + "|".join(re.escape(e) for e in typografie.EINHEITEN) + r")(?!\w)"),
    "_vor_angabe": re.compile(
        r"(?<![\w.])(?:" + "|".join(re.escape(k) for k in typografie.VOR_ANGABE) + r")(?!\w)"),
}
WORT = {
    "_abkuerzungen": re.compile(r"Abkürzung"),
    "_datum": re.compile(r"Datum|Tag und Monat"),
    "_einheiten": re.compile(r"Einheit|Zahlwert|Prozent"),
    "_vor_angabe": re.compile(r"Kürzel|Telefon|Rechnungsnummer"),
}

CODE = re.compile(r"`([^`]+)`")


def zurueckgehalten() -> list[str]:
    """Die Schritte, die der Pass heute nicht ausführt — aus den Daten gelesen."""
    return [name for _, name in typografie.SCHRITTE
            if name and not regeln.darf_automatisch_ersetzen(name)]


def nennt(block: str, schritt: str) -> bool:
    """Nennt der Absatz ein Beispiel dieses Schritts (in Backticks) oder sein Wort?"""
    spannen = CODE.findall(block)
    return (any(BEISPIEL[schritt].search(s) for s in spannen)
            or bool(WORT[schritt].search(block)))


def nennt_zurueckgehaltenes(block: str) -> bool:
    return any(nennt(block, s) for s in zurueckgehalten())


def bloecke(text: str) -> list[str]:
    """Absätze, Tabellenzeilen, Listenpunkte und Überschriften — je einer.

    Umbrüche im Fließtext sind Leerzeichen (Markdown bricht frei um); Code-Zäune
    fallen weg, dort steht Beispieltext und keine Aussage.
    """
    ergebnis: list[str] = []
    aktuell: list[str] = []
    im_zaun = False

    def schliessen():
        if aktuell:
            ergebnis.append(" ".join(aktuell))
            aktuell.clear()

    for zeile in text.splitlines():
        s = zeile.strip().lstrip(">").strip()
        if s.startswith("```"):
            schliessen()
            im_zaun = not im_zaun
            continue
        if im_zaun:
            continue
        if not s:
            schliessen()
        elif s.startswith(("|", "#")):
            schliessen()
            ergebnis.append(s)
        elif re.match(r"([-*]|\d+\.)\s", s):
            schliessen()
            aktuell.append(s)
        else:
            aktuell.append(s)
    schliessen()
    return ergebnis


def doku(datei: str) -> list[str]:
    text = (REPO / datei).read_text(encoding="utf-8")
    return bloecke(text.split("## Was sich zuletzt getan hat")[0])


def unbelegte_zusagen(bloecke_: list[str]) -> list[str]:
    """Absätze, die ein Setzen zusagen, ohne die Warnung zu nennen."""
    treffer = []
    for b in bloecke_:
        if WARNUNG.search(b):
            continue
        zusage = ZUSAGE.search(b) and VERB.search(b)
        beispiel = THEMA.search(b) and any(
            BEISPIEL[s].search(c) for s in zurueckgehalten() for c in CODE.findall(b))
        if zusage or beispiel:
            treffer.append(b)
    return treffer


def antworten(bloecke_: list[str]) -> list[str]:
    """Absätze, die zu den zurückgehaltenen Schritten die Warnung nennen."""
    return [b for b in bloecke_
            if THEMA.search(b) and WARNUNG.search(b) and nennt_zurueckgehaltenes(b)]


# ── Die Probe misst etwas ────────────────────────────────────────────────────

def test_die_zuordnung_deckt_jeden_schritt_mit_regel():
    """Sonst prüfte die Doku-Probe einen Schritt nicht, ohne es zu sagen."""
    namen = {name for _, name in typografie.SCHRITTE if name}
    assert namen, "keine Regel je Schritt — die Probe hätte nichts zu prüfen"
    fehlt = namen - set(BEISPIEL) - set(WORT)
    assert not fehlt, f"kein Erkennungsmerkmal für {sorted(fehlt)} — hier ergänzen"
    assert set(BEISPIEL) == set(WORT)


def test_zurueckgehalten_folgt_den_daten(monkeypatch):
    """Gegenprobe: Der Satz „zurückgehalten“ ist gelesen, nicht mitgeschrieben.

    Ohne sie stünde die Liste in diesem Test, und die Doku könnte still altern,
    während er grün bleibt (dasselbe Muster wie bei `stufe_setzen` in
    test_typografie_hinweise.py: die Herkunft wird in den Daten umgestellt).
    """
    assert zurueckgehalten(), "Vorbedingung: heute wird mindestens ein Schritt zurückgehalten"
    echt = regeln._nach_typografie()
    for schritt in list(zurueckgehalten()):
        with monkeypatch.context() as m:
            m.setattr(regeln, "_nach_typografie",
                      lambda: {**echt, schritt: {**echt[schritt], "herkunft": regeln.MEHRFACH}})
            assert schritt not in zurueckgehalten(), schritt
    with monkeypatch.context() as m:
        m.setattr(regeln, "_nach_typografie",
                  lambda: {**echt, "_datum": {**echt["_datum"], "herkunft": regeln.EINZELN}})
        assert "_datum" in zurueckgehalten(), "ein herabgestufter Schritt wird nicht zurückgehalten"


def test_die_bloecke_sind_nicht_leer():
    """Sonst prüfte alles darunter die leere Menge und wäre still grün."""
    for datei in DOKUS:
        assert len(doku(datei)) >= 20, f"{datei}: nur {len(doku(datei))} Absätze gefunden"


# ── AC 1 und AC 2: die Doku sagt, was geschieht — und was der Nutzer bekommt ──

def test_kein_absatz_verspricht_ein_setzen_ohne_die_warnung():
    """Der Befund im Wortlaut: „setzt geschützte Leerzeichen von selbst“ (SKILL.md),
    „`z. B.`, `10 %`, `§ 5` bekommen geschützte Leerzeichen“ (README.md),
    „`10 %`, `5 km` … Zahl und Einheit bleiben zusammen“ (markdown.md).

    Ein Absatz, der das Setzen zusagt oder ein Beispiel eines zurückgehaltenen
    Schritts nennt, nennt in demselben Absatz die Warnung — sonst ist die
    Zusage falsch, und wer sie glaubt, hält die Warnung für überflüssig.
    """
    offen = {d: unbelegte_zusagen(doku(d)) for d in DOKUS}
    offen = {d: [b[:120] for b in bs] for d, bs in offen.items() if bs}
    assert not offen, (
        "Zusage ohne Warnung — der Pass setzt zurückgehaltene Schritte nicht, `lint` warnt:\n"
        + "\n".join(f"  {d}: {b}" for d, bs in offen.items() for b in bs))


@pytest.mark.parametrize("datei", DOKUS)
def test_die_doku_nennt_die_warnung_zu_den_zurueckgehaltenen_schritten(datei):
    """AC 1 und AC 2: Nicht nur „setzt nicht“, sondern die halbe Auskunft dazu —
    seit #330 gibt es eine Warnung, die die Stelle nennt."""
    gefunden = antworten(doku(datei))
    assert gefunden, (
        f"{datei}: kein Absatz sagt, dass {zurueckgehalten()} nur mit einer Warnung "
        "gemeldet werden (Wort „Warnung“ plus ein Beispiel oder das Wort der Regel, "
        "in einem Absatz über Leerzeichen/Typografie)")


@pytest.mark.parametrize("datei", DOKUS)
def test_die_doku_nennt_den_grund_der_zurueckhaltung(datei):
    """AC 1: „und warum“ — die Regel ist nur einzeln belegt, das Werkzeug ersetzt
    nicht, was es nicht belegen kann."""
    gefunden = [b for b in antworten(doku(datei)) if GRUND.search(b)]
    assert gefunden, (
        f"{datei}: der Absatz mit der Warnung sagt nicht, warum nicht gesetzt wird "
        "(einzeln belegt / nur eine Quelle / nicht automatisch)")


# ── AC 3: keine Zahl ohne Standangabe ────────────────────────────────────────

_ZAHL = r"(?:zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|\d+)"
ANZAHL = re.compile(
    rf"\b{_ZAHL}\s+(?:von|der)\s+{_ZAHL}\s+(?:Schritt|Regel|Ersetzung)\w*"
    rf"|\b{_ZAHL}\s+(?:Schritte|Regeln|Ersetzungen)\b", re.I)
_MONAT = "|".join(typografie.MONATE)
DATUM = re.compile(
    rf"\d{{1,2}}\.\s?\d{{1,2}}\.\s?\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}}|(?:{_MONAT})\s+\d{{4}}")


def zahlen_ohne_stand(bloecke_: list[str]) -> list[str]:
    return [b for b in bloecke_
            if THEMA.search(b) and ANZAHL.search(b) and not DATUM.search(b)]


@pytest.mark.parametrize("datei", DOKUS)
def test_eine_zahl_ueber_die_schritte_traegt_ein_datum(datei):
    """„Vier von sechs Schritten“ ist heute wahr und altert mit der Quellenlage.
    Steht sie da, gehört das Datum in denselben Absatz."""
    offen = zahlen_ohne_stand(doku(datei))
    assert not offen, f"{datei}: Zahl ohne Standangabe:\n  " + "\n  ".join(b[:120] for b in offen)


# ── Gegenproben: die Messmittel können rot werden ────────────────────────────

ALT_README = ("| Absätze, `**fett**`, `*kursiv*` | `z. B.`, `10 %`, `§ 5` "
              "bekommen geschützte Leerzeichen |")
ALT_SKILL = ("- `references/markdown.md` — was im Brieftext erlaubt ist. Der\n"
             "  Typografie-Pass setzt geschützte Leerzeichen von selbst — von Hand "
             "eingefügte sind\n  überflüssig.\n")
ALT_MARKDOWN = "| `10 %`, `5 km`, `1.234,56 EUR` | Zahl und Einheit bleiben zusammen |"
NEU = ("Einheiten wie `10 %` und Kürzel wie `Tel.` setzt der Pass nicht: Die Regel ist nur "
       "einzeln belegt. `lint` warnt an der Stelle — dann setzt du das Leerzeichen selbst.")


@pytest.mark.parametrize("alt", [ALT_README, ALT_SKILL, ALT_MARKDOWN],
                         ids=["readme", "skill", "markdown"])
def test_gegenprobe_der_alte_wortlaut_wird_erkannt(alt):
    """Ohne sie belegt der Test oben nur, dass gerade nichts Falsches dasteht —
    nicht, dass er es fände. Die drei Wortlaute sind die aus dem Befund."""
    assert unbelegte_zusagen(bloecke(alt)), "der alte Wortlaut schlägt nicht an"


def test_gegenprobe_der_neue_wortlaut_besteht():
    """Und umgekehrt: Eine Probe, die jeden Absatz über Leerzeichen abweist,
    ließe die Doku nie mehr grün werden."""
    b = bloecke(NEU)
    assert not unbelegte_zusagen(b)
    assert antworten(b), "die Probe erkennt die Auskunft nicht"
    assert [x for x in antworten(b) if GRUND.search(x)], "die Probe erkennt den Grund nicht"


def test_gegenprobe_ein_absatz_ohne_die_warnung_besteht_nicht():
    """Die Warnung muss im selben Absatz stehen, nicht irgendwo auf der Seite."""
    text = ALT_README + "\n\nWeiter unten steht ein Absatz mit einer Warnung.\n"
    assert unbelegte_zusagen(bloecke(text)), "eine Warnung anderswo heilt die Zusage nicht"
    assert not antworten(bloecke(text))


def test_gegenprobe_die_zerlegung_trennt_zeilen_listenpunkte_und_zaeune():
    text = ("Absatz eins\nüber zwei Zeilen.\n\n| a | b |\n| c | d |\n\n"
            "- Punkt eins\n  weiter\n- Punkt zwei\n\n```\n`10 %` im Zaun\n```\n")
    assert bloecke(text) == [
        "Absatz eins über zwei Zeilen.", "| a | b |", "| c | d |",
        "- Punkt eins weiter", "- Punkt zwei"]


def test_gegenprobe_die_standangabe_wird_verlangt():
    ohne = "Der Pass setzt vier von sechs Schritten selbst; die Leerzeichen bleiben zusammen."
    mit = ohne + " Stand 21.09.2026."
    assert zahlen_ohne_stand(bloecke(ohne)), "die Zahl ohne Datum schlägt nicht an"
    assert not zahlen_ohne_stand(bloecke(mit)), "das Datum heilt die Zahl nicht"
    assert not zahlen_ohne_stand(bloecke("Der Pass setzt Leerzeichen selbst.")), (
        "ein Absatz ohne Zahl schlägt an")
