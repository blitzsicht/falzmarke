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
        assert sitzung.suchkappungen == [("INBOX", "123", 4, 3)], \
            "die Teiltreffer wurden nicht gekappt"
        assert sitzung.gekappt == {}, f"Suchkappung als Ordnerkappung: {sitzung.gekappt}"
    _, sitzung = _postfach(eingang=fremde[:3])                       # Gegenstück: unter der Grenze
    with sitzung:
        assert sitzung.suche_kennung("INBOX", "123") == [] and sitzung.suchkappungen == []


def test_eine_gekappte_suche_meldet_die_kennung_nicht_den_ordner(monkeypatch):
    """Nachreview von #492, Befund 1: Die Suchkappung hieß „„INBOX“: nur die
    neuesten 3 von 4 Mails angesehen“, obwohl der Eingang nicht gekappt war."""
    monkeypatch.setattr(postfach, "SUCHGRENZE", 3)
    fremde = [_eingegangen(f"<x123y{i}@example.org>", betreff=f"fremd {i}", tage=4 - i)
              for i in range(4)]
    _, sitzung = _postfach(eingang=fremde, gesendet=[_antwort("123")])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert not [h for h in bericht.hinweise if "Mails angesehen" in h], \
        f"Suchkappung als Ordnerkappung gemeldet: {bericht.hinweise}"
    assert ("Kennung „123“ in „INBOX“: nur 3 von 4 Teiltreffern verglichen, die neuesten — "
            "eine ältere Nachricht mit dieser Kennung fehlt womöglich im Abgleich"
            in bericht.hinweise), f"Suchkappung ohne Hinweis: {bericht.hinweise}"


def test_eine_gekappte_suche_steht_nur_einmal_im_bericht(monkeypatch):
    """#515, Befund 2 (aus den Reviews von #496 und #497): Beantworten drei Antworten
    dieselbe gekappte Kennung, stand derselbe Satz dreimal unter den Hinweisen."""
    monkeypatch.setattr(postfach, "SUCHGRENZE", 3)
    fremde = [_eingegangen(f"<x123y{i}@example.org>", betreff=f"fremd {i}", tage=4 - i)
              for i in range(4)]
    antworten = [_antwort("123", tage=t) for t in (1, 2, 3)]
    _, sitzung = _postfach(eingang=fremde, gesendet=antworten)
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    saetze = [h for h in bericht.hinweise if h.startswith("Kennung „123“ in „INBOX“")]
    assert len(saetze) == 1, f"Suchkappung {len(saetze)}-mal gemeldet: {bericht.hinweise}"


def test_eine_zweite_gekappte_kennung_bekommt_ihren_eigenen_satz(monkeypatch):
    """Gegenstück zu oben: Nur dieselbe Kennung im selben Ordner fällt zusammen.
    Eine Sperre, die jede weitere Kappung schluckte, bestünde den Test darüber auch."""
    monkeypatch.setattr(postfach, "SUCHGRENZE", 3)
    fremde = [_eingegangen(f"<x{k}y{i}@example.org>", betreff=f"fremd {k} {i}", tage=4 - i)
              for k in ("123", "456") for i in range(4)]
    _, sitzung = _postfach(eingang=fremde,
                           gesendet=[_antwort("123", tage=1), _antwort("456", tage=2)])
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    for kennung in ("123", "456"):
        saetze = [h for h in bericht.hinweise if h.startswith(f"Kennung „{kennung}“ in „INBOX“")]
        assert len(saetze) == 1, f"{kennung}: {len(saetze)}-mal gemeldet: {bericht.hinweise}"


def _suchen_zaehlen(monkeypatch, sitzung):
    """Jeder Aufruf von `suche_kennung` an dieser Sitzung, mit der Kennung. Die
    echte Suche läuft weiter; gezählt wird mit, nicht über eine Ausnahme."""
    aufrufe = []
    echt = sitzung.suche_kennung

    def zaehlend(ordner, kennung):
        aufrufe.append(kennung)
        return echt(ordner, kennung)

    monkeypatch.setattr(sitzung, "suche_kennung", zaehlend)
    return aufrufe


def test_drei_antworten_auf_eine_kennung_suchen_einmal(monkeypatch):
    """#522, Befund 3: Bis dahin liefen Suche und Abruf je Antwort, nicht je Kennung.
    Alle drei Antworten finden die Nachricht trotzdem, die jüngste steht im Zug."""
    _, sitzung = _postfach(eingang=[_eingegangen()],
                           gesendet=[_antwort(tage=t) for t in (1, 2, 3)])
    with sitzung:
        aufrufe = _suchen_zaehlen(monkeypatch, sitzung)
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert len(aufrufe) == 1, f"{len(aufrufe)} Suchen für eine Kennung: {aufrufe}"
    assert bericht.antworten == 3 and bericht.nicht_im_eingang == 0
    (zug,) = bericht.zuege
    assert zug.antwort_datum == HEUTE - timedelta(days=1)


def test_eine_kennung_mit_und_ohne_klammern_sucht_einmal(monkeypatch):
    """#522, Punkt 11: `<abc@x>` und `abc@x` sind für `gleiche_kennung` eine
    Message-ID. Roh geschlüsselt kosteten sie zwei Suchen und zwei Kappungssätze."""
    ohne_klammern = QUELLE[1:-1]
    _, sitzung = _postfach(eingang=[_eingegangen()],
                           gesendet=[_antwort(QUELLE, tage=1), _antwort(ohne_klammern, tage=2)])
    with sitzung:
        aufrufe = _suchen_zaehlen(monkeypatch, sitzung)
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert len(aufrufe) == 1, f"{len(aufrufe)} Suchen für eine Message-ID: {aufrufe}"
    assert bericht.nicht_im_eingang == 0 and len(bericht.zuege) == 1


@pytest.mark.parametrize("zuerst_mit_klammern", [True, False], ids=["mit-zuerst", "ohne-zuerst"])
def test_eine_kopfzeile_ohne_klammern_findet_sich_in_jeder_reihenfolge(
        monkeypatch, zuerst_mit_klammern):
    """Nachreview von #524, Befund 1: Geschlüsselt wurde ohne Klammern, gesucht mit
    der Form der ersten Antwort. Trägt die Nachricht im Eingang `abc@x` und nennt
    die erste Antwort `<abc@x>`, findet die Teilkettensuche nichts, und die zweite
    Antwort mit `abc@x` bekam dieses leere Ergebnis. Vor #524 fand sie die Mail.
    Beide Reihenfolgen, weil der Fehler nur in einer auftrat."""
    ohne_klammern = QUELLE[1:-1]
    formen = [QUELLE, ohne_klammern] if zuerst_mit_klammern else [ohne_klammern, QUELLE]
    _, sitzung = _postfach(eingang=[_eingegangen(ohne_klammern)],
                           gesendet=[_antwort(formen[0], tage=1), _antwort(formen[1], tage=2)])
    with sitzung:
        aufrufe = _suchen_zaehlen(monkeypatch, sitzung)
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert len(bericht.zuege) == 1, (
        f"Kopfzeile ohne Klammern nicht gefunden, gesucht: {aufrufe}, "
        f"nicht im Eingang: {bericht.nicht_im_eingang}")
    assert bericht.nicht_im_eingang == 0 and len(aufrufe) == 1


