"""Die Rechnung als XML nach EN 16931 — dieselbe Quelle wie das PDF (#116).

Der Emitter setzt NICHT den Brieftext, sondern den geprüften Kopf: Eine Rechnung
trägt ihre Angaben im Frontmatter, nicht im Fließtext. Text- und HTML-Fassung
einer E-Mail gehen aus einem Baum hervor; hier gehen PDF und XML aus einem
geprüften Kopf hervor. Der Grund ist derselbe: Zwei Wege durch dieselben Daten
laufen auseinander, und niemand merkt es — der Mensch liest das PDF, die
Maschine die XML.

## Woher die Struktur stammt

Abgelesen an `EN16931_Einfach.pdf` aus dem Testmaterial von Mustang (Apache-2.0),
das derselbe Prüfer im selben Lauf als gültig bestätigt hat. **Nicht** aus dem
Normtext: Der ist kostenpflichtig, und es gilt dieselbe Regel wie für die
DIN 5008 — übertragen werden Fundstellen und Feldnamen, kein Wortlaut.

## Was hier nicht passiert

Gerechnet wird nichts (ADR 0039). Beträge, Bemessungsgrundlagen, Steuer- und
Gesamtbeträge werden übertragen. Fehlt eine Angabe, die das Profil EN 16931
verlangt, bricht die Erzeugung ab und nennt das Feld — ein leeres Element wäre
eine Datei, die durchläuft und beim Empfänger scheitert.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET

#: Die Namensräume am Wurzelelement, abgelesen an der Referenz.
RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"

#: Das Profil aus ADR 0039: EN 16931 (COMFORT), nicht MINIMUM und nicht EXTENDED.
#:
#: Die zweite Referenz (`validXRechnung.pdf`) trägt hier
#: `…#compliant#urn:xoev-de:kosit:standard:xrechnung_1.2` — das ist die
#: XRechnung-Ausprägung und gehört zu #117, nicht hierher.
GUIDELINE = "urn:cen.eu:en16931:2017"

#: Handelsrechnung. Der Code steht in der Referenz; Gutschriften (#115 sieht
#: `gutschrift:` vor) tragen einen anderen und sind hier noch nicht gebaut.
TYPCODE_RECHNUNG = "380"

#: Einheiten, die in den Referenzdateien tatsächlich vorkommen — mehr werden
#: nicht erfunden. Wer eine andere braucht, bekommt eine Meldung mit der Liste
#: statt einer Datei, die beim Empfänger scheitert.
EINHEITEN = {
    "stück": "H87", "stueck": "H87", "stk": "H87", "st": "H87",
    "stunde": "HUR", "stunden": "HUR", "h": "HUR",
    "liter": "LTR", "l": "LTR",
}

#: Wenn keine Einheit angegeben ist. C62 („eins") steht so in der Referenz.
EINHEIT_OHNE = "C62"

#: Umsatzsteuer, Regelsatz. Beides in beiden Referenzen belegt.
STEUER_TYP = "VAT"
STEUER_KATEGORIE = "S"

#: Vorgabewährung. Der Datenvertrag kennt (noch) keine andere.
WAEHRUNG = "EUR"

#: Nachkommastellen, die ein Betrag in der Quelle tragen darf. Mehr wird gemeldet,
#: nicht gerundet: `1240.005` würde sonst still zu `1240.01` — ein Wert, der so nie
#: in der Quelle stand (ADR 0039). Die Referenz setzt Summen zweistellig.
BETRAG_STELLEN = 2

#: Dasselbe für Mengen und Einzelpreise, die die Referenz vierstellig setzt.
MENGE_STELLEN = 4


class RechnungUnvollstaendig(ValueError):
    """Eine Angabe fehlt, die das Profil EN 16931 verlangt.

    Eigene Klasse und kein `Eingabefehler`: Der liegt in `cli`, und ein Emitter,
    der die CLI importiert, dreht die Abhängigkeit um. Der Aufrufer übersetzt.
    """


def _text(eltern, name: str, wert, **attribute) -> ET.Element:
    knoten = ET.SubElement(eltern, name, {k: str(v) for k, v in attribute.items()})
    knoten.text = str(wert)
    return knoten


def _zahl(wert, feld: str, stellen: int) -> Decimal:
    """Der Wert aus der Quelle als Zahl — oder eine Meldung, die das Feld nennt.

    Zwei Dinge fallen hier auf, statt still weiterzulaufen (#116):

    - **Text statt Zahl.** Vorher erreichte `abc` ein nacktes `float()` und brach mit
      einem Traceback ab; die CLI fängt nur `Eingabefehler`.
    - **Mehr Nachkommastellen als dargestellt.** Vorher rundete `:.2f` still. Das
      wäre ein Wert, den das Werkzeug gebildet hat — und falzmarke rechnet nicht.

    `Decimal(str(...))` und nicht `Decimal(float)`: Aus YAML kommt `1240.005` als
    Fließkommazahl, und nur ihre Zeichenfolge trägt die Stellen, die dastanden.
    """
    if isinstance(wert, bool):
        raise RechnungUnvollstaendig(f"`{feld}: {wert}` ist keine Zahl.")
    try:
        zahl = Decimal(str(wert).strip())
    except (InvalidOperation, ValueError):
        raise RechnungUnvollstaendig(f"`{feld}: {wert}` ist keine Zahl.") from None
    exponent = zahl.as_tuple().exponent
    if not isinstance(exponent, int):
        raise RechnungUnvollstaendig(f"`{feld}: {wert}` ist keine Zahl.")
    if -exponent > stellen:
        raise RechnungUnvollstaendig(
            f"`{feld}: {wert}` hat mehr als {stellen} Nachkommastellen. Gerundet wird "
            "nicht — falzmarke setzt, was in der Quelle steht (ADR 0039).")
    return zahl


def _betrag(wert, feld: str = "Betrag") -> str:
    """Zwei Nachkommastellen, wie die Summen in der Referenz — ohne zu runden."""
    return f"{_zahl(wert, feld, BETRAG_STELLEN):.2f}"


def _menge(wert, feld: str = "Menge") -> str:
    """Vier Nachkommastellen — so stehen Mengen und Einzelpreise in der Referenz."""
    return f"{_zahl(wert, feld, MENGE_STELLEN):.4f}"


def datum_kompakt(wert) -> str:
    """`20241115` — das Format 102 aus der Referenz.

    Nimmt ein `date`, ein `datetime` oder eine ISO-Zeichenkette. Alles andere
    wird gemeldet: Ein Datum, das als Text durchgereicht wird, erzeugt eine
    Datei, die der Empfänger nicht liest.
    """
    if isinstance(wert, dt.datetime):
        wert = wert.date()
    if isinstance(wert, dt.date):
        return wert.strftime("%Y%m%d")
    try:
        return dt.date.fromisoformat(str(wert).strip()).strftime("%Y%m%d")
    except ValueError:
        raise RechnungUnvollstaendig(
            f"„{wert}“ ist kein Datum. Erwartet wird `2026-10-03`.") from None


def einheit_code(wert) -> str:
    """Die Einheit als Code der UN/ECE-Liste, oder eine Meldung."""
    if wert in (None, ""):
        return EINHEIT_OHNE
    code = EINHEITEN.get(str(wert).strip().lower().rstrip("."))
    if code is None:
        raise RechnungUnvollstaendig(
            f"`einheit: {wert}` kennt falzmarke nicht. Bekannt sind "
            + ", ".join(sorted({f"`{k}`" for k in EINHEITEN}))
            + " — oder die Angabe weglassen.")
    return code


def _partei(eltern, name: str, bezeichnung: str, anschrift: dict,
            steuernummern: list[tuple[str, str]] | None = None) -> None:
    partei = ET.SubElement(eltern, f"{{{RAM}}}{name}")
    _text(partei, f"{{{RAM}}}Name", bezeichnung)
    adresse = ET.SubElement(partei, f"{{{RAM}}}PostalTradeAddress")
    _text(adresse, f"{{{RAM}}}PostcodeCode", anschrift["plz"])
    _text(adresse, f"{{{RAM}}}LineOne", anschrift["strasse"])
    _text(adresse, f"{{{RAM}}}CityName", anschrift["ort"])
    _text(adresse, f"{{{RAM}}}CountryID", anschrift["land"])
    for schema, nummer in steuernummern or []:
        eintrag = ET.SubElement(partei, f"{{{RAM}}}SpecifiedTaxRegistration")
        _text(eintrag, f"{{{RAM}}}ID", nummer, schemeID=schema)


def _verkaeufer_anschrift(profil: dict) -> dict:
    absender = profil.get("absender") or {}
    rechnung = profil.get("rechnung") or {}
    fehlend = [f for f in ("name", "strasse", "plz", "ort") if not absender.get(f)]
    if not rechnung.get("land"):
        fehlend.append("rechnung.land")
    if fehlend:
        raise RechnungUnvollstaendig(
            "Das Profil trägt nicht alles, was EN 16931 vom Aussteller verlangt: "
            + ", ".join(f"`{f}`" for f in fehlend))
    return {"plz": absender["plz"], "strasse": absender["strasse"],
            "ort": absender["ort"], "land": rechnung["land"]}


def _steuernummern(profil: dict) -> list[tuple[str, str]]:
    """`VA` ist die USt-IdNr., `FC` die Steuernummer — beide Schemata stehen so
    in der Referenz, und beide Felder gibt es im Profil (#116, Schritt 1a)."""
    rechnung = profil.get("rechnung") or {}
    heraus = []
    if rechnung.get("ust_idnr"):
        heraus.append(("VA", rechnung["ust_idnr"]))
    if rechnung.get("steuernummer"):
        heraus.append(("FC", rechnung["steuernummer"]))
    if not heraus:
        raise RechnungUnvollstaendig(
            "Das Profil trägt weder `rechnung.ust_idnr:` noch `rechnung.steuernummer:` — "
            "§ 14 Absatz 4 Nummer 2 UStG verlangt eine von beiden.")
    return heraus


def _empfaenger(kopf: dict) -> tuple[str, dict]:
    """Der Käufer aus `empfaenger:`.

    Die Anschriftzone ist eine Liste freier Zeilen — für den Brief genügt das,
    für die XML nicht. Statt aus ihr zu raten (Ist Zeile 2 die Straße oder eine
    zweite Namenszeile?), verlangt der Emitter `empfaenger_anschrift:`. Raten
    hieße hier, den Empfänger falsch zu adressieren, ohne dass es auffällt.
    """
    anschrift = kopf.get("empfaenger_anschrift")
    if not isinstance(anschrift, dict):
        raise RechnungUnvollstaendig(
            "`empfaenger_anschrift:` fehlt. Die XML braucht Straße, PLZ, Ort und Land "
            "des Empfängers einzeln — aus den freien Zeilen von `empfaenger:` lassen "
            "sie sich nicht sicher ablesen.")
    fehlend = [f for f in ("name", "strasse", "plz", "ort", "land")
               if not anschrift.get(f)]
    if fehlend:
        raise RechnungUnvollstaendig(
            "`empfaenger_anschrift:` fehlt " + ", ".join(f"`{f}:`" for f in fehlend))
    return anschrift["name"], anschrift


def erzeuge(kopf: dict, profil: dict) -> str:
    """Die Rechnung als XML nach EN 16931. Gibt den fertigen Text zurück."""
    for praefix, raum in (("rsm", RSM), ("ram", RAM), ("udt", UDT), ("qdt", QDT)):
        ET.register_namespace(praefix, raum)

    wurzel = ET.Element(f"{{{RSM}}}CrossIndustryInvoice")

    zusammenhang = ET.SubElement(wurzel, f"{{{RSM}}}ExchangedDocumentContext")
    parameter = ET.SubElement(
        zusammenhang, f"{{{RAM}}}GuidelineSpecifiedDocumentContextParameter")
    _text(parameter, f"{{{RAM}}}ID", GUIDELINE)

    dokument = ET.SubElement(wurzel, f"{{{RSM}}}ExchangedDocument")
    if not kopf.get("rechnungsnummer"):
        raise RechnungUnvollstaendig("`rechnungsnummer:` fehlt.")
    _text(dokument, f"{{{RAM}}}ID", kopf["rechnungsnummer"])
    _text(dokument, f"{{{RAM}}}TypeCode", TYPCODE_RECHNUNG)
    ausgestellt = ET.SubElement(dokument, f"{{{RAM}}}IssueDateTime")
    _text(ausgestellt, f"{{{UDT}}}DateTimeString",
          datum_kompakt(kopf.get("datum")), format="102")

    vorgang = ET.SubElement(wurzel, f"{{{RSM}}}SupplyChainTradeTransaction")

    positionen = kopf.get("positionen") or []
    if not positionen:
        raise RechnungUnvollstaendig("`positionen:` fehlt — ohne sie ist es keine Rechnung.")
    for nummer, position in enumerate(positionen, start=1):
        _position(vorgang, nummer, position)

    _kopfdaten(vorgang, kopf, profil)

    ET.indent(wurzel, space="  ")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            + ET.tostring(wurzel, encoding="unicode") + "\n")


def _position(vorgang, nummer: int, position: dict) -> None:
    zeile = ET.SubElement(vorgang, f"{{{RAM}}}IncludedSupplyChainTradeLineItem")
    verweis = ET.SubElement(zeile, f"{{{RAM}}}AssociatedDocumentLineDocument")
    _text(verweis, f"{{{RAM}}}LineID", nummer)

    ware = ET.SubElement(zeile, f"{{{RAM}}}SpecifiedTradeProduct")
    _text(ware, f"{{{RAM}}}Name", position.get("bezeichnung", ""))

    if position.get("einzelpreis") is not None:
        vereinbarung = ET.SubElement(zeile, f"{{{RAM}}}SpecifiedLineTradeAgreement")
        preis = ET.SubElement(vereinbarung, f"{{{RAM}}}NetPriceProductTradePrice")
        _text(preis, f"{{{RAM}}}ChargeAmount", _menge(position["einzelpreis"], f"positionen[{nummer}].einzelpreis"))

    lieferung = ET.SubElement(zeile, f"{{{RAM}}}SpecifiedLineTradeDelivery")
    _text(lieferung, f"{{{RAM}}}BilledQuantity", _menge(position.get("menge", 0), f"positionen[{nummer}].menge"),
          unitCode=einheit_code(position.get("einheit")))

    abrechnung = ET.SubElement(zeile, f"{{{RAM}}}SpecifiedLineTradeSettlement")
    steuer = ET.SubElement(abrechnung, f"{{{RAM}}}ApplicableTradeTax")
    _text(steuer, f"{{{RAM}}}TypeCode", STEUER_TYP)
    _text(steuer, f"{{{RAM}}}CategoryCode", STEUER_KATEGORIE)
    _text(steuer, f"{{{RAM}}}RateApplicablePercent", _betrag(position.get("steuersatz", 0), f"positionen[{nummer}].steuersatz"))
    summe = ET.SubElement(
        abrechnung, f"{{{RAM}}}SpecifiedTradeSettlementLineMonetarySummation")
    _text(summe, f"{{{RAM}}}LineTotalAmount", _betrag(position.get("betrag", 0), f"positionen[{nummer}].betrag"))


def _kopfdaten(vorgang, kopf: dict, profil: dict) -> None:
    vereinbarung = ET.SubElement(vorgang, f"{{{RAM}}}ApplicableHeaderTradeAgreement")
    _partei(vereinbarung, "SellerTradeParty", (profil.get("absender") or {})["name"],
            _verkaeufer_anschrift(profil), _steuernummern(profil))
    name, anschrift = _empfaenger(kopf)
    _partei(vereinbarung, "BuyerTradeParty", name, anschrift)

    lieferung = ET.SubElement(vorgang, f"{{{RAM}}}ApplicableHeaderTradeDelivery")
    if kopf.get("leistungsdatum"):
        ereignis = ET.SubElement(lieferung, f"{{{RAM}}}ActualDeliverySupplyChainEvent")
        zeitpunkt = ET.SubElement(ereignis, f"{{{RAM}}}OccurrenceDateTime")
        _text(zeitpunkt, f"{{{UDT}}}DateTimeString",
              datum_kompakt(kopf["leistungsdatum"]), format="102")

    abrechnung = ET.SubElement(vorgang, f"{{{RAM}}}ApplicableHeaderTradeSettlement")
    _text(abrechnung, f"{{{RAM}}}InvoiceCurrencyCode", WAEHRUNG)

    summen = kopf.get("summen")
    if not isinstance(summen, dict):
        raise RechnungUnvollstaendig(
            "`summen:` fehlt. Das Profil EN 16931 verlangt Netto, Steuer und Brutto — "
            "falzmarke bildet sie nicht (ADR 0039).")

    if not (summen.get("steuer") or []):
        # Nicht „null Euro Steuer" setzen: Die Kategorie ist fest `S` (Regelsatz).
        # Eine steuerfreie Rechnung, etwa nach § 19 UStG, bräuchte eine andere —
        # mit `S` entstünde eine Datei, die falsch ausgezeichnet ist und trotzdem
        # durchläuft. Das ist ein eigener Vorgang.
        raise RechnungUnvollstaendig(
            "`summen.steuer` ist leer. Eine Rechnung ohne Umsatzsteuer (etwa nach "
            "§ 19 UStG) erzeugt falzmarke noch nicht: Die Steuerkategorie wäre "
            "falsch ausgezeichnet.")

    for nummer_steuer, eintrag in enumerate(summen.get("steuer") or [], start=1):
        if eintrag.get("basis") is None:
            raise RechnungUnvollstaendig(
                f"`summen.steuer` (Satz {eintrag.get('satz')}): `basis:` fehlt. "
                "EN 16931 verlangt je Steuersatz die Bemessungsgrundlage, und "
                "falzmarke summiert sie nicht aus den Positionen (ADR 0039).")
        steuer = ET.SubElement(abrechnung, f"{{{RAM}}}ApplicableTradeTax")
        _text(steuer, f"{{{RAM}}}CalculatedAmount",
              _betrag(eintrag.get("betrag", 0), f"summen.steuer[{nummer_steuer}].betrag"))
        _text(steuer, f"{{{RAM}}}TypeCode", STEUER_TYP)
        _text(steuer, f"{{{RAM}}}BasisAmount",
              _betrag(eintrag["basis"], f"summen.steuer[{nummer_steuer}].basis"))
        _text(steuer, f"{{{RAM}}}CategoryCode", STEUER_KATEGORIE)
        _text(steuer, f"{{{RAM}}}RateApplicablePercent",
              _betrag(eintrag.get("satz", 0), f"summen.steuer[{nummer_steuer}].satz"))

    if kopf.get("zahlungsziel"):
        bedingungen = ET.SubElement(abrechnung, f"{{{RAM}}}SpecifiedTradePaymentTerms")
        _text(bedingungen, f"{{{RAM}}}Description",
              f"Zahlbar bis {datum_kompakt(kopf['zahlungsziel'])}")

    fehlend = [f for f in ("netto", "brutto") if summen.get(f) is None]
    if fehlend:
        raise RechnungUnvollstaendig(
            "`summen:` fehlt " + ", ".join(f"`{f}:`" for f in fehlend))
    gesamt = ET.SubElement(
        abrechnung, f"{{{RAM}}}SpecifiedTradeSettlementHeaderMonetarySummation")
    _text(gesamt, f"{{{RAM}}}LineTotalAmount", _betrag(summen["netto"], "summen.netto"))
    _text(gesamt, f"{{{RAM}}}TaxBasisTotalAmount", _betrag(summen["netto"], "summen.netto"))
    wert, feld = _steuer_gesamt(summen)
    _text(gesamt, f"{{{RAM}}}TaxTotalAmount", _betrag(wert, feld), currencyID=WAEHRUNG)
    _text(gesamt, f"{{{RAM}}}GrandTotalAmount", _betrag(summen["brutto"], "summen.brutto"))
    _text(gesamt, f"{{{RAM}}}DuePayableAmount", _betrag(summen["brutto"], "summen.brutto"))


def _steuer_gesamt(summen: dict) -> tuple:
    """Der Steuergesamtbetrag — übertragen, nie gebildet (ADR 0039, #116).

    Bis zum Review vom 13.09.2026 stand hier `sum()` über die Einzelbeträge: die
    einzige Rechenoperation im ganzen Emitter, zwanzig Zeilen unter einem
    Docstring, der „Gerechnet wird nichts" sagt. Bemerkt hat es keine Prüfung —
    die Beispielrechnung hat nur einen Steuersatz, und die Summe eines einzelnen
    Werts ist dieser Wert.

    - `steuer_gesamt:` steht da → genau dieser Wert, auch wenn er von der Summe
      abweicht. Die Summenprobe in `lint` warnt dann; ersetzt wird nichts.
    - genau ein Steuersatz → dessen Betrag. Das ist eine Übernahme.
    - mehrere Sätze ohne `steuer_gesamt:` → Meldung. Die Summe hieße Rundungsregel,
      und die verantwortet der Absender.
    """
    if summen.get("steuer_gesamt") is not None:
        return summen["steuer_gesamt"], "summen.steuer_gesamt"
    steuern = summen.get("steuer") or []
    if len(steuern) == 1:
        return steuern[0].get("betrag", 0), "summen.steuer[1].betrag"
    raise RechnungUnvollstaendig(
        f"`summen.steuer` nennt {len(steuern)} Steuersätze, aber kein `steuer_gesamt:`. "
        "Den Gesamtbetrag bildet falzmarke nicht aus den Einzelbeträgen (ADR 0039) — "
        "er steht in der Quelle oder die XML entsteht nicht.")
