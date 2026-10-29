"""`falzmarke.ablage` — beantwortete Eingangspost wegsortieren (#431, ADR 0061).

Hier wird die echte Klasse `postfach.Postfach` gegen die Attrappe gefahren,
nicht ein zweiter Nachbau. Das Verschieben ist dort einzeln eingeschaltet
(`verschieben_erlaubt=True`); dass es ohne diesen Schalter weiter wirft, hält
`test_postfach.py` fest.
"""

from datetime import datetime, timedelta, timezone

import pytest

from falzmarke import ablage, postfach

from imap_attrappe import ImapAttrappe, nachricht

HEUTE = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
QUELLE = "<kunde-1@example.org>"


def _postfach(*, eingang=(), gesendet=(), sonder=None, verschieben=True,
              faehigkeiten=("IMAP4REV1", "UIDPLUS", "MOVE")):
    """Eine angemeldete Sitzung über einer Attrappe mit Eingang und Gesendet."""
    sonder = sonder if sonder is not None else {
        "INBOX": "", "Gesendete Elemente": "\\Sent", "Entw&APw-rfe": "\\Drafts", "Archiv": ""}
    attrappe = ImapAttrappe({"INBOX": list(eingang), "Gesendete Elemente": list(gesendet)},
                            sonder=sonder, verschieben_erlaubt=verschieben,
                            faehigkeiten=faehigkeiten)
    postfach.IMAP_KLASSE = attrappe
    sitzung = postfach.verbinde("joe@example.org", umgebung={}, frist=30)
    return attrappe, sitzung


@pytest.fixture(autouse=True)
def _klasse_zurueck(monkeypatch):
    monkeypatch.setattr(postfach, "IMAP_KLASSE", postfach.IMAP_KLASSE, raising=False)
    yield


def _eingegangen(kennung=QUELLE, betreff="Angebot S1", tage=5):
    zeit = HEUTE - timedelta(days=tage)
    return (nachricht(an="joe@example.org", von="kunde@example.org", betreff=betreff,
                      datum=zeit, kennung=kennung), zeit)


def _antwort(auf=QUELLE, betreff="AW: Angebot S1", tage=1):
    zeit = HEUTE - timedelta(days=tage)
    return (nachricht(an="kunde@example.org", betreff=betreff, datum=zeit,
                      kennung=f"<eigene-{tage}@example.org>", kopf={"In-Reply-To": auf}), zeit)


# ── Das Ziel ────────────────────────────────────────────────────────────────

def test_ohne_profilzeile_und_ohne_archive_wandert_nichts():
    """Der gemessene Normalfall an den Konten des Betreibers: Es gibt einen
    Ordner „Archiv", und `\\Archive` kennzeichnet ihn keiner."""
    _, sitzung = _postfach()
    with sitzung:
        ordner, grund = ablage.ablageordner(sitzung, None)
    assert ordner is None
    assert "`\\Archive`" in grund and "`email.ablage`" in grund


def test_mit_archive_kennzeichen_wird_es_genommen():
    """Die Gegenprobe zum Test darüber: Ist der Ordner gekennzeichnet, trägt
    der Weg — sonst belegte „wandert nichts" nur, dass nie etwas wandert."""
    _, sitzung = _postfach(sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                   "Archiv": "\\Archive"})
    with sitzung:
        ordner, grund = ablage.ablageordner(sitzung, None)
    assert (ordner, grund) == ("Archiv", None)


def test_die_profilzeile_nennt_den_ordner():
    _, sitzung = _postfach()
    with sitzung:
        assert ablage.ablageordner(sitzung, "Archiv") == ("Archiv", None)


def test_ein_ordner_der_nicht_existiert_wird_nicht_angelegt():
    attrappe, sitzung = _postfach()
    with sitzung:
        ordner, grund = ablage.ablageordner(sitzung, "Erledigt")
    assert ordner is None and "gibt es im Postfach nicht" in grund
    assert not attrappe.befehle("CREATE")
    assert "Erledigt" not in attrappe.ordner


def test_umlaute_im_ordnernamen_werden_kodiert():
    _, sitzung = _postfach(sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                   "Erl&APY-digt": ""})
    with sitzung:
        assert ablage.ablageordner(sitzung, "Erlödigt") == ("Erl&APY-digt", None)


