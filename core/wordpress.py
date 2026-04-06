from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class WordPressPostResult:
    post_id: int
    link: str


def _basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def upload_media_from_url(
    *,
    wp_base_url: str,
    wp_username: str,
    wp_password: str,
    image_url: str,
    filename: str = "thumbnail.jpg",
) -> int:
    """이미지 URL을 WordPress 미디어 라이브러리에 업로드하고 media ID를 반환합니다."""
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    # URL에서 확장자 추론
    parsed_path = urlparse(image_url).path
    ext = Path(parsed_path).suffix
    if ext:
        filename = f"thumbnail{ext}"
    else:
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        filename = f"thumbnail{ext}"

    upload_url = wp_base_url.rstrip("/") + "/wp-json/wp/v2/media"
    headers = {
        "Authorization": _basic_auth_header(wp_username, wp_password),
        "Content-Type": content_type,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    upload_resp = requests.post(upload_url, headers=headers, data=resp.content, timeout=60)
    upload_resp.raise_for_status()
    return int(upload_resp.json()["id"])


def upload_media_from_bytes(
    *,
    wp_base_url: str,
    wp_username: str,
    wp_password: str,
    image_data: bytes,
    mime_type: str,
    filename: str = "generated-image.png",
) -> int:
    """이미지 바이트를 WordPress 미디어 라이브러리에 업로드하고 media ID를 반환합니다."""
    ext = mimetypes.guess_extension(mime_type) or ".png"
    if not filename.endswith(ext):
        filename = f"generated-image{ext}"

    upload_url = wp_base_url.rstrip("/") + "/wp-json/wp/v2/media"
    headers = {
        "Authorization": _basic_auth_header(wp_username, wp_password),
        "Content-Type": mime_type,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    resp = requests.post(upload_url, headers=headers, data=image_data, timeout=60)
    resp.raise_for_status()
    return int(resp.json()["id"])


def publish_post(
    *,
    wp_base_url: str,
    wp_username: str,
    wp_password: str,
    title: str,
    content: str,
    status: str = "publish",
    featured_media_id: int = 0,
) -> WordPressPostResult:
    """
    wp_base_url 예: https://example.com
    REST 엔드포인트: {wp_base_url}/wp-json/wp/v2/posts
    """
    url = wp_base_url.rstrip("/") + "/wp-json/wp/v2/posts"
    headers = {
        "Authorization": _basic_auth_header(wp_username, wp_password),
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    payload: dict = {"title": title, "content": content, "status": status}
    if featured_media_id:
        payload["featured_media"] = featured_media_id

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return WordPressPostResult(post_id=int(data["id"]), link=str(data.get("link", "")))
