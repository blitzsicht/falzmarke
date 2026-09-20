"""veraPDF wird mit fester Version geladen, und seine Prüfsumme wird vor dem Entpacken gehalten (#195).

WARUM ES DAS GIBT

Der Job `pdf-konformitaet` lud den Installer von einer Latest-URL
(`.../releases/verapdf-installer.zip`), entpackte ihn über einen Glob und führte ihn
aus — ohne Version, ohne Prüfsumme, ohne Verifikation. Es war die einzige
Blind-Ausführung im Repository: Alle `uses:`-Einträge stehen auf 40-stelligen
Commit-SHAs. Und es traf ausgerechnet den Prüfer, auf den sich die PDF/A- und
PDF/UA-Aussagen stützen (`docs/pruefkatalog-2026-08-30.md`, Fund 2). Ein Beleg,
dessen Herkunft niemand prüft, trägt weniger, als er zu tragen scheint.

WORAN DIESE DATEI MISST

Nicht am Wortlaut des Schritts, sondern an seinem Verhalten. Der Test holt die
`run`-Schritte, die veraPDF laden und den Installer starten, aus `ci.yml` und führt
sie in einem Wegwerfordner aus. `curl` ist dabei ein Nachbau, der eine kleine
ZIP-Datei liefert und die aufgerufene URL protokolliert; `unzip` ist das echte, mit
einem Protokoll davor; der Installer in der ZIP-Datei schreibt nur eine Zeile ins
Protokoll. Gemessen wird dann:

* mit passendem Digest lädt der Schritt die versionierte URL und startet den Installer;
* bei jeder Abweichung wird der Job rot, **bevor** entpackt wird — der Installer läuft nie.

Beide Hälften gehören zusammen: Erst dass der Aufbau mit passendem Digest bis zum
Installer durchläuft, macht das Ausbleiben bei falschem Digest zu einer Aussage.
Sonst wäre „bricht ab" auch bei einem Nachbau grün, der immer abbricht.

Drei Abweichungen, je einzeln gefahren:

* der gepinnte Digest, eine andere Datei;
* die richtige Datei, der Digest um ein Zeichen verfälscht;
* der richtige Digest, die Datei um ein Byte länger — dieselbe ZIP-Datei bleibt
  entpackbar, nur die Prüfsumme kann den Unterschied bemerken.

VEREINBARUNG MIT DER UMSETZUNG

Der Schritt bleibt ein Shell-Schritt in `ci.yml`, der `curl` und `unzip` benutzt und den
Installer als `verapdf-install` startet — so steht es im Issue. Version und Digest
stehen ebenfalls in `ci.yml`: an genau einer Stelle, nah beieinander, mit einem Datum in
einem Kommentar daneben.

Die Werte unten sind die aus dem Issue (Nachmessung vom 31.08.2026). Wer die Version
anhebt, ändert sie hier absichtlich mit: Der Digest gehört zur Version, und dass er
mitgezogen wurde, soll ein Diff zeigen, nicht ein Zufall.

WAS DIESE DATEI NICHT KANN

* Sie belegt nicht, dass der Job **in der CI** rot wird. Das zeigt nur ein Lauf dort
  (ein Wegwerf-Commit mit falschem Digest); ohne ihn bleibt die Gegenprobe der CI offen
  und ist auch so zu melden.
* Sie belegt keine Echtheit. Ein Digest schützt davor, dass sich die Datei später still
  ändert, nicht davor, dass sie von Anfang an eine andere war. Die GPG-Signatur ist
  bewusst nicht Teil dieses Vorgangs.
* Auf Windows läuft der Verhaltenstest nicht: Der Schritt läuft in der CI nur auf ubuntu.
  Auf Linux **scheitert** er statt zu überspringen, wenn `bash` oder `unzip` fehlen.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from conftest import REPO

CI = REPO / ".github" / "workflows" / "ci.yml"
JOB = "pdf-konformitaet"

# Die Werte aus Issue #195. URL und Digest sind gemessen, nicht geraten: Das
# Schema der URL war nicht zu erraten (`verapdf-installer-1.30.2.zip`,
# `1.30/verapdf-installer.zip` und die Fassung ohne Verzeichnis liefern 404).
VERSION = "1.30.2"
URL = "https://software.verapdf.org/releases/1.30/verapdf-greenfield-1.30.2-installer.zip"
DIGEST = "6cc6341cb1af644044054b81f00a6590a7918abb18f762243de115258bcad838"
assert re.fullmatch(r"[0-9a-f]{64}", DIGEST), "Abschreibfehler im Digest aus Issue #195"

# Ein Diff zeigt standardmäßig drei Zeilen Umfeld. Steht der Digest weiter von
# der Version entfernt, hebt jemand die Version an und sieht ihn im Diff nicht.
DIFF_UMFELD = 3

DATUM_IM_KOMMENTAR = re.compile(r"#.*(\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{2}-\d{2})")
STAND_UMKREIS = 6

ANNAHME = (
    f"Testannahme: der Digest aus Issue #195 ({DIGEST[:16]}…) steht nicht in ci.yml. "
    "Ohne ihn lässt sich weder der passende noch der abweichende Fall herstellen."
)


def _befehlszeilen(text: str) -> list[tuple[int, str]]:
    """Alle Zeilen ohne Kommentaranteil, mit ihrer Nummer (ab 1)."""
    zeilen = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        ohne_kommentar = re.sub(r"#.*$", "", zeile)
        if ohne_kommentar.strip():
            zeilen.append((nr, ohne_kommentar))
    return zeilen


def _zeilen_mit(text: str, gesucht: str) -> list[int]:
    return [nr for nr, zeile in _befehlszeilen(text) if gesucht in zeile]


# ── statisch: was im Repository steht ────────────────────────────────────────

def test_keine_latest_url_mehr_in_der_ci():
    treffer = [
        f"ci.yml:{nr}: {zeile.strip()}"
        for nr, zeile in _befehlszeilen(CI.read_text(encoding="utf-8"))
        if re.search(r"releases/verapdf-installer\.zip", zeile)
    ]
    assert not treffer, (
        "veraPDF kommt weiter von einer Latest-URL ohne Version — der Installer, "
        "der ausgeführt wird, kann sich zwischen zwei Läufen ändern:\n  " + "\n  ".join(treffer)
    )


def test_der_digest_steht_genau_einmal_in_ci_yml():
    stellen = _zeilen_mit(CI.read_text(encoding="utf-8"), DIGEST)
    assert len(stellen) == 1, (
        f"Der Digest aus Issue #195 steht in {len(stellen)} Zeilen von ci.yml "
        f"({stellen}); erwartet genau eine. Null heißt: nicht gepinnt. Mehr als "
        "eine heißt: beim Anheben der Version bleibt eine Kopie alt."
    )


def test_die_version_steht_an_genau_einer_stelle():
    stellen = _zeilen_mit(CI.read_text(encoding="utf-8"), VERSION)
    assert len(stellen) == 1, (
        f"Die Version {VERSION} steht in {len(stellen)} Zeilen von ci.yml ({stellen}); "
        "erwartet genau eine Stelle, an der man sie anhebt. Kommentare zählen nicht mit."
    )


def test_digest_und_version_stehen_im_selben_diff():
    text = CI.read_text(encoding="utf-8")
    digest, version = _zeilen_mit(text, DIGEST), _zeilen_mit(text, VERSION)
    assert digest and version, (
        f"Digest in Zeilen {digest}, Version in Zeilen {version} — eines von beiden "
        "steht gar nicht in ci.yml."
    )
    abstand = abs(digest[0] - version[0])
    assert abstand <= DIFF_UMFELD, (
        f"Digest (Zeile {digest[0]}) und Version (Zeile {version[0]}) liegen {abstand} Zeilen "
        f"auseinander, mehr als das Umfeld von {DIFF_UMFELD} Zeilen, das ein Diff zeigt. "
        "Wer die Version anhebt, sähe den Digest nicht mitziehen."
    )


def test_beim_pin_steht_ein_datum():
    """„Sichtbar, wann sie zuletzt angefasst wurde" — ohne `git blame` zu brauchen."""
    text = CI.read_text(encoding="utf-8")
    stellen = _zeilen_mit(text, DIGEST)
    assert stellen, ANNAHME
    zeilen = text.splitlines()
    mitte = stellen[0]
    umkreis = zeilen[max(0, mitte - 1 - STAND_UMKREIS): mitte + STAND_UMKREIS]
    assert any(DATUM_IM_KOMMENTAR.search(z) for z in umkreis), (
        f"Im Umkreis von {STAND_UMKREIS} Zeilen um den Digest (Zeile {mitte}) steht in "
        "keinem Kommentar ein Datum (TT.MM.JJJJ oder JJJJ-MM-TT). Eine Zahl ohne "
        "Standangabe altert still."
    )


