# Legend of Octo

By Minu Hong.

## ▶ [Play it in your browser](https://tmhon6.github.io/legend_of_octo/)

No download needed. Wait about 15 seconds for it to load, click or tap the page, then press Enter or tap again.
Works with a keyboard on a computer, or with on-screen touch controls on phones and tablets.
On a phone, play sideways: the controls sit on both sides of the game, and your first tap goes full
screen (the FULL / EXIT button toggles it). Put your thumb anywhere on the left half and drag to
swim (any angle; push further to go faster). On an iPhone, use Share → Add to Home Screen to play full screen.

A top-down undersea adventure starring Octo, the reversible octopus. It's a fan tribute to the
1st-gen 2D action-adventure style, built in pygame.

## Run

    python3 -m venv .venv          # first time only
    .venv/bin/pip install pygame   # first time only
    .venv/bin/python main.py

On the title screen, **Enter** starts a new game and **L** loads your saved game.

## Play in a browser

The same code also runs in a web browser through [pygbag](https://pypi.org/project/pygbag/)
(Python compiled to WebAssembly). You need `ffmpeg` installed.

    .venv/bin/pip install pygbag            # first time only
    .venv/bin/python build_web.py           # builds build/web/
    .venv/bin/python build_web.py --serve   # builds, then serves it at http://localhost:8000

### Versions

Every git tag like `v1.0.0` is a version. The web page asks which version to play, and each version
keeps its own saved game. The title screen shows the version you're running. To release one:

    git tag -a v1.1.0 -m "Mini-bosses and touch controls"
    git push origin v1.1.0
    gh workflow run pages.yml        # republish the site so the new version appears

`build_site.py` builds every tagged version, plus the newest development build, into `build/site/`.

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
| T                  | Warp to a completed trial portal                    |
| Left Shift         | Save the game                                       |
| P / Enter / Esc    | Pause. In the pause menu: **S** saves, **Q** quits  |
| M                  | World map (game pauses; ←/→ flips between sea and sky) |
| N                  | Mute / unmute all sound (music and effects)         |
| F11                | Fullscreen                                          |

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

### The Fusion Machine

Next to Hermie's Pearl Shop. For 40 pearls it fuses two forms into a new one with **its own new
attack** (not the two old attacks stuck together) and boosted versions of both parents' strengths.

| Fusion  | Made from        | New attack                                                      |
|---------|------------------|-----------------------------------------------------------------|
| Whippy  | Happy + Grumpy   | Ink Whip: a long tentacle that sweeps a wide arc                |
| Stormy  | Zappy + Chilly   | Hail: hailstones crash down on up to six enemies and freeze them |
| Sparky  | Zappy + Airy     | Chain Bolt: lightning that jumps between up to five enemies     |
| Quaky   | Grumpy + Spiky   | Quake: shockwaves run out four ways and crack rock              |
| Prickly | Bubbly + Spiky   | Spike Roll: roll through enemies as an untouchable spiky ball   |
| Wispy   | Spooky + Glowy   | Lantern: a spirit lantern circles you, burning what it touches  |
| Breezy  | Happy + Airy     | Whirlpool: drags enemies in and churns them up                  |
| Frosty  | Chilly + Bubbly  | Frost Trap: a bubble traps an enemy, then pops for big damage   |

Jellies ignore ink, and slapping an urchin hurts *you*.

## The journey

Grimfin the Shark stole the Golden Pearl. Beat Grimfin in the Sunken Shrine and you only get
**half** of it. Murk, Grimfin's big sister, has the other half in her palace in the dark
Sunken City to the far southeast. Bring both halves together to win.

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
Completed portals become warp points (press **T**).

**Hermie's Pearl Shop**, just west of the temple, sells shrimp platters, bubble bombs, swift fins,
a shell shield, deep ink and a heart shell. Bubble bombs blast open cracked rock and hidden caches.

## Code map (`octo/`)

* `settings.py`: screen size, speeds
* `world.py`: the whole map as ASCII (sea, trial rooms and sky), spawns, arenas, trials, regions and themes, the `Level` class, and a validator that checks everything can be reached
* `entities.py`: Player (forms, jet, bombs), enemies and bosses, NPCs, projectiles, pickups, effects
* `gfx.py`: every sprite, themed tileset and the bitmap font, drawn in code
* `sound.py`: chiptune synth for SFX and music (cached to `.sound_cache.pkl`)
* `game.py`: state machine, trials, shop, save/load, warping, HUD and drawing

Desktop saves go to `savegame_<version>.json` in the project folder (one per version). Browser saves stay in that browser.
