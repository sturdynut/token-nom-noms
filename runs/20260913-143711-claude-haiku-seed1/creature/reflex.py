def act(obs):
    pos = obs['pos']
    food = obs['food']
    rocks = set(tuple(r) for r in obs['rocks'])
    if not food:
        return 'stay'
    dx, dy = min(food, key=lambda f: abs(f[0]) + abs(f[1]))
    moves = []
    if abs(dx) >= abs(dy):
        if dx > 0:
            moves.append(((pos[0]+1, pos[1]), 'e'))
        elif dx < 0:
            moves.append(((pos[0]-1, pos[1]), 'w'))
        if dy > 0:
            moves.append(((pos[0], pos[1]+1), 's'))
        elif dy < 0:
            moves.append(((pos[0], pos[1]-1), 'n'))
    else:
        if dy > 0:
            moves.append(((pos[0], pos[1]+1), 's'))
        elif dy < 0:
            moves.append(((pos[0], pos[1]-1), 'n'))
        if dx > 0:
            moves.append(((pos[0]+1, pos[1]), 'e'))
        elif dx < 0:
            moves.append(((pos[0]-1, pos[1]), 'w'))
    for new_pos, action in moves:
        if new_pos not in rocks:
            return action
    return 'stay'