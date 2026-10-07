"""Synthesises the ambient sound loops and footsteps (original, procedural).

Loops are built in the frequency domain so they repeat seamlessly.
Run:  python tools/build_audio.py
"""
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'audio'
ROOT.mkdir(parents=True, exist_ok=True)
RATE = 22050
RNG = np.random.default_rng(91)


def spectral_noise(seconds, shape):
    n = int(RATE * seconds)
    f = np.fft.rfftfreq(n, 1 / RATE)
    spec = (RNG.normal(size=f.size) + 1j * RNG.normal(size=f.size)) * shape(np.maximum(f, 1.0))
    x = np.fft.irfft(spec, n)
    return x / (np.abs(x).max() + 1e-9)


def periodic_env(n, cycles, seed, depth=0.6):
    t = np.arange(n) / n
    r = np.random.default_rng(seed)
    env = np.ones(n)
    for k in range(1, 4):
        env += depth / k * np.sin(2 * np.pi * (cycles * k) * t + r.uniform(0, 6.28))
    return np.clip(env / env.max(), 0.05, 1.0)


def save(name, x, gain=0.8):
    x = np.clip(x / (np.abs(x).max() + 1e-9) * gain, -1, 1)
    data = (x * 32767).astype('<i2').tobytes()
    with wave.open(str(ROOT / f'{name}.wav'), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)
    print('AUDIO', name, round(len(x) / RATE, 2), 's')


def wind():
    secs = 16
    low = spectral_noise(secs, lambda f: 1 / f ** 1.1 * np.exp(-f / 900))
    high = spectral_noise(secs, lambda f: np.exp(-((f - 600) / 400) ** 2))
    n = low.size
    gust = periodic_env(n, 3, 1, 0.8)
    whistle = periodic_env(n, 5, 2, 1.0) ** 3
    save('wind', low * gust + high * whistle * 0.25, 0.7)


def rain():
    secs = 8
    hiss = spectral_noise(secs, lambda f: np.exp(-((f - 3500) / 2600) ** 2) + 0.3 / f ** 0.3)
    n = hiss.size
    drops = np.zeros(n)
    idx = RNG.integers(0, n - 400, 900)
    for i in idx:
        L = RNG.integers(60, 300)
        drops[i:i + L] += np.sin(np.arange(L) * RNG.uniform(0.6, 1.4)) * np.exp(-np.arange(L) / (L / 4)) * RNG.uniform(0.1, 0.5)
    save('rain', hiss * 0.6 + drops * 0.5, 0.65)


def waves():
    secs = 18
    surf = spectral_noise(secs, lambda f: 1 / f ** 0.9 * np.exp(-f / 2500))
    rumble = spectral_noise(secs, lambda f: np.exp(-f / 120))
    n = surf.size
    t = np.arange(n) / n
    swell = np.zeros(n)
    for k, ph in ((3, 0.0), (5, 1.7), (2, 3.1)):
        swell += np.clip(np.sin(2 * np.pi * k * t + ph), 0, None) ** 3
    swell = swell / swell.max()
    save('waves', surf * (0.15 + swell) + rumble * 0.4, 0.7)


def crickets():
    secs = 6
    n = int(RATE * secs)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for voice in range(5):
        f0 = RNG.uniform(3800, 5200)
        rate = RNG.uniform(1.0, 2.2) * 6 / secs
        rate = round(rate * secs) / secs
        phase = RNG.uniform(0, 1)
        chirp_env = (np.sin(2 * np.pi * (t * rate + phase)) > 0.6).astype(float)
        pulses = (np.sin(2 * np.pi * 30 * t) > 0).astype(float)
        out += np.sin(2 * np.pi * f0 * t) * chirp_env * pulses * RNG.uniform(0.3, 1.0)
    out += spectral_noise(secs, lambda f: np.exp(-f / 300)) * 0.05
    save('crickets', out, 0.4)


def birds():
    secs = 14
    n = int(RATE * secs)
    out = np.zeros(n)
    for k in range(9):
        start = RNG.integers(0, n - RATE)
        notes = RNG.integers(2, 6)
        pos = start
        base = RNG.uniform(2200, 3800)
        for j in range(notes):
            L = int(RATE * RNG.uniform(0.06, 0.16))
            tt = np.arange(L) / RATE
            sweep = base * (1 + RNG.uniform(-0.3, 0.4) * tt / tt[-1])
            ph = 2 * np.pi * np.cumsum(sweep) / RATE
            seg = np.sin(ph) * np.sin(np.pi * np.arange(L) / L) ** 2 * RNG.uniform(0.4, 1.0)
            end = min(n, pos + L)
            out[pos:end] += seg[:end - pos]
            pos += L + int(RATE * RNG.uniform(0.03, 0.12))
    out += spectral_noise(secs, lambda f: 1 / f) * 0.04
    save('birds', out, 0.35)


def thunder():
    secs = 5
    n = int(RATE * secs)
    t = np.arange(n) / RATE
    rumble = spectral_noise(secs, lambda f: np.exp(-f / 90) + 0.2 * np.exp(-f / 600))
    crack = spectral_noise(secs, lambda f: np.exp(-((f - 1500) / 1500) ** 2))
    env = np.exp(-t / 1.6) * (1 - np.exp(-t / 0.05))
    env2 = np.exp(-t / 0.18)
    roll = 0.6 + 0.4 * np.sin(2 * np.pi * 1.3 * t) * np.exp(-t / 2)
    save('thunder', rumble * env * roll + crack * env2 * 0.5, 0.95)


def step(name, centre, width, decay, seconds=0.22, extra=None):
    n = int(RATE * seconds)
    t = np.arange(n) / RATE
    x = spectral_noise(seconds, lambda f: np.exp(-((f - centre) / width) ** 2) + 0.15 / f ** 0.5)
    env = np.exp(-t / decay) * (1 - np.exp(-t / 0.003))
    y = x * env
    if extra is not None:
        y += extra(t)
    save(name, y, 0.8)


def main():
    wind()
    rain()
    waves()
    crickets()
    birds()
    thunder()
    step('step_soft', 500, 700, 0.045)
    step('step_stone', 2200, 1800, 0.03, extra=lambda t: np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.02) * 0.3)
    step('step_wood', 300, 400, 0.05, extra=lambda t: np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.05) * 0.8)


if __name__ == '__main__':
    main()
