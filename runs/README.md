# Runs

Every run committed here is one creature's life: its logs, its reports, its reflex, and how it spent its tokens.
Benchmark runs (seeds 1-5, default rules with drift) rank first, by ticks survived then tokens per tick.
Runs made before world drift existed, or on other settings, are listed below them. Regenerate with `python3 -m nomnom leaderboard`.

| bench | survived | outcome | runtime | model | by | drift | tokens spent | tokens/tick | food | model calls | reflex ticks | self-prompts | $ | run |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| yes | 50/50 | alive | claude | haiku | Matti Salokangas | every 15 | 47,519 | 950.4 | 15 | 7 | 48 | 0 | 0.203 | [20260910-094034-claude-haiku-seed3](20260910-094034-claude-haiku-seed3/) |
| yes | 20/50 | starved | ollama | qwen2.5:7b | Matti Salokangas | every 15 | 11,106 | 555.3 | 0 | 17 | 16 | 6 | 0.000 | [20260910-094037-ollama-qwen2.5_7b-seed3](20260910-094037-ollama-qwen2.5_7b-seed3/) |
|  | 44/50 | eaten by predator | claude | haiku |  | none | 42,759 | 971.8 | 14 | 5 | 43 | 0 | 0.193 | [20260910-091216-claude-haiku-seed1](20260910-091216-claude-haiku-seed1/) |
|  | 20/50 | starved | ollama | llama3.2 |  | none | 41,312 | 2065.6 | 0 | 56 | 0 | 24 | 0.000 | [20260910-091219-ollama-llama3.2-seed1](20260910-091219-ollama-llama3.2-seed1/) |

## What each run folder holds

- `calls.jsonl`: every model call verbatim (prompt, response, tokens, charge, budget before/after)
- `ticks.jsonl`: one line per tick (state, who decided, action, events, cost)
- `reports.jsonl`: the agent's own account of its token strategy
- `creature/reflex.py`, `creature/notes.md`: what the agent wrote for itself, every version kept
- `summary.json`: the row above
