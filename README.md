# Legend of Octo

By Minu Hong.

## ▶ [Play it in your browser](https://tmhon6.github.io/legend_of_octo/)

📜 **[Game layout for review](docs/layout.pdf)**: story flow, the whole map, every dungeon, both towns, the trial rooms and all creatures, without playing. The pages are also pictures in [docs/layout](docs/layout/). Rebuild them with `.venv/bin/python tools/make_layout.py`.

No download needed. Wait about 15 seconds for it to load, click or tap the page, then press Enter or tap again.
Works with a keyboard on a computer, or with on-screen touch controls on phones and tablets.
On a phone, play sideways: the controls sit on both sides of the game, and your first tap goes full
screen (the FULL / EXIT button toggles it). Put your thumb anywhere on the left half and drag to
swim (any angle; push further to go faster). On an iPhone, use Share → Add to Home Screen to play full screen.

A top-down undersea adventure starring Octo, the reversible octopus. It's a fan tribute to the
classic 8-bit action-adventure style, built in pygame. All the characters, places, art, music and
maps are original.

## Run

    python3 -m venv .venv          # first time only
    .venv/bin/pip install pygame   # first time only
    .venv/bin/python main.py

It first asks **which version** to play, like the website does: the latest release (1), the
development build - this folder as it is (2) - or any older release from a list (3). Just Enter
plays the latest. To skip the question:

    .venv/bin/python main.py latest    # or: dev, v2.5.0, ... (list shows them all)

An older release is set up once in `.versions/<tag>/` the first time you choose it. Each version
keeps its own saved game.

On the title screen, **Enter** starts a new game and **L** loads your saved game.

## Play in a browser

