# Contributing

Thanks for your interest. This project has one unusual property that shapes everything else:
**it measures its own output.** Whatever changes here has to stay measurable.

The tool itself, its code comments and its error messages are in German — DIN 5008 is a German
standard and the letters it produces are German business correspondence. This file and
[`SECURITY.md`](SECURITY.md) are in English, because bug reports and security findings come from
everywhere. Both languages are deliberate; please keep them where they are.

## The principle

A check that can never turn red is not evidence.

If you add a check, add its counter-test as well: in
[`tests/test_gegenbeweis.py`](tests/test_gegenbeweis.py) the layout is deliberately broken in
exactly one place, and your new check has to fire there. That includes the control case without
sabotage, which must stay green — without it, the test only proves that a copy measures
differently from the original, not that it measures the right thing.

The same holds for bug fixes: **reproduce the bug first, then fix it.** If it cannot be
reproduced, it is unclear what the fix repairs.

## Before opening a pull request

```bash
python3 skill/scripts/bootstrap.py
python3 -m pytest -q
for f in examples/*.md; do
  python3 skill/scripts/falzmarke.py render "$f" -o "/tmp/$(basename "$f" .md).pdf"
done
```

All tests green, all eight examples without a `FEHL` line.

## Changing measurements

The target values live in **one** place: `FORM` and the constants in
[`skill/falzmarke/geometrie.py`](skill/falzmarke/geometrie.py), documented in
[`skill/references/din5008.md`](skill/references/din5008.md). Change both together.

A changed value needs evidence — the standard, a dimensioned drawing, a measurement. Not the
widely circulated Word template: it demonstrably deviates by several millimetres, see
[`docs/normmasse.md`](docs/normmasse.md).

## The vendored file

`skill/falzmarke/typst/vendor/letter-pro-v3.0.0.typ` is third-party code (MIT) and is kept
**unmodified**. A test verifies its checksum. If something really has to change there, record
every change in `skill/falzmarke/typst/vendor/CHANGES.md` (create it) and update the checksum in
the test — both in the same commit.

Note that the string `normbrief` appears in that file, inside a Deutsche Post URL. It is not a
leftover of this project's former name; do not "fix" it. Replacing it would falsify a third-party
source and break the checksum.

## Style

- Code and comments in German, matching the subject matter.
- Comments explain **why**, not what. Most valuable: the reason something is *not* solved the
  obvious way.
- Commit messages describe the effect, not the file.

## Reporting bugs

For geometry problems, **always include the output of `verify`**:

```bash
python3 skill/scripts/falzmarke.py verify YOUR.pdf --form B --json
```

Without it there is no way to tell whether the layout sits wrong or the measurement is off.