# ── Verhalten: der Schritt, wirklich ausgeführt ──────────────────────────────

def _sha256(daten: bytes) -> str:
    return hashlib.sha256(daten).hexdigest()


def _installer_zip() -> bytes:
    """Eine Miniatur des Installers: ein Verzeichnis mit einem Skript, das nur protokolliert.

    Das Verzeichnis heißt wie im echten Archiv (`verapdf-greenfield-<Version>`), damit
    ein Glob oder ein Name mit Version dasselbe findet wie in der CI.
    """
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as z:
        info = zipfile.ZipInfo(f"verapdf-greenfield-{VERSION}/verapdf-install",
                               date_time=(2026, 9, 20, 0, 0, 0))
        info.external_attr = 0o755 << 16
        z.writestr(info, '#!/bin/sh\necho "$@" >> "$STUB_INSTALLER_LOG"\n')
    return puffer.getvalue()


CURL_NACHBAU = """#!/bin/sh
# Protokolliert jeden Aufruf und liefert statt des Netzes die Datei aus STUB_NUTZLAST.
printf '%s\\n' "$*" >> "$STUB_CURL_LOG"
ziel=""
vorher=""
letztes=""
for a in "$@"; do
  case "$vorher" in
    -o|--output|-[A-Za-z]*o) ziel="$a" ;;
  esac
  case "$a" in
    --output=*) ziel="${a#--output=}" ;;
    -O|--remote-name) namen=1 ;;
  esac
  vorher="$a"
  letztes="$a"
done
[ -n "$namen" ] && ziel="$(basename "$letztes")"
if [ -n "$ziel" ]; then cp "$STUB_NUTZLAST" "$ziel"; else cat "$STUB_NUTZLAST"; fi
"""

