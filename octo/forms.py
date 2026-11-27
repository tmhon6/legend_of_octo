"""Octo's forms: what each one is good at, and what the Fusion Machine can make.

Every form has a passive STRENGTH that is on while Octo is in that form.

The Fusion Machine (next to the Pearl Shop) can fuse ANY two base forms. Every pair leads to one of 16
attack shapes, and there is exactly one fused form for each shape (no copies of the same attack): fusing
a pair makes the fused form for its shape. A fused form also gets boosted versions of both parents'
strengths. The Mega Machine works the same way: one mega form for each of its six giant attacks.
"""
import itertools

# base forms, in the order they're listed everywhere
BASE = ['blue', 'mad', 'zap', 'ice', 'ghost', 'bubble', 'spiky', 'glow', 'air',
        'magnet', 'clammy', 'starry', 'wobbly', 'stony',
        # learned from the new worlds: the Surface, the Sky and the Underdeep
        'sandy', 'leafy', 'crysty', 'cloudy', 'shroomy', 'magmy']
ALTAR_FORMS = BASE[2:]          # what the temple altar teaches (Happy and Grumpy you start with)

NAMES = {'blue': 'HAPPY', 'mad': 'GRUMPY', 'zap': 'ZAPPY', 'ice': 'CHILLY', 'ghost': 'SPOOKY',
         'bubble': 'BUBBLY', 'spiky': 'SPIKY', 'glow': 'GLOWY', 'air': 'AIRY', 'magnet': 'MAGNETY',
         'clammy': 'CLAMMY', 'starry': 'STARRY', 'wobbly': 'WOBBLY', 'stony': 'STONY',
         'sandy': 'SANDY', 'leafy': 'LEAFY', 'crysty': 'CRYSTY', 'cloudy': 'CLOUDY', 'shroomy': 'SHROOMY',
         'magmy': 'MAGMY'}

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
#   dodge: chance a hit misses Octo   crit: chance an attack deals double damage
#   hover: floats over pits, trenches, ponds and sky gaps   heatproof: walks on lava, fire can't hurt
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
    'sandy': ("DODGY", "ONE HIT IN FOUR MISSES YOU COMPLETELY.", {'dodge': 0.25}),
    'leafy': ("OVERGROWN", "HEALS HALF A HEART EVERY 10 SECONDS, AND ENEMIES THAT TOUCH YOU GET PRICKED.",
              {'regen': 600, 'thorns': 1}),
    'crysty': ("SHARP", "ONE ATTACK IN FOUR DEALS DOUBLE DAMAGE.", {'crit': 0.25}),
    'cloudy': ("FLOATY", "FLOATS OVER PITS, TRENCHES, PONDS AND GAPS IN THE SKY.", {'hover': 1}),
    'shroomy': ("FORAGER", "TREASURE DROPS MORE OFTEN AND PEARLS COUNT EXTRA.", {'luck': 1.5, 'pearls': 1.5}),
    'magmy': ("HEATPROOF", "WALKS ON LAVA, AND FIRE CAN'T HURT YOU.", {'heatproof': 1}),
}

# the Z attack of each base form (for menus)
ATTACKS = {'blue': "INK", 'mad': "SLAP", 'zap': "ZAP RING", 'ice': "ICE SHARD", 'ghost': "WISPS",
           'bubble': "BUBBLE SHIELD", 'spiky': "SPINES", 'glow': "FLASH", 'air': "FOG CLOAK",
           'magnet': "MAGNET PULSE", 'clammy': "SHELL BOOMERANG", 'starry': "SEEKER STARS",
           'wobbly': "STING MINES", 'stony': "BOULDER", 'sandy': "SAND QUAKE", 'leafy': "VINE LASH",
           'crysty': "PRISM BEAM", 'cloudy': "RAIN CLOUD", 'shroomy': "SPORE BURST", 'magmy': "MAGMA ORBS"}

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
    'beam': ("BEAM", "BEAM", "A BEAM OF LIGHT SHOOTS STRAIGHT AHEAD, PIERCING EVERY ENEMY IN LINE"),
    'orbit': ("ORBS", "ORBS", "THREE ORBS CIRCLE YOU FOR A WHILE, HITTING WHAT THEY TOUCH"),
    'rain': ("RAIN", "RAIN", "A CLOUD FOLLOWS YOU AND RAINS DOWN ON NEARBY ENEMIES"),
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
    'poison': ("VENOM", "AND POISONS THEM", (150, 230, 80)),
    'slow': ("SLUDGE", "AND SLOWS THEM DOWN", (140, 120, 200)),
    'push': ("GUST", "AND BLASTS THEM AWAY", (220, 240, 255)),
    'confuse': ("DIZZY", "AND MAKES THEM WANDER IN A DAZE", (255, 160, 230)),
    'weaken': ("CRACK", "AND CRACKS THEIR ARMOR SO EVERY HIT HURTS MORE", (230, 200, 255)),
}
# each base form's favourite element (fusions lean towards their parents' elements)
LEANS = {'blue': 'loot', 'mad': 'heavy', 'zap': 'spark', 'ice': 'freeze', 'ghost': 'drain', 'bubble': 'drain',
         'spiky': 'burn', 'glow': 'stun', 'air': 'stun', 'magnet': 'loot', 'clammy': 'heavy',
         'starry': 'spark', 'wobbly': 'stun', 'stony': 'heavy', 'sandy': 'push', 'leafy': 'poison',
         'crysty': 'weaken', 'cloudy': 'slow', 'shroomy': 'confuse', 'magmy': 'burn'}
