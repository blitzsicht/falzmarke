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
from datetime import date

import pytest

from conftest import REPO
from falzmarke import regeln

# Kern des Satzes, ohne die verlinkten Teile — die dürfen sich ändern.
QUELLENLAGE = (
    "der Abgleich mit dem Originaltext der DIN 5008:2020-03 "
    "einschließlich Berichtigung 1:2020-07 steht aus"
)
WARNSTUFE = "Regeln aus einzelnen Quellen wirken nur als Warnung"

#: Dieselbe Zusage auf Englisch (#237). Nicht übersetzt, sondern eigens
#: geschrieben: „steht aus" heißt hier „is still outstanding", und die
#: Berichtigung 1:2020-07 heißt im englischen Normwesen „Corrigendum". Wer die
#: englische Fassung liest, sieht sonst ein Werkzeug ohne Vorbehalt — und
#: genau dorthin, wo kein deutsches README gelesen wird, gehört er
#: (ADR 0032, „Folgen").
QUELLENLAGE_EN = (
    "the comparison against the original text of DIN 5008:2020-03 "
    "including Corrigendum 1:2020-07 is still outstanding"
)
WARNSTUFE_EN = "rules backed by a single source act as warnings only"

MUSS_ENTHALTEN = {
    "README.md": [QUELLENLAGE, WARNSTUFE],
    "README.en.md": [QUELLENLAGE_EN, WARNSTUFE_EN],
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
# `XRechnung-konform` und Verwandte seit #117: Die fremde Prüfung bestätigt ein
# Beispiel gegen eine Regelfassung, sie sagt nichts darüber, ob ein Empfänger
# die Datei annimmt (ADR 0040).
VERBOTEN = re.compile(r"\b(normgerecht|DIN-konform|normkonform|zertifiziert"
                      r"|XRechnung-konform|ZUGFeRD-konform|Factur-X-konform)\w*", re.I)

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
_BEGRIFFE = r"(normgerecht|DIN-konform|normkonform|zertifiziert|XRechnung-konform|ZUGFeRD-konform|Factur-X-konform)"
AUSNAHMEN = re.compile(r"(nicht|kein[e]?|keine[rms]?)\s+\S*\s*" + _BEGRIFFE
                       + r"|" + _BEGRIFFE + r"\S*\s*(ist|sind)?\s*(nicht|kein)", re.I)


#: Die englischen Gegenstücke zu VERBOTEN. Ohne sie greift die Sperre aus
#: ADR 0032 auf Englisch nicht — ausgerechnet dort, wo das Werkzeug neu vor
#: Publikum steht. „compliant" deckt „DIN-compliant" und „standard-compliant"
#: mit ab; einzeln aufgezählt wüchse die Lücke beim nächsten Wort von selbst
#: nach (dieselbe Begründung wie bei NENNUNG in test_fundstellen.py).
VERBOTEN_EN = re.compile(r"\b(compliant|conformant|certified|conformity)\w*", re.I)

#: Wo die Wörter zulässig sind, weil sie verneint oder beschrieben werden.
#: „no claim of conformity" ist der Satz, der die Zusage überhaupt erst
#: ausspricht — er darf nicht an sich selbst scheitern.
AUSNAHMEN_EN = re.compile(
    r"\b(no|not|never|without|neither)\b[^.]{0,40}?"
    r"\b(compliant|conformant|certified|conformity)"
    r"|\b(compliant|conformant|certified|conformity)\w*[^.]{0,20}?\b(is|are)\s+(not|no)\b",
    re.I)


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


@pytest.mark.parametrize("datei", ["README.md", "docs/recht.md", "skill/SKILL.md",
                                   "skill/references/frontmatter.md", "docs/cli.md",
                                   "docs/rechnung.md"])
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
    assert VERBOTEN.search("falzmarke erzeugt XRechnung-konforme Rechnungen.")
    assert not AUSNAHMEN.search("falzmarke erzeugt normgerechte Briefe.")
    # Und die Verneinung darf nicht anschlagen — das ist der Fall, für den die
    # Ausnahme da ist: über die eigene Ausgabe wird das Wort verneint.
    satz = 'Kein „normgerecht“, kein „DIN-konform“ ohne den Satz oben.'
    assert AUSNAHMEN.search(satz), "Die Ausnahme greift bei der Verneinung nicht"


def test_keine_ungedeckte_konformitaetsbehauptung_auf_englisch():
    """Die deutsche Sperre greift für englischen Text nicht — sie kennt die
    Wörter nicht. Ein englisches README ohne eigene Sperre wäre die Lücke, an
    der ADR 0032 seine Bedingung verlöre."""
    # Satzweise auf dem Fließtext, nicht zeilenweise: Markdown bricht frei um,
    # und der Satz „You will find no claim of conformity …" stand im ersten
    # Anlauf über zwei Zeilen. Die Verneinung lag in der einen, das Wort in der
    # anderen — die Prüfung meldete ausgerechnet den Satz, der die
    # Zurückhaltung ausspricht. Ein zeilenweiser Test misst hier den Umbruch.
    saetze = [s for s in re.split(r"(?<=\.)\s", _fliesstext(REPO / "README.en.md")) if s]
    treffer = [s.strip()[:110] for s in saetze
               if VERBOTEN_EN.search(s) and not AUSNAHMEN_EN.search(s)]
    assert not treffer, ("README.en.md: ungedeckte Konformitätsbehauptung:\n  "
                         + "\n  ".join(treffer))


def test_die_englische_pruefung_wuerde_eine_behauptung_bemerken():
    """Gegenprobe: Ohne sie belegt der Test oben nur, dass gerade nichts
    dasteht — nicht, dass er es fände."""
    behauptung = "falzmarke produces DIN-compliant letters."
    assert VERBOTEN_EN.search(behauptung)
    assert not AUSNAHMEN_EN.search(behauptung)
    zusage = "You will find no claim of conformity anywhere in this project."
    assert AUSNAHMEN_EN.search(zusage), "Die Ausnahme greift bei der Verneinung nicht"


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
                     "docs/**/*.md", "README.md", "README.en.md", "CONTRIBUTING.md")
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



