"""Der Datenvertrag `typ: rechnung` (Issue #115).

Die Felder leiten sich aus § 14 Absatz 4 UStG ab — erhoben in #113, belegt in
`docs/recht.md`. Was hier geprüft wird, ist der Vertrag und seine Grenzen, noch
nicht das Setzen: Einen Emitter gibt es nicht, und genau deshalb bricht der
Renderer bei einer Rechnung ab (siehe ganz unten).

**Das Werkzeug rechnet nicht** (ADR 0039). Die Summenprobe vergleicht gegebene
Werte und meldet eine Abweichung als WARNUNG; sie ersetzt nichts und hält keinen
Lauf an. Beide Hälften dieser Zusage stehen unten als eigene Tests.

Jede Prüfung hat ihre Gegenprobe: die vollständige Rechnung, an genau einer
Stelle verändert. Die Kontrollprobe steht vorn — ohne sie belegte jede
Sabotage nur, dass der Linter IRGENDETWAS meldet.
"""

from __future__ import annotations

import pytest

from falzmarke import cli as falzmarke
from conftest import SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

#: Eine vollständige Rechnung, deren Summen stimmen: 1240 + 360 = 1600 netto,
#: 19 % davon 304, zusammen 1904 brutto.
KOPF = """\
typ: rechnung
profil: example
empfaenger:
  - Muster GmbH
  - Musterstraße 1
  - 12345 Musterstadt
datum: 2026-09-11
betreff: Rechnung für die Veranstaltung am 3. Oktober
rechnungsnummer: "2026-0042"
leistungsdatum: 2026-10-03
zahlungsziel: 2026-10-31
positionen:
  - bezeichnung: Technik und Aufbau
    menge: 1
    einzelpreis: 1240.00
    steuersatz: 19
    betrag: 1240.00
  - bezeichnung: Bestuhlung
    menge: 120
    einheit: Stück
    einzelpreis: 3.00
    steuersatz: 19
    betrag: 360.00
summen:
  netto: 1600.00
  steuer:
    - satz: 19
      betrag: 304.00
  brutto: 1904.00
anrede: Sehr geehrte Damen und Herren,
"""

BODY = "anbei unsere Rechnung für die Veranstaltung.\n"


def _datei(tmp_path, kopf: str = KOPF, body: str = BODY):
    pfad = tmp_path / "rechnung.md"
    pfad.write_text(f"---\n{kopf}---\n{body}", encoding="utf-8")
    return pfad


def _bericht(tmp_path, kopf: str = KOPF):
    return falzmarke.linte(_datei(tmp_path, kopf), profil_verzeichnis=PROFILE)


def _ersetzt(alt: str, neu: str) -> str:
    """Die vollständige Rechnung an genau einer Stelle verändert."""
    assert KOPF.count(alt) == 1, f"Anker {alt!r} steht {KOPF.count(alt)}× — die Probe misst nichts"
    return KOPF.replace(alt, neu, 1)


def _regeln(bericht, schwere: str | None = None) -> list[str]:
    return [b.regel for b in bericht.befunde if schwere is None or b.schwere == schwere]


# ── Die Kontrollprobe ───────────────────────────────────────────────────────

def test_eine_vollstaendige_rechnung_ist_sauber(tmp_path):
    bericht = _bericht(tmp_path)
    assert not bericht.befunde, [b.als_zeile("rechnung.md") for b in bericht.befunde]


def test_der_typ_ist_bekannt(tmp_path):
    """Die Vorbedingung aller anderen: Ohne `rechnung` in TYPEN fiele die Datei
    mit „typ ist unbekannt" auf den Brief zurück, und die Rechnungsprüfungen
    liefen nie."""
    assert "typ" not in _regeln(_bericht(tmp_path))


# ── Abnahme 2: Ein unbekanntes Feld bleibt nicht stumm ───────────────────────

