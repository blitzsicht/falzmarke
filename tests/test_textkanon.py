"""Sätze, die nicht verschwinden dürfen.

Manche Formulierungen sind kein Stil, sondern eine Zusage. Der Satz zur
Quellenlage sagt, dass der Abgleich mit dem Originaltext der DIN 5008:2020-03
einschließlich Berichtigung 1:2020-07 aussteht — er ist der Unterschied
zwischen einer beschreibenden Nennung und einer Behauptung, die das Werkzeug
nicht decken kann.

Die Berichtigung gehört seit v0.5.1 in den Satz: Wer nur die Ausgabe 2020-03
nennt, benennt die geltende Fassung unvollständig, und ein Abgleich, der sie
auslässt, wäre keiner.

Solche Sätze überleben Überarbeitungen nur, wenn etwas sie festhält. Genau das
ist hier der Fall: Wer sie streicht, sieht einen roten Test und muss sich
entscheiden, statt sie beiläufig zu verlieren.
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO

# Kern des Satzes, ohne die verlinkten Teile — die dürfen sich ändern.
QUELLENLAGE = (
    "der Abgleich mit dem Originaltext der DIN 5008:2020-03 "
    "einschließlich Berichtigung 1:2020-07 steht aus"
)
WARNSTUFE = "Regeln aus einzelnen Quellen wirken nur als Warnung"

MUSS_ENTHALTEN = {
    "README.md": [QUELLENLAGE, WARNSTUFE],
    "docs/recht.md": [QUELLENLAGE, WARNSTUFE],
    # Der Skill ist der Ort, an dem die Quellenlage am ehesten ankommt: Wer ihn
    # über einen Prompt auslöst, sieht nie ein README. Voller Satz, weil die
    # Beschreibung keine harte Längengrenze hat (Issue #40).
    "skill/SKILL.md": [QUELLENLAGE, WARNSTUFE],
}

# Kurzform für Felder mit Längenbegrenzung.
#
# Der volle Satz passt dort nicht: Die Paketbeschreibung wird in der Trefferliste
# nach rund 100 Zeichen abgeschnitten, die GitHub-Beschreibung nach 120. Ein
# Vorbehalt hinter dem Abschneidepunkt schützt den Herausgeber und nicht den
# Nutzer — genau die Lücke, die ADR 0032 als ihre schwächste Stelle benennt.
#
# Was bleiben muss, ist der Kern: die Sollwerte sind nicht am Originaltext
# geprüft. Alles Weitere trägt die lange Beschreibung.
KURZFORM = "Sollwerte aus Sekundärquellen"

KANAL_KURZTEXTE = {
    # Einzige Quelle für beide Kurztexte — pyproject und die GitHub-Beschreibung
    # werden daraus gespeist, test_marke.py hält sie zusammen.
    "docs/marke/texte.yaml": KURZFORM,
    "pyproject.toml": KURZFORM,
}

# Begriffe, die ohne den Satz oben eine Zusage wären, die niemand geprüft hat.
# Kein `\b` am Ende: gesucht ist auch „normgerechte“, „zertifizierter“.
VERBOTEN = re.compile(r"\b(normgerecht|DIN-konform|normkonform|zertifiziert)\w*", re.I)

# Wo diese Begriffe zulässig sind, weil sie etwas anderes verneinen oder
# beschreiben. Der Regelfall ist die Selbstauskunft: falzmarke sagt über die
# eigene Ausgabe ausdrücklich *nicht* „normgerecht", solange der Normabgleich
# aussteht.
#
# Hier stand bis zum 27.08.2026: „die Word-Vorlage ist nachweislich *nicht*
# normgerecht". Das war genau die Behauptung, die docs/normmasse.md inzwischen
# zurückgenommen hat — gemessen wurde dort gegen die Maßzeichnungen, nicht
# gegen den Normtext, und „nachweislich" trug die Messung nie. Eine Rücknahme
# ist erst fertig, wenn sie überall steht, auch im Kommentar eines Tests.
AUSNAHMEN = re.compile(r"(nicht|kein[e]?|keine[rms]?)\s+\S*\s*(normgerecht|DIN-konform|normkonform|zertifiziert)"
                       r"|(normgerecht|DIN-konform|normkonform|zertifiziert)\S*\s*(ist|sind)?\s*(nicht|kein)", re.I)


def _fliesstext(pfad) -> str:
    """Markdown bricht Zeilen frei um — für die Suche ist der Umbruch ein
    Leerzeichen. Ohne diese Normalisierung würde der Test bei jeder
    Neuformatierung rot, ohne dass sich etwas geändert hätte."""
    roh = pfad.read_text(encoding="utf-8")
    return re.sub(r"\s*\n>?\s*", " ", roh)


@pytest.mark.parametrize("datei, saetze", MUSS_ENTHALTEN.items(), ids=list(MUSS_ENTHALTEN))
def test_der_satz_zur_quellenlage_steht_da(datei, saetze):
    text = _fliesstext(REPO / datei)
    fehlend = [s for s in saetze if s not in text]
    assert not fehlend, (
        f"{datei} nennt nicht mehr: {fehlend}\n"
        "Der Satz ist eine Zusage, keine Formulierung. Wenn der Normabgleich "
        "erledigt ist, darf er weg — dann aber auch aus diesem Test.")


@pytest.mark.parametrize("datei", ["README.md", "docs/recht.md", "skill/SKILL.md"])
def test_keine_ungedeckte_konformitaetsbehauptung(datei):
    """„normgerecht“ ohne den Satz zur Quellenlage wäre eine Behauptung, die
    niemand geprüft hat. Verneinungen bleiben erlaubt."""
    text = (REPO / datei).read_text(encoding="utf-8")
    treffer = []
    for zeile in text.splitlines():
        if VERBOTEN.search(zeile) and not AUSNAHMEN.search(zeile):
            treffer.append(zeile.strip()[:100])
    assert not treffer, f"{datei}: ungedeckte Konformitätsbehauptung:\n  " + "\n  ".join(treffer)


def test_die_pruefung_wuerde_eine_behauptung_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass gerade nichts dasteht."""
    assert VERBOTEN.search("falzmarke erzeugt normgerechte Briefe.")
    assert not AUSNAHMEN.search("falzmarke erzeugt normgerechte Briefe.")
    # Und die Verneinung darf nicht anschlagen — das ist der Fall, für den die
    # Ausnahme da ist: über die eigene Ausgabe wird das Wort verneint.
    satz = 'Kein „normgerecht“, kein „DIN-konform“ ohne den Satz oben.'
    assert AUSNAHMEN.search(satz), "Die Ausnahme greift bei der Verneinung nicht"


