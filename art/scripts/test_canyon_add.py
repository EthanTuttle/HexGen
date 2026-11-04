"""What adding a tile to a finished canyon would change, if the old maze is kept (art/handoff/desert_kit.md, Adding tiles). Rock heights only. Plain Python, about a minute."""
import os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import canyon as cn, ground_cover as gc
real = cn.open_edges
def steps(a, b):
    dq, dr = a[0]-b[0], a[1]-b[1]
    return (abs(dq)+abs(dr)+abs(dq+dr))//2
rng = random.Random(5)
worst = {}
tot = 0; floor_lost = 0
mesas_lost = set()
for trial in range(60):
    region = {(0,0)}
    while len(region) < rng.randint(8,14):
        t = rng.choice(sorted(region)); region.add(rng.choice(cn.neighbours(t)))
    lm = rng.choice(sorted(region))
    facing = next((i for i,n in enumerate(cn.neighbours(lm)) if n in region), None)
    if facing is None: continue
    a = cn.Field(region, lm, facing)
    # add one tile, keeping the old maze
    outer = sorted({n for t in region for n in cn.neighbours(t) if n not in region})
    x = rng.choice(outer)
    olds = [i for i,n in enumerate(cn.neighbours(x)) if n in region and n != lm]
    if not olds: continue
    op = set(a.openset); ent = list(a.entrances)
    i = olds[0]; op.add(cn.edge_key(x,i))
    n = cn.neighbours(x)[i]
    ent = [e for e in ent if cn.neighbours(e[0])[e[1]] != x]  # entrances facing the new tile become ordinary openings
    for t,k in a.entrances:
        if cn.neighbours(t)[k] == x: op.add(cn.edge_key(t,k))
    free = [k for k,m in enumerate(cn.neighbours(x)) if m not in region]
    if free: ent.append((x, free[0]))
    cn.open_edges = lambda *_: (op, ent)
    b = cn.Field(region | {x}, lm, facing, before=a)
    cn.open_edges = real
    if b.x0 != a.x0 or b.y0 != a.y0: continue  # the grid moved: only compare on the same grid
    tot += 1
    for ix in range(0, a.nx):
        for iy in range(0, a.ny):
            px, py = a.x0+ix*cn.CELL+0.03, a.y0+iy*cn.CELL+0.03
            t = gc.tile_at(px, py)
            if t not in region: continue
            va, vb = a.value(px,py), b.value(px,py)
            if a.mesa_depth(px,py) > 0 and vb < cn.TOP_LEVEL + 1 and steps(t, x) > 1: mesas_lost.add(id(a) + round(px))
            va, vb = min(va, cn.TOP_LEVEL), min(vb, cn.TOP_LEVEL)  # bands only: a mesa is its own solid, counted above
            if va < 0.01 and vb > va + 0.05: floor_lost += 1
            if abs(va-vb) > 0.02:
                s = steps(t, x); worst[s] = worst.get(s,0)+1
print("trials", tot, "changed cells by steps from the new tile", sorted(worst.items()), "old floor that became rock", floor_lost, "cells of mesa lost further away", len(mesas_lost))
assert all(s == 1 for s in worst) and floor_lost == 0, "a new tile changed more than the tiles touching it"
