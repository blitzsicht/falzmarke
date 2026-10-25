"""Zeichen, die niemand sieht — und die Stellen, an denen sie dazugehören.

Ein aus einem Browser kopierter Absatz bringt Zero-Width-Marken, weiche
Trennstriche und Bidi-Steuerzeichen mit. Bis `zeichen.py` prüfte das nichts;
sie standen hinterher in der `.eml` und im PDF.

## Warum hier `chr(0x200B)` steht und nicht das Zeichen selbst

Eine Datei über unsichtbare Zeichen darf keine enthalten. Mit dem Zeichen im
Quelltext zeigt kein Editor und kein Diff, was dasteht, `grep` findet es nicht,
und ein Werkzeug, das die Datei anfasst, kann es stillschweigend ersetzen — der
Test prüfte dann etwas anderes, als er behauptet. Die erste Fassung dieser
Datei hatte sie literal: 29 unsichtbare Zeichen, von denen man keines sah.

## Warum die Codepunkte hier wiederholt stehen

Sie werden **nicht** aus `zeichen.py` oder der Regeldatei gelesen. Täten sie
das, kämen Soll und Ist aus derselben Datei: Wer einen Codepunkt aus der Menge
entfernt, entfernt ihn aus dem Test mit, und der Lauf bliebe grün. Genau dieser
Fehler ist in diesem Repo schon passiert (Lehre „Nachgerechneter Sollwert
wandert mit“).

## Die Gegenrichtung trägt hier mehr als die Richtung

Ein geschütztes Leerzeichen ist nicht falsch — falzmarke setzt selbst eines
bei „z. B.“, „§ 7“, „12 kg“. Deshalb hält
`test_die_eigene_typografie_wird_nie_gemeldet` die komplette Ausgabe des
Typografie-Passes gegen die Prüfung. Eine Warnung, die am eigenen Ergebnis
anschlägt, kostet Vertrauen in alle anderen.
"""

from __future__ import annotations

import pytest

from conftest import SKILL
from falzmarke import cli, lint, typografie, zeichen

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

#: Das geschützte Leerzeichen — als Zahl, aus demselben Grund wie unten.
NBSP = chr(0x00A0)

MAIL = """---
typ: email
profil: example
an: erika.muster@example.de
betreff: Angebot Nr. 2026-0815
---
{text}
"""

#: Zeichen ohne Zweck in deutschem Text — Fehler. Je Klasse mindestens eines;
#: `test_jede_klasse_hat_einen_fall` hält das fest.
ZWECKLOS = [
    (0x200B, "Zero Width Space"),
    (0x200C, "Zero Width Non-Joiner"),
    (0x200D, "Zero Width Joiner ohne Bildzeichen"),
    (0x2060, "Word Joiner"),
    (0x00AD, "Soft Hyphen"),
    (0x034F, "Combining Grapheme Joiner"),
    (0x061C, "Arabic Letter Mark"),
    (0x200E, "Left-to-Right Mark"),
    (0x200F, "Right-to-Left Mark"),
    (0x202A, "Left-to-Right Embedding"),
    (0x202E, "Right-to-Left Override"),
    (0x2066, "Left-to-Right Isolate"),
    (0x206F, "Nominal Digit Shapes"),
    (0xFEFF, "Byte Order Mark mitten im Text"),
    (0xFE0F, "Variantenselektor 16 ohne Bildzeichen davor"),
    (0xE0101, "Variantenselektor 18 ohne Bildzeichen davor"),
    (0xE0041, "Tag-Block"),
    (0xFDD0, "Nichtzeichen U+FDD0"),
    (0xFFFE, "Nichtzeichen U+FFFE"),
    (0x10FFFE, "Nichtzeichen der letzten Ebene"),
    (0xE000, "Private Use"),
    (0xF0000, "Private Use, Ebene 15"),
    (0x0001, "Steuerzeichen U+0001"),
    (0x000B, "Zeilenvorschub U+000B"),
    (0x2028, "Line Separator"),
    (0x2029, "Paragraph Separator"),
    (0x115F, "Hangul Choseong Filler"),
    (0x1160, "Hangul Jungseong Filler"),
    (0x3164, "Hangul Filler"),
    (0xFFA0, "Halfwidth Hangul Filler"),
    (0x17B4, "Khmer Vowel Inherent Aq"),
    (0x17B5, "Khmer Vowel Inherent Aa"),
]

