# 0050 — Trägt die Identität eine Signatur, kommt sie aus Thunderbird

**Datum:** 15.10.2026 · **Status:** angenommen · **Ergänzt:** [0049](0049-entwurf-in-thunderbird.md)

## Worum es geht

Thunderbird setzt beim `-compose`-Entwurf die Signatur der Identität unter den Rumpf, den
`body=` mitbringt — und der trägt die Signatur aus dem Profil schon. Der Nachtrag zu 0049 riet
deshalb, die Signaturen in Thunderbird leer zu lassen. Das trägt nicht mehr: Beim Betreiber
haben seit dem 15.10.2026 alle Firmen-Identitäten eine Signatur, per `user.js` aus **derselben
Datei**, die das falzmarke-Profil als `email.signatur_html` nennt. Wer aus Thunderbird heraus
schreibt, soll sie haben; wer über falzmarke schreibt, bekam sie bisher zweimal.

## Entscheidung

Im Thunderbird-Weg sieht `--oeffnen` nach, ob die Identität mit der Absenderadresse selbst eine
Signatur setzt — `attach_signature` mit einer lesbaren `sig_file`, oder ein nicht leerer
`htmlSigText`. Gelesen werden `prefs.js` und danach `user.js` des Standardprofils
(`profiles.ini`, `[Install…] Default=` vor `Default=1`); `user.js` gewinnt, wie in Thunderbird.
Gezählt werden nur Identitäten eingerichteter Konten. Nichts wird geschrieben, nichts gestartet.

Trägt sie eine, steht die Signatur aus dem Profil **nicht** im `body=`, und der Befehl sagt in
einer Zeile, welche Identität und welche Datei sie liefert. In jedem anderen Fall — kein Profil,
keine oder mehrdeutige Identität, unlesbare Datei — bleibt es beim Verhalten von 0049: Signatur
im Rumpf, dazu der Hinweis, jetzt mit dem Grund.

**Die Dateien ändern sich nicht.** `.eml` und `.html` tragen die Signatur weiter; sie werden auch
ohne Thunderbird verwendet, und `verify --email` misst sie wie bisher. Nur der Rumpf des
Entwurfs weicht ab — der erste Fall, in dem der Entwurf nicht genau das trägt, was gemessen
wurde. Deshalb die Prüfung:

- Herausgenommen wird **genau das Stück**, das `eml.signatur_html` geliefert hat, und nur, wenn
  es im HTML-Teil der geschriebenen Datei genau einmal steht. Kein Muster.
- `_ohne_signatur_stimmt` hält danach den fertigen `body=`-Wert gegen den alten: Es darf genau
  die Signatur fehlen, sonst nichts. Schlägt sie an, bleibt die Signatur im Rumpf.
  `tests/test_gegenbeweis.py` sabotiert die Entnahme zweimal — zu viel, gar nichts.
- `_compose_stimmt` und `_rumpf_stimmt` laufen unverändert gegen den Rumpf, der wirklich
  übergeben wird.

## Grenzen

- **Ob Thunderbird die Datei so einsetzt, wie es soll**, ist nicht gemessen — nur, dass die
  Einstellung gesetzt ist und die Datei sich lesen lässt. Was im Fenster steht, prüft weiter der
  Mensch (0049, Entscheidung 2).
- **Welches Profil läuft**, weiß der Befehl nicht; er nimmt das Standardprofil. Wer Thunderbird
  mit einem anderen startet, bekommt eine Aussage über das falsche.
- **`sig_file-rel`** (`[ProfD]…`) wird nicht gelesen, nur `sig_file`. Fehlt sie bei
  `attach_signature`, gilt die Identität als unbestimmt — Signatur im Rumpf.
- **Mehrere Identitäten mit derselben Adresse** zählen nur, wenn sie dasselbe sagen; welche
  `from=` wählt, ist nicht gemessen.
- **Nur Thunderbird auf macOS.** Für Outlook bleibt der Hinweis, wie er war.
