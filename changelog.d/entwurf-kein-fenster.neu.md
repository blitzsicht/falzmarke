- **`email --oeffnen --kein-fenster` legt den Entwurf ab, ohne ein Fenster zu öffnen.** Bis
  v0.10.0 war der Postfach-Weg fensterlos (ADR 0051); seit der Entwurfsbrücke öffnet jeder Lauf
  ein Verfassen-Fenster und holt Thunderbird nach vorn. Vier Briefe in einer Schleife waren
  damit vier Fenster und vier Fokussprünge. Mit dem Schalter bleibt die Brücke ganz heraus — sie
  wird nicht einmal gerufen. Die Hilfe zu `--oeffnen` nennt jetzt auch die beiden
  Umgebungsvariablen: `FALZMARKE_ENTWURF=nie` schaltet den Entwurf ab, `FALZMARKE_BRUECKE=nie`
  nur das Fenster (ADR 0054).
