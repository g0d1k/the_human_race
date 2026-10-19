"""Sound effect definitions, described frame-by-frame for the APU synth."""
import math


def _sweep(f0, f1, frames, duty, v0, v1, curve=1.0):
    out = []
    for i in range(frames):
        t = i / max(1, frames - 1)
        tc = t ** curve
        f = f0 + (f1 - f0) * tc
        v = int(round(v0 + (v1 - v0) * t))
        out.append(((f, duty, max(0, min(15, v))), None, None, None))
    return out


def _noise(period, frames, v0, v1, period_end=None):
    out = []
    for i in range(frames):
        t = i / max(1, frames - 1)
        v = int(round(v0 + (v1 - v0) * t))
        per = period if period_end is None else int(round(period + (period_end - period) * t))
        out.append((None, None, (per, max(0, min(15, v))), None))
    return out


def _merge(*tracks):
    n = max(len(t) for t in tracks)
    out = []
    for i in range(n):
        slots = [None, None, None, None]
        for tr in tracks:
            if i < len(tr):
                for k in range(4):
                    if tr[i][k] is not None:
                        slots[k] = tr[i][k]
        out.append(tuple(slots))
    return out


def _as_p2(track):
    return [(None, fr[0], fr[2], fr[3]) for fr in track]


def _notes(seq, duty, vol, frames_each, decay=0):
    """Melodic jingle: seq of frequencies (or 0 for a rest)."""
    out = []
    for f in seq:
        for i in range(frames_each):
            v = max(2, vol - (i * decay) // max(1, frames_each))
            out.append(((f, duty, v), None, None, None) if f else (None, None, None, None))
    return out


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def _tri_sweep(f0, f1, frames):
    return [(None, None, None, f0 + (f1 - f0) * i / max(1, frames - 1)) for i in range(frames)]


def build_sfx_frames():
    s = {}
    s["shot"] = _sweep(1400, 500, 5, 2, 9, 3, 0.6)
    s["shot_spread"] = _merge(_sweep(1100, 380, 6, 1, 9, 3, 0.7), _noise(2, 3, 4, 1))
    s["shot_laser"] = _sweep(2600, 1800, 7, 0, 9, 4)
    s["enemy_shot"] = _sweep(500, 820, 4, 1, 6, 2)
    s["hit"] = _noise(3, 3, 6, 2)
    s["explode_small"] = _noise(8, 16, 13, 0, 11)
    s["explode_big"] = _merge(_noise(11, 40, 15, 0, 14), _tri_sweep(220, 40, 24))
    s["death"] = _merge(_sweep(900, 80, 50, 2, 13, 2, 0.8), _noise(10, 50, 14, 0, 14))
    s["powerup"] = _notes([_hz(72), _hz(76), _hz(79), _hz(84), _hz(88), _hz(91)], 1, 11, 3)
    s["oneup"] = _merge(_notes([_hz(76), _hz(79), _hz(88), _hz(84), _hz(86), _hz(91)], 2, 12, 6, 6),
                        _as_p2(_notes([_hz(64), _hz(67), _hz(76), _hz(72), _hz(74), _hz(79)], 0, 6, 6, 4)))
    s["menu_move"] = _sweep(1200, 1200, 3, 1, 8, 4)
    s["menu_select"] = _merge(_notes([_hz(79), _hz(91)], 1, 10, 4, 4))
    s["pause"] = _notes([_hz(83), _hz(88), _hz(83), _hz(88)], 2, 10, 4, 6)
    siren = []
    for i in range(48):
        t = i / 47.0
        f = 620 + 360 * (0.5 - 0.5 * math.cos(t * math.pi * 2))
        siren.append(((f, 1, 10), (f * 1.5, 0, 4), None, None))
    s["siren"] = siren
    s["bomb"] = _merge(_noise(13, 60, 15, 0, 15), _sweep(300, 40, 40, 2, 12, 0), _tri_sweep(160, 30, 40))
    s["shield"] = _sweep(400, 1600, 10, 0, 10, 4)
    s["shield_break"] = _merge(_sweep(1600, 300, 12, 0, 11, 2), _noise(4, 8, 8, 0))
    s["warn_beep"] = _sweep(880, 880, 4, 2, 7, 3)
    s["laser_charge"] = _sweep(200, 900, 20, 0, 4, 9)
    s["laser_fire"] = _merge(_noise(5, 30, 10, 3), _sweep(180, 160, 30, 3, 8, 6))
    s["boss_hit"] = _noise(6, 2, 5, 3)
    s["teleport"] = _sweep(300, 2400, 16, 0, 10, 2, 2.0)
    s["tally"] = _sweep(1800, 1800, 2, 1, 6, 4)
    s["join"] = _notes([_hz(67), _hz(72), _hz(79)], 1, 11, 4, 3)
    return s