UNZIP_MIT_PROTOKOLL = """#!/bin/sh
# Das echte unzip, aber mit Spur: Wer nach dem Digest entpackt, soll es hier zeigen.
printf '%s\\n' "$*" >> "$STUB_UNZIP_LOG"
exec "$STUB_ECHTES_UNZIP" "$@"
"""

JAVA_NACHBAU = "#!/bin/sh\nexit 0\n"

# macOS liefert kein `sha256sum` mit, die Runner der CI schon. Ohne diese Zeile
# scheiterte ein korrekter Schritt lokal am Betriebssystem statt am Digest.
SHA256SUM_ALS_SHASUM = '#!/bin/sh\nexec shasum -a 256 "$@"\n'


@dataclass
class Lauf:
    rot: bool
    ausgabe: str
    urls: list[str]
    entpackt: bool
    installer_lief: bool

    def bericht(self) -> str:
        return (f"rot={self.rot} urls={self.urls} entpackt={self.entpackt} "
                f"installer_lief={self.installer_lief}\n--- Ausgabe ---\n{self.ausgabe[-1500:]}")


def _werkzeug_da() -> str:
    """Pfad des echten unzip. Auf Linux ein Fehler, sonst eine Auslassung."""
    if sys.platform.startswith("win"):
        pytest.skip("der Schritt läuft in der CI nur auf ubuntu; der Nachbau braucht POSIX-Shell")
    fehlt = [n for n in ("bash", "unzip") if not shutil.which(n)]
    if fehlt:
        grund = f"{', '.join(fehlt)} fehlt — der Verhaltenstest kann nicht laufen"
        if sys.platform.startswith("linux"):
            # Übersprungen belegt nichts; auf dem Runner, auf dem der Schritt läuft,
            # muss die Messung stattfinden.
            pytest.fail(grund)
        pytest.skip(grund)
    return str(shutil.which("unzip"))


