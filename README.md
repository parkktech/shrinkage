# Shrinkage

> Normally, shrinkage is a bad thing. It's the word you deploy with an
> explanation attached. *"I was in the pool!"* Not here. Here, shrinkage is
> the whole point.

## The uncomfortable truth about your codebase

Your codebase is a grower. Every sprint it grows. Nobody asked it to — it just
does. A new feature lands and somehow there's a new `Manager` class, a new
`utils` file, an interface with exactly one implementer standing there like it's
waiting for friends who are never coming.

And look — being a grower isn't always the flex it sounds like. Growth without
a reason is just swelling. Every line you add is a line somebody (you, in six
months, at 2 a.m.) has to read, test, and debug. The devs you brag about aren't
the ones who wrote the most code. They're the ones who shipped the feature and
the diff came out **negative**.

Shrinkage makes your AI coding agent one of those devs.

## What it actually does

Two things, and they feed each other:

1. **A token-lean codemap.** A script (`codemap.py`) parses your repo — PHP,
   Python, JS/TS, Go, Rust, Java, and C# out of the box, more languages via
   drop-in adapters, exact tree-sitter parsing when installed — into a
   compact symbol map with reference counts. Your agent reads ~4k tokens of map
   instead of grepping half the repo. Cheaper tokens, and it *finds the code
   you already have.*
2. **A doctrine with teeth.** The extension ladder (change a value → add a
   parameter → extend a method → … → new file *only with a stated
   justification*), a reuse gate before any code gets written, a subtraction
   pass while it's in there, and a scoreboard (`diffstat.py`) after every
   change: net LOC, files touched, new/removed symbols. Negative is the high
   score.

## Install

### Claude Code (recommended)

```
/plugin marketplace add parkktech/shrinkage
/plugin install srk@parkktech
```

That's it. You get the `shrinkage` skill (auto-triggers on coding tasks) and
the commands: `/srk:onboard`, `/srk:map`, `/srk:query`, `/srk:gate`,
`/srk:score`, `/srk:trend`, `/srk:shave`, `/srk:audit`, `/srk:config`.

Then, in any repo: `/srk:onboard` (builds the codemap and captures your
preferences — including whether the tools are allowed to be funny).

**Updating:** new versions arrive when `plugin.json`'s version bumps; refresh
manually with `/plugin marketplace update parkktech`.

**Optional, for exact parsing** (regex fallback works without it):

```bash
pip install tree-sitter tree-sitter-javascript tree-sitter-typescript tree-sitter-php
```

### Team repos (zero-command install for collaborators)

Installation is per machine, not per repo — but you can make a repo hand the
plugin to everyone who opens it. Commit this as `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "parkktech": {
      "source": { "source": "github", "repo": "parkktech/shrinkage" }
    }
  },
  "enabledPlugins": {
    "srk@parkktech": true
  }
}
```

Collaborators who open the repo in Claude Code get the marketplace registered
and the plugin enabled automatically. (Private plugin repo → installs work
only for people with read access to it.)

### Standalone (no plugin system, shortest command names)

Clone into your user config and copy the commands — they surface un-namespaced
(`/map`, `/gate`, ...) or rename them to taste:

```bash
git clone https://github.com/parkktech/shrinkage.git ~/.claude/plugins-src/shrinkage
cp -r ~/.claude/plugins-src/shrinkage/skills/shrinkage ~/.claude/skills/
cp ~/.claude/plugins-src/shrinkage/commands/*.md ~/.claude/commands/
```

Update with `git pull` + re-copy.

### GitHub Copilot

See [`skills/shrinkage/adapters/copilot/`](skills/shrinkage/adapters/copilot/) —
repo-level instructions plus `.prompt.md` files that surface as `/srk-*` slash
commands in VS Code, Visual Studio, and JetBrains.

### GSD projects

Nothing extra: with the plugin installed, any repo with `.planning/` is
detected automatically — the codemap lands in `.planning/intel/`, syncs into
GSD's `api-map.json`, and planners/executors/verifiers pick up the rules via
GSD's project-skills discovery.

## Quickstart

```bash
/srk:onboard      # one-time setup in a repo: map + preferences
/srk:map          # build the codemap, see detected languages
/srk:gate "add csv export to reports"   # what should we EXTEND?
# ...implement...
/srk:score        # moment of truth
```

## Commands

| Command | What it does |
|---|---|
| `/srk:onboard` | one-shot setup: builds the map, captures every preference |
| `/srk:map` | build/refresh the codemap; names the language rules to load |
| `/srk:query <term>` | find existing symbols at map cost, not grep cost |
| `/srk:gate <task>` | reuse gate: candidates → extend-or-justify → minimal diff |
| `/srk:score [--pr]` | the scoreboard; `--pr` emits a block for your PR description |
| `/srk:trend` | cumulative weight over time + your current shrink streak |
| `/srk:shave [target]` | subtraction pass — hunt code the repo no longer needs |
| `/srk:audit [dir]` | repo-wide shrink opportunities, ranked by payoff |
| `/srk:config` | all settings: gate, map policy, PR scoreboard, budget, comedy |

CI bonus: `references/ci-integration.md` has a pre-commit hook and a GitHub
Action that posts the scoreboard as a sticky PR comment.

## It will not break your stuff (the Zeroth Law)

Shrinking is what it does; **backwards compatibility is what it is.** The
safety model (`references/safety-model.md`) governs every removal: risk tiers
that cap autonomy, a five-link evidence chain before anything dies (map refs →
repo-wide grep → the language's dynamic-reference checklist → test evidence →
git history), one atomic revertible commit per transform, characterization
tests before touching uncovered code, and a deprecation cycle for anything on
the public surface — because "probably dead" gets measured, not guessed.
Every reduction is a named entry in the consolidation catalog (C1–C10), each
with its known gotchas that the adversarial verifier checks specifically.
A reduction that breaks behavior isn't shrinkage; it's an amputation.

## Plays nice with GSD

If you run [GSD](https://github.com/open-gsd/gsd-core), Shrinkage slots
straight into the phase loop: the map lands in `.planning/intel/` and syncs
into `api-map.json` (upgrading GSD's symbol grounding to every language
Shrinkage parses, not just JS), planners apply the reuse gate, executors follow
the ladder, verifiers check the scoreboard, and GSD's project-skills discovery
picks up the per-language `rules/*.md` automatically. Fresh-context subagents
are exactly where a 4k-token map beats re-exploring the repo — which in GSD is
every single one of them.

## The one thing we let grow

Language support. Adding one is two files, no core changes:
`scripts/parsers/<lang>.py` (regexes + the shared brace scanner; the PHP
adapter is 40 lines) and `rules/<lang>.md` (that language's minimalism idioms).
Detection, mapping, ranking, diffstat, and GSD intel sync pick it up
automatically.

## FAQ

**Is a negative diff really the goal?**
The goal is the feature. A negative diff is the feature *plus* proof you
understood the codebase well enough to not duplicate it.

**My diff came out +400 lines. Should I panic?**
Sometimes code has to grow — new domains exist. The scoreboard doesn't forbid
growth; it makes growth *cost something to claim*. If the +400 survived the
reuse gate and the ladder justifications, own it proudly.

**Can I say "shrinkage" in the sprint review?**
You can, and someone will smile, and that's the correct amount of morale for
one word. If your workplace is fancier than that, tell them it's named after
what happens to the token bill.

---

*Shrinkage: because being a grower isn't always a good thing.*
