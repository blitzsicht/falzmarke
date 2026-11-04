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
              faehigkeiten=("IMAP4REV1", "UIDPLUS", "MOVE"), **optionen):
    """Eine angemeldete Sitzung über einer Attrappe mit Eingang und Gesendet."""
    sonder = sonder if sonder is not None else {
        "INBOX": "", "Gesendete Elemente": "\\Sent", "Entw&APw-rfe": "\\Drafts", "Archiv": ""}
    attrappe = ImapAttrappe({"INBOX": list(eingang), "Gesendete Elemente": list(gesendet)},
                            sonder=sonder, verschieben_erlaubt=verschieben,
                            faehigkeiten=faehigkeiten, **optionen)
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
    Ordner „Archiv“, und `\\Archive` kennzeichnet ihn keiner."""
    _, sitzung = _postfach()
    with sitzung:
        ordner, grund = ablage.ablageordner(sitzung, None)
    assert ordner is None
    assert "`\\Archive`" in grund and "`email.ablage`" in grund


def test_mit_archive_kennzeichen_wird_es_genommen():
    """Die Gegenprobe zum Test darüber: Ist der Ordner gekennzeichnet, trägt
    der Weg — sonst belegte „wandert nichts“ nur, dass nie etwas wandert."""
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


def test_eine_teilkette_der_kennung_ist_kein_treffer():
    """Der Anlass aus #442: `SEARCH HEADER` findet `123` auch in fremden Kennungen."""
    attrappe, sitzung = _postfach(eingang=[_eingegangen("<x123y@example.org>")],
                                  gesendet=[_antwort("123")])
    with sitzung:
        assert sitzung._suche_kopfzeile("INBOX", "Message-ID", "123"), \
            "Kontrollprobe: die Attrappe muss die Teilkette finden wie ein Server"
        assert sitzung.suche_kennung("INBOX", "123") == []
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert bericht.zuege == () and bericht.nicht_im_eingang == 1


def test_viele_teiltreffer_verdraengen_die_echte_nachricht_nicht(monkeypatch):
    """Review von #457 (#468): Die Teiltreffer des Servers wurden auf die neuesten
    `GRENZE` gekappt, **bevor** exakt verglichen wurde. Bei einer kurzen Kennung
    fiel die ältere, echte Nachricht heraus, und der Grenz-Hinweis erschien,
    ausgelöst nur von fremden Treffern."""
    monkeypatch.setattr(postfach, "GRENZE", 2)
    fremde = [_eingegangen(f"<x123y{i}@example.org>", betreff=f"fremd {i}", tage=4 - i)
              for i in range(3)]
    _, sitzung = _postfach(eingang=[_eingegangen("<123>", betreff="echt", tage=5), *fremde],
                           gesendet=[_antwort("123")])
    with sitzung:
        assert len(sitzung._suche_kopfzeile("INBOX", "Message-ID", "123")) == 4, \
            "Kontrollprobe: mehr Teiltreffer als GRENZE, sonst misst der Test nichts"
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert [z.betreff for z in bericht.zuege] == ["echt"] and bericht.nicht_im_eingang == 0
    assert not [h for h in bericht.hinweise if "angesehen" in h], bericht.hinweise


def test_mehr_teiltreffer_als_die_suchgrenze_werden_gekappt_und_gemeldet(monkeypatch):
    """Nachreview von #479: Eine Kennung ohne Klammern ist eine Teilkette, und die
    kann in einem alten Eingang tausendfach treffen. `suche_kennung` holt dann
    nicht jeden Kopf nach, sondern höchstens `SUCHGRENZE`, und sagt es."""
    monkeypatch.setattr(postfach, "SUCHGRENZE", 3)
    fremde = [_eingegangen(f"<x123y{i}@example.org>", betreff=f"fremd {i}", tage=4 - i)
              for i in range(4)]
    _, sitzung = _postfach(eingang=fremde)
    with sitzung:
        assert sitzung.suche_kennung("INBOX", "123") == []
        assert sitzung.gekappt == {"INBOX": (4, 3)}, "die Teiltreffer wurden nicht gekappt"
    _, sitzung = _postfach(eingang=fremde[:3])                       # Gegenstück: unter der Grenze
    with sitzung:
        assert sitzung.suche_kennung("INBOX", "123") == [] and sitzung.gekappt == {}


