"""Das Fähnchen an der Ursprungsmail eines Antwortentwurfs (#549, ADR 0063).

Gegen die IMAP-Attrappe mit der **echten** Klasse `postfach.Postfach`. Die
Attrappe lässt `STORE` nur mit `markieren_erlaubt=True` zu und auch dann nur als
`<uid> +FLAGS (\\Flagged)`. Weil `faehnchen.setze` jeden Fehler fängt, auch den
`AssertionError` der Attrappe, prüft jede Probe hier das **Protokoll** der
Attrappe und nicht, ob etwas geworfen wurde.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from falzmarke import faehnchen, postfach

from imap_attrappe import ImapAttrappe, nachricht

URSPRUNG = "<frage-1@kunde.example>"
ADRESSE = "joe@example.org"
STORE_RICHTIG = ("UID STORE", "101", "+FLAGS", "(\\Flagged)")


def _eingang(*mails, **schalter) -> ImapAttrappe:
    """Eine Attrappe mit diesem Eingang; jede Mail `(kennung, flags)`. UIDs ab 101."""
    jetzt = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
    schalter.setdefault("markieren_erlaubt", True)
    return ImapAttrappe({"INBOX": [
        (nachricht(kennung=kennung, betreff=f"Frage {nummer}", von="kunde@kunde.example",
                   an=ADRESSE), jetzt, flags)
        for nummer, (kennung, flags) in enumerate(mails, 1)]}, **schalter)


@pytest.fixture
def server(monkeypatch):
    def setzen(attrappe):
        monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
        return attrappe
    return setzen


def _stores(attrappe) -> list[tuple]:
    return attrappe.befehle("UID STORE")


def _flags(attrappe, uid: int) -> str:
    return next(n.flags for n in attrappe.ordner["INBOX"] if n.uid == uid)


# ── Die vier Zustände ───────────────────────────────────────────────────────

def test_setzt_das_faehnchen_an_genau_der_ursprungsmail(server):
    attrappe = server(_eingang((URSPRUNG, "\\Seen"), ("<andere@kunde.example>", "")))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis == faehnchen.Faehnchen("gesetzt", uid="101", betreff="Frage 1")
    assert _stores(attrappe) == [STORE_RICHTIG]
    assert _flags(attrappe, 101) == "\\Seen \\Flagged"
    assert _flags(attrappe, 102) == "", "die andere Mail wurde angefasst"
    assert attrappe.abgemeldet == 1


def test_mit_erledigt_wird_nichts_gesetzt_und_nichts_geoeffnet(server):
    attrappe = server(_eingang((URSPRUNG, "")))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=True, umgebung={})
    assert ergebnis.zustand == "nicht_noetig"
    assert attrappe.verbindungen == [] and _stores(attrappe) == []


def test_ein_stehendes_faehnchen_bleibt_unberuehrt(server):
    attrappe = server(_eingang((URSPRUNG, "\\Flagged \\Seen")))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert _stores(attrappe) == [], "STORE an einem Fähnchen, das schon stand"
    assert ergebnis.zustand == "schon_da" and ergebnis.uid == "101"
    assert attrappe.befehle("SELECT") == []


def test_unbekannte_flags_werden_gesetzt_aber_nicht_als_nachgelesen_gemeldet(server):
    """Nennt der Server keine Flags, ist das Fähnchen unbekannt, nicht „fehlt“.
    `+FLAGS` ändert an einem stehenden nichts, also wird gesetzt."""
    attrappe = server(_eingang((URSPRUNG, ""), ohne_flags=True))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis.zustand == "gesetzt" and "nicht nachgelesen" in ergebnis.grund
    assert _stores(attrappe) == [STORE_RICHTIG]


# ── Nicht gesetzt, mit Grund ────────────────────────────────────────────────

def test_nicht_im_eingang_aendert_nichts(server):
    attrappe = server(_eingang(("<andere@kunde.example>", "")))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis.zustand == "nicht_gesetzt" and "nicht im Eingang" in ergebnis.grund
    assert _stores(attrappe) == [] and attrappe.befehle("SELECT") == []


def test_zwei_mails_mit_derselben_kennung_aendern_nichts(server):
    attrappe = server(_eingang((URSPRUNG, ""), (URSPRUNG, "")))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert _stores(attrappe) == [], "STORE, obwohl zwei Mails dieselbe Kennung tragen"
    assert ergebnis.zustand == "nicht_gesetzt" and "2 Mails" in ergebnis.grund
    assert "101, 102" in ergebnis.grund
    assert attrappe.befehle("SELECT") == []


def test_ein_teiltreffer_ist_nicht_die_ursprungsmail(server):
    """`SEARCH HEADER` sucht Teilketten; `<frage-1@…>` steckt in `<x-frage-1@…>`
    nicht, aber `frage-1@kunde.example` ohne Klammern schon (#442)."""
    attrappe = server(_eingang(("<x-frage-1@kunde.example>", "")))
    ergebnis = faehnchen.setze(ADRESSE, "frage-1@kunde.example", erledigt=False, umgebung={})
    assert _stores(attrappe) == []
    # Der Grund legt den Weg fest: abgewiesen hat der exakte Vergleich, nicht etwas davor.
    assert ergebnis.zustand == "nicht_gesetzt" and "nicht im Eingang" in ergebnis.grund


def test_ein_wechsel_der_uidvalidity_verhindert_das_setzen(server):
    attrappe = server(_eingang((URSPRUNG, ""), uidvalidity="7", uidvalidity_select="8"))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert _stores(attrappe) == [], "STORE trotz gewechselter UIDVALIDITY"
    assert ergebnis.zustand == "nicht_gesetzt" and "7 → 8" in ergebnis.grund


def test_ohne_uidvalidity_wird_nicht_gesetzt(server):
    attrappe = server(_eingang((URSPRUNG, ""), uidvalidity=None))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis.zustand == "nicht_gesetzt" and "UIDVALIDITY" in ergebnis.grund
    assert _stores(attrappe) == [] and attrappe.befehle("SELECT") == []


def test_ein_abgelehntes_store_ist_ein_grund_kein_abbruch(server):
    attrappe = server(_eingang((URSPRUNG, ""), store_fehler="Mailbox is read-only"))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis.zustand == "nicht_gesetzt" and "read-only" in ergebnis.grund
    assert attrappe.abgemeldet == 1


def test_ein_store_ohne_wirkung_wird_beim_nachlesen_entdeckt(server):
    """`OK` heißt angenommen, nicht gesetzt."""
    attrappe = server(_eingang((URSPRUNG, ""), store_wirkt=False))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis.zustand == "nicht_gesetzt", "ein STORE ohne Wirkung als gesetzt gemeldet"
    assert "kein Fähnchen" in ergebnis.grund
    assert _stores(attrappe) == [STORE_RICHTIG]


def test_kein_proxy_ist_ein_grund(server):
    server(ImapAttrappe({}, verbindungsfehler=ConnectionRefusedError("abgelehnt")))
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis.zustand == "nicht_gesetzt" and "kein IMAP-Proxy" in ergebnis.grund


def test_ein_umbruch_in_der_kennung_kommt_nie_auf_die_leitung(server):
    """Ein Umbruch begänne auf der Leitung einen zweiten Befehl (#442). Ohne
    spitze Klammern macht `postfach.kennungen` daraus eine Zeile, `_zitiert`
    setzt sie in Anführungszeichen — gesucht wird ein Wert, den es nicht gibt."""
    attrappe = server(_eingang((URSPRUNG, "")))
    ergebnis = faehnchen.setze(ADRESSE, "a@b\r\nA1 DELETE INBOX", erledigt=False, umgebung={})
    assert ergebnis.zustand == "nicht_gesetzt" and _stores(attrappe) == []
    assert not any("\r" in str(e) or "\n" in str(e) for e in attrappe.protokoll)
    assert attrappe.befehle("DELETE") == []


def test_eine_kennung_ausserhalb_von_ascii_wird_nicht_gesucht(server):
    attrappe = server(_eingang((URSPRUNG, "")))
    ergebnis = faehnchen.setze(ADRESSE, "<jörg@kunde.example>", erledigt=False, umgebung={})
    assert attrappe.verbindungen == [], "Verbindung für eine Kennung, die nicht sendbar ist"
    assert ergebnis.zustand == "nicht_gesetzt" and "ASCII" in ergebnis.grund


def test_ein_angehaengter_befehl_hinter_der_kennung_wird_nicht_gesendet(server):
    """Mit spitzen Klammern zählt nur die Kennung selbst; der Rest geht nirgends hin."""
    attrappe = server(_eingang((URSPRUNG, "")))
    ergebnis = faehnchen.setze(ADRESSE, f"{URSPRUNG}\r\nA1 DELETE INBOX", erledigt=False,
                               umgebung={})
    assert ergebnis.zustand == "gesetzt" and _stores(attrappe) == [STORE_RICHTIG]
    assert all("DELETE" not in str(eintrag) for eintrag in attrappe.protokoll)


def test_mehrere_kennungen_sind_mehrdeutig(server):
    attrappe = server(_eingang((URSPRUNG, "")))
    ergebnis = faehnchen.setze(ADRESSE, f"{URSPRUNG} <noch@eine>", erledigt=False, umgebung={})
    assert ergebnis.zustand == "nicht_gesetzt" and "2 Kennungen" in ergebnis.grund
    assert attrappe.verbindungen == []


def test_ein_unerwarteter_fehler_wird_zum_grund(server, monkeypatch):
    server(_eingang((URSPRUNG, "")))
    def kaputt(*_a, **_k):
        raise RuntimeError("unerwartet")
    monkeypatch.setattr(postfach.Postfach, "suche_kennung", kaputt)
    ergebnis = faehnchen.setze(ADRESSE, URSPRUNG, erledigt=False, umgebung={})
    assert ergebnis == faehnchen.Faehnchen("nicht_gesetzt", "RuntimeError: unerwartet")


# ── erledigt lesen ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("wert, erwartet", [
    ("ja", True), ("Ja ", True), (True, True),
    ("nein", False), (False, False), (None, False), ("jein", False), ("", False), (1, False),
])
def test_als_erledigt_zaehlt_nur_ein_eindeutiges_ja(wert, erwartet):
    assert faehnchen.ist_erledigt(wert) is erwartet


