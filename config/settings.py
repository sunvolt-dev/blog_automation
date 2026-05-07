from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_model: str
    hf_token: str
    wp_base_url: str
    wp_username: str
    wp_password: str
    naver_client_id: str
    naver_client_secret: str
    youtube_api_key: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:8080/v1").strip(),
        llm_model=os.getenv("LLM_MODEL", "mlx-community/Qwen3-32B-4bit").strip(),
        hf_token=os.getenv("HF_TOKEN", "").strip(),
        wp_base_url=os.getenv("WP_BASE_URL", "").strip(),
        wp_username=os.getenv("WP_USERNAME", "").strip(),
        wp_password=os.getenv("WP_PASSWORD", "").strip(),
        naver_client_id=os.getenv("NAVER_CLIENT_ID", "").strip(),
        naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", "").strip(),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY", "").strip(),
    )