def test_der_gesendet_ordner_ist_als_ziel_ausgeschlossen():
    """Die Abnahmezeile aus #431: nicht nur unerwünscht, sondern gesperrt —
    und zwar am Kennzeichen des Servers, nicht am Namen."""
    _, sitzung = _postfach()
    with sitzung:
        ordner, grund = ablage.ablageordner(sitzung, "Gesendete Elemente")
    assert ordner is None
    assert "\\sent" in grund and "ADR 0051" in grund


@pytest.mark.parametrize("name,kennzeichen", [
    ("Entw&APw-rfe", "\\Drafts"), ("Papierkorb", "\\Trash"), ("Spam", "\\Junk")])
def test_entwuerfe_papierkorb_und_spam_sind_ausgeschlossen(name, kennzeichen):
    _, sitzung = _postfach(sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                   name: kennzeichen})
    with sitzung:
        ordner, grund = ablage.ablageordner(sitzung, name)
    assert ordner is None and kennzeichen.lower() in grund


def test_der_eingang_ist_nicht_seine_eigene_ablage():
    _, sitzung = _postfach()
    with sitzung:
        ordner, grund = ablage.ablageordner(sitzung, "INBOX")
    assert ordner is None and "eigene Ablage" in grund


# ── Der Plan ────────────────────────────────────────────────────────────────

def test_die_beantwortete_nachricht_wird_gefunden():
    _, sitzung = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert bericht.grund is None and bericht.ziel == "Archiv"
    assert bericht.antworten == 1 and bericht.nicht_im_eingang == 0
    (zug,) = bericht.zuege
    assert zug.betreff == "Angebot S1" and zug.kennung == QUELLE
    assert zug.antwort_betreff == "AW: Angebot S1"
    assert bericht.verschoben == 0


def test_eine_antwort_ohne_nachricht_im_eingang_zaehlt_als_erledigt():
    _, sitzung = _postfach(eingang=[], gesendet=[_antwort()])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert bericht.zuege == () and bericht.nicht_im_eingang == 1


def test_eine_mail_ohne_in_reply_to_ist_keine_antwort():
    ohne = (nachricht(an="kunde@example.org", betreff="Neues Angebot",
                      datum=HEUTE - timedelta(days=1)), HEUTE - timedelta(days=1))
    _, sitzung = _postfach(eingang=[_eingegangen()], gesendet=[ohne])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert bericht.antworten == 0 and bericht.zuege == ()


def test_zwei_antworten_auf_dieselbe_nachricht_sind_ein_zug():
    _, sitzung = _postfach(eingang=[_eingegangen()],
                           gesendet=[_antwort(tage=3), _antwort(betreff="AW: nochmal", tage=1)])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert bericht.antworten == 2
    (zug,) = bericht.zuege
    assert zug.antwort_betreff == "AW: nochmal", "die jüngste Antwort gehört in den Bericht"


def test_eine_alte_antwort_liegt_ausserhalb_des_fensters():
    _, sitzung = _postfach(eingang=[_eingegangen(tage=90)], gesendet=[_antwort(tage=60)])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", seit_tagen=30, heute=HEUTE.date())
    assert bericht.antworten == 0 and bericht.zuege == ()


def test_die_beantwortete_nachricht_darf_aelter_sein_als_das_fenster():
    """Gesucht wird über die Message-ID, nicht über ein Datum — sonst fiele
    gerade der Fall heraus, um den es geht: lange liegende Post."""
    _, sitzung = _postfach(eingang=[_eingegangen(tage=300)], gesendet=[_antwort(tage=2)])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", seit_tagen=30, heute=HEUTE.date())
    assert len(bericht.zuege) == 1


def test_ohne_gesendet_kennzeichen_wird_nichts_gesagt_was_erledigt_ist():
    _, sitzung = _postfach(sonder={"INBOX": "", "Archiv": ""})
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert "`\\Sent`" in bericht.grund and bericht.zuege == ()


# ── Der Zug ─────────────────────────────────────────────────────────────────

