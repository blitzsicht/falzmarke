# vendor — im Quellbaum leer, im Skill-Paket gefüllt

Hier liegen im **ausgelieferten** Skill-Paket die Wheels, aus denen
`scripts/bootstrap.py` ohne Netzzugriff installiert. Im Quellbaum ist das
Verzeichnis leer, und das ist Absicht.

**Warum nicht eingecheckt.** Das `typst`-Wheel ist 32,6 MB groß. Eingecheckt
zöge es jeder Klon mit, bei jeder neuen typst-Fassung käme eine weitere Datei
dazu, und keine davon ließe sich je wieder aus der Historie entfernen. Ein
Repository, das Briefe setzt, trägt keinen Compiler mit sich herum.

**Wer es füllt.** `scripts/skill_packen.sh` lädt das Wheel beim Packen und legt
es hierher. Dasselbe Skript läuft lokal und im Release-Workflow — eine Probe,
die vom echten Job abweichen kann, prüft irgendwann etwas anderes als das, was
passiert.

**Warum ausgerechnet typst.** Von den fünf Abhängigkeiten ist es die einzige mit
nativem Binärkern und damit die, die in einer Sandbox als Erste fehlt. Die
übrigen vier sind verbreitet genug, dass eine Analyse-Umgebung sie meist schon
mitbringt. Gewählt wird das `cp38-abi3`-Wheel: Es gilt für jedes Python ab 3.8
statt für eine einzelne Fassung.

Wer offline arbeitet und mehr braucht, legt weitere Wheels hierher —
`bootstrap.py` nimmt jedes, das passt.

## Wer aus dem Repository baut, hat kein Wheel

Das ist die Kehrseite der Entscheidung oben, und sie soll nicht überraschen: Ein Klon dieses
Repositoriums — und ebenso jede Schnittstelle, die nur Repository-Dateien liest — findet dieses
Verzeichnis **leer**. Der erste Lauf braucht dann Netzzugriff, so wie vor v0.8.1.

Gemessen am 28.08.2026: Ein Werkzeug, das über einen GitHub-Zugriff Repository-Dateien und
Release-Metadaten sieht, bekommt das 33-MB-Binärasset des Releases nicht als lokale Datei. Für
solche Umgebungen ist der Weg deshalb **die `.skill`-Datei selbst**, nicht der Quellbaum.

Wer offline arbeiten muss und nur den Quellbaum hat, legt das Wheel von Hand hierher:

```bash
python3 -m pip download --only-binary=:all: --no-deps \
  --platform manylinux_2_17_x86_64 --python-version 3.8 --implementation cp --abi abi3 \
  --dest skill/vendor "$(grep -E '^typst' skill/requirements.txt)"
```

Das ist derselbe Aufruf, den `scripts/skill_packen.sh` beim Packen ausführt.