#: Leerzeichen, die nicht wie eines aussehen — Warnung, nie Fehler.
EXOTISCHE_LEERZEICHEN = [
    0x1680,   # Ogham Space Mark
    0x2000,   # En Quad
    0x2003,   # Em Space
    0x2009,   # Thin Space
    0x200A,   # Hair Space
    0x205F,   # Medium Mathematical Space
    0x3000,   # Ideographic Space
]

#: Was stumm bleiben muss: die Stellen, an denen der Satz selbst ein
#: geschütztes Leerzeichen setzt, dazu zwei Bildzeichen-Folgen.
STUMM = [
    f"Bitte z.{NBSP}B. den Karton nehmen.",
    f"Das gilt u.{NBSP}a.{NBSP}m. für die Rücksendung.",
    f"Die Lieferung wiegt 12{NBSP}kg.",
    f"Der Betrag lautet 1.234,56{NBSP}EUR.",
    f"Die Frist endet am 25.{NBSP}August 2026.",
    f"Siehe \u00a7{NBSP}7 Absatz 2.",
    f"Zur Rechnung Nr.{NBSP}4711.",
    f"Erreichbar unter Tel.{NBSP}0941 620-9800.",
    "Der Daumen \U0001f44d" + chr(0xFE0F) + " steht für Zustimmung.",
    "Das Zeichen \U0001f468" + chr(0x200D) + "\U0001f680 ist eine Folge.",
]


