"""Die Übergabe einer fertigen Datei ans Betriebssystem (#239, ADR 0038).

Kein Test hier startet ein Programm. Möglich ist das, weil `weg()` und
`kein_bildschirm()` die Plattform und die Umgebung als **Parameter** nehmen
statt sie nachzuschlagen, und weil `_fuehre_aus()` seinen Starter als
Vorgabewert bekommt. Deshalb steht in dieser Datei kein einziges `skipif`:
Eine übersprungene Prüfung sieht aus wie eine bestandene.

Jede Prüfung hat ihre Gegenprobe daneben, und die Gegenprobe steht dabei, nicht
in einem eigenen Abschnitt — eine Zusicherung, die nie fehlschlagen kann, fällt
nur auf, wenn ihr Gegenstück im selben Blickfeld liegt.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from falzmarke import oeffnen


class Rekorder:
    """Ein Starter, der nichts startet, sondern mitschreibt."""

    def __init__(self, rueckgabe=0, stderr="", wirft=None, stdout=""):
        self.aufrufe: list[tuple] = []
        self.kwargs: list[dict] = []
        self._rueckgabe, self._stderr, self._wirft = rueckgabe, stderr, wirft
        self._stdout = stdout

    def __call__(self, argv, **kwargs):
        self.aufrufe.append(tuple(argv))
        self.kwargs.append(kwargs)
        if self._wirft is not None:
            raise self._wirft
        return subprocess.CompletedProcess(argv, self._rueckgabe,
                                           stdout=self._stdout, stderr=self._stderr)

    @property
    def anzahl(self) -> int:
        return len(self.aufrufe)


# ── Die Plattform-Weiche ────────────────────────────────────────────────────

@pytest.mark.parametrize("plattform, erwartet", [
    ("darwin", ("argv", "open")),
    ("linux", ("argv", "xdg-open")),
    ("linux2", ("argv", "xdg-open")),
    ("freebsd14", ("argv", "xdg-open")),
    ("win32", ("startfile", None)),
])
def test_je_plattform_der_uebliche_starter(tmp_path, plattform, erwartet):
    ziel = tmp_path / "nachricht.eml"
    ziel.write_text("x", encoding="utf-8")
    art, argv = oeffnen.weg(ziel, plattform)
    assert art == erwartet[0]
    if erwartet[1] is not None:
        assert argv[0] == erwartet[1]


def test_ein_unbekanntes_system_bekommt_keinen_weg(tmp_path):
    """Gegenprobe: Ohne sie wäre nicht belegt, dass die Weiche eine Weiche ist
    und nicht eine Abbildung, die auf alles antwortet."""
    assert oeffnen.weg(tmp_path / "x.eml", "aix7") is None


def test_der_pfad_wird_aufgeloest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "nachricht.eml").write_text("x", encoding="utf-8")
    _, argv = oeffnen.weg("nachricht.eml", "darwin")
    assert Path(argv[1]).is_absolute()


def test_ein_name_mit_bindestrich_wird_kein_schalter(tmp_path, monkeypatch):
    """`-o` nimmt jeden Zielnamen an. Ein relativer Name mit führendem Strich
    wäre für `open` ein Schalter statt einer Datei."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "-o.eml").write_text("x", encoding="utf-8")
    _, argv = oeffnen.weg("-o.eml", "darwin")
    assert not argv[1].startswith("-")


# ── Wie gestartet wird ──────────────────────────────────────────────────────

def test_niemals_ueber_eine_shell():
    rekorder = Rekorder()
    oeffnen._fuehre_aus("argv", ["open", "/x.eml"], laufen=rekorder)
    # Beide Zusicherungen zusammen: Die zweite ist die Gegenprobe zur ersten —
    # „kein shell=True" wäre bei null Aufrufen leer erfüllt.
    assert rekorder.anzahl == 1
    assert rekorder.kwargs[0].get("shell") is not True


