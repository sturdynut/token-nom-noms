from __future__ import annotations

import json
import os
import random
import re
import subprocess
import time
import urllib.request


class CallResult:
    def __init__(self, text="", input_tokens=0, output_tokens=0, cache_read=0, cache_write=0,
                 cost_usd=None, latency_ms=0, error=None, raw=None, thinking_tokens=0,
                 models=None):
        self.text = text
        self.thinking_tokens = thinking_tokens
        self.models = models or []
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read = cache_read
        self.cache_write = cache_write
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.error = error
        self.raw = raw


class Runtime:
    name = "base"

    def __init__(self, model=None, timeout=180):
        self.model = model
        self.timeout = timeout

    def call(self, system: str, prompt: str) -> CallResult:
        raise NotImplementedError


class ClaudeRuntime(Runtime):
    """Claude Code in --print mode with its own tools, MCP servers and settings stripped."""

    name = "claude"

    def __init__(self, model=None, timeout=180, effort=None):
        super().__init__(model, timeout)
        self.effort = effort

    def call(self, system, prompt):
        cmd = [
            "claude", "-p",
            "--output-format", "json",
            "--no-session-persistence",
            "--tools", "",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--setting-sources", "",
            "--system-prompt", system,
        ]
        if self.model:
            cmd += ["--model", self.model]
        if self.effort:
            cmd += ["--effort", self.effort]
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)
        t0 = time.time()
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                                  timeout=self.timeout, env=env)
        except subprocess.TimeoutExpired:
            return CallResult(error="claude timed out", latency_ms=int((time.time() - t0) * 1000))
        ms = int((time.time() - t0) * 1000)
        try:
            d = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return CallResult(error="claude returned non-JSON: " + (proc.stderr or proc.stdout)[-400:], latency_ms=ms)
        u = d.get("usage", {}) or {}
        res = CallResult(
            text=d.get("result", "") or "",
            input_tokens=u.get("input_tokens", 0),
            output_tokens=u.get("output_tokens", 0),
            cache_read=u.get("cache_read_input_tokens", 0),
            cache_write=u.get("cache_creation_input_tokens", 0),
            thinking_tokens=(u.get("output_tokens_details") or {}).get("thinking_tokens", 0),
            models=sorted((d.get("modelUsage") or {}).keys()),
            cost_usd=d.get("total_cost_usd"),
            latency_ms=ms,
            raw=d,
        )
        if d.get("is_error"):
            res.error = "claude error: " + res.text[:300]
        return res


