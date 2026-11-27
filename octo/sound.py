"""Sound: every sound effect is a tiny chiptune synthesised at startup, and the music - long
arrangements written by tunes.py - plays with gentle fades from one tune to the next.

Desktop: each tune is made the first time it's needed, in a separate process (about a second), so
the game never stalls. Browser: build_web.py makes every tune into an .ogg file ahead of time, and
the browser streams it as it plays (no decoding pause when Octo walks into a new place)."""
import array
import hashlib
import math
import os
import pickle
import random
import subprocess
import sys
import threading

import pygame

WEB = sys.platform == 'emscripten'
HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(HERE, 'audio')

SR = 22050
enabled = False
music_on = True
_sfx = {}
_channels = 1
_music_channel = None

MUSIC_VOL = 0.55
MUSIC_RATE = 22050                      # (tunes.SR: the rate tunes are made at)
FADE_OUT, FADE_IN = 700, 900            # ms: one tune fades out, then the next fades in
QUICK = {'victory': 120, 'boss': 250}   # ...except these, which cut in quickly
_current_track = None                   # the tune that should be playing
_want = None                            # (tune, loops) to start once the old one has faded out
_switching = False
_music_files = {}                       # browser: tune -> its .ogg
_streaming = True                       # browser: pygame.mixer.music streams the .ogg as it plays
_playing = None                         # the tune that's actually on
_ready = {}                             # tune -> Sound (the last few made)
_making = {}                            # desktop: tune -> its Sound once made (None while it's being made)
_jobs = []                              # desktop: tunes waiting to be made, the most wanted first
_worker = None


def _to_sound(samples, vol=1.0):
    buf = array.array('h')
    for v in samples:
        v = max(-1.0, min(1.0, v * vol))
        iv = int(v * 32000)
        for _ in range(_channels):
            buf.append(iv)
    return buf.tobytes()


def _osc(wave, phase, duty=0.5):
    p = phase % 1.0
    if wave == 'square':
        return 1.0 if p < duty else -1.0
    if wave == 'tri':
        return 4 * p - 1 if p < 0.5 else 3 - 4 * p
    if wave == 'saw':
        return 2 * p - 1
    return math.sin(p * 2 * math.pi)


def tone(f0, f1, dur, wave='square', vol=0.5, duty=0.5, attack=0.005, curve=1.0):
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        phase += f / SR
        env = min(1.0, i / (SR * attack + 1)) * (1 - t) ** curve
        out.append(_osc(wave, phase, duty) * env * vol)
    return out


def noise(dur, vol=0.5, curve=1.5, step=1):
    n = int(SR * dur)
    rnd = random.Random(5)
    out = []
    v = 0.0
    for i in range(n):
        if i % step == 0:
            v = rnd.uniform(-1, 1)
        out.append(v * vol * (1 - i / n) ** curve)
    return out


def seq(notes, dur, wave='square', vol=0.4, duty=0.5):
    out = []
    for f in notes:
        out += tone(f, f, dur, wave, vol, duty, curve=0.6)
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)



def init():
    global enabled, SR, _channels, _music_channel
    if WEB:
        _init_web()
        return
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        freq, size, ch = pygame.mixer.get_init()
        SR, _channels = freq, ch
        pygame.mixer.set_num_channels(16)
        _music_channel = pygame.mixer.Channel(0)
        pygame.mixer.set_reserved(1)
    except Exception as e:      # no audio device: play silently
        print("Sound disabled:", e)
        enabled = False
        return
    enabled = True

    # the sound effects take a few seconds to make, so keep them on disk
    src = open(__file__, 'rb').read()
    tag = hashlib.md5(src + f"{SR}/{_channels}".encode()).hexdigest()
    cache = os.path.join(HERE, '.sound_cache.pkl')
    data = None
    try:
        with open(cache, 'rb') as f:
            saved = pickle.load(f)
        if saved.get('tag') == tag:
            data = saved
    except Exception:
        pass
    if data is None:
        data = {'tag': tag, 'sfx': {}}
        _synth(data['sfx'])
        try:
            with open(cache, 'wb') as f:
                pickle.dump(data, f)
        except OSError:
            pass
    for k, b in data['sfx'].items():
        _sfx[k] = pygame.mixer.Sound(buffer=b)


