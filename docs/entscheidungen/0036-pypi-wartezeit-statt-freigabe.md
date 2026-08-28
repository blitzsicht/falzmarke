# 0036 — Eine Wartezeit statt einer Freigabe von Hand

**Datum:** 28.08.2026 · **Status:** angenommen · **Umsetzung:** mit dem Merge dieses Eintrags

## Entscheidung

Der Upload nach PyPI wird nicht mehr von Hand freigegeben. An die Stelle der Freigabe tritt eine
**Wartezeit von 15 Minuten** im Environment `pypi`. Wer in dieser Zeit nichts tut, veröffentlicht;
wer den Lauf abbricht, veröffentlicht nicht.

Die beiden anderen Bremsen bleiben unverändert: Die Deployment-Branch-Policy lässt nur Tags `v*`
zu, und der Job läuft erst, wenn das Release selbst steht.

## Warum

Die Freigabe stand aus einem guten Grund da. Eine hochgeladene Version lässt sich zurückziehen,
aber nie löschen und nie durch eine andere Datei mit derselben Nummer ersetzen; die erste
Veröffentlichung von falzmarke brauchte fünf Anläufe und verbrauchte fünf Nummern. Alle fünf
Ursachen saßen **vor** dem Upload, vier fielen erst nach dem Freigabeklick auf.

Genau diese Fehlerklasse fängt seit [#76](https://github.com/blitzsicht/falzmarke/issues/76)
`scripts/paket_pruefen.sh` — bei **jedem** Push, nicht erst am Tag. Was die Freigabe damals
verhinderte, verhindert heute die CI, und zwar Tage früher. Übrig bleibt ein einziger Fall: ein
versehentlich gesetzter Tag.

Dem steht ein gemessener Preis gegenüber. Am 28.08.2026 hingen **drei** Läufe an dieser Bremse:

| Fassung | Wartezeit | Ausgang |
|---|---|---|
| v0.8.0 | 20 Stunden | abgebrochen, nie veröffentlicht |
| v0.8.1 | 6 Stunden | abgebrochen, durch v0.8.2 abgelöst |
| v0.8.2 | offen | — |

Auf PyPI lag an diesem Tag weiterhin 0.7.3, während drei Fassungen fertig gebaut danebenlagen.

**Ein Tor, das regelmäßig vergessen wird, schützt nicht — es hält nur an.** Der Unterschied ist
wichtig: Eine Bremse, die zuverlässig greift, kostet einen Handgriff. Eine, die vergessen wird,
kostet die Veröffentlichung und erzeugt dabei den Anschein von Sorgfalt.

Fünfzehn Minuten sind lang genug, um einen falschen Tag zu bemerken — der Lauf schreibt vorher
das Release und den Skill-Anhang, beides sichtbar —, und kurz genug, dass niemand sie vergisst.

## Was das nicht heißt

**Der Upload bleibt unumkehrbar**, und der Job trägt das weiterhin im Namen. Diese Entscheidung
macht ihn nicht harmloser, sie verlegt nur den Widerspruch von einem Klick, den jemand geben muss,
auf einen Abbruch, den jemand geben kann. Der Unterschied ist, was passiert, wenn niemand
hinsieht: vorher nichts, jetzt das Erwartete.

**Sie ersetzt keine Prüfung.** Wäre `paket_pruefen.sh` nicht da, wäre diese Entscheidung falsch.
Sie ruht vollständig darauf, dass die Fehlerklasse von damals heute vor dem Tag auffällt — wer
das Skript entfernt, nimmt dieser Entscheidung ihre Grundlage.

**Sie gilt nicht für andere unumkehrbare Vorgänge.** Es gibt derzeit keinen zweiten; entstünde
einer, ist er eigens zu entscheiden und nicht aus dieser hier abzuleiten.

## Wie es eingestellt ist

```bash
gh api repos/blitzsicht/falzmarke/environments/pypi \
  --jq '[.protection_rules[] | {type, wait_timer}]'
```

Erwartet werden `wait_timer: 15` und die `branch_policy`. Steht dort wieder
`required_reviewers`, hat jemand die Einstellung zurückgedreht — dann gilt entweder diese
Entscheidung nicht mehr, oder sie ist nicht umgesetzt. Beides gehört geklärt, nicht ausgesessen.

Die Einstellung lebt bei GitHub, nicht im Repository. Das ist der schwache Punkt dieser
Entscheidung und wird hier benannt statt verschwiegen: Sie lässt sich ändern, ohne dass ein Diff
entsteht. Deshalb steht der Prüfbefehl oben — und deshalb wurde dieser Eintrag erst zusammen mit
der Einstellung wirksam, nicht vorher. Ein Eintrag, der eine Konfiguration beschreibt, die es
nicht gibt, ist schlimmer als keiner: Er sagt dem nächsten Leser, er brauche nicht nachzusehen.
