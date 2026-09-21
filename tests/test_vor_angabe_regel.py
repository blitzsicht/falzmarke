"""Der Schritt `_vor_angabe` trägt eine Regel, die sagt, was er tut (#332).

WARUM ES DAS GIBT

`typografie._vor_angabe` setzt ein geschütztes Leerzeichen hinter `Nr.`,
`Tel.`, `Az.` und ein paar Kürzel mehr. In `regeln/din5008.yaml` hing er an
`schreibweise.zahlengliederung` — „Zahlen in Dreiergruppen mit geschütztem
Leerzeichen: 1 234 567,89". Der Schritt gliedert aber keine Zahl. Seit #330
steht die Kennung in jeder Warnung dieses Schritts, und wer sie nachschlägt,
liest etwas über Dreiergruppen:

    WARNUNG brief-mahnung.md:15 schreibweise.zahlengliederung — Leerzeichen
    schützen: „Rechnung Nr. 2026-0815"

WAS HIER GEMESSEN WIRD

* AC 1: Der Schritt hängt an einer eigenen Regel, deren Titel sagt, was er tut.
* AC 2: `schreibweise.zahlengliederung` bleibt, was sie sagt. Hängt kein Schritt
  mehr an ihr, steht die Begründung daneben; hängt einer an ihr, gliedert er
  tatsächlich Zahlen.
* AC 3: Die Warnung aus dem Beispiel `brief-mahnung.md` nennt die neue Kennung.
* AC 5: Zwei Proben. `Nr. 4711` meldet unter der neuen Kennung; `1 234 567,89`
  meldet **nicht** dort. Ohne die zweite wäre offen, ob nur umbenannt statt
  getrennt wurde.
* AC 6: Die erzeugte Normreferenz führt beide Regeln als eigene Zeilen.

Wie die neue Kennung heißt, legt der Vorgang nicht fest — diese Tests fragen den
Katalog, welche Regel hinter dem Schritt steht, und prüfen dann, was dort
steht. Ein Name, den der Test vorgäbe, prüfte die Namenswahl statt der Sache
(so auch in tests/test_betreff_regeln.py, #296).

AC 4 (Zuordnung Schritt → Regel) steht in tests/test_quellenlage.py, neben der
Zuordnung der Linter-Regeln. AC 7 tragen die vorhandenen Beispieltests.
"""

from __future__ import annotations

import pytest

from falzmarke import cli as falzmarke
from falzmarke import regeln, typografie
from conftest import PROFILE, REPO

ZAHLENGLIEDERUNG = "schreibweise.zahlengliederung"

#: Die Zeile, unter der diese Regel bis #332 stand — von Hand hingeschrieben, damit
#: die Gegenprobe zum Titelprüfer nicht vom Katalog abhängt, den sie prüft.
ALTER_TITEL = "Zahlen in Dreiergruppen mit geschütztem Leerzeichen: 1 234 567,89"

KOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-09-21
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""

NBSP = typografie.NBSP


def _eintrag_von_schritt(schritt: str = "_vor_angabe") -> dict:
    eintrag = regeln.fuer_typografie(schritt)
    assert eintrag is not None, f"{schritt}: keine Regel mit dieser `typografie:`-Zuordnung"
    return eintrag


def _eintrag(kennung: str) -> dict | None:
    return next((r for r in regeln.alle() if r["id"] == kennung), None)


def _benennt_den_gegenstand(titel: str) -> bool:
    """Sagt der Titel, was `_vor_angabe` tut: geschütztes Leerzeichen hinter Kürzeln?

    „Leerzeichen" nennt die Handlung, ein Kürzel aus `VOR_ANGABE` den Gegenstand.
    Von Zahlen in Dreiergruppen darf er nicht reden — das ist ein anderer Schritt.
    """
    unten = titel.lower()
    return ("leerzeichen" in unten
            and any(kuerzel in unten for kuerzel in ("nr.", "tel.", "az."))
            and "dreiergruppen" not in unten)


def linte(tmp_path, body: str):
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{KOPF}---\n{body}", encoding="utf-8")
    return falzmarke.linte(pfad, profil_verzeichnis=PROFILE)


def unter(bericht, kennung: str) -> list:
    return [b for b in bericht.befunde if b.regel == kennung]


def klartext(befund) -> str:
    return f"{befund.meldung} {befund.korrektur}".replace(NBSP, " ")


# ── AC 1: Der Schritt trägt eine Regel, die seinen Gegenstand nennt ─────────