def test_ein_tippfehler_in_einer_position_wird_gemeldet(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("  - bezeichnung: Bestuhlung", "  - bezeichung: Bestuhlung"))
    meldungen = [b for b in bericht.befunde if "bezeichung" in b.meldung]
    assert meldungen, "der Tippfehler blieb stumm"
    assert "bezeichnung" in meldungen[0].korrektur, "der Vorschlag nennt das richtige Feld"


def test_der_befund_nennt_die_zeile_der_positionen(tmp_path):
    """`_feldzeile` findet nur die oberste Ebene. Vor der Korrektur stand ein
    Tippfehler in einer Position auf Zeile 1 — gemessen am 11.09.2026."""
    kopf = _ersetzt("  - bezeichnung: Bestuhlung", "  - bezeichung: Bestuhlung")
    pfad = _datei(tmp_path, kopf)
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    erwartet = pfad.read_text(encoding="utf-8").splitlines().index("positionen:") + 1
    zeilen = {b.zeile for b in bericht.befunde if "bezeichung" in b.meldung}
    assert zeilen == {erwartet}, f"Zeile {zeilen}, erwartet {erwartet}"


def test_ein_unbekanntes_feld_in_den_summen_wird_gemeldet(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("  brutto: 1904.00", "  brutto: 1904.00\n  rabatt: 0"))
    assert any("rabatt" in b.meldung for b in bericht.befunde)


def test_ein_unbekanntes_feld_im_kopf_wird_gemeldet(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("zahlungsziel:", "zahlungsziel_tage: 30\nzahlungsziel:"))
    assert any("zahlungsziel_tage" in b.meldung for b in bericht.befunde)


# ── Die Pflichtfelder ────────────────────────────────────────────────────────

@pytest.mark.parametrize("feld", ["bezeichnung", "menge", "steuersatz", "betrag"])
def test_jedes_pflichtfeld_einer_position_wird_verlangt(tmp_path, feld):
    # Je Feld ein Anker, der in KOPF genau einmal steht. `steuersatz: 19` steht
    # in beiden Positionen — deshalb dort die Zeile davor als Kontext.
    alt, neu = {
        "bezeichnung": ("  - bezeichnung: Technik und Aufbau\n", "  - einheit: Stück\n"),
        "menge": ("    menge: 1\n", ""),
        "steuersatz": ("    einzelpreis: 1240.00\n    steuersatz: 19\n",
                       "    einzelpreis: 1240.00\n"),
        "betrag": ("    betrag: 1240.00\n", ""),
    }[feld]
    kopf = _ersetzt(alt, neu)
    bericht = _bericht(tmp_path, kopf)
    assert any(f"`{feld}:` fehlt" in b.meldung for b in bericht.befunde), \
        [b.meldung for b in bericht.befunde]


def test_eine_leere_rechnungsnummer_gibt_genau_einen_befund(tmp_path):
    """Vor der Korrektur meldeten zwei Prüfungen denselben Fehler — der
    Pflichtfeld-Check UND `rechnung.nummer`. Gemessen am 11.09.2026."""
    bericht = _bericht(tmp_path, _ersetzt('rechnungsnummer: "2026-0042"', 'rechnungsnummer: ""'))
    zur_nummer = [b for b in bericht.befunde if "rechnungsnummer" in (b.regel + b.meldung)]
    assert len(zur_nummer) == 1, [b.als_zeile("x") for b in zur_nummer]


def test_eine_nummer_aus_leerraum_wird_gemeldet(tmp_path):
    """Der Fall, den der Pflichtfeld-Check durchlässt: `"   "` ist nicht leer."""
    bericht = _bericht(tmp_path, _ersetzt('rechnungsnummer: "2026-0042"', 'rechnungsnummer: "   "'))
    assert "rechnung.nummer" in _regeln(bericht, "Fehler")


def test_ohne_positionen_keine_rechnung(tmp_path):
    kopf = KOPF.split("positionen:")[0] + "summen:" + KOPF.split("summen:")[1]
    bericht = _bericht(tmp_path, kopf)
    assert "positionen" in _regeln(bericht, "Fehler")


