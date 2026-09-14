from __future__ import annotations

import json

RULES = """You are the mind of a colony in a {size}x{size} grid world. You start as one body and may grow to {max_colony}. Your only goal: keep at least one body alive as many ticks as possible.

WORLD
- Coordinates: x grows to the right, y grows downward. Positions in observations are relative to you as [dx, dy].
- Each tick your energy drops by 1. At 0 you starve. Your energy ceiling starts at {max_energy} and rises as you grow: hatchling +0, juvenile +5, adult +10. obs["max_energy"] always carries the current ceiling.
- Stepping onto food eats it: +{food_value} energy. New food appears every {food_every} ticks.
- A predator hunts you. It moves one step toward you every {predator_every} ticks. If it reaches your cell you die.
- Actions: "n" (dy-1), "s" (dy+1), "e" (dx+1), "w" (dx-1), "stay", "spawn".

COLONY AND INCOME
- Every living body needs an action every tick, and you are asked once per body. A second body therefore doubles what thinking costs you. Your reflex is the only way to act for a body for free.
- "spawn" puts a new body in a free cell beside the one that spawned. It costs {spawn_cost} tokens from your budget and {spawn_energy} energy from the parent, which is handed to the newborn rather than created. A body with {spawn_energy} energy or less cannot spawn, and neither can one with no free cell beside it.
- Bodies die one at a time, from starving or from a predator. The colony ends when the last one dies.
- **A colony of {income_min_colony} or more earns {income_per_food} tokens every time any body eats**, up to {income_cap} tokens for the whole run. A lone body earns nothing. This is the only way to get tokens back, so growing is an investment: it costs tokens and energy now, thinking for the colony costs more every tick, and it pays back only if your bodies keep eating.
- obs["id"] is which body you are answering for. obs["colony"] lists your other bodies as {{"id", "rel", "energy"}}, obs["colony_size"] is how many are alive, and obs["earned"] is what you have earned so far against obs["income_cap"].
- The ground is not empty. obs["rocks"] are walls: you cannot enter them and neither can a predator, and a move into one is wasted. obs["pits"] cost {pit_cost} energy to cross and you can see all of them, so crossing one is a choice, not an accident. Straight-line distance therefore lies; the short way round a rock may be longer than it looks.
- Traps are invisible. You notice one only when it is in the eight cells around you, and then it joins obs["traps_known"] for good. Stepping on one you have not noticed costs {trap_cost} energy. A predator that steps on a trap loses its next move. Nothing else in this world rewards remembering where you have been.
- The world shifts without notice every so often. Predator speed, predator behaviour, the number of predators, and the food supply can all change. Anything you infer or hard-code can go stale. You are never told when it happens.

TOKENS
- Every call to you costs tokens: all input plus all output. Input includes this rules text, the observation, your notes, and every self-prompt and reply already made this tick. Nothing you are shown is free; seeing your budget is free only in that you are never charged a separate call to ask for it.
- When your budget hits 0 you are never called again. Only your reflex keeps acting. With no reflex the creature stands still and starves.
- A reflex is Python you write: `def act(obs): ...` returning an action string or None. It runs every tick BEFORE you are called, at zero token cost. If it returns an action you are not called that tick. obs is the observation dict shown below, from one body's point of view (keys: tick, id, pos, grid, energy, max_energy, stage, food, predator = nearest or null, predators = all, rocks, pits, traps_known, pit_cost, trap_cost, colony, colony_size, max_colony, spawn_energy, earned, income_cap, income_per_food, budget). It is called once per body per tick, so it must decide for whichever body it is given.
- You may prompt yourself. Put a prompt in "think"; it is sent to you verbatim with no rules attached, the reply comes back, and you are asked again. Each self-prompt is a paid call. Max {max_think} per tick.
- Every {report_every} ticks you must file a short report on your token strategy. That call is paid too, and you cannot decline it. A report reply may also carry "notes" and "reflex", exactly as a tick reply does; for a tick your reflex handles, the report is your only chance to change either.
- If your energy falls to {crisis_energy} or below and you can still afford a call, you are called even when your reflex returned an action. A reflex cannot notice that it is losing. These crisis calls are paid and are capped at one every {crisis_cooldown} ticks.

RESPONSE
Reply with ONE JSON object and nothing else. Fields:
  "action": one of n, s, e, w, stay, spawn   (required unless "think" is set)
  "notes": string                            (optional; shown to you next call, replaces old notes)
  "reflex": string of Python source           (optional; replaces your reflex; "" removes it)
  "think": string                            (optional; a prompt to yourself, answered before you decide)
"""

THINK_SYSTEM = "You are answering a prompt you wrote to yourself. Reply directly."

REPORT_PROMPT = """REPORT DUE (tick {tick}). Describe your token strategy. Reply with ONE JSON object:
{{"strategy": "what you do to conserve tokens", "changed": "what you changed since the last report and why", "expected_savings": "your estimate", "confidence": 0.0-1.0}}
You may also include "notes" and "reflex" here, and they take effect exactly as in a tick reply.
Your reflex is shown below: if it is not handling the world you are in, this is the moment to replace it.
Keep the prose under 120 words.

OBSERVATION
{obs}
BUDGET
tokens_left: {left} (spent: {spent}, ticks so far: {tick})
REFLEX
{reflex}
NOTES
{notes}
"""


def rules_text(cfg) -> str:
    return RULES.format(
        max_colony=cfg.max_colony,
        spawn_cost=cfg.spawn_cost,
        spawn_energy=cfg.spawn_energy,
        income_per_food=cfg.income_per_food,
        income_cap=cfg.income_cap,
        income_min_colony=2,
        pit_cost=cfg.pit_cost,
        trap_cost=cfg.trap_cost,
        crisis_energy=cfg.crisis_energy,
        crisis_cooldown=cfg.crisis_cooldown,
        size=cfg.size,
        max_energy=cfg.max_energy,
        food_value=cfg.food_value,
        food_every=cfg.food_every,
        predator_every=cfg.predator_every,
        max_think=cfg.max_think,
        report_every=cfg.report_every,
    )


def tick_prompt(obs: dict, ledger, notes: str, thoughts: list, reflex_status: str) -> str:
    parts = [
        "OBSERVATION",
        json.dumps(obs, separators=(",", ":")),
        "BUDGET",
        "tokens_left: %d (spent: %d, last call cost: %d)"
        % (ledger.remaining, ledger.spent, ledger.last_charge),
        "REFLEX",
        reflex_status,
        "NOTES",
        notes if notes else "(none)",
    ]
    if thoughts:
        parts.append("SELF-PROMPTS THIS TICK")
        for i, (q, a) in enumerate(thoughts, 1):
            parts.append("Q%d: %s" % (i, q))
            parts.append("A%d: %s" % (i, a))
    parts.append("Respond with one JSON object.")
    return "\n".join(parts)


def report_prompt(obs: dict, ledger, notes: str, tick: int, reflex_src: str = None) -> str:
    return REPORT_PROMPT.format(
        tick=tick,
        obs=json.dumps(obs, separators=(",", ":")),
        left=ledger.remaining,
        spent=ledger.spent,
        reflex=reflex_src if reflex_src else "(none installed)",
        notes=notes if notes else "(none)",
    )
