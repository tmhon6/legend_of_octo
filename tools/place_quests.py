"""Pick hiding spots for side-quest items: reachable open floor in the right regions, spread out,
away from enemies, items and portals. Prints QUEST_SPOTS for octo/folk.py.

    python3 tools/place_quests.py
"""
import os
import random
import sys
from collections import deque

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'octo'))
import world  # noqa: E402

WANT = {
    'hatchlings': [('CORAL REEF', 1), ('KELP WOODS', 1), ('THE LAGOON', 1)],
    'peppers': [('KELP WOODS', 3)],
    'seeds': [('CORAL GARDENS', 4)],
    'marbles': [('GLASS REEF', 5)],
    'shells': [('SUNNY BEACH', 2), ('TIDE MEADOWS', 2), ('PALM JUNGLE', 1)],
    'sister': [('PALM JUNGLE', 1)],
}


def reachable():
    L = world.LEVEL
    walk = world.FLOOR_CHARS | set('KLXRIGlYEBUAD')
    links = {}
    for a, b in world.GEYSERS:
        links[a], links[b] = b, a
    for a, b, _k in world.PASSAGES:
        links[a], links[b] = b, a
    seen = {(int(world.START[0]), int(world.START[1]))}
    q = deque(seen)
    while q:
        x, y = q.popleft()
        hops = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)] + ([links[(x, y)]] if (x, y) in links else [])
        for nx, ny in hops:
            if 0 <= nx < world.LEVEL_W and 0 <= ny < world.LEVEL_H and (nx, ny) not in seen and L[ny][nx] in walk:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def main():
    L = world.LEVEL
    ok = reachable()
    busy = [(int(x), int(y)) for _k, x, y in world.ENEMIES + world.ITEMS]
    busy += [t['portal'] for t in world.TRIALS.values()]
    busy += [(int(x), int(y)) for _b, x, y in world.MINIBOSSES]
    busy += [a for a, b in world.GEYSERS] + [b for a, b in world.GEYSERS]
    busy += [a for a, b, k in world.PASSAGES] + [b for a, b, k in world.PASSAGES]
    rnd = random.Random(2024)
    out = {}
    used = []
    for qid, parts in WANT.items():
        spots = []
        for region, n in parts:
            cands = []
            for (x, y) in ok:
                if y >= world.WORLD_H and region not in ('SUNNY BEACH', 'TIDE MEADOWS', 'PALM JUNGLE'):
                    continue
                if world.region_at(x, y) != region or L[y][x] not in '.,':
                    continue
                if world.arena_of(x, y) or world.area_at(x, y) != 'overworld':
                    continue
                if any(L[y + dy][x + dx] not in '.,' for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    continue
                if any(abs(x - bx) + abs(y - by) < 4 for bx, by in busy + used):
                    continue
                if region == 'CORAL REEF' and abs(x - 47) + abs(y - 50) < 14:
                    continue                         # not right next to the start
                cands.append((x, y))
            cands.sort()
            rnd.shuffle(cands)
            pick = []
            for _ in range(n):
                best = max(cands[:400], key=lambda c: min([abs(c[0] - p[0]) + abs(c[1] - p[1]) for p in pick + used]
                                                           or [999]))
                pick.append(best)
                cands.remove(best)
            spots += pick
            used += pick
        out[qid] = spots
    print("QUEST_SPOTS = {")
    for qid, spots in out.items():
        print(f"    '{qid}': {spots},")
    print("}")


if __name__ == '__main__':
    main()
