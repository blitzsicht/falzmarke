"""Der Linter macht aus zurückgehaltenen Ersetzungen Hinweise (#330).

WARUM ES DAS GIBT

`typografie.anwenden()` ändert den Text nur dort, wo die Regel mehrfach belegt
ist. Was sie zurückhält, sammelt `vorschlaege()` — „der Linter macht
Warnungen daraus", stand im Docstring. Der Linter rief die Funktion nie auf:
Trug eine Regel ihre Stufe, wurde still ersetzt; trug sie sie nicht, geschah
still nichts. Beide Male erfuhr der Schreibende nichts.

WAS HIER GEMESSEN WIRD

* AC 1: Ein zurückgehaltener Schritt wird zu einer Warnung, die die Stelle
  nennt, sagt, was dort hingehört, und erklärt, warum es nicht gesetzt wurde.
* AC 2 und AC 3: Die Warnung ist der **Ersatz** der Ersetzung, nicht ihre
  Begleitung — dieselbe Stelle, einmal herabgestuft, einmal getragen. Ohne die
  zweite Probe wäre offen, ob die Warnung nur immer kommt.
* AC 4: Die Funktion hat einen Aufrufer. Gemessen aus dem Syntaxbaum, nicht per
  Textsuche: Der Docstring nennt den Namen selbst, und ein Treffer dort wäre
  keiner.

Die Kennung eines Hinweises ist die Kennung der Regel, die `vorschlaege()`
liefert (`schreibweise.einheiten`, …) — so steht sie auch in `din5008.yaml`
und in der JSON-Ausgabe von `falzmarke lint --json`.

Die Stufe einer Regel wird **in den Daten** verändert (`regeln._nach_typografie`),
nicht an einer Stelle des Linters: Was die Prüfung sieht, ist dieselbe Auskunft,
die der Pass selbst bekommt.
"""

from __future__ import annotations

import ast

import pytest

from falzmarke import cli as falzmarke
from falzmarke import regeln, typografie
from conftest import PROFILE, SKILL

KOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-09-21
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""

KOPF_11 = KOPF + 'dialekt: "1.1"\n'

KOPF_MAIL = """typ: email
profil: example
an: erika.muster@example.de
betreff: Ein Betreff
anrede: Sehr geehrte Frau Muster,
"""

#: Je Schritt: ein Satz mit genau einer Stelle, die er ändern würde, und der
#: Ausschnitt, den die Meldung nennen muss. Keiner der Sätze berührt einen
#: anderen Schritt — sonst zählte eine Probe für zwei.
STELLEN = {
    "_abkuerzungen": ("Das gilt z. B. für Sie.", "z. B."),
    "_datum": ("Die Feier ist am 3. Oktober.", "3. Oktober"),
    "_einheiten": ("Die Sendung wiegt 5 kg.", "5 kg"),
    "_vor_angabe": ("Rückfragen unter Tel. 0941 620-9800.", "Tel."),
}

NBSP = typografie.NBSP

#: Dieselben Sätze, an der Stelle bereits mit geschütztem Leerzeichen. Von Hand
#: statt aus `STELLEN` abgeleitet: „Tel." trägt kein Leerzeichen im Ausschnitt.
GESCHUETZT = {
    "_abkuerzungen": ("z. B.", f"z.{NBSP}B."),
    "_datum": ("3. Oktober", f"3.{NBSP}Oktober"),
    "_einheiten": ("5 kg", f"5{NBSP}kg"),
    "_vor_angabe": ("Tel. 0941", f"Tel.{NBSP}0941"),
}


def linte(tmp_path, body: str, kopf: str = KOPF):
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{kopf}---\n{body}", encoding="utf-8")
    return falzmarke.linte(pfad, profil_verzeichnis=PROFILE), pfad


def hinweise(bericht) -> list:
    """Die Befunde des Typografie-Passes: Kennung einer Regel mit `typografie:`."""
    kennungen = {r["id"] for r in regeln.alle() if r.get("typografie")}
    assert len(kennungen) >= 4, "die Zuordnung `typografie:` fehlt — die Probe misst nichts"
    return [b for b in bericht.befunde if b.regel in kennungen]