The same code also runs in a web browser through [pygbag](https://pypi.org/project/pygbag/)
(Python compiled to WebAssembly). You need `ffmpeg` installed.

    .venv/bin/pip install pygbag            # first time only
    .venv/bin/python build_web.py           # builds build/web/
    .venv/bin/python build_web.py --serve   # builds, then serves it at http://localhost:8000

### Versions

Every git tag like `v1.0.0` is a version, and every version is on the web page: its two big
buttons are the latest version and the development build (`main` as it is now, the same as the
latest version when nothing new is waiting), and every older version is in the dropdown below them.
Each version keeps its own saved game. The title screen shows the version you're running. To
release one:

    git tag -a v1.1.0 -m "Mini-bosses and touch controls"
    git push origin v1.1.0
    gh workflow run pages.yml        # republish the site so the new version appears

`build_site.py` builds every tagged version plus the development build into `build/site/`. A
version never changes, so each is built once and kept in `build/versions_cache/` (the deploy keeps
that folder between runs too), and only new versions take time to build.

Pushing to `main` on GitHub runs `.github/workflows/pages.yml`, which builds the web version and
publishes it to GitHub Pages. In the repo, set **Settings → Pages → Source** to **GitHub Actions**.
In the browser, saves go to the browser's local storage instead of `savegame.json`.

## Controls

| Key                | Action                                              |
|--------------------|-----------------------------------------------------|
| Arrows / WASD      | Move                                                |
| Z / Space          | Attack (depends on form) · talk · buy in the shop   |
| X / Right Shift    | Next form                                           |
| 1-9, 0             | Jump straight to a form (X cycles through all of them) |
| C                  | Happy ink style: long line <-> short wide burst     |
| V                  | Ink jet: a quick dash that leaves a stinging ink cloud (you can't be hurt mid-jet) |
| B                  | Drop a bubble bomb (buy them in the Pearl Shop)     |
| T                  | Warp to a completed trial portal or Octo's house (and, after the Octo Express milestone, to the towns) |
| Left Shift         | Save the game                                       |
| P / Enter / Esc    | Pause. The pause menu has **RESUME**, **SAVE** and **QUIT** buttons: click or tap them, pick with the arrows and Z, or press **P**, **S** or **Esc** (Q works too). Quit saves first, then goes back to the title screen |
| M                  | World map (game pauses; ←/→ flips between sea and sky) |
| N                  | Mute / unmute all sound (music and effects)         |
| H                  | Wardrobe: pick a hat and the ink jet's colour       |
| Q                  | Journal: side quests, score and milestones, the leaderboard, the bestiary, extras (←/→ switch tabs) |
| R (in the pause menu) | Pebble the snail joins or leaves (two players)   |
| F11                | Fullscreen                                          |
| F3                 | Show the frame rate                                 |

The mouse pointer only shows on the title screen and the pause menu, where you can click their
buttons; while you play it's hidden. On a computer, Esc on the title screen closes the game.

### Player two: Pebble the snail

Octo's pet snail **Pebble** can join on the same screen. Pick **2 PLAYERS** on the title screen,
press R in the pause menu, wake him in his basket in Octo's house, or press a button on a gamepad.

| Player two          | Keyboard     | Gamepad  |
|---------------------|--------------|----------|
| Move                | I J K L      | Stick / d-pad |
| Spit slime (slows what it hits) | Right Shift | A |
| Shell spin (can't be hurt, bowls enemies over) | `/` | B |

Octo keeps the arrow keys and W A S D. With Pebble playing, Octo changes form with X (Right Shift
is Pebble's now).

Pebble has his own three hearts. If he loses them he hides in his shell for a few seconds, then
pops back out next to Octo, so only Octo can lose the game. He picks up pearls and hearts too, his
kills count towards the score, and he always stays on screen with Octo, following him through every
door, portal and town gate. Wherever he slides he leaves a shiny slime trail that dries up after a
few seconds.

## Forms

Octo starts with two forms. Each trial unlocks another. Every form also has its own **strength**,
which is on while you're in that form.

| Form    | Z does                                                     | Strength                                   | From              |
|---------|------------------------------------------------------------|--------------------------------------------|-------------------|
| Happy   | Ink, aimed at the nearest enemy (line or burst)            | Speedy: swims 20% faster                   | start             |
| Grumpy  | Tentacle slap; cuts kelp, swats shots                      | Strong: every attack deals +1 damage       | start             |
| Zappy   | Shock ring that hits everything nearby; shatters ice walls | Charged: ink jet recharges twice as fast   | Trial of Storms   |
| Chilly  | Ice shard that freezes enemies; cools lava into rock       | Tough: big hits hurt half a heart less     | Trial of Currents |
| Spooky  | Two homing wisps that fly through walls; walks through ghost walls | Slippery: twice as long invincible after a hit | Trial of Shadows |
| Bubbly  | Bubble shield: a few seconds of no damage                  | Healing: half a heart every 8 seconds      | Trial of Frost    |
| Spiky   | Spines in all eight directions                             | Thorns: enemies that touch you get hurt    | Trial of Embers   |
| Glowy   | Flash that stuns the whole screen                          | Lucky: double treasure drops; lights the dark | Trial of Echoes |
| Airy    | Fog cloak: enemies lose sight of you                       | Steady: never knocked back, a bit faster   | Trial of Winds    |

### Spirit pearls and the temple altar

Every trial portal (there are 41) gives a **spirit pearl** the first time you beat it. Take three to the
altar on top of the Octo Temple and it teaches you a form of your choice: Zappy, Chilly, Spooky,
Bubbly, Spiky, Glowy, Airy, Magnety, Clammy, Starry, Wobbly or Stony (or +1 heart).

Trials come in seven kinds: waves of enemies, orb grabs, survival barrages, mini-boss duels,
thief chases, defending a giant clam, and sentry races. Some are in the dark or in a strong current.

### The Fusion Machine

Next to Hermie's Pearl Shop. For 25 pearls it fuses **any two** base forms. There are **16 fused
forms**, one for each attack shape - hail, whip, roll, quake, lantern, whirlpool, trap, chain bolt,
nova, boomerang, seeker stars, mines, boulder, beam, orbs and rain - so no two of them share an
attack, and between them they use all 12 elements. Every pair of forms leads to one of them, with
boosted versions of its parents' strengths. If a pair leads to one you've already made, the machine
tells you before you pay. Press **F** (or the FORMS button) to pick any form from a list.

(Saves from before v2.5.0, when every pair made its own fused form, still load: copies of the same
attack fold into the one that's kept.)

### Mini-bosses

Each region has a mini-boss waiting in it, glowing in its own colour. Swim close and you're
pulled into its lair (which takes on the mood of its home: icy, fiery, gloomy...) for a 1-on-1
fight in three stages: crabs lose a claw, then the other, jellies lose their tentacles, and so on -
and each stage makes them faster and adds new moves. Fall and you're swept back out to try again.

Every kind of boss has **signature moves** of its own, besides charging, shooting, calling
minions and teleporting:

| Move | Who | What happens |
|------|-----|--------------|
| Slam | crabs, golems, beetles, hoppers, apes | crouches, leaps high and crashes down where you were, throwing out a ring of orbs |
| Spiral | jellies, urchins, prisms, crystal bugs, spores, fish | spins and pours out a spiral of orbs (more arms when it's angry) |
| Barrage | birds, scorpions, salamanders, puffers, glass fish | takes aim, then fires a rapid stream at you |
| Burst | puffers, spores, jellies, golems, magma | swells up, flashing, and bursts into a ring with one gap to slip through |
| Dash | fish, beetles, scorpions, seahorses | three quick dashes at you |
| Strikes | storm, fire, ice and star bosses | rears up and calls lightning, meteors, lava or icicles down on you and all around you |

**Every attack is warned first, in red on the floor:** a ring where something will land (it fills
in as the moment comes) or a dashed line where a boss is about to charge, dash or fire. Boss shots
are big glowing orbs in the boss's colour (red once it's furious, when steam rises off it too). The
health bar shows the bit you just knocked off before it drains away, and a beaten boss doesn't just
vanish: it shudders, cracks with little blasts and bursts apart in pieces.

Every 1-on-1 starts with a **versus entrance**: the screen cracks and shatters, Octo (hat and all)
and the guardian face off across a slash of light, **VS** slams down, and the panels split apart
on the arena with a **FIGHT!**. Temple bosses get the same entrance the first time you reach their
room. The final blow lands in slow motion with a **VICTORY!** banner. Press Enter or Z (or tap) to
skip ahead.

### 3D

The ground is pixel art, but everything that stands up is drawn in 3D at three times the
resolution (twice in the browser), all in code:
* **Octo is a round 3D figure in his own pixel style.** Every pixel of his sprite becomes a little
  lit cube, and his head is a smoothly shaded ball, with his back drawn from his back sprite. He
  turns smoothly in 3D, sways when he's idle, spins round when he changes form, and wears his hat
  in 3D too, in every form. Pebble the snail is a little 3D snail in the same style.
* **Friendly characters are 3D too.** Every octopus in Octo City is Octo's own 3D model in their
  colours, wearing their hat in 3D (the mayor's crown, the chef's hat...), turning to look at you,
  with their quest marker floating overhead. The turtles of Turtle Town and Old Shelly have domed
  3D shells and turn to face where they're going, Hermie is 3D in his shop, and the Living Legend
  statue is a golden 3D Octo on a stone plinth.
* **Attacks are 3D too.** Ink drops, Pebble's slime, spines, ice shards, wisps, stars, shells,
  orbs, lanterns, mines, bombs, hail, rocks, the spike roll, Octo's slap and every enemy shot are
  their pixel art turned into lit cubes, like Octo. They fly at body height with a shadow on the
  sea floor, and pass in front of and behind Octo, Pebble and the buildings. Zap rings and novas
  are glowing bands round Octo (the far side passes behind him), beams are lit tubes, lightning
  and the whip arc through the water above their reflections, whirlpools are spinning funnels,
  bombs burst into fireballs, and the bubble shield and fog wrap round him in 3D.
* **Enemies are 3D too.** Every creature, guardian, mini-boss and boss is its own pixel art turned
  into lit cubes, so crabs, jellies, eels, urchins and the rest stand up off the sea floor, flash
  when they're hit, and pass in front of and behind Octo, Pebble and the buildings.
* **Kelp and coral stand up off the sea floor**, drawn smooth at full resolution: kelp grows in
  clumps of fronds with long leaves and little gas floats, swaying gently in the swell (and going
  see-through when Octo or Pebble is right behind it), and each coral is a branching coral, a lacy
  sea fan, a brain coral or a cluster of tube sponges, in the colours of its part of the sea. Cut
  kelp leaves bare sand.
* **Geysers are alive:** in the sea, water gushes up out of a stone vent and froths at the top,
  with bubbles streaming up it, spray falling back and rings rippling over the sand; up on a sky
  island, clouds swirl round far below the hole and mist drifts up out of it. **Riding one** is a
  trip: the sea floor drops away as the water blasts Octo up past streaming bubbles, he bursts out
  through the bright surface, clouds rush past and the sky island comes down to meet him (and the
  other way when he drops back down, or tumbles when his water ball bursts). If you're still
  holding a direction when you land, the geyser waits until you let go before it works again.
* **The ink jet dash is 3D:** Octo leans into the jet, leaves see-through copies of himself in
  your jet colour, squirts lit ink blobs behind him and streaks through the water. The jet's
  recharge bar at the top of the screen is a lit 3D tube.
* **The top of the screen is 3D:** a raised panel with shiny pearls, a 3D key and bombs, voxel
  hearts that bob (and beat when you're low), a 3D Octo turning in the form box, and smooth
  lettering.
* **3D buildings:** the Octo Temple pyramid (walk up its stairs onto the top), the stone Octo
  statues in front of it, Hermie's Pearl Shop, both town gates, and every house, hall, stall,
  fountain, tower, lighthouse and hut in Octo City and Turtle Town, and Octo's own house and
  everything in it. Things behind a building disappear behind it.
* **Trial portals** are stone rings with a swirling vortex. Step into one and Octo is pulled in:
  the view rushes towards the portal as he spirals into the vortex, then he pops out in the trial.
* **The opening:** a short loading bar first gets everything ready, so the opening plays smoothly
  from start to end (in a browser too). "Minu Hong presents" fades in over the sunset in clean,
  spaced-out capitals; then glide over a smooth dawn sea (long swells rolling in, streaks of light
  and shade drifting by, the sun's path glittering), dive under, and 3D Octo swims up out of the deep
  as the logo flies together letter by letter. Any key (or a tap) skips it. Then you swim on through the
  logo into the title screen, with bubbles streaming past, and starting a game dives down from the
  title onto the sea floor, which swings up flat from a 3D tilt.
* **The title screen** is drawn at full resolution: kelp sways smoothly, fish, sunbeams and marine
  snow drift without stepping from pixel to pixel, and the menu sits in a box that fits it.
* **The title screen's 3D logo**, **boss entrances** (the versus screen faces 3D Octo, in your form and hat,
  off against a 3D figure of the boss, with **FIGHT!** and **VICTORY!** in 3D letters),
  **town fly-overs**, **milestone medals**, the **leaderboard podium** and the **3D Museum**.

### Hermie's shop

Every item on the counter has its price under it. Walk up to one to see what it does, and press
**Z** to shop: Hermie's catalogue opens at that item (the sea waits while you shop), with every
price, and you buy with Z. Or talk to Hermie for the same catalogue: sea potions, a big bomb bag,
the trial compass, a lucky charm, deep goggles, jet ink, coral armor, a pearl magnet and even
spirit pearls.

Jellies ignore ink, and slapping an urchin hurts *you*.

## The journey

Grimfin the Shark and his big sister Murk stole the Golden Pearl. Murk locked it in her palace in
the dark Sunken City and sealed the door with the magic of seven **Tide Bells**. Ring all seven
to break the seal:

* Murk put a **guardian** (mini-boss) in every region. Each guardian carries the **sigil** that
  unseals its region's dungeon. Beat the guardian, open the dungeon, ring the bell
* one bell is guarded by Grimfin in the **Sunken Shrine** (Big Pinch holds its sigil)
* six more lie in **deep temples** whose cave mouths are hidden in the Kelp Woods, Coral Gardens,
  The Lagoon, The Abyss, Frozen Shelf and Ember Vents

Each temple is a multi-room dungeon of 9 to 14 rooms, seen one screen at a time:

* **Keys and locked doors.** Each key lies in a room you can reach before its door.
* **Sealed rooms.** Their doors slam shut until every enemy inside is beaten.
* **Barriers.** Kelp, cracked walls, ghost walls, ice or lava block the way, and you need the
  right form (or bombs) to pass.
* **Secret cracked walls** to bomb, and a **guardian boss** with three battle stages.
* **Rewards.** Ringing a bell gives you one more heart and carries you back out to the sea.
* **The map.** Press **M** inside a temple to see the rooms you've visited, and the Trial Compass
  shows where the guardian waits.

**Difficulty.** You start with three hearts, the same as classic games of this kind:

* Enemies get tougher and hit harder the further you roam from the Octo Temple, and harder
  still in the later temples.
* Hearts drop less often.
* Every region has its own creature: sand eels, snapjaw clams, lionfish, stingrays, anglerfish, bilge
  ghosts, ice squid, cinder slugs, lantern wisps and cloud puffs.
* Every region, the temples and the boss fights have their own music, and each tune keeps changing
  as it plays: a light first verse, then the full band with harmony, a counter-line and drum fills,
  a bridge in a new key on music-box bells that drops down and builds back up with a snare roll,
  and a big last verse, before it loops round. Calm places get gentle percussion (or none), fights
  get driving drums, Turtle Town a calypso beat and Octo City a swing, and one tune fades into the
  next as Octo moves between places.
* If you fall, you start again at the temple entrance (or your last checkpoint) with three hearts.

Beat Murk to win. Then press Enter for **Deep Tide**, a harder replay of the whole game.

## Four worlds

* **The Sea** (240×80 tiles). Far to the east, past the Frozen Shelf, Ember Vents and Sunken
  City, lie **Glass Reef**, the **Siren Shoals** and dark **Whale Fall**.
* **The Sky**, reached by geysers. It's four times bigger than before: the old Sky Islands plus
  the **Thunderheads**, **Rainbow Reach** and **Starfall Peaks**, linked by plank bridges.
* **The Surface**, up the white **shore steps** in the Lagoon, the Reef and the Siren Shoals:
  **Sunny Beach**, **Tide Meadows**, **Palm Jungle**, **Dune Desert**, and **Volcano Ridge**
  behind a ring of lava.
* **The Underdeep**, down the purple **sinkholes** in the Abyss, the Ship Graveyard and Whale
  Fall: **Crystal Caves**, **Fungus Grotto**, **Bone Trench**, the **Ancient Ruins**, and the
  **Magma Core** (with a lava tube up to the volcano).

Every new region has its own creature (16 new kinds), its own guardian (who drops a spirit pearl)
and its own music. There are **74 trial portals** in all. Press **M**, then left/right, to flip
between the maps of the worlds you've visited.

### Six new forms

**Sandy** (sand quake; dodges one hit in four), **Leafy** (poison vine lash; heals and has
thorns), **Crysty** (piercing prism beam; critical hits), **Cloudy** (rain cloud; *floats over
pits, ponds and sky gaps*), **Shroomy** (dizzying spores; finds more treasure) and **Magmy**
(magma orbs; *walks on lava*). They bring three new attack shapes to the Fusion Machine (beam,
orbs, rain) and five new elements (venom, sludge, gust, dizzy, crack).

### The secret Mega Machine

Make **all 16 fused forms** and an old machine wakes deep in the **Ancient Ruins** of the Underdeep.
It fuses two *fused* forms into a **mega form**, for 100 pearls. There are six mega forms, one for
each huge attack (Supernova, Tsunami, Meteor Storm, Black Hole, Prism Storm, Titan Slam), each
carrying two elements, plus the strengths of both parents, pushed further.

### Fused creatures

Each new region also has a **fused creature** that moves like one creature and attacks like
another, with the head of one and the body of the other. For example, a Glassfish × Scorpion darts
in straight lines and strikes with a stinger. There are 16 kinds.

### Wardrobe: hats and ink colour

Press **H** (or tap **HAT**) to open the wardrobe:
* **27 hats.** A sea cap, a bow and a party hat are yours from the start. Hermie sells a beanie,
  chef hat, cowboy hat, sombrero and top hat. Some are earned: a flower crown for 10 trials, a
  pirate hat for Captain Claw, a propeller cap for visiting every world, a wizard hat for 10 forms,
  a viking helm for 10 guardians, a gold crown for all seven Tide Bells, and a halo for every trial.
  The towns sell a beret, fez, tiara, sun hat and straw hat, and side quests give a snorkel mask,
  headphones, a grad cap, a shell helmet and a lucky bandana. The Champion Crown is for 100,000 points.
* **16 colours for the ink jet's puff**: 9 to start with (rainbow included), five more at Inky's
  in Octo City, Storm ink from Coco's quest and Legend-Gold for the last milestone.

The world map is 160×80 tiles, plus seven one-screen trial rooms and the Sky Islands:

* **Coral Reef** (start, in the Octo Temple), **Kelp Woods**, **Coral Gardens**, **The Lagoon**,
  **The Abyss**, **Ship Graveyard** and the **Sunken Shrine** (Grimfin)
* **Frozen Shelf**: walled off by ice that only Zappy can break
* **Ember Vents**: cut by lava rivers that Chilly cools into rock
* **Sunken City** and **Murk Palace**: behind a ghost wall only Spooky can pass. Pitch dark
  unless you're Glowy
* **Sky Islands**: floating islands above the sea, reached by geysers. They're home to the Trial of Winds (Airy form). Up there Octo rolls around inside a ball of seawater. Hits crack the ball
  instead of costing hearts, but after four cracks it bursts and Octo tumbles back down into the sea

Every region has its own tiles, colour tint and particles, and the new areas have their own music.
Glowing **trial portals** warp you into a hard one-screen challenge: waves of enemies, an orb grab
against the clock, or surviving a barrage. If you fall, you're thrown back out and can try again.
Completed portals become warp points (press **T**), and so does Octo's house once you've been there.

**Hermie's Pearl Shop**, just west of the temple, sells shrimp platters, bubble bombs, swift fins,
a shell shield, deep ink and a heart shell. Bubble bombs blast open cracked rock and hidden caches.

## The towns

**Octo City** lies under the sea; its gate is in the Octo Temple courtyard, right where you start.
**Turtle Town** sits on Sunny Beach, through a gate in the wall north of the shore steps. Both
are full of friendly townsfolk (twelve octopuses and eleven turtles) who wander about, chat and
trade. Press **Z** next to someone to talk. A yellow **!** means they need help, a grey **?** means
you're working on it, a yellow **?** means you've done it, and a gold coin means a shop.

* **Shops:** Inky's ink colours, Madame Tenta's and Myrtle's hats, the Octo City Bank and Nana's
  Swap Shop (pearls, spirit pearls, bombs, even heart shells), Barnaby's kitchen and Dr. Carapace's
  clinic (healing and sea potions).
* **16 side quests:** find the mayor's lost hatchlings, sea peppers for Chef Barnaby, coral
  seeds, Ollie's marbles and Sheldon's shiny shells hidden around the worlds; carry a parcel to
  Turtle Town and coconuts back to Octo City; find Tiny Tim's sister in Palm Jungle; chase
  creatures off Sunny Beach and out of the Underdeep; send Speedy and Coco postcards from far-off
  places; win trials for Dr. Carapace; beat guardians for Professor Octagon; show Ziggy a fused
  form; and follow Granny Octa's trading chain (scarf → ship in a bottle → star map → golden
  conch) between the two towns. Rewards include pearls, spirit pearls, potions, a heart shell, new
  hats and a new ink colour.
* **The journal (Q):** your quests with their progress and where to go, your score and milestones,
  the leaderboard, the **bestiary**, and the extras you've unlocked.
* **The bestiary** lists all 85 creatures, guardians and bosses. Each one fills in when you first
  see it: a 3D model turning on a stand, where it lives, its hit points and damage, what it does,
  and how many you've beaten.

### Octo's house

The townsfolk built Octo a house of his own, right by Octo City's gate: a round blue dome shaped
like his head, with big eye windows that blink, pink cheeks, a door for a mouth, stubby
tentacles round its base and a chimney puffing bubbles. Inside is one cosy room, all in 3D.
Press **Z** next to things to use them:

| Thing | What it does |
|-------|--------------|
| Bed | Sleep till morning: every heart back (Pebble's too) and the game is saved |
| Diary (on the desk) | The story so far and what to do next, and the game is saved |
| Trophy shelf | A cup for each trial won, a bell for each tide bell, a crown for each guardian, and the great bosses' trophies |
| Hat stand | Your hats hang here; use it to try them on |
| Kelp tea | Two hearts back (the pot needs a minute to brew again) |
| Pebble's basket | Pebble naps here. Wake him up to play as player two, or put him back to bed |
| Fish tank | Bloop and Blip, who love fish flakes |
| Jellyfish lamp | Switch it on and off |

The **mailbox** outside gets a thank-you letter (with a few pearls) from everyone whose side quest
you finish; its red flag is up when there's new mail. Once you've been home, the house is a warp
point (press **T**), and it has its own little music-box tune.

## Score, milestones and the leaderboard

Everything earns points: beating creatures (more in tougher regions), pearls, keys, trials,
guardians, temple bosses, Tide Bells, new forms and fusions, heart shells, new regions, meeting
townsfolk, trades and side quests. A Deep Tide run scores 1.5×. Your score shows under the
minimap, with a bar filling up towards the next milestone. Each milestone unlocks something new:

| Points  | Unlock            | What it does |
|---------|-------------------|--------------|
| 1,000   | Quest Compass     | Your map and minimap mark where your side quests lead |
| 2,500   | Turbo Fins        | Swim 12% faster in every form |
| 5,000   | Octo Express      | Warp (T) to Octo City and Turtle Town |
| 8,000   | Pearl Magnet      | Pearls and hearts drift to you from much farther away |
| 12,000  | 3D Museum         | Every guardian you've beaten, as a 3D statue |
| 16,000  | Gold Card         | 25% off at Hermie's and every town stall |
| 22,000  | Quick Jet         | The ink jet recharges twice as fast |
| 30,000  | Octo Radio        | Listen to any tune in the game |
| 40,000  | Heart of the City | One more heart |
| 55,000  | Treasure Sense    | Your map shows treasure you haven't picked up |
| 75,000  | Mega Ink          | One hit in four lands extra hard |
| 100,000 | Living Legend     | A golden statue of you in Octo City, the Champion Crown and Legend-Gold ink |

**The leaderboard** ranks every run you've played against the townsfolk's best scores (Speedy,
Inky, Mayor Octavia, Elder Tortuga, Old Shelly... and the Great Kraken at 120,000). Pass your first
milestone and you'll be asked for your name. Tally, by the scoreboard in Octo City's plaza, shows
the board too. It's kept apart from your saved games (`leaderboard.json` on a computer, the
browser's storage on the web), so new runs join the same board.

Saves from before scores existed are scored for the progress they've already made when you load them.

## Code map (`octo/`)

* `settings.py`: screen size, speeds
* `world.py`: the whole map as ASCII (sea, trial rooms and sky), spawns, arenas, trials, regions and themes, the `Level` class, and a validator that checks everything can be reached
* `base_level.py`: the hand-made map rows. `tools/gen_worlds.py` grows them into the four worlds (`level_data.py`, `worlds_data.py`)
* `temples.py`: builds the six deep temples (room tree, locks and keys, barriers, guardians) from fixed seeds
* `entities.py`: Player (forms, jet, bombs), enemies and bosses, NPCs, projectiles, pickups, effects
* `gfx.py`: every sprite, themed tileset and the bitmap font, drawn in code
* `sound.py`: chiptune synth for the sound effects (cached to `.sound_cache.pkl`), and playing the music with fades from tune to tune
* `tunes.py`: every tune's notes, and the arranger and synthesiser that turn each into a long piece (drums, harmony, bridge, echo) in plain Python
* `voxel.py`: Octo (and any sprite) as a pixel-style 3D figure made of little cubes, with cached renders
* `props3d.py`: the 3D buildings, pyramid, statues, gates and portals, and what stands where
* `scene3d.py`: the 3D layer of the world (drawn in depth order with Octo) and the portal animation
* `attacks3d.py`: every attack in 3D: shots, slaps, rings, beams, bolts, whirlpools, bombs and sparks
* `transition3d.py`: diving from one scene into the next (the opening into the title, the title into the game)
* `hifi.py`: the smooth 3D toolkit for the cinematics: shaded sphere impostors, glows and 3D text
* `cinema.py`: the 3D scenes: the opening (and its smooth dawn sea), the versus entrance, town fly-overs and the milestone medal
* `cities.py`, `townart.py`: the two towns' maps (and the room inside Octo's house) and their pixel art
* `home.py`, `home3d.py`: Octo's house: using the bed, diary, trophies, basket and mailbox, and its 3D models
* `folk.py`: who lives in the towns, their shops and side quests, and the leaderboard rivals
* `town.py`: talking, trading, side quests, the journal, the score, milestones, the leaderboard, the museum and the radio
* `people.py`: the townsfolk and the Living Legend statue
* `score.py`: points, milestones and the leaderboard file
* `coop.py`: player two, Pebble the snail (keys, gamepads, slime, shell spin)
* `beasts.py`: the bestiary's entries, built from the game's creature data
* `hud3d.py`: the 3D top of the screen
* `game.py`: state machine, trials, shop, save/load, warping, HUD and drawing

Desktop saves go to `savegame_<version>.json` in the project folder (one per version). Browser saves stay in that browser.
