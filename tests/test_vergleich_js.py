"""Das Add-on urteilt wie falzmarke: `vergleich.js` gegen `gesendet.py`.

Die Sperre beim Senden (ADR 0053) läuft in Thunderbird, die Prüfung vor dem
Entwurf in Python (ADR 0051). Halten beide dieselbe Mail einmal für gesendet
und einmal nicht, warnt das eine, wo das andere schweigt. Deshalb bekommen
beide hier dieselben Eingaben, und jedes Merkmal muss gleich herauskommen.

Node führt die JS-Fassung aus, ohne Thunderbird. Fehlt node, wird der Test
übersprungen, in der CI nicht: Die Runner von GitHub haben es immer.
"""

import json
import os
import shutil
import subprocess
from email import message_from_bytes, policy
from email.message import EmailMessage

import pytest
from conftest import REPO
from falzmarke import gesendet

VERGLEICH_JS = REPO / "thunderbird" / "entwurfsbruecke" / "vergleich.js"
GOLDEN = sorted((REPO / "tests" / "golden" / "email").glob("*.eml"))

LAEUFER = r"""
const eingabe = JSON.parse(require("fs").readFileSync(0, "utf8"));
const v = require(eingabe.modul);
function merk(fall) {
  const text = fall.html ? v.klartextAusHtml(fall.text) : fall.text;
  const m = v.merkmale({ empfaenger: fall.empfaenger, betreff: fall.betreff, text,
    fassung: fall.fassung });
  return { text, m };
}
const merkmale = eingabe.faelle.map((fall) => {
  const { text, m } = merk(fall);
  return { klartext: text, empfaenger: [...m.empfaenger].sort(), betreff: m.betreff,
    kern: m.kern, bis_signatur: m.bisSignatur, voll: m.voll, fassung: m.fassung };
});
const urteile = eingabe.paare.map(([a, b]) => v.vergleiche(merk(a).m, merk(b).m));
process.stdout.write(JSON.stringify({ merkmale, urteile }));
"""


def _fall(text, *, html=False, empfaenger=("e@example.com",), betreff="Auftrag S1",
          fassung=""):
    return {"text": text, "html": html, "empfaenger": list(empfaenger), "betreff": betreff,
            "fassung": fassung}


# ── Eingaben ────────────────────────────────────────────────────────────────

GRUSS = "Hallo Erika,\n\nbitte die Datei in Gold, Lieferung an die Straße 5.\n\n"
TEXTE = [
    GRUSS + "Viele Grüße\nPaul Beispiel",
    GRUSS + "Mit freundlichen Grüßen aus Musterstadt,\nPaul Beispiel\n-- \nSignatur",
    "Danke, passt so!\n\nAm 21.10.2026 um 10:00 schrieb Erika:\n> alter Text",
    "Text oben\n-----Original Message-----\nFrom: jemand",
    "- erster Punkt\n2) zweiter Punkt\n• dritter Punkt\n10. zehnter",
    "Siehe https://example.com/x?y=1 und <mailto:a@example.com> bis dann.",
    "Zeile eins\r\nZeile zwei\u2028Zeile drei\nBest regards,\nPaul",
    "Hi,\nplease check the file.\nCheers\nPaul",
    "AW: im Text ist kein Betreff\nLG",
    "",
    "Nur eine Zeile ohne Gruß und ohne Zeilenende",
]

HTML = [
    ("<p>Hallo&nbsp;Erika,</p><p>bitte &auml;ndern &amp; pr&uuml;fen, Ma&szlig; 5,5&#160;cm."
     "<br/>Viele Grüße<br>Paul</p>"),
    ("<html><head><title>Titel</title><style>p { color: red }</style></head><body>"
     "<div>Oben</div><!-- Kommentar --><script>var a = \"<p>nicht</p>\";</script>"
     "<table><tr><td>Feld</td><td>Wert &#228; &#xE4;</td></tr></table>"
     "<ul><li>eins</li><li>zwei</li></ul><p>Beste Grüße</p><p>Paul</p></body></html>"),
    "<P CLASS=\"x\">Großbuchstaben im Tag</P><BR><Div>und &lt;spitz&gt; &quot;zitiert&quot;</Div>",
]

