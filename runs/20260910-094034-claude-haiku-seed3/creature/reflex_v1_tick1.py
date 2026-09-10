def act(obs):
    food = obs['food']
    if not food:
        return 'stay'
    closest = min(food, key=lambda f: abs(f[0]) + abs(f[1]))
    fx, fy = closest
    if abs(fx) > abs(fy):
        return 'e' if fx > 0 else 'w'
    else:
        return 'n' if fy < 0 else 's'