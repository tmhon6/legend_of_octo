"""Who lives in the towns: townsfolk, their shops, their side quests, and the leaderboard rivals.

Pure data -- the game logic for talking, trading and quests is in town.py.
"""
import gfx

# ---- octopus townsfolk colours (the game's palette keys: see gfx.OCTO_PAL) --------------------
OCTO_COLOURS = {
    # id: body, light, dark, tentacle tips, blush, pupils
    'octavia': ((150, 90, 210), (210, 170, 250), (100, 50, 160), (250, 200, 90), (255, 140, 200), (20, 10, 40)),
    'inky': ((40, 44, 96), (90, 100, 170), (20, 22, 60), (90, 220, 255), (200, 120, 200), (230, 240, 255)),
    'tenta': ((240, 120, 180), (255, 200, 230), (190, 70, 130), (255, 240, 120), (255, 90, 140), (40, 0, 30)),
    'bubbles': ((230, 190, 60), (255, 240, 150), (180, 130, 20), (255, 255, 230), (255, 150, 110), (40, 20, 0)),
    'barnaby': ((250, 140, 60), (255, 200, 140), (200, 90, 30), (255, 240, 200), (255, 100, 90), (40, 10, 0)),
    'octagon': ((90, 170, 120), (170, 230, 190), (50, 120, 80), (240, 240, 170), (240, 150, 150), (10, 30, 20)),
    'coraline': ((240, 110, 100), (255, 190, 180), (190, 60, 60), (255, 230, 120), (255, 160, 200), (50, 10, 10)),
    'pips': ((60, 90, 170), (130, 160, 230), (30, 50, 120), (240, 240, 255), (240, 140, 170), (10, 10, 30)),
    'ollie': ((250, 210, 80), (255, 245, 170), (210, 160, 40), (255, 150, 90), (255, 140, 120), (30, 20, 0)),
    'granny': ((190, 170, 210), (235, 225, 245), (140, 120, 170), (255, 220, 240), (255, 170, 200), (30, 20, 40)),
    'ziggy': ((60, 200, 190), (170, 250, 240), (30, 140, 140), (255, 90, 200), (255, 140, 220), (0, 30, 30)),
    'tally': ((230, 232, 244), (255, 255, 255), (170, 176, 200), (255, 210, 80), (255, 170, 190), (20, 20, 60)),
    'hatch': ((255, 170, 200), (255, 220, 235), (220, 120, 160), (255, 240, 250), (255, 120, 170), (40, 0, 20)),
}
for _id, (_b, _h, _d, _p, _c, _e) in OCTO_COLOURS.items():
    gfx.OCTO_PAL['cit_' + _id] = {'k': tuple(max(0, v - 90) for v in _d), 'B': _b, 'H': _h, 'D': _d, 'P': _p,
                                  'e': _e, 'w': (255, 255, 255), 'c': _c}

