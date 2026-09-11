# falzmarke als MCP-Dienst im Container.
#
# WOFÜR
#
# MCP-Verzeichnisse — Glama voran — nehmen einen Server erst auf, wenn ein
# Dockerfile im Wurzelverzeichnis liegt: Sie bauen das Repository selbst und
# sprechen den Server über stdio an. Ohne diese Datei fand kein Verzeichnis
# falzmarke, obwohl das Paket den Dienst seit v0.9.x mitbringt (#237).
#
#   docker build -t falzmarke-mcp .
#   docker run --rm -i falzmarke-mcp        # spricht MCP über stdin/stdout
#
# `-i` ist keine Bequemlichkeit: Der Server liest die Anfragen von stdin. Ohne
# offenen Eingabekanal endet er sofort, und das sieht aus wie ein Absturz.
#
# WARUM AUS DEM QUELLTEXT UND NICHT VON PyPI
#
# Ein `pip install falzmarke[mcp]` von PyPI baute ein Image aus der zuletzt
# veröffentlichten Fassung — also nicht aus dem Stand, der daneben im
# Repository liegt. Die CI prüfte dann die Vergangenheit, und ein Fehler im
# Dienst käme erst nach dem nächsten Release zum Vorschein. Glama baut das
# Repository ohnehin; hier steht dasselbe.
#
# WAS NICHT NÖTIG IST
#
# Keine Systemschriften: Das typst-Wheel bringt Libertinus Serif mit, und die
# Profile nennen keine andere Schrift, solange niemand eine setzt. Kein
# gemountetes Profilverzeichnis: Ein Client darf sein Absenderprofil als Objekt
# im Aufruf mitgeben (siehe `_profilverzeichnis` in skill/falzmarke/dienst.py)
# — genau dafür ist der Weg da, dass ein Client das Dateisystem des Servers
# nicht kennt.

FROM python:3.13-slim

# Die Extras des Pakets, als Bauargument.
#
# Das ist der Griff für die Gegenprobe in der CI: Ein Bau mit leerem EXTRAS
# lässt das MCP-SDK weg, und derselbe Handschlag MUSS dann scheitern. Ohne
# diesen zweiten Bau belegte ein grüner Lauf nur, dass er grün ist — nicht,
# dass die Prüfung überhaupt rot werden kann.
ARG EXTRAS="[mcp]"

# Nicht als root. Der Dienst braucht keine Rechte: Er liest von stdin, schreibt
# nach stdout und legt seine Zwischenstände unter /tmp ab.
RUN useradd --create-home --uid 10001 falzmarke

COPY . /src
RUN pip install --no-cache-dir "/src${EXTRAS}" \
    && rm -rf /src /root/.cache

USER falzmarke
WORKDIR /home/falzmarke

# Kein CMD mit Argumenten: `falzmarke mcp` ist der ganze Zweck dieses Images.
# Wer die CLI im Container will, hängt sie über `--entrypoint` davor.
ENTRYPOINT ["falzmarke", "mcp"]
