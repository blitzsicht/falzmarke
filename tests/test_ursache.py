"""Ein Befund nennt nicht nur das Symptom, sondern die Stelle in der Eingabe (#145).

`verify` meldete bisher `soll ≤ 190.0 ist 190.88 bei „1234567"`. Das ist die
Messung, und sie stimmt — aber wer den Brief geschrieben hat, sucht danach die
Stelle in seiner Markdown-Datei, und „190,88" hilft ihm dabei nicht.

## Was vorher gemessen wurde

Issue #145 schlug einen Reparaturmodus vor: zwei, drei Läufe, dazwischen die
Eingabe ändern. Der Vorgang nennt selbst den Haken — der Renderer ist
deterministisch, ein Wiederholungslauf allein ändert nichts — und schließt mit
einer offenen Frage: *Welche Fehlerklassen treten in der Praxis auf?*

Gemessen am 29.08.2026, und das Ergebnis verschiebt die Antwort:

| Fall | Wo er auffällt |
|---|---|
| Betreff über zwei Zeilen | **Datenvertrag**, vor dem Rendern |
| Anschriftfeld über sechs Zeilen | **Datenvertrag**, vor dem Rendern |
| sehr langer Brieftext | läuft durch, grün (wird zweiseitig) |
| sehr breite Empfängerzeile | läuft durch, grün |
| viele Anlagen | läuft durch, grün |
| zu breite Tabelle | `verify`, rechter Rand |
| wortgetreuer Auszug über 68 Zeichen | `verify`, rechter Rand |
| Wort ohne Trennstelle | `verify`, rechter Rand |

Die häufigen Fälle kommen gar nicht bis `verify` — der Datenvertrag weist sie
vorher ab, und seine Meldung nennt die Ursache schon („betreff: 187 Zeichen —
die Norm lässt höchstens 2 Zeilen zu"). Was übrig bleibt, sind **drei Klassen,
alle drei Überläufe nach rechts.** Für die gibt es jetzt eine Ursache im
Bericht; die Schleife braucht es dafür nicht.
"""

from __future__ import annotations

import pytest

from falzmarke import cli, geometrie
from conftest import REPO, SKILL

FIXTURES = REPO / "tests" / "fixtures" / "satzspiegel"
PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

#: Die drei Klassen, die `verify` überhaupt zum Anschlagen bringen — und woran
#: man die richtige Ursache erkennt. Gesucht wird nach einem Wort, nicht nach
#: dem ganzen Satz: Der Wortlaut darf sich bessern, ohne dass der Test bricht.
FAELLE = [
    ("tabelle-zu-breit.md", "Tabelle"),
    ("ueberlauf-auf-seite-zwei.md", "Tabelle"),
    ("codezeile-zu-lang.md", "wortgetreuer Auszug"),
    ("ueberschrift-ohne-trennstelle.md", "ohne Trennstelle"),
]


def _bericht(quelle, tmp_path) -> geometrie.Bericht:
    pdf, form = cli.rendere(FIXTURES / quelle, tmp_path / "probe.pdf",
                            profil_verzeichnis=PROFILE)
    return geometrie.pruefe(pdf, form)


def _rechter_rand(bericht) -> geometrie.Pruefung:
    treffer = [p for p in bericht.pruefungen
               if "rechter Rand" in p.name and not p.bestanden]
    assert treffer, "kein Überlauf gefunden — die Fixture löst nichts mehr aus"
    return treffer[0]


# ── Jede Klasse nennt ihre eigene Ursache ───────────────────────────────────

@pytest.mark.parametrize("quelle,erwartet", FAELLE)
def test_der_befund_nennt_die_ursache(quelle, erwartet, tmp_path):
    befund = _rechter_rand(_bericht(quelle, tmp_path))
    assert befund.ursache, f"{quelle} meldet den Überlauf ohne Ursache"
    assert erwartet in befund.ursache, f"{quelle}: {befund.ursache}"


