from __future__ import annotations

import json
import os


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def replay(run_dir: str, show_calls: bool = False, show_prompts: bool = False):
    cfg = json.load(open(os.path.join(run_dir, "config.json")))
    ticks = _load(os.path.join(run_dir, "ticks.jsonl"))
    calls = _load(os.path.join(run_dir, "calls.jsonl"))
    reports = _load(os.path.join(run_dir, "reports.jsonl"))
    summary_path = os.path.join(run_dir, "summary.json")
    summary = json.load(open(summary_path)) if os.path.exists(summary_path) else None

    c = cfg["config"]
    print("RUN %s" % run_dir)
    print("runtime=%s model=%s budget=%d ticks=%d seed=%d" % (
        cfg["runtime"], cfg["model"], c["budget"], c["ticks"], c["seed"]))
    print()

    calls_by_tick = {}
    for call in calls:
        calls_by_tick.setdefault(call["tick"], []).append(call)
    reports_by_tick = {r["tick"]: r for r in reports}

    for t in ticks:
        o = t["obs"]
        print("tick %2d | %-11s | %-4s | energy %2d | pos %s | pred %-9s | cost %5d | left %6d | %s" % (
            t["tick"], t["source"], t["action"], t["energy_after"], o["pos"], str(o["predator"]),
            t["tick_cost"], t["budget_after"], ", ".join(t["events"])))
        if t.get("reflex_error"):
            print("        reflex error: %s" % t["reflex_error"])
        for call in calls_by_tick.get(t["tick"], []):
            if call["kind"] == "think":
                print("        SELF-PROMPT: %s" % call["prompt"].strip().replace("\n", " ")[:300])
                print("        REPLY:       %s" % (call["response"] or "").strip().replace("\n", " ")[:300])
            if show_calls and call["kind"] == "tick":
                print("        MODEL REPLY: %s" % (call["response"] or "").strip().replace("\n", " ")[:400])
            if show_prompts:
                print("        ---- %s prompt (%d in / %d out, charged %d) ----" % (
                    call["kind"], call["input_tokens"], call["output_tokens"], call["charged"]))
                print("        " + call["prompt"].replace("\n", "\n        "))
                print("        ---- response ----")
                print("        " + (call["response"] or "").replace("\n", "\n        "))
        if t["tick"] in reports_by_tick:
            r = reports_by_tick[t["tick"]]
            print("        REPORT: %s" % json.dumps(r["report"]) if r.get("report") else "        REPORT (unparsed): %s" % (r.get("raw") or r.get("error")))

    print()
    if summary:
        print("RESULT: %s after %d/%d ticks | ate %d | spent %d/%d tokens in %d calls | model ticks %d, reflex ticks %d, idle %d | self-prompts %d | $%.4f" % (
            "alive" if summary["alive"] else summary["cause_of_death"], summary["survived_ticks"], summary["max_ticks"],
            summary["food_eaten"], summary["tokens_spent"], summary["budget"], summary["model_calls"],
            summary["model_ticks"], summary["reflex_ticks"], summary["idle_ticks"], summary["think_calls"], summary["cost_usd"]))
    reflex_path = os.path.join(run_dir, "creature", "reflex.py")
    if os.path.exists(reflex_path):
        print()
        print("FINAL REFLEX (creature/reflex.py):")
        print(open(reflex_path).read())
    notes_path = os.path.join(run_dir, "creature", "notes.md")
    if os.path.exists(notes_path):
        print("FINAL NOTES (creature/notes.md):")
        print(open(notes_path).read())
