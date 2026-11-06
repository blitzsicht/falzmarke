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


@pytest.mark.parametrize("port", ["0", "65536", "70000", "99999"])
def test_ein_port_ausserhalb_des_bereichs_ist_ein_bleibender_grund(port):
    """Nachreview von #569: macOS meldete `99999` als unbekannten Host und Port 0
    als „Can't assign requested address“. Der Grund nennt jetzt den Port."""
    with pytest.raises(postfach.PostfachFehler,
                       match=f"Port {int(port)} liegt nicht zwischen 1 und 65535") as fehler:
        postfach.ziel({"FALZMARKE_GESENDET_IMAP": f"127.0.0.1:{port}"})
    assert fehler.value.voruebergehend is False


@pytest.mark.parametrize("port", [1, 65535])
def test_die_grenzen_des_portbereichs_gelten(port):
    assert postfach.ziel({"FALZMARKE_GESENDET_IMAP": f"127.0.0.1:{port}"}) == ("127.0.0.1", port)


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
    # Die Meldung nennt die Frist. Ihren Wert prüft `test_gesendet` gegen die
    # gemessene Anmeldung (#441).
    with pytest.raises(postfach.PostfachFehler, match=f"in {postfach.FRIST_S:g} s$"):
        postfach.verbinde("joe@example.org", umgebung={})


def test_eine_abgelehnte_anmeldung_nennt_die_meldung(monkeypatch):
    """So antwortet der Proxy auf ein Konto, das er nicht kennt (Gmail)."""
    attrappe = ImapAttrappe(login_fehler="No config file entry found for account ich@gmail.com")
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    with pytest.raises(postfach.PostfachFehler, match="No config file entry"):
        postfach.verbinde("ich@gmail.com", umgebung={})
    assert attrappe.abgemeldet == 1, "die halbe Sitzung bleibt offen"


@pytest.mark.parametrize("adresse", ["joe@example.org\r\nA1 DELETE INBOX",
                                     "joe@example.org\n", "joe\x00@example.org"])
def test_ein_umbruch_in_der_adresse_meldet_nicht_an(server, adresse):
    """`LOGIN` geht nicht durch `_zitiert` (#442, N4). Auf 3.12 setzte `imaplib`
    den Namen samt `\\r\\n` in die Befehlszeile; die Attrappe lehnt wie 3.14 mit
    `ValueError` ab, und das wäre ein Traceback statt eines Grundes.
    """
    with pytest.raises(postfach.PostfachFehler, match="Umbruch oder ein Nullbyte"):
        postfach.verbinde(adresse, umgebung={})
    assert server.verbindungen == [], "abgelehnt wird vor dem Verbindungsaufbau"
    assert server.protokoll == []


@pytest.mark.parametrize("adresse", ["joe@example.org", "joe {5}@example.org",
                                     'jo"e@example.org'])
def test_der_anmeldename_geht_zitiert_auf_die_leitung(server, adresse):
    """Review von #460: `imaplib.login` zitiert nur das Kennwort.

    Unzitiert wäre `joe {5}@example.org` zwei Argumente, und ein `{5}` am Ende
    eines Namens kündigte ein Literal an, auf das der Server wartet.
    """
    with postfach.verbinde(adresse, umgebung={}):
        pass
    (befehl,) = [p for p in server.protokoll if p[0] == "LOGIN"]
    assert befehl[1] == postfach._zitiert(adresse) and befehl[1].startswith('"')
    assert server.angemeldet == [(adresse, postfach.KENNWORT)], \
        "der Proxy liest den Namen ohne Anführungszeichen"


def test_ein_valueerror_aus_imaplib_ist_ein_grund_und_meldet_ab(monkeypatch):
    """Review von #460: `imaplib` wirft ab 3.14 `ValueError` für Steuerzeichen.

    Bis dahin fing `_befehl` davon nur `UnicodeEncodeError`. Jeder andere
    `ValueError` lief als Traceback hinaus, und `verbinde` meldete nicht ab.
    """
    attrappe = ImapAttrappe()
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)

    def login(user, password):
        raise ValueError("NUL, CR and LF not allowed")

    monkeypatch.setattr(attrappe, "login", login)
    with pytest.raises(postfach.PostfachFehler, match="NUL, CR and LF"):
        postfach.verbinde("joe@example.org", umgebung={})
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
    assert kopf.an == ("paula@example.org",)
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
    assert kopf.an == ("paula@example.org", "erika@example.org")