def test_positionen_muessen_eine_liste_sein(tmp_path):
    kopf = KOPF.split("positionen:")[0] + "positionen: Technik\n" + "summen:" + KOPF.split("summen:")[1]
    assert "rechnung.position" in _regeln(_bericht(tmp_path, kopf), "Fehler")


# ── Zahlen sind Zahlen ───────────────────────────────────────────────────────

def test_ein_betrag_mit_tausenderpunkt_ist_keine_zahl(tmp_path):
    """Die Schreibweise des gesetzten Briefes gehört nicht in die Quelle — dort
    wäre „1.240,00" mehrdeutig. Gemeldet statt still gedeutet."""
    bericht = _bericht(tmp_path, _ersetzt("    betrag: 1240.00", '    betrag: "1.240,00"'))
    assert any("ist keine Zahl" in b.meldung for b in bericht.befunde)


def test_ein_wahrheitswert_ist_keine_menge(tmp_path):
    """`bool` ist in Python eine Unterklasse von `int` — ohne eigene Abfrage
    ergäbe `menge: true` die Menge 1.

    `true` und nicht `ja`: PyYAML liest `ja` als TEXT, und dann träfe der Test
    den Zweig für Texte statt den für Wahrheitswerte. Der erste Entwurf stand
    genau dort — grün aus dem falschen Grund.
    """
    bericht = _bericht(tmp_path, _ersetzt("    menge: 1\n", "    menge: true\n"))
    assert any("`menge: True` ist keine Zahl" in b.meldung for b in bericht.befunde), \
        [b.meldung for b in bericht.befunde]


def test_ein_steuersatz_von_150_wird_gemeldet(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("    steuersatz: 19\n    betrag: 1240.00",
                                          "    steuersatz: 150\n    betrag: 1240.00"))
    assert any("außerhalb 0 bis 99" in b.meldung for b in bericht.befunde)


# ── Leistungszeitpunkt ───────────────────────────────────────────────────────

def test_leistungsdatum_und_zeitraum_zugleich_sind_ein_fehler(tmp_path):
    kopf = _ersetzt("leistungsdatum: 2026-10-03",
                    "leistungsdatum: 2026-10-03\nleistungszeitraum: {von: 2026-10-01, bis: 2026-10-03}")
    assert "rechnung.leistung" in _regeln(_bericht(tmp_path, kopf), "Fehler")


def test_ein_zeitraum_ohne_ende_wird_gemeldet(tmp_path):
    kopf = _ersetzt("leistungsdatum: 2026-10-03", "leistungszeitraum: {von: 2026-10-01}")
    assert "rechnung.leistung" in _regeln(_bericht(tmp_path, kopf), "Fehler")


def test_ein_vollstaendiger_zeitraum_ist_sauber(tmp_path):
    """Die Gegenrichtung: Ohne sie belegten die zwei Tests darüber nur, dass
    JEDER Zeitraum gemeldet wird."""
    kopf = _ersetzt("leistungsdatum: 2026-10-03", "leistungszeitraum: {von: 2026-10-01, bis: 2026-10-03}")
    assert not _bericht(tmp_path, kopf).befunde


def test_ein_ungueltiges_zahlungsziel_wird_gemeldet(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("zahlungsziel: 2026-10-31", "zahlungsziel: bald"))
    assert bericht.anzahl_fehler >= 1


# ── Die Summenprobe: sie meldet, und sie hält nicht an (ADR 0039) ────────────

def test_eine_falsche_nettosumme_ist_eine_warnung(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("  netto: 1600.00", "  netto: 1700.00"))
    assert "rechnung.summen" in _regeln(bericht, "Warnung")
    assert "rechnung.summen" not in _regeln(bericht, "Fehler"), \
        "ADR 0039: Eine Rechnung mit widersprüchlichen Summen geht durch"


def test_eine_falsche_summe_haelt_den_lauf_nicht_an(tmp_path):
    """Die zweite Hälfte der Zusage. Ohne sie belegte der Test darüber nur die
    Schwere der Meldung, nicht ihre Wirkung."""
    bericht = _bericht(tmp_path, _ersetzt("  netto: 1600.00", "  netto: 1700.00"))
    assert bericht.ok, "die Summenprobe darf den Lauf nicht anhalten"


