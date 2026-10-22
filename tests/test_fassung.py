"""Die Fassungs-Kopfzeile `X-Falzmarke-Fassung` (ADR 0051).

Jede `.eml` trägt die ersten zwölf Hex-Zeichen des SHA-256 ihrer Quelle. Damit
lässt sich eine gesendete Mail ihrer Quelle zuordnen, auch wenn ein
Mailprogramm Betreff oder Text umbaut. Kopfzeilen gehen nach außen — deshalb
steht dort **kein Pfad und kein Dateiname**, nur der Hash.
"""

from __future__ import annotations

import email
import hashlib
import re
from email import policy

from conftest import PROFILE
from falzmarke import cli as falzmarke
from falzmarke import pruefung_eml

MAIL = """---
typ: email
profil: example
an: erika.muster@example.de
betreff: Angebot Nr. 2026-0815
anrede: Sehr geehrte Frau Muster,
---
wie besprochen erhalten Sie unser Angebot.
"""


def _setze(tmp_path, inhalt=MAIL, name="geheimer-kunde_angebot"):
    quelle = tmp_path / f"{name}.md"
    quelle.write_text(inhalt, encoding="utf-8")
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / name, profil_verzeichnis=PROFILE)
    return quelle, email.message_from_bytes(pfad.read_bytes(), policy=policy.default)


def test_die_kopfzeile_ist_der_hash_der_quelle(tmp_path):
    quelle, nachricht = _setze(tmp_path)
    erwartet = hashlib.sha256(quelle.read_text(encoding="utf-8").encode("utf-8")).hexdigest()[:12]
    assert nachricht["X-Falzmarke-Fassung"] == erwartet
    assert re.fullmatch(r"[0-9a-f]{12}", erwartet)


def test_kein_pfad_und_kein_dateiname_in_den_kopfzeilen(tmp_path):
    quelle, nachricht = _setze(tmp_path)
    kopf = "".join(f"{k}: {v}\n" for k, v in nachricht.items())
    assert "geheimer-kunde" not in kopf and str(tmp_path) not in kopf


def test_eine_geaenderte_quelle_ergibt_eine_andere_fassung(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, eins = _setze(tmp_path / "a")
    _, zwei = _setze(tmp_path / "b", MAIL.replace("unser Angebot", "unser neues Angebot"))
    assert eins["X-Falzmarke-Fassung"] != zwei["X-Falzmarke-Fassung"]


def test_dieselbe_quelle_ergibt_dieselbe_fassung(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, eins = _setze(tmp_path / "a")
    _, zwei = _setze(tmp_path / "b", name="anderer-name")
    assert eins["X-Falzmarke-Fassung"] == zwei["X-Falzmarke-Fassung"], \
        "der Dateiname darf die Fassung nicht ändern"


def test_windows_zeilenenden_aendern_die_fassung_nicht(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, eins = _setze(tmp_path / "a")
    quelle = tmp_path / "b" / "crlf.md"
    quelle.write_bytes(MAIL.replace("\n", "\r\n").encode("utf-8"))
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / "b" / "crlf", profil_verzeichnis=PROFILE)
    zwei = email.message_from_bytes(pfad.read_bytes(), policy=policy.default)
    assert eins["X-Falzmarke-Fassung"] == zwei["X-Falzmarke-Fassung"]


def test_die_pruefung_der_nachricht_bleibt_gruen(tmp_path):
    quelle = tmp_path / "m.md"
    quelle.write_text(MAIL, encoding="utf-8")
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / "m", profil_verzeichnis=PROFILE)
    bericht = pruefung_eml.pruefe(pfad)
    assert bericht.ok, bericht.als_text()
