def act(obs):
    import heapq
    g=obs["grid"];px,py=obs["pos"]
    R=lambda L:{(px+a,py+b) for a,b in (L or [])}
    rocks=R(obs.get("rocks"));pits=R(obs.get("pits"));traps=R(obs.get("traps_known"))
    pl=obs.get("predators") or ([obs["predator"]] if obs.get("predator") else [])
    preds=[(px+a,py+b) for a,b in pl]
    foods=[(px+a,py+b) for a,b in (obs.get("food") or [])]
    pc=obs.get("pit_cost",6);tc=obs.get("trap_cost",8)
    def cost(c):
        k=1
        if c in pits:k+=pc
        if c in traps:k+=tc
        return k
    def ok(c):
        return 0<=c[0]<g and 0<=c[1]<g and c not in rocks
    dist={}
    h=[(0,f) for f in foods if ok(f)]
    heapq.heapify(h)
    while h:
        d,c=heapq.heappop(h)
        if c in dist:continue
        dist[c]=d
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            n=(c[0]+dx,c[1]+dy)
            if ok(n) and n not in dist:
                heapq.heappush(h,(d+cost(c),n))
    moves={"n":(0,-1),"s":(0,1),"e":(1,0),"w":(-1,0),"stay":(0,0)}
    best=None;bs=-1e9
    for a,(dx,dy) in moves.items():
        c=(px+dx,py+dy)
        if not ok(c):continue
        pd=min([abs(c[0]-p[0])+abs(c[1]-p[1]) for p in preds] or [99])
        s=0
        if pd<=1:s-=1000
        elif pd==2:s-=60
        elif pd==3:s-=15
        s+=min(pd,6)*3
        s-=dist.get(c,50)*4
        if a!="stay":s-=(cost(c)-1)*3
        if best is None or s>bs:best,bs=a,s
    return best or "stay"