# ---- everyone in town ----------------------------------------------------------------------
# kind: 'octo' or 'turtle'; shop: which stall's wares they sell; quests: what they ask, in order
NPCS = {
    # Octo City
    'octavia': dict(name="MAYOR OCTAVIA", town='octo', kind='octo', hat='crown', quests=['hatchlings'], lines=[
        "WELCOME TO OCTO CITY, DEAR! EVERY OCTOPUS IN THE SEA IS WELCOME HERE - EVEN REVERSIBLE ONES.",
        "THE SCOREBOARD BY THE FOUNTAIN LISTS THE GREATEST ADVENTURERS OF THE DEEP. TALLY KEEPS COUNT.",
        "OUR SISTER TOWN, TURTLE TOWN, SITS UP ON SUNNY BEACH. THE TURTLES ARE SLOW, BUT OH, ARE THEY KIND."]),
    'inky': dict(name="INKY", town='octo', kind='octo', hat='beanie', shop='ink', lines=[
        "INK IS MY LIFE! WANT YOUR JET TO PUFF IN STYLE? PICK A COLOUR IN THE WARDROBE (PRESS H)."]),
    'tenta': dict(name="MADAME TENTA", town='octo', kind='octo', hat='bow', shop='octohats', lines=[
        "DARLING! A HAT IS THE EIGHTH TENTACLE OF FASHION. WEAR THEM IN THE WARDROBE (PRESS H)."]),
    'bubbles': dict(name="BANKER BUBBLES", town='octo', kind='octo', hat='tophat', shop='bank', lines=[
        "PEARLS IN, PEARLS OUT! THE OCTO CITY BANK SWAPS PEARLS, SPIRIT PEARLS AND BOMBS."]),
    'barnaby': dict(name="CHEF BARNABY", town='octo', kind='octo', hat='chef', shop='food', quests=['peppers'], lines=[
        "A WARM BOWL OF SEAWEED SOUP PUTS EVERY TENTACLE BACK IN ORDER!"]),
    'octagon': dict(name="PROFESSOR OCTAGON", town='octo', kind='octo', hat='gradcap', quests=['specimens'], lines=[
        "FASCINATING! A REVERSIBLE OCTOPUS! I MUST WRITE A PAPER ABOUT YOU.",
        "MY MUSEUM WILL ONE DAY SHOW EVERY GUARDIAN OF THE SEA AS A 3D STATUE. KEEP RAISING YOUR SCORE!"]),
    'coraline': dict(name="CORALINE", town='octo', kind='octo', hat='flower', quests=['seeds'], lines=[
        "EVERY CORAL IN THIS PARK GREW FROM A SEED I PLANTED MYSELF. ISN'T IT LOVELY?"]),
    'pips': dict(name="CAPTAIN PIPS", town='octo', kind='octo', hat='cap', quests=['parcel'], lines=[
        "AHOY! I SAILED ALL EIGHT SEAS ON EIGHT LEGS. WELL... I SWAM. SAME THING."]),
    'ollie': dict(name="LITTLE OLLIE", town='octo', kind='octo', hat='party', small=True, quests=['marbles'], lines=[
        "WHEN I GROW UP I'M GONNA BE A REVERSIBLE OCTOPUS TOO! ...CAN YOU LEARN THAT?"]),
    'granny': dict(name="GRANNY OCTA", town='octo', kind='octo', hat='beanie', quests=['chain'], lines=[
        "EIGHT ARMS, EIGHT KNITTING NEEDLES. I CAN MAKE A SCARF IN A MINUTE, DEARIE."]),
    'ziggy': dict(name="ZIGGY", town='octo', kind='octo', hat='headphones', quests=['dance'], lines=[
        "THE BEAT OF THE DEEP, MAN! EVERY REGION HAS ITS OWN TUNE - HAVE YOU HEARD THEM ALL?"]),
    'tally': dict(name="TALLY", town='octo', kind='octo', hat='cap', role='scores', lines=[
        "I'M TALLY, KEEPER OF SCORES! EVERYTHING YOU DO OUT THERE EARNS POINTS.",
        "PASS A MILESTONE AND SOMETHING NEW UNLOCKS. PRESS Q ANY TIME FOR YOUR JOURNAL: QUESTS, MILESTONES "
        "AND THE LEADERBOARD."]),
    # Turtle Town
    'tortuga': dict(name="ELDER TORTUGA", town='turtle', kind='turtle', shell=(120, 150, 80), skin=(170, 205, 150),
                    beard=True, specs=True, quests=['nestwatch'], lines=[
        "WELCOME, YOUNG ONE. TURTLE TOWN HAS STOOD ON THIS BEACH FOR TWO HUNDRED SLOW, HAPPY YEARS.",
        "THE OCTOPUSES OF OCTO CITY ARE OUR OLDEST FRIENDS. WE TRADE, WE VISIT... SLOWLY."]),
    'sheldon': dict(name="SHELDON", town='turtle', kind='turtle', shell=(110, 140, 190), skin=(160, 210, 150),
                    specs=True, quests=['shells'], lines=[
        "I COLLECT SHELLS. NOT MINE - I'M USING THAT ONE. OTHER SHELLS."]),
    'myrtle': dict(name="MYRTLE", town='turtle', kind='turtle', shell=(230, 150, 180), skin=(170, 220, 160),
                   hat='sunhat', shop='turtlehats', lines=["SUN'S OUT, HATS ON, HON!"]),
    'speedy': dict(name="SPEEDY", town='turtle', kind='turtle', shell=(220, 80, 70), skin=(160, 210, 140),
                   hat='bandana', quests=['postcards'], lines=[
        "THEY CALL ME SPEEDY. I'M... NOT. BUT I DREAM BIG!"]),
    'shellby': dict(name="CAPTAIN SHELLBY", town='turtle', kind='turtle', shell=(90, 120, 160), skin=(150, 200, 150),
                    hat='cap', quests=['crate'], lines=[
        "THE PIER'S MY POST. NOTHING SAILS IN OR OUT OF TURTLE TOWN WITHOUT OLD SHELLBY KNOWING."]),
    'tim': dict(name="TINY TIM", town='turtle', kind='turtle', shell=(150, 200, 110), skin=(180, 230, 170),
                small=True, quests=['sister'], lines=["I'M SEVENTY! THAT'S SUPER YOUNG FOR A TURTLE."]),
    'nana': dict(name="NANA SHELL", town='turtle', kind='turtle', shell=(200, 180, 140), skin=(180, 210, 170),
                 hat='beanie', shop='swap', lines=["SWAP SHOP'S OPEN, SWEETIE. FAIR TRADES ONLY... MOSTLY."]),
    'carapace': dict(name="DR. CARAPACE", town='turtle', kind='turtle', shell=(232, 232, 236), skin=(170, 210, 160),
                     specs=True, shop='clinic', quests=['tourist'], lines=[
        "AN APPLE A DAY... WE DON'T HAVE APPLES. A KELP CHIP A DAY, THEN."]),
    'coco': dict(name="COCO", town='turtle', kind='turtle', shell=(240, 200, 80), skin=(170, 220, 150),
                 hat='straw', quests=['thunder'], lines=["*STRUMS UKULELE* LA LA LA... OH! HELLO THERE!"]),
    'grumble': dict(name="GRUMBLE", town='turtle', kind='turtle', shell=(110, 100, 90), skin=(150, 170, 140),
                    beard=True, quests=['quiet'], lines=["HMPH. IN MY DAY WE DIDN'T HAVE 'FORMS'. WE HAD ONE SHAPE AND WE LIKED IT."]),
    'tilly': dict(name="TILLY", town='turtle', kind='turtle', shell=(240, 170, 200), skin=(190, 230, 180),
                  small=True, hidden=True, lines=["THANK YOU FOR FINDING ME! I'LL NEVER CHASE BUTTERFLIES THAT FAR AGAIN."]),
}

