# Runs

Every run here is one creature's life: its logs, its reports, its reflex, and how it
spent its tokens. Regenerate this file with `python3 -m nomnom leaderboard`.

**How to read it.** Runs are grouped by seed, because seeds differ enormously in
difficulty and ranking across them compares nothing. Tokens per tick is not a score:
a creature that dies early on a small spend looks efficient and played badly. The
column that matters is **vs free**, which is how many more ticks a run survived than
the zero-token hand-written reflex on the same seed.

## The free baseline

`--runtime baseline` installs one hand-written greedy reflex, spends nothing, and
never calls a model. This is the score every paid run has to beat.

| seed | survived | outcome | vs free | runtime | model | by | tokens spent | tokens/tick | food | model calls | reflex ticks | self-prompts | $ | run |
| ---: | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 43/50 | starved |  | baseline | greedy | reference | 0 | 0.0 | 3 | 6 | 41 | 0 | 0.000 | [20260913-103807-baseline-greedy-seed1](20260913-103807-baseline-greedy-seed1/) |
| 2 | 34/50 | eaten by predator |  | baseline | greedy | reference | 0 | 0.0 | 7 | 4 | 33 | 0 | 0.000 | [20260913-103808-baseline-greedy-seed2](20260913-103808-baseline-greedy-seed2/) |
| 3 | 50/50 | alive |  | baseline | greedy | reference | 0 | 0.0 | 10 | 5 | 49 | 0 | 0.000 | [20260913-103809-baseline-greedy-seed3](20260913-103809-baseline-greedy-seed3/) |
| 4 | 18/50 | eaten by predator |  | baseline | greedy | reference | 0 | 0.0 | 6 | 2 | 17 | 0 | 0.000 | [20260913-103810-baseline-greedy-seed4](20260913-103810-baseline-greedy-seed4/) |
| 5 | 18/50 | eaten by predator |  | baseline | greedy | reference | 0 | 0.0 | 2 | 2 | 17 | 0 | 0.000 | [20260913-103810-baseline-greedy-seed5](20260913-103810-baseline-greedy-seed5/) |

## Benchmark runs

Seeds 1-5 on the default rules: 40,000 tokens, 50 ticks, drift every 15, terrain 0.12.

| seed | survived | outcome | vs free | runtime | model | by | tokens spent | tokens/tick | food | model calls | reflex ticks | self-prompts | $ | run |
| ---: | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 16/50 | eaten by predator | -27 | claude | haiku | Matti Salokangas | 41,564 (+1,564 over) | 2597.8 | 1 | 6 | 0 | 0 | 0.169 | [20260913-125018-claude-haiku-seed1](20260913-125018-claude-haiku-seed1/) |

## Other runs

Different settings, or recorded under an older ruleset. Not comparable to the
benchmark rows above.

| seed | survived | outcome | vs free | runtime | model | by | tokens spent | tokens/tick | food | model calls | reflex ticks | self-prompts | $ | run |
| ---: | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3 | 50/50 | alive | same | claude | haiku | Matti Salokangas | 47,519 | 950.4 | 15 | 7 | 48 | 0 | 0.203 | [20260910-094034-claude-haiku-seed3](20260910-094034-claude-haiku-seed3/) |
| 1 | 44/50 | eaten by predator |  | claude | haiku |  | 42,759 | 971.8 | 14 | 5 | 43 | 0 | 0.193 | [20260910-091216-claude-haiku-seed1](20260910-091216-claude-haiku-seed1/) |
| 3 | 20/50 | starved | -30 | ollama | qwen2.5:7b | Matti Salokangas | 11,106 | 555.3 | 0 | 17 | 16 | 6 | 0.000 | [20260910-094037-ollama-qwen2.5_7b-seed3](20260910-094037-ollama-qwen2.5_7b-seed3/) |
| 1 | 20/50 | starved |  | ollama | llama3.2 |  | 41,312 | 2065.6 | 0 | 56 | 0 | 24 | 0.000 | [20260910-091219-ollama-llama3.2-seed1](20260910-091219-ollama-llama3.2-seed1/) |

## What each run folder holds

- `calls.jsonl`: every model call verbatim (prompt, response, tokens, charge, budget before/after)
- `ticks.jsonl`: one line per tick (state, who decided, action, events, cost)
- `reports.jsonl`: the agent's own account of its token strategy
- `creature/reflex.py`, `creature/notes.md`: what the agent wrote for itself, every version kept
- `summary.json`: the row above, including any overdraft past the budget