def test_ohne_date_zaehlt_die_ankunft():
    roh = b"To: a@example.org\r\nSubject: x\r\n\r\n"
    ankunft = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    assert postfach.kopf_aus(roh, "1", ankunft).datum == ankunft


@pytest.mark.parametrize("gesucht, kopfwert, gleich", [
    ("<abc@x>", "<abc@x>", True),
    ("abc@x", "<abc@x>", True),        # ein Programm, das die Klammern weglässt
    ("abc@x>", "<abc@x>", False),      # eine Klammer allein ist kein Paar
    ("<abc@x", "<abc@x>", False),
    ("<<abc@x>>", "<abc@x>", False),   # zwei Paare sind nicht eines
    ("ABC@x", "<abc@x>", False),       # Groß und klein zählen, Absicht seit #457
])
def test_gleiche_kennung_nimmt_genau_ein_klammerpaar_ab(gesucht, kopfwert, gleich):
    """Review von #457: `strip("<>")` nahm jede Klammer an jedem Ende."""
    assert postfach.gleiche_kennung(gesucht, kopfwert) is gleich


#: Die Teilkettensuche des Servers, unter dem alten und dem heutigen Namen.
TEILKETTENSUCHE = frozenset({"suche_kopfzeile", "_suche_kopfzeile"})


def aufrufe_der_teilkettensuche(quellen: dict[str, str]) -> list[str]:
    """`datei:zeile` je Zugriff auf die Teilkettensuche außerhalb von `postfach.py`.

    Gelesen über `ast`: Ein Kommentar, der die Suche erklärt, ist kein Aufruf.
    """
    import ast

    return [f"{name}:{knoten.lineno}" for name, text in sorted(quellen.items())
            if name != "postfach.py"
            for knoten in ast.walk(ast.parse(text))
            if isinstance(knoten, ast.Attribute) and knoten.attr in TEILKETTENSUCHE]


def _paketquellen(ordner=None) -> dict[str, str]:
    """Jede Python-Datei des Pakets, auch in Unterpaketen, unter ihrem Pfad relativ
    zum Paket (POSIX-Schreibweise, damit der Test auf Windows dasselbe sagt)."""
    from pathlib import Path

    ordner = Path(ordner) if ordner else Path(postfach.__file__).parent
    return {p.relative_to(ordner).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(ordner.rglob("*.py"))}


def test_nur_postfach_ruft_die_teilkettensuche():
    """#468: Von außen geht die Suche nach einer Kennung über `suche_kennung`.

    Bis dahin lieferte `suche_kopfzeile` ungefilterte UIDs, und nur ein Satz im
    Docstring verlangte den Nachvergleich. Ein Aufrufer, der ihn vergaß, hätte
    #442 zurückgeholt: eine fremde Mail, deren Kennung die gesuchte enthält.
    """
    quellen = _paketquellen()
    assert {"postfach.py", "ablage.py"} <= set(quellen), sorted(quellen)
    assert aufrufe_der_teilkettensuche(quellen) == []


def test_gegenprobe_der_alte_aufruf_in_ablage_wird_gemeldet():
    quellen = _paketquellen()
    # Nur der Name: Die Argumente stehen seit dem Nachreview von #524 auf eigener Zeile.
    neu = "sitzung.suche_kennung("
    assert quellen["ablage.py"].count(neu) == 1, "die Sabotage findet ihren Anker nicht"
    quellen["ablage.py"] = quellen["ablage.py"].replace(neu, "sitzung.suche_kopfzeile(")
    (fund,) = aufrufe_der_teilkettensuche(quellen)
    assert fund.startswith("ablage.py:")


