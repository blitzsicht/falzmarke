"""Die Homepage-Domain steht fest im Repository, nicht in einer undokumentierten Variable.

WARUM ES DAS GIBT

Bis zum 30.08.2026 las `scripts/repo-einstellungen.sh` die Domain ausschließlich aus
`FALZMARKE_HOMEPAGE`. Leer heißt „überschreib die Homepage mit der Release-Seite“ — und
FALZMARKE_HOMEPAGE kam im gesamten Repository nur an den zwei Stellen im Skript selbst
vor. Wer das Skript ohne die Variable fuhr, verlor damit unbemerkt den Verweis auf
falzmarke.com, obwohl die Domain die ganze Zeit HTTP 200 antwortete (Issue #199).

Diese Tests prüfen die Entscheidungslogik aus `scripts/homepage.py` (netzwerkfrei, über
eine injizierte `pruefen`-Funktion) und halten am echten Skripttext fest, dass der
Default jetzt im Repository steht und ein Rückfall nicht mehr still bleibt.
"""

from __future__ import annotations

import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import homepage                                                   # noqa: E402

SKRIPT = REPO / "scripts" / "repo-einstellungen.sh"
REPO_NAME = "blitzsicht/falzmarke"
RELEASE_SEITE = "https://github.com/blitzsicht/falzmarke/releases/latest"


def _immer(antwort: bool):
    return lambda url: antwort


# ── Die Entscheidungsfunktion, netzwerkfrei ─────────────────────────────────

def test_erreichbare_domain_wird_gesetzt():
    homepage_, meldung = homepage.bestimme(
        REPO_NAME, "https://falzmarke.com", "", pruefen=_immer(True)
    )
    assert homepage_ == "https://falzmarke.com"
    assert "wird als Homepage gesetzt" in meldung


def test_unerreichbare_domain_faellt_auf_die_release_seite_zurueck():
    homepage_, meldung = homepage.bestimme(
        REPO_NAME, "https://falzmarke.com", "", pruefen=_immer(False)
    )
    assert homepage_ == RELEASE_SEITE
    assert "Release-Seite" in meldung


def test_gegenprobe_die_pruefung_wuerde_eine_erreichbare_domain_erkennen():
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass es EINE Ausgabe
    gibt — nicht, dass `pruefen()` tatsächlich über Erfolg/Rückfall entscheidet."""
    homepage_, _ = homepage.bestimme(
        REPO_NAME, "https://falzmarke.com", "", pruefen=_immer(True)
    )
    assert homepage_ != RELEASE_SEITE


# ── Der Rückfall bleibt nicht mehr still ────────────────────────────────────

def test_rueckfall_ohne_vorherige_homepage_ist_nur_ein_hinweis():
    """Gab es vorher keine (oder schon die Release-Seite als) Homepage, ist der
    Rückfall der Normalfall — keine Warnung nötig."""
    _, meldung = homepage.bestimme(
        REPO_NAME, "https://falzmarke.com", "", pruefen=_immer(False)
    )
    assert "WARNUNG" not in meldung

    _, meldung_release = homepage.bestimme(
        REPO_NAME, "https://falzmarke.com", RELEASE_SEITE, pruefen=_immer(False)
    )
    assert "WARNUNG" not in meldung_release


def test_rueckfall_trotz_vorher_gesetzter_echter_domain_ist_eine_warnung():
    """Das ist genau der Vorfall aus Issue #199: eine bereits gesetzte, echte
    Homepage wird durch den Rückfall ersetzt — das muss auffallen, nicht nur
    protokolliert werden."""
    homepage_, meldung = homepage.bestimme(
        REPO_NAME, "https://falzmarke.com", "https://falzmarke.com", pruefen=_immer(False)
    )
    assert homepage_ == RELEASE_SEITE
    assert meldung.startswith("WARNUNG:")
    assert "https://falzmarke.com" in meldung


def test_gegenprobe_ohne_rueckfall_gibt_es_keine_warnung():
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass es *irgendwann*
    eine Warnung gibt — nicht, dass sie am Rückfall selbst hängt."""
    _, meldung = homepage.bestimme(
        REPO_NAME, "https://falzmarke.com", "https://falzmarke.com", pruefen=_immer(True)
    )
    assert "WARNUNG" not in meldung


def test_release_seite_haengt_am_repo():
    assert homepage.release_seite("a/b") == "https://github.com/a/b/releases/latest"


