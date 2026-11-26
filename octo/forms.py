"""Octo's forms: what each one is good at, and what the Fusion Machine can make.

Every form has a passive STRENGTH that is on while Octo is in that form.

The Fusion Machine (next to the Pearl Shop) can fuse ANY two base forms. Each of the 91 possible pairs
makes its own fused form with a brand-new attack: one of 13 attack shapes powered by one of 7 elements,
and no two pairs share the same combination. A fused form also gets boosted versions of both parents'
strengths.
"""
import itertools

# base forms, in the order they're listed everywhere
BASE = ['blue', 'mad', 'zap', 'ice', 'ghost', 'bubble', 'spiky', 'glow', 'air',
        'magnet', 'clammy', 'starry', 'wobbly', 'stony']
ALTAR_FORMS = BASE[2:]          # what the temple altar teaches (Happy and Grumpy you start with)

NAMES = {'blue': 'HAPPY', 'mad': 'GRUMPY', 'zap': 'ZAPPY', 'ice': 'CHILLY', 'ghost': 'SPOOKY',
         'bubble': 'BUBBLY', 'spiky': 'SPIKY', 'glow': 'GLOWY', 'air': 'AIRY', 'magnet': 'MAGNETY',
         'clammy': 'CLAMMY', 'starry': 'STARRY', 'wobbly': 'WOBBLY', 'stony': 'STONY'}

# form -> (strength name, what it does, stats)
#   speed: swim-speed multiplier      power: extra damage on every attack
#   jet:   ink-jet cooldown multiplier armor: damage taken off each hit (never below half a heart)
#   invuln: invincibility-time multiplier after a hit
#   regen: frames between healing half a heart
#   thorns: damage dealt to enemies that touch Octo
#   luck:  treasure-drop multiplier    light: how far Octo sees in the dark
#   steady: never knocked back         magnet: pickups this close fly to Octo
#   shield: blocks shots from the front  pearls: pearl value multiplier
#   stingproof: jellies and urchins can't hurt Octo
STRENGTHS = {
    'blue': ("SPEEDY", "SWIMS 20% FASTER.", {'speed': 1.2}),
    'mad': ("STRONG", "EVERY ATTACK DEALS +1 DAMAGE.", {'power': 1}),
    'zap': ("CHARGED", "THE INK JET RECHARGES TWICE AS FAST.", {'jet': 0.5}),
    'ice': ("TOUGH", "BIG HITS HURT HALF A HEART LESS.", {'armor': 1}),
    'ghost': ("SLIPPERY", "STAYS INVINCIBLE TWICE AS LONG AFTER A HIT.", {'invuln': 2.0}),
    'bubble': ("HEALING", "HEALS HALF A HEART EVERY 8 SECONDS.", {'regen': 480}),
    'spiky': ("THORNS", "ENEMIES THAT TOUCH YOU GET HURT.", {'thorns': 1}),
    'glow': ("LUCKY", "ENEMIES DROP TREASURE TWICE AS OFTEN, AND IT LIGHTS UP THE DARK.",
             {'luck': 2.0, 'light': 120}),
    'air': ("STEADY", "NEVER KNOCKED BACK, AND SWIMS A LITTLE FASTER.", {'steady': 1, 'speed': 1.1}),
    'magnet': ("MAGNETIC", "PEARLS AND HEARTS NEARBY FLY STRAIGHT TO YOU.", {'magnet': 72}),
    'clammy': ("ARMORED", "YOUR SHELL BLOCKS SHOTS FROM THE FRONT.", {'shield': 1}),
    'starry': ("SHINY", "EVERY PEARL YOU PICK UP COUNTS DOUBLE.", {'pearls': 2}),
    'wobbly': ("STINGPROOF", "JELLIES AND URCHINS CAN'T HURT YOU.", {'stingproof': 1}),
    'stony': ("HEAVY", "HITS HURT LESS AND NOTHING KNOCKS YOU BACK, BUT YOU SWIM A BIT SLOWER.",
              {'armor': 1, 'steady': 1, 'speed': 0.9}),
}

# the Z attack of each base form (for menus)
ATTACKS = {'blue': "INK", 'mad': "SLAP", 'zap': "ZAP RING", 'ice': "ICE SHARD", 'ghost': "WISPS",
           'bubble': "BUBBLE SHIELD", 'spiky': "SPINES", 'glow': "FLASH", 'air': "FOG CLOAK",
           'magnet': "MAGNET PULSE", 'clammy': "SHELL BOOMERANG", 'starry': "SEEKER STARS",
           'wobbly': "STING MINES", 'stony': "BOULDER"}

