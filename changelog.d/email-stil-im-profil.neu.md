- **Der Schreibstil des Absenders steht im Profil.** Der neue Abschnitt `email.stil:` nimmt
  `person:` (`ich` oder `wir`), eigene `floskeln:` und freie `hinweise:` auf. `lint` warnt, wenn
  der Text die andere Person benutzt oder eine Wendung aus der eigenen Liste enthält — außerhalb
  wortgetreuer Auszüge. `hinweise:` prüft es nur auf Form: Den Inhalt liest das Modell, das
  formuliert (`SKILL.md` Schritt 4). falzmarke überträgt die Vorgabe, es erzwingt sie nicht
  (ADR 0053).
