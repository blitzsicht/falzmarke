"""Eine Vorlage plus Datenquelle ergibt n Briefe (#3).

Zwei Dinge entscheiden hier über brauchbar oder gefährlich, und beide haben
ihre Gegenprobe:

1. **Ein Wert wird nie zu Markup.** Ein Empfänger namens `Müller & Söhne *GmbH*`
   stünde sonst kursiv im Brief, ein Auftrag `# 2026-0815` würde zur
   Überschrift. Deshalb wird nicht im Rohtext ersetzt, sondern im geprüften
   Baum: Was dort eingesetzt wird, läuft nie wieder durch den Parser.

   Das ist dieselbe Überlegung wie in `emit.py` — eine Fehlerklasse schliessen
   statt sie zu verkleinern. Der Weg über eine Maskierliste (`*`, `_`, `#`,
   `[`, `` ` ``) wäre einfacher und irgendwann unvollständig.

2. **Ein Datensatz, ein Ergebnis.** Wer bei zweihundert Empfängern wegen eines
   zu langen Namens gar nichts bekommt, ist schlechter dran als mit
   hundertneunundneunzig Briefen und einer Fehlerzeile.
"""

from __future__ import annotations

import json

import pytest

from conftest import SKILL
from falzmarke import cli, serie

PROFILE = SKILL / "falzmarke" / "typst" / "profiles"

VORLAGE = """---
profil: example
empfaenger:
  - "{{firma}}"
  - "{{strasse}}"
  - "{{plz}} {{ort}}"
datum: 2026-08-29
betreff: Ihre Anfrage vom 14. August 2026
anrede: "Sehr geehrte {{anrede}} {{nachname}},"
---
vielen Dank für Ihre Anfrage. Wir haben sie unter {{auftrag}} erfasst.

Die Lieferung nach {{ort}} erfolgt bis zum 15. September 2026.
"""

SPALTEN = ["firma", "strasse", "plz", "ort", "anrede", "nachname", "auftrag"]
ZEILEN = [
    ["Muster GmbH", "Musterstraße 1", "12345", "Musterstadt", "Frau", "Kern", "2026-0815"],
    ["Beispiel AG", "Beispielweg 7", "54321", "Beispielhausen", "Herr", "Berg", "2026-0816"],
]


def _aufbau(tmp_path, zeilen=None, vorlage: str = VORLAGE, endung: str = "csv"):
    (tmp_path / "vorlage.md").write_text(vorlage, encoding="utf-8")
    daten = zeilen if zeilen is not None else ZEILEN
    if endung == "csv":
        pfad = tmp_path / "daten.csv"
        pfad.write_text(
            ",".join(SPALTEN) + "\n" + "\n".join(",".join(z) for z in daten) + "\n",
            encoding="utf-8")
    else:
        pfad = tmp_path / "daten.json"
        pfad.write_text(json.dumps([dict(zip(SPALTEN, z)) for z in daten],
                                   ensure_ascii=False), encoding="utf-8")
    return tmp_path / "vorlage.md", pfad


def _lauf(tmp_path, **kwargs):
    vorlage, daten = _aufbau(tmp_path, **kwargs)
    ziel = tmp_path / "briefe"
    code = cli.main(["serie", str(vorlage), "--daten", str(daten),
                     "--ziel", str(ziel), "--benennen", "nachname",
                     "--profiles", str(PROFILE)])
    return code, sorted(p.name for p in ziel.glob("*.pdf")) if ziel.is_dir() else []


def _pdftext(pfad) -> str:
    import pdfplumber

    with pdfplumber.open(str(pfad)) as dokument:
        return "\n".join(s.extract_text() or "" for s in dokument.pages)


# ── Der gewöhnliche Lauf ────────────────────────────────────────────────────

def test_aus_zwei_datensaetzen_werden_zwei_briefe(tmp_path):
    code, dateien = _lauf(tmp_path)
    assert code == 0
    assert dateien == ["001-kern.pdf", "002-berg.pdf"], dateien


def test_dasselbe_aus_json(tmp_path):
    code, dateien = _lauf(tmp_path, endung="json")
    assert code == 0
    assert len(dateien) == 2, dateien


def test_die_werte_stehen_im_brief(tmp_path):
    _lauf(tmp_path)
    text = _pdftext(tmp_path / "briefe" / "001-kern.pdf")
    for wert in ("Muster GmbH", "Musterstadt", "Kern", "2026-0815"):
        assert wert in text, f"„{wert}“ fehlt im Brief"


def test_und_kein_platzhalter_bleibt_stehen(tmp_path):
    """Gegenprobe: Ohne sie belegte der Test darüber nur, dass die Werte
    irgendwo stehen — nicht, dass sie die Platzhalter ersetzt haben."""
    _lauf(tmp_path)
    text = _pdftext(tmp_path / "briefe" / "001-kern.pdf")
    assert "{{" not in text and "}}" not in text, text[:300]


