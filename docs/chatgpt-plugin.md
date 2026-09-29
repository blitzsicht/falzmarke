# Plugin für ChatGPT

Stand: 29.09.2026. Quellen: die Plugin-Doku von OpenAI unter developers.openai.com/plugins/, am
selben Tag gelesen.

## Warum es das Plugin gibt

Eigene Skills nimmt ChatGPT nur in der Desktop-App und in den Tarifen Business, Enterprise und Edu
an. Im Browser und auf dem Handy mit privatem Tarif lehnt ChatGPT die Installation ab („kann nur
bereits bereitgestellte Skills verwalten“). Dort kommt ein Skill nur als Plugin aus dem Verzeichnis
von OpenAI zu den Nutzern.

An der Laufzeit liegt es nicht. Gemessen am 29.09.2026 im Plus-Browser, normaler Chat:

- Python 3.13.5, x86_64, kein PyPI;
- yaml, pdfplumber, pypdf, markdown-it und Pillow sind vorinstalliert;
- der hochgeladene Skill meldete nur typst als fehlend und installierte es aus `vendor/`;
- danach meldete die Prüfung `verify: 34/34`.

## Was das Release liefert

`falzmarke-chatgpt-plugin.zip` baut `scripts/skill_packen.sh` über `scripts/plugin_packen.py`:

    plugin.json              Manifest, Name, Version und Kurzbeschreibung aus pyproject.toml
    skills/falzmarke/        derselbe Ordner wie im Offline-Paket, samt typst-Wheel

Der Packer bricht ab, bevor ein Paket entsteht, das die Einreichung zurückweisen würde:

- ZIP höchstens 100 MB,
- höchstens 5000 Einträge und 20 Pfadsegmente,
- `description` höchstens 1024 Zeichen,
- keine Symlinks,
- ein Wheel muss in `vendor/` liegen.

Die Grenze **je Skill** nennt OpenAI nur im Fehlertext des Portals. Sie ist bis zur ersten
Einreichung offen.

## Einreichen (von Hand, durch den Betreiber)

1. Auf platform.openai.com die Identität prüfen lassen und die Rolle „Apps Management: Write“ holen.
2. Unter platform.openai.com/plugins ein neues Plugin anlegen, Typ **Skills only**, und
   `falzmarke-chatgpt-plugin.zip` aus dem Release hochladen.
3. Die Testfälle unten eintragen, dazu Länder und Release Notes.
   Pflicht ist außerdem eine **Demo-Aufnahme** (URL auf ein Video), die die Hauptfälle zeigt; sie
   wird nicht veröffentlicht.
4. Nach der Freigabe selbst veröffentlichen. Die Adresse des Eintrags im Verzeichnis kommt aus dem
   Portal; sie gehört danach in die Anleitung auf falzmarke.com.

Beobachtet am 29.09.2026 in der Organisation Blitzsicht: „Create plugin“ bot nur **With MCP** an,
nicht „Skills only“, obwohl die Doku beide nennt. An der Identität lag es nicht: Die Organisation
war zu dem Zeitpunkt schon verifiziert. Der OpenAI-Support hat die Anfrage am selben Tag an einen
Menschen übergeben. Der Ausweg über „With MCP“ ist #377.

Jede neue Version muss erneut geprüft werden, und die `version` in `plugin.json` muss sich ändern.
Deshalb geht nicht jedes Patch-Release zu OpenAI, sondern nur eines, das am Skill etwas ändert.

## Testfälle für die Einreichung

Soll auslösen:

1. Schreib mir einen Brief an die Muster GmbH, Musterstraße 1, 12345 Musterstadt: Ich kündige meine
   Mitgliedschaft Nr. 2024-1187 zum nächstmöglichen Termin.
2. Setz eine Mahnung an Herrn Beispiel, Rechnung 2026-044 über 480 Euro ist seit 30 Tagen offen.
3. Ich brauche ein Angebot als PDF zum Ausdrucken für Firma Beispiel AG, Position: 20 Stunden
   Beratung zu je 95 Euro.
4. Schreib eine E-Mail an den Kunden: Der Termin am 3. Oktober verschiebt sich auf 14 Uhr.
5. Formuliere einen Widerspruch gegen den Bescheid vom 12. September an das Finanzamt Musterstadt.

Soll nicht auslösen:

1. Fasse mir diesen Artikel in drei Sätzen zusammen.
2. Übersetze diesen Absatz ins Englische.
3. Erklär mir, was ein Fensterumschlag ist.

## Was nicht behauptet wird

Die Sollwerte stammen aus Sekundärquellen. Der Abgleich mit dem Originaltext der DIN 5008:2020-03
einschließlich Berichtigung 1:2020-07 steht aus, und Regeln aus einzelnen Quellen wirken nur als
Warnung. Das gilt für den Eintrag im Verzeichnis genauso wie für das README.
