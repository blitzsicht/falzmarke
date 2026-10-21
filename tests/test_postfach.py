"""Der Zugang zum Postfach über den IMAP-Proxy (ADR 0051).

Kein Test hier öffnet eine Verbindung: `postfach.IMAP_KLASSE` wird durch die
Attrappe aus `imap_attrappe.py` ersetzt, die wie `imaplib.IMAP4` antwortet.
Geprüft wird die echte Klasse `Postfach` — und dass sie nur liest, außer beim
Ablegen eines Entwurfs: Die Attrappe wirft bei jedem Befehl, der etwas ändern
oder `\\Seen` setzen würde.
"""

from __future__ import annotations

import imaplib
from datetime import date, datetime, timedelta, timezone

import pytest

from falzmarke import postfach
from imap_attrappe import ImapAttrappe, nachricht

JETZT = datetime(2026, 10, 21, 18, 40, tzinfo=timezone.utc)


@pytest.fixture
def server(monkeypatch):
    attrappe = ImapAttrappe({"Gesendete Elemente": [
        (nachricht(betreff="Erste", datum=JETZT - timedelta(hours=1)), JETZT - timedelta(hours=1)),
        (nachricht(betreff="Alt", datum=JETZT - timedelta(days=3)), JETZT - timedelta(days=3)),
    ]})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    return attrappe


# ── modified UTF-7 (RFC 3501, 5.1.3) ────────────────────────────────────────

@pytest.mark.parametrize("klar, kodiert", [
    ("Entwürfe", "Entw&APw-rfe"),
    ("Gesendete Elemente", "Gesendete Elemente"),
    ("A&B", "A&-B"),
    ("[Google Mail]/Entwürfe", "[Google Mail]/Entw&APw-rfe"),
    ("Größe", "Gr&APYA3w-e"),
])
def test_ordnernamen_hin_und_zurueck(klar, kodiert):
    assert postfach.utf7_kodieren(klar) == kodiert
    assert postfach.utf7_dekodieren(kodiert) == klar


def test_ordner_aus_der_thunderbird_adresse():
    url = "imap://joe%40example.org@outlook.office365.com/Entw&APw-rfe"
    assert postfach.ordner_aus_url(url) == ("joe@example.org", "Entw&APw-rfe")
    url = "imap://joe%40example.org@outlook.office365.com/Gesendete Elemente"
    assert postfach.ordner_aus_url(url) == ("joe@example.org", "Gesendete Elemente")


def test_ein_ordner_mit_umlaut_im_klartext_wird_kodiert():
    """So steht es für Gmail in prefs.js: dekodiert, nicht als modified UTF-7."""
    url = "imap://ich%40gmail.com@imap.gmail.com/[Google Mail]/Entwürfe"
    assert postfach.ordner_aus_url(url) == ("ich@gmail.com", "[Google Mail]/Entw&APw-rfe")


@pytest.mark.parametrize("url", ["", "mailbox:///Users/x/Drafts", "imap://host"])
def test_ohne_imap_ordner_keine_angabe(url):
    assert postfach.ordner_aus_url(url) is None


# ── Ziel ────────────────────────────────────────────────────────────────────

def test_das_ziel_ist_der_proxy_ohne_angabe():
    assert postfach.ziel({}) == ("127.0.0.1", 1993)


def test_das_ziel_laesst_sich_setzen():
    assert postfach.ziel({"FALZMARKE_GESENDET_IMAP": "localhost:2993"}) == ("localhost", 2993)


def test_ein_kaputtes_ziel_ist_ein_grund_kein_absturz():
    with pytest.raises(postfach.PostfachFehler, match="FALZMARKE_GESENDET_IMAP"):
        postfach.ziel({"FALZMARKE_GESENDET_IMAP": "localhost"})


# ── Verbinden ───────────────────────────────────────────────────────────────

def test_anmeldung_mit_der_absenderadresse_ohne_tls(server):
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        assert pf.adresse == "joe@example.org"
    assert server.verbindungen == [("127.0.0.1", 1993, postfach.FRIST_S)]
    assert server.angemeldet == [("joe@example.org", postfach.KENNWORT)]
    assert server.abgemeldet == 1


def test_kein_proxy_ist_ein_grund(monkeypatch):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=ConnectionRefusedError(61, "refused")))
    with pytest.raises(postfach.PostfachFehler, match="127.0.0.1:1993") as fehler:
        postfach.verbinde("joe@example.org", umgebung={})
    assert "abgelehnt" in str(fehler.value)


def test_zeitueberschreitung_ist_ein_grund(monkeypatch):
    monkeypatch.setattr(postfach, "IMAP_KLASSE",
                        ImapAttrappe(verbindungsfehler=TimeoutError("timed out")))
    with pytest.raises(postfach.PostfachFehler, match="5 s"):
        postfach.verbinde("joe@example.org", umgebung={})


def test_eine_abgelehnte_anmeldung_nennt_die_meldung(monkeypatch):
    """So antwortet der Proxy auf ein Konto, das er nicht kennt (Gmail)."""
    attrappe = ImapAttrappe(login_fehler="No config file entry found for account ich@gmail.com")
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    with pytest.raises(postfach.PostfachFehler, match="No config file entry"):
        postfach.verbinde("ich@gmail.com", umgebung={})
    assert attrappe.abgemeldet == 1, "die halbe Sitzung bleibt offen"


# ── Lesen ───────────────────────────────────────────────────────────────────