def test_die_laufende_nummer_haelt_gleichnamige_auseinander(tmp_path):
    """Zwei Empfänger gleichen Namens sind in einer Adressliste kein Randfall.

    Ohne die Nummer überschriebe der zweite den ersten — still.
    """
    zeilen = [list(ZEILEN[0]), list(ZEILEN[0])]
    zeilen[1][0] = "Andere GmbH"
    code, dateien = _lauf(tmp_path, zeilen=zeilen)
    assert code == 0
    assert dateien == ["001-kern.pdf", "002-kern.pdf"], dateien


# ── Ein Wert wird nie zu Markup ─────────────────────────────────────────────

@pytest.mark.parametrize("wert,muss_bleiben", [
    ("Auftrag *2026-0815*", "*2026-0815*"),
    ("Auftrag _intern_", "_intern_"),
    ("Auftrag `roh`", "`roh`"),
    ("Auftrag **wichtig**", "**wichtig**"),
])
def test_markdown_in_den_daten_bleibt_text(tmp_path, wert, muss_bleiben):
    """Der Kern der Sache — und er wird im BRIEFTEXT geprüft, nicht im Kopf.

    Das ist keine Feinheit: Ein Wert im Frontmatter läuft ohnehin nie durch den
    Markdown-Parser, dort ist Roh-Ersatz richtig. Gefährlich ist allein der
    Brieftext, und genau dorthin geht `{{auftrag}}`.

    Beim ersten Anlauf stand hier `{{firma}}` — also ein Feld des
    Anschriftblocks. Der Test war grün, blieb aber auch grün, als die
    Ersetzung versuchsweise in den Rohtext verlegt wurde: Er hätte die
    Fehlerklasse nie gefunden, gegen die es ihn gibt.

    Die Daten kommen aus einer fremden Quelle — einer Adressliste, einem Export
    aus dem Warenwirtschaftssystem. Was dort steht, ist Text und muss Text
    bleiben.
    """
    zeilen = [list(ZEILEN[0])]
    zeilen[0][SPALTEN.index("auftrag")] = wert
    _lauf(tmp_path, zeilen=zeilen)
    text = _pdftext(tmp_path / "briefe" / "001-kern.pdf")
    assert muss_bleiben in text, f"„{muss_bleiben}“ wurde zu Markup:\n{text[:400]}"


def test_die_typografie_laesst_den_wert_in_ruhe(tmp_path):
    """Aus `Nord -- Süd` darf kein Halbgeviertstrich werden.

    Im Fließtext der Vorlage ist die Ersetzung richtig und gewollt; in einem
    Firmennamen aus der Datenquelle wäre sie eine stille Änderung an fremden
    Daten.
    """
    zeilen = [list(ZEILEN[0])]
    zeilen[0][SPALTEN.index("auftrag")] = "Nord -- Süd"
    _lauf(tmp_path, zeilen=zeilen)
    text = _pdftext(tmp_path / "briefe" / "001-kern.pdf")
    assert "Nord -- Süd" in text, text[:300]
    assert "Nord – Süd" not in text


def test_und_im_vorlagentext_greift_sie_sehr_wohl(tmp_path):
    """Gegenprobe. Ohne sie wüsste man nicht, ob die Typografie überhaupt läuft
    — dann bewiese der Test darüber nichts."""
    vorlage = VORLAGE.replace("vielen Dank für Ihre Anfrage.",
                              "vielen Dank -- wir haben sie erhalten.")
    _lauf(tmp_path, vorlage=vorlage)
    text = _pdftext(tmp_path / "briefe" / "001-kern.pdf")
    assert "vielen Dank – wir" in text, text[:300]


# ── Ein Datensatz, ein Ergebnis ─────────────────────────────────────────────

def test_ein_kaputter_satz_haelt_die_serie_nicht_an(tmp_path):
    """Die Forderung aus dem Vorgang, wörtlich."""
    zeilen = [list(ZEILEN[0]), list(ZEILEN[1]), list(ZEILEN[0])]
    zeilen[1][0] = ""                        # leere Zeile im Anschriftfeld
    zeilen[2][5] = "Sommer"
    code, dateien = _lauf(tmp_path, zeilen=zeilen)
    assert code == 1, "ein gescheiterter Satz muss sich im Rückgabewert zeigen"
    assert dateien == ["001-kern.pdf", "003-sommer.pdf"], dateien


def test_und_die_meldung_nennt_die_zeile(tmp_path, capsys):
    """„Ein Datensatz ist kaputt" hilft bei zweihundert Zeilen niemandem."""
    zeilen = [list(ZEILEN[0]), list(ZEILEN[1])]
    zeilen[1][0] = ""
    _lauf(tmp_path, zeilen=zeilen)
    ausgabe = capsys.readouterr().out
    assert "Zeile 3" in ausgabe, ausgabe
    assert "Anschriftfeld" in ausgabe, ausgabe


