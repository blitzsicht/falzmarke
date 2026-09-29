"""Einstieg für Vercel: der Referenzdienst aus skill/falzmarke/referenzdienst.py.

Vercel sucht in api/ nach einer Variablen `app` und startet sie als ASGI-
Anwendung. Der Code liegt nicht hier, sondern im Paket — hier steht nur, wie
er gefunden wird. Ungemessen bis zum ersten Deploy (Teil B, siehe README.md).
"""

import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skill"
if SKILL.is_dir():
    sys.path.insert(0, str(SKILL))

from falzmarke.referenzdienst import asgi_app

app = asgi_app()