# ---------------------------------------------------------------------------- fused attacks
# shape -> (short HUD label, noun, what it does)
SHAPES = {
    'hail': ("HAIL", "HAIL", "STONES CRASH DOWN ON UP TO SIX ENEMIES"),
    'whip': ("WHIP", "WHIP", "A LONG TENTACLE SWEEPS A WIDE ARC IN FRONT OF YOU"),
    'roll': ("ROLL", "ROLL", "YOU CURL UP AND BARREL THROUGH ENEMIES, UNTOUCHABLE"),
    'quake': ("QUAKE", "QUAKE", "SHOCKWAVES RUN OUT FOUR WAYS, CRACKING ROCK"),
    'lantern': ("LAMP", "LANTERN", "A SPIRIT LANTERN CIRCLES YOU, HITTING WHAT IT TOUCHES"),
    'whirl': ("VORTEX", "WHIRLPOOL", "A WHIRLPOOL DRAGS ENEMIES IN AND CHURNS THEM"),
    'trap': ("TRAP", "TRAP", "A BUBBLE TRAPS AN ENEMY, THEN POPS FOR BIG DAMAGE"),
    'chain': ("BOLT", "CHAIN", "A BOLT JUMPS FROM ENEMY TO ENEMY, UP TO FIVE TIMES"),
    'nova': ("NOVA", "NOVA", "A BURST RINGS OUT AROUND YOU, HITTING EVERYTHING ON SCREEN NEARBY"),
    'boomerang': ("SHELL", "BOOMERANG", "A SPINNING SHELL FLIES OUT AND COMES BACK, HITTING BOTH WAYS"),
    'seekers': ("STARS", "STARS", "THREE STARS HUNT DOWN THE NEAREST ENEMIES"),
    'mines': ("MINES", "MINES", "DROP MINES THAT BURST WHEN AN ENEMY TOUCHES THEM"),
    'boulder': ("ROCK", "BOULDER", "A BOULDER ROLLS OUT AND CRUSHES EVERYTHING IN ITS PATH"),
}
# element -> (name prefix, what it adds, colour)
ELEMENTS = {
    'freeze': ("FROST", "AND FREEZES THEM SOLID", (190, 235, 255)),
    'burn': ("EMBER", "AND SETS THEM BURNING", (255, 140, 60)),
    'stun': ("DAZZLE", "AND LEAVES THEM DAZED", (255, 250, 150)),
    'heavy': ("CRUSH", "WITH CRUSHING FORCE", (200, 160, 110)),
    'drain': ("LEECH", "AND HEALS YOU A LITTLE", (255, 110, 160)),
    'loot': ("GOLD", "AND SHAKES PEARLS LOOSE", (255, 215, 90)),
    'spark': ("VOLT", "AND ARCS LIGHTNING TO A NEIGHBOUR", (255, 255, 120)),
}
# each base form's favourite element (fusions lean towards their parents' elements)
LEANS = {'blue': 'loot', 'mad': 'heavy', 'zap': 'spark', 'ice': 'freeze', 'ghost': 'drain', 'bubble': 'drain',
         'spiky': 'burn', 'glow': 'stun', 'air': 'stun', 'magnet': 'loot', 'clammy': 'heavy',
         'starry': 'spark', 'wobbly': 'stun', 'stony': 'heavy'}
# the base forms whose own attack already is one of the shapes (a fusion never just copies a parent)
OWN_SHAPE = {'magnet': 'nova', 'clammy': 'boomerang', 'starry': 'seekers', 'wobbly': 'mines', 'stony': 'boulder'}

# hand-named fusions (the first eight the machine ever made)
NAMED = {('zap', 'ice'): ('stormy', 'STORMY', 'hail', 'freeze'),
         ('blue', 'mad'): ('whippy', 'WHIPPY', 'whip', 'heavy'),
         ('bubble', 'spiky'): ('prickly', 'PRICKLY', 'roll', 'heavy'),
         ('mad', 'spiky'): ('quaky', 'QUAKY', 'quake', 'heavy'),
         ('ghost', 'glow'): ('wispy', 'WISPY', 'lantern', 'burn'),
         ('blue', 'air'): ('breezy', 'BREEZY', 'whirl', 'stun'),
         ('ice', 'bubble'): ('frosty', 'FROSTY', 'trap', 'freeze'),
         ('zap', 'air'): ('sparky', 'SPARKY', 'chain', 'spark')}