def test_eine_kennung_ohne_klammern_findet_ihre_nachricht():
    _, sitzung = _postfach(eingang=[_eingegangen("<abc@example.org>")],
                           gesendet=[_antwort("abc@example.org")])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert [z.betreff for z in bericht.zuege] == ["Angebot S1"]
    assert bericht.nicht_im_eingang == 0


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


# ── Die Zuordnung über `In-Reply-To` (#438) ────────────────────────────────

#: Zwei Kennungen, deren Summe über 78 Zeichen liegt. `EmailMessage` faltet die
#: Zeile dann von selbst — der Fall braucht keinen Kunstgriff.
LANG = "<kunde-mit-sehr-langer-nachrichtenkennung-aus-dem-fremdsystem-0001@example.org>"
ZWEITE = "<zweite-kennung@example.org>"


def _antwort_auf_zwei(erste, zweite, *, tage=1, falten=False):
    """Eine Antwort, deren `In-Reply-To` zwei Kennungen nennt — RFC 5322 erlaubt es.

    Die Kopfzeile wird **roh** gesetzt (`roh_kopf`), nicht über `EmailMessage`:
    Dessen Policy kodiert eine lange Message-ID auf Python 3.12 als
    `=?utf-8?q?…?=` und auf 3.14 nicht. Über die Policy gebaut, prüfte diese
    Probe auf der CI-Fassung etwas anderes als lokal (#438).
    """
    zeit = HEUTE - timedelta(days=tage)
    trenner = "\r\n " if falten else " "
    return (nachricht(an="kunde@example.org", betreff="AW: Sammelvorgang", datum=zeit,
                      kennung=f"<eigene-{tage}@example.org>",
                      roh_kopf={"In-Reply-To": f"{erste}{trenner}{zweite}"}), zeit)


def test_eine_gefaltete_kopfzeile_laesst_den_lauf_berichten():
    """Der rohe Feldwert trägt dann einen Umbruch, und ungeparst geht er in die
    IMAP-Befehlszeile. Auf Python 3.14 ist das ein `ValueError`, auf 3.12 und
    3.13 gehen **zwei** Befehle auf die Leitung — gemessen am 29.10.2026, und
    die CI fährt 3.12. Die Attrappe lehnt mit demselben Wortlaut ab wie
    `imaplib.IMAP4._command`, damit die Probe überall gleich anschlägt.
    """
    attrappe, sitzung = _postfach(eingang=[_eingegangen(kennung=LANG)],
                                  gesendet=[_antwort_auf_zwei(LANG, ZWEITE, falten=True)])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert bericht.grund is None, f"der Lauf kam nicht durch: {bericht.grund}"
    assert [z.kennung for z in bericht.zuege] == [LANG]
    gesucht = [a for befehl in attrappe.befehle("UID SEARCH") for a in befehl]
    assert not any("\r" in str(a) or "\n" in str(a) for a in gesucht), \
        "ein Umbruch erreichte die Befehlszeile"


@pytest.mark.parametrize("kennung, erwartet", [
    ("<gut@example.org>", True),
    ("frei ohne Klammern", True),
    ("<a\x00b@example.org>", False),
    ("<a\rb@example.org>", False),
    ("<müller@example.org>", False),
], ids=["gesund", "fallback", "nullbyte", "umbruch", "nicht-ascii"])
def test_sendbar_trennt_was_die_leitung_vertraegt(kennung, erwartet):
    assert postfach.sendbar(kennung) is erwartet


def test_der_kodierfehler_von_imaplib_wird_ein_grund_kein_traceback():
    """`imaplib` kodiert mit ASCII, und das ist ein `ValueError` (#442)."""
    _, sitzung = _postfach()
    with sitzung, pytest.raises(postfach.PostfachFehler, match="SEARCH"):
        sitzung._befehl("SEARCH", lambda: bytes("<müller@example.org>", "ascii"))


def test_eine_unsendbare_kennung_ist_kein_laengst_weggeraeumt():
    """Nicht gesucht heißt nicht gefunden: Die Nachricht wird im Bericht genannt, nicht
    als erledigt gezählt."""
    zeit = HEUTE - timedelta(days=1)
    antwort = (nachricht(an="kunde@example.org", betreff="AW: x", datum=zeit,
                         kennung="<eigene@example.org>",
                         roh_kopf={"In-Reply-To": "<a\x01\x00b@example.org>"}), zeit)
    _, sitzung = _postfach(gesendet=[antwort])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert (bericht.antworten, bericht.nicht_im_eingang, bericht.grund) == (1, 0, None)
    assert any("1 Kennungen in `In-Reply-To` übersprungen" in h for h in bericht.hinweise)
    assert ablage.als_json(bericht)["hinweise"] == list(bericht.hinweise)