# the base forms whose own attack already is one of the shapes (a fusion never just copies a parent)
OWN_SHAPE = {'magnet': 'nova', 'clammy': 'boomerang', 'starry': 'seekers', 'wobbly': 'mines', 'stony': 'boulder',
             'sandy': 'quake', 'leafy': 'whip', 'crysty': 'beam', 'cloudy': 'rain', 'shroomy': 'nova',
             'magmy': 'orbit'}
# the element a base form's own attack carries
OWN_ELEMENT = {'magnet': 'pull', 'sandy': 'push', 'leafy': 'poison', 'crysty': 'weaken', 'cloudy': 'slow',
               'shroomy': 'confuse', 'magmy': 'burn'}

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


OLD_BASE = BASE[:14]          # the first fourteen forms keep the fusions they always had
OLD_SHAPES = 13
OLD_ELEMENTS = 7
VOWELS = set('AEIOU')
BLOCKED_NAMES = {'SONY'}          # real brand names are never used


def _blend(a, b):
    """A rhyming name for the newer fusions: the first sounds of one name, the ending of the other
    (ZAPPY + SHROOMY -> ZOOMY, GRUMPY + SANDY -> GRANDY)."""
    na, nb = NAMES[a], NAMES[b]
    i = 0
    while i < len(na) and na[i] not in VOWELS and not (na[i] == 'Y' and i > 0):
        i += 1
    onset = na[:i]
    if not onset:
        return ''                        # AIRY etc: let the other order make the name
    body = nb[:-1] if nb.endswith('Y') else nb
    j = len(body) - 1
    while j > 0 and body[j] not in VOWELS and body[j] != 'Y':
        j -= 1
    while j > 0 and (body[j - 1] in VOWELS or body[j - 1] == 'Y'):
        j -= 1
    k = 0
    while k < len(nb) and nb[k] not in VOWELS and not (nb[k] == 'Y' and k > 0):
        k += 1
    rhyme = nb[min(j, k):] if nb[min(j, k):] else nb
    return _squash(onset + rhyme)


def _pick(pairs, shapes, elems, used, start_mul=5):
    out = []
    for i, (a, b) in enumerate(pairs):
        prefer = [LEANS[a], LEANS[b]] + elems
        start = (i * start_mul) % len(shapes)
        pick = None
        for e in prefer:
            for k in range(len(shapes)):
                s = shapes[(start + k) % len(shapes)]
                if (s, e) not in used and s not in (OWN_SHAPE.get(a), OWN_SHAPE.get(b)):
                    pick = (s, e)
                    break
            if pick:
                break
        if pick is None:                        # every combination near its parents is taken
            pick = next(((s, e) for e in elems for s in shapes if (s, e) not in used
                         and s not in (OWN_SHAPE.get(a), OWN_SHAPE.get(b))), None) or \
                next((s, e) for s in shapes for e in elems if (s, e) not in used)
        used.add(pick)
        out.append(((a, b), pick))
    return out


