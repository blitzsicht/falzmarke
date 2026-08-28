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
