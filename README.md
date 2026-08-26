# SignalWire Recipes

Working code for every part of a call. Each folder is one idea, proven against
the platform, small enough to read in a sitting and clone into your own project.

Browse the [recipe index](recipes/), or jump straight to a folder and run it.

## Start here

```bash
git clone https://github.com/ericminessale/signalwire-recipes.git
cd signalwire-recipes/recipes/answer-an-inbound-call/python

pip install -r requirements.txt
cp ../.env.example .env      # then fill it in
python app.py
```

The app prints the URL and Basic Auth credentials it is serving on. Point a
phone number's SWML webhook at that URL and call it.

Most recipes need a [SignalWire account](https://signalwire.com/), a
project ID and an API token. A few need only a phone number. Every recipe says
which at the top of its `Run it` section.

## What a recipe folder holds

```
recipes/scope-tools-per-step/
├── README.md          the claim, the mechanism, how to run it, what it cannot do
├── recipe.json        metadata: products, capabilities, related recipes
├── verify.py          proves the claim offline
├── .env.example       every variable the code reads
└── python/
    ├── app.py         usually under 200 lines
    └── requirements.txt
```

Some recipes ship more than one surface. A `swml/` directory holds the same
idea as a single YAML document, and `typescript/` holds it for Node. The
README covers all of them, because they are one recipe rather than three.

## Every claim is checked

A recipe's README states one claim in its first paragraph. That claim is not a
description of intent. It is checked by `verify.py`, which renders the exact
document the platform receives and asserts against it.

```bash
python verify.py scope-tools-per-step   # one recipe
python verify.py                        # all of them
```

The verifiers need no account, no phone number and no network. They read the
JSON keys the platform consumes rather than the SDK method names that produce
them, because those two often differ. When a recipe claims that a tool
disappears until a caller is verified, the verifier renders the document and
checks the tool is absent.

This is the part worth stealing. A snippet that compiles proves very little.

## Recipes and builds

A **recipe** is one idea with one claim, usually under 200 lines. A **build**
is an application you deploy and operate, and its artefact is a repository
rather than a file.

The test is whether you can state the claim in a sentence. A chat-to-voice
handoff draws on two other recipes and is still one idea, so it stays a
recipe. A contact centre is a thing you run, so it is a build.

Builds list what they compose. Those links are checked at build time, so a
build cannot claim a recipe that does not exist.

## Requirements

- Python 3.10 or newer, which is what `signalwire-sdk` requires
- `signalwire-sdk==3.0.1`, installed per recipe from its `requirements.txt`.
  The pin is exact on purpose: every verifier asserts the behaviour of that
  version, so a clone reproduces what was proved
- Node and npm for the recipes that ship a `typescript/` directory, which
  install `@signalwire/js` from their own `package.json`

The import is `from signalwire import AgentBase`. The older
`signalwire_agents` package is a different generation of the SDK and does not
work with this code.

## Layout

| Path | What it is |
|---|---|
| `recipes/` | every recipe and build, one folder each |
| `vocab/` | categories, task groups, surfaces and evidence types |
| `tools/` | the linter, the render checks and the verification helpers |
| `build.py` | generates the static site from the folders |
| `verify.py` | runs every recipe's verifier |

Folders are flat and named for the mechanism, not the scenario. The slug is
what a developer would search for, so `require-verification-before-unlocking-tools`
rather than `bank-agent`. The bank goes in the metadata as a tag.

## Deploying

The site is generated, so a deploy builds it rather than serving committed
files. `site/` is not in the repository.

```bash
python3 -m pip install -r requirements.txt
python3 build.py            # writes site/
```

`vercel.json` carries that build command and points at `site/`. The gate runs
separately in GitHub Actions, because the render checks need a browser and do
not belong in a deploy build.

`site.config.json` holds the repository link, the base URL and `indexable`.
While `indexable` is false the build writes a `robots.txt` that disallows
everything and puts `noindex` on every page. It refuses to finish if a page
escapes without the tag.

A live in-page demo needs an endpoint that mints Browser SDK tokens. Vercel can
host one, which is why it is the target; the demo slot on each recipe page is
built to take it when it exists.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). A recipe is finished when
`python verify.py <slug>` passes, and the linter holds the prose to the
SignalWire writing guide.

## Licence

MIT. See [LICENSE](LICENSE). Take the code and use it.

## Docs

- [SignalWire documentation](https://signalwire.com/docs)
- [SWML reference](https://developer.signalwire.com/swml/)
- [Agents SDK](https://developer.signalwire.com/sdks/agents-sdk/)
