"""
ECG PQRST Simulator — Teaching & Demo Version (clinic-oriented)

• Models a lead-like ECG as a sum of Gaussian waves per beat: P, Q, R, S, T
• Adds optional baseline wander (respiration), measurement noise, mains hum
• Supports irregular RR (AFib-like), widened QRS (LBBB/RBBB), ST-elevation,
  T-wave inversion, and PVC bigeminy patterns
• Includes ready-to-use PRESETS for fast scenarios

Dependencies: numpy, matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt

# ----------------------------
# Helpers
# ----------------------------

def _gauss(x, mu, sigma, amp):
    """Simple Gaussian used for each wave component."""
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def _make_rr_series(duration, base_hr, irregular=False, seed=7):
    """
    Construct RR-intervals (seconds) over 'duration'.
    Clinical note:
      - Regular sinus: near-constant RR around 60/hr seconds
      - AFib-like: highly irregular RR (use lognormal variability)
    """
    rng = np.random.default_rng(seed)
    base_rr = 60.0 / float(base_hr)
    rr = []

    if not irregular:
        # Mild physiologic variability (~2% std)
        rr_std = 0.02 * base_rr
        while sum(rr) < duration + 1.0:
            rr.append(rng.normal(base_rr, rr_std))
    else:
        # AFib-like: irregular, short-long pattern—lognormal gives skew
        # (still clipped to physiologic bounds)
        while sum(rr) < duration + 1.0:
            candidate = rng.lognormal(mean=np.log(base_rr), sigma=0.25)
            rr.append(candidate)

    rr = np.clip(rr, 0.40, 2.0)  # physiologic range
    r_times = np.cumsum(rr)
    return r_times[r_times < (duration + 1.0)]

# ----------------------------
# Core ECG Synthesis
# ----------------------------

def simulate_ecg(
    duration=10.0,        # seconds
    fs=500,               # Hz (sampling)
    hr=70,                # bpm
    morphology=None,      # dict of waves {P,Q,R,S,T} with {amp, mu, sigma}
    irregular_rr=False,   # True -> AFib-like irregular RR (suppresses P in presets)
    wide_qrs=False,       # True -> broaden QRS (bundle-branch-block look)
    rbbb=False,           # Right bundle branch block skew
    lbbb=False,           # Left bundle branch block skew
    st_shift=0.0,         # mV ST elevation (>0) or depression (<0)
    t_inverted=False,     # invert T wave
    pvc_bigeminy=False,   # every other beat = PVC (early, wide, no P, opposite T)
    baseline_wander_hz=0.25,  # respiratory drift (~15 bpm)
    baseline_wander_amp=0.03, # mV
    noise_std=0.02,       # mV measurement noise
    mains_hz=None,        # 50 or 60 to add hum
    seed=13
):
    """
    Returns:
      t (s), ecg (mV), meta (dict)
    Clinical reading notes inline in comments below.
    """
    rng = np.random.default_rng(seed)
    n = int(duration * fs)
    t = np.arange(n) / fs
    ecg = np.zeros_like(t, dtype=float)

    # --- Default morphology relative to R-peak at 0.0 s ---
    # Clinical meaning:
    #   P: atrial depolarization (small +ve bump before QRS)
    #   QRS: ventricular depolarization (sharp complex)
    #   T: ventricular repolarization (wider, usually +ve)
    waves = {
        "P": {"amp": 0.20, "mu": -0.20, "sigma": 0.025},
        "Q": {"amp": -0.05,"mu": -0.040,"sigma": 0.010},
        "R": {"amp": 1.00, "mu":  0.000,"sigma": 0.012},
        "S": {"amp": -0.15,"mu":  0.040,"sigma": 0.010},
        "T": {"amp": 0.30, "mu":  0.300,"sigma": 0.060},
    }
    if morphology:
        for k, v in morphology.items():
            waves[k].update(v)

    # --- Options that alter morphology in clinically familiar ways ---

    # QRS widening (bundle branch blocks)
    if wide_qrs or rbbb or lbbb:
        # Base widening
        waves["Q"]["sigma"] = max(waves["Q"]["sigma"], 0.016)
        waves["R"]["sigma"] = max(waves["R"]["sigma"], 0.026)
        waves["S"]["sigma"] = max(waves["S"]["sigma"], 0.020)

        # Slight timing skew: RBBB pushes terminal forces (+S) a bit later
        # LBBB often shows broad/notched R; we model with a small R delay
        if rbbb:
            waves["S"]["mu"] += 0.01
        if lbbb:
            waves["R"]["mu"] += 0.008

    # T-wave inversion
    if t_inverted:
        waves["T"]["amp"] = -abs(waves["T"]["amp"])

    # AFib-like: no organized P-waves (we’ll suppress P amplitude below)
    if irregular_rr:
        waves["P"]["amp"] = 0.0  # no distinct P (f-waves are not modeled here)

    # RR series
    r_times = _make_rr_series(duration, hr, irregular=irregular_rr, seed=seed)

    # PVC template (very simplified but illustrative)
    pvc_profile = {
        "P": {"amp": 0.0,  "mu": -0.20, "sigma": 0.025},  # no P before PVC
        "Q": {"amp": -0.10,"mu": -0.060,"sigma": 0.020},
        "R": {"amp": 0.90, "mu":  0.000,"sigma": 0.040},  # wide R
        "S": {"amp": -0.20,"mu":  0.060,"sigma": 0.030},
        "T": {"amp": -0.25,"mu":  0.320,"sigma": 0.070},  # opposite-polarity T
    }

    # --- Build ECG as sum of Gaussians around each R-time ---
    # We draw each beat in a local window for efficiency.
    for i, r0 in enumerate(r_times):
        is_pvc = pvc_bigeminy and (i % 2 == 1)  # every second beat

        # Choose morphology for this beat
        beatspec = pvc_profile if is_pvc else waves

        # Draw waves within a window around the beat
        mask = (t >= (r0 - 0.6)) & (t <= (r0 + 0.7))
        tw = t[mask]
        if tw.size == 0:
            continue

        beat = np.zeros_like(tw)
        for name, p in beatspec.items():
            mu = r0 + p["mu"]
            beat += _gauss(tw, mu, p["sigma"], p["amp"])

        # ST-shift: apply a small offset to ST segment (post-QRS pre-T onset)
        # Clinical simplification: add constant offset between S end and T onset
        if abs(st_shift) > 1e-6:
            st_start = r0 + beatspec["S"]["mu"] + 2.5 * beatspec["S"]["sigma"]
            t_onset  = r0 + beatspec["T"]["mu"] - 2.5 * beatspec["T"]["sigma"]
            st_mask = (tw >= st_start) & (tw <= t_onset)
            beat[st_mask] += st_shift

        ecg[mask] += beat

    # Baseline wander (respiration)
    if baseline_wander_amp and baseline_wander_hz:
        ecg += baseline_wander_amp * np.sin(2 * np.pi * baseline_wander_hz * t)

    # Mains hum (optional)
    if mains_hz in (50, 60):
        ecg += 0.01 * np.sin(2 * np.pi * mains_hz * t)

    # Measurement noise
    if noise_std and noise_std > 0:
        ecg += rng.normal(0.0, noise_std, size=t.shape)

    meta = {
        "fs": fs,
        "hr": hr,
        "beats": len(r_times),
        "irregular_rr": irregular_rr,
        "wide_qrs": wide_qrs,
        "rbbb": rbbb,
        "lbbb": lbbb,
        "st_shift": st_shift,
        "t_inverted": t_inverted,
        "pvc_bigeminy": pvc_bigeminy,
    }
    return t, ecg, meta

# ----------------------------
# Presets (quick clinical scenarios)
# ----------------------------

def ecg_preset(name):
    """
    Return kwargs for simulate_ecg() to model common scenarios.
    You can tweak returned dict before passing into simulate_ecg().
    """
    base = dict(duration=8.0, fs=500, hr=70, noise_std=0.02,
                baseline_wander_hz=0.25, baseline_wander_amp=0.02, mains_hz=None)

    presets = {
        "normal": dict(),
        "afib": dict(irregular_rr=True, hr=90),             # no P, irregular RR
        "lbbb": dict(wide_qrs=True, lbbb=True),
        "rbbb": dict(wide_qrs=True, rbbb=True),
        "stemi": dict(st_shift=0.2),                        # ST elevation ~0.2 mV
        "pvc_bigeminy": dict(pvc_bigeminy=True, hr=72),
        "t_inversion": dict(t_inverted=True),
    }
    base.update(presets.get(name.lower(), {}))
    return base

# ----------------------------
# Demo / Usage
# ----------------------------

if __name__ == "__main__":
    # Choose one: "normal", "afib", "lbbb", "rbbb", "stemi", "pvc_bigeminy", "t_inversion"
    scenario = "normal"

    params = ecg_preset(scenario)
    # You can tweak further, e.g.:
    # params["hr"] = 78
    # params["st_shift"] = 0.1

    t, ecg, meta = simulate_ecg(**params)

    # Plot (single chart)
    plt.figure(figsize=(12, 3))
    plt.plot(t, ecg, linewidth=1.2)
    plt.xlabel("Time (s)")
    plt.ylabel("ECG (mV)")
    plt.title(f"ECG Simulation — {scenario}  |  HR={meta['hr']} bpm")
    plt.tight_layout()
    plt.show()

# CONFIGRATIONS:
# =============
# 
# Change scenario = "normal" to a preset you want ("afib", "lbbb", "rbbb", "stemi", "pvc_bigeminy", "t_inversion").
# 
# Optional: tweak params (e.g., params["hr"] = 85 or params["st_shift"] = 0.15).
#
# Run ==> single-plot ECG with clinically annotated behavior in the code.
# 
# renders a clear, single-plot ECG with clinically annotated behavior in the code.
    
