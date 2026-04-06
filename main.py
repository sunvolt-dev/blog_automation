from __future__ import annotations

import logging
from pathlib import Path

import markdown as md

from config.prompts import SYSTEM_PROMPT
from config.settings import load_settings
from core.generator import generate_blog_post
from core.image_generator import generate_and_upload_image
from core.transcriber import transcribe_from_youtube_url
from core.wordpress import publish_post


def _setup_logging() -> None:
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "automation.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def main(youtube_url: str) -> None:
    _setup_logging()
    logger = logging.getLogger("yt-blog-automation")

    try:
        settings = load_settings()
        data_dir = Path(__file__).parent / "data"
        company_info = (data_dir / "company_info.md").read_text(encoding="utf-8")
        seo_guide = (data_dir / "SEO_GUIDE.md").read_text(encoding="utf-8")

        # 1. 자막 추출
        logger.info("자막 추출 중: %s", youtube_url)
        transcript = transcribe_from_youtube_url(youtube_url)
        logger.info("자막 추출 완료 (%d자)", len(transcript.cleaned))

        # 2. 블로그 글 생성 (Gemini)
        logger.info("블로그 글 생성 중 (Gemini 2.0 Flash)")
        post = generate_blog_post(
            transcript_text=transcript.cleaned,
            company_info_md=company_info,
            seo_guide_md=seo_guide,
            system_prompt=SYSTEM_PROMPT,
            api_key=settings.gemini_api_key,
        )
        logger.info("생성 완료: '%s'", post.title)
        logger.info("이미지 프롬프트: %s", post.image_prompt)

        # 3. 이미지 생성 및 업로드 (Pollinations.ai → WordPress)
        featured_media_id = 0

        logger.info("이미지 생성 중 (Pollinations.ai)")
        try:
            featured_media_id = generate_and_upload_image(
                prompt=post.image_prompt,
                hf_token=settings.hf_token,
                wp_base_url=settings.wp_base_url,
                wp_username=settings.wp_username,
                wp_password=settings.wp_password,
            )
            logger.info("이미지 업로드 완료 (media ID=%d)", featured_media_id)
        except Exception as e:
            logger.warning("이미지 생성/업로드 실패, 이미지 없이 진행: %s", e)

        # 4. WordPress 게시 (마크다운 → HTML 변환)
        html_content = md.markdown(post.markdown, extensions=["extra", "nl2br"])
        html_content += """
<hr>
<p><strong>배터리 관련 궁금한 점이 있으신가요?</strong><br>
코리아배터리 전문 상담팀이 도와드리겠습니다.<br>
📞 <strong>031-990-3362</strong>로 문의주세요!</p>
"""
        logger.info("WordPress에 포스트 게시 중")
        result = publish_post(
            wp_base_url=settings.wp_base_url,
            wp_username=settings.wp_username,
            wp_password=settings.wp_password,
            title=post.title,
            content=html_content,
            featured_media_id=featured_media_id,
        )

        logger.info("완료. Post ID=%s Link=%s", result.post_id, result.link)
    except Exception:
        logger.exception("자동화 실패")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("사용법: python main.py <youtube_url>")

    main(sys.argv[1])