def test_zwei_kennungen_suchen_zweimal(monkeypatch):
    """Gegenstück: Ein Schlüssel, der alle Kennungen zusammenwirft, bestünde die
    beiden Proben darüber auch."""
    zweite = "<kunde-2@example.org>"
    _, sitzung = _postfach(eingang=[_eingegangen(), _eingegangen(zweite, betreff="Angebot S2")],
                           gesendet=[_antwort(tage=1), _antwort(zweite, tage=2)])
    with sitzung:
        aufrufe = _suchen_zaehlen(monkeypatch, sitzung)
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    # Gesucht wird ohne Klammerpaar (Nachreview von #524, Befund 1).
    assert sorted(aufrufe) == sorted([QUELLE[1:-1], zweite[1:-1]]), f"gesucht: {aufrufe}"
    assert len(bericht.zuege) == 2, f"Züge: {bericht.zuege}"


def test_leere_klammern_suchen_nicht_nach_nichts(monkeypatch):
    """`<>` hat ohne Klammerpaar einen leeren Schlüssel. Die Teilkettensuche nach
    „“ träfe jede Mail im Eingang und liefe in `SUCHGRENZE`; gesucht wird dann `<>`."""
    _, sitzung = _postfach(eingang=[_eingegangen()], gesendet=[_antwort("<>", tage=1)])
    with sitzung:
        aufrufe = _suchen_zaehlen(monkeypatch, sitzung)
        bericht = ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())
    assert aufrufe == ["<>"], f"gesucht: {aufrufe}"
    assert not bericht.zuege


def test_eine_suche_ueberschreibt_die_kappung_des_ordners_nicht(monkeypatch):
    """Nachreview von #492, Befund 1, die zweite Folge: Die Suche schrieb unter
    demselben Ordnernamen und löschte eine echte Ordnerkappung aus dem Bericht."""
    monkeypatch.setattr(postfach, "GRENZE", 2)
    monkeypatch.setattr(postfach, "SUCHGRENZE", 3)
    fremde = [_eingegangen(f"<x123y{i}@example.org>", betreff=f"fremd {i}", tage=5 - i)
              for i in range(5)]
    _, sitzung = _postfach(eingang=fremde)
    with sitzung:
        sitzung.koepfe("INBOX")
        assert sitzung.gekappt == {"INBOX": (5, 2)}, "Kontrollprobe: der Ordner ist gekappt"
        sitzung.suche_kennung("INBOX", "123")
        assert sitzung.gekappt == {"INBOX": (5, 2)}, \
            f"die Suche überschrieb die Ordnerkappung: {sitzung.gekappt}"
        assert sitzung.suchkappungen == [("INBOX", "123", 5, 3)]


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
                                uidvalidity="1", uids=["101", "103"])
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
    # Der Folgebefehl trägt die UIDVALIDITY, unter der die UIDs eben galten (#495).
    assert "    nichts bewegt — mit --machen --uidvalidity 1 verschieben" in text


def test_fehlt_eine_genannte_uid_wandert_keine():
    """Eine Liste, die nicht mehr stimmt, ist kein Auftrag für den Rest."""
    attrappe, _ = _postfach(eingang=[_offen()])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uidvalidity="1", uids=["101", "999"])
    assert "UID 999 liegt nicht im Eingang" in bericht.grund
    assert bericht.verschoben == 0 and not attrappe.befehle("UID MOVE")
    assert _uids(attrappe) == [101]
    assert [z.uid for z in bericht.zuege] == ["101"], "die gefundene steht trotzdem da"
    assert ablage.zeilen(bericht)[0].startswith("NICHT GEPRÜFT  joe@example.org: UID 999")


# ── #495: Eine UID gilt nur mit der UIDVALIDITY des Eingangs ────────────────

def _neu_nummeriert(attrappe, uidvalidity="2"):
    """Der Server vergibt den Eingang neu: Unter UID 101 liegt jetzt eine fremde Mail."""
    from imap_attrappe import Eintrag

    roh, zeit = _offen("Fremde Mail", "<fremd@example.org>")
    attrappe.ordner["INBOX"] = [Eintrag(101, roh, zeit)]
    attrappe.uidvalidity = uidvalidity


def _nichts_bewegt(attrappe, bericht):
    assert not attrappe.befehle("UID MOVE"), f"UID MOVE gesendet: {attrappe.befehle('UID MOVE')}"
    assert bericht.verschoben == 0 and _uids(attrappe, "Archiv") == []


def test_wechselt_die_uidvalidity_nach_der_anzeige_wandert_keine():
    """Abnahme aus #495: Dieselbe Zahl meint nach dem Wechsel eine andere Mail."""
    attrappe, _ = _postfach(eingang=[_offen("Gemeinte Mail", "<gemeint@example.org>")])
    anzeige = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={}, uids=["101"])
    assert anzeige.uidvalidity == "1" and ablage.als_json(anzeige)["uidvalidity"] == "1"

    _neu_nummeriert(attrappe)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101"], uidvalidity=anzeige.uidvalidity)
    _nichts_bewegt(attrappe, bericht)
    assert "die UIDVALIDITY des Eingangs ist jetzt 2, die Anzeige nannte 1" in bericht.grund
    assert ablage.zeilen(bericht)[0].startswith("NICHT GEPRÜFT  joe@example.org: die UIDVALIDITY")
    assert not attrappe.befehle("SELECT"), "der Eingang wurde nicht einmal zum Schreiben gewählt"


def test_gegenprobe_gleiche_uidvalidity_laesst_die_genannte_mail_wandern():
    """Ohne sie belegte die Probe darüber nichts: Eine Sperre, die jedes
    `--uidvalidity` abweist, wäre dort auch grün."""
    attrappe, _ = _postfach(eingang=[_offen()])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101"], uidvalidity="1")
    assert bericht.grund is None and bericht.verschoben == 1
    assert _uids(attrappe, "Archiv") == [101]


def test_nennt_der_server_keine_uidvalidity_wandert_keine_benannte_mail():
    """Unbekannt ist nicht „gleich“: Ohne Wert ist nichts zu vergleichen."""
    attrappe, _ = _postfach(eingang=[_offen()], uidvalidity=None)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101"], uidvalidity="1")
    _nichts_bewegt(attrappe, bericht)
    assert "der Server nennt für den Eingang keine UIDVALIDITY" in bericht.grund
    assert bericht.uidvalidity is None and ablage.als_json(bericht)["uidvalidity"] is None


