def act(obs):
    pos = obs['pos']
    energy = obs['energy']
    food = obs.get('food') or []
    predator = obs.get('predator')
    rocks = set(tuple(r) for r in (obs.get('rocks') or []))
    traps = set(tuple(t) for t in (obs.get('traps_known') or []))
    pits = set(tuple(p) for p in (obs.get('pits') or []))
    blocked = rocks | traps

    def dist(p):
        return abs(p[0]) + abs(p[1])

    def move_options(dx, dy):
        opts = []
        if dx > 0:
            opts.append(('e', (1, 0)))
        elif dx < 0:
            opts.append(('w', (-1, 0)))
        if dy > 0:
            opts.append(('s', (0, 1)))
        elif dy < 0:
            opts.append(('n', (0, -1)))
        return opts

    def try_moves(dx, dy, avoid_pits=True):
        opts = move_options(dx, dy)
        opts.sort(key=lambda o: -abs(dx) if o[0] in ('e', 'w') else -abs(dy))
        for act_name, cell in opts:
            if cell in blocked:
                continue
            if avoid_pits and cell in pits:
                continue
            return act_name
        for act_name, cell in opts:
            if cell in blocked:
                continue
            return act_name
        return None

    if predator is not None:
        pdx, pdy = predator
        if dist(predator) <= 3:
            dx = -1 if pdx > 0 else (1 if pdx < 0 else 0)
            dy = -1 if pdy > 0 else (1 if pdy < 0 else 0)
            act_name = try_moves(dx, dy, avoid_pits=(energy > 10))
            if act_name:
                return act_name

    if food:
        target = min(food, key=dist)
        dx, dy = target
        act_name = try_moves(dx, dy, avoid_pits=(energy > 10))
        if act_name:
            return act_name

    return 'stay'
