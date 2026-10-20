"""Render a recipe: build the pre-master mix, master it, write WAV/MP3, run objective checks.

Usage (from the repo root): python3 engine/render.py recipes/<track>/<recipe>.py [--skip-mix] [--target -9.0]
Outputs: out/<TAG>.wav (24-bit), out/<TAG>.mp3 (320k), out/<TAG>_check.png, checks printed to stdout.
The recipe module defines ses (engine.Session), SECTIONS, TAG, MASTER_REGION, main(), and optionally
MASTER_TARGET, BASS_BARS/BASS_STEMS/SRC_OF (bass-follows-original check) and
CHORD_STEMS/HARMONY_REF/CHORD_BARS (re-synthesized harmony check).
"""
import os
import sys
import importlib
import numpy as np
from scipy import signal
import dsp
import engine
from master import master

W = engine.WORK


def short_term(x, win=3.0, hop=0.5):
    out = []
    for t in np.arange(0, x.shape[1] / dsp.SR - win, hop):
        seg = x[:, int(t * dsp.SR):int((t + win) * dsp.SR)]
        out.append((t + win / 2, dsp.lufs(seg) if np.abs(seg).max() > 1e-4 else -70))
    return np.array(out)


def checks(rec, y, out_base, src_path):
    ses = rec.ses
    print(f"length {y.shape[1] / dsp.SR:.1f}s  LUFS {dsp.lufs(y):.2f}  TP {dsp.true_peak_db(y):.2f} dBTP  "
          f"DC {np.abs(y.mean(1)).max():.5f}  clipped {(np.abs(y) >= 0.999).sum()}")
    mp3 = dsp.load(out_base + ".mp3")
    print(f"mp3: TP {dsp.true_peak_db(mp3):.2f} dBTP")
    print("section       bars      LUFS")
    for name, r0, nb, _ in rec.SECTIONS:
        print(f"  {name:10s} {r0:3d}-{r0 + nb:3d}  {dsp.lufs(y[:, ses.span(r0, r0 + nb)]):6.1f}")

    bed = np.load(f"{W}/{rec.TAG}_stem_bed.npy")
    # synthesized bass must follow the original bass line: compare pitch class per bar
    bass_bars, src_of = getattr(rec, "BASS_BARS", set()), getattr(rec, "SRC_OF", {})
    bass = None
    for stem_name in getattr(rec, "BASS_STEMS", ["bass"]):
        try:
            s = np.load(f"{W}/{rec.TAG}_stem_{stem_name}.npy").mean(0)
            bass = s if bass is None else bass + s
        except FileNotFoundError:
            pass
    if bass is not None and bass_bars:
        wrong, total = [], 0
        for r in sorted(bass_bars):
            seg = bass[ses.pos(r):ses.pos(r + 1)]
            if np.abs(seg).max() < 1e-3 or r not in src_of:
                continue
            # 80 ms inside one note, mid-bar (a train of retriggered notes has a comb spectrum, and a
            # previous chord's release can still overlap the downbeat)
            n = int(0.08 * dsp.SR)
            a = ses.pos(r, 1.5) - ses.pos(r) + int(0.005 * dsp.SR)
            spec = np.abs(np.fft.rfft(seg[a:a + n] * np.hanning(len(seg[a:a + n])), 1 << 18))
            f = np.fft.rfftfreq(1 << 18, 1 / dsp.SR)
            f0 = f[np.argmax(spec * (f > 28) * (f < 130))]
            pc = int(round(69 + 12 * np.log2(f0 / 440))) % 12
            want = ses.root(src_of[r]) % 12
            total += 1
            if pc != want:
                wrong.append((r, dsp.NOTE_NAMES[pc], dsp.NOTE_NAMES[want]))
        print(f"bass follows original bass line: {total - len(wrong)}/{total} bars; mismatches {wrong[:8]}")

    # re-synthesized chord layers must carry the same harmony as the original, bar by bar
    chord_stems = getattr(rec, "CHORD_STEMS", [])
    if chord_stems:
        def chroma_bars(x, bar_list):
            Sc = dsp.stft_mag(signal.resample_poly(x, 1, 2), 8192, 1200)
            C = dsp.chroma(Sc, 24000, 8192, fmin=100, fmax=4000)
            fps = 24000 / 1200
            return {r: C[:, int(ses.pos(r) / dsp.SR * fps):int(ses.pos(r + 1) / dsp.SR * fps)].mean(1) for r in bar_list}
        ref = sum(np.load(f"{W}/{rec.TAG}_stem_{s}.npy").mean(0) for s in getattr(rec, "HARMONY_REF", ["bed"]))
        syn = sum(np.load(f"{W}/{rec.TAG}_stem_{s}.npy").mean(0) for s in chord_stems)
        cbars = sorted(getattr(rec, "CHORD_BARS", range(ses.total - 2)))
        cr, cs = chroma_bars(ref, cbars), chroma_bars(syn, cbars)
        corr = {r: float(np.corrcoef(cr[r], cs[r])[0, 1]) for r in cbars if cs[r].sum() > 0 and cr[r].sum() > 0}
        # correlation also drops when both play the same chord with different emphasis, so the clash test
        # is: how much of the new layer's energy sits on pitch classes the original isn't playing
        out_of_chord = {}
        for r in corr:  # 'playing' = the original's five strongest pitch classes in that bar
            absent = ~np.isin(np.arange(12), np.argsort(cr[r])[-5:])
            out_of_chord[r] = float(cs[r][absent].sum() / (cs[r].sum() + 1e-12))
        bad = sorted(((round(v, 2), r) for r, v in out_of_chord.items() if v > 0.25), reverse=True)
        print(f"re-synth harmony vs original over {len(corr)} bars: median chroma corr {np.median(list(corr.values())):.2f}; "
              f"energy on pitch classes the original isn't playing: median {np.median(list(out_of_chord.values())):.0%}, "
              f"bars above 25%: {bad[:8]}")

    # clicks: >8 kHz burst right at bar boundaries vs the same measure at mid-bar positions
    hi = dsp.sos_filter(bed.mean(0), "highpass", 8000, dsp.SR, 4)

    def burst(p):
        core = np.sqrt(np.mean(hi[p - 72:p + 72] ** 2) + 1e-12)
        ctx = np.sqrt(np.mean(np.r_[hi[p - 2000:p - 200], hi[p + 200:p + 2000]] ** 2) + 1e-12)
        return float(dsp.db(core) - dsp.db(ctx))
    at_bound = [burst(ses.pos(r) - int(0.003 * dsp.SR)) for r in range(1, ses.total - 2)]
    mid_bar = [burst(ses.pos(r + 0.5)) for r in range(1, ses.total - 2)]
    print(f"splice clicks: boundary burst median {np.median(at_bound):+.1f} / max {max(at_bound):+.1f} dB; "
          f"mid-bar reference median {np.median(mid_bar):+.1f} / max {max(mid_bar):+.1f} dB")

    x = dsp.load(src_path)

    def bands(z):
        f, p = signal.welch(z.mean(0), dsp.SR, nperseg=16384)
        ref = p[(f >= 250) & (f < 2000)].mean()
        return [10 * np.log10(p[(f >= lo) & (f < 2 * lo)].mean() / ref) for lo in (25, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800)]
    print("octave bands vs own 250-2k (25 Hz ... 12.8 kHz):")
    print("  original " + " ".join(f"{v:+5.1f}" for v in bands(x)))
    print("  remix    " + " ".join(f"{v:+5.1f}" for v in bands(y)))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(18, 8))
    st = short_term(y)
    ax[0].plot(st[:, 0], st[:, 1])
    for name, r0, nb, _ in rec.SECTIONS:
        ax[0].axvline(ses.pos(r0) / dsp.SR, color="gray", lw=0.6)
        ax[0].text(ses.pos(r0) / dsp.SR + 0.5, -6.5, name, fontsize=8)
    ax[0].set_ylim(-30, -5)
    fz, tz, Z = signal.stft(y.mean(0)[::2], dsp.SR / 2, nperseg=2048, noverlap=1024)
    Zdb = 20 * np.log10(np.abs(Z) + 1e-9)
    ax[1].pcolormesh(tz, fz, Zdb, vmin=Zdb.max() - 90, vmax=Zdb.max(), cmap="magma", shading="auto")
    ax[1].set_yscale("symlog", linthresh=200)
    ax[1].set_ylim(30, 12000)
    plt.tight_layout()
    plt.savefig(out_base + "_check.png", dpi=60)


def load_recipe(arg):
    """Import a recipe by file path (its folder goes on sys.path so sibling modules resolve) or by name."""
    if arg.endswith(".py"):
        path = os.path.abspath(arg)
        sys.path.insert(0, os.path.dirname(path))
        return importlib.import_module(os.path.splitext(os.path.basename(path))[0])
    return importlib.import_module(arg)


def main():
    rec = load_recipe(sys.argv[1])
    os.makedirs("out", exist_ok=True)
    target = float(sys.argv[sys.argv.index("--target") + 1]) if "--target" in sys.argv else \
        getattr(rec, "MASTER_TARGET", -9.0)
    if "--skip-mix" not in sys.argv:
        rec.main()
    mix = np.load(f"{W}/{rec.TAG}_mix.npy")
    y, rep = master(mix, target, region=rec.ses.span(*rec.MASTER_REGION))
    print(rep)
    out_base = f"out/{rec.TAG}"
    dsp.save(out_base + ".wav", y)
    dsp.save(out_base + ".mp3", y, codec="libmp3lame", extra=("-b:a", "320k"))
    checks(rec, dsp.load(out_base + ".wav"), out_base, rec.ses.an["file"])


if __name__ == "__main__":
    main()
