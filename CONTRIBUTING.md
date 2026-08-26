# Contributing

A recipe is one testable claim about the platform, with the smallest code that
proves it. This file describes what that means in practice.

## One recipe, one claim

Before writing anything, state the claim in a sentence. If it takes two
sentences joined by "and", you have two recipes.

Name the folder after the mechanism, not the story around it. A developer
searching for this will type the mechanism.

```
require-verification-before-unlocking-tools     yes
bank-account-agent                              no
```

The bank belongs in `recipe.json` as `scenario` and as tags. Scenarios change,
mechanisms do not, and one mechanism serves every scenario that needs it.

Languages are directories inside a recipe, never separate recipes. A recipe
that ships Python and YAML is one folder with `python/` and `swml/` in it.

## Add a folder

Two routes. The scaffolder seeds from the planned list, so add your row to
`docs/enum/inventory.json` first:

```bash
python scaffold.py           # creates folders for launch rows with no folder
python scaffold.py --all     # every row, not only the launch set
```

It writes `recipe.json`, a README skeleton, `.env.example` and an empty entry
file per surface. It never deletes and never overwrites prose you have
written, so it is safe to re-run.

To skip the plan, copy the nearest existing recipe folder and edit it. The
generator reads `recipe.json` and nothing else, so a hand-made folder is a
first-class one.

Either way, fill in `summary`, `subcategory` and `products`. Category is
derived from `products`, so list every product the recipe touches and let the
category follow.

## The README is the page

The static site renders this file, so it is both the repository documentation
and the published page. It needs these sections:

| Section | What goes in it |
|---|---|
| What this demonstrates | the claim, stated in the first paragraph |
| How it works | the mechanism, with the JSON or YAML the platform receives |
| Run it | the commands, in order, from a clean clone |
| Verify it | what `verify.py` asserts |
| Limitations | what this does not do, and where it breaks |
| What to change first | the one knob a reader will reach for |

The first paragraph of *What this demonstrates* is the claim, and it renders
on its own as the page's headline assertion. Write it flat, with no throat
clearing.

Aim for 230 to 380 words of prose, not counting code. Running longer usually
means the recipe is doing two things.

## Prove it

A recipe is finished when its verifier passes, not when the code compiles.

```bash
python verify.py <slug>
```

`verify.py` renders the document the platform receives and asserts against it.
Helpers live in `tools/verifylib.py`.

Three rules decide whether a verifier is worth anything:

**Assert the keys the platform receives, not the SDK method names.** The two
often differ. `update_global_data` reaches the wire as `set_global_data`, and
`swml_change_step` arrives as `change_step`.

**Never import expected values from the code under test.** A verifier that
reads `LANGUAGES` from `app.py` and compares it to the rendered document
passes even when both are wrong. Put expected values in the verifier and
compare two surfaces against that third thing.

**An absent key is an assertion.** The SDK omits fields already sitting at
their schema default, so `end_on_exit=False` never appears. Assert
`"key" not in verb` rather than `verb.get(key, default)`, which passes either
way.

## Read the environment

Every variable the code reads belongs in `.env.example`, with a comment
saying what it does.

Call `load_dotenv()` at module level. The SDK does not read `.env` for you. An
early wave of recipes pinned `python-dotenv`, told the reader to copy
`.env.example`, and never loaded it, so every one of them failed from a clean
clone.

An `AgentBase` recipe also needs `SWML_BASIC_AUTH_USER` and
`SWML_BASIC_AUTH_PASSWORD`. Without them the SDK invents a password that
exists only in the running process. The number's webhook then gets a 401, and
the password changes on every restart.

## Pin the SDK exactly

Recipes pin `signalwire-sdk==3.0.1`, not a range. Every verifier asserts the
behaviour of that exact version. An open range installs a newer SDK on a clean
clone, so the code a reader runs no longer matches the claim that was proved.

Moving off the pin is a deliberate change: bump it, run every verifier, fix
what broke, then commit. The linter refuses a range.

## Write it like engineering

The reader is a developer deciding whether the platform does the thing. Name
the verb, the field and the action key. Say what the mechanism is.

```
record_call before connect, so the bridged leg is inside the recording   yes
seamlessly capture your conversations                                    no
```

Use second person and the active voice. Keep sentences under 26 words. Skip
the em dash; a comma, a colon or a full stop says the same thing.

Every claim in the prose is either proven by `verify.py` or attributed to a
documentation URL. There is no third category. If you cannot verify a claim,
do not write it.

`tools/lint_recipes.py` enforces the mechanical parts of this. Every rule in
it is a mistake that shipped once.

## Before you open a pull request

```bash
python tools/lint_recipes.py     # prose, structure, required files
python build.py                  # regenerates the site
python check_extensible.py       # vocabulary stays out of the generator
python verify.py                 # every recipe proves its claim
python tools/gen_index.py        # refresh recipes/README.md
```

The site under `site/` is generated. Never hand-edit it, and never commit a
change to it that `build.py` did not produce.

## Adding a category or a surface

Add a JSON file to `vocab/categories/` or `vocab/surfaces/`. The generator
reads the vocabulary and holds none of it, and `check_extensible.py` fails the
build if a vocabulary literal appears in generator source. A new category
ships its own label, ordering and icon, and no Python changes.
