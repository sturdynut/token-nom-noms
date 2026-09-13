STEPS = {'n': (0, -1), 's': (0, 1), 'e': (1, 0), 'w': (-1, 0)}


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
