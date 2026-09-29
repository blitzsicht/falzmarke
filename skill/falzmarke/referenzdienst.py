"""Öffentlicher MCP-Dienst mit Referenzdaten — ohne Briefe, ohne Nutzerdaten.

Warum es ihn gibt: Das Plugin-Portal von OpenAI bot der Organisation am
29.09.2026 nur „With MCP“ an, nicht „Skills only“. Ein Plugin über diesen Weg
braucht einen öffentlichen MCP-Server über HTTPS. Gesetzt wird trotzdem nicht
hier, sondern im Skill in der Sandbox des Nutzers; dieser Dienst liefert nur,
was ohnehin öffentlich im Repository steht:

    sollwerte(form)        Maße von Form A oder B, aus geometrie.FORM
    regeln_auflisten(...)  die Regeln mit Herkunft und höchster Wirkung
    regel_erklaeren(id)    eine Regel mit ihren Quellen und Belegen

Was hier bewusst fehlt: jedes Werkzeug, das Text des Nutzers annimmt. Die
Prüfungen aus `lint` wären nützlich, verarbeiten aber Adressen und Namen — und
dann stimmte der Satz „keine personenbezogenen Daten auf unserem Server“ nicht
mehr. `tests/test_referenzdienst.py` hält das am Quelltext fest.

Der Dienst ist zustandslos (`stateless_http`) und antwortet mit reinem JSON
statt Server-Sent Events. Beides, damit er als Serverless-Funktion laufen kann.
"""

from __future__ import annotations

import os

from falzmarke import geometrie, regeln

NAME = "falzmarke-referenz"

#: Der Satz, der jede Antwort begleitet. Wortgleich mit dem Kanon aus
#: tests/test_textkanon.py — ein Werkzeug, das Maße ausgibt, gibt auch aus, wie
#: belastbar sie sind.
QUELLENLAGE = (
    "Die Sollwerte stammen aus Sekundärquellen; der Abgleich mit dem Originaltext "
    "der DIN 5008:2020-03 einschließlich Berichtigung 1:2020-07 steht aus, und "
    "Regeln aus einzelnen Quellen wirken nur als Warnung."
)

#: Maße, die für beide Formen gelten (mm).
GEMEINSAM = {
    "seite_breite": geometrie.SEITE_BREITE,
    "seite_hoehe": geometrie.SEITE_HOEHE,
    "lochmarke": geometrie.LOCHMARKE,
    "rand_links": geometrie.RAND_LINKS,
    "rand_rechts": geometrie.RAND_RECHTS,
    "infoblock_x": geometrie.INFOBLOCK_X,
    "anschrift_x_rechts": geometrie.ANSCHRIFT_X_RECHTS,
    "zeilenabstand": geometrie.ZEILE,
}

#: Die Umgebungsvariable mit dem Nachweis-Token von OpenAI. Der Token steht nie
#: im Repository; ohne ihn antwortet der Pfad mit 404.
CHALLENGE_VARIABLE = "OPENAI_APPS_CHALLENGE"
CHALLENGE_PFAD = "/.well-known/openai-apps-challenge"


class Unbekannt(ValueError):
    """Eine Angabe des Aufrufers, zu der es nichts gibt."""


# ── Werkzeuge ───────────────────────────────────────────────────────────────

def sollwerte(form: str = "B") -> dict:
    """Die Maße eines Geschäftsbriefs nach Form A oder B, in Millimetern.

    form   "A" (Briefkopf 27 mm) oder "B" (Briefkopf 45 mm). Vorgabe ist B.

    Bereiche stehen als [von, bis], gemessen von der oberen Blattkante.
    """
    schluessel = (form or "").strip().upper()
    if schluessel not in geometrie.FORM:
        raise Unbekannt(f"Form „{form}“ gibt es nicht — erlaubt sind "
                        f"{', '.join(sorted(geometrie.FORM))}.")
    masse = {k: list(v) if isinstance(v, tuple) else v
             for k, v in geometrie.FORM[schluessel].items()}
    return {"form": schluessel, "einheit": "mm", "masse": masse,
            "gemeinsam": dict(GEMEINSAM), "quellenlage": QUELLENLAGE}


def _kurz(regel: dict) -> dict:
    return {
        "id": regel["id"],
        "titel": regel.get("titel", ""),
        "herkunft": regel.get("herkunft"),
        "hoechstens": regeln.deckel(regel),
        "belege": len(regeln.unabhaengige_belege(regel)),
    }


