"""A tiny MML (Music Macro Language) compiler for the APU synth.

Commands (whitespace and '|' bar lines are ignored):
  t<n>   tempo (set per song, not per channel)
  o<n>   octave        >  octave up       <  octave down
  l<n>   default note length (4 = quarter note); dots allowed
  v<n>   volume 0-15   @<n> pulse duty (0=12.5% 1=25% 2=50% 3=75%)
  y<n>   envelope decay: frames per volume step (0 = sustain)
  s<n>   sustain floor volume for the decay
  q<n>   gate time in eighths of the note length (1-8)
  c d e f g a b [+#-] [length] [.]   notes;  r [length]  rest
  k s h j x   (noise channel) kick, snare, closed hat, open hat, crash
  [ ... ]n    repeat the enclosed section n times
"""

NOTE_OFFS = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}

# noise drums: (period index, start volume, frames per decay step, max frames)
DRUMS = {
    "k": (13, 13, 1, 10),
    "s": (6, 12, 2, 14),
    "h": (1, 6, 1, 4),
    "j": (1, 7, 3, 16),
    "x": (3, 10, 6, 60),
}


def expand_loops(text):
    def parse(i):
        buf = []
        while i < len(text):
            ch = text[i]
            if ch == "[":
                inner, i = parse(i + 1)
                j = i
                while j < len(text) and text[j].isdigit():
                    j += 1
                count = int(text[i:j]) if j > i else 2
                i = j
                buf.append(inner * count)
            elif ch == "]":
                return "".join(buf), i + 1
            else:
                buf.append(ch)
                i += 1
        return "".join(buf), i
    return parse(0)[0]


class Event:
    __slots__ = ("kind", "value", "beats", "vol", "duty", "decay", "floor", "gate")

    def __init__(self, kind, value, beats, vol, duty, decay, floor, gate):
        self.kind = kind
        self.value = value
        self.beats = beats
        self.vol = vol
        self.duty = duty
        self.decay = decay
        self.floor = floor
        self.gate = gate


def parse(text, noise=False):
    s = expand_loops(text.lower())
    i = 0
    n = len(s)
    octave = 4
    length = 4.0
    vol = 10
    duty = 2
    decay = 0
    floor = None
    gate = 7
    events = []

    def read_num(i):
        j = i
        while j < n and s[j].isdigit():
            j += 1
        return (int(s[i:j]) if j > i else None), j

    def read_len(i, default):
        num, i = read_num(i)
        beats = 4.0 / num if num else default
        add = beats / 2.0
        while i < n and s[i] == ".":
            beats += add
            add /= 2.0
            i += 1
        return beats, i

    while i < n:
        ch = s[i]
        i += 1
        if ch in " \t\r\n|":
            continue
        if ch == "o":
            num, i = read_num(i)
            octave = num if num is not None else octave
        elif ch == ">":
            octave += 1
        elif ch == "<":
            octave -= 1
        elif ch == "l":
            num, i = read_num(i)
            if num:
                length = 4.0 / num
                add = length / 2.0
                while i < n and s[i] == ".":
                    length += add
                    add /= 2.0
                    i += 1
        elif ch == "v":
            num, i = read_num(i)
            vol = max(0, min(15, num or 0))
        elif ch == "@":
            num, i = read_num(i)
            duty = max(0, min(3, num or 0))
        elif ch == "q":
            num, i = read_num(i)
            gate = max(1, min(8, num or 8))
        elif ch == "t":
            _, i = read_num(i)
        elif ch == "r":
            beats, i = read_len(i, length)
            events.append(Event("r", None, beats, 0, duty, 0, 0, gate))
        elif noise and ch in DRUMS:
            beats, i = read_len(i, length)
            events.append(Event("d", ch, beats, vol, duty, 0, 0, 8))
        elif ch in NOTE_OFFS:
            semi = NOTE_OFFS[ch]
            while i < n and s[i] in "+#-":
                semi += -1 if s[i] == "-" else 1
                i += 1
            beats, i = read_len(i, length)
            midi = 12 * (octave + 1) + semi
            fl = floor if floor is not None else vol // 2
            events.append(Event("n", midi, beats, vol, duty, decay, fl, gate))
        elif ch == "y":
            num, i = read_num(i)
            decay = num or 0
        elif ch == "s" and not noise:
            num, i = read_num(i)
            floor = num
        # anything else is ignored
    return events


def render_channel(apu, events, kind, tempo):
    """Render events for one voice; returns a bytes stream of 4-bit levels."""
    rate = apu.rate
    spb = rate * 60.0 / tempo
    fl = apu.frame_len
    t = 0.0
    chunks = []
    for ev in events:
        start = int(round(t))
        t += ev.beats * spb
        n = int(round(t)) - start
        if n <= 0:
            continue
        if ev.kind == "r" or (ev.kind == "n" and ev.vol == 0):
            chunks.append(bytes(n))
            continue
        if ev.kind == "d":
            per, v0, dec, maxf = DRUMS[ev.value]
            v0 = min(15, max(1, int(round(v0 * ev.vol / 10.0))))
            frames = min(maxf, n // fl + 1)
            env = [max(0, v0 - f // dec) for f in range(frames)]
            sn = min(n, frames * fl)
            chunks.append(apu.render_tone(apu.noise_block(per), sn, env))
            if n > sn:
                chunks.append(bytes(n - sn))
            continue
        gate_n = max(1, int(n * ev.gate / 8.0))
        frames = gate_n // fl + 2
        freq = 440.0 * (2.0 ** ((ev.value - 69) / 12.0))
        if kind == "tri":
            block = apu.tri_block(freq / 2.0)    # the triangle sounds an octave lower
            chunks.append(apu.render_tone(block, gate_n, [1] * frames, "tri"))
        else:
            block = apu.pulse_block(freq, ev.duty)
            if ev.decay > 0:
                env = [max(ev.floor, ev.vol - f // ev.decay) for f in range(frames)]
            else:
                env = [ev.vol] * frames
            chunks.append(apu.render_tone(block, gate_n, env))
        if n > gate_n:
            chunks.append(bytes(n - gate_n))
    return b"".join(chunks)


def total_beats(events):
    return sum(e.beats for e in events)


def render_song(apu, song):
    tempo = song["tempo"]
    p1, p2, tri, noi = song["ch"]
    e1 = parse(p1)
    e2 = parse(p2)
    et = parse(tri)
    en = parse(noi, noise=True)
    b1 = render_channel(apu, e1, "pulse", tempo)
    b2 = render_channel(apu, e2, "pulse", tempo)
    bt = render_channel(apu, et, "tri", tempo)
    bn = render_channel(apu, en, "noise", tempo)
    beats = max(total_beats(e1), total_beats(e2), total_beats(et), total_beats(en))
    length = int(round(beats * apu.rate * 60.0 / tempo))
    levels = apu.mix(b1, b2, bt, bn)
    if len(levels) < length:
        levels += bytes(length - len(levels))
    return levels[:length] if song.get("loop") else levels
