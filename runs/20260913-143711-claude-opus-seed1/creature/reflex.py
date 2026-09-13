import heapq

def act(obs):
    px, py = obs["pos"]
    n = obs["grid"]
    def A(d):
        return (px + d[0], py + d[1])
    rocks = set(A(r) for r in obs.get("rocks") or [])
    pits = set(A(p) for p in obs.get("pits") or [])
    traps = set(A(t) for t in obs.get("traps_known") or [])
    foods = [A(f) for f in obs.get("food") or []]
    preds = [A(p) for p in (obs.get("predators") or [])]
    pc = obs.get("pit_cost", 6)
    tc = obs.get("trap_cost", 8)
    moves = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
    danger = {}
    for q in preds:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                d = abs(dx) + abs(dy)
                if d <= 2:
                    c = (q[0] + dx, q[1] + dy)
                    v = 200 if d == 0 else (40 if d == 1 else 12)
                    if v > danger.get(c, 0):
                        danger[c] = v
    def cost(c):
        v = 1
        if c in pits:
            v += pc
        if c in traps:
            v += tc
        return v + danger.get(c, 0)
    INF = float("inf")
    start = (px, py)
    dist = {start: 0}
    prev = {}
    pq = [(0, start)]
    while pq:
        d, c = heapq.heappop(pq)
        if d > dist.get(c, INF):
            continue
        for a, (dx, dy) in moves.items():
            nc = (c[0] + dx, c[1] + dy)
            if not (0 <= nc[0] < n and 0 <= nc[1] < n):
                continue
            if nc in rocks:
                continue
            nd = d + cost(nc)
            if nd < dist.get(nc, INF):
                dist[nc] = nd
                prev[nc] = (c, a)
                heapq.heappush(pq, (nd, nc))
    tgt = None
    best = INF
    for f in foods:
        if f != start and f in dist and dist[f] < best:
            best = dist[f]
            tgt = f
    if tgt is not None:
        cur = tgt
        while cur in prev and prev[cur][0] != start:
            cur = prev[cur][0]
        if cur in prev:
            return prev[cur][1]
    bestA = "stay"
    bestS = -INF
    for a, (dx, dy) in list(moves.items()) + [("stay", (0, 0))]:
        nc = (px + dx, py + dy)
        if not (0 <= nc[0] < n and 0 <= nc[1] < n):
            continue
        if nc in rocks:
            continue
        s = 0.0
        if preds:
            s = min(abs(nc[0] - q[0]) + abs(nc[1] - q[1]) for q in preds) * 10.0
        if nc in pits:
            s -= pc
        if nc in traps:
            s -= tc
        if a == "stay":
            s -= 1
        if s > bestS:
            bestS = s
            bestA = a
    return bestA