def _befunde(tmp_path, text: str) -> list[str]:
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(MAIL.format(text=text), encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    return [b.regel for b in bericht.befunde]


# -- Was gemeldet wird ------------------------------------------------------

@pytest.mark.parametrize("punkt,name", ZWECKLOS, ids=[n for _, n in ZWECKLOS])
def test_ein_zweckloses_zeichen_wird_gemeldet(punkt, name):
    befunde = zeichen.befunde(f"Der Karton{chr(punkt)}steht trocken.")
    assert [b.regel for b in befunde] == [zeichen.REGEL_UNSICHTBAR], \
        f"{name} (U+{punkt:04X}) wird nicht gemeldet"


@pytest.mark.parametrize("punkt", EXOTISCHE_LEERZEICHEN,
                         ids=[f"U+{p:04X}" for p in EXOTISCHE_LEERZEICHEN])
def test_ein_exotisches_leerzeichen_wird_gemeldet(punkt):
    befunde = zeichen.befunde(f"Der Karton{chr(punkt)}steht trocken.")
    assert [b.regel for b in befunde] == [zeichen.REGEL_GESCHUETZT]


def test_ein_geschuetztes_leerzeichen_an_falscher_stelle_wird_gemeldet():
    """Die Positivregel darf nicht alles durchlassen.

    Ohne diesen Test belegte `test_die_eigene_typografie_wird_nie_gemeldet`
    nur, dass die Prüfung schweigt — ein Muster, das jedes geschützte
    Leerzeichen erlaubt, bestünde ihn ebenfalls.
    """
    befunde = zeichen.befunde(f"Der{NBSP}Karton steht trocken.")
    assert [b.regel for b in befunde] == [zeichen.REGEL_GESCHUETZT]


def test_jede_klasse_hat_einen_fall():
    """Eine Zeichenmenge ohne Auslöser wäre nie gemessen.

    Gegenstück zu `test_jedes_muster_hat_einen_fall` in `test_floskeln.py`.
    Geprüft werden die Mengen, die `zeichen.py` führt — gegen die Fälle
    oben, die davon unabhängig geschrieben sind.
    """
    gemeldet = {ord(b.zeichen) for punkt, _ in ZWECKLOS
                for b in zeichen.befunde(f"a{chr(punkt)}b")}

    ungedeckt = [f"U+{p:04X}" for p in zeichen.ZWECKLOS_EINZELN if p not in gemeldet]
    assert not ungedeckt, f"ZWECKLOS_EINZELN ohne Fall: {ungedeckt}"

    assert gemeldet & zeichen.VARIANTENSELEKTOREN, \
        "kein Fall für die Variantenselektoren"
    assert any(zeichen._ist_nichtzeichen(p) for p in gemeldet), \
        "kein Fall für die Nichtzeichen"
    assert any(p in gemeldet for p in (0xE000, 0xF0000)), \
        "kein Fall für Private Use"


# -- Und was bleibt ---------------------------------------------------------

@pytest.mark.parametrize("satz", STUMM)
def test_was_dazugehoert_bleibt_stumm(satz):
    assert zeichen.befunde(satz) == [], satz


def test_die_eigene_typografie_wird_nie_gemeldet():
    """Der tragende Test: Die Prüfung meldet nie, was der Satz selbst setzt.

    Die Proben entstehen aus **allen** Listen, aus denen `typografie.py` seine
    geschützten Leerzeichen setzt. Nimmt jemand dort eine Liste hinzu, ohne
    `zeichen._positivmuster()` mitzuziehen, fällt dieser Test — und nicht
    erst der Nutzer, dem die eigene Ausgabe gemeldet wird.
    """
    proben = [f"Das gilt {ersatz} hier." for _, ersatz in typografie.ABKUERZUNGEN]
    proben += [f"Es wiegt 12 {einheit} netto." for einheit in typografie.EINHEITEN]
    proben += [f"Am 25. {monat} 2026." for monat in typografie.MONATE]
    proben += [f"Siehe {kuerzel} 4711 dazu." for kuerzel in typografie.VOR_ANGABE]
    proben += ["Nach \u00a7 7 Absatz 2."]

    gemeldet = []
    for probe in proben:
        gesetzt = probe
        for schritt, _ in typografie.SCHRITTE:
            gesetzt = schritt(gesetzt)
        befunde = zeichen.befunde(gesetzt)
        if befunde:
            gemeldet.append((probe, [b.meldung for b in befunde]))

    # Untergrenze gegen den leeren Lauf, nicht gegen die Listenlänge: Am
    # 25.10.2026 ergaben die vier Listen 51 Proben. Die Grenze darunter fängt
    # eine Liste, die leer läuft oder abgeschnitten ist, und bricht nicht bei
    # jeder Abkürzung, die jemand ergänzt.
    assert len(proben) > 45, f"zu wenige Proben: {len(proben)}"
    assert not gemeldet, f"die eigene Ausgabe wird gemeldet: {gemeldet}"


def test_die_positivregel_liest_aus_typografie(monkeypatch):
    """Gegenprobe zum Test darüber: Kommen die Stellen wirklich von dort?

    Ohne diese Probe könnte `_positivmuster()` eine eigene Liste führen, die
    heute zufällig dieselben Stellen trifft. Hier verliert `typografie.py` die
    Einheit `kg` — und `12 kg` muss gemeldet werden.
    """
    monkeypatch.setattr(typografie, "EINHEITEN",
                        [e for e in typografie.EINHEITEN if e != "kg"])
    monkeypatch.setattr(zeichen, "_POSITIVMUSTER", zeichen._positivmuster())
    befunde = zeichen.befunde(f"Es wiegt 12{NBSP}kg netto.")
    assert [b.regel for b in befunde] == [zeichen.REGEL_GESCHUETZT], \
        "die Positivstellen stammen nicht aus typografie.py"


def test_die_beispiele_bleiben_ohne_befund():
    """Der Bestand ändert sich durch die neue Prüfung nicht."""
    from conftest import BEISPIELE, EMAIL_BEISPIELE, URKUNDE_BEISPIELE

    beispiele = [*BEISPIELE, *EMAIL_BEISPIELE, *URKUNDE_BEISPIELE]
    assert len(beispiele) > 30, f"zu wenige Beispiele gefunden: {len(beispiele)}"
    for beispiel in beispiele:
        befunde = zeichen.befunde(beispiel.read_text(encoding="utf-8"))
        assert not befunde, f"{beispiel.name}: {[b.meldung for b in befunde]}"


def test_crlf_wird_nicht_gemeldet():
    """Eine unter Windows geschriebene Datei trägt CR am Zeilenende.

    Ohne die Ausnahme meldete die Prüfung jede ihrer Zeilen — ein Fehlalarm,
    der mit dem Betriebssystem kommt und nicht mit dem Text.
    """
    assert zeichen.befunde("Guten Tag,\r\n\r\nhier der Text.\r\n") == []


def test_tabulator_bleibt_bei_seiner_eigenen_regel():
    """`lint` meldet den Tabulator schon als Regel `tabulator`. Zweimal
    dasselbe zu melden macht die Meldung nicht wahrer."""
    assert zeichen.befunde("Spalte\tSpalte") == []


# -- Die Stufe steht in der Regeldatei, nicht im Code -----------------------

def test_ein_unsichtbares_zeichen_haelt_den_lauf_an(tmp_path):
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(MAIL.format(text=f"Der Karton{chr(0x200B)}steht trocken.\n"),
                    encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    assert zeichen.REGEL_UNSICHTBAR in [b.regel for b in bericht.befunde]
    assert not bericht.ok, "ein unsichtbares Zeichen muss den Lauf anhalten"


def test_ein_exotisches_leerzeichen_haelt_den_lauf_nicht_an(tmp_path):
    """`deckel: warnung` in `regeln/din5008.yaml` — und nur dort.

    `zeichen.py` trägt keine Stufe; gemeldet wird alles über
    `bericht.fehler`. Dass daraus eine Warnung wird, entscheidet die
    Regeldatei. Wer den Deckel dort entfernt, bringt diesen Test zu Fall, und
    genau da steht die Entscheidung.
    """
    pfad = tmp_path / "nachricht.md"
    pfad.write_text(MAIL.format(text=f"Der Karton{chr(0x2003)}steht trocken.\n"),
                    encoding="utf-8")
    bericht = cli.linte(pfad, profil_verzeichnis=PROFILE)
    assert zeichen.REGEL_GESCHUETZT in [b.regel for b in bericht.befunde]
    assert bericht.ok, "ein ungewöhnliches Leerzeichen darf den Lauf nicht anhalten"


def test_der_befund_traegt_keine_stufe():
    """Sonst gäbe es zwei Wahrheiten: eine im Code, eine in der Regeldatei."""
    assert "stufe" not in zeichen.Befund._fields


# -- Die Meldung ------------------------------------------------------------

def test_die_meldung_nennt_zeichen_und_stelle():
    befund, = zeichen.befunde(f"Der Karton{chr(0x200B)}steht trocken.")
    assert "U+200B" in befund.meldung
    assert "ZERO WIDTH SPACE" in befund.meldung
    assert befund.spalte == 11, befund.spalte
    assert befund.zeile == 1


def test_die_zeilennummer_zeigt_auf_die_quelldatei():
    """Wie in `lint.pruefe_body`: `versatz` ist die Zahl der Zeilen davor."""
    befund, = zeichen.befunde(f"erste\nzweite{chr(0x200B)}Zeile", versatz=5)
    assert befund.zeile == 7, befund.zeile


def test_im_wortgetreuen_auszug_wird_auch_gemeldet(tmp_path):
    """Dort am meisten: Ein Zero-Width-Zeichen verändert den zitierten
    Wortlaut, und genau dagegen ist der Auszug gebaut (#173)."""
    text = f"Aus dem Protokoll:\n\n```\ntemperatur{chr(0x200B)}=4\n```\n"
    assert zeichen.REGEL_UNSICHTBAR in _befunde(tmp_path, text)


# -- Die Regeldatei kennt die Prüfung ---------------------------------------

def test_beide_regeln_stehen_in_der_regeldatei():
    """`tests/test_quellenlage.py` prüft das aus dem Syntaxbaum; hier steht es
    noch einmal namentlich, damit der Fehlschlag die Regel nennt."""
    from falzmarke import regeln

    for name in (zeichen.REGEL_UNSICHTBAR, zeichen.REGEL_GESCHUETZT):
        regel = regeln.fuer_lint(name)
        assert regel is not None, f"{name} steht in keiner Regeldatei"
        assert regel["herkunft"] == "werkzeug", regel["herkunft"]

    assert regeln.deckel_von_lint(zeichen.REGEL_UNSICHTBAR) == regeln.DECKEL_FEHLER
    assert regeln.deckel_von_lint(zeichen.REGEL_GESCHUETZT) == regeln.DECKEL_WARNUNG


def test_lint_ruft_die_pruefung_wirklich_auf():
    """Gegenprobe gegen den stillen Ausfall: `zeichen.py` könnte vollständig
    sein und in `pruefe_body` nicht vorkommen."""
    bericht = lint.Bericht()
    lint.pruefe_body(f"Der Karton{chr(0x200B)}steht trocken.", 0, bericht)
    assert [b.regel for b in bericht.befunde] == [zeichen.REGEL_UNSICHTBAR]
