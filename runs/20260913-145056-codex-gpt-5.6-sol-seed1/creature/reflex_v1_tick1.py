def act(obs):
    import heapq
    W = int(obs.get('grid', 10))
    px, py = obs['pos']
    energy = obs['energy']
    max_energy = obs['max_energy']
    pit_cost = obs.get('pit_cost', 6)
    trap_cost = obs.get('trap_cost', 8)

    def absolute(items):
        return {(px + int(dx), py + int(dy)) for dx, dy in (items or [])}

    rocks = absolute(obs.get('rocks', []))
    pits = absolute(obs.get('pits', []))
    traps = absolute(obs.get('traps_known', []))
    foods = absolute(obs.get('food', []))
    predators = absolute(obs.get('predators', []))
    if not predators and obs.get('predator') is not None:
        predators = absolute([obs['predator']])

    dirs = [('n', 0, -1), ('s', 0, 1), ('e', 1, 0), ('w', -1, 0), ('stay', 0, 0)]
    steps = [(0, -1), (0, 1), (1, 0), (-1, 0)]

    def valid(c):
        return 0 <= c[0] < W and 0 <= c[1] < W and c not in rocks

    def bfs_from(start):
        dist = {start: 0}
        q = [start]
        head = 0
        while head < len(q):
            x, y = q[head]
            head += 1
            for dx, dy in steps:
                n = (x + dx, y + dy)
                if valid(n) and n not in dist:
                    dist[n] = dist[(x, y)] + 1
                    q.append(n)
        return dist

    pred_maps = [bfs_from(p) for p in predators if valid(p)]

    def pred_dist(c):
        if not pred_maps:
            return 99
        return min(m.get(c, 99) for m in pred_maps)

    def route_to_food(start):
        if not foods:
            return 30.0
        heap = [(0.0, start)]
        best = {start: 0.0}
        while heap:
            cost, cell = heapq.heappop(heap)
            if cost != best.get(cell):
                continue
            if cell in foods:
                return cost
            x, y = cell
            for dx, dy in steps:
                n = (x + dx, y + dy)
                if not valid(n):
                    continue
                step_cost = 1.0
                if n in pits:
                    step_cost += pit_cost
                if n in traps:
                    step_cost += trap_cost
                pd = pred_dist(n)
                if pd == 0:
                    step_cost += 10000
                elif pd == 1:
                    step_cost += 500
                elif pd == 2:
                    step_cost += 35
                elif pd == 3:
                    step_cost += 7
                nc = cost + step_cost
                if nc < best.get(n, 1e30):
                    best[n] = nc
                    heapq.heappush(heap, (nc, n))
        return 1000.0

    candidates = []
    urgency = 2.8 if energy <= 10 else (1.7 if energy <= 18 else (0.9 if energy < max_energy - 3 else 0.35))
    for action, dx, dy in dirs:
        dest = (px + dx, py + dy)
        if not valid(dest):
            continue
        pd = pred_dist(dest)
        score = urgency * route_to_food(dest)
        if action == 'stay':
            score += 3.0
        if dest in pits:
            score += pit_cost * (2.2 if energy <= 14 else 1.2)
        if dest in traps:
            score += trap_cost * 2.0
        if dest in foods:
            score -= 30.0 if energy <= 14 else (15.0 if energy < max_energy - 2 else 4.0)
        if dest in predators or pd == 0:
            score += 1000000
        elif pd == 1:
            score += 100000
        elif pd == 2:
            score += 500
        elif pd == 3:
            score += 75
        elif pd == 4:
            score += 15
        score -= min(pd, 8) * 2.2
        mobility = 0
        safe_exits = 0
        for sx, sy in steps:
            nxt = (dest[0] + sx, dest[1] + sy)
            if valid(nxt):
                mobility += 1
                if pred_dist(nxt) >= 3 and nxt not in pits and nxt not in traps:
                    safe_exits += 1
        score -= mobility * 0.8 + safe_exits * 1.4
        if safe_exits == 0 and predators:
            score += 20
        candidates.append((score, -pd, action))

    if not candidates:
        return 'stay'
    candidates.sort()
    return candidates[0][2]