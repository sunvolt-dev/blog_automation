# 블로그 자동화 디벨롭 로드맵

> **작성일:** 2026-04-23
> **진행 방식:** 항목별로 순차 수정 → 테스트 실행으로 검증 → 체크 표시 → 다음 항목

## 🎯 설계 원칙

**수직 슬라이스 먼저, 통합은 나중에.** 현재 범위는 **WordPress + 배터리 단일 브랜드**. 추상화(멀티브랜드·멀티채널)는 두 번째·세 번째 사례가 실제로 생긴 뒤에 공통점을 보고 묶는다. 공통점은 3번쯤 써본 뒤에야 비로소 제대로 보이기 때문.

---

## ✅ 진행 체크리스트

### 우선순위 높음 (사용자 지정)
- [x] 1. 회사소개 보강 (2026-04-23 완료)
- [x] 2. 초안(Draft) 게시 후 수동 검토 → 게시 워크플로우 (2026-04-23 완료)
- [x] 3. SEO 가이드 보강 (2026-04-23 완료)
- [x] 3-B. 트렌드 키워드 자동 수집 파이프라인 (네이버/YouTube, main.py 실행 시 자동) (2026-04-23 완료)
- ~~3-A. 브랜드 메타키워드 자동 수집 스크립트~~ — **취소** (시드 변경 빈도 낮음, 사이트 확장 시 수동 업데이트로 충분)
- [ ] 4. 이미지 생성 모델 탐색
- [ ] 5. 이미지 생성 프롬프트 다변화
- [x] 6. 본문 생성 프롬프트 보강 (시각화 요소 적극 활용) (2026-04-23 완료)

### 추가 제안 (검토 후 진행)
- [ ] 7. YouTube 썸네일 백업 활용
- [ ] 8. 카테고리/태그 자동 지정
- [ ] 9. Dry-run 모드 (게시 없이 HTML 미리보기)
- [ ] 10. 중복 실행 방지
- [~] 11. 에러 복원력 (API 재시도 로직) — Gemini만 완료 (2026-04-23), HF·WP 미구현
- [ ] 12. 배치 처리 모드 (URL 목록 일괄)
- [ ] 13. 메타 디스크립션 / Excerpt 자동 생성
- [ ] 14. 본문 중간 이미지 삽입 (섹션별 이미지)
- [ ] 16. 데이터 포집 & 웹 애널리틱스 통합 (GA4, Search Console, AEO)
- [ ] 17. 독자 데이터 기반 타겟/카테고리 재조정 (16번 선행 후)

### 🚀 Phase 2 — 수직 슬라이스로 플랫폼 하나씩 추가
> 원칙: 한 플랫폼을 **독립 모듈(단독 실행 가능한 엔트리포인트)로 완성** → 다음 플랫폼 → 3개 완성 후 공통부 추출·통합
- [ ] 18a. 네이버 블로그 발행 모듈
- [ ] 18b. Instagram 카드뉴스 발행 모듈
- [ ] 18c. Facebook 발행 모듈
- [ ] 18d. 통합 디스패처 (18a~c 완료 후 공통 인터페이스 추출)

### 🗂 보류 (착수 시점에 재검토)
- [ ] 15. 제품군/브랜드별 분리 아키텍처 — **2번째 브랜드(ATV·골프카트) 착수 직전에 결정**

---

## 📋 항목별 상세

### 1. 회사소개 보강 ✅ (2026-04-23 완료)
**목표:** Gemini가 더 정확하고 풍부한 맥락으로 글을 쓸 수 있도록 회사 정보 확장
**이전 상태:** [data/company_info.md](data/company_info.md) — 간략한 5줄 수준
**완료 내용:**

#### 1-1. `data/company_info.md` 대폭 확장 (회사 팩트)
- **그룹 차원의 전문성**: 코리아텍(LFP 배터리팩) / 썬볼트(전동모빌리티) / 코리아팩(산업용 포장기계) / 굿프라이스·굿쇼핑(유통) 수직 역량 정리
- **주요 제품 / 서비스**: 보조배터리, 무선 이어폰, LFP 배터리팩, ESS 등 제품군 정리
- **신뢰 기반** (E-E-A-T 강화): 국내 자체 제조공장, KC·ISO·특허, 공공조달 실적, 일본 수출·미국 UL·FCC 준비, AS 체계, B2B 레퍼런스
- **브랜드 포트폴리오**: 16개 공식 운영 사이트를 카테고리별(배터리·에너지 / 모빌리티 레저 / 모빌리티 산업 / 산업기계·유통)로 정리
- **콘텐츠 반영 원칙**: 타 브랜드 과도 나열 방지, 주제별 1~2개만 자연스럽게 언급, 메인 브랜드는 항상 코리아배터리
- **타겟 독자**: 일반 소비자 + 배터리 내장 기기 사용자 + 입문~중급 관심 독자
- **내부 정보는 전면 제외**: 매출·영업이익·직원 수·공급망·조직도·IR 등 외부 노출 부적합 정보

