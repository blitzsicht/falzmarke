"""Der Verlauf in der README ist eine Sicht auf CHANGELOG.md, keine zweite Fassung.

Anlass: Ein Changelog in der README ist bequem zu lesen — und driftet, sobald er
von Hand gepflegt wird. Wie weit das geht, zeigt dieses Repository an sich
selbst: `CHANGELOG.md` endet bei v0.6.0, veröffentlicht sind v0.7.0 und v0.7.1.
Zwei Fassungen desselben Verlaufs waeren derselbe Fehler noch einmal.

Der Abschnitt wird deshalb erzeugt (`scripts/changelog.py`), und hier wird
nachgehalten, dass er auf dem Stand ist und dass dabei nichts still unter den
Tisch faellt.
"""

from __future__ import annotations

import re
import sys

import pytest
from markdown_it import MarkdownIt

from conftest import REPO
from test_readme_auf_pypi import relative_ziele

sys.path.insert(0, str(REPO / "scripts"))

import changelog                                                # noqa: E402


@pytest.fixture
def readme() -> str:
    return changelog.ZIEL.read_text(encoding="utf-8")


def _auszug(readme: str) -> str:
    anfang = readme.index(changelog.MARKE_START)
    ende = readme.index(changelog.MARKE_ENDE)
    return readme[anfang:ende]


def test_die_readme_ist_auf_dem_stand_des_changelogs(readme):
    assert changelog.eingesetzt(readme) == readme, (
        "Der Abschnitt in der README passt nicht mehr zu CHANGELOG.md.\n"
        "Neu erzeugen: python3 scripts/changelog.py"
    )


def test_kein_punkt_faellt_unter_den_tisch(readme):
    """Alle Punkte der gezeigten Versionen stehen auch im Auszug.

    Das ist eine Aktualitaetspruefung, kein Nachweis der Vollstaendigkeit: Beide
    gezeigten Versionen setzen jeden Punkt fett, also faende auch eine
    Kurzfassung „nur die fetten Anfaenge“ hier nichts zum Weglassen. Den Nachweis
    fuehrt test_ein_schmuckloser_punkt_ueberlebt_den_auszug.
    """
    auszug = _auszug(readme)
    alle = changelog.versionen(changelog.QUELLE.read_text(encoding="utf-8"))
    fehlend = [
        zeile.strip()
        for _, rumpf in alle[:changelog.VERSIONEN]
        for zeile in rumpf.splitlines()
        if zeile.startswith("- ") and zeile.strip() not in auszug
    ]
    assert not fehlend, (
        f"{len(fehlend)} Punkte stehen in CHANGELOG.md, aber nicht im Auszug:\n  "
        + "\n  ".join(fehlend[:5])
    )


