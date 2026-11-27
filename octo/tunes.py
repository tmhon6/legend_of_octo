"""Legend of Octo's music: every tune's notes, and a small arranger and synthesiser that turn each
tune into a longer piece that keeps changing as it plays.

Each tune is written as 64 steps of melody and bass (some with an arpeggio too). The arranger plays
it through several times, differently each time:

  A1  a light first verse: the melody, the bass and a soft beat
  A2  the full band: a harmony line under the melody, a sparkling counter-line, the whole drum
      groove, with fills at the ends of phrases
  B   a bridge in a new key (up a fourth): the melody on a music-box bell over held bass notes and
      soft chords while the drums drop to half time, then build back up with a snare roll
  A3  the big last verse: the melody doubled an octave up, harmony, chords, more fills, and a
      turnaround fill that leads back to the start

Slow tunes skip A2. Calm places get gentle percussion or none, fights get driving drums, Turtle
Town a calypso beat, Octo City and the Kelp Woods a swing.

The synthesiser uses band-limited oscillators (no harsh fizz), soft envelopes, echo, warm pads and a
small drum kit, all in plain Python: each note's waveform is made once and repeated, and the mixing
is done with C-speed map() calls, so a whole tune takes about a second.

sound.py renders a tune on the desktop the first time it's needed; build_web.py (through
sound.export_ogg) renders them all to .ogg files for the browser, which only plays them."""
import math
import random
import sys
from array import array
from itertools import repeat
from operator import add, mul

SR = 22050
H = 0                       # in a score: hold the note (None rests)
TAIL = 3.0                  # seconds of echo and ringing that wrap round to the start of the loop
CYCLE = 1500                # about this many samples of each waveform are made, then repeated

SCORES = {}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tune(name, mel, bass, step, wave='square', duty=0.25, vol=0.22, bass_vol=0.3, arp=None, style='groove'):
    SCORES[name] = dict(mel=mel, bass=bass, step=step, wave=wave, duty=duty, vol=vol, bass_vol=bass_vol,
                        arp=arp, style=style)


def _bass(roots, pattern):
    """roots: 16 bass notes, one per bar of 4 steps; pattern: offsets per step (None = hold)."""
    out = []
    for r in roots:
        out += [0 if o is None else r + o for o in pattern]
    return out


# ---- the score ----------------------------------------------------------------------------------

