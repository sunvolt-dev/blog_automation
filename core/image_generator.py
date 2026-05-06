from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

_HF_FLUX_URL = (
    "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
)


def generate_and_upload_image(
    prompt: str,
    *,
    hf_token: str,
    wp_base_url: str,
    wp_username: str,
    wp_password: str,
    max_attempts: int = 3,
) -> int:
    """HuggingFace FLUX.1-schnell로 이미지를 생성하고 WordPress에 업로드, media ID 반환."""
    from core.wordpress import upload_media_from_bytes

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "x-wait-for-model": "true",
        "Accept": "image/png",
    }

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(
                _HF_FLUX_URL,
                headers=headers,
                json={"inputs": prompt},
                timeout=180,
            )
        except requests.RequestException as e:
            last_error = e
            wait = min(2**attempt, 30)
            logger.warning(
                "HF 호출 네트워크 오류 (attempt %d/%d, %ds 후 재시도): %s",
                attempt, max_attempts, wait, e,
            )
            time.sleep(wait)
            continue

        content_type_hdr = resp.headers.get("Content-Type", "")

        # cold start / 큐 대기: 503·502 + JSON
        if resp.status_code in (502, 503) and "json" in content_type_hdr:
            try:
                est = float(resp.json().get("estimated_time", 5.0))
            except Exception:
                est = 5.0
            wait = min(est + 1.0, 30.0)
            logger.info(
                "HF 모델 로딩 중, %.1fs 후 재시도 (attempt %d/%d)",
                wait, attempt, max_attempts,
            )
            time.sleep(wait)
            continue

        if not resp.ok:
            last_error = RuntimeError(
                f"HF {resp.status_code}: {resp.text[:200]}"
            )
            logger.warning(
                "HF 응답 오류 %d (attempt %d/%d): %s",
                resp.status_code, attempt, max_attempts, resp.text[:200],
            )
            time.sleep(min(2**attempt, 30))
            continue

        content_type = content_type_hdr.split(";")[0].strip() or "image/png"
        if not content_type.startswith("image/"):
            last_error = RuntimeError(f"이미지가 아닌 응답 ({content_type})")
            logger.warning(
                "HF 응답이 이미지 아님 (attempt %d/%d): %s",
                attempt, max_attempts, content_type,
            )
            time.sleep(min(2**attempt, 30))
            continue

        return upload_media_from_bytes(
            wp_base_url=wp_base_url,
            wp_username=wp_username,
            wp_password=wp_password,
            image_data=resp.content,
            mime_type=content_type,
        )

    raise RuntimeError(
        f"HF 이미지 생성 실패 ({max_attempts}회 재시도 후): {last_error}"
    )
