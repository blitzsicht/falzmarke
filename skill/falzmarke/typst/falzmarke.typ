// falzmarke — DIN-5008-Wrapper um letter-pro v3.0.0
//
// Diese Datei setzt das Layout. Alle Werte stammen aus DIN 5008:2020;
// die Fundstellen stehen in skill/references/din5008.md.
//
// Aufgerufen wird sie aus einer von falzmarke.py erzeugten main.typ:
//
//   #import "falzmarke.typ": brief
//   #show: brief.with(profil: (..), daten: (..))
//   <Body als Typst-Markup>

#import "vendor/letter-pro-v3.0.0.typ": letter-generic, address-tribox, recipient-box

// Grundzeile: 12 pt = 4,2333 mm. DIN rechnet mit 4,23 mm.
#let zeile = 4.2333mm

// Der Zeilenkasten ist 11 pt hoch, die Zeile 12 pt. Typst rechnet den Durchschuss
// nicht in die Blockhoehe ein — ein Blockabstand von n Zeilen ergaebe deshalb nur
// n Zeilen minus 1 pt. `leer(n)` gleicht das aus: der Abstand zwischen zwei
// Zeilenoberkanten wird damit exakt (n + 1) Rasterzeilen.
#let durchschuss = 12pt - 11pt
#let leer(n) = n * zeile + durchschuss

// Blockzitat und wortgetreuer Auszug (Dialekt 1.1).
//
// Auf Modulebene, nicht in `brief`: Der Brieftext wird ausserhalb der Funktion
// ausgewertet, ein `let` darin waere fuer ihn unsichtbar. `main.typ` importiert
// beide zusammen mit `brief` (siehe cli.py).
//
// Beide halten das 12-pt-Raster: Abstaende in `leer(n)`, Schriftgroesse
// unveraendert. Beim Auszug ist das der Grund, warum er trotz
// Festbreitenschrift in 11 pt steht — `top-edge` und `bottom-edge` sind in em
// der Schriftgroesse gesetzt, also bleibt die Zeilenhoehe gleich, solange die
// Groesse es tut.
//
// Kein Kasten, sondern ein Balken links: Ein Kasten braucht Innenabstaende,
// und die sind in einem Zeilenraster nicht frei waehlbar. Der Balken kostet
// keine Zeile.
// `quote` statt eines blossen `block`: Ein Block ist im PDF ein Kasten ohne
// Bedeutung — ein Screenreader liest einen eingerueckten Absatz vor und sagt
// nicht, dass hier jemand zitiert wird. `#quote(block: true)` traegt die
// Auszeichnung `/BlockQuote` in den Strukturbaum; nachgemessen mit pypdf, und
// die Pruefung dazu steht in tests/test_struktur.py (Issue #138).
//
// Die Gestaltung bleibt dieselbe: Die show-Regel ersetzt das Aussehen, nicht
// das Element — der Tag ueberlebt das, ebenfalls nachgemessen.
#let zitat(inhalt) = quote(block: true, inhalt)

#let codeblock(inhalt) = block(
  above: leer(1), below: leer(1),
  inset: (left: 6mm),
  stroke: (left: 1.6pt + luma(160)),
  inhalt,
)

// Kopfhöhe je Form; identisch mit letter-pro
#let kopfhoehe = (A: 27mm, B: 45mm)

// Der Informationsblock zählt normativ mit mindestens dieser Höhe,
// auch wenn er weniger Zeilen hat. Daraus folgt die Betreffposition
// 80,46 mm (Form A) bzw. 98,46 mm (Form B).
#let infoblock-mindesthoehe = 40mm

// ── Bausteine ───────────────────────────────────────────────────────────────

// Rücksendeangabe: eine Zeile, 7–8 pt, unterstrichen, in der 5-mm-Zone.
#let ruecksende-box(text-inhalt) = rect(width: 85mm, height: 5mm, stroke: none, inset: 0pt, {
  set text(size: 7pt)
  set align(horizon)
  pad(left: 5mm, underline(offset: 2pt, text-inhalt))
})

