# Der Mitschnitt fuer das README-GIF. Aufnahme: vhs docs/marke/video/readme.tape
#
# Gezeigt wird die echte CLI, nicht eine nachgestellte. Die Befehlsfolge ist
# dieselbe wie im CI-Job `frischklon` (.github/workflows/ci.yml) — dort wacht
# schon ein Lauf darueber, dass es diese Befehle wirklich gibt.
#
# Farben: Papier und Tinte aus docs/marke/erscheinungsbild.md. Kein Gruen im
# Bild, obwohl der Auftrag es vorsah: die CLI schreibt keine ANSI-Sequenzen,
# jede Zeile kommt in derselben Farbe. Ein GIF mit gruenen OK-Zeilen wuerde
# etwas zeigen, das vor keinem echten Terminal je so aussieht.
#
# Das Tape laeuft aus dem Wurzelverzeichnis des Repos.

Output docs/renders/demo.gif
Output docs/renders/demo.mp4
Output docs/renders/demo.ascii

Require falzmarke

Set Shell "bash"
Set FontSize 18
Set Width 1280
Set Height 720
Set Padding 24
Set TypingSpeed 55ms
Set Theme { "name": "falzmarke", "background": "#FFFFFF", "foreground": "#121E2F", "cursor": "#121E2F", "selection": "#D8DCE2", "black": "#121E2F", "red": "#A32F2F", "green": "#2F8642", "yellow": "#8A6D1F", "blue": "#1F5AA8", "magenta": "#7A3E8F", "cyan": "#1F6F7A", "white": "#5B6470", "brightBlack": "#5B6470", "brightRed": "#A32F2F", "brightGreen": "#2F8642", "brightYellow": "#8A6D1F", "brightBlue": "#1F5AA8", "brightMagenta": "#7A3E8F", "brightCyan": "#1F6F7A", "brightWhite": "#121E2F" }

# Fester Prompt, sonst haengt das Bild an der Shell-Konfiguration dessen,
# der gerade aufnimmt — und zwei Laeufe ergaeben zwei verschiedene GIFs.
Hide
Type "export PS1='$ ' && clear" Enter
Sleep 500ms
Show

# 1. Der Brief, wie ihn ein Agent geschrieben hat: Frontmatter und drei Saetze.
Type "cat examples/brief-mahnung.md" Sleep 400ms Enter
Sleep 3s

Hide
Type "clear" Enter
Sleep 300ms
Show

# 2. Setzen und messen in einem Schritt. --verbose, weil der Bericht sonst
#    aus genau einer Zeile besteht (so gewollt, siehe tests/test_verify.py).
Type "falzmarke render examples/brief-mahnung.md --png --verbose" Sleep 400ms Enter
Sleep 6s

# 3. Die Abschlusszeile stehen lassen.
Sleep 3s
