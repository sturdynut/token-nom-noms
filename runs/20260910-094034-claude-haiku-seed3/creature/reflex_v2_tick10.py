def act(obs):
    if not obs['food']:
        return None
    food = min(obs['food'], key=lambda f: f[0]**2 + f[1]**2)
    dx, dy = food
    if abs(dx) > abs(dy):
        return 'w' if dx < 0 else 'e'
    else:
        return 'n' if dy < 0 else 's'