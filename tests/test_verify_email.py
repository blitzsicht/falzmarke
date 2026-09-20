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
    # Seit #289 ist die Richtung umgekehrt: Der Fließtext darf KEINEN Deckel
    # tragen, weil die 640 px keine Quelle hatten. Sabotiert wird deshalb, was
    # der Emitter nicht mehr setzt — ein `max-width` an einem eigenen Absatz.
    # Der Ausdruck greift in der quoted-printable-Fassung: `class=3D"fm-t"
    # style=3D"margin: 0 0 12px;` steht dort ungebrochen auf einer Zeile, und
    # `0 0 12px` trifft nur Absätze — Listenpunkte haben `0 0 4px`, der Rumpf
    # `0; padding`.
    ("Fließtext ohne Breitendeckel",
     lambda s: s.replace('class=3D"fm-t" style=3D"margin: 0 0 12px;',
                         'class=3D"fm-t" style=3D"max-width: 640px; margin: 0 0 12px;', 1)),
    # Der Befund aus #264, in seiner Gegenrichtung: Ein Deckel am Umschlag
    # quetscht alles darin — bis eine Datentabelle mitten im Wort bricht.
    # Genau diese Zeile stand bis dahin im Emitter und fiel niemandem auf.
    ("Umschlag ohne Breitendeckel",
     lambda s: s.replace('role=3D"presentation" ',
                         'role=3D"presentation" style=3D"max-width: 600px" ', 1)),
    ("Kein Zählpixel",
     lambda s: s.replace("</body>", '<img src=3D"cid:x" alt=3D"x" width=3D"1" height=3D"1">'
                                    "</body>", 1)),
    # Der Name ist seit Issue #104 ein anderer: Eine Tabelle darf jetzt auch
    # Layout sein, wenn sie es sagt. Die Sabotage bleibt dieselbe — aus den
    # Kopfzellen der Datentabelle werden gewöhnliche, und dann ist sie weder
    # das eine noch das andere.
    ("Tabellen sind Daten oder gekennzeichnetes Layout",
     lambda s: s.replace("<th ", "<td ").replace("</th>", "</td>")),
    # Und die Gegenrichtung: Der Umschlag verliert seine Kennzeichnung. Ohne
    # diesen Fall prüfte die Sabotage oben nur die Datentabelle, und der
    # Umschlag — der Grund, warum es die Marke überhaupt gibt — bliebe
    # ungemessen.
    ("Tabellen sind Daten oder gekennzeichnetes Layout",
     lambda s: s.replace('role=3D"presentation" ', "", 1)),
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


def test_ein_fehlendes_date_faellt_auf(tmp_path, roh):
    """Der Befund aus #236: Bis dahin trug die Datei nie ein `Date` — und
    `verify --email` meldete sie trotzdem grün. Die Prüfung konnte an dieser
    Stelle nicht rot werden."""
    ohne = re.sub(r"^Date:.*$", "", roh, count=1, flags=re.M)
    assert ohne != roh, "keine Date-Zeile in der Nachricht — die Sabotage misst nichts"
    assert "Kopfzeile Date" in _gescheitert(_pruefe(tmp_path, ohne))


# ── Die zweite Achse des Breitendeckels: Listen (#289) ──────────────────────

def test_auch_eine_gedeckelte_liste_faellt_auf(tmp_path, profil):
    """Die Sabotage oben trifft einen Absatz — `QUELLE` hat keine Liste.

    Damit wäre die halbe Menge ungemessen: Absätze **und** Listen trugen den
    Deckel, und eine Prüfung, die nur Absätze sieht, lässt ihn an der Liste
    zurückkommen. Deshalb eine eigene Nachricht mit Liste und eine eigene
    Sabotage.
    """
    quelle = "wie besprochen:\n\n- Technik\n- Aufbau\n"
    roh = eml.baue({**KOPF, "betreff": "Probe mit Liste"}, profil,
                   quelle, md.lies(quelle)).as_string()

    anker = '<ul class=3D"fm-t" style=3D"margin: 0 0 12px; padding-left: 22px;'
    assert anker in roh, "der Anker trifft nicht — die Sabotage würde nichts messen"
    kaputt = roh.replace(anker, anker.replace('style=3D"', 'style=3D"max-width: 640px; '), 1)
    assert kaputt != roh

    assert _pruefe(tmp_path, roh).ok, "die Kontrollprobe ist schon rot"
    assert "Fließtext ohne Breitendeckel" in _gescheitert(_pruefe(tmp_path, kaputt))