def test_ohne_machen_bewegt_der_lauf_nichts():
    """Die Abnahmezeile „ein Lauf ohne --machen verändert kein Postfach"."""
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    vorher = len(attrappe.ordner["INBOX"]), len(attrappe.ordner["Archiv"])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={})
    assert len(bericht.zuege) == 1 and bericht.verschoben == 0
    assert not attrappe.befehle("UID MOVE")
    assert not attrappe.befehle("SELECT"), "gewählt wurde nur lesend"
    assert (len(attrappe.ordner["INBOX"]), len(attrappe.ordner["Archiv"])) == vorher


def test_mit_machen_wandert_genau_die_beantwortete_nachricht():
    anderes = (nachricht(an="joe@example.org", betreff="Noch offen",
                         datum=HEUTE - timedelta(days=2), kennung="<offen@example.org>"),
               HEUTE - timedelta(days=2))
    attrappe, _ = _postfach(eingang=[_eingegangen(), anderes], gesendet=[_antwort()])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert bericht.verschoben == 1
    (zug,) = attrappe.befehle("UID MOVE")
    assert zug[2] == '"Archiv"'
    assert [n.uid for n in attrappe.ordner["Archiv"]] == [int(bericht.zuege[0].uid)]
    übrig = [postfach.kopf_aus(n.roh, str(n.uid), None).betreff
             for n in attrappe.ordner["INBOX"]]
    assert übrig == ["Noch offen"], "nur die beantwortete Nachricht wandert"


def test_der_zweite_lauf_verschiebt_nichts_mehr():
    """Idempotenz kommt aus dem Postfach, nicht aus einer Zustandsdatei."""
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    erst = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    zweit = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert erst.verschoben == 1 and zweit.verschoben == 0
    assert zweit.zuege == () and zweit.nicht_im_eingang == 1
    assert len(attrappe.befehle("UID MOVE")) == 1


def test_ohne_move_in_capability_wird_nichts_nachgebaut():
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()],
                            faehigkeiten=("IMAP4REV1",))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert "CAPABILITY kein MOVE" in bericht.grund
    assert not attrappe.befehle("UID MOVE")
    assert len(attrappe.ordner["INBOX"]) == 1


def test_ein_unerreichbares_postfach_ist_ein_grund(monkeypatch):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError()))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={})
    assert "Verbindung abgelehnt" in bericht.grund and bericht.verschoben == 0


def test_der_trockenlauf_haelt_auch_an_einer_sperrenden_attrappe():
    """Die scharfe Fassung der Zusage „ohne --machen wird nichts bewegt".

    Hier verbietet die Attrappe `SELECT` und `UID MOVE` wie überall sonst im
    Bestand. Der Lauf ist nur grün, wenn er beides nicht einmal versucht —
    fällt der Trockenlauf, wird dieser Test rot, ohne dass irgendwo sabotiert
    werden muss. Die Gegenprobe steht darunter.
    """
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()],
                            verschieben=False)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={})
    assert len(bericht.zuege) == 1 and bericht.verschoben == 0
    assert len(attrappe.ordner["INBOX"]) == 1


def test_gegenprobe_mit_machen_schlaegt_die_sperrende_attrappe_an():
    """Ohne sie belegte der Test darüber nichts: Ein Lauf, der am Ziel
    vorbeiläuft, wäre dort auch grün."""
    _postfach(eingang=[_eingegangen()], gesendet=[_antwort()], verschieben=False)
    with pytest.raises(AssertionError, match="readonly|UID MOVE"):
        ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})


# ── Das Profilfeld `email.ablage` ───────────────────────────────────────────

def _profilbefunde(ablage_wert) -> set[str]:
    from falzmarke import lint

    bericht = lint.Bericht()
    lint.pruefe_email_ablage({"absender": "joe@example.org", "ablage": ablage_wert}, bericht)
    return {b.regel for b in bericht.befunde}


def test_ein_leeres_feld_meldet():
    """`ablage: ""` soll melden, nicht stillschweigend „verschiebe nichts"
    bedeuten — derselbe Grund wie bei `email.stil.person`."""
    assert "email.ablage" in _profilbefunde("")
    assert "email.ablage" in _profilbefunde(["Archiv"])


def test_leerraum_am_rand_meldet():
    assert "email.ablage" in _profilbefunde(" Archiv")


def test_ein_gueltiger_ordnername_schweigt():
    assert _profilbefunde("Archiv") == set()
    assert _profilbefunde("INBOX/Erledigt") == set()


