"""Was aus einem Postfach-Entwurf wurde — `falzmarke status` (ADR 0055).

Die Frage kam immer wieder: Ist das schon raus? Hat er etwas geändert? Liegt
der Entwurf noch, oder ist er gelöscht? Drei Quellen beantworten sie, und
keine reicht allein:

* **das Entwurfsbuch** — falzmarke trägt jeden Entwurf ein, den es per
  `APPEND` ins Postfach legt (ADR 0051): Konto, UID, Fassung, Betreff,
  Empfänger und den Text. Eine Datei auf diesem Rechner, nicht im Postfach.
  Nur so ist nach dem Senden noch bekannt, was im Entwurf stand.
* **das Postfach** — was jetzt in „Entwürfe“, „Gesendete Elemente“ und im
  Papierkorb liegt, nur lesend über den Proxy (`postfach.py`). Es sieht auch,
  was vom Handy gesendet wurde.
* **das Tagebuch der Entwurfsbrücke** — was Thunderbird selbst gesehen hat:
  geöffnet, gespeichert, gesendet, ohne Senden geschlossen, von der Sperre
  angehalten. Das Add-on schreibt es als Datei ins Thunderbird-Profil; gelesen
  wird es hier direkt, auch wenn Thunderbird zu ist.

**BELEGT** heißt: Postfach und Tagebuch sagen beide „gesendet“. Thunderbird
wirft `X-Falzmarke-Fassung` beim Senden weg und vergibt eine neue Message-ID
(gemessen am 25.10.2026). Die gesendete Mail findet sich deshalb über
Empfänger und Text, wie in der Prüfung vor dem Entwurf (`gesendet.py`), und
über die Fassung, die das Tagebuch zu ihrer Message-ID kennt (ADR 0056).

Ab Add-on 0.3.0 nennt `status` außerdem, was ein offenes Fenster hinausschicken
würde (Absender, Empfänger samt Bcc, Anhänge, ob der Text noch der angelegte
ist), und wohin eine gesendete Mail laut Tagebuch ging.

Kein `subprocess` (ADR 0038, Punkt 5). Der MCP-Dienst lädt dieses Modul nicht.
"""

from __future__ import annotations

import difflib
import email
import json
import os
import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from email import policy
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote

#: Wo das Entwurfsbuch liegt, wenn `FALZMARKE_ENTWURFSBUCH` nichts sagt. Eine
#: Modulkonstante, damit `conftest.py` sie für jeden Test umlegt: Kein Testlauf
#: schreibt in das Buch des Rechners, auf dem er läuft.
BUCH_VORGABE = (Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
                / "falzmarke" / "entwuerfe.jsonl")

#: Der Name des Tagebuchs im Thunderbird-Profil. Schreibt nur das Add-on.
TAGEBUCH = "entwurfsbruecke-tagebuch.jsonl"

#: Was das Add-on ins Tagebuch schreibt, und wie `status` es nennt.
#: `tests/test_entwurfsbruecke_hintergrund.py` hält beide Seiten gleich.
TAGEBUCH_WORTE = {
    "geoeffnet": "geöffnet", "gespeichert": "gespeichert", "gesendet": "gesendet",
    "geschlossen": "ohne Senden geschlossen", "gesperrt": "Sperre hielt an",
    "trotzdem": "trotz Sperre gesendet", "senden_fehlgeschlagen": "Senden scheiterte",
    "pruefung_fehlgeschlagen": "Sperre konnte nicht prüfen"}

#: So weit zurück sieht `status` ohne `--tage`.
TAGE_VORGABE = 14

#: So viele gesendete Mails sieht `status` höchstens an. Nur Kopfzeilen; ein
#: Bestellpostfach verschickt in vierzehn Tagen leicht mehr als die 500 von
#: `postfach.GRENZE` (gemessen 25.10.2026: 550).
GRENZE_GESENDET = 3000

#: Zeitlimit der ganzen Sitzung. Länger als beim Ablegen: Wer vierzehn Tage
#: Gesendetes an denselben Empfänger liest, lädt auch dessen Anhänge.
FRIST_S = 120

#: Eine gesendete Mail, die kurz vor dem Eintrag datiert ist, gehört noch dazu:
#: `Date` der gesendeten Mail stammt nicht unbedingt von der Uhr, die den Eintrag schrieb.
SPIEL = timedelta(minutes=5)

#: Höchstens so viele Zeilen zeigt `--diff` je Entwurf.
DIFF_ZEILEN = 60


# ── Das Entwurfsbuch ────────────────────────────────────────────────────────

