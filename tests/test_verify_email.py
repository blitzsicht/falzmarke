"""`verify --email`: misst die fertige Datei, nie die Absicht (#64, E7).

Der Aufbau ist der von `test_gegenbeweis.py`: Jede Prüfung bekommt eine
Sabotage, die sie auslösen muss, und jede Sabotage ein `assert`, dass sie die
Datei überhaupt verändert hat. Eine wirkungslose Ersetzung ergibt sonst ein
grünes Ergebnis, das nichts belegt.

Sabotiert wird die **fertige `.eml` als Text**, nicht der Erzeuger. Das ist der
Punkt der Sache: Ein Prüfer, der nur gegen den eigenen Erzeuger antritt,
bestätigt den gemeinsamen Bauplan — er muss auch eine Datei beanstanden, die
von woanders kommt.
"""

from __future__ import annotations

import re

import pytest
import yaml

from falzmarke import eml, markdown as md, pruefung_eml
from conftest import SKILL

PROFIL_DATEI = SKILL / "falzmarke" / "typst" / "profiles" / "example.yaml"
QUELLE = ("wie besprochen erhalten Sie das Angebot.\n\n"
          "| Posten | Betrag |\n|:--|--:|\n| Technik | 1.240,00 |\n")
KOPF = {"an": "erika.muster@example.de", "betreff": "Angebot Nr. 2026-0815",
        "anrede": "Sehr geehrte Frau Muster,", "unterzeichner": "Erika Muster"}


@pytest.fixture
def profil() -> dict:
    return yaml.safe_load(PROFIL_DATEI.read_text(encoding="utf-8"))


@pytest.fixture
def roh(profil) -> str:
    return eml.baue(KOPF, profil, QUELLE, md.lies(QUELLE), mit_quelle=True).as_string()


def _pruefe(tmp_path, text: str, zeilenende: str = "\n"):
    """Schreibt die Nachricht und misst sie.

    `zeilenende` ist ein Parameter, weil RFC 5322 CRLF vorschreibt und ein
    Prüfer beides vertragen muss. Ohne `newline=""` setzt Python unter Windows
    ohnehin CRLF ein — genau daran ist der erste Lauf gescheitert, und zwar
    nur dort.
    """
    pfad = tmp_path / "nachricht.eml"
    pfad.write_text(text.replace("\n", zeilenende), encoding="utf-8", newline="")
    return pruefung_eml.pruefe(pfad)


def _gescheitert(bericht) -> set[str]:
    return {p.name for p in bericht.pruefungen if not p.bestanden}


# ── Die Kontrollprobe ───────────────────────────────────────────────────────

def test_eine_unversehrte_nachricht_ist_gruen(tmp_path, roh):
    """Ohne sie misst jede Sabotage nur die Kopie, nicht die Abweichung."""
    bericht = _pruefe(tmp_path, roh)
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)
    assert len(bericht.pruefungen) >= 20, "zu wenige Prüfungen — der Test misst kaum etwas"


def test_ohne_quellteil_bleibt_es_gruen(tmp_path, profil):
    """Der `text/markdown`-Teil ist die Ausnahme, nicht die Regel (ADR 0034)."""
    ohne = eml.baue(KOPF, profil, QUELLE, md.lies(QUELLE)).as_string()
    assert _pruefe(tmp_path, ohne).ok


def test_die_fehlende_pruefung_wird_benannt(tmp_path, profil):
    """Eine übersprungene Prüfung, die wie eine bestandene aussieht, ist
    schlimmer als keine."""
    ohne = eml.baue(KOPF, profil, QUELLE, md.lies(QUELLE)).as_string()
    bericht = _pruefe(tmp_path, ohne)
    zeile = [p for p in bericht.pruefungen if p.name == "Vollständigkeit gegen die Quelle"][0]
    assert "nicht prüfbar" in zeile.ist


@pytest.mark.parametrize("zeilenende", ["\n", "\r\n"], ids=["LF", "CRLF"])
def test_beide_zeilenenden_werden_vertragen(tmp_path, roh, zeilenende):
    """RFC 5322 schreibt CRLF vor. Eine Nachricht aus einem fremden Programm
    bringt es mit — der Prüfer darf sie deshalb nicht beanstanden.

    Der erste CI-Lauf war unter Linux und macOS grün und nur unter Windows rot:
    Dort setzt Python beim Schreiben von selbst CRLF ein, und der Vergleich auf
    den Signaturtrenner fand `-- \n` nicht mehr.
    """
    bericht = _pruefe(tmp_path, roh, zeilenende=zeilenende)
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)


# ── Jede Prüfung wird rot ───────────────────────────────────────────────────

