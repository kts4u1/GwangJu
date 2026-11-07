# 빛고을 광주, 반도체로 다시 빛나다

광주 반도체 산업을 소개하는 **시민 홍보 영상(3분 3초)** 과 그 제작 소스입니다.

![썸네일](output/thumbnail.jpg)

## 결과물

| 파일 | 설명 |
|---|---|
| [`output/gwangju_semiconductor_3min.mp4`](output/gwangju_semiconductor_3min.mp4) | 완성 영상 · 1920×1080 · 30fps · H.264/AAC · 화면 자막 포함 |
| [`output/gwangju_semiconductor_3min.srt`](output/gwangju_semiconductor_3min.srt) | 자막 파일 (유튜브 등에 따로 올릴 때) |
| [`output/thumbnail.jpg`](output/thumbnail.jpg) | 썸네일용 이미지 |
| [`video/SCRIPT.md`](video/SCRIPT.md) | 나레이션 원고 (시간표 포함) |
| [`video/SOURCES.md`](video/SOURCES.md) | 자료 출처와 사실 확인표 |

## 장면 구성

| 시간 | 장면 | 내용 |
|---|---|---|
| 0:00 – 0:22 | 인트로 | 빛고을 광주가 준비하는 새로운 빛, 반도체 |
| 0:22 – 0:41 | 생활 속 반도체 | 스마트폰·자동차·인공지능의 중심에 있는 반도체 |
| 0:41 – 1:04 | 첨단 패키징 거점 | 2025년 12월 정부의 광주 ‘첨단 패키징’ 거점 지정 |
| 1:04 – 1:37 | 반도체 메가 프로젝트 | 약 800조 원·공장 4곳 투자 계획, 군공항 부지 826만㎡ 국가산단 후보지 |
| 1:37 – 1:53 | 군공항 62년 | 1964년 비행장에서 반도체의 땅으로 |
| 1:53 – 2:15 | 인재 | GIST-Arm 스쿨 5년간 1,400명, 지역 대학 |
| 2:15 – 2:34 | AI 중심도시 | 국가 AI 데이터센터, 인구 320만 전남광주통합특별시 출범 |
| 2:34 – 2:52 | 비전 | 일자리·청년·아이들, 시민과 함께 여는 내일 |
| 2:52 – 3:03 | 엔딩 | 빛고을 광주, 반도체로 다시 빛나다 |

## 만든 방법

- **화면**: HTML·Canvas로 직접 그린 모션그래픽을 Chromium(Playwright)으로 한 프레임씩 렌더링합니다. 실사 촬영 영상이나 외부 이미지는 쓰지 않았습니다.
- **나레이션**: Microsoft Edge 신경망 TTS 여성 음성(`ko-KR-SunHiNeural`)입니다.
- **배경음악**: `video/music.py`로 직접 합성해서 저작권 문제가 없습니다.
- **글꼴**: [Pretendard](https://github.com/orioncactus/pretendard) (SIL Open Font License)를 썼습니다.

## 수정하고 다시 만들기

원고를 고치려면 [`video/script.json`](video/script.json)을 수정하세요. `say`는 음성으로 읽을 문장(숫자를 한글로 풀어 씀)이고, `cap`은 화면 자막입니다. 그다음 아래 명령으로 영상을 다시 만듭니다(약 4~5분).

```bash
cd video
pip install -r requirements.txt
npm install
bash build.sh
```

- 필요한 것: ffmpeg, Node.js, Playwright + Chromium, Python 3
- 문장 길이가 바뀌면 장면 타이밍과 자막은 자동으로 다시 맞춰집니다.
- 정지 화면만 확인하려면 `node render.js stills 30 95 150`을 실행하세요(`build/stills/`에 저장).

## 공개 전 확인할 것

- 영상 속 일부 수치와 일정은 **계획 단계**입니다. 자세한 내용은 [`video/SOURCES.md`](video/SOURCES.md)에 있습니다. 공개 시점의 공식 발표와 한 번 더 대조해 주세요.
- 기관 로고는 넣지 않았습니다. 공식 로고를 넣으려면 해당 기관의 승인이 필요합니다.
- AI 음성 대신 성우 녹음을 쓰려면 [`video/SCRIPT.md`](video/SCRIPT.md)의 문장별 시작 시각에 맞춰 녹음해야 합니다. 그다음 `build/narration.wav`를 녹음 파일로 바꾸고 `build.sh`의 4단계(믹싱·인코딩)를 다시 실행하면 됩니다.
