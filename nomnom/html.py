from __future__ import annotations

import json
import os

from .viz import absolute_state, _load


def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()


def load_run(run_dir: str) -> dict:
    with open(os.path.join(run_dir, "config.json")) as f:
        cfg = json.load(f)
    ticks = _load(os.path.join(run_dir, "ticks.jsonl"))
    calls = _load(os.path.join(run_dir, "calls.jsonl"))
    reports = _load(os.path.join(run_dir, "reports.jsonl"))
    summary_path = os.path.join(run_dir, "summary.json")
    summary = None
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            summary = json.load(f)
    for t in ticks:
        t["state"] = absolute_state(t)
        t.pop("obs", None)
    reflex_path = os.path.join(run_dir, "creature", "reflex.py")
    notes_path = os.path.join(run_dir, "creature", "notes.md")
    return {
        "name": os.path.basename(run_dir.rstrip("/")),
        "runtime": cfg["runtime"],
        "model": cfg["model"],
        "cfg": {k: cfg["config"].get(k) for k in ("size", "budget", "ticks", "max_energy", "seed", "food_value", "predator_every", "drift_every")},
        "summary": summary,
        "ticks": ticks,
        "calls": [{k: c.get(k) for k in ("tick", "kind", "depth", "prompt", "response", "input_tokens",
                                          "output_tokens", "thinking_tokens", "charged", "budget_after", "error")} for c in calls],
        "reports": reports,
        "reflex": _read_text(reflex_path),
        "notes": _read_text(notes_path),
    }


DEFAULT_REPO = "https://github.com/sturdynut/token-nom-noms"


