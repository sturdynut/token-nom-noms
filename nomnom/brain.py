from __future__ import annotations

import json
import os
import re
import time

from .ledger import Ledger
from .prompts import THINK_SYSTEM, report_prompt, rules_text, tick_prompt
from .reflex import run_reflex
from .world import ACTIONS, World


# Bumped when a change to the world or the log shape makes older runs unreplayable by
# this code. Format 1 runs predate the deterministic tie-break in World.observe, so their
# logged cell ordering cannot be reproduced here; `validate` grandfathers them and says so.
LOG_FORMAT = 2


class Config:
    def __init__(self, **kw):
        self.runtime = "mock"
        self.model = None
        self.budget = 40000
        self.ticks = 50
        self.seed = 1
        self.size = 10
        self.start_energy = 20
        self.max_energy = 30
        self.food_value = 8
        self.initial_food = 4
        self.food_every = 2
        self.predator = True
        self.predator_every = 2
        self.drift_every = 15
        self.stage_growth = True
        self.crisis_energy = 5
        self.crisis_cooldown = 5
        self.max_think = 3
        self.report_every = 10
        self.timeout = 180
        self.out = "runs"
        self.quiet = False
        self.watch = False
        self.effort = None
        self.by = None
        for k, v in kw.items():
            if v is not None:
                setattr(self, k, v)

    def as_dict(self):
        return dict(self.__dict__)