def test_ohne_uidvalidity_vom_server_sagt_die_anzeige_dass_uid_nicht_verschiebt():
    _, sitzung = _postfach(eingang=[_offen()], uidvalidity=None)
    with sitzung:
        bericht = ablage.plane_benannt(sitzung, ["101"], wunsch="Archiv")
    assert any("keine UIDVALIDITY, mit --uid lässt sich deshalb nicht verschieben" in z
               for z in ablage.zeilen(bericht))


@pytest.mark.parametrize("benannt", [True, False], ids=["uid", "beantwortet"])
def test_wechselt_die_uidvalidity_zwischen_plan_und_select_geht_kein_move_hinaus(benannt):
    """Der Wechsel mitten im Lauf, zwischen dem EXAMINE des Plans und dem
    SELECT vor dem Zug. Gilt auch ohne `--uid`: Dort tragen die Züge ebenso
    nur UIDs."""
    if benannt:
        attrappe, _ = _postfach(eingang=[_offen()], uidvalidity_select="2")
        optionen = {"uids": ["101"], "uidvalidity": "1"}
    else:
        attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()],
                                uidvalidity_select="2")
        optionen = {}
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                **optionen)
    _nichts_bewegt(attrappe, bericht)
    assert attrappe.befehle("SELECT"), "der Lauf kam bis zum SELECT"
    assert "ist jetzt 2, der Plan dieses Laufs las 1" in bericht.grund
    assert not bericht.zug_gesendet


def test_ohne_uidvalidity_im_plan_geht_kein_move_hinaus():
    """Nachreview #502, Befund 1: Nennt der Server beim EXAMINE keinen Wert, ging
    `UID MOVE` ungeprüft hinaus, auch ohne `--uid`. Jetzt nicht einmal das SELECT.
    Zwilling: Mit Wert wandert dieselbe beantwortete Mail."""
    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()], uidvalidity=None)
    anzeige = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={})
    assert anzeige.zuege and anzeige.uidvalidity is None
    assert "auch mit --machen wird deshalb nicht verschoben" in ablage.zeilen(anzeige)[-1]
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    _nichts_bewegt(attrappe, bericht)
    assert "der Plan dieses Laufs las für den Eingang keine UIDVALIDITY" in bericht.grund
    assert not attrappe.befehle("SELECT"), "der Eingang wurde zum Schreiben gewählt"

    attrappe, _ = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
    anzeige = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={})
    assert ablage.zeilen(anzeige)[-1] == "    nichts bewegt — mit --machen verschieben"
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    assert bericht.grund is None and bericht.verschoben == 1


def test_mit_uids_und_machen_verlangt_auch_die_funktion_die_uidvalidity():
    """Nachreview #502, Befund 2: Die Pflicht stand nur in `cli.py`. Ein direkter
    Aufrufer ohne Wert verglich die neue Nummerierung mit sich selbst, und die fremde
    Mail wanderte. Zwilling: `test_gegenprobe_gleiche_uidvalidity_laesst_…` darüber."""
    attrappe, _ = _postfach(eingang=[_offen("Gemeinte Mail", "<gemeint@example.org>")])
    _neu_nummeriert(attrappe)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101"])
    _nichts_bewegt(attrappe, bericht)
    assert bericht.grund.startswith("mit UIDs und machen fehlt die UIDVALIDITY"), bericht.grund
    assert not attrappe.befehle("EXAMINE"), "das Postfach wurde trotzdem gelesen"


def test_nach_einem_wechsel_zeigt_der_bericht_die_fremde_mail_nicht():
    """Nachreview #502, Befund 3: Unter „1 Nachricht gefunden“ stand die Mail der neuen
    Nummerierung, als wäre sie die genannte. Zwilling: Ohne Wechsel steht die
    gemeinte Mail in der Anzeige."""
    attrappe, _ = _postfach(eingang=[_offen("Gemeinte Mail", "<gemeint@example.org>")])
    anzeige = ablage.raeume_auf("joe@example.org", wunsch="Archiv", umgebung={}, uids=["101"])
    assert any("„Gemeinte Mail“" in z for z in ablage.zeilen(anzeige))
    _neu_nummeriert(attrappe)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uids=["101"], uidvalidity="1")
    assert bericht.zuege == () and bericht.liegen == ()
    text = "\n".join(ablage.zeilen(bericht))
    assert "Fremde Mail" not in text and "gefunden" not in text, text


def test_wechselt_die_uidvalidity_vor_der_zweiten_jahresgruppe_stimmt_der_satz():
    """Nachreview #502, Befund 4: Die erste Gruppe ist gewandert, am SELECT der
    zweiten weicht der Wert ab. Der Grund sagte „verschoben wird nichts“, die Zeile
    darunter „1 davon verschoben“."""
    attrappe, _ = _postfach(**_jahr_lage())
    echt = attrappe.uid

    def uid(befehl, *args):
        antwort = echt(befehl, *args)
        if befehl == "MOVE":
            attrappe.uidvalidity_select = "2"
        return antwort

    attrappe.uid = uid
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={})
    assert bericht.verschoben == 1 and len(attrappe.befehle("UID MOVE")) == 1
    assert "ist jetzt 2, der Plan dieses Laufs las 1" in bericht.grund
    assert "kein weiterer Zug geht hinaus" in bericht.grund
    assert "verschoben wird nichts" not in bericht.grund, bericht.grund
    assert any("1 davon verschoben, der Rest nicht" in z for z in ablage.zeilen(bericht))


def test_fehlt_ein_jahresordner_steht_er_neben_der_liegenden_benannten_mail():
    """Review von #496, Befund 1: Bis dahin ersetzte der Grund „bliebe liegen“
    den Grund zum fehlenden Jahresordner, und der Bediener erfuhr erst im
    nächsten Lauf, nach `--trotz-faehnchen`, davon."""
    alt = datetime(2025, 12, 10, 12, 0, tzinfo=timezone.utc)
    attrappe, _ = _postfach(
        eingang=[_mit_fahnen(_offen("Mit Fähnchen", "<f@example.org>"), "\\Flagged"),
                 (nachricht(an="joe@example.org", betreff="Von 2025", datum=alt,
                            kennung="<alt@example.org>"), alt)],
        sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv/2026": ""})
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={}, uids=["101", "102"], uidvalidity="1")
    assert not attrappe.befehle("UID MOVE") and bericht.verschoben == 0
    assert "UID 101 bliebe liegen (Fähnchen)" in bericht.grund
    assert "„Archiv/2025“" in bericht.grund, f"Jahresordner fehlt im Grund: {bericht.grund}"