@pytest.mark.parametrize("quelle,erwartet", FAELLE)
def test_und_nicht_die_einer_anderen(quelle, erwartet, tmp_path):
    """Gegenprobe: Ohne sie wäre eine Ursache, die immer dasselbe sagt, grün.

    Drei Klassen, drei Texte — wenn die Zuordnung nicht trennt, ist sie
    wertlos. Sie schickte den Leser dann an die falsche Stelle, und das ist
    schlechter als gar keine Ursache.
    """
    befund = _rechter_rand(_bericht(quelle, tmp_path))
    fremde = [w for _, w in FAELLE if w != erwartet]
    getroffen = [w for w in fremde if w in befund.ursache]
    assert not getroffen, f"{quelle} nennt auch: {getroffen} — {befund.ursache}"


def test_die_ursache_steht_im_text_des_berichts(tmp_path):
    """Sie nützt nur, wenn sie da erscheint, wo jemand liest."""
    text = _bericht("tabelle-zu-breit.md", tmp_path).als_text()
    assert "Ursache:" in text, text
    assert "Tabelle" in text


def test_und_im_json(tmp_path):
    """Der Weg für ein Modell, das den Bericht auswertet statt ihn zu lesen."""
    daten = _bericht("codezeile-zu-lang.md", tmp_path).als_dict()
    befunde = [p for p in daten["pruefungen"] if not p["bestanden"]]
    assert any("wortgetreuer Auszug" in p["ursache"] for p in befunde), befunde


# ── Und sie drängt sich nicht auf ───────────────────────────────────────────

def test_ein_gruener_lauf_bleibt_so_kurz_wie_er_war(tmp_path):
    """Der ausführliche Bericht landet bei jedem Render im Kontext.

    Eine Ursache je bestandener Prüfung würde ihn verdoppeln, ohne dass es
    etwas zu tun gäbe. Deshalb erscheint sie nur bei einem Befund.
    """
    pdf, form = cli.rendere(REPO / "examples" / "brief-form-b.md",
                            tmp_path / "gut.pdf", profil_verzeichnis=PROFILE)
    bericht = geometrie.pruefe(pdf, form)
    assert bericht.ok, "das Beispiel muss grün sein, sonst misst dieser Test etwas anderes"
    assert "Ursache:" not in bericht.als_text(ausfuehrlich=True)


def test_wo_die_ursache_unklar_ist_bleibt_sie_leer():
    """Eine geratene Ursache ist schlechter als keine.

    Ein Text in gewöhnlicher Schrift, außerhalb jeder Tabelle, dessen einzelnes
    Wort in den Satzspiegel passt: Dann steht der Überlauf fest, aber nicht
    sein Grund — und dann wird nichts behauptet.
    """
    span = geometrie.Span(text="Wort", x0=180.0, y0=100.0, x1=195.0, y1=104.0,
                          groesse=11.0, fett=False, font="LibertinusSerif-Regular")
    assert geometrie._ursache_ueberlauf(span, []) == ""


def test_der_auszugswert_stimmt_mit_der_fixture_ueberein():
    """68 Zeichen — die Zahl in der Meldung ist gemessen, nicht geschätzt.

    Sie steht in `tests/fixtures/satzspiegel/README.md` als Ergebnis einer
    Einschachtelung. Steht sie an einer der beiden Stellen anders, ist eine von
    beiden gealtert.
    """
    text = (FIXTURES / "README.md").read_text(encoding="utf-8")
    assert f"| Codeblock | {geometrie.AUSZUG_ZEICHEN} Zeichen" in text, \
        f"AUSZUG_ZEICHEN = {geometrie.AUSZUG_ZEICHEN} steht so nicht im README der Fixtures"


def test_der_inline_auszugswert_stimmt_mit_der_fixture_ueberein():
    """70 Zeichen — dieselbe Bindung wie oben, für den Auszug im Satz.

    Seit Issue #173 hängt an dieser Zahl eine Meldung des Linters. Stünde sie
    hier anders als in der Messung, meldete er an der falschen Stelle.
    """
    text = (FIXTURES / "README.md").read_text(encoding="utf-8")
    assert f"| Inline-Code | {geometrie.AUSZUG_ZEICHEN_INLINE} Zeichen" in text, \
        f"AUSZUG_ZEICHEN_INLINE = {geometrie.AUSZUG_ZEICHEN_INLINE} steht so nicht im README"
