# falzmarke

Geschäftsbriefe nach DIN 5008 direkt aus Claude: Du beschreibst den Brief, Claude schreibt den
Inhalt, falzmarke setzt ihn als PDF/A und misst das fertige PDF nach. Sitzt eine Falzmarke nicht,
endet der Lauf mit einem Fehler. Dazu E-Mails als .eml und Serienbriefe.

Dieses Plugin enthält nur den Skill, keinen MCP-Server. Fehlende Python-Pakete holt der Skill beim
ersten Lauf von PyPI.

Sollwerte aus Sekundärquellen, Normabgleich steht aus. Regeln aus nur einer Quelle wirken als
Warnung.

Beispiel: „Schreib eine Kündigung für meinen Mietvertrag zum Monatsende und mach ein PDF daraus.“

Website: [falzmarke.com](https://falzmarke.com/?utm_source=listing&utm_medium=directory&utm_campaign=anthropic-202611)
Quelltext: [github.com/blitzsicht/falzmarke](https://github.com/blitzsicht/falzmarke)
Lizenz: MIT
Datenschutz (Privacy): [Wohin Daten gehen](https://github.com/blitzsicht/falzmarke/blob/main/skill/README.md#wohin-daten-gehen)

## Wohin Daten gehen

Briefe, Mails und Absenderprofile bleiben als Dateien auf deinem Rechner. An falzmarke.com oder
Blitzsicht geht nichts. Zwei Wege führen über das Netz:

- **PyPI:** Beim ersten Lauf lädt der Skill fehlende Python-Pakete. Dabei gehen nur Paketnamen
  hinaus, kein Inhalt.
- **Dein eigenes Postfach, nur wenn du es eingerichtet hast:** Läuft auf deinem Rechner ein
  IMAP-Proxy unter `127.0.0.1:1993`, legt `email --oeffnen` die fertige Mail als Entwurf in den
  Ordner „Entwürfe“ deines Kontos und markiert dort die Mail, auf die du antwortest. Gesendet
  wird nichts; der Skill hat keinen Versandbefehl.

## In English

Create German DIN 5008 business letters in Claude: you describe the letter, falzmarke typesets
PDF/A and measures the finished PDF. Uses target values from secondary sources; the check against
the standard is open.

Where data goes: letters, emails and sender profiles stay as files on your machine; nothing is sent
to falzmarke.com or Blitzsicht. On first run the skill downloads missing Python packages from PyPI
(package names only). If you run an IMAP proxy on `127.0.0.1:1993`, `email --oeffnen` places the
finished email as a draft in your own mailbox and flags the message you reply to. Nothing is sent;
the skill has no send command.
