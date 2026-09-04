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

    def __init__(self, rueckgabe=0, stderr="", wirft=None):
        self.aufrufe: list[tuple] = []
        self.kwargs: list[dict] = []
        self._rueckgabe, self._stderr, self._wirft = rueckgabe, stderr, wirft

    def __call__(self, argv, **kwargs):
        self.aufrufe.append(tuple(argv))
        self.kwargs.append(kwargs)
        if self._wirft is not None:
            raise self._wirft
        return subprocess.CompletedProcess(argv, self._rueckgabe,
                                           stdout="", stderr=self._stderr)

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
