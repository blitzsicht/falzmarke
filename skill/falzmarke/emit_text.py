#!/usr/bin/env python3
"""Erzeugt den Klartextteil einer E-Mail aus dem geprüften Markdown-Baum.

Derselbe Baum wie in `emit.py` und `emit_html.py`. Fett und kursiv verschwinden
hier ersatzlos: `*Wort*` im Klartext ist keine Auszeichnung, sondern ein
Sternchen, das jemand mitliest.

**Warum `format=flowed` (RFC 3676) und nicht einfach lange Zeilen.** Ein Brief
kennt seine Breite, eine Mail nicht. Wer hart auf 72 Zeichen umbricht, erzeugt
auf einem Telefon den bekannten Treppenschnitt; wer gar nicht umbricht, erzeugt
in Clients ohne Umbruch eine Zeile mit Querbalken. Flowed löst beides: Der
Sender faltet, der Empfänger darf entfalten und neu umbrechen.

**Was gefaltet wird und was nicht.** Nur Fließtext-Absätze. Listenpunkte und
Tabellenzeilen bleiben feste Zeilen, weil ihre Einrückung und ihre Ausrichtung
Teil der Bedeutung sind — beim Entfalten würde die Einrückung mitten im Satz
landen. Eine feste Zeile ist in flowed genau das: eine Zeile, die nicht mit
einem Leerzeichen endet.

**`delsp`.** Bei `delsp=yes` löscht der Empfänger das Leerzeichen am Zeilenende
beim Entfalten; der Wortzwischenraum muss deshalb davor stehen, die Faltmarke
kommt zusätzlich. Bei `delsp=no` *ist* der Zwischenraum die Marke. Beide Wege
sind hier gebaut und beide werden gegen ihre Umkehrung geprüft — `delsp=yes`
ist die Vorgabe, weil #61 sie nennt.

Die Signatur-Trennzeile `-- ` steht nicht hier: Die Signatur kommt aus dem
Profil, nicht aus dem Brieftext, und wird in #63 angehängt.
"""

from __future__ import annotations

from falzmarke import baum as baum_modul
from falzmarke import typografie

#: Empfehlung aus RFC 3676: unter 79, mit Luft für Zitatzeichen.
BREITE = 72

#: Einrückung je Listenebene.
EINZUG = "  "


def as_text(text: str, typografie_anwenden: bool = True) -> str:
    if typografie_anwenden:
        text = typografie.anwenden(text)
    return text


def stark(inhalt: str) -> str:
    """Fett ohne Markup — im Klartext gibt es keinen Fettdruck."""
    return inhalt


def betont(inhalt: str) -> str:
    return inhalt


def umbruch() -> str:
    return "\n"


def absatz(inhalt: str) -> str:
    return inhalt


def liste(punkte: list[str], nummeriert: bool = False, start: int = 1,
          tiefe: int = 0) -> str:
    """Je Punkt eine feste Zeile, Unterlisten schon eingerückt in den Punkten.

    Fortsetzungszeilen — ein harter Umbruch im Punkt — werden um die Breite der
    Marke eingerückt, damit sie unter dem Text stehen und nicht unter ihr. Ohne
    das steht die zweite Zeile bündig links und ist von einem neuen, eigenen
    Absatz nicht zu unterscheiden.

    Die Marke ist bei Nummern breiter als bei Strichen (`10. ` gegen `- `),
    deshalb wird ihre Länge gemessen statt geraten.
    """
    einzug = EINZUG * tiefe
    zeilen = []
    for nummer, punkt in enumerate(punkte):
        marke = f"{start + nummer}. " if nummeriert else "- "
        kopf, *rest = punkt.split("\n")
        zeilen.append(f"{einzug}{marke}{kopf}")
        fortsetzung = " " * (len(einzug) + len(marke))
        # Eine Unterliste bringt ihre eigene Einrückung schon mit; nur nackte
        # Fortsetzungen aus einem harten Umbruch brauchen sie hier.
        zeilen.extend(z if z.startswith(" ") else fortsetzung + z for z in rest)
    return "\n".join(zeilen)


AUSRICHTUNG = {"left": "left", "right": "right", "center": "center", None: "left", "": "left"}


