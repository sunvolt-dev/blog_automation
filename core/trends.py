from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import requests

logger = logging.getLogger(__name__)

# 트렌드 수집에 사용할 시드 쿼리. 사이트/브랜드 확장 시 이 목록만 편집.
TRENDING_SEED_QUERIES: list[str] = [
    "리튬이온 배터리",
    "리튬인산철 배터리",
    "LFP 배터리",
    "보조배터리",
    "파워뱅크",
    "고속충전",
    "PD 충전",
    "무선이어폰",
    "무선 충전기",
    "노이즈 캔슬링",
    "지게차 배터리",
    "골프카트 배터리",
    "AGV 배터리",
    "전동카트",
    "전동 지게차",
    "캠핑카 배터리",
    "태양광 ESS",
    "에너지저장장치",
    "배터리 수명",
    "배터리 관리",
]

_NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass(frozen=True)
class NaverTrendItem:
    keyword: str
    recent_ratio: float
    baseline_ratio: float
    change_pct: float


@dataclass(frozen=True)
class YouTubeTrendItem:
    keyword: str
    top_titles: tuple[str, ...] = ()
    top_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrendingResult:
    naver_trends: tuple[NaverTrendItem, ...] = ()
    youtube_trends: tuple[YouTubeTrendItem, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def has_any_data(self) -> bool:
        return bool(self.naver_trends or self.youtube_trends)


def collect_naver_trends(
    client_id: str,
    client_secret: str,
    seed_queries: list[str] | None = None,
) -> list[NaverTrendItem]:
    """네이버 데이터랩 검색어 트렌드 API로 최근 4주 비율 → 상승률 계산.

    구조: 지난 4주를 week 단위로 조회하여 가장 최근 주와 이전 3주 평균을 비교.
    API는 상대 비율(0~100)만 제공하므로 절대 검색량이 아닌 '상대 상승률'임.
    """
    if not client_id or not client_secret:
        logger.warning("네이버 API 자격증명 없음 — 네이버 트렌드 수집 스킵")
        return []

    queries = seed_queries or TRENDING_SEED_QUERIES
    end = date.today()
    start = end - timedelta(days=28)
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    results: list[NaverTrendItem] = []
    for i in range(0, len(queries), 5):
        chunk = queries[i : i + 5]
        body = {
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d"),
            "timeUnit": "week",
            "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in chunk],
        }
        try:
            resp = requests.post(_NAVER_DATALAB_URL, json=body, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("네이버 데이터랩 호출 실패 (chunk=%d): %s", i // 5, e)
            continue

        for item in data.get("results", []):
            kw = item.get("title", "")
            series = item.get("data", [])
            if len(series) < 2:
                continue
            ratios = [float(p.get("ratio", 0.0)) for p in series]
            recent = ratios[-1]
            baseline_list = ratios[:-1]
            baseline = sum(baseline_list) / len(baseline_list) if baseline_list else 0.0
            change_pct = ((recent - baseline) / baseline * 100.0) if baseline > 0 else 0.0
            results.append(
                NaverTrendItem(
                    keyword=kw,
                    recent_ratio=recent,
                    baseline_ratio=baseline,
                    change_pct=change_pct,
                )
            )

    results.sort(key=lambda x: x.change_pct, reverse=True)
    return results


def collect_youtube_trends(
    api_key: str,
    seed_queries: list[str] | None = None,
    published_after_days: int = 7,
    max_results_per_query: int = 5,
) -> list[YouTubeTrendItem]:
    """YouTube Data API v3로 최근 N일간 인기 영상 제목/태그 수집."""
    if not api_key:
        logger.warning("YouTube API 키 없음 — YouTube 트렌드 수집 스킵")
        return []

    queries = seed_queries or TRENDING_SEED_QUERIES
    published_after = (date.today() - timedelta(days=published_after_days)).strftime(
        "%Y-%m-%dT00:00:00Z"
    )

    results: list[YouTubeTrendItem] = []
    for kw in queries:
        try:
            search_resp = requests.get(
                _YOUTUBE_SEARCH_URL,
                params={
                    "key": api_key,
                    "part": "snippet",
                    "q": kw,
                    "type": "video",
                    "maxResults": max_results_per_query,
                    "order": "viewCount",
                    "publishedAfter": published_after,
                    "regionCode": "KR",
                    "relevanceLanguage": "ko",
                },
                timeout=15,
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()
        except Exception as e:
            logger.warning("YouTube search 실패 (%s): %s", kw, e)
            continue

        items = search_data.get("items", [])
        video_ids = [it["id"]["videoId"] for it in items if "videoId" in it.get("id", {})]
        titles = [it["snippet"]["title"] for it in items if "snippet" in it]

        tags: list[str] = []
        if video_ids:
            try:
                v_resp = requests.get(
                    _YOUTUBE_VIDEOS_URL,
                    params={
                        "key": api_key,
                        "part": "snippet",
                        "id": ",".join(video_ids),
                    },
                    timeout=15,
                )
                v_resp.raise_for_status()
                v_data = v_resp.json()
                for vitem in v_data.get("items", []):
                    tags.extend(vitem.get("snippet", {}).get("tags", []))
            except Exception as e:
                logger.warning("YouTube videos 실패 (%s): %s", kw, e)

        top_tags = tuple(t for t, _ in Counter(tags).most_common(10))

        results.append(
            YouTubeTrendItem(
                keyword=kw,
                top_titles=tuple(titles),
                top_tags=top_tags,
            )
        )

    return results


def collect_trending_keywords(
    naver_client_id: str,
    naver_client_secret: str,
    youtube_api_key: str,
) -> TrendingResult:
    """네이버 + YouTube 트렌드 통합 수집. 소스별 실패는 해당 소스만 비움."""
    errors: list[str] = []

    try:
        naver = collect_naver_trends(naver_client_id, naver_client_secret)
    except Exception as e:
        logger.exception("네이버 트렌드 전체 실패")
        naver = []
        errors.append(f"naver: {e}")

    try:
        youtube = collect_youtube_trends(youtube_api_key)
    except Exception as e:
        logger.exception("YouTube 트렌드 전체 실패")
        youtube = []
        errors.append(f"youtube: {e}")

    return TrendingResult(
        naver_trends=tuple(naver),
        youtube_trends=tuple(youtube),
        errors=tuple(errors),
    )


def format_trending_markdown(result: TrendingResult) -> str:
    """TrendingResult → keywords_trending.md 본문으로 쓸 마크다운."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        "# 트렌드 키워드 (자동 수집)",
        "",
        f"> **최종 수집 시각**: {now}",
        "> **수집 소스**: 네이버 데이터랩(검색어 트렌드) + YouTube Data API v3",
        "> **갱신 주기**: `main.py` 실행 시마다 자동 갱신",
        "> **활용 지침**: 글 주제와 직접 관련된 키워드만 본문·제목에 자연스럽게 반영. 무관한 키워드 억지 삽입 금지. 시드 키워드(`keywords_seed.md`)와 충돌 시 본 트렌드 표기 우선.",
        "",
    ]

    if result.errors:
        lines += ["## ⚠️ 수집 오류", ""]
        for e in result.errors:
            lines.append(f"- {e}")
        lines.append("")

    lines += [
        "## 1. 네이버 검색어 상승 키워드 (최근 1주 vs 이전 3주)",
        "",
    ]
    if result.naver_trends:
        for item in result.naver_trends[:15]:
            sign = "+" if item.change_pct >= 0 else ""
            lines.append(
                f"- **{item.keyword}** — {sign}{item.change_pct:.1f}% "
                f"(최근 {item.recent_ratio:.1f} / 기준 {item.baseline_ratio:.1f})"
            )
    else:
        lines.append("*(데이터 없음)*")
    lines.append("")

    lines += [
        "## 2. YouTube 최근 7일 인기 영상·태그 (시드별)",
        "",
    ]
    youtube_has_content = False
    if result.youtube_trends:
        for item in result.youtube_trends:
            if not item.top_titles and not item.top_tags:
                continue
            youtube_has_content = True
            lines.append(f"### 🔎 시드: {item.keyword}")
            if item.top_titles:
                lines.append("**인기 영상 제목**")
                for t in item.top_titles[:3]:
                    lines.append(f"- {t}")
            if item.top_tags:
                lines.append(f"**연관 태그**: {', '.join(item.top_tags[:10])}")
            lines.append("")
    if not youtube_has_content:
        lines.append("*(데이터 없음)*")
        lines.append("")

    return "\n".join(lines)
