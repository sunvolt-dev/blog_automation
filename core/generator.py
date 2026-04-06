from __future__ import annotations

from dataclasses import dataclass

from google import genai


@dataclass(frozen=True)
class GeneratedPost:
    title: str
    markdown: str
    image_prompt: str  # 이미지 생성에 사용할 영어 프롬프트


def generate_blog_post(
    transcript_text: str,
    company_info_md: str,
    seo_guide_md: str,
    system_prompt: str,
    api_key: str,
) -> GeneratedPost:
    client = genai.Client(api_key=api_key)

    user_message = f"""다음 유튜브 자막을 바탕으로 블로그 글을 작성해주세요.

## 회사 정보
{company_info_md}

## SEO 가이드 (반드시 준수)
{seo_guide_md}

## 유튜브 자막
{transcript_text}
"""

    response = client.models.generate_content(
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

    # IMAGE_PROMPT: 줄 찾기 (본문 끝에 있을 수 있음)
    image_prompt = ""
    body_lines = []
    for line in lines[body_start:]:
        if line.startswith("IMAGE_PROMPT:"):
            image_prompt = line[len("IMAGE_PROMPT:"):].strip()
        else:
            body_lines.append(line)

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