// Zusatz- und Vermerkzone: bis zu 3 Zeilen à 8 pt, unten in der 12,7-mm-Zone.
#let vermerke-box(zeilen) = {
  set text(size: 8pt)
  set align(bottom)
  pad(left: 5mm, bottom: 1mm, {
    set par(leading: zeile - 8pt * 1.0)
    zeilen.map(z => [#z]).join(linebreak())
  })
}

// Informationsblock: Leitwort links (8 pt), Angabe rechts (10 pt).
// Zweispaltig, damit jeder Eintrag genau eine Zeile des 12-pt-Rasters belegt —
// untereinander gesetzt käme ein Block mit sieben Einträgen auf über 60 mm und
// schöbe den Betreff weit unter die Normposition.
#let infoblock(eintraege) = {
  set text(size: 10pt)
  grid(
    columns: (30mm, 1fr),
    rows: eintraege.map(_ => zeile),
    column-gutter: 2mm,
    ..eintraege.map(paar => {
      let (leitwort, wert) = paar
      (
        align(left + horizon, text(size: 8pt, leitwort)),
        align(left + horizon, text(size: 10pt, wert)),
      )
    }).flatten()
  )
}

// Briefkopf aus den deklarativen Profilfeldern.
// Ein Profil mit eigenem .typ-Hook liefert stattdessen fertigen Content.
#let briefkopf(profil) = {
  let k = profil.at("briefkopf", default: (:))
  let farbe = if "farbe" in profil { rgb(profil.farbe) } else { black }
  set text(size: 9pt)
  pad(left: 25mm, right: 20mm, top: 8mm, {
    grid(
      columns: (1fr, auto),
      align: (left + horizon, right + horizon),
      {
        if k.at("logo", default: none) != none {
          // Alternativtext: ohne ihn lehnt PDF/UA-1 jedes Bild ab. Der Name des
          // Absenders ist die richtige Beschreibung — das Logo ersetzt ihn hier.
          image(
            k.logo,
            height: k.at("logo_hoehe_mm", default: 42) * 1mm,
            alt: k.at("logo_alt", default: profil.absender.name),
          )
        } else {
          text(size: 16pt, weight: "bold", fill: farbe, profil.absender.name)
        }
      },
      {
        set align(right)
        set par(leading: 0.45em)
        for z in k.at("zeilen", default: ()) [#text(size: 8.5pt, z)\ ]
      },
    )
  })
}

// Fußzeile: Spalten nebeneinander, 7,5 pt.
#let fusszeile(profil) = {
  let spalten = profil.at("fusszeile", default: ())
  if spalten.len() == 0 { return none }
  let farbe = if "farbe" in profil { rgb(profil.farbe) } else { black }
  set text(size: 7pt)
  set par(leading: 0.45em)
  block(width: 100%, {
    line(length: 100%, stroke: 0.4pt + farbe)
    v(1.5mm)
    // Spaltenbreite nach Inhalt: eine IBAN in Vierergruppen passt sonst nicht
    // in ein Viertel der Satzbreite und bricht mitten in der Gruppe um.
    grid(
      columns: spalten.map(_ => auto),
      column-gutter: 1fr,
      ..spalten.map(sp => {
        for z in sp [#z\ ]
      })
    )
  })
}

