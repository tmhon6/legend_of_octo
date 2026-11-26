"""Tiny chiptune synth: every sound effect and music loop is generated at startup."""
import array
import hashlib
import math
import os
import pickle
import random
import sys

import pygame

WEB = sys.platform == 'emscripten'
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio')

SR = 22050
enabled = False
music_on = True
_sfx = {}
_music = {}
_music_channel = None
_current_track = None
_channels = 1


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


def render_song(melody, bass, step, mel_wave='square', mel_duty=0.25, mel_vol=0.22,
                bass_vol=0.3, arp=None):
    """melody/bass are lists of midi numbers per step (None = rest, 0 = hold)."""
    n_step = int(SR * step)
    total = n_step * len(melody)
    out = [0.0] * total

    def voice(notes, wave, duty, vol, gate):
        phase = 0.0
        cur = None
        age = 0
        for s, note in enumerate(notes):
            if note == 0:
                pass            # hold (or keep resting)
            elif note is None:
                cur = None
            else:
                cur = midi(note)
                age = 0
            base = s * n_step
            for i in range(n_step):
                if cur is None:
                    continue
                phase += cur / SR
                env = max(0.0, 1.0 - (age / (SR * gate)))
                age += 1
                out[base + i] += _osc(wave, phase, duty) * vol * (0.35 + 0.65 * env)

    voice(melody, mel_wave, mel_duty, mel_vol, 0.25)
    voice(bass, 'tri', 0.5, bass_vol, 0.6)
    if arp:
        voice(arp, 'square', 0.125, 0.07, 0.08)
    # gentle hi-hat on every other step
    rnd = random.Random(1)
    for s in range(0, len(melody), 2):
        base = s * n_step
        for i in range(int(SR * 0.02)):
            out[base + i] += rnd.uniform(-1, 1) * 0.05 * (1 - i / (SR * 0.02))
    return out


# ---- original tunes ---------------------------------------------------------

def _reef_song():
    H = 0
    mel = [62, H, 65, 69, 67, H, 65, 64, 62, H, 60, H, 57, H, H, H,
           60, H, 64, 67, 65, H, 64, 62, 64, H, 65, 67, 69, H, H, H,
           62, H, 65, 69, 72, H, 71, 69, 67, H, 69, 65, 64, H, 60, H,
           62, 64, 65, 67, 69, H, 67, 64, 62, H, H, H, None, None, 61, H]
    bass = []
    for root in (38, 38, 45, 45, 36, 36, 43, 43, 38, 38, 41, 41, 45, 45, 38, 38):
        bass += [root, H, root + 12, H]
    return render_song(mel, bass, 0.2)


def _shrine_song():
    H = 0
    mel = [57, H, H, 60, 59, H, 57, H, 56, H, H, H, None, None, 52, H,
           57, H, H, 60, 64, H, 63, H, 62, H, H, H, None, None, None, None,
           65, H, 64, H, 62, H, 60, H, 59, H, 60, 62, 59, H, 56, H,
           57, H, 59, H, 60, H, 56, H, 57, H, H, H, None, None, None, None]
    bass = []
    for root in (33, 33, 32, 32, 33, 33, 30, 30, 29, 29, 28, 28, 33, 32, 33, 33):
        bass += [root, H, H, root + 7]
    return render_song(mel, bass, 0.26, mel_wave='square', mel_duty=0.5, mel_vol=0.16)


def _victory_song():
    H = 0
    mel = [60, 64, 67, 72, H, H, 71, 72, 74, H, 76, H, H, H, None, None]
    bass = [36, H, 43, H, 48, H, 43, H, 41, H, 43, H, 36, H, H, H]
    return render_song(mel, bass, 0.14, mel_vol=0.25)


def _trial_song():
    H = 0
    mel = [69, 72, 76, 72, 69, 72, 76, 72, 68, 71, 76, 71, 68, 71, 76, 71,
           67, 70, 74, 70, 67, 70, 74, 70, 68, 71, 74, 76, 77, 76, 74, 71,
           69, 72, 76, 81, 80, 76, 72, 69, 70, 74, 77, 82, 81, 77, 74, 70,
           69, 72, 76, 72, 68, 71, 76, 71, 69, H, 81, H, 80, H, 76, H]
    bass = []
    for root in (45, 45, 44, 44, 43, 43, 44, 44, 45, 45, 46, 46, 45, 44, 45, 45):
        bass += [root, root + 12, root, root + 12]
    return render_song(mel, bass, 0.11, mel_wave='square', mel_duty=0.25, mel_vol=0.15, bass_vol=0.32)


def _title_song():
    """A bright, bouncy theme in F major for the title screen."""
    H = 0
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
    return render_song(mel, bass, 0.15, mel_wave='square', mel_duty=0.25, mel_vol=0.2, arp=arp)


def _frost_song():
    H = 0
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
    return render_song(mel, bass, 0.2, mel_wave='tri', mel_duty=0.5, mel_vol=0.3, bass_vol=0.22, arp=arp)