def _score():
    mel = [62, H, 65, 69, 67, H, 65, 64, 62, H, 60, H, 57, H, H, H,
           60, H, 64, 67, 65, H, 64, 62, 64, H, 65, 67, 69, H, H, H,
           62, H, 65, 69, 72, H, 71, 69, 67, H, 69, 65, 64, H, 60, H,
           62, 64, 65, 67, 69, H, 67, 64, 62, H, H, H, None, None, 61, H]
    bass = []
    for root in (38, 38, 45, 45, 36, 36, 43, 43, 38, 38, 41, 41, 45, 45, 38, 38):
        bass += [root, H, root + 12, H]
    tune('reef', mel, bass, 0.2)

    mel = [57, H, H, 60, 59, H, 57, H, 56, H, H, H, None, None, 52, H,
           57, H, H, 60, 64, H, 63, H, 62, H, H, H, None, None, None, None,
           65, H, 64, H, 62, H, 60, H, 59, H, 60, 62, 59, H, 56, H,
           57, H, 59, H, 60, H, 56, H, 57, H, H, H, None, None, None, None]
    bass = []
    for root in (33, 33, 32, 32, 33, 33, 30, 30, 29, 29, 28, 28, 33, 32, 33, 33):
        bass += [root, H, H, root + 7]
    tune('shrine', mel, bass, 0.26, duty=0.5, vol=0.16, style='eerie')

    mel = [60, 64, 67, 72, H, H, 71, 72, 74, H, 76, H, H, H, None, None]
    bass = [36, H, 43, H, 48, H, 43, H, 41, H, 43, H, 36, H, H, H]
    tune('victory', mel, bass, 0.14, vol=0.25, style='jingle')

    mel = [69, 72, 76, 72, 69, 72, 76, 72, 68, 71, 76, 71, 68, 71, 76, 71,
           67, 70, 74, 70, 67, 70, 74, 70, 68, 71, 74, 76, 77, 76, 74, 71,
           69, 72, 76, 81, 80, 76, 72, 69, 70, 74, 77, 82, 81, 77, 74, 70,
           69, 72, 76, 72, 68, 71, 76, 71, 69, H, 81, H, 80, H, 76, H]
    bass = []
    for root in (45, 45, 44, 44, 43, 43, 44, 44, 45, 45, 46, 46, 45, 44, 45, 45):
        bass += [root, root + 12, root, root + 12]
    tune('trial', mel, bass, 0.11, vol=0.15, bass_vol=0.32, style='drive')

    # the title screen: a bright, bouncy theme in F major
    mel = [65, H, 69, 72, 77, H, 76, 74, 72, H, 69, H, 70, 72, 74, H,
           72, H, 69, 65, 67, H, 69, 70, 69, H, H, H, None, None, 72, 74,
           77, H, 76, 74, 72, H, 74, 76, 77, H, 81, H, 79, 77, 76, H,
           74, H, 72, 70, 69, H, 67, H, 65, H, H, H, None, None, None, None]
    bass = []
    for root in (41, 41, 46, 46, 41, 41, 36, 36, 41, 41, 46, 46, 38, 36, 41, 41):
        bass += [root, H, root + 7, root + 12]
    arp = []
    for root in (65, 65, 70, 70, 65, 65, 60, 60, 65, 65, 70, 70, 62, 60, 65, 65):
        arp += [root + 12, root + 16, root + 19, root + 16]
    tune('title', mel, bass, 0.15, vol=0.2, arp=arp)

    mel = [76, H, 79, H, 83, H, 81, 79, 76, H, H, H, 74, H, 76, H,
           72, H, 76, H, 79, H, 78, 76, 74, H, H, H, None, None, 71, H,
           76, H, 79, H, 84, H, 83, 81, 79, H, 81, H, 83, H, 79, H,
           81, H, 79, 76, 74, H, 72, H, 71, H, H, H, None, None, None, None]
    bass = []
    for root in (40, 40, 36, 36, 43, 43, 38, 38, 40, 40, 36, 36, 45, 43, 40, 40):
        bass += [root, H, H, root + 7]
    arp = []
    for root in (64, 64, 60, 60, 67, 67, 62, 62, 64, 64, 60, 60, 69, 67, 64, 64):
        arp += [root + 12, root + 19, root + 24, root + 19]
    tune('frost', mel, bass, 0.2, wave='tri', duty=0.5, vol=0.3, bass_vol=0.22, arp=arp, style='calm')

    mel = [57, H, 60, 57, 63, H, 62, H, 60, H, 57, H, 56, H, H, H,
           57, H, 60, 57, 63, H, 65, H, 63, 62, 60, H, 62, H, H, H,
           69, H, 68, H, 65, H, 63, H, 62, H, 60, H, 63, H, 62, H,
           60, H, 57, H, 56, H, 57, H, 57, H, H, H, None, None, None, None]
    bass = []
    for root in (33, 33, 33, 32, 33, 33, 35, 35, 38, 38, 36, 36, 33, 32, 33, 33):
        bass += [root, root, H, root + 12]
    tune('vents', mel, bass, 0.14, wave='saw', duty=0.5, vol=0.13, bass_vol=0.34, style='drive')

    mel = [64, H, H, H, 67, H, 66, H, 64, H, H, H, None, None, 59, H,
           60, H, H, H, 64, H, 63, H, 59, H, H, H, None, None, None, None,
           64, H, 67, H, 71, H, 70, H, 67, H, 66, H, 64, H, 63, H,
           64, H, H, H, 59, H, H, H, 64, H, H, H, None, None, None, None]
    bass = []
    for root in (40, 40, 36, 36, 35, 35, 40, 40, 40, 40, 43, 43, 36, 35, 40, 40):
        bass += [root, H, H, H]
    tune('city', mel, bass, 0.3, wave='sine', duty=0.5, vol=0.3, bass_vol=0.3, style='eerie')

    mel = [72, H, 76, H, 79, H, 84, H, 83, H, 79, H, 76, H, 77, 79,
           81, H, 79, H, 77, H, 76, H, 74, H, H, H, None, None, 71, 74,
           72, H, 76, H, 79, H, 84, H, 86, H, 84, H, 83, H, 81, H,
           79, H, 77, 76, 74, H, 76, 74, 72, H, H, H, None, None, None, None]
    bass = []
    for root in (48, 48, 53, 53, 48, 48, 55, 55, 48, 48, 53, 53, 50, 55, 48, 48):
        bass += [root, H, root + 7, H]
    arp = []
    for root in (72, 72, 77, 77, 72, 72, 79, 79, 72, 72, 77, 77, 74, 79, 72, 72):
        arp += [root, root + 4, root + 7, root + 12]
    tune('sky', mel, bass, 0.17, wave='tri', duty=0.5, vol=0.32, bass_vol=0.25, arp=arp)

    # the Kelp Woods: a sneaky, swaying tune in D dorian
    mel = [62, H, 64, 65, 69, H, 67, H, 65, 64, 62, H, 60, H, 62, H,
           65, H, 67, 69, 71, H, 69, H, 67, 65, 64, H, None, None, 62, 64,
           65, H, 64, 62, 60, H, 62, 64, 57, H, H, H, 60, H, 62, H,
           64, H, 65, 64, 62, H, 60, H, 62, H, H, H, None, None, None, None]
    bass = _bass((38, 38, 36, 36, 43, 43, 41, 40, 38, 38, 36, 36, 33, 36, 38, 38), (0, None, 7, 12))
    tune('kelp', mel, bass, 0.19, wave='tri', duty=0.5, vol=0.3, bass_vol=0.26, style='swing')

    # the Coral Gardens: a sunny, skipping tune in G major
    mel = [67, 71, 74, H, 76, 74, 71, H, 72, 71, 69, H, 67, H, H, H,
           69, 72, 76, H, 79, 76, 72, H, 74, 72, 71, H, 69, H, H, H,
           71, 74, 79, H, 78, 76, 74, H, 76, 74, 72, H, 71, 69, 67, H,
           69, H, 71, 72, 74, H, 66, H, 67, H, H, H, None, None, None, None]
    bass = _bass((43, 43, 48, 48, 45, 45, 50, 50, 43, 43, 48, 48, 45, 50, 43, 43), (0, 7, 12, 7))
    arp = []
    for r in (67, 67, 72, 72, 69, 69, 74, 74, 67, 67, 72, 72, 69, 74, 67, 67):
        arp += [r + 12, r + 16, r + 19, r + 24]
    tune('garden', mel, bass, 0.15, vol=0.2, bass_vol=0.26, arp=arp)

    # the Lagoon: lazy, warm and sunlit, on the pentatonic scale
    mel = [72, H, H, 74, 76, H, 79, H, 76, H, 74, H, 72, H, H, H,
           69, H, H, 72, 74, H, 76, H, 74, H, 72, H, 69, H, H, H,
           72, H, 76, H, 79, H, 81, H, 79, H, 76, H, 74, H, 76, H,
           72, H, H, H, 69, H, 67, H, 72, H, H, H, None, None, None, None]
    bass = _bass((48, 48, 45, 45, 41, 41, 43, 43, 48, 48, 45, 45, 41, 43, 48, 48), (0, None, 7, None))
    tune('lagoon', mel, bass, 0.23, wave='sine', duty=0.5, vol=0.34, bass_vol=0.26, style='calm')

    # the Abyss: slow, deep and lonely
    mel = [57, H, H, H, None, None, 60, H, 59, H, H, H, None, None, None, None,
           55, H, H, H, None, None, 57, H, 52, H, H, H, None, None, None, None,
           57, H, 60, H, 64, H, H, H, 63, H, H, H, 60, H, H, H,
           59, H, H, H, 56, H, H, H, 57, H, H, H, None, None, None, None]
    bass = _bass((33, 33, 31, 31, 29, 29, 28, 28, 33, 33, 36, 36, 29, 28, 33, 33), (0, None, None, None))
    tune('abyss', mel, bass, 0.34, wave='sine', duty=0.5, vol=0.3, bass_vol=0.34, style='ambient')

    # Octo City: a bouncy, jazzy stroll through the plaza in F major
    mel = [65, H, 69, 72, 74, H, 72, 69, 70, H, 69, 67, 65, H, H, H,
           67, H, 70, 74, 77, H, 74, 70, 72, H, 70, 69, 67, H, H, H,
           69, 72, 77, H, 76, 74, 72, H, 74, 72, 70, H, 69, 67, 65, H,
           67, H, 69, 70, 72, H, 64, H, 65, H, H, H, None, None, 72, 74]
    bass = _bass((41, 41, 46, 46, 43, 43, 48, 48, 45, 45, 46, 46, 43, 48, 41, 41), (0, 12, 7, 12))
    arp = []
    for r in (65, 65, 70, 70, 67, 67, 72, 72, 69, 69, 70, 70, 67, 72, 65, 65):
        arp += [r + 12, r + 16, r + 19, r + 16]
    tune('octocity', mel, bass, 0.14, vol=0.22, bass_vol=0.28, arp=arp, style='swing')

    # Octo's house: a cosy little music-box lullaby in G major
    mel = [79, H, 74, H, 71, H, 74, H, 76, H, 74, H, 72, H, H, H,
           71, H, 74, H, 79, H, 78, H, 76, H, H, H, 74, H, H, H,
           76, H, 79, H, 83, H, 81, H, 79, H, 76, H, 74, H, 72, H,
           71, H, 72, H, 74, H, 66, H, 67, H, H, H, None, None, None, None]
    bass = _bass((43, 43, 40, 40, 36, 36, 38, 38, 40, 40, 36, 36, 38, 38, 43, 43), (0, None, 7, None))
    arp = []
    for r in (67, 67, 64, 64, 60, 60, 62, 62, 64, 64, 60, 60, 62, 62, 67, 67):
        arp += [r + 12, r + 19, r + 16, r + 19]
    tune('home', mel, bass, 0.2, wave='tri', duty=0.5, vol=0.28, bass_vol=0.18, arp=arp, style='lullaby')

    # Turtle Town: a slow, sunny calypso by the sea in C major
    mel = [72, H, 76, H, 79, 76, H, 74, 72, H, 69, H, 67, H, H, H,
           69, H, 72, H, 76, 74, H, 72, 74, H, 76, H, 74, H, H, H,
           72, H, 76, H, 79, H, 81, 79, 77, H, 76, H, 74, H, 72, H,
           74, H, 72, 69, 67, H, 71, H, 72, H, H, H, None, None, None, None]
    bass = _bass((48, 48, 41, 41, 43, 43, 48, 48, 45, 45, 41, 41, 43, 43, 48, 48), (0, None, 7, 5))
    tune('turtletown', mel, bass, 0.2, wave='tri', duty=0.5, vol=0.32, bass_vol=0.27, style='calypso')

    # the Ship Graveyard: a creaky old sea shanty in D minor
    mel = [62, H, 62, 65, H, 62, 69, H, 67, 65, H, 64, 62, H, H, H,
           60, H, 60, 64, H, 60, 67, H, 65, 64, H, 62, 60, H, H, H,
           62, H, 62, 65, H, 69, 74, H, 72, 70, H, 69, 67, H, 65, H,
           64, H, 62, 61, H, 64, 62, H, H, H, None, None, None, None, None, None]
    bass = _bass((38, 38, 36, 36, 34, 34, 33, 33, 38, 38, 34, 34, 33, 33, 38, 38), (0, None, 7, None))
    tune('wreck', mel, bass, 0.15, wave='saw', duty=0.5, vol=0.12, bass_vol=0.32, style='march')

    # the Murk Palace: cold, creeping and chromatic
    mel = [59, H, 62, H, 61, H, 58, H, 59, H, H, H, None, None, 54, H,
           59, H, 62, H, 66, H, 65, H, 62, H, H, H, None, None, None, None,
           67, H, 66, H, 65, H, 62, H, 61, H, 62, H, 58, H, 59, H,
           54, H, 55, H, 58, H, 61, H, 59, H, H, H, None, None, None, None]
    bass = _bass((35, 35, 34, 34, 35, 35, 31, 31, 35, 35, 34, 34, 31, 30, 35, 35), (0, 0, 6, 0))
    tune('palace', mel, bass, 0.21, duty=0.5, vol=0.14, bass_vol=0.34, style='eerie')

    # the deep temples: a steady, echoing march in A minor
    mel = [69, H, 72, 71, 69, H, 64, H, 65, H, 64, 62, 64, H, H, H,
           69, H, 72, 71, 69, H, 76, H, 74, H, 72, 71, 72, H, H, H,
           77, H, 76, 74, 72, H, 71, H, 72, H, 71, 69, 68, H, 64, H,
           69, H, 71, H, 72, H, 68, H, 69, H, H, H, None, None, None, None]
    bass = _bass((45, 45, 41, 41, 45, 45, 43, 43, 41, 41, 45, 45, 40, 40, 45, 45), (0, 12, 0, 12))
    arp = []
    for r in (69, 69, 65, 65, 69, 69, 67, 67, 65, 65, 69, 69, 64, 64, 69, 69):
        arp += [r + 12, r + 15, r + 19, r + 15]
    tune('temple', mel, bass, 0.14, vol=0.17, bass_vol=0.3, arp=arp, style='march')

    # guardian fights: fast and fierce in E minor
    mel = [64, 64, 67, 64, 70, H, 69, 67, 64, 64, 67, 64, 71, H, 70, 69,
           64, 64, 67, 64, 72, H, 71, 70, 69, 67, 66, 67, 64, H, H, H,
           76, H, 74, H, 72, H, 71, H, 72, H, 71, H, 70, H, 67, H,
           64, 66, 67, 69, 70, 69, 67, 66, 64, H, 76, H, 75, H, 64, H]
    bass = _bass((40, 40, 40, 40, 43, 43, 41, 41, 36, 36, 38, 38, 40, 39, 40, 40), (0, 12, 0, 12))
    tune('boss', mel, bass, 0.1, wave='saw', duty=0.5, vol=0.12, bass_vol=0.34, style='drive')

    for theme, spec in REGION_TUNES.items():
        _compose('r_' + theme, *spec)