// ── Satzregeln ──────────────────────────────────────────────────────────────
//
// Schrift, Zeilenraster, Ueberschriften, Zitat und Auszug — alles, was den
// Text selbst betrifft und nicht das Blatt. Auf Modulebene, weil zwei
// Hauptfunktionen sie teilen: `brief` und `urkunde`. Zweimal hingeschrieben
// liefen sie auseinander, und das Raster ist genau die Stelle, an der man das
// erst merkt, wenn zwei Blaetter nebeneinanderliegen.
#let satzregeln(profil: (:), daten: (:), body) = {
  set text(
    font: profil.at("font", default: "Libertinus Serif"),
    size: 11pt,
    // Aus den Daten, nicht fest: Davon haengt die Silbentrennung ab, und ein
    // englischer Text mit deutschen Trennregeln bricht an falschen Stellen um.
    lang: daten.at("gebiet", default: ("de", "DE")).at(0),
    region: daten.at("gebiet", default: ("de", "DE")).at(1),
    hyphenate: true,
    // Zeilenkasten fest in em statt nach Schriftmetrik: damit ist eine Zeile in
    // jeder Schrift gleich hoch. Ohne das haengt der Zeilenabstand am Ascender
    // der jeweiligen Schrift, und das 12-pt-Raster der Norm geht nicht mehr auf
    // (gemessen: Libertinus Serif und Source Sans 3 wichen um 1,7 mm ab).
    top-edge: 0.75em,
    bottom-edge: -0.25em,
  )
  // Grundzeilenabstand 12 pt = 4,2333 mm: 11 pt Zeilenkasten plus 1 pt Durchschuss.
  // Jede "Leerzeile" der Norm ist damit genau eine Rasterzeile.
  set par(justify: false, leading: durchschuss, spacing: leer(1))

  // Zwischenueberschriften im Brieftext (Dialekt 1.1).
  //
  // Alle vier Ebenen stehen in 11 pt. Das ist keine Sparsamkeit, sondern eine
  // Folge des Rasters: Eine groessere Zeile ist hoeher als eine Rasterzeile,
  // und alles darunter verliert seine Position. Ein Geschaeftsbrief hat auch
  // kein Schriftgroessen-Repertoire — er zeichnet mit Fett und Kursiv aus.
  //
  // Die Ebenen bleiben trotzdem vier: Sie stehen als Struktur im PDF, und
  // davon lebt ein Screenreader. Die Gliederungskennzeichnung (A. I. 1. a)
  // schreibt der Verfasser selbst in den Text.
  //
  // Abstaende in ganzen Rasterzeilen — sonst waere jede Ueberschrift ein
  // Versatz, der sich ueber die Seite summiert. `above: leer(n)` setzt die
  // Leerzeilen darueber, `below: durchschuss` die eine Rasterzeile darunter:
  // Der Zeilenkasten misst 11 pt, der Durchschuss ergaenzt ihn auf 12 pt.
  //
  // Seit Issue #140 ist das gemessen und keine blosse Zusage mehr — die
  // Rasterpruefung haelt die Abstaende aufeinanderfolgender Zeilen des
  // Briefkoerpers gegen 4,2333 mm. Mit `below: 0pt`, wie es hier bis zum
  // Merge von #140 stand, sind es 11 pt statt 12; die Pruefung meldet das
  // seither als „0.92 Zeilen" an jedem Absatz nach einer Ueberschrift.
  // Das Aussehen des Blockzitats. Es steht hier und nicht bei `#let zitat`,
  // weil eine show-Regel den Kontext eines Dokuments braucht; das `#let`
  // liefert nur noch das Element, damit die Auszeichnung entsteht.
  //
  // Kein Kasten, sondern ein Balken links: Ein Kasten braucht Innenabstaende,
  // und die sind in einem Zeilenraster nicht frei waehlbar. Der Balken kostet
  // keine Zeile.
  show quote.where(block: true): it => block(
    above: leer(1), below: leer(1),
    inset: (left: 6mm),
    stroke: (left: 0.6pt + luma(120)),
    it.body,
  )

  set heading(numbering: none, outlined: false)
  show heading: it => {
    let stil = (
      "1": (weight: "bold", style: "normal", davor: 2),
      "2": (weight: "bold", style: "normal", davor: 1),
      "3": (weight: "bold", style: "italic", davor: 1),
      "4": (weight: "regular", style: "italic", davor: 1),
    ).at(str(it.level))
    block(
      above: leer(stil.davor),
      below: durchschuss,
      text(size: 11pt, weight: stil.weight, style: stil.style, it.body),
    )
  }

  // Wortgetreue Auszuege: Festbreite, keine Einfaerbung, gleiche Groesse.
  // `raw` bringt von sich aus eine eigene Schriftgroesse mit; die wuerde das
  // Raster brechen.
  show raw: set text(font: ("DejaVu Sans Mono", "Menlo", "Consolas"), size: 11pt)

  body
}