class CodexRuntime(Runtime):
    """Codex CLI in exec --json mode. Written from the documented event format; verify on your install."""

    name = "codex"

    def call(self, system, prompt):
        cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "--ephemeral", "-s", "read-only"]
        if self.model:
            cmd += ["-m", self.model]
        cmd.append("-")
        full = system + "\n\n" + prompt if system else prompt
        t0 = time.time()
        try:
            proc = subprocess.run(cmd, input=full, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return CallResult(error="codex timed out", latency_ms=int((time.time() - t0) * 1000))
        ms = int((time.time() - t0) * 1000)
        text, usage, err = "", {}, None
        for line in proc.stdout.splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = ev.get("type")
            if t == "item.completed":
                item = ev.get("item", {})
                if item.get("type") == "agent_message":
                    text = item.get("text", "")
                elif item.get("type") == "error":
                    err = item.get("message")
            elif t == "turn.completed":
                usage = ev.get("usage", {}) or {}
            elif t in ("turn.failed", "error"):
                err = ev.get("message") or json.dumps(ev.get("error"))
        cached = usage.get("cached_input_tokens", 0) or 0
        return CallResult(
            text=text,
            input_tokens=max(0, (usage.get("input_tokens", 0) or 0) - cached),
            output_tokens=usage.get("output_tokens", 0) or 0,
            cache_read=cached,
            latency_ms=ms,
            error=err if (err and not text) else None,
            raw={"stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-500:]},
        )


class OllamaRuntime(Runtime):
    """Local model via the Ollama HTTP API."""

    name = "ollama"

    def __init__(self, model="llama3.2", timeout=180, host="http://localhost:11434", num_predict=600):
        super().__init__(model, timeout)
        self.host = host
        self.num_predict = num_predict

    def call(self, system, prompt):
        body = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": self.num_predict, "temperature": 0.3},
        }
        req = urllib.request.Request(
            self.host + "/api/generate",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                d = json.load(r)
        except Exception as e:  # noqa: BLE001
            return CallResult(error="ollama error: %s" % e, latency_ms=int((time.time() - t0) * 1000))
        ms = int((time.time() - t0) * 1000)
        text = d.get("response", "")
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        return CallResult(
            text=text,
            input_tokens=d.get("prompt_eval_count", 0),
            output_tokens=d.get("eval_count", 0),
            latency_ms=ms,
            raw={k: d.get(k) for k in ("model", "done_reason", "total_duration")},
        )


class MockRuntime(Runtime):
    """No LLM. A greedy scripted brain that exercises every path: notes, think, reflex. Tokens are len/4."""

    name = "mock"

    def __init__(self, model="mock", timeout=0, seed=0):
        super().__init__(model, timeout)
        self.rng = random.Random(seed)
        self.calls = 0

    @staticmethod
    def _greedy(obs):
        food = obs.get("food") or []
        pred = obs.get("predator")
        if pred is not None and abs(pred[0]) + abs(pred[1]) <= 2:
            dx, dy = -pred[0], -pred[1]
            return "e" if dx > 0 else "w" if dx < 0 else "s" if dy > 0 else "n"
        if not food:
            return "stay"
        dx, dy = food[0]
        if abs(dx) >= abs(dy):
            return "e" if dx > 0 else "w"
        return "s" if dy > 0 else "n"

    def call(self, system, prompt):
        self.calls += 1
        if system.startswith("You are answering"):
            text = "Move away from the predator when it is within 2 cells, otherwise go to the nearest food."
        elif "REPORT DUE" in prompt:
            text = json.dumps({"strategy": "greedy reflex, no model calls",
                               "changed": "installed reflex at tick 3", "expected_savings": "~all",
                               "confidence": 0.9})
        else:
            m = re.search(r"OBSERVATION\n(\{.*?\})\n", prompt, re.S)
            obs = json.loads(m.group(1)) if m else {}
            out = {"action": self._greedy(obs), "notes": "tick %s: heading for food" % obs.get("tick")}
            if obs.get("tick") == 1 and "SELF-PROMPTS" not in prompt:
                out = {"think": "What is a good survival rule for a grid creature with a slow predator?"}
            elif obs.get("tick") == 3:
                out["reflex"] = (
                    "def act(obs):\n"
                    "    food = obs.get('food') or []\n"
                    "    pred = obs.get('predator')\n"
                    "    if pred is not None and abs(pred[0]) + abs(pred[1]) <= 2:\n"
                    "        dx, dy = -pred[0], -pred[1]\n"
                    "        return 'e' if dx > 0 else 'w' if dx < 0 else 's' if dy > 0 else 'n'\n"
                    "    if not food:\n"
                    "        return 'stay'\n"
                    "    dx, dy = food[0]\n"
                    "    if abs(dx) >= abs(dy):\n"
                    "        return 'e' if dx > 0 else 'w'\n"
                    "    return 's' if dy > 0 else 'n'\n"
                )
                out["notes"] = "reflex installed; greedy food + flee"
            text = json.dumps(out)
        return CallResult(
            text=text,
            input_tokens=(len(system) + len(prompt)) // 4,
            output_tokens=len(text) // 4,
            latency_ms=1,
        )


GREEDY_REFLEX = """STEPS = {'n': (0, -1), 's': (0, 1), 'e': (1, 0), 'w': (-1, 0)}


def act(obs):
    # What a person writes in a few minutes: walk at the nearest food, run from a
    # close predator, and refuse to walk into anything you can see is bad. It does
    # not plan a route, so a rock between it and dinner simply stops it.
    bad = {tuple(c) for c in obs.get('rocks', [])}
    bad |= {tuple(c) for c in obs.get('pits', [])}
    bad |= {tuple(c) for c in obs.get('traps_known', [])}

    def ok(d):
        return STEPS[d] not in bad

    preds = obs.get('predators') or ([obs['predator']] if obs.get('predator') else [])
    near = [p for p in preds if abs(p[0]) + abs(p[1]) <= 2]
    if near:
        p = near[0]
        want = ['e' if -p[0] > 0 else 'w'] if abs(p[0]) >= abs(p[1]) else ['s' if -p[1] > 0 else 'n']
        want += ['n', 's', 'e', 'w']
        for d in want:
            if ok(d):
                return d
        return 'stay'

    food = obs.get('food') or []
    if not food:
        return 'stay'
    dx, dy = food[0]
    want = ['e' if dx > 0 else 'w'] if abs(dx) >= abs(dy) else ['s' if dy > 0 else 'n']
    want += ['s' if dy > 0 else 'n'] if abs(dx) >= abs(dy) else ['e' if dx > 0 else 'w']
    for d in want:
        if ok(d):
            return d
    return 'stay'
"""


class BaselineRuntime(Runtime):
    """No model at all. Installs one hand-written greedy reflex and charges nothing.

    This is the reference row on the leaderboard, not a competitor: it answers the
    question every paid run has to beat, which is what a human's fifteen lines score
    for free. Token counts are genuinely zero, so it also exercises the zero-budget
    path through the harness.
    """

    name = "baseline"

    def __init__(self, model="greedy", timeout=0):
        super().__init__(model, timeout)

    def call(self, system, prompt):
        if "REPORT DUE" in prompt:
            text = json.dumps({"strategy": "a hand-written greedy reflex, installed once, never revised",
                               "changed": "nothing; this run has no model behind it",
                               "expected_savings": "all of it", "confidence": 1.0})
        else:
            text = json.dumps({"action": "stay", "reflex": GREEDY_REFLEX,
                               "notes": "hand-written baseline: flee any predator within 2, else walk to the nearest food"})
        return CallResult(text=text, input_tokens=0, output_tokens=0, latency_ms=0)


RUNTIMES = {
    "claude": ClaudeRuntime,
    "codex": CodexRuntime,
    "ollama": OllamaRuntime,
    "mock": MockRuntime,
    "baseline": BaselineRuntime,
}


def make_runtime(name: str, model=None, timeout=180, effort=None) -> Runtime:
    if name not in RUNTIMES:
        raise SystemExit("unknown runtime %r; choose from %s" % (name, ", ".join(RUNTIMES)))
    cls = RUNTIMES[name]
    kw = {"timeout": timeout}
    if model is not None:
        kw["model"] = model
    if name == "claude" and effort:
        kw["effort"] = effort
    return cls(**kw)
