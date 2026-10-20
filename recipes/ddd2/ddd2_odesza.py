"""ddd2, ODESZA-style remix engine: recontextualize and enlarge. Style emulation only; the chop melody,
piano figure, brass voicings and drum cadences are new, written from your own chord tones.

Moves (from the research notes): tempo eased 136 -> 124 BPM with pitch kept; a pitched-up formant
'vocal chop' hook (formants shifted +20% for the 'another vocalist' effect) with breath transients and
tape-delay throws; CS-80-style brass swells with aftertouch vibrato, chord changes pushed 1/8 early in the
builds; additive piano and FM chimes for the intimate parts; slow strings; a half-time organic pocket
(saturated clap+snap, swung shakers, toms) and marching-snare drumline builds with flams; Decapitator-style
grit, Dopamine-style air ramped into the drops, Devil-Loc-crushed reverb pumping under; tape hiss and
room tone as a 'memory' bed; your tidal-wave sub kept whole, with 2nd-harmonic saturation so it translates.
Usage (repo root): python3 engine/render.py recipes/ddd2/ddd2_odesza.py
"""
import numpy as np
import dsp
import fx
import synth
import engine
import sounddesign as sd
from engine import Session, Mixer, reverse_swell
from ddd2_harmony import CHORDS, chord_of_source_bar, blocks, silence

SR = dsp.SR
W = engine.WORK
TAG = "ddd2_odesza"
SECTIONS = [
    ("memory", 0, 8, 0),
    ("verse", 8, 16, 20),
    ("drumline", 24, 8, 44),
    ("drop", 32, 16, 52),
    ("strip", 48, 4, 84),
    ("breakdown", 52, 8, 68),
    ("final_build", 60, 8, 92),
    ("wave", 68, 8, 100),
    ("wave2", 76, 8, 100),
    ("outro", 84, 4, 108),
    ("coda", 88, 4, 0),
]
END = 92
ses = Session("ddd2", "tracks/ddd2/analysis.json", f"{W}/ddd2_harm.npy", f"{W}/ddd2_perc.npy", END + 2,
              stretch=124 / 136, seed=22)
MAPPING = [(r0 + i, s0 + i) for _, r0, nb, s0 in SECTIONS for i in range(nb)]
SRC_OF = dict(MAPPING)
CHORD = {R: chord_of_source_bar(S) for R, S in MAPPING}
CHORD.update({R: "E" for R in range(4, 8)})  # intro piano moves to E over the B drone (shared B, D#, A#)
CHORD.update({R: "B" for R in range(END, END + 2)})


def bars(*ranges):
    out = set()
    for a, b in ranges:
        out.update(range(a, b))
    return out


GROOVE = bars((12, 31), (32, 52), (68, 84))
SHAKER = bars((8, 31), (32, 52), (66, 86))
CADENCE = bars((68, 84))
HOOK_BARS = bars((16, 24), (32, 52), (68, 88))
DISTANT_HOOK = bars((4, 8))
PIANO_BARS = bars((0, 8), (52, 60), (84, 92))
BRASS_BARS = bars((8, 48), (60, 84))
PUSH_BARS = bars((24, 32), (60, 84))  # brass chord changes land 1/8 early here
STRING_BARS = bars((52, 60), (76, 84))
BELL_BARS = bars((8, 24), (68, 84))
SUB_BARS = bars((32, 52))  # synth sub + mid-bass in drop 1; the original sub carries the waves
BASS_BARS, BASS_STEMS = SUB_BARS, ["sub"]
CHORD_BARS = BRASS_BARS  # harmony check: brass voicings vs the original bed
CHORD_STEMS, HARMONY_REF = ["brass"], ["bed"]
MUTE = {(31, 3), (47, 3), (51, 3), (67, 3), (83, 3)}

KICK = synth.kick(f_end=61.74, f_start=220, pitch_tau=0.02, body_tau=0.1, click=0.5, drive=1.6)  # B1, round
CLAP = sd.decapitator(synth.clap(decay=0.14) + 0.6 * np.pad(sd.snap(), (0, int(0.45 * SR) - len(sd.snap()))),
                      drive_db=8, mix=0.5)
