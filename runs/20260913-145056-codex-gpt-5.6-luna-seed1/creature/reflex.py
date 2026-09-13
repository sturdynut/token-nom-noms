def act(o):
 ds={'n':(0,-1),'s':(0,1),'e':(1,0),'w':(-1,0)}
 rocks={tuple(p) for p in o.get('rocks',[])}; traps={tuple(p) for p in o.get('traps_known',[])}; pits={tuple(p) for p in o.get('pits',[])}; foods={tuple(p) for p in o.get('food',[])}; preds=[tuple(p) for p in o.get('predators',[])]
 x,y=o['pos']; g=o['grid']
 def ok(p,pit=False): return -x<=p[0]<g-x and -y<=p[1]<g-y and p not in rocks and p not in traps and (pit or p not in pits)
 def pd(p): return min([abs(p[0]-a)+abs(p[1]-b) for a,b in preds] or [99])
 def search(pit):
  q=[(0,0)]; prev={(0,0):None}; mv={}
  for z in q:
   if z in foods:
    r=[]
    while prev[z] is not None: r.append(mv[z]); z=prev[z]
    return r[::-1]
   for a,(dx,dy) in ds.items():
    n=(z[0]+dx,z[1]+dy)
    if n not in prev and ok(n,pit) and pd(n)>1: prev[n]=z; mv[n]=a; q.append(n)
  return []
 d=pd((0,0))
 if d<=3:
  c=[]
  for a,(dx,dy) in ds.items():
   p=(dx,dy)
   if ok(p,False) or ok(p,True): c.append((pd(p),p not in pits,p not in foods,a))
  if c: return max(c)[3]
 p=search(False) or search(True)
 if p: return p[0]
 c=[]
 for a,(dx,dy) in ds.items():
  z=(dx,dy)
  if ok(z,False) or ok(z,True): c.append((pd(z),z not in pits,a))
 return max(c)[2] if c else 'stay'