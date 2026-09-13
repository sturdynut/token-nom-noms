from __future__ import annotations

import glob
import json
import os

BENCHMARK_SEEDS = (1, 2, 3, 4, 5)


def collect(runs_dir: str) -> list:
    rows = []
    for path in sorted(glob.glob(os.path.join(runs_dir, "*", "summary.json"))):
        with open(path) as f:
            s = json.load(f)
        if s.get("runtime") == "mock":
            continue
        s["_dir"] = os.path.basename(os.path.dirname(path))
        cfg_path = os.path.join(os.path.dirname(path), "config.json")
        c = {}
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                c = json.load(f)["config"]
        s["_drift"] = c.get("drift_every", 0)
        s["_seed"] = c.get("seed")
        s["_reference"] = s.get("runtime") == "baseline"
        s["_benchmark"] = (not s["_reference"] and c.get("seed") in BENCHMARK_SEEDS
                           and c.get("budget") == 40000 and c.get("ticks") == 50 and s["_drift"] == 15)
        # Tokens per tick is only meaningful next to the outcome it bought: a creature
        # that dies early on a small spend scores well on it and badly at the game.
        s["_per_tick"] = round(s["tokens_spent"] / max(1, s["survived_ticks"]), 1)
        rows.append(s)
    return rows


def _row(r, baseline=None):
    spend = format(r["tokens_spent"], ",")
    if r.get("overdraft"):
        spend += " (+%s over)" % format(r["overdraft"], ",")
    beat = ""
    if baseline is not None:
        d = r["survived_ticks"] - baseline["survived_ticks"]
        beat = "same" if d == 0 else ("+%d" % d if d > 0 else str(d))
    return "| %s | %d/%d | %s | %s | %s | %s | %s | %s | %s | %d | %d | %d | %d | %.3f | [%s](%s) |" % (
        r["_seed"], r["survived_ticks"], r["max_ticks"], "alive" if r["alive"] else r["cause_of_death"],
        beat, r["runtime"], r.get("model") or "", r.get("by") or "", spend, r["_per_tick"],
        r["food_eaten"], r["model_calls"], r["reflex_ticks"], r.get("think_calls", 0),
        r.get("cost_usd") or 0, r["_dir"], r["_dir"] + "/")


HEAD = ("| seed | survived | outcome | vs free | runtime | model | by | tokens spent | tokens/tick | "
        "food | model calls | reflex ticks | self-prompts | $ | run |")
RULE = "| ---: | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"


def write_leaderboard(runs_dir: str = "runs") -> str:
    rows = collect(runs_dir)
    refs = {r["_seed"]: r for r in rows if r["_reference"]}
    bench = sorted((r for r in rows if r["_benchmark"]), key=lambda r: (r["_seed"], -r["survived_ticks"]))
    other = sorted((r for r in rows if not r["_benchmark"] and not r["_reference"]),
                   key=lambda r: (-r["survived_ticks"], r["_per_tick"]))

    lines = [
        "# Runs",
        "",
        "Every run here is one creature's life: its logs, its reports, its reflex, and how it",
        "spent its tokens. Regenerate this file with `python3 -m nomnom leaderboard`.",
        "",
        "**How to read it.** Runs are grouped by seed, because seeds differ enormously in",
        "difficulty and ranking across them compares nothing. Tokens per tick is not a score:",
        "a creature that dies early on a small spend looks efficient and played badly. The",
        "column that matters is **vs free**, which is how many more ticks a run survived than",
        "the zero-token hand-written reflex on the same seed.",
        "",
        "## The free baseline",
        "",
        "`--runtime baseline` installs one hand-written greedy reflex, spends nothing, and",
        "never calls a model. This is the score every paid run has to beat.",
        "",
        HEAD, RULE,
    ]
    for seed in BENCHMARK_SEEDS:
        if seed in refs:
            lines.append(_row(refs[seed]))

    lines += ["", "## Benchmark runs", "",
              "Seeds 1-5 on the default rules: 40,000 tokens, 50 ticks, drift every 15.", "", HEAD, RULE]
    if bench:
        for r in bench:
            lines.append(_row(r, refs.get(r["_seed"])))
    else:
        lines.append("| | | no benchmark runs yet | | | | | | | | | | | | |")

    if other:
        lines += ["", "## Other runs", "",
                  "Different settings, or recorded before world drift existed. Not comparable to",
                  "the benchmark rows above.", "", HEAD, RULE]
        for r in other:
            lines.append(_row(r, refs.get(r["_seed"]) if r["_drift"] else None))

    lines += ["", "## What each run folder holds", "",
              "- `calls.jsonl`: every model call verbatim (prompt, response, tokens, charge, budget before/after)",
              "- `ticks.jsonl`: one line per tick (state, who decided, action, events, cost)",
              "- `reports.jsonl`: the agent's own account of its token strategy",
              "- `creature/reflex.py`, `creature/notes.md`: what the agent wrote for itself, every version kept",
              "- `summary.json`: the row above, including any overdraft past the budget", ""]
    out = os.path.join(runs_dir, "README.md")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    return out