def regeln_auflisten(bereich: str | None = None) -> dict:
    """Die Regeln, gegen die falzmarke prüft, mit Herkunft und Belegstärke.

    bereich   Optional ein Präfix der Kennung, z. B. "geometrie.form_b" oder
              "text". Ohne Angabe kommen alle.

    „hoechstens“ ist die schärfste Wirkung, die eine Regel haben darf: Eine nur
    einzeln belegte Regel warnt, statt einen Fehler zu melden.
    """
    alle = regeln.alle()
    auswahl = [r for r in alle if not bereich or r["id"].startswith(bereich)]
    if bereich and not auswahl:
        bereiche = sorted({r["id"].split(".")[0] for r in alle})
        raise Unbekannt(f"Keine Regel beginnt mit „{bereich}“. Bereiche: "
                        f"{', '.join(bereiche)}.")
    return {"anzahl": len(auswahl), "regeln": [_kurz(r) for r in auswahl],
            "quellenlage": QUELLENLAGE}


def regel_erklaeren(id: str) -> dict:
    """Eine Regel im Detail: was sie verlangt, woher sie stammt, wie belegt.

    id   Die Kennung aus regeln_auflisten, z. B. "geometrie.form_b.briefkopf".
    """
    treffer = [r for r in regeln.alle() if r["id"] == id]
    if not treffer:
        raise Unbekannt(f"Regel „{id}“ gibt es nicht — regeln_auflisten nennt alle.")
    regel = treffer[0]
    verzeichnis = regeln.quellen()
    quellen = []
    for name in regeln._quellennamen(regel):
        quelle = verzeichnis.get(name, {})
        quellen.append({
            "name": name,
            "titel": quelle.get("titel", ""),
            "url": quelle.get("url", ""),
            "art": quelle.get("art", ""),
            "beleg": (regel.get("belegt_durch") or {}).get(name, ""),
        })
    return {**_kurz(regel), "bemerkung": regel.get("bemerkung", ""),
            "quellen": quellen, "quellenlage": QUELLENLAGE}


WERKZEUGE = (sollwerte, regeln_auflisten, regel_erklaeren)

#: Die Angaben, die OpenAI je Werkzeug verlangt, samt Begründung für das
#: Formular. Für alle drei gleich — sie lesen nur, was im Repository steht.
ANNOTATIONEN = {
    "read_only_hint": True,
    "destructive_hint": False,
    "idempotent_hint": True,
    "open_world_hint": False,
}
BEGRUENDUNG = {
    "readOnlyHint": "Liest nur Sollwerte und Regeln, die mit dem Dienst ausgeliefert "
                    "werden; schreibt nichts und speichert nichts.",
    "openWorldHint": "Greift auf keinen externen Dienst zu; alle Daten liegen im Paket.",
    "destructiveHint": "Ändert und löscht nichts.",
}


# ── Server ──────────────────────────────────────────────────────────────────

def baue_server():
    from falzmarke.dienst import _mcp_modul

    MCPServer = _mcp_modul()
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations

    server = MCPServer(
        NAME,
        instructions=("Referenzdaten zu DIN-5008-Geschäftsbriefen: Maße von Form A "
                      "und B, die geprüften Regeln und ihre Quellen. Gesetzt wird "
                      "nicht hier, sondern mit dem Skill falzmarke. " + QUELLENLAGE),
        website_url="https://falzmarke.com",
    )
    for werkzeug in WERKZEUGE:
        server.tool(annotations=ToolAnnotations(**ANNOTATIONEN))(
            _durchgereicht(werkzeug, ToolError))
    return server


def _durchgereicht(werkzeug, ToolError):
    """Eine unbekannte Form oder Regel ist eine Auskunft für den Aufrufer,
    kein Absturz — sie geht als ToolError hinaus (wie in dienst.py)."""
    import functools

    @functools.wraps(werkzeug)
    def gewickelt(*args, **kwargs):
        try:
            return werkzeug(*args, **kwargs)
        except Unbekannt as fehler:
            raise ToolError(str(fehler)) from None

    return gewickelt


def asgi_app(hosts: list[str] | None = None):
    """Die HTTP-Anwendung: MCP unter /mcp, dazu der Nachweispfad für OpenAI.

    hosts   Hostnamen, unter denen der Dienst erreichbar sein darf. Ohne Angabe
            aus FALZMARKE_MCP_HOSTS (kommagetrennt). Das SDK weist sonst jeden
            Host außer localhost ab — Schutz gegen DNS-Rebinding.
    """
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    if hosts is None:
        hosts = [h.strip() for h in os.environ.get("FALZMARKE_MCP_HOSTS", "").split(",")
                 if h.strip()]
    erlaubt = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", *hosts]
    app = baue_server().streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True, allowed_hosts=erlaubt),
    )

    async def nachweis(_request):
        token = os.environ.get(CHALLENGE_VARIABLE, "").strip()
        if not token:
            return PlainTextResponse("", status_code=404)
        return PlainTextResponse(token)

    app.router.routes.append(Route(CHALLENGE_PFAD, nachweis, methods=["GET"]))
    return app
