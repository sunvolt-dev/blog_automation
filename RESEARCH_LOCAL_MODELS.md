# 로컬 모델 마이그레이션 리서치 — M4 Max 128GB

> **작성일:** 2026-05-04
> **목적:** 현재 파이프라인의 외부 AI 의존(Gemini 2.5 Flash, HF FLUX.1-schnell) → **풀 로컬화** 후보 모델 정리. 향후 자막 없는 영상 대응을 위한 STT 추가 검토 포함.
> **타겟 기기:** Apple M4 Max 128GB (unified memory, GPU wired limit ≈ 96GB)
> **연관 로드맵:** [ROADMAP.md](ROADMAP.md) 4번(이미지 생성 모델 탐색), 11번(에러 복원력)

---

## 🎯 0. 요약 (TL;DR)

현재 파이프라인의 외부 의존 3종 → 로컬 대체 표.

| 역할 | 현재 | 추천 로컬 모델 | 백엔드 | 메모리 |
|------|------|---------------|-------|-------|
| **LLM** (블로그 본문) | Google Gemini 2.5 Flash | **Qwen3.5-32B-4bit** (이중언어 균형) <br/> or **EXAONE 4.0 32B-MLX-4bit** (KR 우위 시) | `mlx-lm` server | ~18GB |
| **이미지 생성** | HF FLUX.1-schnell API | **FLUX.1-schnell mflux-8bit** | [`mflux`](https://github.com/filipstrand/mflux) | ~12GB |
| **STT** (자막 보강) | (없음 — yt-dlp 자막만) | **Whisper large-v3-turbo** | [`mlx-whisper`](https://huggingface.co/mlx-community/whisper-large-v3-turbo) | ~6GB |
| **합계 동시 상주** | — | — | — | **~36GB** (128GB에 여유 충분) |

---

## 1️⃣ LLM — 블로그 본문 생성 (Gemini 2.5 Flash 대체)

### 1-1. 현재 사용 위치

[core/generator.py:77](core/generator.py#L77) — `model="gemini-2.5-flash"` 호출. 출력 포맷은 `TITLE:` / 본문 / `IMAGE_PROMPT:` 3블록 ([generator.py:88-114](core/generator.py#L88-L114)).

### 1-2. 필요 성능

| 항목 | Gemini 2.5 Flash 기준 | 로컬 최소 요구치 |
|------|--------------------|----------------|
| **언어** | 한국어 + 영어(향후) 자연스러움 | **이중언어 동등 품질** — KR 톤 어색 없음 + EN 글쓰기 가능 |
| **컨텍스트** | 시스템 프롬프트(SEO/편집 가이드) + 자막(5–15K tok) + 트렌드 → 입력 ~20K tok | **32K context 이상** |
| **지시 준수** | `TITLE:` / `IMAGE_PROMPT:` 포맷 안정 출력 | Instruct-tuned + 출력 포맷 안정성 |
| **속도** | 클라우드 즉시 응답 | **30 TPS+** (블로그 1편 1–2분 내) |
| **재현성** | 기본값 | `temperature=0`, 시드 고정 가능 (mlx-lm 지원) |

### 1-3. 추천 모델 — 이중언어 가중치 적용 순위

> **재조정 근거:** 향후 영어 콘텐츠 작성 가능성 반영. 한국어 단일 평가에서는 EXAONE 4.0 32B 가 1위였으나, **한국어 + 영어 양쪽 모두 강한 모델**을 우선 배치.

| 순위 | 모델 | 한국어 | 영어 | 다국어 폭 | 크기/RAM | 비고 |
|------|------|-------|------|----------|---------|------|
| ⭐ **1** | **Qwen3.5-32B-4bit** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **201개 언어** (Qwen3 82개에서 대폭 확장) | 4bit ~18GB / 8bit ~32GB | **새 1순위.** 한·영 모두 균형 잡힘. Qwen3 → 3.5 에서 한국어 명시적 강화. 영어는 Chinese 모델치고 매우 강함 (대규모 영어 토큰). **본 벤치 프로젝트에서도 검증 완료.** 어떤 언어로 글 쓰든 안전한 일반해 |
| **2** | **Gemma 3 27B** (4bit) <br/> 또는 Gemma 4 31B (MLX 출시 시) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **유럽어 + KR/JA/AR 1위** (Western 모델 중) | ~15GB | Google 출신 → **톤이 Gemini 와 가장 유사** (마이그레이션 친화적). 검색 결과 Gemma 4 31B 가 한국어/다국어 모두 1위로 평가. 영어는 모국어 수준. EN 비중이 높을수록 유리 |
| **3** | **EXAONE 4.0 32B-MLX-4bit** ([HF](https://huggingface.co/lmstudio-community/EXAONE-4.0-32B-MLX-4bit)) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | KR/EN/ES (EXAONE 4.0 에서 ES 추가) | 4bit ~18GB / 8bit ~34GB | **한국어 절대 우위.** Artificial Analysis Index 62 — 32B 클래스 최고. 영어도 "좋음" 수준이지만 Qwen3.5/Gemma 만큼 자연스럽진 않음. **80%+ 한국어 콘텐츠라면 여전히 1순위** |
| **4** | **Qwen3.5-35B-A3B-4bit** (MoE) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Qwen3.5 동등 | ~20GB | 활성 파라미터 3B → **TPS 압도적**. 빠른 초안용. 품질 약간 양보 |
| **5** (오버킬) | **Qwen3.5-122B-A10B-4bit** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 최대 폭 | ~70GB | 128GB 에서 처음으로 제대로 돌릴 수 있는 모델 (64GB OOM). 활성 10B → 실용 속도. 정말 까다로운 톤·SEO 결과 안 나올 때 카드 |

### 1-4. 선택 가이드

- **한·영 혼합 / 미정 / 안전한 1픽** → `Qwen3.5-32B-4bit`
- **Gemini 톤 그대로 옮기고 싶음** → `Gemma 3 27B`
- **80%+ 한국어 콘텐츠 확정** → `EXAONE 4.0 32B-MLX-4bit`
- **속도 최우선 (대량 생성)** → `Qwen3.5-35B-A3B-4bit` (MoE)
- **품질 한계 테스트** → `Qwen3.5-122B-A10B-4bit`

---

## 2️⃣ 이미지 생성 — 대표 이미지 (FLUX.1-schnell HF API 대체)

### 2-1. 현재 사용 위치

[core/image_generator.py:10-12](core/image_generator.py#L10-L12) — HF Inference API 의 `black-forest-labs/FLUX.1-schnell` 호출. 영어 프롬프트는 Gemini 가 본문 생성 시 함께 출력 ([generator.py:114](core/generator.py#L114)).

### 2-2. 필요 성능

| 항목 | HF FLUX.1-schnell 기준 | 로컬 최소 요구치 |
|------|---------------------|----------------|
| **해상도** | 기본 1024×1024 | 1024×1024 |
| **속도** | cold start 포함 10–60s | **<60s/image** |
| **프롬프트 언어** | 영어 (Gemini가 영어로 생성) | 영어 OK. 한국어 in-image 필요 시 별도 모델 |
| **품질** | 4-step schnell — 블로그 히어로 충분 | dev(50-step) 까지 가면 +α |
| **RAM** | API → 0 | 로컬 12–80GB (모델·양자화) |

### 2-3. 추천 모델

| 순위 | 모델 | 백엔드 | RAM | 속도 (M4 Max) | 비고 |
|------|------|-------|-----|---------------|------|
| ⭐ **1** | **FLUX.1-schnell mflux-8bit** ([dhairyashil/FLUX.1-schnell-mflux-8bit](https://huggingface.co/dhairyashil/FLUX.1-schnell-mflux-8bit)) | [`mflux`](https://github.com/filipstrand/mflux) | ~12GB | **2-step ~10.5s** ([검증된 M4 Max 128GB 측정값](https://github.com/filipstrand/mflux/issues/92)) | **현재 모델 그대로, API → 로컬 1:1 마이그레이션.** 8bit 는 FP16 과 시각 차 거의 없음 |
| **2** | **FLUX.1-dev mflux-8bit** | mflux | ~14GB | 50-step ~60–90s | 품질 한 단계 위. close-up 인물·디테일 강함. 발행 빈도 낮으면 채택 |
| **3** | **Qwen-Image 20B** ([mflux 지원](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/qwen/README.md)) | mflux (`mflux-generate-qwen`) | ~20GB+ | (FLUX 보다 느림 예상) | **한국어 in-image 텍스트 렌더링 1위.** 배터리 제품 이미지에 한글 캡션·라벨 박을 때 |
| **4** | **SD 3.5 Large** | Diffusers/MPS or [DrawThings](https://drawthings.ai/) | ~16GB | ~30–60s | LoRA 생태계 큼. FLUX 보다 약간 떨어지지만 community fine-tune 풍부 |
| **5** (신규) | **FLUX.2 (4B/9B)** or **Z-Image 6B** | mflux | 6–12GB | 미공개 | 2025 Q4 ~ 2026 Q1 출시. 더 작고 빠른 차세대 — 안정화되면 1순위 후보 |

### 2-4. 선택 가이드

- **즉시 마이그레이션** → `FLUX.1-schnell mflux-8bit` (결과물 일관성 유지)
- **품질 한 단계 격상** → `FLUX.1-dev mflux-8bit`
- **한글 라벨·캡션 렌더링** → `Qwen-Image 20B`

---

## 3️⃣ STT — 자막 보강 (선택사항)

### 3-1. 현재 한계

[transcriber.py:107-110](core/transcriber.py#L107-L110) — yt-dlp 가 YouTube 자막을 다운로드만 함. **자막 없는 영상은 `RuntimeError` 로 실패.** STT 추가 시 모든 영상 처리 가능.

### 3-2. 필요 성능

| 항목 | yt-dlp 자막 기준 | 로컬 STT 최소 요구치 |
|------|-----------------|-------------------|
| **한국어 정확도** | YouTube 자동 자막 (CER ~10–15%) | **CER ≤ 8%** (Whisper large-v3 클래스) |
| **속도 (RTF)** | 즉시 (다운로드만) | **RTF ≤ 0.2** (10분 영상을 2분 내) |
| **시간 동기화** | 불필요 (cleaned text 만 사용) | 불필요 |
| **다국어** | ko/en/any | 영어 콘텐츠 대응 위해 멀티링귤 권장 |

### 3-3. 추천 모델

| 순위 | 모델 | 백엔드 | 정확도 (KR) | M4 Max 속도 | 비고 |
|------|------|-------|-----------|-------------|------|
| ⭐ **1** | **Whisper large-v3-turbo** | [`mlx-whisper`](https://huggingface.co/mlx-community/whisper-large-v3-turbo) | CER ~5–7% | **2:29 / 25W** ([실측](https://appleworld.today/2024/11/apples-m4-max-accomplished-an-audio-transcode-with-whisper-v3-turbo-in-half-the-time-of-nvidias-ampere/)) | **기본값.** large-v3 의 4-decoder pruned. large-v2 와 동급, 6× 빠름. MLX 네이티브 |
| **2** | **WhisperKit large-v3-turbo (CoreML/ANE)** | [WhisperKit](https://github.com/argmaxinc/WhisperKit) | 동등 | 인코더 sub-250ms, 0.46s latency | **Apple Neural Engine 사용 → 전력 효율 최고.** 실시간 처리면 1순위 |
| **3** | **ghost613/whisper-large-v3-turbo-korean** | [HF](https://huggingface.co/ghost613/whisper-large-v3-turbo-korean) | CER ↓↓ (fine-tuned) | turbo 와 동등 | 한국어 발화 비중 압도적 시. MLX 변환 1회 필요 |
| **4** | **Whisper large-v3 (full)** | mlx-whisper | CER ~4–6% | turbo 의 ~6× 느림 | 정확도 최우선. 본 파이프라인은 turbo 로 충분 |
| **5** | **8bit 양자화 turbo** ([LibraxisAI/whisper-large-v3-turbo-mlx-q8](https://huggingface.co/LibraxisAI/whisper-large-v3-turbo-mlx-q8)) | mlx-whisper | 동등 | 더 빠름, 메모리 ½ | 동시 처리·다른 모델과 공존 시 유리 |
| ❌ 제외 | Parakeet (NVIDIA) | mlx-audio | **한국어 미지원** | — | English-only, 본 케이스 부적합 |

### 3-4. 선택 가이드

- **기본 추가** → `mlx-whisper large-v3-turbo` + yt-dlp 자막 우선, 자막 없을 때만 STT fallback (비용 0)
- **한국어 영상 압도적** → `ghost613/whisper-large-v3-turbo-korean` (KR 특화)
- **전력 효율 / 실시간** → `WhisperKit` (ANE 사용)

---

## 📊 4. 동시 로드 메모리 시뮬레이션 (M4 Max 128GB)

| 시나리오 | LLM | Image | STT | 합계 | 여유 (96GB GPU wired 기준) |
|---------|-----|-------|-----|------|------|
| **표준 (1순위 조합)** | Qwen3.5-32B-4bit (18GB) | FLUX.1-schnell-mflux-8bit (12GB) | whisper-large-v3-turbo (6GB) | **36GB** | ✅ 60GB 여유 |
| **고품질** | Qwen3.5-32B-8bit (32GB) | FLUX.1-dev-mflux-8bit (14GB) | whisper-large-v3 (10GB) | **56GB** | ✅ 40GB 여유 |
| **품질 한계** | Qwen3.5-122B-A10B-4bit (70GB) | FLUX.1-schnell-mflux-8bit (12GB) | whisper-large-v3-turbo (6GB) | **88GB** | ⚠️ 8GB 여유 — 단일 추론만 |
| **빠른 드래프트** | Qwen3.5-35B-A3B-4bit MoE (20GB) | FLUX.1-schnell-mflux-8bit (12GB) | whisper-large-v3-turbo-q8 (4GB) | **36GB** | ✅ 60GB 여유 + 최고 TPS |

> 셋 다 상주시켜도 표준 시나리오는 36GB → 다른 작업·브라우저 등 동시 사용 충분. 122B 클래스만 단독 운영 권장.

---

## 🛠 5. 마이그레이션 작업 분해 (참고)

> 본 리서치는 **모델 선정**까지. 실제 코드 교체는 ROADMAP에 별도 항목으로 추가 권장.

| # | 작업 | 영향 파일 | 난이도 |
|---|------|----------|-------|
| 1 | `mlx_lm.server` 기동 + Gemini 호출부 → OpenAI 호환 HTTP 교체 | [core/generator.py:75-80](core/generator.py#L75-L80) | 중 |
| 2 | HF FLUX API → `mflux` Python 호출 교체 | [core/image_generator.py:36](core/image_generator.py#L36) | 하 |
| 3 | (선택) 자막 없을 때 mlx-whisper fallback 추가 | [core/transcriber.py:107-110](core/transcriber.py#L107-L110) | 중 |
| 4 | `requirements.txt` 정리 — `google-genai` 제거 (or 듀얼 유지), `mlx-lm`, `mflux`, `mlx-whisper` 추가 | [requirements.txt](requirements.txt) | 하 |
| 5 | `config/settings.py` — `gemini_api_key`/`hf_token` 옵셔널 처리, 로컬 모드 플래그 추가 | [config/settings.py](config/settings.py) | 하 |

---

## 🔗 6. 출처 (Sources)

### LLM (Korean / Multilingual)
- [Ultimate Guide - Best Open Source LLM For Korean In 2026 (SiliconFlow)](https://www.siliconflow.com/articles/en/best-open-source-llm-for-korean)
- [Best Local LLMs to Run On Every Apple Silicon Mac in 2026 (apxml)](https://apxml.com/posts/best-local-llms-apple-silicon-mac)
- [EXAONE 4.0 32B MLX-4bit (Hugging Face — lmstudio-community)](https://huggingface.co/lmstudio-community/EXAONE-4.0-32B-MLX-4bit)
- [EXAONE 4.0 paper (arXiv 2507.11407)](https://arxiv.org/abs/2507.11407)
- [Artificial Analysis: EXAONE 4.0 32B = 62 Intelligence Index (highest 32B)](https://x.com/ArtificialAnlys/status/1950884246803136601)
- [Gemma 4 vs Qwen 3.5 — Korean & multilingual comparison (MindStudio)](https://www.mindstudio.ai/blog/gemma-4-vs-qwen-3-5-open-weight-comparison)
- [Open Ko-LLM Leaderboard (Upstage)](https://huggingface.co/spaces/upstage/open-ko-llm-leaderboard)

### Image Generation
- [mflux GitHub (filipstrand)](https://github.com/filipstrand/mflux)
- [FLUX.1-schnell-mflux-8bit (Hugging Face)](https://huggingface.co/dhairyashil/FLUX.1-schnell-mflux-8bit)
- [M4 Max 128GB mflux benchmark — 2-step ~10.5s (mflux Issue #92)](https://github.com/filipstrand/mflux/issues/92)
- [Flux vs SDXL vs SD 3.5 comparison (WillItRunAI)](https://willitrunai.com/blog/flux-vs-sdxl-vs-sd35-comparison)
- [Qwen-Image mflux module README](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/qwen/README.md)

### STT (Whisper)
- [mlx-community/whisper-large-v3-turbo (Hugging Face)](https://huggingface.co/mlx-community/whisper-large-v3-turbo)
- [Apple M4 Max Whisper V3 Turbo benchmark — 2:29 / 25W (AppleWorld)](https://appleworld.today/2024/11/apples-m4-max-accomplished-an-audio-transcode-with-whisper-v3-turbo-in-half-the-time-of-nvidias-ampere/)
- [mac-whisper-speedtest (anvanvan/GitHub)](https://github.com/anvanvan/mac-whisper-speedtest)
- [WhisperKit paper (arXiv 2507.10860)](https://arxiv.org/html/2507.10860v1)
- [ghost613/whisper-large-v3-turbo-korean (Hugging Face)](https://huggingface.co/ghost613/whisper-large-v3-turbo-korean)
- [Whisper Korean telemedicine fine-tuning study (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC13091973/)

---

## 📝 변경 로그

- **2026-05-04**: 초안 작성. LLM 순위는 한국어+영어 이중언어 가중치로 재조정 (이전 한국어 단독 평가에서 EXAONE 4.0 32B 가 1위 → 이중언어 기준 Qwen3.5-32B 가 1위로 이동, EXAONE 은 3위, Gemma 3 27B 가 2위로 부상).
