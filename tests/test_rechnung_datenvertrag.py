"""Der Datenvertrag `typ: rechnung` (Issue #115).

Die Felder leiten sich aus § 14 Absatz 4 UStG ab — erhoben in #113, belegt in
`docs/recht.md`. Geprüft wird der Vertrag und seine Grenzen; seit #116 unten auch
das Setzen: Der Renderer bricht nicht mehr pauschal ab, sondern setzt die Rechnung
und bettet ihre XML ein — und bricht nur noch ab, wenn dafür etwas fehlt.

**Das Werkzeug rechnet nicht** (ADR 0039). Die Summenprobe vergleicht gegebene
Werte und meldet eine Abweichung als WARNUNG; sie ersetzt nichts und hält keinen
Lauf an. Beide Hälften dieser Zusage stehen unten als eigene Tests.

Jede Prüfung hat ihre Gegenprobe: die vollständige Rechnung, an genau einer
Stelle verändert. Die Kontrollprobe steht vorn — ohne sie belegte jede
Sabotage nur, dass der Linter IRGENDETWAS meldet.
"""

from __future__ import annotations

import os

import pytest

from falzmarke import cli as falzmarke
from conftest import REPO, SKILL, ohne_typografiehinweise

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
    # Ohne die Hinweise des Typografie-Passes (#330): Der Füllsatz „unsere
    # Rechnung für …" trägt einen; hier geht es um den Datenvertrag.
    befunde = ohne_typografiehinweise(bericht)
    assert not befunde, [b.als_zeile("rechnung.md") for b in befunde]


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
    assert not ohne_typografiehinweise(_bericht(tmp_path, kopf))


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


# ── Der Renderer setzt die Rechnung — aber nur eine vollständige ────────────
#
# Bis #116 brach er bei jeder Rechnung ab, weil der Emitter fehlte. Jetzt setzt
# er sie und bettet die XML ein. Der bewahrenswerte Kern des alten Tests bleibt:
# Was unvollständig ist, wird NICHT still als Brief gesetzt — dann fehlten
# Positionen und Summen, und niemand erführe davon.

#: Was die XML über den Datenvertrag hinaus braucht (#116): den Empfänger in
#: Feldern und die Bemessungsgrundlage je Steuersatz.
FUER_DIE_XML = """\
empfaenger_anschrift:
  name: Muster GmbH
  strasse: Musterstraße 1
  plz: "12345"
  ort: Musterstadt
  land: DE
"""


def test_eine_unvollstaendige_rechnung_wird_nicht_gesetzt(tmp_path):
    """`empfaenger_anschrift:` fehlt — dann entsteht kein PDF, nicht eines ohne
    maschinenlesbare Daten. Die stille Variante wäre die teure."""
    with pytest.raises(Exception, match="empfaenger_anschrift"):
        falzmarke.rendere(_datei(tmp_path), tmp_path / "rechnung.pdf",
                          profil_verzeichnis=PROFILE)
    assert not (tmp_path / "rechnung.pdf").exists(), "es darf kein PDF entstehen"


def test_eine_vollstaendige_rechnung_traegt_ihre_daten_mit(tmp_path):
    """Die Gegenrichtung. Ohne sie belegte der Test darüber nur, dass irgendetwas
    scheitert — nicht, dass der gute Fall durchgeht."""
    import pypdf

    from falzmarke import geometrie

    kopf = KOPF + FUER_DIE_XML
    kopf = kopf.replace("      betrag: 304.00", "      basis: 1600.00\n      betrag: 304.00")
    assert "basis:" in kopf, "die Probe hat die Bemessungsgrundlage nicht gesetzt"

    pdf, _ = falzmarke.rendere(_datei(tmp_path, kopf), tmp_path / "rechnung.pdf",
                               profil_verzeichnis=PROFILE)

    # A-3b statt A-2b: Das ist der Unterschied, den die Einbettung macht.
    assert geometrie.pdfa_stufe(pdf) == "3b"

    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    anhaenge = [e.get_object() for e in wurzel.get("/AF", [])]
    assert len(anhaenge) == 1, anhaenge
    # Der Name ist nicht frei: An ihm findet die Software des Empfängers die Datei.
    assert str(anhaenge[0].get("/F")) == "factur-x.xml"
    # `Alternative`, nicht `Data` — die XML ist dasselbe Dokument, nicht eine Beilage.
    assert str(anhaenge[0].get("/AFRelationship")) == "/Alternative"

    # Ohne das Erweiterungsschema erwartet kein Prüfwerkzeug die Beilage.
    assert "urn:factur-x" in geometrie.xmp_lesen(pdf)


