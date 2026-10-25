- **Unsichtbare Zeichen im Entwurf werden gemeldet.** Zero-Width-Marken, weiche Trennstriche,
  Bidi-Steuerzeichen und Variantenselektoren aus einer Zwischenablage standen bisher ungeprüft in
  der fertigen `.eml` und im PDF. `lint` nennt jetzt Zeile und Stelle; geändert wird nichts.
  Geschützte Leerzeichen an den Stellen, an denen falzmarke selbst eines setzt — `z. B.`, `§ 7`,
  `12 kg` —, bleiben stumm (ADR 0052).
