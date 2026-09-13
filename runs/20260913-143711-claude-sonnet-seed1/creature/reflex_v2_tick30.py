def act(obs):
    energy = obs['energy']
    food = obs.get('food') or []
    predator = obs.get('predator')
    rocks = set(tuple(r) for r in (obs.get('rocks') or []))
    traps = set(tuple(t) for t in (obs.get('traps_known') or []))
    pits = set(tuple(p) for p in (obs.get('pits') or []))
    blocked = rocks | traps
    dirs = {'n': (0, -1), 's': (0, 1), 'e': (1, 0), 'w': (-1, 0)}

    def dist(p):
        return abs(p[0]) + abs(p[1])

    def best_move(target, avoid_pits, maximize=False):
        best = None
        bestd = None
        for name, (ddx, ddy) in dirs.items():
            cell = (ddx, ddy)
            if cell in blocked:
                continue
            if avoid_pits and cell in pits:
                continue
            newp = (target[0] - ddx, target[1] - ddy)
            d = dist(newp)
            if maximize:
                if bestd is None or d > bestd:
                    bestd = d
                    best = name
            else:
                if bestd is None or d < bestd:
                    bestd = d
                    best = name
        return best

    if predator is not None and dist(predator) <= 3:
        m = best_move(predator, energy <= 10, maximize=True)
        if m:
            return m

    if food:
        target = min(food, key=dist)
        m = best_move(target, energy > 10)
        if m:
            return m
        m = best_move(target, False)
        if m:
            return m

    return 'stay'