# ── „Was die Stufen derzeit wert sind“ altert nicht still (#329) ────────────
#
# Der Abschnitt in docs/recht.md zählte am 27.08.2026 nach und schloss mit
# „bewusst nicht geschehen“: Die Stufen blieben, wie sie waren. Seit #31 zählt
# eine schweigende Quelle nicht mehr — der Abschnitt beschrieb einen Stand, den
# es nicht mehr gab, und niemand merkte es, weil kein Test ihn hielt. Die
# Sätze zur Quellenlage oben halten nur zwei Wortlaute fest; die *Zahlen* in
# dieser Datei alterten ungeprüft.
#
# Gehalten wird hier deshalb zweierlei: Die Zahlen sind die, die die
# Regeldatei jetzt hergibt (gezählt aus den Daten, nicht als zweite Konstante
# — sonst prüfte sich die Doku an einer Kopie ihrer selbst), und sie tragen
# eine Standangabe. Ändert sich die Regeldatei, wird dieser Test rot und der
# Abschnitt muss neu gezählt und neu datiert werden.

STUFEN_UEBERSCHRIFT = "Was die Stufen derzeit wert sind"

#: Der Stand, an dem #329 nachgemessen hat — jünger darf die Standangabe sein,
#: älter nicht: Sonst stünde die Zahl vor #31, und genau das ist der Fehler.
STAND_FRUEHESTENS = date(2026, 9, 21)

_ZAHLWOERTER = {2: "zwei", 3: "drei", 4: "vier", 5: "fünf", 6: "sechs", 7: "sieben",
                8: "acht", 9: "neun", 10: "zehn", 11: "elf", 12: "zwölf"}