def _shell_true_aufrufe(quelle: str) -> list[int]:
    """Zeilen mit `shell=True` als echtem Argument — über den Syntaxbaum.

    Nicht als Textsuche: Der Docstring dieses Moduls erklärt ausführlich,
    *warum* keine Shell dazwischenliegt, und schriebe damit jeden Textgrep rot.
    Ein Baum sieht nur Code.
    """
    return [k.value.lineno
            for knoten in ast.walk(ast.parse(quelle))
            if isinstance(knoten, ast.Call)
            for k in knoten.keywords
            if k.arg == "shell" and isinstance(k.value, ast.Constant)
            and k.value.value is True]


def test_kein_shell_true_im_quelltext():
    quelle = Path(oeffnen.__file__).read_text(encoding="utf-8")
    assert not _shell_true_aufrufe(quelle)


def test_gegenprobe_die_pruefung_wuerde_es_finden():
    """Ohne sie belegt der Test oben nur, dass gerade nichts dasteht."""
    assert _shell_true_aufrufe("lauf = laufen(argv, shell=True)\n")
    # Und sie darf nicht auf Prosa anspringen, sonst wäre sie unbrauchbar:
    assert not _shell_true_aufrufe('"""Ohne shell=True, und zwar deshalb."""\n')


# ── Was bei einem Fehlschlag passiert ───────────────────────────────────────

def test_ein_fehlschlag_wird_gemeldet_und_nicht_geworfen():
    rekorder = Rekorder(rueckgabe=4, stderr="kein Programm zugeordnet")
    code, meldung = oeffnen._fuehre_aus("argv", ["xdg-open", "x"], laufen=rekorder)
    assert code == 4
    assert "kein Programm zugeordnet" in meldung


def test_ein_erfolg_meldet_nichts():
    """Gegenprobe zu oben: Sonst wäre nicht belegt, dass gemeldet wird, *weil*
    etwas schiefging."""
    code, meldung = oeffnen._fuehre_aus("argv", ["open", "x"], laufen=Rekorder())
    assert (code, meldung) == (0, "")


def test_ein_fehlendes_programm_ist_kein_absturz():
    rekorder = Rekorder(wirft=FileNotFoundError())
    code, meldung = oeffnen._fuehre_aus("argv", ["xdg-open", "x"], laufen=rekorder)
    assert code == 127
    assert "xdg-open" in meldung


def test_ein_haengender_starter_laeuft_in_die_frist():
    rekorder = Rekorder(wirft=subprocess.TimeoutExpired("xdg-open", oeffnen.FRIST_S))
    code, meldung = oeffnen._fuehre_aus("argv", ["xdg-open", "x"], laufen=rekorder)
    assert code == 124
    assert str(oeffnen.FRIST_S) in meldung


def test_windows_geht_ueber_startfile(tmp_path):
    gesehen = []
    code, _ = oeffnen._fuehre_aus("startfile", [str(tmp_path / "x.eml")],
                                  startfile=gesehen.append)
    assert (code, len(gesehen)) == (0, 1)


def test_windows_meldet_einen_fehler_statt_zu_werfen():
    def wirft(_):
        raise OSError("keine Anwendung zugeordnet")

    code, meldung = oeffnen._fuehre_aus("startfile", ["x"], startfile=wirft)
    assert code == 1
    assert "keine Anwendung" in meldung


# ── Wann gar nicht erst gestartet wird ──────────────────────────────────────

def test_auf_einem_baurechner_geht_nichts_auf():
    assert oeffnen.kein_bildschirm({"CI": "true"}, "linux")


def test_gegenprobe_ohne_ci_schon():
    """Ohne sie könnte `kein_bildschirm` eine Funktion sein, die immer abrät."""
    assert oeffnen.kein_bildschirm({"DISPLAY": ":0"}, "linux") is None


@pytest.mark.parametrize("wert", ["", "0", "false", "False"])
def test_ein_leeres_ci_ist_kein_baurechner(wert):
    assert oeffnen.kein_bildschirm({"CI": wert, "DISPLAY": ":0"}, "linux") is None