SHAKE = sd.shaker(0.03)
TOM_LO, TOM_HI = synth.tom(98, decay=0.22), synth.tom(131, decay=0.2)
MSNARE = sd.marching_snare()
BASS_DRUM = synth.kick(f_end=82.4, f_start=140, pitch_tau=0.02, body_tau=0.18, click=0.3, drive=1.3)
HALL = fx.make_ir(rt60=4.0, predelay=0.03, seed=91)
VAST = fx.make_ir(rt60=6.0, predelay=0.045, hi_damp=0.55, seed=92)
ROOM = fx.make_ir(rt60=0.8, predelay=0.01, seed=93)
DOTTED8 = 0.75 * ses.spb / SR

TARGETS = {"bed": (-16.5, (32, 48)), "chops": (-20.5, (32, 48)), "brass": (-21.0, (32, 48)),
           "piano": (-20.0, (52, 60)), "strings": (-25.0, (52, 60)), "bells": (-28.0, (8, 24)),
           "sub": (-18.5, (32, 48)), "midbass": (-23.0, (32, 48)), "sat2": (-24.0, (68, 84)),
           "kick": (-17.5, (32, 48)), "clap": (-21.5, (32, 48)), "shaker": (-29.0, (32, 48)),
           "toms": (-27.0, (32, 48)), "snare": (-21.5, (24, 32)), "memory": (-36.0, (0, 8)),
           "crush": (-27.0, (68, 84))}
MASTER_REGION = (76, 84)
MASTER_TARGET = -9.0

# 4-bar chop phrases per chord: (16th step, length in 16ths, MIDI note, vowel). New melody from chord tones.
HOOK = {
    "E": [[(0, 2, 75, "ah"), (3, 1, 78, "oh"), (4, 2, 78, "ah"), (6, 2, 80, "ee"), (10, 1, 78, "oh"), (11, 1, 75, "ah"), (12, 4, 71, "oh")],
          [(0, 2, 71, "ah"), (2, 2, 75, "eh"), (4, 1, 76, "ah"), (5, 1, 75, "oh"), (6, 2, 71, "ah"), (10, 2, 70, "oh"), (12, 4, 71, "oo")],
          [(0, 2, 78, "ah"), (3, 1, 80, "oh"), (4, 2, 80, "ah"), (6, 2, 83, "ee"), (10, 1, 82, "oh"), (11, 1, 80, "ah"), (12, 4, 78, "ah")],
          [(0, 2, 75, "ah"), (2, 1, 78, "eh"), (3, 1, 75, "oh"), (4, 4, 71, "oh"), (12, 1, 78, "ah"), (13, 1, 78, "ah"), (14, 1, 78, "ah")]],
    "B": [[(0, 2, 75, "ah"), (3, 1, 78, "oh"), (4, 2, 78, "ah"), (6, 2, 82, "ee"), (10, 1, 78, "oh"), (11, 1, 75, "ah"), (12, 4, 73, "oh")],
          [(0, 2, 73, "ah"), (2, 2, 75, "eh"), (4, 1, 78, "ah"), (5, 1, 75, "oh"), (6, 2, 73, "ah"), (10, 2, 70, "oh"), (12, 4, 71, "oo")],
          [(0, 2, 78, "ah"), (3, 1, 82, "oh"), (4, 2, 82, "ah"), (6, 2, 85, "ee"), (10, 1, 82, "oh"), (11, 1, 78, "ah"), (12, 4, 75, "ah")],
          [(0, 2, 71, "ah"), (2, 1, 73, "eh"), (3, 1, 75, "oh"), (4, 4, 78, "ah"), (12, 1, 75, "ah"), (13, 1, 75, "ah"), (14, 1, 75, "ah")]],
}
PIANO_FIGURE = [(2, 3), (4, 4), (6, 5), (8, 4), (10, 3), (12, 4), (14, 2)]  # (16th step, voicing index)