def _build():
    used, out = set(), {}
    for (a, b), (fid, name, shape, elem) in NAMED.items():
        used.add((shape, elem))
        out[fid] = {'parents': (a, b), 'name': name, 'shape': shape, 'element': elem}
    names = {v['name'] for v in out.values()}
    shapes, elems = list(SHAPES), list(ELEMENTS)
    # 1) the original 91 pairs, exactly as before
    old = [p for p in itertools.combinations(OLD_BASE, 2)]
    for i, (a, b) in enumerate(old):
        if (a, b) in NAMED:
            continue
        prefer = [LEANS[a], LEANS[b]] + elems[:OLD_ELEMENTS]
        osh = shapes[:OLD_SHAPES]
        start = (i * 5) % len(osh)
        pick = None
        for e in prefer:
            for k in range(len(osh)):
                sh = osh[(start + k) % len(osh)]
                if (sh, e) not in used and sh not in (OWN_SHAPE.get(a), OWN_SHAPE.get(b)):
                    pick = (sh, e)
                    break
            if pick:
                break
        if pick is None:
            pick = next((sh, e) for sh in osh for e in elems[:OLD_ELEMENTS] if (sh, e) not in used)
        used.add(pick)
        na, nb = NAMES[a], NAMES[b]
        for name in (_portmanteau(a, b), _portmanteau(b, a), _squash(na[:3] + nb[-3:]), _squash(nb[:3] + na[-3:]),
                     _squash(na[:2] + nb[-4:]), _squash(nb[:2] + na[-4:]), _squash(na[0] + nb[1:])):
            if name not in names and name not in NAMES.values():
                break
        names.add(name)
        out[f'{a}+{b}'] = {'parents': (a, b), 'name': name, 'shape': pick[0], 'element': pick[1]}
    # 2) every pair with a newer form: any of the 16 shapes and 12 elements
    new = [p for p in itertools.combinations(BASE, 2) if p not in old]
    for (a, b), pick in _pick(new, shapes, elems, used, start_mul=7):
        for name in (_blend(a, b), _blend(b, a), _portmanteau(a, b), _portmanteau(b, a),
                     _squash(NAMES[a][:3] + NAMES[b][-3:]), _squash(NAMES[b][:3] + NAMES[a][-3:])):
            if name and name not in names and name not in NAMES.values() and 4 <= len(name) <= 8 and \
                    name not in BLOCKED_NAMES and \
                    not any(name.count(c * 2) and c * 2 in name[2:] and name.index(c * 2) != name.rindex(c * 2)
                            for c in name):
                break
        names.add(name)
        out[f'{a}+{b}'] = {'parents': (a, b), 'name': name, 'shape': pick[0], 'element': pick[1]}
    for fid, f in out.items():
        shape, elem = f['shape'], f['element']
        f['attack'] = f"{ELEMENTS[elem][0]} {SHAPES[shape][1]}"
        f['label'] = SHAPES[shape][0]
        f['desc'] = f"{SHAPES[shape][2]}, {ELEMENTS[elem][1]}."
    return out


ALL_PAIRS = _build()            # what every pair of base forms would make on its own (190 of them)


def _one_per_shape(table):
    """Keep one fused form for each attack shape: the hand-named original where there is one, and for
    the other shapes the one whose element is used least so far, so the sixteen are as varied as can be.
    Returns (kept forms, shape -> kept id)."""
    keep, used = {}, {}
    for (a, b), (fid, name, shape, elem) in NAMED.items():
        keep[shape] = fid
        used[elem] = used.get(elem, 0) + 1
    for shape in SHAPES:
        if shape in keep:
            continue
        options = [fid for fid, f in table.items() if f['shape'] == shape]
        best = min(options, key=lambda fid: (used.get(table[fid]['element'], 0), options.index(fid)))
        keep[shape] = best
        e = table[best]['element']
        used[e] = used.get(e, 0) + 1
    return {fid: table[fid] for fid in keep.values()}, keep


FUSIONS, FOR_SHAPE = _one_per_shape(ALL_PAIRS)
PAIR = {f['parents']: FOR_SHAPE[f['shape']] for f in ALL_PAIRS.values()}    # any pair -> its shape's form
MERGED = {fid: FOR_SHAPE[f['shape']] for fid, f in ALL_PAIRS.items()}       # an old save's form -> the one kept


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


# ---------------------------------------------------------------------------- mega fusions
# The secret Mega Machine (deep in the Ancient Ruins) wakes once Octo has made every fusion.
# It fuses two FUSED forms into a mega form: one of six huge attacks carrying BOTH parents' elements.
MEGA_SHAPES = {
    'supernova': ("NOVA", "SUPERNOVA", "A HUGE BLAST RINGS OUT ACROSS THE SCREEN"),
    'tsunami': ("WAVE", "TSUNAMI", "THREE GIANT WAVES SURGE OUT AHEAD OF YOU"),
    'meteor': ("METEOR", "METEOR STORM", "METEORS SMASH DOWN ON EVERY ENEMY IN SIGHT"),
    'blackhole': ("HOLE", "BLACK HOLE", "A BLACK HOLE DRAGS EVERYTHING IN AND CRUSHES IT"),
    'prism': ("PRISM", "PRISM STORM", "SEVEN BEAMS FAN OUT AT ONCE"),
    'titan': ("TITAN", "TITAN SLAM", "YOU SLAM DOWN WITH TITANIC FORCE, SHAKING THE GROUND"),
}
MEGA_COST = 100
MEGAS = {}


