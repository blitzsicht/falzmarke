// normbrief — DIN-5008-Wrapper um letter-pro v3.0.0
//
// Diese Datei setzt das Layout. Alle Werte stammen aus DIN 5008:2020;
// die Fundstellen stehen in skill/references/din5008.md.
//
// Aufgerufen wird sie aus einer von normbrief.py erzeugten main.typ:
//
//   #import "normbrief.typ": brief
//   #show: brief.with(profil: (..), daten: (..))
//   <Body als Typst-Markup>

#import "vendor/letter-pro-v3.0.0.typ": letter-generic, address-tribox, recipient-box

// Grundzeile: 12 pt = 4,2333 mm. DIN rechnet mit 4,23 mm.
#let zeile = 4.2333mm

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
          image(k.logo, height: k.at("logo_hoehe_mm", default: 42) * 1mm)
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
  set text(size: 7.5pt)
  set par(leading: 0.45em)
  block(width: 100%, {
    line(length: 100%, stroke: 0.4pt + farbe)
    v(1.5mm)
    grid(
      columns: spalten.map(_ => 1fr),
      column-gutter: 5mm,
      ..spalten.map(sp => {
        for z in sp [#z\ ]
      })
    )
  })
}

// ── Hauptfunktion ───────────────────────────────────────────────────────────

#let brief(profil: (:), daten: (:), body) = {
  let form = daten.at("form", default: "B")
  let kopf-h = kopfhoehe.at(form)

  set text(
    font: profil.at("font", default: "Libertinus Serif"),
    size: 11pt,
    lang: "de",
    region: "DE",
    hyphenate: true,
  )
  // DIN empfiehlt einen Zeilenabstand von etwa 130 % für den Fließtext.
  set par(justify: false, leading: 0.55em, spacing: zeile)

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
    header: briefkopf(profil),
    footer: fusszeile(profil),
    folding-marks: true,
    hole-mark: true,
    address-box: address-tribox(
      ruecksende-box(profil.ruecksendeangabe),
      vermerke-box(vermerke),
      recipient-box(daten.empfaenger.map(z => [#z]).join(linebreak())),
    ),
    information-box: info-content,
    page-numbering: auto,
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
        block(above: 0pt, below: 2 * zeile, strong(daten.betreff))
      }

      daten.anrede
      v(zeile)

      body

      v(zeile)
      daten.gruss

      if profil.at("firma_ueber_unterschrift", default: false) {
        v(zeile)
        profil.absender.name
      }

      // Unterschriftsraum: üblich 3 Leerzeilen.
      if daten.at("signatur", default: none) != none {
        v(0.5 * zeile)
        image(daten.signatur, height: 2.5 * zeile)
        v(0.5 * zeile)
      } else {
        v(3 * zeile)
      }

      daten.unterzeichner

      let anlagen = daten.at("anlagen", default: ())
      if anlagen.len() > 0 {
        v(2 * zeile)
        strong(if anlagen.len() == 1 { "Anlage" } else { "Anlagen" })
        linebreak()
        anlagen.map(a => [#a]).join(linebreak())
      }

      let verteiler = daten.at("verteiler", default: ())
      if verteiler.len() > 0 {
        v(2 * zeile)
        strong("Verteiler")
        linebreak()
        verteiler.map(v => [#v]).join(linebreak())
      }
    },
  )
}
