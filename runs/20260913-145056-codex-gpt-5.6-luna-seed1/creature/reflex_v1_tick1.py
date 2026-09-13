def act(o):
    ds={'n':(0,-1),'s':(0,1),'e':(1,0),'w':(-1,0)}
    rocks={tuple(p) for p in o.get('rocks',[])}
    pits={tuple(p) for p in o.get('pits',[])}
    traps={tuple(p) for p in o.get('traps_known',[])}
    foods={tuple(p) for p in o.get('food',[])}
    preds=[tuple(p) for p in o.get('predators',[])]
    x,y=o['pos']; g=o['grid']
    def valid(p,pit=False):
        if not(-x<=p[0]<g-x and -y<=p[1]<g-y): return False
        return p not in rocks and p not in traps and (pit or p not in pits)
    def path(allow_pit):
        q=[(0,0)]; prev={(0,0):None}; move={}
        for p in q:
            if p in foods:
                out=[]
                while prev[p] is not None:
                    out.append(move[p]); p=prev[p]
                return out[::-1]
            for a,(dx,dy) in ds.items():
                n=(p[0]+dx,p[1]+dy)
                if n not in prev and valid(n,allow_pit) and not any(abs(n[0]-px)+abs(n[1]-py)<=1 for px,py in preds):
                    prev[n]=p; move[n]=a; q.append(n)
        return None
    danger=min([abs(px)+abs(py) for px,py in preds] or [99])
    if danger<=3:
        cand=[]
        for a,(dx,dy) in ds.items():
            p=(dx,dy)
            if valid(p,False) or valid(p,True):
                d=min([abs(p[0]-px)+abs(p[1]-py) for px,py in preds] or [99])
                cand.append((d, p not in pits, a))
        if cand: return max(cand)[2]
    p=path(False) or path(True)
    if p: return p[0]
    for a,(dx,dy) in ds.items():
        if valid((dx,dy),False): return a
    return 'stay'