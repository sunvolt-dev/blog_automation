from __future__ import annotations

import logging
from dataclasses import dataclass

from google import genai
from google.genai.errors import ServerError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedPost:
    title: str
    markdown: str
    image_prompt: str  # 이미지 생성에 사용할 영어 프롬프트


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    retry=retry_if_exception_type(ServerError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini_with_retry(client, model: str, contents: str, config: dict):
    """Gemini API 호출. 503/5xx ServerError 발생 시 지수 백오프로 최대 5회 재시도."""
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )


def generate_blog_post(
    transcript_text: str,
    company_info_md: str,
    editorial_guide_md: str,
    seo_guide_md: str,
    keywords_seed_md: str,
    keywords_trending_md: str,
    system_prompt: str,
    api_key: str,
) -> GeneratedPost:
    client = genai.Client(api_key=api_key)

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

    response = _call_gemini_with_retry(
        client=client,
        model="gemini-2.5-flash",
        contents=user_message,
        config={"system_instruction": system_prompt},
    )

    text_content = response.text.strip()

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

    # IMAGE_PROMPT: 이후 본문 끝까지 모든 줄을 수집 (다중 줄 지원)
    image_prompt_lines: list[str] = []
    body_lines: list[str] = []
    in_image_prompt = False
    for line in lines[body_start:]:
        if line.startswith("IMAGE_PROMPT:"):
            in_image_prompt = True
            first_content = line[len("IMAGE_PROMPT:"):].strip()
            if first_content:
                image_prompt_lines.append(first_content)
        elif in_image_prompt:
            image_prompt_lines.append(line)
        else:
            body_lines.append(line)

    image_prompt = "\n".join(image_prompt_lines).strip()
    markdown = "\n".join(body_lines).strip()

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
