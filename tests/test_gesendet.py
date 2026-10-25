"""Keine Mail doppelt: die Gesendet-Sperre (ADR 0051).

ANLASS (21.10.2026): Eine Antwort ging zweimal an denselben Empfänger. Die
erste aus dem falzmarke-Entwurf, die zweite kurz danach aus einem
Antwortfenster — mit **anderem Betreff** (`Re: <alter Betreff>`), aber
demselben Text. Eine Sperre, die nur den Betreff vergleicht,
hätte die zweite nicht erkannt. Deshalb steht der Fall hier wörtlich nach:
anderer Betreff, gleicher Text, Zitat darunter → gesperrt.

Kein Test öffnet eine Verbindung. Der Proxy ist die Attrappe aus
`imap_attrappe.py`; die Mails darin sind so gebaut, wie Thunderbird sie
verschickt: Textteil aus dem HTML erzeugt, `*fett*`, `  * ` als
Aufzählungszeichen, neu umbrochen, Signatur ohne `-- `.
"""

from __future__ import annotations


from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import PROFILE
from falzmarke import cli as falzmarke
from falzmarke import gesendet, postfach
from imap_attrappe import ImapAttrappe, nachricht

JETZT = datetime(2026, 10, 21, 18, 40, tzinfo=timezone.utc)
EMPFAENGER = "paula@example.org"

MAIL = """---
typ: email
profil: example
an: Paula Beispiel <paula@example.org>
betreff: "AW: Sommerfest – Programm und was noch fehlt"
anrede: Hallo Paula,
gruss: Viele Grüße
---
danke für die Unterlagen zum Sommerfest und die Gästeliste. Die Planung für den Nachmittag übernehme ich gern.

**Programm:** Für den Nachmittag schlage ich einen **Beginn um 15:00&nbsp;Uhr** vor, Ende gegen Abend. Darin enthalten:

- für jede Station die Angabe, wer sie betreut und was dort gebraucht wird
- was der Verein dafür bereitstellen muss (Tische, Zelte)

**Was mir noch fehlt:**

1. **Der Lageplan**, so wie er an die Helfer ging.
2. **Fehlende Stationen:** Im Plan stehen Stationen, die nicht in der Liste sind.
"""

#: So kam derselbe Text als Thunderbird-Mail im Gesendet-Ordner an.
THUNDERBIRD_TEXT = """Hallo Paula,

danke für die Unterlagen zum Sommerfest und die Gästeliste. Die Planung
für den Nachmittag übernehme ich gern.

*Programm:* Für den Nachmittag schlage ich einen *Beginn um
15:00 Uhr* vor, Ende gegen Abend. Darin enthalten:

  * für jede Station die Angabe, wer sie betreut und was dort
    gebraucht wird
  * was der Verein dafür bereitstellen muss (Tische, Zelte)

*Was mir noch fehlt:*

 1. *Der Lageplan*, so wie er an die Helfer ging.
 2. *Fehlende Stationen:* Im Plan stehen Stationen, die nicht in der
    Liste sind.

Viele Grüße


Erika Muster

Geschäftsführerin

E-Mail: muster@example.de <mailto:muster@example.de>
"""

ZITAT = """
Am 20.10.2026 um 09:12 schrieb Paula Beispiel:
> Hallo Erika,
>
> anbei die Gästeliste.
"""

ANDERER_TEXT = """Hallo Paula,

kurze Frage zum Termin am Montag: Passt dir 10 Uhr? Sonst geht auch
der Nachmittag.

Viele Grüße
Erika
"""


@pytest.fixture(autouse=True)
def _kein_echtes_programm(monkeypatch):
    """Kein Test hier startet etwas — weder die Datei noch einen Entwurf."""
    from falzmarke import oeffnen

    def _nein(*_a, **_k):
        raise AssertionError("ein Test wollte wirklich ein Programm starten")

    monkeypatch.setattr(oeffnen, "_fuehre_aus", _nein)
    monkeypatch.setattr(oeffnen, "_lauf", _nein)


@pytest.fixture
def eigene(tmp_path) -> Path:
    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")
    eml_pfad, _ = falzmarke.setze_email(quelle, tmp_path / "antwort", profil_verzeichnis=PROFILE)
    return eml_pfad


def _server(monkeypatch, *gesendete, sonder=None) -> ImapAttrappe:
    attrappe = ImapAttrappe({"Gesendete Elemente": [(roh, zeit) for roh, zeit in gesendete]},
                            sonder=sonder)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    return attrappe


