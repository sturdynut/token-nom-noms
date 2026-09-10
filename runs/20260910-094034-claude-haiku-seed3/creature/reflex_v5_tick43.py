def act(obs):
    food = obs.get('food', [])
    pred = obs.get('predator')
    energy = obs.get('energy', 0)
    if pred and abs(pred[0]) + abs(pred[1]) <= 2:
        if pred[0] > 0: return 'w'
        if pred[0] < 0: return 'e'
        if pred[1] > 0: return 'n'
        return 's'
    if food:
        closest = min(food, key=lambda f: abs(f[0]) + abs(f[1]))
        if abs(closest[0]) >= abs(closest[1]):
            return 'e' if closest[0] > 0 else 'w'
        else:
            return 's' if closest[1] > 0 else 'n'
    return 'stay'