def test_mit_trotz_faehnchen_raet_der_grund_nicht_zu_trotz_faehnchen(monkeypatch):
    """Review von #496, Befund 2: Eine Mail mit Fähnchen, die ohne Ankunft
    liegen bleibt, bekam den Rat, einen Schalter zu setzen, der schon gesetzt war."""
    monkeypatch.setattr(postfach, "_ankunft", lambda *teile: None)
    attrappe, _ = _postfach(eingang=[_mit_fahnen(_offen(), "\\Flagged")],
                            sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                    "Archiv/2026": ""})
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={}, uids=["101"], uidvalidity="1",
                                trotz_faehnchen=True)
    assert not attrappe.befehle("UID MOVE") and bericht.verschoben == 0
    assert "UID 101 bliebe liegen (ohne Ankunftsdatum" in bericht.grund
    assert "--trotz-faehnchen" not in bericht.grund, f"Rat trotz Schalter: {bericht.grund}"


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
                                uidvalidity="1", uids=["101"], trotz_faehnchen=trotz)
    # Ohne Schalter hält das Fähnchen den Lauf an (Nachreview von #494, Befund 5).
    assert (bericht.grund is None) is trotz
    assert _uids(attrappe, "Archiv") == erwartet


def test_bliebe_eine_benannte_mail_liegen_wandert_keine():
    """Nachreview von #494, Befund 5: Eine benannte Mail mit Fähnchen zählt wie
    eine fehlende UID. Bis dahin wanderte der Rest, und der Lauf endete grün."""
    attrappe, _ = _postfach(eingang=[_offen("Erste", "<e1@example.org>"),
                                     _mit_fahnen(_offen("Zweite", "<e2@example.org>"),
                                                 "\\Seen \\Flagged")])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uidvalidity="1", uids=["101", "102"])
    # #504, Befund 1: Der Rat nennt die UIDVALIDITY, sonst endet der Befehl auf Exit 1.
    assert bericht.grund.startswith("UID 102 bliebe liegen (Fähnchen) — verschoben wird nur, "
                                    "wenn jede genannte UID wandern kann; ")
    rat = bericht.grund.rsplit("; ", 1)[-1]
    assert "--trotz-faehnchen" in rat and "--uidvalidity 1" in rat, rat
    assert rat.endswith("hebt das Fähnchen für diesen Lauf auf"), rat
    assert bericht.verschoben == 0 and not attrappe.befehle("UID MOVE")
    assert _uids(attrappe) == [101, 102]
    text = ablage.zeilen(bericht)
    assert text[0].startswith("NICHT GEPRÜFT  joe@example.org: UID 102 bliebe liegen")
    assert any(z.startswith("    UID 101 ") for z in text), "die wandernde fehlt im Text"
    assert any(z.startswith("    UID 102 ") and z.endswith("— liegt, Fähnchen") for z in text)


def test_gegenprobe_ohne_faehnchen_wandern_beide_benannten_mails():
    """Ohne sie belegte der Test darüber nichts: Eine Sperre, die jedes `--uid`
    mit zwei Mails anhält, wäre dort auch grün."""
    attrappe, _ = _postfach(eingang=[_offen("Erste", "<e1@example.org>"),
                                     _mit_fahnen(_offen("Zweite", "<e2@example.org>"), "\\Seen")])
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uidvalidity="1", uids=["101", "102"])
    assert bericht.grund is None and bericht.verschoben == 2
    assert _uids(attrappe, "Archiv") == [101, 102]


def test_unbekannte_flags_an_einer_benannten_mail_halten_den_lauf_an():
    attrappe, _ = _postfach(eingang=[_offen()], ohne_flags=True)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uidvalidity="1", uids=["101"])
    assert "UID 101 bliebe liegen (Fähnchen unbekannt" in bericht.grund
    assert "--trotz-faehnchen" in bericht.grund
    assert bericht.verschoben == 0 and not attrappe.befehle("UID MOVE")


def test_eine_benannte_mail_mit_faehnchen_endet_ueber_die_cli_mit_exit_3(monkeypatch, capsys):
    from falzmarke import cli as falzmarke

    attrappe, _ = _postfach(eingang=[_mit_fahnen(_offen(), "\\Flagged")],
                            sonder={"INBOX": "", "Gesendete Elemente": "\\Sent",
                                    "Archiv": "\\Archive"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--uid", "101",
                           "--uidvalidity", "1", "--machen"]) == falzmarke.EXIT_UMGEBUNG
    fehler = capsys.readouterr().err
    assert fehler.startswith("NICHT GEPRÜFT  joe@example.org: UID 101 bliebe liegen")
    assert "--trotz-faehnchen" in fehler
    assert _uids(attrappe) == [101] and not attrappe.befehle("UID MOVE")


@pytest.mark.parametrize("hinten", [False, True], ids=["vor-dem-literal", "hinter-dem-literal"])
def test_uid_und_ankunft_werden_vor_und_hinter_dem_literal_gelesen(hinten):
    """Nachreview von #494, Befund 2: wie `FLAGS`. Bis dahin las nur die
    Kopfzeile der Antwort, und eine Mail mit `UID` hinter dem Literal fiel
    stumm aus der Liste."""
    _, sitzung = _postfach(eingang=[_eingegangen()], uid_hinten=hinten)
    with sitzung:
        (kopf,) = sitzung.koepfe("INBOX")
    assert kopf.uid == "101"
    assert kopf.ankunft == HEUTE - timedelta(days=5)


@pytest.mark.parametrize("hinten", ["uid", "ankunft"], ids=["nur-uid-hinten", "nur-ankunft-hinten"])
def test_uid_und_ankunft_werden_je_fuer_sich_hinter_dem_literal_gelesen(hinten):
    """#501, Befund 9: `postfach._uid` und `_ankunft` suchen je für sich. Die
    Attrappe verschob beide immer gemeinsam; der Fall „eines davor, eines
    dahinter“ wurde nie gelesen."""
    _, sitzung = _postfach(eingang=[_eingegangen()], uid_hinten=hinten)
    with sitzung:
        koepfe = sitzung.koepfe("INBOX")
    assert [k.uid for k in koepfe] == ["101"], f"UIDs gelesen: {[k.uid for k in koepfe]}"
    assert koepfe[0].ankunft == HEUTE - timedelta(days=5), f"Ankunft gelesen: {koepfe[0].ankunft}"


def test_steht_die_uid_hinter_dem_literal_findet_uid_die_mail():
    attrappe, _ = _postfach(eingang=[_offen()], uid_hinten=True)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={},
                                uidvalidity="1", uids=["101"])
    assert bericht.grund is None and bericht.verschoben == 1
    assert _uids(attrappe, "Archiv") == [101]


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


