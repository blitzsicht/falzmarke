"""lint: die Prüfung vor dem Render.

Je Regel ein Fall, der sie auslöst, und einer, der sie nicht auslösen darf.
Ohne den zweiten wüsste man nur, dass die Regel feuert — nicht, ob sie trifft.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import pytest

from falzmarke import cli as falzmarke
from conftest import BEISPIELE, REPO, SKILL

CLI = SKILL / "scripts" / "falzmarke.py"
PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

KOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""


def schreibe(tmp_path, kopf: str = KOPF, body: str = "Text des Briefes.\n"):
    pfad = tmp_path / "brief.md"
    pfad.write_text(f"---\n{kopf}---\n{body}", encoding="utf-8")
    return pfad


def linte(tmp_path, kopf: str = KOPF, body: str = "Text des Briefes.\n"):
    return falzmarke.linte(schreibe(tmp_path, kopf, body), profil_verzeichnis=PROFILE)


def regeln(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde if b.schwere == "Fehler"}


def warnungen(bericht) -> set[str]:
    return {b.regel for b in bericht.befunde if b.schwere == "Warnung"}


def test_gueltiger_brief_ist_sauber(tmp_path):
    bericht = linte(tmp_path)
    assert bericht.ok, bericht.als_text("brief.md")
    assert bericht.anzahl_warnungen == 0


@pytest.mark.parametrize("name", [p.stem for p in BEISPIELE])
def test_beispiele_sind_sauber(name):
    bericht = falzmarke.linte(REPO / "examples" / f"{name}.md", profil_verzeichnis=PROFILE)
    assert bericht.ok, bericht.als_text(name)


# ── Datum ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("wert", ["morgen", "25.08.2026", "20260825", "nächsten Montag", ""])
def test_datum_muss_iso_sein(tmp_path, wert):
    bericht = linte(tmp_path, KOPF.replace("datum: 2026-08-25", f"datum: {wert or "''"}"))
    assert "datum" in regeln(bericht)


@pytest.mark.parametrize("wert", ["2026-08-25", "2028-02-29", "2026-01-01"])
def test_gueltige_daten_gehen_durch(tmp_path, wert):
    bericht = linte(tmp_path, KOPF.replace("datum: 2026-08-25", f"datum: {wert}"))
    assert "datum" not in regeln(bericht)


def test_unmoegliches_datum_ergibt_keinen_traceback(tmp_path):
    """`2026-13-45` scheiterte bis v0.1.2 in PyYAML mit einem Traceback."""
    brief = schreibe(tmp_path, KOPF.replace("datum: 2026-08-25", "datum: 2026-13-45"))
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "lint", str(brief)], capture_output=True, text=True, encoding="utf-8"
    )
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    assert "Traceback" not in ergebnis.stderr
    assert "2026-08-25" in ergebnis.stderr


# ── Betreff, Anrede, Gruß ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "betreff,regel",
    [
        ('"Betreff: Angebot"', "betreff"),
        ("Angebot Nr. 4711.", "betreff"),
        ("A" * 200, "betreff"),
    ],
)
def test_betreffregeln(tmp_path, betreff, regel):
    bericht = linte(tmp_path, KOPF.replace("betreff: Ein Betreff", f"betreff: {betreff}"))
    assert regel in regeln(bericht)


def test_zweizeiliger_betreff_ist_erlaubt(tmp_path):
    """Ein Angebot mit Vorgangsnummer und Gegenstand ist der Normalfall."""
    lang = "Angebot Nr. 2026-0815 über die Neugestaltung Ihrer Website samt Umzug"
    bericht = linte(tmp_path, KOPF.replace("betreff: Ein Betreff", f"betreff: {lang}"))
    assert bericht.ok, bericht.als_text("brief.md")


def test_anrede_ohne_komma(tmp_path):
    """Warnung statt Fehler: Die Regel steht nur in einer vollen Quelle.

    Bis v0.6.0 galt sie als mehrfach bestätigt und durfte Läufe scheitern
    lassen — gestützt auch auf den Wikipedia-Artikel. Der nennt das Wort
    „Komma" jedoch kein einziges Mal und sagt zur Anrede ausdrücklich, ihr
    Textinhalt sei dort nicht geregelt. Eine Quelle, die zur Regel schweigt,
    trägt sie nicht.
    """
    bericht = linte(tmp_path, KOPF.replace("Herren,", "Herren"))
    assert "anrede" in warnungen(bericht)
    assert "anrede" not in regeln(bericht)


def test_gruss_mit_komma(tmp_path):
    """Warnung statt Fehler: Die Regel steht nur in einer Quelle.

    Die Herabstufung kommt aus `regeln/din5008.yaml` und gilt, bis der
    Abgleich mit dem Originaltext der Norm sie bestätigt.
    """
    bericht = linte(tmp_path, KOPF + "gruss: Mit freundlichen Grüßen,\n")
    assert "gruss" in warnungen(bericht)
    assert "gruss" not in regeln(bericht)


# ── Anschrift und Vermerke ──────────────────────────────────────────────────

def test_sieben_anschriftzeilen(tmp_path):
    zeilen = ", ".join(f"Zeile {i}" for i in range(7))
    bericht = linte(tmp_path, KOPF.replace(
        "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]", f"empfaenger: [{zeilen}]"))
    # Warnung statt Fehler — die Sechs-Zeilen-Grenze steht nur in einer Quelle.
    assert "empfaenger" in warnungen(bericht)


def test_vier_vermerke(tmp_path):
    bericht = linte(tmp_path, KOPF + "vermerke: [Eins, Zwei, Drei, Vier]\n")
    assert "vermerke" in regeln(bericht)


def test_auslandsanschrift_ohne_grossschreibung_warnt(tmp_path):
    bericht = linte(tmp_path, KOPF.replace(
        "empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]",
        "empfaenger: [Muster SA, 12 rue de la Paix, 75002 Paris, FRANKREICH]"))
    assert bericht.ok
    assert any(b.regel == "empfaenger" for b in bericht.befunde)


# ── Informationsblock ───────────────────────────────────────────────────────

def test_zu_langer_infoblockwert(tmp_path):
    bericht = linte(tmp_path, KOPF + "infoblock:\n  email: " + "a" * 40 + "@example.de\n")
    assert any(r.startswith("infoblock.") for r in regeln(bericht))


def test_ungueltige_email(tmp_path):
    bericht = linte(tmp_path, KOPF + "infoblock:\n  email: keine-adresse\n")
    assert "infoblock.email" in regeln(bericht)


def test_telefon_ohne_din_schreibweise_warnt(tmp_path):
    bericht = linte(tmp_path, KOPF + 'infoblock:\n  telefon: "(0941) 620/9800"\n')
    assert bericht.ok, "die Schreibweise ist eine Empfehlung, kein Fehler"
    assert bericht.anzahl_warnungen >= 1


# ── Body ────────────────────────────────────────────────────────────────────

def test_markdownfehler_landet_im_bericht(tmp_path):
    bericht = linte(tmp_path, body="Text\n\n## Verbotene Überschrift\n")
    assert "markdown" in regeln(bericht)
    # Frontmatter bis Zeile 7, dann 'Text', Leerzeile, Überschrift in Zeile 10.
    assert any(b.zeile == 10 for b in bericht.befunde)


def test_zwei_leerzeichen_warnen(tmp_path):
    bericht = linte(tmp_path, body="Zeile eins  \nZeile zwei\n")
    assert bericht.ok
    assert any(b.regel == "umbruch" for b in bericht.befunde)


def test_kaputte_url_ist_fehler(tmp_path):
    bericht = linte(tmp_path, body="Siehe https:// dort weiter.\n")
    assert "url" in regeln(bericht)


def test_gueltige_url_geht_durch(tmp_path):
    bericht = linte(tmp_path, body="Siehe https://example.de/pfad dort.\n")
    assert bericht.ok


# ── Wortgetreue Auszüge (Issue #173) ────────────────────────────────────────
#
# Eine Auszugszeile über der Grenze hat zwei Ausgänge, und bis Issue #173 fiel
# nur einer auf: Ohne Leerzeichen läuft sie aus dem Satzspiegel, und `verify`
# meldet das. Mit Leerzeichen bricht der Satz sie um — das PDF hält danach alle
# Maße ein, nur der Wortlaut ist ein anderer.
#
# Deshalb steht hier zu jedem Fall SEIN Gegenstück: dieselbe Länge mit und ohne
# Leerzeichen. Bleibt eine der beiden stumm, misst die Prüfung nur den halben
# Fall — und genau so stand es vor diesem Vorgang da.

KOPF_11 = KOPF + 'dialekt: "1.1"\n'

#: 81 Zeichen mit Leerzeichen. Aus dem Vorgang: Im PDF steht sie auf zwei
#: Zeilen, die zweite beginnt mit `temperatur=` — als wäre sie ein eigener
#: Datensatz.
PROTOKOLL = "06:14:02 anlage=4711 status=betriebsbereit ok last=0.62 temperatur=21.4 druck=4.8"

#: 81 Zeichen ohne jede Umbruchstelle — der Fall, den `verify` schon fing.
OHNE_LEERZEICHEN = "x" * 81

#: 68 Zeichen, also genau an der Grenze. Muss stumm bleiben.
GERADE_NOCH = "abcdefg " * 8 + "abcd"


def _befunde_zu(tmp_path, body: str, kopf: str = None):
    return [b for b in linte(tmp_path, kopf or KOPF_11, body).befunde if b.regel == "auszug"]


def _im_block(zeile: str) -> str:
    return f"Der Auszug lautet:\n\n```\n{zeile}\n```\n"


@pytest.mark.parametrize("zeile,laenge", [(PROTOKOLL, 81), (OHNE_LEERZEICHEN, 81)])
def test_zu_lange_auszugszeile_wird_gemeldet(tmp_path, zeile, laenge):
    """Mit Leerzeichen und ohne — beide, sonst misst die Prüfung den halben Fall."""
    befunde = _befunde_zu(tmp_path, _im_block(zeile))
    assert len(befunde) == 1, f"kein Befund für eine {laenge}-Zeichen-Zeile"
    assert str(laenge) in befunde[0].meldung
    assert befunde[0].schwere == "Warnung", "der Brief soll trotzdem entstehen"


def test_der_befund_nennt_die_zeile_in_der_quelldatei(tmp_path):
    """Die Zeilennummer ist der Grund, warum die Prüfung hier steht und nicht
    am PDF: Dort ist sie nicht mehr bekannt."""
    pfad = schreibe(tmp_path, KOPF_11, _im_block(PROTOKOLL))
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    erwartet = pfad.read_text(encoding="utf-8").splitlines().index(PROTOKOLL) + 1
    assert [b.zeile for b in bericht.befunde if b.regel == "auszug"] == [erwartet]


def test_auszugszeile_an_der_grenze_bleibt_stumm(tmp_path):
    """Ohne diesen Fall wüsste man nur, dass die Prüfung feuert — nicht, ob sie
    trifft. 68 Zeichen passen, gemessen am 28.08.2026."""
    assert len(GERADE_NOCH) == 68
    assert _befunde_zu(tmp_path, _im_block(GERADE_NOCH)) == []


def test_dieselbe_zeile_ausserhalb_eines_auszugs_bleibt_stumm(tmp_path):
    """Fließtext darf umbrochen werden — dafür ist er da."""
    assert _befunde_zu(tmp_path, f"{PROTOKOLL}\n") == []


def test_ohne_dialekt_11_gilt_die_pruefung_nicht(tmp_path):
    """Ohne 1.1 gibt es keine Auszüge: Backticks sind dann gewöhnlicher Text,
    und den bricht der Satz zu Recht um."""
    assert _befunde_zu(tmp_path, _im_block(PROTOKOLL), kopf=KOPF) == []


def test_gegenprobe_die_pruefung_liest_den_sollwert(tmp_path, monkeypatch):
    """Ein Prüfmittel, das nie stumm werden kann, misst nicht — es meldet.

    Wird die Grenze hochgesetzt, muss der Befund verschwinden. Bleibt er, hängt
    die Meldung an irgendetwas anderem als der gemessenen Zeilenlänge.
    """
    from falzmarke import geometrie
    monkeypatch.setattr(geometrie, "AUSZUG_ZEICHEN", 500)
    assert _befunde_zu(tmp_path, _im_block(PROTOKOLL)) == []


@pytest.mark.parametrize("laenge,erwartet", [(71, 1), (70, 0)])
def test_auszug_im_satz_ab_71_zeichen(tmp_path, laenge, erwartet):
    """Im Satz sind es 70 statt 68 — der abgesetzte Block verliert zwei Zeichen
    an seinen Einzug."""
    inhalt = ("abcdefg " * 10)[:laenge]
    assert len(inhalt) == laenge
    befunde = _befunde_zu(tmp_path, f"Im Satz steht `{inhalt}` und dann Text.\n")
    assert len(befunde) == erwartet


# ── Anhanggrößen in Stufen (#183) ───────────────────────────────────────────
#
# Zu jeder Stufe gehört ihr Gegenstück knapp darunter. Ohne das wüsste man nur,
# dass gewarnt wird — nicht, ob an der richtigen Stelle.

KOPF_MAIL = """typ: email
profil: example
an: Sabine Kern <sabine.kern@example.de>
betreff: Probe Anhanggrenze
anrede: Sehr geehrte Frau Kern,
anlagen_dateien: [probe.bin]
"""


def _mit_anhang(tmp_path, megabyte: float):
    """Legt eine Mail mit einer Anlage dieser Größe an und lintet sie."""
    (tmp_path / "probe.bin").write_bytes(b"\0" * int(megabyte * 1_048_576))
    pfad = schreibe(tmp_path, KOPF_MAIL, "anbei die Datei probe.bin.\n\nViele Grüße\n")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    return [b for b in bericht.befunde if b.regel == "email.anlage_groesse"]


@pytest.mark.parametrize("megabyte,grenze", [(8, 10), (20, 25), (27, 35)])
def test_ueber_einer_stufe_wird_gewarnt(tmp_path, megabyte, grenze):
    """Die Dateigrößen liegen jeweils UNTER der Grenze, die Nachricht darüber —
    das ist der Punkt: 20 MB Datei sind 26,7 MB Nachricht, und daran scheitert
    ein Gmail-Konto, obwohl die Datei die 25 MB nicht erreicht."""
    befunde = _mit_anhang(tmp_path, megabyte)
    assert len(befunde) == 1, f"{megabyte} MB Datei ergaben {len(befunde)} Befunde"
    assert f"{grenze} MB" in befunde[0].meldung, befunde[0].meldung
    assert befunde[0].schwere == "Warnung", "Ebene praxis — nie ein Fehler"


@pytest.mark.parametrize("megabyte", [0.5, 7])
def test_darunter_bleibt_es_still(tmp_path, megabyte):
    """7 MB werden zu 9,3 MB Nachricht und bleiben unter der ersten Stufe."""
    assert _mit_anhang(tmp_path, megabyte) == []


def test_nur_die_hoechste_stufe_wird_gemeldet(tmp_path):
    """Wer 40 MB anhängt, braucht nicht dreimal dasselbe zu lesen."""
    befunde = _mit_anhang(tmp_path, 40)
    assert len(befunde) == 1
    assert "35 MB" in befunde[0].meldung


def test_gemessen_wird_die_nachricht_nicht_die_datei(tmp_path):
    """Der eigentliche Befund aus #183: Die Grenzen der Empfänger gelten der
    Nachricht, und MIME macht aus drei Byte vier. Wer die Dateigröße misst,
    misst an der Grenze vorbei."""
    befund = _mit_anhang(tmp_path, 20)[0]
    assert "26.7 MB" in befund.meldung, befund.meldung
    assert "20.0 MB Dateien" in befund.meldung, befund.meldung


def test_eine_fehlende_anlage_meldet_hier_nichts(tmp_path):
    """Die meldet der Erzeuger mit Dateinamen. Zweimal dieselbe Nachricht ist
    keine doppelte Sicherheit, sondern doppelter Lärm."""
    pfad = schreibe(tmp_path, KOPF_MAIL, "anbei die Datei probe.bin.\n")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert [b for b in bericht.befunde if b.regel == "email.anlage_groesse"] == []


def test_die_meldung_nennt_die_ebene(tmp_path):
    """ADR 0035: Eine Meldung, die „DIN" sagt, wo Mailprogramm-Praxis gemeint
    ist, ist von einer, die ihr Versprechen einlöst, nicht zu unterscheiden.
    Der Hinweis kommt aus der Deckelung — er belegt zugleich, dass die Meldung
    wirklich durch sie läuft."""
    befund = _mit_anhang(tmp_path, 20)[0]
    assert "Ebene: Praxis" in befund.meldung, befund.meldung


def test_der_kodierungsaufschlag_ist_der_der_base64_kodierung(tmp_path):
    """Vier Byte je drei — das ist keine Messung, sondern die Definition der
    Kodierung. Eine gerundete Prozentzahl wäre eine zweite Wahrheit daneben."""
    from falzmarke import lint as lint_modul
    assert lint_modul.KODIERUNGSAUFSCHLAG == 4 / 3


# ── Verhalten der Befehle ───────────────────────────────────────────────────

def test_render_bricht_vor_dem_setzen_ab(tmp_path):
    """Ein Eingabefehler darf keinen Render kosten — und kein PDF hinterlassen."""
    brief = schreibe(tmp_path, KOPF.replace("datum: 2026-08-25", "datum: morgen"))
    ziel = tmp_path / "aus.pdf"
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "render", str(brief), "-o", str(ziel)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert ergebnis.returncode == falzmarke.EXIT_EINGABE
    assert not ziel.exists()
    assert "Maße" not in ergebnis.stderr, "das ist kein Geometriebefund"


def test_json_ausgabe(tmp_path):
    brief = schreibe(tmp_path, KOPF.replace("datum: 2026-08-25", "datum: morgen"))
    ergebnis = subprocess.run(
        [sys.executable, str(CLI), "lint", str(brief), "--json"], capture_output=True, text=True, encoding="utf-8"
    )
    bericht = json.loads(ergebnis.stdout)
    assert bericht["ok"] is False and bericht["fehler"] == 1
    assert bericht["befunde"][0]["regel"] == "datum"
    assert bericht["befunde"][0]["korrektur"]


def test_lint_ist_schnell():
    """Ohne Typst — die Grenze ist großzügig, sie soll nur Ausreißer fangen."""
    quelle = REPO / "examples" / "brief-mehrseitig.md"
    start = time.perf_counter()
    falzmarke.linte(quelle, profil_verzeichnis=PROFILE)
    dauer = time.perf_counter() - start
    assert dauer < 0.5, f"lint brauchte {dauer*1000:.0f} ms"


# ── Unbekannte Frontmatter-Felder ───────────────────────────────────────────
#
# Bis v0.4.0 gab es dagegen keine Prüfung: Jeder Schlüssel, den `baue_daten`
# nicht abfragte, wurde still verworfen. Wer `signatur:` in den Brief schrieb —
# naheliegend, es steht im Profil — bekam keinen Fehler, sondern keine Wirkung.
# Das ist genau der stille Ausgang, den das Werkzeug sonst überall vermeidet.

def test_unbekanntes_feld_bricht_ab(tmp_path):
    bericht = linte(tmp_path, KOPF + "quatschfeld: irgendwas\n")
    assert "frontmatter" in regeln(bericht), bericht.als_text("brief.md")


def test_tippfehler_bekommt_den_richtigen_vorschlag(tmp_path):
    """`signature:` ist der wahrscheinlichste Fehlgriff — englisch statt deutsch."""
    bericht = linte(tmp_path, KOPF + "signature: assets/unterschrift.svg\n")
    text = bericht.als_text("brief.md")
    assert "frontmatter" in regeln(bericht), text
    assert "signatur" in text, text


@pytest.mark.parametrize("feld,wert", [
    ("form", "B"),
    ("norm", "din5008"),
    ("vermerke", "[Einschreiben]"),
    ("betreff_kurz", "Kurz"),
    ("gruss", "Mit freundlichen Grüßen"),
    ("unterzeichner", "i. A. Erika Muster"),
    ("signatur", "keine"),
    ("anlagen", "[Angebot]"),
    ("verteiler", "[Herrn Max Muster]"),
])
def test_dokumentierte_felder_bleiben_erlaubt(tmp_path, feld, wert):
    """Gegenprobe: Eine Sperre, die auch Erlaubtes abweist, wäre unbrauchbar."""
    bericht = linte(tmp_path, KOPF + f"{feld}: {wert}\n")
    assert "frontmatter" not in regeln(bericht), bericht.als_text("brief.md")


# ── Briefkopf: eine Höhe ohne Logo wirkt nicht (#244) ───────────────────────

def _profil_mit(tmp_path, briefkopf: str) -> Path:
    """Ein Profil, das sich nur im Abschnitt `briefkopf:` unterscheidet."""
    verzeichnis = tmp_path / "profile"
    verzeichnis.mkdir(exist_ok=True)
    (verzeichnis / "p.yaml").write_text(
        "absender: {name: Beispiel GmbH, strasse: Weg 1, plz: '93055', ort: Regensburg}\n"
        "ruecksendeangabe: Beispiel GmbH · Weg 1 · 93055 Regensburg\n"
        "form: B\n" + briefkopf, encoding="utf-8")
    return verzeichnis


def _linte_mit_profil(tmp_path, briefkopf: str):
    pfad = schreibe(tmp_path, KOPF.replace("profil: example", "profil: p"))
    return falzmarke.linte(pfad, profil_verzeichnis=_profil_mit(tmp_path, briefkopf))


def test_logohoehe_ohne_logo_warnt(tmp_path):
    """Sie wirkt nie — und bis #244 sagte das niemand. Gefunden hat die Prüfung
    als Erstes `example.yaml` selbst."""
    bericht = _linte_mit_profil(
        tmp_path, "briefkopf: {logo_hoehe_mm: 14, zeilen: [Beispiel GmbH]}\n")
    assert "briefkopf.logo_hoehe_mm" in warnungen(bericht)


def test_logohoehe_mit_logo_ist_still(tmp_path):
    """Der Gegenfall. Ohne ihn wüsste man nur, dass die Regel feuert — nicht,
    ob sie das Richtige trifft."""
    (tmp_path / "profile").mkdir(exist_ok=True)
    (tmp_path / "profile" / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="14"></svg>', encoding="utf-8")
    bericht = _linte_mit_profil(
        tmp_path, "briefkopf: {logo: logo.svg, logo_hoehe_mm: 14, zeilen: [Beispiel GmbH]}\n")
    assert "briefkopf.logo_hoehe_mm" not in warnungen(bericht)


def test_logo_ohne_hoehe_ist_still(tmp_path):
    """Die andere Richtung: Eine Höhe ist freiwillig, das Template hat einen
    Standardwert. Nur die Höhe OHNE Logo ist der Befund."""
    (tmp_path / "profile").mkdir(exist_ok=True)
    (tmp_path / "profile" / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="14"></svg>', encoding="utf-8")
    bericht = _linte_mit_profil(tmp_path, "briefkopf: {logo: logo.svg, zeilen: [Beispiel GmbH]}\n")
    assert "briefkopf.logo_hoehe_mm" not in warnungen(bericht)


def test_das_beispielprofil_warnt_nicht(tmp_path):
    """`example.yaml` trug die Höhe aktiv neben einem auskommentierten `logo:`.
    Ein mitgeliefertes Profil, das bei jedem Lint warnt, wäre Lärm."""
    assert "briefkopf.logo_hoehe_mm" not in warnungen(linte(tmp_path))


def test_unbekannter_infoblock_schluessel_bricht_ab(tmp_path):
    bericht = linte(tmp_path, KOPF + "infoblock: {handy: 0170 1234567}\n")
    assert "infoblock" in regeln(bericht), bericht.als_text("brief.md")


def test_die_feldliste_deckt_sich_mit_dem_datenvertrag(tmp_path):
    """Die Liste im Code und die Tabelle in der Doku sind zwei Stellen.

    Ohne diesen Abgleich altert eine von beiden still — und zwar die, die
    niemand ausführt.
    """
    import re

    from falzmarke import lint as lint_modul

    vertrag = (REPO / "skill" / "references" / "frontmatter.md").read_text(encoding="utf-8")
    block = vertrag.split("```yaml", 1)[1].split("```", 1)[0]
    dokumentiert = set(re.findall(r"^([a-z_]+):", block, flags=re.M))

    fehlend = dokumentiert - lint_modul.FRONTMATTER_FELDER
    assert not fehlend, f"In der Doku, aber vom Linter abgewiesen: {sorted(fehlend)}"


# ── Breite Tabellen in einer Mail (#104) ────────────────────────────────────

def _tabelle(spalten: int) -> str:
    kopf = "| " + " | ".join(f"S{i}" for i in range(spalten)) + " |"
    trenner = "|" + "---|" * spalten
    zeile = "| " + " | ".join("x" for _ in range(spalten)) + " |"
    return f"anbei die Übersicht:\n\n{kopf}\n{trenner}\n{zeile}\n"


KOPF_MAIL_SCHLICHT = """typ: email
profil: example
an: erika.muster@example.de
betreff: Probe Tabelle
anrede: Sehr geehrte Frau Muster,
"""


@pytest.mark.parametrize("spalten,erwartet", [(4, 0), (5, 1), (9, 1)])
def test_ab_fuenf_spalten_wird_gewarnt(tmp_path, spalten, erwartet):
    """Vier bleiben still, fünf melden. Ohne den Fall darunter wüsste man nur,
    dass gewarnt wird — nicht, ob an der richtigen Stelle."""
    bericht = linte(tmp_path, KOPF_MAIL_SCHLICHT, _tabelle(spalten))
    befunde = [b for b in bericht.befunde if b.regel == "email.tabelle_spalten"]
    assert len(befunde) == erwartet
    if erwartet:
        assert befunde[0].schwere == "Warnung", "Ebene praxis — nie ein Fehler"


def test_der_befund_zeigt_auf_die_kopfzeile(tmp_path):
    """Gezählt wird an der Trennzeile, gemeldet die Kopfzeile darüber — dort
    steht, was der Verfasser ändern muss."""
    pfad = schreibe(tmp_path, KOPF_MAIL_SCHLICHT, _tabelle(5))
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    erwartet = next(i for i, z in enumerate(zeilen, 1) if z.startswith("| S0"))
    assert [b.zeile for b in bericht.befunde if b.regel == "email.tabelle_spalten"] == [erwartet]


def test_im_brief_gilt_die_grenze_nicht(tmp_path):
    """Ein Brief steht auf 165 mm fester Breite — dort bricht nichts um."""
    bericht = linte(tmp_path, KOPF, _tabelle(9))
    assert [b for b in bericht.befunde if b.regel == "email.tabelle_spalten"] == []


# ── Die gemeldete Zeile ist die Zeile in der Datei (#184) ───────────────────
#
# Bis dahin nannte jede Frontmatter-Meldung eine Zeile zu viel. Aufgefallen ist
# es keinem Test: Sie prüften, DASS ein Befund kommt, und an einer Stelle die
# Zeile — die läuft aber über den Markdown-Parser, nicht über `_feldzeile`.
# Der Weg durch das Frontmatter hatte keine Messung.
#
# Deshalb steht die Erwartung hier nicht als Zahl, sondern wird aus der Datei
# gelesen. Eine feste Zahl hielte nur bis zum nächsten Feld im Kopf.

def _zeile_in_der_datei(pfad, anfang: str) -> int:
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    treffer = [i for i, z in enumerate(zeilen, 1) if z.startswith(anfang)]
    assert len(treffer) == 1, f"{anfang!r} steht {len(treffer)}× in der Datei"
    return treffer[0]


#: Zwei Felder an zwei verschiedenen Stellen des Kopfes, und zwei Kopflängen —
#: eine Verschiebung um eins fiele bei nur einem Fall womöglich mit dem
#: richtigen Wert zusammen.
KURZ = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Ein Betreff.
anrede: Sehr geehrte Damen und Herren
"""

