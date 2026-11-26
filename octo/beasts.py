"""The Bestiary: every creature, guardian and boss -- where it lives, how tough it is, how many
you've beaten, and a 3D model of it. Creatures are filled in as you meet them.

Open it from the journal (press Q, then the BEASTS tab).
"""
import entities
import gfx
import world

NAMES = {'gull': "GULL", 'crab': "CRAB", 'urchin': "URCHIN", 'jelly': "JELLY", 'puffer': "PUFFER",
         'shark': "GRIMFIN", 'murk': "MURK", 'icecrab': "ICE CRAB", 'lavacrab': "LAVA CRAB", 'eel': "SAND EEL",
         'clam': "SNAPJAW CLAM", 'lionfish': "LIONFISH", 'ray': "STINGRAY", 'angler': "ANGLERFISH",
         'bilge': "BILGE GHOST", 'squid': "ICE SQUID", 'slug': "CINDER SLUG", 'wisp': "LANTERN WISP",
         'cloud': "CLOUD PUFF", 'thief': "THIEF CRAB", 'patroller': "SENTRY"}
NOTES = {'crab': "SCUTTLES SIDEWAYS AND PINCHES. EVERY OCTO'S FIRST FIGHT.",
         'puffer': "SWELLS UP WHEN YOU COME CLOSE, THEN SHOOTS SPINES ALL AROUND.",
         'gull': "SKY RAIDER: CIRCLES OVERHEAD, THEN DIVES AT YOU.",
         'cloud': "A GRUMPY LITTLE CLOUD. POP IT AND IT SPLITS IN TWO."}
CATS = ['CREATURE', 'NEW WORLDS', 'FUSED', 'GUARDIAN', 'TEMPLE BOSS', 'GREAT BOSS']
TEMPLE_BOSSES = {'tanglemaw', 'bramble', 'bellows', 'deepeye', 'hoarclaw', 'slagjaw'}

_entries = None


def _first(spr):
    if isinstance(spr, dict):
        spr = spr.get('swim') or next(iter(spr.values()))
    if isinstance(spr, (list, tuple)):
        spr = spr[0]
    return spr


def _habitats():
    """Where each kind of creature turns up, from the map."""
    out = {}

    def add(key, x, y):
        name = world.region_at(int(x), int(y))
        if name and not name.startswith('TRIAL'):
            out.setdefault(key, [])
            if name not in out[key]:
                out[key].append(name)
    for kind, x, y in world.ENEMIES:
        if kind.startswith('tboss:'):
            add('g:' + kind[6:], x, y)
        else:
            add(kind, x, y)
    for bid, x, y in world.MINIBOSSES:
        add('g:' + bid, x, y)
    return out


def entries():
    """Every entry: dict(key, name, cat, hp, dmg, note, where, sprite)."""
    global _entries
    if _entries is not None:
        return _entries
    homes = _habitats()
    out = []

    def where(key, default="THE TRIALS"):
        h = homes.get(key, [])
        if not h:
            return default
        return ", ".join(h[:2]) + (f" AND {len(h) - 2} MORE" if len(h) > 2 else "")
    base = ['crab', 'icecrab', 'lavacrab', 'urchin', 'jelly', 'puffer', 'gull', 'eel', 'clam', 'lionfish', 'ray',
            'angler', 'bilge', 'squid', 'slug', 'wisp', 'cloud', 'thief', 'patroller']
    for key in base:
        cls = entities.ENEMY_TYPES.get(key) or {'thief': entities.Thief, 'patroller': entities.Patroller}[key]
        note = NOTES.get(key) or (cls.__doc__ or "").strip().split(':', 1)[-1].strip().upper()
        if key == 'thief':
            spr = gfx.tint(_first(gfx.SPR['crab']), (255, 215, 80))
        elif key == 'patroller':
            spr = gfx.tint(_first(gfx.SPR['urchin']), (200, 200, 215))
        else:
            spr = _first(gfx.SPR[key])
        out.append(dict(key=key, name=NAMES[key], cat='CREATURE', hp=getattr(cls, 'max_hp', 2),
                        dmg=getattr(cls, 'damage', 1), note=note, where=where(key), sprite=spr))
    for key, cfg in entities.CRITTERS.items():
        out.append(dict(key=key, name=cfg['name'].replace(" (FUSED)", ""), cat='FUSED' if cfg.get('hybrid') else 'NEW WORLDS',
                        hp=cfg['hp'], dmg=cfg['dmg'], note=cfg.get('doc', ''), where=where(key, cfg.get('region', '')),
                        sprite=_first(gfx.SPR[key])))
    for bid, cfg in entities.MINIBOSS_STYLES.items():
        spr = _first(gfx.SPR[cfg['base']])
        if cfg.get('tint'):
            spr = gfx.tint(spr, cfg['tint'])
        temple = bid in TEMPLE_BOSSES
        out.append(dict(key='g:' + bid, name=cfg['name'], cat='TEMPLE BOSS' if temple else 'GUARDIAN',
                        hp=int(cfg['hp'] * (entities.TEMPLE_BOSS_HP if temple else 2.5)), dmg=cfg['dmg'] + 1,
                        note=("GUARDS A TIDE BELL DEEP IN ITS TEMPLE. " if temple else
                              "A GUARDIAN: FIGHT IT ONE-ON-ONE IN ITS LAIR. ") +
                        "IT BREAKS APART IN THREE STAGES, FIERCER EACH TIME.",
                        where=where('g:' + bid, "A TEMPLE"), sprite=spr))
    for key in ('shark', 'murk'):
        cls = entities.ENEMY_TYPES[key]
        out.append(dict(key=key, name=NAMES[key], cat='GREAT BOSS', hp=getattr(cls, 'max_hp', 30),
                        dmg=getattr(cls, 'damage', 2), note=(cls.__doc__ or "").strip().split(':', 1)[-1].strip().upper(),
                        where="SUNKEN SHRINE" if key == 'shark' else "MURK PALACE", sprite=_first(gfx.SPR[key])))
    out = [e for e in out if e['cat'] != 'GREAT BOSS' or e['key'] in ('shark', 'murk')]
    out.sort(key=lambda e: CATS.index(e['cat']))
    _entries = [e for i, e in enumerate(out) if e['key'] not in {x['key'] for x in out[:i]}]
    return _entries


_kinds = None


def beast_key(e):
    """The bestiary entry for an enemy on the screen."""
    global _kinds
    if isinstance(e, entities.MiniBoss):
        return 'g:' + e.bid
    if isinstance(e, entities.Critter):
        return e.kind
    if _kinds is None:
        _kinds = {cls: k for k, cls in entities.ENEMY_TYPES.items()}
        _kinds[entities.Thief] = 'thief'
        _kinds[entities.Patroller] = 'patroller'
    return _kinds.get(type(e))