def test_zwei_kennungen_in_einer_zeile_finden_beide_nachrichten():
    """Als **eine** Teilkette gesucht, trifft `<a@x> <b@y>` keine der beiden
    Message-IDs. Beide Nachrichten blieben im Eingang und würden trotzdem als
    „längst weggeräumt“ gezählt, also als erledigt gemeldet, ohne es zu sein.
    """
    erste, zweite = "<a@example.org>", "<b@example.org>"
    _, sitzung = _postfach(eingang=[_eingegangen(kennung=erste, betreff="Erstes"),
                                    _eingegangen(kennung=zweite, betreff="Zweites")],
                           gesendet=[_antwort_auf_zwei(erste, zweite)])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert sorted(z.kennung for z in bericht.zuege) == [erste, zweite]
    assert bericht.nicht_im_eingang == 0


def test_eine_antwort_zaehlt_erst_als_erledigt_wenn_keine_kennung_traf():
    """Die Gegenrichtung: Nennt eine Antwort zwei Kennungen und liegt nur eine
    im Eingang, ist sie nicht „ohne Nachricht im Eingang“ — sonst zählte
    dieselbe Antwort gleichzeitig als Zug und als längst erledigt.
    """
    _, sitzung = _postfach(eingang=[_eingegangen(kennung="<a@example.org>")],
                           gesendet=[_antwort_auf_zwei("<a@example.org>", "<fort@example.org>")])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert len(bericht.zuege) == 1 and bericht.nicht_im_eingang == 0


def test_eine_gekappte_suche_im_gesendet_ordner_wird_gemeldet(monkeypatch):
    """Über `postfach.GRENZE` sieht `koepfe` nur die jüngsten Mails. Ohne
    Hinweis liest sich „0 von 2 Antworten seit …“ wie ein vollständiges
    Fenster, und was davor liegt, wird nie aufgeräumt. `entwurfsbuch` meldet
    das für dieselben Ordner längst (ADR 0055).
    """
    monkeypatch.setattr(postfach, "GRENZE", 2)
    _, sitzung = _postfach(eingang=[_eingegangen(kennung="<alt@example.org>", betreff="Alt")],
                           gesendet=[_antwort(auf="<alt@example.org>", tage=3),
                                     _antwort(tage=2), _antwort(tage=1)])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    (hinweis,) = [h for h in bericht.hinweise if "angesehen" in h]
    assert "nur die neuesten 2 von 3" in hinweis
    assert hinweis in "\n".join(ablage.zeilen(bericht)), "der Text verschweigt die Kappung"
    assert hinweis in ablage.als_json(bericht)["hinweise"], "--json verschweigt die Kappung"
    assert bericht.zuege == (), \
        "die Probe trifft nicht: die weggekappte Antwort war trotzdem dabei"


def test_gegenprobe_ohne_kappung_steht_kein_hinweis_da():
    """Ohne sie belegte der Test darüber nichts: Ein Hinweis, der immer käme,
    sagt über die Kappung nichts."""
    _, sitzung = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert bericht.hinweise == () and len(bericht.zuege) == 1


# ── Der Zug ─────────────────────────────────────────────────────────────────

def test_ohne_machen_bewegt_der_lauf_nichts():
    """Die Abnahmezeile „ein Lauf ohne --machen verändert kein Postfach“."""
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


def test_scheitert_der_zug_bleiben_die_gefundenen_nachrichten_sichtbar():
    """„0 von 0 Antworten“ ist die stärkste Form von „nichts geschehen“ — und
    stand bisher genau dort, wo etwas geschehen sein kann: Bricht `UID MOVE`
    ab, nachdem der Server einen Teil des Satzes bewegt hat, verwarf der
    `except` den fertigen Plan samt UIDs (#438).
    """
    _postfach(eingang=[_eingegangen()], gesendet=[_antwort()], faehigkeiten=("IMAP4REV1",))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert "CAPABILITY kein MOVE" in bericht.grund
    assert bericht.antworten == 1 and len(bericht.zuege) == 1, \
        "der Grund hat den Plan mitgenommen"
    assert bericht.verschoben == 0 and bericht.ziel == "Archiv"