# ---- tunes for the newer regions, written by a little composer ------------------------------------
SCALES = {'major': (0, 2, 4, 5, 7, 9, 11), 'minor': (0, 2, 3, 5, 7, 8, 10), 'dorian': (0, 2, 3, 5, 7, 9, 10),
          'mixo': (0, 2, 4, 5, 7, 9, 10), 'phryg': (0, 1, 3, 5, 7, 8, 10), 'penta': (0, 2, 4, 7, 9, 12, 14),
          'lydian': (0, 2, 4, 6, 7, 9, 11)}
PROGRESSIONS = {'major': (0, 5, 3, 4), 'minor': (0, 5, 3, 6), 'dorian': (0, 3, 0, 4), 'mixo': (0, 6, 3, 0),
                'phryg': (0, 1, 0, 6), 'penta': (0, 3, 4, 0), 'lydian': (0, 1, 4, 0)}
# theme: (key root, scale, step length, melody wave, arpeggio?, seed, style)
REGION_TUNES = {
    'glass': (64, 'lydian', 0.17, 'tri', True, 11, 'groove'), 'siren': (62, 'dorian', 0.2, 'sine', False, 12, 'calm'),
    'whale': (50, 'phryg', 0.32, 'sine', False, 13, 'ambient'),
    'thunder': (57, 'minor', 0.12, 'saw', False, 14, 'drive'),
    'rainbow': (67, 'major', 0.15, 'square', True, 15, 'groove'),
    'starfall': (62, 'lydian', 0.24, 'tri', True, 16, 'calm'),
    'beach': (65, 'major', 0.16, 'square', True, 17, 'calypso'),
    'meadow': (67, 'penta', 0.18, 'tri', False, 18, 'groove'),
    'jungle': (60, 'mixo', 0.13, 'square', False, 19, 'calypso'),
    'desert': (57, 'phryg', 0.17, 'saw', False, 20, 'march'),
    'volcano': (52, 'minor', 0.12, 'saw', False, 21, 'drive'),
    'crystal': (69, 'lydian', 0.22, 'sine', True, 22, 'calm'),
    'fungus': (60, 'dorian', 0.2, 'tri', False, 23, 'swing'),
    'bone': (52, 'phryg', 0.28, 'square', False, 24, 'eerie'),
    'ruins': (57, 'dorian', 0.26, 'sine', False, 25, 'ambient'),
    'magma': (50, 'phryg', 0.11, 'saw', False, 26, 'drive'),
}


