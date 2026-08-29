"""Das Logo der Mailsignatur muss auf hellem UND dunklem Grund tragen (#154).

Der Text und die Trennlinie schalten um, sobald das Schema dunkel ist. Das Logo
kann das nicht — es ist ein Rasterbild. Bis hierher stand in der Anleitung, wer
ein Logo einschalte, moege eines waehlen, das auf beiden Gruenden traegt; das
Werkzeug pruefte es nicht. Diese Datei ist die Pruefung, und sie prueft sich
selbst mit: Zu jeder Aussage steht die Gegenrichtung daneben.

Die Testbilder sind hier **gebaut**, nicht gerendert. Ein gerendertes Logo waere
eine Aussage ueber genau dieses Bild; gebaute Flaechen sind eine Aussage ueber
die Messung. Der Fall aus dem Vorgang ist der dritte: viel Tinte, wenig Gruen.
"""

from __future__ import annotations

import shutil

import pytest
import yaml

from conftest import SKILL

from falzmarke import cli, farbe, lint

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

# Die Farben der Marke, dieselben Werte wie in docs/marke/erscheinungsbild.md.
TINTE = (0x12, 0x1E, 0x2F)
GRUEN = (0x3E, 0xB0, 0x57)
PAPIER = (0xFF, 0xFF, 0xFF)
#: Traegt auf beiden Gruenden — gemessen 3,95:1 hell und 4,22:1 dunkel.
MITTELGRAU = (0x80, 0x80, 0x80)


def _bild(pfad, flaechen, breite=20, hoehe=20):
    """Ein PNG aus waagerechten Streifen: [(farbe, anteil), …].

    `anteil` ist der Anteil an der Hoehe. So laesst sich „viel Tinte, wenig
    Gruen" genau einstellen — und damit die Grenze, an der die Pruefung kippt.
    """
    from PIL import Image

    bild = Image.new("RGBA", (breite, hoehe), (0, 0, 0, 0))
    y = 0
    for farbwert, anteil in flaechen:
        bis = min(hoehe, y + round(hoehe * anteil))
        for zeile in range(y, bis):
            for spalte in range(breite):
                bild.putpixel((spalte, zeile), (*farbwert, 255))
        y = bis
    pfad.parent.mkdir(parents=True, exist_ok=True)
    bild.save(pfad)
    return pfad


# ── Die Rechnung selbst ─────────────────────────────────────────────────────

def test_die_zahl_aus_dem_vorgang_stimmt():
    """1,01:1 — der Wert, mit dem #154 aufgemacht wurde."""
    assert round(farbe.kontrast(TINTE, farbe.GRUND_DUNKEL), 2) == 1.01


def test_und_die_gegenrichtung():
    """Ohne sie wuesste man nicht, ob 3,0:1 ueberhaupt jemand nimmt."""
    assert farbe.kontrast(TINTE, farbe.GRUND_HELL) >= farbe.SCHWELLE
    assert farbe.kontrast(PAPIER, farbe.GRUND_DUNKEL) >= farbe.SCHWELLE


def test_mittelgrau_traegt_auf_beiden():
    """Der Gegenfall zur Tinte: eine Farbe, die die Pruefung durchlaesst.

    Ohne sie koennte die Schwelle so hoch stehen, dass gar nichts sie nimmt —
    eine Pruefung, die immer rot ist, ist so wenig wert wie eine, die es nie ist.
    """
    for grund in (farbe.GRUND_HELL, farbe.GRUND_DUNKEL):
        assert farbe.kontrast(MITTELGRAU, grund) >= farbe.SCHWELLE


# ── Die Flaechenmessung ─────────────────────────────────────────────────────

def test_eine_flaeche_aus_tinte_traegt_nur_auf_hell(tmp_path):
    bild = _bild(tmp_path / "tinte.png", [(TINTE, 1.0)])
    assert farbe.tragender_anteil(bild, farbe.GRUND_HELL) == 1.0
    assert farbe.tragender_anteil(bild, farbe.GRUND_DUNKEL) == 0.0
    assert farbe.logo_grund_ohne_halt(bild) == ["dunklem"]


def test_eine_flaeche_aus_mittelgrau_traegt_auf_beiden(tmp_path):
    bild = _bild(tmp_path / "grau.png", [(MITTELGRAU, 1.0)])
    assert farbe.logo_grund_ohne_halt(bild) == []


def test_der_fall_aus_dem_vorgang_faellt_auf(tmp_path):
    """Viel Tinte, eine gruene Ecke — genau die Beschreibung in #154.

    Auf hellem Grund traegt beides. Auf dunklem bleibt das Gruen, und das sind
    hier 15 % der Flaeche: zu wenig.
    """
    bild = _bild(tmp_path / "logo.png", [(TINTE, 0.85), (GRUEN, 0.15)])
    assert farbe.logo_grund_ohne_halt(bild) == ["dunklem"]
    assert farbe.tragender_anteil(bild, farbe.GRUND_DUNKEL) == pytest.approx(0.15)


def test_die_haelfte_ist_die_grenze(tmp_path):
    """Die Schwelle wirkt wirklich dort, wo sie steht — beide Seiten davon.

    Gemischt wird Tinte mit Mittelgrau: Beide tragen auf hellem Grund, nur das
    Grau auch auf dunklem. Damit variiert genau EINE Achse, und der Umschlag
    liegt an der Flaeche statt an der zweiten Farbe.
    """
    knapp_drunter = _bild(tmp_path / "a.png", [(TINTE, 0.55), (MITTELGRAU, 0.45)])
    knapp_drueber = _bild(tmp_path / "b.png", [(TINTE, 0.45), (MITTELGRAU, 0.55)])
    assert farbe.logo_grund_ohne_halt(knapp_drunter) == ["dunklem"]
    assert farbe.logo_grund_ohne_halt(knapp_drueber) == []