# ── `empfaenger_anschrift:` — der Empfänger in Feldern (#116) ───────────────
#
# `empfaenger:` sind ein bis sechs freie Zeilen. Für das Anschriftfeld im
# Fensterumschlag genügt das; die eingebettete XML braucht Straße, PLZ, Ort und
# Land einzeln. Ob die zweite Zeile die Straße ist oder eine zweite Namenszeile,
# lässt sich nicht ablesen — geraten hieße, den Empfänger falsch zu adressieren.

ANSCHRIFT = """\
empfaenger_anschrift:
  name: Muster GmbH
  strasse: Musterstraße 1
  plz: "12345"
  ort: Musterstadt
  land: DE
"""


def test_eine_vollstaendige_empfaengeranschrift_ist_sauber(tmp_path):
    """Kontrollprobe: Ohne sie belegten die Fälle darunter nichts."""
    bericht = _bericht(tmp_path, KOPF + ANSCHRIFT)
    assert "rechnung.empfaenger" not in _regeln(bericht), bericht.als_text()


def test_ohne_das_feld_wird_nichts_gemeldet(tmp_path):
    """Wer einen Brief setzt, braucht es nicht — erst die XML verlangt es."""
    assert "rechnung.empfaenger" not in _regeln(_bericht(tmp_path))


@pytest.mark.parametrize("feld", ["name", "strasse", "plz", "ort", "land"])
def test_ein_fehlendes_feld_wird_gemeldet(tmp_path, feld):
    gekuerzt = "\n".join(z for z in ANSCHRIFT.splitlines()
                         if not z.strip().startswith(f"{feld}:")) + "\n"
    assert f"  {feld}:" not in gekuerzt, "die Probe hat nichts entfernt"
    bericht = _bericht(tmp_path, KOPF + gekuerzt)
    assert "rechnung.empfaenger" in _regeln(bericht, "Fehler"), bericht.als_text()


def test_ein_tippfehler_im_feldnamen_bleibt_nicht_stumm(tmp_path):
    """`strasee:` sähe aus wie eine gesetzte Angabe und wäre keine."""
    bericht = _bericht(tmp_path, KOPF + ANSCHRIFT.replace("strasse:", "strasee:"))
    assert "rechnung.empfaenger" in _regeln(bericht, "Fehler"), bericht.als_text()


def test_freie_zeilen_statt_felder_werden_gemeldet(tmp_path):
    """Der naheliegende Fehler: dieselbe Form wie `empfaenger:` verwenden."""
    bericht = _bericht(tmp_path, KOPF + "empfaenger_anschrift: Musterstraße 1\n")
    assert "rechnung.empfaenger" in _regeln(bericht, "Fehler"), bericht.als_text()


# ── Dieselbe Rechnung, aber über die Kommandozeile ──────────────────────────
#
# Die Tests oben rufen `rendere()` auf. Das deckt NICHT, was `befehl_render`
# darüber hinaus tut — und genau dort saß am 12.09.2026 ein Fehler: Der
# Messbericht leitete die erwartete PDF/A-Stufe aus dem Frontmatter-Feld
# `eingebettet:` ab und erwartete 2b, während die Rechnung korrekt 3b lieferte.
# Der Lauf endete mit Exit 2 für ein Dokument, das in Ordnung war.
#
# Gefunden hat das kein Test, sondern ein Aufruf von Hand: Rechnung und CLI sind
# zwei Achsen, die sich nirgends kreuzten. Hier kreuzen sie sich.

def test_die_kommandozeile_setzt_die_beispielrechnung(tmp_path):
    import subprocess
    import sys

    ziel = tmp_path / "rechnung.pdf"
    # `--verbose`, weil der Bericht bestandene Prüfungen sonst nicht einzeln
    # zeigt: Ohne den Schalter stünde hier nur „35/35 Maße eingehalten". Das
    # war der erste Entwurf dieses Tests, und er prüfte damit nichts von dem,
    # was er zu prüfen vorgab.
    lauf = subprocess.run(
        [sys.executable, "-m", "falzmarke.cli", "render",
         str(REPO / "examples" / "rechnung.md"), "-o", str(ziel), "--verbose"],
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONPATH": str(SKILL)},
    )
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert ziel.is_file()
    # Die Stufe steht im Bericht, und sie muss die richtige sein — nicht die,
    # die ein Brief hätte. Genau hier lag der Fehler vom 12.09.2026.
    assert "PDF/A-3b" in lauf.stdout, lauf.stdout
    assert "PDF/A-2b" not in lauf.stdout, lauf.stdout
    # Und die Fassung, gegen die gesetzt wurde (ADR 0039).
    assert "factur-x.xml" in lauf.stdout and "EN 16931" in lauf.stdout, lauf.stdout


# ── Beträge: Zahl, höchstens zwei Stellen, Steuergesamt (Review von #116) ───

def test_ein_betrag_mit_drei_nachkommastellen_wird_gemeldet(tmp_path):
    bericht = _bericht(tmp_path, _ersetzt("    betrag: 1240.00", "    betrag: 1240.005"))
    assert "rechnung.betrag_stellen" in _regeln(bericht, "Fehler"), bericht.als_text()