def _compose(name, root, scale, step, wave, arp, seed, style):
    """Four phrases (A A' B A'') over a four-chord loop; the melody walks the scale and lands home."""
    rnd = random.Random(seed)
    sc = SCALES[scale]
    prog = PROGRESSIONS[scale]

    def note(deg):
        octave, i = divmod(deg, len(sc))
        return root + sc[i] + 12 * octave

    def motif(start):
        out, d = [], start
        for i in range(8):
            if i in (3, 7) and rnd.random() < 0.6:
                out.append(0)                     # hold
                continue
            if rnd.random() < 0.12:
                out.append(None)                  # rest
                continue
            d += rnd.choice((-2, -1, -1, 1, 1, 2, 0, 3))
            d = max(-3, min(9, d))
            out.append(note(d))
        return out, d
    a1, end = motif(2)
    a2, _ = motif(end)
    b1, _ = motif(4)
    b2, _ = motif(5)
    a_var = a1[:4] + [note(rnd.choice((1, 3, 4))) if x not in (0, None) else x for x in a2[4:]]
    ending = a1[:4] + [note(2), note(1), note(0), 0]
    mel = a1 + a2 + a_var + a2 + b1 + b2 + a1 + ending
    bass, arps = [], []
    for bar in range(16):
        chord = prog[bar % 4] if bar < 15 else 0
        r = root - 24 + sc[chord % len(sc)]
        bass += [r, 0, r + 7, 0] if step > 0.2 else [r, r + 12, r, r + 12]
        third = sc[(chord + 2) % len(sc)] - sc[chord % len(sc)]
        third += 12 if third < 0 else 0
        arps += [r + 24, r + 24 + third, r + 31, r + 24 + third]
    vol = {'saw': 0.12, 'square': 0.16, 'tri': 0.3, 'sine': 0.32}[wave]
    tune(name, mel, bass, step, wave=wave, duty=0.25 if wave == 'square' else 0.5, vol=vol, bass_vol=0.28,
         arp=arps if arp else None, style=style)



# ---- the synthesiser ----------------------------------------------------------------------------
# Pure Python, kept quick: a waveform is made once as a short seamless cycle and repeated (a memory
# copy), each different note is made once (tunes repeat a lot), each voice copies its notes into a
# lane of its own (notes in one voice barely overlap), and whole lanes are then summed, echoed and
# scaled as big whole numbers, one C-speed step each.
_cycles, _decays, _ramps, _envs, _bells, _kits, _curves, _onesc = {}, {}, {}, {}, {}, {}, {}, {}


def _blep(t, dt):
    """PolyBLEP: smooths a waveform's jump so it doesn't alias into a fizz."""
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    if t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


def _tri(p):
    q = (p + 0.25) % 1.0                            # (starts at zero)
    return 4 * q - 1 if q < 0.5 else 3 - 4 * q


def _cycle(wave, f, duty, sr):
    """A whole number of cycles of a waveform, about CYCLE samples long, that repeats seamlessly.
    'chord5' is a soft root + fifth + octave in one wave (a pure fifth), 'chord8' root + octave."""
    key = (wave, round(f, 4), duty, sr)
    c = _cycles.get(key)
    if c is None:
        base = f / 2 if wave == 'chord5' else f
        period = sr / base
        k = max(1, round(CYCLE / period))
        n = max(2, round(k * period))
        dt = k / n                                  # cycles of the base per sample
        out = []
        for i in range(n):
            p = (i * dt) % 1.0
            if wave == 'sine':
                v = math.sin(2 * math.pi * p)
            elif wave == 'tri':
                v = _tri(p)
            elif wave == 'saw':
                v = 2 * p - 1 - _blep(p, dt)
            elif wave == 'chord5':
                v = (_tri(2 * p) + _tri(3 * p) + 0.7 * _tri(4 * p)) / 2.7
            elif wave == 'chord8':
                v = (_tri(p) + 0.7 * _tri(2 * p)) / 1.7
            else:                                   # pulse of the given duty, centred on zero
                v = (1.0 if p < duty else -1.0) + _blep(p, dt) - _blep((p - duty) % 1.0, dt) + 1 - 2 * duty
            out.append(v)
        c = _cycles[key] = array('f', out)
    return c


def _decay(d, s, sr, n):
    key = (d, s, sr)
    cur = _decays.get(key)
    if cur is None or len(cur) < n:
        m = max(n, 4 * sr)
        k = 1.0 / (d * sr)
        cur = _decays[key] = array('f', [s + (1 - s) * math.exp(-i * k) for i in range(m)])
    return cur


def _ramp(n, up=False):
    key = (n, up)
    r = _ramps.get(key)
    if r is None:
        r = _ramps[key] = array('f', [(i + 1) / n if up else 1 - (i + 1) / n for i in range(n)])
    return r


def _envelope(ng, nr, a, d, s, vol, sr):
    """Attack, decay to a sustain level for the note's length, then a short release (times vol)."""
    key = (ng, nr, a, d, s, vol, sr)
    e = _envs.get(key)
    if e is None:
        e = _decay(d, s, sr, ng)[:ng]
        na = min(ng, max(1, int(a * sr)))
        e[:na] = array('f', map(mul, e[:na], _ramp(na, up=True)))
        end = e[-1] if ng else 0.0
        if nr:
            e.extend(map(mul, _ramp(nr), repeat(end)))
        e = _envs[key] = array('f', map(mul, e, repeat(vol)))
    return e


def _curve(rate, amp, n, sr):
    """amp * e^(-rate t), at least n samples long."""
    key = (rate, amp, sr)
    c = _curves.get(key)
    if c is None or len(c) < n:
        c = _curves[key] = array('f', [amp * math.exp(-rate * i / sr) for i in range(n)])
    return c