# ---- what the stalls sell: (id, label, cost, what you get, how many times (None = any)) --------
# cost / get: (resource, amount) where resource is pearls / spirit / bombs / heal / potion / heart,
# or an item id ('hat_...', 'ink_...') to unlock
SHOPS = {
    'ink': ("INKY'S INK", [
        ('ink_ocean', "OCEAN INK", ('pearls', 25), ('ink_ocean', 1), 1),
        ('ink_candy', "CANDY INK", ('pearls', 30), ('ink_candy', 1), 1),
        ('ink_toxic', "TOXIC INK", ('pearls', 35), ('ink_toxic', 1), 1),
        ('ink_shadow', "SHADOW INK", ('pearls', 40), ('ink_shadow', 1), 1),
        ('ink_pearl', "PEARL INK", ('pearls', 60), ('ink_pearl', 1), 1)]),
    'octohats': ("MADAME TENTA'S HATS", [
        ('hat_beret', "BERET", ('pearls', 35), ('hat_beret', 1), 1),
        ('hat_fez', "FEZ", ('pearls', 40), ('hat_fez', 1), 1),
        ('hat_tiara', "TIARA", ('pearls', 70), ('hat_tiara', 1), 1)]),
    'bank': ("OCTO CITY BANK", [
        ('b_spirit', "BUY A SPIRIT PEARL", ('pearls', 100), ('spirit', 1), None),
        ('b_sell', "SELL A SPIRIT PEARL", ('spirit', 1), ('pearls', 45), None),
        ('b_bombs', "FIVE BUBBLE BOMBS", ('pearls', 25), ('bombs', 5), None),
        ('b_potion', "SEA POTION", ('pearls', 20), ('potion', 1), None)]),
    'food': ("BARNABY'S KITCHEN", [
        ('f_soup', "SEAWEED SOUP (ALL HEARTS)", ('pearls', 6), ('heal', 99), None),
        ('f_cake', "SPONGE CAKE (A POTION)", ('pearls', 18), ('potion', 1), None)]),
    'turtlehats': ("MYRTLE'S HAT HUT", [
        ('hat_sunhat', "SUN HAT", ('pearls', 30), ('hat_sunhat', 1), 1),
        ('hat_straw', "STRAW HAT", ('pearls', 35), ('hat_straw', 1), 1)]),
    'swap': ("NANA'S SWAP SHOP", [
        ('s_heart', "HEART SHELL FOR 2 SPIRIT PEARLS", ('spirit', 2), ('heart', 1), 2),
        ('s_spirit', "SPIRIT PEARL (TURTLE PRICE)", ('pearls', 70), ('spirit', 1), None),
        ('s_bombs', "SELL FIVE BOMBS", ('bombs', 5), ('pearls', 20), None)]),
    'clinic': ("DR. CARAPACE'S CLINIC", [
        ('c_heal', "CHECK-UP (ALL HEARTS)", ('pearls', 5), ('heal', 99), None),
        ('c_potion', "SEA POTION", ('pearls', 18), ('potion', 1), None)]),
}

