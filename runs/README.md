# Runs

Every run here is one creature's life: its logs, its reports, its reflex, and how it
spent its tokens. Regenerate this file with `python3 -m nomnom leaderboard`.

**How to read it.** Runs are grouped by seed, because seeds differ enormously in
difficulty and ranking across them compares nothing. The column that matters is
**vs free**, which is how many more ticks a run survived than the zero-token
hand-written reflex on the same seed. **Earned** is tokens won back by foraging with
a colony of two or more, and **colony** is the peak number of bodies alive at once
with the number of spawns paid for.

## The free baseline

`--runtime baseline` installs one hand-written greedy reflex, spends nothing, and
never calls a model. This is the score every paid run has to beat.

| seed | survived | outcome | vs free | runtime | model | by | tokens spent | earned | colony | food | model calls | reflex ticks | $ | run |
| ---: | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 43/50 | starved |  | baseline | greedy | reference | 0 | — | — | 3 | 6 | 41 | 0.000 | [20260913-103807-baseline-greedy-seed1](20260913-103807-baseline-greedy-seed1/) |
| 2 | 34/50 | eaten by predator |  | baseline | greedy | reference | 0 | — | — | 7 | 4 | 33 | 0.000 | [20260913-103808-baseline-greedy-seed2](20260913-103808-baseline-greedy-seed2/) |
| 3 | 50/50 | alive |  | baseline | greedy | reference | 0 | — | — | 10 | 5 | 49 | 0.000 | [20260913-103809-baseline-greedy-seed3](20260913-103809-baseline-greedy-seed3/) |
| 4 | 18/50 | eaten by predator |  | baseline | greedy | reference | 0 | — | — | 6 | 2 | 17 | 0.000 | [20260913-103810-baseline-greedy-seed4](20260913-103810-baseline-greedy-seed4/) |
| 5 | 18/50 | eaten by predator |  | baseline | greedy | reference | 0 | — | — | 2 | 2 | 17 | 0.000 | [20260913-103810-baseline-greedy-seed5](20260913-103810-baseline-greedy-seed5/) |

## Benchmark runs

Seeds 1-5 on the default rules: 40,000 tokens, 50 ticks, drift every 15, terrain 0.12,
spawning on at 2,000 tokens a body.

| seed | survived | outcome | vs free | runtime | model | by | tokens spent | earned | colony | food | model calls | reflex ticks | $ | run |
| ---: | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 50/50 | alive | +7 | claude | fable | Matti Salokangas | 34,667 | 8,000 | 3 (5 spawns) | 21 | 9 | 45 | 0.663 | [20260913-201341-claude-fable-seed1](20260913-201341-claude-fable-seed1/) |
| 3 | 50/50 | alive | same | claude | fable | Matti Salokangas | 35,540 | 6,400 | 3 (3 spawns) | 17 | 11 | 43 | 0.811 | [20260914-130355-claude-fable-seed3](20260914-130355-claude-fable-seed3/) |

## Other runs

Different settings, or recorded under an older ruleset. Not comparable to the
benchmark rows above.

| seed | survived | outcome | vs free | runtime | model | by | tokens spent | earned | colony | food | model calls | reflex ticks | $ | run |
| ---: | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 50/50 | alive | +7 | claude | fable | Matti Salokangas | 15,793 | — | — | 16 | 5 | 49 | 0.445 | [20260913-143711-claude-fable-seed1](20260913-143711-claude-fable-seed1/) |
| 1 | 50/50 | alive | +7 | claude | opus | Matti Salokangas | 18,621 | — | — | 13 | 5 | 49 | 0.277 | [20260913-143711-claude-opus-seed1](20260913-143711-claude-opus-seed1/) |
| 1 | 50/50 | alive | +7 | claude | sonnet | Matti Salokangas | 30,259 | — | — | 10 | 7 | 47 | 0.222 | [20260913-143711-claude-sonnet-seed1](20260913-143711-claude-sonnet-seed1/) |
| 1 | 50/50 | alive | +7 | codex | gpt-5.6-terra | Matti Salokangas | 32,972 | — | — | 10 | 6 | 48 | 0.000 | [20260913-145056-codex-gpt-5.6-terra-seed1](20260913-145056-codex-gpt-5.6-terra-seed1/) |
| 1 | 50/50 | alive | +7 | codex | gpt-5.6-sol | Matti Salokangas | 40,163 (+163 over) | — | — | 11 | 5 | 49 | 0.000 | [20260913-145056-codex-gpt-5.6-sol-seed1](20260913-145056-codex-gpt-5.6-sol-seed1/) |
| 1 | 50/50 | alive | +7 | codex | gpt-5.6-luna | Matti Salokangas | 46,124 (+6,124 over) | — | — | 11 | 4 | 49 | 0.000 | [20260913-145056-codex-gpt-5.6-luna-seed1](20260913-145056-codex-gpt-5.6-luna-seed1/) |
| 1 | 50/50 | alive | +7 | codex | gpt-6-astra | Matti Salokangas | 46,151 (+6,151 over) | — | — | 9 | 4 | 49 | 0.000 | [20260913-145056-codex-gpt-6-astra-seed1](20260913-145056-codex-gpt-6-astra-seed1/) |
| 3 | 50/50 | alive | same | claude | haiku (low effort) | Matti Salokangas | 47,519 | — | — | 15 | 7 | 48 | 0.203 | [20260910-094034-claude-haiku-seed3](20260910-094034-claude-haiku-seed3/) |
| 1 | 44/50 | eaten by predator |  | claude | haiku |  | 42,759 | — | — | 14 | 5 | 43 | 0.193 | [20260910-091216-claude-haiku-seed1](20260910-091216-claude-haiku-seed1/) |
| 3 | 20/50 | starved | -30 | ollama | qwen2.5:7b | Matti Salokangas | 11,106 | — | — | 0 | 17 | 16 | 0.000 | [20260910-094037-ollama-qwen2.5_7b-seed3](20260910-094037-ollama-qwen2.5_7b-seed3/) |
| 1 | 20/50 | starved |  | ollama | llama3.2 |  | 41,312 | — | — | 0 | 56 | 0 | 0.000 | [20260910-091219-ollama-llama3.2-seed1](20260910-091219-ollama-llama3.2-seed1/) |
| 1 | 16/50 | eaten by predator | -27 | claude | haiku (low effort) | Matti Salokangas | 41,564 (+1,564 over) | — | — | 1 | 6 | 0 | 0.169 | [20260913-125018-claude-haiku-seed1](20260913-125018-claude-haiku-seed1/) |
| 1 | 8/50 | eaten by predator | -35 | claude | haiku | Matti Salokangas | 9,268 | — | — | 2 | 1 | 7 | 0.040 | [20260913-143711-claude-haiku-seed1](20260913-143711-claude-haiku-seed1/) |

## What each run folder holds

- `calls.jsonl`: every model call verbatim (prompt, response, tokens, charge, budget before/after)
- `ticks.jsonl`: one line per tick (state, who decided, action, events, cost)
- `reports.jsonl`: the agent's own account of its token strategy
- `creature/reflex.py`, `creature/notes.md`: what the agent wrote for itself, every version kept
- `summary.json`: the row above, including any overdraft past the budget