def test_ohne_fehler_ist_der_rueckgabewert_null(tmp_path):
    """Gegenprobe zum Rückgabewert — sonst könnte er immer 1 sein."""
    code, _ = _lauf(tmp_path)
    assert code == 0


# ── Was den ganzen Lauf anhält ──────────────────────────────────────────────

def test_ein_platzhalter_ohne_spalte_bricht_vorher_ab(tmp_path, capsys):
    """Er beträfe jeden Datensatz — zweihundertmal dieselbe Meldung ist keine
    Hilfe, und zweihundert halbe Briefe sind es erst recht nicht."""
    vorlage = VORLAGE.replace("{{auftrag}}", "{{auftragsnummer}}")
    code, dateien = _lauf(tmp_path, vorlage=vorlage)
    assert code == 1
    assert dateien == [], "es darf kein Brief entstanden sein"
    ausgabe = capsys.readouterr()
    assert "auftragsnummer" in ausgabe.err, ausgabe.err


def test_eine_unbenutzte_spalte_ist_kein_fehler(tmp_path):
    """Bei einer Adressliste ist sie der Normalfall, nicht ein Versehen."""
    namen = serie.platzhalter(VORLAGE)
    serie.pruefe_vorlage(namen, set(SPALTEN) | {"telefon", "kundennummer"})


def test_eine_unbekannte_endung_wird_benannt(tmp_path):
    (tmp_path / "daten.txt").write_text("egal", encoding="utf-8")
    with pytest.raises(serie.Seriefehler, match="csv"):
        serie.lies_daten(tmp_path / "daten.txt")


def test_eine_csv_ohne_kopfzeile_ebenso(tmp_path):
    (tmp_path / "leer.csv").write_text("", encoding="utf-8")
    with pytest.raises(serie.Seriefehler, match="Kopfzeile"):
        serie.lies_daten(tmp_path / "leer.csv")


def test_eine_spalte_ohne_namen_wird_gemeldet(tmp_path):
    """Auf sie könnte kein Platzhalter zeigen — still ignorieren hiesse, eine
    Spalte anzubieten, die niemand benutzen kann."""
    (tmp_path / "d.csv").write_text("firma,,ort\nA,B,C\n", encoding="utf-8")
    with pytest.raises(serie.Seriefehler, match="ohne Namen"):
        serie.lies_daten(tmp_path / "d.csv")


def test_excel_schreibt_eine_byte_order_mark(tmp_path):
    """Ohne `utf-8-sig` hiesse die erste Spalte `\\ufeffirma` statt `firma`,
    und der Platzhalter fände sie nicht — eine halbe Stunde Suche."""
    (tmp_path / "excel.csv").write_bytes(
        "﻿irma,ort\nMuster GmbH,Musterstadt\n".encode("utf-8"))
    saetze = serie.lies_daten(tmp_path / "excel.csv")
    assert list(saetze[0])[0] == "irma", list(saetze[0])


# ── Das Sammel-PDF ──────────────────────────────────────────────────────────

def test_sammel_pdf_traegt_alle_briefe(tmp_path):
    import pypdf

    vorlage, daten = _aufbau(tmp_path)
    ziel = tmp_path / "briefe"
    code = cli.main(["serie", str(vorlage), "--daten", str(daten), "--ziel", str(ziel),
                     "--benennen", "nachname", "--sammel", "--profiles", str(PROFILE)])
    assert code == 0
    sammel = ziel / "serie.pdf"
    assert sammel.is_file(), "kein Sammel-PDF"
    assert len(pypdf.PdfReader(str(sammel)).pages) == 2


def test_ohne_die_option_entsteht_keines(tmp_path):
    """Gegenprobe: Sonst wüsste man nicht, ob die Option etwas tut."""
    _lauf(tmp_path)
    assert not (tmp_path / "briefe" / "serie.pdf").exists()


# ── Die Einzelteile ─────────────────────────────────────────────────────────

def test_platzhalter_werden_gefunden():
    assert serie.platzhalter("{{a}} und {{ b }} und {{c-d}}") == {"a", "b", "c-d"}


def test_und_was_keiner_ist_nicht():
    """Gegenprobe zum Muster: Eine einzelne Klammer ist keiner, und ein
    Ausdruck mit Punkt auch nicht — ein Platzhalter zeigt auf eine Spalte."""
    assert serie.platzhalter("{a} und {{ a.b }} und {{}}") == set()


def test_der_dateiname_haelt_sich_an_das_dateisystem():
    """Eine Sperrliste vergisst `:` auf macOS oder `?` auf Windows — und der
    Fehler fällt erst auf dem anderen System auf."""
    name = serie.dateiname({"n": 'Müller & Söhne: "GmbH"/AG?'}, 7, "n")
    assert name.startswith("007-")
    for zeichen in ':"/?&':
        assert zeichen not in name, name


def test_ohne_benennungsspalte_bleibt_die_nummer():
    assert serie.dateiname({"n": "Kern"}, 3) == "003"