def _vents_song():
    H = 0
    mel = [57, H, 60, 57, 63, H, 62, H, 60, H, 57, H, 56, H, H, H,
           57, H, 60, 57, 63, H, 65, H, 63, 62, 60, H, 62, H, H, H,
           69, H, 68, H, 65, H, 63, H, 62, H, 60, H, 63, H, 62, H,
           60, H, 57, H, 56, H, 57, H, 57, H, H, H, None, None, None, None]
    bass = []
    for root in (33, 33, 33, 32, 33, 33, 35, 35, 38, 38, 36, 36, 33, 32, 33, 33):
        bass += [root, root, H, root + 12]
    return render_song(mel, bass, 0.14, mel_wave='saw', mel_duty=0.5, mel_vol=0.13, bass_vol=0.34)


def _city_song():
    H = 0
    mel = [64, H, H, H, 67, H, 66, H, 64, H, H, H, None, None, 59, H,
           60, H, H, H, 64, H, 63, H, 59, H, H, H, None, None, None, None,
           64, H, 67, H, 71, H, 70, H, 67, H, 66, H, 64, H, 63, H,
           64, H, H, H, 59, H, H, H, 64, H, H, H, None, None, None, None]
    bass = []
    for root in (40, 40, 36, 36, 35, 35, 40, 40, 40, 40, 43, 43, 36, 35, 40, 40):
        bass += [root, H, H, H]
    return render_song(mel, bass, 0.3, mel_wave='sine', mel_duty=0.5, mel_vol=0.3, bass_vol=0.3)


def _sky_song():
    H = 0
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
    return render_song(mel, bass, 0.17, mel_wave='tri', mel_duty=0.5, mel_vol=0.32, bass_vol=0.25, arp=arp)


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

    # synthesis takes a couple of seconds, so cache the raw buffers on disk
    src = open(__file__, 'rb').read()
    tag = hashlib.md5(src + f"{SR}/{_channels}".encode()).hexdigest()
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.sound_cache.pkl')
    data = None
    try:
        with open(cache, 'rb') as f:
            saved = pickle.load(f)
        if saved.get('tag') == tag:
            data = saved
    except Exception:
        pass
    if data is None:
        data = {'tag': tag, 'sfx': {}, 'music': {}}
        _synth(data['sfx'], data['music'])
        try:
            with open(cache, 'wb') as f:
                pickle.dump(data, f)
        except OSError:
            pass
    for k, b in data['sfx'].items():
        _sfx[k] = pygame.mixer.Sound(buffer=b)
    for k, b in data['music'].items():
        _music[k] = pygame.mixer.Sound(buffer=b)


def _init_web():
    """Browser build: load the pre-made .ogg files written by build_web.py (synthesising in the
    browser would take far too long)."""
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
            snd = pygame.mixer.Sound(os.path.join(AUDIO_DIR, name))
            (_music if kind == 'music' else _sfx)[key] = snd
    except Exception as e:
        print("Sound disabled:", e)
        enabled = False
        return
    enabled = True


def export_ogg(out_dir):
    """Used by build_web.py: synthesise everything and write it out as .ogg files (needs ffmpeg)."""
    import subprocess
    import tempfile
    import wave
    data = {'sfx': {}, 'music': {}}
    _synth(data['sfx'], data['music'])
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for kind in ('sfx', 'music'):
            for key, buf in data[kind].items():
                wav = os.path.join(tmp, f'{kind}_{key}.wav')
                with wave.open(wav, 'wb') as w:
                    w.setnchannels(_channels)
                    w.setsampwidth(2)
                    w.setframerate(SR)
                    w.writeframes(buf)
                q = '4' if kind == 'music' else '5'
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-c:a', 'libvorbis',
                                '-q:a', q, os.path.join(out_dir, f'{kind}_{key}.ogg')], check=True)


def _synth(S, M):
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

    M['reef'] = _to_sound(_reef_song())
    M['shrine'] = _to_sound(_shrine_song())
    M['victory'] = _to_sound(_victory_song())
    M['trial'] = _to_sound(_trial_song())
    M['title'] = _to_sound(_title_song())
    M['frost'] = _to_sound(_frost_song())
    M['vents'] = _to_sound(_vents_song())
    M['city'] = _to_sound(_city_song())
    M['sky'] = _to_sound(_sky_song())


def play(name):
    if enabled and music_on and name in _sfx:
        _sfx[name].play()


def music(track, loops=-1):
    global _current_track
    if not enabled:
        return
    if track == _current_track and _music_channel.get_busy():
        return
    _current_track = track
    _music_channel.stop()
    if track and music_on:
        _music_channel.set_volume(0.55)
        _music_channel.play(_music[track], loops=loops)


def toggle_music():
    global music_on
    music_on = not music_on
    if not enabled:
        return
    if music_on:
        t = _current_track
        globals()['_current_track'] = None
        music(t)
    else:
        _music_channel.stop()
