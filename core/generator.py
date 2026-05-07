from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, OpenAI
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

# 본문 누수 방지: 굵게/헤딩/평문 모두 잡는 IMAGE_PROMPT 마커 라인
_IMAGE_MARKER_LINE_RE = re.compile(
    r"^\s*\*{0,2}#{0,3}\s*IMAGE_PROMPT\s*:?\s*\*{0,2}\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class GeneratedPost:
    title: str
    markdown: str
    image_prompt: str  # 이미지 생성에 사용할 영어 프롬프트


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    retry=retry_if_exception_type((APIConnectionError, APIStatusError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_llm_with_retry(client: OpenAI, **kwargs):
    """로컬 mlx-lm 서버 호출. 연결/5xx 발생 시 지수 백오프로 최대 5회 재시도."""
    return client.chat.completions.create(**kwargs)


def generate_blog_post(
    transcript_text: str,
    company_info_md: str,
    editorial_guide_md: str,
    seo_guide_md: str,
    keywords_seed_md: str,
    keywords_trending_md: str,
    system_prompt: str,
    base_url: str,
    model: str,
) -> GeneratedPost:
    client = OpenAI(base_url=base_url, api_key="not-needed")

    user_message = f"""다음 유튜브 자막을 바탕으로 블로그 글을 작성해주세요.

## 회사 정보
{company_info_md}

## 작성 가이드 (반드시 준수 — 페르소나·금지사항·CTA 중복 방지)
{editorial_guide_md}

## SEO 가이드 (반드시 준수)
{seo_guide_md}

## 키워드 시드 (브랜드 주제 가이드 — 정적)
{keywords_seed_md}

## 트렌드 키워드 (주 단위 갱신 — 비어 있으면 시드만 사용)
{keywords_trending_md}

## 유튜브 자막
{transcript_text}
"""

    system_with_no_think = system_prompt.rstrip() + "\n\n/no_think"

    response = _call_llm_with_retry(
        client=client,
        model=model,
        messages=[
            {"role": "system", "content": system_with_no_think},
            {"role": "user", "content": user_message},
        ],
        temperature=0.6,
        top_p=0.9,
        presence_penalty=0.3,
        max_tokens=16384,
        seed=42,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise RuntimeError(
            f"LLM 응답에 content 가 비어있습니다 (reasoning 모드 누수 가능성). "
            f"finish_reason={response.choices[0].finish_reason}"
        )
    text_content = _THINK_BLOCK_RE.sub("", raw_content.strip()).strip()

    # TITLE: 줄과 본문 분리
    lines = text_content.splitlines()
    title = ""
    body_start = 0

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line[len("TITLE:"):].strip().strip("*#`").strip()
            body_start = i + 1
            break

    # 제목 다음 빈 줄 건너뛰기
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    # IMAGE_PROMPT 마커 — 굵게/헤딩/평문 어떤 형태든 매칭, 마지막 출현 기준 분리
    body_text = "\n".join(lines[body_start:])
    marker_matches = list(_IMAGE_MARKER_LINE_RE.finditer(body_text))
    if marker_matches:
        last = marker_matches[-1]
        markdown_section = body_text[: last.start()]
        image_prompt = body_text[last.end():].strip()
    else:
        markdown_section = body_text
        image_prompt = ""

    # 방어적 클린업: 본문에 남은 IMAGE_PROMPT 마커성 라인 제거
    markdown = _IMAGE_MARKER_LINE_RE.sub("", markdown_section).strip()

    # 폴백: 첫 번째 heading을 제목으로
    if not title:
        for line in lines:
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
    if not title:
        title = "블로그 포스트"

    # 이미지 프롬프트 폴백
    if not image_prompt:
        image_prompt = (
            f"Professional product photography for a Korean battery and electronics company blog. "
            f"Topic: {title}. Clean, modern, high quality."
        )

    return GeneratedPost(title=title, markdown=markdown, image_prompt=image_prompt)