# ── Blindkopie: die eine Zusage des Feldes (#242) ───────────────────────────

def _mit_bcc(profil, adresse="archiv@example.com", text=None):
    """Eine Nachricht mit Bcc, wahlweise mit verändertem Rumpf."""
    quelle = text if text is not None else QUELLE
    return eml.baue({**KOPF, "bcc": [f"Archiv <{adresse}>"]}, profil,
                    quelle, md.lies(quelle)).as_string()


def test_eine_blindkopie_im_kopf_ist_gruen(tmp_path, profil):
    """Die Kontrollprobe. Ohne sie misst die Sabotage unten nur die Kopie."""
    bericht = _pruefe(tmp_path, _mit_bcc(profil))
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)
    assert "Blindkopie steht nicht im sichtbaren Teil" in {
        p.name for p in bericht.pruefungen}, "die Prüfung lief gar nicht"


def test_eine_verratene_blindkopie_faellt_auf(tmp_path, profil):
    """Steht die Adresse im Text, ist sie keine Blindkopie mehr — und das fiele
    sonst niemandem auf, weil die Mail in jeder anderen Hinsicht stimmt."""
    verraten = _mit_bcc(profil, text=QUELLE + "\nKopie an archiv@example.com.\n")
    assert "Blindkopie steht nicht im sichtbaren Teil" in _gescheitert(
        _pruefe(tmp_path, verraten))


def test_ohne_blindkopie_wird_nichts_geprueft(tmp_path, roh):
    """Was nicht in der Datei steht, wird nicht geprüft — sonst zählte hier
    eine leere Menge gegen eine leere Menge und sähe wie ein Beleg aus."""
    namen = {p.name for p in _pruefe(tmp_path, roh).pruefungen}
    assert "Blindkopie steht nicht im sichtbaren Teil" not in namen
    assert "Blindkopie ist auswertbar" not in namen


def test_eine_unlesbare_blindkopie_faellt_auf(tmp_path, roh):
    """Ein Bcc, aus dem keine Adresse zu lesen ist, kann auch nicht gegen den
    sichtbaren Teil gehalten werden — die Prüfung darüber liefe dann ins Leere
    und wäre still grün."""
    kaputt = re.sub(r"^(To: .*)$", r"\1\nBcc: @@@", roh, count=1, flags=re.M)
    assert kaputt != roh
    assert "Blindkopie ist auswertbar" in _gescheitert(_pruefe(tmp_path, kaputt))


def test_ein_unlesbares_bcc_erzeugt_keine_leere_pass_zeile(tmp_path, roh):
    """Ist keine Adresse zu lesen, hätte die Sichtbarkeitsprüfung eine leere
    Menge gegen den Text zu halten — und wäre zwangsläufig bestanden. Eine
    grüne Zeile, die nichts belegt, ist schlimmer als keine (Review-Nachtrag
    zu v0.9.3; dieselbe Überlegung wie beim ganz fehlenden Bcc)."""
    kaputt = re.sub(r"^(To: .*)$", r"\1\nBcc: @@@", roh, count=1, flags=re.M)
    assert kaputt != roh
    namen = {p.name for p in _pruefe(tmp_path, kaputt).pruefungen}
    assert "Blindkopie ist auswertbar" in namen, "die erste Prüfung muss laufen"
    assert "Blindkopie steht nicht im sichtbaren Teil" not in namen, (
        "die zweite darf bei leerer Adressmenge gar nicht erst antreten")


