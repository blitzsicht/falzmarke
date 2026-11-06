"""Die Formprüfung von `an` und `cc` (Issue #125).

Die Regeln `email.an` und `email.cc` behaupten „ist eine E-Mail-Adresse“. Der
Vorgang meldete, `parseaddr` prüfe fast nichts — das stimmt, aber danach greift
`EMAIL_MUSTER`, und das fängt schon einiges ab.

**Nachgemessen kam anderes heraus als im Vorgang steht:** Zwei der dort
genannten vier Fälle waren bereits abgefangen, sechs andere rutschten durch.
Diese Datei hält beides fest — was die Grobform schon konnte und was erst
`adresse_grund()` dazugewonnen hat.

Kein DNS, keine neue Abhängigkeit, kein Netzzugriff: Zustellbarkeit hängt von
SPF, DKIM und Spamfiltern ab, also von Dingen, die falzmarke nie kontrolliert
(ADR 0034).
"""

from __future__ import annotations

import re
from email.utils import parseaddr

import pytest

from falzmarke import cli as falzmarke
from falzmarke.lint import EMAIL_MUSTER, adresse_grund, adresse_ist_international
from conftest import SKILL

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

KOPF = """typ: email
profil: example
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""


def _linte_kopf(tmp_path, kopf: str, profile=PROFILE):
    pfad = tmp_path / "mail.md"
    pfad.write_text(f"---\n{KOPF}{kopf}---\nText.\n", encoding="utf-8")
    return falzmarke.linte(pfad, profil_verzeichnis=profile)


def linte_an(tmp_path, adresse: str):
    return _linte_kopf(tmp_path, f'an: "{adresse}"\n')


def _alte_pruefung(eintrag: str) -> bool:
    """Der Stand vor dieser Änderung: parseaddr plus Grobform."""
    _, adresse = parseaddr(eintrag)
    return bool(adresse) and bool(EMAIL_MUSTER.match(adresse))


def _neue_pruefung(eintrag: str) -> bool:
    if not _alte_pruefung(eintrag):
        return False
    _, adresse = parseaddr(eintrag)
    return adresse_grund(eintrag, adresse) is None


# ── Was gültig ist und bleibt ───────────────────────────────────────────────

GUELTIG = [
    "erika@example.de",
    "a.b-c@sub.example.co.uk",
    "max+filter@example.de",
    "m@x.de",
    "Muster GmbH <post@example.de>",
]


@pytest.mark.parametrize("adresse", GUELTIG, ids=GUELTIG)
def test_gueltige_adresse_bleibt_gueltig(tmp_path, adresse):
    """Abnahme 3: Die Verschärfung darf nichts Gültiges verlieren."""
    bericht = linte_an(tmp_path, adresse)
    assert not [b for b in bericht.befunde if b.regel == "an"], bericht.befunde


def test_die_profile_und_beispiele_bleiben_gueltig():
    """Dieselbe Frage an den echten Bestand statt an eine Liste."""
    from conftest import EMAIL_BEISPIELE

    assert EMAIL_BEISPIELE, "keine Mail-Beispiele — der Test misst sonst nichts"
    for pfad in EMAIL_BEISPIELE:
        bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
        schlecht = [b for b in bericht.befunde if b.regel in ("an", "cc")]
        assert not schlecht, f"{pfad.name}: {schlecht}"


# ── Was die Grobform schon konnte ───────────────────────────────────────────

SCHON_ABGEFANGEN = ["@firma.de", "max@firma", "max.firma.de", "max@@firma.de",
                    "max@", "max mustermann", "max@firma.d"]


@pytest.mark.parametrize("adresse", SCHON_ABGEFANGEN, ids=SCHON_ABGEFANGEN)
def test_bleibt_abgefangen(tmp_path, adresse):
    """Abnahme 2: nichts verlieren, was vorher schon auffiel.

    Zwei davon nennt Issue #125 als durchgerutscht — `@firma.de` und
    `max@firma`. Nachgemessen fielen sie schon vorher durch; der Vorgang hatte
    nur `parseaddr` betrachtet, nicht die Kette dahinter.
    """
    assert not _alte_pruefung(adresse), "war schon vorher kein Durchrutscher?"
    assert [b for b in linte_an(tmp_path, adresse).befunde if b.regel == "an"]


# ── Was neu gefangen wird ───────────────────────────────────────────────────

NEU_GEFANGEN = [
    ("max@firma..de", "leeren Teil"),
    (".max@firma.de", "Punkt"),
    ("max.@firma.de", "Punkt"),
    ("max@.firma.de", "leeren Teil"),
    ("max@-firma.de", "Bindestriche"),
    ("max@firma-.de", "Bindestriche"),
    ("max..mustermann@firma.de", "zwei Punkte"),
    ("max@firma_x.de", "Unterstriche"),
]


@pytest.mark.parametrize("adresse,teil", NEU_GEFANGEN, ids=[a for a, _ in NEU_GEFANGEN])
def test_wird_jetzt_gemeldet(tmp_path, adresse, teil):
    """Abnahme 1 — und die Gegenprobe aus Abnahme 4 gleich mit.

    Die erste Zeile belegt, dass die alte Prüfung diesen Fall wirklich
    durchliess. Ohne sie wäre nicht gezeigt, dass sich überhaupt etwas ändert.
    """
    assert _alte_pruefung(adresse), "die alte Prüfung fing das schon — kein Zugewinn"
    assert not _neue_pruefung(adresse)
    befunde = [b for b in linte_an(tmp_path, adresse).befunde if b.regel == "an"]
    assert befunde
    assert teil in befunde[0].meldung, befunde[0].meldung


def test_das_stille_reparieren_wird_gemeldet(tmp_path):
    """`parseaddr` entfernt Leerzeichen: „max@firma .de“ wird zu „max@firma.de“.

    Ohne diese Prüfung ginge der Brief an eine Adresse, die niemand geschrieben
    hat — die teuerste Art von Fehler, die dieses Werkzeug kennt.
    """
    assert parseaddr("max@firma .de")[1] == "max@firma.de", "parseaddr verhält sich anders"
    assert _alte_pruefung("max@firma .de"), "war vorher kein Durchrutscher"
    befunde = [b for b in linte_an(tmp_path, "max@firma .de").befunde if b.regel == "an"]
    assert befunde
    assert "Leerzeichen" in befunde[0].meldung


# ── Der internationale Fall ─────────────────────────────────────────────────

def test_internationale_adresse_warnt_statt_zu_scheitern(tmp_path):
    """Nach RFC 6531 zulässig, von vielen Servern abgelehnt — eine Aussage über
    die Praxis, und die ist nach ADR 0035 nie ein Fehler."""
    bericht = linte_an(tmp_path, "ä@ö.de")
    assert not [b for b in bericht.befunde if b.regel == "an"], "als Fehler gemeldet"
    warnungen = [b for b in bericht.befunde if b.regel == "email.adresse_international"]
    assert warnungen, bericht.befunde
    assert warnungen[0].schwere == "Warnung"


def test_die_form_wird_auch_international_geprueft():
    """Die Nachsicht gilt den Zeichen, nicht der Struktur."""
    assert adresse_grund("max@-ö.de", "max@-ö.de") is not None
    assert adresse_grund("max@ö-firma.de", "max@ö-firma.de") is None


def test_ascii_adressen_loesen_die_warnung_nicht_aus():
    """Gegenrichtung: Die Warnung darf nicht bei jeder Adresse anschlagen."""
    assert not adresse_ist_international("erika@example.de")
    assert adresse_ist_international("ä@ö.de")


# ── Keine neue Abhängigkeit ─────────────────────────────────────────────────

def test_die_pruefung_braucht_kein_netz_und_keine_neue_abhaengigkeit():
    """Abnahme 5. `lint.py` darf nichts importieren, was Netz oder DNS bräuchte."""
    import ast
    import pathlib

    from falzmarke import lint

    quelle = pathlib.Path(lint.__file__).read_text(encoding="utf-8")
    module = set()
    for knoten in ast.walk(ast.parse(quelle)):
        if isinstance(knoten, ast.Import):
            module |= {a.name.split(".")[0] for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom) and knoten.module:
            module.add(knoten.module.split(".")[0])
    verboten = {"dns", "dnspython", "socket", "requests", "urllib3", "http",
                "email_validator", "idna"}
    assert not (module & verboten), sorted(module & verboten)


# ── Komma im Anzeigenamen ohne Anführungszeichen (#519) ─────────────────────
# „Nachname, Vorname <adresse>“ ist in Firmenadressbüchern üblich. `parseaddr`
# zerlegt das zu einer leeren Adresse, und `_adressliste` schrieb daraus den
# To-Header `<>`: eine .eml ohne Empfänger, die erst beim Senden auffällt.

from falzmarke import eml  # noqa: E402

KOMMA = "Muster, Max <max@example.org>"


def test_komma_im_namen_lint_nennt_eintrag_und_abhilfe(tmp_path):
    bericht = linte_an(tmp_path, KOMMA)
    befunde = [b for b in bericht.befunde if b.regel == "an"]
    assert len(befunde) == 1, befunde
    assert KOMMA in befunde[0].meldung
    # Die alte Abhilfe empfahl genau die Form, die schon dastand.
    assert '"Muster, Max" <max@example.org>' in befunde[0].korrektur


def test_komma_im_namen_eml_bricht_ab_statt_leerem_to():
    with pytest.raises(ValueError, match="Muster, Max"):
        eml._adressliste([KOMMA])


@pytest.mark.parametrize("eintrag, erwartet", [
    ('"Muster, Max" <max@example.org>', '"Muster, Max" <max@example.org>'),
    ("Max Muster <max@example.org>", "Max Muster <max@example.org>"),
    ("max@example.org", "max@example.org"),
])
def test_gegenprobe_gueltige_formen_unveraendert(eintrag, erwartet):
    assert eml._adressliste([eintrag]) == erwartet


def test_gegenprobe_umlaut_im_namen_bleibt():
    from email.message import EmailMessage
    nachricht = EmailMessage()
    nachricht["To"] = eml._adressliste(["Jörg Müller <joerg@example.org>"])
    assert str(nachricht["To"]) == "Jörg Müller <joerg@example.org>"


def test_gegenprobe_gequotetes_komma_lintet_sauber(tmp_path):
    bericht = linte_an(tmp_path, '\\"Muster, Max\\" <max@example.org>')
    assert not [b for b in bericht.befunde if b.regel == "an"], bericht.befunde


# ── Folge aus dem Review an PR #523 ──────────────────────────────────────────
# Zwei Adressen in einem Eintrag sehen für den Komma-Ausdruck aus wie ein Name
# mit Komma. Die Abhilfe „Namen quoten“ machte daraus EINEN Empfänger, die
# erste Adresse fiele still weg.

ZWEI = "a@example.org, Erika <c@example.org>"


def test_zwei_adressen_in_einem_eintrag_raten_zur_liste(tmp_path):
    bericht = linte_an(tmp_path, ZWEI)
    befunde = [b for b in bericht.befunde if b.regel == "an"]
    assert len(befunde) == 1, befunde
    assert '"a@example.org, Erika"' not in befunde[0].korrektur
    assert "- a@example.org" in befunde[0].korrektur
    assert "- Erika <c@example.org>" in befunde[0].korrektur


@pytest.mark.parametrize("name", ["Dr. Erika Muster", "Erika (Einkauf)", "Mr. O'Brien"])
def test_listenzeilen_sind_gueltiges_yaml(tmp_path, name):
    # Review an PR #528: Address setzt einen Namen mit Punkt, Klammer oder Semikolon in
    # Anführungszeichen. Als Listenzeile `- "Dr. Erika Muster" <c@example.org>` brach YAML ab.
    import yaml
    bericht = linte_an(tmp_path, f"a@example.org, {name} <c@example.org>")
    korrektur = [b for b in bericht.befunde if b.regel == "an"][0].korrektur
    zeilen = re.findall(r"`(- .+?)`(?= und |$)", korrektur)
    assert len(zeilen) == 2, korrektur
    kopf = "an:\n" + "".join(f"  {z}\n" for z in zeilen)
    assert len(yaml.safe_load(kopf)["an"]) == 2
    # Die vorgeschlagene Liste muss selbst sauber linten.
    pfad = tmp_path / "vorschlag.md"
    pfad.write_text(f"---\n{KOPF}{kopf}---\nText.\n", encoding="utf-8")
    nach = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert not [b for b in nach.befunde if b.regel == "an"], nach.befunde


def test_apostroph_im_namen_hinweis_ist_gueltiges_yaml(tmp_path):
    import yaml
    bericht = linte_an(tmp_path, "O'Brien, Max <max@example.org>")
    korrektur = [b for b in bericht.befunde if b.regel == "an"][0].korrektur
    zeile = re.search(r"`(an: .+?)`(?:$|[ ,.])", korrektur)
    assert zeile, korrektur
    wert = yaml.safe_load(zeile.group(1))["an"]
    assert wert == "\"O'Brien, Max\" <max@example.org>"
    # Die vorgeschlagene Zeile muss selbst sauber linten.
    pfad = tmp_path / "vorschlag.md"
    pfad.write_text(f"---\n{KOPF}{zeile.group(1)}\n---\nText.\n", encoding="utf-8")
    nach = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert not [b for b in nach.befunde if b.regel == "an"], nach.befunde


# ── Folge aus dem Review an PR #528 (#544) ───────────────────────────────────
# Der Rat kannte nur den Feldnamen. Stand der Eintrag in einer Liste, empfahl
# er `an: '…'` für das ganze Feld: Wer das übernahm, verlor die übrigen
# Empfänger, und `lint` meldete danach nichts mehr. Für `email.absender` nannte
# er das Frontmatter, obwohl das Feld im Profil steht.

LISTE_MIT_KOMMA = "an:\n  - x@example.de\n  - 'Muster, Max <c@example.org>'\n  - z@example.de\n"


def test_komma_in_einer_liste_ersetzt_nur_diesen_eintrag(tmp_path):
    import yaml
    bericht = _linte_kopf(tmp_path, LISTE_MIT_KOMMA)
    befunde = [b for b in bericht.befunde if b.regel == "an"]
    assert len(befunde) == 1, befunde
    korrektur = befunde[0].korrektur
    zeile = re.search(r"`(- [^`]+)`$", korrektur)
    assert zeile, f"kein Listeneintrag im Rat: {korrektur}"
    # Den Rat so übernehmen, wie er dasteht: nur der fehlerhafte Eintrag wird ersetzt.
    kopf = LISTE_MIT_KOMMA.replace("- 'Muster, Max <c@example.org>'", zeile.group(1))
    assert yaml.safe_load(kopf)["an"] == [
        "x@example.de", '"Muster, Max" <c@example.org>', "z@example.de"]
    nach = _linte_kopf(tmp_path, kopf)
    assert not [b for b in nach.befunde if b.regel == "an"], nach.befunde


def test_gegenprobe_ein_einzelner_wert_behaelt_die_feldzeile(tmp_path):
    """Steht das Feld als Skalar da, bleibt der Rat `an: '…'`: Dort geht nichts verloren."""
    bericht = linte_an(tmp_path, KOMMA)
    korrektur = [b for b in bericht.befunde if b.regel == "an"][0].korrektur
    assert "im Frontmatter `an: '\"Muster, Max\" <max@example.org>'`" in korrektur
    assert "`- " not in korrektur


def _setze_absender(datei, absender) -> None:
    """`email.absender` im Profil setzen, über YAML statt über eine feste Textzeile:
    Eine andere Beispieladresse in example.yaml soll diese Tests nicht kippen."""
    import yaml
    daten = yaml.safe_load(datei.read_text(encoding="utf-8"))
    daten["email"]["absender"] = absender
    datei.write_text(yaml.safe_dump(daten, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _profile_mit_absender(tmp_path, absender):
    import shutil
    ziel = tmp_path / "profiles"
    shutil.copytree(PROFILE, ziel)
    datei = ziel / "example.yaml"
    _setze_absender(datei, absender)
    return ziel, datei


def test_komma_im_absender_nennt_das_profil(tmp_path):
    import yaml
    profile, datei = _profile_mit_absender(tmp_path, "Muster, Max <muster@example.de>")
    bericht = _linte_kopf(tmp_path, "an: x@example.de\n", profile)
    befunde = [b for b in bericht.befunde if b.regel == "email.absender"]
    assert len(befunde) == 1, bericht.befunde
    korrektur = befunde[0].korrektur
    assert "Frontmatter" not in korrektur
    zeile = re.search(r"im Profil unter `email:` die Zeile `(absender: [^`]+)`$", korrektur)
    assert zeile, korrektur
    # Die vorgeschlagene Zeile ist YAML und, im Profil eingesetzt, lintet sie sauber.
    _setze_absender(datei, yaml.safe_load(zeile.group(1))["absender"])
    nach = _linte_kopf(tmp_path, "an: x@example.de\n", profile)
    assert not [b for b in nach.befunde if b.regel == "email.absender"], nach.befunde


def test_zwei_adressen_im_absender_raten_nicht_zur_liste(tmp_path):
    profile, _ = _profile_mit_absender(tmp_path, "a@example.de, b@example.de")
    bericht = _linte_kopf(tmp_path, "an: x@example.de\n", profile)
    korrektur = [b for b in bericht.befunde if b.regel == "email.absender"][0].korrektur
    assert "genau eine Adresse" in korrektur
    assert "Liste" not in korrektur


# ── Nachreview von #571 ──────────────────────────────────────────────────────
# Eine Liste unter `email.absender` ging ohne Befund durch und wurde beim
# Versand zu `str(list)`. `cc: yes` brachte `lint` zum Absturz. In einer
# Flow-Liste und bei zwei Adressen in einem Listeneintrag passte der Rat nicht
# zu der Stelle, an der der Eintrag steht.

@pytest.mark.parametrize("absender", [
    ["m@example.de"],
    ["Muster, Max <m@example.de>"],
], ids=["gueltig", "mit-komma"])
def test_absender_als_liste_ist_ein_fehler(tmp_path, absender):
    profile, _ = _profile_mit_absender(tmp_path, absender)
    bericht = _linte_kopf(tmp_path, "an: x@example.de\n", profile)
    befunde = [b for b in bericht.befunde if b.regel == "email.absender"]
    assert len(befunde) == 1, bericht.befunde
    assert "`absender:` nimmt genau eine Adresse, im Profil steht eine Liste" in befunde[0].meldung
    assert "in der Liste" not in befunde[0].korrektur
    assert "absender: name@beispiel.de" in befunde[0].korrektur


@pytest.mark.parametrize("kopf, feld, art", [
    ("an: x@example.de\ncc: yes\n", "cc", "ein Wahrheitswert"),
    ("an: 42\n", "an", "eine Zahl"),
    ("an: {Muster: Max <c@example.org>}\n", "an", "eine Zuordnung"),
], ids=["cc-yes", "an-zahl", "an-zuordnung"])
def test_kein_text_und_keine_liste_ist_ein_befund(tmp_path, kopf, feld, art):
    bericht = _linte_kopf(tmp_path, kopf)                  # bisher TypeError bei bool und int
    befunde = [b for b in bericht.befunde if b.regel == feld]
    assert len(befunde) == 1, bericht.befunde
    assert f"`{feld}:` ist weder eine Adresse noch eine Liste, sondern {art}" in befunde[0].meldung
    assert "in der Liste" not in befunde[0].korrektur


FLOW_MIT_KOMMA = "an: [x@example.de, 'Muster, Max <c@example.org>', z@example.de]\n"


def test_komma_in_einer_flow_liste_ersetzt_nur_diesen_eintrag(tmp_path):
    import yaml
    bericht = _linte_kopf(tmp_path, FLOW_MIT_KOMMA)
    korrektur = [b for b in bericht.befunde if b.regel == "an"][0].korrektur
    wert = re.search(r"nur diesen Eintrag ersetzen durch `([^`]+)`$", korrektur)
    assert wert, korrektur
    assert not wert.group(1).startswith("- "), f"Blockzeile in einer Flow-Liste: {korrektur}"
    kopf = FLOW_MIT_KOMMA.replace("'Muster, Max <c@example.org>'", wert.group(1))
    assert yaml.safe_load(kopf)["an"] == [
        "x@example.de", '"Muster, Max" <c@example.org>', "z@example.de"]
    nach = _linte_kopf(tmp_path, kopf)
    assert not [b for b in nach.befunde if b.regel == "an"], nach.befunde


ZWEI_IN_BLOCK = "an:\n  - x@example.de\n  - 'b@example.de, c@example.de'\n"
ZWEI_IN_FLOW = "an: [x@example.de, 'b@example.de, c@example.de']\n"


def test_zwei_adressen_in_einer_blockliste_ersetzen_nur_diesen_eintrag(tmp_path):
    import yaml
    korrektur = [b for b in _linte_kopf(tmp_path, ZWEI_IN_BLOCK).befunde if b.regel == "an"][0].korrektur
    zeilen = re.search(r"nur diesen Eintrag durch zwei Zeilen ersetzen, `(- [^`]+)` und `(- [^`]+)`$",
                       korrektur)
    assert zeilen, korrektur
    neu = ZWEI_IN_BLOCK.replace("  - 'b@example.de, c@example.de'\n",
                                "".join(f"  {z}\n" for z in zeilen.groups()))
    assert yaml.safe_load(neu)["an"] == ["x@example.de", "b@example.de", "c@example.de"]
    nach = _linte_kopf(tmp_path, neu)
    assert not [b for b in nach.befunde if b.regel == "an"], nach.befunde


def test_zwei_adressen_in_einer_flowliste_ersetzen_nur_diesen_eintrag(tmp_path):
    import yaml
    korrektur = [b for b in _linte_kopf(tmp_path, ZWEI_IN_FLOW).befunde if b.regel == "an"][0].korrektur
    werte = re.search(r"nur diesen Eintrag durch zwei ersetzen, `([^`]+)` und `([^`]+)`$", korrektur)
    assert werte, korrektur
    neu = ZWEI_IN_FLOW.replace("'b@example.de, c@example.de'", ", ".join(werte.groups()))
    assert yaml.safe_load(neu)["an"] == ["x@example.de", "b@example.de", "c@example.de"]
    nach = _linte_kopf(tmp_path, neu)
    assert not [b for b in nach.befunde if b.regel == "an"], nach.befunde


@pytest.mark.parametrize("eintrag, teil", [
    (ZWEI, "zwei Adressen"),
    ("Muster", "keine E-Mail-Adresse"),
])
def test_eml_bricht_ab_statt_falschem_kopf(eintrag, teil):
    # „Muster“ ohne @ wurde bisher still zum To-Kopf „Muster“.
    with pytest.raises(ValueError, match=teil):
        eml._adressliste([eintrag])


def test_eml_komma_im_namen_nennt_die_ursache():
    with pytest.raises(ValueError, match="Anführungszeichen"):
        eml._adressliste([KOMMA])


def test_from_mit_komma_im_anzeigenamen():
    # Der Anzeigename lief als Text durch parseaddr: „Siluri, Einkauf“ hätte
    # jede Mail dieses Profils abgebrochen.
    assert eml._from_kopf("Siluri, Einkauf", "order@example.org") == \
        '"Siluri, Einkauf" <order@example.org>'


@pytest.mark.parametrize("name, absender, erwartet", [
    ("Max Muster", "max@example.org", "Max Muster <max@example.org>"),
    (None, "max@example.org", "max@example.org"),
    ("Jörg Müller", "joerg@example.org", "Jörg Müller <joerg@example.org>"),
])
def test_gegenprobe_from_wie_bisher(name, absender, erwartet):
    assert eml._from_kopf(name, absender) == erwartet


def test_from_ohne_adresse_bricht_ab():
    with pytest.raises(ValueError, match="absender"):
        eml._from_kopf("Siluri", "kein-at")