def test_der_schritt_hat_eine_eigene_regel():
    """Der Kern des Befunds: derselbe Katalogeintrag für zwei Dinge."""
    assert _eintrag_von_schritt()["id"] != ZAHLENGLIEDERUNG, (
        "`_vor_angabe` hängt noch an der Regel für Dreiergruppen")


def test_der_titel_benennt_den_gegenstand():
    titel = _eintrag_von_schritt()["titel"]
    assert _benennt_den_gegenstand(titel), (
        f"der Titel sagt nicht, dass es um das geschützte Leerzeichen hinter Kürzeln "
        f"(Nr., Tel., Az.) geht: {titel!r}")


def test_der_titelpruefer_lehnt_den_alten_titel_ab():
    """Gegenprobe zu oben: Ein Prüfer, der jeden Titel annähme, ließe den Test
    darüber auch vor der Lösung grün — und danach erst recht."""
    assert not _benennt_den_gegenstand(ALTER_TITEL)
    assert _benennt_den_gegenstand("Geschütztes Leerzeichen hinter Kürzeln: Nr. 4711, Tel. 0941")


# ── AC 2: zahlengliederung bleibt, was sie sagt ─────────────────────────────

def test_zahlengliederung_bleibt_die_regel_fuer_dreiergruppen():
    eintrag = _eintrag(ZAHLENGLIEDERUNG)
    assert eintrag is not None, f"{ZAHLENGLIEDERUNG} ist verschwunden — AC 2 sagt: sie bleibt"
    assert "Dreiergruppen" in eintrag["titel"], eintrag["titel"]
    assert eintrag.get("typografie") != "_vor_angabe", (
        "zahlengliederung sagt „Dreiergruppen“, der Schritt setzt Leerzeichen hinter Kürzeln")


def test_zahlengliederung_haelt_ihr_versprechen_oder_sagt_warum_nicht(tmp_path):
    """Zwei Fälle, und genau einer trifft zu.

    * Hängt ein Schritt an der Regel, muss er Zahlen gliedern: `1 234 567,89`
      ergibt eine Warnung unter ihrer Kennung.
    * Hängt keiner mehr an ihr (der erwartete Ausgang), steht die Begründung
      daneben — im Eintrag selbst, in `bemerkung`, nicht in einem Kommentar.
      Ohne sie wäre die Regel still verwaist: Sie sieht in der Normreferenz
      wie geprüft aus und wird von niemandem gemeldet.

    Vor der Lösung trifft der erste Fall zu, und der Schritt gliedert nichts.
    """
    eintrag = _eintrag(ZAHLENGLIEDERUNG)
    assert eintrag is not None, f"{ZAHLENGLIEDERUNG} ist verschwunden — AC 2 sagt: sie bleibt"
    schritt = eintrag.get("typografie")

    if schritt:
        bericht = linte(tmp_path, "Die Summe lautet 1 234 567,89 und keinen Cent mehr.\n")
        assert unter(bericht, ZAHLENGLIEDERUNG), (
            f"der Schritt `{schritt}` hängt an {ZAHLENGLIEDERUNG}, meldet aber keine "
            "Zahlengruppe — er gliedert keine Zahlen\n" + bericht.als_text("brief.md"))
    else:
        grund = str(eintrag.get("bemerkung") or "").strip()
        assert len(grund) >= 40, (
            f"kein Schritt hängt mehr an {ZAHLENGLIEDERUNG}, und daneben steht keine "
            f"Begründung (`bemerkung:`): {grund!r}")


# ── AC 3: Die Warnung aus #330 nennt die neue Kennung ───────────────────────

def test_die_mahnung_meldet_die_neue_kennung_und_nicht_mehr_zahlengliederung():
    """Das Beispiel aus dem Vorgang: `brief-mahnung.md`, Zeile 15."""
    neue = _eintrag_von_schritt()["id"]
    bericht = falzmarke.linte(REPO / "examples" / "brief-mahnung.md", profil_verzeichnis=PROFILE)
    text = bericht.als_text("brief-mahnung.md")

    warnungen = [b for b in bericht.befunde if "Rechnung Nr. 2026-0815" in klartext(b)]
    assert warnungen, "Vorbedingung: das Beispiel warnt vor „Rechnung Nr. 2026-0815“\n" + text
    assert all(b.schwere == "Warnung" for b in warnungen)

    assert [b.regel for b in warnungen] == [neue], (
        f"die Warnung nennt nicht die Kennung des Schritts ({neue})\n" + text)
    assert unter(bericht, ZAHLENGLIEDERUNG) == [], (
        "das Beispiel meldet weiter unter zahlengliederung\n" + text)
    assert ZAHLENGLIEDERUNG not in text
    assert f"{neue} —" in text, "die Kennung steht nicht in der Ausgabe von `falzmarke lint`\n" + text


