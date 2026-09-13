def act(obs):
    preds = obs.get('predators') or ([obs['predator']] if obs.get('predator') else [])
    for p in preds:
        if abs(p[0]) + abs(p[1]) <= 2:
            dx, dy = -p[0], -p[1]
            return 'e' if dx > 0 else 'w' if dx < 0 else 's' if dy > 0 else 'n'
    food = obs.get('food') or []
    if not food:
        return 'stay'
    dx, dy = food[0]
    if abs(dx) >= abs(dy):
        return 'e' if dx > 0 else 'w'
    return 's' if dy > 0 else 'n'