def _gesendet(*, vor=timedelta(minutes=7), betreff="AW: Sommerfest – Programm und was noch fehlt",
              text=THUNDERBIRD_TEXT, an=f"Paula Beispiel <{EMPFAENGER}>", kopf=None):
    zeit = JETZT - vor
    return nachricht(an=an, betreff=betreff, text=text, datum=zeit, von="muster@example.de",
                     kopf=kopf), zeit


def _pruefe(eml_pfad, **k) -> gesendet.Befund:
    return gesendet.pruefe_datei(eml_pfad, umgebung={}, jetzt=JETZT, **k)


# ── Die Normalisierung ──────────────────────────────────────────────────────

@pytest.mark.parametrize("a, b", [
    ("AW: Sommerfest – Programm", "Sommerfest - Programm"),
    ("Re: AW: Sommerfest – Programm", "sommerfest programm"),
    ("WG: Fwd: Angebot", "Angebot"),
    ("Re[2]: Angebot", "Angebot"),
])
def test_betreff_ohne_vorsilben_und_zeichen(a, b):
    assert gesendet.betreff_kern(a) == gesendet.betreff_kern(b)


def test_gegenprobe_ein_anderer_betreff_bleibt_anders():
    assert gesendet.betreff_kern("AW: Programm") != gesendet.betreff_kern("AW: Termin")


def test_der_text_bis_zur_grussformel(eigene):
    import email
    from email import policy

    eigen = gesendet.merkmale(email.message_from_bytes(eigene.read_bytes(), policy=policy.default))
    fremd = gesendet.merkmale(email.message_from_bytes(_gesendet()[0], policy=policy.default))
    assert eigen.kern == fremd.kern
    assert len(eigen.kern) > 200, "die Normalisierung hat fast alles weggeworfen"
    assert "vielegrüße" not in eigen.kern and "viele" not in eigen.kern[-20:]
    assert "geschäftsführerin" not in eigen.kern


def test_ein_zitat_darunter_aendert_den_kern_nicht():
    import email
    from email import policy

    ohne = gesendet.merkmale(email.message_from_bytes(_gesendet()[0], policy=policy.default))
    mit = gesendet.merkmale(email.message_from_bytes(
        _gesendet(text=THUNDERBIRD_TEXT + ZITAT)[0], policy=policy.default))
    assert ohne.kern == mit.kern


def test_nur_html_ergibt_denselben_kern():
    import email
    from email import policy

    html = ("<p>Hallo Paula,</p><p>danke f&uuml;r deine Antwort.</p>"
            "<ul><li>erstens</li><li>zweitens</li></ul><p>Viele Grüße</p><p>Erika</p>")
    text = "Hallo Paula,\n\ndanke für deine Antwort.\n\n  * erstens\n  * zweitens\n\nViele Grüße\nErika\n"
    nur_html = gesendet.merkmale(email.message_from_bytes(
        nachricht(text=None, html=html), policy=policy.default))
    nur_text = gesendet.merkmale(email.message_from_bytes(
        nachricht(text=text), policy=policy.default))
    assert nur_html.kern == nur_text.kern and nur_html.kern


# ── Die Sperre ──────────────────────────────────────────────────────────────

def test_gleicher_betreff_gleicher_text_ist_schon_gesendet(eigene, monkeypatch):
    server = _server(monkeypatch, _gesendet())
    befund = _pruefe(eigene)
    assert befund.zustand == "gesendet", befund
    assert befund.sperrt
    assert befund.an == EMPFAENGER
    assert befund.datum == JETZT - timedelta(minutes=7)
    assert server.befehle("EXAMINE") and not server.befehle("APPEND")


def test_der_vorfall_anderer_betreff_gleicher_text_ist_gesperrt(eigene, monkeypatch):
    """Der Fall vom 21.10.2026: `Re: <alter Betreff>`, gleicher Text, Zitat darunter."""
    _server(monkeypatch, _gesendet(betreff="Re: Sommerfest - Planung und was wir brauchen",
                                   text=THUNDERBIRD_TEXT + ZITAT,
                                   kopf={"In-Reply-To": "<vorher@example.org>"}))
    befund = _pruefe(eigene)
    assert befund.zustand == "gesendet", befund
    assert befund.sperrt


def test_gleicher_betreff_anderer_text_ist_eine_geaenderte_fassung(eigene, monkeypatch):
    _server(monkeypatch, _gesendet(text=ANDERER_TEXT))
    befund = _pruefe(eigene)
    assert befund.zustand == "geaendert", befund
    assert befund.sperrt