def klartext(befund) -> str:
    """Meldung und Korrektur, geschützte Leerzeichen als gewöhnliche.

    Wer die Stelle zitiert, zitiert sie mit dem Zeichen aus der Quelle; ein
    Test, der auf NBSP vergliche, hinge an der Schreibweise der Meldung.
    """
    return f"{befund.meldung} {befund.korrektur}".replace(NBSP, " ")


def zeile_von(pfad, text: str) -> int:
    return pfad.read_text(encoding="utf-8").splitlines().index(text) + 1


def stufe_setzen(mp, schritte, herkunft: str) -> None:
    """Setzt die Herkunft der Regeln dieser Schritte — in den Daten, nicht im Code.

    `mp` ist `monkeypatch` oder ein `monkeypatch.context()`; nur der zweite
    stellt den Zustand mitten im Test wieder her.
    """
    echt = regeln._nach_typografie()
    geaendert = dict(echt)
    for schritt in schritte:
        assert schritt in echt, f"{schritt}: keine Regel mit dieser `typografie:`-Zuordnung"
        geaendert[schritt] = {**echt[schritt], "herkunft": herkunft}
    mp.setattr(regeln, "_nach_typografie", lambda: geaendert)


def unter_stufe(tmp_path, monkeypatch, schritt: str, herkunft: str, text: str):
    """(wurde ersetzt, Hinweise, Bericht) für `text`, solange die Regel `herkunft` trägt."""
    with monkeypatch.context() as m:
        stufe_setzen(m, [schritt], herkunft)
        ersetzt = typografie.anwenden(text) != text
        bericht, _ = linte(tmp_path, f"{text}\n")
    return ersetzt, hinweise(bericht), bericht


# ── Der Hebel greift ────────────────────────────────────────────────────────

@pytest.mark.parametrize("schritt", sorted(STELLEN))
def test_die_herkunft_in_den_daten_steuert_den_pass(monkeypatch, schritt):
    """Gegenprobe zu den Proben unten, und deshalb von Anfang an grün: Sie
    stellen die Stufe über `stufe_setzen` um. Wirkte das nicht auf den Pass,
    hielten sie zwei gleiche Zustände gegeneinander — und die Paare „herabgestuft
    warnt, getragen schweigt" bewiesen nichts."""
    probe, _ = STELLEN[schritt]
    for stufe, soll_ersetzen in ((regeln.EINZELN, False), (regeln.MEHRFACH, True), (regeln.PRIMAER, True)):
        with monkeypatch.context() as m:
            stufe_setzen(m, [schritt], stufe)
            assert (typografie.anwenden(probe) != probe) is soll_ersetzen, (schritt, stufe)


# ── AC 1: Ein zurückgehaltener Schritt wird zur Warnung ─────────────────────

@pytest.mark.parametrize("schritt", sorted(STELLEN))
def test_zurueckgehaltener_schritt_wird_zur_warnung(tmp_path, schritt):
    """Alle vier Schritte sind heute zurückgehalten — der Pass setzt nichts.

    `_einheiten` und `_vor_angabe` standen schon vor #31 auf `einzeln_belegt`
    (bzw. führen jetzt `werkzeug`, ohne dass sich das ändert); `_datum` und
    `_abkuerzungen` kamen mit #31 dazu, weil ihre zweite volle Quelle schweigt.
    """
    probe, stelle = STELLEN[schritt]
    assert regeln.darf_automatisch_ersetzen(schritt) is False, "Vorbedingung: Schritt ist zurückgehalten"
    assert typografie.anwenden(probe) == probe, "Vorbedingung: der Pass ändert den Text nicht"

    bericht, pfad = linte(tmp_path, f"{probe}\n")
    gefunden = hinweise(bericht)
    assert len(gefunden) == 1, bericht.als_text("brief.md")

    befund = gefunden[0]
    assert befund.schwere == "Warnung", "ein Hinweis ist nie ein Fehler"
    assert befund.regel == regeln.fuer_typografie(schritt)["id"]
    assert bericht.ok
    assert (bericht.anzahl_fehler, bericht.anzahl_warnungen) == (0, 1)

    text = klartext(befund)
    assert stelle in text, "die Meldung nennt die Stelle nicht"
    assert "Leerzeichen" in text, "die Meldung sagt nicht, was dort hingehört"
    assert "einzeln" in text.lower() and "automatisch" in text.lower(), (
        "die Meldung sagt nicht, warum der Pass es nicht selbst setzt")
    assert befund.zeile == zeile_von(pfad, probe), "die Meldung nennt die Zeile der Quelldatei nicht"
    assert "WARNUNG" in bericht.als_text("brief.md")


