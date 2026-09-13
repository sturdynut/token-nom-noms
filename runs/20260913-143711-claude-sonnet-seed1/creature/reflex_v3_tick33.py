import heapq

def act(obs):
    energy = obs.get('energy', 0)
    food = set(tuple(f) for f in obs.get('food', []))
    rocks = set(tuple(r) for r in obs.get('rocks', []))
    traps = set(tuple(t) for t in obs.get('traps_known', []))
    pits = set(tuple(p) for p in obs.get('pits', []))
    predator = obs.get('predator')
    moves = [('n',0,-1),('s',0,1),('e',1,0),('w',-1,0)]

    # Flee if predator adjacent
    if predator is not None:
        pdx, pdy = predator[0], predator[1]
        if abs(pdx) + abs(pdy) <= 1:
            best = None; bestd = -1
            for a, dx, dy in moves:
                if (dx, dy) in rocks:
                    continue
                nd = abs(pdx-dx) + abs(pdy-dy)
                if nd > bestd:
                    bestd = nd; best = a
            if best:
                return best

    if not food:
        return 'stay'

    # Dijkstra from (0,0) to nearest food, avoiding rocks, weighting traps/pits
    dist = {(0,0): 0}
    prev = {}
    pq = [(0, (0,0))]
    visited = set()
    target = None
    limit = 12
    while pq:
        d, cur = heapq.heappop(pq)
        if cur in visited:
            continue
        visited.add(cur)
        if cur in food and cur != (0,0):
            target = cur
            break
        if abs(cur[0]) > limit or abs(cur[1]) > limit:
            continue
        for a, dx, dy in moves:
            npos = (cur[0]+dx, cur[1]+dy)
            if npos in rocks:
                continue
            cost = 1
            if npos in traps:
                cost = 8
            elif npos in pits:
                cost = 6
            nd = d + cost
            if npos not in dist or nd < dist[npos]:
                dist[npos] = nd
                prev[npos] = (cur, a)
                heapq.heappush(pq, (nd, npos))

    if target is None:
        return 'stay'

    node = target
    path = []
    while node != (0,0):
        p, a = prev[node]
        path.append(a)
        node = p
    path.reverse()
    return path[0] if path else 'stay'
