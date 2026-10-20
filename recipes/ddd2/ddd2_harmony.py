"""ddd2's harmony as the style engines need it: chord per source bar (from analyze.py's bass-per-bar and
chroma), voicings for re-synthesis, chord tones for new melodies, and helpers to lay chords on a remix.

E bars: bass E1, chroma D# F# B A#  -> Emaj9(#11)
B bars: bass B1, chroma B D# F# A#  -> Bmaj7(add9)
S68-71 (original breakdown): chroma D# F# A# C#, no bass -> D#m7
"""
import numpy as np

CHORDS = {
    "E": {"root": 28, "pad": [52, 59, 63, 66, 70], "bright": [64, 71, 75, 78], "piano": [40, 52, 59, 63, 66, 70],
          "brass": [52, 59, 63, 66], "tones": [64, 66, 68, 70, 71, 75]},  # original E colour has no G#
    "B": {"root": 35, "pad": [54, 59, 63, 66, 70], "bright": [66, 71, 75, 78], "piano": [47, 54, 59, 63, 66, 70],
          "brass": [54, 59, 63, 66], "tones": [59, 61, 63, 66, 70, 71]},
    "D#m": {"root": 27, "pad": [51, 58, 61, 66, 70], "bright": [63, 70, 73, 78], "piano": [39, 51, 58, 61, 66, 70],
            "brass": [51, 58, 61, 66], "tones": [63, 66, 70, 73]},
}


def chord_of_source_bar(S):
    if S < 20 or 92 <= S <= 99:
        return "B"
    if 68 <= S <= 71:
        return "D#m"
    if 72 <= S <= 75:
        return "B"
    if S >= 108:
        return "E" if S in (108, 109) else "B"
    return "E" if (S - 20) % 8 < 4 else "B"


def blocks(chord_by_bar, bars):
    """Group consecutive remix bars with the same chord into (start_bar, n_bars, chord) blocks."""
    out = []
    for R in sorted(bars):
        c = chord_by_bar[R]
        if out and out[-1][0] + out[-1][1] == R and out[-1][2] == c:
            out[-1][1] += 1
        else:
            out.append([R, 1, c])
    return [tuple(b) for b in out]


def reverse_bars(x, ses, b0, b1):
    """Reverse each bar of x in place between bars b0 and b1."""
    y = np.array(x, dtype=np.float64, copy=True)
    for R in range(b0, b1):
        sl = ses.span(R, R + 1)
        y[:, sl] = y[:, sl][:, ::-1]
    return y


def gate_16ths(ses, n, bars_beats, duty=0.5, fade_ms=2.0):
    """Gain curve that chops (bar, start_beat, end_beat) spans into 1/16 on/off stutters."""
    g = np.ones(n)
    f = int(fade_ms * 48)
    for R, b0, b1 in bars_beats:
        k = 0
        while b0 + k * 0.25 < b1:
            a = ses.pos(R, b0 + k * 0.25 + 0.25 * duty)
            e = ses.pos(R, b0 + (k + 1) * 0.25)
            g[a:e] = 0.0
            g[max(0, a - f):a] = np.minimum(g[max(0, a - f):a], np.linspace(1, 0, a - max(0, a - f)))
            g[e:e + f] = np.minimum(g[e:e + f], np.linspace(0, 1, min(f, n - e)))
            k += 1
    return g


def silence(ses, n, spans, fade_ms=4.0):
    """Gain curve muting (bar_start, bar_end) spans, with short fades."""
    g = np.ones(n)
    f = int(fade_ms * 48)
    for b0, b1 in spans:
        a, e = ses.pos(b0), min(n, ses.pos(b1))
        g[a:e] = 0.0
        g[max(0, a - f):a] *= np.linspace(1, 0, a - max(0, a - f))
        g[e:e + f] *= np.linspace(0, 1, min(f, n - e))
    return g
