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
#let zitat(inhalt) = block(
  above: leer(1), below: leer(1),
  inset: (left: 6mm),
  stroke: (left: 0.6pt + luma(120)),
  inhalt,
)

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

// ── Hauptfunktion ───────────────────────────────────────────────────────────

#let brief(profil: (:), daten: (:), briefkopf-eigen: none, body) = {
  let form = daten.at("form", default: "B")
  let kopf-h = kopfhoehe.at(form)

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
  // Abstaende in `leer(n)`, also ganzen Rasterzeilen — sonst waere jede
  // Ueberschrift ein Versatz, der sich ueber die Seite summiert.
  //
  // Das ist eine Zusage dieser Datei, KEINE gemessene Eigenschaft: Die
  // Geometriepruefung misst Raender, Zonen und den untersten Text, nicht die
  // Lage der Zeilen auf dem Raster. Nachgemessen mit einem krummen Abstand —
  // das PDF aendert sich, und keine Pruefung schlaegt an. Wer hier etwas
  // aendert, hat also kein Netz unter sich. Die Luecke steht als Issue #140.
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
      below: 0pt,
      text(size: 11pt, weight: stil.weight, style: stil.style, it.body),
    )
  }

  // Wortgetreue Auszuege: Festbreite, keine Einfaerbung, gleiche Groesse.
  // `raw` bringt von sich aus eine eigene Schriftgroesse mit; die wuerde das
  // Raster brechen.
  show raw: set text(font: ("DejaVu Sans Mono", "Menlo", "Consolas"), size: 11pt)

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