def test_ohne_das_feld_wird_nichts_gemeldet():
    from falzmarke import lint

    bericht = lint.Bericht()
    lint.pruefe_email_ablage({"absender": "joe@example.org"}, bericht)
    assert bericht.befunde == []


def test_das_feld_steht_in_der_positivliste():
    """Ohne diese Zeile meldete `lint` ein gepflegtes `ablage:` als unbekannt."""
    from falzmarke import lint

    assert "ablage" in lint.PROFIL_EMAIL_FELDER


# ── Ausgabe ─────────────────────────────────────────────────────────────────

def test_text_und_json_sagen_dasselbe():
    """Nach #414 entscheidet eine Stelle, beide Darstellungen folgen ihr."""
    _, sitzung = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    text = "\n".join(ablage.zeilen(bericht))
    daten = ablage.als_json(bericht)
    assert daten["ablage"] == "Archiv" and "Archiv" in text
    assert str(daten["antworten"]) in text
    assert len(daten["zuege"]) == len(bericht.zuege)
    assert daten["zuege"][0]["betreff"] in text
    assert daten["verschoben"] == 0 and "--machen" in text


def test_ein_grund_steht_in_beiden_darstellungen():
    _, sitzung = _postfach()
    with sitzung:
        bericht = ablage.plane(sitzung, heute=HEUTE.date())
    (zeile,) = ablage.zeilen(bericht)
    assert zeile.startswith("NICHT GEPRÜFT")
    assert ablage.als_json(bericht)["grund"] == bericht.grund


def test_der_grund_kostet_exit_3_und_der_saubere_lauf_nicht(monkeypatch, capsys):
    """Beide Richtungen in einem Durchgang: Ein Lauf ohne Befund gibt immer 0,
    und ein Exit-Code, der nie 3 wird, belegte die Zeile in `docs/email.md`
    nicht. Gemessen am Gerät ging das unter — `python3 -c "…main()"` wirft den
    Rückgabewert weg und zeigt stur 0 (28.10.2026).
    """
    from falzmarke import cli as falzmarke

    # Kein `\\Sent`-Kennzeichen: dann ist nicht zu wissen, was beantwortet ist.
    attrappe, _ = _postfach(sonder={"INBOX": "", "Archiv": "\\Archive"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org"]) \
        == falzmarke.EXIT_UMGEBUNG
    assert capsys.readouterr().err.startswith("NICHT GEPRÜFT  joe@example.org")

    # Dieselbe Lage, nur mit Gesendet-Ordner: ein Zug, nichts bewegt, Exit 0.
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()],
                            sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                    "Archiv": "\\Archive"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org"]) == falzmarke.EXIT_OK
    ausgabe = capsys.readouterr()
    assert ausgabe.out.startswith("OK  joe@example.org") and "Archiv" in ausgabe.out
    assert attrappe.befehle("UID MOVE") == []


def test_ein_fenster_unter_einem_tag_ist_ein_eingabefehler(capsys):
    """`--seit 0` fragt nach Antworten aus der Zukunft. Exit 1, vor dem Postfach.

    Die Reihenfolge ist Teil der Aussage: Schlüge die Grenze erst nach der
    Anmeldung zu, nähme der Lauf erst eine Verbindung auf.
    """
    from falzmarke import cli as falzmarke

    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--seit", "0"]) \
        == falzmarke.EXIT_EINGABE
    assert "--seit" in capsys.readouterr().err


# ── Die Quelle selbst ───────────────────────────────────────────────────────

#: IMAP-Befehle, die eine Nachricht bewegen oder verändern.
BEFEHLE = {"MOVE", "COPY", "STORE", "EXPUNGE", "DELETE", "CREATE", "RENAME", "APPEND",
           "SEARCH", "FETCH", "SELECT", "EXAMINE", "LIST", "LOGIN", "LOGOUT"}


def _befehlswoerter(baum) -> set[str]:
    """Jedes Textliteral, das für sich genommen ein IMAP-Befehl ist.

    Nicht die Argumente von `uid(...)`: `postfach.Postfach._befehl` nimmt die
    Methode und reicht die Argumente weiter, also steht `"MOVE"` gar nicht im
    Aufruf von `uid`. Eine Prüfung, die nur Aufrufe ansieht, fände deshalb
    weder den erlaubten noch einen verbotenen Befehl — gemessen, nicht
    vermutet: Genau so fiel der Positivteil beim ersten Lauf.

    **Docstrings sind ausgenommen.** Der Modulkopf von `ablage` nennt `COPY`,
    `STORE` und `EXPUNGE`, um zu erklären, dass es sie nicht benutzt; ein
    freier Treffer würde also ausgerechnet die Erklärung des Verbots als
    Verstoß melden. Und ohne den Ausschluss könnte der Positivteil unten aus
    Prosa statt aus Code erfüllt werden.

    Verglichen wird auf Gleichheit, nicht auf Vorkommen: Der Satz „falzmarke
    baut es nicht aus COPY, STORE und EXPUNGE nach" ist kein Befehl.
    """
    import ast

    prosa = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, (ast.Module, ast.ClassDef, ast.FunctionDef,
                               ast.AsyncFunctionDef)):
            erster = (knoten.body or [None])[0]
            if (isinstance(erster, ast.Expr) and isinstance(erster.value, ast.Constant)
                    and isinstance(erster.value.value, str)):
                prosa.add(id(erster.value))
    aus = set()
    for knoten in ast.walk(baum):
        if (isinstance(knoten, ast.Constant) and isinstance(knoten.value, str)
                and id(knoten) not in prosa):
            wort = knoten.value.strip().upper()
            if wort in BEFEHLE:
                aus.add(wort)
    return aus