def src_span(S0, S1):
    return int(ses.src_bar_t[S0] * SR), int(ses.src_bar_t[S1] * SR)


# ---------------------------------------------------------------- drums

def drums():
    st = {k: ses.stem() for k in ("kick", "clap", "shaker", "toms", "snare")}
    trig = []
    rng = np.random.default_rng(41)
    for R in sorted(GROOVE):
        trig += ses.hits(st["kick"], KICK, {R}, [0, 7, 10] if R % 2 == 0 else [0, 10], mute=MUTE, jitter_ms=2)
        trig += ses.hits(st["clap"], CLAP, {R}, [8], mute=MUTE, jitter_ms=5)
        if R % 4 == 3:
            ses.hits(st["toms"], TOM_HI, {R}, [13], mute=MUTE)
            ses.hits(st["toms"], TOM_LO, {R}, [15], mute=MUTE)
    for R in sorted(SHAKER):
        ses.hits(st["shaker"], SHAKE, {R}, range(16), vel=[0.45, 0.6, 1.0, 0.6], pan=-0.25, swing=0.08, rand=0.2,
                 mute=MUTE, jitter_ms=6)
    for R in sorted(CADENCE):  # light drumline cadence riding the wave
        ses.hits(st["snare"], MSNARE, {R}, [0, 2, 3, 6, 8, 10, 11, 14], vel=[0.9, 0.35, 0.5, 0.7, 0.8, 0.35, 0.5, 0.75],
                 gain=0.5, pan=0.15, mute=MUTE, jitter_ms=4)
    for b0, level in ((24, 1.0), (60, 1.0)):  # drumline builds into each drop
        for i in range(8):
            R = b0 + i
            div = [1, 1, 2, 2, 4, 4, 8, 1][i]
            for k in range(4 * div):
                beat = k / div
                if i == 7 and beat >= 3:
                    break
                u = (i * 4 + beat) / 32
                g = level * dsp.undb(-9 + 9 * u)  # +9 dB crescendo
                p = ses.pos(R, beat) + int(rng.uniform(-3, 3) * 48)
                ses.add(st["snare"], MSNARE, p, g, pan=0.1)
                if div == 1:  # flams on the quarter-note sections
                    ses.add(st["snare"], MSNARE, p - int(0.025 * SR), g * dsp.undb(-8), pan=-0.1)
            if i < 7:
                for beat in (0, 2):
                    ses.add(st["kick"], BASS_DRUM, ses.pos(R, beat), 0.8)
                    trig.append(ses.pos(R, beat))
            if i >= 6:
                for k, tom in enumerate((TOM_HI, TOM_LO, TOM_HI, TOM_LO)):
                    if i == 7 and k >= 3:
                        break
                    ses.add(st["toms"], tom, ses.pos(R, k), 0.7 + 0.1 * k)
    st["clap"] = st["clap"] + 0.3 * fx.reverb(st["clap"], HALL)
    st["snare"] = st["snare"] + 0.25 * fx.reverb(st["snare"], HALL)
    st["toms"] = st["toms"] + 0.3 * fx.reverb(st["toms"], HALL)
    st["kick"] = sd.decapitator(st["kick"], drive_db=6, mix=0.3)
    return st, trig


# ---------------------------------------------------------------- melodic layers