def test_scheitert_der_zug_stehen_die_uids_auch_im_text():
    """Der Test darüber hält den Plan im Bericht fest, dieser hier in der
    Textausgabe. Bis #442 (N2) ergab derselbe Bericht dort genau eine Zeile,
    `NICHT GEPRÜFT …`, und die UIDs standen nur im JSON.
    """
    _postfach(eingang=[_eingegangen()], gesendet=[_antwort()], faehigkeiten=("IMAP4REV1",))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    (zug,) = bericht.zuege
    text = ablage.zeilen(bericht)
    assert text[0].startswith("NICHT GEPRÜFT"), "der Grund muss vorn stehen, er geht auf stderr"
    assert any(f"UID {zug.uid} " in z and zug.betreff in z for z in text[1:]), \
        "die gefundene Nachricht fehlt in der Textausgabe"
    # Ohne MOVE in CAPABILITY ging kein ändernder Befehl hinaus. Bis zum Review
    # von #459 hieß es hier trotzdem „ob der Server … bewegt hat, ist nicht
    # geprüft“, und der Bediener suchte im Ablageordner nach nichts.
    assert text[1] == ("    1 Nachricht für „Archiv“ gefunden; "
                       "nichts bewegt, der Zug war noch nicht gesendet")
    assert bericht.zug_gesendet is False and ablage.als_json(bericht)["zug_gesendet"] is False


def test_bricht_uid_move_selbst_ab_bleibt_offen_was_bewegt_ist(monkeypatch):
    """Der eine Fall, in dem der Server schon etwas bewegt haben kann.

    Gegenstück zum Test darüber: Dort brach der Lauf vor dem Zug ab, hier im
    Zug. Nur hier darf der Text sagen, dass es nicht geprüft ist.
    """
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    echtes_uid = attrappe.uid

    def move_bricht_ab(befehl, *args):
        if befehl.upper() == "MOVE":
            attrappe.protokoll.append(("UID MOVE", *args))
            raise OSError("Verbindung getrennt")
        return echtes_uid(befehl, *args)

    monkeypatch.setattr(attrappe, "uid", move_bricht_ab)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert "Verbindung getrennt" in bericht.grund
    assert bericht.zug_gesendet is True and ablage.als_json(bericht)["zug_gesendet"] is True
    assert ablage.zeilen(bericht)[1] == ("    1 Nachricht für „Archiv“ gefunden; "
                                         "ob der Server davon schon etwas bewegt hat, "
                                         "ist nicht geprüft")


def test_ein_grund_ohne_plan_bleibt_eine_zeile():
    """Gegenstück: ohne Züge kein Satz über „gefunden“."""
    bericht = ablage.Bericht(adresse="joe@example.org", ziel=None, grund="Verbindung abgelehnt",
                             seit=None, antworten=0, nicht_im_eingang=0, zuege=(), verschoben=0)
    assert ablage.zeilen(bericht) == ["NICHT GEPRÜFT  joe@example.org: Verbindung abgelehnt"]


def test_ein_ziel_das_nach_dem_plan_verschwindet_ist_ein_grund(monkeypatch):
    """Der Ablageordner wird je Lauf **einmal** bestimmt. Vorher bestimmte ihn
    der Zug ein zweites Mal und benutzte das Ergebnis ungeprüft: Fiel der
    Ordner inzwischen weg, lief `None` als Ziel ins Modul und endete als
    `TypeError`, nicht als Satz (#438).

    Der Ordner verschwindet hier **nach** dem Plan, nicht nach dem n-ten
    `LIST`: Eine Probe, die interne Aufrufe zählt, misst den Umbau mit, nicht
    die Zusage — und wurde genau daran rot, als der Umbau einen `LIST` sparte.
    """
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    echtes_plane = ablage.plane

    def plane_und_dann_ordner_weg(*args, **kwargs):
        bericht = echtes_plane(*args, **kwargs)
        attrappe.sonder.pop("Archiv", None)
        attrappe.ordner.pop("Archiv", None)
        return bericht

    monkeypatch.setattr(ablage, "plane", plane_und_dann_ordner_weg)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert bericht.grund, "ein verschwundenes Ziel muss ein Satz sein, kein Absturz"
    assert bericht.verschoben == 0 and len(bericht.zuege) == 1, \
        "der Grund hat den Plan mitgenommen"