def test_das_modul_kennt_genau_einen_aendernden_befehl():
    """`MOVE` und sonst nichts — gelesen am Syntaxbaum, nicht an der Doku.

    Anders als in `test_postfach.py` reicht die Verbotsliste über
    Attributnamen hier **nicht**: `self._v.uid("COPY", …)` heißt `uid` und
    käme durch. Geprüft werden deshalb die Argumente von `uid(...)`, und der
    Positivteil belegt, dass die Prüfung die Stelle überhaupt liest.
    """
    import ast
    from pathlib import Path

    baum = ast.parse(Path(ablage.__file__).read_text(encoding="utf-8"))

    befehle = _befehlswoerter(baum)
    assert "MOVE" in befehle, "die Prüfung sieht den ändernden Befehl nicht"
    assert not befehle & {"COPY", "STORE", "EXPUNGE", "DELETE", "CREATE", "RENAME",
                          "APPEND"}, befehle

    zugriffe = {k.attr for k in ast.walk(baum) if isinstance(k, ast.Attribute)}
    assert not zugriffe & {"store", "expunge", "copy", "move", "delete", "create", "rename",
                           "send", "sendmail", "send_message"}, zugriffe
    assert {"uid", "select"} <= zugriffe, "die Prüfung sieht die Zugriffe nicht"

    importe = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            importe |= {a.name.split(".")[0] for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom):
            importe.add((knoten.module or "").split(".")[0])
    assert not importe & {"smtplib", "subprocess", "socket", "imaplib"}, importe


def test_gegenprobe_die_quellpruefung_findet_einen_zweiten_befehl():
    """Drei Proben, die melden MÜSSEN — sonst belegte der Test darüber nichts.

    Die zweite ist die wichtige: So steht der Befehl in `ablage.verschiebe`
    wirklich, als weitergereichtes Argument. Eine Prüfung, die nur Aufrufe von
    `uid` ansieht, bliebe dort grün.
    """
    import ast

    direkt = _befehlswoerter(ast.parse('def f(v):\n    v.uid("COPY", "1", "y")\n'))
    assert direkt == {"COPY"}

    weitergereicht = _befehlswoerter(ast.parse(
        'def f(s):\n    s._befehl("x", s._v.uid, "EXPUNGE", "1")\n'))
    assert weitergereicht == {"EXPUNGE"}, "so sieht der echte Aufruf aus"

    # Und die Gegenrichtung: Prosa über die Befehle ist kein Verstoß.
    prosa = _befehlswoerter(ast.parse(
        '"""Kein COPY, kein STORE, kein EXPUNGE."""\ndef f():\n    """Auch kein MOVE."""\n'))
    assert prosa == set(), "die Erklärung des Verbots darf nicht als Verstoß gelten"
