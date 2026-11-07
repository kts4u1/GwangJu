#!/usr/bin/env bash
# 광주 반도체 시민 홍보 영상 전체 빌드
#   필요: ffmpeg, Node.js + Playwright(Chromium), Python 3 + edge-tts, numpy
#   사용: bash build.sh [렌더 작업자 수]
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
OUT=../output
mkdir -p build "$OUT"

[ -d node_modules/pretendard ] || npm install --no-audit --no-fund

echo "▶ 1/4 나레이션 생성 (edge-tts)"
$PY tts.py

echo "▶ 2/4 배경음악 합성"
$PY music.py

echo "▶ 3/4 화면 렌더링"
node render.js video "${1:-3}"

echo "▶ 4/4 음성·음악 믹싱 및 최종 인코딩"
DUR=$($PY -c "import json;print(json.load(open('build/timeline.json'))['total'])")
ffmpeg -v error -y -i build/music.wav -i build/narration.wav -filter_complex "\
[1]aformat=sample_rates=48000:channel_layouts=stereo,apad=whole_dur=${DUR},asplit[vo][sc];\
[0]aresample=48000,volume=0.5[m];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[md];\
[md][vo]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,atrim=0:${DUR}[out]" -map "[out]" -ar 48000 build/audio.wav
ffmpeg -v error -y -i build/video.mp4 -i build/audio.wav -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest \
  "$OUT/gwangju_semiconductor_3min.mp4"
cp build/subtitles.srt "$OUT/gwangju_semiconductor_3min.srt"
ffprobe -v error -show_entries format=duration,size -of compact "$OUT/gwangju_semiconductor_3min.mp4"
echo "✔ 완료: $OUT/gwangju_semiconductor_3min.mp4"
