"""Life in the towns -- and the score that follows you everywhere.

TownLife is mixed into Game. It adds:
* the two towns: walking in and out, the welcome fly-over, townsfolk who wander, talk and trade
* side quests and the journal (press Q): quests, milestones, the leaderboard and extras
* the score: points for progress, milestones that unlock new features, the leaderboard
* the extras milestones unlock: the 3D Museum and Octo Radio
"""
import math

import pygame

import cinema
import folk
import forms
import gfx
import hifi
import score
import sound
import style
import world
from people import Citizen, LegendStatue, ScorePop
from settings import HI, HUD_H, PLAY_H, SCREEN_W, TILE

ACTION = {pygame.K_z, pygame.K_SPACE, pygame.K_j}
CONFIRM = {pygame.K_RETURN, pygame.K_KP_ENTER}
UP, DOWN = {pygame.K_UP, pygame.K_w}, {pygame.K_DOWN, pygame.K_s}
LEFT, RIGHT = {pygame.K_LEFT, pygame.K_a}, {pygame.K_RIGHT, pygame.K_d}
CLOSE = {pygame.K_ESCAPE, pygame.K_q, pygame.K_p, pygame.K_m, pygame.K_x, pygame.K_t}
TABS = ['QUESTS', 'SCORE', 'LEADERS', 'EXTRAS']
NAME_MAX = 10
GREETING = {
    'octo': ["WELCOME TO OCTO CITY!",
             "TALK TO EVERYONE HERE (PRESS Z NEXT TO THEM). A YELLOW ! MEANS SOMEONE NEEDS YOUR HELP, AND A GOLD "
             "COIN MEANS A SHOP.",
             "EVERYTHING YOU DO EARNS POINTS, AND MILESTONES UNLOCK NEW THINGS. TALLY BY THE SCOREBOARD KNOWS ALL "
             "ABOUT IT. PRESS Q ANY TIME FOR YOUR JOURNAL."],
    'turtle': ["WELCOME TO TURTLE TOWN!",
               "THE TURTLES HAVE SIDE QUESTS AND SHOPS OF THEIR OWN. TAKE YOUR TIME - NOBODY HERE IS IN A HURRY.",
               "PRESS Q FOR YOUR JOURNAL: YOUR QUESTS, YOUR SCORE AND THE LEADERBOARD."],
}
RADIO = [('title', "LEGEND OF OCTO"), ('reef', "CORAL REEF"), ('kelp', "KELP WOODS"), ('garden', "CORAL GARDENS"),
         ('lagoon', "THE LAGOON"), ('abyss', "THE ABYSS"), ('wreck', "SHIP GRAVEYARD"), ('frost', "FROZEN SHELF"),
         ('vents', "EMBER VENTS"), ('city', "SUNKEN CITY"), ('palace', "MURK PALACE"), ('sky', "SKY ISLANDS"),
         ('shrine', "SUNKEN SHRINE"), ('temple', "THE TEMPLES"), ('trial', "TRIALS"), ('boss', "BOSS BATTLE"),
         ('octocity', "OCTO CITY"), ('turtletown', "TURTLE TOWN"), ('victory', "VICTORY")] + \
    [('r_' + t, n) for t, n in (('glass', "GLASS REEF"), ('siren', "SIREN SHOALS"), ('whale', "WHALE FALL"),
                                ('thunder', "THUNDERHEADS"), ('rainbow', "RAINBOW REACH"),
                                ('starfall', "STARFALL PEAKS"), ('beach', "SUNNY BEACH"), ('meadow', "TIDE MEADOWS"),
                                ('jungle', "PALM JUNGLE"), ('desert', "DUNE DESERT"), ('volcano', "VOLCANO RIDGE"),
                                ('crystal', "CRYSTAL CAVES"), ('fungus', "FUNGUS GROTTO"), ('bone', "BONE TRENCH"),
                                ('ruins', "ANCIENT RUINS"), ('magma', "MAGMA CORE"))]


def _px(tx, ty):
    return tx * TILE + TILE / 2 - 8, ty * TILE + TILE / 2 - 8


def _fmt(n):
    return f"{n:,}"


