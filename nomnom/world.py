from __future__ import annotations

import random

DIRS = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0), "stay": (0, 0)}
ACTIONS = tuple(DIRS.keys())


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
        self.creature = (size // 2, size // 2)
        self.energy = start_energy
        self.alive = True
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
        occupied = (set(self.food) | {self.creature} | set(self.predators)
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

    def _rel(self, cell):
        return [cell[0] - self.creature[0], cell[1] - self.creature[1]]

    # ---- public --------------------------------------------------------

    def observe(self) -> dict:
        cx, cy = self.creature
        key = lambda d: (abs(d[0]) + abs(d[1]), d[0], d[1])  # noqa: E731  distance, then a fixed tie-break
        food = sorted((self._rel(f) for f in self.food), key=key)
        preds = sorted((self._rel(p) for p in self.predators), key=key)
        rocks = sorted((self._rel(r) for r in self.rocks), key=key)
        pits = sorted((self._rel(p) for p in self.pits), key=key)
        traps = sorted((self._rel(t) for t in self.known_traps), key=key)
        return {
            "tick": self.tick_no,
            "pos": [cx, cy],
            "grid": self.size,
            "energy": self.energy,
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
            "alive": self.alive,
        }

    def step(self, action: str) -> list:
        """Advance one tick. Returns a list of human-readable events."""
        if not self.alive:
            return ["dead"]
        events = []
        self.tick_no += 1
        dx, dy = DIRS.get(action, (0, 0))
        nx = min(max(self.creature[0] + dx, 0), self.size - 1)
        ny = min(max(self.creature[1] + dy, 0), self.size - 1)
        if self.blocked((nx, ny)):
            events.append("blocked by rock")
        elif (nx, ny) != self.creature:
            self.creature = (nx, ny)
            events.append("moved " + action)
            if self.creature in self.pits:
                self.energy -= self.pit_cost
                events.append("crossed a pit (-%d)" % self.pit_cost)
            if self.creature in self.traps:
                self.traps.discard(self.creature)
                self.known_traps.add(self.creature)
                self.energy -= self.trap_cost
                events.append("SPRUNG A TRAP (-%d)" % self.trap_cost)
        elif action != "stay":
            events.append("bumped wall")

        self._sense_traps()

        if self.creature in self.food:
            self.food.discard(self.creature)
            self.max_energy = self.current_max_energy()
            self.energy = min(self.energy + self.food_value, self.max_energy)
            self.eaten += 1
            events.append("ate food (+%d)" % self.food_value)

        self.energy -= 1

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

        if self.creature in self.predators:
            self.alive = False
            self.cause_of_death = "eaten by predator"
            events.append("EATEN BY PREDATOR")
            return events

        if self.tick_no % self.food_every == 0 and self._spawn_food():
            events.append("food spawned")

        if self.energy <= 0:
            self.energy = 0
            self.alive = False
            self.cause_of_death = "starved"
            events.append("STARVED")
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
                if c == self.creature:
                    row.append("@")
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