#: Wortlaute, die nach #31 falsch sind. Beide Sätze standen bis #329 im
#: Abschnitt; sie behaupteten, es sei nichts herabgestuft worden.
VERALTET = {
    "bewusst nicht geschehen": r"bewusst\s+nicht\s+geschehen",
    "Stufen unverändert geblieben": r"Stufen\s+unverändert\s+geblieben",
    "sechs Warnungen, deren einzige Quelle schweigt":
        r"sechs\s+Warnungen,?\s+deren\s+einzige\s+Quelle",
}


#: Was zum offenen Rest gesagt sein muss (AC 3). Gemessen am 21.09.2026 verteilen
#: sich die 44 Paare auf letter_pro 15, massskizze_b 12, onlineprinters 10,
#: wikipedia 5, koma_script 1 und massskizze_a 1 — „Maßzeichnungen“ ist also
#: nur ein Teil. Der Test verlangt das Wort, nicht die Behauptung, es seien alle:
#: „überwiegend Maßzeichnungen und Quelltexte“ genügt und stimmt.
OFFENER_REST = {
    "dass er Handarbeit bleibt": r"Handarbeit",
    "dass er Maßzeichnungen betrifft": r"Maßzeichnung",
}


def _glatt(text: str) -> str:
    """Ohne Auszeichnung: `**nicht**` und „nicht“ sind für die Suche dasselbe.

    Der Unterstrich bleibt — Regelkennungen wie `text.vermerke_max_3` brauchen ihn.
    """
    return re.sub(r"[*`]", "", text)


def _abschnitt_stufen() -> str:
    """Der Abschnitt „Was die Stufen derzeit wert sind“, als glatter Fließtext."""
    roh = (REPO / "docs/recht.md").read_text(encoding="utf-8")
    treffer = [t for t in re.split(r"(?m)^## ", roh) if t.startswith(STUFEN_UEBERSCHRIFT)]
    assert len(treffer) == 1, (
        f"docs/recht.md: Abschnitt „{STUFEN_UEBERSCHRIFT}“ nicht genau einmal gefunden "
        f"({len(treffer)}) — misst dieser Test noch etwas?")
    return _glatt(re.sub(r"\s*\n>?\s*", " ", treffer[0]))


def _zahl_bei(text: str, zahl: int, stichwort: str, fenster: int = 100) -> bool:
    """Steht `zahl` (als Ziffern oder Wort) als eigenes Wort im Text, mit dem
    `stichwort` in der Nähe?

    „Eigenes Wort“ heißt: `3` trifft weder `dreizehn` noch `vermerke_max_3` noch
    `#31`, und `7` nicht `27.08.2026`. Ohne die Nähe zum Stichwort träfe jede
    Ziffer irgendwo im Abschnitt, und der Test wäre erfüllt, ohne dass die Zahl
    etwas Gezähltes bezeichnet.
    """
    formen = [str(zahl)] + ([_ZAHLWOERTER[zahl]] if zahl in _ZAHLWOERTER else [])
    for form in formen:
        for treffer in re.finditer(rf"(?<![\w.,-]){form}(?!\w|[.,]\d)", text, re.I):
            nah = text[max(0, treffer.start() - fenster): treffer.end() + fenster]
            if re.search(stichwort, nah, re.I):
                return True
    return False