SABOTAGEN = [
    ("Keine Message-ID", lambda s: s.replace("Subject:", "Message-ID: <x@y.de>\nSubject:", 1)),
    ("Transfer-Encoding des Textteils",
     lambda s: s.replace("Content-Transfer-Encoding: quoted-printable",
                         "Content-Transfer-Encoding: base64", 1)),
    ("format=flowed", lambda s: s.replace('; format="flowed"', "", 1)),
    ("delsp gesetzt", lambda s: s.replace('; delsp="yes"', "", 1)),
    ("Space-Stuffing", lambda s: s.replace("wie besprochen", "> wie besprochen", 1)),
    ("Signaturtrenner", lambda s: s.replace("--=20\n", "", 1)),
    ("Keine verbotenen Bestandteile",
     lambda s: s.replace("</head>", '<link rel=3D"stylesheet" href=3D"https://x.invalid/a.css">'
                                    "</head>", 1)),
    ("Sprache ausgezeichnet", lambda s: s.replace('<html lang=3D"de">', "<html>", 1)),
    ("Breite begrenzt", lambda s: s.replace("max-width:", "min-width:")),
    ("Kein Zählpixel",
     lambda s: s.replace("</body>", '<img src=3D"cid:x" alt=3D"x" width=3D"1" height=3D"1">'
                                    "</body>", 1)),
    ("Tabellen sind Datentabellen",
     lambda s: s.replace("<th ", "<td ").replace("</th>", "</td>")),
    ("Text und HTML sagen dasselbe", lambda s: s.replace("besprochen", "besprochenXYZ", 1)),
    ("Quellteil ist CommonMark",
     lambda s: s.replace('variant="CommonMark"', 'variant="Markdown"', 1)),
]


@pytest.mark.parametrize("name, sabotiere", SABOTAGEN, ids=[n for n, _ in SABOTAGEN])
def test_jede_pruefung_kann_rot_werden(tmp_path, roh, name, sabotiere):
    kaputt = sabotiere(roh)
    assert kaputt != roh, (
        f"Die Sabotage für „{name}“ hat die Datei nicht verändert — "
        "ein grünes Ergebnis würde hier nichts belegen")
    assert name in _gescheitert(_pruefe(tmp_path, kaputt))


def test_ein_fehlender_betreff_faellt_auf(tmp_path, roh):
    ohne = re.sub(r"^Subject:.*$", "", roh, count=1, flags=re.M)
    assert ohne != roh
    assert "Kopfzeile Subject" in _gescheitert(_pruefe(tmp_path, ohne))


def test_vertauschte_alternativen_fallen_auf(tmp_path, profil):
    """In `multipart/alternative` gilt der LETZTE Teil als der reichste.
    Stünde der Text hinten, zeigte jeder Client den Klartext statt des HTML."""
    nachricht = eml.baue(KOPF, profil, QUELLE, md.lies(QUELLE))
    teile = nachricht.get_payload()
    nachricht.set_payload(list(reversed(teile)))
    bericht = _pruefe(tmp_path, nachricht.as_string())
    assert "Reihenfolge der Alternativen" in _gescheitert(bericht)


# ── Der Prüfer steht für sich ───────────────────────────────────────────────

def test_der_signaturtrenner_ist_hier_eigenstaendig():
    """Ein Prüfer, der die Konstante des Erzeugers importiert, kann nicht rot
    werden, wenn der Erzeuger sie ändert — er bestätigt dann nur, dass beide
    dasselbe meinen. Derselbe Grund, aus dem die vendorte Layoutquelle in
    `regeln/din5008.yaml` nicht als Beleg zählt.
    """
    quelle = (SKILL / "falzmarke" / "pruefung_eml.py").read_text(encoding="utf-8")
    assert "SIGNATUR_TRENNER = " in quelle
    assert "from falzmarke.eml import" not in quelle
    assert "eml.SIGNATUR_TRENNER" not in quelle


@pytest.mark.parametrize("inhalt", ["", "kein Kopf, kein Körper\n", "Guten Tag.\n"])
def test_was_keine_nachricht_ist_bricht_sauber_ab(tmp_path, inhalt):
    """Kein Traceback für eine Datei, die jemand verwechselt hat."""
    pfad = tmp_path / "keine.eml"
    pfad.write_text(inhalt, encoding="utf-8")
    with pytest.raises(pruefung_eml.EmlUnlesbar):
        pruefung_eml.pruefe(pfad)


# ── Der Weg über die Kommandozeile ──────────────────────────────────────────