def test_jeder_zurueckgehaltene_schritt_nennt_seine_eigene_stelle(tmp_path, monkeypatch):
    """Vier Schritte, vier Sätze, vier Hinweise — je einer mit Kennung und Zeile."""
    with monkeypatch.context() as m:
        stufe_setzen(m, STELLEN, regeln.EINZELN)
        saetze = [probe for probe, _ in STELLEN.values()]
        bericht, pfad = linte(tmp_path, "\n\n".join(saetze) + "\n")
        gefunden = hinweise(bericht)

    assert {b.regel for b in gefunden} == {regeln.fuer_typografie(s)["id"] for s in STELLEN}
    for schritt, (probe, stelle) in STELLEN.items():
        kennung = regeln.fuer_typografie(schritt)["id"]
        eigene = [b for b in gefunden if b.regel == kennung]
        assert len(eigene) == 1, f"{schritt}: {len(eigene)} Hinweise\n" + bericht.als_text("brief.md")
        assert stelle in klartext(eigene[0]), schritt
        assert eigene[0].zeile == zeile_von(pfad, probe), schritt


def test_die_mail_bekommt_dieselben_hinweise(tmp_path):
    """Der Pass läuft in Brief **und** Mail über dieselben Textknoten."""
    bericht, pfad = linte(tmp_path, "Die Sendung wiegt 5 kg.\n", KOPF_MAIL)
    gefunden = hinweise(bericht)
    assert len(gefunden) == 1, bericht.als_text("nachricht.md")
    assert "5 kg" in klartext(gefunden[0])
    assert gefunden[0].zeile == zeile_von(pfad, "Die Sendung wiegt 5 kg.")


@pytest.mark.parametrize("body", [
    "- Erstens 5 kg\n- Zweitens\n",
    "Das wiegt **5 kg** genau.\n",
    "| Posten | Menge |\n|---|---|\n| Sand | 5 kg |\n",
], ids=["aufzaehlung", "fett", "tabellenzelle"])
def test_der_hinweis_gilt_auch_in_verschachtelten_knoten(tmp_path, body):
    """Der Pass setzt auf jedem Textknoten — der Linter muss dort hinsehen, wo er setzt."""
    bericht, _ = linte(tmp_path, body)
    gefunden = hinweise(bericht)
    assert len(gefunden) == 1, bericht.als_text("brief.md")
    assert "5 kg" in klartext(gefunden[0])


# ── AC 2 und AC 3: Ersatz, nicht Begleitung ─────────────────────────────────

