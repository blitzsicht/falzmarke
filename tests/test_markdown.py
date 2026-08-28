"""falzmarke-Markdown: der Dialekt, Fall für Fall.

Die Tabelle unten ist die verbindliche Beschreibung dessen, was gesetzt wird
und was abgelehnt wird. Sie ist die Prüfung und zugleich die Vorlage für
`references/frontmatter.md` — weicht die Doku ab, ist die Doku falsch.
"""

from __future__ import annotations

import pytest

from falzmarke.markdown import MarkdownFehler, konvertiere
from falzmarke.typografie import NBSP

# (Eingabe, erwartet) — erwartet ist entweder ein Stück der Typst-Ausgabe
# oder ein Stück der Fehlermeldung, je nach Marke.
GESETZT = [
    ("Erster Absatz.\n\nZweiter Absatz.", ['#par[#text("Erster Absatz.")]', '#par[#text("Zweiter Absatz.")]']),
    ("Das ist **fett**.", ['#strong[#text("fett")]']),
    ("Das ist *kursiv*.", ['#emph[#text("kursiv")]']),
    ("Das ist _kursiv_.", ['#emph[#text("kursiv")]']),
    ("Das ist __fett__.", ['#strong[#text("fett")]']),
    ("Das ist ***beides***.", ['#strong[', "#emph["]),
    ("Siehe https://example.de/pfad?x=1&y=2 dort.", ['https://example.de/pfad?x=1&y=2']),
    ("- eins\n- zwei", ["#list([", '#text("eins")']),
    ("* eins\n* zwei", ["#list(["]),
    ("+ eins\n+ zwei", ["#list(["]),
    ("1. eins\n2. zwei", ["#enum(start: 1"]),
    ("3. drei\n4. vier", ["#enum(start: 3"]),
    ("1) eins\n2) zwei", ["#enum(start: 1"]),
    ("- eins\n  - unter\n  - noch\n- zwei", ["#list([", "#list(["]),
    ("Zeile eins\\\nZeile zwei", ["#linebreak()"]),
    ("Zeile eins  \nZeile zwei", ["#linebreak()"]),
    ("Zeile eins\nZeile zwei", ['#text("Zeile eins")', '#text(" ")', '#text("Zeile zwei")']),
    ("| A | B |\n|---|---|\n| 1 | 2 |", ["#table(", "columns: 2", "align: (left, left)"]),
    ("| A | Betrag |\n|---|---:|\n| 1 | 9 EUR |", ["align: (left, right)"]),
    ("Die Menge 3 \\* 4 Stück.", ['3 * 4']),
    ("Datei a\\_b.pdf", ["a_b.pdf"]),
    ("Rechnung 3 * 4 Stunden", ["3 * 4"]),
    ("Datei_v2.pdf ist da", ["Datei_v2.pdf"]),
    ("Az. 12//345 weiter im Text", ["12//345"]),
    ("Ein a /* b */ c Zeichen", ["/* b */"]),
    ("Nr. 12 und #import und mehr", ["#import"]),
    ("Kosten 5 $ und $x$ dazu", ["5 $", "$x$"]),
    ("Post an user@example.de heute", ["user@example.de"]),
    # In Typst steht ein geschützter Backslash doppelt; gelesen wird einer.
    ("Pfad C:\\\\Ordner\\\\Datei nennen", ["C:\\\\Ordner"]),
    ('Er sagte "Hallo" dazu', ["„Hallo“"]),
    ("Gilt z.B. und d.h. hier", [f"z.{NBSP}B.", f"d.{NBSP}h."]),
    ("Angebot -- Nachtrag folgt", ["–"]),
    # Einheiten (10 %, 5 km) stehen nur in einer Quelle und werden seit v0.4
    # nicht mehr automatisch verbunden — siehe tests/test_quellenlage.py.
    # § und Datum bleiben: Paragrafzeichen ist Satztechnik, das Datum ist
    # mehrfach belegt.
    ("Es sind 10 % und 5 km und § 3 und 25. August", [f"§{NBSP}3", f"25.{NBSP}August"]),
    ("5&nbsp;km und AT&amp;T und &copy; 2026", [f"5{NBSP}km", "AT&T", "©"]),
]

