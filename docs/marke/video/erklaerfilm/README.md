# Erklärfilm

Sechzig Sekunden vom Wunsch zum Ziel, in zwei Formaten: `Querformat` 1920 × 1080 und
`Hochformat` 1080 × 1920. Eine Zeitleiste, zwei Kompositionen — das Hochformat stapelt,
was quer nebeneinander steht.

## Bauen

```bash
make film-assets     # Schriften und Bilder nach public/ holen
cd docs/marke/video/erklaerfilm
npm install          # einmalig
npm start            # Remotion Studio zum Ansehen
```

`public/` liegt **nicht** im Repo. Es wären Kopien von Dateien, die schon da sind — und
`brief-mahnung.png` fiele als `*.png` sogar still unter eine `.gitignore`-Regel. Ein Ordner
im Repo, aus dem sich der Film trotzdem nicht bauen lässt, wäre schlimmer als gar keiner.
`make film-assets` baut ihn in einer Sekunde neu; `make film` ruft ihn selbst auf.

Aus dem Wurzelverzeichnis des Repos:

```bash
make film            # beide Fassungen nach docs/renders/
make pruefe-video    # ffprobe-Gatter über das Ergebnis
```

## Woher die Inhalte kommen

Nichts in diesem Ordner ist abgetippt.

| Datei | Quelle | Neu bauen |
|---|---|---|
| `src/texte.json` | [`docs/marke/texte.yaml`](../../texte.yaml) | `python3 scripts/texte.py` |
| `src/bericht.json` | ein echter `verify --json`-Lauf | `python3 scripts/bericht.py` |
| `src/brand.ts` | [`docs/marke/erscheinungsbild.md`](../../erscheinungsbild.md) | von Hand, beides zusammen |
| `public/brief-mahnung.png` | `docs/renders/`, erzeugt von der CI | `make bericht` rendert neu |

`tests/test_marke.py` prüft die Zeitleiste auf Lückenlosigkeit und jede Szene auf
mindestens 2,5 Sekunden Lesezeit. Wer eine Messzeile zeigen will, die es im Bericht nicht
gibt, fällt beim Bauen von `bericht.json` auf.

## Warum das lokal gerendert wird und nicht in CI

Zwei Gründe, und der zweite wiegt schwerer.

Erstens ist es die Hausordnung: Jedes Video in dieser Werkzeugkette entsteht auf einem
Rechner und wird nach Sichtprüfung eingecheckt. Ein Film ändert sich selten; ihn bei jedem
Push neu zu bauen, kostet Minuten und bringt nichts.

Zweitens die Lizenz. Remotion ist quelloffen einsehbar, aber keine Open-Source-Software im
Sinne der OSI. Automatisiertes Rendern gilt beim Hersteller als eigener Lizenzfall, und in
einem öffentlichen Repository ist nicht absehbar, wer den Build wie oft auslöst. Die
fertigen MP4-Dateien sind davon nicht berührt — sie sind Ergebnis, nicht Software, und
stehen wie das übrige Repository unter der MIT-Lizenz.

**Wer den Film selbst neu rendert, benutzt Remotion und braucht ab vier Beschäftigten eine
Company License.** Einzelheiten in
[`THIRD_PARTY_LICENSES.md`](../../../../THIRD_PARTY_LICENSES.md), Abschnitt „Nur für die
Videoerzeugung". Maßgeblich ist der Hersteller, nicht diese Datei.

Sollte die Lizenz je im Weg stehen, ist [Motion Canvas](https://motioncanvas.io) (MIT) der
vorgesehene Ersatz. Die Szenen hängen an `src/brand.ts` und `src/texte.json`, nicht an
Remotion-Eigenheiten.

## Schriften

`src/fontFaces.ts` deklariert alle Schriften **zentral**. Das ist kein Stilfrage: Im
Schwesterprojekt trug bis August 2026 jede Komposition ihren eigenen Block mit einem
absoluten Pfad. Der zeigt beim Rendern auf den Server-Root statt auf `public/` — jede
Schrift lief in einen 404, Chrome fiel still auf system-ui zurück, und das war nur im
Render-Log zu sehen, nie im Bild. Zehn veröffentlichte Videos waren davon betroffen.

`staticFile()` löst gegen `public/` auf, `font-display: block` lässt Remotion auf die
Schrift warten, statt einen Frame in Ersatzschrift zu rendern.
