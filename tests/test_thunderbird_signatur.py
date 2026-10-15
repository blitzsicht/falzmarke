"""Die Signatur im Thunderbird-Entwurf kommt nur einmal (ADR 0050).

ANLASS (15.10.2026): Beim Betreiber tragen alle Firmen-Identitäten in
Thunderbird eine Signatur — per `user.js` aus derselben Datei wie das
falzmarke-Profil. Thunderbird setzt sie unter den Rumpf, den `-compose body=`
mitbringt, und der trug die aus dem Profil schon: zweimal dieselbe Signatur.

Kein Test hier liest das Thunderbird-Profil des Rechners. Jeder baut sich ein
Attrappenverzeichnis unter `tmp_path` — `profiles.ini`, `prefs.js`, `user.js`,
eine Signaturdatei — und reicht es als `thunderbird_ordner` durch. Gestartet
wird nichts: `pgrep` und der `-compose`-Aufruf werden eingespeist und
mitgeschrieben.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import REPO
from falzmarke import cli, eml, oeffnen, pruefung_eml

ABSENDER = "muster@example.de"
TB_BINARY = "/Applications/Thunderbird.app/Contents/MacOS/thunderbird"
BEISPIELE = ["email-signatur", "email-logo", "email-mahnung"]


# ── Werkzeug ────────────────────────────────────────────────────────────────

def _prefs(werte: dict) -> str:
    return "".join(f"user_pref({json.dumps(k)}, {json.dumps(v)});\n" for k, v in werte.items())


def _grundwerte(signaturdatei: Path | None = None, **identitaet) -> dict:
    """Zwei Konten, je eine Identität; `id1` trägt die Adresse des Beispielprofils."""
    werte = {
        "mail.accountmanager.accounts": "account1,account2",
        "mail.account.account1.identities": "id1",
        "mail.account.account2.identities": "id2",
        "mail.identity.id1.useremail": ABSENDER,
        "mail.identity.id2.useremail": "andere@example.org",
    }
    if signaturdatei is not None:
        werte["mail.identity.id1.attach_signature"] = True
        werte["mail.identity.id1.sig_file"] = str(signaturdatei)
    for name, wert in identitaet.items():
        werte[f"mail.identity.id1.{name}"] = wert
    return werte


def _attrappe(tmp_path: Path, prefs: dict, user: dict | None = None,
              altprofil: dict | None = None) -> Path:
    """Ein Thunderbird-Profilordner wie beim Betreiber am 15.10.2026.

    `profiles.ini` nennt zwei Profile: Das der Installation (`[Install…]`)
    ist das echte; ein zweites trägt noch `Default=1` von früher. `altprofil`
    füllt dieses zweite — so lässt sich prüfen, dass das richtige gelesen wird.
    """
    ordner = tmp_path / "Thunderbird"
    profil = ordner / "Profiles" / "abcd1234.default-release"
    alt = ordner / "Profiles" / "wxyz9876.default"
    profil.mkdir(parents=True)
    alt.mkdir(parents=True)
    (ordner / "profiles.ini").write_text(
        "[General]\nStartWithLastProfile=1\nVersion=2\n\n"
        "[Profile0]\nName=default-release\nIsRelative=1\n"
        "Path=Profiles/abcd1234.default-release\n\n"
        "[Install712DAF5A23ABECDC]\nDefault=Profiles/abcd1234.default-release\nLocked=1\n\n"
        "[Profile1]\nName=default\nIsRelative=1\nPath=Profiles/wxyz9876.default\nDefault=1\n",
        encoding="utf-8")
    (profil / "prefs.js").write_text("// Mozilla User Preferences\n\n" + _prefs(prefs),
                                     encoding="utf-8")
    if user is not None:
        (profil / "user.js").write_text(_prefs(user), encoding="utf-8")
    if altprofil is not None:
        (alt / "prefs.js").write_text(_prefs(altprofil), encoding="utf-8")
    return ordner


@pytest.fixture
def signaturdatei(tmp_path) -> Path:
    datei = tmp_path / "signatur" / "firma.html"
    datei.parent.mkdir()
    datei.write_text("<html><body><p>Firma GmbH</p></body></html>", encoding="utf-8")
    return datei


class Thunderbird:
    """Läuft, nimmt den Auftrag an, startet nichts — und merkt sich die Zeile."""

    def __init__(self):
        self.aufrufe: list[list[str]] = []

    def __call__(self, argv, **_kwargs):
        self.aufrufe.append(list(argv))
        if argv[0] == "pgrep":
            return subprocess.CompletedProcess(argv, 0, stdout="4711\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    @property
    def rumpf(self) -> str:
        (aufruf,) = [a for a in self.aufrufe if "-compose" in a]
        return oeffnen.compose_zerlegen(aufruf[-1])["body"]


def _beispiel(tmp_path: Path, name: str) -> tuple[Path, dict, str]:
    """Die echte Kette bis zu den Feldern: Beispiel → `.eml` → `entwurfsfelder`."""
    quelle = REPO / "examples" / "email" / f"{name}.md"
    eml_pfad, _, unterschrift = cli._setze_email(quelle, tmp_path / "aus" / name)
    felder = eml.entwurfsfelder(eml_pfad)
    felder["signatur_html"] = unterschrift
    return eml_pfad, felder, unterschrift


def _entwurf(felder: dict, ordner: Path) -> tuple[oeffnen.Entwurfslage, Thunderbird]:
    tb = Thunderbird()
    lage = oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0"},
                           laufen=tb, binaer=lambda: TB_BINARY, thunderbird_ordner=ordner)
    assert lage.programm == "Thunderbird", lage
    return lage, tb


def _signatur_im_rumpf(unterschrift: str, felder: dict) -> str:
    """Die Signatur so, wie sie im `body=`-Wert steht — eingebettet und auf einer Zeile."""
    return oeffnen.rumpf_fuer_compose(oeffnen.eingebettet(unterschrift, felder["inline"]))


# ── Die vier Pflichtfälle, an allen drei Signaturformen ─────────────────────
#
# `email-signatur` bringt eine fertige Signatur mit (#275), `email-logo` baut
# sie als Tabelle mit Logo, `email-mahnung` als Absätze ohne Logo.

@pytest.mark.parametrize("name", BEISPIELE)
def test_identitaet_mit_signatur_der_rumpf_hat_keine(tmp_path, signaturdatei, name):
    eml_pfad, felder, unterschrift = _beispiel(tmp_path, name)
    ordner = _attrappe(tmp_path, _grundwerte(signaturdatei))
    lage, tb = _entwurf(felder, ordner)

    assert lage.signatur.zustand == "thunderbird", lage.signatur
    assert (lage.signatur.identitaet, lage.signatur.quelle) == ("id1", str(signaturdatei))
    rumpf = tb.rumpf
    assert _signatur_im_rumpf(unterschrift, felder) not in rumpf
    # Was nicht Signatur ist, bleibt — die Grußformel zuerst.
    assert "Mit freundlichen Grüßen" in rumpf
    assert oeffnen._rumpf_stimmt(rumpf) is None


@pytest.mark.parametrize("name", BEISPIELE)
def test_gegenprobe_identitaet_ohne_signatur_der_rumpf_behaelt_sie(tmp_path, name):
    _, felder, unterschrift = _beispiel(tmp_path, name)
    ordner = _attrappe(tmp_path, _grundwerte())
    lage, tb = _entwurf(felder, ordner)

    assert lage.signatur.zustand == "keine", lage.signatur
    assert tb.rumpf.count(_signatur_im_rumpf(unterschrift, felder)) == 1


def test_unbekannte_absenderadresse_behaelt_die_signatur(tmp_path, signaturdatei):
    _, felder, unterschrift = _beispiel(tmp_path, "email-signatur")
    werte = _grundwerte(signaturdatei)
    werte["mail.identity.id1.useremail"] = "jemand-anders@example.de"
    lage, tb = _entwurf(felder, _attrappe(tmp_path, werte))

    assert lage.signatur.zustand == "unbestimmt"
    assert ABSENDER in lage.signatur.grund
    assert tb.rumpf.count(_signatur_im_rumpf(unterschrift, felder)) == 1


def test_user_js_ueberschreibt_prefs_js(tmp_path, signaturdatei):
    """`prefs.js` sagt „keine“, `user.js` hängt die Datei an — `user.js` gewinnt."""
    _, felder, unterschrift = _beispiel(tmp_path, "email-signatur")
    prefs = _grundwerte(attach_signature=False)
    user = {"mail.identity.id1.attach_signature": True,
            "mail.identity.id1.sig_file": str(signaturdatei)}
    lage, tb = _entwurf(felder, _attrappe(tmp_path, prefs, user=user))

    assert lage.signatur.zustand == "thunderbird", lage.signatur
    assert _signatur_im_rumpf(unterschrift, felder) not in tb.rumpf


def test_gegenprobe_user_js_nimmt_die_signatur_auch_weg(tmp_path, signaturdatei):
    """Die andere Richtung: `prefs.js` hängt an, `user.js` schaltet ab."""
    _, felder, unterschrift = _beispiel(tmp_path, "email-signatur")
    user = {"mail.identity.id1.attach_signature": False}
    lage, tb = _entwurf(felder, _attrappe(tmp_path, _grundwerte(signaturdatei), user=user))

    assert lage.signatur.zustand == "keine", lage.signatur
    assert tb.rumpf.count(_signatur_im_rumpf(unterschrift, felder)) == 1


# ── Weitere Fälle der Erkennung ─────────────────────────────────────────────

def test_ein_signaturtext_zaehlt_wie_eine_datei(tmp_path):
    _, felder, unterschrift = _beispiel(tmp_path, "email-mahnung")
    werte = _grundwerte(htmlSigText="<b>Erika</b>")
    lage, tb = _entwurf(felder, _attrappe(tmp_path, werte))

    assert lage.signatur.zustand == "thunderbird"
    assert lage.signatur.quelle == "Signaturtext der Identität"
    assert _signatur_im_rumpf(unterschrift, felder) not in tb.rumpf


def test_eine_unlesbare_signaturdatei_laesst_die_signatur_stehen(tmp_path):
    _, felder, unterschrift = _beispiel(tmp_path, "email-mahnung")
    werte = _grundwerte(tmp_path / "gibt-es-nicht.html")
    lage, tb = _entwurf(felder, _attrappe(tmp_path, werte))

    assert lage.signatur.zustand == "unbestimmt"
    assert "nicht lesbar" in lage.signatur.grund
    assert tb.rumpf.count(_signatur_im_rumpf(unterschrift, felder)) == 1


def test_das_profil_der_installation_gilt_nicht_das_alte_default(tmp_path, signaturdatei):
    """Beim Betreiber trägt ein altes Profil noch `Default=1`. Gelesen werden muss
    das aus `[Install…]` — hier das ohne Signatur, das alte hätte eine."""
    _, felder, unterschrift = _beispiel(tmp_path, "email-signatur")
    ordner = _attrappe(tmp_path, _grundwerte(), altprofil=_grundwerte(signaturdatei))
    lage, tb = _entwurf(felder, ordner)

    assert lage.signatur.zustand == "keine", lage.signatur
    assert oeffnen.thunderbird_standardprofil(ordner).name == "abcd1234.default-release"


def test_eine_identitaet_ohne_konto_zaehlt_nicht(tmp_path, signaturdatei):
    """Thunderbird wählt mit `from=` nur unter Identitäten eingerichteter Konten."""
    _, felder, _ = _beispiel(tmp_path, "email-signatur")
    werte = _grundwerte(signaturdatei)
    werte["mail.accountmanager.accounts"] = "account2"
    lage, _ = _entwurf(felder, _attrappe(tmp_path, werte))
    assert lage.signatur.zustand == "unbestimmt"


def test_ohne_profilordner_bleibt_es_beim_alten(tmp_path):
    _, felder, unterschrift = _beispiel(tmp_path, "email-signatur")
    lage, tb = _entwurf(felder, tmp_path / "kein-thunderbird")
    assert lage.signatur.zustand == "unbestimmt"
    assert tb.rumpf.count(_signatur_im_rumpf(unterschrift, felder)) == 1


def test_ohne_bekannte_profilsignatur_wird_nichts_herausgeschnitten(tmp_path, signaturdatei):
    """Wer `entwurf` ohne `signatur_html` aufruft, bekommt den alten Rumpf und den Hinweis."""
    _, felder, unterschrift = _beispiel(tmp_path, "email-signatur")
    del felder["signatur_html"]
    lage, tb = _entwurf(felder, _attrappe(tmp_path, _grundwerte(signaturdatei)))
    assert lage.signatur.zustand == "unbestimmt"
    assert tb.rumpf.count(_signatur_im_rumpf(unterschrift, felder)) == 1


# ── Die Datei bleibt, wie sie war ───────────────────────────────────────────

def test_die_eml_behaelt_die_signatur_und_besteht_verify(tmp_path, signaturdatei):
    eml_pfad, felder, unterschrift = _beispiel(tmp_path, "email-signatur")
    vorher = eml_pfad.read_bytes()
    lage, _ = _entwurf(felder, _attrappe(tmp_path, _grundwerte(signaturdatei)))

    assert lage.signatur.zustand == "thunderbird"
    assert eml_pfad.read_bytes() == vorher
    assert eml.entwurfsfelder(eml_pfad)["html"].count("\n" + unterschrift) == 1
    assert pruefung_eml.pruefe(eml_pfad).ok


# ── Die Prüfung vor dem Aufruf meldet weiter ────────────────────────────────

def test_compose_stimmt_meldet_einen_falschen_rumpf_auch_ohne_signatur(tmp_path,
                                                                       signaturdatei):
    """`_compose_stimmt` hält die Zeile gegen den Rumpf OHNE Signatur — und muss
    rot werden, wenn darin etwas anderes steht als vorgesehen."""
    _, felder, _ = _beispiel(tmp_path, "email-mahnung")
    _, tb = _entwurf(felder, _attrappe(tmp_path, _grundwerte(signaturdatei)))
    rumpf = tb.rumpf
    vorgabe = {**felder, "html": rumpf}
    zeile = oeffnen.compose_argumente(vorgabe, [])[1]
    assert oeffnen._compose_stimmt(zeile, vorgabe, []) is None

    falsch = zeile.replace("Mit freundlichen Grüßen", "Mit freundlichen Grüssen")
    assert falsch != zeile, "die Sabotage griff nicht"
    assert "Rumpf" in (oeffnen._compose_stimmt(falsch, vorgabe, []) or "")


# ── Am Befehl ───────────────────────────────────────────────────────────────

def _befehl(tmp_path, monkeypatch, capsys, ordner: Path):
    """`falzmarke email … --oeffnen` mit Attrappen statt Thunderbird und Profil."""
    tb = Thunderbird()
    echt = oeffnen.entwurf
    monkeypatch.setattr(oeffnen, "entwurf", lambda felder, **k: echt(
        felder, plattform="darwin", umgebung={"DISPLAY": ":0"}, laufen=tb,
        binaer=lambda: TB_BINARY, thunderbird_ordner=ordner, **k))
    quelle = REPO / "examples" / "email" / "email-signatur.md"
    code = cli.main(["email", str(quelle), "-o", str(tmp_path / "aus" / "mail"), "--oeffnen"])
    return code, capsys.readouterr(), tb


def test_der_befehl_nennt_die_signatur_aus_thunderbird(tmp_path, monkeypatch, capsys,
                                                         signaturdatei):
    code, ausgabe, tb = _befehl(tmp_path, monkeypatch, capsys,
                                _attrappe(tmp_path, _grundwerte(signaturdatei)))
    assert code == 0
    zeilen = [z for z in ausgabe.out.splitlines() if z.startswith("OK  Signatur aus Thunderbird")]
    assert len(zeilen) == 1, ausgabe.out
    assert "id1" in zeilen[0] and ABSENDER in zeilen[0] and str(signaturdatei) in zeilen[0]
    assert "Signatur des Kontos" not in ausgabe.err
    assert "Termin vereinbaren" not in tb.rumpf


def test_gegenprobe_ohne_bestimmbare_identitaet_bleibt_der_hinweis(tmp_path, monkeypatch,
                                                                   capsys):
    code, ausgabe, tb = _befehl(tmp_path, monkeypatch, capsys, tmp_path / "kein-thunderbird")
    assert code == 0
    assert "Signatur aus Thunderbird" not in ausgabe.out
    assert "Signatur des Kontos" in ausgabe.err
    assert "nicht bestimmt" in ausgabe.err
    assert "Termin vereinbaren" in tb.rumpf
