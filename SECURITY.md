# Security

## Reporting

Please report security-relevant findings **privately** to **servus@blitzsicht.com**, not as a
public issue. You can expect a reply within three working days.

This file is in English because findings come from everywhere; the tool itself is German, see
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Where the attack surface is

falzmarke processes files it did not write and hands them to a compiler. The interesting parts are
therefore:

- **Front matter** is read with `yaml.safe_load` — never `load`.
- **Letter body** is translated into Typst markup. Text is emitted as a Typst string literal
  rather than escaped piecemeal ([`skill/falzmarke/markdown.py`](skill/falzmarke/markdown.py)),
  and the Markdown parser runs against an allow-list of node types. A way to get Typst code
  through either of those would be a finding.
- **Profile paths, logos and signature images** are resolved relative to the profile file and
  copied into a temporary working directory. A way out of that directory would be a finding.
- **Typst** compiles inside its own root directory and reads nothing above it. System fonts are
  disabled (`ignore_system_fonts`), so a document cannot pull in fonts from the host.

## What is not a security finding

- A letter with wrong geometry — that is a bug, please open an issue.
- Credentials inside your own profile: profiles belong in `~/.config/falzmarke/profiles/`, not in
  a public repository. The bundled search path keeps the two apart on purpose.
- The string `normbrief` inside `skill/falzmarke/typst/vendor/letter-pro-v3.0.0.typ`. It is part
  of a Deutsche Post URL in a third-party file that is kept byte-for-byte unmodified, and is
  verified by checksum.

## Supported versions

Only the latest release receives fixes. There is no long-term support branch.