class Eintrag(NamedTuple):
    """Ein Entwurf, den falzmarke ins Postfach gelegt hat."""

    zeit: datetime
    konto: str
    uid: str
    fassung: str
    betreff: str
    an: tuple[str, ...]
    text: str
    ordner: str = ""
    #: Bcc des Entwurfs. None bei Einträgen von vor 0.11 (ADR 0056): Dann ist
    #: unbekannt, ob ein Bcc geplant war, und `status` vergleicht ohne.
    blindkopie: tuple[str, ...] | None = None


def buchpfad(umgebung: Mapping[str, str] | None = None) -> Path | None:
    """Die Datei des Entwurfsbuchs — oder None bei `FALZMARKE_ENTWURFSBUCH=nie`."""
    umgebung = os.environ if umgebung is None else umgebung
    wert = (umgebung.get("FALZMARKE_ENTWURFSBUCH") or "").strip()
    if wert.lower() == "nie":
        return None
    return Path(wert).expanduser() if wert else BUCH_VORGABE


def eintragen(ablage, felder: Mapping, *, umgebung: Mapping[str, str] | None = None,
              jetzt: datetime | None = None) -> str:
    """Hängt den eben abgelegten Entwurf ans Buch. Rückgabe: leer, sonst der Grund.

    Geworfen wird nichts — der Entwurf liegt schon im Postfach, und ein Buch,
    das sich nicht schreiben lässt, macht ihn nicht ungültig. Der Aufrufer
    meldet den Grund, damit `status` später nicht still weniger weiß.
    """
    from falzmarke import gesendet

    pfad = buchpfad(umgebung)
    if pfad is None:
        return "FALZMARKE_ENTWURFSBUCH=nie ist gesetzt"
    roh = felder.get("roh") or b""
    text = gesendet.klartext(email.message_from_bytes(bytes(roh), policy=policy.default))
    zeile = {
        "zeit": (jetzt or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "konto": ablage.adresse.strip().lower(),
        "ordner": ablage.ordner,
        "uid": str(ablage.uid),
        "fassung": str(felder.get("fassung") or "").strip(),
        "betreff": str(felder.get("betreff") or ""),
        "an": [str(a).lower() for a in (felder.get("an") or []) + (felder.get("kopie") or [])],
        "blindkopie": [str(a).lower() for a in felder.get("blindkopie") or []],
        "text": text,
    }
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("a", encoding="utf-8") as datei:
            datei.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError as fehler:
        return f"{pfad}: {fehler.strerror or fehler}"
    return ""


def _zeit(wert) -> datetime | None:
    try:
        zeit = datetime.fromisoformat(str(wert))
    except ValueError:
        return None
    return zeit if zeit.tzinfo else zeit.replace(tzinfo=timezone.utc)


def _jsonzeilen(pfad: Path | None) -> list[dict]:
    """Die Zeilen einer JSONL-Datei, die sich lesen lassen. Fehlt sie: keine."""
    if pfad is None or not pfad.is_file():
        return []
    zeilen = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            wert = json.loads(zeile)
        except ValueError:
            continue  # eine halb geschriebene letzte Zeile
        if isinstance(wert, dict):
            zeilen.append(wert)
    return zeilen


def lesen(umgebung: Mapping[str, str] | None = None) -> list[Eintrag]:
    eintraege = []
    for zeile in _jsonzeilen(buchpfad(umgebung)):
        zeit = _zeit(zeile.get("zeit"))
        # Eine UID ist eine Zahl; eine andere Zeile hat nicht falzmarke geschrieben.
        if zeit is None or not zeile.get("konto") or not str(zeile.get("uid") or "").isdigit():
            continue
        eintraege.append(Eintrag(
            zeit=zeit, konto=str(zeile["konto"]).lower(), uid=str(zeile["uid"]),
            fassung=str(zeile.get("fassung") or ""), betreff=str(zeile.get("betreff") or ""),
            an=tuple(str(a).lower() for a in zeile.get("an") or []),
            text=str(zeile.get("text") or ""), ordner=str(zeile.get("ordner") or ""),
            blindkopie=(tuple(str(a).lower() for a in zeile["blindkopie"])
                        if isinstance(zeile.get("blindkopie"), list) else None)))
    return eintraege


def tagebuch(profilordner: Path | None = None) -> tuple[list[dict], str]:
    """Die Einträge des Add-on-Tagebuchs und ein Hinweis, warum es fehlt (sonst leer)."""
    from falzmarke import oeffnen

    ordner = oeffnen.THUNDERBIRD_ORDNER if profilordner is None else Path(profilordner)
    profil = oeffnen.thunderbird_standardprofil(ordner)
    if profil is None:
        return [], f"kein Thunderbird-Standardprofil unter {ordner}"
    pfad = profil / TAGEBUCH
    if not pfad.is_file():
        return [], "kein Tagebuch im Thunderbird-Profil — die Entwurfsbrücke ab 0.2.0 schreibt es"
    return _jsonzeilen(pfad), ""


def fassungen(eintraege: list[dict]) -> dict[str, str]:
    """Message-ID → Fassung aus den Einträgen „gesendet“ des Tagebuchs (ADR 0056).

    Thunderbird übernimmt `X-Falzmarke-Fassung` beim Senden nicht in die
    gesendete Mail (gemessen 25.10.2026); das Tagebuch kennt sie aus dem Entwurf.
    """
    from falzmarke import gesendet

    aus = {}
    for tag in eintraege:
        ursprung = tag.get("ursprung")
        fassung = str(ursprung.get("fassung") or "") if isinstance(ursprung, Mapping) else ""
        kennung = gesendet.kennung(tag.get("message_id"))
        if tag.get("art") == "gesendet" and kennung and fassung:
            aus[kennung] = fassung
    return aus


# ── Der Abgleich ────────────────────────────────────────────────────────────

class Zustand(NamedTuple):
    """Was aus einem Entwurf wurde.

    `art`:

    - `wartet` — liegt in „Entwürfe“, nicht gesendet
    - `offen` — liegt dort und ist gerade in einem Fenster offen
    - `schon_raus` — liegt noch, aber derselbe Text ging schon hinaus
    - `gesendet` — liegt nicht mehr, und eine gesendete Mail passt;
      `text_gleich` sagt, ob mit dem Text des Entwurfs
    - `ersetzt` — liegt nicht mehr, ein neuerer Entwurf mit demselben Betreff schon
    - `geloescht` — liegt im Papierkorb
    - `verschwunden` — weder in „Entwürfe“ noch gesendet noch im Papierkorb
    """

    art: str
    betreff: str
    an: tuple[str, ...]
    angelegt: datetime | None
    uid: str
    #: Zeiten der gesendeten Mails mit demselben Text, älteste zuerst.
    gesendet: tuple[datetime | None, ...] = ()
    #: Zeiten der gesendeten Mails mit demselben Betreff und anderem Text.
    anders: tuple[datetime | None, ...] = ()
    text_gleich: bool | None = None
    #: Ob das Entwurfsbuch den Entwurf kennt.
    im_buch: bool = False
    #: Die Einträge des Tagebuchs zu diesem Entwurf, in Reihenfolge.
    tagebuch: tuple[dict, ...] = ()
    nachfolger: str = ""
    diff: tuple[str, ...] = ()
    #: Was das offene Fenster jetzt hinausschicken würde (`fenster` der Brücke, ADR 0056).
    fenster: Mapping | None = None
    #: Ob der Text im Fenster noch der des angelegten Entwurfs ist.
    fenster_text_gleich: bool | None = None
    #: Absender, Empfänger und Anhänge laut Tagebuch-Eintrag „gesendet“ (Add-on ab 0.3.0).
    versand: Mapping | None = None
    #: Gesendet, aber nicht im Entwurf / im Entwurf, aber nicht gesendet.
    empfaenger_plus: tuple[str, ...] = ()
    empfaenger_minus: tuple[str, ...] = ()

    @property
    def belegt(self) -> bool:
        """Postfach und Tagebuch sagen beide „gesendet“."""
        return bool(self.gesendet or self.anders) and any(
            t.get("art") == "gesendet" for t in self.tagebuch)


class Bericht(NamedTuple):
    adresse: str
    zustaende: tuple[Zustand, ...] = ()
    #: Leer heißt geprüft. Sonst ist nichts geprüft, und das ist kein „nichts gefunden“.
    grund: str = ""
    entwuerfe: str = ""
    gesendet: str = ""
    papierkorb: str = ""
    angesehen: int = 0
    tage: int = TAGE_VORGABE
    im_buch: int = 0
    tagebuch: int = 0
    hinweise: tuple[str, ...] = ()


def _offene_uids(adresse: str, umgebung: Mapping[str, str]) -> tuple[dict[str, dict], str]:
    """UID → was die Brücke über das Fenster meldet, in dem dieser Entwurf offen ist."""
    from falzmarke import bruecke

    try:
        fenster = bruecke.offene_entwuerfe(umgebung=umgebung)
    except bruecke.BrueckenFehler as fehler:
        return {}, f"offene Fenster nicht geprüft: {fehler}"
    uids = {}
    for eintrag in fenster:
        ziel = unquote(str(eintrag.get("draft_id") or "").split("?")[0]).lower()
        treffer = re.search(r"#(\d+)$", ziel)
        if treffer and adresse in ziel:
            uids[treffer.group(1)] = eintrag
    return uids, ""


def _ursprung(tag: Mapping, adresse: str) -> Mapping | None:
    ursprung = tag.get("ursprung")
    if not isinstance(ursprung, Mapping):
        return None
    return ursprung if str(ursprung.get("konto") or "").lower() == adresse else None


def _kette(tagebuch: list[dict], adresse: str, uid: str) -> set[str]:
    """Die UID und alle, unter denen Thunderbird denselben Entwurf neu gespeichert hat.

    Speichern legt einen neuen Entwurf mit neuer UID an; `gespeichert` trägt die
    alte im Ursprung und die neue in `neu_uid`. Gilt in beide Richtungen: Ein
    liegender Entwurf findet so auch, was vor dem Speichern geschah.
    """
    kette = {uid}
    gewachsen = True
    while gewachsen:
        gewachsen = False
        for tag in tagebuch:
            ursprung = _ursprung(tag, adresse)
            neu = tag.get("neu_uid")
            if tag.get("art") != "gespeichert" or ursprung is None or not isinstance(neu, list):
                continue
            glieder = {str(ursprung.get("uid") or "")} | {str(n) for n in neu if n is not None}
            glieder.discard("")
            if glieder & kette and not glieder <= kette:
                kette |= glieder
                gewachsen = True
    return kette


def _gehoert_dazu(tag: Mapping, adresse: str, kette: set[str], fassung: str) -> bool:
    """Über die UID. Die Fassung zählt nur, wenn der Eintrag keine UID kennt:
    Zwei Entwürfe aus derselben Quelle tragen dieselbe (gemessen 25.10.2026)."""
    ursprung = _ursprung(tag, adresse)
    if ursprung is None:
        return False
    uid = str(ursprung.get("uid") or "")
    if uid:
        return uid in kette
    return bool(fassung and str(ursprung.get("fassung") or "") == fassung)


def _fenstertext_gleich(fenster: Mapping | None, vorlage: str) -> bool | None:
    """Ob der Text im offenen Fenster noch der angelegte ist. None: nicht prüfbar.

    Verglichen wird der Kern bis zur Grußformel wie in `gesendet.py`: Thunderbird
    setzt die Konto-Signatur darunter und schreibt Aufzählungszeichen um.
    """
    from falzmarke import gesendet

    if not fenster or not fenster.get("live") or "text" not in fenster or not vorlage:
        return None
    eigen = gesendet.merkmale_aus(empfaenger=(), betreff="", text=vorlage)
    jetzt = gesendet.merkmale_aus(empfaenger=(), betreff="", text=str(fenster["text"]))
    if len(eigen.kern) >= gesendet.KERN_MIN:
        return eigen.kern == jetzt.kern
    return eigen.voll == jetzt.voll


def _versand(eintrag: Eintrag, tagebuch: tuple[dict, ...]) -> dict:
    """Empfänger laut letztem Tagebuch-Eintrag „gesendet“ gegen die des Entwurfs.

    Leer, wenn das Tagebuch keine Empfänger nennt (Add-on vor 0.3.0). Kennt das
    Entwurfsbuch kein Bcc (Eintrag vor 0.11), zählt das Bcc auf keiner Seite.
    """
    versand = next((t for t in reversed(tagebuch)
                    if t.get("art") == "gesendet" and isinstance(t.get("an"), list)), None)
    if versand is None:
        return {}
    gesendet_an = {str(a).lower() for f in ("an", "kopie") for a in versand.get(f) or []}
    geplant = set(eintrag.an)
    if eintrag.blindkopie is not None:
        gesendet_an |= {str(a).lower() for a in versand.get("blindkopie") or []}
        geplant |= set(eintrag.blindkopie)
    return {"versand": versand, "empfaenger_plus": tuple(sorted(gesendet_an - geplant)),
            "empfaenger_minus": tuple(sorted(geplant - gesendet_an))}


def abgleich(adresse: str, *, tage: int = TAGE_VORGABE, mit_diff: bool = False,
             umgebung: Mapping[str, str] | None = None, jetzt: datetime | None = None,
             profilordner: Path | None = None) -> Bericht:
    """Gleicht Entwurfsbuch, Postfach und Tagebuch für eine Absenderadresse ab.

    Wirft nichts: Ist das Postfach nicht zu erreichen, trägt der Bericht den
    Grund, und kein Entwurf gilt als geprüft.
    """
    from falzmarke import gesendet, oeffnen, postfach

    umgebung = os.environ if umgebung is None else umgebung
    adresse = adresse.strip().lower()
    jetzt = jetzt or datetime.now(timezone.utc)
    grenze = jetzt - timedelta(days=tage)
    buch = [e for e in lesen(umgebung) if e.konto == adresse and e.zeit >= grenze]
    tage_eintraege, tagebuch_grund = tagebuch(profilordner)
    tage_eintraege = [t for t in tage_eintraege
                      if (_zeit(t.get("zeit")) or grenze) >= grenze]
    hinweise = [tagebuch_grund] if tagebuch_grund else []
    offen, offen_grund = _offene_uids(adresse, umgebung)
    if offen_grund:
        hinweise.append(offen_grund)

    leer = Bericht(adresse, tage=tage, im_buch=len(buch), tagebuch=len(tage_eintraege),
                   hinweise=tuple(hinweise))
    try:
        sitzung = postfach.verbinde(adresse, umgebung=umgebung, frist=FRIST_S)
    except postfach.PostfachFehler as fehler:
        return leer._replace(grund=str(fehler))
    with sitzung:
        try:
            ordner_e = (oeffnen.thunderbird_ordner(adresse, "draft_folder", profilordner)
                        or sitzung.sonderordner("\\Drafts"))
            ordner_g = (oeffnen.thunderbird_ordner(adresse, "fcc_folder", profilordner)
                        or sitzung.sonderordner("\\Sent") or "Gesendete Elemente")
            ordner_p = sitzung.sonderordner("\\Trash")
            if not ordner_e:
                return leer._replace(grund=f"im Postfach von {adresse} ist kein "
                                           "Entwürfe-Ordner gekennzeichnet")
            liegend = sitzung.koepfe(ordner_e)
            raus = [k for k in sitzung.koepfe(ordner_g, seit=grenze.date(),
                                                 grenze=GRENZE_GESENDET)
                    if k.datum is None or k.datum >= grenze]
            weg = (sitzung.koepfe(ordner_p, seit=grenze.date(), grenze=GRENZE_GESENDET)
                   if ordner_p else [])
            if not ordner_p:
                hinweise.append("kein Papierkorb gekennzeichnet — „gelöscht“ ist nicht prüfbar")
            for name in (ordner_e, ordner_g, ordner_p):
                if name and name in sitzung.gekappt:
                    gefunden, angesehen = sitzung.gekappt[name]
                    hinweise.append(
                        f"„{postfach.utf7_dekodieren(name)}“: nur die neuesten "
                        f"{angesehen} von {gefunden} Mails angesehen — "
                        "was davor liegt, fehlt im Abgleich")
            gleiche: dict[tuple, list] = {}
            for kopf in liegend:
                kern = gesendet.betreff_kern(kopf.betreff)
                if kern:
                    gleiche.setdefault((kern, frozenset(kopf.an)), []).append(kopf)
            for doppelt in gleiche.values():
                if len(doppelt) > 1:
                    hinweise.append(
                        f"{len(doppelt)} Entwürfe „{doppelt[0].betreff}“ an "
                        f"{', '.join(sorted(doppelt[0].an))} liegen (UID "
                        f"{', '.join(k.uid for k in doppelt)}) — nur einen senden")

            gelesen: dict[str, tuple] = {}
            bekannt = fassungen(tage_eintraege)

            def gesendete(kopf):
                if kopf.uid not in gelesen:
                    nachricht = email.message_from_bytes(sitzung.nachricht(ordner_g, kopf.uid),
                                                         policy=policy.default)
                    gelesen[kopf.uid] = (gesendet.merkmale(nachricht, mit_bcc=True,
                                                           fassungen=bekannt),
                                         gesendet.klartext(nachricht))
                return gelesen[kopf.uid]

            def treffer(eigen, ab, stufe):
                gleich, anders = [], []
                for kopf in raus:
                    if not eigen.empfaenger & set(kopf.an):
                        continue
                    if ab is not None and kopf.datum is not None and kopf.datum < ab - SPIEL:
                        continue
                    fremd, text = gesendete(kopf)
                    urteil = gesendet.vergleiche(eigen, fremd)
                    if urteil == "gesendet":
                        gleich.append((kopf, text))
                    # Eine Antwort im selben Faden ist keine geänderte Fassung des Entwurfs:
                    # Sie trägt ein `AW:` mehr (wie die Sperre Antworten auslässt, ADR 0055).
                    elif urteil == "geaendert" and gesendet.antwortstufe(kopf.betreff) <= stufe:
                        anders.append((kopf, text))
                return gleich, anders

            zustaende = []
            erledigt: set[int] = set()
            for kopf in liegend:
                nummer = next((i for i, e in enumerate(buch) if e.uid == kopf.uid
                               and (not e.fassung or e.fassung == kopf.fassung)), None)
                if nummer is not None:
                    erledigt.add(nummer)
                gleich, anders = [], []
                nachricht = None
                fenster = offen.get(kopf.uid)
                if any(set(kopf.an) & set(k.an) for k in raus) or fenster is not None:
                    nachricht = email.message_from_bytes(sitzung.nachricht(ordner_e, kopf.uid),
                                                         policy=policy.default)
                if any(set(kopf.an) & set(k.an) for k in raus):
                    gleich, anders = treffer(gesendet.merkmale(nachricht), None,
                                             gesendet.antwortstufe(kopf.betreff))
                art = ("offen" if fenster is not None else "schon_raus" if gleich else "wartet")
                vorlage = (buch[nummer].text if nummer is not None
                           else gesendet.klartext(nachricht) if nachricht is not None else "")
                kette = _kette(tage_eintraege, adresse, kopf.uid)
                zustaende.append(Zustand(
                    art, kopf.betreff, kopf.an, kopf.datum, kopf.uid,
                    gesendet=tuple(sorted((k.datum for k, _ in gleich), key=_sortzeit)),
                    anders=tuple(sorted((k.datum for k, _ in anders), key=_sortzeit)),
                    im_buch=nummer is not None,
                    tagebuch=tuple(t for t in tage_eintraege
                                   if _gehoert_dazu(t, adresse, kette, kopf.fassung)),
                    fenster=fenster, fenster_text_gleich=_fenstertext_gleich(fenster, vorlage)))

            for nummer, eintrag in enumerate(buch):
                if nummer in erledigt:
                    continue
                eigen = gesendet.merkmale_aus(empfaenger=eintrag.an, betreff=eintrag.betreff,
                                              text=eintrag.text, fassung=eintrag.fassung)
                gleich, anders = treffer(eigen, eintrag.zeit,
                                         gesendet.antwortstufe(eintrag.betreff))
                kette = _kette(tage_eintraege, adresse, eintrag.uid)
                tagebuch_hier = tuple(t for t in tage_eintraege
                                      if _gehoert_dazu(t, adresse, kette, eintrag.fassung))
                nachfolger = next((k.uid for k in sorted(liegend, key=lambda k: -int(k.uid))
                                   if int(k.uid) > int(eintrag.uid)
                                   and set(k.an) & set(eintrag.an)
                                   and gesendet.betreff_kern(k.betreff) == eigen.betreff), "")
                # Was vor diesem Entwurf im Papierkorb lag, ist ein anderer.
                neuer = [k for k in weg if k.datum is None or k.datum >= eintrag.zeit - SPIEL]
                # Der Entwurf selbst: dieselbe Fassung. Derselbe Betreff allein kann auch ein
                # anderer Entwurf sein und reicht nur für „gelöscht“ statt „verschwunden“.
                selbst = bool(eintrag.fassung) and any(k.fassung == eintrag.fassung for k in neuer)
                im_papierkorb = selbst or any(
                    set(k.an) & set(eintrag.an)
                    and gesendet.betreff_kern(k.betreff) == eigen.betreff for k in neuer)
                if gleich or any(t.get("art") == "gesendet" for t in tagebuch_hier):
                    art = "gesendet"
                # Liegt der Entwurf selbst im Papierkorb, hat ihn jemand weggeworfen: Nach dem
                # Senden löscht Thunderbird ihn ohne Papierkorb (`deleteStorage`). Derselbe
                # Betreff mit anderem Text ist dann eine andere Mail, etwa eine Antwort, die kein
                # `AW:` mehr bekam, weil der Betreff schon eines trug (ADR 0055).
                elif anders and not selbst:
                    art = "gesendet"
                elif nachfolger:
                    art = "ersetzt"
                elif im_papierkorb:
                    art = "geloescht"
                else:
                    art = "verschwunden"
                diff = ()
                if mit_diff and anders and not gleich:
                    spaeteste = max(anders, key=lambda t: _sortzeit(t[0].datum))
                    diff = tuple(difflib.unified_diff(
                        eintrag.text.splitlines(), spaeteste[1].splitlines(),
                        "Entwurf", "gesendet", lineterm="", n=1))[:DIFF_ZEILEN]
                zustaende.append(Zustand(
                    art, eintrag.betreff, eintrag.an, eintrag.zeit, eintrag.uid,
                    gesendet=tuple(sorted((k.datum for k, _ in gleich), key=_sortzeit)),
                    anders=tuple(sorted((k.datum for k, _ in anders), key=_sortzeit)),
                    text_gleich=(True if gleich else False if anders else None),
                    im_buch=True, tagebuch=tagebuch_hier, nachfolger=nachfolger, diff=diff,
                    **_versand(eintrag, tagebuch_hier)))
        except postfach.PostfachFehler as fehler:
            return leer._replace(grund=str(fehler), hinweise=tuple(hinweise))

    zustaende.sort(key=lambda z: _sortzeit(z.angelegt), reverse=True)
    return Bericht(adresse, tuple(zustaende), entwuerfe=postfach.utf7_dekodieren(ordner_e),
                   gesendet=postfach.utf7_dekodieren(ordner_g),
                   papierkorb=postfach.utf7_dekodieren(ordner_p) if ordner_p else "",
                   angesehen=len(raus), tage=tage, im_buch=len(buch),
                   tagebuch=len(tage_eintraege), hinweise=tuple(hinweise))


def _sortzeit(zeit: datetime | None) -> datetime:
    return zeit or datetime.min.replace(tzinfo=timezone.utc)


# ── Melden ──────────────────────────────────────────────────────────────────

KOPF = {"wartet": "WARTET", "offen": "OFFEN", "schon_raus": "SCHON RAUS",
        "gesendet": "GESENDET", "ersetzt": "ERSETZT", "geloescht": "GELÖSCHT",
        "verschwunden": "VERSCHWUNDEN"}


def _wann(zeit: datetime | None, zeitzone=None) -> str:
    return zeit.astimezone(zeitzone).strftime("%d.%m. %H:%M") if zeit else "ohne Datum"


def _tagebuchzeile(tagebuch: tuple[dict, ...], zeitzone=None) -> str:
    teile = []
    for eintrag in tagebuch[-4:]:
        art = str(eintrag.get("art"))
        wort = TAGEBUCH_WORTE.get(art, art)
        teile.append(f"{wort} {_wann(_zeit(eintrag.get('zeit')), zeitzone)}")
    return "Tagebuch: " + " · ".join(teile) if teile else ""


def _liste(werte) -> str:
    return ", ".join(str(w) for w in werte or []) or "—"


def _empfaengerzeilen(z: Zustand) -> list[str]:
    """Was im offenen Fenster steht und wohin die Mail laut Tagebuch ging (ADR 0056)."""
    aus = []
    f = z.fenster
    if f and f.get("live"):
        teile = [f"Fenster: von {f.get('identitaet') or '—'}", f"An {_liste(f.get('an'))}"]
        teile += [f"Cc {_liste(f.get('kopie'))}"] if f.get("kopie") else []
        teile += [f"Bcc {_liste(f.get('blindkopie'))}", f"Anhänge {_liste(f.get('anhaenge'))}"]
        if z.fenster_text_gleich is not None:
            teile.append("Text wie angelegt" if z.fenster_text_gleich else "Text geändert")
        if f.get("ungespeichert"):
            teile.append("ungespeichert")
        aus.append(" · ".join(teile))
    elif f:
        aus.append(f"Fenster nicht lesbar: {f.get('fehler') or 'Add-on vor 0.3.0'}")
    v = z.versand
    if v:
        teile = [f"Ging an {_liste(v.get('an'))}"]
        teile += [f"Cc {_liste(v.get('kopie'))}"] if v.get("kopie") else []
        teile += [f"Bcc {_liste(v.get('blindkopie'))}"]
        if "anhaenge" in v:
            teile.append(f"Anhänge {_liste(v.get('anhaenge'))}")
        if z.empfaenger_plus or z.empfaenger_minus:
            abw = ([f"+{a}" for a in z.empfaenger_plus] + [f"−{a}" for a in z.empfaenger_minus])
            teile.append("ABWEICHEND vom Entwurf: " + " ".join(abw))
        else:
            teile.append("Empfänger wie angelegt")
        aus.append(" · ".join(teile))
    return aus


def zeilen(bericht: Bericht, *, zeitzone=None) -> list[str]:
    """Die Ausgabe von `falzmarke status`, eine Zeile je Entwurf."""
    if bericht.grund:
        return [f"NICHT GEPRÜFT  {bericht.adresse}: {bericht.grund}"]
    liegen = sum(z.art in ("wartet", "offen", "schon_raus") for z in bericht.zustaende)
    aus = [(f"OK  {bericht.adresse}: {liegen} in „{bericht.entwuerfe}“, {bericht.im_buch} im "
            f"Entwurfsbuch, {bericht.angesehen} Mails der letzten {bericht.tage} Tage in "
            f"„{bericht.gesendet}“ angesehen, {bericht.tagebuch} Tagebucheinträge")]
    for z in bericht.zustaende:
        an = ", ".join(z.an) or "—"
        kopf = f"{KOPF[z.art]:<13}{_wann(z.angelegt, zeitzone)}  „{z.betreff}“ → {an}"
        if z.art in ("wartet", "offen", "schon_raus"):
            rest = f"liegt in „{bericht.entwuerfe}“ (UID {z.uid})"
            if z.art == "offen":
                rest += ", gerade im Fenster offen"
            if z.gesendet:
                rest += (f" — ging aber {_wann(z.gesendet[-1], zeitzone)} schon raus"
                         + (f" ({len(z.gesendet)}×)" if len(z.gesendet) > 1 else "")
                         + ", nicht noch einmal senden")
            elif z.anders:
                rest += (f" — gleicher Betreff ging {_wann(z.anders[-1], zeitzone)} "
                         "mit anderem Text raus")
        elif z.art == "gesendet":
            zeiten = z.gesendet or z.anders
            if zeiten:
                rest = (f"{_wann(zeiten[0], zeitzone)}"
                        + (f", {len(zeiten)}×" if len(zeiten) > 1 else "")
                        + (", Text unverändert" if z.text_gleich else ", Text geändert"))
            else:
                rest = f"laut Tagebuch, nicht in „{bericht.gesendet}“ gefunden"
            rest += " · BELEGT" if z.belegt else ""
        elif z.art == "ersetzt":
            rest = f"neuer Entwurf UID {z.nachfolger} in „{bericht.entwuerfe}“"
        elif z.art == "geloescht":
            rest = f"in „{bericht.papierkorb}“"
            if z.anders:
                rest += (f" — gleicher Betreff ging {_wann(z.anders[-1], zeitzone)} "
                         "mit anderem Text raus")
        else:
            orte = [bericht.entwuerfe, bericht.gesendet] + ([bericht.papierkorb]
                                                            if bericht.papierkorb else [])
            rest = "weder in " + " noch in ".join(f"„{o}“" for o in orte)
        aus.append(f"{kopf} · {rest}")
        aus.extend(" " * 13 + zeile for zeile in _empfaengerzeilen(z))
        tagebuchzeile = _tagebuchzeile(z.tagebuch, zeitzone)
        if tagebuchzeile:
            aus.append(" " * 13 + tagebuchzeile)
        aus.extend(" " * 13 + d for d in z.diff)
    aus.extend(f"HINWEIS  {h}" for h in bericht.hinweise)
    return aus


def als_json(bericht: Bericht) -> dict:
    """Dasselbe als JSON, für Sitzungen, die damit weiterrechnen."""
    def zeit(z):
        return z.isoformat() if z else None

    return {
        "adresse": bericht.adresse, "geprueft": not bericht.grund, "grund": bericht.grund,
        "tage": bericht.tage, "angesehen": bericht.angesehen, "hinweise": list(bericht.hinweise),
        "entwuerfe": [{
            "zustand": z.art, "betreff": z.betreff, "an": list(z.an), "angelegt": zeit(z.angelegt),
            "uid": z.uid, "gesendet": [zeit(t) for t in z.gesendet],
            "anders_gesendet": [zeit(t) for t in z.anders], "text_gleich": z.text_gleich,
            "im_buch": z.im_buch, "belegt": z.belegt, "nachfolger": z.nachfolger,
            "tagebuch": list(z.tagebuch), "fenster": dict(z.fenster) if z.fenster else None,
            "fenster_text_gleich": z.fenster_text_gleich,
            "versand": dict(z.versand) if z.versand else None,
            "empfaenger_plus": list(z.empfaenger_plus),
            "empfaenger_minus": list(z.empfaenger_minus)} for z in bericht.zustaende],
    }