def test_mit_jahr_zeigt_der_zug_den_gefundenen_ordner():
    """Nachreview von #527, Befund 3: Ist der Jahresordner auf dem Server gefunden,
    kommt der angezeigte Name aus ihm, nicht aus `_lesbar(name)`. „R&Dev-Team“
    ist ein dokumentierter Fehlfall von `_lesbar` und erschien so verstümmelt."""
    _, sitzung = _postfach(**_jahr_lage(ordner=("R&-Dev-Team/2025", "R&-Dev-Team/2026")))
    with sitzung:
        bericht = ablage.plane(sitzung, wunsch="R&Dev-Team/{jahr}", heute=HEUTE.date())
    assert bericht.grund is None
    assert [(z.ziel, z.ziel_server) for z in bericht.zuege] == [
        ("R&Dev-Team/2025", "R&-Dev-Team/2025"), ("R&Dev-Team/2026", "R&-Dev-Team/2026")], \
        f"angezeigt: {[z.ziel for z in bericht.zuege]}"


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
                                umgebung={}, uidvalidity="1", uids=["101"])
    assert bericht.verschoben == 1
    assert [b[1:] for b in attrappe.befehle("UID MOVE")] == [("101", '"Archiv/2025"')]


def test_ohne_ankunftsdatum_bleibt_die_mail_bei_jahr_liegen(monkeypatch):
    """Das Jahr kommt aus INTERNALDATE, nicht aus `Date`: Fehlt es, bleibt die Mail.

    Benannt hält sie seit dem Nachreview von #494 den Lauf an; der Hinweis auf
    `--trotz-faehnchen` fehlt, denn der hilft hier nicht.
    """
    monkeypatch.setattr(postfach, "_ankunft", lambda *teile: None)
    attrappe, _ = _postfach(**_jahr_lage(antworten=False))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={}, uidvalidity="1", uids=["101"])
    assert bericht.grund.startswith("UID 101 bliebe liegen (ohne Ankunftsdatum")
    assert "--trotz-faehnchen" not in bericht.grund
    assert bericht.verschoben == 0
    assert not attrappe.befehle("UID MOVE")
    ((zug, grund),) = bericht.liegen
    assert zug.uid == "101" and grund == "ohne Ankunftsdatum, das Jahr für „Archiv/{jahr}“ fehlt"


@pytest.mark.parametrize("name", [
    # Zwischen `&` und `-` stehen 1, 2 oder 4 Base64-Zeichen: kein ganzes UTF-16.
    "R&D-Projekte", "F&E-Archiv", "AT&T-Rechnungen", "Q&A-Ablage", "R&De-Team",
    "R&Devs-Team",
    # Ohne `-` nach dem `&` greift die Dekodierung nie. Diese drei können nicht
    # rot werden; sie stehen für die häufigste Schreibweise und bleiben (#522/2).
    "Kunden & Co", "A&B", "Müller&Söhne"])
def test_ein_lesbarer_name_mit_und_zeichen_bleibt_wie_er_ist(name):
    """#515, Befund 4: Übliche Namen mit `&` sind kein gültiges UTF-7 oder dekodieren
    auf sich selbst. Wann still verändert wird, steht im Docstring von `_lesbar`."""
    assert ablage._lesbar(name) == name


def test_die_bekannte_grenze_von_lesbar():
    """Hält die Grenze aus dem Docstring fest: Ändert sich das Verhalten, muss auch
    die Begründung der Streichung von #515, Befund 4 neu gelesen werden.

    „R&Dev-Team“ und „B&Bau-Rechnungen“ sind dokumentierte Fehlfälle (#522,
    Punkt 1): lesbar gemeint, als UTF-7 gelesen. Drei Buchstaben reichen."""
    # Ausgeschrieben, weil U+0DEB und das kombinierende U+05AB im Quelltext unlesbar sind.
    for name, gelesen in (("R&Dev-Team", "R\u0debTeam"),
                          ("B&Bau-Rechnungen", "B\u05abRechnungen"),
                          # Elf Zeichen: n = 3, 6, 8, 11 … (Nachreview von #527, Befund 7).
                          ("A&Projektakte-B", "A\u3eba\u237a\u4b5a\u92d7B"),
                          ("Kunden &-Co", "Kunden &Co"), ("Gesch&AOQ-ft", "Geschäft")):
        assert ablage._lesbar(name) == gelesen, \
            f"Grenze verschoben: {name!r} → {ablage._lesbar(name)!r}"


def test_jahr_in_server_schreibweise_steht_lesbar_in_text_und_json():
    """Nachreview von #494, Befund 8: Ohne `{jahr}` wurde das Ziel schon
    dekodiert, mit `{jahr}` stand `&AOQ-` in der Ausgabe."""
    lage = _jahr_lage(ordner=("Gesch&AOQ-ft/2025", "Gesch&AOQ-ft/2026"))
    attrappe, _ = _postfach(**lage)
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Gesch&AOQ-ft/{jahr}", machen=True,
                                umgebung={})
    assert bericht.grund is None and bericht.verschoben == 2
    assert _uids(attrappe, "Gesch&AOQ-ft/2025") == [101]
    daten = ablage.als_json(bericht)
    assert daten["ablage"] == "Geschäft/{jahr}", f"Ablage im JSON: {daten['ablage']}"
    ziele = [z["ziel"] for z in daten["zuege"]]
    assert ziele == ["Geschäft/2025", "Geschäft/2026"], f"Ziele im JSON: {ziele}"
    assert any(z.endswith("→ „Geschäft/2025“") for z in ablage.zeilen(bericht))


def _zweiter_jahreszug_bricht_ab(monkeypatch, attrappe, *, am):
    """Der erste Jahreszug geht durch, der zweite bricht `am` SELECT oder MOVE ab."""
    echtes_select, echtes_uid = attrappe.select, attrappe.uid
    zuege = []

    def select(mailbox="INBOX", readonly=False):
        if not readonly:
            zuege.append(mailbox)
            if am == "SELECT" and len(zuege) == 2:
                return "NO", [b"Mailbox busy."]
        return echtes_select(mailbox, readonly=readonly)

    def uid(befehl, *args):
        if am == "MOVE" and befehl.upper() == "MOVE" and len(zuege) == 2:
            attrappe.protokoll.append(("UID MOVE", *args))
            raise OSError("Verbindung getrennt")
        return echtes_uid(befehl, *args)

    monkeypatch.setattr(attrappe, "select", select)
    monkeypatch.setattr(attrappe, "uid", uid)