def _veraPDF_schritte(ci_text: str) -> tuple[list[dict], dict[str, str]]:
    """Die `run`-Schritte vom ersten, der veraPDF nennt, bis zu dem, der den Installer startet."""
    plan = yaml.safe_load(ci_text)
    job = plan["jobs"][JOB]
    schritte = job["steps"]
    laufend = [i for i, s in enumerate(schritte) if "run" in s]
    start = next((i for i in laufend if "verapdf" in schritte[i]["run"].lower()), None)
    ende = [i for i in laufend
            if re.search(r"(?<![\w-])verapdf-install(?![\w.-])", schritte[i]["run"])]
    assert start is not None and ende, (
        f"Im Job {JOB} steht kein `run`-Schritt, der veraPDF lädt und `verapdf-install` "
        "startet — die Vereinbarung dieser Datei (ein Shell-Schritt in ci.yml) ist verletzt."
    )
    umgebung = {}
    for quelle in (plan.get("env"), job.get("env")):
        umgebung.update({k: str(v) for k, v in (quelle or {}).items()})
    return schritte[start: ende[-1] + 1], umgebung


def _fahre(ci_text: str, nutzlast: bytes, ort: Path) -> Lauf:
    """Führt die veraPDF-Schritte aus ci_text aus; `nutzlast` ist, was curl „herunterlädt"."""
    echtes_unzip = _werkzeug_da()
    schritte, umgebung_ci = _veraPDF_schritte(ci_text)

    bin_, protokoll, tmp, arbeit = (ort / n for n in ("bin", "protokoll", "tmp", "arbeit"))
    for verzeichnis in (bin_, protokoll, tmp, arbeit):
        verzeichnis.mkdir()
    nachbauten = {"curl": CURL_NACHBAU, "unzip": UNZIP_MIT_PROTOKOLL, "java": JAVA_NACHBAU}
    if not shutil.which("sha256sum"):
        nachbauten["sha256sum"] = SHA256SUM_ALS_SHASUM
    for name, inhalt in nachbauten.items():
        (bin_ / name).write_text(inhalt, encoding="utf-8")
        (bin_ / name).chmod(0o755)

    nutzlast_datei = ort / "nutzlast.zip"
    nutzlast_datei.write_bytes(nutzlast)
    curl_log, unzip_log, installer_log = (protokoll / n for n in ("curl", "unzip", "installer"))

    def ersetze(text: str, umgebung: dict[str, str]) -> str:
        # Was GitHub vor der Shell auflöst, löst der Nachbau ebenso auf. Alles
        # andere wäre geraten und bricht laut.
        bekannt = {"github.workspace": str(arbeit), "runner.temp": str(tmp)}
        bekannt.update({f"env.{k}": v for k, v in umgebung.items()})

        def wert(m):
            name = m.group(1).strip()
            if name not in bekannt:
                pytest.fail(f"Ausdruck ${{{{ {name} }}}} in ci.yml ist im Nachbau nicht bekannt")
            return bekannt[name]

        text = re.sub(r"\$\{\{(.*?)\}\}", wert, text)
        # Der Schritt schreibt nach /tmp; der Test schreibt dorthin nicht, sondern in seinen Ordner.
        return re.sub(r"/tmp\b", str(tmp), text)

    ausgabe: list[str] = []
    rot = False
    for nr, schritt in enumerate(schritte):
        umgebung_schritt = {**umgebung_ci, **{k: str(v) for k, v in (schritt.get("env") or {}).items()}}
        umgebung_schritt = {k: ersetze(v, umgebung_schritt) for k, v in umgebung_schritt.items()}
        umgebung = dict(os.environ)
        umgebung.update({
            "PATH": os.pathsep.join([str(bin_), os.environ.get("PATH", "")]),
            "GITHUB_PATH": str(ort / "github_path"),
            "GITHUB_WORKSPACE": str(arbeit),
            "RUNNER_TEMP": str(tmp),
            "STUB_NUTZLAST": str(nutzlast_datei),
            "STUB_CURL_LOG": str(curl_log),
            "STUB_UNZIP_LOG": str(unzip_log),
            "STUB_INSTALLER_LOG": str(installer_log),
            "STUB_ECHTES_UNZIP": echtes_unzip,
            **umgebung_schritt,
        })
        # Ohne `shell:` startet GitHub `bash -e {0}`; `shell: bash` ist strenger (pipefail).
        shell = schritt.get("shell")
        if shell not in (None, "bash"):
            pytest.fail(f"`shell: {shell}` ist im Nachbau nicht vorgesehen")
        optionen = ["-e"] if shell is None else ["--noprofile", "--norc", "-eo", "pipefail"]
        skript = ort / f"schritt-{nr}.sh"
        skript.write_text(ersetze(schritt["run"], umgebung_schritt) + "\n", encoding="utf-8")
        lauf = subprocess.run(["bash", *optionen, str(skript)], cwd=arbeit, env=umgebung,
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
        ausgabe.append(f"[Schritt {nr}: {schritt.get('name', '?')}] Exit {lauf.returncode}\n"
                       f"{lauf.stdout}{lauf.stderr}")
        if lauf.returncode != 0:
            rot = True
            break  # wie GitHub: ein roter Schritt beendet den Job

    urls = []
    if curl_log.exists():
        for zeile in curl_log.read_text(encoding="utf-8").splitlines():
            urls += [t.strip("'\"") for t in zeile.split() if t.strip("'\"").startswith("http")]
    return Lauf(rot=rot, ausgabe="\n".join(ausgabe), urls=urls,
                entpackt=unzip_log.exists(), installer_lief=installer_log.exists())


def test_passender_digest_laedt_die_versionierte_url_und_installiert(tmp_path):
    """Die Hälfte, ohne die das Ausbleiben unten nichts sagt: mit passendem Digest geht es durch."""
    text = CI.read_text(encoding="utf-8")
    assert DIGEST in text, ANNAHME
    nutzlast = _installer_zip()

    lauf = _fahre(text.replace(DIGEST, _sha256(nutzlast)), nutzlast, tmp_path)

    assert not lauf.rot, "Der Schritt scheitert, obwohl der Digest passt:\n" + lauf.bericht()
    assert URL in lauf.urls, f"Geladen wurde nicht {URL}:\n" + lauf.bericht()
    assert lauf.entpackt and lauf.installer_lief, (
        "Der Schritt erreicht mit passendem Digest den Installer nicht:\n" + lauf.bericht()
    )


@pytest.mark.parametrize("fall", ["andere-datei", "digest-verfaelscht", "datei-ein-byte-laenger"])
def test_abweichung_bricht_vor_dem_entpacken_ab(fall, tmp_path):
    text = CI.read_text(encoding="utf-8")
    nutzlast = _installer_zip()

    if fall == "andere-datei":
        # Der gepinnte Digest bleibt, wie er im Repository steht; die Datei ist eine andere.
        ci, geliefert = text, nutzlast
    else:
        assert DIGEST in text, ANNAHME
        passend = _sha256(nutzlast)
        if fall == "digest-verfaelscht":
            letzte = "0" if passend[-1] != "0" else "1"
            ci, geliefert = text.replace(DIGEST, passend[:-1] + letzte), nutzlast
        else:
            # Der Digest passt zur Originaldatei; geliefert wird sie mit einem Byte mehr.
            ci, geliefert = text.replace(DIGEST, passend), nutzlast + b"\x00"

    lauf = _fahre(ci, geliefert, tmp_path)

    assert lauf.rot, (
        "Der Job blieb grün, obwohl die heruntergeladene Datei nicht zum gepinnten "
        "Digest passt:\n" + lauf.bericht()
    )
    assert not lauf.entpackt, (
        "Es wurde entpackt, bevor (oder ohne dass) der Digest geprüft war:\n" + lauf.bericht()
    )
    assert not lauf.installer_lief, "Ein ungeprüfter Installer wurde ausgeführt:\n" + lauf.bericht()
    # Ohne diese Zeile könnte der Abbruch von irgendwo herrühren, nur nicht von der Prüfung.
    assert URL in lauf.urls, (
        f"Der Abbruch kam, bevor {URL} geladen wurde — er sagt nichts über den Digest:\n"
        + lauf.bericht()
    )
