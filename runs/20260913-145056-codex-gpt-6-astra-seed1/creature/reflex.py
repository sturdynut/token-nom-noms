def act(obs):
 import heapq, math
 from collections import deque
 n=obs['grid']; x,y=obs['pos']; pos=(x,y)
 def absolute(items):
  return {(x+a,y+b) for a,b in items}
 rocks=absolute(obs.get('rocks',[])); pits=absolute(obs.get('pits',[])); traps=absolute(obs.get('traps_known',[]))
 signature=(n,tuple(sorted(rocks)))
 if getattr(act,'signature',None)!=signature:
  cells=[(a,b) for a in range(n) for b in range(n) if (a,b) not in rocks]
  graph={p:[q for q in ((p[0],p[1]-1),(p[0],p[1]+1),(p[0]+1,p[1]),(p[0]-1,p[1])) if 0<=q[0]<n and 0<=q[1]<n and q not in rocks] for p in cells}
  distances={}
  for start in cells:
   d={start:0}; queue=deque([start])
   while queue:
    p=queue.popleft()
    for q in graph[p]:
     if q not in d:
      d[q]=d[p]+1; queue.append(q)
   distances[start]=d
  act.signature=signature; act.graph=graph; act.distances=distances
 graph=act.graph; distances=act.distances
 def dist(a,b):
  return distances.get(a,{}).get(b,999)
 raw=obs.get('predators')
 if raw is None:
  raw=[obs['predator']] if obs.get('predator') is not None else []
 predators=tuple(sorted(absolute(raw)))
 tick=obs['tick']; speed=1
 previous=getattr(act,'previous',None)
 history=getattr(act,'speeds',[])
 if previous and tick>previous[0] and predators and previous[1]:
  elapsed=tick-previous[0]
  observed=max(min(dist(p,q) for q in previous[1]) for p in predators)
  if observed<999 and len(predators)==len(previous[1]):
   history.append((tick,max(1,min(4,int(math.ceil(observed/elapsed))))))
 history=[h for h in history if tick-h[0]<=16]
 if history: speed=max(h[1] for h in history)
 act.speeds=history; act.previous=(tick,predators)
 food=tuple(sorted(absolute(obs.get('food',[]))))
 food_index={p:i for i,p in enumerate(food)}
 full_mask=(1<<len(food))-1
 extra={p:(obs.get('pit_cost',6) if p in pits else 0)+(obs.get('trap_cost',8) if p in traps else 0) for p in graph}
 food_dist=[]
 for target in food:
  costs={target:0}; heap=[(0,target)]
  while heap:
   cost,p=heapq.heappop(heap)
   if cost!=costs[p]: continue
   for q in graph.get(p,[]):
    nc=cost+1+extra.get(p,0)
    if nc<costs.get(q,1e9):
     costs[q]=nc; heapq.heappush(heap,(nc,q))
  food_dist.append(costs)
 def nearest_food(p,mask):
  best=999
  while mask:
   bit=mask & -mask; i=bit.bit_length()-1; mask-=bit
   best=min(best,food_dist[i].get(p,999))
  return best
 def clearance(p,pp):
  return min((dist(p,q) for q in pp),default=20)
 def advance(pp,target):
  result=[]
  for p in pp:
   for unused in range(speed):
    choices=graph.get(p,[])
    if not choices: break
    q=min(choices,key=lambda q:(dist(q,target),-len(graph.get(q,[])),q))
    if dist(q,target)>=dist(p,target): break
    p=q
   result.append(p)
  return tuple(sorted(result))
 def evaluate(p,energy,mask,pp):
  gap=clearance(p,pp)
  exits=sum(clearance(q,pp)>speed for q in graph.get(p,[]))
  target=nearest_food(p,mask)
  hunger=0 if target==999 else min(target,35)
  danger=10*max(0,3-gap)**2
  if pp and exits==0: danger+=35
  return 1.8*energy-1.15*hunger+1.25*min(gap,6)+0.65*exits-danger
 moves=[('n',(0,-1)),('s',(0,1)),('e',(1,0)),('w',(-1,0)),('stay',(0,0))]
 # Search several steps ahead, replanning from the real observation each tick.
 states=[(evaluate(pos,obs['energy'],full_mask,predators),pos,obs['energy'],full_mask,predators,None)]
 best_action=None
 for depth in range(7):
  next_states={}
  for old_score,p,energy,mask,pp,first in states:
   for action,(dx,dy) in moves:
    q=(p[0]+dx,p[1]+dy)
    if q not in graph: continue
    if clearance(q,pp)<=speed: continue
    en=energy-1-(extra.get(q,0) if q!=p else 0)
    remaining=mask
    i=food_index.get(q)
    if i is not None and remaining & (1<<i):
     en=min(obs['max_energy'],en+8); remaining &= ~(1<<i)
    if en<=0: continue
    next_pred=advance(pp,q)
    if q in next_pred: continue
    chosen=action if first is None else first
    score=evaluate(q,en,remaining,next_pred)
    key=(q,remaining,next_pred)
    candidate=(score,q,en,remaining,next_pred,chosen)
    if key not in next_states or score>next_states[key][0]: next_states[key]=candidate
  if not next_states: break
  states=sorted(next_states.values(),key=lambda s:s[0],reverse=True)[:40]
  best_action=states[0][5]
 if best_action is not None: return best_action
 # If the conservative search has no safe route, choose the best immediate escape.
 best=None; answer='stay'
 for action,(dx,dy) in moves:
  q=(x+dx,y+dy)
  if q not in graph: continue
  en=obs['energy']-1-(extra.get(q,0) if q!=pos else 0)
  if q in food_index: en=min(obs['max_energy'],en+8)
  gap=clearance(q,predators)
  exits=sum(clearance(r,predators)>speed for r in graph[q])
  value=(q not in predators,en>0,gap>speed,min(gap,8),en+exits)
  if best is None or value>best: best=value; answer=action
 return answer