def chop_hook(trig):
    out, throws = ses.stem(), ses.stem()
    rng = np.random.default_rng(7)
    sixteenth = ses.spb / 4 / SR
    for R in sorted(HOOK_BARS | DISTANT_HOOK):
        c = CHORD[R] if CHORD[R] in HOOK else "B"
        k = (R - (32 if R >= 32 else 16 if R >= 16 else 4)) % 4
        phrase = HOOK[c][k]
        if R in bars((16, 24)) and k % 2 == 1:
            phrase = phrase[:3]  # verse: the hook only half-formed
        for j, (st, ln, m, v) in enumerate(phrase):
            y = sd.vocal_chop(sd.midi_hz(m), ln * sixteenth * 0.92, vowel=v, shift=1.2, q=10, breath=0.1, seed=R * 16 + j)
            p = ses.pos(R, st / 4) + int(rng.uniform(-10, 10) * 48)
            g = 0.55 if R in DISTANT_HOOK else rng.uniform(0.8, 1.0)
            ses.add(out, y, p, g, pan=rng.uniform(-0.15, 0.15))
            if k == 3 and st >= 12:  # throw the last stutter of every phrase into the tape delay
                ses.add(throws, y, p, g)
    out = sd.decapitator(out, drive_db=9, mix=0.45)
    wet = 0.3 * fx.reverb(out, HALL) + 0.1 * sd.tape_delay(out, DOTTED8, feedback=0.35) + \
        0.8 * sd.tape_delay(throws, DOTTED8, feedback=0.45, taps=8)
    far = ses.auto(0.0).set(4, 8, 1.0).smooth().v  # intro motif: distant, drowned in a vast hall
    out = out * (1 - 0.7 * far) + fx.reverb(out * far, VAST) * 1.2
    return (out + wet) * engine.duck(ses, trig, 3.0, release=0.2)


def brass_layer():
    out = ses.stem()
    for R0, nb, c in blocks(CHORD, BRASS_BARS):
        push = int(0.5 * ses.spb) if R0 in PUSH_BARS and R0 - 1 in BRASS_BARS else 0
        length = (ses.pos(R0 + nb) - ses.pos(R0) + push) / SR + 0.6
        y = sd.brass(CHORDS[c]["brass"], length, attack=0.25, cut0=600, cut1=3000, after=1.0, seed=R0)
        ses.add(out, y, ses.pos(R0) - push)
    sweep = sd.smooth_curve(ses.auto(21000).set(60, 68, 400, 8000, "exp").v)  # brass sweep through the final build
    out = fx.tv_filter(out, "lowpass", sweep)
    out = out * dsp.undb(ses.auto(0.0).set(8, 24, -12.0).set(24, 32, -12.0, 0.0).smooth().v)  # verse: a pad under it all
    return out + 0.45 * fx.reverb(out, VAST)


_piano_cache = {}


def piano(m, length, vel):
    key = (m, length, round(vel, 1))  # additive synthesis is slow; reuse notes at the same velocity step
    if key not in _piano_cache:
        _piano_cache[key] = sd.piano_note(m, length, vel=key[2], seed=m)
    return _piano_cache[key]


def piano_layer():
    out = ses.stem()
    rng = np.random.default_rng(11)
    for R in sorted(PIANO_BARS):
        v = CHORDS[CHORD[R]]["piano"]
        for i, m in enumerate(v):  # rolled chord on beat 1
            ses.add(out, piano(m, 3.5, 0.55 + 0.1 * rng.random()), ses.pos(R) + i * int(0.025 * SR), 0.8,
                    pan=-0.3 + 0.12 * i)
        for st, idx in PIANO_FIGURE:
            ses.add(out, piano(v[idx] + (12 if R >= 84 and st >= 8 else 0), 1.8, 0.45 + 0.15 * rng.random()),
                    ses.pos(R, st / 4) + int(rng.uniform(-8, 8) * 48), 0.6, pan=0.2 * np.sin(st))
    wow = engine.wobble(out, depth_cents=12, rate_hz=0.5)
    w = ses.auto(0.0).set(0, 8, 1.0).set(8, 9, 1.0, 0.0).smooth().v
    out = out * (1 - w) + wow * w
    return out + 0.5 * fx.reverb(out, VAST)


def strings_layer():
    out = ses.stem()
    for R0, nb, c in blocks(CHORD, STRING_BARS):
        length = (ses.pos(R0 + nb) - ses.pos(R0)) / SR + 1.5
        ses.add(out, sd.strings_pad(CHORDS[c]["bright"], length, attack=1.2, release=2.0, seed=R0), ses.pos(R0))
    return out + 0.4 * fx.reverb(out, VAST)