class TownLife:
    # ==================================================================
    # setup (called from new_game / load_game)
    # ==================================================================
    def town_setup(self):
        fl = self.flags
        fl.setdefault('score', 0)
        fl.setdefault('run', score.new_run_id())
        self.board = score.load_board()
        self.citizens = {}
        for nid, d in folk.NPCS.items():
            spot = world.CITIES[d['town']]['spots'].get(nid) or folk.QUEST_SPOTS['sister'][0]
            c = Citizen(nid, *_px(*spot))
            self.citizens[nid] = c
            self.npcs.append(c)
        sx, sy = world.CITIES['octo']['spots']['statue']
        self.statue = LegendStatue(*_px(sx, sy))
        self.npcs.append(self.statue)
        self.medal_queue = []
        self.medal = self.cityintro = None
        self.jtab = self.jsel = 0
        self._score_base = self._counts()
        self.update_tilly()

    def town_after_load(self, had_score):
        """A loaded game: put quest things back, and give old saves the score they've earned."""
        for qid, st in self.quests().items():
            if st['s'] == 'active' and folk.QUESTS[qid]['kind'] == 'collect':
                self.spawn_quest_items(qid)
        self.update_tilly()
        if not had_score:                             # a save from before scores: count its progress
            base = {'base_form': 2, 'heart': 3}
            pts = sum(max(0, v - base.get(k, 0)) * score.POINTS.get(k, 0) for k, v in self._counts().items())
            self.flags['score'] = pts
            got = self.flags.setdefault('milestones', [])
            names = []
            for p_, mid, title, desc in score.MILESTONES:
                if pts >= p_ and mid not in got:
                    got.append(mid)
                    self.apply_unlock(mid, quiet=True)
                    names.append(title)
            if pts:
                self.say_later = ["YOUR LEGEND HAS BEEN WRITTEN DOWN: " + _fmt(pts) + " POINTS SO FAR!"] + \
                    (["MILESTONES UNLOCKED: " + ", ".join(names) + "."] if names else [])
        self._score_base = self._counts()

    # ==================================================================
    # the score
    # ==================================================================
    def score(self):
        return self.flags.get('score', 0)

    def add_score(self, pts, pos=None):
        if pts <= 0:
            return
        if self.flags.get('deep'):
            pts = int(pts * 1.5)                       # the Deep Tide is worth more
        self.flags['score'] = self.score() + pts
        if pos is not None:
            self.effects.append(ScorePop(pos[0], pos[1] - 8, pts))
        self.check_milestones()

    def _counts(self):
        p, fl = self.player, self.flags
        return {'trial': len(self.trials_done), 'bell': len(fl.get('bells', [])), 'guardian': len(fl.get('minis', [])),
                'base_form': sum(1 for f in p.forms if f in forms.BASE),
                'fusion': sum(1 for f in p.forms if f in forms.FUSIONS),
                'mega': sum(1 for f in p.forms if forms.is_mega(f)), 'heart': p.max_hp // 2,
                'grimfin': 1 if fl.get('shark_dead') else 0, 'murk': 1 if fl.get('murk_dead') else 0,
                'region': len(fl.get('regions_seen', [])), 'temple': len(fl.get('temples_seen', [])),
                'town': len(fl.get('towns_seen', []))}

    def score_watch(self):
        """Points for every step forward, however it happened (trials, bells, forms, hearts...)."""
        counts = self._counts()
        base = self._score_base
        for k, v in counts.items():
            if v > base.get(k, 0):
                self.add_score((v - base.get(k, 0)) * score.POINTS[k], self.player.rect.center)
        self._score_base = counts

    def score_kill(self, e):
        from entities import MiniBoss
        if isinstance(e, MiniBoss):
            if getattr(e, 'in_temple', False):
                self.flags.setdefault('tbosses', [])
                if e.bid not in self.flags['tbosses']:
                    self.flags['tbosses'].append(e.bid)
                pts = 800
            elif getattr(e, 'in_trial', False):
                pts = 150
            else:
                pts = 0                                 # guardians count through score_watch
        elif getattr(e, 'boss', False):
            pts = 0
        else:
            cx, cy = e.rect.center
            pts = 5 + 5 * self.tier_at(cx // TILE, cy // TILE)
        if pts:
            self.add_score(pts, e.rect.center)
        # side quests that want creatures beaten somewhere
        cx, cy = e.rect.center
        tx, ty = cx // TILE, cy // TILE
        for qid, st in self.quests().items():
            q = folk.QUESTS[qid]
            if st['s'] != 'active' or q['kind'] != 'kill' or st['n'] >= q['n']:
                continue
            if ('region' in q and world.region_at(tx, ty) != q['region']) or \
                    ('world' in q and world.world_at(tx, ty) != q['world']):
                continue
            st['n'] += 1
            self.toast = (f"{q['title']}: {st['n']}/{q['n']}", 80)

    def town_region(self, region):
        """Octo swam into a new region (first visits score; postcard quests note them)."""
        seen = self.flags.setdefault('regions_seen', [])
        if region and region not in seen and region != 'BOSS LAIR':
            seen.append(region)
        for qid, st in self.quests().items():
            q = folk.QUESTS[qid]
            if st['s'] == 'active' and q['kind'] == 'visit' and region in q['regions'] and region not in st['seen']:
                st['seen'].append(region)
                self.toast = (f"{q['title']}: {len(st['seen'])}/{len(q['regions'])}", 110)
                sound.play('key')

    # ---- milestones ---------------------------------------------------
    def check_milestones(self):
        got = self.flags.setdefault('milestones', [])
        for pts, mid, title, desc in score.MILESTONES:
            if self.score() >= pts and mid not in got:
                got.append(mid)
                self.apply_unlock(mid)
                self.medal_queue.append((pts, mid, title, desc))
                self.record_score()

    def apply_unlock(self, mid, quiet=False):
        p = self.player
        p.items.add('u_' + mid)
        if mid == 'heart':
            p.max_hp += 2
            p.hp = p.max_hp
            self._score_base['heart'] = p.max_hp // 2      # this heart isn't worth points itself
        elif mid == 'legend':
            p.items.add('hat_champion')
            p.items.add('ink_legend')

    def unlocked(self, mid):
        return 'u_' + mid in self.player.items

    def start_medal(self):
        pts, mid, title, desc = self.medal_queue.pop(0)
        self.medal = cinema.MedalCut(pts, title, desc)
        self.medal_info = (pts, mid, title, desc)
        self.medal_t = 0
        self.state = 'medal'

    def update_medal(self):
        self.medal_t += 1
        for name in self.medal.cues(self.medal_t):
            sound.play(name)
        if self.medal.done:
            self.end_medal()

    def end_medal(self):
        pts, mid, title, desc = self.medal_info
        self.medal = None
        self.state = 'play'
        then = self.open_name if not self.board.get('name') else None
        pages = [f"MILESTONE: {_fmt(pts)} POINTS!", f"UNLOCKED - {title}: {desc}"]
        if then:
            pages.append("PUT YOUR NAME ON THE LEADERBOARD!")
        self.say(pages, then=then)

    # ---- leaderboard ----------------------------------------------------
    def player_name(self):
        return self.board.get('name') or "OCTO"

    def record_score(self):
        score.record(self.board, self.flags.get('run'), self.player_name(), self.score(), bool(self.flags.get('deep')))
        score.save_board(self.board)

    def ranking(self):
        return score.ranking(self.board, folk.RIVALS, self.flags.get('run'), self.player_name(), self.score(),
                             bool(self.flags.get('deep')))

    def open_name(self, back='play'):
        name = self.board.get('name') or "OCTO"
        self.name_buf = list(name[:NAME_MAX])
        self.name_c = len(self.name_buf) - 1
        self.name_back = back
        self.state = 'name'
        sound.play('pause')

    def name_key(self, k):
        buf = self.name_buf
        if k in CONFIRM:
            name = ''.join(buf).strip() or "OCTO"
            self.board['name'] = name
            self.record_score()
            sound.play('item')
            self.state = self.name_back
            self.toast = (f"HELLO, {name}!", 100)
            return
        if k == pygame.K_ESCAPE:
            self.state = self.name_back
            return
        if pygame.K_a <= k <= pygame.K_z or pygame.K_0 <= k <= pygame.K_9 or k == pygame.K_SPACE:
            ch = ' ' if k == pygame.K_SPACE else chr(k).upper()
            if self.name_c == len(buf) - 1 and len(buf) < NAME_MAX and buf[self.name_c] != ' ':
                buf.append(ch)
                self.name_c += 1
            else:
                buf[self.name_c] = ch
                self.name_c = min(len(buf) - 1, self.name_c + 1)
            sound.play('text')
            return
        if k == pygame.K_BACKSPACE:
            if len(buf) > 1:
                del buf[self.name_c]
                self.name_c = max(0, self.name_c - 1)
            else:
                buf[0] = ' '
            sound.play('text')
        elif k in (pygame.K_UP, pygame.K_DOWN):
            letters = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.!"
            i = letters.find(buf[self.name_c])
            i = (i + (1 if k == pygame.K_UP else -1)) % len(letters)
            buf[self.name_c] = letters[i]
            sound.play('text')
        elif k == pygame.K_RIGHT:
            if self.name_c == len(buf) - 1 and len(buf) < NAME_MAX:
                buf.append('A')
            self.name_c = min(len(buf) - 1, self.name_c + 1)
            sound.play('text')
        elif k == pygame.K_LEFT:
            self.name_c = max(0, self.name_c - 1)
            sound.play('text')

    def draw_name(self, scr):
        box = pygame.Rect(16, HUD_H + 30, SCREEN_W - 32, 110)
        self.draw_box(scr, box)
        gfx.text(scr, "YOUR NAME FOR THE LEADERBOARD", SCREEN_W // 2, box.y + 8, (255, 220, 120), center=True)
        n = len(self.name_buf)
        x0 = SCREEN_W // 2 - n * 8
        for i, ch in enumerate(self.name_buf):
            x = x0 + i * 16
            on = i == self.name_c
            pygame.draw.rect(scr, (255, 220, 120) if on else (70, 80, 120), (x, box.y + 28, 14, 18), 1)
            if not (on and (self.t // 15) % 2 == 0 and ch == ' '):
                self.big_text(scr, ch, x + 7, box.y + 30, (255, 255, 255) if on else (190, 200, 230))
            if on:
                gfx.text(scr, "+", x + 4, box.y + 18, (150, 160, 200))
                gfx.text(scr, "-", x + 4, box.y + 49, (150, 160, 200))
        for j, line in enumerate(["TYPE IT, OR UP/DOWN TO PICK LETTERS", "LEFT/RIGHT MOVE   BACKSPACE DELETES",
                                  "ENTER (OR TAP) WHEN YOU'RE DONE"]):
            gfx.text(scr, line, SCREEN_W // 2, box.y + 64 + j * 11, (170, 180, 220), center=True)

    # ==================================================================
    # the towns
    # ==================================================================
    def enter_city(self, cid):
        c = world.CITIES[cid]
        self._clear_field()
        sound.play('door')
        self._move_player(*c['entry'], 'up')
        self.checkpoint = c['entry']
        seen = self.flags.setdefault('towns_seen', [])
        if cid not in seen:
            seen.append(cid)
            self.cityintro = cinema.CityIntro(cid)
            self.ci_t = 0
            self.ci_town = cid
            self.state = 'cityintro'
        else:
            self.toast = ("WELCOME BACK TO " + c['title'] + "!", 110)

    def leave_city(self, cid):
        c = world.CITIES[cid]
        self._clear_field()
        sound.play('door')
        self._move_player(*c['exit_to'], 'down')
        self.checkpoint = c['exit_to']

    def update_cityintro(self):
        self.ci_t += 1
        for name in self.cityintro.cues(self.ci_t):
            sound.play(name)
        if self.cityintro.done:
            self.end_cityintro()

    def end_cityintro(self):
        self.cityintro = None
        self.state = 'play'
        sound.music(self.area_music())
        self.say(GREETING[self.ci_town])

    def update_tilly(self):
        """Tilly hides in Palm Jungle while Tiny Tim's quest is on, and goes home once found."""
        tilly = self.citizens.get('tilly') if hasattr(self, 'citizens') else None
        if tilly is None:
            return
        st = self.qstate('sister')
        if st is None:
            tilly.hidden = True
            return
        tilly.hidden = False
        home = st['s'] == 'done' or st.get('found')
        spot = world.CITIES['turtle']['spots']['tilly_home'] if home else folk.QUEST_SPOTS['sister'][0]
        want = _px(*spot)
        if math.hypot(tilly.home[0] - want[0], tilly.home[1] - want[1]) > 2:
            tilly.place(*want)

    def town_tick(self):
        """Every frame of play."""
        lv = self.level
        lv.blockers = [n.rect for n in self.npcs if not getattr(n, 'hidden', False)]
        if self.t % 15 == 0:
            for nid, c in self.citizens.items():
                c.icon = self.npc_icon(nid)
        self.score_watch()
        if self.medal_queue and self.state == 'play' and not (self.trial or self.bossfight or self.active_arena):
            self.start_medal()
        if getattr(self, 'say_later', None) and self.state == 'play':
            pages, self.say_later = self.say_later, None
            self.say(pages)

    # ==================================================================
    # talking
    # ==================================================================
    def talk_citizen(self, npc):
        nid = npc.id
        p = self.player
        met = self.flags.setdefault('met', [])
        if nid not in met:
            met.append(nid)
            self.add_score(20, npc.rect.center)
        d = folk.NPCS[nid]
        name = d['name']
        # 1. something you're carrying (or someone you're looking for) for this person
        for qid, st in list(self.quests().items()):
            q = folk.QUESTS[qid]
            if st['s'] != 'active':
                continue
            if q['kind'] == 'deliver' and q['to'] == nid:
                self.finish_quest(qid)
                return
            if q['kind'] == 'chain' and st['step'] < len(q['steps']):
                who, need, give, pages = q['steps'][st['step']]
                if who == nid and need in p.items:
                    p.items.discard(need)
                    p.items.add(give)
                    st['step'] += 1
                    sound.play('item')
                    self.add_score(100, npc.rect.center)
                    self.say(pages + [f"YOU GAVE THE {folk.ITEM_NAMES[need]} AND GOT THE {folk.ITEM_NAMES[give]}!"])
                    return
            if q['kind'] == 'find' and q['who'] == nid and not st.get('found'):
                st['found'] = True
                sound.play('item')
                self.say([name + ": " + d['lines'][0],
                          f"{name} HURRIES HOME. GO BACK AND TELL {folk.NPCS[q['giver']]['name']}!"])
                self.update_tilly()
                return
        # 2. this person's own quests
        for qid in d.get('quests', []):
            st = self.qstate(qid)
            q = folk.QUESTS[qid]
            if st and st['s'] == 'active':
                if self.quest_ready(qid):
                    self.finish_quest(qid)
                    return
                if 'shop' not in d:
                    have, need = self.quest_progress(qid)
                    self.say([f"{name}: {q['nag']}  ({have}/{need})"])
                    return
                break
            if st is None:
                self.start_quest(qid)
                self.say(q['offer'] + [f"NEW SIDE QUEST: {q['title']}!  (PRESS Q TO SEE YOUR QUESTS)"])
                return
        # 3. shops and jobs
        if 'shop' in d:
            self.open_trade(d['shop'], name)
            return
        if d.get('role') == 'scores':
            rank = next((i + 1 for i, r in enumerate(self.ranking()) if r[3]), None)
            nxt, title = score.next_milestone(self.score())
            pages = [name + ": " + d['lines'][npc.talks % len(d['lines'])],
                     f"YOUR SCORE: {_fmt(self.score())} - THAT'S #{rank} ON THE LEADERBOARD."]
            if nxt:
                pages.append(f"NEXT MILESTONE: {_fmt(nxt)} POINTS UNLOCKS {title}.")
            npc.talks += 1
            self.say(pages, then=lambda: self.open_journal(2))
            return
        if nid == 'octagon' and self.unlocked('museum'):
            self.say(["PROFESSOR OCTAGON: WELCOME TO THE MUSEUM! EVERY GUARDIAN YOU'VE BEATEN STANDS HERE IN 3D."],
                     then=self.open_museum)
            return
        lines = d['lines']
        self.say([name + ": " + lines[npc.talks % len(lines)]])
        npc.talks += 1

    def talk_statue(self):
        if self.unlocked('legend'):
            self.say([f"A GOLDEN STATUE OF {self.player_name()}, THE LIVING LEGEND OF THE DEEP. "
                      f"SCORE: {_fmt(self.score())}."])
        else:
            self.say(["AN EMPTY PLINTH. THE SIGN SAYS: 'RESERVED FOR A LIVING LEGEND - 100,000 POINTS.'"])

    def npc_icon(self, nid):
        d = folk.NPCS[nid]
        for qid, st in self.quests().items():
            if st['s'] != 'active':
                continue
            q = folk.QUESTS[qid]
            if q['kind'] == 'deliver' and q['to'] == nid:
                return 'ready'
            if q['kind'] == 'chain' and st['step'] < len(q['steps']) and q['steps'][st['step']][0] == nid:
                return 'chain'
            if q['kind'] == 'find' and q['who'] == nid and not st.get('found'):
                return 'ready'
        for qid in d.get('quests', []):
            st = self.qstate(qid)
            if st and st['s'] == 'active':
                return 'ready' if self.quest_ready(qid) else 'busy'
            if st is None:
                return 'new'
        return 'shop' if 'shop' in d else None

    # ==================================================================
    # side quests
    # ==================================================================
    def quests(self):
        return self.flags.setdefault('quests', {})

    def qstate(self, qid):
        return self.quests().get(qid)

    def start_quest(self, qid):
        q = folk.QUESTS[qid]
        p = self.player
        st = {'s': 'active', 'n': 0}
        kind = q['kind']
        if kind == 'trials':
            st['base'] = len(self.trials_done)
        elif kind == 'visit':
            st['seen'] = []
        elif kind == 'deliver':
            p.items.add('q_' + qid)
        elif kind == 'chain':
            st['step'] = 0
            p.items.add(q['first'])
        self.quests()[qid] = st
        if kind == 'collect':
            self.spawn_quest_items(qid)
        if kind == 'find':
            self.update_tilly()
        sound.play('key')

    def spawn_quest_items(self, qid):
        q = folk.QUESTS[qid]
        have = {i.item_id for i in self.pickups}
        for i, (tx, ty) in enumerate(folk.QUEST_SPOTS[qid]):
            iid = ('quest', qid, i)
            if iid not in self.collected and iid not in have:
                self.place_item(q['item'], tx, ty, iid)

    def quest_item_got(self, it):
        qid = it.item_id[1] if isinstance(it.item_id, tuple) and len(it.item_id) > 1 else None
        st = self.qstate(qid) if qid else None
        if not st:
            return
        q = folk.QUESTS[qid]
        st['n'] = min(len(folk.QUEST_SPOTS[qid]), st['n'] + 1)
        need = len(folk.QUEST_SPOTS[qid])
        sound.play('item')
        self.burst(it.rect.center, (255, 230, 160), 10)
        self.add_score(50, it.rect.center)
        if st['n'] >= need:
            self.toast = (f"ALL {need} FOUND! TAKE THEM TO {folk.NPCS[q['giver']]['name']}.", 160)
        else:
            self.toast = (f"{q['thing']} {st['n']}/{need}", 100)

    def quest_progress(self, qid):
        q, st = folk.QUESTS[qid], self.qstate(qid) or {}
        kind = q['kind']
        if kind == 'collect':
            return st.get('n', 0), len(folk.QUEST_SPOTS[qid])
        if kind == 'kill':
            return min(st.get('n', 0), q['n']), q['n']
        if kind == 'visit':
            return len(st.get('seen', [])), len(q['regions'])
        if kind == 'find':
            return (1 if st.get('found') else 0), 1
        if kind == 'guardians':
            return min(len(self.flags.get('minis', [])), q['n']), q['n']
        if kind == 'trials':
            return max(0, min(len(self.trials_done) - st.get('base', 0), q['n'])), q['n']
        if kind == 'fusion':
            return (1 if self.is_fused() else 0), 1
        if kind == 'chain':
            return st.get('step', 0), len(q['steps']) + 1
        return 0, 1

    def is_fused(self):
        m = self.player.mood
        return m in forms.FUSIONS or forms.is_mega(m)

    def quest_ready(self, qid):
        q, st = folk.QUESTS[qid], self.qstate(qid)
        if not st or st['s'] != 'active':
            return False
        if q['kind'] == 'deliver':
            return False
        if q['kind'] == 'chain':
            return st.get('step', 0) >= len(q['steps']) and q['steps'][-1][2] in self.player.items
        have, need = self.quest_progress(qid)
        return have >= need

    def finish_quest(self, qid):
        q, st = folk.QUESTS[qid], self.qstate(qid)
        p = self.player
        st['s'] = 'done'
        p.items.discard('q_' + qid)
        if q['kind'] == 'chain':
            p.items.discard(q['steps'][-1][2])
        r = q['reward']
        got = []
        if r.get('pearls'):
            p.pearls += r['pearls']
            got.append(f"{r['pearls']} PEARLS")
        if r.get('spirit'):
            p.spirit += r['spirit']
            got.append(f"{r['spirit']} SPIRIT PEARL" + ("S" if r['spirit'] > 1 else ""))
        if r.get('potion'):
            p.potions = min(2, p.potions + r['potion'])
            got.append("A SEA POTION")
        if r.get('heart'):
            p.max_hp += 2 * r['heart']
            p.hp = p.max_hp
            got.append("A HEART SHELL")
        if r.get('item'):
            p.items.add(r['item'])
            iid = r['item']
            if iid.startswith('hat_'):
                got.append(style.HATS[iid[4:]][0] + " (WEAR IT: PRESS H)")
            elif iid.startswith('ink_'):
                got.append(next(n for n, c, need in style.DASH_COLORS if need == iid) + " INK (PRESS H)")
        self.add_score(r.get('score', 0), p.rect.center)
        sound.play('item')
        self.burst(p.rect.center, (255, 240, 160), 16)
        self.record_score()
        self.update_tilly()
        self.say(q['done'] + [f"QUEST COMPLETE: {q['title']}!", "REWARD: " + ", ".join(got + [
            f"{_fmt(r.get('score', 0))} POINTS"]) + "."])

    def quest_targets(self):
        """Where active quests lead, for the Quest Compass: [(tile x, tile y)]."""
        out = []
        for qid, st in self.quests().items():
            if st['s'] != 'active':
                continue
            q = folk.QUESTS[qid]
            if q['kind'] == 'collect':
                for i, spot in enumerate(folk.QUEST_SPOTS[qid]):
                    if ('quest', qid, i) not in self.collected:
                        out.append(spot)
            elif q['kind'] == 'find' and not st.get('found'):
                out += folk.QUEST_SPOTS['sister']
            elif q['kind'] == 'deliver':
                out.append(world.CITIES[folk.NPCS[q['to']]['town']]['door'])
            elif q['kind'] == 'chain' and st['step'] < len(q['steps']):
                out.append(world.CITIES[folk.NPCS[q['steps'][st['step']][0]]['town']]['door'])
        return out

    def draw_quest_marks(self, scr, spot, inside):
        if not self.unlocked('compass'):
            return
        for tx, ty in self.quest_targets():
            if inside(tx, ty):
                sx, sy = spot(tx, ty)
                pygame.draw.rect(scr, (0, 0, 0), (sx - 2, sy - 5, 5, 9))
                pygame.draw.line(scr, (255, 220, 60), (sx, sy - 4), (sx, sy))
                scr.set_at((sx, sy + 2), (255, 220, 60))

    def draw_treasure_marks(self, scr, spot, inside):
        if not self.unlocked('treasure'):
            return
        for i, (kind, tx, ty) in enumerate(world.ITEMS):
            if ('item', i) not in self.collected and inside(tx, ty) and kind not in ('shrimp',):
                sx, sy = spot(tx, ty)
                pygame.draw.circle(scr, (120, 255, 160), (sx, sy), 1)

    # ==================================================================
    # shops
    # ==================================================================
    def price(self, cost):
        res, amt = cost
        if res == 'pearls' and self.unlocked('goldcard'):
            return res, max(1, int(amt * 0.75 + 0.5))
        return res, amt

    def open_trade(self, shop, who):
        self.trade = {'shop': shop, 'who': who, 'i': 0, 'msg': ''}
        self.state = 'trade'
        sound.play('pause')

    def trade_key(self, k):
        offers = folk.SHOPS[self.trade['shop']][1]
        if k in UP:
            self.trade['i'] = (self.trade['i'] - 1) % len(offers)
            self.trade['msg'] = ''
            sound.play('text')
        elif k in DOWN:
            self.trade['i'] = (self.trade['i'] + 1) % len(offers)
            self.trade['msg'] = ''
            sound.play('text')
        elif k in ACTION or k in CONFIRM:
            self.do_trade(offers[self.trade['i']])
        elif k in CLOSE:
            self.state = 'play'
            sound.play('pause')

    def _have(self, res):
        p = self.player
        return {'pearls': p.pearls, 'spirit': p.spirit, 'bombs': p.bombs}.get(res, 0)

    def trades_done(self, oid):
        return self.flags.setdefault('trades', {}).get(oid, 0)

    def do_trade(self, offer):
        oid, label, cost, (get, n), limit = offer
        res, amt = self.price(cost)
        p = self.player
        tr = self.trade
        if limit is not None and self.trades_done(oid) >= limit or (get.startswith(('hat_', 'ink_')) and get in p.items):
            tr['msg'] = "SOLD OUT!" if not get.startswith(('hat_', 'ink_')) else "YOU ALREADY HAVE IT!"
            sound.play('nope')
            return
        if self._have(res) < amt:
            tr['msg'] = f"YOU NEED {amt} {res.upper()}."
            sound.play('nope')
            return
        if get == 'bombs' and 'bombbag' not in p.items:
            tr['msg'] = "YOU NEED A BOMB BAG FIRST (HERMIE'S SHOP)."
            sound.play('nope')
            return
        if get == 'potion' and p.potions >= 2:
            tr['msg'] = "YOU CAN ONLY CARRY TWO POTIONS."
            sound.play('nope')
            return
        if get == 'heal' and p.hp >= p.max_hp:
            tr['msg'] = "YOU'RE ALREADY FIT AS A FIDDLE!"
            sound.play('nope')
            return
        if res == 'pearls':
            p.pearls -= amt
        elif res == 'spirit':
            p.spirit -= amt
        elif res == 'bombs':
            p.bombs -= amt
        if get == 'pearls':
            p.pearls += n
        elif get == 'spirit':
            p.spirit += n
        elif get == 'bombs':
            from entities import max_bombs
            p.bombs = min(max_bombs(p), p.bombs + n)
        elif get == 'potion':
            p.potions = min(2, p.potions + n)
        elif get == 'heal':
            p.hp = p.max_hp
            sound.play('munch')
        elif get == 'heart':
            p.max_hp += 2
            p.hp = p.max_hp
        else:
            p.items.add(get)
        t = self.flags.setdefault('trades', {})
        t[oid] = t.get(oid, 0) + 1
        self.add_score(10)
        sound.play('buy')
        tr['msg'] = "THANK YOU!" if not get.startswith(('hat_', 'ink_')) else "YOURS NOW! PRESS H TO TRY IT ON."

    def draw_trade(self, scr):
        p = self.player
        title, offers = folk.SHOPS[self.trade['shop']]
        box = pygame.Rect(8, HUD_H + 3, SCREEN_W - 16, PLAY_H - 6)
        self.draw_box(scr, box)
        gfx.text(scr, title, SCREEN_W // 2, box.y + 5, (255, 220, 120), center=True)
        have = f"YOU HAVE {p.pearls} PEARLS, {p.spirit} SPIRIT, {p.bombs} BOMBS"
        gfx.text(scr, have, SCREEN_W // 2, box.y + 16, (170, 180, 220), center=True)
        if self.unlocked('goldcard'):
            gfx.text(scr, "GOLD CARD: 25% OFF!", SCREEN_W // 2, box.y + 26, (255, 210, 80), center=True)
        for j, (oid, label, cost, (get, n), limit) in enumerate(offers):
            y = box.y + 40 + j * 13
            on = j == self.trade['i']
            res, amt = self.price(cost)
            owned = get.startswith(('hat_', 'ink_')) and get in p.items
            out = limit is not None and self.trades_done(oid) >= limit
            ok = self._have(res) >= amt and not owned and not out
            if on:
                gfx.text(scr, ">", box.x + 5, y, (255, 220, 120))
            col = (120, 200, 140) if owned else (255, 255, 255) if ok else (150, 150, 175)
            gfx.text(scr, label, box.x + 14, y, col)
            tag = "OWNED" if owned else "SOLD OUT" if out else f"{amt} {'SPIRIT' if res == 'spirit' else res.upper()}"
            gfx.text(scr, tag, box.right - 6 - gfx.text_width(tag), y, col)
            if get.startswith('hat_') and on:
                img = style.icon(get[4:])
                if img:
                    scr.blit(pygame.transform.scale(img, (36, 24)), (box.right - 46, box.bottom - 58))
            if get.startswith('ink_') and on:
                idx = next(i for i, (nm, c, need) in enumerate(style.DASH_COLORS) if need == get)
                for i in range(5):
                    pygame.draw.circle(scr, style.dash_rgb(idx, self.t + i * 3), (box.right - 50 + i * 8, box.bottom - 46),
                                       5 - i // 2)
        msg = self.trade['msg']
        if msg:
            gfx.text(scr, msg, SCREEN_W // 2, box.bottom - 24, (255, 220, 120), center=True)
        gfx.text(scr, "Z: TRADE   ESC: LEAVE", SCREEN_W // 2, box.bottom - 10, (140, 150, 190), center=True)

    # ==================================================================
    # the journal (Q)
    # ==================================================================
    def open_journal(self, tab=0):
        if self.trial or self.bossfight:
            sound.play('nope')
            return
        self.jtab = tab
        self.jsel = 0
        self.state = 'journal'
        sound.play('pause')

    def journal_rows(self):
        if self.jtab == 0:
            qs = self.quests()
            active = [q for q in folk.QUESTS if q in qs and qs[q]['s'] == 'active']
            done = [q for q in folk.QUESTS if q in qs and qs[q]['s'] == 'done']
            return active + done
        if self.jtab == 1:
            return score.MILESTONES
        if self.jtab == 2:
            return self.ranking()
        return ['museum', 'radio', 'name']

    def journal_key(self, k):
        rows = self.journal_rows()
        if k in LEFT or k in RIGHT:
            self.jtab = (self.jtab + (1 if k in RIGHT else -1)) % len(TABS)
            self.jsel = 0
            if self.jtab == 2:
                self.record_score()
            sound.play('text')
        elif k in UP and rows:
            self.jsel = (self.jsel - 1) % len(rows)
            sound.play('text')
        elif k in DOWN and rows:
            self.jsel = (self.jsel + 1) % len(rows)
            sound.play('text')
        elif (k in ACTION or k in CONFIRM) and self.jtab == 3:
            what = rows[self.jsel]
            if what == 'name':
                self.open_name(back='journal')
            elif not self.unlocked(what):
                sound.play('nope')
            elif what == 'museum':
                self.open_museum(back='journal')
            else:
                self.open_radio()
        elif (k in ACTION or k in CONFIRM) and self.jtab == 2:
            self.open_name(back='journal')
        elif k in CLOSE:
            self.state = 'play'
            sound.play('pause')

    def draw_journal(self, scr):
        box = pygame.Rect(6, HUD_H + 2, SCREEN_W - 12, PLAY_H - 4)
        self.draw_box(scr, box)
        tw = (box.w - 8) // len(TABS)
        for i, name in enumerate(TABS):
            r = pygame.Rect(box.x + 4 + i * tw, box.y + 4, tw - 2, 12)
            on = i == self.jtab
            pygame.draw.rect(scr, (60, 70, 130) if on else (20, 24, 50), r)
            pygame.draw.rect(scr, (255, 220, 120) if on else (70, 80, 120), r, 1)
            gfx.text(scr, name, r.centerx, r.y + 3, (255, 230, 150) if on else (150, 160, 200), center=True)
        rows = self.journal_rows()
        y0 = box.y + 22
        if self.jtab == 0:
            self._draw_quests(scr, box, rows, y0)
        elif self.jtab == 1:
            self._draw_milestones(scr, box, rows, y0)
        elif self.jtab == 2:
            self._draw_leaders(scr, box, rows, y0)
        else:
            self._draw_extras(scr, box, rows, y0)
        gfx.text(scr, "<> TABS   Q: CLOSE", SCREEN_W // 2, box.bottom - 9, (130, 140, 180), center=True)

    def _list(self, rows, show):
        top = max(0, min(self.jsel - show // 2, len(rows) - show))
        return top, rows[top:top + show]

    def _check(self, scr, x, y, col=(120, 230, 140)):
        pygame.draw.line(scr, col, (x, y + 3), (x + 2, y + 5))
        pygame.draw.line(scr, col, (x + 2, y + 5), (x + 6, y))

    def _draw_quests(self, scr, box, rows, y0):
        if not rows:
            msg = ("NO SIDE QUESTS YET. THE TOWNSFOLK OF OCTO CITY (ITS GATE IS BY THE OCTO TEMPLE) AND TURTLE TOWN "
                   "(ON SUNNY BEACH) NEED YOUR HELP. LOOK FOR A YELLOW ! ABOVE THEIR HEADS.")
            for j, line in enumerate(gfx.wrap(msg, 38)):
                gfx.text(scr, line, box.x + 8, y0 + 8 + j * 11, (200, 210, 240))
            return
        done_n = sum(1 for q in rows if self.qstate(q)['s'] == 'done')
        gfx.text(scr, f"{done_n}/{len(folk.QUESTS)} DONE", box.right - 8 - gfx.text_width(f"{done_n}/{len(folk.QUESTS)} DONE"),
                 y0, (150, 160, 200))
        self.jsel = min(self.jsel, len(rows) - 1)
        top, vis = self._list(rows, 6)
        for j, qid in enumerate(vis):
            i = top + j
            y = y0 + 10 + j * 11
            q, st = folk.QUESTS[qid], self.qstate(qid)
            on = i == self.jsel
            if on:
                gfx.text(scr, ">", box.x + 4, y, (255, 220, 120))
            if st['s'] == 'done':
                self._check(scr, box.x + 12, y)
                gfx.text(scr, q['title'], box.x + 22, y, (130, 170, 140))
            else:
                ready = self.quest_ready(qid)
                gfx.text(scr, q['title'], box.x + 22, y, (255, 230, 120) if ready else (255, 255, 255))
                have, need = self.quest_progress(qid)
                tag = "DONE! GO BACK" if ready else f"{have}/{need}"
                gfx.text(scr, tag, box.right - 8 - gfx.text_width(tag), y, (255, 220, 120) if ready else (170, 180, 220))
        qid = rows[self.jsel]
        q, st = folk.QUESTS[qid], self.qstate(qid)
        giver = folk.NPCS[q['giver']]
        town = world.CITIES[giver['town']]['title']
        y = box.y + 104
        pygame.draw.line(scr, (60, 70, 110), (box.x + 4, y - 3), (box.right - 4, y - 3))
        gfx.text(scr, f"FROM {giver['name']}, {town}", box.x + 8, y, (170, 200, 255))
        if st['s'] == 'done':
            text = "ALL DONE - THANK YOU!"
        elif q['kind'] == 'chain' and st['step'] < len(q['steps']):
            who, need, give, pages = q['steps'][st['step']]
            text = f"TAKE THE {folk.ITEM_NAMES[need]} TO {folk.NPCS[who]['name']} IN " \
                   f"{world.CITIES[folk.NPCS[who]['town']]['title']}."
        elif q['kind'] == 'chain':
            text = f"BRING THE {folk.ITEM_NAMES[q['steps'][-1][2]]} BACK TO {giver['name']}."
        elif self.quest_ready(qid):
            text = f"DONE! GO BACK TO {giver['name']} IN {town}."
        elif q['kind'] == 'deliver':
            text = f"TAKE THE {q['thing']} TO {folk.NPCS[q['to']]['name']}: {q['where']}."
        else:
            text = q['nag']
        for j, line in enumerate(gfx.wrap(text, 37)[:4]):
            gfx.text(scr, line, box.x + 8, y + 11 + j * 10, (210, 220, 245))

    def _draw_milestones(self, scr, box, rows, y0):
        sc = self.score()
        gfx.text(scr, "SCORE", box.x + 8, y0 + 2, (170, 180, 220))
        self.big_text(scr, _fmt(sc), box.x + 40 + gfx.text_width(_fmt(sc)), y0 - 2, (255, 230, 120))
        nxt, title = score.next_milestone(sc)
        prev = max([p_ for p_, *_ in score.MILESTONES if p_ <= sc], default=0)
        bx, by, bw = box.x + 8, y0 + 18, box.w - 16
        pygame.draw.rect(scr, (30, 34, 60), (bx, by, bw, 5))
        if nxt:
            k = (sc - prev) / max(1, nxt - prev)
            pygame.draw.rect(scr, (255, 200, 70), (bx, by, int(bw * k), 5))
            gfx.text(scr, f"NEXT: {title} AT {_fmt(nxt)}", box.x + 8, by + 8, (200, 210, 240))
        else:
            pygame.draw.rect(scr, (255, 200, 70), (bx, by, bw, 5))
            gfx.text(scr, "EVERY MILESTONE REACHED!", box.x + 8, by + 8, (255, 220, 120))
        top, vis = self._list(rows, 7)
        for j, (pts, mid, title_, desc) in enumerate(vis):
            i = top + j
            y = by + 22 + j * 10
            got = mid in self.flags.get('milestones', [])
            if i == self.jsel:
                gfx.text(scr, ">", box.x + 4, y, (255, 220, 120))
            if got:
                self._check(scr, box.x + 12, y)
            gfx.text(scr, _fmt(pts), box.x + 22, y, (255, 220, 120) if got else (130, 140, 170))
            gfx.text(scr, title_, box.x + 70, y, (255, 255, 255) if got else (150, 155, 180))
        pts, mid, title_, desc = rows[self.jsel]
        for j, line in enumerate(gfx.wrap(desc, 39)[:2]):
            gfx.text(scr, line, box.x + 8, box.bottom - 32 + j * 10, (180, 200, 240))

    def _draw_leaders(self, scr, box, rows, y0):
        top3 = rows[:3]
        # the podium is drawn in 3D on the hi-res canvas
        self._podium = top3
        listed = rows[3:7]
        you = next((i for i, r in enumerate(rows) if r[3]), None)
        y = y0 + 76
        for j, (name, sc, kind, me) in enumerate(listed):
            col = (255, 230, 120) if me else (220, 225, 245)
            gfx.text(scr, f"{j + 4}.", box.x + 10, y + j * 9, (150, 160, 200))
            gfx.text(scr, name[:16], box.x + 28, y + j * 9, col)
            gfx.text(scr, _fmt(sc), box.right - 10 - gfx.text_width(_fmt(sc)), y + j * 9, col)
        if you is not None and you >= 7:
            name, sc, kind, me = rows[you]
            gfx.text(scr, f"{you + 1}.", box.x + 10, y + 37, (150, 160, 200))
            gfx.text(scr, name[:16], box.x + 28, y + 37, (255, 230, 120))
            gfx.text(scr, _fmt(sc), box.right - 10 - gfx.text_width(_fmt(sc)), y + 37, (255, 230, 120))
        gfx.text(scr, "Z: CHANGE NAME    *: A DEEP TIDE RUN", SCREEN_W // 2, box.bottom - 19, (130, 140, 180),
                 center=True)

    def draw_podium(self, hr):
        rows = getattr(self, '_podium', None)
        if not rows:
            return
        H_ = HI
        base_y = (HUD_H + 86) * H_
        slots = [(1, 128, 30), (0, 88, 20), (2, 168, 12)]          # (rank index, x, height)
        items = []
        for idx, x, h in slots:
            if idx >= len(rows):
                continue
            name, sc, kind, me = rows[idx]
            col = [(255, 210, 80), (210, 215, 230), (220, 150, 90)][idx]
            px0, w = x * H_, 34 * H_
            top = base_y - h * H_
            pygame.draw.rect(hr, cinema.mix(col, (0, 0, 0), 0.45), (px0 - w // 2, top, w, h * H_))
            pygame.draw.rect(hr, col, (px0 - w // 2, top, w, 4 * H_))
            num = hifi.text(str(idx + 1), 12 * H_, (255, 255, 255))
            hr.blit(num, num.get_rect(center=(px0, top + h * H_ / 2 + 2 * H_)))
            label = hifi.text(name[:12], 6 * H_, (255, 240, 200) if me else (230, 235, 250), shadow=False)
            hr.blit(label, label.get_rect(center=(px0, base_y + 4 * H_)))
            pts = hifi.text(_fmt(sc), 5 * H_, (255, 220, 120), shadow=False)
            hr.blit(pts, pts.get_rect(center=(px0, top - 2 * H_ - 26 * H_)))
            # the figure on top
            z = 400 * H_
            k = hifi.F / z
            fy = top - 12 * H_
            pos = ((px0 - hifi.W / 2) / k, (fy - hifi.H / 2) / k, z)
            items += self._figure(name, kind, me).items(pos, yaw=math.sin(self.t * 0.03 + idx) * 0.5, pitch=0.2, t=self.t,
                                                        size=10 * H_ / k)
        hifi.render(hr, items)

    def _figure(self, name, kind, me):
        cache = self.__dict__.setdefault('_figures', {})
        key = (name, kind, me, self.player.mood if me else None)
        m = cache.get(key)
        if m is None:
            look = folk.RIVAL_LOOK.get(name)
            if me or kind in ('you', 'run'):
                mood = self.player.mood if me else 'blue'
                m = hifi.Octo3D(gfx.OCTO_PAL[mood], hat=style.icon(self.player.hat) if me else None)
            elif kind == 'turtle':
                d = folk.NPCS.get(look, {})
                m = hifi.Turtle3D(shell=d.get('shell', (80, 150, 90)), skin=d.get('skin', (150, 210, 140)),
                                  beard=d.get('beard', False), specs=d.get('specs', False))
            elif look == 'kraken':
                m = hifi.Octo3D({'B': (150, 30, 50), 'P': (255, 200, 80), 'e': (255, 220, 60), 'c': (255, 90, 90)},
                                mad=True)
            else:
                m = hifi.Octo3D(gfx.OCTO_PAL['cit_' + look] if look and 'cit_' + look in gfx.OCTO_PAL
                                else gfx.OCTO_PAL['blue'])
            cache[key] = m
        return m

    def _draw_extras(self, scr, box, rows, y0):
        names = {'museum': ("3D MUSEUM", "SEE EVERY GUARDIAN YOU'VE BEATEN AS A 3D STATUE."),
                 'radio': ("OCTO RADIO", "LISTEN TO ANY TUNE IN THE GAME."),
                 'name': ("CHANGE YOUR NAME", "THE NAME THAT GOES ON THE LEADERBOARD.")}
        self.jsel = min(self.jsel, len(rows) - 1)
        for j, what in enumerate(rows):
            y = y0 + 8 + j * 16
            title, desc = names[what]
            ok = what == 'name' or self.unlocked(what)
            if j == self.jsel:
                gfx.text(scr, ">", box.x + 6, y, (255, 220, 120))
            gfx.text(scr, title, box.x + 16, y, (255, 255, 255) if ok else (140, 145, 170))
            if not ok:
                pts = score.MILESTONE[what][0]
                tag = f"LOCKED: {_fmt(pts)}"
                gfx.text(scr, tag, box.right - 8 - gfx.text_width(tag), y, (170, 130, 130))
        what = rows[self.jsel]
        for j, line in enumerate(gfx.wrap(names[what][1], 39)):
            gfx.text(scr, line, box.x + 8, y0 + 64 + j * 10, (190, 205, 240))
        gfx.text(scr, f"PLAYING AS {self.player_name()}", box.x + 8, y0 + 90, (150, 160, 200))
        gfx.text(scr, "Z: OPEN", box.x + 8, y0 + 102, (130, 140, 180))

    # ==================================================================
    # the 3D museum
    # ==================================================================
    def museum_exhibits(self):
        from entities import MINIBOSS_STYLES
        out = []
        for bid in self.flags.get('minis', []) + self.flags.get('tbosses', []):
            cfg = MINIBOSS_STYLES.get(bid)
            if not cfg:
                continue
            base = gfx.SPR[cfg['base']]
            img = base[0] if isinstance(base, list) else next(iter(base.values()))[0]
            if cfg.get('tint'):
                img = gfx.tint(img, cfg['tint'])
            where = "A TEMPLE GUARDIAN" if bid in self.flags.get('tbosses', []) else "A REGION GUARDIAN"
            out.append((cfg['name'], img, where))
        if self.flags.get('shark_dead'):
            out.append(("GRIMFIN", gfx.SPR['shark']['swim'][0], "GUARDIAN OF THE SUNKEN SHRINE"))
        if self.flags.get('murk_dead'):
            out.append(("MURK", gfx.SPR['murk']['swim'][0] if isinstance(gfx.SPR['murk'], dict) else gfx.SPR['murk'][0],
                        "QUEEN OF THE SUNKEN CITY"))
        return out

    def open_museum(self, back='play'):
        self.mus_i = 0
        self.mus_back = back
        self.mus_models = {}
        self.state = 'museum'
        sound.play('pause')

    def museum_key(self, k):
        ex = self.museum_exhibits()
        if ex and (k in LEFT or k in RIGHT):
            self.mus_i = (self.mus_i + (1 if k in RIGHT else -1)) % len(ex)
            sound.play('text')
        elif k in CLOSE or k in CONFIRM:
            self.state = self.mus_back
            sound.play('pause')

    def draw_museum(self, hr):
        H_ = HI
        if getattr(self, '_mus_bg', None) is None:
            self._mus_bg = hifi.gradient(hifi.W, hifi.H, [(0, (30, 22, 40)), (0.6, (60, 44, 70)), (1, (20, 14, 26))])
        hr.blit(self._mus_bg, (0, 0))
        cx = hifi.W / 2
        # spotlight
        cone = pygame.Surface((hifi.W, hifi.H))
        pygame.draw.polygon(cone, (60, 52, 34), [(cx - 20 * H_, 0), (cx + 20 * H_, 0), (cx + 70 * H_, 190 * H_),
                                                 (cx - 70 * H_, 190 * H_)])
        hr.blit(cone, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        hifi.add_glow(hr, (90, 80, 50), cx, 190 * H_, 70 * H_)
        ped = cinema._cylinder(80 * H_, 26 * H_, (200, 190, 210))
        hr.blit(ped, (cx - ped.get_width() / 2, 170 * H_))
        pygame.draw.ellipse(hr, (235, 228, 245), (cx - 40 * H_, 163 * H_, 80 * H_, 14 * H_))
        title = hifi.text3d("3D MUSEUM", 18 * H_, (255, 240, 190), (230, 170, 80), (110, 70, 30))
        hr.blit(title, (cx - title.get_width() / 2, 6 * H_))
        ex = self.museum_exhibits()
        if not ex:
            img = hifi.text("NO STATUES YET - BEAT A GUARDIAN!", 10 * H_, (230, 220, 240))
            hr.blit(img, img.get_rect(center=(cx, 120 * H_)))
            return
        self.mus_i %= len(ex)
        name, sprite, where = ex[self.mus_i]
        m = self.mus_models.get(name)
        if m is None:
            m = self.mus_models[name] = hifi.Beads3D(sprite)
        z = 520 * H_
        k = hifi.F / z
        items = m.items(((cx - hifi.W / 2) / k, (118 * H_ - hifi.H / 2) / k, z), yaw=self.t * 0.02,
                        pitch=0.12 + math.sin(self.t * 0.01) * 0.06, scale=5.2 * H_ / k)
        hifi.render(hr, items)
        n = hifi.text(name, 15 * H_, (255, 230, 140))
        hr.blit(n, n.get_rect(center=(cx, 206 * H_)))
        w = hifi.text(f"{where}   {self.mus_i + 1} / {len(ex)}", 8 * H_, (220, 210, 235), shadow=False)
        hr.blit(w, w.get_rect(center=(cx, 220 * H_)))
        if len(ex) > 1:
            for sx, ch in ((24, "<"), (232, ">")):
                a = hifi.text(ch, 20 * H_, (255, 230, 160))
                hr.blit(a, a.get_rect(center=(sx * H_, 118 * H_)))

    # ==================================================================
    # Octo Radio
    # ==================================================================
    def open_radio(self):
        self.radio_i = 0
        self.radio_on = None
        self.state = 'radio'
        sound.play('pause')

    def radio_key(self, k):
        if k in UP:
            self.radio_i = (self.radio_i - 1) % len(RADIO)
            sound.play('text')
        elif k in DOWN:
            self.radio_i = (self.radio_i + 1) % len(RADIO)
            sound.play('text')
        elif k in ACTION or k in CONFIRM:
            track = RADIO[self.radio_i][0]
            self.radio_on = track
            sound.music(track, loops=0 if track == 'victory' else -1)
        elif k in CLOSE:
            self.state = 'journal'
            sound.music(self.area_music())

    def draw_radio(self, scr):
        box = pygame.Rect(8, HUD_H + 3, SCREEN_W - 16, PLAY_H - 6)
        self.draw_box(scr, box)
        gfx.text(scr, "OCTO RADIO", SCREEN_W // 2, box.y + 5, (255, 220, 120), center=True)
        show = 12
        top = max(0, min(self.radio_i - show // 2, len(RADIO) - show))
        for j, (track, name) in enumerate(RADIO[top:top + show]):
            i = top + j
            y = box.y + 18 + j * 10
            on = i == self.radio_i
            if on:
                gfx.text(scr, ">", box.x + 6, y, (255, 220, 120))
            col = (120, 255, 170) if track == self.radio_on else (255, 255, 255) if on else (170, 180, 210)
            gfx.text(scr, f"{i + 1:02d} {name}", box.x + 16, y, col)
            if track == self.radio_on:
                for b in range(4):
                    hgt = 2 + int(abs(math.sin(self.t * 0.2 + b)) * 5)
                    pygame.draw.rect(scr, (120, 255, 170), (box.right - 30 + b * 4, y + 7 - hgt, 3, hgt))
        gfx.text(scr, "Z: PLAY   ESC: BACK", SCREEN_W // 2, box.bottom - 10, (140, 150, 190), center=True)

    # ==================================================================
    # HUD
    # ==================================================================
    def draw_score_hud(self, scr):
        sc = self.score()
        shown = getattr(self, '_hud_score', sc)
        if shown < sc:                                 # roll the counter up
            shown = min(sc, shown + max(1, (sc - shown) // 6))
        else:
            shown = sc
        self._hud_score = shown
        x, y = 4, 38
        pts = [(x + 3 + math.cos(a) * r, y + 3 + math.sin(a) * r)
               for i, a in enumerate(-math.pi / 2 + j * math.pi / 5 for j in range(10))
               for r in [(3.4 if i % 2 == 0 else 1.5)]]
        pygame.draw.polygon(scr, (255, 210, 70), pts)
        gfx.text(scr, f"{shown:06d}" if shown < 1000000 else str(shown), x + 9, y, (255, 230, 140))
        nxt, _ = score.next_milestone(sc)
        prev = max([p_ for p_, *_ in score.MILESTONES if p_ <= sc], default=0)
        w = 48
        pygame.draw.rect(scr, (40, 40, 70), (x, y + 10, w, 2))
        k = 1.0 if not nxt else (sc - prev) / max(1, nxt - prev)
        pygame.draw.rect(scr, (255, 200, 70), (x, y + 10, int(w * k), 2))