def test_bricht_der_zweite_jahreszug_vor_seinem_move_ab_ist_fuer_den_rest_nichts_gesendet(
        monkeypatch):
    """Nachreview von #494, Befund 3: Bis dahin galt `verschoben > 0` als
    „gesendet“, und der Text nannte den Stand des Rests ungeprüft, obwohl für
    ihn nie ein MOVE hinausging."""
    attrappe, _ = _postfach(**_jahr_lage())
    _zweiter_jahreszug_bricht_ab(monkeypatch, attrappe, am="SELECT")
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={})
    assert "Mailbox busy" in bericht.grund and bericht.verschoben == 1
    assert bericht.zug_gesendet is False, "zug_gesendet ohne gesendetes MOVE für den Rest"
    assert ablage.als_json(bericht)["zug_gesendet"] is False
    assert [b[1:] for b in attrappe.befehle("UID MOVE")] == [("101", '"Archiv/2025"')]
    stand = ablage.zeilen(bericht)[1]
    assert stand == ("    2 Nachrichten für „Archiv/{jahr}“ gefunden; "
                     "1 davon verschoben, der Rest nicht, weil der Lauf "
                     "vor seinem Zug abbrach"), f"Stand im Text: {stand}"


def test_bricht_der_zweite_jahreszug_im_move_ab_bleibt_der_rest_offen(monkeypatch):
    """Gegenstück: Hier ging das MOVE des Rests hinaus, nur hier ist sein Stand offen."""
    attrappe, _ = _postfach(**_jahr_lage())
    _zweiter_jahreszug_bricht_ab(monkeypatch, attrappe, am="MOVE")
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Archiv/{jahr}", machen=True,
                                umgebung={})
    assert "Verbindung getrennt" in bericht.grund and bericht.verschoben == 1
    assert bericht.zug_gesendet is True
    assert ablage.zeilen(bericht)[1] == ("    2 Nachrichten für „Archiv/{jahr}“ gefunden; "
                                         "1 davon verschoben, ob der Server vom Rest schon "
                                         "etwas bewegt hat, ist nicht geprüft")


def test_uid_verlangt_genau_ein_konto(capsys):
    """Dieselbe UID ist in zwei Postfächern zwei fremde Mails."""
    from falzmarke import cli as falzmarke

    assert falzmarke.main(["aufraeumen", "--absender", "a@example.org", "--absender",
                           "b@example.org", "--uid", "101"]) == falzmarke.EXIT_EINGABE
    assert "--uid" in capsys.readouterr().err


def test_uid_mit_machen_verlangt_uidvalidity(monkeypatch, capsys):
    """#495: Ohne den Wert der Anzeige ist nicht zu prüfen, ob die UIDs noch
    dieselben Mails meinen. Abgewiesen wird, bevor ein Postfach aufgeht."""
    from falzmarke import cli as falzmarke

    attrappe, _ = _postfach(eingang=[_offen()])
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    attrappe.verbindungen.clear()
    code = falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--uid", "101",
                           "--machen"])
    fehler = capsys.readouterr().err
    assert fehler.startswith("FEHLER  --uid mit --machen braucht --uidvalidity"), \
        f"--uid --machen ohne --uidvalidity nicht abgewiesen: Exit {code}, {fehler}"
    assert code == falzmarke.EXIT_EINGABE
    assert not attrappe.verbindungen and _uids(attrappe) == [101]


@pytest.mark.parametrize("argumente,anfang", [
    (["--uidvalidity", "1"], "FEHLER  --uidvalidity gilt nur mit --uid"),
    (["--uid", "101", "--uidvalidity", "0"], "FEHLER  --uidvalidity braucht eine Zahl ab 1"),
], ids=["ohne-uid", "null"])
def test_uidvalidity_ohne_uid_oder_unter_eins_wird_abgewiesen(argumente, anfang, capsys):
    from falzmarke import cli as falzmarke

    code = falzmarke.main(["aufraeumen", "--absender", "a@example.org", *argumente])
    assert capsys.readouterr().err.startswith(anfang)
    assert code == falzmarke.EXIT_EINGABE


def test_wechselt_die_uidvalidity_endet_die_cli_mit_exit_3(monkeypatch, capsys):
    from falzmarke import cli as falzmarke

    attrappe, _ = _postfach(eingang=[_offen()], sonder={
        "INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": "\\Archive"})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    assert falzmarke.main(["aufraeumen", "--absender", "joe@example.org", "--uid", "101",
                           "--uidvalidity", "7", "--machen"]) == falzmarke.EXIT_UMGEBUNG
    fehler = capsys.readouterr().err
    assert "UIDVALIDITY des Eingangs ist jetzt 1, die Anzeige nannte 7" in fehler
    assert not attrappe.befehle("UID MOVE")


@pytest.mark.parametrize("seit", ["30", "0"], ids=["gueltig", "ausserhalb"])
def test_uid_und_seit_schliessen_sich_aus(seit, capsys):
    """Nachreview von #494, Befund 6: Mit `--uid` gibt es kein Fenster. Ein
    gesetztes `--seit` wurde still übergangen, und `--seit 0` scheiterte an
    einer Grenze, die gar nicht galt."""
    from falzmarke import cli as falzmarke

    code = falzmarke.main(["aufraeumen", "--absender", "a@example.org", "--uid", "101",
                           "--seit", seit])
    fehler = capsys.readouterr().err
    assert fehler.startswith("FEHLER  --seit gilt nicht mit --uid"), \
        f"--seit {seit} mit --uid nicht abgewiesen: Exit {code}, {fehler}"
    assert code == falzmarke.EXIT_EINGABE


def test_ohne_seit_gilt_die_vorgabe_und_seit_null_bleibt_ein_fehler(monkeypatch, capsys):
    """Gegenprobe zu `default=None`: Ohne `--uid` kommen weiter 30 Tage an,
    und die Grenze greift wie vorher."""
    from falzmarke import cli as falzmarke

    angekommen = []
    monkeypatch.setattr(ablage, "raeume_auf", lambda adresse, **kw: angekommen.append(
        kw["seit_tagen"]) or ablage.Bericht(
            adresse=adresse, ziel="Archiv", grund="Attrappe", seit=None, antworten=0,
            nicht_im_eingang=0, zuege=(), verschoben=0))
    monkeypatch.setattr(falzmarke, "ablage_aus_profil", lambda adresse, zusatz: ("Archiv", None))
    falzmarke.main(["aufraeumen", "--absender", "a@example.org"])
    assert angekommen == [ablage.SEIT_TAGEN]
    assert falzmarke.main(["aufraeumen", "--absender", "a@example.org", "--seit", "0"]) \
        == falzmarke.EXIT_EINGABE
    assert "--seit braucht 1 bis" in capsys.readouterr().err


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
                           "--uidvalidity", "1", "--machen"]) == falzmarke.EXIT_OK
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


# ── `aufraeumen --alle`: die Konten kommen aus den Profilen (#541) ──────────
#
# Drei Konten, drei Attrappen: Der Lauf öffnet sie in der Reihenfolge der
# Adressen (alphabetisch), `_konten` reicht sie in dieser Reihenfolge herein.