def test_gleicher_empfaenger_anderer_text_und_betreff_ist_frei(eigene, monkeypatch):
    _server(monkeypatch, _gesendet(betreff="Termin Montag", text=ANDERER_TEXT))
    befund = _pruefe(eigene)
    assert befund.zustand == "frei", befund
    assert not befund.sperrt
    assert befund.angesehen == 1


def test_anderer_empfaenger_gleicher_text_ist_frei(eigene, monkeypatch):
    _server(monkeypatch, _gesendet(an="jemand@example.com"))
    assert _pruefe(eigene).zustand == "frei"


def test_aelter_als_24_stunden_ist_frei(eigene, monkeypatch):
    _server(monkeypatch, _gesendet(vor=timedelta(hours=25)))
    assert _pruefe(eigene).zustand == "frei"


def test_das_fenster_laesst_sich_weiten(eigene, monkeypatch):
    _server(monkeypatch, _gesendet(vor=timedelta(hours=25)))
    befund = gesendet.pruefe_datei(eigene, umgebung={"FALZMARKE_GESENDET_STUNDEN": "72"},
                                   jetzt=JETZT)
    assert befund.zustand == "gesendet", befund


def test_gleiche_fassung_reicht_auch_bei_verschobenem_text(eigene, monkeypatch):
    """Die Kopfzeile ist die dritte Spur — falls ein Programm den Text stärker umbaut."""
    import email
    from email import policy

    fassung = email.message_from_bytes(eigene.read_bytes(),
                                       policy=policy.default)["X-Falzmarke-Fassung"]
    assert fassung
    _server(monkeypatch, _gesendet(betreff="Ganz anders", text=ANDERER_TEXT,
                                   kopf={"X-Falzmarke-Fassung": str(fassung)}))
    assert _pruefe(eigene).zustand == "gesendet"


def test_ohne_proxy_nicht_geprueft_mit_grund(eigene, monkeypatch):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    befund = _pruefe(eigene)
    assert befund.zustand == "nicht_geprueft"
    assert not befund.sperrt
    assert "127.0.0.1:1993" in befund.grund


def test_abgeschaltet_wird_nicht_verbunden(eigene, monkeypatch):
    server = _server(monkeypatch, _gesendet())
    befund = gesendet.pruefe_datei(eigene, umgebung={"FALZMARKE_GESENDET": "nie"}, jetzt=JETZT)
    assert befund.zustand == "aus" and "FALZMARKE_GESENDET=nie" in befund.grund
    assert server.verbindungen == []