def test_ein_unerreichbares_postfach_ist_ein_grund(monkeypatch):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError()))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={})
    assert "Verbindung abgelehnt" in bericht.grund and bericht.verschoben == 0


def test_der_trockenlauf_haelt_auch_an_einer_sperrenden_attrappe():
    """Die scharfe Fassung der Zusage „ohne --machen wird nichts bewegt“.

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


# ── Fähnchen, benannte Mails, Jahresordner (#478) ───────────────────────────
#
# Die Attrappe vergibt UIDs ab 101 in der Reihenfolge des Eingangs.

def _mit_fahnen(eintrag, flags):
    return (*eintrag, flags)


def _offen(betreff="Eingereichte Fassung", kennung="<abschluss@example.org>", tage=3):
    """Eine Eingangsmail, auf die keine Antwort verweist — erledigt ohne Antwort."""
    zeit = HEUTE - timedelta(days=tage)
    return (nachricht(an="joe@example.org", von="amt@example.org", betreff=betreff,
                      datum=zeit, kennung=kennung), zeit)


def _uids(attrappe, ordner="INBOX"):
    return [n.uid for n in attrappe.ordner[ordner]]


def test_mit_uid_wandert_genau_die_genannte_mail_auch_ohne_antwort():
    attrappe, _ = _postfach(eingang=[_offen("Erste", "<e1@example.org>"),
                                     _offen("Zweite", "<e2@example.org>"),
                                     _offen("Dritte", "<e3@example.org>")])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101", "103"])
    assert bericht.grund is None and bericht.benannt and bericht.verschoben == 2
    (zug,) = attrappe.befehle("UID MOVE")
    assert zug[1:] == ("101,103", '"Archiv"'), "es bleibt beim einen UID MOVE"
    assert _uids(attrappe) == [102] and _uids(attrappe, "Archiv") == [101, 103]


def test_mit_uid_ohne_machen_bewegt_nichts_und_nennt_datum_absender_betreff():
    attrappe, _ = _postfach(eingang=[_offen()])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={}, uids=["101"])
    assert bericht.verschoben == 0
    assert not attrappe.befehle("UID MOVE") and not attrappe.befehle("SELECT")
    text = ablage.zeilen(bericht)
    assert text[0] == ("OK  joe@example.org: 1 benannte Nachricht im Eingang, "
                       "1 zum Ablegen → „Archiv“")
    (zeile,) = [z for z in text if z.startswith("    UID 101 ")]
    datum = (HEUTE - timedelta(days=3)).astimezone().strftime("%d.%m.%Y")
    assert datum in zeile and "amt@example.org" in zeile and "„Eingereichte Fassung“" in zeile
    assert "beantwortet" not in zeile, "eine benannte Mail hat keine Antwort"
    assert "    nichts bewegt — mit --machen verschieben" in text


def test_fehlt_eine_genannte_uid_wandert_keine():
    """Eine Liste, die nicht mehr stimmt, ist kein Auftrag für den Rest."""
    attrappe, _ = _postfach(eingang=[_offen()])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101", "999"])
    assert "UID 999 liegt nicht im Eingang" in bericht.grund
    assert bericht.verschoben == 0 and not attrappe.befehle("UID MOVE")
    assert _uids(attrappe) == [101]
    assert [z.uid for z in bericht.zuege] == ["101"], "die gefundene steht trotzdem da"
    assert ablage.zeilen(bericht)[0].startswith("NICHT GEPRÜFT  joe@example.org: UID 999")


def test_eine_beantwortete_mail_mit_faehnchen_bleibt_liegen():
    """Abnahme aus #478; die Gegenprobe ohne Fähnchen steht darunter."""
    attrappe, _ = _postfach(eingang=[_mit_fahnen(_eingegangen(), "\\Seen \\Flagged")],
                            gesendet=[_antwort()])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert bericht.grund is None and bericht.zuege == () and bericht.verschoben == 0
    assert not attrappe.befehle("UID MOVE") and _uids(attrappe) == [101]
    ((zug, grund),) = bericht.liegen
    assert (zug.uid, grund) == ("101", "Fähnchen")