def test_durchsichtiges_wird_ueber_den_grund_gerechnet(tmp_path):
    """Ein halbdurchsichtiges Weiss auf Dunkel ist Grau, nicht Weiss.

    Naehme die Messung die eigene Farbe des Punktes, ginge jedes Logo mit
    weichem Rand als tragend durch — und beim Empfaenger verschwaende es.
    """
    from PIL import Image

    pfad = tmp_path / "weich.png"
    bild = Image.new("RGBA", (10, 10), (0xFF, 0xFF, 0xFF, 140))
    bild.save(pfad)
    # 140/255 Weiss ueber #1E1E1E ergibt ~#9C9C9C: traegt noch.
    # Dieselbe Deckung ueber Weiss ergibt fast Weiss: traegt nicht.
    assert farbe.tragender_anteil(pfad, farbe.GRUND_DUNKEL) == 1.0
    assert farbe.tragender_anteil(pfad, farbe.GRUND_HELL) == 0.0


def test_ganz_durchsichtige_punkte_zaehlen_nicht(tmp_path):
    """Sonst bestimmte die Bildgroesse das Ergebnis und nicht das Bild."""
    from PIL import Image

    pfad = tmp_path / "rand.png"
    bild = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    for y in range(4):
        for x in range(20):
            bild.putpixel((x, y), (*MITTELGRAU, 255))
    bild.save(pfad)
    # 20 % der Bildpunkte sind sichtbar — und die tragen vollstaendig.
    assert farbe.tragender_anteil(pfad, farbe.GRUND_HELL) == 1.0
    assert farbe.logo_grund_ohne_halt(pfad) == []


# ── Und der Linter meldet es ────────────────────────────────────────────────

def _profil_mit(tmp_path, bilddatei) -> tuple[dict, object]:
    ziel = tmp_path / "profiles"
    if not ziel.exists():
        shutil.copytree(PROFILE, ziel)
    pfad = ziel / "example.yaml"
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    profil["email"]["logo"] = f"assets/{bilddatei.name}"
    shutil.copy2(bilddatei, ziel / "assets" / bilddatei.name)
    pfad.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
    return profil, pfad


def _befunde(profil, pfad) -> list[str]:
    bericht = lint.Bericht()
    lint.pruefe_email_profil(profil, bericht, pfad)
    return [b.regel for b in bericht.befunde]


def test_der_linter_meldet_ein_logo_das_nur_hell_traegt(tmp_path):
    bild = _bild(tmp_path / "quelle" / "tinte.png", [(TINTE, 1.0)])
    assert "email.logo_kontrast" in _befunde(*_profil_mit(tmp_path, bild))


def test_der_linter_schweigt_bei_einem_logo_das_beide_traegt(tmp_path):
    """Gegenprobe. Ohne sie koennte die Regel jedes Logo melden."""
    bild = _bild(tmp_path / "quelle" / "grau.png", [(MITTELGRAU, 1.0)])
    assert "email.logo_kontrast" not in _befunde(*_profil_mit(tmp_path, bild))


def test_ohne_logo_gibt_es_nichts_zu_melden(tmp_path):
    ziel = tmp_path / "profiles"
    shutil.copytree(PROFILE, ziel)
    pfad = ziel / "example.yaml"
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    assert profil["email"]["logo"] is False, "das Beispielprofil fuehrt kein Logo"
    assert "email.logo_kontrast" not in _befunde(profil, pfad)


def test_ein_unlesbares_bild_ist_kein_stilles_ok(tmp_path):
    """NICHT GEPRUEFT darf nicht wie gruen aussehen.

    Eine kaputte Datei faellt sonst erst beim Empfaenger auf — und dort als
    fehlendes Logo, ohne Hinweis worauf.
    """
    ziel = tmp_path / "profiles"
    shutil.copytree(PROFILE, ziel)
    kaputt = ziel / "assets" / "kaputt.png"
    kaputt.write_bytes(b"\x89PNG\r\n\x1a\n" + b"nicht wirklich ein Bild")
    pfad = ziel / "example.yaml"
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    profil["email"]["logo"] = "assets/kaputt.png"
    pfad.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
    assert "email.logo_kontrast" in _befunde(profil, pfad)


def test_ohne_profilpfad_bleibt_die_pruefung_stumm(tmp_path):
    """Der aeltere Aufrufweg ohne Pfad darf nicht abstuerzen.

    Er kann nichts messen — eine Profildatei ohne Ort hat keine Nachbardateien.
    Das ist der einzige Fall, in dem Schweigen richtig ist.
    """
    bild = _bild(tmp_path / "quelle" / "tinte.png", [(TINTE, 1.0)])
    profil, _ = _profil_mit(tmp_path, bild)
    bericht = lint.Bericht()
    lint.pruefe_email_profil(profil, bericht)
    assert "email.logo_kontrast" not in [b.regel for b in bericht.befunde]


# ── Die Regel steht auch im Regelwerk ───────────────────────────────────────

def test_die_regel_ist_eingetragen():
    from falzmarke import regeln

    treffer = [r for r in regeln.alle() if r["id"] == "email.logo_kontrast"]
    assert treffer, "die Regel fehlt in regeln/email.yaml"
    assert treffer[0]["wirkung"] == "warnung"


def test_die_beispielnachricht_bleibt_ohne_befund():
    """Der Bestand aendert sich durch die neue Regel nicht."""
    from conftest import EMAIL_BEISPIELE

    for beispiel in EMAIL_BEISPIELE:
        bericht = cli.linte(beispiel, profil_verzeichnis=PROFILE)
        assert "email.logo_kontrast" not in [b.regel for b in bericht.befunde], beispiel.name
