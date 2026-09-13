def act(o):
 import heapq
 N=int(o.get('grid',10)); x,y=o['pos']; E=o['energy']; M=o['max_energy']
 rel=lambda k:{(x+a,y+b) for a,b in o.get(k,[]) or []}
 R,P,T,F,Q=map(rel,('rocks','pits','traps_known','food','predators'))
 if not Q and o.get('predator') is not None: Q=rel('predator')
 S=((0,-1,'n'),(0,1,'s'),(1,0,'e'),(-1,0,'w'))
 ok=lambda z:0<=z[0]<N and 0<=z[1]<N and z not in R
 D={z:0 for z in Q if ok(z)}; q=list(D); i=0
 while i<len(q):
  z=q[i]; i+=1
  for a,b,_ in S:
   w=(z[0]+a,z[1]+b)
   if ok(w) and w not in D:D[w]=D[z]+1;q.append(w)
 H={z:0 for z in F if ok(z)}; h=[(0,z) for z in H]; heapq.heapify(h)
 while h:
  c,z=heapq.heappop(h)
  if c!=H[z]:continue
  dz=D.get(z,99); enter=1+(o.get('pit_cost',6) if z in P else 0)+(o.get('trap_cost',8) if z in T else 0)+(40 if dz<3 else 8 if dz==3 else 0)
  for a,b,_ in S:
   w=(z[0]+a,z[1]+b)
   if ok(w) and c+enter<H.get(w,10**9):H[w]=c+enter;heapq.heappush(h,(c+enter,w))
 best=None
 for a,b,A in S+((0,0,'stay'),):
  z=(x+a,y+b)
  if not ok(z):continue
  d=D.get(z,99); u=3 if E<=12 else .8 if E<M-4 else .25
  s=u*H.get(z,50)+(100000 if d<2 else 400 if d==2 else 45 if d==3 else 8 if d==4 else 0)-2*min(d,8)
  s+=(o.get('pit_cost',6)*2 if z in P else 0)+(o.get('trap_cost',8)*2 if z in T else 0)+(3 if A=='stay' else 0)
  s-=sum(ok((z[0]+c,z[1]+e)) for c,e,_ in S)
  if z in F:s-=18 if E<M-3 else 4
  v=(s,A)
  if best is None or v<best:best=v
 return best[1] if best else 'stay'