def _jetzt_eingang(kennung, betreff="Angebot S1"):
    from datetime import datetime, timedelta, timezone

    jetzt = datetime.now(timezone.utc)
    return (nachricht(an="a@example.de", von="kunde@example.de", betreff=betreff,
                      datum=jetzt - timedelta(days=5), kennung=kennung),
            jetzt - timedelta(days=5))


def _jetzt_antwort(auf):
    from datetime import datetime, timedelta, timezone

    zeit = datetime.now(timezone.utc) - timedelta(days=1)
    return (nachricht(an="kunde@example.de", betreff="AW: Angebot S1", datum=zeit,
                      kennung="<eigene-1@example.de>", kopf={"In-Reply-To": auf}), zeit)


def _konto(*, kennung, ordner=("Archiv",), verschieben=True):
    """Ein Konto mit einer beantworteten Mail im Eingang."""
    sonder = {"INBOX": "", "Gesendete Elemente": "\\Sent", **{o: "" for o in ordner}}
    return ImapAttrappe({"INBOX": [_jetzt_eingang(kennung)],
                         "Gesendete Elemente": [_jetzt_antwort(kennung)]},
                        sonder=sonder, verschieben_erlaubt=verschieben)


def _profile(verzeichnis, monkeypatch, **konten):
    """`name=(absender, ablage)`; `ablage=None` lässt die Zeile weg.

    Der Suchweg der Profile reicht bis in `~/.config` des Rechners, auf dem der
    Test läuft: Ohne diese Einengung liefe `--alle` über die echten Konten des
    Betreibers. Hier sieht es nur `verzeichnis`.
    """
    from falzmarke import cli as falzmarke

    monkeypatch.setattr(falzmarke, "profil_verzeichnisse", lambda *a, **kw: [verzeichnis])
    for name, (absender, ablage_wert) in konten.items():
        zeile = f"  ablage: {ablage_wert}\n" if ablage_wert else ""
        (verzeichnis / f"{name}.yaml").write_text(
            f"email:\n  absender: {absender}\n{zeile}", encoding="utf-8")


def _konten(monkeypatch, *attrappen):
    """Reicht die Attrappen nacheinander als Verbindung herein."""
    rest = list(attrappen)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", lambda *a, **kw: rest.pop(0)(*a, **kw))
    return rest


def test_alle_prueft_zwei_konten_und_nennt_das_dritte_als_uebersprungen(
        monkeypatch, tmp_path, capsys):
    """Abnahme 1 (#541): drei Profile, eines ohne `ablage` — zwei Konten werden
    geprüft, das dritte steht als übersprungen da und ist kein Fehler. Es wird
    auch kein Postfach dafür geöffnet: Die Attrappen sind nur zwei."""
    import json

    from falzmarke import cli as falzmarke

    _profile(tmp_path, monkeypatch, eins=("a@example.de", "Archiv"), zwei=("b@example.de", "Archiv"),
             drei=("c@example.de", None))
    a, b = _konto(kennung="<a@example.de>"), _konto(kennung="<b@example.de>")
    rest = _konten(monkeypatch, a, b)
    code = falzmarke.main(["aufraeumen", "--alle", "--profiles", str(tmp_path), "--json"])
    bericht = json.loads(capsys.readouterr().out)
    assert code == falzmarke.EXIT_OK and rest == []
    assert [k["absender"] for k in bericht["konten"]] == ["a@example.de", "b@example.de"]
    assert [len(k["zuege"]) for k in bericht["konten"]] == [1, 1]
    assert bericht["uebersprungen"] == ["c@example.de"] and bericht["nicht_geprueft"] == 0
    assert not any(k["grund"] for k in bericht["konten"])


def test_alle_nennt_uebersprungene_im_text_nicht_als_nicht_geprueft(
        monkeypatch, tmp_path, capsys):
    from falzmarke import cli as falzmarke

    _profile(tmp_path, monkeypatch, eins=("a@example.de", "Archiv"), drei=("c@example.de", None))
    _konten(monkeypatch, _konto(kennung="<a@example.de>"))
    code = falzmarke.main(["aufraeumen", "--alle", "--profiles", str(tmp_path)])
    ausgabe = capsys.readouterr()
    assert code == falzmarke.EXIT_OK
    assert "ÜBERSPRUNGEN  c@example.de" in ausgabe.out
    assert "NICHT GEPRÜFT" not in ausgabe.out + ausgabe.err


def test_alle_ein_konto_ohne_jahresordner_haelt_die_anderen_nicht_an(
        monkeypatch, tmp_path, capsys):
    """Abnahme 2 (#541): Das erste Konto meldet `NICHT GEPRÜFT` (kein Jahresordner),
    das zweite verschiebt trotzdem, der Exit-Code ist 3."""
    import json

    from falzmarke import cli as falzmarke

    _profile(tmp_path, monkeypatch, eins=("a@example.de", "Archiv/{jahr}"), zwei=("b@example.de", "Archiv"))
    kaputt = _konto(kennung="<a@example.de>", ordner=("Archiv/1999",))
    heil = _konto(kennung="<b@example.de>")
    _konten(monkeypatch, kaputt, heil)
    code = falzmarke.main(["aufraeumen", "--alle", "--machen", "--json",
                           "--profiles", str(tmp_path)])
    bericht = json.loads(capsys.readouterr().out)
    assert code == falzmarke.EXIT_UMGEBUNG
    assert bericht["nicht_geprueft"] == 1
    assert "Jahresordner" in (bericht["konten"][0]["grund"] or ""), bericht["konten"][0]["grund"]
    assert bericht["konten"][1]["grund"] is None and bericht["konten"][1]["verschoben"] == 1
    assert len(kaputt.ordner["INBOX"]) == 1 and not kaputt.befehle("UID MOVE")
    assert len(heil.ordner["INBOX"]) == 0 and len(heil.ordner["Archiv"]) == 1


def test_alle_ohne_machen_bewegt_nichts(monkeypatch, tmp_path, capsys):
    """Abnahme 3 (#541): Beide Attrappen verbieten jedes Verschieben. Der Lauf
    ist nur grün, wenn er es nicht einmal versucht."""
    from falzmarke import cli as falzmarke

    _profile(tmp_path, monkeypatch, eins=("a@example.de", "Archiv"), zwei=("b@example.de", "Archiv"))
    a = _konto(kennung="<a@example.de>", verschieben=False)
    b = _konto(kennung="<b@example.de>", verschieben=False)
    _konten(monkeypatch, a, b)
    code = falzmarke.main(["aufraeumen", "--alle", "--profiles", str(tmp_path)])
    assert code == falzmarke.EXIT_OK
    assert len(a.ordner["INBOX"]) == 1 and len(b.ordner["INBOX"]) == 1
    assert "nichts bewegt" in capsys.readouterr().out