FUSION_COST = 25


def _portmanteau(a, b):
    na, nb = NAMES[a], NAMES[b]
    name = (na[:(len(na) + 1) // 2] + nb[len(nb) // 2:])[:8]
    return _squash(name)


def _squash(name):
    out = ''
    for ch in name[:8]:                  # no triple letters ("HAPPPY")
        if not out.endswith(ch * 2):
            out += ch
    return out


def _build():
    pairs = list(itertools.combinations(BASE, 2))
    used, out = set(), {}
    for (a, b), (fid, name, shape, elem) in NAMED.items():
        used.add((shape, elem))
        out[fid] = {'parents': (a, b), 'name': name, 'shape': shape, 'element': elem}
    shapes, elems = list(SHAPES), list(ELEMENTS)
    names = {v['name'] for v in out.values()}
    for i, (a, b) in enumerate(pairs):
        if (a, b) in NAMED:
            continue
        prefer = [LEANS[a], LEANS[b]] + elems
        start = (i * 5) % len(shapes)
        pick = None
        for e in prefer:
            for k in range(len(shapes)):
                s = shapes[(start + k) % len(shapes)]
                if (s, e) not in used and s not in (OWN_SHAPE.get(a), OWN_SHAPE.get(b)):
                    pick = (s, e)
                    break
            if pick:
                break
        if pick is None:                        # (never happens, but stay safe)
            pick = next((s, e) for s in shapes for e in elems if (s, e) not in used)
        used.add(pick)
        na, nb = NAMES[a], NAMES[b]
        for name in (_portmanteau(a, b), _portmanteau(b, a), _squash(na[:3] + nb[-3:]), _squash(nb[:3] + na[-3:]),
                     _squash(na[:2] + nb[-4:]), _squash(nb[:2] + na[-4:]), _squash(na[0] + nb[1:])):
            if name not in names and name not in NAMES.values():
                break
        names.add(name)
        out[f'{a}+{b}'] = {'parents': (a, b), 'name': name, 'shape': pick[0], 'element': pick[1]}
    for fid, f in out.items():
        shape, elem = f['shape'], f['element']
        f['attack'] = f"{ELEMENTS[elem][0]} {SHAPES[shape][1]}"
        f['label'] = SHAPES[shape][0]
        f['desc'] = f"{SHAPES[shape][2]}, {ELEMENTS[elem][1]}."
    return out


FUSIONS = _build()
PAIR = {f['parents']: fid for fid, f in FUSIONS.items()}


def fusion_of(a, b):
    """The fused form made from two base forms (in either order), or None."""
    return PAIR.get((a, b)) or PAIR.get((b, a))


def _fuse_stats(a, b):
    sa, sb = STRENGTHS[a][2], STRENGTHS[b][2]
    out = {}
    for k in set(sa) | set(sb):
        va, vb = sa.get(k), sb.get(k)
        if k == 'speed':
            out[k] = round(max(v for v in (va, vb) if v) + 0.1, 2)
        elif k in ('luck', 'invuln', 'pearls'):
            out[k] = round(max(v for v in (va, vb) if v) + 0.5, 2)
        elif k in ('jet', 'regen'):
            out[k] = min(v for v in (va, vb) if v) * 0.7
        elif k in ('power', 'thorns', 'armor'):
            out[k] = min(2, (va or 0) + (vb or 0) + 1)
        elif k == 'magnet':
            out[k] = max(v for v in (va, vb) if v) + 24
        else:
            out[k] = max(v for v in (va, vb) if v)
    return out


for _f, _d in FUSIONS.items():
    _a, _b = _d['parents']
    STRENGTHS[_f] = (STRENGTHS[_a][0] + "+ / " + STRENGTHS[_b][0] + "+",
                     "THE STRENGTHS OF BOTH FORMS, EVEN STRONGER.", _fuse_stats(_a, _b))
    NAMES[_f] = _d['name']
    ATTACKS[_f] = _d['attack']


def stat(form, key, default):
    return STRENGTHS.get(form, ("", "", {}))[2].get(key, default)


def is_fused(form):
    return form in FUSIONS
