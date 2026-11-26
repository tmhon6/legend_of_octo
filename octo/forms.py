"""Octo's forms: what each one is good at, and what the Fusion Machine can make.

Every form has a passive STRENGTH that is on while Octo is in that form.
Fused forms (made by the Fusion Machine next to the Pearl Shop) get a brand-new attack of their own
and a boosted version of both parents' strengths.
"""

# form -> (strength name, what it does, stats)
#   speed: swim-speed multiplier      power: extra damage on every attack
#   jet:   ink-jet cooldown multiplier armor: damage taken off each hit (never below half a heart)
#   invuln: invincibility-time multiplier after a hit
#   regen: frames between healing half a heart
#   thorns: damage dealt to enemies that touch Octo
#   luck:  treasure-drop multiplier    light: how far Octo sees in the dark
#   steady: never knocked back
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
}

# fused form -> (parent a, parent b, attack name, attack description)
FUSIONS = {
    'stormy': ('zap', 'ice', "HAIL", "CALLS DOWN HAILSTONES ON UP TO SIX ENEMIES. THEY HIT HARD AND FREEZE."),
    'whippy': ('blue', 'mad', "INK WHIP", "A LONG INKY TENTACLE THAT SWEEPS A WIDE ARC IN FRONT OF YOU."),
    'prickly': ('bubble', 'spiky', "SPIKE ROLL", "CURL INTO A SPIKY BALL AND ROLL THROUGH ENEMIES. NOTHING CAN HURT YOU."),
    'quaky': ('mad', 'spiky', "QUAKE", "SLAM THE SEA FLOOR: SHOCKWAVES RUN OUT FOUR WAYS AND CRACK ROCK."),
    'wispy': ('ghost', 'glow', "LANTERN", "A SPIRIT LANTERN CIRCLES YOU, BURNING EVERY ENEMY IT TOUCHES."),
    'breezy': ('blue', 'air', "WHIRLPOOL", "A SPINNING WHIRLPOOL THAT DRAGS ENEMIES IN AND CHURNS THEM UP."),
    'frosty': ('ice', 'bubble', "FROST TRAP", "A FREEZING BUBBLE THAT TRAPS AN ENEMY, THEN POPS FOR BIG DAMAGE."),
    'sparky': ('zap', 'air', "CHAIN BOLT", "LIGHTNING THAT JUMPS FROM ENEMY TO ENEMY, UP TO FIVE TIMES."),
}
FUSION_COST = 40


def _fuse_stats(a, b):
    sa, sb = STRENGTHS[a][2], STRENGTHS[b][2]
    out = {}
    for k in set(sa) | set(sb):
        va, vb = sa.get(k), sb.get(k)
        if k in ('speed', 'luck', 'invuln'):
            out[k] = round(max(v for v in (va, vb) if v) + (0.1 if k == 'speed' else 0.5), 2)
        elif k in ('jet', 'regen'):
            out[k] = min(v for v in (va, vb) if v) * 0.7
        elif k in ('power', 'thorns', 'armor'):
            out[k] = min(2, (va or 0) + (vb or 0) + 1)
        else:
            out[k] = max(v for v in (va, vb) if v)
    return out


for _f, (_a, _b, _, _) in FUSIONS.items():
    STRENGTHS[_f] = (STRENGTHS[_a][0] + "+ & " + STRENGTHS[_b][0] + "+",
                     "THE STRENGTHS OF BOTH FORMS, EVEN STRONGER.", _fuse_stats(_a, _b))


def stat(form, key, default):
    return STRENGTHS.get(form, ("", "", {}))[2].get(key, default)
