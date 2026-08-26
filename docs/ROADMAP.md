<!-- Erzeugt von scripts/roadmap.py, wöchentlich über
     .github/workflows/roadmap.yml. Änderungen von Hand gehen beim
     nächsten Lauf verloren. -->

# Roadmap

Die Reihenfolge der Phasen folgt [ADR 0030](entscheidungen/0030-reihenfolge-der-roadmap.md). Diese Seite wird aus den
Meilensteinen und offenen Issues erzeugt und nicht von Hand gepflegt: die Wahrheit
steht im Issue, hier steht nur eine Sicht darauf.

**19 offene Vorgänge** in 6 Phasen.

## 1. Vor Verbreitung

Muss abgeschlossen sein, bevor das Werkzeug öffentlich beworben wird: Typst Universe, Skills-Listen, LinkedIn, Website-Launch.

**8 offen · 1 erledigt**

| Nr. | Was | Priorität | Bereich | Zustand |
|---|---|---|---|---|
| [#12](https://github.com/blitzsicht/falzmarke/issues/12) | Normabgleich gegen den Originaltext der DIN 5008:2020-03 | P0 | norm | blockiert, maintainer |
| [#16](https://github.com/blitzsicht/falzmarke/issues/16) | Quellenlage: vendorte Implementierung zählt als unabhängiger Beleg | P0 | norm | maintainer |
| [#34](https://github.com/blitzsicht/falzmarke/issues/34) | PDF-Konformität mit einem unabhängigen Werkzeug prüfen | P0 | verify, ci | — |
| [#35](https://github.com/blitzsicht/falzmarke/issues/35) | Briefkörper bleibt auf jeder Seite im Satzspiegel | P0 | verify, dialekt | — |
| [#7](https://github.com/blitzsicht/falzmarke/issues/7) | Als Paket auf PyPI veröffentlichen | P1 | ci | — |
| [#13](https://github.com/blitzsicht/falzmarke/issues/13) | Schaufenster: die Falzmarke ist auf keinem Bild zu erkennen | P1 | doku, marke | — |
| [#18](https://github.com/blitzsicht/falzmarke/issues/18) | Form A steht nur auf der eigenen Layoutbasis — externer Beleg fehlt | P1 | norm | — |
| [#31](https://github.com/blitzsicht/falzmarke/issues/31) | Quellen stehen bei Regeln, zu denen sie schweigen — die Validierung merkt es nicht | P1 | norm | maintainer |

## 2. Lange Schreiben

Überschriften, Listen, Zitate, Code — lange und professionelle Schreiben

**2 offen · 0 erledigt**

| Nr. | Was | Priorität | Bereich | Zustand |
|---|---|---|---|---|
| [#26](https://github.com/blitzsicht/falzmarke/issues/26) | Dialekt 1.1: Struktur für lange Schreiben (Überschriften, Listen, Zitate, Code) | P1 | feature, skill, dialekt | — |
| [#11](https://github.com/blitzsicht/falzmarke/issues/11) | Englische Leitwörter und Datumsformate | P3 | i18n | — |

## 3. Einfacher Zugang

Dienst, MCP, Browser, Website

**2 offen · 0 erledigt**

| Nr. | Was | Priorität | Bereich | Zustand |
|---|---|---|---|---|
| [#5](https://github.com/blitzsicht/falzmarke/issues/5) | MCP-Server, damit andere KI-Clients Briefe setzen können | P1 | mcp | — |
| [#6](https://github.com/blitzsicht/falzmarke/issues/6) | GitHub Action: Briefe im Repo rendern | P2 | ci | — |

## 4. Dokumentpakete

Anlagen, Hybridbrief, Serienbrief, Ablage

**3 offen · 0 erledigt**

| Nr. | Was | Priorität | Bereich | Zustand |
|---|---|---|---|---|
| [#1](https://github.com/blitzsicht/falzmarke/issues/1) | Anlagen-PDFs an den Brief anhängen | P2 | hybridbrief | — |
| [#3](https://github.com/blitzsicht/falzmarke/issues/3) | Serienbrief aus CSV oder JSON | P2 | skill | — |
| [#9](https://github.com/blitzsicht/falzmarke/issues/9) | Ablage in Paperless-NGX | P3 | hybridbrief | — |

## 5. Beweis

proof — Zustandsmodell, Signatur, Siegel

**2 offen · 0 erledigt**

| Nr. | Was | Priorität | Bereich | Zustand |
|---|---|---|---|---|
| [#14](https://github.com/blitzsicht/falzmarke/issues/14) | Digitale Signatur des PDF (PAdES) — Entscheidung und Grenzen | P2 | feature, recht | maintainer |
| [#19](https://github.com/blitzsicht/falzmarke/issues/19) | Beweiskette: Schichten proof und delivery (Rahmen für v0.7/v0.8) | P2 | feature, recht | maintainer |

## 6. Geparkt

Wartet auf eine Vorbedingung — nicht verworfen

**2 offen · 1 erledigt**

| Nr. | Was | Priorität | Bereich | Zustand |
|---|---|---|---|---|
| [#2](https://github.com/blitzsicht/falzmarke/issues/2) | Umschlagdruck DL und C6/5 | P3 | norm | geparkt |
| [#10](https://github.com/blitzsicht/falzmarke/issues/10) | Schweiz (SN 010130) und Österreich (ÖNORM A 1080) | P3 | norm | geparkt |