def test_der_gesendet_ordner_kommt_aus_list(eigene, monkeypatch):
    """Kein Thunderbird-Profil (conftest): dann das Kennzeichen `\\Sent`."""
    server = ImapAttrappe({"Sent Items": [_gesendet()]},
                          sonder={"INBOX": "", "Sent Items": "\\Sent"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
    befund = _pruefe(eigene)
    assert befund.zustand == "gesendet" and befund.ordner == "Sent Items"


def test_ohne_kennzeichen_gesendete_elemente(eigene, monkeypatch):
    server = ImapAttrappe({"Gesendete Elemente": [_gesendet()]},
                          sonder={"INBOX": "", "Gesendete Elemente": ""})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
    assert _pruefe(eigene).zustand == "gesendet"


def test_der_gesendet_ordner_kommt_aus_thunderbird(eigene, monkeypatch, tmp_path):
    from test_thunderbird_signatur import _attrappe, _grundwerte

    ordner = _attrappe(tmp_path, _grundwerte(
        fcc_folder="imap://muster%40example.de@outlook.office365.com/Postausgang Kopie"))
    server = ImapAttrappe({"Postausgang Kopie": [_gesendet()]})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", server)
    befund = _pruefe(eigene, thunderbird_ordner=ordner)
    assert befund.zustand == "gesendet" and befund.ordner == "Postausgang Kopie"
    assert not server.befehle("LIST"), "Thunderbird nannte den Ordner, LIST war unnötig"


# ── Die Meldungen ───────────────────────────────────────────────────────────

def test_die_meldung_schon_gesendet():
    befund = gesendet.Befund("gesendet", datum=datetime(2026, 10, 21, 16, 33,
                                                         tzinfo=timezone.utc),
                             an=EMPFAENGER, betreff="AW: Programm")
    zeilen = gesendet.meldung(befund, zeitzone=timezone(timedelta(hours=2))).splitlines()
    assert zeilen[0].startswith("SCHON GESENDET  21.10.2026 18:33 an paula@example.org")
    assert "„AW: Programm“" in zeilen[0]
    assert "--trotz-gesendet" in zeilen[-1]


def test_die_meldung_geaenderte_fassung():
    befund = gesendet.Befund("geaendert", datum=JETZT, an=EMPFAENGER, betreff="AW: Programm")
    text = gesendet.meldung(befund)
    assert text.startswith("GEÄNDERTE FASSUNG  ")
    assert "Nachtrag" in text and "--trotz-gesendet" in text


def test_die_meldung_nicht_geprueft():
    text = gesendet.meldung(gesendet.Befund("nicht_geprueft", grund="kein Proxy"))
    assert text == "GESENDET NICHT GEPRÜFT: kein Proxy"


# ── Der Befehl ──────────────────────────────────────────────────────────────

class _Entwurf:
    def __init__(self):
        self.aufrufe = 0

    def __call__(self, felder, **_k):
        from falzmarke import oeffnen
        self.aufrufe += 1
        return oeffnen.Entwurfslage("Testprogramm", "", konto=felder["absender"])


@pytest.fixture
def befehl(tmp_path, monkeypatch):
    """`falzmarke email … --oeffnen` mit Attrappen: Entwurf zählt mit, Prüfung scharf."""
    from falzmarke import oeffnen

    monkeypatch.delenv("FALZMARKE_GESENDET", raising=False)
    # Ohne Bildschirm prüft der Befehl nicht (s. unten) — auf dem Baurechner
    # ist `CI` gesetzt. Das Fenster hält hier die Attrappe `_Entwurf` zu.
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("FALZMARKE_OEFFNEN", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")  # Linux-Runner: sonst „kein Bildschirm“
    entwurf = _Entwurf()
    monkeypatch.setattr(oeffnen, "entwurf", entwurf)
    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")

    def lauf(*extra):
        return falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE), "--oeffnen",
                               *extra])
    lauf.entwurf = entwurf
    lauf.eml = tmp_path / "antwort.eml"
    return lauf


def _jetzt_gesendet(**k):
    zeit = datetime.now(timezone.utc) - timedelta(minutes=3)
    return nachricht(an=EMPFAENGER, betreff=k.get("betreff", "AW: Sommerfest – Programm und was "
                                                             "noch fehlt"),
                     text=k.get("text", THUNDERBIRD_TEXT), datum=zeit), zeit


def test_befehl_sperrt_mit_exit_4_und_ohne_entwurf(befehl, monkeypatch, capsys):
    _server(monkeypatch, _jetzt_gesendet())
    code = befehl()
    ausgabe = capsys.readouterr()
    assert code == falzmarke.EXIT_SCHON_GESENDET == 4
    assert befehl.entwurf.aufrufe == 0, "trotz Treffer ein Entwurf"
    assert "SCHON GESENDET  " in ausgabe.err
    assert befehl.eml.is_file(), "die .eml ist trotzdem geschrieben"


def test_befehl_vorfall_anderer_betreff(befehl, monkeypatch, capsys):
    _server(monkeypatch, _jetzt_gesendet(betreff="Re: Sommerfest - Planung und was wir brauchen",
                                         text=THUNDERBIRD_TEXT + ZITAT))
    assert befehl() == 4
    assert befehl.entwurf.aufrufe == 0


def test_befehl_geaenderte_fassung_sperrt_auch(befehl, monkeypatch, capsys):
    _server(monkeypatch, _jetzt_gesendet(text=ANDERER_TEXT))
    assert befehl() == 4
    assert "GEÄNDERTE FASSUNG" in capsys.readouterr().err
    assert befehl.entwurf.aufrufe == 0


def test_befehl_trotz_gesendet_oeffnet(befehl, monkeypatch, capsys):
    _server(monkeypatch, _jetzt_gesendet())
    code = befehl("--trotz-gesendet")
    ausgabe = capsys.readouterr()
    assert code == 0
    assert befehl.entwurf.aufrufe == 1
    assert "SCHON GESENDET" in ausgabe.err and "--trotz-gesendet" in ausgabe.err


def test_befehl_frei_oeffnet_und_nennt_die_zahl(befehl, monkeypatch, capsys):
    _server(monkeypatch, _jetzt_gesendet(betreff="Termin", text=ANDERER_TEXT))
    code = befehl()
    ausgabe = capsys.readouterr()
    assert code == 0 and befehl.entwurf.aufrufe == 1
    assert "nicht gesendet" in ausgabe.out and "1 Mail" in ausgabe.out


