"""Master a pre-master mix: mono sub, glue compression, soft clip, true-peak limiter, loudness target.

Usage: python3 master.py mix.npy out_basename [target_lufs]
Writes out_basename.wav (24-bit) and out_basename.mp3 (320k).
"""
import sys
import numpy as np
from scipy import ndimage
import dsp
import fx

SR = dsp.SR


def master(mix, target_lufs=-9.0, ceiling_db=-1.2, region=slice(None)):
    """target_lufs is measured over `region` (the main drop), so quieter sections keep their contrast."""
    x = dsp.sos_filter(mix.astype(np.float64), "highpass", 20, SR, 2)  # removes DC from kick/impact
    x = fx.mono_below(x, 120)
    # glue: threshold a few dB under the loud-section RMS, so only the dense parts get ~1-2 dB
    rms = 10 * np.log10(ndimage.uniform_filter1d(np.mean(x ** 2, 0), int(0.4 * SR))[::SR // 10] + 1e-12)
    thr = float(np.percentile(rms, 95)) - 2.5
    x, gr = fx.compress(x, threshold_db=thr, ratio=1.8, attack=0.02, release=0.2, knee_db=6)
    g_db = target_lufs - dsp.lufs(x[:, region])
    for _ in range(8):
        y = fx.limiter(fx.soft_clip(x * dsp.undb(g_db), 0.85), ceiling_db - 0.1)
        err = target_lufs - dsp.lufs(y[:, region])
        if abs(err) < 0.05:
            break
        g_db += err
    report = {"glue_threshold_db": round(thr, 1), "glue_gr_max_db": round(float(gr.max()), 2),
              "glue_gr_p95_db": round(float(np.percentile(gr, 95)), 2), "input_gain_db": round(g_db, 2)}
    # gain reduction of soft clip + limiter, measured on 5 ms RMS envelopes (per-sample ratios blow up
    # near zero crossings)
    pre = x * dsp.undb(g_db)
    e_pre = np.sqrt(np.maximum(ndimage.uniform_filter1d(np.mean(pre ** 2, 0), int(0.005 * SR)), 0))
    e_post = np.sqrt(np.maximum(ndimage.uniform_filter1d(np.mean(np.asarray(y, dtype=np.float64) ** 2, 0),
                                                         int(0.005 * SR)), 0))
    loud = e_pre > 0.05
    lim_gr = dsp.db(e_pre[loud]) - dsp.db(np.maximum(e_post[loud], 1e-9))
    report["limiter_gr_p99_db"] = round(float(np.percentile(lim_gr, 99)), 2)
    report["limiter_gr_max_db"] = round(float(lim_gr.max()), 2)
    return y.astype(np.float32), report


if __name__ == "__main__":
    import remix
    mix = np.load(sys.argv[1])
    base = sys.argv[2]
    target = float(sys.argv[3]) if len(sys.argv) > 3 else -9.0
    y, rep = master(mix, target, region=remix.span(80, 96))
    rep["lufs"] = round(dsp.lufs(y), 2)
    rep["true_peak_db"] = round(dsp.true_peak_db(y), 2)
    rep["sample_peak_db"] = round(float(dsp.db(np.abs(y).max())), 2)
    print(rep)
    dsp.save(base + ".wav", y)
    dsp.save(base + ".mp3", y, codec="libmp3lame", extra=("-b:a", "320k"))