def test_cli_gibt_die_erwarteten_exit_codes(tmp_path, roh):
    import subprocess
    import sys

    from conftest import REPO

    pfad = tmp_path / "nachricht.eml"
    pfad.write_text(roh, encoding="utf-8")
    befehl = [sys.executable, str(REPO / "skill" / "scripts" / "falzmarke.py"),
              "verify", "--email", str(pfad)]

    lauf = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8")
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert "verify:" in lauf.stdout

    pfad.write_text(roh.replace('; format="flowed"', "", 1), encoding="utf-8")
    kaputt = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8")
    assert kaputt.returncode != 0
    assert "format=flowed" in kaputt.stdout


def test_cli_meldet_eine_fremde_datei_als_eingabefehler(tmp_path):
    import subprocess
    import sys

    from conftest import REPO

    pfad = tmp_path / "fremd.eml"
    pfad.write_text("Das ist ein Einkaufszettel.\n", encoding="utf-8")
    lauf = subprocess.run(
        [sys.executable, str(REPO / "skill" / "scripts" / "falzmarke.py"),
         "verify", "--email", str(pfad)],
        capture_output=True, text=True, encoding="utf-8")
    assert lauf.returncode == 1
    assert "keine E-Mail-Datei" in lauf.stderr


# ── Links in beiden Fassungen (#103, gefunden über das Beispiel aus #107) ────
#
# `examples/email/email-links.md` war der erste Brief mit Links, und er brachte
# die Gleichheitsprüfung sofort auf 21/22. Drei Ursachen lagen übereinander;
# jede für sich sah aus wie die ganze.

def _wortmengen(quelle: str) -> tuple[set[str], set[str]]:
    from falzmarke import pruefung_eml

    return (pruefung_eml._woerter(quelle), pruefung_eml._woerter(quelle))


def test_eine_adresse_in_spitzen_klammern_ist_kein_tag():
    """Im Klartext steht `<https://…>` — für `<[^>]+>` sieht das aus wie Markup.

    Ohne diese Behandlung fiel die Adresse aus dem Vergleich, und zwar auf
    beiden Seiten: Die Prüfung war dort still wirkungslos, statt rot zu werden.
    """
    from falzmarke import pruefung_eml

    woerter = pruefung_eml._woerter("Die Bedingungen: <https://example.de/agb.html> gelten.")
    assert "https://example.de/agb.html" in woerter, woerter


def test_ein_echtes_tag_bleibt_draussen():
    """Gegenprobe. Ohne sie könnte die Ausnahme jedes Markup durchlassen."""
    from falzmarke import pruefung_eml

    woerter = pruefung_eml._woerter("<p class='x'>Text</p>")
    assert woerter == {"text"}, woerter


def test_zeichensetzung_am_wortrand_zaehlt_nicht():
    """`Bedingungen:` im Text und `Bedingungen` im HTML sind dasselbe Wort."""
    from falzmarke import pruefung_eml

    assert pruefung_eml._woerter("Bedingungen: gelten") == \
        pruefung_eml._woerter("<a>Bedingungen</a> gelten")


def test_das_linkziel_im_attribut_zaehlt_mit():
    """Im HTML steht die Adresse nur im `href` — sie ist trotzdem da."""
    from falzmarke import pruefung_eml

    woerter = pruefung_eml._woerter('<a href="https://example.de/agb">Bedingungen</a>')
    assert "https://example.de/agb" in woerter, woerter


def test_aber_nicht_jedes_attribut():
    """Gegenprobe: `style` und `src` sind Markup, kein Wortlaut.

    Zählte die Prüfung sie mit, vergliche sie Stilangaben mit dem Brieftext —
    und ein echter Unterschied ginge in dem Rauschen unter.
    """
    from falzmarke import pruefung_eml

    woerter = pruefung_eml._woerter('<img src="cid:logo" style="height: 40px" alt="x">')
    assert "cid:logo" not in woerter, woerter
    assert "40px" not in woerter, woerter


def test_das_beispiel_mit_links_besteht_vollstaendig(tmp_path):
    """Die Abnahme aus #107: Alle Beispiele laufen mit.

    Und der Grund, warum es dieses Beispiel braucht: Ohne einen Brief mit Links
    lief die Gleichheitsprüfung nie über einen — die drei Fehler oben wären
    ungesehen geblieben.
    """
    from conftest import REPO

    from falzmarke import cli

    quelle = REPO / "examples" / "email" / "email-links.md"
    assert quelle.is_file(), "das Beispiel mit Links fehlt"
    ziel, _ = cli.setze_email(
        quelle, tmp_path / "links",
        profil_verzeichnis=SKILL / "falzmarke" / "typst" / "profiles")
    bericht = pruefung_eml.pruefe(ziel)
    gescheitert = [p.name for p in bericht.pruefungen if not p.bestanden]
    assert not gescheitert, gescheitert
