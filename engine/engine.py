"""Remix engine: a Session holds the strict grid, the (optionally time-stretched) source layers and
the helpers recipes use to arrange bars, program parts, automate, mix and save stems.
"""
import os
import json
import numpy as np
from scipy import signal
import dsp
import fx
import synth

SR = dsp.SR
WORK = os.environ.get("REMIX_WORK", "work")
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def scale_pcs(key_name):
    """'B major' / 'D# minor' -> set of pitch classes."""
    tonic, mode = key_name.split()
    t = dsp.NOTE_NAMES.index(tonic)
    if mode == "minor":
        t = (t + 3) % 12  # relative major
    return {(t + s) % 12 for s in MAJOR}


class Auto:
    """Per-sample automation curve written in bars."""

    def __init__(self, ses, default):
        self.s = ses
        self.v = np.full(ses.N, float(default))

    def set(self, b0, b1, v0, v1=None, shape="lin"):
        sl = self.s.span(b0, b1)
        n = sl.stop - sl.start
        if n <= 0:
            return self
        if v1 is None:
            self.v[sl] = v0
        elif shape == "exp":
            self.v[sl] = v0 * (v1 / v0) ** np.linspace(0, 1, n)
        else:
            p = shape if isinstance(shape, float) else 1.0
            self.v[sl] = v0 + (v1 - v0) * np.linspace(0, 1, n) ** p
        return self

    def smooth(self, ms=20.0):
        """Turn steps into short ramps (a gain that jumps on a sustained sound clicks)."""
        from scipy import ndimage
        self.v = ndimage.uniform_filter1d(self.v, max(1, int(ms * SR / 1000)))
        return self


class Session:
    def __init__(self, name, analysis, harm, perc, total_bars, stretch=1.0, seed=11):
        self.name = name
        self.an = json.load(open(analysis))
        self.stretch = stretch
        self.bpm = self.an["bpm"] * stretch
        self.spb = 60.0 / self.bpm * SR
        self.total = total_bars
        self.N = int(round(total_bars * 4 * self.spb))
        self.rng = np.random.default_rng(seed)
        # rubberband's constant-ratio stretch maps time linearly (checked: the bed's pumping dip sits at
        # 23.4% of the beat before and after), so source beats simply scale. Kick-onset detectors are
        # not reliable on stretched material because transients get smeared.
        src_beats = np.array(self.an["beats"]) / stretch
        self.harm = self._layer(harm, "harm")
        self.perc = self._layer(perc, "perc") if perc else None
        self.src_bar_t = src_beats[self.an["downbeat_phase"]::4]
        self.key = scale_pcs(self.an["key_rank"][0][0])
        self.bass_src = np.array(self.an.get("beat_bass_harm_midi", self.an["beat_bass_midi"]))

    def _layer(self, path, tag):
        x = np.load(path, mmap_mode="r")
        if self.stretch == 1.0:
            return x
        cache = f"{WORK}/{self.name}_{tag}_x{self.stretch}.npy"
        if not os.path.exists(cache):
            np.save(cache, fx.rubberband(np.asarray(x), tempo=self.stretch).astype(np.float32))
        return np.load(cache, mmap_mode="r")

    # ---- grid
    def pos(self, bar, beat=0.0):
        return int(round((bar * 4 + beat) * self.spb))

    def span(self, b0, b1):
        return slice(self.pos(b0), min(self.N, self.pos(b1)))

    def auto(self, default):
        return Auto(self, default)

    def stem(self):
        return np.zeros((2, self.N), np.float32)

    # ---- placement
    def add(self, dst, snd, at, gain=1.0, pan=0.0):
        if snd.ndim == 1:
            th = (pan + 1) * np.pi / 4
            snd = np.stack([snd * np.cos(th), snd * np.sin(th)])
        if at < 0:
            snd, at = snd[:, -at:], 0
        b = min(self.N, at + snd.shape[1])
        if at < self.N and b > at:
            dst[:, at:b] += gain * snd[:, :b - at]

    def hits(self, dst, sound, bars, steps, gain=1.0, vel=None, pan=0.0, swing=0.0, rand=0.0, mute=(),
             jitter_ms=0.0, late_ms=0.0):
        """Place `sound` on 16th-note steps (0-15, may be fractional) in each bar of `bars`.
        swing delays odd 16ths by that fraction of a 16th; jitter_ms adds random +-timing (off-grid feel);
        late_ms pushes every hit late (laid-back snares). Returns the sample positions used."""
        out = []
        for R in sorted(bars):
            for i, st in enumerate(steps):
                beat = st / 4
                if (R, int(beat)) in mute:
                    continue
                if swing and int(st) % 2 == 1 and st == int(st):
                    beat += swing / 4
                g = gain * (vel[i % len(vel)] if vel else 1.0) * self.rng.uniform(1 - rand, 1 + rand)
                p = self.pos(R, beat) + int(late_ms * SR / 1000)
                if jitter_ms:
                    p += int(self.rng.uniform(-jitter_ms, jitter_ms) * SR / 1000)
                self.add(dst, sound, max(0, p), g, pan)
                out.append(max(0, p))
        return out

    # ---- source
    def assemble(self, layer, mapping, pre=0.006, jump_tail=0.04):
        """Place source bar S at remix bar R for each (R, S), crossfading in the pre-roll before downbeats."""
        out = self.stem()
        p = int(pre * SR)
        for j, (R, S) in enumerate(mapping):
            contiguous = j + 1 < len(mapping) and mapping[j + 1] == (R + 1, S + 1)
            t = p if contiguous else int(jump_tail * SR)
            a = int(round(self.src_bar_t[S] * SR)) - p
            length = self.pos(R + 1) - self.pos(R) + t
            seg = np.asarray(layer[:, max(0, a):a + length], dtype=np.float32)
            if a < 0:
                seg = np.pad(seg, ((0, 0), (-a, 0)))
            if seg.shape[1] < length:
                seg = np.pad(seg, ((0, 0), (0, length - seg.shape[1])))
            env = np.ones(length, np.float32)
            env[:p] = np.linspace(0, 1, p)
            env[-t:] = np.linspace(1, 0, t)
            o = self.pos(R) - p
            if o < 0:
                seg, env, o = seg[:, -o:], env[-o:], 0
            e = min(self.N, o + seg.shape[1])
            out[:, o:e] += (seg * env)[:, :e - o]
        return out

    def root(self, S, lo=28, hi=39):
        """Majority bass root of source bar S, snapped to the key and folded into [lo, hi]."""
        k = self.an["downbeat_phase"] + 4 * S
        notes = []
        for v in self.bass_src[k:k + 4]:
            r = int(round(v))
            pc = r % 12
            if pc not in self.key:
                pc = min(self.key, key=lambda q: (min((q - pc) % 12, (pc - q) % 12), q))
                r = r - r % 12 + pc
            while r > hi:
                r -= 12
            while r < lo:
                r += 12
            notes.append(r)
        vals, counts = np.unique(notes, return_counts=True)
        return int(vals[np.argmax(counts)])


