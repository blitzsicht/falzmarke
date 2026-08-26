# Erzeugte Dateien der Marke und der Videos.
#
# Warum eine Makefile in einem Python-Repo: Diese Ziele rufen unterschiedliche
# Werkzeuge auf — Chrome, vhs, Remotion, Python. Ein gemeinsamer Einstieg spart
# es, sich vier Aufrufe zu merken, von denen jeder woanders laeuft.
#
# Nichts davon laeuft in CI ausser dem GIF. Der Erklaerfilm entsteht lokal, wie
# jedes andere Video im Haus; CI misst nur das eingecheckte Ergebnis.

FILM := docs/marke/video/erklaerfilm

.PHONY: help marke texte bericht changelog gif film film-assets film-quer film-hoch pruefe-video alles

help:
	@echo "make marke        Banner und Vorschaubild aus der HTML-Quelle"
	@echo "make texte        texte.md und texte.json aus texte.yaml"
	@echo "make bericht      Messwerte fuer den Film aus einem echten verify-Lauf"
	@echo "make changelog    Verlaufsabschnitt der README aus CHANGELOG.md"
	@echo "make gif          README-GIF neu aufzeichnen (braucht vhs)"
	@echo "make film-assets  Schriften und Bilder nach erklaerfilm/public/ kopieren"
	@echo "make film         Erklaerfilm in beiden Formaten (braucht npm install im Filmordner)"
	@echo "make pruefe-video ffprobe-Gatter ueber die fertigen Videos"
	@echo "make alles        marke, texte, bericht, gif, film, pruefe-video"

marke:
	bash scripts/marke.sh --verify

texte:
	python3 scripts/texte.py

bericht:
	python3 scripts/bericht.py

changelog:
	python3 scripts/changelog.py

gif:
	vhs docs/marke/video/readme.tape

# public/ liegt nicht im Repo: es waeren Kopien von Dateien, die schon da sind —
# und brief-mahnung.png fiele als *.png sogar still unter die .gitignore-Regel.
# Ein Ordner im Repo, aus dem sich der Film trotzdem nicht bauen laesst, waere
# schlimmer als gar keiner.
film-assets:
	mkdir -p $(FILM)/public/fonts
	cp docs/marke/fonts/Montserrat-ExtraBold.ttf $(FILM)/public/fonts/
	cp docs/marke/fonts/Montserrat-SemiBold.ttf  $(FILM)/public/fonts/
	cp skill/falzmarke/assets/fonts/SourceSans3-Regular.otf  $(FILM)/public/fonts/
	cp skill/falzmarke/assets/fonts/SourceSans3-Semibold.otf $(FILM)/public/fonts/
	cp docs/assets/brand/logo.svg     $(FILM)/public/logo.svg
	cp docs/renders/brief-mahnung.png $(FILM)/public/brief-mahnung.png
	@echo "OK  Bausteine in $(FILM)/public/"

film: texte bericht film-assets film-quer film-hoch

film-quer:
	cd $(FILM) && npm run quer

film-hoch:
	cd $(FILM) && npm run hoch

pruefe-video:
	bash scripts/pruefe-video.sh

alles: marke texte bericht changelog gif film pruefe-video
