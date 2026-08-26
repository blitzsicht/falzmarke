"""Ein öffentliches Issue beschreibt das Werkzeug, nicht unsere Arbeitsweise.

ADR 0031. Die Regel dafür gab es für Dateien schon; bei Issues riss sie
trotzdem, weil sie nur gelesen werden musste. Diese Tests halten den Wächter
gegen den Zustand, den er hätte finden müssen.

Zwei Zusicherungen sind hier wichtiger als die Trefferzahl:

1. Er wird **rot am alten Zustand** — sonst wüsste man nur, dass er grün ist.
2. Er **zitiert den Fund nicht**. Das Aktionsprotokoll eines öffentlichen
   Repositorys ist öffentlich; eine Meldung mit Fundtext verdoppelt den Fund.
"""

from __future__ import annotations

import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import oeffentlichkeit as hygiene                                 # noqa: E402


GEHEIM_OPS = "blitzsicht-ops"
GEHEIM_PFAD = "docs/falzmarke-intern/quellenpruefung-2026-08-25/"


def _issue(nummer, titel="Ein Titel", body="", comments=()):
    return {"number": nummer, "title": titel, "body": body, "comments": list(comments)}


def _sauber():
    return [
        _issue(1, "Briefkörper bleibt im Satzspiegel", "Auf jeder Seite, nicht nur der ersten."),
        _issue(2, "Als Paket veröffentlichen", "Damit `pip install` genügt.",
               ["Die Belege liegen beim Maintainer vor."]),
    ]


def _wie_es_war():
    """Der Wortlaut vor der Bereinigung vom 26.08.2026."""
    return _sauber() + [
        _issue(12, "Normabgleich", "",
               [f"Belege intern in `{GEHEIM_OPS}`, `{GEHEIM_PFAD}`."]),
        _issue(36, "Entscheidung: Orchestrierung innen oder außen?",
               "Arbeitspakete liegen im OPS-Repo und verweisen per `### Code-Repo` hierher."),
    ]


# ── Trennschärfe: rot am alten Stand, grün am neuen ─────────────────────────

def test_der_alte_zustand_wird_gefunden():
    """Die Gegenprobe. Ohne sie belegt der Test darunter nur, dass nichts anschlägt."""
    befunde = hygiene.pruefe(_wie_es_war())
    getroffen = {b["nummer"] for b in befunde}
    assert getroffen == {12, 36}, f"erwartet 12 und 36, gefunden {getroffen}"


def test_der_bereinigte_zustand_ist_still():
    assert hygiene.pruefe(_sauber()) == []


def test_der_belegverweis_ohne_ort_bleibt_erlaubt():
    """ADR 0031 verbietet den Ort, nicht die Aussage. Ein Wächter, der auch
    „liegt beim Maintainer vor" anstriche, würde die Belegkultur beschädigen."""
    assert hygiene.pruefe([_issue(3, "Quellenlage", "",
                                  ["Die Belege liegen beim Maintainer vor; sie sind nicht "
                                   "frei lizenziert und gehören nicht in dieses Repository."])]) == []


@pytest.mark.parametrize("text, kennung", [
    ("siehe `irgendwas-ops`", "ops-repo"),
    ("in `projekt-intern/`", "interner-ordner"),
    ("steht in auftrag-backlog-roadmap.md", "auftragsdatei"),
    ("liegt unter thoughts/shared", "auftragsordner"),
    ("Pfad /Volumes/Arbeit/x", "lokaler-pfad"),
    ("### Code-Repo", "arbeitspaket"),
])
def test_jedes_muster_greift_einzeln(text, kennung):
    """Sonst trüge ein einzelnes Muster die ganze Prüfung, und die übrigen
    könnten kaputt sein, ohne dass ein Test rot wird."""
    befunde = hygiene.pruefe([_issue(1, "T", text)])
    assert befunde, f"{kennung}: nichts gefunden in {text!r}"
    assert kennung in {t["kennung"] for t in befunde[0]["treffer"]}


# ── Der Bericht darf den Fund nicht verraten ────────────────────────────────

def test_der_bericht_zitiert_den_fund_nicht():
    """Der Kern. Action-Protokolle öffentlicher Repositorys sind öffentlich."""
    befunde = hygiene.pruefe(_wie_es_war())
    text = hygiene.bericht(befunde, geprueft=4)

    assert GEHEIM_OPS not in text, "Der Bericht nennt das interne Repository im Klartext"
    assert GEHEIM_PFAD not in text, "Der Bericht nennt den internen Pfad im Klartext"
    assert "Code-Repo" not in text, "Der Bericht zitiert die gefundene Zeile"


def test_der_bericht_nennt_trotzdem_was_zu_tun_ist():
    """Gegenprobe: ein Bericht, der gar nichts sagt, bestünde den Test darüber
    ebenfalls — und wäre nutzlos."""
    text = hygiene.bericht(hygiene.pruefe(_wie_es_war()), geprueft=4)
    assert "#12" in text and "#36" in text, "Ohne Nummern ist der Befund nicht verfolgbar"
    assert "ops-repo" in text, "Ohne Musterkennung weiß niemand, wonach zu suchen ist"


def test_zusatzbegriffe_aus_der_umgebung_erscheinen_nie_im_bericht(monkeypatch):
    """Die Eigennamen kommen aus einem Secret. Stünden sie im Bericht, wäre das
    Secret über das öffentliche Protokoll wieder draußen."""
    monkeypatch.setenv("HYGIENE_ZUSATZ", "Zaubername,Kundenname")
    befunde = hygiene.pruefe([_issue(5, "T", "Das betrifft Zaubername direkt.")])
    assert befunde, "Der Zusatzbegriff wurde nicht gefunden"
    text = hygiene.bericht(befunde, geprueft=1)
    assert "Zaubername" not in text and "Kundenname" not in text


def test_ohne_zusatzliste_greifen_nur_die_formmuster(monkeypatch):
    monkeypatch.delenv("HYGIENE_ZUSATZ", raising=False)
    assert hygiene.pruefe([_issue(5, "T", "Das betrifft Zaubername direkt.")]) == []


# ── Kein stiller Erfolg über die leere Menge ────────────────────────────────

def test_keine_issues_ist_kein_gruenes_ergebnis():
    with pytest.raises(hygiene.Hygienefehler):
        hygiene.pruefe([])


def test_die_probe_traegt_ueberhaupt_text():
    """Positivprobe auf die Testdaten selbst."""
    assert sum(len(v["body"]) + sum(map(len, v["comments"])) for v in _wie_es_war()) > 100