class Mixer:
    """Calibrates each stem to a short-term LUFS target over reference bars, saves it, sums it."""

    def __init__(self, ses, targets, tag):
        self.s = ses
        self.targets = targets
        self.tag = tag
        self.mix = np.zeros((2, ses.N), np.float64)
        self.gains = {}

    def add(self, name, x, gain_db=None):
        if gain_db is None:
            target, (b0, b1) = self.targets[name]
            gain_db = target - dsp.lufs(np.asarray(x)[:, self.s.span(b0, b1)])
        self.gains[name] = round(float(gain_db), 1)
        x = (np.asarray(x) * dsp.undb(gain_db)).astype(np.float32)
        np.save(f"{WORK}/{self.tag}_stem_{name}.npy", x)
        self.mix += x

    def save(self):
        np.save(f"{WORK}/{self.tag}_mix.npy", self.mix.astype(np.float32))


# ---------------------------------------------------------------- shared processing

def duck(ses, triggers, depth_db, release=0.12, attack=0.004):
    """Sidechain gain curve; depth_db may be a number or an Auto curve (depth varying over the track)."""
    base_db = dsp.db(fx.duck_curve(ses.N, triggers, 1.0, attack=attack, release=release))
    d = depth_db.v if isinstance(depth_db, Auto) else depth_db
    return dsp.undb(base_db * d)