def test_linux_ohne_display_haelt_zu():
    assert oeffnen.kein_bildschirm({}, "linux")


def test_macos_braucht_kein_display():
    """Gegenprobe: Sonst wäre die DISPLAY-Regel womöglich eine
    „nie öffnen"-Regel, die zufällig richtig aussieht."""
    assert oeffnen.kein_bildschirm({}, "darwin") is None


def test_wayland_zaehlt_auch():
    assert oeffnen.kein_bildschirm({"WAYLAND_DISPLAY": "wayland-0"}, "linux") is None


@pytest.mark.parametrize("wunsch, erwartet_zu", [("nie", True), ("immer", False)])
def test_der_schalter_sticht_alles(wunsch, erwartet_zu):
    # „immer" gegen die schärfste Gegenlage: Baurechner ohne Bildschirm.
    umgebung = {"FALZMARKE_OEFFNEN": wunsch, "CI": "true"}
    assert bool(oeffnen.kein_bildschirm(umgebung, "linux")) is erwartet_zu


# ── Das Ganze ───────────────────────────────────────────────────────────────

def test_oeffne_startet_und_schweigt(tmp_path, monkeypatch):
    ziel = tmp_path / "nachricht.eml"
    ziel.write_text("x", encoding="utf-8")
    rekorder = Rekorder()
    monkeypatch.setattr(oeffnen, "_fuehre_aus",
                        lambda art, argv, **_: (rekorder(argv), (0, ""))[1])
    assert oeffnen.oeffne(ziel, plattform="darwin",
                          umgebung={"DISPLAY": ":0"}) is None
    assert rekorder.anzahl == 1


def test_oeffne_startet_nichts_ohne_bildschirm(tmp_path, monkeypatch):
    """Die tragende Gegenprobe zum Test darüber: gleiche Datei, gleiche
    Plattform — nur die Umgebung sagt nein, und es bleibt bei null Aufrufen."""
    ziel = tmp_path / "nachricht.eml"
    ziel.write_text("x", encoding="utf-8")
    rekorder = Rekorder()
    monkeypatch.setattr(oeffnen, "_fuehre_aus",
                        lambda art, argv, **_: (rekorder(argv), (0, ""))[1])
    grund = oeffnen.oeffne(ziel, plattform="linux", umgebung={"CI": "1"})
    assert grund and rekorder.anzahl == 0


def test_ein_unbekanntes_system_meldet_sich(tmp_path):
    ziel = tmp_path / "nachricht.eml"
    ziel.write_text("x", encoding="utf-8")
    grund = oeffnen.oeffne(ziel, plattform="aix7", umgebung={"DISPLAY": ":0"})
    assert grund and "aix7" in grund


def test_ein_fehlschlag_kommt_als_satz_zurueck(tmp_path, monkeypatch):
    ziel = tmp_path / "nachricht.eml"
    ziel.write_text("x", encoding="utf-8")
    monkeypatch.setattr(oeffnen, "_fuehre_aus",
                        lambda *a, **k: (3, "kein Programm für text/eml"))
    grund = oeffnen.oeffne(ziel, plattform="darwin", umgebung={"DISPLAY": ":0"})
    assert grund == "kein Programm für text/eml"


def test_ein_stummer_fehlschlag_bekommt_trotzdem_einen_satz(tmp_path, monkeypatch):
    """Ein Starter, der mit Code endet und nichts sagt, darf nicht in einer
    leeren Meldung verschwinden."""
    ziel = tmp_path / "nachricht.eml"
    ziel.write_text("x", encoding="utf-8")
    monkeypatch.setattr(oeffnen, "_fuehre_aus", lambda *a, **k: (3, ""))
    grund = oeffnen.oeffne(ziel, plattform="darwin", umgebung={"DISPLAY": ":0"})
    assert grund and "3" in grund


