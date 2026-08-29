"""Das README-GIF darf nichts zeigen, was die CLI nicht wirklich ausgibt.

Ein Demo-Bild ist eine Behauptung ueber das Programm. Sie altert still: Jemand
aendert eine Ausgabezeile, das GIF bleibt liegen, und im README steht monatelang
ein Terminal, das es so nie gab. Genau diese Klasse Fehler faengt schon
tests/test_installationswege.py fuer die README ab — hier fuer das bewegte Bild.

Geprueft wird gegen `docs/renders/demo.ascii`, den Textmitschnitt derselben
Aufnahme. Der Test braucht kein vhs: er vergleicht den mitgeschnittenen Text mit
einem frischen Lauf der Befehle, die im Tape stehen.

Vorbehalt, gemessen am 25.08.2026: Der ascii-Mitschnitt endet eine Zeile vor dem
Video. Im letzten Frame des MP4 steht `OK  verify: 30/30 Maße eingehalten`, in
der ascii-Datei nicht mehr. Darum prueft dieser Test die Richtung, auf die es
ankommt — alles Mitgeschnittene ist echt — und nicht, ob der Mitschnitt
vollstaendig ist.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

import pytest

from conftest import REPO

TAPE = REPO / "docs" / "marke" / "video" / "readme.tape"
MITSCHNITT = REPO / "docs" / "renders" / "demo.ascii"
GIF = REPO / "docs" / "renders" / "demo.gif"
CLI = REPO / "skill" / "scripts" / "falzmarke.py"

GIF_GRENZE = 5 * 1024 * 1024        # GitHub spielt groessere nicht mehr von allein ab
MP4_GRENZE = 10 * 1024 * 1024


def sichtbare_befehle() -> list[str]:
    """Alle `Type "..."` aus dem Tape, die nicht in einem Hide-Block stehen.

    Was zwischen Hide und Show getippt wird, richtet nur die Umgebung her
    (Prompt, clear) und erscheint nie im Bild.
    """
    befehle, versteckt = [], False
    for zeile in TAPE.read_text(encoding="utf-8").splitlines():
        nackt = zeile.strip()
        if nackt.startswith("#"):
            continue
        if nackt == "Hide":
            versteckt = True
        elif nackt == "Show":
            versteckt = False
        elif not versteckt:
            for treffer in re.finditer(r'Type\s+"([^"]*)"', nackt):
                befehle.append(treffer.group(1))
    return befehle


@pytest.fixture(scope="module")
def echte_ausgabe(tmp_path_factory) -> set[str]:
    """Fuehrt die Tape-Befehle wirklich aus und sammelt jede ausgegebene Zeile."""
    # Das Tape laeuft aus dem Wurzelverzeichnis des Repos, und die Ausgabe nennt
    # die Pfade so, wie sie dort getippt werden ("examples/brief-mahnung.md").
    # Damit die Zeilen woertlich vergleichbar bleiben, wird die Struktur im
    # Arbeitsverzeichnis nachgebaut — und nichts ins Repo geschrieben.
    arbeit = tmp_path_factory.mktemp("tape")
    (arbeit / "examples").mkdir()
    for befehl in sichtbare_befehle():
        for wort in befehl.split():
            if wort.endswith(".md") and (REPO / wort).is_file():
                shutil.copy2(REPO / wort, arbeit / wort)

    zeilen: set[str] = set()
    for befehl in sichtbare_befehle():
        # Im Bild steht `falzmarke …`; hier laeuft dieselbe CLI aus dem Repo.
        teile = befehl.split()
        if teile[0] == "falzmarke":
            argumente = [sys.executable, str(CLI), *teile[1:]]
        elif teile[0] == "cat":
            argumente = ["cat", teile[1]]
        else:
            pytest.fail(f"Unbekannter Befehl im Tape: {befehl}")
        ergebnis = subprocess.run(
            argumente, cwd=arbeit, capture_output=True, text=True, encoding="utf-8"
        )
        assert ergebnis.returncode == 0, f"{befehl} scheiterte:\n{ergebnis.stderr}"
        for zeile in (ergebnis.stdout + ergebnis.stderr).splitlines():
            if zeile.strip():
                zeilen.add(pfadtrenner_vereinheitlichen(zeile.strip()))
    return zeilen


def pfadtrenner_vereinheitlichen(zeile: str) -> str:
    """Windows meldet `examples\\brief-mahnung.pdf`, das GIF zeigt `examples/…`.

    Der Mitschnitt entsteht auf einem Rechner, der Test laeuft auf dreien. Ohne
    diese Angleichung waere der Test auf Windows immer rot — und zwar aus einem
    Grund, der mit der Sache nichts zu tun hat.
    """
    return zeile.replace("\\", "/")


def mitgeschnittene_zeilen() -> list[str]:
    """Zeilen aus dem Mitschnitt, ohne Rahmen, Prompt und Tippspuren."""
    raus = []
    for zeile in MITSCHNITT.read_text(encoding="utf-8").splitlines():
        nackt = zeile.strip()
        # "$" ist der gesetzte Prompt, ">" der Fortsetzungsprompt der Shell —
        # beides Rahmen, kein Inhalt.
        if not nackt or set(nackt) <= {"─"} or nackt.startswith("$") or nackt == ">":
            continue
        raus.append(pfadtrenner_vereinheitlichen(nackt))
    return raus


# ── Was die CLI ausgibt, muss in das Terminal der Aufnahme passen ──────────
#
# Gemessen am 28.08.2026 an einem roten Lauf der Video-Aktion (Merge von #140
# auf main): Die neue Zeile
#
#   OK    Seite 1, Zeilenraster: soll Vielfaches von 4,2333 ist 7 Abstände,
#         alle auf dem Raster (tol ±0.06 Zeilen)
#
# ist 110 Zeichen lang. Im Mitschnitt stand die schliessende Klammer allein in
# der naechsten Zeile, und der Test darunter meldete beide Haelften als „Zeilen,
# die kein Lauf erzeugt". Die Kopplung zwischen Ausgabebreite und Aufnahmebreite
# war bis dahin nirgends festgehalten: Sie fiel erst auf main auf, nachdem der PR
# gruen durchgelaufen war — die Video-Aktion laeuft nur dort.
#
# 109 ist deshalb keine Schaetzung aus Schriftgroesse und Pixelbreite, sondern
# die Folge einer Beobachtung: 110 Zeichen passten nachweislich nicht mehr.
#
# In ZEICHEN, nicht in Bytes. Beim ersten Anlauf zu diesem Test war die Grenze
# aus `awk '{print length}'` genommen — das zaehlt Bytes und meldete fuer
# dieselbe Zeile 112. Mit der zu weiten Grenze blieb die Gegenprobe unten gruen,
# und der Test haette den Fall, fuer den es ihn gibt, durchgelassen.
MITSCHNITT_SPALTEN = 109


def zu_breit(zeilen) -> list[str]:
    return [z for z in zeilen if len(z) > MITSCHNITT_SPALTEN]


def test_keine_ausgabezeile_ist_breiter_als_die_aufnahme(echte_ausgabe):
    breit = zu_breit(echte_ausgabe)
    assert not breit, (
        "Diese Zeilen brechen im Mitschnitt um und machen die Video-Aktion rot:\n"
        + "\n".join(f"{len(z)} Zeichen: {z}" for z in sorted(breit))
    )


def test_die_breitenpruefung_wuerde_eine_zu_lange_zeile_bemerken():
    """Gegenprobe: ohne sie belegt der Test oben nur, dass er gelaufen ist."""
    gerade_noch = "x" * MITSCHNITT_SPALTEN
    eins_zuviel = "x" * (MITSCHNITT_SPALTEN + 1)
    assert zu_breit([gerade_noch]) == []
    assert zu_breit([eins_zuviel]) == [eins_zuviel]


# ── Der Mitschnitt erfindet nichts ──────────────────────────────────────────

def test_jede_zeile_im_gif_stammt_aus_einem_echten_lauf(echte_ausgabe):
    quelle = REPO / "examples" / "brief-mahnung.md"
    erlaubt = set(echte_ausgabe)
    erlaubt |= {pfadtrenner_vereinheitlichen(z.strip())
                for z in quelle.read_text(encoding="utf-8").splitlines() if z.strip()}

    fremd = [z for z in mitgeschnittene_zeilen() if z not in erlaubt]
    assert not fremd, "Im Mitschnitt stehen Zeilen, die kein Lauf erzeugt:\n" + "\n".join(fremd[:10])


def test_die_pruefung_wuerde_eine_erfundene_zeile_bemerken(echte_ausgabe):
    """Gegenprobe: ein Satz, den die CLI nie schreibt, muss auffallen."""
    quelle = REPO / "examples" / "brief-mahnung.md"
    erlaubt = set(echte_ausgabe)
    erlaubt |= {pfadtrenner_vereinheitlichen(z.strip())
                for z in quelle.read_text(encoding="utf-8").splitlines() if z.strip()}
    assert "OK  verify: 99/99 Maße eingehalten" not in erlaubt


def test_der_lauf_endet_mit_der_abschlusszeile(echte_ausgabe):
    """Das Versprechen des GIFs — sie muss aus dem Programm kommen, nicht aus dem Tape."""
    assert any(re.fullmatch(r"OK\s+verify: \d+/\d+ Maße eingehalten", z) for z in echte_ausgabe)


def test_tape_zeigt_keine_feste_pruefzahl():
    """Die Zahl haengt am Layout — 30/30 hier, mehr bei anderen Briefen.

    Wer sie ins Tape schreibt, behauptet eine Konstante, die keine ist.
    """
    assert not re.search(r"\d+/\d+ Maße", TAPE.read_text(encoding="utf-8"))


# ── Das Tape zeigt nur Befehle, die es gibt ─────────────────────────────────

def test_tape_nennt_keinen_pypi_befehl():
    """`pipx install falzmarke` gibt es nicht — dieselbe Falle wie in der README."""
    nackt = re.compile(r"(?<![\w./-])(?:uvx\s+falzmarke\b|pipx\s+install\s+falzmarke\b)")
    assert not nackt.search(TAPE.read_text(encoding="utf-8"))


def test_tape_verweist_nur_auf_vorhandene_dateien():
    for befehl in sichtbare_befehle():
        for wort in befehl.split():
            if wort.endswith(".md"):
                assert (REPO / wort).is_file(), f"{wort} fehlt, wird aber im GIF gezeigt"


# ── Die Ausgaben halten die Budgets ─────────────────────────────────────────

@pytest.mark.skipif(not GIF.exists(), reason="GIF noch nicht aufgezeichnet")
def test_gif_bleibt_unter_der_grenze():
    assert GIF.stat().st_size <= GIF_GRENZE, f"{GIF.stat().st_size} Byte"


@pytest.mark.skipif(not (REPO / "docs/renders/demo.mp4").exists(), reason="MP4 fehlt")
def test_mp4_bleibt_unter_der_grenze():
    mp4 = REPO / "docs" / "renders" / "demo.mp4"
    assert mp4.stat().st_size <= MP4_GRENZE, f"{mp4.stat().st_size} Byte"


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe fehlt")
@pytest.mark.skipif(not (REPO / "docs/renders/demo.mp4").exists(), reason="MP4 fehlt")
def test_mp4_hat_die_masse_aus_dem_tape():
    soll = {}
    for zeile in TAPE.read_text(encoding="utf-8").splitlines():
        if treffer := re.match(r"Set (Width|Height) (\d+)", zeile.strip()):
            soll[treffer.group(1)] = int(treffer.group(2))
    ergebnis = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0",
         str(REPO / "docs" / "renders" / "demo.mp4")],
        capture_output=True, text=True,
    )
    breite, hoehe = (int(x) for x in ergebnis.stdout.strip().split(","))
    assert (breite, hoehe) == (soll["Width"], soll["Height"])