def _init_web():
    """Browser build: load the pre-made .ogg files written by build_web.py (making them in the
    browser would take far too long). Tunes are only noted here: they stream when they play."""
    global enabled, _music_channel
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        _music_channel = pygame.mixer.Channel(0)
        pygame.mixer.set_reserved(1)
        for name in sorted(os.listdir(AUDIO_DIR)):
            kind, _, rest = name.partition('_')
            key = rest.rsplit('.', 1)[0]
            path = os.path.join(AUDIO_DIR, name)
            if kind == 'music':
                _music_files[key] = path
            else:
                _sfx[key] = pygame.mixer.Sound(path)
    except Exception as e:
        print("Sound disabled:", e)
        enabled = False
        return
    enabled = True


def export_ogg(out_dir):
    """Used by build_web.py: make every sound effect and tune and write them out as .ogg files
    (needs ffmpeg). The tunes take about a second each."""
    import tempfile
    import wave
    sys.path.insert(0, HERE)
    import tunes
    sfx = {}
    _synth(sfx)
    os.makedirs(out_dir, exist_ok=True)

    def write(tmp, kind, key, buf, channels, rate, q):
        wav = os.path.join(tmp, f'{kind}_{key}.wav')
        with wave.open(wav, 'wb') as w:
            w.setnchannels(channels)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(buf)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-c:a', 'libvorbis', '-q:a', q,
                        os.path.join(out_dir, f'{kind}_{key}.ogg')], check=True)
        os.remove(wav)
    with tempfile.TemporaryDirectory() as tmp:
        for key, buf in sfx.items():
            write(tmp, 'sfx', key, buf, _channels, SR, '5')
        for key in tunes.NAMES:
            write(tmp, 'music', key, tunes.render(key, tunes.SR).tobytes(), 1, tunes.SR, '3')
            print("  tune", key)