# ── Der Entwurf (#263) ──────────────────────────────────────────────────────
#
# Kein Test in diesem Abschnitt startet ein Programm. Was `osascript` täte,
# wird eingespeist; geprüft wird, WOMIT es aufgerufen würde — und dass die
# Antwort gegengelesen wird, statt einem Exit-Code zu glauben.

class Antwortet:
    """Ein `osascript`, das nichts ausführt, sondern zwei Fragen beantwortet.

    Die Suche nach dem Programm (`-e POSIX path …`) und der Lauf des Skripts
    brauchen verschiedene Antworten. Ein Rekorder mit einer einzigen Rückgabe
    könnte den zweiten Schritt nicht messen.
    """

    def __init__(self, *, gefunden=True, nachweis="1 0 0 0", code=0, stderr=""):
        self.aufrufe: list[tuple] = []
        self.dateien_da: list[bool] = []
        self._gefunden, self._nachweis = gefunden, nachweis
        self._code, self._stderr = code, stderr

    def __call__(self, argv, **kwargs):
        self.aufrufe.append(tuple(argv))
        if "-e" in argv:
            treffer = "/Applications/Beispiel.app/" if self._gefunden else ""
            return subprocess.CompletedProcess(argv, 0 if self._gefunden else 1,
                                               stdout=treffer, stderr="")
        # Die Anhänge müssen JETZT dastehen, nicht irgendwann: Ein Verzeichnis,
        # das vor dem Aufruf abgeräumt wird, hängt leere Anlagen an.
        self.dateien_da.append(all(Path(a).exists() for a in argv[1:]
                                   if a.startswith("/") and "falzmarke-entwurf-" in a))
        return subprocess.CompletedProcess(argv, self._code,
                                           stdout=self._nachweis, stderr=self._stderr)


FELDER = {"betreff": "Probe", "an": ["a@example.de"], "kopie": [],
          "blindkopie": [], "html": "<p>Text</p>", "anhaenge": []}


@pytest.mark.parametrize("plattform", ["linux", "win32", "freebsd14"])
def test_ausserhalb_von_macos_gibt_es_keinen_entwurfsweg(plattform):
    """Windows über COM und Linux sind ungemessen — und was ungemessen ist,
    wird nicht behauptet."""
    rekorder = Rekorder()
    assert oeffnen.entwurfsweg(plattform, laufen=rekorder) is None
    assert rekorder.anzahl == 0, "es wurde gefragt, obwohl die Antwort feststand"


def test_auf_macos_wird_das_system_gefragt_und_nichts_gestartet():
    antwort = Antwortet()
    gewaehlt = oeffnen.entwurfsweg("darwin", laufen=antwort)
    assert gewaehlt is not None and gewaehlt[1] == "Microsoft Outlook"
    (aufruf,) = antwort.aufrufe
    assert aufruf[0] == "osascript" and "-e" in aufruf
    frage = aufruf[-1]
    assert "path to application id" in frage
    # Die Gegenprobe zur Zeile darüber: Es darf nichts dabei sein, was startet.
    assert "activate" not in frage and "open " not in frage


def test_ohne_passendes_programm_bleibt_es_bei_der_datei():
    antwort = Antwortet(gefunden=False)
    assert oeffnen.entwurfsweg("darwin", laufen=antwort) is None


def test_die_argumente_stehen_in_fester_reihenfolge():
    argv = oeffnen.entwurfsargumente(
        {"betreff": "B", "html": "<p>H</p>", "an": ["a@x.de", "b@x.de"],
         "kopie": ["c@x.de"], "blindkopie": ["archiv@x.de"]},
        ["/tmp/eins.pdf", "/tmp/zwei.pdf"])
    assert argv == ["B", "<p>H</p>", "a@x.de,b@x.de", "c@x.de", "archiv@x.de",
                    "/tmp/eins.pdf", "/tmp/zwei.pdf"]