def test_gegenprobe_ohne_faehnchen_wandert_die_beantwortete_mail():
    attrappe, _ = _postfach(eingang=[_mit_fahnen(_eingegangen(), "\\Seen")],
                            gesendet=[_antwort()])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert bericht.verschoben == 1 and bericht.liegen == ()
    assert _uids(attrappe, "Archiv") == [101]


def test_die_ausgabe_sagt_liegt_faehnchen_in_text_und_json():
    _, sitzung = _postfach(eingang=[_mit_fahnen(_eingegangen(), "\\Flagged")],
                           gesendet=[_antwort()])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    text = ablage.zeilen(bericht)
    assert text[0].startswith("OK  joe@example.org: 1 von 1 Antworten seit ")
    assert ", 1 davon bleiben liegen → „Archiv“" in text[0]
    assert any(z.startswith("    UID 101 ") and z.endswith("„Angebot S1“ — liegt, Fähnchen")
               for z in text), text
    (liegt,) = ablage.als_json(bericht)["liegen"]
    assert (liegt["uid"], liegt["grund"]) == ("101", "Fähnchen")


def test_nennt_der_server_keine_flags_bleibt_die_mail_liegen():
    """Unbekannt ist nicht „nicht gesetzt“: Im Zweifel bleibt die Mail im Eingang."""
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()], ohne_flags=True)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert bericht.verschoben == 0 and not attrappe.befehle("UID MOVE")
    ((_, grund),) = bericht.liegen
    assert grund.startswith("Fähnchen unbekannt")


@pytest.mark.parametrize("hinten", [False, True], ids=["vor-dem-literal", "hinter-dem-literal"])
def test_die_flags_werden_vor_und_hinter_dem_literal_gelesen(hinten):
    """RFC 3501 legt die Reihenfolge der FETCH-Teile nicht fest. Steht `FLAGS`
    hinter dem Literal, liefert `imaplib` es als eigenes Element danach."""
    _, sitzung = _postfach(eingang=[_mit_fahnen(_eingegangen(), "\\Seen \\Flagged")],
                           flags_hinten=hinten)
    with sitzung:
        (kopf,) = sitzung.koepfe("INBOX")
    assert kopf.fahnen == ("\\seen", "\\flagged")
    assert kopf.ankunft == HEUTE - timedelta(days=5)


@pytest.mark.parametrize("trotz, erwartet", [(False, []), (True, [101])],
                         ids=["ohne-schalter", "trotz-faehnchen"])
def test_eine_benannte_mail_mit_faehnchen_wandert_nur_mit_dem_schalter(trotz, erwartet):
    attrappe, _ = _postfach(eingang=[_mit_fahnen(_offen(), "\\Flagged")])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101"], trotz_faehnchen=trotz)
    assert bericht.grund is None
    assert _uids(attrappe, "Archiv") == erwartet


_ALT_478 = datetime(2025, 12, 10, 12, 0, tzinfo=timezone.utc)
_NEU_478 = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def _jahr_lage(ordner=("Archiv/2025", "Archiv/2026"), *, antworten=True):
    """Zwei beantwortete Mails, eine von 2025, eine von 2026."""
    eingang = [(nachricht(an="joe@example.org", von="kunde@example.org", betreff=betreff,
                          datum=zeit, kennung=kennung), zeit)
               for betreff, kennung, zeit in (("Alt", "<alt@example.org>", _ALT_478),
                                              ("Neu", "<neu@example.org>", _NEU_478))]
    gesendet = [_antwort("<alt@example.org>", tage=2), _antwort("<neu@example.org>", tage=1)]
    return dict(eingang=eingang, gesendet=gesendet if antworten else (),
                sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                        **{name: "" for name in ordner}})


def test_jahr_im_ziel_legt_jede_mail_in_das_jahr_ihrer_ankunft():
    attrappe, _ = _postfach(**_jahr_lage())
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={})
    assert bericht.grund is None and bericht.verschoben == 2
    assert [b[1:] for b in attrappe.befehle("UID MOVE")] == [
        ("101", '"Archiv/2025"'), ("102", '"Archiv/2026"')]
    assert _uids(attrappe, "Archiv/2025") == [101] and _uids(attrappe, "Archiv/2026") == [102]
    assert ablage.als_json(bericht)["ablage"] == "Archiv/{jahr}"
    assert any(z.endswith("→ „Archiv/2025“") for z in ablage.zeilen(bericht))