def test_die_quellen_reichen_in_die_unterpakete(tmp_path):
    """Nachreview von #479: `glob("*.py")` sah `regeln/` nicht. Ein Aufruf in
    einem Unterpaket wäre an der Prüfung oben vorbeigegangen."""
    assert "regeln/__init__.py" in _paketquellen(), "Unterpakete fehlen"
    (tmp_path / "unter").mkdir(parents=True)
    (tmp_path / "unter" / "x.py").write_text(
        's._suche_kopfzeile("INBOX", "Message-ID", k)\n', encoding="utf-8")
    assert aufrufe_der_teilkettensuche(_paketquellen(tmp_path)) == ["unter/x.py:1"]


def zugriffe_auf_utf7_dekodieren(quellen: dict[str, str]) -> tuple[list[str], int]:
    """`(funde, erlaubt)`: je Zugriff auf `utf7_dekodieren` ein `datei:zeile in funktion`,
    dazu die Zahl der Zugriffe an der einen erlaubten Stelle.

    Erlaubt ist allein der Rumpf von `postfach.utf7_anzeige`, nicht die ganze Datei
    (Nachreview von #535, Befund 1). Gelesen über `ast`: Kommentare und Docstrings,
    die die Funktion nennen, sind kein Zugriff. Gezählt wird jeder Name und jedes
    Attribut, nicht nur ein Aufruf; auch `map(utf7_dekodieren, …)` dekodiert ohne
    Rückfall.
    """
    import ast

    funde: list[str] = []
    erlaubt = 0

    def besuche(knoten, datei: str, funktion: str) -> None:
        nonlocal erlaubt
        if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funktion = knoten.name
        name = (knoten.id if isinstance(knoten, ast.Name)
                else knoten.attr if isinstance(knoten, ast.Attribute) else None)
        if name == "utf7_dekodieren":
            if datei == "postfach.py" and funktion == "utf7_anzeige":
                erlaubt += 1
            else:
                funde.append(f"{datei}:{knoten.lineno} in {funktion or '<modul>'}")
        for kind in ast.iter_child_nodes(knoten):
            besuche(kind, datei, funktion)

    for datei, text in sorted(quellen.items()):
        besuche(ast.parse(text), datei, "")
    return funde, erlaubt


def test_nur_utf7_anzeige_dekodiert_ordnernamen():
    """Nachreview von #535, Befund 1: Jeder dekodierte Ordnername dient nur der
    Anzeige. Ein Server, der „AT&T-Rechnungen“ wörtlich führt, ließ das blanke
    `utf7_dekodieren` werfen, und mit ihm SELECT, APPEND und ganze Läufe. Von außen
    dekodiert deshalb nur `utf7_anzeige`, die bei ungültigem UTF-7 den Namen lässt."""
    quellen = _paketquellen()
    assert {"postfach.py", "ablage.py", "regeln/__init__.py"} <= set(quellen), sorted(quellen)
    funde, erlaubt = zugriffe_auf_utf7_dekodieren(quellen)
    assert funde == [], f"utf7_dekodieren ohne Rückfall: {funde}"
    assert erlaubt == 1, f"utf7_anzeige ruft utf7_dekodieren {erlaubt}-mal, erwartet 1"


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


#: Ein Ordnername, den ein nicht konformer Server wörtlich führt: kein gültiges
#: modified UTF-7 (Nachreview von #535, Befund 1).
UNGUELTIG = "AT&T-Entwurf"


def test_ablegen_in_einen_ordner_mit_ungueltigem_utf7_namen(server):
    """Der Text zum APPEND wird gebaut, bevor der Befehl läuft. Mit dem blanken
    `utf7_dekodieren` brach er das APPEND ab, das der Server ausgeführt hätte."""
    server.ordner[UNGUELTIG] = []
    roh = nachricht(betreff="Neu")
    with postfach.verbinde("joe@example.org", umgebung={}, frist=30) as pf:
        pf.ablegen(UNGUELTIG, roh)
    (append,) = server.befehle("APPEND")
    assert append[1] == UNGUELTIG
    assert server.ordner[UNGUELTIG][-1].roh == roh


def test_lesen_aus_einem_ordner_mit_ungueltigem_utf7_namen(monkeypatch):
    """Dasselbe für das EXAMINE in `_waehle`."""
    attrappe = ImapAttrappe({UNGUELTIG: [(nachricht(betreff="Liegt", datum=JETZT), JETZT)]})
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    with postfach.verbinde("joe@example.org", umgebung={}, frist=30) as pf:
        koepfe = pf.koepfe(UNGUELTIG)
    assert [k.betreff for k in koepfe] == ["Liegt"]
    assert ("EXAMINE", UNGUELTIG) in attrappe.protokoll