def _synth(S):
    S['ink'] = _to_sound(tone(900, 260, 0.12, 'square', 0.4, duty=0.25))
    S['slap'] = _to_sound(mix(noise(0.08, 0.5, step=3), tone(180, 60, 0.1, 'tri', 0.6)))
    S['hit'] = _to_sound(tone(320, 110, 0.11, 'square', 0.4))
    S['tink'] = _to_sound(mix(tone(1900, 1900, 0.06, 'square', 0.2, duty=0.125),
                              tone(2500, 2500, 0.06, 'square', 0.15, duty=0.125)))
    S['die'] = _to_sound(mix(noise(0.3, 0.5, step=6), tone(500, 60, 0.3, 'square', 0.25)))
    S['hurt'] = _to_sound(tone(500, 90, 0.3, 'saw', 0.45))
    S['pearl'] = _to_sound(tone(1320, 1320, 0.05, 'square', 0.3, duty=0.25)
                           + tone(1760, 1760, 0.09, 'square', 0.3, duty=0.25))
    S['munch'] = _to_sound(noise(0.04, 0.4, step=4) + [0.0] * int(SR * 0.03)
                           + noise(0.04, 0.4, step=4) + tone(900, 1300, 0.05, 'square', 0.2, 0.25))
    S['heart'] = _to_sound(seq([midi(n) for n in (72, 76, 79)], 0.06, 'square', 0.3, 0.25))
    S['key'] = _to_sound(seq([midi(n) for n in (67, 72, 76, 79, 84)], 0.05, 'square', 0.3, 0.25))
    S['item'] = _to_sound(seq([midi(n) for n in (60, 64, 67, 72, 67, 72, 76, 79)], 0.08,
                              'square', 0.3, 0.5))
    S['flip'] = _to_sound(tone(250, 900, 0.09, 'tri', 0.5) + tone(900, 400, 0.09, 'tri', 0.5))
    S['door'] = _to_sound(mix(noise(0.25, 0.4, step=12), tone(110, 55, 0.3, 'square', 0.3)))
    S['shut'] = _to_sound(mix(noise(0.15, 0.4, step=16), tone(90, 50, 0.15, 'tri', 0.6)))
    S['cut'] = _to_sound(noise(0.07, 0.35, step=2))
    S['text'] = _to_sound(tone(1200, 1200, 0.015, 'square', 0.12, duty=0.25))
    S['roar'] = _to_sound(mix(noise(0.8, 0.4, curve=0.7, step=20), tone(140, 40, 0.8, 'saw', 0.3)))
    S['warp'] = _to_sound(seq([midi(n) for n in (79, 74, 71, 67, 62, 59, 55)], 0.05,
                              'square', 0.3, 0.5))
    S['shoot'] = _to_sound(tone(600, 300, 0.06, 'square', 0.25, duty=0.125))
    S['bubble'] = _to_sound(tone(200, 700, 0.12, 'sine', 0.5))
    S['lowhp'] = _to_sound(tone(1500, 1500, 0.06, 'square', 0.12, duty=0.5))
    S['boom'] = _to_sound(mix(noise(0.6, 0.6, curve=1.1, step=10), tone(130, 28, 0.55, 'tri', 0.8)))
    S['jet'] = _to_sound(mix(noise(0.2, 0.3, curve=1.2, step=2), tone(260, 900, 0.16, 'sine', 0.35)))
    S['fuse'] = _to_sound(tone(2200, 2200, 0.02, 'square', 0.1, duty=0.25))
    S['buy'] = _to_sound(seq([midi(n) for n in (72, 79, 84)], 0.06, 'square', 0.3, 0.25))
    S['nope'] = _to_sound(seq([midi(n) for n in (55, 50)], 0.09, 'square', 0.25, 0.5))
    S['zap'] = _to_sound(mix(noise(0.22, 0.35, curve=1.0, step=1),
                              tone(1800, 300, 0.22, 'square', 0.25, duty=0.125)))
    S['ice'] = _to_sound(tone(2400, 1600, 0.1, 'tri', 0.35) + tone(3000, 3000, 0.04, 'sine', 0.25))
    S['wisp'] = _to_sound(tone(400, 800, 0.2, 'sine', 0.35) + tone(800, 500, 0.12, 'sine', 0.2))
    S['portal'] = _to_sound(seq([midi(n) for n in (60, 67, 72, 79, 84, 91)], 0.05, 'tri', 0.35))
    S['tick'] = _to_sound(tone(1000, 1000, 0.03, 'square', 0.15, duty=0.25))
    S['whoosh'] = _to_sound(mix(noise(0.5, 0.35, curve=0.8, step=3), tone(200, 1400, 0.45, 'sine', 0.3)))
    S['pause'] = _to_sound(seq([midi(n) for n in (76, 72)], 0.05, 'square', 0.25, 0.25))


def play(name):
    if enabled and music_on and name in _sfx:
        _sfx[name].play()


def warm():
    """Play every sound effect once, inaudibly quietly, a few at a time on spare channels. In a browser the
    first time a sound plays can stall the game for a moment, so this is done behind the loading
    bar. A generator: one step per handful of sounds."""
    if not enabled:
        return
    chans = [pygame.mixer.Channel(i) for i in range(8, 16)]
    names = sorted(_sfx)
    for i in range(0, len(names), len(chans)):
        for ch, name in zip(chans, names[i:i + len(chans)]):
            ch.set_volume(0.01)                 # (far too quiet to hear, but not skipped as silent)
            ch.play(_sfx[name])
        yield 'frame'                           # (let a frame pass: the browser gets them ready)
    for ch in chans:
        ch.stop()
        ch.set_volume(1.0)


# ---- music ------------------------------------------------------------------------------------

