// Beispiel für einen frei gestalteten Briefkopf.
//
// Wird in einem Profil `briefkopf_typ: example-kopf.typ` gesetzt, ruft
// falzmarke diese Funktion statt der YAML-Bausteine auf. Das Anschriftfeld
// bleibt davon unberührt: seine Höhe erzwingt letter-pro.
//
// Verfügbar ist alles aus dem Profil-Dictionary — absender, farbe, briefkopf,
// fusszeile und was sonst in der YAML steht.

#let briefkopf(profil) = {
  let farbe = if "farbe" in profil { rgb(profil.farbe) } else { black }
  set text(size: 9pt)
  pad(left: 25mm, right: 20mm, top: 10mm, {
    grid(
      columns: (1fr, auto),
      align: (bottom, bottom),
      {
        text(size: 22pt, weight: "bold", fill: farbe, profil.absender.name)
        linebreak()
        v(1mm)
        line(length: 42mm, stroke: 2pt + farbe)
      },
      {
        set align(right)
        set par(leading: 0.5em)
        text(size: 8pt, fill: farbe.darken(20%))[
          #profil.absender.strasse \
          #profil.absender.plz #profil.absender.ort
        ]
      },
    )
  })
}
