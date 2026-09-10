def act(obs):
    energy = obs.get('energy', 0)
    food = obs.get('food', [])
    predators = obs.get('predators', [])
    if energy < 8:
        if food:
            f = min(food, key=lambda x: abs(x[0]) + abs(x[1]))
            if f[0] > 0: return 'e'
            if f[0] < 0: return 'w'
            return 's' if f[1] > 0 else 'n'
        return 'stay'
    if predators:
        p = min(predators, key=lambda x: abs(x[0]) + abs(x[1]))
        dist = abs(p[0]) + abs(p[1])
        if dist < 2:
            if abs(p[0]) > abs(p[1]):
                return 'w' if p[0] > 0 else 'e'
            else:
                return 'n' if p[1] > 0 else 's'
    if food:
        f = min(food, key=lambda x: abs(x[0]) + abs(x[1]))
        if f[0] > 0: return 'e'
        if f[0] < 0: return 'w'
        return 's' if f[1] > 0 else 'n'
    return 'stay'