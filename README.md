# Legend of Octo

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

Pushing to `main` on GitHub runs `.github/workflows/pages.yml`, which builds the web version and
publishes it to GitHub Pages. In the repo, set **Settings → Pages → Source** to **GitHub Actions**.
In the browser, saves go to the browser's local storage instead of `savegame.json`.

## Controls

| Key                | Action                                              |
|--------------------|-----------------------------------------------------|
| Arrows / WASD      | Move                                                |
| Z / Space          | Attack (depends on form) · talk · buy in the shop   |
| X / Right Shift    | Next form                                           |
| 1-9                | Jump straight to a form                             |
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

Octo starts with two forms. Each trial unlocks another.

| Form    | Z does                                                     | From                      |
|---------|------------------------------------------------------------|---------------------------|
| Happy   | Ink, aimed at the nearest enemy (line or burst)            | start                     |
| Grumpy  | Tentacle slap; cuts kelp, swats shots                      | start                     |
| Zappy   | Shock ring that hits everything nearby; shatters ice walls | Trial of Storms           |
| Chilly  | Ice shard that freezes enemies; cools lava into rock       | Trial of Currents         |
| Spooky  | Two homing wisps that fly through walls; walks through ghost walls | Trial of Shadows  |
| Bubbly  | Bubble shield: a few seconds of no damage                  | Trial of Frost            |
| Spiky   | Spines in all eight directions                             | Trial of Embers           |
| Glowy   | Flash that stuns the whole screen; lights up dark places   | Trial of Echoes           |
| Airy    | Fog cloak: for 5 seconds enemies can't see you and attack the spot where you vanished | Trial of Winds |

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

Desktop saves go to `savegame.json` in the project folder. Browser saves stay in that browser.