def extract_json(text: str):
    """Find the first JSON object in a model reply. Tolerates code fences and chatter."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text)
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


class Creature:
    """Holds the agent-authored state that persists between ticks: notes and reflex."""

    def __init__(self, creature_dir: str):
        self.dir = creature_dir
        os.makedirs(creature_dir, exist_ok=True)
        self.notes = ""
        self.reflex_src = None
        self.reflex_version = 0
        self.reflex_last = "(none)"
        self.reflex_error = None

    def set_notes(self, notes: str):
        self.notes = notes
        with open(os.path.join(self.dir, "notes.md"), "w") as f:
            f.write(notes)

    def set_reflex(self, src, tick: int):
        if not src:
            self.reflex_src = None
            self.reflex_last = "(none)"
            return
        self.reflex_version += 1
        self.reflex_src = src
        self.reflex_error = None
        try:
            compile(src, "reflex.py", "exec")
        except SyntaxError as e:
            self.reflex_error = "SyntaxError: %s (line %s)" % (e.msg, e.lineno)
        path = os.path.join(self.dir, "reflex.py")
        with open(path, "w") as f:
            f.write(src)
        with open(os.path.join(self.dir, "reflex_v%d_tick%d.py" % (self.reflex_version, tick)), "w") as f:
            f.write(src)

    def status(self) -> str:
        if not self.reflex_src:
            return "(none)"
        s = "active (v%d, %d lines); last tick it returned %s" % (
            self.reflex_version, self.reflex_src.count("\n") + 1, self.reflex_last)
        if self.reflex_error:
            s += "\nERROR: " + self.reflex_error
        return s


class Game:
    def __init__(self, cfg: Config, runtime):
        self.cfg = cfg
        self.runtime = runtime
        self.last_calls = []
        self._last_tick_entry = None
        stamp = time.strftime("%Y%m%d-%H%M%S")
        model_tag = (runtime.model or runtime.name).replace("/", "_").replace(":", "_")
        self.run_dir = os.path.join(cfg.out, "%s-%s-%s-seed%d" % (stamp, runtime.name, model_tag, cfg.seed))
        os.makedirs(self.run_dir, exist_ok=True)
        self.world = World(
            seed=cfg.seed, size=cfg.size, start_energy=cfg.start_energy, max_energy=cfg.max_energy,
            food_value=cfg.food_value, initial_food=cfg.initial_food, food_every=cfg.food_every,
            predator=cfg.predator, predator_every=cfg.predator_every, drift_every=cfg.drift_every,
            stage_growth=cfg.stage_growth,
        )
        self.ledger = Ledger(cfg.budget, self.run_dir)
        self.creature = Creature(os.path.join(self.run_dir, "creature"))
        self.rules = rules_text(cfg)
        self._last_crisis = -10 ** 9
        self.stats = {"model_ticks": 0, "reflex_ticks": 0, "idle_ticks": 0, "crisis_calls": 0,
                      "think_calls": 0, "report_calls": 0, "parse_errors": 0, "call_errors": 0}
        with open(os.path.join(self.run_dir, "config.json"), "w") as f:
            json.dump({"format": LOG_FORMAT, "config": cfg.as_dict(), "runtime": runtime.name,
                       "model": runtime.model, "rules": self.rules}, f, indent=2)

    # ---- model plumbing ------------------------------------------------

    def last_tick_entry(self):
        return self._last_tick_entry

    def _call(self, kind: str, system: str, prompt: str, tick: int, depth: int = 0):
        res = self.runtime.call(system, prompt)
        charge = self.ledger.record_call(tick=tick, kind=kind, depth=depth, runtime=self.runtime.name,
                                         model=self.runtime.model or "", system=system, prompt=prompt, res=res)
        self.last_calls.append({"tick": tick, "kind": kind, "prompt": prompt, "response": res.text,
                                "charged": charge, "error": res.error})
        if res.error:
            self.stats["call_errors"] += 1
            self._say("  ! %s" % res.error)
        return res

    def _decide_with_model(self, obs: dict, tick: int):
        """Ask the agent for an action, servicing self-prompts along the way."""
        thoughts = []
        for depth in range(self.cfg.max_think + 1):
            prompt = tick_prompt(obs, self.ledger, self.creature.notes, thoughts, self.creature.status())
            res = self._call("tick", self.rules, prompt, tick, depth)
            if res.error:
                return "stay", "model_error"
            parsed = extract_json(res.text)
            if parsed is None:
                self.stats["parse_errors"] += 1
                self._say("  ! unparseable reply: %r" % res.text[:120])
                return "stay", "parse_error"
            if "notes" in parsed and isinstance(parsed["notes"], str):
                self.creature.set_notes(parsed["notes"])
            if "reflex" in parsed and isinstance(parsed["reflex"], str):
                had = bool(self.creature.reflex_src)
                self.creature.set_reflex(parsed["reflex"], tick)
                if parsed["reflex"]:
                    self._say("  reflex installed v%d%s" % (self.creature.reflex_version,
                              " (SYNTAX ERROR)" if self.creature.reflex_error else ""))
                elif had:
                    self._say("  reflex removed")
            think = parsed.get("think")
            if isinstance(think, str) and think.strip() and depth < self.cfg.max_think and self.ledger.remaining > 0:
                self.stats["think_calls"] += 1
                self._say("  self-prompt: %s" % think.strip().replace("\n", " ")[:100])
                r2 = self._call("think", THINK_SYSTEM, think, tick, depth + 1)
                thoughts.append((think, r2.text if not r2.error else "(error: %s)" % r2.error))
                if self.ledger.remaining <= 0:
                    return "stay", "budget_exhausted_mid_tick"
                continue
            action = parsed.get("action")
            if action in ACTIONS:
                return action, "model"
            return "stay", "model_bad_action"
        return "stay", "think_limit"

    def _report(self, obs: dict, tick: int):
        self.stats["report_calls"] += 1
        prompt = report_prompt(obs, self.ledger, self.creature.notes, tick, self.creature.reflex_src)
        res = self._call("report", self.rules, prompt, tick)
        parsed = extract_json(res.text) if not res.error else None
        if parsed:
            if isinstance(parsed.get("notes"), str):
                self.creature.set_notes(parsed["notes"])
            if isinstance(parsed.get("reflex"), str) and parsed["reflex"]:
                self.creature.set_reflex(parsed["reflex"], tick)
                self._say("  reflex installed v%d (from report)" % self.creature.reflex_version)
        self.ledger.record_report({"tick": tick, "budget_after": self.ledger.remaining,
                                   "report": parsed, "raw": res.text, "error": res.error})
        if parsed:
            self._say("  report: %s" % json.dumps(parsed)[:200])

    # ---- main loop -------------------------------------------------------

    def _say(self, msg: str):
        if not self.cfg.quiet:
            print(msg, flush=True)

    def run(self) -> dict:
        w = self.world
        self._say("run dir: %s" % self.run_dir)
        self._say("runtime=%s model=%s budget=%d ticks=%d seed=%d" % (
            self.runtime.name, self.runtime.model, self.cfg.budget, self.cfg.ticks, self.cfg.seed))
        for tick in range(1, self.cfg.ticks + 1):
            obs = w.observe()
            obs["tick"] = tick
            obs["budget"] = self.ledger.remaining
            budget_before = self.ledger.remaining
            action, source, reflex_err = None, "idle", None

            if self.creature.reflex_src and not self.creature.reflex_error:
                action, reflex_err = run_reflex(self.creature.reflex_src, obs)
                if reflex_err:
                    self.creature.reflex_error = reflex_err
                    self.creature.reflex_last = "ERROR"
                    action = None
                elif action in ACTIONS:
                    self.creature.reflex_last = repr(action)
                    source = "reflex"
                else:
                    self.creature.reflex_last = "None"
                    action = None

            # A reflex always returns an action, so a creature running one can starve with
            # its budget untouched: nothing in the loop ever forces a spend. When energy is
            # critical and a call is still affordable, override the reflex and think.
            if (source == "reflex" and self.cfg.crisis_energy
                    and obs["energy"] <= self.cfg.crisis_energy
                    and self.ledger.remaining > 0
                    and tick - self._last_crisis >= self.cfg.crisis_cooldown):
                self._last_crisis = tick
                self.stats["crisis_calls"] += 1
                self._say("  crisis: energy %d, overriding reflex" % obs["energy"])
                action, source = self._decide_with_model(obs, tick)
                source = "crisis" if source == "model" else source

            if action is None and self.ledger.remaining > 0:
                action, source = self._decide_with_model(obs, tick)
            if action is None:
                action, source = "stay", "idle"

            events = w.step(action)
            bucket = ("reflex_ticks" if source == "reflex"
                      else "idle_ticks" if source == "idle" else "model_ticks")
            self.stats[bucket] += 1
            tick_cost = budget_before - self.ledger.remaining
            self.last_calls = [c for c in self.last_calls if c["tick"] == tick]
            self._last_tick_entry = entry = {
                "tick": tick, "obs": obs, "source": source, "action": action, "events": events,
                "state": w.state(),
                "energy_after": w.energy, "eaten_total": w.eaten, "alive": w.alive,
                "budget_after": self.ledger.remaining, "tick_cost": tick_cost,
                "reflex_error": reflex_err, "notes": self.creature.notes,
                "reflex_version": self.creature.reflex_version,
                "drift": next((e[7:] for e in events if e.startswith("DRIFT: ")), None),
            }
            self.ledger.record_tick(entry)
            if self.cfg.watch:
                from .viz import render_frame
                print(render_frame(self.last_tick_entry(), self.cfg.as_dict(), self.run_dir, self.last_calls), flush=True)
            else:
                self._say("tick %2d | %-11s | %-4s | energy %2d | food %d | pred %-9s | cost %5d | left %6d | %s" % (
                    tick, source, action, w.energy, len(w.food),
                    str(obs["predator"]), tick_cost, self.ledger.remaining, ", ".join(events)))

            if not w.alive:
                break
            if tick % self.cfg.report_every == 0 and tick < self.cfg.ticks and self.ledger.remaining > 0:
                obs2 = w.observe()
                obs2["budget"] = self.ledger.remaining
                self._report(obs2, tick)

        summary = {
            "format": LOG_FORMAT,
            "run_dir": self.run_dir,
            "by": self.cfg.by,
            "runtime": self.runtime.name,
            "model": self.runtime.model,
            "seed": self.cfg.seed,
            "survived_ticks": w.tick_no,
            "max_ticks": self.cfg.ticks,
            "alive": w.alive,
            "cause_of_death": w.cause_of_death,
            "food_eaten": w.eaten,
            "final_energy": w.energy,
            "budget": self.cfg.budget,
            "tokens_spent": self.ledger.spent,
            "tokens_left": self.cfg.budget - self.ledger.spent,
            "overdraft": self.ledger.overdraft,
            "model_calls": self.ledger.calls,
            "cost_usd": round(self.ledger.cost_usd, 4),
            "reflex_versions": self.creature.reflex_version,
            "drifts": w.drifts,
            **self.stats,
        }
        with open(os.path.join(self.run_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        self._say("")
        self._say("RESULT: %s after %d ticks | ate %d | spent %d/%d tokens in %d calls (%d reflex ticks, %d self-prompts) | $%.4f" % (
            "alive" if w.alive else w.cause_of_death, w.tick_no, w.eaten, self.ledger.spent, self.cfg.budget,
            self.ledger.calls, self.stats["reflex_ticks"], self.stats["think_calls"], self.ledger.cost_usd))
        self._say("replay: python3 -m nomnom replay %s" % self.run_dir)
        return summary