def test_ein_schmuckloser_punkt_ueberlebt_den_auszug(tmp_path, monkeypatch):
    """Ein Punkt ohne fett gesetzten Anfang darf nicht verschwinden.

    Der naheliegende Weg zu einem kuerzeren Auszug waere gewesen, je Punkt nur
    den fetten Anfang zu uebernehmen. In CHANGELOG.md haben 19 der 73 Punkte
    keinen — alle in v0.2 und v0.3, also ausserhalb dessen, was der Auszug heute
    zeigt. Gegen die echte Datei liefe eine solche Kuerzung deshalb unbemerkt
    durch. Diese Pruefung stellt die Lage her, in der es auffaellt.
    """
    quelle = tmp_path / "CHANGELOG.md"
    quelle.write_text(
        "# Änderungen\n\n## v9.9.9 — 01.01.2027\n\n### Neu\n"
        "- **Mit fettem Anfang.** Erklärung.\n"
        "- Ohne fetten Anfang, nur ein Satz.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(changelog, "QUELLE", quelle)
    assert "- Ohne fetten Anfang, nur ein Satz." in changelog.abschnitt(), (
        "Ein Punkt ohne fett gesetzten Anfang steht nicht im Auszug — die Kürzung "
        "verschluckt ihn still."
    )


def test_die_ueberschriften_ordnen_sich_der_readme_unter(readme):
    """Jede Überschrift aus dem Changelog liegt unter der ihrer Version.

    Geprüft wird die Ebene, nicht nur das Vorkommen von `## `: Ohne das Anheben
    stünde `### Neu` auf derselben Ebene wie `### v0.6.0` und läse sich als
    Schwester der Version statt als deren Rubrik. Genau das ist die erste
    Fassung dieser Prüfung durchgelassen — sie sah nur nach `## ` und blieb
    grün, während der Auszug bereits falsch verschachtelt war.
    """
    ebenen = [
        (len(zeile) - len(zeile.lstrip("#")), zeile.strip())
        for zeile in _auszug(readme).splitlines()
        if zeile.startswith("#")
    ]
    assert ebenen[0] == (2, "## Was sich zuletzt getan hat"), ebenen[:1]

    version = None
    for ebene, zeile in ebenen[1:]:
        if re.match(r"^#+ v\d+\.\d+\.\d+", zeile):
            assert ebene == 3, f"Versionsüberschrift auf Ebene {ebene}: {zeile}"
            version = ebene
            continue
        assert version is not None, f"Rubrik „{zeile}“ steht vor jeder Version"
        assert ebene > version, (
            f"„{zeile}“ liegt auf Ebene {ebene}, die Version darüber auf {version} — "
            "die Rubrik liest sich damit als eigener Abschnitt neben der Version."
        )


def test_eine_aenderung_am_changelog_faellt_auf(tmp_path, monkeypatch, readme):
    """Gegenprobe: Ohne sie belegte der Aktualitätstest nur, dass zwei Dateien existieren."""
    # Eine ganze Version oben anfuegen statt eine Rubrik zu treffen: „### Neu“
    # gibt es nicht in jeder Version. Genau daran ist diese Gegenprobe nach dem
    # Merge von v0.7.x einmal gescheitert — sie ersetzte nichts und war deshalb
    # gruen, ohne etwas zu belegen.
    quelle = changelog.QUELLE.read_text(encoding="utf-8")
    kopf = changelog.VERSION_KOPF.search(quelle)
    assert kopf, "CHANGELOG.md hat keine Versionsüberschrift — dann greift hier nichts"
    gefaelscht = tmp_path / "CHANGELOG.md"
    gefaelscht.write_text(
        quelle[:kopf.start()]
        + "## v99.0.0 — 01.01.2099\n\n### Neu\n- **Ein Punkt, den die README nicht kennt.**\n\n"
        + quelle[kopf.start():],
        encoding="utf-8",
    )
    monkeypatch.setattr(changelog, "QUELLE", gefaelscht)
    assert changelog.eingesetzt(readme) != readme, (
        "Ein zusätzlicher Punkt in CHANGELOG.md ändert den Auszug nicht — "
        "der Aktualitätstest kann dann nicht rot werden."
    )


def test_eine_leere_quelle_bricht_ab_statt_zu_leeren(tmp_path, monkeypatch):
    """Ein leerer Abschnitt ist die teuerste Fehlerart: Er sieht aus wie „nichts passiert“."""
    leer = tmp_path / "CHANGELOG.md"
    leer.write_text("# Änderungen\n\nNoch nichts.\n", encoding="utf-8")
    monkeypatch.setattr(changelog, "QUELLE", leer)
    with pytest.raises(SystemExit) as fehler:
        changelog.abschnitt()
    assert "v1.2.3" in str(fehler.value)


# ── Der Auszug muss auf PyPI tragen (v0.9.9) ──────────────────────────────


def test_relative_verweise_werden_absolut(tmp_path, monkeypatch):
    """Ein relativer Verweis im Changelog darf nicht als solcher in die README.

    Anlass: Beim Bündeln von v0.9.9 trugen drei Fragmente `](docs/entscheidungen/…)`.
    Auf PyPI löst das nicht auf, und die Projektseite einer veröffentlichten
    Version lässt sich nicht mehr ändern — siehe tests/test_readme_auf_pypi.py.
    """
    quelle = tmp_path / "CHANGELOG.md"
    quelle.write_text(
        "# Änderungen\n\n## v9.9.9 — 01.01.2099\n\n### Neu\n\n"
        "- Siehe [ADR 0047](docs/entscheidungen/0047-geometrie-regeln-tragen-ihre-stufe.md)\n"
        "- Ein Bild: ![Marke](docs/marke/logo.png)\n"
        "- Ein Anker: [oben](#kopf) und eine Adresse: [Post](mailto:wer@example.org)\n"
        "- Schon absolut: [Vorgang](https://github.com/blitzsicht/falzmarke/issues/355)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(changelog, "QUELLE", quelle)
    auszug = changelog.abschnitt()

    assert "](https://github.com/blitzsicht/falzmarke/blob/main/docs/entscheidungen/" in auszug
    assert "](https://github.com/blitzsicht/falzmarke/raw/main/docs/marke/logo.png)" in auszug, (
        "Ein Bild braucht `raw`, nicht `blob` — sonst zeigt PyPI die HTML-Seite statt der Datei."
    )
    assert "](#kopf)" in auszug and "](mailto:wer@example.org)" in auszug, (
        "Anker und mailto sind keine Pfade und dürfen nicht umgeschrieben werden."
    )
    assert auszug.count("blob/main/https") == 0, "Ein absoluter Verweis wurde ein zweites Mal umgeschrieben."


def test_die_umschreibung_wuerde_einen_relativen_verweis_bemerken(tmp_path, monkeypatch):
    """Gegenprobe: ohne die Umschreibung steht der relative Verweis im Auszug.

    Ohne sie wäre der Test darüber erfüllt, sobald irgendein absoluter Verweis
    im Text steht — auch wenn `_absolut` gar nichts tut.
    """
    quelle = tmp_path / "CHANGELOG.md"
    quelle.write_text(
        "# Änderungen\n\n## v9.9.9 — 01.01.2099\n\n### Neu\n\n"
        "- Siehe [ADR 0047](docs/entscheidungen/0047-geometrie-regeln-tragen-ihre-stufe.md)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(changelog, "QUELLE", quelle)
    monkeypatch.setattr(changelog, "_absolut", lambda rumpf: rumpf)
    auszug = changelog.abschnitt()
    assert "](docs/entscheidungen/0047-geometrie-regeln-tragen-ihre-stufe.md)" in auszug, (
        "Ohne _absolut() bleibt der Verweis relativ — genau das muss der Test darüber verhindern."
    )


def _auszug_aus(tmp_path, monkeypatch, punkte: str) -> str:
    quelle = tmp_path / "CHANGELOG.md"
    quelle.write_text(
        "# Änderungen\n\n## v9.9.9 — 01.01.2099\n\n### Behoben\n\n" + punkte, encoding="utf-8"
    )
    monkeypatch.setattr(changelog, "QUELLE", quelle)
    return changelog.abschnitt()


def test_code_bleibt_im_auszug_woertlich(tmp_path, monkeypatch):
    """`` `[Text](url)` `` ist ein Beispiel, kein Verweis, und bleibt stehen (#480).

    Anlass: Das Fragment zu #424 trug die Link-Schreibweise im Code-Span. Am PR
    war alles grün; erst der Release-PR #472 wurde an
    test_kein_punkt_faellt_unter_den_tisch rot, weil der Auszug daraus
    `[Text](https://github.com/…/blob/main/url)` gemacht hatte. Der echte Verweis
    in derselben Zeile wird trotzdem umgeschrieben.
    """
    auszug = _auszug_aus(tmp_path, monkeypatch, (
        "- Die Schreibweise `[Text](url)` und ``a`[b](c)`` bleiben, "
        "[ADR](docs/x.md) wird absolut.\n"
        "- Ein Block:\n\n  ```md\n  [Bild](docs/demo.gif)\n  ```\n"
    ))
    assert "`[Text](url)`" in auszug and "``a`[b](c)``" in auszug, auszug
    assert "  [Bild](docs/demo.gif)\n" in auszug, "Der Codeblock wurde umgeschrieben."
    assert f"[ADR]({changelog.BASIS_URL}/blob/main/docs/x.md)" in auszug, (
        "Neben dem Code-Span blieb der echte Verweis relativ."
    )


#: Je Grenze eines Code-Spans ein Fall: (Punkte, Ziel, Meldung).
OFFENE_BACKTICKS = {
    "listenpunkt": ("- Ein ` allein.\n- Danach [A](docs/a.md), dann ein ` zu.\n",
                    "docs/a.md", "Ein Backtick verband zwei Listenpunkte."),
    "absatz": ("Ein Absatz mit `offen\n\n[B](docs/b.md) und ein spätes ` zu.\n",
               "docs/b.md", "Ein Backtick verband zwei Absätze."),
}


@pytest.mark.parametrize("punkte, ziel, grund", list(OFFENE_BACKTICKS.values()),
                         ids=list(OFFENE_BACKTICKS))
def test_ein_offener_backtick_schuetzt_keinen_verweis(punkte, ziel, grund, tmp_path, monkeypatch):
    """Ein Backtick ohne Partner im selben Block ist kein Code (#480).

    Die Ausklammerung ist die gefährlichere Richtung: Was sie zu Unrecht für Code
    hält, geht relativ nach PyPI. Ein Code-Span endet deshalb dort, wo ein
    Markdown-Leser einen neuen Block beginnt. Je Fall ein eigener Auszug: In
    einem gemeinsamen schlösse der Backtick des einen den des anderen.
    """
    auszug = _auszug_aus(tmp_path, monkeypatch, punkte)
    assert f"]({changelog.BASIS_URL}/blob/main/{ziel})" in auszug, grund


def test_ein_backtick_lauf_schliesst_nur_mit_einem_gleich_langen(tmp_path, monkeypatch):
    """``` ``x` [C](c.md) `y`` ``` ist ein einziger Code-Span, der Verweis darin Text."""
    auszug = _auszug_aus(tmp_path, monkeypatch, "- Ungleich lang: ``x` [C](docs/c.md) `y``\n")
    assert "``x` [C](docs/c.md) `y``" in auszug, "Ein Lauf aus zwei Backticks schloss mit einem."


# ── Jedes Fragment am eigenen PR nachgemessen (#480) ──────────────────────


#: Das Fragment aus #469 im Wortlaut, wie es vor der Umformulierung in #472 stand.
FRAGMENT_469 = (
    "- **Eine nackte Adresse im Mailtext ist im HTML-Teil wieder anklickbar.** Aus "
    "`https://…` und `http://…` wird beim Lesen ein Link wie bei `[Text](url)`: im HTML "
    "ein `<a href>`, im Textteil die Adresse in spitzen Klammern (#424).\n"
)


def code_stellen(text: str) -> list[str]:
    """Der Inhalt jedes Code-Spans und Codeblocks, so wie ein Markdown-Leser ihn sieht."""
    stellen: list[str] = []

    def sammeln(marken) -> None:
        for marke in marken:
            if marke.type in ("code_inline", "fence", "code_block"):
                stellen.append(marke.content)
            if marke.children:
                sammeln(marke.children)

    sammeln(MarkdownIt("commonmark").parse(text))
    return stellen


def umschreibung_befunde(text: str) -> list[str]:
    """Was `_absolut` an diesem Text falsch machte, gemessen mit einem Parser.

    Der Parser ist der Schiedsrichter, nicht die Regex in `changelog.py`: Er
    entscheidet, was Code ist und was ein Verweis. Ändert die Umschreibung Code,
    stimmt der Auszug nicht mehr mit CHANGELOG.md überein. Lässt sie einen
    Verweis relativ, zeigt er auf PyPI ins Leere.
    """
    neu = changelog._absolut(text)
    befunde = []
    if code_stellen(neu) != code_stellen(text):
        befunde.append("Code verändert")
    befunde += [f"relativ geblieben: {ziel}" for ziel in relative_ziele(neu)]
    return befunde


def _schriftstuecke():
    yield pytest.param(changelog.QUELLE, id="CHANGELOG.md")
    for fragment in sorted(changelog.FRAGMENTE.glob("*.md")):
        yield pytest.param(fragment, id=fragment.name)


@pytest.mark.parametrize("pfad", list(_schriftstuecke()))
def test_die_umschreibung_laesst_code_stehen_und_jeden_verweis_absolut(pfad):
    """Am PR des Fragments rot, nicht erst am Release-PR (#480).

    Ein Fragment geht erst beim Bündeln durch `_absolut`. Bis dahin sah keine
    Prüfung, was die Umschreibung daraus macht: Das Fragment aus #469 war an
    seinem PR grün und wurde im Release-PR #472 rot.
    """
    befunde = umschreibung_befunde(pfad.read_text(encoding="utf-8"))
    assert not befunde, f"{pfad.name}: {befunde}"


def test_das_fragment_aus_469_uebersteht_die_umschreibung():
    """Der Anlass selbst. Dass der Test darüber an ihm rot würde, belegt der
    Abschnitt „#480“ in test_gegenbeweis.py, unter der zurückgebauten Ausklammerung."""
    assert code_stellen(FRAGMENT_469) == ["https://…", "http://…", "[Text](url)", "<a href>"], (
        "Der Parser findet die vier Code-Spans nicht — dann misst er auch keine Änderung daran."
    )
    assert umschreibung_befunde(FRAGMENT_469) == []