LANG = """profil: example
form: B
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
vermerke: [Einschreiben]
datum: 2026-08-25
betreff_kurz: Kurz
betreff: Ein Betreff.
anrede: Sehr geehrte Damen und Herren
"""


@pytest.mark.parametrize("kopf", [KURZ, LANG], ids=["kurzer Kopf", "langer Kopf"])
@pytest.mark.parametrize("feld,regel", [("betreff:", "betreff"), ("anrede:", "anrede")])
def test_die_gemeldete_zeile_steht_wirklich_dort(tmp_path, kopf, feld, regel):
    """Der Betreff endet auf einen Punkt, die Anrede ohne Komma — beide lösen
    aus, und beide melden über `_feldzeile`."""
    pfad = schreibe(tmp_path, kopf)
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    gemeldet = [b.zeile for b in bericht.befunde if b.regel == regel]
    assert gemeldet, f"kein Befund für {regel} — dann misst dieser Test nichts"
    assert gemeldet[0] == _zeile_in_der_datei(pfad, feld), (
        f"{regel} gemeldet in Zeile {gemeldet[0]}, steht aber in Zeile "
        f"{_zeile_in_der_datei(pfad, feld)}")


def test_auch_in_einer_mail(tmp_path):
    """Der Fall, an dem #184 aufgefallen ist: `datum:` gehört in eine Mail
    nicht hinein, und die Meldung zeigte eine Zeile zu tief."""
    kopf = """typ: email
profil: example
an: erika.muster@example.de
betreff: Ein Betreff
datum: 2026-08-29
anrede: Sehr geehrte Frau Muster,
"""
    pfad = schreibe(tmp_path, kopf)
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    gemeldet = [b.zeile for b in bericht.befunde if b.regel == "email.datum"]
    assert gemeldet == [_zeile_in_der_datei(pfad, "datum:")]


def test_auch_der_hinweis_auf_eine_nicht_genannte_anlage(tmp_path):
    """Der letzte Aufruf, der `_feldzeile` mit leerem Kopf bekam und deshalb
    immer Zeile 1 meldete — dritter Punkt aus #184. Zeile 1 ist die
    `---`-Zeile: eine Fundstelle, an der nie etwas steht."""
    (tmp_path / "probe.pdf").write_bytes(b"%PDF-1.7\n")
    kopf = """typ: email
profil: example
an: erika.muster@example.de
betreff: Ein Betreff
anrede: Sehr geehrte Frau Muster,
anlagen_dateien: [probe.pdf]
"""
    pfad = schreibe(tmp_path, kopf, "Text ohne jede Erwähnung.\n")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    gemeldet = [b.zeile for b in bericht.befunde if b.regel == "email.anlage"]
    assert gemeldet == [_zeile_in_der_datei(pfad, "anlagen_dateien:")]
