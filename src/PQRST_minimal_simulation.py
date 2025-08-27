import numpy as np
import matplotlib.pyplot as plt

def ecg_wave(duration=10, fs=500, hr=60):
    # Time axis
    t = np.arange(0, duration, 1/fs)
    ecg = np.zeros_like(t)

    # Default morphology (relative to R=0 sec)
    waves = {
        "P": {"amp": 0.2,  "mu": -0.2,  "sigma": 0.025},
        "Q": {"amp": -0.05,"mu": -0.04, "sigma": 0.010},
        "R": {"amp": 1.0,  "mu": 0.0,   "sigma": 0.012},
        "S": {"amp": -0.15,"mu": 0.04,  "sigma": 0.010},
        "T": {"amp": 0.3,  "mu": 0.3,   "sigma": 0.060},
    }

    # Compute RR interval
    rr = 60.0 / hr
    r_times = np.arange(0, duration, rr)

    # Build ECG beat by beat
    for r in r_times:
        for w in waves.values():
            ecg += w["amp"] * np.exp(-0.5 * ((t - (r + w["mu"])) / w["sigma"])**2)

    return t, ecg

# Run example: 10 s at 70 bpm
t, ecg = ecg_wave(duration=10, fs=500, hr=70)

plt.figure(figsize=(10,3))
plt.plot(t, ecg)
plt.xlabel("Time (s)")
plt.ylabel("ECG (mV)")
plt.title("Synthetic ECG (PQRST)")
plt.tight_layout()
plt.show()