def test_fehlende_felder_werden_zu_leeren_argumenten_nicht_zu_none():
    argv = oeffnen.entwurfsargumente({}, [])
    assert argv == ["", "", "", "", ""], "None im Argument wäre ein Absturz im Skript"


def test_das_skript_setzt_nichts_aus_eingaben_zusammen():
    """Der Betreff ist ein Wert, keine Programmzeile.

    Stünde er im Skripttext, wäre ein Anführungszeichen darin Syntax — und ein
    Betreff ist Eingabe.
    """
    assert "{betreff}" not in oeffnen.SKRIPT_OUTLOOK
    assert "%s" not in oeffnen.SKRIPT_OUTLOOK
    assert "on run argv" in oeffnen.SKRIPT_OUTLOOK


def test_im_steuerskript_steht_kein_versandbefehl():
    """ADR 0034 gilt unverändert: Entwurf ja, Senden nie."""
    for _, _, skript in oeffnen.ENTWURFSPROGRAMME:
        assert "send " not in skript and "send\n" not in skript


def test_gegenprobe_die_suche_wuerde_ein_send_finden():
    """Ohne sie belegt der Test oben nur, dass gerade nichts dasteht."""
    erfunden = "tell application \"X\" to send entwurf\n"
    assert "send " in erfunden


def test_der_nachweis_wird_gegen_die_vorgabe_gehalten():
    felder = {"an": ["a@x.de"], "kopie": [], "blindkopie": [],
              "anhaenge": [("x.pdf", b"x")]}
    assert oeffnen._nachweis_stimmt("1 0 0 1", felder) is None
    fehlt = oeffnen._nachweis_stimmt("1 0 0 0", felder)
    assert fehlt and "Anhänge" in fehlt, "ein verschluckter Anhang fiel nicht auf"


def test_eine_antwort_ohne_zahlen_gilt_nicht_als_nachweis():
    grund = oeffnen._nachweis_stimmt("ok", {"an": [], "kopie": [], "blindkopie": [],
                                            "anhaenge": []})
    assert grund and "Zählung" in grund


def test_der_entwurf_meldet_das_programm(tmp_path):
    antwort = Antwortet(nachweis="1 0 0 0")
    name, grund = oeffnen.entwurf(FELDER, plattform="darwin",
                                  umgebung={"DISPLAY": ":0"}, laufen=antwort)
    assert (name, grund) == ("Microsoft Outlook", "")
    lauf = antwort.aufrufe[-1]
    assert lauf[0] == "osascript" and lauf[1].endswith(".applescript")
    assert lauf[2:] == ("Probe", "<p>Text</p>", "a@example.de", "", "")


def test_ein_verschluckter_anhang_faellt_auf():
    """Der Fall, den ein Exit-Code allein nie zeigt: Das Skript läuft durch,
    aber die Anlage fehlt."""
    felder = {**FELDER, "anhaenge": [("rechnung.pdf", b"%PDF-1.7")]}
    antwort = Antwortet(nachweis="1 0 0 0")
    name, grund = oeffnen.entwurf(felder, plattform="darwin",
                                  umgebung={"DISPLAY": ":0"}, laufen=antwort)
    assert name is None and "Anhänge" in grund


def test_die_anhaenge_liegen_da_waehrend_das_programm_sie_liest():
    felder = {**FELDER, "anhaenge": [("rechnung.pdf", b"%PDF-1.7")]}
    antwort = Antwortet(nachweis="1 0 0 1")
    name, _ = oeffnen.entwurf(felder, plattform="darwin",
                              umgebung={"DISPLAY": ":0"}, laufen=antwort)
    assert name == "Microsoft Outlook"
    assert antwort.dateien_da == [True], "das Verzeichnis war beim Aufruf schon weg"