def test_ein_summenfeld_aus_text_wird_gemeldet(tmp_path):
    """Vorher übersprang die Rechenprobe den Text still."""
    bericht = _bericht(tmp_path, _ersetzt("  netto: 1600.00", '  netto: "abc"'))
    assert "rechnung.betrag_stellen" in _regeln(bericht, "Fehler"), bericht.als_text()


def test_ein_abweichendes_steuer_gesamt_warnt_und_haelt_nicht_an(tmp_path):
    """Übertragen wird, was dasteht — die Probe warnt nur."""
    bericht = _bericht(tmp_path, _ersetzt("  brutto: 1904.00",
                                          "  brutto: 1904.00\n  steuer_gesamt: 305.00"))
    assert "rechnung.summen" in _regeln(bericht, "Warnung"), bericht.als_text()
    assert "rechnung.summen" not in _regeln(bericht, "Fehler"), bericht.als_text()
    assert "steuer_gesamt" not in " ".join(b.meldung for b in bericht.befunde
                                           if b.regel == "rechnung.summen"
                                           and "unbekannt" in b.meldung)


# ── XRechnung im Datenvertrag (#117, Teil 2) ────────────────────────────────

XRECHNUNG = REPO / "examples" / "xrechnung.md"


def _xrechnung_regeln(tmp_path, ersetzen: tuple[str, str] | None = None, anhaengen: str = "") -> set[str]:
    text = XRECHNUNG.read_text(encoding="utf-8")
    if ersetzen:
        assert ersetzen[0] in text, ersetzen
        text = text.replace(*ersetzen)
    if anhaengen:
        text = text.replace("leistungsdatum:", anhaengen + "\nleistungsdatum:", 1)
    pfad = tmp_path / "x.md"
    pfad.write_text(text, encoding="utf-8")
    # Ohne die Hinweise des Typografie-Passes (#330), wie die Kontrollproben unten.
    return {b.regel for b in ohne_typografiehinweise(falzmarke.linte(pfad, PROFILE))}


def test_das_xrechnung_beispiel_ist_sauber(tmp_path):
    """Kontrollprobe — ohne sie belegte jede Sabotage darunter nichts."""
    assert _xrechnung_regeln(tmp_path) == set()


def test_eine_falsche_pruefziffer_der_leitweg_id(tmp_path):
    assert "rechnung.leitweg_id" in _xrechnung_regeln(
        tmp_path, ('leitweg_id: "04011000-1234512345-06"', 'leitweg_id: "04011000-1234512345-07"'))


def test_eine_unbekannte_auspraegung(tmp_path):
    assert "rechnung.erechnung" in _xrechnung_regeln(
        tmp_path, ("erechnung: xrechnung", "erechnung: zugferd-extended"))


def test_beide_referenzen_zugleich(tmp_path):
    assert "rechnung.referenz" in _xrechnung_regeln(tmp_path, anhaengen='kaeuferreferenz: "4711"')


def test_xrechnung_ohne_referenz(tmp_path):
    assert "rechnung.xrechnung" in _xrechnung_regeln(
        tmp_path, ('leitweg_id: "04011000-1234512345-06"\n', ""))


def test_xrechnung_ohne_empfaengeradresse(tmp_path):
    assert "rechnung.xrechnung" in _xrechnung_regeln(tmp_path, ("  adresse: einkauf@example.de\n", ""))


def test_gegenprobe_ohne_empfaengeradresse_unter_en16931_still(tmp_path):
    """Die Pflicht gilt nur für XRechnung. Unter EN 16931 bleibt die Adresse freiwillig."""
    # Beides entfernen: die Ausprägung UND die Adresse. Nur die Ausprägung zu
    # streichen ließ nichts fehlen — der Test blieb auch mit der Pflicht unter
    # EN 16931 grün (Sabotage am 13.09.2026, „Testfall an der falschen Stelle").
    pfad_text = XRECHNUNG.read_text(encoding="utf-8").replace("erechnung: xrechnung\n", "") \
        .replace("  adresse: einkauf@example.de\n", "")
    assert "erechnung:" not in pfad_text and "einkauf@example.de" not in pfad_text
    pfad = tmp_path / "en16931.md"
    pfad.write_text(pfad_text, encoding="utf-8")
    text_regeln = {b.regel for b in ohne_typografiehinweise(falzmarke.linte(pfad, PROFILE))}
    assert text_regeln == set(), text_regeln


def test_eine_kaputte_empfaengeradresse(tmp_path):
    assert "rechnung.empfaenger_adresse" in _xrechnung_regeln(
        tmp_path, ("  adresse: einkauf@example.de\n", "  adresse: einkauf@@example\n"))
