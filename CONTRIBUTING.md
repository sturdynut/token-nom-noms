# Contributing

There are four ways in. Pick the lightest one that interests you.

## 1. Watch

Open the replay page at https://sturdynut.github.io/token-nom-noms/ and scrub through
the runs. No install needed. The same page is `docs/index.html` in the repo.

## 2. Run your agent and submit the run

You need Python 3.9+ and a working agent CLI on your machine: Claude Code, Codex, or
Ollama. Nothing in this repo holds credentials; the harness shells out to your CLI.

```
git clone <your fork>
python3 -m nomnom run --runtime claude --model haiku --seed 1 --by "<your handle>"
python3 -m nomnom validate          # rebuilds the world from your seed and checks it against your log
python3 -m nomnom leaderboard       # refreshes runs/README.md
```

`--by` is opt-in. Without it nothing identifying is written to `summary.json`.

Before you spend anything, see what free scores on your seed:

```
python3 -m nomnom run --runtime baseline --seed 1
```

That is a hand-written greedy reflex costing zero tokens. It survives one of the five
benchmark seeds, because rocks break the straight-line heuristic it relies on. If your paid run does not beat it on the same seed, that is the
interesting result, and the leaderboard's **vs free** column will show it.

You do not need to regenerate `docs/index.html`. It is a build artifact, refreshed on
main by CI, and marked generated so it stays out of your diff.

Then open a PR with the new `runs/<run>/` folder and the updated `runs/README.md`.
Keep every file in the run folder intact. The prompts, replies, notes, reflex versions
and reports are the point of the project. Do not edit them.

Benchmark seeds are **1 through 5** on the default rules (40,000 tokens, 50 ticks,
drift every 15). Runs on other settings are welcome; they are shown but not ranked
against benchmark runs.

## 3. Extend the game

Each of these is one file:

- **A runtime adapter** in `nomnom/runtimes.py`, so a new agent CLI can play. It needs
  to return the reply text and real token counts.
- **A drift kind** in `nomnom/world.py`, a new way for a reflex to go stale, or a new
  terrain feature alongside the rocks, pits and traps.
- **An analysis** over the JSONL logs. Ideas: report cost as a share of budget, prompt
  length over time, ticks between a drift and the agent's next re-think, how often a
  crisis interrupt saved a creature.

## 4. Discuss what the agents did

Open a discussion or issue titled with the finding and link the run. Two to start
from: a creature that wrote a one-line reflex that never moved and starved with most
of its budget unspent, and a creature whose strategy reports cost more than all of its
decisions combined.

## Running someone else's run folder is not the risk; running the harness is

`nomnom run` executes Python that a language model wrote, in a subprocess on your
machine, with the full standard library and your permissions. There is no sandbox
beyond a two-second timeout. That is inherent to the game, since the reflex is the
point, but know it before you run an agent you have not watched.

Reviewing a submitted run folder is safe: `validate`, `leaderboard` and `html` only read
the logs, and none of them execute a contributed reflex.

## What the checks enforce

CI runs the unit tests and `validate` on every PR. `validate` checks that each run folder
is complete, that the summary matches the logs, that no mock runs are included, and that
the world rebuilt from the seed and the logged actions matches what was recorded.

Two honest limits. Runs in log format 1 predate the deterministic ordering of
equal-distance cells, so for those the replay verifies position, energy and life but not
cell order; `validate` prints a note saying so rather than passing them silently. And
token counts come from your runtime and cannot be verified here. The logs are the
evidence, which is why the rule about not editing them matters.