def bed_chain(ses, bed, hpf, lpf, gain, triggers, duck_lo=3.0, duck_hi=1.0, release=0.12,
              width=1.2, send=None, ir=None, blur_mix=None, blur_regions=(), blur_s=None):
    """Blur (optional) -> HPF/LPF automation -> two-band sidechain -> width -> gain -> reverb send."""
    bed = np.asarray(bed, dtype=np.float64)
    if blur_mix is not None:
        blurred = np.zeros_like(bed)
        for b0, b1 in blur_regions:
            sl = ses.span(max(0, b0 - 1), b1 + 1)
            blurred[:, sl] = fx.spectral_blur(bed[:, sl], blur_s or 1.6 * ses.spb / SR)
        bed = bed * (1 - blur_mix.v) + blurred * blur_mix.v
    else:
        blurred = None
    bed = fx.tv_filter(bed, "highpass", hpf.v)
    bed = fx.tv_filter(bed, "lowpass", lpf.v)
    if len(triggers):
        lo = dsp.sos_filter(bed, "lowpass", 400, SR, 2)
        bed = lo * duck(ses, triggers, duck_lo, release) + (bed - lo) * duck(ses, triggers, duck_hi, release)
    bed = fx.widen(bed, width) * dsp.undb(gain.v)
    wet = fx.reverb(bed * send.v, ir) if send is not None else 0.0
    return bed + wet, blurred


def snare_roll(ses, dst, sound, b0, bars=4, level=1.0, end_beat=3.0, pitch_up=0.55):
    """Quarters -> 8ths -> 16ths -> 32nds over `bars` bars, stopping at end_beat of the last bar."""
    hits = []
    for i in range(bars):
        div = [1, 2, 4, 8][min(3, i + 4 - bars)]
        for k in range(4 * div):
            beat = k / div
            if i == bars - 1 and beat >= end_beat:
                break
            hits.append((b0 + i) * 4 + beat)
    first, last = hits[0], hits[-1]
    for h in hits:
        u = (h - first) / max(1e-9, last - first)
        n = int(len(sound) / (1 + pitch_up * u))
        snd = np.interp(np.arange(n) * (1 + pitch_up * u), np.arange(len(sound)), sound)
        ses.add(dst, snd, int(round(h * ses.spb)), level * (0.25 + 0.75 * u ** 1.5), pan=0.1)


def reverse_swell(ses, dst, bed_raw, bar, ir, beats=2, gain=0.6):
    chord = np.asarray(bed_raw[:, ses.pos(bar):ses.pos(bar, 1)])
    sw = synth.reverse_swell(chord, ir)
    n = int(beats * ses.spb)
    ses.add(dst, sw[:, -n:] * np.linspace(0, 1, n) ** 1.5, ses.pos(bar) - n, gain)


def chop(ses, bed_raw, bar, beat=1.5, semitones=12, decay=0.07, length_beats=0.5):
    """A short slice of the bed (between kicks), resampled by `semitones`, with a pluck envelope."""
    ratio = 2 ** (semitones / 12)
    n_out = int(length_beats * ses.spb)
    src = np.asarray(bed_raw[:, ses.pos(bar, beat):ses.pos(bar, beat) + int(n_out * ratio) + 2], dtype=np.float64)
    idx = np.arange(n_out) * ratio
    y = np.stack([np.interp(idx, np.arange(src.shape[1]), c) for c in src])
    t = np.arange(n_out) / SR
    return y * np.minimum(t / 0.003, 1) * np.exp(-t / decay)


def wobble(x, depth_cents=40, rate_hz=1.5):
    """Tape-style pitch wobble that keeps the length (mean speed 1)."""
    x = fx.as_stereo(x)
    n = x.shape[1]
    t = np.arange(n) / SR
    speed = 2 ** (depth_cents / 1200 * np.sin(2 * np.pi * rate_hz * t))
    pos = np.cumsum(speed)
    pos = (pos - pos[0]) * (n - 1) / (pos[-1] - pos[0])
    return np.stack([np.interp(pos, np.arange(n), c) for c in x])


def lofi_texture(n, level=1.0, seed=5):
    """Vinyl crackle + soft hiss, stereo."""
    rng = np.random.default_rng(seed)
    hiss = dsp.sos_filter(rng.standard_normal((2, n)), "bandpass", (1500, 9000), SR, 1) * 0.08
    clicks = np.zeros((2, n))
    for c in range(2):
        idx = rng.integers(0, n, int(n / SR * 9))
        clicks[c, idx] = rng.uniform(-1, 1, len(idx)) * rng.uniform(0.2, 1, len(idx)) ** 3
    clicks = dsp.sos_filter(clicks, "highpass", 1200, SR, 1)
    return (hiss + clicks) * level