def tabelle(zeilen: list[list[str]], ausrichtungen: list[str | None]) -> str:
    """Ausgerichteter Text, Spaltenbreite nach Inhalt, `|` als Trenner.

    Unter der Kopfzeile steht eine Strichzeile — im Klartext gibt es keinen
    Fettdruck, an dem man den Kopf sonst erkennen würde.
    """
    if not zeilen:
        return ""
    spalten = max(len(z) for z in zeilen)
    breiten = [
        max((len(z[s]) for z in zeilen if s < len(z)), default=0)
        for s in range(spalten)
    ]

    def _zeile(werte: list[str]) -> str:
        zellen = []
        for s in range(spalten):
            inhalt = werte[s] if s < len(werte) else ""
            richtung = AUSRICHTUNG.get(
                ausrichtungen[s] if s < len(ausrichtungen) else None, "left"
            )
            if richtung == "right":
                zellen.append(inhalt.rjust(breiten[s]))
            elif richtung == "center":
                zellen.append(inhalt.center(breiten[s]))
            else:
                zellen.append(inhalt.ljust(breiten[s]))
        # rstrip ist keine Kosmetik: Eine Zeile, die mit einem Leerzeichen
        # endet, ist in format=flowed eine weiche Faltmarke. Ohne das würde
        # eine Tabelle mit linksbündiger letzter Spalte beim Empfänger in den
        # nächsten Absatz laufen.
        return " | ".join(zellen).rstrip()

    ausgabe = [_zeile(zeilen[0]), "-|-".join("-" * b for b in breiten)]
    ausgabe.extend(_zeile(z) for z in zeilen[1:])
    return "\n".join(ausgabe)


# ── Der Weg über den Baum ───────────────────────────────────────────────────


def _inline(knoten) -> str:
    if isinstance(knoten, tuple):
        return "".join(_inline(k) for k in knoten)
    if isinstance(knoten, baum_modul.Text):
        return as_text(knoten.inhalt, typografie_anwenden=knoten.typografie)
    if isinstance(knoten, baum_modul.Umbruch):
        return umbruch()
    if isinstance(knoten, baum_modul.Stark):
        return stark(_inline(knoten.kinder))
    if isinstance(knoten, baum_modul.Betont):
        return betont(_inline(knoten.kinder))
    return _block(knoten)


def _block(knoten, tiefe: int = 0) -> str:
    if isinstance(knoten, baum_modul.Absatz):
        return absatz(_inline(knoten.kinder))
    if isinstance(knoten, baum_modul.Liste):
        punkte = []
        for p in knoten.punkte:
            teile = []
            for k in p:
                if isinstance(k, baum_modul.Liste):
                    teile.append("\n" + _block(k, tiefe + 1))
                else:
                    teile.append(_inline(k))
            punkte.append("".join(teile))
        return liste(punkte, nummeriert=knoten.nummeriert, start=knoten.start, tiefe=tiefe)
    if isinstance(knoten, baum_modul.Tabelle):
        return tabelle(
            [[_inline(z) for z in zeile] for zeile in knoten.zeilen],
            list(knoten.ausrichtungen),
        )
    # Kein stilles Uebergehen — derselbe Grund wie im Typst-Emitter.
    raise TypeError(
        f"Der Text-Emitter kennt {type(knoten).__name__} nicht. "
        "Neuer Knoten in baum.py? Dann gehört er auch hierher."
    )


def teile(bloecke) -> list[tuple[str, bool]]:
    """Geprüfter Baum -> je Block sein Text und ob er fest bleiben muss.

    „Fest" heißt: nicht weich umbrechbar. Listen und Tabellen tragen ihre
    Bedeutung in der Form — eine gefaltete Einrückung landet beim Entfalten
    mitten im Satz, und eine gefaltete Tabellenspalte zerbricht.

    Diese Auskunft entsteht hier, wo der Knotentyp bekannt ist, und wird an
    `falte()` weitergereicht. Sie aus dem fertigen Text zurückzuraten wäre
    möglich und war es auch — die Heuristik hielt „2. Mahnung: …" am
    Satzanfang für einen Aufzählungspunkt und ein „A | B" im Fließtext für
    eine Tabelle, und ließ beide Absätze ungefaltet stehen.
    """
    ergebnis = []
    for b in bloecke:
        text = _block(b)
        if text.strip():
            ergebnis.append((text, isinstance(b, (baum_modul.Liste, baum_modul.Tabelle))))
    return ergebnis


