# 0041 — Rechnungen von Kleinunternehmern (§ 19 UStG)

**Datum:** 14.09.2026 · **Status:** angenommen ·
**Umgesetzt in:** [#316](https://github.com/blitzsicht/falzmarke/issues/316), [#317](https://github.com/blitzsicht/falzmarke/issues/317) ·
**Ergänzt:** ADR 0039, ADR 0040

## Worum es geht

falzmarke lehnt heute jede Rechnung ohne Umsatzsteuer ab (`emit_xml.py`, „`summen.steuer` ist
leer"), weil die Steuerkategorie fest auf `S` steht und eine steuerfreie Rechnung damit falsch
ausgezeichnet wäre. `skill/references/frontmatter.md` beschreibt diese Lücke. Diese Entscheidung
legt fest, wie falzmarke die Rechnung eines Kleinunternehmers erzeugt.

Beschreibend, nicht bewertend: Ob jemand Kleinunternehmer ist, entscheiden Ansässigkeit und Umsatz,
nicht das Werkzeug. falzmarke überträgt eine Angabe des Absenders und prüft sie nicht (ADR 0039).

## Was die Quellen sagen

**BELEGT** heißt: Primärquelle gelesen. **GEMESSEN** heißt: an einer Datei gegen ein fremdes
Werkzeug gefahren, mit Gegenprobe.

| Aussage | Quelle | Stärke |
|---|---|---|
| Umsätze eines im Inland ansässigen Kleinunternehmers sind steuerfrei (Gesamtumsatz Vorjahr höchstens 25 000 €, laufendes Jahr höchstens 100 000 €) | § 19 Abs. 1 UStG | BELEGT |
| Mindestangaben: Name und Anschrift beider Seiten, Steuernummer oder USt-IdNr. oder Kleinunternehmer-IdNr., Ausstellungsdatum, Menge und Art, Entgelt in einer Summe **mit Hinweis, dass die Steuerbefreiung für Kleinunternehmer gilt**, bei Gutschrift die Angabe „Gutschrift" | § 34a Satz 1 UStDV | BELEGT |
| §§ 33 und 34 bleiben unberührt; die Rechnung darf immer als sonstige Rechnung gehen | § 34a Satz 2 und 4 UStDV | BELEGT |
| Der Hinweis darf umgangssprachlich sein, wenn er eindeutig ist, etwa „steuerfreier Kleinunternehmer" | BMF-Schreiben 18.03.2025, Abschn. 14.7a Abs. 1 UStAE | BELEGT |
| Eine E-Rechnung eines Kleinunternehmers setzt die Zustimmung des Empfängers voraus (formfrei) | BMF-Schreiben 18.03.2025, Abschn. 14.7a Abs. 3 UStAE | BELEGT |
| Kategorie **E**, Satz 0, Steuerbetrag 0; der Hinweis in BT-120 **und** BT-33; BT-121 leer | XRechnung-Spezifikation 3.0.2 (20.06.2024), Kap. 13.3; FeRD-Beispiel `E13_01_Kleinunternehmer_ohneUStId.xml` aus dem Paket ZUGFeRD 2.5.2 (Dateikopf: „Version 2.5.0") | BELEGT, zwei Stellen |
| Kein VATEX-Code für die deutsche Regelung; das französische Gegenstück `VATEX-FR-FRANCHISE` ist landesgebunden | CEF-Genericode `VATEX-2026-05-15` | BELEGT |
| Mit `E` gilt: BT-120 oder BT-121 Pflicht (BR-E-10), Satz 0 (BR-E-05), Steuer 0 (BR-E-09), Verkäufer braucht BT-31, BT-32 oder BT-63 (BR-E-02) | EN-16931-Schematron, Release 1.3.16 | BELEGT |
| `O` statt `E` verböte die USt-IdNr. des Verkäufers (BR-O-02); § 34a Nr. 2 lässt sie zu | EN-16931-Schematron, § 34a UStDV | BELEGT |

**Gemessen am 14.09.2026** mit Mustang 2.26.0 (ZF_250, XR_30) und dem KoSIT-Validator 1.6.3
(Konfiguration XRechnung 3.0.2, Stand 31.08.2026). Grundlage waren die Goldens `rechnung.xml` und
`xrechnung.xml`, umgebaut auf Kategorie E:

| Datei | Mustang | KoSIT (nur XRechnung) |
|---|---|---|
| E, Satz 0, Steuer 0, Hinweis in BT-120 | gültig | angenommen |
| dieselbe **ohne** Hinweis | ungültig an BR-E-10 | abgelehnt an BR-E-10 |
| dieselbe mit Satz 19 | ungültig an BR-E-05, BR-CO-17 | abgelehnt an BR-E-05 |
| nur Steuernummer, keine USt-IdNr. | ungültig an **BR-CO-26** | abgelehnt an BR-CO-26 |
| nur Steuernummer, zusätzlich als BT-29 | gültig | angenommen |
| nur Steuernummer als BT-29, Hinweis zusätzlich in BT-33 | gültig | angenommen |
| FeRD-Beispiel E13, als Kontrollprobe | gültig | — |

Nicht untersucht: das PDF und ob ein Empfängerprogramm die Datei annimmt.

## Ein Fund, der nicht an § 19 hängt

**BR-CO-26 trifft schon heute jede Rechnung aus einem Profil ohne `ust_idnr:`.** Gegenprobe mit
Kategorie S: `rechnung.xml` mit Steuernummer statt USt-IdNr. ist bei Mustang ungültig an BR-CO-26.
`lint` akzeptiert ein Profil mit nur `steuernummer:` (Regel `rechnung.steuernummer`), und
`emit_xml._partei` schreibt keine BT-29. Das ist ein eigener Vorgang. Er muss vor § 19 erledigt
sein, weil gerade Kleinunternehmer oft keine USt-IdNr. haben.

## Entscheidung 1: Kategorie E, kein VATEX, Hinweis in BT-120 und BT-33

Für eine Rechnung eines Kleinunternehmers schreibt falzmarke je Position und in der Aufschlüsselung
`CategoryCode` `E` und `RateApplicablePercent` `0.00`, dazu einmal `CalculatedAmount` `0.00` und
den Hinweis als `ExemptionReason` (BT-120). Derselbe Hinweis steht als
`SellerTradeParty/Description` (BT-33), wie in beiden Quellen. `TaxTotalAmount` ist `0.00`,
Brutto gleich Netto.

Kein `ExemptionReasonCode`: Die Liste kennt keinen passenden Code, und ein fachfremder wie
`VATEX-EU-I` (so in einem Mustang-Test) wäre eine falsche Angabe, die trotzdem durchläuft.

**Nicht O**, weil O die USt-IdNr. des Verkäufers verbietet, § 34a Nr. 2 sie aber zulässt, und
weil beide herausgebenden Stellen E verwenden.

## Entscheidung 2: Status und Hinweis stehen im Profil

```yaml
# im Profil
rechnung:
  steuernummer: 201/113/40209
  kleinunternehmer: true
  kleinunternehmer_hinweis: "…"   # Pflicht, wenn kleinunternehmer: true — keine Vorgabe
```

**Im Profil, nicht im Schreiben**, wie Steuernummer, USt-IdNr. und Bank: Der Status ist eine
Eigenschaft des Absenders für ein Kalenderjahr, nicht eines Empfängers. `serie` variiert nur
Empfänger, nicht den Absender. Ein Gültigkeitsdatum bekommt das Feld nicht. Wer die Grenze
überschreitet, stellt sein Profil um; das kann falzmarke ohne Umsatz nicht erkennen.

**Der Hinweis hat keine Vorgabe.** falzmarke druckt keinen selbst formulierten Rechtstext in
fremde Rechnungen. Der Mustertext der KoSIT stammt aus der Zeit vor 2025 („kein Ausweis") und
passt nicht mehr zum Wortlaut „steuerfrei". Das gilt wie bei `email.pflichtangaben:`
(`docs/recht.md`): Das Feld ist Pflicht, sein Inhalt wird nicht bewertet. Die Doku nennt das
Beispiel aus dem BMF-Schreiben mit Fundstelle, das Beispielprofil trägt einen Text mit Kommentar.

Im Schreiben entfallen `steuersatz:` je Position und `summen.steuer`; `summen:` trägt `netto:` und
`brutto:`. Weil der Status für das ganze Profil gilt, kann eine Mischung aus steuerpflichtigen und
steuerfreien Positionen nicht entstehen, ohne dass die erste Regel unten anschlägt.

**Neue Fehlerregeln**, alle `herkunft: werkzeug`, `ebene: werkzeug`:

| Regel | Fehler, wenn |
|---|---|
| `rechnung.kleinunternehmer_steuer` | `kleinunternehmer: true` und ein `steuersatz:` (auch 0), eine Zeile in `summen.steuer` oder `steuer_gesamt` |
| `rechnung.kleinunternehmer_hinweis` | `kleinunternehmer: true` und `kleinunternehmer_hinweis:` fehlt oder ist leer (BR-E-10) |
| `rechnung.kleinunternehmer_summe` | `kleinunternehmer: true` und `brutto:` ungleich `netto:` |

Dazu kommen zwei Regeln für den Rand: `rechnung.kleinunternehmer` meldet einen Status, der nicht
`true` oder `false` ist, denn YAML liest `ja` als Text. Und `rechnung.steuer` meldet eine leere
`summen.steuer` ohne Status. Diese Meldung verweist auf das Profilfeld.

`rechnung.kleinunternehmer_summe` weicht bewusst vom Muster „eine Summenabweichung ist eine
Warnung" ab (`rechnung.summen`, ADR 0039). Hier ist kein Rundungsfall denkbar: Bei Steuer 0 wäre
jede Abweichung ein Verstoß gegen BR-CO-15 in der XML. Die Ausnahme steht als Kommentar in
`regeln/rechnung.yaml`.

**Doppelt durchgesetzt**, wie `rechnung.betrag_stellen` und `rechnung.xrechnung`: Der MCP-Dienst
ruft `rendere()` ohne `lint` auf (`dienst.py`). Alle drei Regeln prüft deshalb auch `emit_xml` und
bricht mit `RechnungUnvollstaendig` ab.

## Entscheidung 3: Der Hinweis steht im PDF und in der XML, mit demselben Wortlaut

Das PDF zeigt unter der Positionstabelle nur den Gesamtbetrag, keine Zeile „Summe netto" mit
demselben Wert und keine Steuerzeile, und darunter den Hinweis. Die XML trägt ihn als BT-120 und
BT-33. Eine Treue-Prüfung wie bei den Beträgen (`tests/test_rechnung_treue.py`) hält PDF und XML
gegeneinander.

falzmarke bewertet nicht, ob der Text die Anforderung aus § 34a Nr. 5 erfüllt.

## Entscheidung 4: Was ausdrücklich nicht dazugehört

- **Keine Prüfung der Umsatzgrenzen** und keine Erinnerung daran. falzmarke kennt keinen Umsatz.
  Eine Warnung bei jedem Lauf wäre Rauschen, das niemand mehr liest. Die Grenzen nennt die Doku.
- **Keine Gutschrift.** falzmarke baut Gutschriften noch nicht (`emit_xml.py`, Typcode). Wenn sie
  kommen, gilt für Kleinunternehmer § 34a Nr. 6; das steht dann in jenem Vorgang.
- **Keine Kleinunternehmer-Identifikationsnummer** und kein § 19 Abs. 4 (Ansässigkeit im übrigen
  Gemeinschaftsgebiet).
- **Die Kleinbetragsrechnung bleibt, wie sie ist** (§ 34a Satz 2). Eine Kleinunternehmer-Rechnung
  unter 250 € läuft durch dieselben Regeln; ein Beispiel dafür ist nicht nötig.
- **Kein Zwang zur XML, aber auch kein Schalter dagegen.** § 34a Satz 4 erlaubt das PDF allein.
  falzmarke erzeugt die XML trotzdem, wie bei jeder Rechnung. Eine E-Rechnung setzt beim
  Kleinunternehmer die Zustimmung des Empfängers voraus (Abschn. 14.7a Abs. 3 UStAE). Die Doku
  sagt das, das Werkzeug prüft es nicht.

## Umsetzung, in dieser Reihenfolge

1. **Vorgang A — BR-CO-26 (#316).** Hat das Profil keine `ust_idnr:`, schreibt `emit_xml` die
   Steuernummer zusätzlich als `SellerTradeParty/ID` (BT-29). Mit USt-IdNr. bleibt alles, wie es
   ist, und die bestehenden Goldens ändern sich nicht.
   - Das ist ein Behelf, wie ihn FeRD E13 vormacht. Die XRechnung-Spezifikation beschreibt BT-29
     eigentlich als Kennung, die der Käufer vergibt. BT-30 (Registerkennung) ließe BR-CO-26
     ebenso zu, hat aber nicht jeder Absender.
   - Tests: ein Profil nur mit Steuernummer, dazu CI-Mustang und KoSIT je mit so einer Datei. Die
     Gegenprobe ohne BT-29 muss an BR-CO-26 scheitern.
   - Changelog-Fragment `behoben`.
2. **Vorgang B — § 19 (#317).**
   - Profilfelder und Datenvertrag: `frontmatter.md`. `docs/profiles.md` beschreibt den
     Abschnitt `rechnung:` nicht und bleibt deshalb unberührt.
   - Die drei Lint-Regeln in `regeln/rechnung.yaml` und dieselben Prüfungen in `emit_xml`.
   - Emitter mit Kategorie E, BT-120 und BT-33.
   - PDF: Summentabelle ohne Nettozeile, Hinweis darunter.
   - Treue-Prüfung PDF gegen XML für den Hinweis.
   - Beispiel `examples/rechnung-kleinunternehmer.md` mit Profil, dazu Goldens nach dem Muster aus
     #119.
   - CI: Mustang für ZUGFeRD und XRechnung, KoSIT für XRechnung, je eine Kleinunternehmer-Rechnung
     mit Gegenproben an BR-E-10 und BR-E-05.
   - Sabotage-Gegenproben je Regel in `tests/test_gegenbeweis.py`.
   - Doku: `docs/rechnung.md`, `docs/recht.md` (Grenzen, Hinweis, Zustimmung), die Stelle in
     `frontmatter.md`, die heute die Lücke beschreibt.
   - `docs/cli.md` nur, falls sich eine Meldung ändert.
   - Changelog-Fragment `neu`.

Beide Vorgänge erzeugen Goldens. Deshalb eignet sich keiner für cw-nachtschicht, solange
cw-nachtschicht#97 offen ist.

## Review

Drei Blickwinkel am 14.09.2026: Fakten gegen Quellen und Code, Zuschnitt und Datenvertrag,
Außenwirkung und Risiko. Eingearbeitet:

- BT-33 als zweite Stelle für den Hinweis
- die Zustimmung des Empfängers
- BT-29 als Behelf benannt, BT-30 als Alternative
- Versionsangaben so, wie sie in den Dateien stehen
- Gutschrift ausgeschlossen, § 33 abgegrenzt
- die doppelte Durchsetzung für den MCP-Dienst
- Herkunft der Regeln und die Ausnahme bei der Summenregel
- die Mischungsfrage als Folge von Entscheidung 2
- Summentabelle ohne doppelte Zeile

Der Vorgabetext entfällt. Er war zwischen den Blickwinkeln strittig: eigener Wortlaut gegen
Rechtsrisiko. Das Pflichtfeld nimmt beiden den Grund.