# ── Kanäle: die Quellenlage muss dorthin, wo kein README gelesen wird ────────


@pytest.mark.parametrize("datei", sorted(KANAL_KURZTEXTE))
def test_kurztext_traegt_die_quellenlage(datei):
    """Issue #40: Ein Kanal geht erst live, wenn sein Text den Vorbehalt trägt.

    ADR 0032 gibt die Verbreitung frei, *weil* der Belegstand ehrlich
    ausgewiesen ist. Diese Begründung trägt nur so weit, wie der Hinweis
    tatsächlich ankommt.
    """
    inhalt = (REPO / datei).read_text(encoding="utf-8")
    assert KANAL_KURZTEXTE[datei] in inhalt, (
        f"{datei} nennt die Quellenlage nicht mehr. Ohne sie ruht ADR 0032 auf "
        f"einer Zusage, die dieser Kanal nicht einlöst."
    )


def test_kurztexte_bleiben_unter_der_abschneidegrenze():
    """Ein Vorbehalt hinter dem Abschneidepunkt ist keiner.

    GitHub zeigt 120 Zeichen, die Paketsuche rund 100. Gemessen wird gegen die
    schärfere der beiden — sonst stünde der Hinweis zwar in der Datei, aber
    nicht in der Trefferliste.
    """
    import yaml

    kanon = yaml.safe_load((REPO / "docs/marke/texte.yaml").read_text(encoding="utf-8"))
    beschreibung = kanon["github_beschreibung"]
    assert len(beschreibung) <= 100, (
        f"{len(beschreibung)} Zeichen — die Paketsuche schneidet bei rund 100 ab, "
        f"der Vorbehalt am Ende wäre dann unsichtbar."
    )
    assert KURZFORM in beschreibung


def test_gegenprobe_der_kanalpruefung():
    """Belegt, dass die Prüfung oben überhaupt trennt.

    Ohne diesen Test wüsste die Suite nur, dass die Dateien den Satz heute
    enthalten — nicht, dass ein Entfernen auffiele. Geprüft wird deshalb an
    einem Text, dem der Hinweis fehlt: Die Bedingung muss dort falsch sein.
    """
    ohne_hinweis = "DIN-5008-Briefe aus Markdown, am fertigen PDF nachgemessen."
    assert KURZFORM not in ohne_hinweis

    mit_hinweis = ohne_hinweis + " Sollwerte aus Sekundärquellen."
    assert KURZFORM in mit_hinweis

    # Und derselbe Schnitt am vollen Satz, für die Dateien in MUSS_ENTHALTEN.
    assert QUELLENLAGE not in "Ein Text, der die Quellenlage verschweigt."


# ── Zurückgenommene Behauptungen dürfen nicht zurückkehren ──────────────────
#
# Das Gegenstück zu allem darüber: Dort geht es um Sätze, die bleiben müssen,
# hier um solche, die weg sind und weg bleiben sollen. Beide Fälle sind
# gemessen entstanden — die zweite Sorte gleich zweimal an einem Tag.

#: Textquellen, in denen eine zurückgenommene Aussage wieder auftauchen könnte.
#: Bewusst nicht nur `.py` und `.md`: Der Regelkatalog ist YAML, und genau dort
#: blieb die `Date`-Behauptung nach #236 und #249 stehen — die Rücknahme-Suche
#: von #249 lief ohne `*.yaml` und übersah ihn.
TEXTQUELLEN = sorted(
    p for muster in ("skill/**/*.py", "skill/**/*.md", "skill/**/*.yaml",
                     "docs/**/*.md", "README.md", "CONTRIBUTING.md")
    for p in REPO.glob(muster)
    if "vendor" not in p.parts and "__pycache__" not in p.parts
)