EMPFAENGER = [
    ("Erika <E@Example.com>",),
    ("a@example.com, B <b@example.org>",),
    ("\"Beispiel, Paul\" <j@example.de>", "x@example.net"),
    ("\"r@falsch.example\" <r@richtig.example>",),
]

BETREFFE = ["AW: WG: Re[2]: Auftrag S11133 – Gold", "Fwd: Antw: SV: Nachtrag", "", "tr: x"]


def _golden() -> list[dict]:
    faelle = []
    for pfad in GOLDEN:
        nachricht = message_from_bytes(pfad.read_bytes(), policy=policy.default)
        for art in ("plain", "html"):
            teil = nachricht.get_body(preferencelist=(art,))
            if teil is not None:
                faelle.append(_fall(teil.get_content(), html=art == "html",
                                    betreff=str(nachricht.get("Subject") or "")))
    return faelle


def _faelle() -> list[dict]:
    return ([_fall(t) for t in TEXTE] + [_fall(h, html=True) for h in HTML]
            + [_fall(GRUSS, empfaenger=e) for e in EMPFAENGER]
            + [_fall(GRUSS, betreff=b) for b in BETREFFE]
            + [_fall(GRUSS, fassung=" f-1 ")] + _golden())


# Gleich bis zur Grußformel, aber kürzer als ANFANG_MIN: nur der Kern trägt.
KURZ = "Hallo Erika,\nbitte die Datei in Gold.\nViele Grüße\nPaul"
KURZ_ANDERS_SIGNIERT = KURZ.replace("Paul", "Paul Beispiel\n-- \nBeispiel GmbH")
LANG = ("Hallo Erika,\nbitte alle Formate neu anlegen, das Farbblatt und das JPG auch in Gold, "
        "und die Dateien wieder mit unserer Auftragsnummer benennen.\n")

#: (eigen, fremd, erwartet) — das Urteil von `gesendet.vergleiche`.
PAARE = [
    (_fall(KURZ), _fall(KURZ_ANDERS_SIGNIERT), "gesendet"),
    (_fall(LANG + "Sonnige Grüße\nPaul"), _fall(LANG + "Gruß und Kuss\nPaul"), "gesendet"),
    (_fall(LANG), _fall(LANG + "Danke dir!\nPaul\n\nAm 1.1. schrieb R:\n> x"), "gesendet"),
    (_fall(KURZ, fassung="f-1"), _fall("ganz anders", fassung="f-1"), "gesendet"),
    (_fall(KURZ), _fall("Hallo,\nbitte doch in Silber.\nLG\nPaul"), "geaendert"),
    (_fall(KURZ), _fall("Hallo,\nbitte doch in Silber.", betreff="Re: Auftrag S1"), "geaendert"),
    (_fall(KURZ), _fall("Hallo,\nbitte doch in Silber.", betreff="Auftrag S2"), "frei"),
    (_fall("Kurz.\nLG"), _fall("Kurz.\nLG", betreff="anders"), "frei"),
    (_fall(HTML[0], html=True), _fall("Hallo Erika,\nbitte ändern & prüfen, Maß 5,5 cm.\nVG"),
     "gesendet"),
]


# ── Python-Seite ────────────────────────────────────────────────────────────

def _nachricht(fall) -> EmailMessage:
    nachricht = EmailMessage()
    nachricht["To"] = ", ".join(fall["empfaenger"])
    nachricht["Subject"] = fall["betreff"]
    if fall["fassung"]:
        nachricht["X-Falzmarke-Fassung"] = fall["fassung"]
    nachricht.set_content(fall["text"], subtype="html" if fall["html"] else "plain")
    return nachricht