def bells_layer():
    out = ses.stem()
    rng = np.random.default_rng(13)
    for R in sorted(BELL_BARS):
        tones = CHORDS[CHORD[R]]["tones"]
        for st in ((0, 10) if R % 2 == 0 else (6, 14)):
            ses.add(out, sd.fm_bell(sd.midi_hz(rng.choice(tones) + 12)), ses.pos(R, st / 4), rng.uniform(0.5, 0.9),
                    pan=rng.uniform(-0.6, 0.6))
    return out + 0.4 * fx.reverb(out, HALL) + 0.2 * sd.tape_delay(out, DOTTED8)


def bass_layers(trig):
    sub, mid = ses.stem(), ses.stem()
    for R0, nb, c in blocks(CHORD, SUB_BARS):
        length = (ses.pos(R0 + nb) - ses.pos(R0)) / SR + 0.2
        ses.add(sub, synth.wave_bass(CHORDS[c]["root"], length, decay_db=3.0 * nb / 4, attack=0.012), ses.pos(R0))
    eighth = ses.spb / 2
    for R in sorted(SUB_BARS):
        f = sd.midi_hz(CHORDS[CHORD[R]]["root"] + 12)
        for k in range(8):
            if (R, k // 2) in MUTE:
                continue
            n = int(eighth * 0.7)
            y = dsp.sos_filter(sd.saw(f, n) + sd.saw(f * 2 ** (6 / 1200), n, 0.5), "lowpass", 900, SR, 2)
            ses.add(mid, sd.fade(np.tanh(2 * y), 0.004, 0.03), ses.pos(R, k / 2), 1.0 if k % 2 else 0.75)
    d = engine.duck(ses, trig, 5.0, release=0.18)
    return sub * d, sd.tube(mid, drive=2.0) * d


# ---------------------------------------------------------------- source treatment

def bed_layer(bed_raw, trig):
    clean = np.asarray(bed_raw, dtype=np.float64)
    warm = sd.decapitator(clean, drive_db=8, mix=0.3)
    memory = engine.wobble(dsp.sos_filter(clean, "lowpass", 3000, SR, 2), depth_cents=15, rate_hz=0.5)
    m = ses.auto(0.0).set(0, 8, 1.0).set(8, 9, 1.0, 0.0).set(87, 88, 0.0, 1.0).set(88, END + 2, 1.0).smooth(60).v
    bed = warm * (1 - m) + memory * m
    hpf = ses.auto(20.0).set(28, 31.875, 20, 800, "exp").set(31.875, 32, 800).set(32, 48, 110).set(48, 52, 300) \
        .set(52, 60, 60)
    lpf = ses.auto(21000).set(48, 52, 1500).set(84, 88, 21000, 1200, "exp").set(88, END + 2, 3000, 500, "exp")
    bed = fx.tv_filter(bed, "highpass", sd.smooth_curve(hpf.v))
    bed = fx.tv_filter(bed, "lowpass", sd.smooth_curve(lpf.v))
    air = ses.auto(0.0).set(24, 32, 0.0, 1.0).set(32, 48, 1.0).set(60, 68, 0.0, 1.0).set(68, 84, 1.0).smooth(60).v
    bed = bed + (sd.exciter(bed, amount_db=-12) - bed) * air
    lo = dsp.sos_filter(bed, "lowpass", 400, SR, 2)
    bed = lo * engine.duck(ses, trig, 4.0, release=0.2) + (bed - lo) * engine.duck(ses, trig, 2.0, release=0.2)
    gain = ses.auto(0.0).set(0, 2, -30, -8, 0.5).set(2, 8, -8).set(8, 24, -1.0).set(48, 52, -10.0).set(52, 60, -4.0) \
        .set(84, 88, -3.0).set(88, 92, -6.0, -30.0).set(92, END + 2, -90).smooth()
    return bed * dsp.undb(gain.v)


def sat2(bed_raw, trig):
    """Your wave sub with added 2nd-harmonic warmth (80-300 Hz) so it reads on small speakers."""
    low = dsp.sos_filter(np.asarray(bed_raw, dtype=np.float64), "lowpass", 110, SR, 4) * \
        ses.auto(0.0).set(68, 84, 1.0).set(84, 84.5, 1.0, 0.0).smooth(40).v
    return dsp.sos_filter(sd.tube(low, drive=3.0, bias=0.3), "bandpass", (80, 300), SR, 2) * \
        engine.duck(ses, trig, 3.0, release=0.15)


def memory_bed():
    n = ses.N
    tex = sd.tape_hiss(n) + 0.6 * sd.room_tone(n)
    return tex * ses.auto(0.0).set(0, 8, 1.0).set(8, 10, 1.0, 0.0).set(52, 60, 0.7).set(84, END + 2, 1.0).smooth(60).v


def fx_layer(bed_raw):
    out = ses.stem()
    for b in (32, 68):
        ses.add(out, synth.impact(), ses.pos(b), 0.8)
        ses.add(out, synth.crash(), ses.pos(b), 0.35)
    ses.add(out, synth.riser(8 * 4 * ses.spb / SR, f0=400, f1=10000, seed=95), ses.pos(60), 0.45)
    ses.add(out, synth.riser(4 * 4 * ses.spb / SR, f0=600, f1=8000, seed=96), ses.pos(28), 0.35)
    for b in (32, 52, 56, 68, 84):  # reversed reverb swells into chord changes and drops
        reverse_swell(ses, out, bed_raw, b, VAST, gain=0.6)
    return out + 0.3 * fx.reverb(out, HALL)


def main():
    print(f"{TAG}: {ses.bpm:.3f} BPM, {ses.total} bars, {ses.N / SR:.1f}s")
    bed_raw = ses.assemble(ses.harm, MAPPING)
    m = Mixer(ses, TARGETS, TAG)
    st, trig = drums()
    for k in list(st):
        m.add(k, st.pop(k))
    print("drums done")
    bed = bed_layer(bed_raw, trig)
    m.add("bed", bed)
    m.add("sat2", sat2(bed_raw, trig))
    sub, mid = bass_layers(trig)
    m.add("sub", sub)
    m.add("midbass", mid)
    del sub, mid
    chops = chop_hook(trig)
    m.add("chops", chops)
    brass = brass_layer()
    m.add("brass", brass)
    # Devil-Loc-style crushed reverb of brass + chops + bed, pumping under the drops
    crush_src = (np.load(f"{W}/{TAG}_stem_brass.npy") + np.load(f"{W}/{TAG}_stem_chops.npy") +
                 np.load(f"{W}/{TAG}_stem_bed.npy")) * ses.auto(0.0).set(32, 48, 1.0).set(68, 84, 1.0).smooth(40).v
    m.add("crush", sd.devil_loc(fx.reverb(crush_src, HALL)) * engine.duck(ses, trig, 6.0, release=0.2))
    del bed, chops, brass, crush_src
    m.add("piano", piano_layer())
    m.add("strings", strings_layer())
    m.add("bells", bells_layer())
    m.add("memory", memory_bed())
    f = fx_layer(bed_raw)
    m.add("fx", f, gain_db=-9.0 - dsp.db(np.abs(f).max()))
    print("stem gains dB:", m.gains)

    fxs = np.load(f"{W}/{TAG}_stem_fx.npy")  # gaps: half-beat before each breakdown phrase, beat before drops
    g = silence(ses, ses.N, [(31.875, 32), (55.875, 56), (59.875, 60), (67.75, 68)])
    mix = (m.mix - fxs) * g + fxs
    T = END + 2
    section = ses.auto(0.0).set(0, 8, -3.0).set(8, 24, -2.5).set(24, 32, -2.5, -0.5).set(32, 48, -0.8) \
        .set(48, 52, -3.0).set(52, 60, -4.0).set(60, 68, -3.0, -0.5).set(68, 76, -0.8).set(84, 88, -2.0) \
        .set(88, T, -3.0).smooth()
    m.mix = mix * dsp.undb(section.v)
    m.save()
    print(f"pre-master: integrated {dsp.lufs(m.mix):.2f} LUFS, peak {dsp.db(np.abs(m.mix).max()):.2f} dBFS")


if __name__ == "__main__":
    main()