def _stand_daten(text: str, fenster: int = 60) -> list[date]:
    """Alle Datumsangaben, die nach einem Stand aussehen: ein Datum mit
    „Stand“, „gemessen“ oder „nachgezählt“ in der Nähe."""
    daten = []
    for treffer in re.finditer(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", text):
        nah = text[max(0, treffer.start() - fenster): treffer.end() + fenster]
        if not re.search(r"Stand|gemessen|nachgezählt|nachgemessen|gezählt", nah, re.I):
            continue
        tag, monat, jahr = (int(g) for g in treffer.groups())
        try:
            daten.append(date(jahr, monat, tag))
        except ValueError:
            continue
    return daten


def _herkunft_von(kennung: str) -> str:
    return next(r["herkunft"] for r in regeln.alle() if r["id"] == kennung)


def _gemessen() -> dict[str, tuple[int, str]]:
    """Was der Abschnitt nennen muss: Bezeichnung → (Zahl aus den Daten, Stichwort).

    Aus `regeln.alle()`, `schweigende_quellen()` und `ohne_belegpruefung()`
    gezählt — dieselben Funktionen, an denen tests/test_quellenlage.py die
    Beleglage festhält.
    """
    schweigend = regeln.schweigende_quellen()
    betroffen = {kennung for kennung, _ in schweigend}
    return {
        "Regeln gesamt": (len(regeln.alle()), r"Regel"),
        "ungeprüfte Quelle-Regel-Paare": (len(regeln.ohne_belegpruefung()), r"Paar"),
        "schweigende Quellen": (len(schweigend), r"schweig|nichts"),
        "davon jetzt Werkzeugprüfung":
            (sum(1 for k in betroffen if _herkunft_von(k) == regeln.WERKZEUG), r"werkzeug"),
        "von Fehler auf Warnung gefallen":
            (sum(1 for k in betroffen if _herkunft_von(k) == regeln.EINZELN), r"Warnung|warn"),
        #: Offener Rest 1. Ohne diese blieb die Suite grün, während der Abschnitt
        #: falsche Zahlen nannte — genau die stille Alterung, gegen die #329
        #: angetreten ist. Fiele `geometrie.seitenformat` auf `einzeln_belegt`,
        #: wären beide Zahlen falsch.
        #:
        #: Die Gesamtzahl „auf mehrfach bestätigt" steht bewusst NICHT hier: Sie
        #: ist zurzeit ebenfalls 10 wie die schweigenden Quellen, und zwei gleiche
        #: Zahlen kann die Nähe-Suche nicht trennen (siehe der Test darunter).
        #: Gedeckt ist sie trotzdem — sie ist die Summe dieser beiden.
        "davon Quellen derselben Gruppe": (_gruppenlage()[0], r"Zeichnung"),
        "davon Unabhängigkeit ungeprüft": (_gruppenlage()[1], r"Träger"),
    }


def _mehrfach() -> list[dict]:
    """Regeln, die einen Lauf scheitern lassen dürfen."""
    return [r for r in regeln.alle() if r.get("herkunft") == "mehrfach_bestaetigt"]


def _gruppenlage() -> tuple[int, int]:
    """(Regeln, deren Quellen dieselbe Gruppe teilen; Rest).

    Zwei Quellen einer Gruppe sind nicht unabhängig — die Gruppe ist genau
    dafür da. Gezählt statt geschrieben, damit die Zahlen mit den Daten wandern.
    """
    q = regeln.quellen()
    gleich = 0
    for r in _mehrfach():
        gruppen = [q.get(n, {}).get("gruppe", n) for n in (r.get("quellen") or [])]
        if len(set(gruppen)) < len(gruppen):
            gleich += 1
    return gleich, len(_mehrfach()) - gleich


@pytest.mark.parametrize("was", ["Regeln gesamt", "ungeprüfte Quelle-Regel-Paare",
                                 "schweigende Quellen", "davon jetzt Werkzeugprüfung",
                                 "von Fehler auf Warnung gefallen",
                                 "davon Quellen derselben Gruppe",
                                 "davon Unabhängigkeit ungeprüft"])
def test_der_stufenabschnitt_nennt_die_gemessene_zahl(was):
    """AC 1: Die Zahlen des Abschnitts sind die der Regeldatei von heute."""
    erwartet, stichwort = _gemessen()[was]
    assert erwartet > 0, f"{was}: gemessen 0 — dann zählt dieser Test nichts"
    assert _zahl_bei(_abschnitt_stufen(), erwartet, stichwort), (
        f"docs/recht.md, „{STUFEN_UEBERSCHRIFT}“: nennt nicht {erwartet} ({was}).\n"
        "Die Regeldatei hat sich verschoben oder der Abschnitt wurde nie nachgezählt. "
        "Neu zählen, datieren und hier nichts anpassen — die Zahl kommt aus den Daten.")


def test_der_stufenabschnitt_nennt_die_drei_regeln_die_auf_warnung_fielen():
    """AC 1, zweite Hälfte der Zahl 3: Sie steht nicht allein, sondern mit den
    Kennungen — sonst ließe sich nicht nachprüfen, welche drei gemeint sind."""
    gefallen = sorted(k for k, _ in regeln.schweigende_quellen()
                      if _herkunft_von(k) == regeln.EINZELN)
    assert gefallen, "keine auf Warnung gefallene Regel — dann misst dieser Test nichts"
    text = _abschnitt_stufen()
    fehlt = [k for k in gefallen if k not in text]
    assert not fehlt, f"docs/recht.md, „{STUFEN_UEBERSCHRIFT}“: nennt nicht {fehlt}"


def test_der_stufenabschnitt_traegt_eine_standangabe():
    """AC 1: „Eine Zahl ohne Datum altert still.“ Das Datum muss neuer sein als
    der Abschnitt vom 27.08.2026 — sonst steht die Zahl vor #31 — und darf nicht
    in der Zukunft liegen."""
    daten = _stand_daten(_abschnitt_stufen())
    assert daten, ("docs/recht.md: keine Standangabe im Abschnitt — ein Datum mit "
                   "„Stand“, „gemessen“ oder „nachgezählt“ in der Nähe fehlt.")
    brauchbar = [d for d in daten if STAND_FRUEHESTENS <= d <= date.today()]
    assert brauchbar, (
        "docs/recht.md: Standangaben " + ", ".join(d.strftime("%d.%m.%Y") for d in daten)
        + f" — keine ab {STAND_FRUEHESTENS.strftime('%d.%m.%Y')} (Nachmessung von #329) "
        "und nicht nach heute.")


def test_der_stufenabschnitt_sagt_dass_es_mit_31_geschehen_ist():
    """AC 2: Der Satz „bewusst nicht geschehen“ ist ersetzt — es *ist*
    geschehen, und der Abschnitt nennt den Vorgang, mit dem."""
    text = _glatt(_fliesstext(REPO / "docs/recht.md"))
    noch_da = [name for name, muster in VERALTET.items() if re.search(muster, text)]
    assert not noch_da, (
        f"docs/recht.md sagt weiter: {noch_da}. Seit #31 stimmt das nicht mehr — "
        "eine schweigende Quelle zählt nicht mit, drei Regeln fielen von Fehler auf Warnung.")
    assert re.search(r"#31(?!\d)", _abschnitt_stufen()), (
        f"docs/recht.md, „{STUFEN_UEBERSCHRIFT}“: nennt #31 nicht — "
        "dann steht nirgends, womit es geschehen ist.")


def test_der_stufenabschnitt_nennt_den_offenen_rest_als_handarbeit():
    """AC 3: Die ungeprüften Paare stehen als offener Rest daneben — mit dem
    Hinweis, dass sie Maßzeichnungen betreffen und Handarbeit bleiben."""
    text = _abschnitt_stufen()
    fehlt = [was for was, muster in OFFENER_REST.items() if not re.search(muster, text)]
    assert not fehlt, (
        f"docs/recht.md, „{STUFEN_UEBERSCHRIFT}“: der offene Rest sagt nicht: {fehlt}")


def test_wer_dieselbe_zeichnung_nennt_zaehlt_nach_31():
    """Die Zeile „9 stützen sich auf dieselbe Zeichnung“ war die Zahl vor #31:
    `text.vermerke_max_3` hing an `onlineprinters` und fiel heraus. Bleibt die
    Zeile im Abschnitt, muss ihre Zahl die von `stufe_traegt_nicht()` sein.

    Bedingt, weil die Zeile wegfallen darf — nicht aber falsch weiterstehen.
    """
    text = _abschnitt_stufen()
    if "dieselbe Zeichnung" not in text:
        pytest.skip("Der Abschnitt nennt die Zeile nicht mehr")
    erwartet = len(regeln.stufe_traegt_nicht())
    assert erwartet > 0
    assert _zahl_bei(text, erwartet, r"Zeichnung"), (
        f"docs/recht.md nennt „dieselbe Zeichnung“, aber nicht {erwartet} dabei — "
        "die Liste in `regeln.stufe_traegt_nicht()` ist seit #31 kürzer.")


# ── Gegenproben: Ohne sie belegt oben nur, dass gerade etwas dasteht ────────

def test_die_zahlensuche_trennt_richtige_von_falscher_zahl():
    """`_zahl_bei` darf nur anschlagen, wo die Zahl wirklich als Zählung steht."""
    satz = "Von 122 Regeln tragen 44 Quelle-Regel-Paare keine Prüfung."
    assert _zahl_bei(satz, 122, "Regel")
    assert _zahl_bei(satz, 44, "Paar")
    # Die falsche Zahl, dasselbe Stichwort — das ist die Sabotage.
    assert not _zahl_bei(satz.replace("122", "121"), 122, "Regel")
    assert not _zahl_bei(satz.replace("44", "45"), 44, "Paar")
    # Das Wort zählt wie die Ziffer.
    assert _zahl_bei("Sieben Regeln führen werkzeug.", 7, "werkzeug")
    # Zu weit vom Stichwort weg: keine Zählung *dieser* Sache.
    assert not _zahl_bei("122 " + "x" * 300 + " Regeln", 122, "Regel")


def test_die_zahlensuche_greift_nicht_in_fremde_zahlen():
    """Die Ziffer 3 steckt in `dreizehn`, `text.vermerke_max_3`, `#31`; die 7 in
    einem Datum. Trifft sie dort, ist der Test erfüllt, ohne dass etwas gezählt wäre."""
    assert not _zahl_bei("Von den dreizehn normbezogenen Regeln", 3, "Regel")
    assert not _zahl_bei("die Regel text.vermerke_max_3 warnt", 3, "Regel")
    assert not _zahl_bei("Regeln seit #31", 3, "Regel")
    assert not _zahl_bei("Regeln, Stand 27.08.2026", 7, "Regel")
    assert not _zahl_bei("Regeln, Stand 27.08.2026", 8, "Regel")
    assert not _zahl_bei("Berichtigung 1:2020-07 und Regeln", 7, "Regel")
    # Und die Kontrolle dazu: dieselbe Zahl, richtig geschrieben, trifft.
    assert _zahl_bei("Drei Regeln fielen auf Warnung", 3, "Warnung")


def test_die_standsuche_trennt_alten_von_neuem_stand():
    """AC 1: Der Abschnitt von heute trägt den 27.08.2026 — der ist zu alt."""
    alt = "Am 27.08.2026 wurde nachgezählt, was die Regeln tatsächlich tragen."
    assert _stand_daten(alt) == [date(2026, 8, 27)]
    assert not any(STAND_FRUEHESTENS <= d for d in _stand_daten(alt)), \
        "der alte Stand darf nicht als aktuell gelten"
    assert STAND_FRUEHESTENS in _stand_daten("Stand: 21.09.2026, gemessen gegen main.")
    assert STAND_FRUEHESTENS in _stand_daten("Am 21.09.2026 nachgezählt.")
    # Ein Datum ohne Bezug zum Zählen ist keine Standangabe.
    assert _stand_daten("Das EHUG trat am 01.01.2007 in Kraft.") == []
    # Und ein unmögliches Datum bricht die Suche nicht ab.
    assert _stand_daten("Stand 31.02.2026 und Stand 21.09.2026.") == [date(2026, 9, 21)]


def test_die_veraltet_muster_treffen_den_alten_wortlaut():
    """AC 2: Die Muster müssen den Satz kennen, den sie streichen sollen — und
    wortgetreu in der Form, in der er in der Markdown-Quelle stand."""
    alt = {
        "bewusst nicht geschehen": "Das ist bewusst **nicht** geschehen: Der Normabgleich",
        "Stufen unverändert geblieben": "hierher, weil die Stufen unverändert\ngeblieben sind.",
        "sechs Warnungen, deren einzige Quelle schweigt":
            "Dazu sechs Warnungen, deren einzige Quelle zu ihnen schweigt.",
    }
    assert alt.keys() == VERALTET.keys()
    for name, muster in VERALTET.items():
        satz = _glatt(re.sub(r"\s*\n>?\s*", " ", alt[name]))
        assert re.search(muster, satz), f"{name}: das Muster kennt den alten Satz nicht"
    # Der neue, richtige Wortlaut darf nicht anschlagen — sonst bliebe er rot.
    neu = "Mit #31 ist es geschehen: sieben Regeln führen jetzt `werkzeug`."
    assert not any(re.search(m, _glatt(neu)) for m in VERALTET.values())


def test_ein_richtig_nachgezaehlter_abschnitt_besteht_dieselben_pruefungen():
    """Gegenprobe in die andere Richtung: Ist der Abschnitt so, wie AC 1 bis 3 ihn
    beschreiben, darf keine Prüfung oben rot bleiben. Sonst wäre sie strenger
    als der Auftrag, und die Umsetzung liefe gegen eine Wand, die niemand
    beschlossen hat. Die Zahlen kommen aus den Daten, nicht aus dem Text hier."""
    z = {was: n for was, (n, _) in _gemessen().items()}
    gefallen = sorted(k for k, _ in regeln.schweigende_quellen()
                      if _herkunft_von(k) == regeln.EINZELN)
    roh = (
        "Stand 21.09.2026, gemessen gegen `main` nach dem Merge von #31.\n\n"
        "| | |\n|---|---|\n"
        f"| {z['Regeln gesamt']} | Regeln gesamt |\n"
        f"| {z['schweigende Quellen']} | Quelle-Regel-Paare, bei denen die Quelle "
        "**nachweislich schweigt** (alle `onlineprinters`) |\n"
        f"| {z['davon jetzt Werkzeugprüfung']} | davon führen jetzt `herkunft: werkzeug` |\n"
        f"| {z['von Fehler auf Warnung gefallen']} | fielen von Fehler auf Warnung: "
        + ", ".join(f"`{k}`" for k in gefallen) + " |\n\n"
        "Das ist mit #31 geschehen. Offen bleiben "
        f"{z['ungeprüfte Quelle-Regel-Paare']} ungeprüfte Quelle-Regel-Paare; "
        "sie betreffen überwiegend Maßzeichnungen und bleiben Handarbeit.\n\n"
        # Offener Rest 1 gehört in die Gegenprobe wie jede andere Zahl: Ein
        # richtig nachgezählter Abschnitt nennt auch ihn.
        f"| {z['davon Quellen derselben Gruppe']} | stützen sich auf zwei Quellen, "
        "die dieselbe **Zeichnung** sind |\n"
        f"| {z['davon Unabhängigkeit ungeprüft']} | zwei Quellen desselben "
        "**Trägers**, Unabhängigkeit ungeprüft |\n")
    text = _glatt(re.sub(r"\s*\n>?\s*", " ", roh))

    for was, (n, stichwort) in _gemessen().items():
        assert _zahl_bei(text, n, stichwort), f"{was}: {n} nicht gefunden"
    assert all(k in text for k in gefallen)
    assert any(STAND_FRUEHESTENS <= d <= date.today() for d in _stand_daten(text))
    assert not any(re.search(m, text) for m in VERALTET.values())
    assert re.search(r"#31(?!\d)", text)
    assert all(re.search(m, text) for m in OFFENER_REST.values())


def test_die_gemessenen_zahlen_sind_nicht_leer_und_verschieden():
    """Zählwerte > 0 statt bloßer Fehlerfreiheit: Fielen zwei Zahlen zusammen
    (oder wären sie 0), träfe die Nähe-Suche mit einer Ziffer beide."""
    gemessen = _gemessen()
    zahlen = [z for z, _ in gemessen.values()]
    assert all(z > 0 for z in zahlen), gemessen
    assert len(set(zahlen)) == len(zahlen), (
        f"zwei Zählungen liefern dieselbe Zahl: {gemessen} — die Suche trennte sie nicht mehr")
