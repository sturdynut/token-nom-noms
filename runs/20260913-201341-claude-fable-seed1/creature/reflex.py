def act(obs):
    from collections import deque
    g=obs['grid'];px,py=obs['pos'];e=obs['energy']
    rocks=set(map(tuple,obs['rocks']));pits=set(map(tuple,obs['pits']));traps=set(map(tuple,obs['traps_known']))
    preds=[tuple(p) for p in obs['predators']]
    others=set(tuple(c['rel']) for c in obs['colony'])
    food=set(map(tuple,obs['food']))
    dirs={'n':(0,-1),'s':(0,1),'e':(1,0),'w':(-1,0)}
    def inb(c): return 0<=px+c[0]<g and 0<=py+c[1]<g
    def bad(c): return c in rocks or c in traps or c in others
    def danger(c): return any(abs(c[0]-p[0])<=1 and abs(c[1]-p[1])<=1 for p in preds)
    if obs['colony_size']<3 and e>=22 and not danger((0,0)):
        for d in dirs.values():
            if inb(d) and not bad(d) and d not in pits and not danger(d): return 'spawn'
    def bfs(allow_pits):
        s=(0,0);prev={s:None};q=deque([s])
        while q:
            c=q.popleft()
            if c in food and c!=s:
                while prev[c]!=s: c=prev[c]
                for k,d in dirs.items():
                    if d==c: return k
            for d in dirs.values():
                n=(c[0]+d[0],c[1]+d[1])
                if n in prev or not inb(n) or bad(n) or danger(n): continue
                if n in pits and not allow_pits: continue
                prev[n]=c;q.append(n)
        return None
    r=bfs(False)
    if r: return r
    if e>12:
        r=bfs(True)
        if r: return r
    best=None;bs=-1
    for k,d in dirs.items():
        if not inb(d) or bad(d) or d in pits: continue
        s=min([abs(d[0]-p[0])+abs(d[1]-p[1]) for p in preds]+[9])
        if s>bs: bs=s;best=k
    if preds and danger((0,0)) and best: return best
    return 'stay'