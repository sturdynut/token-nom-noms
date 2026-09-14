"""Stdlib-only tests: python3 -m unittest discover -s tests"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nomnom.brain import extract_json  # noqa: E402
from nomnom.ledger import Ledger  # noqa: E402
from nomnom.reflex import run_reflex  # noqa: E402
from nomnom.runtimes import CallResult, GREEDY_REFLEX  # noqa: E402
from nomnom.world import SPAWN, World, stage_for  # noqa: E402


class TestExtractJson(unittest.TestCase):
    def test_plain_object(self):
        self.assertEqual(extract_json('{"action": "n"}'), {"action": "n"})

    def test_fenced(self):
        self.assertEqual(extract_json('```json\n{"action": "s"}\n```'), {"action": "s"})

    def test_prose_before_and_after(self):
        self.assertEqual(extract_json('Let me think. {"action": "e"} That is my move.'),
                         {"action": "e"})

    def test_nested_object_survives(self):
        got = extract_json('{"action": "w", "notes": {"deep": [1, 2]}}')
        self.assertEqual(got["notes"], {"deep": [1, 2]})

    def test_no_json_returns_none(self):
        self.assertIsNone(extract_json("I decline to answer."))
        self.assertIsNone(extract_json(""))
        self.assertIsNone(extract_json(None))

    def test_bare_array_is_not_a_dict(self):
        self.assertIsNone(extract_json("[1, 2, 3]"))


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_ledger")
        os.makedirs(self.dir, exist_ok=True)

    def tearDown(self):
        for f in os.listdir(self.dir):
            os.remove(os.path.join(self.dir, f))
        os.rmdir(self.dir)

    def _charge(self, ledger, **kw):
        return ledger.record_call(tick=1, kind="tick", depth=0, runtime="t", model="m",
                                  system="s", prompt="p", res=CallResult(text="x", **kw))

    def test_cache_reads_are_discounted_and_writes_are_not(self):
        led = Ledger(1000, self.dir)
        self.assertEqual(self._charge(led, input_tokens=10, output_tokens=5,
                                      cache_read=100, cache_write=20), 10 + 5 + 20 + 10)

    def test_overdraft_is_reported_and_remaining_floors_at_zero(self):
        led = Ledger(100, self.dir)
        self._charge(led, input_tokens=250)
        self.assertEqual(led.remaining, 0)
        self.assertEqual(led.spent, 250)
        self.assertEqual(led.overdraft, 150)

    def test_no_overdraft_when_inside_budget(self):
        led = Ledger(100, self.dir)
        self._charge(led, input_tokens=40)
        self.assertEqual(led.overdraft, 0)
        self.assertEqual(led.remaining, 60)

    def test_every_call_is_written_to_the_log(self):
        led = Ledger(100, self.dir)
        self._charge(led, input_tokens=1)
        self._charge(led, input_tokens=1)
        with open(os.path.join(self.dir, "calls.jsonl")) as f:
            rows = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["budget_before"] - rows[0]["budget_after"], rows[0]["charged"])


class TestReflexSandbox(unittest.TestCase):
    def test_valid_reflex_returns_an_action(self):
        obs = {"food": [[2, 0]], "predator": [8, 8], "predators": [[8, 8]], "energy": 10}
        self.assertEqual(run_reflex(GREEDY_REFLEX, obs), ("e", None))

    def test_flees_a_close_predator(self):
        obs = {"food": [[2, 0]], "predator": [1, 0], "predators": [[1, 0]], "energy": 10}
        action, err = run_reflex(GREEDY_REFLEX, obs)
        self.assertIsNone(err)
        self.assertEqual(action, "w")

    def test_exception_is_reported_not_raised(self):
        action, err = run_reflex("def act(obs):\n    return 1 / 0\n", {})
        self.assertIsNone(action)
        self.assertIn("ZeroDivisionError", err)

    def test_missing_act_is_reported(self):
        action, err = run_reflex("x = 1\n", {})
        self.assertIsNone(action)
        self.assertIn("act(obs)", err)

    def test_infinite_loop_times_out(self):
        action, err = run_reflex("def act(obs):\n    while True:\n        pass\n", {}, timeout=1.0)
        self.assertIsNone(action)
        self.assertIn("timed out", err)


class TestWorld(unittest.TestCase):
    def test_same_seed_gives_the_same_world(self):
        a, b = World(seed=7), World(seed=7)
        for _ in range(20):
            self.assertEqual(a.observe(), b.observe())
            a.step("e")
            b.step("e")

    def test_observation_order_is_stable_for_tied_distances(self):
        """Ordering is load-bearing: reflexes pick with min(), which takes the first tie.

        Set iteration order is not stable across Python versions, so observe() must
        impose its own total order or logged runs stop replaying.
        """
        cells = [(5, 4), (4, 5), (6, 5), (5, 6)]  # all exactly one step from the centre
        seen = set()
        for order in ([0, 1, 2, 3], [3, 2, 1, 0], [2, 0, 3, 1]):
            w = World(seed=3, initial_food=0, predator=False)
            w.creature = (5, 5)
            w.food = {cells[i] for i in order}
            seen.add(tuple(tuple(f) for f in w.observe()["food"]))
        self.assertEqual(len(seen), 1, "insertion order leaked into the observation")
        only = list(seen)[0]
        self.assertEqual(list(only),
                         sorted(only, key=lambda d: (abs(d[0]) + abs(d[1]), d[0], d[1])))

    def test_energy_falls_every_tick_including_stay(self):
        w = World(seed=1, initial_food=0, predator=False)
        before = w.energy
        w.step("stay")
        self.assertEqual(w.energy, before - 1)

    def test_starvation_ends_the_run(self):
        w = World(seed=1, start_energy=2, initial_food=0, predator=False, drift_every=0)
        w.step("stay")
        w.step("stay")
        self.assertFalse(w.alive)
        self.assertEqual(w.cause_of_death, "starved")

    def test_drift_fires_on_schedule_and_only_four_times(self):
        w = World(seed=2, drift_every=5)
        kinds = []
        for t in range(1, 60):
            for e in w.step("stay" if w.alive else "stay"):
                if e.startswith("DRIFT: "):
                    kinds.append(w.drifts[-1]["kind"])
            if not w.alive:
                # Revive the body; this test only cares about the drift schedule.
                w.critters[0]["alive"] = True
                w.critters[0]["energy"] = 20
        self.assertEqual(len(kinds), 4)
        self.assertEqual(sorted(kinds), ["camping_predator", "fast_predator",
                                         "scarce_food", "second_predator"])

    def test_drift_disabled_means_no_drift(self):
        w = World(seed=2, drift_every=0, start_energy=500)
        for _ in range(60):
            w.step("stay")
        self.assertEqual(w.drifts, [])

    def test_second_predator_can_kill(self):
        w = World(seed=4, drift_every=0)
        w.predators = [(5, 5), (0, 0)]
        w.creature = (5, 4)
        w.step("s")
        self.assertFalse(w.alive)
        self.assertEqual(w.cause_of_death, "eaten by predator")

    def test_stage_growth_raises_the_ceiling_only_when_enabled(self):
        off = World(seed=1, stage_growth=False)
        on = World(seed=1, stage_growth=True)
        off.tick_no = on.tick_no = 40
        self.assertEqual(stage_for(40), "adult")
        self.assertEqual(off.current_max_energy(), off.base_max_energy)
        self.assertEqual(on.current_max_energy(), on.base_max_energy + 10)

    def test_creature_cannot_leave_the_grid(self):
        w = World(seed=1, size=5, initial_food=0, predator=False)
        w.creature = (0, 0)
        w.step("n")
        self.assertEqual(w.creature, (0, 0))
        w.step("w")
        self.assertEqual(w.creature, (0, 0))


class TestTerrain(unittest.TestCase):
    def _world(self, **kw):
        kw.setdefault("terrain_density", 0.15)
        return World(seed=11, **kw)

    def test_open_ground_by_default(self):
        w = World(seed=11)
        self.assertEqual((w.rocks, w.pits, w.traps), (set(), set(), set()))

    def test_terrain_is_generated_and_never_under_the_creature(self):
        w = self._world()
        self.assertTrue(w.rocks or w.pits or w.traps)
        for group in (w.rocks, w.pits, w.traps):
            self.assertNotIn(w.creature, group)
            for p in w.predators:
                self.assertNotIn(p, group)

    def test_the_grid_stays_walkable(self):
        for seed in range(1, 25):
            w = World(seed=seed, terrain_density=0.2)
            reachable = w._walkable_from(w.creature, w.rocks)
            self.assertGreaterEqual(reachable, 0.75 * (w.size * w.size - len(w.rocks)),
                                    "seed %d boxed the creature in" % seed)

    def test_rocks_block_the_creature(self):
        w = World(seed=11, initial_food=0, predator=False, drift_every=0)
        w.creature = (5, 5)
        w.rocks = {(5, 4)}
        events = w.step("n")
        self.assertEqual(w.creature, (5, 5))
        self.assertIn("blocked by rock", events)

    def test_pits_are_crossable_and_cost_energy(self):
        w = World(seed=11, initial_food=0, predator=False, drift_every=0, pit_cost=6)
        w.creature, w.pits = (5, 5), {(5, 4)}
        before = w.energy
        w.step("n")
        self.assertEqual(w.creature, (5, 4))
        self.assertEqual(w.energy, before - 6 - 1)  # pit, then the per-tick drain

    def test_an_unsensed_trap_fires_and_is_remembered(self):
        w = World(seed=11, initial_food=0, predator=False, drift_every=0, trap_cost=8)
        w.creature, w.traps = (5, 5), {(5, 1)}
        w.step("n")  # to (5,4): still two away, nothing sensed
        self.assertNotIn((5, 1), w.known_traps)
        before = w.energy
        w.step("n")  # to (5,3): now adjacent-but-one; sensing happens at Chebyshev 1
        w.step("n")  # to (5,2): senses the trap without firing it
        self.assertIn((5, 1), w.known_traps)
        self.assertIn((5, 1), w.traps, "sensing must not disarm the trap")
        w.step("n")  # step onto it
        self.assertNotIn((5, 1), w.traps)
        self.assertLess(w.energy, before - 3)

    def test_a_trap_stuns_a_predator_and_is_consumed(self):
        w = World(seed=11, initial_food=0, drift_every=0, predator_every=1)
        w.creature, w.predators, w.traps = (5, 5), [(3, 5)], {(4, 5)}
        w.step("stay")
        self.assertEqual(w.predators, [(4, 5)])
        self.assertNotIn((4, 5), w.traps)
        w.step("stay")
        self.assertEqual(w.predators, [(4, 5)], "the stunned predator should lose a move")
        w.step("stay")
        self.assertEqual(w.predators, [(5, 5)])

    def test_terrain_is_the_same_for_the_same_seed(self):
        a, b = self._world(), self._world()
        self.assertEqual((a.rocks, a.pits, a.traps), (b.rocks, b.pits, b.traps))

    def test_only_sensed_traps_are_observable(self):
        w = World(seed=11, initial_food=0, predator=False, drift_every=0)
        w.creature = (5, 5)
        w.traps = {(5, 4), (0, 0)}
        w._sense_traps()
        seen = {tuple(t) for t in w.observe()["traps_known"]}
        self.assertEqual(seen, {(0, -1)}, "a distant trap must stay hidden")


class TestColony(unittest.TestCase):
    def _w(self, **kw):
        kw.setdefault("spawning", True)
        kw.setdefault("initial_food", 0)
        kw.setdefault("predator", False)
        kw.setdefault("drift_every", 0)
        return World(seed=5, **kw)

    def test_spawning_off_by_default(self):
        w = World(seed=5)
        self.assertFalse(w.spawning)
        self.assertEqual(len(w.critters), 1)
        w.step(SPAWN)
        self.assertEqual(len(w.critters), 1, "no colony without the flag")

    def test_spawn_moves_energy_from_parent_to_child(self):
        w = self._w(start_energy=30, spawn_energy=10)
        w.step(SPAWN)
        self.assertEqual(len(w.living), 2)
        parent, child = w.critters[0], w.critters[1]
        # parent pays 10 and then every body pays the per-tick drain
        self.assertEqual(parent["energy"], 30 - 10 - 1)
        self.assertEqual(child["energy"], 10 - 1)

    def test_a_body_too_poor_to_spawn_does_not(self):
        w = self._w(start_energy=10, spawn_energy=10)
        events = w.step(SPAWN)
        self.assertEqual(len(w.living), 1)
        self.assertTrue(any("could not spawn" in e for e in events))

    def test_colony_is_capped(self):
        w = self._w(start_energy=30, max_colony=2)
        w.step(SPAWN)
        self.assertEqual(len(w.living), 2)
        w.step({0: SPAWN, 1: "stay"})
        self.assertEqual(len(w.living), 2, "cap must hold")

    def test_the_colony_outlives_one_body(self):
        w = self._w(start_energy=30)
        w.step(SPAWN)
        w.critters[1]["energy"] = 1
        w.step({0: "stay", 1: "stay"})
        self.assertFalse(w.critters[1]["alive"])
        self.assertTrue(w.alive, "the colony survives while the founder lives")
        self.assertEqual(w.deaths, 1)

    def test_a_lone_body_earns_nothing(self):
        w = self._w(start_energy=30)
        w.food = {(5, 4)}
        w.step("n")
        self.assertEqual(w.earned, 0)

    def test_a_pair_earns_on_every_meal(self):
        w = self._w(start_energy=30, income_per_food=400)
        w.step(SPAWN)
        w.critters[0]["pos"] = (5, 5)
        w.food = {(5, 4)}
        w.step({0: "n", 1: "stay"})
        self.assertEqual(w.earned, 400)
        self.assertEqual(w.earned_this_tick, 400)

    def test_earnings_stop_at_the_cap(self):
        w = self._w(start_energy=30, income_per_food=400, income_cap=500)
        w.step(SPAWN)
        for _ in range(4):
            w.critters[0]["energy"] = 30
            x, y = w.critters[0]["pos"]
            w.food = {(x, y - 1)}
            w.step({0: "n", 1: "stay"})
        self.assertEqual(w.earned, 500, "the cap is the cap")

    def test_every_body_is_asked_and_each_acts(self):
        w = self._w(start_energy=30)
        w.step(SPAWN)
        a, b = w.critters[0]["pos"], w.critters[1]["pos"]
        w.step({0: "s", 1: "s"})
        self.assertEqual(w.critters[0]["pos"], (a[0], a[1] + 1))
        self.assertEqual(w.critters[1]["pos"], (b[0], b[1] + 1))

    def test_json_string_body_ids_still_address_the_right_body(self):
        w = self._w(start_energy=30)
        w.step(SPAWN)
        before = w.critters[1]["pos"]
        w.step({"0": "stay", "1": "s"})
        self.assertEqual(w.critters[1]["pos"], (before[0], before[1] + 1))


class TestGameLoop(unittest.TestCase):
    """End-to-end through the real tick loop, with the zero-cost baseline as the brain."""

    def setUp(self):
        self.out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_runs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.out, ignore_errors=True)

    def _play(self, **kw):
        from nomnom.brain import Config, Game
        from nomnom.runtimes import make_runtime
        cfg = Config(runtime="baseline", out=self.out, quiet=True, ticks=30, seed=1, **kw)
        return Game(cfg, make_runtime("baseline")).run()

    def test_a_free_run_costs_nothing_and_still_plays(self):
        s = self._play()
        self.assertEqual(s["tokens_spent"], 0)
        self.assertEqual(s["overdraft"], 0)
        self.assertGreater(s["reflex_ticks"], 20)

    def test_crisis_interrupt_fires_when_energy_is_critical(self):
        s = self._play(start_energy=7, crisis_energy=5, crisis_cooldown=1, initial_food=0,
                       food_every=999, predator=False)
        self.assertGreater(s["crisis_calls"], 0,
                           "a starving creature on a reflex never got a paid re-think")

    def test_crisis_interrupt_can_be_disabled(self):
        s = self._play(start_energy=7, crisis_energy=0, initial_food=0,
                       food_every=999, predator=False)
        self.assertEqual(s["crisis_calls"], 0)

    def test_summary_and_logs_agree(self):
        from nomnom.validate import validate_run
        s = self._play()
        problems, _ = validate_run(s["run_dir"])
        self.assertEqual(problems, [])

    def test_a_new_run_validates_strictly(self):
        import json as _json
        s = self._play()
        with open(os.path.join(s["run_dir"], "config.json")) as f:
            cfg = _json.load(f)
        self.assertGreaterEqual(cfg["format"], 2)
        from nomnom.validate import validate_run
        _, notes = validate_run(s["run_dir"])
        self.assertFalse([n for n in notes if "not verified" in n],
                         "a freshly recorded run should be checked in full")


if __name__ == "__main__":
    unittest.main()
