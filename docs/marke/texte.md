<!-- Erzeugt aus texte.yaml — nicht von Hand aendern.
     Neu bauen: python3 scripts/texte.py -->

# Textkanon

Einzige Quelle fuer Claim, Untertitel und die Szenentexte des Erklaerfilms ist
[`texte.yaml`](texte.yaml). Diese Datei ist daraus erzeugt.

README, `pyproject.toml`, der Banner und der Film werden gegen den Kanon geprueft
(`tests/test_marke.py`). Wer einen Satz aendern will, aendert die YAML und laesst
`python3 scripts/texte.py` laufen.


## Claim

**Briefe schreiben mit KI — nach Norm, nicht nach Gefühl.**

Sekundaer, nie allein: *Nachgemessen, nicht geschätzt.*


## Untertitel

- Deutsch: DIN-5008-Briefe aus Markdown — als PDF/A gesetzt und auf den Millimeter geprüft.
- Englisch: German business letters from Markdown — rendered to PDF/A and verified to the millimetre.


## Kurzformen

- Fusszeile: Claude-Skill · CLI · PDF/A · Hybridbrief
- Adresse: falzmarke.com
- GitHub-Beschreibung (90 Zeichen): `DIN-5008-Briefe aus Markdown, am fertigen PDF nachgemessen. Sollwerte aus Sekundärquellen.`


## Installationsbefehle

Nur diese duerfen in Bild und Text gezeigt werden. Seit v0.7.3 gibt es
`pipx install falzmarke` zwar wirklich ([PyPI](https://pypi.org/project/falzmarke/)) —
der Kanon bleibt trotzdem beim `git+`-Weg: Er trifft auch den unveroeffentlichten
Stand von `main`, und er steckt im gerenderten Film. Umstellen hiesse Film und
Szenen neu rendern.

- Ohne Clone: `uvx --from git+https://github.com/blitzsicht/falzmarke falzmarke`
- Dauerhaft: `pipx install git+https://github.com/blitzsicht/falzmarke`


## Nutzen im Bild

- ohne: Frei gesetzt: jedes Mal ein anderes Blatt.
- mit: Aus Norm und Profil: jedes Mal dasselbe.


## Erklaerfilm — 26 Sekunden

| Zeit | Szene | Text im Bild | Bild |
|---|---|---|---|
| 0–4 s | Auftrag | Hey, schreib mir eine Mahnung an die Muster GmbH: Rechnung 2026-0815, 2.380 Euro, Frist 8. September. | Eingabefeld eines Chats, der Satz tippt sich, dann wird abgeschickt |
| 4–9 s | Ohne | Frei gesetzt. | ein Blatt, dreimal umgesprungen: brief.txt, brief.docx, brief.pdf — dann durchgestrichen |
| 9–16 s | Norm | Der ganze Brief, nachgemessen. | der Brief, darauf der Stempel; danach Zonen und Masse ueber das ganze Blatt |
| 16–21 s | Gleich | Jedes Mal dieselbe Form. | drei gleiche Blaetter |
| 21–26 s | Für dich | Briefe schreiben mit KI — nach Norm, nicht nach Gefühl. | Zeichen, Claim, Installationsbefehl, Adresse |