ABGELEHNT = [
    ("# Kapitel", "Überschriften"),
    ("Kapitel\n======", "Überschriften"),
    ("> Zitat hier", "Blockzitate"),
    ("Der Befehl `render` tut es.", "Code"),
    ("```\ncode\n```", "Code"),
    ("    vier Leerzeichen Einrückung", "Code"),
    ("Siehe [Website](https://example.de).", "Adresse ausschreiben"),
    ("Siehe [Website][1].\n\n[1]: https://example.de", "Adresse ausschreiben"),
    ("Siehe <https://example.de>.", "Adresse ausschreiben"),
    ("![Logo](logo.png)", "Bilder gehören ins Profil"),
    ("oben\n\n---\n\nunten", "Trennlinien"),
    ("Das ist ~~alt~~ neu.", "Durchgestrichener"),
    ("- [ ] offener Punkt\n- [ ] zweiter", "Aufgabenlisten"),
    ("Text[^1] dazu\n\n[^1]: Anmerkung", "Fußnoten"),
    ("Ein <br> Umbruch", "HTML"),
    ("Ein <abc> Element", "HTML"),
    ("- 5 °C waren es gestern.", "einzelner Strich"),
    ("- a\n  - b\n    - c\n  - d\n- e", "Ebenen"),
    ("| A | B |\n| 1 | 2 |", "Tabelle"),
]


@pytest.mark.parametrize("eingabe,erwartet", GESETZT, ids=[e[:34] for e, _ in GESETZT])
def test_wird_gesetzt(eingabe, erwartet):
    ergebnis = konvertiere(eingabe)
    for stueck in erwartet:
        assert stueck in ergebnis, f"{stueck!r} fehlt in:\n{ergebnis}"


@pytest.mark.parametrize("eingabe,grund", ABGELEHNT, ids=[e[:34] for e, _ in ABGELEHNT])
def test_wird_abgelehnt(eingabe, grund):
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere(eingabe)
    assert grund in str(fehler.value), f"Erwartet '{grund}', bekam: {fehler.value}"


# Bis Dialekt 1.1 waren diese beiden ein Fehler. Jetzt werden sie gesetzt UND
# gemeldet — in beiden Fassungen. Wo vorher abgebrochen wurde, gab es keine
# Ausgabe, die sich ändern könnte; ein gültiger Brief wird davon nicht ungültig.
GESETZT_MIT_HINWEIS = [
    ("1. Januar 2027 beginnt die Frist.", 1, "#enum(start: 1"),
    ("2. Mahnung zur Rechnung 4711", 2, "#enum(start: 2"),
]


@pytest.mark.parametrize("eingabe,start,erwartet", GESETZT_MIT_HINWEIS,
                         ids=[e[:34] for e, _, _ in GESETZT_MIT_HINWEIS])
def test_einzelne_nummer_wird_gesetzt_und_gemeldet(eingabe, start, erwartet):
    hinweise = []
    ergebnis = konvertiere(eingabe, hinweise=hinweise)
    # Der Startwert bleibt erhalten: Es wird nichts still umnummeriert.
    assert erwartet in ergebnis, f"{erwartet!r} fehlt in:\n{ergebnis}"
    assert len(hinweise) == 1, f"genau eine Meldung erwartet, bekam {hinweise}"
    assert "den Punkt schützen" in hinweise[0].meldung


def test_einzelne_nummer_meldet_auch_in_fassung_11():
    """Die Herabstufung gilt für beide Fassungen, nicht nur die neue."""
    hinweise = []
    konvertiere("2. Mahnung zur Rechnung 4711", dialekt="1.1", hinweise=hinweise)
    assert len(hinweise) == 1


def test_ohne_hinweisliste_geht_die_meldung_nicht_verloren_sondern_der_brief_steht():
    """Wer keine Liste mitgibt, bekommt trotzdem einen gesetzten Brief."""
    ergebnis = konvertiere("2. Mahnung zur Rechnung 4711")
    assert "#enum(start: 2" in ergebnis


def test_geschuetzter_punkt_macht_die_zeile_zu_text():
    """Die Korrektur, die die Fehlermeldung vorschlägt, muss auch funktionieren."""
    ergebnis = konvertiere("2\\. Mahnung zur Rechnung 4711")
    assert "#enum" not in ergebnis
    assert "2. Mahnung" in ergebnis


def test_fehler_nennt_die_zeile_der_originaldatei():
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere("Text\n\n## Titel", zeilenversatz=18)
    assert fehler.value.zeile == 21