// ── Hauptfunktion ───────────────────────────────────────────────────────────

#let brief(profil: (:), daten: (:), briefkopf-eigen: none, body) = {
  let form = daten.at("form", default: "B")
  let kopf-h = kopfhoehe.at(form)

  show: satzregeln.with(profil: profil, daten: daten)

  set document(
    title: daten.betreff,
    author: profil.absender.name,
  )

  // Folgeseiten tragen eine Kopfzeile mit Betreff und Datum.
  // letter-generic setzt page.header nicht, dieses set bleibt also wirksam.
  set page(header: context {
    if here().page() > 1 {
      set text(size: 8pt)
      grid(
        columns: (1fr, auto),
        align: (left, right),
        daten.at("betreff_kurz", default: daten.betreff),
        daten.datum,
      )
      v(-0.5mm)
      line(length: 100%, stroke: 0.4pt + gray)
    }
  })

  // Die Woerter, die im Satz stehen. Vorgabe deutsch, damit ein Aufruf ohne
  // dieses Feld weiter funktioniert.
  let woerter = daten.at("woerter", default: (
    anlage: "Anlage", anlagen: "Anlagen", verteiler: "Verteiler",
    seite: "Seite {n} von {m}",
  ))

  let vermerke = daten.at("vermerke", default: ())
  let info-eintraege = daten.at("infoblock", default: ())

  let info-content = if info-eintraege.len() > 0 { infoblock(info-eintraege) } else { none }

  // Die Fusszeile waechst nach oben in den unteren Rand hinein. DIN verlangt
  // unten mindestens 20 mm Textrand; fuer eine mehrzeilige Fusszeile braucht es
  // mehr, sonst laeuft sie aus der Seite. Profile koennen den Wert setzen.
  let rand-unten = profil.at("rand_unten_mm", default: 42) * 1mm

  letter-generic(
    format: "DIN-5008-" + form,
    margin: (left: 25mm, right: 20mm, top: 20mm, bottom: rand-unten),
    // Ein Profil darf den Briefkopf selbst setzen: liegt neben der YAML eine
    // .typ-Datei mit `briefkopf(profil)`, gewinnt sie über die Bausteine.
    // Die Höhe von 27 bzw. 45 mm erzwingt letter-pro unabhängig davon — ein
    // eigener Kopf kann das Anschriftfeld also nicht verschieben.
    header: if briefkopf-eigen != none { briefkopf-eigen(profil) } else { briefkopf(profil) },
    footer: fusszeile(profil),
    folding-marks: true,
    hole-mark: true,
    address-box: address-tribox(
      ruecksende-box(profil.ruecksendeangabe),
      vermerke-box(vermerke),
      recipient-box(daten.empfaenger.map(z => [#z]).join(linebreak())),
    ),
    information-box: info-content,
    // letter-pro setzt bei `auto` fest „Seite x von y“ (vendor-Datei, Zeile 177).
    // Die Datei ist pruefsummengesichert und wird nicht angefasst; stattdessen
    // bekommt sie eine Funktion, wie ihr eigener Vertrag es vorsieht.
    page-numbering: (n, m) => woerter.seite
      .replace("{n}", str(n)).replace("{m}", str(m)),
    {
      // Betreffposition: 2 Leerzeilen unter dem tiefer reichenden von
      // Anschriftfeld (Unterkante kopfhoehe + 45 mm) und Informationsblock
      // (Oberkante kopfhoehe + 5 mm, normativ mindestens 40 mm hoch).
      //
      // Der Abstand wird nicht addiert, sondern gemessen: `here().position()`
      // liefert die tatsaechliche Flussposition, und eingefuegt wird nur die
      // Differenz zur Sollposition. Damit bleibt der Betreff auch dann richtig,
      // wenn letter-generic oder Typst die Zwischenabstaende aendern.
      context {
        let h-info = if info-content == none {
          infoblock-mindesthoehe
        } else {
          calc.max(measure(info-content).height, infoblock-mindesthoehe)
        }
        let unterkante = calc.max(kopf-h + 45mm, kopf-h + 5mm + h-info)
        let soll = unterkante + 2 * zeile
        let ist = here().position().y
        v(calc.max(0mm, soll - ist), weak: false)
        // 2 Leerzeilen zwischen Betreff und Anrede
        block(above: 0pt, below: leer(2), strong(daten.betreff))
        block(above: 0pt, below: 0pt, daten.anrede)
      }

      // 1 Leerzeile zwischen Anrede und Text; innerhalb des Textes sorgt
      // par.spacing fuer je eine Leerzeile zwischen den Absaetzen.
      block(above: leer(1), below: 0pt, body)

      block(above: leer(1), below: 0pt, daten.gruss)

      if profil.at("firma_ueber_unterschrift", default: false) {
        block(above: leer(1), below: 0pt, profil.absender.name)
      }

      // Unterschriftsraum: ueblich 3 Leerzeilen. Mit Signaturbild wird der Raum
      // vom Bild gefuellt, der Abstand darunter bleibt gleich.
      //
      // `3 * zeile - durchschuss` und nicht `2.5 * zeile`: Ein Bild hat keinen
      // Zeilenkasten, also greift die Kompensation nicht, die `leer(n)` fuer
      // Textbloecke einrechnet. Mit der alten Hoehe stand alles unter der
      // Unterschrift 0,58 Rasterzeilen daneben — gemessen an sechs Beispielen,
      // Issue #140. Sichtbar wird so etwas erst, wenn zwei Blaetter
      // nebeneinanderliegen.
      if daten.at("signatur", default: none) != none {
        block(above: leer(1), below: 0pt, image(
          daten.signatur,
          height: 3 * zeile - durchschuss,
          alt: "Unterschrift " + daten.unterzeichner,
        ))
        block(above: leer(1), below: 0pt, daten.unterzeichner)
      } else {
        block(above: leer(3), below: 0pt, daten.unterzeichner)
      }

      let anlagen = daten.at("anlagen", default: ())
      if anlagen.len() > 0 {
        block(above: leer(1), below: 0pt, {
          strong(if anlagen.len() == 1 { woerter.anlage } else { woerter.anlagen })
          linebreak()
          anlagen.map(a => [#a]).join(linebreak())
        })
      }

      let verteiler = daten.at("verteiler", default: ())
      if verteiler.len() > 0 {
        block(above: leer(1), below: 0pt, {
          strong(woerter.verteiler)
          linebreak()
          verteiler.map(v => [#v]).join(linebreak())
        })
      }
    },
  )
}

// ── Urkunde: ein Schriftstück ohne Anschriftfeld ───────────────────────────
//
// Vereinbarung, Erklärung, Nachweis: ein Titel statt eines Betreffs, kein
// Empfänger, dafür Unterschriften. Nichts davon regelt die DIN 5008 — alle
// Maße dieses Abschnitts sind Setzungen des Werkzeugs (ADR 0048). Geteilt
// mit dem Brief wird, was das Profil ausmacht: Briefkopf, Fußzeile, Schrift,
// Ränder und das 12-pt-Raster.

// Ausfüllfeld: eine leere Linie fester Länge für Handeinträge, 2 mm je
// Unterstrich der Quelle (Dialekt 1.2).
//
// Ein Kasten mit Unterkante und nicht `line()`: Die Messung hält drei gleich
// lange *Linien* untereinander für einen Tabellenrahmen und nimmt den Bereich
// vom Zeilenraster aus (`geometrie._tabellenbereiche`). Drei Felder
// untereinander sind der Normalfall eines Formulars — sie würden jeden
// Rasterfehler dazwischen verstecken. Ein Kastenrand steht im PDF als flaches
// Rechteck und nicht als Linie; damit bleibt die Tabellenerkennung, was sie
// ist, und das Feld trotzdem messbar.
//
// Die Höhe liegt unter dem Zeilenkasten (0,75 em), also ändert das Feld den
// Zeilenabstand nicht.
#let feld-einheit = 2mm
#let feld(n) = box(
  width: n * feld-einheit,
  height: 0.6em,
  baseline: 1.5pt,
  stroke: (bottom: 0.5pt + black),
)

// Angabentabelle: Bezeichnung und Wert, ohne Kopfzeile und ohne Rahmen
// (Dialekt 1.2). Die Bezeichnungsspalte ist so breit wie ihr längster
// Eintrag, der Wert bekommt den Rest der Satzbreite.
//
// `table` und nicht `grid`: Nur so steht /Table, /TR, /TD im PDF. Ohne Rahmen
// erkennt die Messung sie nicht als Tabelle — sie muss das Raster deshalb
// selbst halten: Zellen ohne Innenabstand, eine Zeile je Rasterzeile.
#let angaben(..zellen) = block(
  above: leer(1), below: leer(1),
  table(
    columns: (auto, 1fr),
    stroke: none,
    column-gutter: 4mm,
    // Der Durchschuss steht ZWISCHEN den Zeilen, nicht unter jeder: Als
    // Innenabstand hinge er auch an der letzten und schöbe alles darunter um
    // 1 pt aus dem Raster (gemessen: 2,08 statt 2,00 Zeilen).
    row-gutter: durchschuss,
    inset: 0pt,
    ..zellen,
  ),
)

// Länge der Unterschriftslinie. Ungerade, damit sie nie mit einem
// Ausfüllfeld zusammenfällt (das misst immer ein Vielfaches von 2 mm).
#let unterschrift-linie = 65mm

// Ort-Datum-Zeile aus den Kopfdaten: Text und Ausfüllfelder im Wechsel.
#let _teile(teile) = teile.map(t => {
  if "feld" in t { feld(t.feld) } else { t.text }
}).join()

#let urkunde(profil: (:), daten: (:), briefkopf-eigen: none, body) = {
  show: satzregeln.with(profil: profil, daten: daten)

  set document(title: daten.titel, author: profil.absender.name)

  let woerter = daten.woerter
  let rand-unten = profil.at("rand_unten_mm", default: 42) * 1mm
  // Kein Anschriftfeld, also auch keine Form: Die Kopfhöhe richtet sich nach
  // dem Briefkopf des Profils, nicht nach der Lage eines Fensters. cli.py
  // wählt 27 oder 45 mm und vermerkt die Wahl im PDF.
  let kopf-h = daten.kopf_mm * 1mm

  set page(
    paper: "a4",
    margin: (left: 25mm, right: 20mm, top: 20mm, bottom: rand-unten),
    // Folgeseiten: der Titel als Kopfzeile, wie beim Brief der Betreff.
    header: context {
      if here().page() > 1 {
        set text(size: 8pt)
        daten.titel
        v(-0.5mm)
        line(length: 100%, stroke: 0.4pt + gray)
      }
    },
    // Fuß wie letter-pro ihn setzt (vendor-Datei, Zeile 162–194): Seitenzahl
    // nur bei mehr als einer Seite, Fußzeile nur auf der ersten. Nachgebaut,
    // weil letter-generic das Anschriftfeld immer reserviert.
    footer-descent: 0%,
    footer: context {
      show: pad.with(top: 12pt, bottom: 12pt)
      let n = here().page()
      let m = counter(page).final().first()
      grid(
        columns: 1fr,
        rows: (0.65em, 1fr),
        row-gutter: 12pt,
        if m > 1 {
          align(right, woerter.seite.replace("{n}", str(n)).replace("{m}", str(m)))
        },
        if n == 1 { fusszeile(profil) },
      )
    },
  )

  pad(top: -20mm, left: -25mm, right: -20mm, block(
    width: 100%, height: kopf-h,
    if briefkopf-eigen != none { briefkopf-eigen(profil) } else { briefkopf(profil) },
  ))

  // Der Titel ist die Überschrift erster Ebene: PDF/UA verlangt, dass die
  // erste Überschrift eines Dokuments Ebene 1 ist, und die Abschnitte im
  // Text sind Ebene 2.
  heading(level: 1, daten.titel)

  let parteien = daten.at("parteien", default: ())
  let partei(p) = {
    strong(p.name)
    for z in p.at("anschrift", default: ()) { linebreak(); z }
    if p.at("zusatz", default: none) != none { linebreak(); p.zusatz }
  }
  if parteien.len() == 1 {
    block(above: leer(1), below: 0pt, partei(parteien.at(0)))
  } else if parteien.len() == 2 {
    block(above: leer(1), below: 0pt, grid(
      columns: (1fr, 1fr),
      column-gutter: 10mm,
      { woerter.zwischen; linebreak(); partei(parteien.at(0)) },
      { woerter.und; linebreak(); partei(parteien.at(1)) },
    ))
  }

  block(above: leer(1), below: 0pt, body)

  // Ort, Datum und Unterschriften bleiben zusammen: Eine Unterschrift allein
  // auf der letzten Seite ist ein Blatt, das zu nichts gehört.
  let unterschriften = daten.at("unterschriften", default: ())
  // Ohne Unterschrift steht die Ort-Datum-Zeile für sich — sie still
  // wegzulassen hieße, ein Feld der Quelle zu verwerfen (Review von #381).
  if unterschriften.len() == 0 and daten.at("ort_datum", default: none) != none {
    block(above: leer(1), below: 0pt, _teile(daten.ort_datum))
  }
  if unterschriften.len() > 0 {
    block(breakable: false, above: leer(1), below: 0pt, {
      let ort-datum = daten.at("ort_datum", default: none)
      if ort-datum != none {
        block(above: 0pt, below: leer(1), _teile(ort-datum))
      } else {
        // Eine leere Linie zum Eintragen, darunter, was hingehört. Die Linie
        // steht in einem Kasten von genau einer Rasterzeile: Eine Zeile, in
        // der nur ein Feld steht, hat keinen Zeilenkasten, der sie auf 12 pt
        // brächte — die Beschriftung stand sonst 2,63 statt 3,00 Zeilen unter
        // dem Text (gemessen von der Rasterprüfung).
        block(above: 0pt, below: 0pt, height: zeile, align(bottom + left, feld(30)))
        block(above: 0pt, below: leer(1), woerter.ort_datum)
      }
      // Die Rollenzeile gibt es nur, wenn jemand eine Rolle trägt — sonst
      // stünde unter den Namen eine leere Zeile, und der Anlagenvermerk
      // rutschte um eine nach unten.
      //
      // Die letzte Zeile des Gitters misst 11 pt und nicht 12: Ein Gitter hat
      // keinen Durchschuss, den der Block darunter mit `leer(1)` ausgleichen
      // könnte. Mit 12 pt stand der Anlagenvermerk 2,08 statt 2,00 Zeilen
      // tiefer — gemessen von der Rasterprüfung am ersten Musterdokument.
      let mit-rolle = unterschriften.any(u => u.at("rolle", default: none) != none)
      let letzte = zeile - durchschuss
      grid(
        columns: (1fr, 1fr),
        column-gutter: 10mm,
        rows: if mit-rolle { (3 * zeile, zeile, letzte) } else { (3 * zeile, letzte) },
        ..range(2).map(i => if i < unterschriften.len() {
          grid.cell(align: bottom + left, pad(bottom: 1mm, line(length: unterschrift-linie, stroke: 0.5pt)))
        } else { [] }),
        ..range(2).map(i => if i < unterschriften.len() { unterschriften.at(i).name } else { [] }),
        ..if mit-rolle {
          range(2).map(i => if i < unterschriften.len() {
            unterschriften.at(i).at("rolle", default: none)
          } else { [] })
        } else { () },
      )
    })
  }

  let anlagen = daten.at("anlagen", default: ())
  if anlagen.len() > 0 {
    block(above: leer(1), below: 0pt, {
      strong(if anlagen.len() == 1 { woerter.anlage } else { woerter.anlagen })
      linebreak()
      anlagen.map(a => [#a]).join(linebreak())
    })
  }
}