@pytest.mark.parametrize("schritt", sorted(STELLEN))
def test_dieselbe_stelle_warnt_nur_herabgestuft(tmp_path, monkeypatch, schritt):
    """Zwei Proben am selben Satz. Herabgestuft: unverändert **und** gewarnt.
    Trägt die Regel ihre Stufe: ersetzt **und** still. Für `_datum` ist das der
    Fall „3. Oktober" aus dem Vorgang."""
    probe, stelle = STELLEN[schritt]

    ersetzt, gefunden, bericht = unter_stufe(tmp_path, monkeypatch, schritt, regeln.EINZELN, probe)
    assert not ersetzt, "Vorbedingung: eine herabgestufte Regel ändert den Text nicht"
    assert len(gefunden) == 1, f"{schritt}: herabgestuft, aber keine Warnung\n" + bericht.als_text("brief.md")
    assert stelle in klartext(gefunden[0])
    assert gefunden[0].regel == regeln.fuer_typografie(schritt)["id"]

    for stufe in (regeln.MEHRFACH, regeln.PRIMAER):
        ersetzt, gefunden, bericht = unter_stufe(tmp_path, monkeypatch, schritt, stufe, probe)
        assert ersetzt, f"Vorbedingung: unter `{stufe}` setzt der Pass"
        assert gefunden == [], (
            f"{schritt}: unter `{stufe}` wird ersetzt UND gewarnt — die Warnung begleitet die "
            "Ersetzung, statt sie zu vertreten\n" + bericht.als_text("brief.md"))
        assert bericht.anzahl_warnungen == 0, bericht.als_text("brief.md")


def test_seit_31_setzt_keiner_der_vier_schritte_und_jeder_warnt(tmp_path):
    """Der Ist-Stand nach #31: `_datum` und `_abkuerzungen` waren mehrfach belegt
    und wurden gesetzt — bis sich zeigte, dass ihre zweite volle Quelle zur
    Regel schweigt. Jetzt setzt keiner der vier Schritte mehr; aus vier
    Stellen werden vier Warnungen, eine je Schritt und keine doppelt.

    Der Test steht an der Stelle von `…setzen_weiter_und_nur_die_zurueckgehaltene_warnt`:
    Jener hielt den Zustand fest, in dem zwei von drei setzten. Der Zustand
    ist nicht mehr da, und wer ihn wollte, müsste #31 zurücknehmen.
    """
    saetze = [probe for probe, _ in STELLEN.values()]
    for probe in saetze:
        assert typografie.anwenden(probe) == probe, f"der Pass setzt weiter: {probe!r}"

    bericht, pfad = linte(tmp_path, "\n\n".join(saetze) + "\n")
    gefunden = hinweise(bericht)
    assert sorted(b.zeile for b in gefunden) == sorted(zeile_von(pfad, s) for s in saetze), (
        bericht.als_text("brief.md"))
    assert {b.regel for b in gefunden} == {regeln.fuer_typografie(s)["id"] for s in STELLEN}
    assert (bericht.anzahl_fehler, bericht.anzahl_warnungen) == (0, len(STELLEN)), (
        bericht.als_text("brief.md"))


# ── Gegenproben: die Warnung kommt nicht immer ──────────────────────────────

def test_ohne_anlass_und_bei_geschuetzter_schreibung_bleibt_es_still(tmp_path, monkeypatch):
    """Alle vier Regeln herabgestuft — und trotzdem schweigt der Linter, wo der
    Schritt nichts zu ändern hätte. Die erste Probe belegt, dass er unter
    genau diesen Bedingungen sonst spricht."""
    with monkeypatch.context() as m:
        stufe_setzen(m, STELLEN, regeln.EINZELN)

        roh = "\n\n".join(probe for probe, _ in STELLEN.values()) + "\n"
        assert len(hinweise(linte(tmp_path, roh)[0])) == len(STELLEN), "Vorbedingung: sonst misst der Rest nichts"

        geschuetzt = "\n\n".join(STELLEN[schritt][0].replace(alt, neu)
                                 for schritt, (alt, neu) in GESCHUETZT.items()) + "\n"
        assert geschuetzt != roh and geschuetzt.count(NBSP) == len(STELLEN)

    with monkeypatch.context() as m:
        stufe_setzen(m, STELLEN, regeln.MEHRFACH)
        assert typografie.anwenden(geschuetzt) == geschuetzt, (
            "Vorbedingung: an der geschützten Schreibung gäbe es nichts zu ersetzen")

    with monkeypatch.context() as m:
        stufe_setzen(m, STELLEN, regeln.EINZELN)
        assert hinweise(linte(tmp_path, geschuetzt)[0]) == [], "die Stelle ist längst geschützt"

        neutral, _ = linte(tmp_path, "Ein Satz ohne Anlass.\n\nZwei Sätze, ganz gewöhnlich.\n")
        assert hinweise(neutral) == []
        assert neutral.befunde == [], neutral.als_text("brief.md")