#: Die Aussage, die #236 widerlegt hat: falzmarke setzt `Date` selbst.
#: Beide Wortstellungen, weil beide im Repo vorkamen („der Mailclient setzt es"
#: und „das setzt der Mailclient").
DATUM_ZURUECKGENOMMEN = re.compile(
    r"(?:(?:Mailclient|Mailprogramm|Client)\s+setzt\s+(?:es|ihn|das\s+Datum)"
    r"|setzt\s+(?:der|das)\s+(?:Mailclient|Mailprogramm))", re.I)


def _ohne_verlauf(datei: Path) -> str:
    """Der Text ohne den Changelog-Auszug.

    Dort steht die zurückgenommene Behauptung zu Recht — als Zitat dessen, was
    korrigiert wurde. Eine Suche, die den Verlauf mitnimmt, träfe ausgerechnet
    die Stelle, die die Korrektur dokumentiert.
    """
    return datei.read_text(encoding="utf-8").split("## Was sich zuletzt getan hat")[0]


def test_die_dateiliste_ist_nicht_leer():
    """Sonst prüfte alles darunter die leere Menge und wäre still grün."""
    assert len(TEXTQUELLEN) >= 20, f"nur {len(TEXTQUELLEN)} Textquellen gefunden"


@pytest.mark.parametrize("datei", TEXTQUELLEN, ids=lambda p: str(p.relative_to(REPO)))
def test_niemand_behauptet_wieder_der_client_setze_das_datum(datei):
    """Seit #236 setzt falzmarke die Kopfzeile `Date` selbst.

    Die alte Begründung stand an sechs Stellen. #249 hat fünf davon
    mitgezogen; die sechste — `regeln/email.yaml` — blieb stehen, weil die
    Suche nur `*.py` und `*.md` durchlief, und wanderte von dort in die
    erzeugte `references/din5008.md`. Diese Prüfung ist der Ersatz für ein
    `grep`, an das jedes Mal jemand denken müsste.
    """
    treffer = [z.strip()[:100] for z in _ohne_verlauf(datei).splitlines()
               if DATUM_ZURUECKGENOMMEN.search(z)]
    assert not treffer, (
        f"{datei.relative_to(REPO)}: seit #236 setzt falzmarke `Date` selbst:\n  "
        + "\n  ".join(treffer))


def test_gegenprobe_der_datumspruefung():
    """Ohne sie belegt der Test oben nur, dass gerade nichts dasteht."""
    assert DATUM_ZURUECKGENOMMEN.search("Der Mailclient setzt es beim Versand.")
    assert DATUM_ZURUECKGENOMMEN.search("das setzt der Mailclient beim Versand")
    # Und der heutige, richtige Wortlaut darf NICHT anschlagen — sonst wäre die
    # Prüfung nicht abschaltbar und der korrigierte Text bliebe rot.
    assert not DATUM_ZURUECKGENOMMEN.search(
        "Die Kopfzeile `Date` entsteht beim Setzen der Nachricht.")
    # Und der Verlauf bleibt unangetastet: Im Changelog steht die alte Aussage
    # als Zitat, und die Prüfung darf ihn nicht mitnehmen.
    assert DATUM_ZURUECKGENOMMEN.search('sagte „der Mailclient setzt es beim Versand"')
    assert "Mailclient" not in _ohne_verlauf(REPO / "README.md")


# ── Zahlen in der Doku altern nicht still ───────────────────────────────────

def test_die_doku_nennt_die_geltende_infoblock_grenze():
    """`INFOBLOCK_WERT_MAX` stand bis #244 auf 32 und wurde auf 21 korrigiert.

    README und Frontmatter-Referenz nannten weiter 32 — als aktuelle Zusage,
    nicht als Historie. Wer sich danach richtet, schreibt einen Wert, der jetzt
    hart abbricht, und lernt die echte Grenze erst aus der Fehlermeldung.
    """
    from falzmarke.lint import INFOBLOCK_WERT_MAX

    for datei in ("README.md", "skill/references/frontmatter.md"):
        text = (REPO / datei).read_text(encoding="utf-8")
        # Nur der Ist-Zustand, nicht der Changelog-Verlauf: Dort steht die alte
        # Zahl zu Recht, und zwar als das, was sie ist — Vergangenheit.
        vorne = text.split("## Was sich zuletzt getan hat")[0]
        gefunden = re.findall(r"höchstens (\d+) Zeichen", vorne)
        assert gefunden, f"{datei}: keine Zeichengrenze genannt — misst der Test noch etwas?"
        assert str(INFOBLOCK_WERT_MAX) in gefunden, (
            f"{datei} nennt {gefunden}, die Grenze steht auf {INFOBLOCK_WERT_MAX}")