# ---- side quests -----------------------------------------------------------------------------
# kind: collect (find items), kill (beat enemies somewhere), visit (go places), deliver (carry
# something to someone), find (find someone), guardians, trials, fusion (show up in a fused form),
# chain (a trading chain). Rewards: pearls, spirit, potion, heart, item (hat_/ink_), score.
QUESTS = {
    # ---- Octo City
    'hatchlings': dict(title="LOST HATCHLINGS", giver='octavia', kind='collect', item='q_hatch', thing="HATCHLING",
                       where="CORAL REEF, KELP WOODS AND THE LAGOON",
                       offer=["MAYOR OCTAVIA: OH, OCTO, THANK GOODNESS! THREE OF OUR HATCHLINGS SWAM OFF ON A FIELD "
                              "TRIP AND NEVER CAME BACK!",
                              "ONE WAS LAST SEEN IN THE CORAL REEF, ONE IN THE KELP WOODS, ONE IN THE LAGOON. "
                              "PLEASE BRING THEM HOME!"],
                       nag="THE HATCHLINGS ARE STILL OUT THERE: THE CORAL REEF, THE KELP WOODS AND THE LAGOON.",
                       done=["MAYOR OCTAVIA: ALL THREE, SAFE AND SOUND! OCTO CITY OWES YOU, OCTO.",
                             "PLEASE TAKE THIS REWARD - AND A FREE DESSERT AT BARNABY'S, ANY TIME."],
                       reward=dict(pearls=60, score=600)),
    'peppers': dict(title="CHEF'S SPECIAL", giver='barnaby', kind='collect', item='q_pepper', thing="SEA PEPPER",
                    where="THE KELP WOODS",
                    offer=["CHEF BARNABY: MY FAMOUS FIRE-KELP STEW NEEDS THREE SEA PEPPERS, AND I'M ALL OUT!",
                           "THEY GROW WILD IN THE KELP WOODS. BRING ME THREE AND I'LL MAKE IT WORTH YOUR WHILE!"],
                    nag="THREE SEA PEPPERS FROM THE KELP WOODS, PLEASE! THE STEW WAITS FOR NO ONE.",
                    done=["CHEF BARNABY: PERFECT PEPPERS! *SNIFF* SMELL THAT HEAT!",
                          "HERE - A SEA POTION FOR THE ROAD. IT SAVES YOU ONCE IF YOU FALL."],
                    reward=dict(potion=1, pearls=30, score=400)),
    'seeds': dict(title="CORAL SEEDS", giver='coraline', kind='collect', item='q_seed', thing="CORAL SEED",
                  where="THE CORAL GARDENS",
                  offer=["CORALINE: MY PARK NEEDS NEW CORAL, BUT THE BEST SEEDS ONLY GROW IN THE CORAL GARDENS.",
                         "COULD YOU FIND FOUR GLOWING CORAL SEEDS FOR ME? THEY SPARKLE PINK!"],
                  nag="FOUR GLOWING CORAL SEEDS FROM THE CORAL GARDENS, PRETTY PLEASE!",
                  done=["CORALINE: OH, THEY'RE BEAUTIFUL! I'LL PLANT THEM RIGHT BY THE POND.",
                        "TAKE THIS SPIRIT PEARL. IT GLOWED IN MY GARDEN FOR YEARS - NOW IT'S YOURS."],
                  reward=dict(spirit=1, score=500)),
    'specimens': dict(title="SPECIMENS PLEASE", giver='octagon', kind='guardians', n=3,
                      where="ANYWHERE A GUARDIAN WAITS",
                      offer=["PROFESSOR OCTAGON: I'M WRITING A BOOK ON MURK'S GUARDIANS. BUT I NEED DATA!",
                             "BEAT THREE OF THEM AND TELL ME ALL ABOUT IT. FOR SCIENCE!"],
                      nag="THREE GUARDIANS BEATEN, THAT'S ALL I ASK. FOR SCIENCE!",
                      done=["PROFESSOR OCTAGON: THREE GUARDIANS! MY PEN CAN'T KEEP UP!",
                            "YOU'VE EARNED AN HONORARY DEGREE. HERE'S YOUR CAP - AND A SPIRIT PEARL FOR RESEARCH."],
                      reward=dict(item='hat_gradcap', spirit=1, score=700)),
    'parcel': dict(title="SPECIAL DELIVERY", giver='pips', kind='deliver', to='tortuga', thing="PARCEL",
                   where="TURTLE TOWN, ON SUNNY BEACH",
                   offer=["CAPTAIN PIPS: I'VE A PARCEL FOR ELDER TORTUGA IN TURTLE TOWN, BUT MY TENTACLES ACHE.",
                          "TURTLE TOWN IS UP ON SUNNY BEACH - TAKE THE SHORE STEPS OUT OF THE SEA. YOU'LL CARRY IT?"],
                   nag="THE PARCEL GOES TO ELDER TORTUGA IN TURTLE TOWN, UP ON SUNNY BEACH.",
                   done=["ELDER TORTUGA: A PARCEL FROM PIPS! MY NEW READING GLASSES! NOW I CAN SEE YOU, YOUNG ONE.",
                         "THANK YOU FOR CARRYING IT ALL THIS WAY. TAKE THESE PEARLS."],
                   reward=dict(pearls=60, score=300)),
    'marbles': dict(title="OLLIE'S MARBLES", giver='ollie', kind='collect', item='q_marble', thing="GLASS MARBLE",
                    where="THE GLASS REEF, FAR TO THE EAST",
                    offer=["LITTLE OLLIE: I LOST MY MARBLES! ALL FIVE! THEY ROLLED ALL THE WAY TO THE GLASS REEF.",
                           "IT'S REALLY FAR EAST. THEY'RE SHINY AND BLUE. PLEEEASE?"],
                    nag="MY FIVE MARBLES ARE IN THE GLASS REEF! FAR, FAR EAST!",
                    done=["LITTLE OLLIE: MY MARBLES! YOU'RE THE BEST OCTO EVER!",
                          "HERE, HAVE MY SNORKEL MASK. IT MAKES YOU LOOK SUPER COOL."],
                    reward=dict(item='hat_snorkel', pearls=40, score=600)),
    'dance': dict(title="DANCE FEVER", giver='ziggy', kind='fusion',
                  where="THE FUSION MACHINE, EAST OF HERMIE'S SHOP",
                  offer=["ZIGGY: I'M PUTTING ON THE BIGGEST DANCE PARTY IN THE DEEP, AND I NEED A HEADLINER!",
                         "COME BACK IN A FUSED FORM - ANY ONE - AND SHOW ME YOUR MOVES!"],
                  nag="COME BACK IN A FUSED FORM, MAN! THE FUSION MACHINE BY HERMIE'S SHOP CAN MAKE ONE.",
                  done=["ZIGGY: WHOA! THOSE MOVES! THAT GLOW! YOU'RE THE HEADLINER, NO QUESTION.",
                        "TAKE MY SPARE HEADPHONES. THE DEEP SOUNDS BETTER WITH THEM."],
                  reward=dict(item='hat_headphones', score=500)),
    'chain': dict(title="GRANNY'S SWAP", giver='granny', kind='chain', where="BOTH TOWNS",
                  steps=[('shellby', 'tr_scarf', 'tr_ship',
                          ["CAPTAIN SHELLBY: A SCARF? FROM GRANNY OCTA? *SNIFF* THE SEA BREEZE WON'T BOTHER ME NOW!",
                           "TAKE THIS SHIP IN A BOTTLE. PROFESSOR OCTAGON IN OCTO CITY COLLECTS 'EM."]),
                         ('octagon', 'tr_ship', 'tr_map',
                          ["PROFESSOR OCTAGON: A SHIP IN A BOTTLE! A FINE SPECIMEN!",
                           "IN RETURN, AN OLD STAR MAP. COCO IN TURTLE TOWN WRITES SONGS ABOUT THE STARS."]),
                         ('coco', 'tr_map', 'tr_conch',
                          ["COCO: A MAP OF THE STARS! I FEEL A SONG COMING ON...",
                           "TAKE MY GOLDEN CONCH. GRANNY OCTA LOVES ITS SOUND - TAKE IT TO HER!"])],
                  first='tr_scarf',
                  offer=["GRANNY OCTA: I KNITTED A SCARF FOR CAPTAIN SHELLBY IN TURTLE TOWN. HE ALWAYS HAS THE "
                         "SNIFFLES.",
                         "WOULD YOU TAKE IT TO HIM, DEARIE? YOU NEVER KNOW WHAT A KIND DEED BRINGS BACK."],
                  nag="FOLLOW THE TRADES, DEARIE - WHATEVER YOU'RE CARRYING, SOMEONE WANTS IT.",
                  done=["GRANNY OCTA: MY GOLDEN CONCH! I GAVE IT TO COCO YEARS AGO... AND IT CAME ALL THE WAY BACK.",
                        "YOU'VE A KIND HEART, OCTO. HERE - LET IT GROW A LITTLE BIGGER."],
                  reward=dict(heart=1, pearls=40, score=900)),
    # ---- Turtle Town
    'nestwatch': dict(title="NEST WATCH", giver='tortuga', kind='kill', n=6, region='SUNNY BEACH',
                      where="SUNNY BEACH",
                      offer=["ELDER TORTUGA: CREATURES KEEP PROWLING SUNNY BEACH, RIGHT WHERE OUR EGGS ARE LAID.",
                             "WOULD YOU CHASE OFF SIX OF THEM? THE LITTLE ONES WILL SLEEP SOUNDER."],
                      nag="SIX CREATURES ON SUNNY BEACH, YOUNG ONE. THE NESTS ARE COUNTING ON YOU.",
                      done=["ELDER TORTUGA: THE BEACH IS QUIET AGAIN. THE EGGS ARE SAFE.",
                            "WEAR THIS SHELL HELMET WITH PRIDE. IT WAS MINE, ONE HUNDRED AND FIFTY YEARS AGO."],
                      reward=dict(item='hat_shellhelm', pearls=50, score=600)),
    'shells': dict(title="SHINY SHELLS", giver='sheldon', kind='collect', item='q_shell', thing="SHINY SHELL",
                   where="SUNNY BEACH, TIDE MEADOWS AND PALM JUNGLE",
                   offer=["SHELDON: MY COLLECTION IS MISSING FIVE SHINY SHELLS. THEY'RE SOMEWHERE ON THE SURFACE.",
                          "TWO ON SUNNY BEACH, TWO IN THE TIDE MEADOWS AND ONE IN PALM JUNGLE, IF MY NOTES ARE RIGHT."],
                   nag="FIVE SHINY SHELLS: SUNNY BEACH, TIDE MEADOWS, PALM JUNGLE.",
                   done=["SHELDON: MAGNIFICENT! MY COLLECTION IS COMPLETE! WELL... UNTIL I FIND MORE.",
                         "HERE: TWO SPIRIT PEARLS FROM THE BACK OF MY CABINET."],
                   reward=dict(spirit=2, score=700)),
    'sister': dict(title="LOST SISTER", giver='tim', kind='find', who='tilly', where="PALM JUNGLE",
                   offer=["TINY TIM: MY SISTER TILLY CHASED A BUTTERFLY INTO PALM JUNGLE AND DIDN'T COME BACK!",
                          "SHE'S PINK AND SMALL, LIKE ME. PLEASE FIND HER!"],
                   nag="TILLY'S SOMEWHERE IN PALM JUNGLE! PLEASE HURRY!",
                   done=["TINY TIM: TILLY! YOU'RE HOME! *HUGS SLOWLY*",
                         "THANK YOU, OCTO! HERE'S MY WHOLE PEARL SAVINGS!"],
                   reward=dict(pearls=80, score=500)),
    'postcards': dict(title="POSTCARDS", giver='speedy', kind='visit', regions=['DUNE DESERT', 'VOLCANO RIDGE',
                                                                              'TIDE MEADOWS'],
                      where="DUNE DESERT, VOLCANO RIDGE AND TIDE MEADOWS",
                      offer=["SPEEDY: I'VE ALWAYS WANTED TO SEE THE WORLD. BUT, Y'KNOW... IT'D TAKE ME A CENTURY.",
                             "VISIT THE DUNE DESERT, VOLCANO RIDGE AND THE TIDE MEADOWS, AND TELL ME ALL ABOUT THEM!"],
                      nag="DUNE DESERT, VOLCANO RIDGE, TIDE MEADOWS. TELL ME EVERYTHING!",
                      done=["SPEEDY: A DESERT? A VOLCANO? WOW! I FEEL LIKE I WENT THERE MYSELF!",
                            "TAKE MY LUCKY BANDANA. IT MAKES YOU FEEL FAST, EVEN IF YOU'RE NOT."],
                      reward=dict(item='hat_bandana', spirit=1, score=700)),
    'quiet': dict(title="QUIET PLEASE", giver='grumble', kind='kill', n=10, world='under', where="THE UNDERDEEP",
                  offer=["GRUMBLE: CREATURES IN THE UNDERDEEP RUMBLE ALL NIGHT. I CAN FEEL IT THROUGH MY SHELL.",
                         "GO DOWN THERE AND QUIET TEN OF THEM. THEN MAYBE I'LL GET SOME SLEEP. HMPH."],
                  nag="TEN CREATURES IN THE UNDERDEEP. THE SINKHOLES TAKE YOU DOWN. HMPH.",
                  done=["GRUMBLE: ...SILENCE. BLESSED SILENCE. HMPH. THANKS, I SUPPOSE.",
                        "HERE. PEARLS. DON'T SPEND THEM ALL AT ONCE."],
                  reward=dict(pearls=120, score=700)),
    'crate': dict(title="COCONUT CRATE", giver='shellby', kind='deliver', to='barnaby', thing="CRATE OF COCONUTS",
                  where="OCTO CITY, BY THE OCTO TEMPLE",
                  offer=["CAPTAIN SHELLBY: CHEF BARNABY IN OCTO CITY ORDERED A CRATE OF COCONUTS.",
                         "MY BOAT'S IN FOR REPAIRS. COULD YOU TAKE IT? OCTO CITY'S GATE IS RIGHT BY THE OCTO TEMPLE."],
                  nag="THE COCONUTS GO TO CHEF BARNABY IN OCTO CITY.",
                  done=["CHEF BARNABY: MY COCONUTS! COCONUT-KELP PUDDING TONIGHT!",
                        "FOR YOUR TROUBLE: A SEA POTION AND A FEW PEARLS."],
                  reward=dict(potion=1, pearls=30, score=300)),
    'tourist': dict(title="TRIAL TOURIST", giver='carapace', kind='trials', n=3,
                    where="ANY TRIAL PORTAL",
                    offer=["DR. CARAPACE: DOCTOR'S ORDERS: MORE EXERCISE! WIN THREE MORE TRIALS.",
                           "IT'S GOOD FOR THE HEART. AND THE OTHER HEART, IF YOU'RE AN OCTOPUS."],
                    nag="THREE MORE TRIALS, PATIENT. DOCTOR'S ORDERS.",
                    done=["DR. CARAPACE: THREE TRIALS! A CLEAN BILL OF HEALTH!",
                          "TWO SPIRIT PEARLS, FOR YOUR TROUBLE. TAKE THEM TO THE TEMPLE ALTAR."],
                    reward=dict(spirit=2, score=600)),
    'thunder': dict(title="SONG OF THUNDER", giver='coco', kind='visit', regions=['THUNDERHEADS'],
                    where="THE THUNDERHEADS, UP IN THE SKY",
                    offer=["COCO: I'M WRITING A SONG ABOUT THE SKY, BUT I'VE NEVER HEARD REAL THUNDER.",
                           "VISIT THE THUNDERHEADS, HIGH UP IN THE SKY, AND COME BACK AND TELL ME HOW IT SOUNDS!"],
                    nag="THE THUNDERHEADS ARE IN THE SKY. THE GEYSERS IN THE SEA CAN BLAST YOU UP!",
                    done=["COCO: BOOM? KRA-KOOM? OH, THAT'S PERFECT! *STRUMS FURIOUSLY*",
                          "TAKE THIS STORM INK. YOUR JET WILL CRACKLE LIKE LIGHTNING!"],
                    reward=dict(item='ink_storm', score=500)),
}

