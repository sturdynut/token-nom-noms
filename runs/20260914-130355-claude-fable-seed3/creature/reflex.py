def act(obs):
    from collections import deque
    g=obs["grid"];px,py=obs["pos"]
    blk=set()
    for r in obs["rocks"]+obs["pits"]+obs["traps_known"]:blk.add((r[0],r[1]))
    for c in obs["colony"]:blk.add((c["rel"][0],c["rel"][1]))
    preds=[(p[0],p[1]) for p in obs["predators"]]
    foods=set((f[0],f[1]) for f in obs["food"])
    def ok(x,y):return 0<=px+x<g and 0<=py+y<g and (x,y) not in blk
    def pd(x,y):return min([abs(x-a)+abs(y-b) for a,b in preds] or [99])
    dist={};dq=deque()
    for f in foods:
        if ok(*f):dist[f]=0;dq.append(f)
    while dq:
        x,y=dq.popleft()
        for dx,dy in ((0,1),(0,-1),(1,0),(-1,0)):
            n=(x+dx,y+dy)
            if ok(*n) and n not in dist and pd(*n)>=2:
                dist[n]=dist[(x,y)]+1;dq.append(n)
    e=obs["energy"]
    w=10 if e<=15 else 2
    moves={"n":(0,-1),"s":(0,1),"e":(1,0),"w":(-1,0),"stay":(0,0)}
    best="stay";bs=None
    for a,(dx,dy) in moves.items():
        if a!="stay" and not ok(dx,dy):continue
        d=pd(dx,dy);fd=dist.get((dx,dy),50)
        if d<=1:s=-1000+d
        elif d==2:s=40-fd*w
        else:s=100-fd*w+min(d,6)
        if bs is None or s>bs:bs=s;best=a
    if e>=24 and obs["colony_size"]<3 and obs["budget"]>8000 and obs["earned"]<obs["income_cap"] and pd(0,0)>=4:
        for dx,dy in ((0,1),(0,-1),(1,0),(-1,0)):
            if ok(dx,dy):return "spawn"
    return best