# Minimal ECG (PQRST) with two toggles: noise + wide QRS
#	Normal, clean: ecg_wave(hr=70, noise=False, wide_qrs=False)
#	Bundle-branch-block look with noise: ecg_wave(hr=70, noise=True, wide_qrs=True)
# Requires: numpy, matplotlib

import numpy as np
import matplotlib.pyplot as plt

def ecg_wave(duration=10.0, fs=500, hr=60, noise=False, wide_qrs=False):
    """
    Returns (t, ecg) where:
      t   : time vector (s)
      ecg : synthetic ECG (mV, arbitrary scale)

    Toggles:
      noise     : add light white noise
      wide_qrs  : broaden QRS complex (bundle-branch-block–like look)
    """
    t = np.arange(0, duration, 1/fs)
    ecg = np.zeros_like(t)

    # Base morphology (relative to R at 0.0 s)
    waves = {
        "P": {"amp": 0.20, "mu": -0.20, "sigma": 0.025},
        "Q": {"amp": -0.05,"mu": -0.040,"sigma": 0.010},
        "R": {"amp": 1.00, "mu":  0.000,"sigma": 0.012},
        "S": {"amp": -0.15,"mu":  0.040,"sigma": 0.010},
        "T": {"amp": 0.30, "mu":  0.300,"sigma": 0.060},
    }

    # Toggle: widen QRS
    if wide_qrs:
        waves["R"]["sigma"] = 0.026
        waves["S"]["sigma"] = 0.020
        waves["Q"]["sigma"] = 0.018

    # RR interval (seconds)
    rr = 60.0 / float(hr)
    r_times = np.arange(0, duration, rr)

    # Build ECG as sum of Gaussians per beat
    for r in r_times:
        for w in waves.values():
            mu = r + w["mu"]
            ecg += w["amp"] * np.exp(-0.5 * ((t - mu) / w["sigma"])**2)

    # Toggle: light measurement noise
    if noise:
        rng = np.random.default_rng(0)
        ecg += rng.normal(0.0, 0.02, size=t.shape)

    return t, ecg

if __name__ == "__main__":
    # Example 1: clean, normal QRS
    t1, ecg1 = ecg_wave(duration=8, fs=500, hr=70, noise=False, wide_qrs=False)

    # Example 2: noisy, wide QRS
    t2, ecg2 = ecg_wave(duration=8, fs=500, hr=70, noise=True, wide_qrs=True)

    # Plot
    plt.figure(figsize=(12,4))
    plt.plot(t1, ecg1, label="Normal QRS (clean)")
    plt.plot(t2, ecg2, label="Wide QRS + noise", alpha=0.9)
    plt.xlabel("Time (s)")
    plt.ylabel("ECG (a.u.)")
    plt.title("Synthetic ECG (PQRST) — minimal with two toggles")
    plt.legend()
    plt.tight_layout()
    plt.show()
