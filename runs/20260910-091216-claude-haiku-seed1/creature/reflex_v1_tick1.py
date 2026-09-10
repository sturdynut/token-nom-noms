def act(obs):
    food = obs['food']
    predator = obs['predator']
    if abs(predator[0]) <= 1 and abs(predator[1]) <= 1 and predator != [0, 0]:
        if predator[0] < 0:
            return 'e'
        elif predator[0] > 0:
            return 'w'
        elif predator[1] < 0:
            return 's'
        else:
            return 'n'
    if food:
        closest = min(food, key=lambda f: abs(f[0]) + abs(f[1]))
        dx, dy = closest
        if abs(dx) > abs(dy):
            return 'e' if dx > 0 else 'w'
        else:
            return 's' if dy > 0 else 'n'
    return 'stay'