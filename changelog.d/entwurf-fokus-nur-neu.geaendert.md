- **Thunderbird wird nur noch nach vorn geholt, wenn das Fenster in diesem Aufruf entstand.**
  Stand es schon offen, sprang der Fokus trotzdem. Entwurfsbrücke 0.3.5 (#415).

  **Achtung beim Update: `falzmarke entwurf-oeffnen` holt einen bereits offenen Entwurf nicht
  mehr nach vorn.** Der Befehl sagt weiterhin, dass das Fenster steht („war schon offen“, Exit
  0), aber den Wechsel dorthin macht jetzt der Mensch. Das ist der Preis dafür, dass eine
  Schleife über viele Briefe nicht mehr bei jedem Lauf den Fokus wegnimmt; wer den Sprung will,
  schließt das Fenster vorher oder wechselt selbst.
