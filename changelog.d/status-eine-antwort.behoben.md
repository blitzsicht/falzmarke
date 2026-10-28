- **`falzmarke status` antwortet in der Textausgabe und in `--json` dasselbe.** Vier Stellen
  stellten dieselbe Lage verschieden dar. `· BELEGT` stand nur hinter `GESENDET`, während
  `--json` `belegt` für jeden Zustand meldete — jetzt hängt das Wort an einer einzigen Stelle,
  hinter jedem Zustand, den zwei Quellen tragen. Es steht damit auch hinter `SCHON RAUS` und
  verstärkt dort die Warnung „nicht noch einmal senden“. Hinter `GELÖSCHT` steht es nicht: Dass
  derselbe Betreff mit anderem Text hinausging, belegt für diesen Entwurf nichts. Die Zahl der
  Tagebucheinträge im Kopf zählte alle Konten des Thunderbird-Profils, obwohl die Zeile hinter
  einem einzelnen Absender steht; gezählt werden jetzt dessen Einträge.

  **Achtung beim Update: eine Zeile kann eine andere Überschrift tragen als bisher.** Liegt ein
  Entwurf noch in „Entwürfe“, steht aber derselbe Text schon in „Gesendet“, und ist zugleich ein
  Verfassen-Fenster offen, hieß die Zeile `OFFEN` und die Warnung stand erst dahinter. Jetzt
  heißt sie `SCHON RAUS` — dass der Text schon hinausging, ist die Nachricht, auf die es
  ankommt. Das offene Fenster nennt dieselbe Zeile weiter („gerade im Fenster offen“). Wer die
  Textausgabe mit `grep` auswertet, prüft das besser nach; `--json` trug die Lage schon vorher
  in eigenen Feldern.