# ── Die Zeilen ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ergebnis, anfang", [
    (faehnchen.Faehnchen("gesetzt", uid="1", betreff="Frage"), "OK  Fähnchen gesetzt an „Frage“"),
    (faehnchen.Faehnchen("schon_da", uid="1", betreff="Frage"), "OK  Fähnchen stand schon"),
    (faehnchen.Faehnchen("nicht_noetig"), "HINWEIS  erledigt: ja — kein Fähnchen"),
    (faehnchen.Faehnchen("nicht_gesetzt", "weil"), "HINWEIS  Fähnchen nicht gesetzt: weil"),
], ids=["gesetzt", "schon_da", "nicht_noetig", "nicht_gesetzt"])
def test_jeder_zustand_hat_seine_eigene_zeile(ergebnis, anfang):
    assert faehnchen.zeile(ergebnis, ADRESSE).startswith(anfang)


def test_erledigt_verspricht_nicht_das_ablegen_eines_frueheren_faehnchens():
    """Nachreview #553: `erledigt: ja` sieht nicht nach. Ein früherer Entwurf
    ohne `erledigt` kann das Fähnchen gesetzt haben; die Zeile sagt, dass es bleibt."""
    zeile = faehnchen.zeile(faehnchen.Faehnchen("nicht_noetig"), ADRESSE)
    assert "früher gesetztes bleibt stehen" in zeile


