def act(obs):
 p=tuple(obs['pos']); n=obs['grid']; E=obs['energy']
 R={(p[0]+a,p[1]+b) for a,b in obs['rocks']}; P={(p[0]+a,p[1]+b) for a,b in obs['pits']}; T={(p[0]+a,p[1]+b) for a,b in obs['traps_known']}; F={(p[0]+a,p[1]+b) for a,b in obs['food']}; Z=[(p[0]+a,p[1]+b) for a,b in obs['predators']]
 ds=[('n',(0,-1)),('s',(0,1)),('e',(1,0)),('w',(-1,0)),('stay',(0,0))]
 def ok(q): return 0<=q[0]<n and 0<=q[1]<n and q not in R
 def foodcost(s):
  if not F:return 40
  d={s:0}; seen=set()
  while d:
   u=min((x for x in d if x not in seen),key=lambda x:d[x],default=None)
   if u is None:break
   if u in F:return d[u]
   seen.add(u)
   for a,b in ((0,-1),(0,1),(1,0),(-1,0)):
    v=(u[0]+a,u[1]+b)
    if ok(v):
     z=d[u]+1+(obs['pit_cost'] if v in P else 0)+(obs['trap_cost'] if v in T else 0)
     if z<d.get(v,999):d[v]=z
  return 60
 best='stay'; bs=-10**9
 for name,(a,b) in ds:
  q=(p[0]+a,p[1]+b)
  if not ok(q):continue
  c=foodcost(q); danger=min((abs(q[0]-z[0])+abs(q[1]-z[1]) for z in Z),default=12)
  if danger<=2:score=35*danger-c
  elif E<=10:score=6*danger-5*c
  else:score=11*danger-2*c
  if q in P:score-=obs['pit_cost']*2
  if q in T:score-=obs['trap_cost']*2
  if score>bs:best,bs=name,score
 return best