# Entwurfsbrücke: das Thunderbird-Add-on

`falzmarke email --oeffnen` legt einen Entwurf in „Entwürfe“ ab. Die Entwurfsbrücke öffnet ihn
in Thunderbird, wie „Entwurf bearbeiten“ es tut. Sie notiert, was aus ihm wurde, und hält das
Senden an, wenn derselbe Text schon an diese Empfänger ging. Senden, speichern, löschen oder
verschieben kann sie nicht. Warum ein Add-on: [ADR 0054](entscheidungen/0054-entwurfsbruecke-in-thunderbird.md),
Status und Sperre: [ADR 0055](entscheidungen/0055-entwurfsbuch-status-und-sperre.md).

## Installieren

1. Am [jüngsten Release](https://github.com/blitzsicht/falzmarke/releases/latest) die Datei
   `entwurfsbruecke-<fassung>.xpi` laden.
2. In Thunderbird: Menü → Add-ons und Themes → Zahnrad → „Add-on aus Datei installieren…“ → die
   Datei wählen.
3. Thunderbird fragt nach drei Rechten: `compose` (das Verfassen-Fenster und der Moment vor dem
   Senden), `messagesRead` und `accountsRead` (in „Gesendet“ nachsehen). Mehr verlangt das Add-on
   nicht. Thunderbird beschreibt `compose` weiter, als das Add-on es nutzt.

Thunderbird ab 128 genügt. Die Datei ist nicht bei Mozilla signiert. Thunderbird verlangt das
nicht: `xpinstall.signatures.required` steht dort ab Werk auf `false`.

## Prüfen, ob es die Datei aus dem Release ist

Neben jeder `.xpi` liegt ihre Prüfsumme, und der Release-Lauf bestätigt, aus welchem Commit sie
stammt:

```bash
shasum -a 256 entwurfsbruecke-<fassung>.xpi        # gleich dem Inhalt von …xpi.sha256
gh attestation verify entwurfsbruecke-<fassung>.xpi --repo blitzsicht/falzmarke
```

Selbst packen geht auch, `python3 scripts/xpi_packen.py` schreibt `dist/entwurfsbruecke-<fassung>.xpi`.
Aus demselben Commit gepackt, gibt das dieselben Bytes wie die Datei am Release.

## Updates

Einmal installiert, sucht Thunderbird selbst nach neuen Fassungen. Es liest dafür `updates.json`
am jüngsten Release. Die Datei nennt Fassung, Link und Prüfsumme; Thunderbird installiert nur die
Datei mit genau dieser Prüfsumme. Von Hand: Add-ons und Themes → Zahnrad → „Nach Updates suchen“.

Ein Update kann neue Rechte verlangen. Dann fragt Thunderbird vorher.

## Läuft es?

```bash
falzmarke entwurf-oeffnen --absender ich@example.de
```

Die letzte Zeile nennt die Fassung, die in Thunderbird antwortet:
`OK  Entwurfsbrücke <fassung> in Thunderbird <version>`. Fehlt das Add-on, steht dort, warum kein Fenster
aufgeht.

## Was es aufschreibt

Ein Tagebuch, `entwurfsbruecke-tagebuch.jsonl` im Profilordner von Thunderbird: geöffnet,
gespeichert, gesendet, ohne Senden geschlossen, angehalten. `falzmarke status` liest es mit. Was
in den Einträgen steht: `thunderbird/entwurfsbruecke/README.md`. Gerufen wird das Add-on über
einen Unix-Socket im Profilordner von Thunderbird (`bruecke.sock`, Rechte 0600): Von außen ist
es nicht erreichbar, und auf demselben Rechner kommt nur das Konto daran, das Thunderbird
fährt.

## Entfernen

Add-ons und Themes → Entwurfsbrücke → Entfernen. Das Tagebuch bleibt im Profilordner liegen,
bis man es löscht. falzmarke legt Entwürfe danach weiter ab, öffnet sie nur nicht mehr.