def _python(fall) -> tuple[dict, gesendet.Merkmale]:
    """Merkmale wie `gesendet.merkmale` sie bildet, und der Fall mit dem Text,
    den Python tatsächlich gelesen hat (`set_content` hängt ein Zeilenende an)."""
    nachricht = _nachricht(fall)
    teil = nachricht.get_body(preferencelist=("html" if fall["html"] else "plain",))
    gelesen = dict(fall, text=teil.get_content())
    return gelesen, gesendet.merkmale(nachricht)


def _ergebnis_python(fall) -> dict:
    gelesen, m = _python(fall)
    return {"klartext": gesendet.klartext(_nachricht(gelesen)), "empfaenger": sorted(m.empfaenger),
            "betreff": m.betreff, "kern": m.kern, "bis_signatur": m.bis_signatur,
            "voll": m.voll, "fassung": m.fassung}


# ── JS-Seite ────────────────────────────────────────────────────────────────

def _node() -> str:
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            pytest.fail("node fehlt im CI-Runner — der Vergleich im Add-on bliebe ungeprüft")
        pytest.skip("node fehlt: der Vergleich im Add-on ist nicht geprüft")
    return node


def _js(modul, faelle, paare) -> dict:
    eingabe = {"modul": str(modul), "faelle": faelle, "paare": paare}
    fertig = subprocess.run([_node(), "-e", LAEUFER], input=json.dumps(eingabe),
                            capture_output=True, encoding="utf-8", timeout=60, check=False)
    assert fertig.returncode == 0, fertig.stderr
    return json.loads(fertig.stdout)


def _abweichungen(modul) -> list[str]:
    """Jedes Merkmal und jedes Urteil, in dem JS und Python auseinanderliegen."""
    gelesen = [_python(f)[0] for f in _faelle()]
    paare = [[_python(a)[0], _python(b)[0]] for a, b, _ in PAARE]
    js = _js(modul, gelesen, paare)
    aus = []
    for nummer, (fall, ergebnis) in enumerate(zip(gelesen, js["merkmale"], strict=True)):
        erwartet = _ergebnis_python(fall)
        for feld, wert in erwartet.items():
            if ergebnis[feld] != wert:
                aus.append(f"Fall {nummer} {feld}: JS {ergebnis[feld]!r}, Python {wert!r}")
    for nummer, ((a, b, _), urteil) in enumerate(zip(PAARE, js["urteile"], strict=True)):
        erwartet = gesendet.vergleiche(_python(a)[1], _python(b)[1])
        if urteil != erwartet:
            aus.append(f"Paar {nummer}: JS {urteil}, Python {erwartet}")
    return aus


# ── Tests ───────────────────────────────────────────────────────────────────

def test_die_eingaben_decken_golden_mails_und_handfaelle_ab():
    faelle = _faelle()
    assert len(GOLDEN) >= 5
    assert sum(f["html"] for f in faelle) >= len(GOLDEN) + len(HTML)
    assert len(faelle) >= 40


@pytest.mark.parametrize(("nummer", "erwartet"), [(n, p[2]) for n, p in enumerate(PAARE)])
def test_python_urteilt_wie_erwartet(nummer, erwartet):
    eigen, fremd, _ = PAARE[nummer]
    assert gesendet.vergleiche(_python(eigen)[1], _python(fremd)[1]) == erwartet


def test_js_und_python_bilden_dieselben_merkmale_und_urteile():
    assert _abweichungen(VERGLEICH_JS) == []


@pytest.mark.parametrize(("alt", "neu"), [
    ('.replace(/ß/g, "ss")', ""),
    ("const KERN_MIN = 20;", "const KERN_MIN = 2000;"),
    ('"p", "br", "div"', '"p", "div"'),
])
def test_gegenprobe_eine_abweichung_in_js_faellt_auf(tmp_path, alt, neu):
    quelle = VERGLEICH_JS.read_text(encoding="utf-8")
    assert quelle.count(alt) == 1, f"{alt!r} steht nicht genau einmal in vergleich.js"
    kaputt = tmp_path / "vergleich.js"
    kaputt.write_text(quelle.replace(alt, neu), encoding="utf-8")
    assert _abweichungen(kaputt) != []