#### 1-2. `data/editorial_guide.md` 신규 생성 (작성 규칙 분리)
`company_info.md`에서 **관심사 분리** — 회사 팩트(변경 주기 느림) vs 작성 규칙(변경 주기 빠름).
- **에디터 페르소나**: "국내 자체 배터리 제조공장을 운영하는 제조사의 시니어 콘텐츠 에디터" — 판매자/마케터가 아닌 엔지니어링·제조 현장 관점. 합쇼체, 자칭 "저희 코리아배터리/당사", 근거 기반 신중한 태도
- **작성 금지·주의사항** (4개 카테고리):
  - 법적·안전 리스크: 의료 효능 주장, 안전성 단정, 영구 보증, 무근거 수치
  - 경쟁·시장 리스크: 경쟁사 비방, 최저가 단정, 무근거 순위
  - 브랜드·내부 정보: 매출·직원·공급망·임직원 실명 노출 금지
  - 콘텐츠 품질: 자막에 없는 사실 창작 금지, 반복 표현 지양
- **CTA·연락처 중복 방지**: [main.py:73-78](main.py#L73-L78) 푸터가 `031-990-3362` 자동 첨부하므로 본문 내 전화번호·CTA 문구 금지

#### 1-3. 파이프라인 통합
- [main.py](main.py): `editorial_guide.md` 로드 → `generate_blog_post()` 전달
- [core/generator.py](core/generator.py): `editorial_guide_md` 파라미터 추가, 프롬프트에 `## 작성 가이드` 섹션 삽입

**영향 파일:** `data/company_info.md`, `data/editorial_guide.md` (신규), `main.py`, `core/generator.py`

**의도적 제외 항목:**
- **가격대 정보**: editorial_guide.md의 "구체 최저가·가격 단정 금지" 원칙과 충돌
- **용어·어휘 사전**: 현 단계에서 불필요 판단 (사용자 결정)
- **경쟁사 직접 비교**: 비방·깎아내리기 금지 원칙상 제외. 차별점은 "신뢰 기반" 섹션에 긍정 서술로 간접 반영

---

### 2. 초안(Draft) 게시 후 수동 검토 → 게시 워크플로우 ✅ (2026-04-23 완료)
**목표:** 바로 publish 하지 않고 draft로 올린 뒤 사람이 확인하고 최종 발행
**이전 상태:** `main.py`가 `sys.argv[1]`만 읽고 `publish_post()`를 `status` 지정 없이 호출 → 항상 즉시 발행
**완료 내용:**

#### 2-1. `main.py` CLI 개편 — argparse 도입
- `sys.argv` 직접 파싱 → `argparse` 교체
- `--publish` 단일 플래그 추가 (옵션 A 채택 — 기본 draft, 명시적 발행)
  ```bash
  python main.py <url>                  # 초안(draft)으로 저장
  python main.py <url> --publish        # 즉시 발행
  python main.py --help                 # 도움말
  ```
- `main()` 시그니처: `main(youtube_url: str, publish: bool = False)`
- `status = "publish" if publish else "draft"` 분기 → `publish_post(..., status=status)`로 전달

#### 2-2. 초안 검토 흐름 UX
- draft 저장 시 **WordPress 관리자 편집 링크**를 로그에 출력 (`{wp_base_url}/wp-admin/post.php?post=<id>&action=edit`)
- 헬퍼 `_admin_edit_url()` 추가
- publish 시에는 기존처럼 public 링크 출력 → draft/publish 경로 분기

#### 2-3. 옵션 A 채택 근거
- 지금은 **draft ↔ publish 두 상태**만 필요 — YAGNI
- 기본값이 draft라 실수로 바로 발행되는 사고 방지 (안전 기본값)
- 타이핑 최소 (일상 검토 작업은 플래그 없이 가장 짧은 명령)
- 향후 `pending`·`future`(예약 발행) 필요 시 `--status X` 형으로 리팩토링은 5분 작업

#### 2-4. 실사용 테스트 (2026-04-23)
- 테스트 URL: `https://youtu.be/pAtcyzbkdNc` (DIY 리튬 배터리 가이드 영상)
- 결과: draft 저장 성공 (Post ID=3727), 이미지 업로드 완료, 편집 링크 정상 출력
- 생성된 제목 — editorial_guide 적용 확인: 과장·광고성 표현 없음, 정보성 톤 유지

**영향 파일:** `main.py` (단독 수정 — `core/wordpress.py`는 이미 `status` 파라미터 보유, 변경 불필요)

**보류 항목 (향후 필요 시):**
- 승인 전용 스크립트 `approve.py <post_id>` — 실제 검토 흐름을 한두 번 써본 뒤 필요성 판단

---

### 3. SEO 가이드 보강 ✅ (2026-04-23 완료)
**목표:** AI가 SEO 규칙을 더 구체적이고 실행 가능하게 따르도록 가이드 확장
**이전 상태:** [data/SEO_GUIDE.md](data/SEO_GUIDE.md) — 5개 기본 규칙(계층구조, 키워드 밀도, Alt, 메타 디스크립션, 링크)
**완료 내용:**

#### 3-1. `data/SEO_GUIDE.md` 대폭 확장 — 기존 5절 유지 + 6절 신규
- **6. 제목 작성 공식** — A(숫자+혜택) / B(질문+해결) / C(비교) / D(대상+용도) 4가지 공식 + 공통 규칙(30자, 이모지 금지)
- **7. 첫 문단 Hook 패턴** — 공감형·통계형·질문형·결론선제형 4가지 + 클리셰 도입 금지
- **8. 본문 구조화 규칙** — TOC, FAQ(schema 연동 전제), 핵심 요약 박스, 시각 요소(인용·표·체크리스트·이모지 절제)
- **9. 키워드 전략** — 시드(정적) + 트렌드(동적) 이중 활용법, Long-tail 전략
- **10. E-E-A-T 요소 본문 반영** — Experience/Expertise/Authoritativeness/Trustworthiness 각 신호를 본문에 자연스럽게 삽입하는 구체 예시
- **11. 자가 검증 체크리스트** — 생성 후 Gemini가 자체 점검할 12개 항목

#### 3-2. `data/keywords_seed.md` 신규 생성 — 브랜드 주제 시드 (정적)
- **출처**: 주요 5개 사이트(korea-battery, korea-tech, sunvolt-battery, smart-battery, koreapack)의 페이지 헤딩·카테고리·타이틀 + 운영자 직접 입력 키워드 (썬볼트배터리)
- **주의**: 대부분 사이트가 `<meta name="keywords">`를 비워둠 — 현대 SEO에서 무시되기 때문. 대신 실제 페이지 헤딩을 시드로 활용
- **구조**: (1) 핵심 브랜드 키워드 / (2) 기술·제품 카테고리 / (3) 타겟 산업·용도 / (4) 대표 표기 규칙 (표기 통일 테이블)

#### 3-3. `data/keywords_trending.md` 신규 생성 — 트렌드 키워드 (동적, 스키마만)
- **현재**: 값 비어 있음. Gemini는 "트렌드 없음"으로 간주하고 시드만 사용
- **목적**: 로드맵 3-B 구현 시 스크립트가 이 파일을 주 단위로 덮어씀
- **스키마 정의**: 카테고리별로 키워드·변동률·출처·수집일 포맷 표준화
- **시드·트렌드 충돌 시 트렌드 우선** 원칙 명시 (검색자의 실제 언어에 맞춤)

#### 3-4. 파이프라인 통합
- [main.py](main.py): 두 신규 파일 로드 → `generate_blog_post()` 전달
- [core/generator.py](core/generator.py): `keywords_seed_md`, `keywords_trending_md` 파라미터 추가, 프롬프트에 `## 키워드 시드`, `## 트렌드 키워드` 섹션 삽입

**영향 파일:** `data/SEO_GUIDE.md` (확장), `data/keywords_seed.md` (신규), `data/keywords_trending.md` (신규), `main.py`, `core/generator.py`

**보류 항목 (별도 로드맵 3-A, 3-B로 분리):**
- **3-A**: 16개 브랜드 사이트 메타키워드·헤딩 자동 수집 스크립트 (주기 재실행)
- **3-B**: 트렌드 키워드 자동 수집 파이프라인 (네이버 데이터랩 / 구글 pytrends / 유튜브 Data API)
- **내부 링크 세부 URL 목록**: korea-battery.com 사이트 구조 정돈 후 추가. 현재는 브랜드 메인 URL 수준만 연결

---

### 3-A. 브랜드 메타키워드 자동 수집 스크립트 ❌ 취소 (2026-04-23)
**취소 사유:** 브랜드 사이트의 카테고리·제품군이 거의 변하지 않음(분기~연 단위). 새 브랜드 추가도 드물어, 5분짜리 수동 편집이 **스크레이퍼 작성·유지보수(JS 렌더링·리다이렉트 처리 등) 부담보다 저렴**. 대표님 판단("시드쿼리는 크게 바뀔 일 없음") 반영.
**정책 대안:** `keywords_seed.md`는 **수동 유지**. 신규 브랜드 사이트 생성 시 담당자가 해당 파일의 "핵심 브랜드 키워드" 섹션에 수기 추가.

---

### 3-B. 트렌드 키워드 자동 수집 파이프라인 ✅ (2026-04-23 완료)
**목표:** 블로그 생성 시점의 검색자 실시간 관심사를 반영
**완료 내용:**

#### 3-B-1. `core/trends.py` 신규 생성
- `TRENDING_SEED_QUERIES` 상수 — 배터리·전자·전동모빌리티 20개 시드 (파일 상단, 사이트 확장 시 편집)
- `collect_naver_trends()` — 네이버 데이터랩 검색어 트렌드 API. 최근 1주 vs 이전 3주 비율로 상승률 계산, 5개씩 청크 나눠 호출
- `collect_youtube_trends()` — YouTube Data API v3. 시드 쿼리별로 최근 7일 이내 업로드 + 조회수 상위 5개 영상 제목 + 태그 수집
- `collect_trending_keywords()` — 두 소스 통합. 소스별 실패는 해당 소스만 비움 (나머지는 계속)
- `format_trending_markdown()` — 결과 → `keywords_trending.md` 형식 마크다운 변환

#### 3-B-2. `main.py` 통합 — 매 실행 시 자동 수집
- **주기 실행 스크립트 대신** `main.py` 실행 시마다 자동 수집 (대표님 제안 반영)
- 자막 추출 직후 트렌드 수집 → `keywords_trending.md` 파일 덮어쓰기 → Gemini 프롬프트 주입
- 실패 시 기존 `keywords_trending.md` 값 보존 (안전 기본값)

#### 3-B-3. 생성 로그 기록 — `logs/generation_<타임스탬프>.md`
- 실행 시각, YouTube URL, 제목, 상태(draft/publish), Post ID, 편집 URL
- 이미지 프롬프트, 자막 미리보기 (첫 400자)
- 수집된 네이버 트렌드 상위 10개 (변동률 포함)
- 수집된 YouTube 시드별 영상 수·태그 요약
- 수집 오류 (있을 경우)
- 투명성·디버깅·향후 감사용

#### 3-B-4. 환경 설정
- `.env`에 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `YOUTUBE_API_KEY` 추가
- `config/settings.py`에 3개 필드 로딩 코드 추가

**주의·제약:**
- YouTube 일일 쿼터 10,000 유닛 중 실행당 약 2,020 유닛 사용 → **일일 4~5회 실행 한도** (일반 운영에 충분)
- 네이버 데이터랩 API는 애플리케이션 등록 시 **"데이터랩 (검색어 트렌드)" 체크 필수** (누락 시 401 에러 — 실제로 초기 발생, 해결 후 정상 동작)
- **시드 주변 트렌드**만 포착 가능 — 시드에 없는 신규 주제는 미포착. 시드 확장 주기 고려 필요

**보류·후속 (향후 필요 시):**
- 순수 인기 급상승(chart=mostPopular) 모드 추가 — 시드 무관 전체 트렌드
- 네이버 연관 검색어 기능 활용
- 생성 후 본문 내 키워드 사용 감사 스크립트 — Gemini가 실제로 반영했는지 측정
- 16번(애널리틱스)·17번(독자 데이터)과 연계한 키워드 자동 튜닝

**영향 파일:** `core/trends.py` (신규), `main.py` (통합), `config/settings.py` (API 키), `.env` (환경 변수), `data/keywords_trending.md` (자동 갱신)

---

### 4. 이미지 생성 모델 탐색
**목표:** 현재 FLUX.1-schnell 외 대안 비교 후 품질·속도·비용 최적 모델 선정
**현재 상태:** [core/image_generator.py](core/image_generator.py) — FLUX.1-schnell 고정
**비교 후보:**
- FLUX.1-dev (schnell 대비 고품질, 느림)
- Stable Diffusion 3.5 Large
- SDXL + Lightning LoRA
- Google Imagen 3 (Gemini API)
- OpenAI gpt-image-1
- 국내 이미지 생성 API (Karlo 등)
**평가 지표:** 한국적 맥락 이해도, 제품샷 품질, 텍스트 렌더링, API 안정성, 비용
**작업 내용:**
- 동일 프롬프트로 3~4개 모델 샘플 생성
- 모델 전환 가능하도록 `image_generator.py` 추상화 (`provider` 파라미터)
**영향 파일:** `core/image_generator.py`, `config/settings.py`

---

### 5. 이미지 생성 프롬프트 다변화
**목표:** 매 포스트마다 비슷한 이미지가 나오지 않도록 프롬프트 템플릿 다양화
**현재 상태:** Gemini가 매번 유사한 패턴의 `IMAGE_PROMPT` 생성 → 결과물 단조로움
**작업 내용:**
- 이미지 스타일 프리셋 여러 개 정의 (제품샷, 라이프스타일, 인포그래픽, 미니멀, 플랫레이 등)
- 랜덤 또는 본문 주제에 따라 스타일 선택
- 색상 팔레트·조명·앵글 다양화 지시
- 브랜드 일관성 유지용 필수 요소는 고정 (톤, 금지 요소)
- 시스템 프롬프트에 스타일 선택 규칙 추가
**영향 파일:** `config/prompts.py`, `core/generator.py` (또는 별도 `image_prompt_builder.py`)

---

### 6. 본문 생성 프롬프트 보강 ✅ (2026-04-23 완료)
**목표:** 단조로운 평문 위주 → 시각적으로 풍부하고 가독성 높은 포스트
**이전 상태:** [config/prompts.py](config/prompts.py) — 20줄 수준, 기본 마크다운만 지시
**완료 내용:**

#### 6-1. SYSTEM_PROMPT 전면 재작성 (20줄 → ~100줄)
- **역할 선언**: "국내 자체 배터리 제조공장을 운영하는 시니어 콘텐츠 에디터" 정체성 고정
- **글의 목적 우선순위**: 검색 유입 > 신뢰 구축 > 주제 선점 (판매 유도는 푸터에 일임)
- **참조 문서 충돌 시 우선순위**: editorial_guide 금지사항 > SEO_GUIDE > company_info > 키워드

#### 6-2. 9단계 생성 절차 명시
주제 추출 → 제목 공식 선택 → Hook 패턴 선택 → H2 3개+ 구조 설계 → 시각 요소 배치 → FAQ 판단 → 제조사 관점 삽입 → 핵심 요약 → 자가 검증

#### 6-3. 본문 출력 템플릿 고정
`Hook → TOC(1,500자+일 때만) → H2 섹션들 → FAQ(기준 충족 시) → 핵심 요약 인용박스`

#### 6-4. FAQ 포함 기준 구체화 (자율 판단)
- **포함 조건 5가지**: how-to/가이드, 용어·개념 소개, 비교·선택, 안전·관리법, 1,200자+ 제품·기술 중심
- **제외 조건 5가지**: 뉴스·리포트, 800자 미만 팁, 이미 Q&A 구조, 단일 제품 리뷰, 감상·칼럼
- FAQ 포함 시 2~4개, 검색자가 쓸 법한 자연어 질문

#### 6-5. 시각 요소 6종 사용 규칙
굵게 (H2당 2~3회), 인용 박스(⚠️💡📌), 테이블(비교·스펙 필수), 체크리스트, 구분선, 이모지(H2/H3 금지)

#### 6-6. 제조사 관점 삽입 규칙 (글당 1~2회)
- 예시 문구 3종 제시 ("저희는 ~", "자체 제조 현장에서 ~", "제조 과정에서 ~")
- 안전·품질·내구성·관리법 주제에서 우선 사용
- 일반 정보 설명·뉴스성 글에는 삽입 자제

#### 6-7. 기본 원칙 보강
합쇼체 고정, 사실 창작 금지, 전문 용어 첫 등장 시 풀어 설명, 비유·예시 1개+, 대표 표기 규칙 준수, CTA·전화번호 본문 금지, 긴 문단 금지(3~4문장당 시각 요소)

**영향 파일:** `config/prompts.py`

**사용자 검증 (2026-04-23):** 생성 성공, 전보다 만족스러움 확인. 보완 과제는 후속으로 처리.

---

### 11. 에러 복원력 (API 재시도 로직) — 부분 완료 (2026-04-23)
**목표:** 일시적 네트워크/API 실패로 전체 파이프라인이 죽지 않도록
**배경:** Gemini 2.5 Flash의 503 UNAVAILABLE(high demand) 에러가 하루에도 수차례 발생 — 전체 파이프라인이 자막 추출·트렌드 수집 포함 재실행 필요했음
**완료 내용:**

#### 11-1. Gemini API 재시도 (core/generator.py) ✅
- `tenacity` 기반 데코레이터 `_call_gemini_with_retry()`
- **조건**: `google.genai.errors.ServerError` (503·5xx)만 재시도, 4xx 인증 에러는 즉시 실패
- **지수 백오프**: 4초 → 8초 → 16초 → 32초 → 최대 60초
- **최대 5회 시도** (총 약 60초 버팀)
- 재시도 시 WARNING 로그로 추적 가능

**미구현 (향후 필요 시):**
- HuggingFace 이미지 API 재시도 — 현재 실패해도 파이프라인이 이미지 없이 계속 진행(`try/except` 처리됨)이라 우선순위 낮음
- WordPress API 재시도 — 실패 빈도 낮아 우선순위 낮음

**영향 파일:** `core/generator.py` (재시도 데코레이터 추가)

---

### 7. YouTube 썸네일 백업 활용
**목표:** 이미지 생성 실패 시 버려지는 YouTube 썸네일을 fallback으로 활용
**현재 상태:** [core/transcriber.py](core/transcriber.py)에서 `thumbnail_url` 추출 중이지만 main.py에서 미사용
**작업 내용:**
- 이미지 생성 실패 시 `upload_media_from_url(transcript.thumbnail_url)` 호출
- featured_media_id로 지정
**영향 파일:** `main.py`

---

### 8. 카테고리/태그 자동 지정
**목표:** WordPress 포스트의 카테고리·태그 자동 설정 (SEO/분류에 중요)
**현재 상태:** [core/wordpress.py](core/wordpress.py) `publish_post()` payload에 categories/tags 미포함
**작업 내용:**
- Gemini 응답에 `CATEGORY:`, `TAGS:` 라인 추가 요청
- WordPress 기존 카테고리·태그 목록 조회 API 연동 (GET `/wp-json/wp/v2/categories`)
- 매칭되는 ID 찾아서 POST payload에 삽입
- 새 태그는 자동 생성 허용 여부 결정
**영향 파일:** `config/prompts.py`, `core/generator.py`, `core/wordpress.py`

---

### 9. Dry-run 모드
**목표:** WordPress 게시 없이 HTML 결과물만 로컬로 확인
**작업 내용:**
- `main.py`에 `--dry-run` 플래그 추가
- 활성화 시 `output/<slug>.html` 파일로 저장, WordPress 호출 스킵
- 이미지 생성도 스킵 옵션 (`--no-image`) 고려
**영향 파일:** `main.py`

---

### 10. 중복 실행 방지
**목표:** 같은 YouTube URL을 이미 포스트로 발행했는지 감지
**작업 내용:**
- 처리한 URL을 `data/processed.jsonl`에 기록 (URL, post_id, 시각)
- 실행 시작 시 해당 URL이 이미 있으면 경고 + 사용자 확인
- `--force` 플래그로 덮어쓰기 허용
**영향 파일:** `main.py`, 새 `data/processed.jsonl`

---

### 11. 에러 복원력 (API 재시도 로직)
**목표:** 일시적 네트워크/API 실패로 전체 파이프라인이 죽지 않도록
**작업 내용:**
- Gemini, HuggingFace, WordPress 호출에 지수 백오프 재시도
- `tenacity` 라이브러리 도입 고려
- Timeout 명시적 설정
**영향 파일:** `core/generator.py`, `core/image_generator.py`, `core/wordpress.py`, `requirements.txt`

---

### 12. 배치 처리 모드
**목표:** URL 목록을 한 번에 처리
**작업 내용:**
- `urls.txt` 파일 지원 (`python main.py --batch urls.txt`)
- 각 URL마다 순차 실행, 실패 시 다음 URL 계속 진행
- 결과 리포트 (성공/실패 목록) 출력
**영향 파일:** `main.py`

---

### 13. 메타 디스크립션 / Excerpt 자동 생성
**목표:** WordPress의 excerpt 필드 채워 검색 결과 CTR 향상
**작업 내용:**
- Gemini 응답에 `EXCERPT:` 라인 추가 (150자 내외 Hook)
- `publish_post()` payload에 `excerpt` 필드 추가
**영향 파일:** `config/prompts.py`, `core/generator.py`, `core/wordpress.py`

---

### 14. 본문 중간 이미지 삽입
**목표:** 대표 이미지 외에 본문 섹션 사이에도 이미지 2~3장 자동 삽입
**작업 내용:**
- Gemini 응답에 `SECTION_IMAGE_PROMPTS:` 목록 추가 (본문 위치 표시 포함)
- 각 프롬프트로 이미지 생성·업로드
- 본문 HTML 변환 시 지정 위치에 `<img>` 삽입 (SEO 가이드대로 alt 포함)
**영향 파일:** `config/prompts.py`, `core/generator.py`, `core/image_generator.py`, `main.py`

---

### 15. 제품군/브랜드별 분리 아키텍처 (🗂 보류)
**현재 결정:** **보류.** 지금은 배터리 단일 브랜드로 WordPress 발행 완성에만 집중.
**재검토 트리거:** ATV 또는 골프카트 콘텐츠를 실제로 발행하기 직전 시점
**재검토 시 결정할 것:**
- **옵션 A**: 프로젝트 복제 (브랜드마다 repo 분리) — 운영 완전 격리, 코드 동기화 부담
- **옵션 B**: 단일 코드 + `data/brands/<name>/` 데이터 분리 + `--brand` 플래그 — 공통 개선 자동 전파, 데이터만 분리
**참고용 옵션 B 구조(착수 시):**
```
data/
├── brands/
│   ├── battery/      (company_info.md, SEO_GUIDE.md, keywords.md)
│   ├── atv/
│   └── golf_cart/
└── common/
```
CLI: `python main.py --brand battery "<url>"`
**지금 준비해둘 것(옵션 B 쪽 선택 대비용, 최소 비용):** 1번(회사소개)·3번(SEO)을 작성할 때 "배터리 한정" 내용은 파일 상단에 명시해두면, 나중에 분리 시점에 품이 덜 든다

---

### 16. 데이터 포집 & 웹 애널리틱스 통합
**목표:** 유입 경로·독자층 데이터를 수집해 콘텐츠 전략 의사결정 근거 확보 (SEO/AEO 관점)
**현재 상태:** 분석 도구 없음. 발행 후 성과 측정 불가
**시급성:** 중간 — 설치는 빠르지만 **데이터 누적에 4~8주** 필요
**작업 내용:**
- **GA4 설치**: WordPress 사이트에 GA4 스니펫 (플러그인 또는 theme header 직접 삽입)
- **Search Console 등록 및 사이트맵 제출**
- **AEO(Answer Engine Optimization) 마크업**: 포스트 HTML에 schema.org 구조화 데이터 자동 삽입
  - `Article` schema (작성자, 발행일)
  - `FAQPage` schema (FAQ 섹션용)
  - `HowTo` schema (가이드성 포스트용)
  - → AI 검색엔진(ChatGPT, Perplexity, Google SGE) 인용 확률 상승
- **UTM 태그 규칙**: 각 발행 채널(WP/네이버/IG/FB) 구분용 utm_source/medium/campaign 파라미터 규격 정립
- **대시보드**: 주요 지표(유입수, 체류시간, 전환) 주간 요약 리포트 자동 생성 (Looker Studio 또는 단순 스크립트)
**영향 파일:** `core/wordpress.py` (schema 삽입), 새 `core/analytics.py`, WordPress 설정

---

### 17. 독자 데이터 기반 타겟/카테고리 재조정
**목표:** 실제 유입 데이터로 타겟 페르소나·키워드·카테고리를 주기적으로 갱신
**현재 상태:** 가정 기반 페르소나. 실제 독자층 미검증
**시급성:** 낮음 — **16번 선행 필수**, 최소 1~2개월 데이터 축적 후
**작업 내용:**
- GA4 API로 주요 포스트 유입 키워드·지역·디바이스·연령대 추출
- 상위 키워드를 `data/brands/<brand>/keywords.md`에 주기적 반영
- 저성과 카테고리 축소, 고성과 주제 확대
- 타겟 페르소나 문서 업데이트 → 1번(회사소개) 자동 피드백 루프
- (고도화) 성과 데이터를 Gemini 프롬프트에 컨텍스트로 주입하여 글 스타일 자동 최적화
**영향 파일:** `data/brands/*/company_info.md`, `data/brands/*/SEO_GUIDE.md`, 신규 `scripts/analytics_feedback.py`

---

### Phase 2 개요 — 멀티채널 수직 슬라이스 🚀
**공통 원칙:**
- 각 플랫폼을 **독립 모듈 + 단독 엔트리포인트**로 완성 (예: `publish_naver.py`, `publish_instagram.py`)
- 공통 모듈(`core/transcriber`, `core/generator`)은 그대로 재사용
- 3개 모듈 완성 후 공통 인터페이스를 **추출** (미리 설계하지 않음)
- 같은 원본을 채널별 알고리즘·포맷·독자층에 맞춰 **재가공**
- 전 채널 UTM 태그 통일 (16번과 연동)

---

### 18a. 네이버 블로그 발행 모듈
**독립 엔트리포인트:** `publish_naver.py <youtube_url>`
**핵심 작업:**
- 네이버 OpenAPI 또는 자동화 기반 발행 (공식 API 제약 확인 필요)
- 네이버 톤 재가공 (WordPress 대비 더 감성적·구어체, 이모지 활발)
- 네이버 검색 특화 키워드 전략
- 네이버 전용 프롬프트 (`config/prompts_naver.py`)
**신규 환경변수:** `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` (또는 발행 계정 인증 방식)

---

### 18b. Instagram 카드뉴스 발행 모듈
**독립 엔트리포인트:** `publish_instagram.py <youtube_url>`
**핵심 작업:**
- 본문을 5~10장 카드 슬라이드로 재구성 (한 장당 핵심 1문장)
- 카드 이미지 자동 생성 (템플릿 SVG/Pillow + 텍스트 오버레이)
- Meta Graph API로 피드 발행 (+ 릴스 커버 선택)
- 해시태그 전략 (30개, 규모별 믹스)
- Instagram 전용 프롬프트 (`config/prompts_instagram.py`)
**신규 환경변수:** `META_ACCESS_TOKEN`, `IG_BUSINESS_ID`

---

### 18c. Facebook 발행 모듈
**독립 엔트리포인트:** `publish_facebook.py <youtube_url>`
**핵심 작업:**
- 핵심 훅 3~5줄 요약 + WordPress 포스트 링크
- Meta Graph API로 페이지 발행
- Facebook 전용 프롬프트 (`config/prompts_facebook.py`)
**신규 환경변수:** `META_ACCESS_TOKEN`, `FB_PAGE_ID`

---

### 18d. 통합 디스패처 (18a~c 완료 후)
**목표:** 3개 모듈의 실제 구현을 본 뒤 공통점을 추출하여 한 번에 멀티채널 발행
**착수 전제:** 18a, 18b, 18c 모두 실제 운영 중이어야 함 — **추상화는 현실 데이터 기반**으로
**작업 내용:**
- 공통 인터페이스 식별 (`Distributor.publish(post, media) -> Result`)
- `core/distributors/` 아래로 기존 모듈 이전
- `publish_all.py <youtube_url>` 엔트리포인트 추가 — 1회 실행으로 전체 채널 발행
- 채널별 실패 격리 (한 채널 실패해도 나머지 계속)
- 통합 로그 + 채널별 결과 리포트

---

## 📝 진행 메모

각 항목 완료 시 아래에 날짜·커밋해시·간단 메모 기록:

| 번호 | 완료일 | 메모 |
|------|--------|------|
| 1    | 2026-04-23 | 회사소개 보강 — 회사 팩트(`company_info.md`)와 작성 규칙(`editorial_guide.md`)을 관심사 분리. 페르소나·금지사항·CTA 중복 방지 규칙 추가. 브랜드 포트폴리오 16개 사이트 정리. |
| 2    | 2026-04-23 | Draft 게시 워크플로우 — `main.py`에 argparse 도입, `--publish` 단일 플래그 (기본 draft). draft 저장 시 WP 관리자 편집 링크 출력. Post ID=3727 테스트 성공. |
| 3    | 2026-04-23 | SEO 가이드 보강 — `SEO_GUIDE.md` 5절 → 11절로 확장(제목 공식·Hook·TOC·FAQ·E-E-A-T·자가 검증). 키워드를 시드(정적)+트렌드(동적) 이중 파일로 분리. 자동 수집은 3-A, 3-B로 분리. |
| 3-B  | 2026-04-23 | 트렌드 키워드 자동 수집 — `core/trends.py` 신규. 네이버 데이터랩 + YouTube Data API v3로 `main.py` 실행 시마다 자동 수집·파일 갱신. 생성 로그(`logs/generation_*.md`) 기록. |
| 3-A  | 2026-04-23 | ❌ 취소 — 브랜드 시드 변경 빈도 낮아 수동 유지로 충분하다고 판단. |
| 6    | 2026-04-23 | 본문 생성 프롬프트 보강 — SYSTEM_PROMPT 20줄 → ~100줄 재작성. 9단계 생성 절차, 본문 템플릿, FAQ 포함 기준, 시각 요소 6종 규칙, 제조사 관점 삽입 규칙 추가. 결과물 품질 개선 확인. |
| 11   | 2026-04-23 | 에러 복원력 부분 완료 — Gemini 503/5xx에 지수 백오프 재시도(최대 5회, 60초). HF·WP는 미구현 유지. |
