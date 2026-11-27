"""Octo's own house in Octo City.

It stands by the city gate: a round blue dome with Octo's face (its door is his mouth). Inside,
one cosy room, everything in 3D:
  bed          sleep till morning: every heart back (Pebble's too) and the game is saved
  diary        the story so far, and the game is saved
  trophy shelf a cup for each trial, a bell for each tide bell, a crown for each guardian
  hat stand    try on your hats
  fish tank    Bloop and Blip, who like fish flakes
  tea table    a cup of kelp tea: two hearts back
  basket       Pebble naps here: wake him up to play as player two (or put him back to bed)
  lamp, plant  a jellyfish lamp to switch on and off, and a sea anemone that waves
and outside a mailbox with thank-you letters (and a few pearls) from everyone you've helped.
Once you've been home, it's a warp point (press T).

Home is mixed into Game.
"""
import math

import pygame

import home3d
import hifi
import props3d
import sound
import style
import voxel
import world
from entities import Entity
from settings import HI, TILE

USE = {'bed', 'shelf', 'desk', 'tank', 'table', 'hats', 'lamp', 'basket', 'plant', 'mail'}
SLEEP_LEN = 200                  # frames: dusk, the night, then morning
SLEEP_MID = 100                  # when the hearts come back and the game is saved

LETTERS = {
    # quest (or 'welcome') -> who from, the letter, the pearls in the envelope
    'welcome': ("MAYOR OCTAVIA", ["DEAR OCTO, WELCOME HOME! THE WHOLE CITY CHIPPED IN TO BUILD YOU THIS HOUSE - "
                                  "ROUND AND BLUE, JUST LIKE YOU.",
                                  "SLEEP IN YOUR BED TO REST AND SAVE, AND WRITE IN YOUR DIARY ANY TIME. "
                                  "LOVE, MAYOR OCTAVIA. P.S. A LITTLE HOUSE-WARMING GIFT!"], 20),
    'hatchlings': ("MAYOR OCTAVIA", ["DEAR OCTO, THE HATCHLINGS DREW YOU A PICTURE. IT'S YOU, WITH NINE ARMS. "
                                     "THEY'RE STILL LEARNING TO COUNT.",
                                     "THANK YOU FOR BRINGING THEM HOME. P.S. SOME PEARLS FOR BRAVERY."], 20),
    'peppers': ("CHEF BARNABY", ["DEAR OCTO, MY FIRE-KELP STEW WON FIRST PRIZE AT THE COOK-OFF! THE JUDGES' "
                                 "EYEBROWS ARE STILL SMOKING.",
                                 "COULDN'T HAVE DONE IT WITHOUT YOUR PEPPERS. P.S. A FEW PEARLS FOR YOUR TROUBLE!"], 15),
    'seeds': ("CORALINE", ["DEAR OCTO, YOUR CORAL SEEDS SPROUTED! THE PARK GLOWS PINK EVERY EVENING NOW.",
                           "COME AND SEE IT SOMETIME. P.S. I FOUND THESE PEARLS WHILE I WAS DIGGING."], 15),
    'specimens': ("PROFESSOR OCTAGON", ["DEAR OCTO, MY BOOK ON MURK'S GUARDIANS IS FINISHED, AND YOU'RE IN CHAPTER ONE.",
                                        "MY EDITOR SAYS IT'S A PAGE-TURNER. P.S. YOUR SHARE OF THE ROYALTIES."], 20),
    'parcel': ("CAPTAIN PIPS", ["AHOY, OCTO! THAT PARCEL GOT THROUGH DRY AS A BONE. WELL, AS DRY AS ANYTHING GETS "
                                "DOWN HERE.",
                                "BEST DELIVERY SQUID I EVER HAD - EVEN IF YOU'RE AN OCTOPUS. P.S. PEARLS, MATEY!"], 15),
    'marbles': ("LITTLE OLLIE", ["DEAR OCTO, I HAVE ALL MY MARBLES BACK! I KEEP THEM IN A SOCK NOW SO THEY CAN'T "
                                 "ROLL AWAY.",
                                 "YOU'RE MY HERO!!! P.S. HERE IS ALL MY POCKET MONEY."], 10),
    'dance': ("ZIGGY", ["YO, OCTO! EVERYONE'S STILL TALKING ABOUT YOUR MOVES.",
                        "YOU'VE GOT EIGHT ARMS AND YOU USED EVERY ONE OF THEM. LEGEND. P.S. SOMETHING FROM THE TIP JAR!"],
              15),
    'chain': ("GRANNY OCTA", ["DEAR OCTO, I'M KNITTING YOU A SCARF. IT'S EIGHT METRES LONG - ONE FOR EACH ARM.",
                              "THANK YOU FOR ALL THAT RUNNING ABOUT FOR AN OLD LADY. P.S. PEARLS FOR SWEETS."], 20),
    'nestwatch': ("ELDER TORTUGA", ["DEAR OCTO, THE EGGS HAVE HATCHED: TWELVE LITTLE TURTLES, AND EVERY ONE OF THEM "
                                    "WANTS TO BE YOU WHEN THEY GROW UP.",
                                    "TURTLE TOWN WON'T FORGET YOU. P.S. PEARLS FROM THE TOWN CHEST."], 20),
    'shells': ("SHELDON", ["DEAR OCTO, MY SHELL COLLECTION IS THE TALK OF THE BEACH! I GAVE EVERY SHELL A NAME. "
                           "ONE OF THEM IS CALLED OCTO.",
                           "THANKS, PAL. P.S. PEARLS - I FOUND THEM IN A SHELL, OF COURSE."], 15),
    'sister': ("TINY TIM", ["DEAR OCTO, TILLY SAYS SORRY FOR HIDING. I SAID SORRY FOR CRYING. NOW WE ONLY PLAY "
                            "HIDE-AND-SEEK IN THE GARDEN.",
                            "THANK YOU FOR FINDING HER! P.S. PEARLS FROM BOTH OF US."], 10),
    'postcards': ("SPEEDY", ["DEAR OCTO, ALL YOUR POSTCARDS ARE ON MY WALL. IT'S LIKE I WENT EVERYWHERE MYSELF - "
                             "ONLY FASTER.",
                             "P.S. SOME PEARLS FOR THE STAMPS!"], 15),
    'quiet': ("GRUMBLE", ["OCTO. IT IS QUIET NOW. I SLEPT FOR THREE DAYS. IT WAS WONDERFUL.",
                          "DON'T VISIT. ...ALL RIGHT, VISIT ONCE. P.S. PEARLS. DON'T MAKE A FUSS ABOUT IT."], 20),
    'crate': ("CAPTAIN SHELLBY", ["DEAR OCTO, THE COCONUTS ARRIVED SAFE AND THE WHOLE PIER HAD A PARTY.",
                                  "THERE WAS DANCING. THERE WAS SHELL-CRACKING. THERE WAS A SMALL FIRE. P.S. PEARLS!"],
              15),
    'tourist': ("DR. CARAPACE", ["DEAR OCTO, I'VE STUDIED YOUR TRIAL NOTES. I CONCLUDE THAT YOU ARE VERY BRAVE, OR "
                                 "VERY SILLY.",
                                 "PROBABLY BOTH: THE BEST EXPLORERS ARE. P.S. SOME PEARLS, FOR SCIENCE."], 15),
    'thunder': ("COCO", ["DEAR OCTO, I WROTE A SONG ABOUT YOU! IT'S CALLED THE INKY STORM AND IT HAS ELEVEN VERSES.",
                         "I'LL SING THEM ALL NEXT TIME YOU VISIT! P.S. PEARLS FROM THE CONCERT."], 15),
}
TANK_TALK = ["BLOOP AND BLIP, YOUR PET FISH, BLOW YOU A BUBBLE EACH.",
             "BLOOP IS CHASING BLIP. BLIP IS CHASING BLOOP. NOBODY KNOWS WHO STARTED IT."]


