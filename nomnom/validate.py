from __future__ import annotations

import glob
import json
import os

from .world import World

REQUIRED = ("config.json", "ticks.jsonl", "calls.jsonl", "summary.json")


def _load(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def validate_run(run_dir: str) -> list:
    """Return a list of problems. Empty means the run is internally consistent."""
    problems = []
    for name in REQUIRED:
        if not os.path.exists(os.path.join(run_dir, name)):
            problems.append("missing " + name)
    if problems:
        return problems
    cfg = json.load(open(os.path.join(run_dir, "config.json")))
    c = cfg["config"]
    ticks = _load(os.path.join(run_dir, "ticks.jsonl"))
    calls = _load(os.path.join(run_dir, "calls.jsonl"))
    summary = json.load(open(os.path.join(run_dir, "summary.json")))

    if cfg.get("runtime") == "mock":
        problems.append("mock runs do not belong in the shared runs folder")
    if not ticks:
        return problems + ["no ticks recorded"]
    if summary.get("survived_ticks") != len(ticks):
        problems.append("summary says %s ticks, log has %d" % (summary.get("survived_ticks"), len(ticks)))
    if bool(summary.get("alive")) != bool(ticks[-1]["alive"]):
        problems.append("summary alive flag disagrees with last tick")
    charged = sum(x.get("charged", 0) for x in calls)
    if summary.get("tokens_spent") != charged:
        problems.append("summary tokens_spent %s but calls add up to %d" % (summary.get("tokens_spent"), charged))
    if summary.get("model_calls") != len(calls):
        problems.append("summary model_calls %s but %d calls logged" % (summary.get("model_calls"), len(calls)))

    # Replay the world from the seed and the logged actions; the simulation is deterministic.
    w = World(seed=c["seed"], size=c["size"], start_energy=c["start_energy"], max_energy=c["max_energy"],
              food_value=c["food_value"], initial_food=c["initial_food"], food_every=c["food_every"],
              predator=c["predator"], predator_every=c["predator_every"], drift_every=c.get("drift_every", 0))
    for t in ticks:
        expected_obs = t.get("obs")
        if expected_obs:
            got = w.observe()
            for k in ("pos", "energy", "food", "predator"):
                if got.get(k) != expected_obs.get(k):
                    problems.append("tick %d: %s was %s in the log, replay gives %s" % (t["tick"], k, expected_obs.get(k), got.get(k)))
                    return problems
        w.step(t["action"])
        st = t.get("state")
        if st:
            got = w.state()
            for k in ("pos", "energy", "food", "alive"):
                if got.get(k) != st.get(k):
                    problems.append("tick %d: %s after step was %s in the log, replay gives %s" % (t["tick"], k, st.get(k), got.get(k)))
                    return problems
        if bool(w.alive) != bool(t["alive"]):
            problems.append("tick %d: log says alive=%s, replay says %s" % (t["tick"], t["alive"], w.alive))
            return problems
    return problems


def validate_all(runs_dir: str = "runs") -> int:
    dirs = sorted(d for d in glob.glob(os.path.join(runs_dir, "*")) if os.path.isdir(d))
    bad = 0
    for d in dirs:
        probs = validate_run(d)
        if probs:
            bad += 1
            print("FAIL %s" % d)
            for p in probs:
                print("     - " + p)
        else:
            print("ok   %s" % d)
    print("%d run(s), %d with problems" % (len(dirs), bad))
    return bad
