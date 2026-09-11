# falzmarke

**Other tools produce a PDF. falzmarke measures the result.**

You write the content as Markdown. falzmarke typesets it as a German business letter
following DIN 5008:2020, as PDF/A — and then measures the finished PDF. If the folding mark
does not sit at 105.0 mm, the run ends with an error instead of with a letter that is only
roughly right.

*This is a short English overview. The full documentation is German and lives in
[README.md](README.md) — that file is authoritative wherever the two disagree.*

[![CI](https://github.com/blitzsicht/falzmarke/actions/workflows/ci.yml/badge.svg)](https://github.com/blitzsicht/falzmarke/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](pyproject.toml)

---

## What it is for

DIN 5008 is the German standard for business correspondence. It fixes where the address field
sits so it shows through a window envelope, where the folding marks go so the sheet folds into
that envelope, how far the text block is inset, and how the information block on the right is
laid out. Getting this wrong is not a matter of taste: the letter arrives with the address
half-hidden, or the recipient's filing hole punches through a line of text.

falzmarke is for anyone who has to produce such letters from a machine — a script, an agent, a
pipeline — and wants the geometry checked rather than assumed.

**A note on what is and is not claimed.** The target values used here come from secondary
sources — publicly available drawings, guidance and reference implementations. The original
text of DIN 5008:2020-03 is copyrighted and is deliberately not part of this repository, so
the comparison against the original text of DIN 5008:2020-03 including Corrigendum 1:2020-07
is still outstanding. Because of that, rules backed by a single source act as warnings only;
a rule has to be corroborated by more than one source before it can fail a run. Every rule
carries its provenance in
[`skill/falzmarke/regeln/din5008.yaml`](skill/falzmarke/regeln/din5008.yaml). You will find no
claim of conformity anywhere in this project, and that omission is the point.

## What the measurement looks like

Every run prints a geometry report. An excerpt:

```
OK    Falzmarke 1, y: soll 105.00 ist 105.00 (tol ±0.3)
OK    Infoblock, x-links: soll 125.00 ist 125.00 (tol ±0.5)
OK    Betreff, y-Oberkante: soll 98.47 ist 97.91 (tol -1.75/+0.6)
OK    Abstand Betreff → Anrede (2 Leerzeilen): soll 12.70 ist 12.70 (tol ±0.2)
```

The report is read back out of the produced PDF with an independent library, not taken from
the values that went in. A tool that hands you a PDF and leaves open whether the measurements
hold is a PDF generator like any other.

## Install

```bash
pipx install falzmarke          # or: uvx falzmarke …
```

The Typst compiler ships as a Python wheel: no system installation, no LaTeX, no headless
browser. The package is on [PyPI](https://pypi.org/project/falzmarke/).

## Write a letter

```bash
falzmarke init brief.md --profil example --betreff "Angebot Nr. 2026-0815"
falzmarke render brief.md --png
```

The Markdown file is the source of truth, not the PDF. Changes go into the `.md` and the
letter is rendered again — never patched in the PDF.

Sender data lives in a profile: letterhead, footer columns, return line, signature, colours.
Profiles are YAML and are looked up in `~/.config/falzmarke/profiles/`. The fields are
documented in
[`skill/references/frontmatter.md`](skill/references/frontmatter.md).

## The same file as an email

```bash
falzmarke email brief.md --oeffnen
```

The same Markdown source, with `typ: email` in the front matter, becomes an `.eml` with a text
part, an HTML part, attachments and a signature — and the HTML body is measured too, not just
built. On macOS `--oeffnen` hands the message to the mail client as a **draft**, ready for a
human to read and send. falzmarke never sends anything; there is no send command and no option
that sends.

## As an MCP server

falzmarke speaks the Model Context Protocol over stdio, so clients that know nothing about
Claude skills can typeset and check letters through it.

```bash
pip install 'falzmarke[mcp]'
falzmarke mcp
```

Four tools:

| Tool | What it does |
|---|---|
| `brief_rendern` | Markdown with front matter → PDF, with the measurement report |
| `email_setzen` | the same source as `.eml`, with the measured HTML body |
| `brief_pruefen` | measure an existing PDF, including one this tool did not make |
| `profile_auflisten` | which sender profiles the server knows |

In a container — this is also how the MCP directories build it:

```bash
git clone https://github.com/blitzsicht/falzmarke.git && cd falzmarke
docker build -t falzmarke-mcp .
docker run --rm -i falzmarke-mcp   # -i is required: the server reads from stdin
```

The sender profile may be passed as an object in the call, so a client with no access to the
server's filesystem can bring its own sender rather than living with whatever profiles happen
to sit there.

What the service does **not** do: send, file, or deliver. It typesets and it measures.

## As a Claude skill

The `skill/` directory is a Claude skill. Either upload
[`falzmarke.skill`](https://github.com/blitzsicht/falzmarke/releases/latest) in the Claude
settings, or symlink it for Claude Code:

```bash
ln -s "$PWD/skill" ~/.claude/skills/falzmarke
```

Then: *"Write a letter to Muster GmbH, an offer for …"*

## Scope and limits

- **German business letters.** Forms A and B of DIN 5008. This is not a general-purpose
  document generator.
- **A subset of Markdown.** Paragraphs, bold, italic, lists, hard breaks, pipe tables.
  Anything else stops the run with a line number — links, images, code and HTML always.
  Headings, deeper lists and block quotes need an explicit dialect switch.
- **Linux, macOS, Windows.** PDF/A-2b by default; PDF/A-3b when a file is embedded.
- The interface, the messages and the documentation are German. The subject is a German
  standard, and translating the error messages would put a layer between the measurement and
  the person reading it.

## Contributing and licence

MIT, see [LICENSE](LICENSE). Contributions are welcome;
[CONTRIBUTING.md](CONTRIBUTING.md) is German but carries a short English paragraph, and so
does [SECURITY.md](SECURITY.md). Issues and pull requests in English are fine.
