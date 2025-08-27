# Synthetic ECG (PQRST) generator
# - Sum-of-Gaussians morphology per beat
# - Adjustable HR, variability, sampling rate, noise & baseline wander
# - Optional mains interference (50/60 Hz)
# - Saves a PNG and CSV when run as a script

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def _gaussian(x, mu, sigma, amp):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def make_ecg(
    duration_s=10.0,
    fs=500,
    hr_bpm=60,
    hr_std=1.5,             # beat-to-beat variability (bpm std)
    powerline_hz=None,      # set to 50 or 60 to add mains noise
    noise_std=0.02,         # mV (white noise)
    baseline_amp=0.05,      # mV baseline wander amplitude
    baseline_hz=0.33,       # Hz (respiratory ~ 0.2–0.4 Hz)
    morphology=None,        # dict to override wave params (amp/mu/sigma)
    seed=7
):
    """
    Returns (t, ecg) where:
      t   : time vector (seconds)
      ecg : synthetic ECG in mV

    Morphology keys: "P","Q","R","S","T"
      - amp  : mV       (e.g., R~1.0)
      - mu   : sec from R-peak (R at 0.0)
      - sigma: sec (approx width/2.355)
    """
    rng = np.random.default_rng(seed)
    n = int(duration_s * fs)
    t = np.arange(n) / fs
    ecg = np.zeros_like(t, dtype=float)

    # --- Default morphology relative to R=0s ---
    default = {
        "P": {"amp": 0.25, "mu": -0.20, "sigma": 0.025},
        "Q": {"amp": -0.05,"mu": -0.035,"sigma": 0.010},
        "R": {"amp": 1.00, "mu":  0.000,"sigma": 0.012},
        "S": {"amp": -0.15,"mu":  0.040,"sigma": 0.010},
        "T": {"amp": 0.35, "mu":  0.300,"sigma": 0.060},
    }
    if morphology:
        for k, v in morphology.items():
            default[k].update(v)

    # --- RR intervals with small variability ---
    base_rr = 60.0 / hr_bpm
    rr_std = (hr_std / (hr_bpm**2)) * 60.0   # approx bpm->sec std
    rr = rng.normal(loc=base_rr, scale=rr_std, size=int(np.ceil(duration_s / base_rr) + 4))
    rr = np.clip(rr, 0.4, 2.0)
    r_times = np.cumsum(rr)
    r_times = r_times[r_times < (duration_s + 1.0)]

    # --- Synthesize beat by beat in a local window ---
    for r in r_times:
        mask = (t >= (r - 0.6)) & (t <= (r + 0.7))
        tw = t[mask]
        if tw.size == 0:
            continue
        beat = np.zeros_like(tw)
        for name, p in default.items():
            mu = r + p["mu"]
            beat += _gaussian(tw, mu, p["sigma"], p["amp"])
        ecg[mask] += beat

    # --- Baseline wander (respiratory) ---
    if baseline_amp and baseline_hz:
        ecg += baseline_amp * np.sin(2 * np.pi * baseline_hz * t)

    # --- Mains interference (optional) ---
    if powerline_hz is not None:
        ecg += 0.01 * np.sin(2 * np.pi * powerline_hz * t)

    # --- White measurement noise ---
    if noise_std:
        ecg += rng.normal(0.0, noise_std, size=t.shape)

    return t, ecg


if __name__ == "__main__":
    # Example: 12 s, 500 Hz, ~72 bpm
    t, ecg = make_ecg(
        duration_s=12.0,
        fs=500,
        hr_bpm=72,
        hr_std=2.0,
        powerline_hz=None,   # set to 50 or 60 if needed
        noise_std=0.02,
        baseline_amp=0.03,
        baseline_hz=0.25,
        seed=42
    )

    # Save CSV
    df = pd.DataFrame({"time_s": t, "ecg_mV": ecg})
    df.to_csv("synthetic_ecg.csv", index=False)

    # Plot and save PNG (single chart, default colors)
    import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 3))
    plt.plot(t, ecg, linewidth=1.2)
    plt.xlabel("Time (s)")
    plt.ylabel("ECG (mV)")
    plt.title("Synthetic ECG (PQRST)")
    plt.tight_layout()
    plt.savefig("synthetic_ecg.png", dpi=200)
    plt.show()
