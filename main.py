from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import markdown as md
import requests

from config.prompts import SYSTEM_PROMPT
from config.settings import load_settings
from core.generator import GeneratedPost, generate_blog_post
from core.image_generator import generate_and_upload_image
from core.transcriber import transcribe_from_youtube_url
from core.trends import (
    TrendingResult,
    collect_trending_keywords,
    format_trending_markdown,
)
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


def _admin_edit_url(wp_base_url: str, post_id: int) -> str:
    return wp_base_url.rstrip("/") + f"/wp-admin/post.php?post={post_id}&action=edit"


def _check_llm_server(base_url: str, model: str) -> None:
    """mlx_lm.server 가 살아있는지 사전 확인. 죽어 있으면 즉시 친절한 에러."""
    try:
        requests.get(base_url.rstrip("/") + "/models", timeout=5).raise_for_status()
    except Exception as e:
        raise RuntimeError(
            f"LLM 서버에 연결할 수 없습니다 ({base_url}): {e}\n"
            f"별도 터미널에서 다음 명령으로 서버를 먼저 기동하세요:\n"
            f"  mlx_lm.server --model {model} --port 8080"
        ) from e


def _write_generation_log(
    *,
    log_dir: Path,
    started_at: datetime,
    youtube_url: str,
    transcript_preview: str,
    post: GeneratedPost,
    trending: TrendingResult,
    publish: bool,
    post_id: int,
    primary_link: str,
) -> Path:
    """생성 1건에 대한 메타데이터 로그(.md)를 logs/ 아래 기록."""
    ts = started_at.strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"generation_{ts}.md"

    lines: list[str] = [
        "# Blog Generation Log",
        "",
        f"- **실행 시각**: {started_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **YouTube URL**: {youtube_url}",
        f"- **상태**: {'발행(publish)' if publish else '초안(draft)'}",
        f"- **Post ID**: {post_id}",
        f"- **{'Public Link' if publish else '편집 URL'}**: {primary_link}",
        "",
        "## 생성 제목",
        post.title,
        "",
        "## 이미지 프롬프트",
        f"`{post.image_prompt}`",
        "",
        "## 자막 미리보기 (첫 400자)",
        transcript_preview,
        "",
        "## 수집된 네이버 트렌드 (상위 10)",
    ]
    if trending.naver_trends:
        for item in trending.naver_trends[:10]:
            lines.append(
                f"- {item.keyword} — {item.change_pct:+.1f}% "
                f"(최근 {item.recent_ratio:.1f} / 기준 {item.baseline_ratio:.1f})"
            )
    else:
        lines.append("*(없음)*")

    lines += ["", "## 수집된 YouTube 트렌드 (시드별 요약)"]
    if trending.youtube_trends:
        for item in trending.youtube_trends:
            if not item.top_titles and not item.top_tags:
                continue
            tags_preview = ", ".join(item.top_tags[:5]) or "N/A"
            lines.append(
                f"- **{item.keyword}**: 영상 {len(item.top_titles)}건 / 태그: {tags_preview}"
            )
    else:
        lines.append("*(없음)*")

    if trending.errors:
        lines += ["", "## 수집 오류"]
        for e in trending.errors:
            lines.append(f"- {e}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


def main(youtube_url: str, publish: bool = False) -> None:
    _setup_logging()
    logger = logging.getLogger("yt-blog-automation")
    started_at = datetime.now()

    status = "publish" if publish else "draft"

    try:
        settings = load_settings()
        _check_llm_server(settings.llm_base_url, settings.llm_model)
        base_dir = Path(__file__).parent
        data_dir = base_dir / "data"
        logs_dir = base_dir / "logs"

        company_info = (data_dir / "company_info.md").read_text(encoding="utf-8")
        editorial_guide = (data_dir / "editorial_guide.md").read_text(encoding="utf-8")
        seo_guide = (data_dir / "SEO_GUIDE.md").read_text(encoding="utf-8")
        keywords_seed = (data_dir / "keywords_seed.md").read_text(encoding="utf-8")
        footer_cta = (data_dir / "footer_cta.md").read_text(encoding="utf-8")

        # 1. 자막 추출
        logger.info("자막 추출 중: %s", youtube_url)
        transcript = transcribe_from_youtube_url(youtube_url)
        logger.info("자막 추출 완료 (%d자)", len(transcript.cleaned))

        # 2. 트렌드 키워드 수집 (네이버 + YouTube)
        logger.info("트렌드 키워드 수집 중 (네이버 + YouTube)")
        trending = collect_trending_keywords(
            naver_client_id=settings.naver_client_id,
            naver_client_secret=settings.naver_client_secret,
            youtube_api_key=settings.youtube_api_key,
        )
        if trending.has_any_data:
            trending_md = format_trending_markdown(trending)
            (data_dir / "keywords_trending.md").write_text(trending_md, encoding="utf-8")
            keywords_trending = trending_md
            logger.info(
                "트렌드 수집 완료 — 네이버 %d개, YouTube 시드 %d개",
                len(trending.naver_trends),
                len(trending.youtube_trends),
            )
        else:
            trending_path = data_dir / "keywords_trending.md"
            if trending_path.exists():
                keywords_trending = trending_path.read_text(encoding="utf-8")
                logger.warning("트렌드 수집 결과 없음 — 기존 keywords_trending.md 사용")
            else:
                keywords_trending = ""
                logger.warning("트렌드 수집 결과 없음 — 트렌드 키워드 없이 진행 (시드만 사용)")
            for e in trending.errors:
                logger.warning("수집 오류: %s", e)

        # 3. 블로그 글 생성 (로컬 LLM via mlx_lm.server)
        logger.info("블로그 글 생성 중 (local LLM: %s)", settings.llm_model)
        post = generate_blog_post(
            transcript_text=transcript.cleaned,
            company_info_md=company_info,
            editorial_guide_md=editorial_guide,
            seo_guide_md=seo_guide,
            keywords_seed_md=keywords_seed,
            keywords_trending_md=keywords_trending,
            system_prompt=SYSTEM_PROMPT,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
        logger.info("생성 완료: '%s'", post.title)
        logger.info("이미지 프롬프트: %s", post.image_prompt)

        # 4. 이미지 생성 및 업로드 (로컬 mflux FLUX.1-dev → WordPress)
        featured_media_id = 0
        logger.info("이미지 생성 중 (로컬 mflux FLUX.1-dev BF16)")
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

        # 5. WordPress 게시
        full_markdown = post.markdown.rstrip() + "\n\n" + footer_cta.lstrip()
        html_content = md.markdown(
            full_markdown,
            extensions=["extra", "nl2br", "tables", "sane_lists"],
        )
        logger.info("WordPress %s 중", "발행" if publish else "초안 저장")
        result = publish_post(
            wp_base_url=settings.wp_base_url,
            wp_username=settings.wp_username,
            wp_password=settings.wp_password,
            title=post.title,
            content=html_content,
            status=status,
            featured_media_id=featured_media_id,
        )

        if publish:
            primary_link = result.link
            logger.info("발행 완료. Post ID=%s Link=%s", result.post_id, primary_link)
        else:
            primary_link = _admin_edit_url(settings.wp_base_url, result.post_id)
            logger.info("초안 저장 완료 (Post ID=%s)", result.post_id)
            logger.info("검토·발행 링크: %s", primary_link)

        # 6. 생성 로그 기록
        transcript_preview = transcript.cleaned[:400]
        if len(transcript.cleaned) > 400:
            transcript_preview += "..."
        log_path = _write_generation_log(
            log_dir=logs_dir,
            started_at=started_at,
            youtube_url=youtube_url,
            transcript_preview=transcript_preview,
            post=post,
            trending=trending,
            publish=publish,
            post_id=result.post_id,
            primary_link=primary_link,
        )
        logger.info("생성 로그 기록: %s", log_path)
    except Exception:
        logger.exception("자동화 실패")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YouTube 영상 → 코리아배터리 블로그 포스트 자동 변환",
    )
    parser.add_argument("youtube_url", help="YouTube 영상 URL")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="즉시 발행 (지정하지 않으면 초안(draft)으로 저장하고 편집 링크를 출력)",
    )
    args = parser.parse_args()
    main(youtube_url=args.youtube_url, publish=args.publish)