def test_fehlt_ein_jahresordner_wandert_keine_mail_des_laufs():
    """Abnahme aus #478: Fehlt `Archiv/2025`, geht auch die Mail von 2026 nicht."""
    attrappe, _ = _postfach(**_jahr_lage(ordner=("Archiv/2026",)))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={})
    assert "„Archiv/2025“" in bericht.grund and "gibt es im Postfach nicht" in bericht.grund
    assert "keine Mail dieses Laufs wandert" in bericht.grund
    assert not attrappe.befehle("UID MOVE")
    assert _uids(attrappe) == [101, 102] and _uids(attrappe, "Archiv/2026") == []
    assert "Archiv/2025" not in attrappe.ordner, "der Ordner wurde angelegt"


def test_jahr_gilt_auch_fuer_benannte_mails():
    attrappe, _ = _postfach(**_jahr_lage(antworten=False))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={}, uids=["101"])
    assert bericht.verschoben == 1
    assert [b[1:] for b in attrappe.befehle("UID MOVE")] == [("101", '"Archiv/2025"')]


def test_ohne_ankunftsdatum_bleibt_die_mail_bei_jahr_liegen(monkeypatch):
    """Das Jahr kommt aus INTERNALDATE, nicht aus `Date`: Fehlt es, bleibt die Mail."""
    monkeypatch.setattr(postfach, "_ankunft", lambda meta: None)
    attrappe, _ = _postfach(**_jahr_lage(antworten=False))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={}, uids=["101"])
    assert bericht.grund is None and bericht.verschoben == 0
    assert not attrappe.befehle("UID MOVE")
    ((zug, grund),) = bericht.liegen
    assert zug.uid == "101" and grund == "ohne Ankunftsdatum, das Jahr für „Archiv/{jahr}“ fehlt"


def test_uid_verlangt_genau_ein_konto(capsys):
    """Dieselbe UID ist in zwei Postfächern zwei fremde Mails."""
    from falzmarke import cli as falzmarke

    assert falzmarke.main(["aufraeumen", "--absender", "a@example.org", "--absender",
                           "b@example.org", "--uid", "101"]) == falzmarke.EXIT_EINGABE
    assert "--uid" in capsys.readouterr().err


def test_uid_und_entwuerfe_schliessen_sich_aus(capsys):
    from falzmarke import cli as falzmarke

    assert falzmarke.main(["aufraeumen", "--absender", "a@example.org", "--entwuerfe",
                           "--uid", "101"]) == falzmarke.EXIT_EINGABE
    assert "--entwuerfe" in capsys.readouterr().err


def test_gegenprobe_uid_mit_einem_konto_verschiebt_ueber_die_cli(monkeypatch, capsys):
    """Ohne sie belegten die beiden Tests darüber nichts: Eine Sperre, die jedes
    `--uid` abweist, wäre dort auch grün."""
    from falzmarke import cli as falzmarke

    attrappe, _ = _postfach(eingang=[_offen()],
                            sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                    "Archiv": "\\Archive"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--uid", "101",
                           "--machen"]) == falzmarke.EXIT_OK
    assert "1 nach „Archiv“ verschoben" in capsys.readouterr().out
    assert _uids(attrappe, "Archiv") == [101]


# ── Das Profilfeld `email.ablage` ───────────────────────────────────────────

def _profilbefunde(ablage_wert) -> set[str]:
    from falzmarke import lint

    bericht = lint.Bericht()
    lint.pruefe_email_ablage({"absender": "joe@example.org", "ablage": ablage_wert}, bericht)
    return {b.regel for b in bericht.befunde}


