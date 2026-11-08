"""나레이션 생성 + 타임라인 계산.

script.json의 각 문장을 edge-tts(한국어 신경망 음성)로 합성하고,
문장 사이 간격을 정리해 하나의 나레이션 트랙(build/narration.wav),
장면·자막·단어 타이밍(build/timeline.json), 자막 파일(build/subtitles.srt)을 만듭니다.
단어 타이밍은 화면의 숫자를 나레이션이 그 숫자를 말하는 순간에 맞춰 띄우는 데 씁니다.
"""
import asyncio, hashlib, json, os, subprocess, sys, wave
import numpy as np
import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
SR = 48000
FRAME = 0.01        # 무음 분석 단위 (초)

# 타이밍 (초)
LEAD = 6.0          # 첫 장면: 지도(대한민국 → 광주) 확대 후 첫 나레이션
SCENE_PRE = 1.3     # 장면 전환 후 첫 문장까지
SCENE_POST = 1.5    # 장면 마지막 문장 끝 ~ 다음 장면 시작
GAP_SENT = 0.55     # 문장 끝(.) 다음 간격
GAP_CLAUSE = 0.15   # 쉼표·이어지는 구절 다음 간격
END_POST = 6.0      # 엔딩 문장 후 영상 끝까지
MAX_PAUSE = 0.38    # 문장 안 쉼(쉼표 등) 최대 길이
EXTRA_PRE = {"mega": 0.0}   # 장면별 추가 여유가 필요하면 지정


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, "<i2").astype(np.float32) / 32768


def tighten(x, thr_db=-42):
    """앞뒤 무음 제거, 문장 안의 긴 쉼은 MAX_PAUSE로 줄임.
    원래 시각 → 새 시각 변환에 쓰도록 남긴 프레임 목록도 돌려줍니다."""
    n = int(SR * FRAME)
    frames = len(x) // n
    rms = np.sqrt(np.mean(x[:frames * n].reshape(frames, n) ** 2, axis=1) + 1e-12)
    loud = 20 * np.log10(rms) > thr_db
    idx = np.flatnonzero(loud)
    if len(idx) == 0:
        return x, np.arange(frames)
    first, last = idx[0], idx[-1]
    kept, run = [], 0
    keep = int(MAX_PAUSE / FRAME)
    for f in range(max(0, first - 3), min(frames, last + 6)):
        run = 0 if loud[f] else run + 1
        if run <= keep:
            kept.append(f)
    kept = np.array(kept)
    y = np.concatenate([x[f * n:(f + 1) * n] for f in kept])
    fade = int(SR * 0.008)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    return y, kept


def remap(t, kept):
    """합성 원본 기준 시각 t(초)를 정리된 클립 기준 시각으로 바꿉니다."""
    i = np.searchsorted(kept, int(t / FRAME))
    return float(min(i, len(kept) - 1)) * FRAME


async def synth(text, voice, rate, mp3, words_path):
    if os.path.exists(mp3) and os.path.getsize(mp3) > 0 and os.path.exists(words_path):
        return json.load(open(words_path, encoding="utf-8"))
    for attempt in range(4):
        try:
            audio, words = bytearray(), []
            async for ch in edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary").stream():
                if ch["type"] == "audio":
                    audio += ch["data"]
                elif ch["type"] == "WordBoundary":
                    words.append({"t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7, "w": ch["text"]})
            open(mp3, "wb").write(audio)
            json.dump(words, open(words_path, "w", encoding="utf-8"), ensure_ascii=False)
            return words
        except Exception as e:  # 네트워크 오류 시 재시도
            print("  retry", attempt + 1, e, file=sys.stderr)
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("TTS failed: " + text)


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


async def main():
    spec = json.load(open(os.path.join(HERE, "script.json"), encoding="utf-8"))
    os.makedirs(os.path.join(BUILD, "tts"), exist_ok=True)
    voice, rate = spec["voice"], spec.get("rate", "+0%")

    clips = []
    for sc in spec["scenes"]:
        for ln in sc["lines"]:
            key = hashlib.sha1(f"{voice}|{rate}|{ln['say']}".encode()).hexdigest()[:16]
            base = os.path.join(BUILD, "tts", key)
            words = await synth(ln["say"], voice, rate, base + ".mp3", base + ".words.json")
            y, kept = tighten(decode(base + ".mp3"))
            clips.append((y, [{"t": remap(w["t"], kept), "w": w["w"]} for w in words]))

    t, k, scenes, captions = LEAD, 0, [], []
    for si, sc in enumerate(spec["scenes"]):
        start = 0.0 if si == 0 else t
        if si > 0:
            t += SCENE_PRE + EXTRA_PRE.get(sc["id"], 0)
        cues = []
        for li, ln in enumerate(sc["lines"]):
            y, words = clips[k]
            d = len(y) / SR
            cue = {"start": round(t, 3), "end": round(t + d, 3),
                   "words": [{"t": round(t + w["t"], 3), "w": w["w"]} for w in words]}
            cues.append(cue)
            captions.append({"start": cue["start"], "end": cue["end"], "text": ln.get("cap", ln["say"]), "clip": k})
            t += d
            if li < len(sc["lines"]) - 1:
                t += GAP_SENT if ln["say"].rstrip().endswith((".", "?", "!")) else GAP_CLAUSE
            k += 1
        t += END_POST if si == len(spec["scenes"]) - 1 else SCENE_POST
        scenes.append({"id": sc["id"], "start": round(start, 3), "end": round(t, 3), "cues": cues})
    total = round(t, 3)

    track = np.zeros(int(SR * total) + SR, np.float32)
    for c in captions:
        a = int(c["start"] * SR)
        y = clips[c["clip"]][0]
        track[a:a + len(y)] += y
    track = track[:int(SR * total)]
    track = track / max(1e-6, np.abs(track).max()) * 0.89
    with wave.open(os.path.join(BUILD, "narration.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype("<i2").tobytes())

    json.dump({"total": total, "title": spec["title"], "scenes": scenes,
               "captions": [{k2: v for k2, v in c.items() if k2 != "clip"} for c in captions]},
              open(os.path.join(BUILD, "timeline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(BUILD, "subtitles.srt"), "w", encoding="utf-8") as f:
        for i, c in enumerate(captions, 1):
            f.write(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'] + 0.25)}\n{c['text']}\n\n")
    print(f"total {total:.1f}s  ({int(total // 60)}:{total % 60:04.1f})")
    for s in scenes:
        print(f"  {s['id']:<10} {s['start']:6.1f} → {s['end']:6.1f}  ({s['end'] - s['start']:.1f}s)")


if __name__ == "__main__":
    asyncio.run(main())