# where quest things are hidden (generated with tools/place_quests.py, checked by world.validate)
QUEST_SPOTS = {
    'hatchlings': [(65, 36), (9, 16), (13, 54)],
    'peppers': [(26, 5), (18, 13), (8, 21)],
    'seeds': [(87, 2), (77, 20), (69, 6), (93, 20)],
    'marbles': [(237, 6), (172, 24), (196, 2), (214, 25), (161, 2)],
    'shells': [(129, 281), (2, 270), (65, 221), (10, 216), (137, 216)],
    'sister': [(96, 253)],
}

# leaderboard rivals (name, score, kind)
RIVALS = [('SPEEDY', 2500, 'turtle'), ('LITTLE OLLIE', 6000, 'octo'), ('INKY', 12000, 'octo'),
          ('SHELDON', 20000, 'turtle'), ('CORALINE', 30000, 'octo'), ('MAYOR OCTAVIA', 45000, 'octo'),
          ('ELDER TORTUGA', 65000, 'turtle'), ('OLD SHELLY', 85000, 'turtle'), ('THE GREAT KRAKEN', 120000, 'octo')]
RIVAL_LOOK = {'SPEEDY': 'speedy', 'LITTLE OLLIE': 'ollie', 'INKY': 'inky', 'SHELDON': 'sheldon',
              'CORALINE': 'coraline', 'MAYOR OCTAVIA': 'octavia', 'ELDER TORTUGA': 'tortuga',
              'OLD SHELLY': 'shelly', 'THE GREAT KRAKEN': 'kraken'}

ITEM_NAMES = {'tr_scarf': "KNITTED SCARF", 'tr_ship': "SHIP IN A BOTTLE", 'tr_map': "OLD STAR MAP",
              'tr_conch': "GOLDEN CONCH", 'q_parcel': "PARCEL", 'q_crate': "CRATE OF COCONUTS"}
