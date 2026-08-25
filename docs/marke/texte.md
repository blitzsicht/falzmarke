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
- GitHub-Beschreibung (107 Zeichen): `DIN-5008-Briefe aus Markdown — als PDF/A gesetzt, auf den Millimeter geprüft. Skill für KI-Agenten und CLI.`


## Installationsbefehle

Nur diese duerfen in Bild und Text gezeigt werden. `pipx install falzmarke`
gibt es nicht — das Paket liegt nicht auf PyPI ([#7](https://github.com/blitzsicht/falzmarke/issues/7)).

- Ohne Clone: `uvx --from git+https://github.com/blitzsicht/falzmarke falzmarke`
- Dauerhaft: `pipx install git+https://github.com/blitzsicht/falzmarke`


## Erklaerfilm — 60 Sekunden

| Zeit | Szene | Text im Bild | Bild |
|---|---|---|---|
| 0–6 s | Wunsch | Ich brauche heute eine Mahnung an die Muster GmbH. | Markenfläche, Zeichen klein |
| 6–18 s | Sagen | Ein Satz genügt. Den Brief schreibt der Agent als Markdown. | stilisierter Chat, darunter die entstehende Markdown-Datei |
| 18–32 s | Setzen | Form aus Norm und Profil. Nichts wird von Hand gesetzt. | Terminalzeile, dann baut sich das Blatt auf: Anschriftfeld, Informationsblock, Betreff, Falzmarken |
| 32–42 s | Prüfen | Nachgemessen, nicht geschätzt. | Messlinien an Falzmarken, Anschriftfeld und Betreff; Bestätigungszeilen |
| 42–52 s | Ziel | PDF/A, archivfest. Ihr PDF ist Ihre Datei. | PDF mit zwei Anhängen; drei Wege: drucken, versenden, archivieren |
| 52–60 s | Für dich | Briefe schreiben mit KI — nach Norm, nicht nach Gefühl. | Zeichen groß, Claim, darunter der Installationsbefehl und die Adresse |
