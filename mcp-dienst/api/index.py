"""Einstieg für Vercel: der Referenzdienst aus skill/falzmarke/referenzdienst.py.

Vercel sucht in api/ nach einer Variablen `app` und startet sie als ASGI-
Anwendung. Der Code liegt nicht hier, sondern im Paket — hier steht nur, wie
er gefunden wird. Vor dem Deploy: bash mcp-dienst/packen.sh (siehe README.md).
"""

import sys
from pathlib import Path

# Zuerst der gepackte Stand aus packen.sh (so liegt er auf Vercel), sonst der
# Quellbaum (lokal und in den Tests).
HIER = Path(__file__).resolve().parents[1]
for kandidat in (HIER / "_skill", HIER.parent / "skill"):
    if (kandidat / "falzmarke" / "referenzdienst.py").is_file():
        sys.path.insert(0, str(kandidat))
        break

from falzmarke.referenzdienst import asgi_app

app = asgi_app()