def test_sonderordner_aus_list(server):
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        assert pf.sonderordner("\\Sent") == "Gesendete Elemente"
        assert pf.sonderordner("\\Drafts") == "Entw&APw-rfe"
        assert pf.sonderordner("\\Junk") is None


def test_koepfe_seit_einem_tag_nur_lesend(server):
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        koepfe = pf.koepfe("Gesendete Elemente", seit=date(2026, 10, 20))
    assert [k.betreff for k in koepfe] == ["Erste"]
    kopf = koepfe[0]
    assert kopf.an == ("nico@example.org",)
    assert kopf.datum == JETZT - timedelta(hours=1)
    assert server.befehle("EXAMINE") and not server.befehle("SELECT")
    (suche,) = server.befehle("UID SEARCH")
    assert suche[1:] == ("SINCE", "20-Oct-2026")


def test_ohne_seit_alle(server):
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        assert len(pf.koepfe("Gesendete Elemente")) == 2


def test_die_nachricht_kommt_byte_gleich(server):
    roh = server.ordner["Gesendete Elemente"][0].roh
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        uid = pf.koepfe("Gesendete Elemente")[0].uid
        assert pf.nachricht("Gesendete Elemente", uid) == roh


def test_ein_fehlender_ordner_ist_ein_grund(server):
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        with pytest.raises(postfach.PostfachFehler, match="Gibtsnicht"):
            pf.koepfe("Gibtsnicht")


def test_kopf_liest_fassung_und_bezug():
    roh = nachricht(kopf={"In-Reply-To": "<a@b>", "X-Falzmarke-Fassung": "0123456789ab",
                          "Cc": "Erika <erika@example.org>"})
    kopf = postfach.kopf_aus(roh, "7", None)
    assert kopf.fassung == "0123456789ab"
    assert kopf.antwort_auf == "<a@b>"
    assert kopf.an == ("nico@example.org", "erika@example.org")


def test_ohne_date_zaehlt_die_ankunft():
    roh = b"To: a@example.org\r\nSubject: x\r\n\r\n"
    ankunft = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    assert postfach.kopf_aus(roh, "1", ankunft).datum == ankunft


# ── Ablegen: der einzige schreibende Befehl ────────────────────────────────

def test_ablegen_als_entwurf_mit_draft_und_seen(server):
    roh = nachricht(betreff="Neu")
    with postfach.verbinde("joe@example.org", umgebung={}, frist=30) as pf:
        pf.ablegen("Entw&APw-rfe", roh)
    (append,) = server.befehle("APPEND")
    assert append[1] == "Entw&APw-rfe" and append[2] == "(\\Draft \\Seen)"
    assert server.ordner["Entw&APw-rfe"][-1].roh == roh


def test_ein_abgelehntes_ablegen_ist_ein_grund(server):
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        with pytest.raises(postfach.PostfachFehler, match="APPEND"):
            pf.ablegen("Gibtsnicht", b"x")


def test_gegenprobe_die_attrappe_wirft_bei_aendernden_befehlen():
    """Ohne sie belegte die Readonly-Prüfung oben nichts: Eine Attrappe, die
    jeden Befehl schluckt, wäre auch bei einem STORE grün."""
    attrappe = ImapAttrappe()
    for name in ("store", "expunge", "copy", "move", "delete"):
        with pytest.raises(AssertionError, match="verboten"):
            getattr(attrappe, name)("1", "x")
    with pytest.raises(AssertionError, match="readonly"):
        attrappe.select("INBOX")
    attrappe.select("INBOX", readonly=True)
    with pytest.raises(AssertionError, match="PEEK"):
        attrappe.uid("FETCH", "1", "(BODY[])")


def test_das_modul_kennt_keinen_aendernden_befehl():
    """Die Quelle selbst: kein STORE, EXPUNGE, COPY, MOVE, DELETE — und kein
    smtplib. Gelesen wird der Syntaxbaum, nicht die Doku."""
    import ast
    from pathlib import Path

    quelle = Path(postfach.__file__).read_text(encoding="utf-8")
    # Jeder Attributzugriff, nicht nur Aufrufe: `postfach` reicht die Methode
    # der Verbindung weiter (`self._v.select`), statt sie dort aufzurufen.
    zugriffe = {k.attr for k in ast.walk(ast.parse(quelle)) if isinstance(k, ast.Attribute)}
    assert not zugriffe & {"store", "expunge", "copy", "move", "delete", "rename", "send",
                           "sendmail", "send_message"}, zugriffe
    assert {"append", "select", "uid", "login"} <= zugriffe, "die Prüfung sieht die Zugriffe nicht"
    # Importe über den Baum, nicht als Text: Der Modulkopf erklärt, warum
    # `smtplib` und `subprocess` fehlen, und nennt sie dabei beim Namen.
    importe = set()
    for knoten in ast.walk(ast.parse(quelle)):
        if isinstance(knoten, ast.Import):
            importe |= {a.name.split(".")[0] for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom):
            importe.add((knoten.module or "").split(".")[0])
    assert "imaplib" in importe, importe
    assert not importe & {"smtplib", "subprocess", "socket"}, importe


def test_imaplib_fehler_werden_zum_grund(server, monkeypatch):
    def kaputt(*_a, **_k):
        raise imaplib.IMAP4.abort("socket error: EOF")
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        monkeypatch.setattr(server, "uid", kaputt)
        with pytest.raises(postfach.PostfachFehler, match="EOF"):
            pf.koepfe("Gesendete Elemente")
