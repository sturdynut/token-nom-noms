# Contributing

There are four ways in. Pick the lightest one that interests you.

## 1. Watch

Open the replay page at https://sturdynut.com/token-nom-noms/ and scrub through
the runs. No install needed. The same page is `docs/index.html` in the repo.

## 2. Run your agent and submit the run

You need Python 3.9+ and a working agent CLI on your machine: Claude Code, Codex, or
Ollama. Nothing in this repo holds credentials; the harness shells out to your CLI.

```
git clone <your fork>
python3 -m nomnom run --runtime claude --model haiku --seed 1 --by "<your handle>"
python3 -m nomnom validate          # replays your run from the seed and checks the summary
python3 -m nomnom leaderboard       # refreshes runs/README.md
```

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
- **A drift kind** in `nomnom/world.py`, a new way for a reflex to go stale.
- **An analysis** over the JSONL logs. Ideas: claimed versus observed savings per
  report, prompt length over time, ticks between a drift and the agent's next re-think.

## 4. Discuss what the agents did

Open a discussion or issue titled with the finding and link the run. Two to start
from: a creature that wrote a one-line reflex that never moved and starved with most
of its budget unspent, and a creature whose strategy reports cost more than all of its
decisions combined.

## What the checks enforce

The `validate` command, run in CI on every PR, checks that each run folder is complete,
that the summary matches the logs, that the world replays deterministically from the
seed and the logged actions, and that no mock runs are included. Token counts come from
your runtime and cannot be verified here; the logs are the evidence.
