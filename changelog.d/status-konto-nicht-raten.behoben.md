- **`OFFEN` und `BELEGT` konnten an manchen Einrichtungen nie entstehen, und zwar still.**
  Welchem Konto ein offenes Verfassen-Fenster gehört, wurde aus der Adresse der Nachricht
  (`imap-message://…`) geraten: Ihr Autoritätsteil trägt aber den IMAP-Anmeldenamen, nicht die
  E-Mail-Adresse. Lautet der Login `m0123456` oder `order`, während die Adresse
  `order@example.de` ist, traf der Vergleich nie — ein Entwurf, der gerade in einem Fenster
  stand, hieß `WARTET`. Umgekehrt traf er auch ein fremdes Konto, dessen Adresse die eigene als
  Teilstück enthält. Gefragt wird jetzt das Add-on, das die Absenderadresse des Fensters ab 0.3.0
  meldet; fehlt sie, hängt die Zuordnung an der UID, und die Adresse entscheidet nur noch
  zwischen zwei Fenstern derselben UID. Das Tagebuch kommt aus dem Thunderbird-Profil, in dem der
  Socket der Brücke liegt, nicht länger blind aus dem Standardprofil — bei gesetztem
  `FALZMARKE_BRUECKE_SOCKET` las `status` sonst eine Datei, die niemand schreibt, und meldete
  „kein Tagebuch", was nach einem zu alten Add-on klingt. Fehlt es wirklich, nennt der Hinweis
  jetzt das gelesene Profil. (#410)