def test_ein_leeres_feld_meldet():
    """`ablage: ""` soll melden, nicht stillschweigend „verschiebe nichts“
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


def test_ein_abgebrochener_bericht_steht_ganz_auf_stderr(monkeypatch, capsys):
    """Die Plan- und UID-Zeilen gehören zu ihrem Grund (Review von #459).

    Bis dahin ging nur `NICHT GEPRÜFT` auf stderr, die UIDs darunter auf
    stdout. Mit `2>/dev/null` blieben sie ohne Konto und ohne Grund stehen.
    """
    from falzmarke import cli as falzmarke

    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()],
                            sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                    "Archiv": "\\Archive"},
                            faehigkeiten=("IMAP4REV1",))
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org",
                           "--machen"]) == falzmarke.EXIT_UMGEBUNG
    ausgabe = capsys.readouterr()
    assert ausgabe.out == "", f"auf stdout gelandet: {ausgabe.out!r}"
    assert ausgabe.err.startswith("NICHT GEPRÜFT  joe@example.org") and "UID " in ausgabe.err


def test_ein_fenster_unter_einem_tag_ist_ein_eingabefehler(capsys):
    """`--seit 0` fragt nach Antworten aus der Zukunft. Exit 1, vor dem Postfach.

    Die Reihenfolge ist Teil der Aussage: Schlüge die Grenze erst nach der
    Anmeldung zu, nähme der Lauf erst eine Verbindung auf.
    """
    from falzmarke import cli as falzmarke

    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--seit", "0"]) \
        == falzmarke.EXIT_EINGABE
    assert "--seit" in capsys.readouterr().err


def test_ein_fenster_ueber_zehn_jahren_ist_ein_eingabefehler(capsys):
    """`--seit 9999999` passierte die Untergrenze und starb in der
    Datumsrechnung: `OverflowError: date value out of range` (#438)."""
    from falzmarke import cli as falzmarke

    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org",
                           "--seit", "9999999"]) == falzmarke.EXIT_EINGABE
    assert "--seit" in capsys.readouterr().err


def test_gegenprobe_zehn_jahre_passieren_die_eingabepruefung(monkeypatch, capsys):
    """Ohne sie wäre eine Obergrenze, die alles ablehnt, auch grün. `--seit
    3650` kommt bis zum Postfach und scheitert dort an etwas anderem."""
    from falzmarke import cli as falzmarke

    attrappe, _ = _postfach(sonder={"INBOX": "", "Archiv": "\\Archive"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org",
                           "--seit", "3650"]) == falzmarke.EXIT_UMGEBUNG
    assert "NICHT GEPRÜFT" in capsys.readouterr().err


def test_zwei_profile_mit_verschiedener_ablage_sind_ein_grund(tmp_path, monkeypatch, capsys):
    """Dasselbe Konto, zwei Profile, verschiedenes `email.ablage`. Der Hinweis
    sagte „keines wird genommen“ — genommen wurde `\\Archive`, und mit
    `--machen` wanderte die Post dorthin. Unter `--json` stand das auf keinem
    Kanal (#438).
    """
    import json

    from falzmarke import cli as falzmarke

    for name, ziel in (("eins", "Archiv/A"), ("zwei", "Archiv/B")):
        (tmp_path / f"{name}.yaml").write_text(
            f"email:\n  absender: joe@example.org\n  ablage: {ziel}\n", encoding="utf-8")
    attrappe = ImapAttrappe(
        {"INBOX": [_eingegangen()], "Gesendete Elemente": [_antwort()]},
        sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": "\\Archive"},
        verschieben_erlaubt=True)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    code = falzmarke.main(["aufraeumen", "--absender", "joe@example.org",
                           "--profiles", str(tmp_path), "--machen", "--json"])
    (eintrag,) = json.loads(capsys.readouterr().out)
    assert code == falzmarke.EXIT_UMGEBUNG
    assert eintrag["grund"] and "email.ablage" in eintrag["grund"], \
        "der Grund fehlt in --json"
    assert eintrag["ablage"] is None and eintrag["verschoben"] == 0
    assert attrappe.verbindungen == [], "ohne Ziel wird kein Postfach geöffnet"
    assert len(attrappe.ordner["INBOX"]) == 1


def test_gegenprobe_ein_profil_allein_nennt_sein_ziel(tmp_path, monkeypatch, capsys):
    """Ohne sie belegte der Test darüber nichts: Ein Grund, der bei jedem
    `--profiles` käme, sagte über die Mehrdeutigkeit nichts."""
    from falzmarke import cli as falzmarke

    (tmp_path / "eins.yaml").write_text(
        "email:\n  absender: joe@example.org\n  ablage: Archiv\n", encoding="utf-8")
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org",
                           "--profiles", str(tmp_path)]) == falzmarke.EXIT_OK
    assert "Archiv" in capsys.readouterr().out


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
    baut es nicht aus COPY, STORE und EXPUNGE nach“ ist kein Befehl.
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
