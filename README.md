# token-nom-noms

**Watch the runs:** https://sturdynut.github.io/token-nom-noms/

[![Claude haiku's creature at tick 31, running on its fourth reflex after two world shifts](docs/screenshot.png)](https://sturdynut.github.io/token-nom-noms/#run=2&tick=31)

A survival game where the creature's brain is an LLM agent, and every thought
costs tokens from a fixed budget. The agent can only act by prompting itself.
The point of the game is to survive. The point of the project is to harvest
the token-efficiency strategies the agents invent under scarcity.

## Milestone 1 (this version)

One agent, one creature, fifty ticks, and a log you can read end to end.

- A 10x10 grid with food, one slow predator, and hunger.
- Each tick the harness hands the agent its observation, its notes from last
  tick, and its remaining budget (always visible, always free).
- The agent replies with a JSON action. It may also:
  - write **notes** that it will receive next tick (its own context, its own cost),
  - install a **reflex**: Python `act(obs)` that runs every tick before the model
    at zero token cost, so a good reflex means the model is never called,
  - **think**: send a prompt to itself. The reply comes back and it is asked again.
    Self-prompts are paid calls, capped per tick.
- Every 10 ticks the agent files a short report on its token strategy. That call is paid too.
- **The world drifts.** Every 15 ticks one rule silently changes: predators speed up, food
  gets scarce, a second predator appears, or predators start camping food instead of
  chasing. The agent is told that shifts happen, never when or what. A reflex written at
  tick 1 goes stale, so the real decision is when a re-think is worth paying for.
- When the budget hits zero the model is never called again. Only the reflex keeps acting.

Every model call is logged verbatim: system prompt, prompt, response, token counts,
charge, and budget before and after. Self-reports are separate from telemetry, so
you can compare what the agent claims with what it actually spent.

## Watch it

```
python3 -m nomnom run --runtime claude --model haiku --watch     # live terminal view while it runs
python3 -m nomnom replay runs/<run-dir> --watch --fps 6           # animate a finished run in the terminal
python3 -m nomnom html runs/<run-dir> --open                      # standalone HTML5 canvas replay
python3 -m nomnom html runs/*/ -o docs/index.html                 # one page with every run, switchable
```

The canvas page shows the grid, energy and budget meters, the creature's notes and
self-prompts for the selected tick, and a per-tick spend strip that doubles as the
scrubber. Bar color is who decided (paid model call, free reflex, idle), bar height
is tokens charged. Both views read only the run logs, never the simulation.

## Community runs

`runs/` is committed. Each run folder is one creature's complete life, and
`runs/README.md` is the leaderboard built from every `summary.json`. To contribute:

1. Fork, then run your agent: `python3 -m nomnom run --runtime <claude|codex|ollama> --model <m> --by <your handle>`.
2. `python3 -m nomnom leaderboard` to refresh the table.
3. Open a PR with the new run folder. Keep the logs intact; the prompts and reports are the point.

Benchmark seeds are 1 through 5 on the default rules. `python3 -m nomnom validate` replays
every run from its seed and checks the summary, and CI runs it on each PR. See
`CONTRIBUTING.md` for the four ways to take part.

Compare within a runtime first. Cross-runtime token counts are not on the same scale.

## Run it

No dependencies beyond Python 3.9+.

```
python3 -m nomnom run --runtime mock                       # scripted brain, no LLM, for testing
python3 -m nomnom run --runtime claude --model haiku       # Claude Code in headless mode
python3 -m nomnom run --runtime ollama --model llama3.2    # local model via Ollama
python3 -m nomnom run --runtime codex                      # Codex CLI (adapter untested, see below)

python3 -m nomnom run --runtime claude --model haiku --budget 40000 --ticks 50 --seed 1
python3 -m nomnom replay runs/<run-dir>                    # readable transcript
python3 -m nomnom replay runs/<run-dir> --prompts          # every prompt and response in full
```

Each run writes to `runs/<timestamp>-<runtime>-<model>-seed<n>/`:

| file | contents |
| --- | --- |
| `calls.jsonl` | one line per model call: kind (tick/think/report), prompt, response, tokens, charge, budget |
| `ticks.jsonl` | one line per tick: observation, action source (model/reflex/idle), action, events, cost |
| `reports.jsonl` | the agent's strategy reports |
| `creature/notes.md` | the agent's current self-authored notes |
| `creature/reflex.py` | the agent's current reflex, plus every prior version |
| `summary.json` | survival, food, tokens, calls, reflex ticks, self-prompts, dollar cost, who ran it |
| `config.json` | full config and the exact rules text the agent saw |

## Token accounting

The charge for a call is `uncached input + output + cache writes + 0.1 * cache reads`,
rounded up. Raw counts are logged, so you can re-weight later. Claude Code's own
system prompt is replaced with the game rules and its tools, MCP servers and settings
are disabled, so its per-call overhead is roughly 440 tokens rather than 70k+.

Runtimes are not comparable on raw tokens: different tokenizers, different overheads,
and a local model is free at the margin. Treat each runtime as its own league.

## Runtimes

- **claude**: `claude -p --output-format json` with `--system-prompt`, `--tools ""`,
  and MCP/settings disabled. Usage comes from the JSON result. Thinking tokens are
  charged as output and logged separately; pass `--effort low` to curb them.
- **ollama**: `POST /api/generate`. Usage from `prompt_eval_count` and `eval_count`.
  `<think>` blocks are stripped from the reply but their tokens are still charged.
- **codex**: `codex exec --json`. Parses `item.completed` agent messages and the
  `turn.completed` usage event. Written from the documented format but not verified
  on this machine, because the installed Codex CLI needs an upgrade for its configured model.
- **mock**: a scripted greedy brain that exercises notes, think, reflex and reports
  without spending anything.

## Next

- Token income from eating so burn rate versus investment becomes a real economy.
- Evolution stages gated on survival plus skills, not just age.
- Multiple creatures in one world, one per runtime.
- A summary tool across runs: tokens per surviving tick, prompt length over time,
  claimed versus observed savings per report.
