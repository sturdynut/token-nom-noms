from __future__ import annotations

import json
import subprocess
import sys

_RUNNER = r"""
import json, sys
payload = json.load(sys.stdin)
ns = {}
try:
    exec(compile(payload["src"], "reflex.py", "exec"), ns)
    fn = ns.get("act")
    if fn is None:
        raise RuntimeError("reflex.py does not define act(obs)")
    out = fn(payload["obs"])
    print(json.dumps({"action": out if isinstance(out, str) else None}))
except Exception as e:
    print(json.dumps({"error": "%s: %s" % (type(e).__name__, e)}))
"""


def run_reflex(src: str, obs: dict, timeout: float = 2.0):
    """Run the creature's reflex in a subprocess. Returns (action_or_None, error_or_None)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _RUNNER],
            input=json.dumps({"src": src, "obs": obs}),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, "reflex timed out after %.1fs" % timeout
    line = proc.stdout.strip().splitlines()
    if not line:
        return None, "reflex produced no output: " + proc.stderr.strip()[-300:]
    try:
        out = json.loads(line[-1])
    except json.JSONDecodeError:
        return None, "reflex output not JSON: " + line[-1][:200]
    if "error" in out:
        return None, out["error"]
    return out.get("action"), None