def _bell(pitch, sr):
    """A music-box bell: a bright strike that rings away by itself."""
    key = (pitch, sr)
    b = _bells.get(key)
    if b is None:
        f = hz(pitch)
        n = int(1.3 * sr)
        b = None
        for ratio, amp, rate in ((1, 1.0, 2.3), (2, 0.22, 5.0), (4, 0.12, 9.0), (7.1, 0.06, 30.0)):
            if f * ratio >= sr * 0.45:
                continue
            m = min(n, int(sr * 6.9 / rate))        # (until it has faded to a thousandth)
            cyc = _cycle('sine', f * ratio, 0.5, sr)
            part = map(mul, (cyc * (m // len(cyc) + 1))[:m], _curve(rate, amp, m, sr))
            if b is None:
                b = array('f', part)
            else:
                b[:m] = array('f', map(add, b[:m], part))
        na = max(1, int(0.002 * sr))
        b[:na] = array('f', map(mul, b[:na], _ramp(na, up=True)))
        _bells[key] = b
    return b


def _kit(sr):
    """The drum kit, made once."""
    kit = _kits.get(sr)
    if kit:
        return kit
    rnd = random.Random(7)
    kit = _kits[sr] = {}

    def noise_hit(dur, tau, order, gain, attack=0.0):
        n = int(dur * sr)
        a = b = 0.0
        out = []
        na = attack * sr
        for i in range(n):
            x = rnd.uniform(-1, 1)
            v = x - a if order == 1 else (x - 2 * a + b) * 0.5   # differences keep only the highs
            b, a = a, x
            env = math.exp(-i / (tau * sr)) * (min(1.0, i / na) if na else 1.0)
            out.append(v * env * gain)
        return out

    out, ph = [], 0.0
    for i in range(int(0.32 * sr)):
        t = i / sr
        ph += (46 + 118 * math.exp(-t / 0.032)) / sr
        out.append(math.sin(2 * math.pi * ph) * math.exp(-t / 0.14) + rnd.uniform(-1, 1) * 0.25 * math.exp(-t / 0.0015))
    kit['kick'] = out
    body = [math.sin(2 * math.pi * 188 * i / sr) * math.exp(-i / sr / 0.045) * 0.6 for i in range(int(0.22 * sr))]
    kit['snare'] = list(map(add, noise_hit(0.22, 0.07, 1, 0.55), body))
    kit['hat'] = noise_hit(0.07, 0.014, 2, 0.9)
    kit['ohat'] = noise_hit(0.35, 0.09, 2, 0.7)
    kit['crash'] = noise_hit(1.6, 0.45, 2, 0.6)
    kit['shaker'] = noise_hit(0.09, 0.03, 1, 0.6, attack=0.012)
    rim = noise_hit(0.05, 0.005, 1, 0.4)
    kit['rim'] = [v + math.sin(2 * math.pi * 1650 * i / sr) * math.exp(-i / sr / 0.007) * 0.6 for i, v in enumerate(rim)]
    for name, f0 in (('tom1', 200), ('tom2', 150), ('tom3', 110)):
        out, ph = [], 0.0
        for i in range(int(0.3 * sr)):
            t = i / sr
            ph += f0 * (1 + 0.5 * math.exp(-t / 0.02)) / sr
            out.append(math.sin(2 * math.pi * ph) * math.exp(-t / 0.11))
        kit[name] = out
    for k in kit:
        kit[k] = array('f', kit[k])
    return kit


DRUM_VOL = {'kick': 0.5, 'snare': 0.3, 'hat': 0.1, 'ohat': 0.07, 'crash': 0.12, 'shaker': 0.09, 'rim': 0.13,
            'tom1': 0.28, 'tom2': 0.28, 'tom3': 0.3}


ONE = 1 << 20                           # a sample of 1.0, in the lanes' whole numbers
assert sys.byteorder == 'little'        # (the lanes are read as little-endian whole numbers)


class _Lane:
    """One voice's samples, as 64-bit whole numbers. Its notes are copied in; only where one note's
    tail meets the next are samples added."""
    __slots__ = ('buf', 'end')

    def __init__(self, n):
        self.buf = array('q', bytes(8 * n))
        self.end = 0

    def put(self, i, x):
        buf = self.buf
        j = min(len(buf), i + len(x))
        if j <= i:
            return
        if j - i < len(x):
            x = x[:j - i]
        if i >= self.end:
            buf[i:j] = x
        else:
            k = min(self.end, j)
            buf[i:k] = array('q', map(add, buf[i:k], x[:k - i]))
            if k < j:
                buf[k:j] = x[k - i:]
        self.end = max(self.end, j)


def _ones(n):
    """A big whole number with a 1 in each of n 64-bit fields."""
    v = _onesc.get(n)
    if v is None:
        v = _onesc[n] = int.from_bytes((1).to_bytes(8, 'little') * n, 'little')
    return v


def _big(buf):
    """A lane as one big whole number, sample k in bits 64k to 64k+63. Whole lanes then add, delay
    (shift) and scale (multiply) in one C-speed step each, instead of sample by sample."""
    v = int.from_bytes(buf.tobytes(), 'little')
    return v - (((v >> 63) & _ones(len(buf))) << 64)     # (negative samples borrowed from the next field)


def _finish(v, bias, n, rms_target):
    """v holds n samples, each x * ONE * 2^16 + bias. Bring the tune to a steady loudness (keeping
    every peak in range) and make 16-bit samples: scaled and offset so that each sample's 16 bits
    land in bits 32-47 of its field, then read straight out."""
    unit = ONE << 16
    digits = array('q')
    digits.frombytes(v.to_bytes(8 * n, 'little'))
    hi = lo = bias
    for i in range(0, n, 32768):                      # (in pieces, so a game running alongside never waits long)
        piece = digits[i:i + 32768]
        hi, lo = max(hi, max(piece)), min(lo, min(piece))
    peak = max(hi - bias, bias - lo) / unit or 1.0
    sub = digits[::7]
    rms = math.sqrt(math.fsum(((x - bias) / unit) ** 2 for x in sub) / max(1, len(sub))) or 1.0
    g = min(rms_target / rms, 0.93 / peak) * 32767          # output steps per 1.0
    a = max(1, round(g * (1 << 32) / unit))
    out = array('h')
    out.frombytes((v * a + ((1 << 48) + (1 << 31) - a * bias) * _ones(n)).to_bytes(8 * n, 'little'))
    return out[2::4]


# ---- the arranger -------------------------------------------------------------------------------
X = {'X': 1.0, 'x': 0.75, 'o': 0.45}
# a measure of 16 sixteenth notes per drum: X accent, x normal, o soft
KITS = {
    'groove': {'light': {'kick': 'x.......x.......', 'hat': '..o...o...o...o.'},
               'full': {'kick': 'x.......x.x.....', 'snare': '....x.......x...', 'hat': 'x.o.x.o.x.o.x.o.',
                        'ohat': '..............o.'},
               'half': {'kick': 'x...............', 'snare': '........o.......', 'hat': 'o...o...o...o...'},
               'build': {'kick': 'x.......x.......', 'hat': 'o.o.o.o.o.o.o.o.', 'snare': '............o...'}},
    'drive': {'light': {'kick': 'x...x...x...x...', 'hat': '..o...o...o...o.'},
              'full': {'kick': 'X...x...X...x.x.', 'snare': '....X.......X...', 'hat': 'xoxoxoxoxoxoxoxo'},
              'half': {'kick': 'x.......x.......', 'snare': '........x.......', 'hat': 'o.o.o.o.o.o.o.o.'},
              'build': {'kick': 'x...x...x...x...', 'hat': 'x.x.x.x.x.x.x.x.', 'snare': '....o.......o...'}},
    'swing': {'light': {'kick': 'x.......x.......', 'hat': 'o...o.o.o...o.o.'},
              'full': {'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': 'x...x.o.x...x.o.',
                       'rim': '..............o.'},
              'half': {'kick': 'x...............', 'hat': 'o...o...o...o...'},
              'build': {'kick': 'x.......x.......', 'hat': 'x...x.o.x...x.o.', 'snare': '............o...'}},
    'calypso': {'light': {'shaker': 'o.o.o.o.o.o.o.o.', 'rim': '...x..x.....x...'},
                'full': {'kick': 'x..x....x..x....', 'rim': '...x..x....x..x.', 'shaker': 'xoxoxoxoxoxoxoxo',
                         'ohat': '..o.......o.....'},
                'half': {'shaker': 'o...o...o...o...', 'rim': '...o..o.........'},
                'build': {'kick': 'x.......x.......', 'shaker': 'xoxoxoxoxoxoxoxo'}},
    'march': {'light': {'kick': 'x.......x.......', 'snare': '....o.......o.oo'},
              'full': {'kick': 'x...x...x...x...', 'snare': '..o.x.o...o.x.xx', 'hat': 'o...o...o...o...'},
              'half': {'kick': 'x.......x.......', 'snare': '............o...'},
              'build': {'kick': 'x...x...x...x...', 'snare': 'o.o.o.o.o.o.o.o.'}},
    'calm': {'light': {},
             'full': {'kick': 'o.......o.......', 'shaker': '..o...o...o...o.', 'rim': '............o...'},
             'half': {'shaker': '..o.......o.....'},
             'build': {'shaker': 'o.o.o.o.o.o.o.o.', 'kick': 'o.......o.......'}},
    'eerie': {'light': {}, 'full': {'kick': 'o...............', 'rim': '..........o.....'}, 'half': {},
              'build': {'kick': 'o.......o.......'}},
    'quiet': {'light': {}, 'full': {}, 'half': {}, 'build': {}},
}
KIT_OF = {'groove': 'groove', 'drive': 'drive', 'swing': 'swing', 'calypso': 'calypso', 'march': 'march',
          'calm': 'calm', 'eerie': 'eerie', 'ambient': 'eerie', 'lullaby': 'quiet'}
LOUD = ('groove', 'drive', 'swing', 'calypso', 'march')
SOFT = ('calm', 'eerie', 'ambient', 'lullaby')
_TOMS = [(8, 'tom1', .8), (10, 'tom1', .7), (11, 'tom2', .7), (12, 'tom2', .8), (13, 'tom3', .7), (14, 'tom3', .85),
         (15, 'snare', 1.0)]
_SNARES = [(12, 'snare', .5), (13, 'snare', .6), (14, 'snare', .75), (15, 'snare', .9)]
FILLS = {'groove': (_SNARES, _TOMS), 'swing': (_SNARES, _TOMS), 'march': (_SNARES, _TOMS),
         'drive': (_SNARES, [(8 + j, 'snare', .4 + .6 * j / 7) for j in range(8)]),
         'calypso': ([(12, 'tom1', .6), (14, 'tom2', .7)],
                     [(8, 'tom1', .7), (9, 'tom1', .5), (10, 'tom2', .7), (12, 'tom2', .6), (13, 'tom3', .7),
                      (14, 'tom3', .8)]),
         'calm': ([], [(12, 'tom3', .4), (14, 'tom2', .45)]), 'eerie': ([], []), 'quiet': ([], [])}
ROLLS = {'calm': [(j, 'shaker', .3 + .7 * j / 15) for j in range(16)], 'eerie': [], 'quiet': []}
_SNARE_ROLL = [(j, 'snare', .25 + .75 * j / 15) for j in range(16)]
LOUDNESS = {'groove': 0.175, 'drive': 0.19, 'swing': 0.17, 'calypso': 0.175, 'march': 0.175, 'calm': 0.15,
            'eerie': 0.14, 'ambient': 0.14, 'lullaby': 0.13, 'jingle': 0.2}
GOOD = (0, 3, 4, 5, 7, 8, 9)            # intervals over the bass that sound sweet
LEAD = 0.17                             # how loud every melody is, before the final levelling
_SETS = [frozenset((r + i) % 12 for i in shape) for shape in
         ((0, 2, 4, 5, 7, 9, 11), (0, 2, 3, 5, 7, 8, 11), (0, 2, 3, 5, 7, 9, 11)) for r in range(12)]
WET = ('lead', 'arp', 'bell', 'bell2')  # these get the echo


def _notes(steps):
    """(first step, length in steps, pitch) for each note in a step list."""
    out, cur = [], None
    for i, n in enumerate(steps):
        if n == 0:
            if cur is not None:
                cur[1] += 1
        elif n is None:
            cur = None
        else:
            cur = [i, 1, n]
            out.append(cur)
    return out


def _key(sc):
    """The seven notes the tune mostly uses (its key), for writing a harmony line."""
    w = [0.0] * 12
    for seq, k in ((sc['mel'], 1.0), (sc['bass'], 0.8), (sc['arp'] or (), 0.5)):
        for n in seq:
            if n:
                w[n % 12] += k
    return max(_SETS, key=lambda s: sum(w[p] for p in s))


def _inst(wave, duty=0.5, a=0.004, d=0.2, s=0.42, r=0.03):
    return (wave, duty, a, d, s, r)


class _Lanes(dict):
    def __init__(self, n):
        super().__init__()
        self.n = n

    def __missing__(self, k):                        # (made when a voice first plays)
        lane = self[k] = _Lane(self.n)
        return lane


class _Arrangement:
    def __init__(self, sc, sr, length=None):
        self.sc, self.sr = sc, sr
        self.step = st = sc['step']
        self.spb = 4 if st < 0.185 else 2            # steps per beat
        self.style = style = sc['style']
        self.kit = KIT_OF.get(style, 'groove')
        self.swing = 0.22 if style == 'swing' else 0.0
        self.plan = ['A1', 'B', 'A3'] if st * 64 > 15.5 else ['A1', 'A2', 'B', 'A3']
        self.sec = 64 * st
        self.loop = int(round((length or self.sec * len(self.plan)) * sr))
        self.n = n = self.loop + int(TAIL * sr)
        self.lanes = _Lanes(n)
        self.made = {}                               # notes already played: they repeat a lot
        self.rnd = random.Random(3)
        self.pcs = _key(sc)
        mel = [n for n in sc['mel'] if n]
        self.mean = sum(mel) / len(mel)
        self.up = 5 if self.mean + 5 <= 77 else -7    # the bridge's new key
        lows = [n for n in sc['bass'] if n]
        self.bass_up = 12 if min(lows) + self.up < 31 else 0
        # the bass sounding at every step, and the root of each 4-step bar
        now, cur = [], None
        for n in sc['bass']:
            cur = None if n is None else (cur if n == 0 else n)
            now.append(cur)
        self.bass_now = now
        self.roots, r = [], lows[0]
        for g in range(len(now) // 4):
            r = now[4 * g] or r
            self.roots.append(r)
        w = sc['wave']
        # every melody comes out about as loud as the others (a saw or a thin pulse is quieter than a
        # full square at the same setting), with the bass kept in proportion, but never far louder
        rms = {'square': 2 * math.sqrt(sc['duty'] * (1 - sc['duty'])), 'saw': 0.577, 'tri': 0.577}.get(w, 0.707)
        k = LEAD / (sc['vol'] * rms)
        self.vol = sc['vol'] * k
        self.bass_vol = min(sc['bass_vol'] * k, 1.4 * LEAD / 0.577)
        if w == 'square':
            self.lead = _inst('pulse', sc['duty'], d=0.2, s=0.42)
            self.harm = _inst('pulse', 0.5 if sc['duty'] != 0.5 else 0.125, d=0.2, s=0.4)
        elif w == 'saw':
            self.lead = _inst('saw', d=0.18, s=0.45)
            self.harm = _inst('pulse', 0.25, d=0.18, s=0.4)
        else:
            self.lead = _inst(w, a=0.006, d=0.4, s=0.6, r=0.06)
            self.harm = self.lead
        bell = st >= 0.17 or style in SOFT
        self.alt = ('bell',) if bell else _inst('pulse', 0.125, d=0.15, s=0.5, r=0.05)
        self.alt_vol = 0.2 if bell else self.vol * (0.9 if w in ('square', 'saw') else 0.5)
        if style in SOFT:
            self.octave, self.oct_inst, self.oct_vol = 12, ('bell',), 0.12
        elif self.mean <= 71:
            self.octave, self.oct_inst, self.oct_vol = 12, _inst('pulse', 0.125, d=0.2, s=0.35), self.vol * 0.3
        else:
            self.octave, self.oct_inst, self.oct_vol = -12, _inst('tri', a=0.006, d=0.3, s=0.6), 0.14
        self.bass = _inst('tri', a=0.004, d=0.35, s=0.5, r=0.04)
        self.pedal = _inst('tri', a=0.01, d=0.8, s=0.7, r=0.08)
        self.arp = _inst('pulse', 0.125, a=0.002, d=0.06, s=0.2, r=0.02)
        chord = 'chord8' if style in ('eerie', 'ambient') else 'chord5'
        self.pad = _inst(chord, a=0.25, d=1.0, s=1.0, r=0.35)

    # -- timing
    def at(self, i):
        """Seconds from a section's start to step i (with any swing)."""
        return i * self.step + (self.swing * self.step if i % 2 else 0.0)

    def tick_at(self, j, tick):
        t = j * tick
        k = j * self.spb                              # (in quarter steps)
        if self.swing and k % 4 == 0 and (k // 4) % 2:  # an off-beat step: swung like the notes
            t += self.swing * self.step
        return t

    def play(self, lane, inst, t0, i, n, pitch, vol):
        sr = self.sr
        a = int(round((t0 + self.at(i)) * sr))
        if inst[0] == 'bell':
            key = ('bell', pitch, vol)
            x = self.made.get(key)
            if x is None:
                x = self.made[key] = array('q', map(int, map(mul, _bell(pitch, sr), repeat(vol * ONE))))
            self.bells = getattr(self, 'bells', 0) + 1
            self.lanes[lane if self.bells % 2 else 'bell2'].put(a, x)     # (two lanes take turns: bells ring on)
            return
        b = int(round((t0 + self.at(i + n)) * sr))
        ng = max(1, b - a - int(0.008 * sr))          # (a hair of space before the next note)
        key = (inst, pitch, ng, vol)
        x = self.made.get(key)
        if x is None:
            wave, duty, att, d, s, r = inst
            nr = int(r * sr)
            m = ng + nr
            cyc = _cycle(wave, hz(pitch), duty, sr)
            x = self.made[key] = array('q', map(int, map(mul, (cyc * (m // len(cyc) + 1))[:m],
                                                         _envelope(ng, nr, att, d, s, vol * ONE, sr))))
        self.lanes[lane].put(a, x)

    def hit(self, t, kind, vel):
        key = (kind, round(vel, 2))
        x = self.made.get(key)
        if x is None:
            x = self.made[key] = array('q', map(int, map(mul, _kit(self.sr)[kind],
                                                         repeat(key[1] * DRUM_VOL[kind] * ONE))))
        self.lanes['cymbals' if kind in ('crash', 'ohat') else 'drums'].put(int(round(t * self.sr)), x)

    # -- harmony
    def third_below(self, i, m):
        """A sweet harmony note under melody note m at step i: a third (or sixth) below in the key."""
        pcs = self.pcs
        cands = []
        if m % 12 in pcs:
            x, k = m, 0
            while k < 2:
                x -= 1
                k += (x % 12) in pcs
            cands.append(x)
        cands += [h for h in (m - 4, m - 3, m - 9, m - 8) if h % 12 in pcs]
        bass = self.bass_now[i]
        for h in cands:
            if bass is None or (h - bass) % 12 in GOOD:
                return h + 12 if h < 52 else h
        return None

    # -- one pass through the tune
    def section(self, kind, t0):
        sc, style = self.sc, self.style
        T = self.up if kind == 'B' else 0
        TB = T + (self.bass_up if kind == 'B' else 0)
        # the melody: on a bell (or a thin pulse) in the bridge; harmony and an octave double later on
        lead, lv = (self.alt, self.alt_vol) if kind == 'B' else (self.lead, self.vol)
        for i, n, p in _notes(sc['mel']):
            self.play('bell' if lead[0] == 'bell' else 'lead', lead, t0, i, n, p + T, lv)
            if kind in ('A2', 'A3') and style not in ('eerie', 'ambient'):
                h = self.third_below(i, p)
                if h is not None:
                    self.play('harm', self.harm, t0, i, n, h, self.vol * 0.42)
            if kind == 'A3':
                self.play('bell' if self.oct_inst[0] == 'bell' else 'oct', self.oct_inst, t0, i, n,
                          p + self.octave, self.oct_vol)
        # the bass: long held roots for the first half of the bridge
        if kind == 'B':
            for gi in range(8):
                self.play('bass', self.pedal, t0, 4 * gi, 4, self.roots[gi] + TB, self.bass_vol * 0.9)
        for i, n, p in _notes(sc['bass']):
            if not (kind == 'B' and i < 32):
                self.play('bass', self.bass, t0, i, n, p + TB, self.bass_vol)
        # a counter-line: the tune's own arpeggio, or one made from the bass's chords
        if sc['arp']:
            vol = 0.075 * (0.6 if kind == 'A1' else 1.0)
            for i, n, p in _notes(sc['arp']):
                if not (kind == 'B' and i < 32):
                    self.play('arp', self.arp, t0, i, n, p + T, vol)
        elif style in LOUD and kind != 'A1':
            for i in range(64):
                if kind == 'B' and i < 32:
                    continue
                r = self.roots[i // 4] + T
                while r < 58:
                    r += 12
                while r > 70:
                    r -= 12
                self.play('arp', self.arp, t0, i, 1, r + (0, 7, 12, 7)[i % 4], 0.065)
        # soft chords, two voices a hair apart (a gentle chorus)
        if kind in ('B', 'A3') or (kind == 'A2' and style in SOFT):
            pv = 0.075 if kind == 'B' else 0.055
            gi = 0
            while gi < 16:
                r, gj = self.roots[gi], gi + 1
                while gj < 16 and self.roots[gj] == r:
                    gj += 1
                base = r + T
                while base < 50:
                    base += 12
                self.play('pad1', self.pad, t0, 4 * gi, 4 * (gj - gi), base - 0.06, pv)
                self.play('pad2', self.pad, t0, 4 * gi, 4 * (gj - gi), base + 0.06, pv)
                gi = gj
        self.drums(kind, t0)

    def drums(self, kind, t0):
        kit = KITS[self.kit]
        measures = 64 // (4 * self.spb)
        tick = self.spb * self.step / 4
        small, big = FILLS[self.kit]
        for m in range(measures):
            second = m >= measures // 2
            mode = 'light' if kind == 'A1' else ('build' if second else 'half') if kind == 'B' else 'full'
            fill = []
            if kind in ('A2', 'A3'):
                fill = big if m == measures - 1 else small if m == measures // 2 - 1 else []
            elif kind == 'B' and m == measures - 1:
                fill = ROLLS.get(self.kit, _SNARE_ROLL)
            start = min((j for j, *_ in fill), default=16)
            base = t0 + m * 16 * tick
            if m == 0 and self.kit in LOUD and kind in ('A1', 'A2', 'A3'):
                self.hit(base, 'crash', 0.55 if kind == 'A1' else 0.9)
            elif m == 0 and self.kit == 'calm' and kind == 'A3':
                self.hit(base, 'crash', 0.45)
            for name, pat in kit[mode].items():
                for j, ch in enumerate(pat):
                    if ch != '.' and j < start:
                        v = X[ch]
                        if name in ('hat', 'shaker'):
                            v *= 0.85 + 0.3 * self.rnd.random()
                        self.hit(base + self.tick_at(j, tick), name, v)
            for j, name, v in fill:
                self.hit(base + self.tick_at(j, tick), name, v)

    def mixdown(self, length, wrap):
        """Sum the lanes, echo the wet ones, wrap the ringing end round to the start (so the loop is
        seamless) and keep length samples: a big whole number of samples x * ONE * 2^16 + bias."""
        lanes, n = self.lanes, self.n
        taps = (0.18, 0.06) if self.style == 'drive' else (0.34, 0.16, 0.07) if self.style in SOFT else (0.25, 0.1)
        d = int(0.75 * self.spb * self.step * self.sr)
        wet = sum((_big(lanes[k].buf) for k in WET if k in lanes), 0)
        total = (wet + sum((_big(lane.buf) for k, lane in lanes.items() if k not in WET), 0)) << 16
        for k, g in enumerate(taps, 1):
            total += (wet << (64 * k * d)) * round(g * 65536)
        bias = 1 << 44                                # every field positive: the fields read cleanly
        total += bias * _ones(n + len(taps) * d)
        head = total & ((1 << (64 * length)) - 1)
        if wrap:
            t = n - length
            head += ((total >> (64 * length)) & ((1 << (64 * t)) - 1)) - bias * _ones(t)
        return head, bias

    def render(self):
        for k, kind in enumerate(self.plan):
            self.section(kind, k * self.sec)
        v, bias = self.mixdown(self.loop, True)
        return _finish(v, bias, self.loop, LOUDNESS.get(self.style, 0.17))


def _jingle(sc, sr):
    """A short fanfare that plays once (no loop)."""
    length = len(sc['mel']) * sc['step'] + 1.6
    a = _Arrangement(dict(sc, style='groove'), sr, length)
    for i, n, p in _notes(sc['mel']):
        a.play('lead', a.lead, 0, i, n, p, a.vol)
        h = a.third_below(i, p)
        if h is not None:
            a.play('harm', a.harm, 0, i, n, h, a.vol * 0.42)
    for i, n, p in _notes(sc['bass']):
        a.play('bass', a.bass, 0, i, n, p, a.bass_vol)
    a.hit(0, 'crash', 0.8)
    a.hit(0, 'kick', 0.9)
    last = max(i for i, n, p in _notes(sc['mel']))
    for j in range(4):
        a.hit(a.at(last) - (4 - j) * sc['step'] / 2, 'snare', 0.4 + 0.15 * j)
    a.hit(a.at(last), 'kick', 1.0)
    a.hit(a.at(last), 'crash', 1.0)
    v, bias = a.mixdown(a.loop, False)
    return _finish(v, bias, a.loop, LOUDNESS['jingle'])


def render(name, sr=SR):
    """A whole tune, arranged and played: 16-bit mono samples at sr (an array('h')). Loops seamlessly,
    except the victory jingle, which plays once."""
    _envs.clear()
    _onesc.clear()
    sc = SCORES[name]
    if sc['style'] == 'jingle':
        return _jingle(sc, sr)
    return _Arrangement(sc, sr).render()


_score()
NAMES = list(SCORES)
