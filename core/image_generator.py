from __future__ import annotations

import requests


def generate_and_upload_image(
    prompt: str,
    *,
    hf_token: str,
    wp_base_url: str,
    wp_username: str,
    wp_password: str,
) -> int:
    """Hugging Face로 이미지를 생성하고 WordPress에 업로드 후 media ID를 반환합니다."""
    from core.wordpress import upload_media_from_bytes

    resp = requests.post(
        "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
        headers={"Authorization": f"Bearer {hf_token}"},
        json={"inputs": prompt},
        timeout=120,
    )
    resp.raise_for_status()

    return upload_media_from_bytes(
        wp_base_url=wp_base_url,
        wp_username=wp_username,
        wp_password=wp_password,
        image_data=resp.content,
        mime_type="image/jpeg",
    )
