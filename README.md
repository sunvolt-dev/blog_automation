# blog_automation

YouTube 영상 → 코리아배터리 블로그 포스트 자동 변환 파이프라인.

## 동작 흐름

`main.py`에 YouTube URL을 전달하면 다음 순서로 실행됩니다.

1. **자막 추출** — `yt-dlp`로 VTT 자막 다운로드 (한국어/영어 우선)
2. **트렌드 수집** — 네이버 데이터랩 + YouTube Data API로 주간 키워드 수집
3. **본문 생성** — Gemini 2.5 Flash로 블로그 글 + 이미지 프롬프트 생성
4. **대표 이미지 생성** — HuggingFace FLUX.1-schnell → WordPress 미디어 업로드
5. **WordPress 게시** — REST API로 draft 또는 publish
6. **로그 기록** — `logs/generation_*.md`에 실행 메타데이터 저장

## 실행

```bash
pip install -r requirements.txt
python main.py <YouTube URL>              # 초안(draft) 저장 + 편집 링크 출력
python main.py <YouTube URL> --publish    # 즉시 발행
```

## 환경변수 (`.env`)

```
GEMINI_API_KEY=
HF_TOKEN=
WP_BASE_URL=
WP_USERNAME=
WP_PASSWORD=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

## 구조

```
main.py              파이프라인 오케스트레이션
config/
  settings.py        .env 로딩
  prompts.py         Gemini 시스템 프롬프트
core/
  transcriber.py     yt-dlp 자막 추출 + VTT 파싱
  trends.py          네이버/YouTube 트렌드 수집
  generator.py       Gemini 블로그 생성 (제목/본문/이미지 프롬프트 파싱)
  image_generator.py HuggingFace 이미지 생성
  wordpress.py       WordPress REST API (미디어 업로드 + 게시)
data/                브랜드·가이드 문서 (프롬프트에 주입)
logs/                실행 로그 (gitignore)
```
