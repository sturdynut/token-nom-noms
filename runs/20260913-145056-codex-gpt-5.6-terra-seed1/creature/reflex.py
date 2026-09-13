def act(obs):
    x,y=obs['pos']; n=obs['grid']
    rocks={(x+a,y+b) for a,b in obs['rocks']}; pits={(x+a,y+b) for a,b in obs['pits']}; traps={(x+a,y+b) for a,b in obs['traps_known']}
    foods=[(x+a,y+b) for a,b in obs['food']]
    best=('stay',10**9)
    for a,dx,dy in [('n',0,-1),('s',0,1),('e',1,0),('w',-1,0),('stay',0,0)]:
        q=(x+dx,y+dy)
        if not(0<=q[0]<n and 0<=q[1]<n) or q in rocks or q in traps: continue
        danger=min((abs(px-dx)+abs(py-dy) for px,py in obs['predators']),default=99)
        food=min((abs(fx-q[0])+abs(fy-q[1]) for fx,fy in foods),default=20)
        cost=obs['pit_cost'] if q in pits else 0
        score=food*(20 if obs['energy']<=8 else 8)+cost+(60 if danger<2 else 18 if danger<3 else 0)
        if score<best[1]: best=(a,score)
    return best[0]