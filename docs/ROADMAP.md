<!-- Erzeugt von scripts/roadmap.py, wöchentlich über
     .github/workflows/roadmap.yml. Änderungen von Hand gehen beim
     nächsten Lauf verloren. -->

# Roadmap

Die Reihenfolge der Phasen folgt [ADR 0030](entscheidungen/0030-reihenfolge-der-roadmap.md). Diese Seite wird aus den
Meilensteinen und offenen Issues erzeugt und nicht von Hand gepflegt: die Wahrheit
steht im Issue, hier steht nur eine Sicht darauf.

**19 offene Vorgänge** in 7 Phasen.

## 1. Vor Verbreitung

Belegarbeit, die vor einer starken Behauptung stehen muss. Sperrt seit ADR 0032 nicht mehr die Verbreitung selbst — nur die Wörter normgerecht, DIN-konform, normkonform und zertifiziert.

**4 offen · 6 erledigt**

| Nr. | Was | Typ | Priorität | Bereich | Zustand |
|---|---|---|---|---|---|
| [#12](https://github.com/blitzsicht/falzmarke/issues/12) | Normabgleich gegen den Originaltext der DIN 5008:2020-03 | Forschung | P0 | norm | maintainer |
| [#16](https://github.com/blitzsicht/falzmarke/issues/16) | Quellenlage: vendorte Implementierung zählt als unabhängiger Beleg | Forschung | P0 | norm | maintainer |
| [#18](https://github.com/blitzsicht/falzmarke/issues/18) | Form A steht nur auf der eigenen Layoutbasis — externer Beleg fehlt | Forschung | P1 | norm | — |
| [#31](https://github.com/blitzsicht/falzmarke/issues/31) | Quellen stehen bei Regeln, zu denen sie schweigen — die Validierung merkt es nicht | Fehler | P1 | norm | maintainer |

## 2. Lange Schreiben

Überschriften, Listen, Zitate, Code — lange und professionelle Schreiben

**1 offen · 1 erledigt**

| Nr. | Was | Typ | Priorität | Bereich | Zustand |
|---|---|---|---|---|---|
| [#26](https://github.com/blitzsicht/falzmarke/issues/26) | Dialekt 1.1: Struktur für lange Schreiben (Überschriften, Listen, Zitate, Code) | Epic | P1 | skill, dialekt | — |

## 3. E-Mail

Geschäftsmails nach DIN 5008 Abschnitt 22 aus derselben Quelle wie der Brief — als Datei, nicht als Versand (ADR 0029).

**8 offen · 0 erledigt**

| Nr. | Was | Typ | Priorität | Bereich | Zustand |
|---|---|---|---|---|---|
| [#60](https://github.com/blitzsicht/falzmarke/issues/60) | Entscheidung: E-Mail ist Ausgabe, nicht Kanal (ADR 0034) | — | P1 | recht, email | maintainer |
| [#59](https://github.com/blitzsicht/falzmarke/issues/59) | E-Mail-Fassung nach DIN 5008 Abschnitt 22 aus derselben Quelle | — | P2 | skill, email | — |
| [#61](https://github.com/blitzsicht/falzmarke/issues/61) | Markdown-Baum vom Typst-Emitter entkoppeln, HTML- und Text-Emitter (E3, E4) | — | P2 | skill, email | — |
| [#62](https://github.com/blitzsicht/falzmarke/issues/62) | Profil-Abschnitt email: und Frontmatter typ: email (E1, E2) | — | P2 | profile, email | — |
| [#63](https://github.com/blitzsicht/falzmarke/issues/63) | Aufbau der .eml und der Begleitdateien (E5) | — | P2 | email | — |
| [#64](https://github.com/blitzsicht/falzmarke/issues/64) | Lint E7xx und verify --email (E6, E7) | — | P2 | norm, verify, email | — |
| [#65](https://github.com/blitzsicht/falzmarke/issues/65) | Befehl email, Skill und MCP-Dienst (E8) | — | P2 | skill, mcp, email | — |
| [#66](https://github.com/blitzsicht/falzmarke/issues/66) | Beispiele, Tests und Doku der E-Mail-Fassung (E9) | — | P2 | doku, email | — |

## 4. Einfacher Zugang

Dienst, MCP, Browser, Website

**0 offen · 2 erledigt**

Nichts offen.

## 5. Dokumentpakete

Anlagen, Hybridbrief, Serienbrief, Ablage

**2 offen · 2 erledigt**

| Nr. | Was | Typ | Priorität | Bereich | Zustand |
|---|---|---|---|---|---|
| [#3](https://github.com/blitzsicht/falzmarke/issues/3) | Serienbrief aus CSV oder JSON | Feature | P2 | skill | — |
| [#9](https://github.com/blitzsicht/falzmarke/issues/9) | Ablage in Paperless-NGX | Feature | P3 | hybridbrief | — |

## 6. Beweis

proof — Zustandsmodell, Signatur, Siegel

**2 offen · 0 erledigt**

| Nr. | Was | Typ | Priorität | Bereich | Zustand |
|---|---|---|---|---|---|
| [#14](https://github.com/blitzsicht/falzmarke/issues/14) | Digitale Signatur des PDF (PAdES) — Entscheidung und Grenzen | Entscheidung | P2 | recht | maintainer |
| [#19](https://github.com/blitzsicht/falzmarke/issues/19) | Beweiskette: Schichten proof und delivery (Rahmen für v0.7/v0.8) | Epic | P2 | recht | maintainer |

## 7. Geparkt

Wartet auf eine Vorbedingung — nicht verworfen

**2 offen · 1 erledigt**

| Nr. | Was | Typ | Priorität | Bereich | Zustand |
|---|---|---|---|---|---|
| [#2](https://github.com/blitzsicht/falzmarke/issues/2) | Umschlagdruck DL und C6/5 | Feature | P3 | norm | geparkt |
| [#10](https://github.com/blitzsicht/falzmarke/issues/10) | Schweiz (SN 010130) und Österreich (ÖNORM A 1080) | Feature | P3 | norm | geparkt |
