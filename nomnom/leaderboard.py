from __future__ import annotations

import glob
import json
import os


def collect(runs_dir: str) -> list:
    rows = []
    for path in sorted(glob.glob(os.path.join(runs_dir, "*", "summary.json"))):
        s = json.load(open(path))
        if s.get("runtime") == "mock":
            continue
        s["_dir"] = os.path.basename(os.path.dirname(path))
        cfg_path = os.path.join(os.path.dirname(path), "config.json")
        c = json.load(open(cfg_path))["config"] if os.path.exists(cfg_path) else {}
        s["_drift"] = c.get("drift_every", 0)
        s["_benchmark"] = (c.get("seed") in (1, 2, 3, 4, 5) and c.get("budget") == 40000
                           and c.get("ticks") == 50 and s["_drift"] == 15)
        s["tokens_per_tick"] = round(s["tokens_spent"] / max(1, s["survived_ticks"]), 1)
        rows.append(s)
    rows.sort(key=lambda r: (not r["_benchmark"], -r["survived_ticks"], r["tokens_per_tick"]))
    return rows


def write_leaderboard(runs_dir: str = "runs") -> str:
    rows = collect(runs_dir)
    out = os.path.join(runs_dir, "README.md")
    lines = [
        "# Runs",
        "",
        "Every run committed here is one creature's life: its logs, its reports, its reflex, and how it spent its tokens.",
        "Benchmark runs (seeds 1-5, default rules with drift) rank first, by ticks survived then tokens per tick.",
        "Runs made before world drift existed, or on other settings, are listed below them. Regenerate with `python3 -m nomnom leaderboard`.",
        "",
        "| bench | survived | outcome | runtime | model | by | drift | tokens spent | tokens/tick | food | model calls | reflex ticks | self-prompts | $ | run |",
        "| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in rows:
        lines.append("| %s | %d/%d | %s | %s | %s | %s | %s | %s | %s | %d | %d | %d | %d | %.3f | [%s](%s) |" % (
            "yes" if r["_benchmark"] else "", r["survived_ticks"], r["max_ticks"], "alive" if r["alive"] else r["cause_of_death"],
            r["runtime"], r.get("model") or "", r.get("by") or "", ("every %d" % r["_drift"]) if r["_drift"] else "none",
            format(r["tokens_spent"], ","), r["tokens_per_tick"],
            r["food_eaten"], r["model_calls"], r["reflex_ticks"], r["think_calls"], r.get("cost_usd") or 0,
            r["_dir"], r["_dir"] + "/"))
    lines += ["", "## What each run folder holds", "",
              "- `calls.jsonl`: every model call verbatim (prompt, response, tokens, charge, budget before/after)",
              "- `ticks.jsonl`: one line per tick (state, who decided, action, events, cost)",
              "- `reports.jsonl`: the agent's own account of its token strategy",
              "- `creature/reflex.py`, `creature/notes.md`: what the agent wrote for itself, every version kept",
              "- `summary.json`: the row above", ""]
    with open(out, "w") as f:
        f.write("\n".join(lines))
    return out
