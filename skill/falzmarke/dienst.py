"""falzmarke als MCP-Dienst — Briefe setzen und prüfen aus fremden KI-Clients.

ADR 0029 hält fest, was dieser Dienst ist und was nicht: Er **setzt und prüft**,
er befördert nichts. Es gibt deshalb kein Werkzeug, das versendet, ablegt oder
zustellt.

    falzmarke mcp            # Server über stdio, wie MCP-Clients ihn erwarten

Drei Werkzeuge:

    brief_rendern      Markdown mit Frontmatter -> PDF, samt Messbericht
    brief_pruefen      bestehendes PDF nachmessen (auch fremde)
    profile_auflisten  welche Absenderprofile der Server kennt

**Der Messbericht kommt bei jedem Rendern mit.** Das ist keine Bequemlichkeit,
sondern der Gegenstand: Ein Werkzeug, das ein PDF zurückgibt und offen lässt, ob
die Maße stimmen, wäre ein PDF-Generator wie jeder andere.

Das MCP-SDK ist eine **optionale** Abhängigkeit — `pip install 'mcp>=2,<3'`,
oder über das Extra `falzmarke[mcp]`, sobald diese Änderung veröffentlicht ist.
Das Paket selbst liegt seit v0.7.3 auf PyPI; das Extra kommt mit dem nächsten
Release nach dem Merge dazu.
Es bringt 28 Pakete mit — darunter uvicorn, starlette, cryptography und
opentelemetry, also Server- und Auth-Infrastruktur. Ein Werkzeug, das offline
Briefe setzt, soll die nicht mitschleppen; wer den Dienst betreibt, installiert
sie bewusst.
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

from falzmarke.cli import (
    Eingabefehler,
    Umgebungsfehler,
    finde_profile,
    rendere,
)

NAME = "falzmarke"


def _mcp_modul():
    """Das SDK, oder eine Meldung, die sagt, was zu tun ist.

    Gleiches Muster wie cli._typst_modul(): Eine fehlende Abhängigkeit ist ein
    Umgebungsfehler mit einem Befehl in der Meldung, kein nackter ImportError.

    Gebunden an das SDK ab 2.0. In 1.x hiess diese Klasse `FastMCP` und lag
    unter `mcp.server.fastmcp`; wer diesen Dienst gegen 1.x startet, bekommt
    deshalb keinen halb funktionierenden Server, sondern diese Meldung. Der
    Fall ist nicht theoretisch — die erste Fassung dieses Moduls war gegen die
    1.x-API geschrieben und wäre still veraltet, hätte sie niemand gestartet.
    """
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        try:
            import mcp  # noqa: F401
        except ImportError:
            raise Umgebungsfehler(
                "Das Python-Paket 'mcp' fehlt — es gehört nicht zur Grundausstattung.\n"
                "  pip install 'mcp>=2,<3'\n"
                "  Wer falzmarke selbst über pip installiert, nimmt das Extra:\n"
                "  pip install 'falzmarke[mcp]' — ab dem Release, das dieses Extra bringt."
            ) from None
        raise Umgebungsfehler(
            "Das Paket 'mcp' ist da, aber zu alt: MCPServer fehlt.\n"
            "  falzmarke braucht das SDK ab 2.0 — in 1.x hieß die Klasse FastMCP.\n"
            "  pip install -U 'mcp>=2,<3'"
        ) from None
    return MCPServer


def _profilverzeichnis(profil, arbeit: Path) -> tuple[str, Path | None, list[str]]:
    """Nimmt einen Profilnamen oder ein ganzes Profil und liefert beides auflösbar.

    Ein Client ohne Zugriff auf das Dateisystem des Servers kann seinen Absender
    sonst nie mitgeben — er müsste mit den Profilen leben, die zufällig auf dem
    Server liegen. Ein Inline-Profil wird dafür in das Arbeitsverzeichnis
    geschrieben und wie jedes andere geladen; der Server behält nichts davon.

    Bilder bleiben aussen vor: `briefkopf.logo` und `signatur` verweisen auf
    Nachbardateien des Profils, die es hier nicht gibt. Sie werden verworfen —
    aber nicht still: Was wegfiel, steht im Ergebnis des Aufrufs, sonst wundert
    sich der Aufrufer über einen Brief ohne sein Logo und findet keinen Grund.

    Gibt (Profilname, Suchverzeichnis oder None, verworfene Felder) zurück.
    """
    if not profil:
        return "", None, []
    if isinstance(profil, str):
        return profil, None, []
    if not isinstance(profil, dict):
        raise Eingabefehler(
            "profil ist weder ein Name noch ein Profil-Objekt, sondern "
            f"{type(profil).__name__}."
        )

    import yaml

    daten = {**profil}
    verworfen: list[str] = []

    briefkopf = {**daten.get("briefkopf", {})}
    if "logo" in briefkopf:
        briefkopf.pop("logo")
        daten["briefkopf"] = briefkopf
        verworfen.append("briefkopf.logo")
    if "signatur" in daten:
        daten.pop("signatur")
        verworfen.append("signatur")

    verzeichnis = arbeit / "profile"
    verzeichnis.mkdir(parents=True, exist_ok=True)
    (verzeichnis / "inline.yaml").write_text(
        yaml.safe_dump(daten, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return "inline", verzeichnis, verworfen


def _kopf_ergaenzen(text: str, profil: str, form: str | None) -> str:
    """Setzt profil und form ins Frontmatter, wenn der Aufruf sie mitgibt.

    Der Aufrufparameter gewinnt gegen das Frontmatter: Wer beim Aufruf ein
    Profil nennt, meint dieses — sonst müsste er den Brieftext umschreiben, um
    denselben Brief unter einem anderen Absender zu setzen.
    """
    import yaml

    teile = text.split("---", 2)
    kopf = yaml.safe_load(teile[1]) or {} if len(teile) >= 3 else {}
    rumpf = teile[2] if len(teile) >= 3 else text
    if profil:
        kopf["profil"] = profil
    if form:
        kopf["form"] = form.upper()
    return ("---\n" + yaml.safe_dump(kopf, allow_unicode=True, sort_keys=False)
            + "---" + rumpf)


# ── Die drei Werkzeuge ──────────────────────────────────────────────────────

def brief_rendern(brief: str, profil=None, form: str | None = None,
                  als: str = "pfad", ziel: str | None = None) -> dict:
    """Setzt einen Brief und misst ihn nach.

    brief   Markdown mit Frontmatter — der Text selbst, nicht ein Pfad. Ein
            KI-Client hat den Brief im Kontext, nicht auf einer Platte.
    profil  Name eines Profils auf dem Server oder ein ganzes Profil-Objekt.
            Fehlt beides, gilt das im Frontmatter genannte.
    form    "A" oder "B"; ohne Angabe entscheidet Frontmatter oder Profil.
    als     "pfad" (Vorgabe) oder "base64".
    ziel    Wohin das PDF soll. Ohne Angabe in ein Temporärverzeichnis, das
            stehen bleibt — der zurückgegebene Pfad muss gültig sein.

    Der Messbericht ist immer dabei.
    """
    from falzmarke import geometrie

    if als not in ("pfad", "base64"):
        raise Eingabefehler(f"als ist „{als}“ — erlaubt sind „pfad“ und „base64“.")

    with tempfile.TemporaryDirectory(prefix="falzmarke-mcp-") as tmp:
        arbeit = Path(tmp)
        name, verzeichnis, verworfen = _profilverzeichnis(profil, arbeit)

        quelle = arbeit / "brief.md"
        text = brief if brief.lstrip().startswith("---") else f"---\n---\n\n{brief}"
        if name or form:
            text = _kopf_ergaenzen(text, name, form)
        quelle.write_text(text, encoding="utf-8")

        # Ohne "ziel" darf das PDF nicht im Arbeitsverzeichnis liegen: Das raeumt
        # dieser Aufruf beim Verlassen weg, und der zurueckgegebene Pfad zeigte
        # auf eine geloeschte Datei. Ein Verzeichnis, das stehen bleibt, ist das
        # kleinere Uebel — der einfachste Aufruf, brief_rendern(brief), muss
        # funktionieren.
        ausgabe = Path(ziel) if ziel else Path(
            tempfile.mkdtemp(prefix="falzmarke-")) / "brief.pdf"
        pdf, gesetzte_form = rendere(quelle, ausgabe, profil_verzeichnis=verzeichnis)
        bericht = geometrie.pruefe(pdf, gesetzte_form)

        ergebnis = {
            "form": gesetzte_form,
            "bestanden": bericht.ok,
            "bericht": bericht.als_dict(),
            "zusammenfassung": bericht.als_text(),
        }
        if verworfen:
            ergebnis["verworfen"] = {
                "felder": verworfen,
                "grund": "Verweise auf Bilddateien neben dem Profil — die gibt es "
                         "hier nicht. Wer Logo oder Unterschrift braucht, legt das "
                         "Profil auf dem Server ab und nennt es beim Namen.",
            }
        if als == "base64":
            ergebnis["pdf_base64"] = base64.b64encode(pdf.read_bytes()).decode("ascii")
            ergebnis["dateiname"] = pdf.name
        else:
            ergebnis["pfad"] = str(pdf.resolve())
        return ergebnis


def email_setzen(nachricht: str, profil=None, als: str = "pfad",
                 ziel: str | None = None, mit_quelle: bool = False) -> dict:
    """Setzt die E-Mail-Fassung und misst sie nach.

    nachricht    Markdown mit Frontmatter — der Text selbst, nicht ein Pfad.
                 Das Frontmatter muss `typ: email` tragen.
    profil       Name eines Profils auf dem Server oder ein ganzes
                 Profil-Objekt. Fehlt beides, gilt das im Frontmatter genannte.
    als          "pfad" (Vorgabe) oder "base64".
    ziel         Wohin die Dateien sollen. Ohne Angabe in ein
                 Temporärverzeichnis, das stehen bleibt — der zurückgegebene
                 Pfad muss gültig sein.
    mit_quelle   Die Markdown-Quelle als eigener Teil (ADR 0034, Punkt 3).
                 Vorgabe ist ohne: Der Teil macht sichtbar, was im Brief nicht
                 sichtbar wäre.

    **Es wird nichts versendet.** Das Ergebnis sind Dateien; ob und wann sie
    jemand abschickt, entscheidet ein Mailprogramm (ADR 0034). Der Messbericht
    aus `verify --email` ist immer dabei — dieselbe Zusage wie beim Brief.
    """
    from falzmarke import pruefung_eml
    from falzmarke.cli import setze_email

    if als not in ("pfad", "base64"):
        raise Eingabefehler(f"als ist „{als}“ — erlaubt sind „pfad“ und „base64“.")

    with tempfile.TemporaryDirectory(prefix="falzmarke-mcp-") as tmp:
        arbeit = Path(tmp)
        name, verzeichnis, verworfen = _profilverzeichnis(profil, arbeit)

        quelle = arbeit / "nachricht.md"
        text = nachricht if nachricht.lstrip().startswith("---") else f"---\n---\n\n{nachricht}"
        if name:
            text = _kopf_ergaenzen(text, name, None)
        quelle.write_text(text, encoding="utf-8")

        ausgabe = Path(ziel) if ziel else Path(
            tempfile.mkdtemp(prefix="falzmarke-")) / "nachricht"
        eml_pfad, dateien = setze_email(quelle, ausgabe, profil_verzeichnis=verzeichnis,
                                        mit_quelle=mit_quelle)
        bericht = pruefung_eml.pruefe(eml_pfad)

        ergebnis = {
            "bestanden": bericht.ok,
            "bericht": bericht.als_dict(),
            "zusammenfassung": bericht.als_text(),
            "versendet": False,
        }
        if verworfen:
            ergebnis["verworfen"] = {
                "felder": verworfen,
                "grund": "Verweise auf Bilddateien neben dem Profil — die gibt es "
                         "hier nicht. Wer ein Logo braucht, legt das Profil auf "
                         "dem Server ab und nennt es beim Namen.",
            }
        if als == "base64":
            ergebnis["eml_base64"] = base64.b64encode(eml_pfad.read_bytes()).decode("ascii")
            ergebnis["dateiname"] = eml_pfad.name
        else:
            ergebnis["pfad"] = str(eml_pfad.resolve())
            ergebnis["vorschau"] = str(
                next(d for d in dateien if d.suffix == ".html").resolve())
        return ergebnis


def brief_pruefen(pdf_pfad: str | None = None, pdf_base64: str | None = None,
                  form: str | None = None) -> dict:
    """Misst ein bestehendes PDF nach — auch eines, das falzmarke nie gesehen hat.

    Entweder pdf_pfad oder pdf_base64. Ohne form wird sie aus den Falzmarken
    abgeleitet: Form A faltet bei 87 und 192 mm, Form B bei 105 und 210.
    """
    from falzmarke import geometrie

    if bool(pdf_pfad) == bool(pdf_base64):
        raise Eingabefehler("Genau eines von pdf_pfad und pdf_base64 angeben.")

    with tempfile.TemporaryDirectory(prefix="falzmarke-pruef-") as tmp:
        if pdf_base64:
            pdf = Path(tmp) / "eingang.pdf"
            pdf.write_bytes(base64.b64decode(pdf_base64))
        else:
            pdf = Path(pdf_pfad)
            if not pdf.is_file():
                raise Eingabefehler(f"Datei nicht gefunden: {pdf}")

        gewaehlt = (form or "").upper() or geometrie.erkenne_form(pdf) or ""
        if not gewaehlt:
            raise Eingabefehler(
                "Die Form ließ sich nicht erkennen — es sind keine Falzmarken im "
                "Heftrand. Mit form=\"A\" oder form=\"B\" angeben."
            )
        bericht = geometrie.pruefe(pdf, gewaehlt)
        return {
            "form": gewaehlt,
            "bestanden": bericht.ok,
            "bericht": bericht.als_dict(),
            "zusammenfassung": bericht.als_text(),
        }


def profile_auflisten() -> dict:
    """Welche Absenderprofile dieser Server kennt.

    Nennt nur Namen, keine Inhalte: In einem Profil stehen Anschrift, Bankdaten
    und Steuernummer des Absenders. Wer sie sehen will, sieht sie in der Datei.
    """
    return {
        "profile": sorted(finde_profile().keys()),
        "hinweis": "Ein Profil kann auch als Objekt an brief_rendern übergeben "
                   "werden — dann braucht der Server keines.",
    }


# ── Server ──────────────────────────────────────────────────────────────────

WERKZEUGE = (brief_rendern, email_setzen, brief_pruefen, profile_auflisten)

def _durchgereicht(werkzeug, ToolError):
    """Macht aus einem erwarteten Fehler eine Meldung, die den Client erreicht.

    Ohne das bekommt der Aufrufer „Error executing tool brief_rendern“ und sonst
    nichts: Das SDK behandelt jede Ausnahme ausser ToolError als Absturz und
    maskiert sie, damit keine Interna nach draussen gehen. Das ist richtig — nur
    sind „Pflichtfelder fehlen: datum“ und „Profil example: Pflichtfeld
    ruecksendeangabe fehlt“ keine Interna, sondern genau die Auskunft, aus der
    ein Client seinen Aufruf berichtigen kann. Gemessen am 26.08.2026 gegen
    einen echten stdio-Client: ohne diese Uebersetzung kam der Text nicht an.

    Uebersetzt werden nur die beiden erwarteten Fehlerarten. Ein echter Absturz
    bleibt maskiert und im Serverlog — auch das mit Absicht.
    """
    import functools

    @functools.wraps(werkzeug)
    def gewickelt(*args, **kwargs):
        try:
            return werkzeug(*args, **kwargs)
        except (Eingabefehler, Umgebungsfehler) as fehler:
            raise ToolError(str(fehler)) from None

    return gewickelt


def baue_server():
    """Meldet die drei Werkzeuge an. Getrennt von main(), damit Tests sie sehen."""
    # _mcp_modul() zuerst: Es übersetzt ein fehlendes oder zu altes SDK in eine
    # Meldung mit Befehl. Stand der ToolError-Import davor, flog stattdessen ein
    # nackter ModuleNotFoundError — genau die Auskunft, die niemandem hilft.
    MCPServer = _mcp_modul()
    from mcp.server.mcpserver.exceptions import ToolError

    server = MCPServer(NAME)
    for werkzeug in WERKZEUGE:
        server.tool()(_durchgereicht(werkzeug, ToolError))
    return server



def main(argv: list[str] | None = None) -> int:
    """Startet den Server über stdio — so erwarten ihn MCP-Clients."""
    baue_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
