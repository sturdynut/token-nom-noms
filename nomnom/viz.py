from __future__ import annotations

import json
import os
import shutil
import sys
import time

CLEAR = "\x1b[2J\x1b[H"
RESET = "\x1b[0m"
GREEN, RED, YELLOW, DIM, BOLD, CYAN, MAGENTA = "\x1b[32m", "\x1b[31m", "\x1b[33m", "\x1b[2m", "\x1b[1m", "\x1b[36m", "\x1b[35m"
SOURCE_COLOR = {"reflex": GREEN, "model": CYAN, "idle": RED}


def absolute_state(entry: dict) -> dict:
    """Post-step state for a tick entry, deriving it from the pre-step observation for old logs."""
    if entry.get("state"):
        return entry["state"]
    o = entry["obs"]
    px, py = o["pos"]
    preds = o.get("predators") if o.get("predators") is not None else ([o["predator"]] if o.get("predator") else [])
    return {
        "pos": [px, py],
        "predator": [px + o["predator"][0], py + o["predator"][1]] if o.get("predator") else None,
        "predators": [[px + p[0], py + p[1]] for p in preds],
        "food": [[px + f[0], py + f[1]] for f in o.get("food", [])],
        "energy": entry["energy_after"],
        "alive": entry["alive"],
    }


def bar(value, total, width=20, color=GREEN):
    total = max(total, 1)
    filled = int(round(width * max(0, min(value, total)) / total))
    return color + "█" * filled + DIM + "░" * (width - filled) + RESET


def render_frame(entry: dict, cfg: dict, run_label: str, calls: list, trail: list = None) -> str:
    st = absolute_state(entry)
    size = cfg.get("size", 10)
    max_energy = cfg.get("max_energy", 30)
    budget = cfg.get("budget", 0)
    ticks = cfg.get("ticks", 0)
    food = {tuple(f) for f in st["food"]}
    preds = {tuple(p) for p in (st.get("predators") or ([st["predator"]] if st.get("predator") else []))}
    pos = tuple(st["pos"])
    trail = {tuple(p) for p in (trail or [])}

    lines = [CLEAR + BOLD + "token-nom-noms" + RESET + "  " + DIM + run_label + RESET,
             "tick %d/%d   %s" % (entry["tick"], ticks, (RED + BOLD + "DEAD: " + ", ".join(e for e in entry["events"] if e.isupper()) + RESET) if not st["alive"] else "")]
    for y in range(size):
        row = []
        for x in range(size):
            c = (x, y)
            if c == pos:
                row.append((GREEN if st["alive"] else RED) + BOLD + "@" + RESET)
            elif c in preds:
                row.append(RED + BOLD + "P" + RESET)
            elif c in food:
                row.append(YELLOW + "*" + RESET)
            elif c in trail:
                row.append(DIM + "·" + RESET)
            else:
                row.append(DIM + "." + RESET)
        lines.append(" ".join(row))
    src = entry["source"].split("_")[0]
    color = SOURCE_COLOR.get(src, CYAN)
    lines.append("")
    lines.append("energy  %s %2d/%d" % (bar(st["energy"], max_energy), st["energy"], max_energy))
    lines.append("budget  %s %d/%d" % (bar(entry["budget_after"], budget, color=CYAN), entry["budget_after"], budget))
    lines.append("source  %s%-11s%s action %s%-4s%s cost %d   reflex v%d" % (
        color, entry["source"], RESET, BOLD, entry["action"], RESET, entry["tick_cost"], entry.get("reflex_version", 0)))
    lines.append("events  " + ", ".join(entry["events"]) if entry["events"] else "events  -")
    if entry.get("drift"):
        lines.append(YELLOW + BOLD + "WORLD SHIFTED: " + entry["drift"] + RESET)
    notes = (entry.get("notes") or "").strip().replace("\n", " ")
    if notes:
        lines.append("notes   " + DIM + notes[:200] + RESET)
    for c in calls:
        if c["kind"] == "think":
            lines.append(MAGENTA + "self-prompt " + RESET + c["prompt"].strip().replace("\n", " ")[:160])
            lines.append(MAGENTA + "reply       " + RESET + (c.get("response") or "").strip().replace("\n", " ")[:160])
        elif c["kind"] == "report":
            lines.append(YELLOW + "report      " + RESET + (c.get("response") or "").strip().replace("\n", " ")[:200])
    return "\n".join(lines)


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def watch(run_dir: str, fps: float = 4.0, pause_on_calls: bool = True):
    """Animate a finished run in the terminal."""
    cfg = json.load(open(os.path.join(run_dir, "config.json")))["config"]
    ticks = _load(os.path.join(run_dir, "ticks.jsonl"))
    calls = _load(os.path.join(run_dir, "calls.jsonl"))
    by_tick = {}
    for c in calls:
        by_tick.setdefault(c["tick"], []).append(c)
    trail = []
    delay = 1.0 / max(fps, 0.1)
    try:
        for entry in ticks:
            these = by_tick.get(entry["tick"], [])
            sys.stdout.write(render_frame(entry, cfg, os.path.basename(run_dir.rstrip("/")), these, trail) + "\n")
            sys.stdout.flush()
            trail.append(absolute_state(entry)["pos"])
            trail[:] = trail[-8:]
            time.sleep(delay * (3 if (pause_on_calls and these) else 1))
    except KeyboardInterrupt:
        pass
    summary_path = os.path.join(run_dir, "summary.json")
    if os.path.exists(summary_path):
        s = json.load(open(summary_path))
        print("\n%s after %d/%d ticks | ate %d | spent %d/%d tokens in %d calls | reflex ticks %d | self-prompts %d" % (
            "alive" if s["alive"] else s["cause_of_death"], s["survived_ticks"], s["max_ticks"], s["food_eaten"],
            s["tokens_spent"], s["budget"], s["model_calls"], s["reflex_ticks"], s["think_calls"]))