class HomeThing(Entity):
    """Something in (or by) the house you can walk up to and use. It isn't drawn: its 3D model is."""

    def __init__(self, what, x0, y0, x1, y1):
        super().__init__(x0 * TILE, y0 * TILE)
        self.what = what
        self.hb = (0, 0, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE)
        self.name = what.upper()

    def update(self, game):
        pass

    def draw(self, surf, ox=0, oy=0):
        pass


class Home:
    # ==================================================================
    # setting up
    # ==================================================================
    def home_setup(self):
        self.sleep_t = 0
        self.tea_cd = 0
        self.fed_t = 0
        self.home_things = {}
        for cid in ('home', 'octo'):
            for what, (x0, y0, x1, y1) in world.CITIES[cid].get('things', {}).items():
                if what in USE:
                    thing = HomeThing(what, x0, y0, x1, y1)
                    self.home_things[what] = thing
                    self.npcs.append(thing)

    def at_home(self):
        p = self.player
        return p is not None and world.city_at(p.rect.centerx // TILE, p.rect.centery // TILE) == 'home'

    def came_home(self):
        """Called when Octo walks in through his front door."""
        fl = self.flags
        if not fl.get('home_seen'):
            fl['home_seen'] = True
            sound.play('item')
            self.say(["HOME SWEET HOME!",
                      "THE TOWNSFOLK BUILT THIS HOUSE JUST FOR YOU, OCTO. LOOK AROUND: PRESS Z NEXT TO THINGS TO USE THEM.",
                      "THE BED LETS YOU REST AND SAVE, PEBBLE NAPS IN HIS BASKET, AND YOUR HOUSE IS NOW A WARP POINT "
                      "(PRESS T)."])
        else:
            self.toast = ("HOME SWEET HOME!", 90)

    # ==================================================================
    # using things
    # ==================================================================
    def use_home(self, what):
        p = self.player
        fl = self.flags
        if what == 'bed':
            self.start_sleep()
        elif what == 'desk':
            self.say(self.diary_pages(), then=self._diary_saved)
        elif what == 'shelf':
            self.say(self.trophy_pages())
        elif what == 'hats':
            if sum(1 for h in style.HATS if h != 'none' and style.unlocked(self, h)) == 0:
                self.say(["AN EMPTY HAT STAND. FIND SOME HATS AND HANG THEM HERE!"])
            else:
                self.open_wardrobe()
        elif what == 'tank':
            if self.fed_t:
                self.say([TANK_TALK[self.t % len(TANK_TALK)]])
            else:
                self.fed_t = 300
                sound.play('bubble')
                self.say(["YOU SPRINKLE IN SOME FISH FLAKES. BLOOP AND BLIP GOBBLE THEM UP!"])
        elif what == 'table':
            hurt = p.hp < p.max_hp or (self.snail is not None and self.snail.hp < self.snail.max_hp)
            if not hurt:
                self.say(["A POT OF KELP TEA, STILL WARM. YOU'RE FEELING FINE, SO YOU SAVE IT FOR LATER."])
            elif self.tea_cd:
                self.say(["THE TEAPOT IS EMPTY. IT'LL BE BREWED AGAIN IN A LITTLE WHILE."])
            else:
                p.hp = min(p.max_hp, p.hp + 4)
                if self.snail is not None:
                    self.snail.hp = min(self.snail.max_hp, self.snail.hp + 4)
                self.tea_cd = 60 * 60
                sound.play('heart')
                self.say(["A WARM CUP OF KELP TEA. SLURP!  (+2 HEARTS)"])
        elif what == 'basket':
            self.use_basket()
        elif what == 'lamp':
            fl['lamp_off'] = not fl.get('lamp_off')
            sound.play('tick')
            self.toast = ("LAMP OFF" if fl['lamp_off'] else "LAMP ON", 50)
        elif what == 'plant':
            self.say(["YOUR SEA ANEMONE WAVES ALL ITS LITTLE ARMS AT YOU. YOU WAVE BACK."])
        elif what == 'mail':
            self.read_mail()

    def use_basket(self):
        if self.snail is not None:
            if self.snail.resting:
                self.say(["PEBBLE IS ALREADY HAVING A NAP IN HIS SHELL."])
                return
            self.coop_leave()
            self.say(["PEBBLE CURLS UP IN HIS BASKET FOR A NAP. ZZZ...  (PLAYER TWO HAS LEFT)"])
            return
        if self.touch.active and not getattr(self, 'joys', None):
            self.say(["PEBBLE IS FAST ASLEEP IN HIS BASKET, SNORING VERY QUIETLY.",
                      "(TO PLAY AS PEBBLE, PLAYER TWO NEEDS A KEYBOARD OR A GAMEPAD.)"])
            return
        self.coop_join(quiet=True)
        self.say(["PEBBLE WAKES UP, STRETCHES HIS EYE-STALKS AND SLIDES OUT OF HIS BASKET!",
                  "PLAYER TWO: ARROW KEYS TO MOVE, RIGHT CTRL TO SPIT SLIME, / TO SPIN IN HIS SHELL."])

    # ---- the diary and the trophies -------------------------------------
    def diary_pages(self):
        import beasts
        fl = self.flags
        day = fl.get('nights', 0) + 1
        trials, bells = len(self.trials_done), len(self.bells())
        done = sum(1 for st in self.quests().values() if st['s'] == 'done')
        seen = len(fl.get('beasts_seen', []))
        pages = [f"OCTO'S DIARY - DAY {day}.",
                 f"DEAR DIARY, SO FAR I'VE FINISHED {trials} OF THE {len(world.TRIALS)} TRIALS AND RUNG {bells} OF THE "
                 f"{world.BELLS_NEEDED} TIDE BELLS.",
                 f"I'VE MET {seen} OF THE {len(beasts.entries())} CREATURES IN MY BESTIARY AND HELPED {done} OF "
                 f"MY NEIGHBOURS. MY SCORE IS {self.score():,}."]
        if self.snail is not None:
            pages.append("PEBBLE CAME ALONG TODAY. HE ATE A LEAF AND TRIED TO EAT A CRAB.")
        pages.append("TOMORROW: " + self.next_goal())
        return pages

    def _diary_saved(self):
        self.save_game()
        self.toast = ("DIARY WRITTEN. GAME SAVED!", 110)

    def trophies(self):
        fl = self.flags
        return {'cups': len(self.trials_done), 'bells': len(self.bells()), 'crowns': len(fl.get('minis', [])),
                'tooth': bool(fl.get('shark_dead')), 'pearl': bool(fl.get('murk_dead'))}

    def trophy_pages(self):
        t = self.trophies()
        if not (t['cups'] or t['bells'] or t['crowns']):
            return ["YOUR TROPHY SHELF. IT'S EMPTY FOR NOW - BUT NOT FOR LONG!",
                    "FINISH TRIALS, RING TIDE BELLS AND BEAT GUARDIANS, AND YOUR TROPHIES WILL APPEAR HERE."]
        pages = ["YOUR TROPHY SHELF:",
                 f"TRIAL CUPS: {t['cups']} OF {len(world.TRIALS)}.  TIDE BELLS: {t['bells']} OF "
                 f"{world.BELLS_NEEDED}.  GUARDIAN CROWNS: {t['crowns']} OF {len(world.MINIBOSSES)}."]
        extra = []
        if t['tooth']:
            extra.append("GRIMFIN'S TOOTH")
        if t['pearl']:
            extra.append("THE GOLDEN PEARL")
        if extra:
            pages.append("AND IN PRIDE OF PLACE: " + " AND ".join(extra) + "!")
        return pages

    # ---- the mailbox ---------------------------------------------------
    def letters(self):
        """Every letter that has come so far: the welcome, and a thank-you for each finished quest."""
        out = ['welcome']
        for qid, st in self.quests().items():
            if st['s'] == 'done' and qid in LETTERS:
                out.append(qid)
        return out

    def unread_letters(self):
        read = self.flags.get('letters_read', [])
        return [k for k in self.letters() if k not in read]

    def read_mail(self):
        new = self.unread_letters()
        if not new:
            n = len(self.letters())
            self.say([f"NO NEW MAIL TODAY. ({n} LETTER{'S' if n != 1 else ''} SAVED IN YOUR DESK.)",
                      "HELP THE TOWNSFOLK WITH THEIR SIDE QUESTS AND THEY'LL WRITE TO YOU."])
            return
        read = self.flags.setdefault('letters_read', [])
        pages = [f"YOU'VE GOT MAIL! {len(new)} NEW LETTER{'S' if len(new) > 1 else ''}."]
        pearls = 0
        for k in new:
            who, text, gift = LETTERS[k]
            pages.append("FROM " + who + ":")
            pages += text
            pearls += gift
            read.append(k)
        pages.append(f"THERE WERE {pearls} PEARLS IN THE ENVELOPES!")
        self.player.pearls += pearls
        sound.play('item')
        self.say(pages)

    # ==================================================================
    # a night's sleep
    # ==================================================================
    def start_sleep(self):
        p = self.player
        self.sleep_t = 0
        self.sleep_back = (p.x, p.y)
        self.state = 'sleep'
        sound.play('pause')
        sound.music(None)

    def update_sleep(self):
        self.sleep_t += 1
        t = self.sleep_t
        if t == SLEEP_MID:
            p = self.player
            p.hp = p.max_hp
            if self.snail is not None:
                self.snail.hp = self.snail.max_hp
                self.snail.resting = 0
            self.flags['nights'] = self.flags.get('nights', 0) + 1
            self.tea_cd = 0
        if t >= SLEEP_LEN:
            self.end_sleep()

    def sleep_key(self, k):
        if self.sleep_t < SLEEP_MID:
            return
        self.sleep_t = max(self.sleep_t, SLEEP_LEN - 30)

    def end_sleep(self):
        p = self.player
        bx0, by0, bx1, by1 = world.CITIES['home']['things']['bed']
        p.x, p.y = (bx1 + 1) * TILE, (by0 + 1) * TILE          # hop out on the side of the bed
        p.facing = 'down'
        self.state = 'play'
        sound.music(self.area_music())
        self.save_game()
        sound.play('heart')
        self.say(["GOOD MORNING, OCTO! YOU FEEL ALL REFRESHED.", "EVERY HEART IS BACK, AND YOUR GAME IS SAVED."])

    def sleep_dark(self):
        """How dark the room is while Octo sleeps (0..1)."""
        t = self.sleep_t
        if t < 40:
            return t / 40
        if t > SLEEP_LEN - 40:
            return max(0.0, (SLEEP_LEN - t) / 40)
        return 1.0

    def draw_sleep(self, ui, hires):
        k = self.sleep_dark()
        if k > 0:
            ui.blit(self.tint_layer((6, 10, 40), int(170 * k)), (0, 56))
        if 30 < self.sleep_t < SLEEP_LEN - 30:                 # a little night-time caption
            img = hifi.text("Z Z Z . . .", 9 * HI, (200, 210, 255), outline=(10, 12, 40), shadow=False)
            hires.blit(img, img.get_rect(center=(128 * HI, (56 + 160) * HI)))

    # ==================================================================
    # drawing: the moving bits of the house's models
    # ==================================================================
    def draw_home_prop(self, hr, prop, shake):
        k = prop.kind
        key = prop.key
        if k == 'home':
            key = 'o_home_blink' if self.t % 260 < 9 or 120 < self.t % 260 < 127 else 'o_home'
        elif k == 'mail':
            if self.t % 30 == 0 or not hasattr(self, '_unread'):
                self._unread = len(self.unread_letters())
            key = 'o_mail_up' if self._unread else 'o_mail'
        img, (ax, ay) = props3d.image(key)
        x, y = self._hr(prop.x, prop.y, shake)
        hr.blit(img, (x - ax, y - ay))
        P = lambda px, py, pz: self._hr(prop.x + px - props3d.KX * pz, prop.y + py - props3d.KZ * pz, shake)  # noqa
        if k == 'home':
            for i in range(3):                                   # bubbles from the chimney
                f = ((self.t + i * 40) % 120) / 120
                bx, by = P(53 + math.sin(f * 9 + i) * 2.5, 22, 58 + f * 30)
                r = max(1, int((1.2 + f * 1.6) * HI))
                pygame.draw.circle(hr, (220, 240, 255), (int(bx), int(by)), r, max(1, HI // 2))
        elif k == 'wall':
            self._draw_portholes(hr, P)
        elif k == 'bed' and self.state == 'sleep':
            self._draw_sleeper(hr, prop, P, shake)
        elif k == 'shelf':
            self._draw_trophies(hr, P)
        elif k == 'tank':
            self._draw_fish(hr, P)
        elif k == 'tea':
            for i, (cx, cy, cz) in enumerate(((30, 18.5, 16), (17, 19.5, 16), (28.6, 14.5, 18))):
                for j in range(2):
                    f = ((self.t * 0.6 + i * 23 + j * 30) % 60) / 60
                    sx, sy = P(cx + math.sin(f * 6 + i + j) * 1.5, cy, cz + f * 10)
                    a = int(150 * (1 - f))
                    if a > 10:
                        dot = pygame.Surface((2 * HI, 2 * HI), pygame.SRCALPHA)
                        pygame.draw.circle(dot, (255, 255, 255, a), (HI, HI), HI)
                        hr.blit(dot, (sx - HI, sy - HI))
        elif k == 'basket' and self.snail is None:
            self._draw_pet(hr, P)
        elif k == 'hats':
            self._draw_hats(hr, P)
        elif k == 'lamp' and not self.flags.get('lamp_off'):
            gx, gy = P(8, 10, 26)
            r = int((15 + 1.5 * math.sin(self.t * 0.05)) * HI)
            glow = self.__dict__.setdefault('_lamp_glow', {})
            g = glow.get(r)
            if g is None:
                g = glow[r] = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                for j in range(8, 0, -1):
                    pygame.draw.circle(g, (255, 190, 235, 10), (r, r), int(r * j / 8))
            hr.blit(g, (gx - r, gy - r))

    def _draw_portholes(self, hr, P):
        """Now and then a fish swims past a porthole."""
        for i, (x, z, r) in enumerate(home3d.PORTHOLES):
            f = ((self.t + i * 170) % 340) / 340
            if f > 0.35:
                continue
            dx = (f / 0.35 * 2 - 1) * (r - 1.5) * (1 if i % 2 else -1)
            cx, cy = P(x + dx, 32.7, z + math.sin(f * 30) * 0.6 - 0.5)
            w, h = 3.0 * HI, 1.6 * HI
            col = (20, 50, 100)
            pygame.draw.ellipse(hr, col, (cx - w / 2, cy - h / 2, w, h))
            tail = -1 if i % 2 else 1
            pygame.draw.polygon(hr, col, [(cx - tail * w / 2, cy), (cx - tail * (w / 2 + 1.3 * HI), cy - 1.0 * HI),
                                          (cx - tail * (w / 2 + 1.3 * HI), cy + 1.0 * HI)])

    def _draw_sleeper(self, hr, prop, P, shake):
        """Octo tucked up in bed: his head on the pillow, the covers over the rest of him."""
        img, (ax, ay) = voxel.octo_image(self.player.mood, 0, 0.12, HI * 0.9, 0.75, None)
        fx, fy = P(16, 21, 13)
        fy += math.sin(self.t * 0.05) * HI * 0.4                     # breathing
        hr.blit(img, (fx - ax, fy - ay))
        cov, (cx, cy) = props3d.image('h_bed_covers')
        x, y = self._hr(prop.x, prop.y, shake)
        hr.blit(cov, (x - cx, y - cy))
        if 20 < self.sleep_t < SLEEP_LEN - 20:
            zx, zy = P(22, 8, 30)
            for i in range(3):
                f = ((self.sleep_t + i * 20) % 60) / 60
                size = (4 + i * 1.5) * f + 2
                img = hifi.text("Z", int(size * HI), (230, 236, 255), outline=(20, 24, 60), shadow=False)
                hr.blit(img, (zx + f * 8 * HI, zy - f * 18 * HI))

    def _icon(self, key):
        return props3d.image(key)

    def _draw_trophies(self, hr, P):
        t = self.trophies()
        rows = [
            (home3d.SHELVES[0], ['t_crown'] * min(8, t['crowns'])),
            (home3d.SHELVES[1], ['t_cup' if i % 3 != 2 else 't_cup_silver' for i in range(min(8, t['cups']))]),
            (home3d.SHELVES[2], (['t_tooth'] if t['tooth'] else []) + ['t_bell'] * min(7, t['bells']) +
             (['t_pearl'] if t['pearl'] else [])),
        ]
        for z, items in rows:
            n = len(items)
            if not n:
                continue
            step = min(7.0, 54.0 / max(1, n))
            x0 = 32 - step * (n - 1) / 2
            for i, key in enumerate(items):
                img, (ax, ay) = self._icon(key)
                sx, sy = P(x0 + i * step, 8.5, z)
                hr.blit(img, (sx - ax, sy - ay))
                if key in ('t_cup', 't_crown', 't_pearl') and (self.t // 6 + i * 7) % 50 == 0:
                    pygame.draw.circle(hr, (255, 255, 230), (int(sx), int(sy - 5 * HI)), max(1, HI // 2 + 1))

    def _draw_fish(self, hr, P):
        x0, x1, z0, z1 = home3d.TANK
        fast = 2.2 if self.fed_t else 1.0
        if self.fed_t:
            self.fed_t -= 1
        for i, (col, fin) in enumerate((((250, 140, 50), (255, 220, 120)), ((250, 230, 80), (255, 255, 200)))):
            ph = self.t * 0.012 * fast + i * 2.1
            u = (math.sin(ph) + 1) / 2
            fx = x0 + 3 + u * (x1 - x0 - 6)
            fz = (z1 - 3 if self.fed_t else (z0 + z1) / 2 + math.sin(ph * 2.3 + i) * (z1 - z0) / 3)
            facing = 1 if math.cos(ph) > 0 else -1
            cx, cy = P(fx, 14.4, fz)
            w, h = 4.0 * HI, 2.4 * HI
            pygame.draw.ellipse(hr, col, (cx - w / 2, cy - h / 2, w, h))
            pygame.draw.polygon(hr, fin, [(cx - facing * w / 2, cy), (cx - facing * (w / 2 + 1.6 * HI), cy - 1.2 * HI),
                                          (cx - facing * (w / 2 + 1.6 * HI), cy + 1.2 * HI)])
            pygame.draw.circle(hr, (20, 20, 40), (int(cx + facing * w * 0.25), int(cy - h * 0.1)), max(1, HI // 2))
        for i in range(3):                                       # bubbles
            f = ((self.t + i * 37) % 110) / 110
            bx, by = P(10 + i * 13 + math.sin(f * 8 + i) * 1.5, 14.4, z0 - 1 + f * (z1 - z0 + 3))
            pygame.draw.circle(hr, (200, 240, 255), (int(bx), int(by)), max(1, int(HI * 0.7)), max(1, HI // 2))

    def _draw_pet(self, hr, P):
        """Pebble asleep in his basket (when he isn't out playing)."""
        import coop
        model = voxel.sprite_model(coop.frames()['right'][0], depth=4.0)
        img, (ax, ay) = voxel.cached(('pet_asleep',), model, HI * 0.8, -0.35, 0.65, None, False, coop.INK)
        sx, sy = P(16, 9.5, 4.2)
        sy += math.sin(self.t * 0.04) * HI * 0.4
        hr.blit(img, (sx - ax, sy - ay))
        zx, zy = P(23, 8, 16)
        f = (self.t % 90) / 90
        z = hifi.text("Z", int((5 + f * 4) * HI), (230, 236, 255), outline=(20, 24, 60), shadow=False)
        hr.blit(z, (zx + f * 5 * HI, zy - f * 12 * HI))

    def _draw_hats(self, hr, P):
        """Up to three of Octo's hats (not the one he's wearing) hang on the stand."""
        if self.t % 60 == 0 or not hasattr(self, '_stand_hats'):
            wearing = self.player.hat
            self._stand_hats = [h for h in style.HATS if h not in ('none', wearing) and style.unlocked(self, h)][:3]
        for (side, z), hat in zip(home3d.HOOKS, self._stand_hats):
            model = voxel.sprite_model(style._hat(hat), depth=2.5, key=('hatmodel', hat))
            img, (ax, ay) = voxel.cached(('stand_hat', hat), model, HI * 0.62, 0.3 * side, 0.6, None, False, (20, 20, 30))
            sx, sy = P(8 + side * 4.6, 10.2, z - 3.5)
            hr.blit(img, (sx - ax, sy - ay))

    # ==================================================================
    # ticking along (every frame of play)
    # ==================================================================
    def home_tick(self):
        if self.tea_cd:
            self.tea_cd -= 1