def repo_url() -> str:
    """The origin remote as a browsable URL, so a fork's page links to the fork."""
    import subprocess
    try:
        out = subprocess.run(["git", "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:  # noqa: BLE001
        return DEFAULT_REPO
    if not out:
        return DEFAULT_REPO
    if out.startswith("git@"):
        out = "https://" + out[4:].replace(":", "/", 1)
    return out[:-4] if out.endswith(".git") else out


def render(runs: list, wrap: bool = True, repo: str = None) -> str:
    repo = repo or repo_url()
    data = json.dumps(runs, separators=(",", ":")).replace("</", "<\\/")
    body = (TEMPLATE.replace("__DATA__", data)
            .replace("__REPO_SHORT__", repo.split("//", 1)[-1])
            .replace("__REPO__", repo))
    if not wrap:
        return body
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
            + body + "\n</body>\n</html>\n")


def write_html(run_dirs: list, out: str = None, wrap: bool = True, repo: str = None) -> str:
    runs = [load_run(d) for d in run_dirs]
    if out is None:
        out = os.path.join(run_dirs[0], "replay.html")
    with open(out, "w") as f:
        f.write(render(runs, wrap, repo))
    return out


TEMPLATE = r"""<title>Token Nom Noms</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#F2F5F1; --panel:#FBFCFA; --line:#D6DDD7; --ink:#1B2320; --ink-2:#4F5B55; --ink-3:#7E8A83;
  --model:#5B4FC9; --model-soft:#E5E2F7; --reflex:#2E8B57; --reflex-soft:#DDEFE4; --idle:#8A9490;
  --predator:#C8383A; --food:#A8790F; --food-fill:#E3B33E; --grid:#E1E7E1; --trail:#B9C6BC;
  --creature:#2E8B57; --creature-dark:#1F6640; --eye:#F7FAF7; --focus:#5B4FC9;
  --rock:#AFBCB2; --rock-edge:#8C9B91; --pit:#C3CBD6; --pit-edge:#8E9AAA; --trap:#C8383A;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#131917; --panel:#1B2220; --line:#2C3632; --ink:#E4EAE5; --ink-2:#A9B5AE; --ink-3:#77837C;
    --model:#7B72DC; --model-soft:#2A2748; --reflex:#48A874; --reflex-soft:#1F3A2B; --idle:#5E6963;
    --predator:#E0555A; --food:#B98A22; --food-fill:#D9A83A; --grid:#232C29; --trail:#33413B;
    --creature:#48A874; --creature-dark:#2D7A50; --eye:#0F1512; --focus:#9D95EE;
    --rock:#3A453F; --rock-edge:#4E5B53; --pit:#2A3340; --pit-edge:#3E4A5A; --trap:#E0555A;
  }
}
:root[data-theme="dark"]{
  --bg:#131917; --panel:#1B2220; --line:#2C3632; --ink:#E4EAE5; --ink-2:#A9B5AE; --ink-3:#77837C;
  --model:#7B72DC; --model-soft:#2A2748; --reflex:#48A874; --reflex-soft:#1F3A2B; --idle:#5E6963;
  --predator:#E0555A; --food:#B98A22; --food-fill:#D9A83A; --grid:#232C29; --trail:#33413B;
  --creature:#48A874; --creature-dark:#2D7A50; --eye:#0F1512; --focus:#9D95EE;
  --rock:#3A453F; --rock-edge:#4E5B53; --pit:#2A3340; --pit-edge:#3E4A5A; --trap:#E0555A;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,sans-serif;padding-block:20px 48px;padding-inline:clamp(16px,3vw,40px)}
h1,h2,h3{font-family:"Bricolage Grotesque","IBM Plex Sans",system-ui,sans-serif;text-wrap:balance;margin:0}
h1{font-size:clamp(26px,3.4vw,38px);font-weight:700;letter-spacing:-0.01em;line-height:1.05}
h2{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
.num{font-variant-numeric:tabular-nums}
header{margin-bottom:14px;display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;justify-content:space-between}
.repo{display:inline-flex;align-items:center;gap:6px;color:var(--ink-2);font-size:13px;text-decoration:none;border-bottom:1px solid var(--line);padding-bottom:2px}
.repo:hover{color:var(--ink);border-bottom-color:var(--ink-3)}
.repo svg{width:12px;height:12px;stroke:currentColor;fill:none;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.foot-link{margin-top:28px;padding-top:16px;border-top:1px solid var(--line);font-size:13px;color:var(--ink-3)}
.foot-link a{color:var(--ink-2)}
.runbar{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px 24px;margin-bottom:16px}
.runbar .sub{color:var(--ink-2);font-size:13.5px}
.runbar .sub b{color:var(--ink);font-weight:600}

.picker{display:grid;gap:12px;margin-bottom:20px}
.pickrow{display:grid;grid-template-columns:72px 1fr;gap:12px;align-items:start}
@media (max-width:620px){.pickrow{grid-template-columns:1fr;gap:6px}}
.picklabel{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);padding-top:14px}
@media (max-width:620px){.picklabel{padding-top:0}}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip-btn{display:flex;align-items:center;gap:10px;padding:11px 16px;border-radius:12px;border:1px solid var(--line);background:var(--panel);cursor:pointer;text-align:left;line-height:1.25;transition:border-color .12s,background .12s}
.chip-btn:hover{border-color:var(--ink-3)}
.chip-btn.on{border-color:var(--model);background:var(--model-soft)}
.chip-btn.on .cb-name{color:var(--model)}
.chip-btn svg{flex:none;width:17px;height:17px;stroke:var(--ink-3);fill:none;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.chip-btn.on svg{stroke:var(--model)}
.cb-text{display:grid}
.cb-name{font-size:14px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}
.cb-sub{font-size:11.5px;color:var(--ink-3);font-variant-numeric:tabular-nums}
.dot{width:8px;height:8px;border-radius:50%;flex:none}
.dot.ok{background:var(--reflex)}.dot.bad{background:var(--predator)}
@media (prefers-reduced-motion: reduce){.chip-btn{transition:none}}

.combo{position:relative;max-width:460px;flex:1 1 320px}
.combo-field{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:12px;border:1px solid var(--line);background:var(--panel)}
.combo-field:focus-within{border-color:var(--focus)}
.combo-field svg{width:15px;height:15px;stroke:var(--ink-3);fill:none;stroke-width:1.7;flex:none}
.combo input{flex:1;min-width:0;border:0;background:transparent;color:var(--ink);font:inherit;font-size:14px;padding:0;outline:none}
.combo input::placeholder{color:var(--ink-3)}
.combo-caret{border:0;background:transparent;color:var(--ink-3);cursor:pointer;padding:0 2px;font-size:12px;line-height:1}
.combo ul{position:absolute;z-index:5;left:0;right:0;top:calc(100% + 6px);margin:0;padding:5px;list-style:none;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:0 10px 28px rgba(0,0,0,.18);max-height:280px;overflow-y:auto}
.combo ul[hidden]{display:none}
.combo li{padding:8px 10px;border-radius:8px;cursor:pointer;font-size:13px;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.combo li:hover,.combo li.cursor{background:var(--grid)}
.combo li.on{background:var(--model-soft)}
.combo li b{font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}
.combo li span{color:var(--ink-2);font-variant-numeric:tabular-nums}
.combo li.empty-li{color:var(--ink-3);font-style:italic;cursor:default}
.combo li.empty-li:hover{background:transparent}
.pickrow .withpill{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;font-size:13px;font-weight:500;border:1px solid var(--line);background:var(--panel)}
.pill.dead{border-color:var(--predator);color:var(--predator)}
.pill.alive{border-color:var(--reflex);color:var(--reflex)}
select,button{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 10px;cursor:pointer}
button:hover,select:hover{border-color:var(--ink-3)}
button:focus-visible,select:focus-visible,input:focus-visible,canvas:focus-visible,.strip:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
button.primary{background:var(--ink);color:var(--bg);border-color:var(--ink);min-width:78px}
.explain{border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding-block:18px;margin-bottom:22px;display:grid;gap:16px}
.lede{margin:0;font-family:"Bricolage Grotesque","IBM Plex Sans",system-ui,sans-serif;font-size:clamp(18px,2.2vw,23px);font-weight:500;line-height:1.3;letter-spacing:-0.01em;max-width:46ch}
.lede b{font-weight:700}
.lede2{display:inline-block;margin-top:.35em;color:var(--ink-2)}
.how{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px 28px}
.how h3{margin:0 0 4px;font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:13.5px;font-weight:600;color:var(--ink)}
.how p{margin:0;font-size:13.5px;color:var(--ink-2);max-width:46ch}
.how b{color:var(--ink);font-weight:600}
.finding{margin:0;font-size:14.5px;line-height:1.45;color:var(--ink);border-left:3px solid var(--reflex);padding-left:12px;max-width:62ch}
.guide{display:grid;gap:7px;font-size:13px;color:var(--ink-2)}
.guide p{margin:0}
.keys{margin:0;padding:0;list-style:none;display:grid;gap:4px}
.keys li{display:flex;gap:4px;align-items:baseline}
.guide .k{font-weight:600;white-space:nowrap}
.guide .k::before{content:"";display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:baseline;background:currentColor}
.guide .paid{color:var(--model)}.guide .free{color:var(--reflex)}
.guide .rept{color:var(--food)}.guide .out{color:var(--idle)}
.stage{display:grid;grid-template-columns:minmax(260px,520px) minmax(280px,1fr);gap:24px;align-items:start}
@media (max-width:760px){.stage{grid-template-columns:1fr}}
.world{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}
canvas{display:block;width:100%;aspect-ratio:1/1;max-width:100%;border-radius:6px}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:10px;font-size:13px;color:var(--ink-2)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
.sw.round{border-radius:50%}
.sw.dia{transform:rotate(45deg);border-radius:2px;width:10px;height:10px}
.panel{display:grid;gap:18px}
.tickline{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.tickline .big{font-family:"Bricolage Grotesque",system-ui,sans-serif;font-size:40px;font-weight:700;line-height:1;letter-spacing:-0.02em}
.tickline .of{color:var(--ink-3)}
.meters{display:grid;gap:10px}
.meter{display:grid;grid-template-columns:64px 1fr 120px;align-items:center;gap:10px;font-size:13px}
.meter .lab{color:var(--ink-2);text-transform:uppercase;letter-spacing:.06em;font-size:11px;font-weight:600}
.meter .bar{height:12px;background:var(--grid);border-radius:4px;overflow:hidden;position:relative}
.meter .bar i{position:absolute;inset:0;width:0;border-radius:4px;transition:width .12s linear}
.meter.energy .bar i{background:var(--reflex)}
.meter.budget .bar i{background:var(--model)}
.meter .val{text-align:right;color:var(--ink-2)}
@media (prefers-reduced-motion: reduce){.meter .bar i{transition:none}}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px 16px}
.fact .k{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
.fact .v{font-size:15px;font-weight:500}
.chip{display:inline-block;padding:1px 8px;border-radius:4px;font-size:13px;font-weight:600}
.chip.model{background:var(--model-soft);color:var(--model)}
.chip.reflex{background:var(--reflex-soft);color:var(--reflex)}
.chip.idle{background:var(--grid);color:var(--ink-2)}
.block{border-top:1px solid var(--line);padding-top:12px;display:grid;gap:6px}
.block .body{font-size:13.5px;color:var(--ink-2);white-space:pre-wrap;word-break:break-word;max-height:190px;overflow:auto}
.qa{display:grid;gap:4px;font-size:13.5px}
.qa .q{color:var(--ink)}
.qa .q::before{content:"self-prompt ";color:var(--model);font-weight:600;font-size:11px;letter-spacing:.06em;text-transform:uppercase}
.qa .a{color:var(--ink-2)}
.qa .a::before{content:"reply ";color:var(--ink-3);font-weight:600;font-size:11px;letter-spacing:.06em;text-transform:uppercase}
.qa .rep{color:var(--food)}
.qa .rep::before{content:"report ";color:var(--food);font-weight:600;font-size:11px;letter-spacing:.06em;text-transform:uppercase}
.empty{color:var(--ink-3);font-style:italic}
.ledger{margin-top:28px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px 12px}
.ledger .head{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;justify-content:space-between;margin-bottom:8px}
.transport{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.strip{position:relative;height:120px;touch-action:none;cursor:col-resize}
.strip svg{display:block;width:100%;height:100%;overflow:visible}
.tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--bg);font-size:12px;padding:5px 8px;border-radius:5px;white-space:nowrap;transform:translate(-50%,-110%);display:none;z-index:2}
input[type=range]{width:100%;margin:6px 0 0;accent-color:var(--model)}
.foot{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px;margin-top:28px}
pre{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;font-size:12.5px;line-height:1.5;overflow-x:auto;color:var(--ink-2)}
.reports{display:grid;gap:10px}
.report{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:13.5px;display:grid;gap:4px}
.report .t{font-weight:600;color:var(--ink)}
.report .k{color:var(--ink-3);font-size:11px;letter-spacing:.06em;text-transform:uppercase;font-weight:600;margin-right:6px}
.hint{color:var(--ink-3);font-size:12.5px}
</style>

<header>
  <h1>Token Nom Noms</h1>
  <a class="repo" href="__REPO__">Source, logs and leaderboard on GitHub
    <svg viewBox="0 0 14 14" aria-hidden="true"><path d="M5 2h7v7"/><path d="M12 2 5.5 8.5"/><path d="M9.5 8.5V12H2V4.5h3.5"/></svg>
  </a>
</header>

<section class="explain">
  <p class="lede">Every thought an AI has costs <b>tokens</b>,<br>and tokens cost money.<br><span class="lede2">This is a game about running out of them.</span></p>
  <div class="how">
    <div>
      <h3>One creature, one budget</h3>
      <p>An AI agent is handed a small world, a creature to keep alive, and a fixed pile of tokens. Every thought it has is deducted from the pile. When the pile is empty, it never thinks again.</p>
    </div>
    <div>
      <h3>Thinking costs, instinct is free</h3>
      <p>The agent can write itself a <b>reflex</b>: a few lines of code that play the creature automatically. Writing it costs tokens once. Running it costs nothing, forever.</p>
    </div>
    <div>
      <h3>So when is a thought worth paying for?</h3>
      <p>That is the entire game, and it is the same question anyone building with AI has to answer. Each run below is one agent trying to work it out, logged down to the last token.</p>
    </div>
  </div>
  <p class="finding">The surprise so far: the better the model, the less it spends. The strongest wrote itself a pathfinder on its very first move and barely thought again, outliving a weaker model that burned nearly three times the tokens before dying.</p>
  <div class="guide">
    <p>Pick a run, press play, and watch the bar along the bottom.</p>
    <ul class="keys">
      <li><span class="k paid">Purple</span> is a paid thought.</li>
      <li><span class="k free">Green</span> is the free reflex playing.</li>
      <li><span class="k rept">Amber</span> is a report the agent was required to file.</li>
      <li><span class="k out">Grey</span> is out of money with no reflex to fall back on.</li>
    </ul>
  </div>
</section>

<section class="picker">
  <div class="pickrow">
    <span class="picklabel" id="lab-h">Harness</span>
    <div class="chips" id="harnessRow" role="group" aria-labelledby="lab-h"></div>
  </div>
  <div class="pickrow">
    <span class="picklabel" id="lab-m">Model</span>
    <div class="chips" id="modelRow" role="group" aria-labelledby="lab-m"></div>
  </div>
  <div class="pickrow">
    <span class="picklabel" id="lab-r">Run</span>
    <div class="withpill">
      <div class="combo" id="combo">
        <div class="combo-field">
          <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.2"/><path d="M10.2 10.2 14 14"/></svg>
          <input id="runFilter" type="text" role="combobox" aria-expanded="false" aria-controls="runList"
                 aria-autocomplete="list" aria-labelledby="lab-r" autocomplete="off" placeholder="Filter by seed, outcome or date">
          <button class="combo-caret" id="comboCaret" type="button" aria-label="Show all runs">&#9662;</button>
        </div>
        <ul id="runList" role="listbox" aria-labelledby="lab-r" hidden></ul>
      </div>
      <span class="pill" id="outcome"></span>
    </div>
  </div>
</section>

<div class="runbar">
  <div class="sub" id="meta"></div>
</div>

<section class="stage">
  <div class="world">
    <canvas id="c" width="520" height="520" tabindex="0" aria-label="World grid"></canvas>
    <div class="legend">
      <span><i class="sw round" style="background:var(--creature)"></i>creature</span>
      <span><i class="sw dia" style="background:var(--predator)"></i>predator</span>
      <span><i class="sw round" style="background:var(--food-fill);border:1px solid var(--food)"></i>food</span>
      <span><i class="sw" style="background:var(--rock);border:1px solid var(--rock-edge)"></i>rock</span>
      <span><i class="sw round" style="background:var(--pit);border:1px solid var(--pit-edge)"></i>pit</span>
      <span><i class="sw" style="background:transparent;color:var(--trap);font-weight:700;font-size:13px;line-height:12px;text-align:center">&times;</i>trap found</span>
      <span><i class="sw round" style="border:2px solid var(--model)"></i>paid thought this tick</span>
    </div>
  </div>
  <div class="panel">
    <div class="tickline"><span class="big num" id="tick">0</span><span class="of num" id="of">/ 0 ticks</span><span id="stagepill" class="pill"></span></div>
    <div class="meters">
      <div class="meter energy"><span class="lab">energy</span><div class="bar"><i id="ebar"></i></div><span class="val num" id="eval"></span></div>
      <div class="meter budget"><span class="lab">budget</span><div class="bar"><i id="bbar"></i></div><span class="val num" id="bval"></span></div>
    </div>
    <div class="facts">
      <div class="fact"><div class="k">decided by</div><div class="v" id="src"></div></div>
      <div class="fact"><div class="k">action</div><div class="v mono" id="act"></div></div>
      <div class="fact"><div class="k">tokens this tick</div><div class="v num" id="cost"></div></div>
      <div class="fact"><div class="k">reflex</div><div class="v" id="reflexv"></div></div>
    </div>
    <div class="block"><h2>What happened</h2><div class="body" id="events"></div></div>
    <div class="block"><h2>World shifts so far</h2><div class="body" id="world"></div></div>
    <div class="block"><h2>Notes the creature left itself</h2><div class="body mono" id="notes"></div></div>
    <div class="block"><h2>Self-prompts this tick</h2><div class="qa" id="thoughts"></div></div>
  </div>
</section>

<section class="ledger">
  <div class="head">
    <div>
      <h2>Token spend per tick</h2>
      <div class="legend" style="margin-top:4px">
        <span><i class="sw" style="background:var(--model)"></i>paid: the model was called</span>
        <span><i class="sw" style="background:var(--reflex)"></i>free: reflex decided</span>
        <span><i class="sw" style="background:var(--idle)"></i>idle: no budget, no reflex</span>
        <span><i class="sw" style="background:var(--food)"></i>report filed (stacked on top)</span>
        <span><i class="sw" style="border-left:2px dashed var(--food);width:0;border-radius:0"></i>world shifted</span>
      </div>
    </div>
    <div class="transport">
      <button id="first" aria-label="First tick">⏮</button>
      <button id="prev" aria-label="Previous tick">◀</button>
      <button id="play" class="primary">Play</button>
      <button id="next" aria-label="Next tick">▶</button>
      <button id="last" aria-label="Last tick">⏭</button>
      <select id="speed" aria-label="Playback speed"><option value="2">2 ticks/s</option><option value="4" selected>4 ticks/s</option><option value="10">10 ticks/s</option></select>
    </div>
  </div>
  <div class="strip" id="strip" tabindex="0" aria-label="Spend per tick, click or drag to scrub"><svg id="stripsvg" preserveAspectRatio="none"></svg><div class="tip" id="tip"></div></div>
  <input type="range" id="scrub" min="1" max="1" value="1" aria-label="Tick">
  <div class="hint">Drag the strip or use ← → keys. Bar height is tokens charged that tick, with the report's cost stacked on the tick it was filed.</div>
</section>

<section class="foot">
  <div><h2 style="margin-bottom:8px">Strategy reports</h2><div class="reports" id="reports"></div></div>
  <div><h2 style="margin-bottom:8px">Final reflex</h2><pre class="mono" id="reflex"></pre></div>
</section>

<p class="foot-link">Every run here is committed with its full logs. Fork it, run your own agent, and
  open a pull request: <a href="__REPO__">__REPO_SHORT__</a></p>

<script id="runs" type="application/json">__DATA__</script>
<script>
(function(){
  const RUNS = JSON.parse(document.getElementById('runs').textContent);
  const $ = id => document.getElementById(id);
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  let run = RUNS[0], i = 0, timer = null;
  // deep links: #run=<index>&tick=<n>
  const hash = Object.fromEntries(location.hash.replace(/^#/, '').split('&').filter(Boolean).map(kv => kv.split('=').map(decodeURIComponent)));
  if (hash.run && RUNS[+hash.run]) run = RUNS[+hash.run];
  function syncHash() { try { history.replaceState(null, '', '#run=' + RUNS.indexOf(run) + '&tick=' + run.ticks[i].tick); } catch (e) {} }

  // ---- harness -> model -> run picker ---------------------------------
  // Abstract marks rather than brand logos: a rule for the free reference line,
  // a burst for Claude, angle brackets for Codex, stacked layers for a local model.
  const ICONS = {
    baseline: '<path d="M2 11h13M2 6h6"/>',
    claude: '<path d="M8.5 2v13M3 5l11 7M14 5 3 12"/>',
    codex: '<path d="M6 4 2 8.5 6 13M11 4l4 4.5L11 13"/>',
    ollama: '<path d="M2.5 5.5 8.5 2.5l6 3-6 3z"/><path d="M2.5 8.5l6 3 6-3"/><path d="M2.5 11.5l6 3 6-3"/>',
  };
  const icon = h => '<svg viewBox="0 0 17 17" aria-hidden="true">' + (ICONS[h] || ICONS.claude) + '</svg>';
  const uniq = a => a.filter((v, k) => a.indexOf(v) === k);
  const harnesses = () => uniq(RUNS.map(r => r.runtime))
    .sort((a, b) => (a === 'baseline') - (b === 'baseline') || a.localeCompare(b));
  const modelsIn = h => uniq(RUNS.filter(r => r.runtime === h).map(r => r.model || ''));
  const runsIn = (h, m) => RUNS.filter(r => r.runtime === h && (r.model || '') === m);
  let selH = run.runtime, selM = run.model || '';

  function tile(cls, inner, on, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip-btn' + (on ? ' on' : '');
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.innerHTML = inner;
    b.addEventListener('click', onClick);
    return b;
  }

  function buildPicker() {
    const hr = $('harnessRow'); hr.textContent = '';
    harnesses().forEach(h => {
      const n = RUNS.filter(r => r.runtime === h).length;
      hr.appendChild(tile('h', icon(h) + '<span class="cb-text"><span class="cb-name">' + esc(h) +
        '</span><span class="cb-sub">' + n + (n === 1 ? ' run' : ' runs') + '</span></span>',
        h === selH, () => { selH = h; selM = modelsIn(h)[0]; pick(runsIn(selH, selM)[0]); }));
    });
    const mr = $('modelRow'); mr.textContent = '';
    modelsIn(selH).forEach(m => {
      const rs = runsIn(selH, m);
      const best = rs.reduce((a, r) => Math.max(a, (r.summary || {}).survived_ticks || 0), 0);
      const cap = (rs[0].summary || {}).max_ticks || run.cfg.ticks;
      const alive = rs.some(r => (r.summary || {}).alive);
      mr.appendChild(tile('m', '<span class="dot ' + (alive ? 'ok' : 'bad') + '"></span>' +
        '<span class="cb-text"><span class="cb-name">' + esc(m || '—') + '</span>' +
        '<span class="cb-sub">' + rs.length + (rs.length === 1 ? ' run' : ' runs') +
        ' · best ' + best + '/' + cap + '</span></span>',
        m === selM, () => { selM = m; pick(runsIn(selH, selM)[0]); }));
    });
    buildRunList($('runFilter').value);
  }

  function runLabel(r) {
    const s = r.summary || {};
    return (s.alive ? 'alive' : (s.cause_of_death || 'ended')) + ' ' + s.survived_ticks + '/' + s.max_ticks +
           ' · ' + fmt(s.tokens_spent) + ' tokens · ' + r.name.slice(0, 8);
  }

  const list = $('runList'), filt = $('runFilter');
  let cursor = -1, pool = [];

  function buildRunList(q) {
    q = (q || '').trim().toLowerCase();
    pool = runsIn(selH, selM).filter(r =>
      !q || (('seed ' + r.cfg.seed + ' ' + runLabel(r) + ' ' + r.name).toLowerCase().indexOf(q) >= 0));
    list.textContent = '';
    if (!pool.length) {
      const li = document.createElement('li');
      li.className = 'empty-li'; li.textContent = 'No runs match that filter';
      list.appendChild(li); cursor = -1; return;
    }
    pool.forEach((r, k) => {
      const li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', r === run ? 'true' : 'false');
      li.className = (r === run ? 'on' : '') + (k === cursor ? ' cursor' : '');
      li.innerHTML = '<b>seed ' + esc(r.cfg.seed) + '</b><span>' + esc(runLabel(r)) + '</span>';
      li.addEventListener('mousedown', e => { e.preventDefault(); pick(r); closeCombo(); });
      list.appendChild(li);
    });
  }

  function fieldLabel(r) {
    const s = r.summary || {};
    return 'seed ' + r.cfg.seed + ' · ' + (s.alive ? 'alive' : (s.cause_of_death || 'ended')) +
           ' ' + s.survived_ticks + '/' + s.max_ticks;
  }
  function openCombo() { list.hidden = false; filt.setAttribute('aria-expanded', 'true'); }
  function closeCombo() { list.hidden = true; filt.setAttribute('aria-expanded', 'false'); cursor = -1; }
  filt.addEventListener('focus', () => { filt.value = ''; buildRunList(''); openCombo(); });
  filt.addEventListener('input', () => { cursor = -1; buildRunList(filt.value); openCombo(); });
  filt.addEventListener('blur', () => setTimeout(() => { closeCombo(); filt.value = fieldLabel(run); }, 120));
  $('comboCaret').addEventListener('click', () => {
    if (list.hidden) { filt.value = ''; buildRunList(''); openCombo(); filt.focus(); } else closeCombo();
  });
  filt.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (list.hidden) { buildRunList(filt.value); openCombo(); }
      if (!pool.length) return;
      cursor = (cursor + (e.key === 'ArrowDown' ? 1 : pool.length - 1)) % pool.length;
      buildRunList(filt.value);
      const el = list.children[cursor]; if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      if (!list.hidden && pool[cursor]) { e.preventDefault(); pick(pool[cursor]); closeCombo(); filt.blur(); }
    } else if (e.key === 'Escape') { closeCombo(); filt.blur(); }
  });

  function pick(r) {
    if (!r || r === run) { if (r) filt.value = fieldLabel(r); buildPicker(); return; }
    run = r; selH = r.runtime; selM = r.model || ''; i = 0;
    filt.value = fieldLabel(r);
    stop(); buildStrip(); buildFoot(); show(); buildPicker();
  }

  function callsAt(t, kind) { return run.calls.filter(c => c.tick === t && (!kind || c.kind === kind)); }
  function fmt(n) { return (n == null ? '–' : n.toLocaleString()); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[ch])); }

  // ---- canvas ----------------------------------------------------------
  const cv = $('c'), ctx = cv.getContext('2d');
  function draw() {
    const t = run.ticks[i], st = t.state, n = run.cfg.size;
    const W = cv.width = cv.clientWidth * devicePixelRatio, H = cv.height = W;
    const cell = W / n;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = css('--panel'); ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = css('--grid'); ctx.lineWidth = Math.max(1, devicePixelRatio);
    for (let k = 0; k <= n; k++) { const p = Math.round(k * cell) + 0.5; ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, H); ctx.moveTo(0, p); ctx.lineTo(W, p); ctx.stroke(); }
    const cx = c => (c + 0.5) * cell;
    // Terrain sits under everything: walls, visible pits, and traps already found.
    (st.rocks || []).forEach(([x, y]) => {
      ctx.fillStyle = css('--rock'); ctx.strokeStyle = css('--rock-edge');
      ctx.lineWidth = Math.max(1, cell * 0.03);
      const p = cell * 0.1, side = cell - 2 * p;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x * cell + p, y * cell + p, side, side, cell * 0.14);
      else ctx.rect(x * cell + p, y * cell + p, side, side);
      ctx.fill(); ctx.stroke();
    });
    (st.pits || []).forEach(([x, y]) => {
      ctx.fillStyle = css('--pit'); ctx.strokeStyle = css('--pit-edge');
      ctx.lineWidth = Math.max(1, cell * 0.03);
      ctx.beginPath(); ctx.ellipse(cx(x), cx(y), cell * 0.34, cell * 0.26, 0, 0, 7);
      ctx.fill(); ctx.stroke();
    });
    (st.traps_known || []).forEach(([x, y]) => {
      ctx.strokeStyle = css('--trap'); ctx.lineWidth = Math.max(1.5, cell * 0.055);
      const r = cell * 0.24;
      ctx.beginPath();
      ctx.moveTo(cx(x) - r, cx(y) - r); ctx.lineTo(cx(x) + r, cx(y) + r);
      ctx.moveTo(cx(x) + r, cx(y) - r); ctx.lineTo(cx(x) - r, cx(y) + r);
      ctx.stroke();
    });
    // trail
    const trail = run.ticks.slice(Math.max(0, i - 8), i);
    trail.forEach((tt, k) => { const [x, y] = tt.state.pos; ctx.fillStyle = css('--trail'); ctx.globalAlpha = 0.25 + 0.75 * (k + 1) / (trail.length + 1); ctx.beginPath(); ctx.arc(cx(x), cx(y), cell * 0.09, 0, 7); ctx.fill(); });
    ctx.globalAlpha = 1;
    // food
    st.food.forEach(([x, y]) => { ctx.fillStyle = css('--food-fill'); ctx.strokeStyle = css('--food'); ctx.lineWidth = Math.max(1, cell * 0.04); ctx.beginPath(); ctx.arc(cx(x), cx(y), cell * 0.17, 0, 7); ctx.fill(); ctx.stroke(); });
    // predators
    const preds = st.predators || (st.predator ? [st.predator] : []);
    preds.forEach(([x, y]) => { const r = cell * 0.32; ctx.fillStyle = css('--predator'); ctx.beginPath(); ctx.moveTo(cx(x), cx(y) - r); ctx.lineTo(cx(x) + r, cx(y)); ctx.lineTo(cx(x), cx(y) + r); ctx.lineTo(cx(x) - r, cx(y)); ctx.closePath(); ctx.fill();
      ctx.fillStyle = css('--eye'); ctx.beginPath(); ctx.arc(cx(x) - r * 0.28, cx(y) - r * 0.1, cell * 0.05, 0, 7); ctx.arc(cx(x) + r * 0.28, cx(y) - r * 0.1, cell * 0.05, 0, 7); ctx.fill(); });
    // creature
    const [x, y] = st.pos; const stage = stageOf(t.tick); const r = cell * (stage === 'hatchling' ? 0.26 : stage === 'juvenile' ? 0.31 : 0.36);
    if (t.source.startsWith('model') || t.source === 'parse_error' || t.source === 'think_limit') { ctx.strokeStyle = css('--model'); ctx.lineWidth = Math.max(2, cell * 0.06); ctx.beginPath(); ctx.arc(cx(x), cx(y), r + cell * 0.12, 0, 7); ctx.stroke(); }
    ctx.fillStyle = st.alive ? css('--creature') : css('--idle'); ctx.beginPath(); ctx.arc(cx(x), cx(y), r, 0, 7); ctx.fill();
    ctx.fillStyle = st.alive ? css('--creature-dark') : css('--ink-3'); ctx.beginPath(); ctx.arc(cx(x), cx(y) + r * 0.35, r * 0.62, 0, Math.PI, false); ctx.fill();
    ctx.strokeStyle = css('--eye'); ctx.fillStyle = css('--eye'); ctx.lineWidth = Math.max(1.5, cell * 0.05);
    if (st.alive) { ctx.beginPath(); ctx.arc(cx(x) - r * 0.35, cx(y) - r * 0.2, r * 0.16, 0, 7); ctx.arc(cx(x) + r * 0.35, cx(y) - r * 0.2, r * 0.16, 0, 7); ctx.fill(); }
    else { const e = r * 0.16; [[-1, 0], [1, 0]].forEach(([sx]) => { const ex = cx(x) + sx * r * 0.35, ey = cx(y) - r * 0.2; ctx.beginPath(); ctx.moveTo(ex - e, ey - e); ctx.lineTo(ex + e, ey + e); ctx.moveTo(ex + e, ey - e); ctx.lineTo(ex - e, ey + e); ctx.stroke(); }); }
  }
  function stageOf(t) { return t < 15 ? 'hatchling' : t < 35 ? 'juvenile' : 'adult'; }

  // ---- panel -----------------------------------------------------------
  function show() {
    const t = run.ticks[i], st = t.state, cfg = run.cfg, s = run.summary;
    $('meta').innerHTML = '<b>' + esc(run.runtime) + (run.model ? ' · ' + esc(run.model) : '') + '</b> · seed ' + cfg.seed + ' · budget ' + fmt(cfg.budget) + ' tokens · ' + esc(run.name);
    if (s) { const dead = !s.alive; $('outcome').className = 'pill ' + (dead ? 'dead' : 'alive'); $('outcome').textContent = dead ? s.cause_of_death + ' at tick ' + s.survived_ticks : 'alive after ' + s.survived_ticks + ' ticks'; }
    $('tick').textContent = t.tick; $('of').textContent = '/ ' + cfg.ticks + ' ticks';
    $('stagepill').textContent = stageOf(t.tick);
    const emax = st.max_energy || cfg.max_energy;
    $('ebar').style.width = Math.min(100, 100 * st.energy / emax) + '%';
    $('eval').textContent = st.energy + ' / ' + emax;
    $('bbar').style.width = (100 * t.budget_after / cfg.budget) + '%'; $('bval').textContent = fmt(t.budget_after) + ' left';
    const src = t.source === 'reflex' ? 'reflex' : t.source === 'idle' ? 'idle' : 'model';
    $('src').innerHTML = '<span class="chip ' + src + '">' + esc(src === 'model' ? 'model' + (t.source !== 'model' ? ' (' + t.source.replace(/_/g, ' ') + ')' : '') : src) + '</span>';
    $('act').textContent = t.action; $('cost').textContent = fmt(t.tick_cost);
    $('reflexv').textContent = t.reflex_version ? 'v' + t.reflex_version + (t.reflex_error ? ' · error' : '') : 'none';
    const ev = t.events.length ? t.events.join(', ') : 'nothing';
    $('events').innerHTML = esc(ev.replace(/, DRIFT: [^,]*$/, '')) + (t.drift ? '\n<b style="color:var(--food)">WORLD SHIFTED · ' + esc(t.drift) + '</b>' : '') + (t.reflex_error ? '\n<span style="color:var(--predator)">reflex error: ' + esc(t.reflex_error) + '</span>' : '');
    const rules = []; if (st.predator_mode === 'camp') rules.push('predators camp food'); const drifts = run.ticks.slice(0, i + 1).filter(x => x.drift).map(x => x.drift);
    $('world').textContent = drifts.length ? drifts.join(' · ') : 'no shifts yet';
    $('notes').innerHTML = t.notes ? esc(t.notes) : '<span class="empty">none yet</span>';
    const th = callsAt(t.tick, 'think'), rp = callsAt(t.tick, 'report');
    let html = th.map(c => '<div class="q">' + esc(c.prompt) + '</div><div class="a">' + esc(c.response || c.error) + '</div>').join('');
    if (rp.length) html += rp.map(c => '<div class="rep">filed this tick, ' + fmt(c.charged) + ' tokens</div>').join('');
    $('thoughts').innerHTML = html || '<span class="empty">none</span>';
    $('scrub').value = t.tick;
    draw(); markStrip(); syncHash();
    if (!pickerReady) return;
    list.querySelectorAll('li[role=option]').forEach((li, k) => {
      const on = pool[k] === run;
      li.setAttribute('aria-selected', on ? 'true' : 'false');
      li.classList.toggle('on', on);
    });
  }

  // ---- spend strip -----------------------------------------------------
  const svg = $('stripsvg'), NS = 'http://www.w3.org/2000/svg';
  let bars = [];
  function buildStrip() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    const n = run.ticks.length;
    const reportCost = t => callsAt(t.tick, 'report').reduce((a, c) => a + (c.charged || 0), 0);
    const max = Math.max(1, ...run.ticks.map(t => t.tick_cost + reportCost(t)));
    svg.setAttribute('viewBox', '0 0 ' + n * 10 + ' 100');
    bars = run.ticks.map((t, k) => {
      const g = document.createElementNS(NS, 'g');
      const h = t.tick_cost > 0 ? Math.max(3, 96 * t.tick_cost / max) : (t.source === 'idle' ? 2 : 4);
      const r = document.createElementNS(NS, 'rect');
      r.setAttribute('x', k * 10 + 1); r.setAttribute('y', 100 - h); r.setAttribute('width', 8); r.setAttribute('height', h);
      r.setAttribute('fill', t.source === 'reflex' ? css('--reflex') : t.source === 'idle' ? css('--idle') : css('--model'));
      g.appendChild(r);
      const rc = reportCost(t);
      if (rc > 0) { const rh = Math.max(3, 96 * rc / max); const d = document.createElementNS(NS, 'rect'); d.setAttribute('x', k * 10 + 1); d.setAttribute('y', 100 - h - 1 - rh); d.setAttribute('width', 8); d.setAttribute('height', rh); d.setAttribute('fill', css('--food')); g.appendChild(d); }
      svg.appendChild(g); return g;
    });
    run.ticks.forEach((t, k) => { if (!t.drift) return; const l = document.createElementNS(NS, 'line'); l.setAttribute('x1', k * 10 + 10); l.setAttribute('x2', k * 10 + 10); l.setAttribute('y1', 0); l.setAttribute('y2', 100); l.setAttribute('stroke', css('--food')); l.setAttribute('stroke-width', 1); l.setAttribute('stroke-dasharray', '3 2'); l.setAttribute('vector-effect', 'non-scaling-stroke'); svg.appendChild(l); });
    const cur = document.createElementNS(NS, 'rect'); cur.id = 'cursor'; cur.setAttribute('y', 0); cur.setAttribute('width', 10); cur.setAttribute('height', 100); cur.setAttribute('fill', css('--ink')); cur.setAttribute('opacity', 0.14); svg.appendChild(cur);
    $('scrub').max = n; $('scrub').min = 1;
  }
  function markStrip() { const cur = $('cursor'); if (cur) cur.setAttribute('x', i * 10); }
  const strip = $('strip'), tip = $('tip');
  function tickFromEvent(e) { const b = strip.getBoundingClientRect(); const f = (e.clientX - b.left) / b.width; return Math.min(run.ticks.length - 1, Math.max(0, Math.floor(f * run.ticks.length))); }
  let dragging = false;
  strip.addEventListener('pointerdown', e => { dragging = true; strip.setPointerCapture(e.pointerId); stop(); i = tickFromEvent(e); show(); });
  strip.addEventListener('pointermove', e => { const k = tickFromEvent(e); const t = run.ticks[k]; const b = strip.getBoundingClientRect(); tip.style.display = 'block'; tip.style.left = ((k + 0.5) / run.ticks.length * b.width) + 'px'; tip.style.top = '0px';
    const rc = callsAt(t.tick, 'report').reduce((a, c) => a + (c.charged || 0), 0);
    tip.textContent = 'tick ' + t.tick + ' · ' + t.source.replace(/_/g, ' ') + ' · ' + fmt(t.tick_cost) + ' tokens' + (rc ? ' + report ' + fmt(rc) : '') + ' · ' + fmt(t.budget_after - rc) + ' left'; if (dragging) { i = k; show(); } });
  strip.addEventListener('pointerup', () => dragging = false);
  strip.addEventListener('pointerleave', () => { tip.style.display = 'none'; dragging = false; });
  $('scrub').addEventListener('input', e => { stop(); i = +e.target.value - 1; show(); });

  // ---- transport ---------------------------------------------------------
  function step(d) { i = Math.min(run.ticks.length - 1, Math.max(0, i + d)); show(); }
  function play() { if (timer) return stop(); if (i >= run.ticks.length - 1) i = 0; $('play').textContent = 'Pause'; timer = setInterval(() => { if (i >= run.ticks.length - 1) return stop(); step(1); }, 1000 / +$('speed').value); }
  function stop() { clearInterval(timer); timer = null; $('play').textContent = 'Play'; }
  $('play').addEventListener('click', play);
  $('next').addEventListener('click', () => { stop(); step(1); });
  $('prev').addEventListener('click', () => { stop(); step(-1); });
  $('first').addEventListener('click', () => { stop(); i = 0; show(); });
  $('last').addEventListener('click', () => { stop(); i = run.ticks.length - 1; show(); });
  $('speed').addEventListener('change', () => { if (timer) { stop(); play(); } });
  document.addEventListener('keydown', e => { if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') return; if (e.key === 'ArrowRight') { stop(); step(1); } else if (e.key === 'ArrowLeft') { stop(); step(-1); } else if (e.key === ' ') { e.preventDefault(); play(); } });

  // ---- foot ----------------------------------------------------------------
  function buildFoot() {
    const rs = run.reports;
    $('reports').innerHTML = rs.length ? rs.map(r => { const p = r.report || {}; const claimed = p.strategy || p.notes || r.raw || r.error || '';
      return '<div class="report"><div class="t">Tick ' + r.tick + ' · ' + fmt(r.budget_after) + ' tokens left</div>' +
        (p.strategy ? '<div><span class="k">strategy</span>' + esc(p.strategy) + '</div>' : '') +
        (p.changed ? '<div><span class="k">changed</span>' + esc(p.changed) + '</div>' : '') +
        (p.expected_savings ? '<div><span class="k">claims</span>' + esc(p.expected_savings) + '</div>' : '') +
        (!p.strategy && claimed ? '<div>' + esc(String(claimed).slice(0, 400)) + '</div>' : '') + '</div>'; }).join('')
      : '<span class="empty">no reports were filed</span>';
    $('reflex').textContent = run.reflex || 'The creature never wrote a reflex.';
  }

  let pickerReady = false;
  buildStrip(); buildFoot();
  if (hash.tick) { const k = run.ticks.findIndex(t => t.tick === +hash.tick); if (k >= 0) i = k; }
  buildPicker(); filt.value = fieldLabel(run); pickerReady = true;
  show();
  let raf = null; window.addEventListener('resize', () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); });
  if (window.matchMedia) { window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { buildStrip(); show(); }); }
  new MutationObserver(() => { buildStrip(); show(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
</script>"""