def music(track, loops=-1):
    """Change to another tune (None for quiet): the old one fades out, then the new one fades in.
    loops=0 plays it once (the victory fanfare)."""
    global _current_track, _want, _switching
    if not enabled:
        return
    if track == _current_track and (_switching or _busy()):
        return                                  # already playing, or on its way
    _current_track = track
    _want = (track, loops)
    _switching = True
    if _busy():
        _fade_out(QUICK.get(track, FADE_OUT))
    if track and not WEB:
        _prepare(track)
    update()


def update():
    """Called every frame: once the old tune has faded out (and, on a desktop, the new one is made),
    start the new one."""
    global _switching, _streaming, _playing
    if not enabled or not _switching or _busy():
        return
    track, loops = _want
    _playing = None
    if not track or not music_on:
        _switching = False
        return
    fade_in = 0 if track in QUICK else FADE_IN
    if WEB:
        path = _music_files.get(track)
        if path is None:
            _switching = False
            return
        if _streaming:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(MUSIC_VOL)
                pygame.mixer.music.play(loops, fade_ms=fade_in)
                _switching, _playing = False, track
                return
            except Exception as e:              # no streaming here: decode the whole tune instead
                print("music streaming unavailable:", e)
                _streaming = False
        snd = _ready.get(track)
        if snd is None:
            try:
                snd = pygame.mixer.Sound(path)
            except Exception as e:
                print("music:", e)
                _switching = False
                return
            _keep(track, snd)
    else:
        snd = _ready.get(track)
        if snd is None:
            snd = _making.get(track)
            if snd is None:
                if track not in _making:
                    _prepare(track)
                return                          # still being made
            del _making[track]
            if snd is False:                    # (it couldn't be made)
                _switching = False
                return
            _keep(track, snd)
    _music_channel.set_volume(MUSIC_VOL)
    _music_channel.play(snd, loops=loops, fade_ms=fade_in)
    _switching, _playing = False, track


def _busy():
    if WEB and _streaming:
        return pygame.mixer.music.get_busy()
    return _music_channel.get_busy()


def _fade_out(ms):
    if WEB and _streaming:
        pygame.mixer.music.fadeout(ms)
    else:
        _music_channel.fadeout(ms)


def _stop():
    global _playing
    _playing = None
    if WEB and _streaming:
        pygame.mixer.music.stop()
    else:
        _music_channel.stop()


def _keep(track, snd):
    """Remember the last few tunes made, so going back and forth costs nothing."""
    _ready.pop(track, None)
    _ready[track] = snd
    while len(_ready) > 6:
        del _ready[next(iter(_ready))]


def _prepare(track):
    """Desktop: have a tune made, in a separate process so the game keeps running smoothly meanwhile.
    One at a time, the most wanted first."""
    global _worker
    if track in _ready or track in _making:
        return
    if track in _jobs:
        _jobs.remove(track)
    _jobs.insert(0, track)
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_work, daemon=True)
        _worker.start()


def _work():
    import io
    import wave
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import tunes; "
            "sys.stdout.buffer.write(tunes.render(sys.argv[2]).tobytes())")
    while _jobs:
        track = _jobs.pop(0)
        if track != _current_track or track in _ready:
            continue                            # (not wanted any more)
        _making[track] = None
        snd = False
        try:
            pcm = subprocess.run([sys.executable, '-c', code, HERE, track], capture_output=True, check=True).stdout
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as w:     # the tunes' own rate: the mixer converts it to its own
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(MUSIC_RATE)
                w.writeframes(pcm)
            buf.seek(0)
            snd = pygame.mixer.Sound(file=buf)
        except Exception as e:
            print("music:", track, e)
        _making[track] = snd


def toggle_music():
    global music_on, _current_track, _switching
    music_on = not music_on
    if not enabled:
        return
    if music_on:
        t = _current_track
        _current_track = None
        music(t)
    else:
        _stop()
        _switching = False


def status():
    """For test pages: the tune that's on, whether it's really playing, and how."""
    if not enabled:
        return 'off'
    pos = pygame.mixer.music.get_pos() if WEB and _streaming else -1
    return f"{_playing}|{'busy' if _busy() else 'idle'}|{'stream' if WEB and _streaming else 'sound'}|{pos}"