def test_ein_wortlaut_wird_nicht_beanstandet(tmp_path):
    """Ein wortgetreuer Auszug geht nie durch den Pass — dort gäbe es nichts zu
    ersetzen und darum nichts anzumerken. Die erste Probe: derselbe Satz ohne
    Backticks trägt den Hinweis."""
    ausserhalb, _ = linte(tmp_path, "Der Zähler zeigt 5 kg an.\n", KOPF_11)
    assert len(hinweise(ausserhalb)) == 1, "Vorbedingung: außerhalb des Auszugs wird gemeldet"

    im_satz, _ = linte(tmp_path, "Der Zähler zeigt `5 kg` an.\n", KOPF_11)
    im_block, _ = linte(tmp_path, "Der Zähler zeigt:\n\n```\n5 kg\n```\n", KOPF_11)
    assert hinweise(im_satz) == [], im_satz.als_text("brief.md")
    assert hinweise(im_block) == [], im_block.als_text("brief.md")


def test_das_frontmatter_wird_nicht_beanstandet(tmp_path):
    """Der Pass läuft auf Textknoten des Briefes, nicht auf dem Betreff. Ein
    Hinweis dazu wäre eine Ersetzung, die es nie gäbe. Die erste Probe: derselbe
    Wortlaut im Text trägt ihn."""
    kopf = KOPF.replace("betreff: Ein Betreff", "betreff: Rechnung Nr. 2026-0815 über 5 kg Sand")
    bericht, pfad = linte(tmp_path, "Die Sendung wiegt 5 kg.\n", kopf)
    gefunden = hinweise(bericht)
    assert [b.zeile for b in gefunden] == [zeile_von(pfad, "Die Sendung wiegt 5 kg.")], (
        "der Hinweis gehört an die Textzeile, nicht an den Betreff\n" + bericht.als_text("brief.md"))


# ── AC 4: Die Funktion hat einen Aufrufer ───────────────────────────────────

def aufrufer(name: str) -> set[str]:
    """Die Module unter `skill/falzmarke`, die `name` **aufrufen** — aus dem Syntaxbaum.

    Ein Docstring, der den Namen nennt, ist kein Aufruf; eine Textsuche träfe
    genau ihn (und trifft ihn: Das war der Befund von #330).
    """
    treffer = set()
    for pfad in sorted((SKILL / "falzmarke").rglob("*.py")):
        for knoten in ast.walk(ast.parse(pfad.read_text(encoding="utf-8"))):
            if not isinstance(knoten, ast.Call):
                continue
            ziel = knoten.func
            gerufen = ziel.attr if isinstance(ziel, ast.Attribute) else getattr(ziel, "id", None)
            if gerufen == name:
                treffer.add(pfad.name)
    return treffer


def test_der_aufruferzaehler_findet_bekannte_aufrufer_und_keine_erfundenen():
    """Gegenprobe zu unten: Ein Zähler, der nie etwas findet, ließe die Probe
    für `vorschlaege` aus dem falschen Grund rot — und nach der Lösung nie grün."""
    assert {"emit.py", "emit_text.py", "emit_html.py"} <= aufrufer("anwenden")
    assert aufrufer("gibt_es_in_diesem_paket_nicht") == set()


def test_vorschlaege_hat_einen_aufrufer():
    """Der Befund von #330: zwei Treffer, beide in `typografie.py` selbst."""
    gerufen_von = aufrufer("vorschlaege") - {"typografie.py"}
    assert gerufen_von, "`typografie.vorschlaege()` hat außerhalb von typografie.py keinen Aufrufer"