def test_ein_anhangname_zeigt_nie_aus_dem_ordner():
    felder = {**FELDER, "anhaenge": [("../../etc/passwd", b"x")]}
    antwort = Antwortet(nachweis="1 0 0 1")
    oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0"},
                    laufen=antwort)
    pfade = [a for a in antwort.aufrufe[-1] if "falzmarke-entwurf-" in str(a)]
    assert pfade and all(".." not in p for p in pfade), pfade


def test_der_schalter_haelt_den_entwurf_zu_ohne_die_datei_aufzugeben():
    antwort = Antwortet()
    name, grund = oeffnen.entwurf(FELDER, plattform="darwin",
                                  umgebung={"FALZMARKE_ENTWURF": "nie", "DISPLAY": ":0"},
                                  laufen=antwort)
    assert name is None and "FALZMARKE_ENTWURF" in grund
    assert antwort.aufrufe == [], "es wurde gestartet, obwohl abgeschaltet war"


def test_gegenprobe_ohne_den_schalter_laeuft_es():
    """Ohne sie belegte der Test darüber nur, dass irgendetwas None ergibt."""
    antwort = Antwortet(nachweis="1 0 0 0")
    name, _ = oeffnen.entwurf(FELDER, plattform="darwin",
                              umgebung={"DISPLAY": ":0"}, laufen=antwort)
    assert name == "Microsoft Outlook"


def test_auf_einem_baurechner_entsteht_kein_entwurf():
    antwort = Antwortet()
    name, grund = oeffnen.entwurf(FELDER, plattform="darwin",
                                  umgebung={"CI": "true"}, laufen=antwort)
    assert name is None and "Baurechner" in grund
    assert antwort.aufrufe == []


def test_ein_fehler_des_skripts_wird_zum_satz_und_nicht_zur_ausnahme():
    antwort = Antwortet(code=1, stderr="execution error: Outlook ist nicht berechtigt (-1743)")
    name, grund = oeffnen.entwurf(FELDER, plattform="darwin",
                                  umgebung={"DISPLAY": ":0"}, laufen=antwort)
    assert name is None and "-1743" in grund


def test_ein_haengendes_steuerskript_laeuft_in_die_frist():
    def haengt(argv, **kwargs):
        if "-e" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="/Applications/X.app/", stderr="")
        raise subprocess.TimeoutExpired(argv, oeffnen.FRIST_ENTWURF_S)

    name, grund = oeffnen.entwurf(FELDER, plattform="darwin",
                                  umgebung={"DISPLAY": ":0"}, laufen=haengt)
    assert name is None and str(oeffnen.FRIST_ENTWURF_S) in grund


def test_die_blindkopie_geht_in_den_entwurf():
    """Der Mangel aus #272: Bis dahin las der Entwurfsweg nur To und Cc.

    Die Blindkopie stand in der `.eml`, `verify --email` hatte sie gemessen —
    und im Entwurfsfenster fehlte sie. Eine Zeile, die nie da war, vermisst
    niemand.
    """
    felder = {**FELDER, "blindkopie": ["archiv@example.de"]}
    antwort = Antwortet(nachweis="1 0 1 0")
    name, grund = oeffnen.entwurf(felder, plattform="darwin",
                                  umgebung={"DISPLAY": ":0"}, laufen=antwort)
    assert (name, grund) == ("Microsoft Outlook", "")
    assert antwort.aufrufe[-1][6] == "archiv@example.de", antwort.aufrufe[-1]
    assert "make new bcc recipient" in oeffnen.SKRIPT_OUTLOOK


def test_eine_verschluckte_blindkopie_faellt_auf():
    """Dieselbe Zählung wie beim Anhang: Ein Programm, das die Adresse
    stillschweigend fallen lässt, kommt hier nicht durch."""
    felder = {**FELDER, "blindkopie": ["archiv@example.de"]}
    antwort = Antwortet(nachweis="1 0 0 0")
    name, grund = oeffnen.entwurf(felder, plattform="darwin",
                                  umgebung={"DISPLAY": ":0"}, laufen=antwort)
    assert name is None
    assert "Blindkopien: 0 statt 1" in grund, grund