# ── domain_antwortet: die echte Netzwerkprüfung, gegen einen echten Server ──


def test_domain_antwortet_erkennt_eine_antwortende_adresse():
    """Kein Mock — ein echter, garantiert erreichbarer Endpunkt (PyPI-JSON-API,
    dieselbe Domain, die die CI ohnehin für test_installationswege.py braucht)."""
    assert homepage.domain_antwortet("https://pypi.org/pypi/falzmarke/json") is True


def test_domain_antwortet_erkennt_eine_nicht_aufloesbare_adresse():
    """Gegenprobe zur echten Prüfung: eine Domain, die es nicht gibt, muss False
    liefern — nicht nur eine, deren Antwort so vorbereitet wurde."""
    assert homepage.domain_antwortet("https://diese-domain-gibt-es-nicht.invalid") is False


# ── Das Skript: Default im Repository, kein stiller Rückfall ────────────────


def test_skript_hat_die_domain_als_konstante():
    text = SKRIPT.read_text(encoding="utf-8")
    assert 'STANDARD_HOMEPAGE="https://falzmarke.com"' in text
    assert 'HOMEPAGE_WUNSCH="${FALZMARKE_HOMEPAGE:-$STANDARD_HOMEPAGE}"' in text


def test_skript_faellt_ohne_variable_nicht_mehr_auf_leerstring_zurueck():
    """Die alte Falle: `${FALZMARKE_HOMEPAGE:-}` — leer heißt Rückfall auf die
    Release-Seite. Ohne diesen Test könnte die Konstante von oben danebenstehen,
    ohne dass HOMEPAGE_WUNSCH sie tatsächlich verwendet."""
    text = SKRIPT.read_text(encoding="utf-8")
    assert '${FALZMARKE_HOMEPAGE:-}"' not in text


def test_skript_ruft_die_entscheidungslogik_auf():
    text = SKRIPT.read_text(encoding="utf-8")
    assert "python3 scripts/homepage.py" in text
    assert "--bisher" in text


def test_skript_fragt_die_bisherige_homepage_ab():
    """Ohne den bisherigen Wert kann scripts/homepage.py einen stillen Rückfall
    nicht von einem lauten unterscheiden — die Warnlogik bräuchte ihn sonst nicht."""
    text = SKRIPT.read_text(encoding="utf-8")
    assert "repos/$REPO\" --jq '.homepage" in text


def test_meldung_wird_vor_dem_anwenden_gezeigt():
    """Trockenlauf-Anforderung aus dem Issue: Die Homepage, die gesetzt würde,
    steht vor der Zeile, die sie tatsächlich anwendet."""
    text = SKRIPT.read_text(encoding="utf-8")
    meldung = text.index('hinweis "$HOMEPAGE_MELDUNG"')
    anwendung = text.index('--homepage "$HOMEPAGE"')
    assert meldung < anwendung


# ── Positionierung: die Beschreibung führt jetzt mit der Prüfung ────────────


def test_beschreibung_nennt_die_pruefung_vor_dem_massenmerkmal():
    """Issue #199, Original-Punkt 3: 'DIN-5008-Briefe aus Markdown' gibt es laut
    Messung achtmal auf GitHub, das Nachmessen am fertigen PDF laut derselben
    Messung nirgends. Die Beschreibung muss deshalb mit der Prüfung beginnen,
    nicht mit dem, was es schon gibt."""
    text = SKRIPT.read_text(encoding="utf-8")
    zeile = next(z for z in text.splitlines() if z.startswith("BESCHREIBUNG="))
    pos_pruefung = zeile.index("geprüft")
    pos_markdown = zeile.index("DIN-5008-Briefe aus Markdown")
    assert pos_pruefung < pos_markdown, zeile


def test_gegenprobe_die_alte_beschreibung_haette_den_test_oben_nicht_bestanden():
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass beide Wörter
    irgendwo in der Zeile stehen — nicht, dass die Reihenfolge wirklich geprüft
    wird."""
    alte_zeile = (
        'BESCHREIBUNG="DIN-5008-Briefe aus Markdown — als PDF/A gesetzt, '
        'auf den Millimeter geprüft. Skill für KI-Agenten und CLI."'
    )
    pos_pruefung = alte_zeile.index("geprüft")
    pos_markdown = alte_zeile.index("DIN-5008-Briefe aus Markdown")
    assert pos_pruefung > pos_markdown
