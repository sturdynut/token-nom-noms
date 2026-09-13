from __future__ import annotations

import glob
import json
import os

from .world import World

REQUIRED = ("config.json", "ticks.jsonl", "calls.jsonl", "summary.json")

# Cell lists are compared in order for format 2 and later. Format 1 runs were recorded
# before World.observe got a deterministic tie-break, so equal-distance cells came out in
# set-iteration order that this Python cannot reproduce. Ordering is load-bearing: agent
# reflexes pick with min(), which returns the first of a tie. Those runs are therefore
# replayed for position, energy and life only, and reported as partly unverified rather
# than quietly normalized into passing.
STRICT_ORDER_FORMAT = 2


def _load(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def _read_json(path):
    with open(path) as f:
        return json.load(f)


def _cells(v):
    if isinstance(v, list) and v and all(isinstance(x, list) for x in v):
        return sorted(tuple(x) for x in v)
    return v


def validate_run(run_dir: str):
    """Return (problems, notes). Empty problems means the run is internally consistent."""
    problems, notes = [], []
    for name in REQUIRED:
        if not os.path.exists(os.path.join(run_dir, name)):
            problems.append("missing " + name)
    if problems:
        return problems, notes
    cfg = _read_json(os.path.join(run_dir, "config.json"))
    c = cfg["config"]
    fmt = cfg.get("format", 1)
    strict = fmt >= STRICT_ORDER_FORMAT
    if not strict:
        notes.append("format %d: recorded before the deterministic ordering fix, so cell "
                     "order is not verified (position, energy and life are)" % fmt)
    ticks = _load(os.path.join(run_dir, "ticks.jsonl"))
    calls = _load(os.path.join(run_dir, "calls.jsonl"))
    summary = _read_json(os.path.join(run_dir, "summary.json"))

    if cfg.get("runtime") == "mock":
        problems.append("mock runs do not belong in the shared runs folder")
    if not ticks:
        return problems + ["no ticks recorded"], notes
    if summary.get("survived_ticks") != len(ticks):
        problems.append("summary says %s ticks, log has %d" % (summary.get("survived_ticks"), len(ticks)))
    if bool(summary.get("alive")) != bool(ticks[-1]["alive"]):
        problems.append("summary alive flag disagrees with last tick")
    charged = sum(x.get("charged", 0) for x in calls)
    if summary.get("tokens_spent") != charged:
        problems.append("summary tokens_spent %s but calls add up to %d" % (summary.get("tokens_spent"), charged))
    if summary.get("model_calls") != len(calls):
        problems.append("summary model_calls %s but %d calls logged" % (summary.get("model_calls"), len(calls)))
    if strict and summary.get("tokens_left") != c["budget"] - charged:
        problems.append("summary tokens_left %s should be budget minus spend (%d)"
                        % (summary.get("tokens_left"), c["budget"] - charged))
    if charged > c["budget"]:
        notes.append("overdrew the budget by %d tokens on its last call" % (charged - c["budget"]))

    # The simulation is deterministic, so the world can be rebuilt from the seed and the
    # logged actions. Anything that disagrees means the logs and this code are not the
    # same experiment.
    w = World(seed=c["seed"], size=c["size"], start_energy=c["start_energy"], max_energy=c["max_energy"],
              food_value=c["food_value"], initial_food=c["initial_food"], food_every=c["food_every"],
              predator=c["predator"], predator_every=c["predator_every"],
              drift_every=c.get("drift_every", 0), stage_growth=c.get("stage_growth", False),
              terrain_density=c.get("terrain_density", 0.0), pit_cost=c.get("pit_cost", 6),
              trap_cost=c.get("trap_cost", 8))
    norm = (lambda v: v) if strict else _cells
    for t in ticks:
        expected_obs = t.get("obs")
        if expected_obs:
            got = w.observe()
            for k in ("pos", "energy", "food", "predator", "rocks", "pits", "traps_known"):
                if k not in expected_obs:
                    continue  # the key postdates this run's log shape
                if norm(got.get(k)) != norm(expected_obs.get(k)):
                    problems.append("tick %d: %s was %s in the log, replay gives %s"
                                    % (t["tick"], k, expected_obs.get(k), got.get(k)))
                    return problems, notes
        w.step(t["action"])
        st = t.get("state")
        if st:
            got = w.state()
            for k in ("pos", "energy", "food", "alive"):
                if norm(got.get(k)) != norm(st.get(k)):
                    problems.append("tick %d: %s after step was %s in the log, replay gives %s"
                                    % (t["tick"], k, st.get(k), got.get(k)))
                    return problems, notes
        if bool(w.alive) != bool(t["alive"]):
            problems.append("tick %d: log says alive=%s, replay says %s" % (t["tick"], t["alive"], w.alive))
            return problems, notes
    return problems, notes


def validate_all(runs_dir: str = "runs") -> int:
    dirs = sorted(d for d in glob.glob(os.path.join(runs_dir, "*")) if os.path.isdir(d))
    bad = 0
    for d in dirs:
        problems, notes = validate_run(d)
        if problems:
            bad += 1
            print("FAIL %s" % d)
            for p in problems:
                print("     - " + p)
        else:
            print("ok   %s" % d)
        for n in notes:
            print("     note: " + n)
    print("%d run(s), %d with problems" % (len(dirs), bad))
    return bad