def test_alle_zwei_profile_mit_verschiedener_ablage_sind_ein_grund(
        monkeypatch, tmp_path, capsys):
    """Abnahme 4 (#541): Wie bei `--absender` (#438) — für diese Adresse ein
    Grund, kein Rückfall auf `\\Archive`, kein Postfach geöffnet; das andere
    Konto läuft weiter."""
    import json

    from falzmarke import cli as falzmarke

    _profile(tmp_path, monkeypatch, eins=("a@example.de", "Archiv/A"), zwei=("a@example.de", "Archiv/B"),
             drei=("b@example.de", "Archiv"))
    heil = _konto(kennung="<b@example.de>")
    rest = _konten(monkeypatch, heil)
    code = falzmarke.main(["aufraeumen", "--alle", "--machen", "--json",
                           "--profiles", str(tmp_path)])
    bericht = json.loads(capsys.readouterr().out)
    assert code == falzmarke.EXIT_UMGEBUNG and rest == []
    assert "verschiedene `email.ablage`" in bericht["konten"][0]["grund"]
    assert bericht["konten"][1]["verschoben"] == 1


def test_alle_ohne_ein_einziges_konto_ist_nicht_gruen(monkeypatch, tmp_path, capsys):
    """Ein Zeitplan, der nichts prüft, meldet Exit 3 statt 0."""
    from falzmarke import cli as falzmarke

    _profile(tmp_path, monkeypatch, drei=("c@example.de", None))
    code = falzmarke.main(["aufraeumen", "--alle", "--profiles", str(tmp_path)])
    assert code == falzmarke.EXIT_UMGEBUNG
    assert capsys.readouterr().err.startswith("NICHT GEPRÜFT  kein Profil nennt")


@pytest.mark.parametrize("zusatz", [
    ["--absender", "a@example.de"], ["--uid", "101"], ["--entwuerfe"],
    ["--uidvalidity", "3"], ["--trotz-faehnchen"],
], ids=["absender", "uid", "entwuerfe", "uidvalidity", "trotz-faehnchen"])
def test_alle_ist_mit_einzelkonto_schaltern_unvereinbar(zusatz, monkeypatch, tmp_path, capsys):
    from falzmarke import cli as falzmarke

    _profile(tmp_path, monkeypatch, eins=("a@example.de", "Archiv"))
    attrappe = _konto(kennung="<a@example.de>")
    _konten(monkeypatch, attrappe)
    code = falzmarke.main(["aufraeumen", "--alle", "--profiles", str(tmp_path), *zusatz])
    assert code == falzmarke.EXIT_EINGABE
    assert capsys.readouterr().err.startswith(f"FEHLER  --alle gilt nicht mit {zusatz[0]}")
    assert not attrappe.verbindungen


def test_aufraeumen_braucht_absender_oder_alle(capsys):
    from falzmarke import cli as falzmarke

    assert falzmarke.main(["aufraeumen"]) == falzmarke.EXIT_EINGABE
    assert "--absender ADRESSE oder --alle" in capsys.readouterr().err


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


# ── #501: Aufräumbefunde aus den Reviews von #496 und #497 ──────────────────

def _entwurfsablage_tage(monkeypatch, argumente):
    """Mit welchen `tage` kommt `aufraeumen` bei `entwurfsablage.raeume_auf` an?"""
    from falzmarke import cli as falzmarke
    from falzmarke import entwurfsablage, entwurfsbuch

    angekommen = []

    def lauf(adresse, *, tage=entwurfsbuch.TAGE_VORGABE, **_k):
        angekommen.append(tage)
        return entwurfsablage.Bericht(adresse)

    monkeypatch.setattr(entwurfsablage, "raeume_auf", lauf)
    falzmarke.main(["aufraeumen", "--absender", "a@example.org", *argumente])
    return angekommen


def test_mit_entwuerfe_gelten_ohne_seit_vierzehn_tage(monkeypatch):
    """#501, Befund 1: Bis dahin kamen auch hier 30 an, weil `--seit` vor der
    `--entwuerfe`-Weiche auf die Vorgabe des Eingangs gesetzt wurde."""
    from falzmarke import entwurfsbuch

    assert entwurfsbuch.TAGE_VORGABE == 14
    angekommen = _entwurfsablage_tage(monkeypatch, ["--entwuerfe"])
    assert angekommen == [14], f"Tage bei --entwuerfe: {angekommen}"


def test_ein_gesetztes_seit_gilt_in_beiden_modi(monkeypatch):
    """Gegenprobe zu Befund 1: `--seit 7` darf weder von 14 noch von 30 überdeckt werden."""
    angekommen = _entwurfsablage_tage(monkeypatch, ["--entwuerfe", "--seit", "7"])
    assert angekommen == [7], f"Tage bei --entwuerfe --seit 7: {angekommen}"


def test_die_hilfe_nennt_beide_vorgaben(capsys):
    """#501, Befund 1: Die Hilfe sagte für beide Modi „Vorgabe 30 Tage“."""
    from falzmarke import cli as falzmarke

    with pytest.raises(SystemExit):
        falzmarke.main(["aufraeumen", "--help"])
    hilfe = " ".join(capsys.readouterr().out.split())
    assert "Vorgabe 30" in hilfe, f"Hilfe ohne die 30 des Eingangs: {hilfe}"
    assert "Vorgabe 14" in hilfe, f"Hilfe ohne die 14 der Entwürfe: {hilfe}"


def test_fehlt_der_jahresordner_nennt_der_grund_den_lesbaren_namen():
    """#501, Befund 3: Bei `{jahr}` stand im Grund der Wunsch in Server-
    Schreibweise (`Gesch&AOQ-ft/2025`), während `ziel` den lesbaren Namen zeigte."""
    _postfach(**_jahr_lage(ordner=("Gesch&AOQ-ft/2026",)))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Gesch&AOQ-ft/{jahr}", machen=True,
                                umgebung={})
    assert bericht.verschoben == 0 and bericht.grund
    assert "„Geschäft/2025“" in bericht.grund, f"Lesbarer Name fehlt im Grund: {bericht.grund}"
    assert "&AOQ" not in bericht.grund, f"Roher Name im Grund: {bericht.grund}"


def test_ein_lesbarer_wunsch_mit_jahr_bleibt_im_grund_lesbar():
    """Gegenprobe zu Befund 3: Steht der Wunsch schon lesbar im Profil, ändert sich nichts."""
    _postfach(**_jahr_lage(ordner=("Gesch&AOQ-ft/2026",)))
    bericht = ablage.raeume_auf("joe@example.org", wunsch="Geschäft/{jahr}", machen=True,
                                umgebung={})
    assert bericht.verschoben == 0 and bericht.grund
    assert "„Geschäft/2025“" in bericht.grund, f"Lesbarer Name fehlt im Grund: {bericht.grund}"