def test_befehl_ohne_pruefung_oeffnet_und_sagt_es_zuletzt(befehl, monkeypatch, capsys):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    code = befehl()
    ausgabe = capsys.readouterr()
    assert code == 0 and befehl.entwurf.aufrufe == 1
    letzte = ausgabe.err.rstrip().splitlines()[-1]
    assert letzte.startswith("GESENDET NICHT GEPRÜFT: "), ausgabe.err


def test_befehl_abgeschaltet_verbindet_nicht(befehl, monkeypatch, capsys):
    server = _server(monkeypatch, _jetzt_gesendet())
    monkeypatch.setenv("FALZMARKE_GESENDET", "nie")
    assert befehl() == 0
    assert server.verbindungen == [] and befehl.entwurf.aufrufe == 1


def test_ohne_bildschirm_wird_nicht_geprueft(befehl, monkeypatch, capsys):
    """`FALZMARKE_OEFFNEN=nie` oder `CI`: Es entsteht kein Entwurf, also wird
    auch kein Postfach gefragt — auch nicht aus einem Kindprozess heraus."""
    server = _server(monkeypatch, _jetzt_gesendet())
    monkeypatch.setenv("FALZMARKE_OEFFNEN", "nie")
    assert befehl() == 0
    assert server.verbindungen == []
    assert "Gesendet nicht geprüft: FALZMARKE_OEFFNEN=nie" in capsys.readouterr().err


def test_ohne_oeffnen_wird_nicht_geprueft(tmp_path, monkeypatch):
    """Nichts geht auf, also gibt es nichts zu sperren — und keinen Grund, das
    Postfach zu fragen."""
    monkeypatch.delenv("FALZMARKE_GESENDET", raising=False)
    server = _server(monkeypatch, _jetzt_gesendet())
    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")
    assert falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE)]) == 0
    assert server.verbindungen == []


def test_die_flags_stehen_in_der_hilfe(capsys):
    with pytest.raises(SystemExit):
        falzmarke.main(["email", "--help"])
    hilfe = capsys.readouterr().out
    assert "--trotz-gesendet" in hilfe and "--noch-ein-entwurf" in hilfe


# ── Fassung aus dem Tagebuch (ADR 0056) ─────────────────────────────────────

def _thunderbird_mit_tagebuch(tmp_path, eintraege) -> Path:
    import json

    from falzmarke import entwurfsbuch

    ordner = tmp_path / "Thunderbird"
    profil = ordner / "Profiles" / "abc.default-release"
    profil.mkdir(parents=True)
    (ordner / "profiles.ini").write_text("[Install1]\nDefault=Profiles/abc.default-release\n",
                                         encoding="utf-8")
    (profil / entwurfsbuch.TAGEBUCH).write_text(
        "".join(json.dumps(e) + "\n" for e in eintraege), encoding="utf-8")
    return ordner


def _fassung_von(eml_pfad) -> str:
    import email
    from email import policy

    return str(email.message_from_bytes(eml_pfad.read_bytes(),
                                        policy=policy.default)["X-Falzmarke-Fassung"])


@pytest.mark.parametrize(("kennung", "erwartet"), [
    ("test@example.org", "gesendet"),
    # Gegenprobe: Das Tagebuch kennt eine andere Mail, die Fassung bleibt unbekannt.
    ("andere@example.org", "geaendert"),
])
def test_ohne_kopfzeile_kommt_die_fassung_aus_dem_tagebuch(eigene, monkeypatch, tmp_path,
                                                           kennung, erwartet):
    """Gemessen 25.10.2026: Thunderbird lässt `X-Falzmarke-Fassung` beim Senden weg.
    Die Mail ging mit geändertem Text hinaus, die Message-ID steht im Tagebuch."""
    _server(monkeypatch, _gesendet(text=ANDERER_TEXT))
    ordner = _thunderbird_mit_tagebuch(tmp_path, [{
        "zeit": JETZT.isoformat(), "art": "gesendet", "message_id": kennung,
        "ursprung": {"konto": "muster@example.de", "uid": 7, "fassung": _fassung_von(eigene)}}])
    assert _pruefe(eigene, thunderbird_ordner=ordner).zustand == erwartet


@pytest.mark.parametrize("roh", ["<a@b.de>", " a@b.de ", "<<a@b.de>>", "a@b.de", "\t<a@b.de>\n"])
def test_die_kennung_ohne_klammern_und_leerraum(roh):
    assert gesendet.kennung(roh) == "a@b.de"