# ── AC 5: Zwei Proben — getrennt, nicht nur umbenannt ───────────────────────

def test_nr_meldet_unter_der_neuen_kennung_und_die_zahlengruppe_nicht_dort(tmp_path):
    """Die erste Probe: `Nr. 4711` warnt unter der Kennung des Schritts. Die
    zweite: `1 234 567,89` warnt dort **nicht** — sonst hätte man den Namen
    getauscht, ohne Kürzel und Zahlengruppe zu trennen."""
    neue = _eintrag_von_schritt()["id"]
    assert neue != ZAHLENGLIEDERUNG, "Vorbedingung: eine eigene Kennung, sonst trennt nichts"

    kuerzel = linte(tmp_path, "Ihre Bestellung trägt die Nr. 4711 und liegt bereit.\n")
    treffer = unter(kuerzel, neue)
    assert len(treffer) == 1, kuerzel.als_text("brief.md")
    assert "Nr. 4711" in klartext(treffer[0])
    assert treffer[0].schwere == "Warnung"
    assert unter(kuerzel, ZAHLENGLIEDERUNG) == [], kuerzel.als_text("brief.md")

    zahl = linte(tmp_path, "Die Summe lautet 1 234 567,89 und keinen Cent mehr.\n")
    assert unter(zahl, neue) == [], (
        "eine Zahlengruppe meldet unter der Kennung des Kürzel-Schritts\n" + zahl.als_text("brief.md"))
    assert not any("1 234 567,89" in klartext(b) for b in zahl.befunde if b.regel == neue)


@pytest.mark.parametrize("kuerzel", ["Nr.", "Tel.", "Az."])
def test_jedes_genannte_kuerzel_meldet_unter_der_neuen_kennung(tmp_path, kuerzel):
    """Die drei Kürzel aus AC 1, je für sich: Ein Titel, der sie nennt, muss
    für alle drei gelten."""
    neue = _eintrag_von_schritt()["id"]
    bericht = linte(tmp_path, f"Bitte melden Sie sich unter {kuerzel} 4711 bei uns.\n")
    treffer = unter(bericht, neue)
    assert len(treffer) == 1, bericht.als_text("brief.md")
    assert f"{kuerzel} 4711" in klartext(treffer[0])
    assert unter(bericht, ZAHLENGLIEDERUNG) == [], (
        f"{kuerzel} meldet unter zahlengliederung\n" + bericht.als_text("brief.md"))


def test_ein_satz_ohne_kuerzel_und_ohne_zahlengruppe_bleibt_still(tmp_path):
    """Gegenprobe zu den beiden oben: Die Kennung kommt nicht immer."""
    neue = _eintrag_von_schritt()["id"]
    bericht = linte(tmp_path, "Ein Satz ohne Anlass und ohne Zahl.\n")
    assert unter(bericht, neue) == [] and unter(bericht, ZAHLENGLIEDERUNG) == [], (
        bericht.als_text("brief.md"))


# ── AC 6: Die Normreferenz führt beide Regeln als eigene Zeilen ─────────────

def _quellenlage_abschnitt() -> str:
    text = (REPO / "skill" / "references" / "din5008.md").read_text(encoding="utf-8")
    anfang, ende = "<!-- quellenlage:anfang -->", "<!-- quellenlage:ende -->"
    assert anfang in text and ende in text, "die Marken des erzeugten Abschnitts fehlen"
    return text[text.index(anfang):text.index(ende)]


def test_die_erzeugte_normreferenz_fuehrt_beide_regeln_getrennt():
    """Erzeugt (`python3 scripts/quellenlage.py`), nicht von Hand geändert: Beide
    Titel stehen als eigene Zeile im Abschnitt „Quellenlage je Regel“. Die
    Aktualität selbst hält `test_die_normreferenz_ist_auf_dem_stand_der_regeldatei`."""
    schritt = _eintrag_von_schritt()
    gliederung = _eintrag(ZAHLENGLIEDERUNG)
    assert gliederung is not None
    assert schritt["titel"] != gliederung["titel"], "beide Regeln tragen denselben Titel"

    zeilen = _quellenlage_abschnitt().splitlines()
    for regel in (schritt, gliederung):
        eigene = [z for z in zeilen if z.startswith(f"| {regel['titel']} |")]
        assert len(eigene) == 1, (
            f"{regel['id']}: {len(eigene)} Zeilen in der Normreferenz statt einer — "
            "`python3 scripts/quellenlage.py` ausführen")