def test_kein_zugelassener_commonmark_fall_bricht_ab():
    """Gegenprobe gegen die Positivliste: Was CommonMark für die zugelassenen
    Knotentypen vorsieht, muss durchlaufen — sonst ist die Liste zu eng."""
    faelle = [
        "*foo bar*", "**foo bar**", "_foo bar_", "__foo bar__",
        "*foo\nbar*", "foo *bar* baz", "a * foo bar * b",
        "- a\n- b\n- c", "1. a\n2. b", "10. a\n11. b",
        "foo\nbar", "foo  \nbar", "foo\\\nbar",
        "\\*not emphasized\\*", "\\_nor this\\_",
    ]
    for fall in faelle:
        konvertiere(fall)


# ── Die Referenz und der Renderer ───────────────────────────────────────────

def test_was_markdown_md_als_moeglich_listet_rendert_auch(tmp_path):
    """Jede Zeile der Positivtabelle einmal wirklich setzen.

    Eine Dokumentation, die niemand ausführt, altert still an der nächsten
    Änderung — und zwar zur gefährlichsten Sorte: Sie verspricht etwas, das das
    Werkzeug ablehnt. Diese Prüfung ist der Grund, warum die Tabelle in
    `references/markdown.md` eine Tabelle mit Syntax-Spalte ist.
    """
    from falzmarke import cli as falzmarke
    from conftest import REPO, SKILL

    proben = {
        "**fett**": "Ein **fetter** Teil.",
        "*kursiv*": "Ein *kursiver* Teil.",
        "***beides***": "Ein ***fett-kursiver*** Teil.",
        "harter Umbruch": "Erste Zeile\\\nzweite Zeile.",
        "Aufzählung": "- erster Punkt\n- zweiter Punkt",
        "nummerierte Liste": "1. erster Punkt\n2. zweiter Punkt",
        "Tabelle": "| A | B |\n|:--|--:|\n| 1 | 2 |",
        "Escape": "Drei \\* vier Stück.",
        "Entity": "Zeichen &amp; mehr.",
        "Zeichen mit Leerraum": "Die Rechnung 3 * 4 Stück.",
    }
    kopf = ("---\nprofil: example\n"
            "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]\n"
            "datum: 2026-08-25\nbetreff: Probe\n"
            "anrede: Sehr geehrte Damen und Herren,\n---\n")

    gescheitert = []
    for name, quelle in proben.items():
        brief = tmp_path / "b.md"
        brief.write_text(kopf + quelle + "\n", encoding="utf-8")
        try:
            falzmarke.rendere(brief, tmp_path / f"{abs(hash(name))}.pdf",
                              profil_verzeichnis=SKILL / "falzmarke" / "typst" / "profiles")
        except Exception as fehler:                      # noqa: BLE001
            gescheitert.append(f"{name}: {type(fehler).__name__}: {fehler}")

    assert not gescheitert, (
        "In references/markdown.md als möglich gelistet, aber abgewiesen:\n"
        + "\n".join(gescheitert))


def test_was_markdown_md_als_fehler_listet_bricht_auch_ab(tmp_path):
    """Die Gegenrichtung — sonst belegt der Test oben nur, dass irgendetwas geht."""
    from falzmarke import cli as falzmarke
    from conftest import SKILL

    proben = {
        "Überschrift": "# Eine Überschrift",
        "Link": "Siehe [hier](https://example.de).",
        "Bild": "![Logo](logo.png)",
        "Code": "Ein `code` im Text.",
        "Blockzitat": "> Ein Zitat.",
        "HTML": "Ein <b>Fettdruck</b>.",
        "durchgestrichen": "Ein ~~Fehler~~.",
        "Fußnote": "Ein Wort[^1].",
        "Aufgabenliste": "- [ ] offen",
    }
    kopf = ("---\nprofil: example\n"
            "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]\n"
            "datum: 2026-08-25\nbetreff: Probe\n"
            "anrede: Sehr geehrte Damen und Herren,\n---\n")

    durchgerutscht = []
    for name, quelle in proben.items():
        brief = tmp_path / "b.md"
        brief.write_text(kopf + quelle + "\n", encoding="utf-8")
        try:
            falzmarke.rendere(brief, tmp_path / f"{abs(hash(name))}.pdf",
                              profil_verzeichnis=SKILL / "falzmarke" / "typst" / "profiles")
            durchgerutscht.append(name)
        except Exception:                                # noqa: BLE001, S110
            pass

    assert not durchgerutscht, (
        "In references/markdown.md als Fehler gelistet, aber gesetzt: "
        + ", ".join(durchgerutscht))