# ── Die Attrappe selbst ─────────────────────────────────────────────────────

def test_gegenprobe_das_markieren_ist_einzeln_einzuschalten():
    """Ohne den Schalter wirft die Attrappe bei STORE und SELECT weiter. Sonst
    wäre er eine Hintertür für jeden anderen Test."""
    zu = ImapAttrappe()
    zu.select("INBOX", readonly=True)
    with pytest.raises(AssertionError, match="UID STORE"):
        zu.uid("STORE", "1", "+FLAGS", "(\\Flagged)")
    with pytest.raises(AssertionError, match="readonly"):
        zu.select("INBOX")

    offen = ImapAttrappe(markieren_erlaubt=True)
    offen.select('"INBOX"')
    assert offen.uid("STORE", "1", "+FLAGS", "(\\Flagged)")[0] == "OK"
    for falsch in (("1", "-FLAGS", "(\\Flagged)"), ("1", "+FLAGS", "(\\Deleted)"),
                   ("1", "FLAGS", "(\\Flagged)"), ("1,2", "+FLAGS", "(\\Flagged)"),
                   ("1", "+FLAGS", "(\\Flagged \\Seen)")):
        with pytest.raises(AssertionError, match="nur als"):
            offen.uid("STORE", *falsch)
    with pytest.raises(AssertionError, match="UID MOVE"):
        offen.uid("MOVE", "1", '"Archiv"')


# ── Die Quelle selbst ───────────────────────────────────────────────────────

def test_das_modul_kennt_genau_einen_aendernden_befehl():
    """`STORE` mit `+FLAGS` und `\\Flagged` — gelesen am Syntaxbaum, ohne Docstrings."""
    import ast
    from pathlib import Path

    from test_ablage import _befehlswoerter

    baum = ast.parse(Path(faehnchen.__file__).read_text(encoding="utf-8"))
    befehle = _befehlswoerter(baum)
    assert "STORE" in befehle, "die Prüfung sieht den ändernden Befehl nicht"
    assert not befehle & {"MOVE", "COPY", "EXPUNGE", "DELETE", "CREATE", "RENAME",
                          "APPEND"}, befehle

    texte = {k.value for k in ast.walk(baum)
             if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    assert "+FLAGS" in texte and "-FLAGS" not in texte and "FLAGS" not in texte
    assert faehnchen.FLAG == "\\Flagged"
    assert not any(("\\Deleted" in t or "\\Seen" in t) and len(t) < 20 for t in texte), \
        "ein zweites Flag steht als Wert im Code"

    zugriffe = {k.attr for k in ast.walk(baum) if isinstance(k, ast.Attribute)}
    assert not zugriffe & {"store", "expunge", "copy", "move", "delete", "create", "rename",
                           "append", "send", "sendmail", "send_message"}, zugriffe
    assert {"uid", "select"} <= zugriffe, "die Prüfung sieht die Zugriffe nicht"
