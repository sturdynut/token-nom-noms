from __future__ import annotations

import json
import math
import os
import time


class Ledger:
    """Tracks the token budget and appends every model call to calls.jsonl."""

    def __init__(self, budget: int, run_dir: str, cache_read_weight: float = 0.1, cache_write_weight: float = 1.0):
        self.budget = budget
        self.remaining = budget
        self.spent = 0
        self.last_charge = 0
        self.calls = 0
        self.cost_usd = 0.0
        self.cache_read_weight = cache_read_weight
        self.cache_write_weight = cache_write_weight
        self.run_dir = run_dir
        self._calls_path = os.path.join(run_dir, "calls.jsonl")
        self._ticks_path = os.path.join(run_dir, "ticks.jsonl")
        self._reports_path = os.path.join(run_dir, "reports.jsonl")

    def charge_for(self, res) -> int:
        raw = (
            res.input_tokens
            + res.output_tokens
            + res.cache_write * self.cache_write_weight
            + res.cache_read * self.cache_read_weight
        )
        return int(math.ceil(raw))

    def record_call(self, *, tick: int, kind: str, depth: int, runtime: str, model: str,
                    system: str, prompt: str, res) -> int:
        charge = self.charge_for(res)
        before = self.remaining
        # The true cost of a call is only known after it returns, so a call authorized on
        # the last token can overrun. `remaining` is the agent's usable budget and floors
        # at zero; `spent` records what was actually consumed, so the two disagree by the
        # overdraft. summary.json reports both.
        self.remaining = max(0, self.remaining - charge)
        self.spent += charge
        self.last_charge = charge
        self.calls += 1
        self.cost_usd += res.cost_usd or 0.0
        entry = {
            "ts": time.time(),
            "tick": tick,
            "kind": kind,
            "depth": depth,
            "runtime": runtime,
            "model": model,
            "system": system,
            "prompt": prompt,
            "response": res.text,
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "thinking_tokens": getattr(res, "thinking_tokens", 0),
            "cache_read": res.cache_read,
            "cache_write": res.cache_write,
            "charged": charge,
            "budget_before": before,
            "budget_after": self.remaining,
            "cost_usd": res.cost_usd,
            "latency_ms": res.latency_ms,
            "error": res.error,
        }
        self._append(self._calls_path, entry)
        return charge

    @property
    def overdraft(self) -> int:
        """Tokens spent beyond the budget. Zero unless the last call overran."""
        return max(0, self.spent - self.budget)

    def record_tick(self, entry: dict):
        self._append(self._ticks_path, entry)

    def record_report(self, entry: dict):
        self._append(self._reports_path, entry)

    @staticmethod
    def _append(path: str, obj: dict):
        with open(path, "a") as f:
            f.write(json.dumps(obj) + "\n")
