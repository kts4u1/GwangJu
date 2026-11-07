"""배경음악 합성 (저작권 걱정 없는 자체 제작 음원).

build/timeline.json의 장면 경계에 맞춰 화음이 바뀌는 앰비언트 패드,
아르페지오, 장면 전환 효과음, 강조 타악을 만들어 build/music.wav로 저장합니다.
"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
SR = 44100
tl = json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))
DUR = tl["total"]
t = np.arange(int(SR * DUR)) / SR
sc = {s["id"]: s for s in tl["scenes"]}

CHORDS = {  # MIDI 음 (장면 분위기에 맞춘 화음)
    "intro": [48, 55, 59, 64, 74], "life": [45, 52, 55, 60, 71], "packaging": [41, 53, 57, 60, 64],
    "mega": [43, 50, 55, 62, 69], "airbase": [40, 52, 55, 59, 62], "talent": [41, 53, 57, 60, 67],
    "aicity": [38, 50, 53, 57, 64], "vision": [43, 55, 59, 62, 71], "end": [48, 55, 62, 64, 71],
}
ARP_GAIN = {"intro": 0, "life": .7, "packaging": .8, "mega": 1, "airbase": .35, "talent": .9, "aicity": .9, "vision": 1, "end": .5}
note = lambda m: 440 * 2 ** ((m - 69) / 12)

pad = np.zeros_like(t)
arp = np.zeros_like(t)
for s in tl["scenes"]:
    a, b, notes = s["start"], s["end"], CHORDS[s["id"]]
    env = np.clip((t - a + .9) / 1.8, 0, 1) * np.clip((b + .9 - t) / 1.8, 0, 1)
    for i, n in enumerate(notes):
        f, ph = note(n), i * 1.7
        v = np.sin(2 * np.pi * f * t + ph) + .3 * np.sin(2 * np.pi * 2 * f * t + ph) + .1 * np.sin(2 * np.pi * 3 * f * t)
        lfo = .75 + .25 * np.sin(2 * np.pi * (.09 + .03 * i) * t + ph)
        pad += v * lfo * env * (.5 if n < 50 else .3)
    g = ARP_GAIN[s["id"]]
    if g:
        pattern = [2, 3, 4, 3]
        for k, st in enumerate(np.arange(a + .5, b - .3, .5)):
            f = note(notes[pattern[k % 4]] + 12)
            n0 = int(st * SR); n1 = min(len(t), n0 + int(SR * 1.2))
            tt = np.arange(n1 - n0) / SR
            arp[n0:n1] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3.4) * .16 * g


def boom(at, amp=1.0):
    out = np.zeros_like(t); n0 = int(at * SR); tt = t[n0:] - at
    f = 55 * np.exp(-tt * 1.2) + 32
    out[n0:] = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.8) * amp
    return out


def whoosh(at, length=1.0, amp=.12, seed=0):
    out = np.zeros_like(t); n0 = max(0, int((at - length) * SR)); n1 = min(len(t), int((at + .25) * SR))
    tt = np.arange(n1 - n0) / SR
    env = np.clip(tt / length, 0, 1) ** 2 * np.clip((n1 - n0) / SR - tt, 0, .25) / .25
    noise = np.random.default_rng(seed).normal(0, 1, n1 - n0)
    out[n0:n1] = np.convolve(noise, np.ones(30) / 30, "same") * env * amp
    return out


def kicks(a, b, amp=.35):
    out = np.zeros_like(t)
    for st in np.arange(a, b, .5):
        n0 = int(st * SR); n1 = min(len(t), n0 + int(SR * .35)); tt = np.arange(n1 - n0) / SR
        f = 45 + 75 * np.exp(-tt * 30)
        out[n0:n1] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * amp
    return out


fx = boom(.6, .9) + boom(sc["mega"]["start"] + .35, .8) + boom(sc["airbase"]["cues"][3]["start"], .5) + boom(sc["end"]["start"] + .3, 1.0)
for i, s in enumerate(tl["scenes"][1:]):
    fx += whoosh(s["start"] + .35, 1.2 if s["id"] in ("mega", "end") else .8, .14 if s["id"] in ("mega", "end") else .07, i)
drums = kicks(sc["mega"]["start"] + 1.2, sc["mega"]["end"] - .5) + kicks(sc["vision"]["cues"][0]["start"], sc["vision"]["end"] - .3, .3)

mix = pad * .2 + arp + fx + drums
ir_len = int(SR * 2.4)
ir = np.random.default_rng(9).normal(0, 1, ir_len) * np.exp(-np.arange(ir_len) / SR * 2.6)
ir /= np.abs(ir).sum() / 12
nfft = 1 << int(np.ceil(np.log2(len(mix) + ir_len)))
wet = np.fft.irfft(np.fft.rfft(mix, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(mix)]
out = mix * .75 + wet * .35
out *= np.clip(t / 1.0, 0, 1) * np.clip((DUR - t) / 2.0, 0, 1)
out = out / np.abs(out).max() * .8
st = np.stack([out, np.roll(out, int(SR * .012))], 1)
with wave.open(os.path.join(BUILD, "music.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print(f"music.wav {DUR:.1f}s")
