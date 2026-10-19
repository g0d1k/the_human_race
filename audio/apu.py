"""A small NES APU emulation: 2 pulse voices (12.5/25/50/75% duty), a 4-bit
triangle, and an LFSR noise channel, mixed with the APU's non-linear mixer.

Everything is pure Python (no numpy). To stay fast on low-end machines, each
voice is rendered as a `bytes` object of 4-bit levels built by repeating
pre-computed waveform blocks; volume envelopes use `bytes.translate`, and the
voices are mixed with `map(operator.add, ...)`, which runs at C speed.
"""
import array
import operator
import sys

CPU_HZ = 1789773
NOISE_PERIODS = (4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068)
DUTIES = (0.125, 0.25, 0.5, 0.75)
TRI_SEQ = tuple(list(range(15, -1, -1)) + list(range(0, 16)))


def _lfsr_sequence():
    """One full period (32767 steps) of the NES 15-bit noise LFSR (long mode)."""
    reg = 1
    out = bytearray(32767)
    for i in range(32767):
        fb = (reg ^ (reg >> 1)) & 1
        reg = (reg >> 1) | (fb << 14)
        out[i] = (~reg) & 1
    return bytes(out)


def note_freq(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


class APU:
    def __init__(self, rate):
        self.rate = rate
        self.frame_len = max(1, int(round(rate / 60.0)))
        self.lfsr = _lfsr_sequence()
        self._pulse = {}
        self._tri = {}
        self._noise = {}
        # volume tables: map a 0/1 waveform byte to a 0..15 level
        self.vol = [bytes(min(15, b * v) for b in range(256)) for v in range(16)]
        # triangle "times 16" table (the triangle has no volume control)
        self.x16 = bytes(min(255, b * 16) for b in range(256))
        self.tri_mute = bytes(256)
        # Non-linear APU mixer, normalised to an 8-bit output level.
        pulse = [0.0] + [95.52 / (8128.0 / n + 100.0) for n in range(1, 31)]
        tnd = []
        for idx in range(256):
            t = idx >> 4
            n = idx & 15
            s = 3 * t + 2 * n
            tnd.append(0.0 if s == 0 else 163.67 / (24329.0 / s + 100.0))
        peak = pulse[30] + tnd[255]
        self.ptab = bytes(int(round(pulse[i] / peak * 255 * 0.999)) if i < 31 else 0 for i in range(256))
        self.ttab = bytes(int(round(tnd[i] / peak * 255 * 0.999)) for i in range(256))

    # ------------------------------------------------------------------
    # Waveform blocks (cached). Each block holds a whole number of periods
    # so it can be repeated seamlessly.
    # ------------------------------------------------------------------
    def _periods(self, freq):
        period = self.rate / freq
        n = max(1, int(round(2048.0 / period)))
        length = max(1, int(round(n * period)))
        return n, length

    def pulse_block(self, freq, duty):
        key = (round(freq, 2), duty)
        blk = self._pulse.get(key)
        if blk is None:
            n, length = self._periods(freq)
            d = DUTIES[duty]
            step = n / float(length)
            blk = bytes(1 if ((i * step) % 1.0) < d else 0 for i in range(length))
            self._pulse[key] = blk
        return blk

    def tri_block(self, freq):
        key = round(freq, 2)
        blk = self._tri.get(key)
        if blk is None:
            n, length = self._periods(freq)
            step = n * 32.0 / length
            blk = bytes(TRI_SEQ[int(i * step) & 31] for i in range(length))
            self._tri[key] = blk
        return blk

    def noise_block(self, period_index):
        blk = self._noise.get(period_index)
        if blk is None:
            step = CPU_HZ / NOISE_PERIODS[period_index] / self.rate
            length = self.rate // 2
            lf = self.lfsr
            blk = bytes(lf[int(i * step) % 32767] for i in range(length))
            self._noise[period_index] = blk
        return blk

    # ------------------------------------------------------------------
    def render_tone(self, block, n, envelope, table_kind="vol"):
        """Repeat `block` to n samples applying a per-frame volume envelope."""
        if n <= 0:
            return b""
        reps = n // len(block) + 1
        full = block * reps
        fl = self.frame_len
        out = []
        pos = 0
        last = 0
        for v in envelope:
            if pos >= n:
                break
            end = min(n, pos + fl)
            last = v
            if table_kind == "tri":
                tbl = None if v > 0 else self.tri_mute
            else:
                tbl = self.vol[v]
            seg = full[pos:end]
            out.append(seg.translate(tbl) if tbl is not None else seg)
            pos = end
        if pos < n:
            seg = full[pos:n]
            if table_kind == "tri":
                out.append(seg if last > 0 else bytes(n - pos))
            else:
                out.append(seg.translate(self.vol[last]))
        return b"".join(out)

    def mix(self, p1, p2, tri, noise):
        """Mix four level streams into 8-bit output levels (bytes)."""
        n = max(len(p1), len(p2), len(tri), len(noise))

        def pad(b):
            return b if len(b) == n else b + bytes(n - len(b))
        p1, p2, tri, noise = pad(p1), pad(p2), pad(tri), pad(noise)
        add = operator.add
        ps = bytes(map(add, p1, p2))
        tn = bytes(map(add, tri.translate(self.x16), noise))
        return bytes(map(add, ps.translate(self.ptab), tn.translate(self.ttab)))


def levels_to_buffer(levels, fmt, channels, gain=1.0):
    """Convert 8-bit unipolar levels into a raw buffer in the mixer's format."""
    channels = max(1, channels)
    size = abs(fmt)
    if size == 8:
        if fmt > 0:   # unsigned 8-bit
            tbl = bytes(min(255, 128 + int(i * 0.5 * gain)) for i in range(256))
        else:
            tbl = bytes((int(i * 0.5 * gain)) & 0xFF for i in range(256))
        mono = levels.translate(tbl)
        if channels == 1:
            return mono
        out = bytearray(len(mono) * channels)
        for c in range(channels):
            out[c::channels] = mono
        return bytes(out)
    if size == 16:
        # silence maps to 0 so sounds start and stop without clicks
        k = 118.0 * gain
        vals = [min(32767, int(i * k)) for i in range(256)]
        if fmt > 0:   # unsigned 16-bit
            vals = [v + 32768 - 15000 for v in vals]
            vals = [max(0, min(65535, v)) for v in vals]
        else:
            vals = [v & 0xFFFF for v in vals]
        lo = bytes(v & 0xFF for v in vals)
        hi = bytes((v >> 8) & 0xFF for v in vals)
        if sys.byteorder == "big":
            lo, hi = hi, lo
        L = levels.translate(lo)
        H = levels.translate(hi)
        frame = 2 * channels
        out = bytearray(len(levels) * frame)
        for c in range(channels):
            out[2 * c::frame] = L
            out[2 * c + 1::frame] = H
        samples = array.array("H" if fmt > 0 else "h")
        samples.frombytes(bytes(out))
        return samples
    if size == 32:
        # SDL reports float32 as 32; treat it as float samples in -1..1
        k = gain / 280.0
        tbl = [i * k for i in range(256)]
        mono = array.array("f", map(tbl.__getitem__, levels))
        if channels == 1:
            return mono.tobytes()
        out = array.array("f", bytes(len(mono) * 4 * channels))
        for c in range(channels):
            out[c::channels] = mono
        return out.tobytes()
    raise ValueError("unsupported mixer format %r" % (fmt,))


def render_sfx(apu, frames):
    """Render a short effect described frame by frame.

    Each frame is a tuple (pulse1, pulse2, noise, tri):
      pulse = (freq, duty_index, volume) or None
      noise = (period_index, volume) or None
      tri   = freq or None
    A simple per-sample loop is fine here because effects are short.
    """
    fl = apu.frame_len
    rate = float(apu.rate)
    lf = apu.lfsr
    p1 = bytearray()
    p2 = bytearray()
    nz = bytearray()
    tr = bytearray()
    ph1 = ph2 = pht = 0.0
    nph = 0.0
    for fr in frames:
        a, b, c, d = (tuple(fr) + (None, None, None, None))[:4]
        if a:
            f, du, v = a
            inc = f / rate
            dd = DUTIES[du]
            buf = bytearray(fl)
            for i in range(fl):
                ph1 += inc
                if ph1 >= 1.0:
                    ph1 -= 1.0
                if ph1 < dd:
                    buf[i] = v
            p1 += buf
        else:
            p1 += bytes(fl)
        if b:
            f, du, v = b
            inc = f / rate
            dd = DUTIES[du]
            buf = bytearray(fl)
            for i in range(fl):
                ph2 += inc
                if ph2 >= 1.0:
                    ph2 -= 1.0
                if ph2 < dd:
                    buf[i] = v
            p2 += buf
        else:
            p2 += bytes(fl)
        if c:
            per, v = c
            step = CPU_HZ / NOISE_PERIODS[per] / rate
            buf = bytearray(fl)
            for i in range(fl):
                nph += step
                if lf[int(nph) % 32767]:
                    buf[i] = v
            nz += buf
        else:
            nz += bytes(fl)
        if d:
            inc = d * 32.0 / rate
            buf = bytearray(fl)
            for i in range(fl):
                pht += inc
                if pht >= 32.0:
                    pht -= 32.0
                buf[i] = TRI_SEQ[int(pht)]
            tr += buf
        else:
            tr += bytes(fl)
    return apu.mix(bytes(p1), bytes(p2), bytes(tr), bytes(nz))
