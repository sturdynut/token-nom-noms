from __future__ import annotations

import argparse
import os
import sys

from .brain import Config, Game
from .replay import replay
from .runtimes import RUNTIMES, make_runtime


def main(argv=None):
    p = argparse.ArgumentParser(prog="nomnom", description="token-nom-noms: survive on a token budget")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run one creature for N ticks")
    r.add_argument("--runtime", choices=list(RUNTIMES), default="mock")
    r.add_argument("--model", default=None, help="model name for the runtime (e.g. haiku, llama3.2)")
    r.add_argument("--budget", type=int, default=40000, help="token budget for the whole run")
    r.add_argument("--ticks", type=int, default=50)
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--size", type=int, default=10)
    r.add_argument("--max-think", type=int, default=3, dest="max_think")
    r.add_argument("--report-every", type=int, default=10, dest="report_every")
    r.add_argument("--no-predator", action="store_true")
    r.add_argument("--drift-every", type=int, default=15, dest="drift_every", help="ticks between silent world shifts (0 disables)")
    r.add_argument("--crisis-energy", type=int, default=5, dest="crisis_energy", help="energy at or below which the model overrides the reflex (0 disables)")
    r.add_argument("--terrain", type=float, default=0.12, dest="terrain_density", help="share of cells holding a rock, pit or hidden trap (0 for open ground)")
    r.add_argument("--no-spawning", action="store_true", help="one body only, no colony and no token income")
    r.add_argument("--spawn-cost", type=int, default=2000, dest="spawn_cost", help="tokens charged per new body")
    r.add_argument("--income-cap", type=int, default=20000, dest="income_cap", help="most a run can earn back by foraging")
    r.add_argument("--timeout", type=int, default=180, help="seconds per model call")
    r.add_argument("--out", default="runs")
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--watch", action="store_true", help="animate the world in the terminal while running")
    r.add_argument("--effort", default=None, help="claude runtime only: --effort level passed to claude (e.g. low)")
    r.add_argument("--by", default=None, help="credit this run to a name or handle in summary.json (opt-in; nothing is recorded without it)")

    lb = sub.add_parser("leaderboard", help="aggregate every run's summary.json into runs/README.md")
    lb.add_argument("--runs", default="runs")

    va = sub.add_parser("validate", help="check every run folder is complete and replays deterministically")
    va.add_argument("--runs", default="runs")

    v = sub.add_parser("replay", help="print a readable transcript of a run")
    v.add_argument("run_dir")
    v.add_argument("--calls", action="store_true", help="also show each model reply")
    v.add_argument("--prompts", action="store_true", help="show full prompts and responses")
    v.add_argument("--watch", action="store_true", help="animate the run in the terminal")
    v.add_argument("--fps", type=float, default=4.0)

    h = sub.add_parser("html", help="write a standalone HTML5 canvas replay of one or more runs")
    h.add_argument("run_dirs", nargs="+")
    h.add_argument("-o", "--out", default=None, help="output file (default: replay.html in the first run dir)")
    h.add_argument("--open", action="store_true", help="open the result in the default browser")

    a = p.parse_args(argv)
    if a.cmd == "run":
        cfg = Config(runtime=a.runtime, model=a.model, budget=a.budget, ticks=a.ticks, seed=a.seed,
                     size=a.size, max_think=a.max_think, report_every=a.report_every,
                     predator=not a.no_predator, drift_every=a.drift_every,
                     crisis_energy=a.crisis_energy, terrain_density=a.terrain_density,
                     spawning=not a.no_spawning, spawn_cost=a.spawn_cost, income_cap=a.income_cap,
                     timeout=a.timeout, out=a.out, quiet=a.quiet,
                     watch=a.watch, effort=a.effort, by=a.by)
        runtime = make_runtime(a.runtime, a.model, a.timeout, a.effort)
        summary = Game(cfg, runtime).run()
        return 0 if summary["alive"] else 1
    if a.cmd == "replay":
        if a.watch:
            from .viz import watch
            watch(a.run_dir, fps=a.fps)
        else:
            replay(a.run_dir, show_calls=a.calls, show_prompts=a.prompts)
        return 0
    if a.cmd == "validate":
        from .validate import validate_all
        return 1 if validate_all(a.runs) else 0
    if a.cmd == "leaderboard":
        from .leaderboard import write_leaderboard
        print(write_leaderboard(a.runs))
        return 0
    if a.cmd == "html":
        from .html import write_html
        path = write_html(a.run_dirs, a.out)
        print(path)
        if a.open:
            import webbrowser
            webbrowser.open("file://" + os.path.abspath(path))
        return 0


if __name__ == "__main__":
    sys.exit(main())
