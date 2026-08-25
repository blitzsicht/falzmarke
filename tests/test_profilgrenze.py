"""Ein Profil darf auf Nachbardateien zeigen, nicht darüber hinaus.

Anlass, gemessen am 25.08.2026 an v0.3.0: `briefkopf_typ` prüfte die
Ordnergrenze, `logo` und `signatur` nicht — dieselbe Datei, dieselbe
Fehlerklasse, nur an einer Stelle bedacht.

Warum das zählt: Ein Brief kann sein Profil im Frontmatter mitbringen
(dokumentiertes Feature für claude.ai). Dann stammt das Profil von dem, der den
Brief geschickt hat. Ein `logo: ../geheim/privat.png` bettete jede Bilddatei
ein, die der Empfänger lesen kann — und der Lauf meldete dabei
`30/30 Maße eingehalten`, also keinerlei Auffälligkeit.

Die Tests hier prüfen beide Richtungen. Ein Wächter, der alles blockt, wäre
genauso falsch wie keiner: Das mitgelieferte Beispielprofil zeigt auf
`assets/logo.svg` in einem Unterordner, und das muss erlaubt bleiben.
"""

from __future__ import annotations

import shutil

import pytest

from falzmarke import cli as falzmarke
from conftest import REPO, SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

BRIEF = """---
profil: {profil}
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Probe
anrede: Sehr geehrte Damen und Herren,
gruss: Mit freundlichen Grüßen
unterzeichner: Test
---
Text des Briefes.
"""

PROFIL_RUMPF = """absender: {name: Test GmbH, strasse: Weg 1, plz: "93055", ort: Regensburg}
ruecksendeangabe: Test GmbH · Weg 1 · 93055 Regensburg
"""


@pytest.fixture
def aufbau(tmp_path):
    """Ein Profilordner und ein Bild daneben, das ausserhalb liegt."""
    profil = tmp_path / "profil"
    aussen = tmp_path / "aussen"
    profil.mkdir()
    aussen.mkdir()
    shutil.copy(PROFILE / "assets" / "logo.svg", aussen / "fremd.svg")
    return tmp_path, profil, aussen


def _rendere(tmp_path, profil_datei):
    brief = tmp_path / "b.md"
    brief.write_text(BRIEF.format(profil=f"./profil/{profil_datei}"), encoding="utf-8")
    return falzmarke.rendere(brief, tmp_path / "b.pdf")


@pytest.mark.parametrize("zeile", [
    'briefkopf: {logo: ../aussen/fremd.svg, logo_hoehe_mm: 14}',
    "signatur: ../aussen/fremd.svg",
    "briefkopf_typ: ../aussen/fremd.typ",
], ids=["logo", "signatur", "briefkopf_typ"])
def test_verweis_nach_draussen_wird_abgewiesen(aufbau, zeile):
    tmp_path, profil, aussen = aufbau
    (aussen / "fremd.typ").write_text(
        '#let briefkopf(profil) = { text("draussen") }\n', encoding="utf-8")
    (profil / "p.yaml").write_text(PROFIL_RUMPF + zeile + "\n", encoding="utf-8")

    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        _rendere(tmp_path, "p.yaml")
    assert "im Profilordner liegen" in str(fehler.value), str(fehler.value)


@pytest.mark.parametrize("zeile", [
    'briefkopf: {logo: getarnt.svg, logo_hoehe_mm: 14}',
    "signatur: getarnt.svg",
], ids=["logo", "signatur"])
def test_symlink_nach_draussen_wird_abgewiesen(aufbau, zeile):
    """`resolve()` folgt dem Symlink — ein getarnter Verweis hilft deshalb nicht."""
    tmp_path, profil, aussen = aufbau
    (profil / "getarnt.svg").symlink_to(aussen / "fremd.svg")
    (profil / "p.yaml").write_text(PROFIL_RUMPF + zeile + "\n", encoding="utf-8")

    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        _rendere(tmp_path, "p.yaml")
    assert "im Profilordner liegen" in str(fehler.value), str(fehler.value)


def test_eingebettetes_profil_kommt_nicht_aus_dem_briefordner(tmp_path):
    """Der gefährlichste Fall: Der Brief bringt das Profil selbst mit, und
    beides stammt von jemand anderem. Bezugspunkt ist dann der Brief."""
    aussen = tmp_path / "aussen"
    aussen.mkdir()
    shutil.copy(PROFILE / "assets" / "logo.svg", aussen / "fremd.svg")
    arbeit = tmp_path / "arbeit"
    arbeit.mkdir()
    brief = arbeit / "fremder-brief.md"
    brief.write_text(
        "---\n"
        "profil:\n"
        "  absender: {name: Test GmbH, strasse: Weg 1, plz: \"93055\", ort: Regensburg}\n"
        "  ruecksendeangabe: Test GmbH · Weg 1 · 93055 Regensburg\n"
        "  briefkopf: {logo: ../aussen/fremd.svg, logo_hoehe_mm: 14}\n"
        "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]\n"
        "datum: 2026-08-25\nbetreff: Probe\n"
        "anrede: Sehr geehrte Damen und Herren,\n"
        "gruss: Mit freundlichen Grüßen\nunterzeichner: Test\n"
        "---\nText.\n",
        encoding="utf-8",
    )
    with pytest.raises(falzmarke.Eingabefehler) as fehler:
        falzmarke.rendere(brief, arbeit / "b.pdf")
    assert "im Profilordner liegen" in str(fehler.value), str(fehler.value)


def test_unterordner_neben_dem_profil_bleibt_erlaubt(tmp_path):
    """Gegenprobe: Ohne sie belegen die Tests oben nur, dass irgendetwas blockt.

    Das mitgelieferte Beispiel zeigt auf `assets/logo.svg` — ein Unterordner des
    Profilordners. Ein Wächter, der auch den abweist, wäre unbrauchbar.
    """
    profil = tmp_path / "profil"
    (profil / "assets").mkdir(parents=True)
    shutil.copy(PROFILE / "assets" / "logo.svg", profil / "assets" / "logo.svg")
    (profil / "p.yaml").write_text(
        PROFIL_RUMPF + "briefkopf: {logo: assets/logo.svg, logo_hoehe_mm: 14}\n",
        encoding="utf-8")

    pdf, _ = _rendere(tmp_path, "p.yaml")
    assert pdf.is_file()


def test_das_mitgelieferte_beispiel_rendert_weiterhin(tmp_path):
    """Der schärfste Fall des vorigen Tests: das echte Profil aus dem Paket,
    dessen Logo in `profiles/assets/` liegt."""
    from falzmarke import geometrie
    pdf, form = falzmarke.rendere(
        REPO / "examples" / "brief-form-b.md", tmp_path / "grenze.pdf")
    gescheitert = [p.name for p in geometrie.pruefe(pdf, form).pruefungen if not p.bestanden]
    assert not gescheitert, gescheitert
