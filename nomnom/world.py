from __future__ import annotations

import random

DIRS = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0), "stay": (0, 0)}
SPAWN = "spawn"
ACTIONS = tuple(DIRS.keys()) + (SPAWN,)


def stage_for(age: int) -> str:
    if age < 15:
        return "hatchling"
    if age < 35:
        return "juvenile"
    return "adult"


class World:
    """A small grid with food, one slow predator, and a creature that gets hungry."""

    def __init__(
        self,
        seed: int,
        size: int = 10,
        start_energy: int = 20,
        max_energy: int = 30,
        food_value: int = 8,
        initial_food: int = 4,
        food_every: int = 2,
        predator: bool = True,
        predator_every: int = 2,
        drift_every: int = 15,
        stage_growth: bool = False,
        terrain_density: float = 0.0,
        pit_cost: int = 6,
        trap_cost: int = 8,
        spawning: bool = False,
        spawn_energy: int = 10,
        max_colony: int = 6,
        income_per_food: int = 400,
        income_cap: int = 20000,
        income_min_colony: int = 2,
    ):
        self.rng = random.Random(seed)
        self.size = size
        self.base_max_energy = max_energy
        self.max_energy = max_energy
        self.stage_growth = stage_growth
        self.food_value = food_value
        self.food_every = food_every
        self.predator_every = predator_every

        self.tick_no = 0
        self.spawning = spawning
        self.spawn_energy = spawn_energy
        self.max_colony = max_colony
        self.income_per_food = income_per_food
        self.income_cap = income_cap
        self.income_min_colony = income_min_colony
        self.earned = 0
        self.earned_this_tick = 0
        self.spawns = 0
        self.deaths = 0
        self.peak_colony = 1
        self._next_id = 1
        # One colony, many bodies. The colony lives while any body does.
        self.critters = [{"id": 0, "pos": (size // 2, size // 2), "energy": start_energy,
                          "alive": True, "born": 0}]
        self.cause_of_death = None
        self.eaten = 0
        self.pit_cost = pit_cost
        self.trap_cost = trap_cost
        self.rocks: set = set()
        self.pits: set = set()
        self.traps: set = set()
        self.known_traps: set = set()
        self.food: set = set()
        self.predators = [(0, 0)] if predator else []
        self.predator_mode = "hunt"
        self._stunned: set = set()
        self.drift_every = drift_every
        self.drifts = []
        self._drift_pool = ["fast_predator", "scarce_food", "second_predator", "camping_predator"]
        if drift_every:
            self.rng.shuffle(self._drift_pool)
        else:
            self._drift_pool = []

        if terrain_density > 0:
            self._build_terrain(terrain_density)
        self._sense_traps()

        for _ in range(initial_food):
            self._spawn_food()

    # ---- helpers -------------------------------------------------------

    def _build_terrain(self, density: float):
        """Scatter rocks, pits and hidden traps, keeping the grid walkable.

        Rocks are walls. Pits are visible and crossable at a price, so they are a
        decision rather than a barrier. Traps are invisible until sensed, which is
        the only thing in this world that rewards remembering where you have been.
        """
        cells = [(x, y) for x in range(self.size) for y in range(self.size)]
        spawn = {self.creature} | set(self.predators)
        # Keep a ring around the creature clear so nothing starts boxed in.
        cx, cy = self.creature
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                spawn.add((cx + dx, cy + dy))
        free = [c for c in cells if c not in spawn]
        total = max(3, int(round(len(cells) * density)))
        for attempt in range(40):
            picks = self.rng.sample(free, min(total, len(free)))
            rocks = set(picks[: max(1, total // 2)])
            if self._walkable_from(self.creature, rocks) >= 0.75 * (len(cells) - len(rocks)):
                rest = picks[len(rocks):]
                half = len(rest) // 2
                self.rocks = rocks
                self.pits = set(rest[:half])
                self.traps = set(rest[half:])
                return
        # Every layout boxed the creature in; play on open ground rather than cheat.
        self.rocks, self.pits, self.traps = set(), set(), set()

    def _walkable_from(self, start, rocks) -> int:
        seen, stack = {start}, [start]
        while stack:
            x, y = stack.pop()
            for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
                c = (x + dx, y + dy)
                if (0 <= c[0] < self.size and 0 <= c[1] < self.size
                        and c not in rocks and c not in seen):
                    seen.add(c)
                    stack.append(c)
        return len(seen)

    def _sense_traps(self):
        """Traps in the eight cells around the creature are noticed without firing."""
        cx, cy = self.creature
        for t in self.traps:
            if abs(t[0] - cx) <= 1 and abs(t[1] - cy) <= 1:
                self.known_traps.add(t)

    def blocked(self, cell) -> bool:
        return cell in self.rocks

    @property
    def living(self):
        return [c for c in self.critters if c["alive"]]

    @property
    def alive(self) -> bool:
        return bool(self.living)

    @property
    def creature(self):
        """Position of the lead body: the oldest one still alive."""
        live = self.living
        return live[0]["pos"] if live else self.critters[0]["pos"]

    @creature.setter
    def creature(self, pos):
        (self.living or self.critters)[0]["pos"] = tuple(pos)

    @property
    def energy(self) -> int:
        # After a death this must keep reporting what the body had, not zero: a creature
        # taken by a predator still had energy, and the logs record that.
        return (self.living or self.critters)[0]["energy"]

    @energy.setter
    def energy(self, v):
        (self.living or self.critters)[0]["energy"] = v

    def by_id(self, cid):
        for c in self.critters:
            if c["id"] == cid:
                return c
        return None

    def current_max_energy(self) -> int:
        """Growing up raises the energy ceiling, so the stage label means something."""
        if not self.stage_growth:
            return self.base_max_energy
        return self.base_max_energy + {"hatchling": 0, "juvenile": 5, "adult": 10}[stage_for(self.tick_no)]

    @property
    def predator(self):
        """Nearest predator, or None. Kept so reflexes written before drift keep working."""
        if not self.predators:
            return None
        cx, cy = self.creature
        return min(sorted(self.predators), key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))

    def _empty_cells(self):
        occupied = (set(self.food) | {c["pos"] for c in self.critters} | set(self.predators)
                    | self.rocks | self.pits | self.traps)
        return [
            (x, y)
            for x in range(self.size)
            for y in range(self.size)
            if (x, y) not in occupied
        ]

    def _spawn_food(self) -> bool:
        cells = self._empty_cells()
        if not cells:
            return False
        self.food.add(self.rng.choice(cells))
        return True

    def _rel(self, cell, origin=None):
        ox, oy = origin if origin is not None else self.creature
        return [cell[0] - ox, cell[1] - oy]

    # ---- public --------------------------------------------------------

    def observe(self, cid: int = None) -> dict:
        me = self.by_id(cid) if cid is not None else (self.living or self.critters)[0]
        cx, cy = me["pos"]
        key = lambda d: (abs(d[0]) + abs(d[1]), d[0], d[1])  # noqa: E731  distance, then a fixed tie-break
        rel = lambda c: self._rel(c, (cx, cy))  # noqa: E731
        food = sorted((rel(f) for f in self.food), key=key)
        preds = sorted((rel(p) for p in self.predators), key=key)
        rocks = sorted((rel(r) for r in self.rocks), key=key)
        pits = sorted((rel(p) for p in self.pits), key=key)
        traps = sorted((rel(t) for t in self.known_traps), key=key)
        obs = {
            "tick": self.tick_no,
            "pos": [cx, cy],
            "grid": self.size,
            "energy": me["energy"],
            "max_energy": self.current_max_energy(),
            "stage": stage_for(self.tick_no),
            "food": food,
            "predator": preds[0] if preds else None,
            "predators": preds,
            "rocks": rocks,
            "pits": pits,
            "traps_known": traps,
            "pit_cost": self.pit_cost,
            "trap_cost": self.trap_cost,
        }
        if self.spawning:
            obs["id"] = me["id"]
            obs["colony"] = [{"id": c["id"], "rel": rel(c["pos"]), "energy": c["energy"]}
                             for c in self.living if c["id"] != me["id"]]
            obs["colony_size"] = len(self.living)
            obs["max_colony"] = self.max_colony
            obs["spawn_energy"] = self.spawn_energy
            obs["earned"] = self.earned
            obs["income_cap"] = self.income_cap
            obs["income_per_food"] = self.income_per_food
            obs["income_min_colony"] = self.income_min_colony
        return obs

    def _spawn_at(self, parent) -> bool:
        """Put a new body next to a parent. Fails if it is boxed in or the colony is full."""
        if len(self.living) >= self.max_colony:
            return False
        if parent["energy"] <= self.spawn_energy:
            return False
        px, py = parent["pos"]
        taken = {c["pos"] for c in self.critters if c["alive"]} | set(self.predators)
        for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
            cell = (px + dx, py + dy)
            if not (0 <= cell[0] < self.size and 0 <= cell[1] < self.size):
                continue
            if cell in self.rocks or cell in taken or cell in self.pits or cell in self.traps:
                continue
            parent["energy"] -= self.spawn_energy
            self.critters.append({"id": self._next_id, "pos": cell,
                                  "energy": self.spawn_energy, "alive": True, "born": self.tick_no})
            self._next_id += 1
            self.spawns += 1
            self.peak_colony = max(self.peak_colony, len(self.living))
            return True
        return False

    def _apply_drift(self) -> str:
        if not self._drift_pool:
            return None
        kind = self._drift_pool.pop(0)
        if kind == "fast_predator":
            self.predator_every = 1
            detail = "predators now move every tick"
        elif kind == "scarce_food":
            self.food_every, self.food_value = 4, 5
            detail = "food now spawns every 4 ticks and is worth 5"
        elif kind == "second_predator":
            cx, cy = self.creature
            corners = [(0, 0), (0, self.size - 1), (self.size - 1, 0), (self.size - 1, self.size - 1)]
            open_corners = [c for c in corners if not self.blocked(c)] or corners
            far = max(open_corners, key=lambda c: abs(c[0] - cx) + abs(c[1] - cy))
            self.rocks.discard(far)
            self.predators.append(far)
            self.food.discard(far)
            detail = "a second predator appeared at %s" % list(far)
        else:
            self.predator_mode = "camp"
            detail = "predators now camp the nearest food instead of chasing you"
        self.drifts.append({"tick": self.tick_no, "kind": kind, "detail": detail})
        return "DRIFT: " + detail

    def state(self) -> dict:
        """Absolute positions after the last step, for renderers."""
        return {
            "pos": list(self.creature),
            "predator": list(self.predator) if self.predator is not None else None,
            "predators": [list(p) for p in self.predators],
            "predator_mode": self.predator_mode,
            "rocks": sorted(list(r) for r in self.rocks),
            "pits": sorted(list(p) for p in self.pits),
            "traps_known": sorted(list(t) for t in self.known_traps),
            "food": sorted(list(f) for f in self.food),
            "energy": self.energy,
            "max_energy": self.current_max_energy(),
            "alive": self.alive,
            "critters": [{"id": c["id"], "pos": list(c["pos"]), "energy": c["energy"],
                          "alive": c["alive"]} for c in self.critters],
            "earned": self.earned,
        }

    def step(self, actions) -> list:
        """Advance one tick.

        `actions` is either a single action string, for a one-body world, or a mapping of
        body id to action. Phase order is unchanged from the single-body game so that
        every run recorded before colonies existed still replays exactly.
        """
        if not self.alive:
            return ["dead"]
        events = []
        self.tick_no += 1
        self.earned_this_tick = 0
        if isinstance(actions, str):
            actions = {self.living[0]["id"]: actions}
        else:
            # A log round-trips through JSON, which stringifies the integer body ids.
            actions = {int(k): v for k, v in actions.items()}
        many = len(self.living) > 1
        tag = lambda c, msg: ("#%d %s" % (c["id"], msg)) if many else msg  # noqa: E731

        # --- act: move, or spend energy to put another body on the board ---------
        for c in list(self.living):
            action = actions.get(c["id"], "stay")
            if action == SPAWN:
                if self.spawning and self._spawn_at(c):
                    events.append(tag(c, "spawned a new body"))
                else:
                    events.append(tag(c, "could not spawn"))
                continue
            dx, dy = DIRS.get(action, (0, 0))
            nx = min(max(c["pos"][0] + dx, 0), self.size - 1)
            ny = min(max(c["pos"][1] + dy, 0), self.size - 1)
            if self.blocked((nx, ny)):
                events.append(tag(c, "blocked by rock"))
            elif (nx, ny) != c["pos"]:
                c["pos"] = (nx, ny)
                events.append(tag(c, "moved " + action))
                if c["pos"] in self.pits:
                    c["energy"] -= self.pit_cost
                    events.append(tag(c, "crossed a pit (-%d)" % self.pit_cost))
                if c["pos"] in self.traps:
                    self.traps.discard(c["pos"])
                    self.known_traps.add(c["pos"])
                    c["energy"] -= self.trap_cost
                    events.append(tag(c, "SPRUNG A TRAP (-%d)" % self.trap_cost))
            elif action != "stay":
                events.append(tag(c, "bumped wall"))

        self._sense_traps()

        # --- eat, and earn once the colony is big enough to forage as a group ----
        for c in self.living:
            if c["pos"] in self.food:
                self.food.discard(c["pos"])
                self.max_energy = self.current_max_energy()
                c["energy"] = min(c["energy"] + self.food_value, self.max_energy)
                self.eaten += 1
                events.append(tag(c, "ate food (+%d)" % self.food_value))
                if (self.spawning and len(self.living) >= self.income_min_colony
                        and self.earned < self.income_cap):
                    gain = min(self.income_per_food, self.income_cap - self.earned)
                    self.earned += gain
                    self.earned_this_tick += gain
                    events.append("earned %d tokens" % gain)

        for c in self.living:
            c["energy"] -= 1

        if self.predators and self.tick_no % self.predator_every == 0:
            moved = []
            for (px, py) in self.predators:
                if (px, py) in self._stunned:
                    self._stunned.discard((px, py))
                    moved.append((px, py))
                    continue
                target = self.creature
                if self.predator_mode == "camp" and self.food:
                    target = min(sorted(self.food), key=lambda f: abs(f[0] - px) + abs(f[1] - py))
                tx, ty = target
                step = (px + ((tx > px) - (tx < px)), py) if abs(tx - px) >= abs(ty - py) \
                    else (px, py + ((ty > py) - (ty < py)))
                if self.blocked(step):
                    # Try the other axis before giving up, so a rock diverts rather than parks it.
                    alt = (px, py + ((ty > py) - (ty < py))) if abs(tx - px) >= abs(ty - py) \
                        else (px + ((tx > px) - (tx < px)), py)
                    step = (px, py) if self.blocked(alt) else alt
                if step in self.traps:
                    self.traps.discard(step)
                    self._stunned.add(step)
                    events.append("a predator sprang a trap")
                moved.append(step)
            self.predators = moved
            events.append("predator moved" if len(moved) == 1 else "predators moved")

        eaten_up = [c for c in self.living if c["pos"] in self.predators]
        for c in eaten_up:
            c["alive"] = False
            self.deaths += 1
            events.append(tag(c, "EATEN BY PREDATOR"))
        if not self.living:
            self.cause_of_death = "eaten by predator"
            return events

        if self.tick_no % self.food_every == 0 and self._spawn_food():
            events.append("food spawned")

        starved = [c for c in self.living if c["energy"] <= 0]
        for c in starved:
            c["energy"] = 0
            c["alive"] = False
            self.deaths += 1
            events.append(tag(c, "STARVED"))
        if not self.living:
            self.cause_of_death = "starved"
            return events

        if self.drift_every and self.tick_no % self.drift_every == 0:
            d = self._apply_drift()
            if d:
                events.append(d)
        return events

    def render(self) -> str:
        rows = []
        for y in range(self.size):
            row = []
            for x in range(self.size):
                c = (x, y)
                here = [k for k in self.living if k["pos"] == c]
                if here:
                    row.append("@" if here[0]["id"] == 0 else str(here[0]["id"] % 10))
                elif c in self.predators:
                    row.append("P")
                elif c in self.food:
                    row.append("*")
                elif c in self.rocks:
                    row.append("#")
                elif c in self.pits:
                    row.append("O")
                elif c in self.known_traps:
                    row.append("^")
                else:
                    row.append(".")
            rows.append(" ".join(row))
        return "\n".join(rows)