def mega_id(a, b):
    a, b = sorted((a, b))
    return f"mega:{a}|{b}"


def _mega_shape(mid):
    import zlib
    return list(MEGA_SHAPES)[zlib.crc32(mid.encode()) % len(MEGA_SHAPES)]


_MEGA_FOR = {}


def _mega_for(shape):
    """The one mega form of a giant attack: of the pairs of fused forms that make it, the one whose two
    elements have been used least by the others, so the six are as varied as can be."""
    if not _MEGA_FOR:
        pairs = list(itertools.combinations(sorted(FUSIONS), 2))
        used = {}
        for sh in MEGA_SHAPES:
            options = [(a, b) for a, b in pairs if _mega_shape(mega_id(a, b)) == sh]
            if not options:
                continue

            def score(ab):
                ea, eb = FUSIONS[ab[0]]['element'], FUSIONS[ab[1]]['element']
                return (used.get(ea, 0) + used.get(eb, 0) + (2 if ea == eb else 0), options.index(ab))
            a, b = min(options, key=score)
            _MEGA_FOR[sh] = mega_id(a, b)
            for e in (FUSIONS[a]['element'], FUSIONS[b]['element']):
                used[e] = used.get(e, 0) + 1
    return _MEGA_FOR.get(shape)


def merge_form(f):
    """What a form in an older save is now: a fused form folded into the one kept for its attack, and
    a mega form into the one for its giant attack."""
    if is_mega(f):
        return _mega_for(_mega_shape(f)) or f
    return MERGED.get(f, f)


def is_mega(form):
    return isinstance(form, str) and form.startswith('mega:')


def register_mega(mid):
    """Make the names, attack and strengths of a mega form (they're built the first time they're needed)."""
    if mid in MEGAS:
        return MEGAS[mid]
    a, b = mid[5:].split('|')
    fa, fb = FUSIONS[a], FUSIONS[b]
    shape = _mega_shape(mid)
    ea, eb = fa['element'], fb['element']
    elems = (ea, eb) if ea != eb else (ea, 'heavy' if ea != 'heavy' else 'stun')
    na, nb = fa['name'], fb['name']
    name = _squash(na[:(len(na) + 1) // 2] + nb[len(nb) // 2:])[:9]
    m = {'parents': (a, b), 'name': name, 'shape': shape, 'elements': elems,
         'attack': f"{ELEMENTS[elems[0]][0]}-{ELEMENTS[elems[1]][0]} {MEGA_SHAPES[shape][1]}",
         'label': MEGA_SHAPES[shape][0],
         'desc': f"{MEGA_SHAPES[shape][2]}. {ELEMENTS[elems[0]][0]} + {ELEMENTS[elems[1]][0]} POWER."}
    MEGAS[mid] = m
    sa, sb = STRENGTHS[a][2], STRENGTHS[b][2]
    stats = {}
    for k in set(sa) | set(sb):
        va, vb = sa.get(k), sb.get(k)
        vals = [v for v in (va, vb) if v]
        if k in ('jet', 'regen'):
            stats[k] = min(vals) * 0.8
        elif k in ('power', 'thorns', 'armor'):
            stats[k] = min(3, sum(vals))
        elif k in ('dodge', 'crit'):
            stats[k] = min(0.5, sum(vals))
        else:
            stats[k] = max(vals)
    sa_name, sb_name = STRENGTHS[a][0].split(' /')[0], STRENGTHS[b][0].split(' /')[0]
    STRENGTHS[mid] = ("MEGA " + sa_name + ("" if sa_name == sb_name else " / " + sb_name),
                      "EVERY STRENGTH OF BOTH FUSED FORMS, PUSHED EVEN FURTHER.", stats)
    NAMES[mid] = name
    ATTACKS[mid] = m['attack']
    return m


def mega_of(a, b):
    """The mega form two fused forms make: the one for the giant attack their pair leads to."""
    mid = _mega_for(_mega_shape(mega_id(a, b))) or mega_id(a, b)
    register_mega(mid)
    return mid
