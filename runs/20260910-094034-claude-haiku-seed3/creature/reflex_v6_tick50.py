def act(obs):
  p = obs.get('predator')
  if p and p[0]**2 + p[1]**2 <= 6:
    if abs(p[0]) >= abs(p[1]):
      return 'w' if p[0] > 0 else 'e'
    else:
      return 's' if p[1] > 0 else 'n'
  f = obs.get('food')
  if f:
    n = min(f, key=lambda x: x[0]**2 + x[1]**2)
    if abs(n[0]) >= abs(n[1]):
      return 'e' if n[0] > 0 else 'w'
    else:
      return 's' if n[1] > 0 else 'n'
  return None