def test_ungueltiger_ordnername_wird_angezeigt_wie_geliefert():
    assert postfach.utf7_anzeige(UNGUELTIG) == UNGUELTIG
    assert postfach.utf7_anzeige("Entw&APw-rfe") == "Entwürfe"
    assert postfach.utf7_anzeige("A&-B") == "A&B"
    with pytest.raises(ValueError, match="Invalid base64-encoded string"):
        postfach.utf7_dekodieren(UNGUELTIG)


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


def test_gegenprobe_das_verschieben_ist_einzeln_einzuschalten():
    """Seit #431 kann die Attrappe `UID MOVE` — aber nur mit
    `verschieben_erlaubt=True`. Ohne diese Probe wäre die Erweiterung eine
    Hintertür: Jeder andere Test dürfte dann unbemerkt verschieben, und die
    Zusage von `postfach` wäre nur noch im Text.
    """
    attrappe = ImapAttrappe()
    attrappe.select("INBOX", readonly=True)
    with pytest.raises(AssertionError, match="UID MOVE"):
        attrappe.uid("MOVE", "101", '"Archiv"')
    with pytest.raises(AssertionError, match="readonly"):
        attrappe.select("INBOX")

    # Und mit dem Schalter geht beides — sonst belegte die Probe oben nur,
    # dass die Attrappe grundsätzlich wirft.
    offen = ImapAttrappe(sonder={"INBOX": "", "Archiv": ""},
                         verschieben_erlaubt=True)
    offen.select('"INBOX"')
    assert offen.uid("MOVE", "1", '"Archiv"')[0] == "OK"


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
    assert not importe & {"smtplib", "subprocess"}, importe
    assert socket_ausser_fehlerklassen(quelle) == set()


SOCKET_ERLAUBT = frozenset({"gaierror", "EAI_AGAIN"})


def socket_ausser_fehlerklassen(quelle: str) -> set[str]:
    """Was `postfach` aus `socket` nimmt, außer zwei Namen für die Klasse eines
    Fehlers. Bis #505 war `socket` ganz verboten; seitdem unterscheidet
    `_vergeht` einen vertippten Host (`gaierror`, bleibt) von einer gestörten
    Namensauflösung (`EAI_AGAIN`, vergeht). Eine eigene Verbindung, ein
    `from socket import …` und ein Alias bleiben verboten: Jeder davon wäre ein
    Netzweg neben IMAP oder versteckte ihn vor dieser Prüfung."""
    import ast

    baum = ast.parse(quelle)
    funde: set[str] = set()
    gelesen: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.ImportFrom) and (knoten.module or "").split(".")[0] == "socket":
            funde.add(f"from socket import {', '.join(a.name for a in knoten.names)}")
        elif isinstance(knoten, ast.Import):
            funde |= {f"import socket as {a.asname}" for a in knoten.names
                      if a.name == "socket" and a.asname}
        elif (isinstance(knoten, ast.Attribute) and isinstance(knoten.value, ast.Name)
              and knoten.value.id == "socket"):
            gelesen.add(knoten.attr)
    funde |= {f"socket.{name}" for name in gelesen - SOCKET_ERLAUBT}
    # Die Prüfung muss sehen, was sie erlaubt — sonst bliebe sie auch leer,
    # wenn sie gar keinen Zugriff fände.
    if "import socket" in quelle and not gelesen:
        funde.add("socket importiert, aber kein Zugriff gefunden")
    return funde


def test_imaplib_fehler_werden_zum_grund(server, monkeypatch):
    def kaputt(*_a, **_k):
        raise imaplib.IMAP4.abort("socket error: EOF")
    with postfach.verbinde("joe@example.org", umgebung={}) as pf:
        monkeypatch.setattr(server, "uid", kaputt)
        with pytest.raises(postfach.PostfachFehler, match="EOF"):
            pf.koepfe("Gesendete Elemente")