def test_brutto_das_nicht_passt_wird_gemeldet(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("  brutto: 1904.00", "  brutto: 2000.00"))
    assert any("ergibt nicht brutto" in b.meldung for b in bericht.befunde)


def test_ein_cent_rundung_ist_keine_abweichung(tmp_path):
    """Die Toleranz: Ein Cent je Steuersatz entsteht, wenn je Satz gerundet
    wird. Das ist keine Abweichung, sondern Rundung."""
    bericht = _bericht(tmp_path, _ersetzt("  brutto: 1904.00", "  brutto: 1904.01"))
    assert "rechnung.summen" not in _regeln(bericht)


def test_zwei_cent_sind_eine_abweichung(tmp_path):
    """Die Gegenprobe zur Toleranz — ohne sie belegte der Test darüber nur,
    dass die Prüfung gar nicht rechnet."""
    bericht = _bericht(tmp_path, _ersetzt("  brutto: 1904.00", "  brutto: 1904.02"))
    assert "rechnung.summen" in _regeln(bericht, "Warnung")


def test_der_steuerbetrag_wird_nicht_nachgerechnet(tmp_path):
    """ADR 0039 und Abnahme 3 aus #115: Was das Werkzeug nicht berechnet, sagt es
    ausdrücklich. 19 % von 1600 sind 304 — ein Steuerbetrag von 300 bleibt
    trotzdem stumm, solange Netto plus Steuer das angegebene Brutto ergibt."""
    kopf = _ersetzt("      betrag: 304.00", "      betrag: 300.00")
    kopf = kopf.replace("  brutto: 1904.00", "  brutto: 1900.00")
    assert "rechnung.summen" not in _regeln(_bericht(tmp_path, kopf))


# ── Eine Rechnung ist ein Schreiben ──────────────────────────────────────────

def test_die_briefpruefungen_gelten_weiter(tmp_path):
    """#115: „Der Brieftext bleibt." Die Rechnung läuft durch den Briefzweig,
    und seine Prüfungen — hier die Anschriftzone — gelten dort genauso."""
    zu_viel = "empfaenger:\n" + "".join(f"  - Zeile {i}\n" for i in range(1, 9))
    kopf = _ersetzt(
        "empfaenger:\n  - Muster GmbH\n  - Musterstraße 1\n  - 12345 Musterstadt\n", zu_viel)
    # Ohne Schwere-Filter: Die Anschriftzone ist im Katalog nur einzeln belegt
    # und meldet deshalb als Warnung. Belegt werden soll hier, DASS die
    # Briefprüfung auch bei einer Rechnung läuft — nicht, wie hart.
    assert "empfaenger" in _regeln(_bericht(tmp_path, kopf))


def test_ein_mailfeld_in_der_rechnung_wird_gemeldet(tmp_path):
    """`an:` bedeutet in einer Rechnung dasselbe wie im Brief: nichts."""
    bericht = _bericht(tmp_path, _ersetzt("datum: 2026-09-11", "datum: 2026-09-11\nan: a@example.de"))
    assert any("an" in b.meldung and "empfaenger" in (b.korrektur + b.meldung)
               for b in bericht.befunde), [b.meldung for b in bericht.befunde]


# ── Der Renderer setzt noch keine Rechnung ───────────────────────────────────

def test_der_renderer_bricht_bei_einer_rechnung_ab(tmp_path):
    """Ohne diesen Abbruch fiele eine Rechnung in den Briefzweig und entstünde als
    PDF — OHNE Positionen und Summen, und ohne ein Wort darüber. Das ist genau
    die Fehlerart, gegen die das Werkzeug antritt."""
    with pytest.raises(Exception, match="typ: rechnung"):
        falzmarke.rendere(_datei(tmp_path), tmp_path / "rechnung.pdf",
                          profil_verzeichnis=PROFILE)
    assert not (tmp_path / "rechnung.pdf").exists(), "es darf kein PDF entstehen"
