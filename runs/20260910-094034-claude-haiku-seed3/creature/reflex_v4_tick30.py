def act(obs):
    if not obs['food']: return 'stay'
    food = min(obs['food'], key=lambda f: abs(f[0])+abs(f[1]))
    if obs['predators']:
        closest = min(obs['predators'], key=lambda p: abs(p[0])+abs(p[1]))
        if abs(closest[0])+abs(closest[1]) <= 2: return None
    if food[0] < 0: return 'w'
    elif food[0] > 0: return 'e'
    elif food[1] < 0: return 'n'
    elif food[1] > 0: return 's'
    return 'stay'