def setze(bloecke) -> str:
    """Geprüfter Baum -> Klartext, ungefaltet.

    Für den Textteil einer Mail ist `falte()` der richtige Einstieg; diese
    Funktion liefert denselben Text ohne Faltung — und ist das, wogegen der
    Rundlauf von `falte()`/`entfalte()` geprüft wird.
    """
    return "\n\n".join(text for text, _ in teile(bloecke)) + "\n"


def _falte_zeile(zeile: str, breite: int, delsp: bool) -> list[str]:
    """Eine Zeile in weich verbundene Stücke.

    Geschnitten wird im Original, nicht aus Wörtern wieder zusammengesetzt:
    Ein `split(" ")`/`join(" ")` verliert einen doppelten Zwischenraum, wenn
    der Umbruch genau darauf fällt — stille Textänderung in einem Werkzeug,
    dessen Zusage Genauigkeit ist.
    """
    stuecke: list[str] = []
    rest = zeile
    while len(rest) > breite:
        schnitt = rest.rfind(" ", 0, breite + 1)
        if schnitt <= 0:
            # Kein Faltpunkt innerhalb der Breite — ein überlanges Wort. Dann
            # lieber hinter der Breite falten als das Wort zerschneiden.
            schnitt = rest.find(" ", breite)
            if schnitt <= 0:
                break
        stuecke.append(rest[:schnitt + 1])
        rest = rest[schnitt + 1:]
    stuecke.append(rest)
    # Alle bis auf die letzte bekommen die Faltmarke. Bei delsp löscht der
    # Empfänger sie, deshalb steht der Wortzwischenraum schon davor.
    return [s + (" " if delsp else "") for s in stuecke[:-1]] + [stuecke[-1]]


def falte(bloecke, breite: int = BREITE, delsp: bool = True) -> str:
    """Geprüfter Baum -> `format=flowed`.

    Nimmt den Baum und nicht den fertigen Text, weil nur hier bekannt ist,
    welche Zeile fest bleiben muss (siehe `teile()`).

    Erst falten, dann Space-Stuffing — die Reihenfolge steht in RFC 3676 §4.4
    und ist nicht beliebig: Wer zuerst stufft, faltet das gestuffte Leerzeichen
    mit und verschiebt es in die Zeilenmitte.
    """
    ausgabe: list[str] = []
    bloecke_gesetzt = teile(bloecke)
    for nummer, (text, fest) in enumerate(bloecke_gesetzt):
        if nummer:
            ausgabe.append("")            # Leerzeile zwischen den Blöcken
        for zeile in text.split("\n"):
            stuecke = [zeile] if (fest or len(zeile) <= breite) \
                else _falte_zeile(zeile, breite, delsp)
            for s in stuecke:
                # Space-Stuffing: was mit Leerzeichen, '>' oder 'From ' beginnt,
                # sähe sonst wie ein Zitat oder eine mbox-Trennzeile aus.
                if s.startswith((" ", ">")) or s.startswith("From "):
                    s = " " + s
                ausgabe.append(s)
    return "\n".join(ausgabe) + "\n"


def entfalte(text: str, delsp: bool = True) -> str:
    """`format=flowed` -> Klartext. Die Umkehrung von `falte()`.

    Sie steht hier, weil eine Faltung ohne ihre Umkehrung nicht prüfbar wäre:
    Erst der Rundlauf zeigt, ob die Faltmarken tragen.
    """
    ausgabe: list[str] = []
    offen = False
    for zeile in text.split("\n"):
        if zeile.startswith(" "):        # Space-Stuffing zurücknehmen
            zeile = zeile[1:]
        weich = zeile.endswith(" ")
        if weich:
            zeile = zeile[:-1] if delsp else zeile
        if offen:
            ausgabe[-1] += zeile
        else:
            ausgabe.append(zeile)
        offen = weich
    return "\n".join(ausgabe)