def test_ein_unlesbares_date_faellt_auf(tmp_path, roh):
    """Getrennt von der Sabotage darüber, weil sie einen anderen Fall trifft:
    Das Feld ist da, nur kann es kein Mailprogramm lesen. Für den Empfänger
    ist das dasselbe „(null), (null)" wie ein fehlendes."""
    kaputt = re.sub(r"^Date:.*$", "Date: neulich", roh, count=1, flags=re.M)
    assert kaputt != roh
    gescheitert = _gescheitert(_pruefe(tmp_path, kaputt))
    assert "Date ist nach RFC 5322 lesbar" in gescheitert


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

    `mit_quelle=True` steht hier seit #213 und ist kein Beiwerk: Ohne das Flag
    trägt die Nachricht keinen `text/markdown`-Teil, `_pruefe_quellteil` meldet
    dann „nicht prüfbar" — und das zählt als bestanden. Genau daran lief der
    Fehler vorbei. Von den drei Achsen Links, Quellteil und `pruefe()` deckten
    die Tests je zwei ab, gekreuzt hat sie keiner:

    * dieser Test hatte Links und `pruefe()`, aber keinen Quellteil,
    * `test_email_beispiele.py::test_der_quellteil_traegt_genau_die_quelle`
      hat Links und Quellteil, ruft aber `pruefe()` nicht auf,
    * die Fixture `roh` hat Quellteil und `pruefe()`, doch `QUELLE` führt
      keinen Link.

    Wer das Flag hier entfernt, macht die Lücke wieder auf.
    """
    from conftest import REPO

    from falzmarke import cli

    quelle = REPO / "examples" / "email" / "email-links.md"
    assert quelle.is_file(), "das Beispiel mit Links fehlt"
    ziel, _ = cli.setze_email(
        quelle, tmp_path / "links",
        profil_verzeichnis=SKILL / "falzmarke" / "typst" / "profiles",
        mit_quelle=True)
    bericht = pruefung_eml.pruefe(ziel)
    gescheitert = [p.name for p in bericht.pruefungen if not p.bestanden]
    assert not gescheitert, gescheitert


# ── Markdown-Links in der Quelle (#213) ─────────────────────────────────────
#
# `--mit-quelle` hängt die rohe Markdown-Quelle an und hält sie gegen die
# gesetzten Fassungen. Die Link-Syntax `[Text](URL)` überlebt diesen Vergleich
# nicht: In Text und HTML ist der Link aufgelöst, in der Quelle steht er in
# Klammern. Gemessen am 01.09.2026 fiel dadurch jede Mail mit Link auf 24/26,
# gemeldet mit Token wie `blitzsicht](https://…` — reinen Syntaxresten.
#
# Das Gewicht liegt in der Folge, nicht im Fehlalarm: Regel 0 verlangt ein
# grünes `verify --email` vor dem Versand. War das für jede Mail mit Link
# unerreichbar, erzieht die Regel dazu, ein rotes verify zu übergehen.


@pytest.mark.parametrize("ziel", [
    "https://example.de/agb",
    "mailto:info@example.de",
    "tel:+4994162098000",
], ids=["https", "mailto", "tel"])
def test_ein_link_in_der_quelle_gilt_als_vollstaendig(tmp_path, profil, ziel):
    """Alle drei Schemata der Positivliste, an der echten Nachricht gemessen.

    Nicht auf der Ebene der Wortmengen, sondern über `pruefe()`: Der Fehler
    entstand im Zusammenspiel von Quellteil und gesetzter Fassung, und genau
    das baut `eml.baue(..., mit_quelle=True)` hier auf.
    """
    quelle = f"wie besprochen gelten die [Bedingungen des Hauses]({ziel}) seit August.\n"
    nachricht = eml.baue(KOPF, profil, quelle,
                         md.lies(quelle, ziel="email"), mit_quelle=True)
    bericht = _pruefe(tmp_path, nachricht.as_string())
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)


def test_ein_link_mit_titel_zaehlt_auch():
    """CommonMark erlaubt `[Text](URL "Titel")`. Der Titel ist Beiwerk, Text
    und Ziel sind Wortlaut — beide stehen in den gesetzten Fassungen."""
    woerter = pruefung_eml._woerter('Die [Bedingungen](https://example.de/agb "AGB") gelten.')
    assert "bedingungen" in woerter, woerter
    assert "https://example.de/agb" in woerter, woerter


def test_ein_fehlendes_wort_im_linktext_faellt_weiter_auf():
    """Die wichtigere Hälfte der Prüfung: Der Fix darf nicht blind machen.

    Ohne diese Gegenprobe belegten die Tests oben nur, dass etwas grün ist —
    eine Normalisierung, die den ganzen Link samt Linktext verschluckt, wäre
    ebenso grün und hätte die Prüfung an dieser Stelle still abgeschaltet.
    Hier fehlt `Entwicklung` in der gesetzten Fassung wirklich.
    """
    quelle = "siehe [Forschung und Entwicklung](https://example.de/f) hier"
    gesetzt = "siehe Forschung: <https://example.de/f> hier"
    fehlend = ({w for w in pruefung_eml._woerter(quelle) if len(w) > 3}
               - pruefung_eml._woerter(gesetzt))
    assert fehlend == {"entwicklung"}, fehlend


def test_ist_der_linktext_die_adresse_zaehlt_das_schema_nicht():
    """`[erika@example.de](mailto:erika@example.de)` — das Ziel wiederholt nur
    den Linktext.

    Der Setzer lässt die Wiederholung im Klartext weg; gemessen an
    `email-links.md` steht dort `erika.muster@example.de.` und kein zweites
    `<mailto:…>`. Verlangte die Prüfung das Schema trotzdem, wäre das derselbe
    Fehlalarm aus #213 eine Ebene tiefer — und der Grund, warum der erste
    Anlauf dieses Fixes das Beispiel noch nicht bestand.
    """
    quelle = "schreiben Sie an [erika@example.de](mailto:erika@example.de)."
    gesetzt = "schreiben Sie an erika@example.de."
    fehlend = ({w for w in pruefung_eml._woerter(quelle) if len(w) > 3}
               - pruefung_eml._woerter(gesetzt))
    assert not fehlend, fehlend


def test_ein_abweichendes_linkziel_faellt_sehr_wohl_auf():
    """Die Gegenprobe zur Ausnahme darüber — ohne sie wäre jedes Ziel egal.

    Zeigt der Link woandershin, als sein Text behauptet, ist das kein
    Schema-Präfix mehr, sondern ein Unterschied im Wortlaut. Genau der Fall,
    den ein Empfänger nicht sieht und die Prüfung sehen muss.
    """
    quelle = "schreiben Sie an [erika@example.de](mailto:fremd@example.com)."
    gesetzt = "schreiben Sie an erika@example.de."
    fehlend = ({w for w in pruefung_eml._woerter(quelle) if len(w) > 3}
               - pruefung_eml._woerter(gesetzt))
    assert fehlend == {"mailto:fremd@example.com"}, fehlend


def test_klammern_ohne_link_verschlucken_nichts():
    """Gegenprobe gegen Übergriff.

    `[1] steht unten (siehe Anhang)` ist keine Link-Syntax — dazwischen steht
    Text. Griffe die Normalisierung trotzdem zu, verschwände er aus dem
    Vergleich, und die Prüfung wäre dort still wirkungslos statt rot. Dasselbe
    über einen Zeilenumbruch hinweg: eine offene `[` darf nicht bis zur
    nächsten Klammer irgendwo weiter unten fressen.
    """
    einzeilig = pruefung_eml._woerter("Anmerkung [1] steht unten (siehe Anhang) danach.")
    for wort in ("anmerkung", "steht", "unten", "siehe", "anhang", "danach"):
        assert wort in einzeilig, (wort, einzeilig)

    mehrzeilig = pruefung_eml._woerter("Anfang [nicht geschlossen\nzweite Zeile (klammer) Ende")
    for wort in ("anfang", "nicht", "geschlossen", "zweite", "zeile", "klammer", "ende"):
        assert wort in mehrzeilig, (wort, mehrzeilig)


# ── Nummerierte Listen (#216) ───────────────────────────────────────────────
#
# Die Ziffern einer nummerierten Liste stehen nur im Klartext. Im HTML setzt
# der Browser sie über den CSS-Counter von `<ol>`; im Textstrom kommen sie dort
# nicht vor. Die Gleichheitsprüfung meldete deshalb genau ein fehlendes "Wort"
# je Listenpunkt — gemessen am 01.09.2026: 21/22 bei zwei Punkten, 20/22 bei
# drei.
#
# Weil `email` die Prüfung selbst aufruft und bei Fehlschlag mit Code 2 endet,
# war damit JEDE Nachricht mit nummerierter Liste blockiert. Die Listenform ist
# in `references/markdown.md` ausdrücklich zugelassen; der Umweg über "Frage 1 —"
# als Absatz kostet die Bedeutung, die eine Nummerierung trägt.


def test_eine_nummerierte_liste_besteht_die_pruefung(tmp_path, profil):
    """Der gemeldete Fall, an der echten Nachricht gemessen."""
    quelle = ("hier eine nummerierte Liste:\n\n"
              "1. erste Frage\n2. zweite Frage\n3. dritte Frage\n")
    nachricht = eml.baue(KOPF, profil, quelle, md.lies(quelle, ziel="email"), mit_quelle=True)
    bericht = _pruefe(tmp_path, nachricht.as_string())
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)


def test_eine_bindestrich_liste_bleibt_gruen(tmp_path, profil):
    """Kontrollprobe aus dem Issue: Die Aufzählung war nie das Problem.

    Ohne sie belegte der Test darüber nur, dass Listen irgendwie durchgehen —
    nicht, dass die Behandlung der Ziffern die Ursache war.
    """
    quelle = "hier eine Aufzählung:\n\n- erster Punkt\n- zweiter Punkt\n"
    nachricht = eml.baue(KOPF, profil, quelle, md.lies(quelle, ziel="email"), mit_quelle=True)
    assert _pruefe(tmp_path, nachricht.as_string()).ok


def test_ein_fehlender_listenpunkt_faellt_weiter_auf():
    """Die wichtigere Hälfte: Der Fix darf nicht blind machen.

    Weggeschnitten wird die Nummerierung, nicht der Punkt. Fehlt eine ganze
    Zeile in einer der beiden Fassungen, muss das weiterhin rot werden —
    sonst hätte die Prüfung an dieser Stelle nur aufgehört zu messen.
    """
    text = "1. erste Frage\n2. zweite Frage\n3. dritte Frage"
    html = "<ol><li>erste Frage</li><li>dritte Frage</li></ol>"
    fehlend = pruefung_eml._woerter(text) - pruefung_eml._woerter(html)
    assert fehlend == {"zweite"}, fehlend


def test_eine_zahl_im_fliesstext_bleibt_erhalten():
    """Gegenprobe gegen Übergriff: Nur die Nummerierung am Zeilenanfang faellt
    weg. Eine Zahl mitten im Satz ist Wortlaut und wird weiter verglichen —
    ginge sie verloren, fiele ein falscher Betrag nicht mehr auf."""
    woerter = pruefung_eml._woerter("wir liefern 3 Stück zu 12,50 Euro")
    assert "3" in woerter and "12,50" in woerter, woerter

    # Und der schärfere Fall: eine Ziffer MIT Punkt, aber mitten in der Zeile.
    # Ohne den Zeilenanker verschwände hier die 5 — auf beiden Seiten, also
    # ohne dass die Prüfung rot würde. Genau die stille Wirkungslosigkeit, vor
    # der `RANDZEICHEN` und die Link-Behandlung ihre Kommentare tragen.
    mitten = pruefung_eml._woerter("das steht in Abschnitt 5. Dort auch die Frist")
    assert "5" in mitten, mitten


def test_eine_jahreszahl_am_zeilenanfang_bleibt_erhalten():
    """Die Grenze ist bei drei Ziffern gezogen.

    `2026. Ein gutes Jahr.` sieht wie ein Listenpunkt aus, ist aber keiner —
    Listen laufen nicht bis in die Tausender. Ohne die Grenze verschwaende die
    Jahreszahl aus dem Vergleich, und zwar unbemerkt: Sie faellt auf BEIDEN
    Seiten weg, die Pruefung bliebe gruen und waere dort still wirkungslos.
    """
    assert "2026" in pruefung_eml._woerter("2026. Ein gutes Jahr."), \
        pruefung_eml._woerter("2026. Ein gutes Jahr.")


def test_auch_die_klammerform_zaehlt_als_nummerierung():
    """`1)` ist dieselbe Liste mit anderem Zeichen."""
    assert pruefung_eml._woerter("1) erster\n2) zweiter") == {"erster", "zweiter"}


# ── Der Umschlag und das Logo (#104) ────────────────────────────────────────

def test_eine_mail_mit_logo_besteht_die_pruefung(tmp_path, profil):
    """Der Befund, mit dem #104 messbar wurde.

    Gemessen am 29.08.2026: Jede Nachricht mit `email.logo` im Profil fiel
    durch `verify --email` — „Tabellen sind Datentabellen: 1 ohne <th>". Der
    Signaturblock legt das Logo in eine Tabelle, und die trug weder Kopfzellen
    noch eine Kennzeichnung als Layout.

    Aufgefallen war es niemandem: Das Beispielprofil hat kein Logo, also
    erzeugte kein einziger Test diese Tabelle. Ein Fehler, den kein Testfall
    auslösen kann, ist von einem behobenen nicht zu unterscheiden.
    """
    from PIL import Image

    logo = tmp_path / "logo.png"
    Image.new("RGBA", (120, 40), (0x12, 0x4E, 0x8F, 255)).save(logo)
    mit_logo = dict(profil)
    mit_logo["email"] = dict(profil.get("email") or {}, logo="logo.png")

    nachricht = eml.baue(KOPF, mit_logo, QUELLE, md.lies(QUELLE),
                         mit_quelle=True, profil_pfad=tmp_path / "example.yaml")
    bericht = _pruefe(tmp_path, nachricht.as_string())
    assert bericht.ok, bericht.als_text(ausfuehrlich=True)


def test_das_logo_traegt_beide_masse(tmp_path, profil):
    """Breite UND Höhe als Attribut, die Breite aus dem Seitenverhältnis
    gerechnet. Ohne Maße reserviert kein Client Platz, und wo Bilder blockiert
    sind — der Normalfall in Outlook — steht der Alternativtext in einem
    Kasten von null Pixeln."""
    from PIL import Image

    logo = tmp_path / "logo.png"
    Image.new("RGBA", (120, 40), (0x12, 0x4E, 0x8F, 255)).save(logo)
    html = eml.htmlteil(KOPF, profil, md.lies(QUELLE),
                        logo=eml.Logo("datei", f"cid:{eml.LOGO_CID}", logo))
    assert 'width="120" height="40"' in html, html[html.find("<img"):][:200]


def test_ein_schmaleres_logo_bekommt_eine_andere_breite(tmp_path, profil):
    """Sonst wäre die Breite eine feste Zahl und jedes andere Logo verzerrt."""
    from PIL import Image

    logo = tmp_path / "logo.png"
    Image.new("RGBA", (40, 40), (0x12, 0x4E, 0x8F, 255)).save(logo)
    html = eml.htmlteil(KOPF, profil, md.lies(QUELLE),
                        logo=eml.Logo("datei", f"cid:{eml.LOGO_CID}", logo))
    assert 'width="40" height="40"' in html


# ── Der Knopf als Anker in einer mitgebrachten Signatur (#322) ──────────────
#
# Am 14.09.2026 meldete `verify --email` 27/27 und 29/29, und in Outlook für Mac
# zerfiel der Termin-Knopf der Signatur in zwei Kästen und überlappte die Zeile
# davor. Outlook ignoriert `display:inline-block`, `margin` und `padding` auf
# einem `<a>`. Eine mitgebrachte Signatur (#275) wurde eingebettet, ohne dass die
# Prüfung sie ansah.
#
# Gemessen wird an der fertigen Datei und ohne Namen: Welche Prüfung anschlägt,
# steht im Bericht, nicht in diesem Test. Was hier festgehalten wird, ist die
# Wirkung — ein Anker als Kasten wird beanstandet, derselbe Knopf im
# Tabellengerüst nicht, und die Meldung sagt, wo und was stattdessen.

from signatur_knopf import (                                           # noqa: E402
    ANKERKNOPF_TERMIN, TABELLENKNOPF_TERMIN, eml_mit_signatur, html_der_eml, signatur)

#: Die Zahl der Prüfungen der Nachricht aus `signatur_knopf.eml_mit_signatur`
#: vor #322 — am 20.09.2026 gemessen: 25. Die Mails vom 14.09. trugen mehr
#: Prüfungen (Quellteil, Anhänge: 27 und 29), die Rechnung ist dieselbe: Aus
#: 27/27 wird 28/28 (AC 3), hier aus 25/25 also 26/26 — eine mehr, nicht keine
#: und nicht zwei.
PRUEFUNGEN_VOR_322 = 25


def _rot(bericht) -> list:
    """Alle Prüfungen, die nicht bestanden haben — Fehler und Warnungen.

    „Rot" heißt hier `not bestanden` und nicht `not bericht.ok`. Ob die Prüfung
    ein Fehler oder nur eine Warnung ist, entscheidet der Regelkatalog (ADR 0035:
    Verhalten eines Mailprogramms ist Praxis, und Praxis ist nie ein Fehler).
    Diese Tests legen die Stufe nicht fest — sie verlangen nur, dass der Befund
    im Bericht steht und nicht still bleibt.
    """
    return [p for p in bericht.pruefungen if not p.bestanden]


def test_die_neue_pruefung_steht_in_der_zaehlung(tmp_path):
    """AC 3: aus 27/27 wird 28/28 — eine Prüfung mehr, nicht keine und nicht zwei.

    Gezählt wird an der grünen Nachricht: Eine Prüfung, die nur im Fehlerfall
    einen Eintrag schriebe, sähe im grünen Lauf aus wie keine (wie beim
    Quellteil: „nicht prüfbar" steht dort ausdrücklich da).

    Dieselbe Nachricht ist die Kontrollprobe für alles Folgende: Sie trägt den
    Knopf im Tabellengerüst und muss ganz grün sein — sonst sähe „die Prüfung
    schlägt an" weiter unten nach einem Beleg aus, ohne einer zu sein.
    """
    pfad = eml_mit_signatur(tmp_path, signatur(TABELLENKNOPF_TERMIN))
    assert "inline-block" not in html_der_eml(pfad)
    bericht = pruefung_eml.pruefe(pfad)
    soll = PRUEFUNGEN_VOR_322 + 1
    assert len(bericht.pruefungen) == soll, (
        f"{len(bericht.pruefungen)} Prüfungen statt {soll}")
    assert f"{soll}/{soll}" in bericht.als_text(), bericht.als_text()
    assert bericht.ok and not bericht.warnungen and not _rot(bericht), \
        bericht.als_text(ausfuehrlich=True)


def test_der_anker_als_knopf_faellt_auf(tmp_path):
    """AC 1, in der Form vom 14.09.2026 — zeichengenau der Termin-Knopf aus
    `blitzsicht.html`. Genau eine Prüfung schlägt an, und die Zahl bleibt gleich:
    Dass sie im Fehlerfall dazukommt und im grünen fehlt, wäre ein anderer Fehler.
    """
    pfad = eml_mit_signatur(tmp_path, signatur(ANKERKNOPF_TERMIN))
    assert "display:inline-block" in html_der_eml(pfad), (
        "die Sabotage steht nicht in der Datei — der Test würde nichts messen")
    bericht = pruefung_eml.pruefe(pfad)
    rot = _rot(bericht)
    assert len(rot) == 1, bericht.als_text(ausfuehrlich=True)
    assert len(bericht.pruefungen) == PRUEFUNGEN_VOR_322 + 1


#: (Bezeichnung, der ganze Anker). Vollständige Tags statt eines Stil-Schnipsels:
#: Die Prüfung muss den Anker finden, wie auch immer er geschrieben ist —
#: Attributreihenfolge, Zeilenumbruch und Anführungszeichen sind in fremdem HTML
#: nicht zu erwarten, sondern zu ertragen.
ANKER_MIT_KASTEN = [
    ("inline-block und padding",
     '<a href="https://example.de/termin" '
     'style="display:inline-block;padding:6px 12px;">Termin vereinbaren</a>'),
    ("inline-block und margin",
     '<a href="https://example.de/termin" '
     'style="display:inline-block;margin-top:10px;">Termin vereinbaren</a>'),
    ("beides, mit Leerzeichen",
     '<a href="https://example.de/termin" '
     'style="display: inline-block; margin-top: 10px; padding: 6px 12px;">Termin vereinbaren</a>'),
    ("nur eine Seite gepolstert",
     '<a href="https://example.de/termin" '
     'style="display:inline-block;padding-left:12px;">Termin vereinbaren</a>'),
    ("Stil vor dem Ziel",
     '<a style="display:inline-block;padding:6px 12px;" '
     'href="https://example.de/termin">Termin vereinbaren</a>'),
    ("einfache Anführungszeichen",
     "<a href='https://example.de/termin' "
     "style='display:inline-block;padding:6px 12px;'>Termin vereinbaren</a>"),
    ("Tag über mehrere Zeilen",
     '<a href="https://example.de/termin"\n'
     '   style="font-size: 13px;\n'
     '          display: inline-block;\n'
     '          padding: 6px 12px;">Termin vereinbaren</a>'),
    ("Großbuchstaben",
     '<a href="https://example.de/termin" '
     'style="DISPLAY:INLINE-BLOCK;PADDING:6px;">Termin vereinbaren</a>'),
]


@pytest.mark.parametrize("anker", [a for _, a in ANKER_MIT_KASTEN],
                         ids=[n for n, _ in ANKER_MIT_KASTEN])
def test_jede_schreibweise_des_ankers_als_kasten_faellt_auf(tmp_path, anker):
    pfad = eml_mit_signatur(tmp_path, signatur(anker))
    assert "inline-block" in html_der_eml(pfad).lower(), (
        "die Sabotage steht nicht in der Datei — der Test würde nichts messen")
    bericht = pruefung_eml.pruefe(pfad)
    assert len(_rot(bericht)) == 1, bericht.als_text(ausfuehrlich=True)


#: Die Gegenprobe der Gegenprobe. Jeder dieser Fälle hat ein Merkmal des
#: schlechten Knopfes — aber nicht die Kombination auf einem Anker. Eine Prüfung,
#: die nur „irgendwo inline-block" oder „irgendwo padding" sucht, schlüge hier an
#: und wäre für jede Signatur mit Tabellenknopf ein Fehlalarm.
ANKER_OHNE_KASTEN = [
    ("inline-block allein",
     '<a href="https://example.de/termin" '
     'style="display:inline-block;color:#1a3a5c;">Termin vereinbaren</a>'),
    ("Kasten am Span, Anker ohne",
     '<span style="display:inline-block;padding:6px 12px;">'
     '<a href="https://example.de/termin" '
     'style="color:#1a3a5c;text-decoration:none;">Termin vereinbaren</a></span>'),
]


@pytest.mark.parametrize("anker", [a for _, a in ANKER_OHNE_KASTEN],
                         ids=[n for n, _ in ANKER_OHNE_KASTEN])
def test_ohne_die_kombination_auf_dem_anker_bleibt_es_gruen(tmp_path, anker):
    """AC 1 nennt die Kombination: `display:inline-block` **zusammen mit**
    `padding` oder `margin` **auf einem `<a>`**.

    Jeder Fall trägt beide Hälften: erst die Vorbedingung, dass dieselbe
    Prüfung den falschen Knopf findet, dann, dass sie den Nachbau mit nur einem
    der Merkmale durchlässt. Ohne die erste Hälfte wäre das Grün der zweiten
    auch das einer Prüfung, die es gar nicht gibt.
    """
    (tmp_path / "schlecht").mkdir()
    schlecht = pruefung_eml.pruefe(
        eml_mit_signatur(tmp_path / "schlecht", signatur(ANKERKNOPF_TERMIN)))
    assert len(_rot(schlecht)) == 1, "die Vorbedingung fehlt: der falsche Knopf wird nicht gefunden"

    bericht = pruefung_eml.pruefe(eml_mit_signatur(tmp_path, signatur(anker)))
    assert not _rot(bericht), bericht.als_text(ausfuehrlich=True)


def test_die_meldung_nennt_die_stelle_und_den_ersatz(tmp_path):
    """AC 2: Ein bloßes „unzulässig" hilft niemandem, der die Signatur nicht
    geschrieben hat.

    Die Signatur trägt zwei Knöpfe, und nur einer ist falsch. Die Meldung muss
    auf **diesen** zeigen — an Linktext oder Ziel erkennbar — und darf nicht
    den guten mitnennen; sonst sagte sie nur „irgendwo in der Signatur".
    Gelesen wird, was der Mensch sieht: der knappe Bericht.
    """
    pfad = eml_mit_signatur(tmp_path, signatur(ANKERKNOPF_TERMIN))
    text = pruefung_eml.pruefe(pfad).als_text()
    kleingeschrieben = text.lower()

    assert "inline-block" in kleingeschrieben, f"nennt nicht, was falsch ist:\n{text}"
    assert "<table" in kleingeschrieben and "<td" in kleingeschrieben, (
        f"nennt nicht, was an die Stelle gehört:\n{text}")
    assert "Termin vereinbaren" in text or "example.de/termin" in text, (
        f"nennt die Stelle nicht:\n{text}")
    assert "Bewertung abgeben" not in text and "example.de/bewerten" not in text, (
        f"zeigt auch auf den richtig gebauten Knopf:\n{text}")

    # Die Rückseite: Ohne den falschen Knopf gibt es keine Meldung. Sonst wäre
    # die Stelle, die sie nennt, nicht die, an der der Befund liegt, sondern die,
    # die sie zuerst findet.
    (tmp_path / "gut").mkdir()
    gut = pruefung_eml.pruefe(
        eml_mit_signatur(tmp_path / "gut", signatur(TABELLENKNOPF_TERMIN))).als_text()
    assert "inline-block" not in gut.lower(), gut
    assert "Termin vereinbaren" not in gut and "Bewertung abgeben" not in gut, gut


def test_cli_meldet_den_anker_als_knopf(tmp_path):
    """AC 1 heißt „`verify --email` meldet". Bis hierher lief alles über
    `pruefe()`; den Weg, den der Mensch nimmt, geht dieser Test."""
    import subprocess
    import sys

    from conftest import REPO

    pfad = eml_mit_signatur(tmp_path, signatur(ANKERKNOPF_TERMIN))
    lauf = subprocess.run(
        [sys.executable, str(REPO / "skill" / "scripts" / "falzmarke.py"),
         "verify", "--email", str(pfad)],
        capture_output=True, text=True, encoding="utf-8")
    assert "inline-block" in lauf.stdout, lauf.stdout + lauf.stderr
    assert "<table" in lauf.stdout.lower(), lauf.stdout

    (tmp_path / "gut").mkdir()
    gut = subprocess.run(
        [sys.executable, str(REPO / "skill" / "scripts" / "falzmarke.py"),
         "verify", "--email",
         str(eml_mit_signatur(tmp_path / "gut", signatur(TABELLENKNOPF_TERMIN)))],
        capture_output=True, text=True, encoding="utf-8")
    assert gut.returncode == 0, gut.stdout + gut.stderr
    assert "inline-block" not in gut.stdout
